"""Add intelligent task calculation columns to masterplans table

Revision ID: 20251104_1140
Revises: 20251031_0801_create_masterplan_milestones
Create Date: 2025-11-04 11:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251104_1140'
down_revision = '20251031_0801_create_masterplan_milestones'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to masterplans table for intelligent task calculation
    op.add_column('masterplans', sa.Column('calculated_task_count', sa.Integer(), nullable=True))
    op.add_column('masterplans', sa.Column('complexity_metrics', postgresql.JSON(), nullable=True))
    op.add_column('masterplans', sa.Column('task_breakdown', postgresql.JSON(), nullable=True))
    op.add_column('masterplans', sa.Column('parallelization_level', sa.Integer(), nullable=True))
    op.add_column('masterplans', sa.Column('calculation_rationale', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove the new columns
    op.drop_column('masterplans', 'calculation_rationale')
    op.drop_column('masterplans', 'parallelization_level')
    op.drop_column('masterplans', 'task_breakdown')
    op.drop_column('masterplans', 'complexity_metrics')
    op.drop_column('masterplans', 'calculated_task_count')
