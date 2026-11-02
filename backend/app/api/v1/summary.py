"""GET /api/v1/summary — dashboard numbers for the signed-in user."""

from flask import Blueprint, current_app, jsonify
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.auth import read_session
from app.extensions import db
from app.models import CourseRecord, TranscriptUpload
from app.services.summary import compute_summary

summary_bp = Blueprint("summary", __name__, url_prefix="/api/v1")


@summary_bp.get("/summary")
def get_summary():
    user_session = read_session()
    if user_session is None:
        return jsonify({"error": "Not signed in"}), 401

    user = user_session.user
    try:
        records = db.session.scalars(
            select(CourseRecord).where(CourseRecord.user_id == user.id)
        ).all()
        has_audit = db.session.scalar(
            select(TranscriptUpload.id).where(
                TranscriptUpload.user_id == user.id,
                TranscriptUpload.status == "parsed",
            ).limit(1)
        ) is not None
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to load summary")
        return jsonify({"error": "Summary service unavailable"}), 503

    return jsonify(compute_summary(list(records), user.major or "", has_audit)), 200
