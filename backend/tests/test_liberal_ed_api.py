"""Liberal education tracker in GET /plan and the double-dipper endpoint. Synthetic data only."""
import pytest


@pytest.fixture
def le_catalog(app, catalog):
    """Give synthetic catalog rows liberal education designations."""
    from sqlalchemy import update

    from app.extensions import db
    from app.models import CatalogCourse

    designations = {
        "CSCI 1001": "Literature; Global Perspectives",
        "CSCI 1003": "Historical Perspectives; Race, Power, and Justice US; Writing Intensive",
        "CSCI 1005": "Arts/Humanities",
        "MATH 2007": "Social Sciences; Environment",
        "MATH 2009": "Physical Sciences; Technology and Society; Writing Intensive",
        "MATH 2011": "Biological Sciences; Diversity and Soc Justice US",
    }
    for code, value in designations.items():
        db.session.execute(update(CatalogCourse).where(CatalogCourse.course_code == code).values(le_attributes=value))
    db.session.commit()
    return designations


def save_coursework(client, headers, *courses):
    body = {"courses": list(courses), "skipped": False}
    assert client.put("/api/v1/coursework", json=body, headers=headers).status_code == 200


def work(code, status="done", grade="A", term="Fall 2025"):
    return {"code": code, "title": "Synthetic", "credits": 4, "status": status,
            "term": term if status == "done" else "Fall 2026", "grade": grade if status == "done" else None}


def test_plan_includes_tracker_from_coursework(client, make_user, login_as, post_headers, le_catalog, today):
    login_as(make_user())
    save_coursework(client, post_headers, work("CSCI 1001"), work("CSCI 1003", status="prog"))
    liberal = client.get("/api/v1/plan").json["liberalEd"]
    core = {item["id"]: item for item in liberal["core"]["items"]}
    themes = {item["id"]: item for item in liberal["themes"]["items"]}
    assert core["literature"]["status"] == "done"
    assert core["historical-perspectives"]["status"] == "in_progress"
    assert themes["global-perspectives"]["codes"]["done"] == ["CSCI 1001"]
    assert themes["race-power-justice"]["status"] == "in_progress"
    assert liberal["writing"]["intensive"]["projected"]["total"] == 1
    assert liberal["source"] == "catalog"


def test_failed_course_does_not_count(client, make_user, login_as, post_headers, le_catalog, today):
    login_as(make_user())
    save_coursework(client, post_headers, work("CSCI 1001", grade="F"))
    core = {item["id"]: item for item in client.get("/api/v1/plan").json["liberalEd"]["core"]["items"]}
    assert core["literature"]["status"] == "needed"


def test_double_dippers_rank_courses_covering_remaining_needs(client, make_user, login_as, post_headers, le_catalog, today):
    login_as(make_user())
    save_coursework(client, post_headers, work("CSCI 1001"))
    response = client.get("/api/v1/liberal-ed/double-dippers?limit=10")
    assert response.status_code == 200
    body = response.json
    codes = [course["code"] for course in body["courses"]]
    assert "CSCI 1001" not in codes  # already taken
    assert "CSCI 1005" not in codes  # covers only one need
    assert codes[:2] == ["CSCI 1003", "MATH 2009"]  # three needs each, then code order
    first = body["courses"][0]
    assert first["covers"] == ["Historical Perspectives", "Race, Power, and Justice US", "Writing Intensive"]
    # The former theme name still counts toward Race, Power, and Justice.
    by_code = {course["code"]: course for course in body["courses"]}
    assert by_code["MATH 2011"]["covers"] == ["Biological Sciences", "Race, Power, and Justice US"]
    assert body["total"] == len(codes)


def test_double_dippers_paginate_and_validate(client, make_user, login_as, le_catalog, today):
    login_as(make_user())
    page = client.get("/api/v1/liberal-ed/double-dippers?limit=1&offset=1").json
    assert page["limit"] == 1 and page["offset"] == 1 and len(page["courses"]) == 1
    assert client.get("/api/v1/liberal-ed/double-dippers?limit=0").status_code == 400
    assert client.get("/api/v1/liberal-ed/double-dippers?limit=x").status_code == 400


def test_double_dippers_require_sign_in(client):
    assert client.get("/api/v1/liberal-ed/double-dippers").status_code == 401
