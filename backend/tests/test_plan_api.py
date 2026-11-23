"""Plan read/write API against migrated SQLite, the synthetic catalog and synthetic program files."""
import json
import shutil
from pathlib import Path

import pytest

MINI = "Mini Synthetic B.S."
FIXTURES = Path(__file__).parent / "fixtures" / "programs"


@pytest.fixture
def planner(client, make_user, login_as, post_headers, catalog, program_files, today):
    def setup(major=MINI, courses=(), user=None):
        user = user or make_user()
        login_as(user)
        assert client.put("/api/v1/profile", json={"major": major}, headers=post_headers).status_code == 200
        if courses:
            body = {"courses": list(courses), "skipped": False}
            assert client.put("/api/v1/coursework", json=body, headers=post_headers).status_code == 200
        return user
    return setup


def put(client, headers, changes, **extra):
    return client.put("/api/v1/plan", json={"changes": changes, **extra}, headers=headers)


def by_code(plan):
    return {course["code"]: course for course in plan["courses"]}


def test_current_courses_can_move_out_and_back_with_credit_edits(client, planner, post_headers):
    planner(courses=[work("MINI 1101", "prog", term="Fall 2026", credits=4)])
    moved = put(client, post_headers, [{"code": "MINI 1101", "status": "plan", "term": "Spring 2027"}], catalogTerm="Fall 2026")
    assert moved.status_code == 200
    assert by_code(moved.json)["MINI 1101"]["status"] == "plan"
    assert client.get("/api/v1/coursework").json["courses"] == []

    current = put(client, post_headers, [{"code": "MINI 1101", "status": "prog", "term": "Fall 2026", "credits": 4}])
    assert current.status_code == 200
    assert by_code(current.json)["MINI 1101"]["credits"] == 4
    assert client.get("/api/v1/coursework").json["courses"][0]["status"] == "prog"
    edited = put(client, post_headers, [{"code": "MINI 1101", "status": "prog", "term": "Fall 2026", "credits": 2}])
    assert edited.status_code == 200
    assert by_code(client.get("/api/v1/plan").json)["MINI 1101"]["credits"] == 2
    assert put(client, post_headers, [{"code": "MINI 1101", "status": "avail", "term": None}]).status_code == 200
    assert client.get("/api/v1/coursework").json["courses"] == []


def test_current_credit_corrections_do_not_require_a_catalog_selection(client, planner, post_headers):
    planner(courses=[work("CSCI 1001", "prog", term="Fall 2026", credits=4)])
    response = put(client, post_headers, [{"code": "CSCI 1001", "status": "prog", "term": "Fall 2026", "credits": 2}])
    assert response.status_code == 200
    assert by_code(response.json)["CSCI 1001"]["credits"] == 2


@pytest.mark.parametrize("credits", [True, 0, 13, 2.25, "3"])
def test_current_credit_validation_preserves_enrollment(client, planner, post_headers, credits):
    planner(courses=[work("MINI 1101", "prog", term="Fall 2026", credits=4)])
    response = put(client, post_headers, [{"code": "MINI 1101", "status": "prog", "term": "Fall 2026", "credits": credits}], catalogTerm="Fall 2026")
    assert response.status_code == 400
    assert client.get("/api/v1/coursework").json["courses"][0]["credits"] == 4


def test_moving_current_prerequisite_after_dependent_is_atomic(client, planner, post_headers):
    planner(courses=[work("MINI 1101", "prog", term="Fall 2026")])
    assert put(client, post_headers, [{"code": "MINI 1102", "status": "plan", "term": "Spring 2027"}], catalogTerm="Fall 2026").status_code == 200
    response = put(client, post_headers, [{"code": "MINI 1101", "status": "plan", "term": "Fall 2027"}])
    assert response.status_code == 409
    assert client.get("/api/v1/coursework").json["courses"][0]["status"] == "prog"


def test_failed_attempt_is_preserved_when_current_retake_moves(client, planner, post_headers):
    planner(courses=[work("MINI 1101", grade="F"), work("MINI 1101", "prog", term="Fall 2026")])
    response = put(client, post_headers, [{"code": "MINI 1101", "status": "plan", "term": "Spring 2027"}], catalogTerm="Fall 2026")
    assert response.status_code == 200
    assert by_code(response.json)["MINI 1101"]["status"] == "plan"
    rows = client.get("/api/v1/coursework").json["courses"]
    assert len(rows) == 1 and rows[0]["grade"] == "F"
    assert put(client, post_headers, [{"code": "MINI 1101", "status": "plan", "term": "Fall 2027"}]).status_code == 200


def test_current_enrollment_does_not_overwrite_a_same_term_failed_attempt(client, planner, post_headers):
    planner(courses=[work("MINI 1101", grade="F", term="Fall 2026")])
    response = put(client, post_headers, [{"code": "MINI 1101", "status": "prog", "term": "Fall 2026"}], catalogTerm="Fall 2026")
    assert response.status_code == 409
    assert client.get("/api/v1/coursework").json["courses"][0]["grade"] == "F"


def test_current_suggestion_cannot_use_a_same_semester_in_progress_prerequisite(client, planner, post_headers):
    planner(courses=[work("MINI 1101", "prog", term="Fall 2026")])
    response = put(client, post_headers, [{"code": "MINI 1102", "status": "plan", "term": "Fall 2026"}], catalogTerm="Fall 2026")
    assert response.status_code == 409
    assert response.json["violations"][0]["reason"] == "prerequisite_not_before"


def work(code, status="done", grade="A", term="Fall 2025", credits=3):
    return {"code": code, "title": f"Synthetic {code}", "credits": credits, "status": status,
            "grade": None if status == "prog" else grade, "term": term}


def stored(app):
    from app.extensions import db
    from app.models import Plan, PlanCourse
    return ([(row.code, row.term, row.source) for row in db.session.query(PlanCourse).order_by(PlanCourse.code)],
            [row.catalog_term for row in db.session.query(Plan)])


def test_plan_requires_authentication_and_trusted_origin(client, planner):
    planner()
    client.delete_cookie("gp_session")
    assert client.get("/api/v1/plan").status_code == 401
    planner()
    assert client.put("/api/v1/plan", json={"changes": []}, headers={"Origin": "https://evil.invalid"}).status_code == 403


def test_unconfirmed_version_lists_supported_terms_without_applying_requirements(client, planner):
    planner()
    plan = client.get("/api/v1/plan").json
    assert plan["terms"][:3] == ["Completed", "Fall 2026", "Spring 2027"]
    assert (plan["currentTerm"], plan["catalogTerm"], plan["availableCatalogTerms"]) == ("Fall 2026", None, ["Fall 2026"])
    assert plan["requirementProgress"] == [] and plan["courses"] == []
    assert "program_version_unconfirmed" in plan["warnings"]


def test_unknown_major_has_no_versions_and_a_clear_warning(client, planner):
    planner(major="Undeclared synthetic")
    plan = client.get("/api/v1/plan").json
    assert (plan["catalogTerm"], plan["availableCatalogTerms"], plan["requirementProgress"]) == (None, [], [])
    assert plan["warnings"] == ["program_requirements_unavailable"]


def test_confirming_a_version_shows_program_options_and_progress_and_persists(client, planner, post_headers, app):
    planner()
    response = put(client, post_headers, [], catalogTerm="Fall 2026")
    assert response.status_code == 200
    courses = by_code(response.json)
    assert courses["MINI 1101"]["status"] == "avail"
    assert courses["MINI 1002"]["status"] == "block" and courses["MINI 1002"]["lockReason"]
    assert response.json["requirementProgress"][0]["id"] == "core"
    assert client.get("/api/v1/plan").json["catalogTerm"] == "Fall 2026"
    assert stored(app) == ([], ["Fall 2026"])


def test_coursework_statuses_terms_and_base_credits(client, planner, post_headers):
    planner(courses=[work("MINI 1101", credits=4), work("MINI 1102", "prog", term="Fall 2026", credits=4),
                     work("OUTS 1001"), work("OUTS 1002", grade="F"), work("OUTS 1003", grade="W")])
    plan = put(client, post_headers, [], catalogTerm="Fall 2026").json
    courses = by_code(plan)
    assert (courses["MINI 1101"]["status"], courses["MINI 1101"]["term"], courses["MINI 1101"]["credits"]) == ("done", "Completed", 4)
    assert (courses["MINI 1102"]["status"], courses["MINI 1102"]["term"]) == ("prog", "Fall 2026")
    assert "OUTS 1001" not in courses
    assert plan["baseCredits"] == 3


def test_course_fields_come_from_versioned_metadata(client, planner, post_headers):
    planner()
    courses = by_code(put(client, post_headers, [], catalogTerm="Fall 2026").json)
    math = courses["MINI 2001"]
    assert (math["title"], math["credits"], math["offered"], math["requirement"]) == ("Mini math", 3, ["Spring"], "Math and stats")
    assert (math["prereqs"], math["concurrent"], math["professors"], math["metadataSource"]) == (["MINI 1001", "MINI 1101"], [], [], "program")
    assert math["prerequisiteTree"] == {"type": "any_of", "requirements": [
        {"type": "course", "course_code": "MINI 1001"}, {"type": "course", "course_code": "MINI 1101"}]}
    assert courses["MINI 1101"]["prerequisiteTree"] is None
    assert courses["MATH 3101"]["metadataWarnings"] == ["offered_terms_unverified"]
    assert courses["MINI 3001"]["requirement"] == "Elective"


def test_put_adds_moves_and_removes_supplemental_program_courses(client, planner, post_headers, app):
    planner()
    added = put(client, post_headers, [{"code": "MINI 1101", "status": "plan", "term": "Spring 2027"}], catalogTerm="Fall 2026")
    assert added.status_code == 200
    assert by_code(added.json)["MINI 1101"]["status"] == "plan"
    assert stored(app)[0] == [("MINI 1101", "Spring 2027", "user")]
    moved = put(client, post_headers, [{"code": "MINI 1101", "status": "plan", "term": "Fall 2027"}])
    assert by_code(moved.json)["MINI 1101"]["term"] == "Fall 2027"
    removed = put(client, post_headers, [{"code": "MINI 1101", "status": "avail", "term": None}])
    assert by_code(removed.json)["MINI 1101"]["status"] == "avail"
    assert by_code(client.get("/api/v1/plan").json)["MINI 1101"]["status"] == "avail"
    assert stored(app)[0] == []


def test_put_adds_a_catalog_only_course_as_an_elective_with_reload_warnings(client, planner, post_headers):
    planner()
    response = put(client, post_headers, [{"code": "CSCI 1001", "status": "plan", "term": "Fall 2027"}], catalogTerm="Fall 2026")
    assert response.status_code == 200
    course = by_code(client.get("/api/v1/plan").json)["CSCI 1001"]
    assert (course["status"], course["term"], course["requirement"], course["metadataSource"]) == ("plan", "Fall 2027", "Elective", "catalog")
    assert "catalog_version_unverified" in course["metadataWarnings"]


def test_unknown_major_can_save_catalog_only_plans_without_a_version(client, planner, post_headers, app):
    planner(major="Undeclared synthetic")
    response = put(client, post_headers, [{"code": "CSCI 1001", "status": "plan", "term": "Fall 2027"}])
    assert response.status_code == 200 and response.json["catalogTerm"] is None
    assert stored(app) == ([("CSCI 1001", "Fall 2027", "user")], [None])


@pytest.mark.parametrize("body", [
    {"changes": [{"code": "MINI 1101", "status": "plan", "term": "Spring 2027", "extra": 1}]},
    {"changes": [{"code": "MINI 1101", "status": "done", "term": "Spring 2027"}]},
    {"changes": [{"code": "MINI 1101", "status": "plan", "term": "Completed"}]},
    {"changes": [{"code": "MINI 1101", "status": "plan", "term": "Spring 2026"}]},
    {"changes": [{"code": "MINI 1101", "status": "plan", "term": "Fall 2040"}]},
    {"changes": [{"code": "MINI 1101", "status": "plan", "term": None}]},
    {"changes": [{"code": "MINI 1101", "status": "avail", "term": "Spring 2027"}]},
    {"changes": [{"code": "bad", "status": "plan", "term": "Spring 2027"}]},
    {"changes": {}}, {"changes": [], "unexpected": True}, [], {"changes": [], "catalogTerm": 5},
])
def test_put_rejects_invalid_changes_without_writing(client, planner, post_headers, app, body):
    planner()
    put(client, post_headers, [{"code": "MINI 1101", "status": "plan", "term": "Spring 2027"}], catalogTerm="Fall 2026")
    before = stored(app)
    response = client.put("/api/v1/plan", json=body, headers=post_headers)
    assert response.status_code == 400 and response.json["code"] == "invalid_change"
    assert stored(app) == before


def test_put_rejects_codes_unknown_to_catalog_and_program(client, planner, post_headers, app):
    planner()
    response = put(client, post_headers, [{"code": "ZZZZ 9999", "status": "plan", "term": "Spring 2027"}], catalogTerm="Fall 2026")
    assert (response.status_code, response.json["code"]) == (404, "unknown_course")
    assert stored(app) == ([], [])


def test_put_reports_schedule_violations_atomically(client, planner, post_headers, app):
    planner(courses=[work("MINI 1001")])
    put(client, post_headers, [], catalogTerm="Fall 2026")
    response = put(client, post_headers, [
        {"code": "MINI 1101", "status": "plan", "term": "Spring 2027"},
        {"code": "MINI 2001", "status": "plan", "term": "Fall 2027"},
        {"code": "MINI 1102", "status": "plan", "term": "Spring 2027"},
        {"code": "MINI 1002", "status": "plan", "term": "Fall 2027"},
        {"code": "MINI 1001", "status": "plan", "term": "Fall 2027"},
    ])
    assert (response.status_code, response.json["code"]) == (409, "plan_invalid")
    violations = response.json["violations"]
    assert {"code": "MINI 2001", "reason": "not_offered_in_season", "detail": "Fall"} in violations
    assert {"code": "MINI 1102", "reason": "prerequisite_not_before", "detail": "MINI 1101"} in violations
    assert {"code": "MINI 1002", "reason": "course_metadata_unavailable", "detail": "course_metadata_unavailable"} in violations
    assert {"code": "MINI 1001", "reason": "locked_course", "detail": "done"} in violations
    assert stored(app) == ([], ["Fall 2026"])


def test_moving_a_prerequisite_later_is_rejected_naming_the_dependent(client, planner, post_headers):
    planner()
    assert put(client, post_headers, [{"code": "MINI 1101", "status": "plan", "term": "Spring 2027"},
                                      {"code": "MINI 1102", "status": "plan", "term": "Fall 2027"}], catalogTerm="Fall 2026").status_code == 200
    response = put(client, post_headers, [{"code": "MINI 1101", "status": "plan", "term": "Fall 2028"}])
    assert response.status_code == 409
    assert response.json["violations"] == [{"code": "MINI 1102", "reason": "prerequisite_not_before", "detail": "MINI 1101"}]


def test_known_program_saves_require_a_confirmed_supported_version(client, planner, post_headers, app):
    planner()
    change = [{"code": "MINI 1101", "status": "plan", "term": "Spring 2027"}]
    unconfirmed = put(client, post_headers, change)
    assert (unconfirmed.status_code, unconfirmed.json["code"]) == (400, "program_version_unconfirmed")
    unavailable = put(client, post_headers, change, catalogTerm="Fall 2030")
    assert (unavailable.status_code, unavailable.json["code"]) == (400, "program_version_unavailable")
    assert stored(app) == ([], [])


def test_changing_versions_keeps_saved_courses_and_uses_only_the_new_file(client, planner, post_headers, tmp_path, monkeypatch, app):
    from app.services import programs

    directory = tmp_path / "versions"
    directory.mkdir()
    shutil.copy(FIXTURES / "mini-synthetic--fall-2026.json", directory)
    second = json.loads((FIXTURES / "mini-synthetic--fall-2026.json").read_text(encoding="utf-8"))
    second.update(catalogTerm="Fall 2027", totalCredits=30)
    second["courseMetadata"] = {code: {**record, "catalogTerm": "Fall 2027"} for code, record in second["courseMetadata"].items()}
    second["courseMetadata"]["MINI 2001"]["title"] = "Mini math, second version"
    (directory / "mini-synthetic--fall-2027.json").write_text(json.dumps(second), encoding="utf-8")
    monkeypatch.setenv("PROGRAM_DATA_PATH", str(directory))
    programs.clear_program_cache()
    planner()
    put(client, post_headers, [{"code": "MINI 1101", "status": "plan", "term": "Spring 2027"}], catalogTerm="Fall 2026")
    switched = put(client, post_headers, [], catalogTerm="Fall 2027").json
    assert switched["catalogTerm"] == "Fall 2027"
    assert switched["availableCatalogTerms"] == ["Fall 2026", "Fall 2027"]
    assert by_code(switched)["MINI 1101"]["status"] == "plan"
    assert by_code(switched)["MINI 2001"]["title"] == "Mini math, second version"
    assert stored(app) == ([("MINI 1101", "Spring 2027", "user")], ["Fall 2027"])


def test_users_never_see_or_change_each_others_plans(client, planner, post_headers, make_user, app):
    first = planner()
    put(client, post_headers, [{"code": "MINI 1101", "status": "plan", "term": "Spring 2027"}], catalogTerm="Fall 2026")
    planner()
    other = client.get("/api/v1/plan").json
    assert other["catalogTerm"] is None and other["courses"] == []
    confirmed = put(client, post_headers, [], catalogTerm="Fall 2026").json
    assert by_code(confirmed)["MINI 1101"]["status"] == "avail"
    assert put(client, post_headers, [{"code": "MINI 1101", "status": "avail", "term": None}], catalogTerm="Fall 2026").status_code == 200
    planner(user=first)
    assert by_code(client.get("/api/v1/plan").json)["MINI 1101"]["status"] == "plan"
