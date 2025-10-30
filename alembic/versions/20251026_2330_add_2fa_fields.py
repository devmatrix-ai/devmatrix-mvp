"""add_2fa_fields

Revision ID: 20251026_2330
Revises: 20251026_2159
Create Date: 2025-10-26 23:30:00.000000

Phase 2 Task Group 9: Add 2FA/MFA (TOTP) fields to users table.

Adds:
- totp_secret: Encrypted TOTP secret for 2FA
- totp_enabled: Flag indicating if user has 2FA enabled
- totp_backup_codes: JSONB array of hashed backup codes
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251026_2330'
down_revision: Union[str, None] = '20251026_2159'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add 2FA/MFA fields to users table.

    Fields:
    - totp_secret: TEXT (encrypted TOTP secret, NULL if 2FA not enabled)
    - totp_enabled: BOOLEAN (default FALSE, indicates if 2FA is active)
    - totp_backup_codes: JSONB (array of hashed backup codes, NULL if 2FA not enabled)
    """
    # Add totp_secret column (encrypted TOTP secret)
    op.add_column(
        'users',
        sa.Column('totp_secret', sa.TEXT(), nullable=True)
    )

    # Add totp_enabled column (flag for 2FA status)
    op.add_column(
        'users',
        sa.Column(
            'totp_enabled',
            sa.BOOLEAN(),
            nullable=False,
            server_default='false'
        )
    )

    # Add totp_backup_codes column (JSONB array of hashed codes)
    op.add_column(
        'users',
        sa.Column(
            'totp_backup_codes',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True
        )
    )

    # Add index on totp_enabled for faster queries
    op.create_index(
        'idx_users_totp_enabled',
        'users',
        ['totp_enabled'],
        unique=False
    )

    print("✓ Added 2FA/MFA fields to users table")
    print("  - totp_secret (TEXT, nullable, encrypted)")
    print("  - totp_enabled (BOOLEAN, default FALSE)")
    print("  - totp_backup_codes (JSONB, nullable)")
    print("  - idx_users_totp_enabled (index)")


def downgrade() -> None:
    """
    Remove 2FA/MFA fields from users table.
    """
    # Drop index
    op.drop_index('idx_users_totp_enabled', table_name='users')

    # Drop columns
    op.drop_column('users', 'totp_backup_codes')
    op.drop_column('users', 'totp_enabled')
    op.drop_column('users', 'totp_secret')

    print("✓ Removed 2FA/MFA fields from users table")
