"""Coursework a user has completed or is taking.

One table holds two kinds of rows:

- kind = 'course': credit tied to a specific course code, e.g. CSCI 1133
  taken at UMN, or AP Calculus counted as MATH 1271.
- kind = 'unmapped_credit': credit that does not map to a course, e.g. 6 IB
  credits that only count toward total credits. These have no course_code and
  are identified by `reference`.

Constraints are written to work on both SQLite (local development) and
PostgreSQL.
"""

from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db

KINDS = ("course", "unmapped_credit")
STATUSES = ("completed", "in_progress")
CREDIT_SOURCES = ("institutional", "AP", "IB", "transfer")
SEASONS = ("Spring", "Summer", "Fall")
GRADES = ("A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "F", "S", "N")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class CourseRecord(db.Model):
    __tablename__ = "course_records"
    __table_args__ = (
        CheckConstraint(_in("kind", KINDS), name="ck_course_records_kind"),
        CheckConstraint(_in("status", STATUSES), name="ck_course_records_status"),
        CheckConstraint(_in("credit_source", CREDIT_SOURCES), name="ck_course_records_source"),
        # A course row has a code; an unmapped credit has none and needs a reference instead.
        CheckConstraint(
            "(kind = 'course' AND course_code IS NOT NULL) OR "
            "(kind = 'unmapped_credit' AND course_code IS NULL AND reference IS NOT NULL)",
            name="ck_course_records_kind_fields",
        ),
        # Year and season are set together or not at all (AP/IB/transfer may have no term).
        # The explicit IS NOT NULL matters: "NULL IN (...)" is UNKNOWN, and CHECK lets UNKNOWN pass.
        CheckConstraint(
            "(term_year IS NULL AND term_season IS NULL) OR "
            "(term_year IS NOT NULL AND term_season IS NOT NULL AND " + _in("term_season", SEASONS) + ")",
            name="ck_course_records_term",
        ),
        # Courses taken at UMN always have a term.
        CheckConstraint(
            "credit_source <> 'institutional' OR term_year IS NOT NULL",
            name="ck_course_records_institutional_term",
        ),
        CheckConstraint(
            "credits >= 0 AND earned_credits >= 0 AND earned_credits <= credits",
            name="ck_course_records_credits",
        ),
        CheckConstraint("grade IS NULL OR " + _in("grade", GRADES), name="ck_course_records_grade"),
        # Failing grades earn no credit.
        CheckConstraint(
            "grade IS NULL OR grade NOT IN ('F', 'N') OR earned_credits = 0",
            name="ck_course_records_failed_credits",
        ),
        # An in-progress row is a real UMN course this term: nothing earned, no grade yet.
        CheckConstraint(
            "status <> 'in_progress' OR (kind = 'course' AND credit_source = 'institutional' "
            "AND term_year IS NOT NULL AND earned_credits = 0 AND grade IS NULL)",
            name="ck_course_records_in_progress",
        ),
        # Only unmapped credit can record what it was later used for.
        CheckConstraint(
            "kind = 'unmapped_credit' OR confirmed_usage IS NULL",
            name="ck_course_records_usage",
        ),
        # The same credit allocation (e.g. one AP exam result) cannot be recorded twice.
        # NULL references are allowed to repeat.
        UniqueConstraint("user_id", "reference", name="uq_course_records_reference"),
        # Same course in the same term twice is a duplicate; a retake in a different term is fine.
        Index(
            "uq_course_records_attempt",
            "user_id", "course_code", "term_year", "term_season",
            unique=True,
            sqlite_where=text("kind = 'course' AND term_year IS NOT NULL"),
            postgresql_where=text("kind = 'course' AND term_year IS NOT NULL"),
        ),
        # Without a term (AP/IB/transfer), a course can only be credited once.
        # NULLs never count as equal in a unique index, so this needs its own index.
        Index(
            "uq_course_records_termless",
            "user_id", "course_code",
            unique=True,
            sqlite_where=text("kind = 'course' AND term_year IS NULL"),
            postgresql_where=text("kind = 'course' AND term_year IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    course_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    credit_source: Mapped[str] = mapped_column(String(16), nullable=False)
    term_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    term_season: Mapped[str | None] = mapped_column(String(6), nullable=True)
    credits: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    earned_credits: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    grade: Mapped[str | None] = mapped_column(String(2), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confirmed_usage: Mapped[str | None] = mapped_column(String(500), nullable=True)
