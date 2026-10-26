"""Opt-in tests against migrated PostgreSQL; every fixture transaction rolls back.

Run only against the dedicated local development database:
RUN_POSTGRES_MODEL_TESTS=true python -m pytest tests/test_academic_postgres.py -q
"""

import os

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError

from app.core.config import load_settings
from app.models import CourseRecord, ExtraCredit, StudentProfile

pytestmark = pytest.mark.skipif(
    os.environ.get('RUN_POSTGRES_MODEL_TESTS') != 'true',
    reason='Requires explicit opt-in to real PostgreSQL model checks.',
)


@pytest.fixture
def database():
    settings = load_settings()
    if settings.app_env != 'development' or settings.database_url.host not in {'127.0.0.1', 'localhost'}:
        pytest.fail('These rollback tests require a local development database.')
    engine = create_engine(settings.database_url)
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            # Explicit IDs avoid advancing sequences, and never overwrite data.
            assert connection.execute(select(StudentProfile.id).where(StudentProfile.id == 900001)).first() is None
            connection.execute(StudentProfile.__table__.insert().values(
                id=900001, program='Philosophy B.A.', catalog_year='Fall 2030',
                current_term_year=2030, current_term_season='Fall',
                target_graduation_term_year=2032, target_graduation_term_season='Spring',
                max_credits_per_term=16,
            ))
            yield connection
        finally:
            transaction.rollback()
    engine.dispose()


def course(**overrides):
    fields = dict(id=900101, student_id=900001, course_code='CSCI 1133',
                  status='completed', term_year=2025, term_season='Fall',
                  credits=4, earned_credits=4, grade='A',
                  credit_source='institutional', grading_basis='AF', credit_reference=None)
    return fields | overrides


def extra(**overrides):
    return dict(id=900201, student_id=900001, reference='TEST-IB-001', source='IB',
                earned_credits=6, usage_confirmed=False, confirmed_usage=None) | overrides


def reject(connection, table, fields, expected_constraint):
    with pytest.raises(IntegrityError) as error:
        with connection.begin_nested():
            connection.execute(table.insert().values(**fields))
    assert error.value.orig.diag.constraint_name == expected_constraint


def test_different_term_retake_and_unknown_grade_are_preserved(database):
    database.execute(CourseRecord.__table__.insert().values(**course()))
    database.execute(CourseRecord.__table__.insert().values(**course(
        id=900102, term_year=2026, term_season='Spring', grade=None)))
    assert database.execute(select(CourseRecord.id).where(CourseRecord.student_id == 900001)
                            .order_by(CourseRecord.id)).scalars().all() == [900101, 900102]


def test_same_attempt_cannot_change_source_to_evade_unique_key(database):
    database.execute(CourseRecord.__table__.insert().values(**course()))
    reject(database, CourseRecord.__table__, course(id=900102, credit_source='transfer'),
           'uq_course_attempt')


def test_null_term_is_unique_but_one_exam_can_map_to_different_courses(database):
    first = course(term_year=None, term_season=None, credit_source='IB', grade=None,
                   grading_basis=None, credit_reference='TEST-IB-002-CSCI')
    database.execute(CourseRecord.__table__.insert().values(**first))
    reject(database, CourseRecord.__table__, first | dict(id=900102, credit_reference=None),
           'uq_course_attempt')
    database.execute(CourseRecord.__table__.insert().values(**(first | dict(
        id=900103, course_code='MATH 1272', credit_reference='TEST-IB-002-MATH'))))


@pytest.mark.parametrize(('changes', 'constraint'), [
    ({'student_id': 900999}, 'fk_course_student'),
    ({'course_code': None}, None),
    ({'credits': -1, 'earned_credits': 0}, 'ck_course_credits'),
    ({'earned_credits': 5}, 'ck_course_credits'),
    ({'credits': 'NaN'}, 'ck_course_credits'),
    ({'status': 'in_progress'}, 'ck_course_in_progress'),
    ({'term_year': None, 'credit_source': 'transfer'}, 'ck_course_term'),
    ({'term_season': 'Winter'}, 'ck_course_term'),
    ({'term_year': None, 'term_season': None}, 'ck_course_institutional_term'),
    ({'grade': 'W'}, 'ck_course_grade'),
    ({'grade': 'T5'}, 'ck_course_grade'),
    ({'grade': 'S'}, 'ck_course_grade_basis'),
    ({'grade': 'F'}, 'ck_course_failed_credits'),
    ({'credit_source': 'IB'}, 'ck_course_exam_grade'),
])
def test_invalid_course_rows_rejected_by_postgresql(database, changes, constraint):
    reject(database, CourseRecord.__table__, course(**changes), constraint)


def test_specific_course_credit_reference_cannot_be_used_twice(database):
    database.execute(CourseRecord.__table__.insert().values(**course(credit_reference='TEST-ALLOCATION-1')))
    reject(database, CourseRecord.__table__, course(id=900102, course_code='MATH 1272',
           credit_reference='TEST-ALLOCATION-1'), 'uq_course_credit_reference')


def test_extra_reference_cannot_change_source_to_evade_unique_key(database):
    database.execute(ExtraCredit.__table__.insert().values(**extra()))
    reject(database, ExtraCredit.__table__, extra(id=900202, source='transfer'), 'uq_extra_reference')


@pytest.mark.parametrize(('changes', 'constraint'), [
    ({'student_id': 900999}, 'fk_extra_student'),
    ({'earned_credits': 0}, 'ck_extra_credits'),
    ({'usage_confirmed': True}, 'ck_extra_usage'),
    ({'confirmed_usage': 'Elective'}, 'ck_extra_usage'),
    ({'usage_confirmed': True, 'confirmed_usage': '  '}, 'ck_extra_usage'),
])
def test_invalid_extra_rows_rejected_by_postgresql(database, changes, constraint):
    reject(database, ExtraCredit.__table__, extra(**changes), constraint)


def test_invalid_graduation_order_rejected(database):
    with pytest.raises(IntegrityError) as error:
        with database.begin_nested():
            database.execute(StudentProfile.__table__.update().where(StudentProfile.id == 900001)
                             .values(target_graduation_term_year=2030, target_graduation_term_season='Summer'))
    assert error.value.orig.diag.constraint_name == 'ck_student_term_order'


def test_parent_deletion_cascades_to_children(database):
    database.execute(CourseRecord.__table__.insert().values(**course()))
    database.execute(ExtraCredit.__table__.insert().values(**extra()))
    database.execute(StudentProfile.__table__.delete().where(StudentProfile.id == 900001))
    assert database.execute(select(CourseRecord.id).where(CourseRecord.student_id == 900001)).first() is None
    assert database.execute(select(ExtraCredit.id).where(ExtraCredit.student_id == 900001)).first() is None
