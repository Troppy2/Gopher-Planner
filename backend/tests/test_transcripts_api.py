"""Upload, status, and coursework endpoints against an in-memory database."""

import io
from datetime import datetime, timedelta, timezone

import pytest

import app.api.v1.transcripts as transcripts_module
from app import create_app
from app.api.v1.auth import COOKIE_NAME, hash_session_token
from app.extensions import db
from app.models import User, UserSession
from tests.test_apas_parser import SAMPLE

ORIGIN = "http://localhost:3000"


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("FRONTEND_ORIGIN", ORIGIN)
    flask_app = create_app()
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()


def sign_in(client, email="student@umn.edu", token="token-1"):
    user = User(google_sub=email, email=email)
    db.session.add(user)
    db.session.flush()
    db.session.add(UserSession(
        user_id=user.id,
        token_hash=hash_session_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    ))
    db.session.commit()
    client.set_cookie(COOKIE_NAME, token)
    return user


def upload(client, pdf_text, monkeypatch, filename="audit.pdf"):
    monkeypatch.setattr(transcripts_module, "extract_pdf_text", lambda _f: pdf_text)
    return client.post(
        "/api/v1/transcripts",
        data={"file": (io.BytesIO(b"%PDF-fake"), filename)},
        headers={"Origin": ORIGIN},
        content_type="multipart/form-data",
    )


def test_upload_requires_sign_in(app, monkeypatch):
    assert upload(app.test_client(), SAMPLE, monkeypatch).status_code == 401


def test_upload_parses_and_stores_courses(app, monkeypatch):
    client = app.test_client()
    sign_in(client)

    response = upload(client, SAMPLE, monkeypatch)
    assert response.status_code == 201
    upload_id = response.get_json()["id"]

    status = client.get(f"/api/v1/transcripts/{upload_id}").get_json()
    assert status == {
        "id": upload_id, "fileName": "audit.pdf", "status": "parsed",
        "completed": 4, "inProgress": 2,
    }

    courses = client.get("/api/v1/coursework").get_json()["courses"]
    assert [c["code"] for c in courses][:2] == ["MATH 1271", "CSCI 1133"]  # Spring 2025 first
    ib = courses[0]
    assert (ib["creditSource"], ib["earnedCredits"]) == ("IB", 4.0)


def test_second_upload_replaces_first(app, monkeypatch):
    client = app.test_client()
    sign_in(client)
    upload(client, SAMPLE, monkeypatch)
    upload(client, "F 25 1CSCI1133 4.0 A Intro to Programming Concepts", monkeypatch)
    codes = [c["code"] for c in client.get("/api/v1/coursework").get_json()["courses"]]
    assert codes == ["CSCI 1133"]


def test_scanned_pdf_is_no_text(app, monkeypatch):
    client = app.test_client()
    sign_in(client)
    upload_id = upload(client, "   ", monkeypatch).get_json()["id"]
    assert client.get(f"/api/v1/transcripts/{upload_id}").get_json()["status"] == "no_text"


def test_non_audit_pdf_fails(app, monkeypatch):
    client = app.test_client()
    sign_in(client)
    upload_id = upload(client, "A cover letter", monkeypatch).get_json()["id"]
    assert client.get(f"/api/v1/transcripts/{upload_id}").get_json()["status"] == "failed"


def test_rejects_non_pdf(app, monkeypatch):
    client = app.test_client()
    sign_in(client)
    assert upload(client, SAMPLE, monkeypatch, filename="audit.docx").status_code == 400


def test_rejects_untrusted_origin(app):
    client = app.test_client()
    sign_in(client)
    response = client.post("/api/v1/transcripts", headers={"Origin": "https://evil.example"})
    assert response.status_code == 403


def test_cannot_read_someone_elses_upload(app, monkeypatch):
    alice = app.test_client()
    sign_in(alice, "alice@umn.edu", "token-a")
    upload_id = upload(alice, SAMPLE, monkeypatch).get_json()["id"]

    bob = app.test_client()
    sign_in(bob, "bob@umn.edu", "token-b")
    assert bob.get(f"/api/v1/transcripts/{upload_id}").status_code == 404
