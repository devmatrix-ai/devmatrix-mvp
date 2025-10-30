"""Fix MasterPlanPhase schema - add missing columns

Revision ID: 20251030_2239_fix_masterplan_phases_schema
Revises: 20251030_1006_add_user_id_to_conversations
Create Date: 2025-10-30 22:39:00.000000

The MasterPlanPhase model defines columns that don't exist in the table:
- phase_type (Enum)
- total_milestones, total_tasks, completed_tasks (Integer)
- progress_percent (Float)
- started_at, completed_at (DateTime)

This migration adds all missing columns and removes the incorrect 'status' column.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import enum

# revision identifiers, used by Alembic.
revision = '20251030_2239_fix_masterplan_phases_schema'
down_revision = '20251028_1315'
branch_labels = None
depends_on = None


def upgrade():
    """Add missing columns to masterplan_phases table."""

    # Create enum type for PhaseType
    phase_type_enum = postgresql.ENUM('setup', 'core', 'polish', name='phasetype')
    phase_type_enum.create(op.get_bind(), checkfirst=True)

    # Add missing columns
    op.add_column('masterplan_phases',
                  sa.Column('phase_type', postgresql.ENUM('setup', 'core', 'polish', name='phasetype'),
                           nullable=False, server_default='setup'))

    op.add_column('masterplan_phases',
                  sa.Column('total_milestones', sa.Integer(), nullable=False, server_default='0'))

    op.add_column('masterplan_phases',
                  sa.Column('total_tasks', sa.Integer(), nullable=False, server_default='0'))

    op.add_column('masterplan_phases',
                  sa.Column('completed_tasks', sa.Integer(), nullable=False, server_default='0'))

    op.add_column('masterplan_phases',
                  sa.Column('progress_percent', sa.Float(), nullable=False, server_default='0.0'))

    op.add_column('masterplan_phases',
                  sa.Column('started_at', sa.DateTime(), nullable=True))

    op.add_column('masterplan_phases',
                  sa.Column('completed_at', sa.DateTime(), nullable=True))

    # Drop the incorrect 'status' column if it exists
    op.drop_column('masterplan_phases', 'status')


def downgrade():
    """Revert the schema changes."""

    # Recreate the status column
    op.add_column('masterplan_phases',
                  sa.Column('status', sa.VARCHAR(length=50), nullable=False, server_default='pending'))

    # Drop the newly added columns
    op.drop_column('masterplan_phases', 'completed_at')
    op.drop_column('masterplan_phases', 'started_at')
    op.drop_column('masterplan_phases', 'progress_percent')
    op.drop_column('masterplan_phases', 'completed_tasks')
    op.drop_column('masterplan_phases', 'total_tasks')
    op.drop_column('masterplan_phases', 'total_milestones')
    op.drop_column('masterplan_phases', 'phase_type')

    # Drop the enum type
    op.execute('DROP TYPE IF EXISTS phasetype')
