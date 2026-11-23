from decimal import Decimal, ROUND_HALF_UP

# UMN Twin Cities published A-F scale, verified 2026-11-07:
# https://onestop.umn.edu/academics/transcripts-and-grades/grades
GRADE_POINTS = {
    "A": 4.000, "A-": 3.667, "B+": 3.333, "B": 3.000, "B-": 2.667,
    "C+": 2.333, "C": 2.000, "C-": 1.667, "D+": 1.333, "D": 1.000, "F": 0.000,
}


def calculate_summary(courses, *, major="", program=None):
    total = program["totalCredits"] if program else 120
    source = ""
    if courses:
        source = "Based on your transcript" if any(course["source"] == "transcript" for course in courses) else "Based on the courses you entered"
    completed_credits = sum((Decimal(str(course["credits"])) for course in courses
                             if course["status"] == "done" and course.get("grade") not in {"F", "N", "W", "I"}), Decimal(0))
    graded = [course for course in courses if course["status"] == "done" and course.get("grade") in GRADE_POINTS]
    graded_credits = sum((Decimal(str(course["credits"])) for course in graded), Decimal(0))
    quality_points = sum((Decimal(str(course["credits"])) * Decimal(str(GRADE_POINTS[course["grade"]])) for course in graded), Decimal(0))
    gpa = float((quality_points / graded_credits).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) if graded_credits else None
    percent = min(100, int((completed_credits * 100 / Decimal(str(total))).quantize(Decimal("1"), rounding=ROUND_HALF_UP))) if courses else None
    return {
        "gpa": gpa, "gradedCredits": float(graded_credits), "creditsCompleted": float(completed_credits), "creditsTotal": total,
        "percentComplete": percent, "program": major, "source": source,
    }
