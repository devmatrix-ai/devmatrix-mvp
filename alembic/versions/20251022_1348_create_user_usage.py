"""create user_usage table

Revision ID: 20251022_1348_create_user_usage
Revises: 20251022_1347_create_user_quotas
Create Date: 2025-10-22 13:48:00.000000

Task 1.2.3: Create user_usage table
- Create table with all fields
- Add FK constraint to users with ON DELETE CASCADE
- Add unique constraint on (user_id, month)
- Add indexes
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251022_1348_create_user_usage'
down_revision: Union[str, None] = '20251022_1347_create_user_quotas'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user_usage table."""
    op.create_table(
        'user_usage',
        sa.Column('usage_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('month', sa.Date(), nullable=False),
        sa.Column('llm_tokens_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('llm_cost_usd', sa.Numeric(precision=10, scale=4), nullable=True, server_default='0.0'),
        sa.Column('masterplans_created', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('storage_bytes', sa.BigInteger(), nullable=True, server_default='0'),
        sa.Column('api_calls', sa.Integer(), nullable=True, server_default='0'),
        sa.PrimaryKeyConstraint('usage_id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'month', name='uq_user_usage_user_month')
    )

    # Create compound index on (user_id, month) for fast lookups
    op.create_index('idx_user_usage_user_month', 'user_usage', ['user_id', 'month'], unique=False)


def downgrade() -> None:
    """Drop user_usage table."""
    op.drop_index('idx_user_usage_user_month', table_name='user_usage')
    op.drop_table('user_usage')
