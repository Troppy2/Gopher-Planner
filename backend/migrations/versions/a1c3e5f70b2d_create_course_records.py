"""create course_records

Revision ID: a1c3e5f70b2d
Revises: 6dd8d6e5f05f
Create Date: 2026-10-26 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1c3e5f70b2d'
down_revision = '6dd8d6e5f05f'
branch_labels = None
depends_on = None

COURSE_ATTEMPT = "kind = 'course' AND term_year IS NOT NULL"
COURSE_TERMLESS = "kind = 'course' AND term_year IS NULL"


def upgrade():
    op.create_table(
        'course_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('kind', sa.String(length=16), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('course_code', sa.String(length=32), nullable=True),
        sa.Column('credit_source', sa.String(length=16), nullable=False),
        sa.Column('term_year', sa.Integer(), nullable=True),
        sa.Column('term_season', sa.String(length=6), nullable=True),
        sa.Column('credits', sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column('earned_credits', sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column('grade', sa.String(length=2), nullable=True),
        sa.Column('reference', sa.String(length=128), nullable=True),
        sa.Column('confirmed_usage', sa.String(length=500), nullable=True),
        sa.CheckConstraint("kind IN ('course', 'unmapped_credit')", name='ck_course_records_kind'),
        sa.CheckConstraint("status IN ('completed', 'in_progress')", name='ck_course_records_status'),
        sa.CheckConstraint("credit_source IN ('institutional', 'AP', 'IB', 'transfer')",
                           name='ck_course_records_source'),
        sa.CheckConstraint(
            "(kind = 'course' AND course_code IS NOT NULL) OR "
            "(kind = 'unmapped_credit' AND course_code IS NULL AND reference IS NOT NULL)",
            name='ck_course_records_kind_fields'),
        sa.CheckConstraint(
            "(term_year IS NULL AND term_season IS NULL) OR "
            "(term_year IS NOT NULL AND term_season IS NOT NULL "
            "AND term_season IN ('Spring', 'Summer', 'Fall'))",
            name='ck_course_records_term'),
        sa.CheckConstraint("credit_source <> 'institutional' OR term_year IS NOT NULL",
                           name='ck_course_records_institutional_term'),
        sa.CheckConstraint("credits >= 0 AND earned_credits >= 0 AND earned_credits <= credits",
                           name='ck_course_records_credits'),
        sa.CheckConstraint(
            "grade IS NULL OR grade IN "
            "('A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'F', 'S', 'N')",
            name='ck_course_records_grade'),
        sa.CheckConstraint("grade IS NULL OR grade NOT IN ('F', 'N') OR earned_credits = 0",
                           name='ck_course_records_failed_credits'),
        sa.CheckConstraint(
            "status <> 'in_progress' OR (kind = 'course' AND credit_source = 'institutional' "
            "AND term_year IS NOT NULL AND earned_credits = 0 AND grade IS NULL)",
            name='ck_course_records_in_progress'),
        sa.CheckConstraint("kind = 'unmapped_credit' OR confirmed_usage IS NULL",
                           name='ck_course_records_usage'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'reference', name='uq_course_records_reference'),
    )
    op.create_index('ix_course_records_user_id', 'course_records', ['user_id'])
    op.create_index(
        'uq_course_records_attempt', 'course_records',
        ['user_id', 'course_code', 'term_year', 'term_season'], unique=True,
        sqlite_where=sa.text(COURSE_ATTEMPT), postgresql_where=sa.text(COURSE_ATTEMPT))
    op.create_index(
        'uq_course_records_termless', 'course_records',
        ['user_id', 'course_code'], unique=True,
        sqlite_where=sa.text(COURSE_TERMLESS), postgresql_where=sa.text(COURSE_TERMLESS))


def downgrade():
    op.drop_index('uq_course_records_termless', table_name='course_records')
    op.drop_index('uq_course_records_attempt', table_name='course_records')
    op.drop_index('ix_course_records_user_id', table_name='course_records')
    op.drop_table('course_records')
