"""Export public UMN Twin Cities course versions so program course IDs resolve to official facts."""
import argparse
import csv
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    from scripts.export_programs import discover_catalog
except ImportError:  # executed as a script from backend/
    from export_programs import discover_catalog

FIELDS = ["course_group_id", "revision_id", "code", "title", "credits_min", "credits_max", "typically_offered",
          "prerequisite_text", "repeatable", "effective_start_date", "effective_end_date", "source_url", "retrieved_at_utc",
          "le_attributes", "description"]
PREREQUISITE = re.compile(r"(?:^|\n)\s*prereq:\s*(.+)", re.IGNORECASE)


def _number(value):
    return "" if value is None else f"{value:g}" if isinstance(value, (int, float)) else str(value)


def course_row(record, *, retrieved_at):
    """Keep only academic identity and scheduling facts. Contact and proposal fields are omitted."""
    hours = (record.get("credits") or {}).get("creditHours") or {}
    match = PREREQUISITE.search(record.get("description") or "")
    return {
        "course_group_id": record["courseGroupId"], "revision_id": record["id"],
        "code": f"{record['subjectCode']} {record['courseNumber']}",
        "title": record.get("longName") or record.get("name") or "",
        "credits_min": _number(hours.get("min")), "credits_max": _number(hours.get("max")),
        "typically_offered": record.get("courseTypicallyOffered") or "",
        "prerequisite_text": match.group(1).strip() if match else "",
        "repeatable": "true" if (record.get("credits") or {}).get("repeatable") else "false",
        "effective_start_date": record.get("effectiveStartDate") or "", "effective_end_date": record.get("effectiveEndDate") or "",
        "source_url": f"https://umtc.catalog.prod.coursedog.com/courses/{record['courseGroupId']}",
        "retrieved_at_utc": retrieved_at,
        "le_attributes": "; ".join(sorted((record.get("customFields") or {}).get("catalogAttributes") or [])),
        "description": PREREQUISITE.sub("", record.get("description") or "").strip(),
    }


def fetch_courses(session, config):
    url = f"https://app.coursedog.com/api/v1/cm/{config['school']}/courses/search/%24filters"
    records, expected = [], None
    while True:
        params = {"catalogId": config["catalog_id"], "skip": len(records), "limit": 500, "sortBy": "id",
                  "effectiveDatesRange": f"{config['effective_start']},{config['effective_end']}"}
        response = session.post(url, params=params, json={"condition": "AND", "filters": []}, timeout=120)
        response.raise_for_status()
        page = response.json()
        if expected is None:
            expected = page["listLength"]
        elif page["listLength"] != expected:
            raise ValueError("Course count changed during export; retry with a new snapshot")
        records.extend(page["data"])
        if len({item["id"] for item in records}) != len(records):
            raise ValueError("Course response contains duplicate versions")
        if len(records) == expected:
            return records
        if not page["data"] or len(records) > expected:
            raise ValueError("Course response is incomplete or changed during export")


def write_courses(path, records, *, retrieved_at):
    if not records:
        raise ValueError("Cannot publish an empty course snapshot")
    rows = [course_row(item, retrieved_at=retrieved_at) for item in records]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    import requests

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New CSV path; existing snapshots are preserved")
    parser.add_argument("--from-date", required=True, help="Earliest effective date to include, YYYY-MM-DD")
    parser.add_argument("--to-date", required=True, help="Latest effective date to include, YYYY-MM-DD")
    args = parser.parse_args(argv)
    with requests.Session() as session:
        session.headers.update({"x-requested-with": "catalog", "Origin": "https://umtc.catalog.prod.coursedog.com",
                                "Referer": "https://umtc.catalog.prod.coursedog.com/"})
        page = session.get("https://umtc.catalog.prod.coursedog.com/courses", timeout=60)
        page.raise_for_status()
        config = {**discover_catalog(page.text), "effective_start": args.from_date, "effective_end": args.to_date}
        records = fetch_courses(session, config)
    write_courses(args.output, records, retrieved_at=datetime.now(timezone.utc).isoformat())
    print(f"Exported {len(records)} public Twin Cities course versions effective {args.from_date} through {args.to_date}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
