"""Shared opaque-cookie authentication and origin protection."""
import hashlib
from datetime import datetime, timezone
from functools import wraps

from flask import current_app, g, jsonify, request
from sqlalchemy import select

from app.core.config import Settings
from app.extensions import db
from app.models import UserSession

COOKIE_NAME = "gp_session"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_session_token(token: str) -> str:
    """Hash the opaque session token before storing or querying it."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def check_request_origin():
    """Reject state-changing browser requests from untrusted origins."""
    settings: Settings = current_app.config["SETTINGS"]
    origin = request.headers.get("Origin")

    if origin != settings.frontend_origin:
        return jsonify({"error": "Untrusted request origin"}), 403

    return None


def read_session() -> UserSession | None:
    """Return an active database session, or None if invalid."""
    token = request.cookies.get(COOKIE_NAME)

    if not token:
        return None

    token_hash = hash_session_token(token)

    user_session = db.session.scalar(
        select(UserSession).where(
            UserSession.token_hash == token_hash,
        )
    )

    if user_session is None or not user_session.is_active:
        return None

    return user_session


def require_auth(handler):
    @wraps(handler)
    def authenticated(*args, **kwargs):
        session = read_session()
        if session is None:
            return jsonify({"error": "Not signed in"}), 401
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            error = check_request_origin()
            if error is not None:
                return error
        g.user = session.user
        return handler(*args, **kwargs)
    return authenticated
