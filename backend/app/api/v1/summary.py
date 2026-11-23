from flask import Blueprint, g
from sqlalchemy import select

from app.core.auth import require_auth
from app.extensions import db
from app.models import Plan
from app.services.coursework import get_coursework
from app.services.programs import ProgramVersionUnavailable, ProgramVersionUnconfirmed, load_program
from app.services.summary import calculate_summary

summary_bp = Blueprint("summary", __name__, url_prefix="/api/v1")


def confirmed_program(user):
    """The user's program for their explicitly confirmed catalog term, never a candidate year."""
    term = db.session.scalar(select(Plan.catalog_term).where(Plan.user_id == user.id))
    try:
        return load_program(user.major or "", term)
    except (ProgramVersionUnavailable, ProgramVersionUnconfirmed):
        return None


@summary_bp.get("/summary")
@require_auth
def get_summary():
    return calculate_summary(get_coursework(g.user)["courses"], major=g.user.major or "", program=confirmed_program(g.user))
