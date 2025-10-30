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

    # Step 1: Drop foreign key constraint from messages table
    op.drop_constraint('messages_conversation_id_fkey', 'messages', type_='foreignkey')

    # Step 2: Rename columns in conversations table
    op.alter_column('conversations', 'conversation_id', new_column_name='id')

    # Step 3: Add session_id column to conversations
    op.add_column('conversations', sa.Column('session_id', sa.String(length=255), nullable=True))

    # Step 4: Add metadata column to conversations if it doesn't exist
    # Use try-except pattern with op.f() for proper constraint naming
    try:
        op.add_column('conversations', sa.Column('metadata', postgresql.JSONB(), nullable=True, server_default='{}'))
    except Exception:
        pass  # Column may already exist

    # Step 5: Rename columns in messages table
    op.alter_column('messages', 'message_id', new_column_name='id')

    # Step 6: Add metadata column to messages
    op.add_column('messages', sa.Column('metadata', postgresql.JSONB(), nullable=True, server_default='{}'))

    # Step 7: Recreate foreign key with new column name
    op.create_foreign_key(
        'messages_conversation_id_fkey',
        'messages', 'conversations',
        ['conversation_id'], ['id'],
        ondelete='CASCADE'
    )

    # Step 8: Update indexes if needed
    # The existing indexes should still work as they reference by name, not column


def downgrade() -> None:
    """Revert conversations and messages schema changes."""

    # Step 1: Drop foreign key
    op.drop_constraint('messages_conversation_id_fkey', 'messages', type_='foreignkey')

    # Step 2: Remove metadata columns
    op.drop_column('messages', 'metadata')
    op.drop_column('conversations', 'metadata')

    # Step 3: Remove session_id column
    op.drop_column('conversations', 'session_id')

    # Step 3: Rename columns back
    op.alter_column('messages', 'id', new_column_name='message_id')
    op.alter_column('conversations', 'id', new_column_name='conversation_id')

    # Step 4: Recreate original foreign key
    op.create_foreign_key(
        'messages_conversation_id_fkey',
        'messages', 'conversations',
        ['conversation_id'], ['conversation_id'],
        ondelete='CASCADE'
    )
