"""Liberal education helpers beyond the tracker that ships inside GET /plan."""
from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.courses import serialize_course
from app.core.auth import require_auth
from app.extensions import db
from app.repositories import catalog
from app.repositories.plans import planned_courses
from app.services.liberal_ed import load_rules
from app.services.metadata import referenced_codes
from app.services.plan import coursework_attempts, earned, liberal_ed_status, resolve_context

liberal_ed_bp = Blueprint("liberal_ed", __name__, url_prefix="/api/v1/liberal-ed")


def needs_by_name(remaining):
    """Map each remaining need to every designation that satisfies it, including former names."""
    rules = load_rules()
    groups = {entry["designations"][0]: entry["designations"]
              for section in ("core", "themes") for entry in rules[section]["items"]}
    groups.update({name: [name] for name in rules["writing"]["intensive"]["designations"]})
    return {name: groups.get(name, [name]) for name in remaining}


@liberal_ed_bp.get("/double-dippers")
@require_auth
def double_dippers():
    try:
        limit = int(request.args.get("limit", "10"))
        offset = int(request.args.get("offset", "0"))
    except ValueError:
        return jsonify({"error": "limit and offset must be integers", "code": "invalid_request"}), 400
    if not 1 <= limit <= 50 or offset < 0:
        return jsonify({"error": "limit must be 1 to 50 and offset nonnegative", "code": "invalid_request"}), 400
    try:
        user = g.user
        context = resolve_context(user)
        program = context.program
        attempts = coursework_attempts(user)
        planned = planned_courses(user.id)
        status = liberal_ed_status(user.id, attempts, planned, program, referenced_codes(program) if program else set())
        taken = {row["code"] for row in attempts if earned(row) or row["status"] == "prog"} | set(planned)
        page, total = catalog.double_dippers(needs_by_name(status["remaining"]), exclude=taken, limit=limit, offset=offset)
        return jsonify({
            "remaining": status["remaining"],
            "courses": [{**serialize_course(course), "covers": covered} for course, covered in page],
            "total": total, "limit": limit, "offset": offset,
        })
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Double dipper lookup failed")
        return jsonify({"error": "Could not load course suggestions", "code": "unavailable"}), 503
