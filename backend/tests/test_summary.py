import importlib
import importlib.util
import pytest


def test_grade_points_match_umn_published_scale():
    assert importlib.util.find_spec("app.services.summary") is not None, "Missing summary service"
    module = importlib.import_module("app.services.summary")
    assert module.GRADE_POINTS == {
        "A": 4.000, "A-": 3.667, "B+": 3.333, "B": 3.000, "B-": 2.667,
        "C+": 2.333, "C": 2.000, "C-": 1.667, "D+": 1.333, "D": 1.000, "F": 0.000,
    }


def test_empty_coursework_summary_has_explicit_missing_metrics():
    module = importlib.import_module("app.services.summary")
    assert hasattr(module, "calculate_summary"), "Missing summary calculation"
    assert module.calculate_summary([], major="Synthetic program") == {
        "gpa": None, "gradedCredits": 0, "creditsCompleted": 0, "creditsTotal": 120,
        "percentComplete": None, "program": "Synthetic program", "source": "",
    }


def row(grade="A", credits=3, status="done", source="manual"):
    return {"grade": grade, "credits": credits, "status": status, "source": source}


def test_gpa_is_credit_weighted_over_graded_done_courses_only():
    from app.services.summary import calculate_summary

    result = calculate_summary([row("A", 4), row("B+", 3), row("A", 8, "prog"), row("S", 4)])
    assert result["gpa"] == 3.71
    assert result["gradedCredits"] == 7


@pytest.mark.parametrize("grade,earned", [
    *[(grade, 3) for grade in ("A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "S", None)],
    *[(grade, 0) for grade in ("F", "N", "W", "I")],
])
def test_completed_credits_follow_grade_credit_rules(grade, earned):
    from app.services.summary import calculate_summary

    result = calculate_summary([row(grade)])
    assert result["creditsCompleted"] == earned
    if grade in {"S", "N", "W", "I", None}:
        assert result["gpa"] is None
        assert result["gradedCredits"] == 0


def test_in_progress_courses_never_count_as_completed_or_graded():
    from app.services.summary import calculate_summary

    result = calculate_summary([row(None, status="prog")])
    assert result["creditsCompleted"] == 0
    assert result["gpa"] is None
    assert result["gradedCredits"] == 0


@pytest.mark.parametrize("count,total,expected", [(25, 120, 63), (40, 120, 100), (41, 120, 100), (10, 60, 50)])
def test_completion_percentage_uses_program_total_rounds_and_caps(count, total, expected):
    import inspect
    from app.services.summary import calculate_summary

    assert "program" in inspect.signature(calculate_summary).parameters, "Missing program credit goal"
    result = calculate_summary([row(credits=3)] * count, program={"totalCredits": total})
    assert result["percentComplete"] == expected
    assert result["creditsTotal"] == total


@pytest.mark.parametrize("sources,expected", [
    (["manual"], "Based on the courses you entered"),
    (["transcript"], "Based on your transcript"),
    (["manual", "transcript"], "Based on your transcript"),
])
def test_summary_source_describes_persisted_provenance(sources, expected):
    from app.services.summary import calculate_summary

    assert calculate_summary([row(source=source) for source in sources])["source"] == expected


def test_summary_api_returns_empty_metrics_for_signed_in_user(client, make_user, login_as):
    login_as(make_user())
    response = client.get("/api/v1/summary")
    assert response.status_code == 200
    assert response.json == {"gpa": None, "gradedCredits": 0, "creditsCompleted": 0,
                            "creditsTotal": 120, "percentComplete": None, "program": "", "source": ""}


def test_summary_api_uses_only_signed_in_users_coursework(client, make_user, login_as, post_headers):
    first, second = make_user(), make_user()
    course = {"code": "CSCI 1001", "title": "Synthetic course", "credits": 4,
              "status": "done", "grade": "A-", "term": None}
    login_as(first)
    assert client.put("/api/v1/profile", json={"major": "Synthetic program"}, headers=post_headers).status_code == 200
    assert client.put("/api/v1/coursework", json={"courses": [course], "skipped": False}, headers=post_headers).status_code == 200
    expected = {"gpa": 3.67, "gradedCredits": 4, "creditsCompleted": 4, "creditsTotal": 120,
                "percentComplete": 3, "program": "Synthetic program", "source": "Based on the courses you entered"}
    assert client.get("/api/v1/summary").json == expected
    login_as(second)
    assert client.get("/api/v1/summary").json["creditsCompleted"] == 0
    assert client.put("/api/v1/coursework", json={"courses": [{**course, "grade": "F", "credits": 2}], "skipped": False}, headers=post_headers).status_code == 200
    own = client.get("/api/v1/summary").json
    assert (own["gpa"], own["gradedCredits"], own["creditsCompleted"], own["percentComplete"], own["program"]) == (0, 2, 0, 0, "")
    login_as(first)
    assert client.get("/api/v1/summary").json == expected


def confirm_catalog_term(user, term):
    from app.extensions import db
    from app.models import Plan

    db.session.add(Plan(user_id=user.id, catalog_term=term))
    db.session.commit()


def test_summary_uses_the_confirmed_program_versions_total_credits(client, make_user, login_as, post_headers, program_files):
    user = make_user()
    login_as(user)
    assert client.put("/api/v1/profile", json={"major": "Rich Synthetic B.S."}, headers=post_headers).status_code == 200
    course = {"code": "TEST 1001", "title": "Synthetic", "credits": 3, "status": "done", "grade": "A", "term": None}
    assert client.put("/api/v1/coursework", json={"courses": [course], "skipped": False}, headers=post_headers).status_code == 200
    assert client.get("/api/v1/summary").json["creditsTotal"] == 120
    confirm_catalog_term(user, "Fall 2026")
    summary = client.get("/api/v1/summary").json
    assert (summary["creditsTotal"], summary["percentComplete"]) == (30, 10)


def test_summary_keeps_the_default_total_for_unknown_or_unavailable_program_versions(client, make_user, login_as, post_headers, program_files):
    user = make_user()
    login_as(user)
    client.put("/api/v1/profile", json={"major": "Rich Synthetic B.S."}, headers=post_headers)
    confirm_catalog_term(user, "Fall 2030")
    assert client.get("/api/v1/summary").json["creditsTotal"] == 120
    client.put("/api/v1/profile", json={"major": "Unknown program"}, headers=post_headers)
    assert client.get("/api/v1/summary").json["creditsTotal"] == 120
