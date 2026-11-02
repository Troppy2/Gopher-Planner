"""Summary math and the GET /api/v1/summary endpoint."""

from decimal import Decimal

from app.models import CourseRecord
from app.services.summary import compute_summary
from tests.test_apas_parser import SAMPLE
from tests.test_transcripts_api import app, sign_in, upload  # noqa: F401  (fixture)


def record(code, credits, grade, status="completed", source="institutional"):
    credits = Decimal(credits)
    done = status == "completed" and grade not in ("F", "N")
    return CourseRecord(
        course_code=code, credits=credits, grade=grade, status=status,
        credit_source=source, earned_credits=credits if done else Decimal(0),
    )


def test_gpa_weights_by_credits_and_skips_s_and_transfer():
    summary = compute_summary([
        record("CSCI 1133", "4", "A"),          # 4 x 4.000
        record("DNCE 3110", "2", "A-"),         # 2 x 3.667
        record("CSCI 1135", "1", "S"),          # no grade points
        record("MATH 1271", "4", None, source="IB"),
    ], program="Computer Science", has_audit=True)

    assert summary["gpa"] == 3.89                # (16 + 7.334) / 6
    assert summary["gradedCredits"] == 6.0
    assert summary["creditsCompleted"] == 11.0   # 4 + 2 + 1 + 4
    assert summary["percentComplete"] == 9       # 11 / 120
    assert summary["source"] == "Based on your APAS"


def test_failed_course_counts_in_gpa_but_earns_nothing():
    summary = compute_summary([
        record("CSCI 1133", "4", "A"),
        record("CSCI 1933", "4", "F"),
    ], program="", has_audit=True)
    assert summary["gpa"] == 2.0
    assert summary["creditsCompleted"] == 4.0


def test_in_progress_is_separate():
    summary = compute_summary([
        record("CSCI 2021", "4", None, status="in_progress"),
    ], program="", has_audit=True)
    assert summary["creditsCompleted"] == 0.0
    assert summary["creditsInProgress"] == 4.0
    assert summary["gpa"] is None


def test_no_coursework():
    summary = compute_summary([], program="", has_audit=False)
    assert (summary["gpa"], summary["percentComplete"]) == (None, None)
    assert summary["source"] == "No coursework yet"


def test_endpoint_uses_uploaded_audit(app, monkeypatch):  # noqa: F811
    client = app.test_client()
    assert client.get("/api/v1/summary").status_code == 401

    sign_in(client)
    upload(client, SAMPLE, monkeypatch)
    summary = client.get("/api/v1/summary").get_json()
    # SAMPLE: CSCI 1133 A (4), CSCI 1135 S (1), PHYS 1301W B+ (4), MATH 1271 IB (4)
    assert summary["gpa"] == 3.67
    assert summary["creditsCompleted"] == 13.0
    assert summary["creditsInProgress"] == 5.0
