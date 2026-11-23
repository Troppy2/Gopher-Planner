"""Reject duplicate coursework attempts with unknown terms.

Revision ID: e4b7c2a91d06
Revises: cf8c0dfdbb15
"""
from alembic import op
import sqlalchemy as sa


revision = "e4b7c2a91d06"
down_revision = "cf8c0dfdbb15"
branch_labels = None
depends_on = None


def upgrade():
    # Fail without deleting or changing rows if legacy attempts collide.
    duplicate = op.get_bind().execute(sa.text(
        "SELECT 1 FROM coursework WHERE term IS NULL "
        "GROUP BY user_id, code HAVING COUNT(*) > 1 LIMIT 1"
    )).first()
    if duplicate is not None:
        raise RuntimeError("Duplicate unknown-term coursework attempts require explicit data repair before upgrade")
    op.create_index(
        "uq_coursework_user_code_unknown_term", "coursework", ["user_id", "code"],
        unique=True, sqlite_where=sa.text("term IS NULL"), postgresql_where=sa.text("term IS NULL"),
    )


def downgrade():
    op.drop_index("uq_coursework_user_code_unknown_term", table_name="coursework")
