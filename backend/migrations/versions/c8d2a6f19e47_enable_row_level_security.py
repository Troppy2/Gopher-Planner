"""Enable row level security on every application table (PostgreSQL only).

Supabase exposes the public schema through its Data API to anyone holding the project's
publishable key. With RLS on and no policies, that API can read and write nothing. The Flask
backend connects as the table owner, which bypasses RLS, so it is unaffected.

Revision ID: c8d2a6f19e47
Revises: b5e1f04c7a93
"""
from alembic import op


revision = "c8d2a6f19e47"
down_revision = "b5e1f04c7a93"
branch_labels = None
depends_on = None

TABLES = ("alembic_version", "users", "user_sessions", "transcripts", "coursework", "plans", "plan_courses",
          "catalog_releases", "catalog_courses", "catalog_prerequisite_edges")


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')


def downgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
