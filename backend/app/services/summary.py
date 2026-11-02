"""Dashboard numbers computed from course_records.

Nothing here is stored: the summary is recomputed on every request, so it can
never drift out of sync with the course rows it is based on.
"""

from decimal import ROUND_HALF_UP, Decimal

from app.models import CourseRecord

# UMN grade points (https://policy.umn.edu/education/gradingtranscripts).
GRADE_POINTS = {
    "A": Decimal("4.000"), "A-": Decimal("3.667"),
    "B+": Decimal("3.333"), "B": Decimal("3.000"), "B-": Decimal("2.667"),
    "C+": Decimal("2.333"), "C": Decimal("2.000"), "C-": Decimal("1.667"),
    "D+": Decimal("1.333"), "D": Decimal("1.000"),
    "F": Decimal("0.000"),
}

# Minimum credits for a UMN bachelor's degree. Per-program totals come later.
DEGREE_CREDITS = 120


def compute_summary(records: list[CourseRecord], program: str, has_audit: bool) -> dict:
    completed = [r for r in records if r.status == "completed"]
    in_progress = [r for r in records if r.status == "in_progress"]

    # GPA counts only A-F grades; S/N and transfer credit have no grade points.
    graded = [r for r in completed if r.grade in GRADE_POINTS]
    graded_credits = sum((r.credits for r in graded), Decimal(0))
    points = sum((GRADE_POINTS[r.grade] * r.credits for r in graded), Decimal(0))
    gpa = (
        float((points / graded_credits).quantize(Decimal("0.01"), ROUND_HALF_UP))
        if graded_credits else None
    )

    credits_completed = sum((r.earned_credits for r in completed), Decimal(0))
    credits_in_progress = sum((r.credits for r in in_progress), Decimal(0))
    percent = (
        min(100, round(credits_completed / DEGREE_CREDITS * 100)) if records else None
    )

    # Keys match the frontend's Summary type; creditsInProgress is extra.
    return {
        "gpa": gpa,
        "gradedCredits": float(graded_credits),
        "creditsCompleted": float(credits_completed),
        "creditsInProgress": float(credits_in_progress),
        "creditsTotal": DEGREE_CREDITS,
        "percentComplete": percent,
        "program": program,
        "source": "Based on your APAS" if has_audit else "No coursework yet",
    }
