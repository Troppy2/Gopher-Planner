"""Liberal education designations on catalog courses.

Revision ID: e9a1c47b2d58
Revises: d3f8a2c61b74
"""
import sqlalchemy as sa
from alembic import op

revision = "e9a1c47b2d58"
down_revision = "d3f8a2c61b74"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("catalog_courses") as batch:
        batch.add_column(sa.Column("le_attributes", sa.Text(), nullable=False, server_default=""))


def downgrade():
    with op.batch_alter_table("catalog_courses") as batch:
        batch.drop_column("le_attributes")
