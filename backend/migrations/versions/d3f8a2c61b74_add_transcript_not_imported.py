"""Record course codes a transcript upload could not import.

Revision ID: d3f8a2c61b74
Revises: c8d2a6f19e47
"""
import sqlalchemy as sa
from alembic import op

revision = "d3f8a2c61b74"
down_revision = "c8d2a6f19e47"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("transcripts") as batch:
        batch.add_column(sa.Column("not_imported", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("transcripts") as batch:
        batch.drop_column("not_imported")
