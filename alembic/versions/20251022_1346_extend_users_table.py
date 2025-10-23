"""extend users table

Revision ID: 20251022_1346_extend_users_table
Revises: 93ad2d77767b
Create Date: 2025-10-22 13:46:00.000000

Task 1.2.1: Extend users table with email verification and password reset fields
- Add is_verified, verification_token, verification_token_created_at
- Add password_reset_token, password_reset_expires
- Add indexes on token columns
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251022_1346_extend_users_table'
down_revision: Union[str, None] = '93ad2d77767b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add email verification and password reset fields to users table."""
    # Add email verification fields
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('users', sa.Column('verification_token', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('users', sa.Column('verification_token_created_at', sa.DateTime(), nullable=True))

    # Add password reset fields
    op.add_column('users', sa.Column('password_reset_token', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('users', sa.Column('password_reset_expires', sa.DateTime(), nullable=True))

    # Create indexes for token lookups
    op.create_index('idx_verification_token', 'users', ['verification_token'], unique=False)
    op.create_index('idx_password_reset_token', 'users', ['password_reset_token'], unique=False)


def downgrade() -> None:
    """Remove email verification and password reset fields from users table."""
    # Drop indexes
    op.drop_index('idx_password_reset_token', table_name='users')
    op.drop_index('idx_verification_token', table_name='users')

    # Drop password reset fields
    op.drop_column('users', 'password_reset_expires')
    op.drop_column('users', 'password_reset_token')

    # Drop email verification fields
    op.drop_column('users', 'verification_token_created_at')
    op.drop_column('users', 'verification_token')
    op.drop_column('users', 'is_verified')
