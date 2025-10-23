"""modify discovery_documents.user_id to UUID FK

Revision ID: 20251022_1351_discovery_documents_user_id_fk
Revises: 20251022_1350_masterplans_user_id_fk
Create Date: 2025-10-22 13:51:00.000000

Task 1.2.6: Modify discovery_documents.user_id to UUID FK
- Alter column type from String to UUID
- Add FK constraint to users.user_id with ON DELETE CASCADE
- Add index on user_id

WARNING: This will delete all existing discovery documents if they have non-UUID user_id values
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251022_1351_discovery_documents_user_id_fk'
down_revision: Union[str, None] = '20251022_1350_masterplans_user_id_fk'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Modify discovery_documents.user_id to UUID FK.

    WARNING: This assumes a fresh start. If there's existing data with non-UUID user_id,
    you should either:
    1. Truncate the table first, OR
    2. Update existing rows to valid UUID values before running this migration
    """
    # Drop the existing index if it exists
    op.drop_index('idx_discovery_user', table_name='discovery_documents', if_exists=True)

    # Alter column type from String to UUID
    # Using CAST to convert existing String values to UUID
    # If existing values are not valid UUIDs, this will fail
    op.alter_column(
        'discovery_documents',
        'user_id',
        existing_type=sa.String(length=100),
        type_=postgresql.UUID(as_uuid=True),
        existing_nullable=False,
        postgresql_using='user_id::uuid'
    )

    # Add foreign key constraint to users table
    op.create_foreign_key(
        'fk_discovery_documents_user_id',
        'discovery_documents',
        'users',
        ['user_id'],
        ['user_id'],
        ondelete='CASCADE'
    )

    # Recreate index on user_id
    op.create_index('idx_discovery_user', 'discovery_documents', ['user_id'], unique=False)


def downgrade() -> None:
    """Revert discovery_documents.user_id to String."""
    # Drop the index
    op.drop_index('idx_discovery_user', table_name='discovery_documents')

    # Drop foreign key constraint
    op.drop_constraint('fk_discovery_documents_user_id', 'discovery_documents', type_='foreignkey')

    # Convert UUID back to String
    op.alter_column(
        'discovery_documents',
        'user_id',
        existing_type=postgresql.UUID(as_uuid=True),
        type_=sa.String(length=100),
        existing_nullable=False,
        postgresql_using='user_id::text'
    )

    # Recreate original index
    op.create_index('idx_discovery_user', 'discovery_documents', ['user_id'], unique=False)
