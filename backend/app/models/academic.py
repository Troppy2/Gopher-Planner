"""Academic storage models, separate from future request/response schemas.

Row-local invariants and same-table uniqueness belong here. Comparing course
terms with a student's current term, or references across tables, uses
service validation inside the save transaction.
"""

from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


def required_text(column: str) -> str:
    return f"{column} = btrim({column}) AND length({column}) > 0"


def required_term(prefix: str) -> str:
    return (
        f"{prefix}_year BETWEEN 1 AND 9999 AND "
        f"{prefix}_season IN ('Spring', 'Summer', 'Fall')"
    )


class StudentProfile(Base):
    __tablename__ = 'student_profiles'
    __table_args__ = (
        CheckConstraint(required_text('program'), name='ck_student_program'),
        CheckConstraint(required_text('catalog_year'), name='ck_student_catalog_year'),
        CheckConstraint(required_term('current_term'), name='ck_student_current_term'),
        CheckConstraint(required_term('target_graduation_term'), name='ck_student_target_term'),
        CheckConstraint(
            "target_graduation_term_year > current_term_year OR "
            "(target_graduation_term_year = current_term_year AND "
            "CASE target_graduation_term_season WHEN 'Spring' THEN 1 WHEN 'Summer' THEN 2 ELSE 3 END "
            ">= CASE current_term_season WHEN 'Spring' THEN 1 WHEN 'Summer' THEN 2 ELSE 3 END)",
            name='ck_student_term_order',
        ),
        CheckConstraint('max_credits_per_term > 0 AND max_credits_per_term <= 9999.99',
                        name='ck_student_max_credits'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program: Mapped[str] = mapped_column(String(128), nullable=False)
    # Requirement-version label, not a course term or an inferred degree.
    catalog_year: Mapped[str] = mapped_column(String(64), nullable=False)
    current_term_year: Mapped[int] = mapped_column(Integer, nullable=False)
    current_term_season: Mapped[str] = mapped_column(String(6), nullable=False)
    target_graduation_term_year: Mapped[int] = mapped_column(Integer, nullable=False)
    target_graduation_term_season: Mapped[str] = mapped_column(String(6), nullable=False)
    max_credits_per_term: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)

    course_records: Mapped[list['CourseRecord']] = relationship(
        back_populates='student', cascade='all, delete-orphan', passive_deletes=True
    )
    extra_credits: Mapped[list['ExtraCredit']] = relationship(
        back_populates='student', cascade='all, delete-orphan', passive_deletes=True
    )


class CourseRecord(Base):
    __tablename__ = 'course_records'
    __table_args__ = (
        CheckConstraint(required_text('course_code') + ' AND course_code = upper(course_code)',
                        name='ck_course_code'),
        CheckConstraint("status IN ('completed', 'in_progress')", name='ck_course_status'),
        CheckConstraint("credit_source IN ('institutional', 'IB', 'AP', 'transfer')",
                        name='ck_course_source'),
        # Explicit IS NOT NULL checks matter: PostgreSQL CHECK permits UNKNOWN.
        CheckConstraint(
            "(term_year IS NULL AND term_season IS NULL) OR "
            "(term_year IS NOT NULL AND term_season IS NOT NULL AND " + required_term('term') + ')',
            name='ck_course_term',
        ),
        CheckConstraint("credit_source <> 'institutional' OR term_year IS NOT NULL",
                        name='ck_course_institutional_term'),
        CheckConstraint('credits >= 0 AND credits <= 9999.99 AND earned_credits >= 0 '
                        'AND earned_credits <= 9999.99 AND earned_credits <= credits',
                        name='ck_course_credits'),
        CheckConstraint("grade IS NULL OR grade IN "
                        "('A','A-','B+','B','B-','C+','C','C-','D+','D','F','S','N')",
                        name='ck_course_grade'),
        CheckConstraint("grading_basis IS NULL OR grading_basis IN ('AF','SN')",
                        name='ck_course_grading_basis'),
        CheckConstraint("grading_basis IS NULL OR grade IS NULL OR "
                        "(grading_basis = 'AF' AND grade NOT IN ('S','N')) OR "
                        "(grading_basis = 'SN' AND grade IN ('S','N'))",
                        name='ck_course_grade_basis'),
        CheckConstraint("grade IS NULL OR grade NOT IN ('F','N') OR earned_credits = 0",
                        name='ck_course_failed_credits'),
        CheckConstraint("status <> 'in_progress' OR "
                        "(earned_credits = 0 AND grade IS NULL AND "
                        "credit_source = 'institutional' AND term_year IS NOT NULL)",
                        name='ck_course_in_progress'),
        CheckConstraint("credit_source NOT IN ('IB','AP') OR "
                        "(grade IS NULL AND grading_basis IS NULL)",
                        name='ck_course_exam_grade'),
        CheckConstraint('credit_reference IS NULL OR (' + required_text('credit_reference') + ')',
                        name='ck_course_reference'),
        # Source/status are attributes, not a way to evade attempt deduplication.
        UniqueConstraint('student_id', 'course_code', 'term_year', 'term_season',
                         name='uq_course_attempt', postgresql_nulls_not_distinct=True),
        # Ordinary UNIQUE intentionally allows multiple unknown (NULL) references.
        UniqueConstraint('student_id', 'credit_reference', name='uq_course_credit_reference'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey('student_profiles.id', name='fk_course_student', ondelete='CASCADE'),
        nullable=False,
    )
    course_code: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    term_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    term_season: Mapped[str | None] = mapped_column(String(6), nullable=True)
    credits: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    earned_credits: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    grade: Mapped[str | None] = mapped_column(String(2), nullable=True)
    credit_source: Mapped[str] = mapped_column(String(16), nullable=False)
    grading_basis: Mapped[str | None] = mapped_column(String(2), nullable=True)
    credit_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    student: Mapped[StudentProfile] = relationship(back_populates='course_records')


class ExtraCredit(Base):
    __tablename__ = 'extra_credits'
    __table_args__ = (
        CheckConstraint(required_text('reference'), name='ck_extra_reference'),
        CheckConstraint("source IN ('institutional', 'IB', 'AP', 'transfer')", name='ck_extra_source'),
        CheckConstraint('earned_credits > 0 AND earned_credits <= 9999.99', name='ck_extra_credits'),
        CheckConstraint(
            '(usage_confirmed = false AND confirmed_usage IS NULL) OR '
            '(usage_confirmed = true AND confirmed_usage IS NOT NULL AND '
            + required_text('confirmed_usage') + ')',
            name='ck_extra_usage',
        ),
        UniqueConstraint('student_id', 'reference', name='uq_extra_reference'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey('student_profiles.id', name='fk_extra_student', ondelete='CASCADE'),
        nullable=False,
    )
    reference: Mapped[str] = mapped_column(String(128), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    earned_credits: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    usage_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    confirmed_usage: Mapped[str | None] = mapped_column(String(500), nullable=True)
    student: Mapped[StudentProfile] = relationship(back_populates='extra_credits')
