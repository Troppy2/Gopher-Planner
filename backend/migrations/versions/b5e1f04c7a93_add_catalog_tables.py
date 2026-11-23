"""Move the course catalog into the application database.

Creates empty tables only. Rows are loaded by `scripts/import_catalog.py`, never by the app.

Revision ID: b5e1f04c7a93
Revises: a7c3d91e5b20
"""
from alembic import op
import sqlalchemy as sa


revision = "b5e1f04c7a93"
down_revision = "a7c3d91e5b20"
branch_labels = None
depends_on = None


def text_columns(*names):
    return [sa.Column(name, sa.Text(), nullable=False) for name in names]


def upgrade():
    op.create_table(
        "catalog_releases",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("generated_at", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "catalog_courses",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("release_id", sa.Integer(), nullable=False),
        sa.Column("subject_code", sa.String(length=16), nullable=False),
        sa.Column("course_number", sa.String(length=16), nullable=False),
        sa.Column("course_code", sa.String(length=32), nullable=False),
        *text_columns("course_name", "campus", "description"),
        sa.Column("minimum_credits", sa.String(length=16), nullable=False),
        sa.Column("maximum_credits", sa.String(length=16), nullable=False),
        *text_columns("repeatable", "maximum_completions", "maximum_credits_earned", "grading_basis",
                      "requirements", "typically_offered", "prerequisite_status", "prerequisite_source_text"),
        sa.Column("prerequisite_json", sa.Text(), nullable=True),
        *text_columns("prerequisite_unresolved_courses", "prerequisite_extraction_method"),
        sa.ForeignKeyConstraint(["release_id"], ["catalog_releases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("release_id", "course_code", name="uq_catalog_courses_release_code"),
    )
    op.create_index("ix_catalog_courses_release_id", "catalog_courses", ["release_id"])
    op.create_index("ix_catalog_courses_course_code", "catalog_courses", ["course_code"])
    op.create_index("ix_catalog_courses_subject_number", "catalog_courses", ["subject_code", "course_number"])
    op.create_table(
        "catalog_prerequisite_edges",
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("prerequisite_course_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["catalog_courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prerequisite_course_id"], ["catalog_courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("course_id", "prerequisite_course_id"),
    )
    op.create_index("ix_catalog_prerequisite_edges_prerequisite_course_id",
                    "catalog_prerequisite_edges", ["prerequisite_course_id"])


def downgrade():
    op.drop_table("catalog_prerequisite_edges")
    op.drop_table("catalog_courses")
    op.drop_table("catalog_releases")
