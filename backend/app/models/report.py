"""Student reports, separate from academic data."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.extensions import db
from app.models.user import utc_now


class DataReport(db.Model):
    __tablename__ = "data_reports"
    __table_args__ = (
        Index("ix_data_reports_course", "target_type", "course_code"),
        Index("ix_data_reports_requirement", "target_type", "program_id", "requirement_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    course_code: Mapped[str | None] = mapped_column(String(12))
    program_id: Mapped[str | None] = mapped_column(String(120))
    catalog_term: Mapped[str | None] = mapped_column(String(20))
    requirement_id: Mapped[str | None] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(String(40), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", server_default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
