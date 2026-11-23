"""Report, per major, requirement courses that are missing from the full catalog export.

Read-only: it changes no program file and no database. Run from `backend`:

    uv run python scripts/validate_programs.py
    uv run python scripts/validate_programs.py --json report.json

A missing code usually means a retired course, a typo in the machine mapping, or a course the export
did not include. Check each against APAS or the catalog before editing a program file.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.metadata import normalize_code, referenced_codes  # noqa: E402

DEFAULT_CSV = BACKEND / "data" / "catalog-exports" / "courses.2026-11-22.csv"
DEFAULT_PROGRAMS = BACKEND / "data" / "programs"


def catalog_codes(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        return {normalize_code(row["code"]) for row in csv.DictReader(handle) if not row["effective_end_date"].strip()}


def validate(programs_dir, codes):
    report = []
    for file in sorted(Path(programs_dir).glob("*.json")):
        program = json.loads(file.read_text(encoding="utf-8"))
        referenced = {normalize_code(code) for code in referenced_codes(program)}
        missing = sorted(referenced - codes)
        report.append({"file": file.name, "program": program.get("name", file.stem),
                       "referenced": len(referenced), "missing": missing})
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check program requirement courses against the catalog export.")
    parser.add_argument("--catalog", default=str(DEFAULT_CSV))
    parser.add_argument("--programs", default=str(DEFAULT_PROGRAMS))
    parser.add_argument("--json", help="Also write the full report to this file.")
    args = parser.parse_args(argv)
    report = validate(args.programs, catalog_codes(args.catalog))
    flagged = [entry for entry in report if entry["missing"]]
    for entry in flagged:
        print(f"{entry['program']}: {len(entry['missing'])}/{entry['referenced']} missing: {', '.join(entry['missing'])}")
    print(f"\n{len(report)} programs checked, {len(flagged)} with missing courses, "
          f"{sum(len(e['missing']) for e in flagged)} missing references.")
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 1 if flagged else 0


if __name__ == "__main__":
    sys.exit(main())
