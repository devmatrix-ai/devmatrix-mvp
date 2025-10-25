"""Add acceptance tests tables (already applied manually)

Revision ID: a4c5ea0ab4a9
Revises: mge_v2_schema
Create Date: 2025-10-25 01:20:45.101985

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a4c5ea0ab4a9'
down_revision = 'mge_v2_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tables already created manually via SQL
    # This migration documents the schema changes for acceptance tests

    # acceptance_tests table with columns:
    # - test_id (UUID PRIMARY KEY)
    # - masterplan_id (UUID NOT NULL)
    # - requirement_text (TEXT NOT NULL)
    # - requirement_priority (VARCHAR(10) CHECK IN ('must', 'should'))
    # - test_code (TEXT NOT NULL)
    # - test_language (VARCHAR(20) NOT NULL)
    # - timeout_seconds (INTEGER DEFAULT 30)
    # - created_at (TIMESTAMP NOT NULL DEFAULT NOW())

    # acceptance_test_results table with columns:
    # - result_id (UUID PRIMARY KEY)
    # - test_id (UUID FK to acceptance_tests)
    # - wave_id (UUID nullable)
    # - status (VARCHAR(20) CHECK IN ('pass', 'fail', 'timeout', 'error'))
    # - execution_time (TIMESTAMP NOT NULL DEFAULT NOW())
    # - execution_duration_ms (INTEGER)
    # - error_message (TEXT)
    # - stdout (TEXT)
    # - stderr (TEXT)

    pass


def downgrade() -> None:
    # Drop tables in reverse order (respecting FK constraints)
    op.execute("DROP TABLE IF EXISTS acceptance_test_results CASCADE")
    op.execute("DROP TABLE IF EXISTS acceptance_tests CASCADE")
