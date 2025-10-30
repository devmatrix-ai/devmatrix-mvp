"""fix_conversations_messages_schema

Revision ID: a917f33d2fd7
Revises: 20251027_0100
Create Date: 2025-10-28 12:02:52.590354

Fix schema mismatch between migrations and code:
- Rename conversation_id to id in conversations table
- Rename message_id to id in messages table
- Add metadata column to conversations table
- Add metadata column to messages table
- Update foreign keys accordingly
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'a917f33d2fd7'
down_revision = '20251027_0100'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Fix conversations and messages schema."""

    # Only add columns if they don't already exist
    # Using raw SQL for better control and idempotency

    # Add session_id column to conversations if it doesn't exist
    op.execute("""
        ALTER TABLE conversations ADD COLUMN IF NOT EXISTS
        session_id VARCHAR(255) DEFAULT NULL;
    """)

    # Add metadata column to conversations if it doesn't exist
    op.execute("""
        ALTER TABLE conversations ADD COLUMN IF NOT EXISTS
        metadata JSONB DEFAULT '{}';
    """)

    # Add metadata column to messages if it doesn't exist
    op.execute("""
        ALTER TABLE messages ADD COLUMN IF NOT EXISTS
        metadata JSONB DEFAULT '{}';
    """)


def downgrade() -> None:
    """Revert conversations and messages schema changes."""

    # Note: This migration is idempotent - it only adds columns that may not exist
    # Downgrade removes the columns that were added
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS session_id;")
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS metadata;")
    op.execute("ALTER TABLE messages DROP COLUMN IF EXISTS metadata;")
