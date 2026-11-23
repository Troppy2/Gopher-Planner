def entry(**changes):
    return {"code": "CSCI 1001", "title": "Synthetic course", "credits": 3.5,
            "status": "done", "term": None, "grade": "A-", **changes}


def test_get_coursework_returns_empty_state_for_new_user(client, make_user, login_as):
    login_as(make_user())
    response = client.get("/api/v1/coursework")
    assert response.status_code == 200
    assert response.json == {"courses": [], "skipped": False}


def test_put_coursework_persists_manual_entries(client, make_user, login_as, post_headers):
    login_as(make_user())
    body = {"courses": [entry()], "skipped": False}
    response = client.put("/api/v1/coursework", json=body, headers=post_headers)
    assert response.status_code == 200
    expected = {"courses": [{**entry(), "source": "manual"}], "skipped": False}
    assert response.json == expected
    assert client.get("/api/v1/coursework").json == expected


def test_put_coursework_replaces_previous_set(client, make_user, login_as, post_headers):
    login_as(make_user())
    first = client.put("/api/v1/coursework", json={"courses": [entry()], "skipped": False}, headers=post_headers)
    assert first.status_code == 200
    course = entry(code="MATH 2001", status="prog", grade=None, term="Fall 2026")
    response = client.put("/api/v1/coursework", json={"courses": [course], "skipped": False}, headers=post_headers)
    assert response.status_code == 200
    assert client.get("/api/v1/coursework").json == {"courses": [{**course, "source": "manual"}], "skipped": False}


def test_put_coursework_persists_skipped_empty_state(client, make_user, login_as, post_headers):
    login_as(make_user())
    body = {"courses": [], "skipped": True}
    response = client.put("/api/v1/coursework", json=body, headers=post_headers)
    assert response.status_code == 200
    assert response.json == body
    assert client.get("/api/v1/coursework").json == body
import pytest




@pytest.mark.parametrize("body", [
    {"courses": [entry(code="bad")], "skipped": True},
    *[{"courses": [entry(credits=value)], "skipped": True} for value in (0, 13, 0.3, True, 10**400)],
    {"courses": [entry(grade="Z")], "skipped": True},
    {"courses": [entry(status="prog")], "skipped": True},
    {"courses": [entry(term="Winter 2026")], "skipped": True},
    {"courses": [entry(), entry()], "skipped": True},
    {"courses": [entry(code=f"CSCI {1000+i}") for i in range(301)], "skipped": True},
    {"courses": {}, "skipped": True},
    [],
    {"courses": [entry(extra="no")], "skipped": True},
    {"courses": [entry()], "skipped": True, "user_id": 99},
    {"courses": [entry(title="")], "skipped": True},
    {"courses": [entry(status="plan")], "skipped": True},
    {"courses": [entry()], "skipped": "yes"},
])
def test_put_coursework_rejects_invalid_input_atomically(app, client, make_user, login_as, post_headers, body):
    login_as(make_user())
    saved = client.put("/api/v1/coursework", json={"courses": [entry()], "skipped": False}, headers=post_headers)
    assert saved.status_code == 200
    app.config["PROPAGATE_EXCEPTIONS"] = False
    response = client.put("/api/v1/coursework", json=body, headers=post_headers)
    assert response.status_code == 400
    assert isinstance(response.json["code"], str)
    assert client.get("/api/v1/coursework").json == saved.json


def test_put_coursework_preserves_existing_transcript_provenance(client, make_user, login_as, post_headers):
    from uuid import uuid4
    from app.extensions import db
    from app.models import Coursework, Transcript

    user = make_user()
    transcript = Transcript(id=uuid4().hex, user_id=user.id, file_name="synthetic.pdf", status="parsed")
    db.session.add(transcript)
    db.session.flush()
    db.session.add(Coursework(user_id=user.id, transcript_id=transcript.id, source="transcript", **entry()))
    db.session.commit()
    login_as(user)
    course = {**entry(), "source": "transcript"}
    response = client.put("/api/v1/coursework", json={"courses": [course], "skipped": False}, headers=post_headers)
    assert response.status_code == 200
    assert response.json["courses"] == [course]
    row = db.session.query(Coursework).filter_by(user_id=user.id).one()
    assert row.transcript_id == transcript.id


def test_coursework_is_isolated_between_two_users(client, make_user, login_as, post_headers):
    first, second = make_user(), make_user()
    login_as(first)
    saved = client.put("/api/v1/coursework", json={"courses": [entry()], "skipped": False}, headers=post_headers)
    assert saved.status_code == 200
    login_as(second)
    assert client.get("/api/v1/coursework").json == {"courses": [], "skipped": False}
    changed = client.put("/api/v1/coursework", json={"courses": [entry(credits=4)], "skipped": True}, headers=post_headers)
    assert changed.status_code == 200
    login_as(first)
    assert client.get("/api/v1/coursework").json == saved.json


@pytest.mark.parametrize("method", ["get", "put"])
def test_coursework_requires_authentication(client, post_headers, method):
    response = getattr(client, method)("/api/v1/coursework", json={"courses": [], "skipped": False}, headers=post_headers)
    assert response.status_code == 401
    assert response.json == {"error": "Not signed in"}


def test_coursework_rejects_wrong_origin_without_mutating(client, make_user, login_as):
    login_as(make_user())
    response = client.put("/api/v1/coursework", json={"courses": [entry()], "skipped": True}, headers={"Origin": "http://untrusted.invalid"})
    assert response.status_code == 403
    assert client.get("/api/v1/coursework").json == {"courses": [], "skipped": False}
