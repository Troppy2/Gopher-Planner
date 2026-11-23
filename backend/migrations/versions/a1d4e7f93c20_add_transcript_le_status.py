"""Liberal education status read from an APAS audit: required and covered categories.

Revision ID: a1d4e7f93c20
Revises: f2b6d8e04a13
"""
import sqlalchemy as sa
from alembic import op

revision = "a1d4e7f93c20"
down_revision = "f2b6d8e04a13"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("transcripts") as batch:
        batch.add_column(sa.Column("le_required", sa.Text(), nullable=True))
        batch.add_column(sa.Column("le_covered", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("transcripts") as batch:
        batch.drop_column("le_covered")
        batch.drop_column("le_required")
