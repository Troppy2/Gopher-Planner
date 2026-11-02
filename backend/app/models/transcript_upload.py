"""One uploaded APAS PDF and the result of parsing it.

The PDF itself is never stored: we read it in memory, keep only the parsed
courses (in course_records) and these counts.
"""

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db

STATUSES = ("parsed", "no_text", "failed")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TranscriptUpload(db.Model):
    __tablename__ = "transcript_uploads"
    __table_args__ = (
        CheckConstraint(
            "status IN ('parsed', 'no_text', 'failed')",
            name="ck_transcript_uploads_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    completed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    in_progress_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
