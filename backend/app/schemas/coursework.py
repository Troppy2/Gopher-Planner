"""Validation before any coursework mutation."""
import math
import re

CODE_PATTERN = re.compile(r"^[A-Z]{2,6} \d{4}[A-Z]?$")
TERM_PATTERN = re.compile(r"^(Fall|Spring|Summer) [1-9]\d{3}$")
GRADES = {"A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "F", "S", "N", "W", "I"}
FIELDS = {"code", "title", "credits", "status", "term", "grade", "source"}


class CourseworkValidationError(ValueError):
    pass


def validate_coursework(body):
    if not isinstance(body, dict) or set(body) - {"courses", "skipped"}:
        raise CourseworkValidationError("Expected a coursework object with known fields")
    courses = body.get("courses")
    if not isinstance(courses, list) or len(courses) > 300:
        raise CourseworkValidationError("courses must be a list with at most 300 entries")
    if not isinstance(body.get("skipped", False), bool):
        raise CourseworkValidationError("skipped must be a boolean")
    identities = set()
    for course in courses:
        if not isinstance(course, dict) or set(course) - FIELDS:
            raise CourseworkValidationError("Course entries must contain only known fields")
        if not isinstance(course.get("code"), str) or not CODE_PATTERN.fullmatch(course["code"]):
            raise CourseworkValidationError("Invalid course code")
        title = course.get("title")
        if not isinstance(title, str) or not 1 <= len(title) <= 255:
            raise CourseworkValidationError("title must contain 1 to 255 characters")
        credits = course.get("credits")
        if (isinstance(credits, bool) or not isinstance(credits, (int, float))
                or not 0 < credits <= 12 or not math.isfinite(credits) or credits * 2 % 1):
            raise CourseworkValidationError("credits must be positive, at most 12, in steps of 0.5")
        status = course.get("status")
        if not isinstance(status, str) or status not in {"done", "prog"}:
            raise CourseworkValidationError("status must be done or prog")
        term = course.get("term")
        if term is not None and (not isinstance(term, str) or not TERM_PATTERN.fullmatch(term)):
            raise CourseworkValidationError("Invalid academic term")
        grade = course.get("grade")
        if grade is not None and (not isinstance(grade, str) or grade not in GRADES):
            raise CourseworkValidationError("Invalid grade")
        if status == "prog" and grade is not None:
            raise CourseworkValidationError("In-progress courses cannot have a grade")
        identity = (course["code"], term)
        if identity in identities:
            raise CourseworkValidationError("Duplicate course and term")
        identities.add(identity)
    return {"courses": courses, "skipped": body.get("skipped", False)}
