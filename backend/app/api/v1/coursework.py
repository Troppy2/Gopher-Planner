from flask import Blueprint, g, request

from app.core.auth import require_auth
from app.services.coursework import get_coursework, save_coursework
from app.schemas.coursework import CourseworkValidationError

coursework_bp = Blueprint("coursework", __name__, url_prefix="/api/v1")


@coursework_bp.get("/coursework")
@require_auth
def read_coursework():
    return get_coursework(g.user)


@coursework_bp.put("/coursework")
@require_auth
def replace_coursework():
    try:
        return save_coursework(g.user, request.get_json(silent=True))
    except CourseworkValidationError as error:
        return {"error": str(error), "code": "invalid_coursework"}, 400
