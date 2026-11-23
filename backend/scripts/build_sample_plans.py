"""Build per-program sample plan files from the sample plan export.

Run from `backend`:

    uv run python scripts/build_sample_plans.py --sample-plans data/catalog-exports/sample-plans.<date>.csv

Writes `data/sample_plans/<program-id>.json` for every export page that matches a program file.
Integrated BS/MS plans are skipped; the first remaining plan on a page is used. Liberal education
slots keep their categories under the catalog's designation names.
"""
import argparse
import csv
import json
import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
CODE = re.compile(r"\b([A-Z]{2,6}) (\d{4}[A-Z]?)\b")
CATEGORIES = {
    "Arts/Humanities": (r"arts/humanities", r"\bAH\b"),
    "Biological Sciences": (r"biological sciences", r"\bBIOL?\b"),
    "Civic Life and Ethics": (r"civic life", r"\bCIV\b"),
    "Environment": (r"\benvironment\b", r"\bENV\b"),
    "Global Perspectives": (r"global perspectives", r"\bGP\b"),
    "Historical Perspectives": (r"historical perspectives", r"\b(?:HIS|HP)\b"),
    "Literature": (r"\bliterature\b", r"\b(?:LTR|LIT)\b"),
    "Mathematical Thinking": (r"mathematical thinking", r"\bMTH\b"),
    "Physical Sciences": (r"physical sciences", r"\bPHYS?\b"),
    "Race, Power, and Justice US": (r"race, power", r"\bRPJ\b"),
    "Social Sciences": (r"social sciences", r"\b(?:SOCS|SS)\b"),
    "Technology and Society": (r"technology and society", r"\bTS\b"),
}


def le_categories(title, le):
    found = []
    for name, (title_pattern, code_pattern) in CATEGORIES.items():
        if re.search(title_pattern, title or "", re.IGNORECASE) or re.search(code_pattern, (le or "").upper()):
            found.append(name)
    return sorted(found)


def _credits(text):
    match = re.search(r"\d+(?:\.\d+)?", text or "")
    return float(match.group()) if match else 3.0


def _item(row):
    kind, credits = row["kind"], _credits(row["credits"])
    if kind == "le":
        categories = le_categories(row["title"], row["le"])
        return {"kind": "le", "categories": categories, "credits": credits, "label": row["title"].strip(" (")} if categories else None
    if kind == "elective":
        return {"kind": "elective", "credits": credits}
    codes = [f"{subject} {number}" for subject, number in CODE.findall(f"{row['code']} {row['title']}")]
    if not codes:
        return None
    if kind == "choice" or len(codes) > 1:
        return {"kind": "choice", "codes": list(dict.fromkeys(codes)), "credits": credits, "preferred": row["preferred"] == "true"}
    return {"kind": "course", "codes": codes[:1], "credits": credits, "preferred": row["preferred"] == "true"}


def build_plan(rows, *, program_id):
    plans = [name for name in dict.fromkeys(row["plan"] for row in rows) if "integrated" not in name.lower()]
    if not plans:
        return None
    chosen = [row for row in rows if row["plan"] == plans[0]]
    terms = {}
    for row in chosen:
        item = _item(row)
        if item is not None:
            terms.setdefault((int(row["year"]), row["season"]), []).append(item)
    order = {"Fall": 0, "Spring": 1, "Summer": 2}
    return {
        "programId": program_id, "plan": plans[0].lstrip("+ ").strip(), "source": chosen[0]["url"],
        "retrieved": chosen[0]["retrieved_at_utc"][:10],
        "terms": [{"year": year, "season": season, "items": items}
                  for (year, season), items in sorted(terms.items(), key=lambda pair: (pair[0][0], order.get(pair[0][1], 3)))],
    }


def _norm(text):
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def match_program(slug, title, programs):
    """Program id whose id prefixes the page slug (or the reverse), else an exact name match."""
    by_id = sorted((pid for pid in programs if _norm(slug).startswith(_norm(pid)) or _norm(pid).startswith(_norm(slug))),
                   key=len, reverse=True)
    if len(by_id) == 1:
        return by_id[0]
    names = [pid for pid, name in programs.items() if _norm(name) == _norm(title)]
    return names[0] if len(names) == 1 else None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-plans", type=Path, required=True)
    parser.add_argument("--programs", type=Path, default=BACKEND / "data" / "programs")
    parser.add_argument("--output", type=Path, default=BACKEND / "data" / "sample_plans")
    args = parser.parse_args(argv)
    programs = {}
    for file in args.programs.glob("*.json"):
        program = json.loads(file.read_text(encoding="utf-8"))
        programs[program["id"]] = program["name"]
    pages = {}
    with args.sample_plans.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            pages.setdefault(row["url"], []).append(row)
    args.output.mkdir(parents=True, exist_ok=True)
    written, unmatched = 0, []
    for url, rows in sorted(pages.items()):
        program_id = match_program(url.rsplit("/", 1)[-1], rows[0]["program_title"], programs)
        plan = build_plan(rows, program_id=program_id) if program_id else None
        if plan is None:
            unmatched.append(url.rsplit("/", 1)[-1])
            continue
        (args.output / f"{program_id}.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        written += 1
    print(f"Wrote {written} sample plans; unmatched pages: {', '.join(unmatched) or 'none'}")


if __name__ == "__main__":
    main()
