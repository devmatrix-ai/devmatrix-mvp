"""Add acceptance tests tables for MGE V2

Revision ID: 0ed951ee005a
Revises: 1a290de30226
Create Date: 2025-11-11 12:25:29.097123

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP


# revision identifiers, used by Alembic.
revision = '0ed951ee005a'
down_revision = '1a290de30226'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create acceptance_tests table
    op.create_table(
        'acceptance_tests',
        sa.Column('test_id', UUID(as_uuid=True), primary_key=True),
        sa.Column('masterplan_id', UUID(as_uuid=True), sa.ForeignKey('masterplans.masterplan_id', ondelete='CASCADE'), nullable=False),
        sa.Column('requirement_text', sa.Text(), nullable=False, comment='Original requirement from masterplan'),
        sa.Column('requirement_priority', sa.String(10), nullable=False, comment='must or should classification'),
        sa.Column('test_code', sa.Text(), nullable=False, comment='Generated test code (pytest/jest/vitest)'),
        sa.Column('test_language', sa.String(20), nullable=False, comment='pytest, jest, or vitest'),
        sa.Column('test_framework_version', sa.String(20)),
        sa.Column('timeout_seconds', sa.Integer(), default=30, comment='Test execution timeout'),
        sa.Column('created_at', TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint("requirement_priority IN ('must', 'should')", name='valid_priority'),
        sa.CheckConstraint("test_language IN ('pytest', 'jest', 'vitest')", name='valid_language')
    )

    # Create indexes for acceptance_tests
    op.create_index('idx_acceptance_tests_masterplan', 'acceptance_tests', ['masterplan_id'])
    op.create_index('idx_acceptance_tests_priority', 'acceptance_tests', ['masterplan_id', 'requirement_priority'])

    # Create acceptance_test_results table
    op.create_table(
        'acceptance_test_results',
        sa.Column('result_id', UUID(as_uuid=True), primary_key=True),
        sa.Column('test_id', UUID(as_uuid=True), sa.ForeignKey('acceptance_tests.test_id', ondelete='CASCADE'), nullable=False),
        sa.Column('wave_id', UUID(as_uuid=True), sa.ForeignKey('execution_waves.wave_id'), nullable=True),
        sa.Column('execution_time', TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, comment='pass, fail, timeout, or error'),
        sa.Column('error_message', sa.Text(), comment='Error message if failed'),
        sa.Column('execution_duration_ms', sa.Integer(), comment='Actual execution time in milliseconds'),
        sa.Column('stdout', sa.Text(), comment='Test stdout'),
        sa.Column('stderr', sa.Text(), comment='Test stderr'),
        sa.CheckConstraint("status IN ('pass', 'fail', 'timeout', 'error')", name='valid_status')
    )

    # Create indexes for acceptance_test_results
    op.create_index('idx_test_results_test', 'acceptance_test_results', ['test_id'])
    op.create_index('idx_test_results_wave', 'acceptance_test_results', ['wave_id'])
    op.create_index('idx_test_results_status', 'acceptance_test_results', ['test_id', 'status'])

    # Add markdown_content field to masterplans table
    op.add_column('masterplans', sa.Column('markdown_content', sa.Text(), nullable=True, comment='Full masterplan markdown with requirements'))


def downgrade() -> None:
    # Remove markdown_content from masterplans
    op.drop_column('masterplans', 'markdown_content')

    # Drop indexes for acceptance_test_results
    op.drop_index('idx_test_results_status', 'acceptance_test_results')
    op.drop_index('idx_test_results_wave', 'acceptance_test_results')
    op.drop_index('idx_test_results_test', 'acceptance_test_results')

    # Drop acceptance_test_results table
    op.drop_table('acceptance_test_results')

    # Drop indexes for acceptance_tests
    op.drop_index('idx_acceptance_tests_priority', 'acceptance_tests')
    op.drop_index('idx_acceptance_tests_masterplan', 'acceptance_tests')

    # Drop acceptance_tests table
    op.drop_table('acceptance_tests')
