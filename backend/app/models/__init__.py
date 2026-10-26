"""PostgreSQL metadata; importing models registers tables, never creates them."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Alembic imports Base here, so all user-data tables must be registered here.
from app.models.academic import CourseRecord, ExtraCredit, StudentProfile  # noqa: E402,F401
