from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import User
from app.api.v1.auth import check_request_origin, read_session
from app.models.user import User
from app.models.summary import Summary

profile_bp = Blueprint("profile", __name__, url_prefix="/api/v1")


def serialize_profile(user: User, summary: Summary | None = None) -> dict:
    if summary is None:
        summary = getattr(user, "summary", None)

def serialize_profile(user: User, summary: Summary | None = None) -> dict:
    if summary is None:
        summary = getattr(user, "summary", None)

    return {
        "name": user.name or "",
        "major": user.major or "",
        "standing": user.standing or "",
        "careerGoals": user.career_goals or "",
        "creditLoad": user.credit_load,
        "graduationTarget": user.graduation_target or "",
        "onboarded": user.onboarded,
        "credits": summary.credits if summary else 0,
        "gpa": summary.gpa if summary and summary.gpa else 0.0,
        "classTaken": summary.class_taken if summary else "",
        "classCurrent": summary.class_current if summary else "",
        "classPlanned": summary.class_planned if summary else "",
        "program": summary.program if summary else "",
        "credits": summary.credits if summary else 0,
        "gpa": summary.gpa if summary and summary.gpa else 0.0,
        "classTaken": summary.class_taken if summary else "",
        "classCurrent": summary.class_current if summary else "",
        "classPlanned": summary.class_planned if summary else "",
        "program": summary.program if summary else "",
    }


PROFILE_FIELDS = {
    "name": "name",
    "major": "major",
    "standing": "standing",
    "careerGoals": "career_goals",
    "creditLoad": "credit_load",
    "graduationTarget": "graduation_target",
    "onboarded": "onboarded",
    "credits": "summary.credits",
    "gpa": "summary.gpa",
    "classTaken": "summary.class_taken",
    "program": "summary.program",
    "credits": "summary.credits",
    "gpa": "summary.gpa",
    "classTaken": "summary.class_taken",
    "program": "summary.program",
}


def validate_profile_field(field: str, value: object) -> str | None:
    if field in {
        "name", "major", "standing", "careerGoals", "graduationTarget"
    }:
        if not isinstance(value, str):
            return f"{field} must be a string"

        max_lengths = {
            "name": 255,
            "major": 255,
            "standing": 50,
            "careerGoals": 10000,
            "graduationTarget": 50,
        }

        if len(value) > max_lengths[field]:
            return f"{field} must be at most {max_lengths[field]} characters"

    elif field == "creditLoad":
        if isinstance(value, bool) or not isinstance(value, int):
            return "creditLoad must be an integer"

        if not 1 <= value <= 30:
            return "creditLoad must be between 1 and 30"

    elif field == "onboarded":
        if not isinstance(value, bool):
            return "onboarded must be a boolean"

    return None


@profile_bp.get("/profile")
def get_profile():
    try:
        user_session = read_session()

        if user_session is None:
            return jsonify({"error": "Not signed in"}), 401

        return jsonify(serialize_profile(user_session.user)), 200

    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to load user profile")
        return jsonify({"error": "Profile service unavailable"}), 503


@profile_bp.put("/profile")
def update_profile():
    origin_error = check_request_origin()
    if origin_error is not None:
        return origin_error

    try:
        user_session = read_session()

        if user_session is None:
            return jsonify({"error": "Not signed in"}), 401

        body = request.get_json(silent=True)

        if not isinstance(body, dict):
            return jsonify({"error": "Expected a JSON body"}), 400

        unknown_fields = set(body) - set(PROFILE_FIELDS)

        if unknown_fields:
            return jsonify({
                "error": "Unknown profile fields",
                "fields": sorted(unknown_fields),
            }), 400

        user = user_session.user

        for field, value in body.items():
            error = validate_profile_field(field, value)
            if error:
                return jsonify({"error": error}), 400

        for field, value in body.items():
            setattr(user, PROFILE_FIELDS[field], value)

        db.session.commit()

        return jsonify(serialize_profile(user)), 200

    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to update user profile")
        return jsonify({"error": "Profile service unavailable"}), 503