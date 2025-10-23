"""create user_quotas table

Revision ID: 20251022_1347_create_user_quotas
Revises: 20251022_1346_extend_users_table
Create Date: 2025-10-22 13:47:00.000000

Task 1.2.2: Create user_quotas table
- Create table with all fields
- Add FK constraint to users with ON DELETE CASCADE
- Add unique constraint on user_id
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251022_1347_create_user_quotas'
down_revision: Union[str, None] = '20251022_1346_extend_users_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user_quotas table."""
    op.create_table(
        'user_quotas',
        sa.Column('quota_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('llm_tokens_monthly_limit', sa.Integer(), nullable=True),
        sa.Column('masterplans_limit', sa.Integer(), nullable=True),
        sa.Column('storage_bytes_limit', sa.BigInteger(), nullable=True),
        sa.Column('api_calls_per_minute', sa.Integer(), nullable=False, server_default='30'),
        sa.PrimaryKeyConstraint('quota_id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', name='uq_user_quotas_user_id')
    )

    # Create index on user_id for fast lookups
    op.create_index('ix_user_quotas_user_id', 'user_quotas', ['user_id'], unique=True)


def downgrade() -> None:
    """Drop user_quotas table."""
    op.drop_index('ix_user_quotas_user_id', table_name='user_quotas')
    op.drop_table('user_quotas')
