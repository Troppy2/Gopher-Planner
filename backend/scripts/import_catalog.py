"""Import a catalog export into the database named by DATABASE_URL.

Run from `backend` after `uv run flask db upgrade`:

    uv run python scripts/import_catalog.py --source data/courses.db
    uv run python scripts/import_catalog.py --csv data/catalog-exports/courses.2026-11-23.csv         --requisites data/catalog-exports/requisites.2026-11-25.csv

`--source` rows win; `--csv` adds every other current course. A CSV course's prerequisites come from
`data/prerequisites/reviewed.json` when listed there, otherwise the enforced registration requirement in
`--requisites` when it parses completely, otherwise the catalog text (a parsed tree, or unverified text
that warns and never blocks). Reviewed trees also replace `--source` rows' prerequisites.

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
    parser.add_argument("--requisites", help="Enforced enrollment requirements from export_requisites.py.")
    parser.add_argument("--reviewed", default=str(BACKEND / "data" / "prerequisites" / "reviewed.json"),
                        help="Hand-reviewed prerequisite trees.")
    args = parser.parse_args(argv)
    reviewed = args.reviewed if Path(args.reviewed).is_file() else None
    with create_app().app_context():
        result = import_catalog(args.source, extra_csv=args.csv, requisites=args.requisites, reviewed=reviewed)
    print(f"Imported {result['releases']} release(s), {result['courses']} courses, "
          f"{result['edges']} prerequisite edges")


if __name__ == "__main__":
    main()
