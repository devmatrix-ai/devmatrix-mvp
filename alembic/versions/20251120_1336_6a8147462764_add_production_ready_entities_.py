"""Add production-ready entities (TaskEntity, ProductEntity)

Revision ID: 6a8147462764
Revises: 66518741fa75
Create Date: 2025-11-20 13:36:00.363960

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '6a8147462764'
down_revision = '66518741fa75'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add production-ready entities (TaskEntity, ProductEntity).

    NOTE: This migration only adds new tables for production-ready code generation.
    Existing tables (users, masterplans, etc.) are intentionally preserved.
    """
    # Create products table
    op.create_table('products',
        sa.Column('id', sa.UUID(), nullable=False, comment='Unique product identifier (UUID)'),
        sa.Column('sku', sa.String(length=50), nullable=False, comment='Stock Keeping Unit (unique product code)'),
        sa.Column('name', sa.String(length=200), nullable=False, comment='Product name'),
        sa.Column('description', sa.Text(), nullable=True, comment='Product description'),
        sa.Column('price_cents', sa.Integer(), nullable=False, comment='Price in cents (avoid floating point issues)'),
        sa.Column('stock_quantity', sa.Integer(), nullable=False, comment='Current stock quantity'),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='Product active status (soft delete)'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='Timestamp when product was created (UTC)'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, comment='Timestamp when product was last updated (UTC)'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_products_active_stock', 'products', ['is_active', 'stock_quantity'], unique=False)
    op.create_index(op.f('ix_products_is_active'), 'products', ['is_active'], unique=False)
    op.create_index(op.f('ix_products_name'), 'products', ['name'], unique=False)
    op.create_index('ix_products_name_active', 'products', ['name', 'is_active'], unique=False)
    op.create_index(op.f('ix_products_sku'), 'products', ['sku'], unique=True)

    # Create tasks table
    op.create_table('tasks',
        sa.Column('id', sa.UUID(), nullable=False, comment='Unique task identifier (UUID)'),
        sa.Column('title', sa.String(length=200), nullable=False, comment='Task title (max 200 chars)'),
        sa.Column('description', sa.Text(), nullable=True, comment='Detailed task description'),
        sa.Column('completed', sa.Boolean(), nullable=False, comment='Task completion status'),
        sa.Column('priority', sa.Integer(), nullable=True, comment='Task priority (0=low, 1=medium, 2=high)'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='Timestamp when task was created (UTC)'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, comment='Timestamp when task was last updated (UTC)'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tasks_completed'), 'tasks', ['completed'], unique=False)
    op.create_index('ix_tasks_completed_created', 'tasks', ['completed', 'created_at'], unique=False)
    op.create_index('ix_tasks_priority_completed', 'tasks', ['priority', 'completed'], unique=False)
    op.create_index(op.f('ix_tasks_title'), 'tasks', ['title'], unique=False)


def downgrade() -> None:
    """
    Rollback production-ready entities.

    Removes products and tasks tables.
    """
    op.drop_index(op.f('ix_tasks_title'), table_name='tasks')
    op.drop_index('ix_tasks_priority_completed', table_name='tasks')
    op.drop_index('ix_tasks_completed_created', table_name='tasks')
    op.drop_index(op.f('ix_tasks_completed'), table_name='tasks')
    op.drop_table('tasks')
    
    op.drop_index(op.f('ix_products_sku'), table_name='products')
    op.drop_index('ix_products_name_active', table_name='products')
    op.drop_index(op.f('ix_products_name'), table_name='products')
    op.drop_index(op.f('ix_products_is_active'), table_name='products')
    op.drop_index('ix_products_active_stock', table_name='products')
    op.drop_table('products')
