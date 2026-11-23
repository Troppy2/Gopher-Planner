
import json

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from app.core.auth import read_session
from app.repositories import catalog

courses_bp = Blueprint("courses", __name__, url_prefix="/api/v1/courses")

TERMS = ("Fall", "Spring", "Summer")
COLUMNS = [column.name for column in catalog.CatalogCourse.__table__.columns]
AVAILABILITY_OPTIONS = ("Offered next term", "Not offered next term")


def require_auth():
    """Return the authenticated session, or a 401 response."""
    user_session = read_session()

    if user_session is None:
        return None, (jsonify({"error": "Not signed in"}), 401)

    return user_session, None


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


def serialize_course(course) -> dict:
    row = {column: getattr(course, column) for column in COLUMNS}
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
        "leAttributes": [part.strip() for part in (getattr(course, "le_attributes", "") or "").split(";") if part.strip()],
    }


@courses_bp.get("")
@courses_bp.get("/")
def get_courses():
    user_session, auth_error = require_auth()
    if auth_error is not None:
        return auth_error

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

    try:
        rows, total = catalog.search_courses(
            query=query, subject=subject, level=level, credits=credits, term=term,
            requirement=requirement, le=[value.strip() for value in request.args.getlist("le") if value.strip()], availability=availability, next_term=next_term,
            limit=limit, offset=offset)
        return jsonify({
            "courses": [serialize_course(row) for row in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        })
    except SQLAlchemyError:
        current_app.logger.exception("Catalog query failed")
        return jsonify({"error": "Could not load the course catalog"}), 500


@courses_bp.get("/<string:code>")
def get_course(code: str):
    user_session, auth_error = require_auth()
    if auth_error is not None:
        return auth_error

    try:
        row = catalog.get_course(code.strip().upper())
        if row is None:
            return jsonify({"error": "Course not found"}), 404
        course = serialize_course(row)
        course["resolvedPrerequisites"] = [
            {"code": item_code, "title": title}
            for item_code, title in catalog.resolved_prerequisites(row.id)
        ]
        return jsonify(course)
    except SQLAlchemyError:
        current_app.logger.exception("Course detail query failed")
        return jsonify({"error": "Could not load course details"}), 500
