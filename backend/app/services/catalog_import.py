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
from app.services.requisites import has_condition, load_enforced, load_reviewed, resolve_prerequisites

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


def _prerequisite_record(expression, origin, text):
    if origin == "none":
        return {"status": "none", "requirements": None, "source_text": text or None, "needs_review": False}
    return {"status": "found", "requirements": expression, "source_text": text, "needs_review": has_condition(expression)}


def _csv_course(row, identity, release_id, *, enforced=None, reviewed=None, subjects=frozenset(), known=None):
    """Map a full-catalog CSV row. Prerequisites come from ``resolve_prerequisites``: a reviewed or fully
    parsed tree is enforced; anything else stays text that is shown and warned, never enforced."""
    code = " ".join(row["code"].split())
    subject, _, number = code.partition(" ")
    expression, origin, text = resolve_prerequisites(code, row["prerequisite_text"], enforced=enforced, reviewed=reviewed,
                                                     subject=subject, subjects=subjects, known=known)
    prerequisites = _prerequisite_record(expression, origin, text)
    course = dict.fromkeys(COURSE_COLUMNS, "-")
    course.update(
        id=identity, release_id=release_id, subject_code=subject, course_number=number, course_code=code,
        course_name=row["title"].strip(), campus="Twin Cities", description=(row.get("description") or "").strip(),
        minimum_credits=row["credits_min"] or "0", maximum_credits=row["credits_max"] or row["credits_min"] or "0",
        repeatable="Yes" if row["repeatable"].strip().lower() == "true" else "No",
        typically_offered=row["typically_offered"].strip() or "-",
        prerequisite_status="none" if origin == "none" else "text_only" if expression.get("type") == "condition" else "found",
        prerequisite_source_text=text or "-",
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


def read_csv_source(path, *, release_id, first_id, skip_codes, today=None, enforced=None, reviewed=None):
    """Current revisions only; for a code with several current revisions the latest start date wins."""
    rows = _latest_csv_rows(path, today or date.today().isoformat())
    subjects = {code.split(" ")[0] for code in rows}
    known = set(rows) | set(skip_codes)
    latest = {code: row for code, row in rows.items() if code not in skip_codes}
    return [_csv_course(row, first_id + index, release_id, enforced=enforced, reviewed=reviewed, subjects=subjects,
                        known=known)
            for index, row in enumerate(sorted(latest.values(), key=lambda r: r["code"]))]


def import_catalog(path, *, extra_csv=None, today=None, requisites=None, reviewed=None):
    """SQLite rows win over the CSV; ``extra_csv`` adds every other current course from the full catalog export.

    ``requisites`` (enforced enrollment requirements) improves CSV rows' prerequisites. ``reviewed``
    hand-checked trees replace the prerequisites of any course they list, SQLite rows included."""
    releases, courses, edges = read_source(path)
    if not releases or not courses:
        raise ValueError("catalog export has no release or no courses")
    enforced = load_enforced(requisites)
    reviewed_trees, _ = load_reviewed(reviewed)
    for course in courses:
        course.setdefault("le_attributes", "")
        if course["course_code"] in reviewed_trees:
            expression, origin, text = resolve_prerequisites(course["course_code"], "", reviewed=reviewed_trees)
            course["prerequisite_json"] = json.dumps(_prerequisite_record(expression, origin, text))
            course["prerequisite_status"] = "none" if expression is None else "found"
            course["prerequisite_unresolved_courses"] = "[]"
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
            skip_codes={course["course_code"] for course in courses}, today=today, enforced=enforced,
            reviewed=reviewed_trees)
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
