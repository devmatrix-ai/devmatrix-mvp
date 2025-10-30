"""add workspace_path to masterplans

Revision ID: 20251028_1315
Revises: 8fe2fe1d893a
Create Date: 2025-10-28 13:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251028_1315'
down_revision = '8fe2fe1d893a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add workspace_path column to masterplans table (if it exists)
    op.execute("""
        ALTER TABLE IF EXISTS masterplans ADD COLUMN IF NOT EXISTS
        workspace_path VARCHAR(500) DEFAULT NULL;
    """)


def downgrade() -> None:
    # Remove workspace_path column from masterplans table
    op.drop_column('masterplans', 'workspace_path')
