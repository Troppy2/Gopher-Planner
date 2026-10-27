from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from sqlalchemy import ForeignKey, Float
# Import from the user models to establish a relationship with the User model
from app.models.user import User

if TYPE_CHECKING:
    from app.models.user_session import UserSession


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

# The ORM summary tbale that holds summary of user data
class Summary(db.Model):
    __tablename__ = "summaries"

    # this maps the current user data to the user id
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    gpa: Mapped[float] = mapped_column(Float, nullable=False)
    # Classes have three categories: taken, current, and planned.
    class_taken: Mapped[String] = mapped_column(Text, nullable=False)
    class_current: Mapped[String] = mapped_column(Text, nullable=False)
    class_planned: Mapped[String] = mapped_column(Text, nullable=False)
    
    program: Mapped[String] = mapped_column(Text, nullable=False)
    
    # Transcript data (encrypted)
    transcript_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
