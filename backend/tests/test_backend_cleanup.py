"""Configuration and session housekeeping (issue #12)."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

CLAIMS = {"sub": "synthetic-sub", "email": "synthetic@umn.edu", "email_verified": True,
          "name": "Synthetic Student", "picture": None}


def sign_in(client, monkeypatch, post_headers):
    monkeypatch.setattr("app.core.google_auth.id_token.verify_oauth2_token", lambda *a, **kw: CLAIMS)
    response = client.post("/api/v1/auth/google", json={"credential": "synthetic"}, headers=post_headers)
    assert response.status_code == 200
    return response


def test_app_starts_without_jwt_secret(tmp_path, monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "synthetic-client")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'no-secret.db').as_posix()}")
    from app import create_app

    application = create_app()
    assert application.test_client().get("/health").json == {"status": "ok"}


def test_missing_google_client_id_is_still_required(tmp_path, monkeypatch):
    import pytest
    from app.core.config import Settings

    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'missing.db').as_posix()}")
    with pytest.raises(RuntimeError, match="GOOGLE_CLIENT_ID"):
        Settings.from_env()


def test_sign_in_removes_expired_and_revoked_sessions_for_that_user(app, client, monkeypatch, post_headers):
    from app.extensions import db
    from app.models import User, UserSession

    sign_in(client, monkeypatch, post_headers)
    user = db.session.scalar(select(User).where(User.google_sub == "synthetic-sub"))
    now = datetime.now(timezone.utc)
    db.session.add_all([
        UserSession(user_id=user.id, token_hash="e" * 64, expires_at=now - timedelta(seconds=1)),
        UserSession(user_id=user.id, token_hash="r" * 64, expires_at=now + timedelta(days=1), revoked_at=now),
        UserSession(user_id=user.id, token_hash="a" * 64, expires_at=now + timedelta(days=1)),
    ])
    db.session.commit()

    sign_in(client, monkeypatch, post_headers)

    db.session.expire_all()
    hashes = set(db.session.scalars(select(UserSession.token_hash).where(UserSession.user_id == user.id)))
    assert "e" * 64 not in hashes
    assert "r" * 64 not in hashes
    assert "a" * 64 in hashes
    assert len(hashes) == 3  # the untouched active session plus two real sign-ins


def test_sign_in_does_not_touch_other_users_sessions(app, client, make_user, monkeypatch, post_headers):
    from app.extensions import db
    from app.models import UserSession

    other = make_user()
    db.session.add(UserSession(user_id=other.id, token_hash="o" * 64,
                               expires_at=datetime.now(timezone.utc) - timedelta(days=1)))
    db.session.commit()

    sign_in(client, monkeypatch, post_headers)
    sign_in(client, monkeypatch, post_headers)

    count = db.session.scalar(select(func.count()).select_from(UserSession).where(UserSession.user_id == other.id))
    assert count == 1


def test_current_session_still_works_after_cleanup(app, client, monkeypatch, post_headers):
    sign_in(client, monkeypatch, post_headers)
    sign_in(client, monkeypatch, post_headers)
    assert client.get("/api/v1/profile").status_code == 200
