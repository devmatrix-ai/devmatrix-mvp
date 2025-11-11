"""Merge migration heads

Revision ID: 1a290de30226
Revises: 20251031_0801_create_masterplan_milestones, 20251104_1140
Create Date: 2025-11-11 12:25:24.887997

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1a290de30226'
down_revision = ('20251031_0801_create_masterplan_milestones', '20251104_1140')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
