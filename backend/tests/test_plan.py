"""Plan shape built from course_records, and GET /api/v1/plan."""

from datetime import date
from decimal import Decimal

from app.models import CourseRecord
from app.services.plan import build_plan, plan_terms
from tests.test_apas_parser import SAMPLE
from tests.test_transcripts_api import app, sign_in, upload  # noqa: F401  (fixture)


def no_catalog(_codes):
    return {}


def record(code, status, season, year, title="Some course"):
    return CourseRecord(
        kind="course", course_code=code, title=title, status=status,
        term_season=season, term_year=year, credits=Decimal("4"),
        earned_credits=Decimal("4") if status == "completed" else Decimal("0"),
        credit_source="institutional",
    )


def test_terms_run_from_current_term_to_graduation():
    assert plan_terms(("Fall", 2026), ("Spring", 2028)) == [
        "Completed", "Fall 2026", "Spring 2027", "Fall 2027", "Spring 2028",
    ]


def test_terms_without_graduation_target_cover_four_years():
    terms = plan_terms(("Fall", 2026), None)
    assert terms[1] == "Fall 2026" and terms[-1] == "Spring 2030" and len(terms) == 9


def test_completed_and_in_progress_courses():
    plan = build_plan([
        record("CSCI 1133", "completed", "Fall", 2025),
        record("CSCI 2021", "in_progress", "Fall", 2026),
    ], no_catalog, "Spring 2028", date(2026, 11, 2))

    assert plan["currentTerm"] == "Fall 2026"
    by_code = {c["code"]: c for c in plan["courses"]}
    assert (by_code["CSCI 1133"]["status"], by_code["CSCI 1133"]["term"]) == ("done", "Completed")
    assert (by_code["CSCI 2021"]["status"], by_code["CSCI 2021"]["term"]) == ("prog", "Fall 2026")
    assert by_code["CSCI 2021"]["requirement"] == "Major core"


def test_current_term_from_calendar_when_nothing_in_progress():
    plan = build_plan([], no_catalog, None, date(2027, 3, 1))
    assert plan["currentTerm"] == "Spring 2027"
    assert plan["courses"] == []


def test_endpoint_adds_catalog_details(app, monkeypatch):  # noqa: F811
    client = app.test_client()
    assert client.get("/api/v1/plan").status_code == 401

    sign_in(client)
    upload(client, SAMPLE, monkeypatch)
    plan = client.get("/api/v1/plan").get_json()

    assert plan["terms"][0] == "Completed"
    assert plan["currentTerm"] == "Fall 2026"
    csci2021 = next(c for c in plan["courses"] if c["code"] == "CSCI 2021")
    # Offered terms and prerequisites come from backend/data/courses.db.
    assert csci2021["offered"] == ["Fall", "Spring"]
    assert csci2021["prereqs"]
