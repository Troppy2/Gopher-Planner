"""The catalog lives in the application database; the app never opens a SQLite catalog at runtime."""
import hashlib
import sqlite3
import threading
import time

from sqlalchemy import create_engine, func, inspect, select, text

from tests.conftest import TEST_DATABASE_URL, postgres_only


def counts():
    from app.extensions import db
    from app.models import CatalogCourse, CatalogPrerequisiteEdge, CatalogRelease

    return tuple(db.session.scalar(select(func.count()).select_from(model))
                 for model in (CatalogRelease, CatalogCourse, CatalogPrerequisiteEdge))


def test_le_filter_matches_a_whole_designation(client, catalog, make_user, login_as):
    from app.extensions import db
    from app.models import CatalogCourse
    login_as(make_user())
    db.session.query(CatalogCourse).filter_by(course_code="CSCI 1001").one().le_attributes = "Synthetic arts; Synthetic perspective"
    db.session.commit()
    result = client.get('/api/v1/courses', query_string={"le": "Synthetic perspective"}).json
    assert result["total"] == 1
    assert result["courses"][0]["code"] == "CSCI 1001"
    assert client.get('/api/v1/courses', query_string={"le": "perspective"}).json["total"] == 0
    assert client.get('/api/v1/courses', query_string=[("le", "Synthetic perspective"), ("le", "Other synthetic category")]).json["total"] == 0


def test_migration_creates_catalog_tables(app):
    from app.extensions import db

    assert {"catalog_releases", "catalog_courses", "catalog_prerequisite_edges"} <= set(inspect(db.engine).get_table_names())


def test_import_copies_courses_and_edges_without_touching_the_source(app, catalog):
    from app.services.catalog_import import import_catalog

    assert counts() == (1, 12, 1)
    before = hashlib.sha256(catalog.read_bytes()).hexdigest()
    import_catalog(catalog)
    assert counts() == (1, 12, 1)
    assert hashlib.sha256(catalog.read_bytes()).hexdigest() == before


def test_import_replaces_the_previous_release(app, catalog, tmp_path):
    from app.extensions import db
    from app.models import CatalogRelease
    from app.services.catalog_import import import_catalog

    replacement = tmp_path / "replacement.db"
    with sqlite3.connect(catalog) as source, sqlite3.connect(replacement) as target:
        source.backup(target)
        target.execute("UPDATE catalog SET version = 'synthetic-2'")
        target.execute("DELETE FROM prerequisite_edges")
        target.execute("DELETE FROM courses WHERE id > 6")
    import_catalog(replacement)
    assert counts() == (1, 6, 0)
    assert db.session.scalars(select(CatalogRelease.version)).all() == ["synthetic-2"]


def test_runtime_catalog_reads_never_open_sqlite(client, catalog, make_user, login_as, monkeypatch):
    from app.repositories.catalog import find_courses

    def refuse(*args, **kwargs):
        raise AssertionError("runtime opened a SQLite catalog")

    monkeypatch.setattr(sqlite3, "connect", refuse)
    login_as(make_user())
    assert client.get("/api/v1/courses?q=synthetic").json["total"] == 12
    assert client.get("/api/v1/courses/CSCI%201002").json["resolvedPrerequisites"] == [
        {"code": "CSCI 1001", "title": "Synthetic course 1"}]
    assert set(find_courses(["CSCI 1002", "ZZZZ 9999"])) == {"CSCI 1002"}


def test_text_search_stays_case_insensitive(client, catalog, make_user, login_as):
    login_as(make_user())
    assert client.get("/api/v1/courses?q=SYNTHETIC%20COURSE%201").json["total"] == 4
    assert client.get("/api/v1/courses?q=csci%201001").json["courses"][0]["code"] == "CSCI 1001"


def held_user_lock(user_id):
    """Hold the user's row lock from a separate connection, as a concurrent request would."""
    engine = create_engine(TEST_DATABASE_URL)
    connection = engine.connect()
    transaction = connection.begin()
    connection.execute(text("SELECT id FROM users WHERE id = :id FOR NO KEY UPDATE"), {"id": user_id})
    return engine, connection, transaction


def assert_waits_for_lock(app, user_id, request):
    engine, connection, transaction = held_user_lock(user_id)
    result = {}
    worker = threading.Thread(target=lambda: result.setdefault("status", request(app.test_client())))
    try:
        worker.start()
        time.sleep(0.8)
        assert "status" not in result, "write did not wait for the user's row lock"
    finally:
        transaction.commit()
        connection.close()
        engine.dispose()
    worker.join(10)
    assert result["status"] == 200


def session_client(app, token):
    def request(method, path, body):
        def call(client):
            client.set_cookie("gp_session", token)
            return getattr(client, method)(path, json=body, headers={"Origin": "http://localhost:5173"}).status_code
        return call
    return request


@postgres_only
def test_plan_and_coursework_writes_serialize_per_user(app, client, catalog, make_user, login_as, post_headers):
    user = make_user()
    session = login_as(user)
    token = client.get_cookie("gp_session").value
    assert session is not None
    request = session_client(app, token)
    plan_body = {"changes": [{"code": "CSCI 1001", "status": "plan", "term": "Fall 2027"}]}
    assert_waits_for_lock(app, user.id, request("put", "/api/v1/plan", plan_body))
    assert_waits_for_lock(app, user.id, request("put", "/api/v1/coursework", {"courses": [], "skipped": False}))
