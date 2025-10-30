"""create conversation_shares table

Revision ID: 20251026_2159
Revises: 15c544aaf40b
Create Date: 2025-10-26 21:59:00.000000

Phase 2 - Task Group 8: Granular Permission System
Creates conversation_shares table for user-to-user conversation sharing.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251026_2159'
down_revision = '15c544aaf40b'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create conversation_shares table.

    Enables user-to-user conversation sharing with three permission levels:
    - view: Read-only access
    - comment: Read + write messages
    - edit: Full access except delete
    """
    # Create conversation_shares table
    op.create_table(
        'conversation_shares',
        sa.Column('share_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('shared_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('shared_with', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_level', sa.String(20), nullable=False),
        sa.Column('shared_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('share_id'),
        sa.CheckConstraint(
            "permission_level IN ('view', 'comment', 'edit')",
            name='ck_conversation_shares_permission_level'
        ),
        sa.UniqueConstraint('conversation_id', 'shared_with', name='uq_conversation_shares_conversation_user'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.conversation_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['shared_by'], ['users.user_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['shared_with'], ['users.user_id'], ondelete='CASCADE')
    )

    # Create indexes for performance
    op.create_index(
        'idx_conversation_shares_conversation_id',
        'conversation_shares',
        ['conversation_id']
    )
    op.create_index(
        'idx_conversation_shares_shared_with',
        'conversation_shares',
        ['shared_with']
    )


def downgrade():
    """Drop conversation_shares table and indexes."""
    op.drop_index('idx_conversation_shares_shared_with', table_name='conversation_shares')
    op.drop_index('idx_conversation_shares_conversation_id', table_name='conversation_shares')
    op.drop_table('conversation_shares')
