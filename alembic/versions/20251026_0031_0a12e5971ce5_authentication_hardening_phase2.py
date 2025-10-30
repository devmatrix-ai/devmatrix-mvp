"""authentication_hardening_phase2

Revision ID: 0a12e5971ce5
Revises: 6caa818c486e
Create Date: 2025-10-26 00:31:45.943290

Phase 2 - Task Group 1: Database Schema - Authentication Extensions
Extends users table with authentication hardening fields:
- password_last_changed: Track when password was last changed
- legacy_password: Flag users with passwords that predate new complexity policy
- failed_login_attempts: Counter for failed login attempts (account lockout)
- locked_until: Timestamp when account lockout expires
- last_failed_login: Timestamp of most recent failed login attempt

Indexes:
- idx_users_locked_until: For efficient auto-unlock background job queries
- idx_users_legacy_password: For efficient queries of users requiring password update

Default values:
- legacy_password=TRUE for existing users (grandfather clause)
- legacy_password=FALSE for new users (via model default)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0a12e5971ce5'
down_revision = '6caa818c486e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add authentication hardening fields to users table"""

    # Add password_last_changed column
    # NULL allowed for existing users who haven't changed password yet
    op.add_column('users', sa.Column(
        'password_last_changed',
        sa.TIMESTAMP(timezone=True),
        nullable=True
    ))

    # Add legacy_password flag
    # Default TRUE for existing users (grandfathered)
    # New users will get FALSE from model default
    op.add_column('users', sa.Column(
        'legacy_password',
        sa.Boolean(),
        nullable=False,
        server_default='true'
    ))

    # Add failed_login_attempts counter
    # Defaults to 0 for all users
    op.add_column('users', sa.Column(
        'failed_login_attempts',
        sa.Integer(),
        nullable=False,
        server_default='0'
    ))

    # Add locked_until timestamp
    # NULL when account is not locked
    op.add_column('users', sa.Column(
        'locked_until',
        sa.TIMESTAMP(timezone=True),
        nullable=True
    ))

    # Add last_failed_login timestamp
    # NULL when no failed attempts yet
    op.add_column('users', sa.Column(
        'last_failed_login',
        sa.TIMESTAMP(timezone=True),
        nullable=True
    ))

    # Create index on locked_until for auto-unlock job queries
    # Query pattern: WHERE locked_until IS NOT NULL AND locked_until <= NOW()
    op.create_index(
        'idx_users_locked_until',
        'users',
        ['locked_until'],
        unique=False
    )

    # Create index on legacy_password for user notification queries
    # Query pattern: WHERE legacy_password = TRUE
    op.create_index(
        'idx_users_legacy_password',
        'users',
        ['legacy_password'],
        unique=False
    )


def downgrade() -> None:
    """Remove authentication hardening fields from users table"""

    # Drop indexes first
    op.drop_index('idx_users_legacy_password', table_name='users')
    op.drop_index('idx_users_locked_until', table_name='users')

    # Drop columns in reverse order
    op.drop_column('users', 'last_failed_login')
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
    op.drop_column('users', 'legacy_password')
    op.drop_column('users', 'password_last_changed')
