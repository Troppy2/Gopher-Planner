"""Isolated migration-backed API fixtures. No real accounts or credentials."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4
import json
import os
import sqlite3
from pathlib import Path

import pytest
from flask_migrate import upgrade


# TEST_DATABASE_URL points at a disposable PostgreSQL database (never Supabase or any
# shared database). Every test drops and recreates its public schema. Unset: SQLite.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")
ON_POSTGRES = TEST_DATABASE_URL.startswith("postgresql")
postgres_only = pytest.mark.skipif(not ON_POSTGRES, reason="needs TEST_DATABASE_URL (PostgreSQL)")
sqlite_only = pytest.mark.skipif(ON_POSTGRES, reason="SQLite-specific behavior")


def reset_postgres(url):
    from sqlalchemy import create_engine, text

    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    engine.dispose()


def make_database_url(tmp_path, name="users.db"):
    if ON_POSTGRES:
        reset_postgres(TEST_DATABASE_URL)
        return TEST_DATABASE_URL
    return f"sqlite:///{(tmp_path / name).as_posix()}"


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "synthetic-client")
    monkeypatch.setenv("JWT_SECRET", "synthetic-test-value")
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://localhost:5173")
    monkeypatch.setenv("DATABASE_URL", make_database_url(tmp_path))
    from app import create_app
    from app.extensions import db

    application = create_app()
    application.config.update(TESTING=True)
    with application.app_context():
        upgrade(directory="migrations")
        yield application
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def post_headers():
    return {"Origin": "http://localhost:5173"}


@pytest.fixture
def clock(monkeypatch):
    """Settable external clock, shared by session and application tests."""
    state = {"now": datetime(2026, 11, 7, 12, tzinfo=timezone.utc)}

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            value = state["now"]
            return value.astimezone(tz) if tz else value.replace(tzinfo=None)

    from app.models import user_session
    from app.core import auth
    monkeypatch.setattr(user_session, "datetime", FrozenDatetime)
    monkeypatch.setattr(auth, "datetime", FrozenDatetime)
    return state


@pytest.fixture
def make_user(app):
    from app.extensions import db
    from app.models import User

    def make(email=None):
        identity = uuid4().hex
        user = User(google_sub=identity, email=email or f"synthetic-{identity}@example.invalid")
        db.session.add(user)
        db.session.commit()
        return user

    return make


@pytest.fixture
def login_as(app, client):
    from app.api.v1.auth import hash_session_token
    from app.extensions import db
    from app.models import UserSession

    def login(user, *, expires_at=None, revoked_at=None):
        token = uuid4().hex
        session = UserSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=expires_at or datetime.now(timezone.utc) + timedelta(days=1),
            revoked_at=revoked_at,
        )
        db.session.add(session)
        db.session.commit()
        client.set_cookie("gp_session", token)
        return session

    return login


@pytest.fixture
def catalog(app, tmp_path):
    """Build a synthetic SQLite export (schema copied from the bundled file, rows invented),
    then import it into the test database through the same path production uses."""
    from app.services.catalog_import import import_catalog

    path = tmp_path / "catalog.db"
    source = Path(__file__).resolve().parents[1] / "data" / "courses.db"
    with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as original:
        schema = original.execute("SELECT sql FROM sqlite_master WHERE type='table'").fetchall()
    with sqlite3.connect(path) as connection:
        for (statement,) in schema:
            connection.execute(statement)
        connection.execute("INSERT INTO catalog VALUES (1, 'synthetic', '2026-01-01')")
        columns = [row[1] for row in connection.execute("PRAGMA table_info(courses)")]
        for index in range(1, 13):
            subject = "CSCI" if index <= 6 else "MATH"
            number = str(1000 + index if index <= 6 else 2000 + index)
            tree = {"type": "course", "course_code": "CSCI 1001"} if index == 2 else None
            if index == 3:
                tree = {"type": "any_of", "requirements": [
                    {"type": "course", "course_code": "CSCI 1001"},
                    {"type": "course", "course_code": "CSCI 1002"}]}
            if index == 4:
                tree = {"type": "all_of", "requirements": [
                    {"type": "course", "course_code": "CSCI 1002"},
                    {"type": "condition", "text": "Synthetic permission condition"}]}
            row = dict.fromkeys(columns, "-")
            row.update(id=index, catalog_id=1, subject_code=subject, course_number=number,
                       course_code=f"{subject} {number}", course_name=f"Synthetic course {index}",
                       minimum_credits="4" if index % 2 else "3",
                       maximum_credits="4" if index % 2 else "3",
                       typically_offered="Fall" if index % 2 else "Spring",
                       requirements="synthetic-core" if index <= 6 else "-",
                       prerequisite_json=json.dumps({"status": "found" if tree else "none", "requirements": tree}),
                       prerequisite_unresolved_courses="[]")
            connection.execute(f"INSERT INTO courses ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})", list(row.values()))
        connection.execute("INSERT INTO prerequisite_edges VALUES (2, 1)")
    import_catalog(path)
    return path


@pytest.fixture
def program_files(monkeypatch):
    """Point program lookup at synthetic fixtures only, never shipped academic files."""
    from app.services import programs

    path = Path(__file__).parent / "fixtures" / "programs"
    monkeypatch.setenv("PROGRAM_DATA_PATH", str(path))
    programs.clear_program_cache()
    yield path
    programs.clear_program_cache()


@pytest.fixture
def today(monkeypatch):
    """Settable planning date; defaults to a Fall 2026 day."""
    from datetime import date
    from app.services import plan

    state = {"value": date(2026, 11, 7)}
    monkeypatch.setattr(plan, "today", lambda: state["value"])
    return state
