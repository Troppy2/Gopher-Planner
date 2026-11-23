"""Label planned courses that fill a sample-plan slot (e.g. a liberal education category).

Revision ID: f2b6d8e04a13
Revises: e9a1c47b2d58
"""
import sqlalchemy as sa
from alembic import op

revision = "f2b6d8e04a13"
down_revision = "e9a1c47b2d58"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("plan_courses") as batch:
        batch.add_column(sa.Column("slot", sa.String(length=120), nullable=True))


def downgrade():
    with op.batch_alter_table("plan_courses") as batch:
        batch.drop_column("slot")
