"""Course catalog tables. Seed data, kept apart from user data and written only by the importer."""
from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class CatalogRelease(db.Model):
    __tablename__ = "catalog_releases"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    version: Mapped[str] = mapped_column(String(64))
    generated_at: Mapped[str] = mapped_column(String(64))


class CatalogCourse(db.Model):
    """Columns mirror the bundled export as text so an import is lossless."""
    __tablename__ = "catalog_courses"
    __table_args__ = (
        UniqueConstraint("release_id", "course_code", name="uq_catalog_courses_release_code"),
        Index("ix_catalog_courses_course_code", "course_code"),
        Index("ix_catalog_courses_subject_number", "subject_code", "course_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    release_id: Mapped[int] = mapped_column(ForeignKey("catalog_releases.id", ondelete="CASCADE"), index=True)
    subject_code: Mapped[str] = mapped_column(String(16))
    course_number: Mapped[str] = mapped_column(String(16))
    course_code: Mapped[str] = mapped_column(String(32))
    course_name: Mapped[str] = mapped_column(Text)
    campus: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    minimum_credits: Mapped[str] = mapped_column(String(16))
    maximum_credits: Mapped[str] = mapped_column(String(16))
    repeatable: Mapped[str] = mapped_column(Text)
    maximum_completions: Mapped[str] = mapped_column(Text)
    maximum_credits_earned: Mapped[str] = mapped_column(Text)
    grading_basis: Mapped[str] = mapped_column(Text)
    requirements: Mapped[str] = mapped_column(Text)
    typically_offered: Mapped[str] = mapped_column(Text)
    prerequisite_status: Mapped[str] = mapped_column(Text)
    prerequisite_source_text: Mapped[str] = mapped_column(Text)
    prerequisite_json: Mapped[str | None] = mapped_column(Text)
    prerequisite_unresolved_courses: Mapped[str] = mapped_column(Text)
    prerequisite_extraction_method: Mapped[str] = mapped_column(Text)
    # "; "-separated liberal education designations from the full catalog export (e.g. "Global Perspectives").
    le_attributes: Mapped[str] = mapped_column(Text, default="", server_default="")


class CatalogPrerequisiteEdge(db.Model):
    __tablename__ = "catalog_prerequisite_edges"

    course_id: Mapped[int] = mapped_column(ForeignKey("catalog_courses.id", ondelete="CASCADE"), primary_key=True)
    prerequisite_course_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_courses.id", ondelete="CASCADE"), primary_key=True, index=True)
