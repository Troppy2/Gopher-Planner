from flask import Blueprint, g, request

from app.core.auth import require_auth
from app.extensions import db
from app.services.plan import PlanError, generate, get_plan, save_changes
from app.services.programs import list_programs

plan_bp = Blueprint("plan", __name__, url_prefix="/api/v1")


def error_response(error):
    db.session.rollback()
    body = {"error": error.message, "code": error.code}
    if error.violations is not None:
        body["violations"] = error.violations
    return body, error.status


@plan_bp.get("/plan")
@require_auth
def read_plan():
    return get_plan(g.user)


@plan_bp.put("/plan")
@require_auth
def update_plan():
    try:
        return save_changes(g.user, request.get_json(silent=True))
    except PlanError as error:
        return error_response(error)


@plan_bp.post("/plans/generate")
@require_auth
def generate_plan_route():
    body = request.get_json(silent=True) if request.data else {}
    try:
        return generate(g.user, body)
    except PlanError as error:
        return error_response(error)
    except Exception:
        db.session.rollback()
        # The stack trace is logged without request bodies or student data.
        import logging
        logging.getLogger(__name__).exception("Plan generation failed")
        return {"error": "Plan generation failed", "code": "generation_failed"}, 500


@plan_bp.get("/programs")
@require_auth
def read_programs():
    return {"programs": list_programs()}
