"""Load a catalog export (the bundled SQLite file format) into the application database.

The source is opened read-only. The previous release is replaced in one transaction, so readers
see either the old catalog or the new one, never a mix.
"""
import csv
import json
import sqlite3
from datetime import date
from pathlib import Path

from sqlalchemy import delete, insert

from app.extensions import db
from app.models import CatalogCourse, CatalogPrerequisiteEdge, CatalogRelease

COURSE_COLUMNS = [column.name for column in CatalogCourse.__table__.columns if column.name not in {"release_id", "le_attributes"}]


def read_source(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"catalog export not found: {path}")
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only = ON")
        releases = [dict(row) for row in connection.execute("SELECT id, version, generated_at FROM catalog")]
        courses = [dict(row) for row in connection.execute(
            f"SELECT {', '.join(COURSE_COLUMNS)}, catalog_id AS release_id FROM courses")]
        edges = [dict(row) for row in connection.execute(
            "SELECT course_id, prerequisite_course_id FROM prerequisite_edges")]
    finally:
        connection.close()
    return releases, courses, edges


def _current(row, today):
    start, end = row["effective_start_date"].strip(), row["effective_end_date"].strip()
    return (not start or start <= today) and (not end or end >= today)


def _csv_course(row, identity, release_id):
    """Map a full-catalog CSV row. Prerequisites are kept as unverified text: shown and warned, never enforced."""
    code = " ".join(row["code"].split())
    subject, _, number = code.partition(" ")
    text = row["prerequisite_text"].strip()
    prerequisites = ({"status": "found", "requirements": {"type": "condition", "text": text},
                      "source_text": text, "needs_review": True}
                     if text else {"status": "none", "requirements": None, "source_text": None, "needs_review": False})
    course = dict.fromkeys(COURSE_COLUMNS, "-")
    course.update(
        id=identity, release_id=release_id, subject_code=subject, course_number=number, course_code=code,
        course_name=row["title"].strip(), campus="Twin Cities", description=(row.get("description") or "").strip(),
        minimum_credits=row["credits_min"] or "0", maximum_credits=row["credits_max"] or row["credits_min"] or "0",
        repeatable="Yes" if row["repeatable"].strip().lower() == "true" else "No",
        typically_offered=row["typically_offered"].strip() or "-",
        prerequisite_status="text_only" if text else "none", prerequisite_source_text=text or "-",
        prerequisite_json=json.dumps(prerequisites), prerequisite_unresolved_courses="[]",
        prerequisite_extraction_method="catalog_text", le_attributes=(row.get("le_attributes") or "").strip())
    return course


def _latest_csv_rows(path, today):
    latest = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            code = " ".join(row["code"].split())
            if not code or not _current(row, today):
                continue
            if code not in latest or row["effective_start_date"] >= latest[code]["effective_start_date"]:
                latest[code] = row
    return latest


def read_csv_source(path, *, release_id, first_id, skip_codes, today=None):
    """Current revisions only; for a code with several current revisions the latest start date wins."""
    latest = {code: row for code, row in _latest_csv_rows(path, today or date.today().isoformat()).items()
              if code not in skip_codes}
    return [_csv_course(row, first_id + index, release_id) for index, row in enumerate(sorted(latest.values(), key=lambda r: r["code"]))]


def import_catalog(path, *, extra_csv=None, today=None):
    """Reviewed SQLite rows win; ``extra_csv`` adds every other current course from the full catalog export."""
    releases, courses, edges = read_source(path)
    if not releases or not courses:
        raise ValueError("catalog export has no release or no courses")
    for course in courses:
        course.setdefault("le_attributes", "")
    if extra_csv:
        # Reviewed rows keep their prerequisites but take catalog-wide facts the SQLite export lacks.
        latest = _latest_csv_rows(extra_csv, today or date.today().isoformat())
        for course in courses:
            source = latest.get(course["course_code"])
            if source:
                course["le_attributes"] = (source.get("le_attributes") or "").strip()
                if (source.get("description") or "").strip() and course.get("description") in {None, "", "-"}:
                    course["description"] = source["description"].strip()
        courses = courses + read_csv_source(
            extra_csv, release_id=releases[0]["id"], first_id=max(course["id"] for course in courses) + 1,
            skip_codes={course["course_code"] for course in courses}, today=today)
    try:
        db.session.execute(delete(CatalogPrerequisiteEdge))
        db.session.execute(delete(CatalogCourse))
        db.session.execute(delete(CatalogRelease))
        db.session.execute(insert(CatalogRelease), releases)
        for start in range(0, len(courses), 2000):
            db.session.execute(insert(CatalogCourse), courses[start:start + 2000])
        if edges:
            db.session.execute(insert(CatalogPrerequisiteEdge), edges)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return {"releases": len(releases), "courses": len(courses), "edges": len(edges)}
