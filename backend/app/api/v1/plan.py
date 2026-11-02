"""GET /api/v1/plan — the signed-in user's plan built from their coursework."""

import sqlite3
from datetime import date

from flask import Blueprint, current_app, jsonify
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.auth import read_session
from app.api.v1.courses import open_catalog
from app.extensions import db
from app.models import CourseRecord
from app.services.plan import build_plan, read_catalog_info

plan_bp = Blueprint("plan", __name__, url_prefix="/api/v1")


def catalog_info(codes: list[str]) -> dict[str, dict]:
    # Catalog details are optional: if the catalog file is missing, the plan still loads.
    try:
        connection = open_catalog()
    except sqlite3.Error:
        current_app.logger.exception("Catalog unavailable; plan without catalog details")
        return {}
    try:
        return read_catalog_info(connection, codes)
    finally:
        connection.close()


@plan_bp.get("/plan")
def get_plan():
    user_session = read_session()
    if user_session is None:
        return jsonify({"error": "Not signed in"}), 401

    user = user_session.user
    try:
        records = db.session.scalars(
            select(CourseRecord).where(CourseRecord.user_id == user.id)
        ).all()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to load plan")
        return jsonify({"error": "Plan service unavailable"}), 503

    plan = build_plan(list(records), catalog_info, user.graduation_target, date.today())
    return jsonify(plan), 200
