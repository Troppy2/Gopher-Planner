from flask import Blueprint

from app.core.auth import require_auth
from app.services.options import get_options

options_bp = Blueprint("options", __name__, url_prefix="/api/v1")


@options_bp.get("/options")
@require_auth
def read_options():
    return get_options()
