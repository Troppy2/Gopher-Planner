
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request
from google.auth.exceptions import GoogleAuthError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.config import Settings
from app.core.google_auth import verify_google_credential
from app.extensions import db
from app.models import User, UserSession

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

COOKIE_NAME = "gp_session"
SESSION_LIFETIME = timedelta(days=7)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_session_token(token: str) -> str:
    """Hash the opaque session token before storing or querying it."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def set_session_cookie(response, token: str, settings: Settings):
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=int(SESSION_LIFETIME.total_seconds()),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="Lax",
        path="/",
    )
    return response


def clear_session_cookie(response):
    settings: Settings = current_app.config["SETTINGS"]
    response.delete_cookie(
        COOKIE_NAME,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="Lax",
    )
    return response


def check_request_origin():
    """Reject state-changing browser requests from untrusted origins."""
    settings: Settings = current_app.config["SETTINGS"]
    origin = request.headers.get("Origin")

    if origin != settings.frontend_origin:
        return jsonify({"error": "Untrusted request origin"}), 403

    return None


def serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name or "",
        "picture": user.picture_url or "",
        "major": user.major or "",
        "standing": user.standing or "",
        "careerGoals": user.career_goals or "",
        "creditLoad": user.credit_load,
        "graduationTarget": user.graduation_target or "",
        "onboarded": user.onboarded,
    }


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


@auth_bp.post("/google")
def google_login():
    origin_error = check_request_origin()
    if origin_error is not None:
        return origin_error

    body = request.get_json(silent=True)

    if not isinstance(body, dict):
        return jsonify({"error": "Expected a JSON body"}), 400

    credential = body.get("credential")
    if not isinstance(credential, str) or not credential:
        return jsonify({"error": "Missing Google credential"}), 400

    settings: Settings = current_app.config["SETTINGS"]

    try:
        google_user = verify_google_credential(
            credential,
            settings.google_client_id,
        )
    except PermissionError:
        return jsonify(
            {"error": "Only verified @umn.edu accounts can sign in"}
        ), 403
    except (ValueError, GoogleAuthError):
        return jsonify({"error": "Invalid Google credential"}), 401

    now = utc_now()
    token = secrets.token_urlsafe(32)

    try:
        # Use Google's stable subject ID to identify the account.
        user = db.session.scalar(
            select(User).where(User.google_sub == google_user["id"])
        )

        if user is None:
            # Do not silently link an unrelated Google identity to an
            # existing account merely because the email matches.
            existing_email = db.session.scalar(
                select(User.id).where(
                    User.email == google_user["email"]
                )
            )

            if existing_email is not None:
                db.session.rollback()
                return jsonify({
                    "error": (
                        "This email is already associated with another "
                        "account identity. Please contact support."
                    )
                }), 409

            user = User(
                google_sub=google_user["id"],
                email=google_user["email"],
                name=google_user["name"],
                picture_url=google_user["picture"],
            )
            db.session.add(user)
        else:
            # Refresh profile details from the newly verified Google token.
            user.email = google_user["email"]
            user.name = google_user["name"]
            user.picture_url = google_user["picture"]

        db.session.flush()

        user_session = UserSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            created_at=now,
            expires_at=now + SESSION_LIFETIME,
        )
        db.session.add(user_session)
        db.session.commit()

        # Serialize after commit so the response uses persisted user data.
        response_user = serialize_user(user)

    except IntegrityError:
        db.session.rollback()
        current_app.logger.warning(
            "Login failed because a user or session uniqueness constraint "
            "was violated."
        )
        return jsonify({
            "error": "Could not create account. Please try signing in again."
        }), 409

    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception(
            "Database error while creating a login session"
        )
        return jsonify({"error": "Authentication service unavailable"}), 503

    response = jsonify({
        "user": response_user,
        "expires_in": int(SESSION_LIFETIME.total_seconds()),
    })
    return set_session_cookie(response, token, settings)


@auth_bp.get("/session")
def get_session():
    try:
        user_session = read_session()

        if user_session is None:
            response = jsonify({"error": "Not signed in"})
            response.status_code = 401
            clear_session_cookie(response)
            return response

        return jsonify({"user": serialize_user(user_session.user)})

    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to validate login session")
        return jsonify({"error": "Authentication service unavailable"}), 503


@auth_bp.post("/logout")
def logout():
    origin_error = check_request_origin()
    if origin_error is not None:
        return origin_error

    token = request.cookies.get(COOKIE_NAME)

    if token:
        try:
            user_session = db.session.scalar(
                select(UserSession).where(
                    UserSession.token_hash == hash_session_token(token)
                )
            )

            if user_session is not None and user_session.revoked_at is None:
                user_session.revoked_at = utc_now()
                db.session.commit()

        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Failed to revoke login session")

            response = jsonify({
                "error": "Could not securely revoke session. Please retry."
            })
            response.status_code = 503
            clear_session_cookie(response)
            return response

    response = jsonify({"message": "Signed out"})
    return clear_session_cookie(response)
