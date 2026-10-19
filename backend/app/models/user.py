
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db

if TYPE_CHECKING:
    from app.models.user_session import UserSession


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    def __init__(
        self,
        *,
        google_sub: str,
        email: str,
        name: str | None = None,
        picture_url: str | None = None,
    ) -> None:
        self.google_sub = google_sub
        self.email = email
        self.name = name
        self.picture_url = picture_url

    id: Mapped[int] = mapped_column(primary_key=True)

    google_sub: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(320), unique=True, nullable=False, index=True
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    picture_url: Mapped[str | None] = mapped_column(
        String(2048), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
