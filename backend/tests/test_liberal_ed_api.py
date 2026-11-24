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
        # Mirror real catalog rows: CSCI 1003 has a prerequisite in the synthetic catalog, the rest have none.
        status = "found" if code == "CSCI 1003" else "none"
        db.session.execute(update(CatalogCourse).where(CatalogCourse.course_code == code)
                           .values(le_attributes=value, prerequisite_status=status))
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
    # Three needs each; the course without prerequisites ranks first.
    assert codes[:2] == ["MATH 2009", "CSCI 1003"]
    assert body["courses"][0]["covers"] == ["Physical Sciences", "Technology and Society", "Writing Intensive"]
    assert body["courses"][1]["covers"] == ["Historical Perspectives", "Race, Power, and Justice US", "Writing Intensive"]
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


def test_generation_fills_liberal_ed_gaps_with_courses_that_count_twice(client, make_user, login_as, post_headers,
                                                                         le_catalog, program_files, today):
    login_as(make_user())
    profile = {"major": "Mini Synthetic B.S.", "graduationTarget": "Spring 2030", "creditLoad": 18}
    assert client.put("/api/v1/profile", json=profile, headers=post_headers).status_code == 200
    response = client.post("/api/v1/plans/generate", json={"catalogTerm": "Fall 2026", "dryRun": True}, headers=post_headers)
    assert response.status_code == 200
    plan = response.json["plan"]
    slots = {course["code"]: course["slot"] for course in plan["courses"] if course.get("slot")}
    # Prerequisite-free designated courses fill the gaps; CSCI 1003 has a prerequisite and is skipped.
    assert "CSCI 1003" not in slots
    assert slots["MATH 2009"] == "Physical Sciences, Technology and Society, Writing Intensive"
    assert slots["MATH 2011"] == "Race, Power, and Justice US, Biological Sciences"
    liberal = plan["liberalEd"]
    themes = {item["id"]: item["status"] for item in liberal["themes"]["items"]}
    assert themes["race-power-justice"] == "planned"
    core = {item["id"]: item["status"] for item in liberal["core"]["items"]}
    assert {core[key] for key in ("literature", "arts-humanities", "social-sciences", "physical-sciences", "biological-sciences")} == {"planned"}


def test_generation_does_not_add_liberal_ed_already_covered(client, make_user, login_as, post_headers,
                                                            le_catalog, program_files, today):
    login_as(make_user())
    profile = {"major": "Mini Synthetic B.S.", "graduationTarget": "Spring 2030", "creditLoad": 18}
    assert client.put("/api/v1/profile", json=profile, headers=post_headers).status_code == 200
    save_coursework(client, post_headers, work("CSCI 1001"))  # Literature and Global Perspectives
    plan = client.post("/api/v1/plans/generate", json={"catalogTerm": "Fall 2026", "dryRun": True}, headers=post_headers).json["plan"]
    slots = {course["code"]: course["slot"] for course in plan["courses"] if course.get("slot")}
    assert not any("Literature" in label or "Global Perspectives" in label for label in slots.values())


def test_generated_liberal_ed_slots_can_be_saved(client, make_user, login_as, post_headers, le_catalog, program_files, today):
    """Build, then keep the draft: gap-filled slot labels must pass save validation."""
    login_as(make_user())
    profile = {"major": "Mini Synthetic B.S.", "graduationTarget": "Spring 2030", "creditLoad": 18}
    assert client.put("/api/v1/profile", json=profile, headers=post_headers).status_code == 200
    draft = client.post("/api/v1/plans/generate", json={"catalogTerm": "Fall 2026", "dryRun": True}, headers=post_headers).json["plan"]
    changes = [{"code": c["code"], "status": "plan", "term": c["term"], **({"slot": c["slot"]} if c.get("slot") else {})}
               for c in draft["courses"] if c["status"] == "plan"]
    assert any("," in change.get("slot", "") for change in changes)  # a multi-designation label, e.g. with RPJ
    saved = client.put("/api/v1/plan", json={"changes": changes, "catalogTerm": "Fall 2026"}, headers=post_headers)
    assert saved.status_code == 200, saved.json
    by_code = {c["code"]: c for c in saved.json["courses"]}
    assert by_code["MATH 2011"]["slot"] == "Race, Power, and Justice US, Biological Sciences"
    assert by_code["MATH 2011"]["slotCategories"] == ["Biological Sciences", "Diversity and Soc Justice US"] or \
        set(by_code["MATH 2011"]["slotCategories"]) >= {"Biological Sciences"}


def test_made_up_slot_labels_are_still_rejected(client, make_user, login_as, post_headers, le_catalog, program_files, today):
    login_as(make_user())
    assert client.put("/api/v1/profile", json={"major": "Mini Synthetic B.S."}, headers=post_headers).status_code == 200
    change = {"code": "MATH 2011", "status": "plan", "term": "Spring 2027", "slot": "Basket Weaving"}
    response = client.put("/api/v1/plan", json={"changes": [change], "catalogTerm": "Fall 2026"}, headers=post_headers)
    assert response.status_code == 400
    # A real designation the course does not carry is rejected too.
    change["slot"] = "Literature"
    response = client.put("/api/v1/plan", json={"changes": [change], "catalogTerm": "Fall 2026"}, headers=post_headers)
    assert response.status_code == 400
