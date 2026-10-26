"""Transaction boundary and response serialization; never infer academic validity."""

from app.repositories.academic_profile import read_snapshot, replace_snapshot
from app.schemas.academic_profile import SEASONS


def stored_term(row, prefix):
    year = getattr(row, prefix + '_year')
    if year is None:
        return None
    return {'year': year, 'season': getattr(row, prefix + '_season')}


def serialize_snapshot(records):
    student, courses, extra = records
    courses.sort(key=lambda row: (row.course_code, row.term_year or 0,
                                  SEASONS.get(row.term_season, 0)))
    extra.sort(key=lambda row: row.reference)
    return {
        'profile': {
            'program': student.program, 'catalog_year': student.catalog_year,
            'current_term': stored_term(student, 'current_term'),
            'target_graduation_term': stored_term(student, 'target_graduation_term'),
            'max_credits_per_term': float(student.max_credits_per_term),
        },
        'course_records': [{
            'course_code': row.course_code, 'status': row.status, 'term': stored_term(row, 'term'),
            'credits': float(row.credits), 'earned_credits': float(row.earned_credits),
            'grade': row.grade, 'credit_source': row.credit_source,
            'grading_basis': row.grading_basis, 'credit_reference': row.credit_reference,
        } for row in courses],
        'extra_credits': [{
            'reference': row.reference, 'source': row.source, 'earned_credits': float(row.earned_credits),
            'usage_confirmed': row.usage_confirmed, 'confirmed_usage': row.confirmed_usage,
        } for row in extra],
    }


def save_profile(session_factory, snapshot):
    # Commit happens only after every database operation and serialization succeeds.
    with session_factory.begin() as session:
        replace_snapshot(session, snapshot)
        result = serialize_snapshot(read_snapshot(session))
    return result


def get_profile(session_factory):
    with session_factory.begin() as session:
        records = read_snapshot(session)
        return None if records is None else serialize_snapshot(records)
