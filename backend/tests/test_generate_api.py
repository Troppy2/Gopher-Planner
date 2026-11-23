"""Synchronous generation API and the audit's end-to-end flow. Only Google verification and the clock are faked."""
import pytest

MINI = "Mini Synthetic B.S."


@pytest.fixture
def student(client, make_user, login_as, post_headers, catalog, program_files, today):
    def setup(major=MINI, courses=(), user=None, **profile):
        user = user or make_user()
        login_as(user)
        assert client.put("/api/v1/profile", json={"major": major, **profile}, headers=post_headers).status_code == 200
        if courses:
            assert client.put("/api/v1/coursework", json={"courses": list(courses), "skipped": False}, headers=post_headers).status_code == 200
        return user
    return setup


def work(code, status="done", grade="A", term="Fall 2025", credits=3):
    return {"code": code, "title": f"Synthetic {code}", "credits": credits, "status": status,
            "grade": None if status == "prog" else grade, "term": term}


def generate(client, headers, **body):
    return client.post("/api/v1/plans/generate", json=body, headers=headers)


def rows(app):
    from app.extensions import db
    from app.models import Plan, PlanCourse
    return (sorted((row.plan_id, row.code, row.term, row.source) for row in db.session.query(PlanCourse)),
            sorted((row.user_id, row.catalog_term, row.generated_at is not None) for row in db.session.query(Plan)))


def planned(plan):
    return {course["code"]: course["term"] for course in plan["courses"] if course["status"] == "plan"}


def test_empty_current_semester_is_seeded_from_the_sample_without_writing_on_preview(client, student, post_headers, tmp_path, monkeypatch, app):
    import json
    student(graduationTarget="Spring 2030")
    (tmp_path / "mini-synthetic.json").write_text(json.dumps({"terms": [
        {"year": 1, "season": "Fall", "items": [{"kind": "course", "codes": ["MINI 1101"]}]},
        {"year": 1, "season": "Spring", "items": [{"kind": "course", "codes": ["MINI 1102"]}]},
    ]}), encoding="utf-8")
    monkeypatch.setenv("SAMPLE_PLAN_DATA_PATH", str(tmp_path))
    before = rows(app)
    preview = generate(client, post_headers, dryRun=True, catalogTerm="Fall 2026")
    assert preview.status_code == 200
    assert planned(preview.json["plan"])["MINI 1101"] == "Fall 2026"
    assert planned(preview.json["plan"])["MINI 1102"] == "Spring 2027"
    assert rows(app) == before
    saved = generate(client, post_headers, catalogTerm="Fall 2026")
    assert saved.status_code == 200
    assert client.get("/api/v1/plan").json == saved.json["plan"]
    assert planned(saved.json["plan"])["MINI 1101"] == "Fall 2026"


def test_generation_keeps_existing_current_enrollment(client, student, post_headers):
    student(courses=[work("MINI 1101", "prog", term="Fall 2026")])
    result = generate(client, post_headers, catalogTerm="Fall 2026").json["plan"]
    assert all(term != "Fall 2026" for term in planned(result).values())
    assert next(c for c in result["courses"] if c["code"] == "MINI 1101")["status"] == "prog"


@pytest.mark.parametrize("covered", [False, True])
def test_sample_slots_round_trip_and_dry_run_is_read_only(client, student, post_headers, app, tmp_path, monkeypatch, covered):
    import json
    from app.extensions import db
    from app.models import CatalogCourse

    student(graduationTarget="Spring 2029", courses=[work("CSCI 1001")] if covered else [])
    for code in ("CSCI 1001", "CSCI 1006"):
        row = db.session.query(CatalogCourse).filter_by(course_code=code).one()
        row.le_attributes = "Synthetic perspective"
        row.prerequisite_status = "none"
    db.session.commit()
    sample = {"terms": [{"year": 2, "season": "Spring", "items": [
        {"kind": "le", "categories": ["Synthetic perspective"], "label": "Synthetic perspective"},
        {"kind": "course", "codes": ["MATH 2008"]}]}]}
    (tmp_path / "mini-synthetic.json").write_text(json.dumps(sample), encoding="utf-8")
    monkeypatch.setenv("SAMPLE_PLAN_DATA_PATH", str(tmp_path))
    before = rows(app)
    dry = generate(client, post_headers, catalogTerm="Fall 2026", dryRun=True)
    assert dry.status_code == 200
    assert rows(app) == before
    plan = dry.json["plan"]
    slots = [course for course in plan["courses"] if course.get("slot")]
    assert [course["code"] for course in slots] == ([] if covered else ["CSCI 1006"])
    if slots:
        assert slots[0]["slot"] == "Synthetic perspective"
        assert slots[0]["term"] == "Spring 2027"
    assert planned(plan)["MATH 2008"] == "Spring 2027"
    projected = plan["baseCredits"] + sum(c["credits"] for c in plan["courses"] if c["status"] in {"done", "prog", "plan"})
    assert plan["electiveCredits"] == max(0, 24 - projected)
    saved = generate(client, post_headers, catalogTerm="Fall 2026")
    assert saved.json["plan"] == plan
    assert client.get("/api/v1/plan").json == plan
    if slots:
        replacement = db.session.query(CatalogCourse).filter_by(course_code="MATH 2010").one()
        replacement.le_attributes = "Synthetic perspective"
        db.session.commit()
        swapped = client.put("/api/v1/plan", headers=post_headers, json={"changes": [
            {"code": "CSCI 1006", "status": "avail", "term": None},
            {"code": "MATH 2010", "status": "plan", "term": "Spring 2027", "slot": "Synthetic perspective"}]})
        assert swapped.status_code == 200
        assert next(c for c in swapped.json["courses"] if c["code"] == "MATH 2010")["slot"] == "Synthetic perspective"


def test_generation_matches_the_engine_and_persists_the_plan(client, student, post_headers, app):
    from app.services.metadata import resolve_course
    from app.services.planning.generate import generate_plan
    from app.services.planning.terms import plan_window
    from app.services.programs import load_program

    student()
    response = generate(client, post_headers, catalogTerm="Fall 2026")
    assert response.status_code == 200
    body = response.json
    assert body["status"] == "succeeded" and body["jobId"]
    program = load_program(MINI, "Fall 2026")
    expected = generate_plan(program, coursework=[], metadata={code: resolve_course(code, program, None) for code in program["courseMetadata"]},
                             terms=["Fall 2026", *plan_window("Fall 2026", "")], credit_load=15)
    assert planned(body["plan"]) == {item["code"]: item["term"] for item in expected["placements"]}
    assert body["plan"]["catalogTerm"] == "Fall 2026"
    assert client.get("/api/v1/plan").json == body["plan"]
    assert all(source == "generated" for _, _, _, source in rows(app)[0])


def test_le_prefetch_keeps_candidates_for_each_category(client, student, post_headers, tmp_path, monkeypatch):
    import json
    from app.extensions import db
    from app.models import CatalogCourse
    student(graduationTarget="Spring 2029")
    for code, category in [("CSCI 1002", "Synthetic arts"), ("CSCI 1004", "Synthetic arts"), ("CSCI 1006", "Synthetic history")]:
        row = db.session.query(CatalogCourse).filter_by(course_code=code).one()
        row.le_attributes, row.prerequisite_status = category, "none"
        row.prerequisite_json = json.dumps({"status": "none", "requirements": None})
    db.session.commit()
    (tmp_path / "mini-synthetic.json").write_text(json.dumps({"terms": [{"year": 2, "season": "Spring", "items": [
        {"kind": "le", "categories": ["Synthetic arts", "Synthetic history"], "label": "Synthetic breadth"}]}]}), encoding="utf-8")
    monkeypatch.setenv("SAMPLE_PLAN_DATA_PATH", str(tmp_path))
    from app.services import plan as service
    original = service.generate_plan
    def without_transaction(*args, **kwargs):
        assert not db.session().in_transaction()
        result = original(*args, **kwargs)
        assert not db.session().in_transaction()
        return result
    monkeypatch.setattr(service, "generate_plan", without_transaction)
    response = generate(client, post_headers, catalogTerm="Fall 2026", dryRun=True)
    assert response.status_code == 200
    slots = {c["code"] for c in response.json["plan"]["courses"] if c.get("slot")}
    assert slots == {"CSCI 1002", "CSCI 1006"}
    assert generate(client, post_headers, catalogTerm="Fall 2026").status_code == 200
    db.session.query(CatalogCourse).filter_by(course_code="MATH 2010").one().le_attributes = "Synthetic history"
    db.session.commit()
    response = client.put("/api/v1/plan", headers=post_headers, json={"changes": [
        {"code": code, "status": "avail", "term": None} for code in sorted(slots)] + [
        {"code": code, "status": "plan", "term": "Spring 2027", "slot": "Synthetic breadth"}
        for code in ["CSCI 1004", "MATH 2010"]]})
    assert response.status_code == 200


def test_generation_rejects_a_stale_snapshot_without_overwriting_newer_edits(client, student, post_headers, monkeypatch):
    from app.services import plan as service
    student()
    original = service.generate_plan
    def with_edit(*args, **kwargs):
        result = original(*args, **kwargs)
        response = client.put("/api/v1/plan", headers=post_headers, json={"catalogTerm": "Fall 2026", "changes": [
            {"code": "CSCI 1001", "status": "plan", "term": "Fall 2027"}]})
        assert response.status_code == 200
        return result
    monkeypatch.setattr(service, "generate_plan", with_edit)
    response = generate(client, post_headers, catalogTerm="Fall 2026")
    assert response.status_code == 409
    assert response.json["code"] == "plan_changed"
    assert planned(client.get("/api/v1/plan").json) == {"CSCI 1001": "Fall 2027"}


def test_rerunning_generation_replaces_generated_rows_without_duplicates(client, student, post_headers, app):
    student()
    generate(client, post_headers, catalogTerm="Fall 2026")
    first = rows(app)[0]
    assert generate(client, post_headers).status_code == 200
    assert rows(app)[0] == first


def test_dry_run_returns_the_same_plan_and_writes_nothing(client, student, post_headers, app):
    student()
    before = rows(app)
    dry = generate(client, post_headers, dryRun=True, catalogTerm="Fall 2026")
    assert dry.status_code == 200 and planned(dry.json["plan"]) and dry.json["plan"]["catalogTerm"] == "Fall 2026"
    assert rows(app) == before
    saved = generate(client, post_headers, catalogTerm="Fall 2026").json
    assert planned(saved["plan"]) == planned(dry.json["plan"])
    assert saved["warnings"] == dry.json["warnings"]


def test_completed_and_in_progress_coursework_is_never_placed(client, student, post_headers):
    student(courses=[work("MINI 1101"), work("MINI 1102", "prog", term="Fall 2026", credits=4)])
    plan = generate(client, post_headers, catalogTerm="Fall 2026").json["plan"]
    assert "MINI 1101" not in planned(plan) and "MINI 1102" not in planned(plan)
    statuses = {course["code"]: course["status"] for course in plan["courses"]}
    assert (statuses["MINI 1101"], statuses["MINI 1102"]) == ("done", "prog")


def test_credit_load_and_graduation_target_are_respected(client, student, post_headers):
    student(creditLoad=7, graduationTarget="Fall 2028")
    plan = generate(client, post_headers, catalogTerm="Fall 2026").json["plan"]
    assert plan["terms"] == ["Completed", "Fall 2026", "Spring 2027", "Fall 2027", "Spring 2028", "Fall 2028"]
    loads = {}
    for course in plan["courses"]:
        if course["status"] == "plan":
            loads[course["term"]] = loads.get(course["term"], 0) + course["credits"]
    assert loads and max(loads.values()) <= 7 and set(loads) <= set(plan["terms"][1:])


def test_unconfirmed_and_unsupported_versions_return_distinct_warnings_and_write_nothing(client, student, post_headers, app):
    student()
    before = rows(app)
    unconfirmed = generate(client, post_headers)
    assert unconfirmed.status_code == 200 and unconfirmed.json["status"] == "succeeded"
    assert "program_version_unconfirmed" in unconfirmed.json["warnings"] and planned(unconfirmed.json["plan"]) == {}
    unsupported = generate(client, post_headers, catalogTerm="Fall 2030")
    assert "program_version_unavailable" in unsupported.json["warnings"] and planned(unsupported.json["plan"]) == {}
    assert unsupported.json["plan"]["catalogTerm"] is None
    assert rows(app) == before


def test_meeting_the_credit_goal_with_unmet_requirements_stays_visibly_incomplete(client, student, post_headers):
    student(courses=[work(f"OUTS {1000 + index}", credits=4) for index in range(6)], creditLoad=3, graduationTarget="Spring 2027")
    body = generate(client, post_headers, catalogTerm="Fall 2026").json
    assert body["plan"]["baseCredits"] == 24
    assert "requirements_incomplete" in body["warnings"]
    assert "graduation_target_unreachable" not in body["warnings"]
    groups = [item for item in body["plan"]["requirementProgress"] if item["parentId"] is None]
    assert any(group["projectedStatus"] == "unsatisfied" for group in groups)


def test_unknown_major_generates_no_placements_with_a_warning(client, student, post_headers, app):
    student(major="Undeclared synthetic")
    body = generate(client, post_headers).json
    assert (planned(body["plan"]), body["warnings"]) == ({}, ["program_requirements_unavailable"])
    assert rows(app)[0] == []


def test_engine_failure_returns_generation_failed_without_partial_writes(client, student, post_headers, app, monkeypatch):
    student()
    generate(client, post_headers, catalogTerm="Fall 2026")
    before = rows(app)

    def explode(*args, **kwargs):
        raise RuntimeError("synthetic engine failure")

    monkeypatch.setattr("app.services.plan.generate_plan", explode)
    response = generate(client, post_headers, catalogTerm="Fall 2026")
    assert (response.status_code, response.json) == (500, {"error": "Plan generation failed", "code": "generation_failed"})
    assert rows(app) == before


def test_generating_for_one_user_never_changes_another_users_plan(client, student, post_headers, make_user, app):
    first = student()
    generate(client, post_headers, catalogTerm="Fall 2026")
    first_rows = [row for row in rows(app)[0]]
    student()
    generate(client, post_headers, catalogTerm="Fall 2026", dryRun=False)
    student(user=first)
    assert {course["code"] for course in client.get("/api/v1/plan").json["courses"] if course["status"] == "plan"} == \
        {code for _, code, _, _ in first_rows}


def test_full_flow_from_sign_in_to_a_reloaded_plan(app, client, monkeypatch, post_headers, catalog, program_files, today):
    claims = {"sub": "synthetic-flow", "email": "synthetic-flow@umn.edu", "email_verified": True, "name": "Synthetic Student"}
    monkeypatch.setattr("app.core.google_auth.id_token.verify_oauth2_token", lambda *a, **kw: claims)
    assert client.post("/api/v1/auth/google", json={"credential": "synthetic"}, headers=post_headers).status_code == 200
    profile = {"name": "Synthetic Student", "major": MINI, "creditLoad": 9, "graduationTarget": "Fall 2028"}
    assert client.put("/api/v1/profile", json=profile, headers=post_headers).status_code == 200
    courses = {"courses": [work("MINI 1101", credits=3), work("OUTS 1001", credits=4)], "skipped": False}
    assert client.put("/api/v1/coursework", json=courses, headers=post_headers).status_code == 200
    generated = client.post("/api/v1/plans/generate", json={"catalogTerm": "Fall 2026"}, headers=post_headers)
    assert generated.status_code == 200 and planned(generated.json["plan"])
    summary = client.get("/api/v1/summary").json
    assert (summary["creditsCompleted"], summary["creditsTotal"], summary["gpa"]) == (7, 24, 4.0)
    assert client.get("/api/v1/plan").json == generated.json["plan"]
    edit = client.put("/api/v1/plan", json={"changes": [{"code": "CSCI 1001", "status": "plan", "term": "Fall 2027"}]}, headers=post_headers)
    assert edit.status_code == 200
    saved_plan, saved_summary = edit.json, client.get("/api/v1/summary").json
    cookie = client.get_cookie("gp_session")
    fresh = app.test_client()
    fresh.set_cookie("gp_session", cookie.value)
    assert fresh.get("/api/v1/plan").json == saved_plan
    assert fresh.get("/api/v1/summary").json == saved_summary
    assert next(course for course in saved_plan["courses"] if course["code"] == "CSCI 1001")["requirement"] == "Elective"


@pytest.mark.parametrize("audit, expected", [
    (None, ["CSCI 1006", "MATH 2010"]),  # no audit: catalog tags only, every slot category counts
    ({"required": ["Global Perspectives"], "covered": []}, ["CSCI 1006"]),  # not listed by APAS: not required
    ({"required": ["Global Perspectives", "Technology and Society"], "covered": ["Global Perspectives", "Technology and Society"]}, []),
])
def test_apas_liberal_education_status_decides_which_slots_need_courses(client, student, post_headers, tmp_path, monkeypatch, audit, expected):
    import json
    from app.extensions import db
    from app.models import CatalogCourse, Transcript

    user = student(graduationTarget="Spring 2029")
    for code, category in (("CSCI 1006", "Global Perspectives"), ("MATH 2010", "Technology and Society")):
        row = db.session.query(CatalogCourse).filter_by(course_code=code).one()
        row.le_attributes, row.prerequisite_status = category, "none"
    if audit:
        db.session.add(Transcript(id="t-le", user_id=user.id, file_name="apas.pdf", status="parsed",
                                  le_required=json.dumps(audit["required"]), le_covered=json.dumps(audit["covered"])))
    db.session.commit()
    (tmp_path / "mini-synthetic.json").write_text(json.dumps({"terms": [{"year": 2, "season": "Spring", "items": [
        {"kind": "le", "categories": ["Global Perspectives"], "label": "Global Perspectives"},
        {"kind": "le", "categories": ["Technology and Society"], "label": "Technology and Society"}]}]}), encoding="utf-8")
    monkeypatch.setenv("SAMPLE_PLAN_DATA_PATH", str(tmp_path))
    plan = generate(client, post_headers, catalogTerm="Fall 2026", dryRun=True).json["plan"]
    assert sorted(c["code"] for c in plan["courses"] if c.get("slot")) == expected
