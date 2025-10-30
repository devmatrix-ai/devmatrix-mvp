"""add_session_id_to_conversations

Revision ID: 8fe2fe1d893a
Revises: a917f33d2fd7
Create Date: 2025-10-28 12:04:40.364327

Add session_id column to conversations table
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8fe2fe1d893a'
down_revision = 'a917f33d2fd7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add session_id column to conversations."""
    op.add_column('conversations', sa.Column('session_id', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Remove session_id column from conversations."""
    op.drop_column('conversations', 'session_id')
