"""Rate limits on sign-in and expensive endpoints, proxy handling and readiness. Synthetic only."""
import pytest
from flask_migrate import upgrade
from sqlalchemy.exc import OperationalError

from tests.conftest import make_database_url


@pytest.fixture
def make_app(tmp_path, monkeypatch):
    """Build an app with extra environment variables set before create_app reads them."""
    created = []

    def make(**env):
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "synthetic-client")
        monkeypatch.setenv("JWT_SECRET", "synthetic-test-value")
        monkeypatch.setenv("FRONTEND_ORIGIN", "http://localhost:5173")
        monkeypatch.setenv("DATABASE_URL", make_database_url(tmp_path, f"limits-{len(created)}.db"))
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        from app import create_app

        application = create_app()
        application.config.update(TESTING=True)
        with application.app_context():
            upgrade(directory="migrations")
        created.append(application)
        return application

    yield make
    from app.extensions import db
    for application in created:
        with application.app_context():
            db.session.remove()
            db.engine.dispose()


def sign_in(client, post_headers, **headers):
    return client.post("/api/v1/auth/google", json={}, headers={**post_headers, **headers})


def test_sign_in_is_limited_per_address(make_app, post_headers):
    client = make_app().test_client()
    for _ in range(30):
        assert sign_in(client, post_headers).status_code == 400
    response = sign_in(client, post_headers)
    assert response.status_code == 429
    assert response.json["code"] == "too_many_requests"
    assert "Retry-After" in response.headers


def test_forwarded_address_is_ignored_without_trusted_proxy(make_app, post_headers):
    client = make_app().test_client()
    for index in range(30):
        sign_in(client, post_headers, **{"X-Forwarded-For": f"203.0.113.{index}"})
    assert sign_in(client, post_headers, **{"X-Forwarded-For": "203.0.113.250"}).status_code == 429


def test_trusted_proxy_separates_clients(make_app, post_headers):
    client = make_app(TRUSTED_PROXY_HOPS="1").test_client()
    for _ in range(30):
        sign_in(client, post_headers, **{"X-Forwarded-For": "203.0.113.1"})
    assert sign_in(client, post_headers, **{"X-Forwarded-For": "203.0.113.1"}).status_code == 429
    assert sign_in(client, post_headers, **{"X-Forwarded-For": "203.0.113.2"}).status_code == 400


def test_rate_limits_can_be_disabled(make_app, post_headers):
    client = make_app(RATELIMIT_ENABLED="false").test_client()
    for _ in range(35):
        assert sign_in(client, post_headers).status_code == 400


def test_transcript_uploads_are_limited_per_session(make_app, post_headers):
    from app.api.v1.auth import hash_session_token
    from app.extensions import db
    from app.models import User, UserSession
    from datetime import datetime, timedelta, timezone

    application = make_app()

    def session_client(name):
        client = application.test_client()
        with application.app_context():
            user = User(google_sub=f"limit-{name}", email=f"limit-{name}@example.invalid")
            db.session.add(user)
            db.session.flush()
            db.session.add(UserSession(user_id=user.id, token_hash=hash_session_token(f"token-{name}"),
                                       expires_at=datetime.now(timezone.utc) + timedelta(days=1)))
            db.session.commit()
        client.set_cookie("gp_session", f"token-{name}")
        return client

    first, second = session_client("a"), session_client("b")
    for _ in range(20):
        assert first.post("/api/v1/transcripts", headers=post_headers).status_code != 429
    assert first.post("/api/v1/transcripts", headers=post_headers).status_code == 429
    # Same address, different session: its own budget.
    assert second.post("/api/v1/transcripts", headers=post_headers).status_code != 429


def test_ready_reports_database_state(make_app, monkeypatch):
    application = make_app()
    client = application.test_client()
    assert client.get("/ready").json == {"status": "ok"}

    from app.extensions import db

    def broken(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("synthetic outage"))

    monkeypatch.setattr(db.session, "execute", broken)
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json == {"status": "unavailable"}
