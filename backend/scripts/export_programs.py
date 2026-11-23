"""Export public UMN Twin Cities catalog programs without interpreting academic rules."""
import json
import csv
import hashlib
import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


class _Bootstrap(HTMLParser):
    def __init__(self):
        super().__init__()
        self.collect = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.collect = dict(attrs).get("id") == "__NUXT_DATA__"

    def handle_endtag(self, tag):
        if tag == "script":
            self.collect = False

    def handle_data(self, data):
        if self.collect:
            self.parts.append(data)


def discover_catalog(html):
    parser = _Bootstrap()
    parser.feed(html)
    nodes = json.loads("".join(parser.parts))

    def resolve(index):
        if index < 0:
            return None
        value = nodes[index]
        if isinstance(value, dict):
            return {key: resolve(ref) for key, ref in value.items()}
        if isinstance(value, list):
            if value and value[0] in ("Reactive", "Ref", "ShallowReactive"):
                return resolve(value[1])
            return [resolve(ref) for ref in value]
        return value

    pinia = nodes[nodes[0]["pinia"]]
    settings = nodes[nodes[pinia[1]]["settings"]]
    dates = resolve(settings["effectiveDatesRange"])
    return {
        "catalog_id": resolve(settings["activeCatalog"]),
        "school": resolve(settings["school"]),
        "effective_start": dates["effectiveStartDate"],
        "effective_end": dates["effectiveEndDate"],
        "filters": resolve(settings["programsFilters"]),
    }


def fetch_programs(session, config):
    url = f"https://app.coursedog.com/api/v1/cm/{config['school']}/programs/search/%24filters"
    records = []
    expected_total = None
    while True:
        params = {
            "catalogId": config["catalog_id"], "skip": len(records), "limit": 500,
            "sortBy": "id",
            "effectiveDatesRange": f"{config['effective_start']},{config['effective_end']}",
        }
        response = session.post(url, params=params,
                                json={"condition": "AND", "filters": [config["filters"]]}, timeout=60)
        response.raise_for_status()
        page = response.json()
        if expected_total is None:
            expected_total = page["listLength"]
        elif page["listLength"] != expected_total:
            raise ValueError("Catalog record count changed during export; retry with a new snapshot")
        records.extend(page["data"])
        if len({record["id"] for record in records}) != len(records):
            raise ValueError("Catalog response contains duplicate program revisions")
        if len(records) == page["listLength"]:
            return records
        if not page["data"] or len(records) > page["listLength"]:
            raise ValueError("Catalog response is incomplete or changed during export")


def program_row(record, *, catalog_id, retrieved_at):
    custom = record.get("customFields", {})
    program_id = record["programGroupId"]
    return {
        "program_id": program_id,
        "revision_id": record["id"],
        "code": record.get("code", ""),
        "name": record.get("catalogDisplayName") or record.get("name", ""),
        "campus": record.get("campus", ""),
        "career": record.get("career", ""),
        "program_type": record.get("type", ""),
        "degree": record.get("degreeDesignation", ""),
        "effective_start_date": record.get("effectiveStartDate") or "",
        "effective_end_date": record.get("effectiveEndDate") or "",
        "degree_credits_min": custom.get("cdProgramCreditsDegreeMin", ""),
        "degree_credits_max": custom.get("cdProgramCreditsDegreeMax", ""),
        "program_credits_min": custom.get("cdProgramCreditsProgramMin", ""),
        "program_credits_max": custom.get("cdProgramCreditsProgramMax", ""),
        "college": record.get("college", ""),
        "description_json": json.dumps(record.get("description") or custom.get("cdProgramDescr", ""), ensure_ascii=True),
        "departments_json": json.dumps(record.get("departments"), ensure_ascii=True, sort_keys=True),
        "academic_metadata_json": json.dumps({
            key: value for key, value in custom.items()
            if not any(marker in key.lower() for marker in (
                "contact", "email", "phone", "address", "stakeholder", "budgetowner",
                "proposal", "programreview", "communicated", "assessment",
            ))
        }, ensure_ascii=True, sort_keys=True),
        "requirements_json": json.dumps(record.get("requisites"), ensure_ascii=True, sort_keys=True),
        "requirement_levels_json": json.dumps(record.get("requirementLevels"), ensure_ascii=True, sort_keys=True),
        "source_url": f"https://umtc.catalog.prod.coursedog.com/programs/{program_id}",
        "source_catalog_id": catalog_id,
        "retrieved_at_utc": retrieved_at,
    }


def write_snapshot(path, records, config, *, retrieved_at):
    if not records:
        raise ValueError("Cannot publish an empty program snapshot")
    rows = []
    for record in records:
        row = program_row(record, catalog_id=config["catalog_id"], retrieved_at=retrieved_at)
        row["source_window_start"] = config["effective_start"]
        row["source_window_end"] = config["effective_end"]
        content = {key: value for key, value in row.items() if key != "retrieved_at_utc"}
        row["academic_content_sha256"] = hashlib.sha256(
            json.dumps(content, sort_keys=True, ensure_ascii=True).encode("utf-8")
        ).hexdigest()
        rows.append(row)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    import requests

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New CSV path; existing snapshots are preserved")
    args = parser.parse_args(argv)
    with requests.Session() as session:
        session.headers.update({
            "x-requested-with": "catalog", "Origin": "https://umtc.catalog.prod.coursedog.com",
            "Referer": "https://umtc.catalog.prod.coursedog.com/",
        })
        page = session.get("https://umtc.catalog.prod.coursedog.com/programs", timeout=60)
        page.raise_for_status()
        config = discover_catalog(page.text)
        records = fetch_programs(session, config)
    retrieved_at = datetime.now(timezone.utc).isoformat()
    write_snapshot(args.output, records, config, retrieved_at=retrieved_at)
    print(f"Exported {len(records)} public Twin Cities program revisions to {args.output}")
    print(f"Catalog {config['catalog_id']}; source selection window {config['effective_start']} through {config['effective_end']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
