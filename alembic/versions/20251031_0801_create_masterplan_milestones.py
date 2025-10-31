"""Create masterplan_milestones table

Revision ID: 20251031_0801_create_masterplan_milestones
Revises: 20251030_2239_fix_masterplan_phases_schema
Create Date: 2025-10-31 08:01:00.000000

The MasterPlanMilestone model expects a masterplan_milestones table that groups
related tasks into logical milestones within phases. This migration creates that table.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251031_0801_create_masterplan_milestones'
down_revision = '20251030_2239_fix_masterplan_phases_schema'
branch_labels = None
depends_on = None


def upgrade():
    """Create masterplan_milestones table."""

    # Create the masterplan_milestones table
    op.create_table(
        'masterplan_milestones',
        sa.Column('milestone_id', sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column('phase_id', sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column('milestone_number', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('depends_on_milestones', sa.JSON(), nullable=True),
        sa.Column('total_tasks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completed_tasks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('progress_percent', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['phase_id'], ['masterplan_phases.phase_id'], ),
        sa.PrimaryKeyConstraint('milestone_id')
    )

    # Create indexes
    op.create_index('idx_milestone_phase', 'masterplan_milestones', ['phase_id'], unique=False)
    op.create_index('idx_milestone_number', 'masterplan_milestones', ['phase_id', 'milestone_number'], unique=False)

    # Update masterplan_tasks to reference the new milestone table
    # First, check if milestone_id column exists in masterplan_tasks
    # If not, add it
    op.add_column('masterplan_tasks',
                  sa.Column('milestone_id', sa.dialects.postgresql.UUID(), nullable=True))

    # Add foreign key constraint for milestone_id
    op.create_foreign_key(
        'fk_masterplan_tasks_milestone_id',
        'masterplan_tasks',
        'masterplan_milestones',
        ['milestone_id'],
        ['milestone_id']
    )


def downgrade():
    """Drop masterplan_milestones table."""

    # Drop the foreign key constraint
    op.drop_constraint('fk_masterplan_tasks_milestone_id', 'masterplan_tasks', type_='foreignkey')

    # Drop milestone_id column from masterplan_tasks
    op.drop_column('masterplan_tasks', 'milestone_id')

    # Drop indexes
    op.drop_index('idx_milestone_number', table_name='masterplan_milestones')
    op.drop_index('idx_milestone_phase', table_name='masterplan_milestones')

    # Drop the table
    op.drop_table('masterplan_milestones')
