"""Per-user write serialization.

Every request that reads and then replaces a user's rows (plan, coursework, transcript import)
takes this lock first (FOR NO KEY UPDATE, so foreign-key checks from other writes are not blocked), so two tabs or a double click cannot interleave and lose an update or
race to create the same plan row. On PostgreSQL this is a row lock on the user that lasts until
the transaction ends; SQLite has no row locks and serializes writers on its own.
"""
from sqlalchemy import select

from app.extensions import db
from app.models import User


def lock_user(user_id):
    return db.session.scalar(
        select(User).where(User.id == user_id).with_for_update(key_share=True).execution_options(populate_existing=True))
