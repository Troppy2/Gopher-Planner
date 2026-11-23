"""Import a catalog export into the database named by DATABASE_URL.

Run from `backend` after `uv run flask db upgrade`:

    uv run python scripts/import_catalog.py --source data/courses.db
    uv run python scripts/import_catalog.py --csv data/catalog-exports/courses.2026-11-22.csv

`--source` rows (hand-checked prerequisites) win; `--csv` adds every other current course with
prerequisites kept as unverified text.

The source file is opened read-only and never modified. Rerunning replaces the catalog.
"""
import argparse
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app import create_app  # noqa: E402
from app.services.catalog_import import import_catalog  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description="Import a catalog export into DATABASE_URL.")
    parser.add_argument("--source", default=str(BACKEND / "data" / "courses.db"))
    parser.add_argument("--csv", help="Full catalog CSV export to merge in (current revisions only).")
    args = parser.parse_args(argv)
    with create_app().app_context():
        result = import_catalog(args.source, extra_csv=args.csv)
    print(f"Imported {result['releases']} release(s), {result['courses']} courses, "
          f"{result['edges']} prerequisite edges")


if __name__ == "__main__":
    main()
