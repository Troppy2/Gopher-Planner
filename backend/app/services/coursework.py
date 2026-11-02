"""Write parsed APAS courses into course_records.

An APAS audit is a full snapshot of a student's record, so an upload replaces
all of the user's course rows instead of merging with old ones. The caller
owns the transaction and commits.
"""

from sqlalchemy import delete

from app.extensions import db
from app.models import CourseRecord
from app.parsers.apas import ParsedCourse


def replace_courses(user_id: int, courses: list[ParsedCourse]) -> tuple[int, int]:
    """Replace the user's course rows. Returns (completed_count, in_progress_count)."""
    db.session.execute(
        delete(CourseRecord).where(
            CourseRecord.user_id == user_id,
            CourseRecord.kind == "course",
        )
    )

    for course in courses:
        completed = course.status == "completed"
        failed = course.grade in ("F", "N")
        db.session.add(CourseRecord(
            user_id=user_id,
            kind="course",
            status=course.status,
            course_code=course.course_code,
            title=course.title,
            credit_source=course.credit_source,
            term_year=course.term_year,
            term_season=course.term_season,
            credits=course.credits,
            earned_credits=course.credits if completed and not failed else 0,
            grade=course.grade,
        ))

    completed_count = sum(c.status == "completed" for c in courses)
    return completed_count, len(courses) - completed_count


def serialize_course_record(record: CourseRecord) -> dict:
    return {
        "id": record.id,
        "code": record.course_code,
        "title": record.title,
        "status": record.status,
        "creditSource": record.credit_source,
        "term": f"{record.term_season} {record.term_year}" if record.term_year else None,
        "credits": float(record.credits),
        "earnedCredits": float(record.earned_credits),
        "grade": record.grade,
    }
