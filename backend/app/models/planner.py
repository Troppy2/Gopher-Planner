"""User-owned coursework and single-plan persistence."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.user import utc_now


class Transcript(db.Model):
    __tablename__ = "transcripts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20))
    error_code: Mapped[str | None] = mapped_column(String(64))
    # JSON list of course codes found but not importable (transfer placeholders, unreadable codes).
    not_imported: Mapped[str | None] = mapped_column(Text)
    # JSON lists of liberal education categories the audit lists, and those it shows as covered.
    le_required: Mapped[str | None] = mapped_column(Text)
    le_covered: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Coursework(db.Model):
    __tablename__ = "coursework"
    __table_args__ = (
        UniqueConstraint("user_id", "code", "term", name="uq_coursework_user_code_term"),
        # Ordinary UNIQUE treats NULL terms as distinct on both supported databases.
        Index("uq_coursework_user_code_unknown_term", "user_id", "code", unique=True,
              sqlite_where=text("term IS NULL"), postgresql_where=text("term IS NULL")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(12))
    title: Mapped[str] = mapped_column(String(255))
    credits: Mapped[Decimal] = mapped_column(Numeric(4, 1))
    status: Mapped[str] = mapped_column(String(20))
    term: Mapped[str | None] = mapped_column(String(20))
    grade: Mapped[str | None] = mapped_column(String(2))
    source: Mapped[str] = mapped_column(String(20))
    transcript_id: Mapped[str | None] = mapped_column(ForeignKey("transcripts.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Plan(db.Model):
    __tablename__ = "plans"
    __table_args__ = (UniqueConstraint("user_id", name="uq_plans_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    catalog_term: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class PlanCourse(db.Model):
    __tablename__ = "plan_courses"
    __table_args__ = (UniqueConstraint("plan_id", "code", name="uq_plan_courses_plan_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(12))
    term: Mapped[str] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(20))
    # Sample-plan slot this course fills, e.g. "Global Perspectives"; None for requirement courses.
    slot: Mapped[str | None] = mapped_column(String(120))
