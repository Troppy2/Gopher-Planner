"""Database-level rules for course_records, checked against in-memory SQLite."""

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.extensions import db
from app.models import CourseRecord, User


@pytest.fixture
def session():
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    db.Model.metadata.create_all(engine)
    with Session(engine) as s:
        user = User(google_sub="sub-1", email="student@umn.edu")
        s.add(user)
        s.commit()
        yield s


def course(**overrides):
    fields = dict(
        user_id=1, kind="course", status="completed", course_code="CSCI 1133",
        credit_source="institutional", term_year=2025, term_season="Fall",
        credits=Decimal("4"), earned_credits=Decimal("4"), grade="A",
    )
    return CourseRecord(**(fields | overrides))


def unmapped(**overrides):
    fields = dict(
        user_id=1, kind="unmapped_credit", status="completed", course_code=None,
        credit_source="IB", term_year=None, term_season=None,
        credits=Decimal("6"), earned_credits=Decimal("6"), reference="IB-HL-ECON",
    )
    return CourseRecord(**(fields | overrides))


def save(session, *records):
    session.add_all(records)
    session.commit()


def rejects(session, *records):
    with pytest.raises(IntegrityError):
        save(session, *records)
    session.rollback()


def test_valid_rows_save(session):
    save(
        session,
        course(),
        course(course_code="MATH 1271", credit_source="AP", term_year=None,
               term_season=None, grade=None, reference="AP-CALC-AB"),
        course(course_code="CSCI 2021", status="in_progress", term_year=2026,
               earned_credits=Decimal("0"), grade=None),
        unmapped(),
    )
    assert session.query(CourseRecord).count() == 4


def test_two_unmapped_credits_without_term_can_coexist(session):
    # The bug a naive merge would introduce: both rows have NULL code and term.
    save(session, unmapped(reference="IB-HL-ECON"), unmapped(reference="IB-SL-BIO"))


def test_retake_in_different_term_is_allowed(session):
    save(session, course(grade="F", earned_credits=Decimal("0")),
         course(term_year=2026, term_season="Spring"))


def test_same_course_same_term_is_rejected(session):
    rejects(session, course(), course())


def test_same_termless_course_twice_is_rejected(session):
    ap = dict(course_code="MATH 1271", credit_source="AP", term_year=None,
              term_season=None, grade=None)
    rejects(session, course(**ap, reference="AP-1"), course(**ap, reference="AP-2"))


def test_same_reference_twice_is_rejected(session):
    rejects(session, unmapped(), unmapped(earned_credits=Decimal("3")))


@pytest.mark.parametrize("bad", [
    dict(course_code=None),                                  # course without a code
    dict(term_year=None, term_season=None),                  # UMN course without a term
    dict(term_season=None),                                  # half a term
    dict(earned_credits=Decimal("5")),                       # earned more than attempted
    dict(grade="F"),                                         # failed but earned credit
    dict(grade="Z"),                                         # unknown grade
    dict(status="in_progress"),                              # in progress but already graded
    dict(confirmed_usage="LE: Social Sciences"),             # usage belongs to unmapped credit
])
def test_invalid_course_rows_are_rejected(session, bad):
    rejects(session, course(**bad))


@pytest.mark.parametrize("bad", [
    dict(course_code="ECON 1101"),                           # unmapped credit with a code
    dict(reference=None),                                    # unmapped credit needs a reference
    dict(status="in_progress", credit_source="institutional",
         term_year=2026, term_season="Fall",
         earned_credits=Decimal("0")),                       # unmapped credit cannot be in progress
])
def test_invalid_unmapped_rows_are_rejected(session, bad):
    rejects(session, unmapped(**bad))
