"""Review collected reports without changing academic data."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.extensions import db
from app.models import DataReport


def summarize(include_notes=False):
    groups = {}
    for row in db.session.scalars(db.select(DataReport).where(DataReport.status == "open").order_by(DataReport.created_at.desc(), DataReport.id.desc())):
        key = (row.target_type, row.course_code, row.program_id, row.catalog_term, row.requirement_id)
        group = groups.setdefault(key, {
            "target": row.course_code if row.target_type == "course" else f"{row.program_id} / {row.catalog_term} / {row.requirement_id}",
            "students": set(), "reasons": Counter(), "newest": row.created_at.isoformat(),
            **({"notes": []} if include_notes else {}),
        })
        group["students"].add(row.user_id)
        group["reasons"][row.reason] += 1
        if include_notes and row.note:
            group["notes"].append(row.note.strip()[:200])
    result = [{**g, "students": len(g["students"]), "reasons": dict(g["reasons"])} for g in groups.values()]
    return sorted(result, key=lambda g: (g["students"], g["newest"], g["target"]), reverse=True)


def main(argv=None, *, application=None):
    parser = argparse.ArgumentParser(description="Review reports in DATABASE_URL. Does not change catalog or program data.")
    parser.add_argument("--notes", action="store_true", help="Include student-written notes, limited to 200 characters.")
    parser.add_argument("--json", type=Path, metavar="PATH")
    parser.add_argument("--set-status", nargs=2, metavar=("ID", "STATUS"))
    args = parser.parse_args(argv)
    if args.set_status:
        report_id, status = args.set_status
        if not report_id.isdigit() or status not in {"open", "resolved", "dismissed"}:
            parser.error("--set-status requires an integer ID and open, resolved, or dismissed")
    with (application or create_app()).app_context():
        if args.set_status:
            row = db.session.get(DataReport, int(report_id))
            if row is None:
                print("Report not found")
                return 1
            row.status = status
            db.session.commit()
            print(f"Report {row.id}: {row.status}")
            return 0
        groups = summarize(args.notes)
        print("Target | Students | Reason counts | Newest report")
        for group in groups:
            reasons = ", ".join(f"{k}: {v}" for k, v in sorted(group["reasons"].items()))
            print(f"{group['target']} | {group['students']} | {reasons} | {group['newest']}")
            for note in group.get("notes", []):
                # Escape controls so student text cannot manipulate the maintainer terminal.
                print("  Note: " + json.dumps(note, ensure_ascii=True))
        if args.json:
            args.json.write_text(json.dumps(groups, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
