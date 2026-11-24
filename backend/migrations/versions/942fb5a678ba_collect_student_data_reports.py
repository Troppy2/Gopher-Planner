"""collect student data reports

Revision ID: 942fb5a678ba
Revises: a1d4e7f93c20
Create Date: 2026-11-24 11:26:57.629621

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '942fb5a678ba'
down_revision = 'a1d4e7f93c20'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('data_reports',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('target_type', sa.String(length=20), nullable=False),
    sa.Column('course_code', sa.String(length=12), nullable=True),
    sa.Column('program_id', sa.String(length=120), nullable=True),
    sa.Column('catalog_term', sa.String(length=20), nullable=True),
    sa.Column('requirement_id', sa.String(length=64), nullable=True),
    sa.Column('reason', sa.String(length=40), nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('status', sa.String(length=20), server_default='open', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('data_reports', schema=None) as batch_op:
        batch_op.create_index('ix_data_reports_course', ['target_type', 'course_code'], unique=False)
        batch_op.create_index('ix_data_reports_requirement', ['target_type', 'program_id', 'requirement_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_reports_user_id'), ['user_id'], unique=False)

    # Match the existing deny-by-default Supabase Data API policy.
    if op.get_bind().dialect.name == "postgresql":
        op.execute('ALTER TABLE data_reports ENABLE ROW LEVEL SECURITY')


def downgrade():
    # This intentionally removes collected reports; accounts and academic data remain.
    with op.batch_alter_table('data_reports', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_data_reports_user_id'))
        batch_op.drop_index('ix_data_reports_requirement')
        batch_op.drop_index('ix_data_reports_course')

    op.drop_table('data_reports')
