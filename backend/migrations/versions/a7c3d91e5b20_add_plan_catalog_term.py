"""Record the explicitly selected program catalog term on each plan.

Revision ID: a7c3d91e5b20
Revises: e4b7c2a91d06
"""
from alembic import op
import sqlalchemy as sa


revision = "a7c3d91e5b20"
down_revision = "e4b7c2a91d06"
branch_labels = None
depends_on = None


def upgrade():
    # Nullable: existing plans remain unconfirmed until the user selects a version.
    with op.batch_alter_table("plans") as batch:
        batch.add_column(sa.Column("catalog_term", sa.String(length=20), nullable=True))


def downgrade():
    with op.batch_alter_table("plans") as batch:
        batch.drop_column("catalog_term")
