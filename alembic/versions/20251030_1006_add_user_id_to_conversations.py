"""Add user_id column to conversations table

Revision ID: add_user_id_conversations
Revises: 20251028_1315
Create Date: 2025-10-30 10:06:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_user_id_conversations'
down_revision = '20251028_1315'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add user_id column if it doesn't exist
    op.execute("""
        ALTER TABLE conversations
        ADD COLUMN IF NOT EXISTS user_id VARCHAR(255);
    """)

    # Create index on user_id for better query performance
    op.create_index('idx_conversations_user_id', 'conversations', ['user_id'], if_not_exists=True)


def downgrade() -> None:
    # Drop index if it exists
    op.drop_index('idx_conversations_user_id', table_name='conversations', if_exists=True)

    # Drop column if it exists
    op.execute("""
        ALTER TABLE conversations
        DROP COLUMN IF EXISTS user_id;
    """)
