
import json
import sqlite3
from pathlib import Path
from urllib.parse import quote

from flask import Blueprint, current_app, jsonify, request

courses_bp = Blueprint("courses", __name__, url_prefix="/api/v1/courses")

# backend/app/api/v1/courses.py -> backend/data/courses.db
CATALOG_DB = Path(__file__).resolve().parents[3] / "data" / "courses.db"

TERMS = ("Fall", "Spring", "Summer")
AVAILABILITY_OPTIONS = ("Offered next term", "Not offered next term")


def open_catalog() -> sqlite3.Connection:
    """Open the catalog read-only; never modify it through the API."""
    db_uri = f"file:{quote(str(CATALOG_DB.resolve()), safe='/')}?mode=ro"
    connection = sqlite3.connect(db_uri, uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


def parse_json(value: str | None):
    if not value:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


def parse_offered(value: str) -> list[str]:
    """Extract the terms mentioned in typically_offered."""
    return [term for term in TERMS if term in value]


def serialize_course(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "code": row["course_code"],
        "subject": row["subject_code"],
        "number": row["course_number"],
        "title": row["course_name"],
        "campus": row["campus"],
        "description": row["description"],
        "minimumCredits": float(row["minimum_credits"]),
        "maximumCredits": float(row["maximum_credits"]),
        "repeatable": row["repeatable"],
        "maximumCompletions": row["maximum_completions"],
        "maximumCreditsEarned": row["maximum_credits_earned"],
        "gradingBasis": row["grading_basis"],
        "requirements": (
            None if row["requirements"] == "-" else row["requirements"]
        ),
        "typicallyOffered": row["typically_offered"],
        "offered": parse_offered(row["typically_offered"]),
        "prerequisiteStatus": row["prerequisite_status"],
        "prerequisiteSourceText": row["prerequisite_source_text"],
        "prerequisites": parse_json(row["prerequisite_json"]),
        "unresolvedPrerequisiteCourses": parse_json(
            row["prerequisite_unresolved_courses"]
        ) or [],
    }


@courses_bp.get("")
@courses_bp.get("/")
def get_courses():
    query = request.args.get("q", "").strip()
    subject = request.args.get("subject", "").strip().upper()
    level = request.args.get("level", "").strip()
    credits = request.args.get("credits", "").strip()
    term = request.args.get("term", "").strip().title()
    requirement = request.args.get("requirement", "").strip()
    availability = request.args.get("availability", "").strip()
    next_term = request.args.get("nextTerm", "Spring").strip().title()

    if term and term not in TERMS:
        return jsonify({"error": "term must be Fall, Spring, or Summer"}), 400

    if level and level not in {"1", "2", "3", "4", "5", "6", "7", "8", "9"}:
        return jsonify({"error": "level must be a digit from 1 to 9"}), 400

    if credits and credits not in {"1 to 2", "3", "4 or more"}:
        return jsonify({
            "error": "credits must be '1 to 2', '3', or '4 or more'"
        }), 400

    if availability and availability not in AVAILABILITY_OPTIONS:
        return jsonify({
            "error": "Invalid availability filter"
        }), 400

    if next_term not in TERMS:
        return jsonify({
            "error": "nextTerm must be Fall, Spring, or Summer"
        }), 400

    try:
        limit = int(request.args.get("limit", "50"))
        offset = int(request.args.get("offset", "0"))
    except ValueError:
        return jsonify({"error": "limit and offset must be integers"}), 400

    if not 1 <= limit <= 100 or offset < 0:
        return jsonify({
            "error": "limit must be 1–100 and offset must be nonnegative"
        }), 400

    where = []
    params: list[object] = []

    if query:
        pattern = f"%{query}%"
        where.append(
            "(course_code LIKE ? OR course_name LIKE ? "
            "OR description LIKE ?)"
        )
        params.extend([pattern, pattern, pattern])

    if subject:
        where.append("subject_code = ?")
        params.append(subject)

    if level:
        where.append("substr(course_number, 1, 1) = ?")
        params.append(level)

    if credits == "1 to 2":
        where.append(
            "CAST(maximum_credits AS REAL) <= 2"
        )
    elif credits == "3":
        where.append(
            "CAST(minimum_credits AS REAL) = 3 "
            "AND CAST(maximum_credits AS REAL) = 3"
        )
    elif credits == "4 or more":
        where.append("CAST(minimum_credits AS REAL) >= 4")

    if term:
        # Includes both regular and periodic offerings for that term.
        where.append("typically_offered LIKE ?")
        params.append(f"%{term}%")

    if requirement:
        if requirement.lower() in {"none", "-"}:
            where.append("requirements = '-'")
        else:
            where.append("requirements = ?")
            params.append(requirement)

    if availability:
        # Initial behavior matches the frontend's Spring default.
        # Alternating-year offerings need year-aware logic to be exact.
        where.append("typically_offered LIKE ?")
        params.append(f"%{next_term}%")

        if availability == "Not offered next term":
            where[-1] = "typically_offered NOT LIKE ?"

        where.append("typically_offered != '-'")

    clause = f"WHERE {' AND '.join(where)}" if where else ""

    try:
        with open_catalog() as connection:
            total = connection.execute(
                f"SELECT COUNT(*) FROM courses {clause}",
                params,
            ).fetchone()[0]

            rows = connection.execute(
                f"""
                SELECT *
                FROM courses
                {clause}
                ORDER BY subject_code, course_number, course_code
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()

        return jsonify({
            "courses": [serialize_course(row) for row in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        })
    except sqlite3.Error:
        current_app.logger.exception("Catalog query failed")
        return jsonify({"error": "Could not load the course catalog"}), 500


@courses_bp.get("/<string:code>")
def get_course(code: str):
    try:
        with open_catalog() as connection:
            row = connection.execute(
                "SELECT * FROM courses WHERE course_code = ? LIMIT 1",
                (code.strip().upper(),),
            ).fetchone()

            if row is None:
                return jsonify({"error": "Course not found"}), 404

            course = serialize_course(row)

            prerequisite_rows = connection.execute(
                """
                SELECT prerequisite.course_code, prerequisite.course_name
                FROM prerequisite_edges AS edge
                JOIN courses AS prerequisite
                  ON prerequisite.id = edge.prerequisite_course_id
                WHERE edge.course_id = ?
                ORDER BY prerequisite.course_code
                """,
                (row["id"],),
            ).fetchall()

            course["resolvedPrerequisites"] = [
                {"code": item["course_code"], "title": item["course_name"]}
                for item in prerequisite_rows
            ]

        return jsonify(course)
    except sqlite3.Error:
        current_app.logger.exception("Course detail query failed")
        return jsonify({"error": "Could not load course details"}), 500
