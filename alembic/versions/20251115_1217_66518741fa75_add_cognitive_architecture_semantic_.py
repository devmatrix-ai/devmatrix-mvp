"""add_cognitive_architecture_semantic_fields

Revision ID: 66518741fa75
Revises: 5d9a2bf7565b
Create Date: 2025-11-15 12:17:52.582694

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '66518741fa75'
down_revision = '5d9a2bf7565b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add cognitive architecture fields to masterplan_subtasks table.

    Note: In MGE V2, subtasks are the atomic units of code generation.

    Task 0.3.1: Semantic Signature Fields
    - semantic_hash: Hash of semantic task signature
    - semantic_purpose: Task purpose description
    - semantic_domain: Domain category (auth, api, database, ui, etc.)
    - Index on semantic_hash for fast lookup

    Task 0.3.2: Pattern Bank Metadata
    - pattern_similarity_score: Cosine similarity score from pattern bank
    - pattern_matched_from_id: Reference to matched pattern
    - first_pass_success: Whether first inference attempt succeeded
    - validation_timestamp: When validation was performed
    """
    # Task 0.3.1: Semantic signature fields
    op.add_column('masterplan_subtasks', sa.Column('semantic_hash', sa.String(64), nullable=True))
    op.add_column('masterplan_subtasks', sa.Column('semantic_purpose', sa.Text(), nullable=True))
    op.add_column('masterplan_subtasks', sa.Column('semantic_domain', sa.String(50), nullable=True))

    # Task 0.3.2: Pattern bank metadata
    op.add_column('masterplan_subtasks', sa.Column('pattern_similarity_score', sa.Float(), nullable=True))
    op.add_column('masterplan_subtasks', sa.Column('pattern_matched_from_id', sa.String(255), nullable=True))
    op.add_column('masterplan_subtasks', sa.Column('first_pass_success', sa.Boolean(), nullable=True, default=False))
    op.add_column('masterplan_subtasks', sa.Column('validation_timestamp', sa.DateTime(), nullable=True))

    # Create index on semantic_hash for fast lookup
    op.create_index('idx_subtask_semantic_hash', 'masterplan_subtasks', ['semantic_hash'])


def downgrade() -> None:
    """Remove cognitive architecture fields from masterplan_subtasks table."""
    # Drop index
    op.drop_index('idx_subtask_semantic_hash', table_name='masterplan_subtasks')

    # Drop pattern bank metadata columns (Task 0.3.2)
    op.drop_column('masterplan_subtasks', 'validation_timestamp')
    op.drop_column('masterplan_subtasks', 'first_pass_success')
    op.drop_column('masterplan_subtasks', 'pattern_matched_from_id')
    op.drop_column('masterplan_subtasks', 'pattern_similarity_score')

    # Drop semantic signature columns (Task 0.3.1)
    op.drop_column('masterplan_subtasks', 'semantic_domain')
    op.drop_column('masterplan_subtasks', 'semantic_purpose')
    op.drop_column('masterplan_subtasks', 'semantic_hash')
