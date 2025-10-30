"""create_rbac_tables

Revision ID: 15c544aaf40b
Revises: 0a12e5971ce5
Create Date: 2025-10-26 11:25:36.871933

Phase 2 - Task Group 6: Database Schema - RBAC Tables
Creates roles and user_roles tables for Role-Based Access Control (RBAC).

Tables:
- roles: System and custom roles (superadmin, admin, user, viewer)
- user_roles: Many-to-many user-role assignments with audit tracking

System Roles (seeded with is_system=TRUE):
- superadmin: Full system access, cannot be deleted
- admin: Manage users, view all conversations, access audit logs
- user: Full CRUD on own resources, share conversations
- viewer: Read-only access to shared resources

Indexes:
- idx_roles_name: Fast role name lookups
- idx_user_roles_user_id: Fast user-based role queries
- idx_user_roles_role_id: Fast role-based user queries

Constraints:
- UNIQUE(user_id, role_id): Prevent duplicate role assignments
- CASCADE delete on user_id and role_id
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '15c544aaf40b'
down_revision = '0a12e5971ce5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create roles and user_roles tables, seed system roles"""

    # Create roles table
    op.create_table(
        'roles',
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_name', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('role_id'),
        sa.UniqueConstraint('role_name', name='uq_role_name')
    )

    # Create index on role_name for fast lookups
    op.create_index('idx_roles_name', 'roles', ['role_name'], unique=False)

    # Create user_roles table (many-to-many with audit tracking)
    op.create_table(
        'user_roles',
        sa.Column('user_role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('assigned_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('user_role_id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.role_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.user_id']),
        sa.UniqueConstraint('user_id', 'role_id', name='uq_user_role')
    )

    # Create indexes on user_roles for fast lookups
    op.create_index('idx_user_roles_user_id', 'user_roles', ['user_id'], unique=False)
    op.create_index('idx_user_roles_role_id', 'user_roles', ['role_id'], unique=False)

    # Seed 4 system roles
    # These roles are marked as is_system=TRUE and cannot be deleted
    # Note: We use gen_random_uuid() for role_id (available in PostgreSQL 13+)
    # Alternative: uuid_generate_v4() requires uuid-ossp extension
    op.execute("""
        INSERT INTO roles (role_id, role_name, description, is_system, created_at)
        VALUES
            (gen_random_uuid(), 'superadmin', 'Full system access', TRUE, NOW()),
            (gen_random_uuid(), 'admin', 'Manage users and view all conversations', TRUE, NOW()),
            (gen_random_uuid(), 'user', 'Full access to own resources', TRUE, NOW()),
            (gen_random_uuid(), 'viewer', 'Read-only access to shared resources', TRUE, NOW())
    """)


def downgrade() -> None:
    """Remove roles and user_roles tables"""

    # Drop indexes first
    op.drop_index('idx_user_roles_role_id', table_name='user_roles')
    op.drop_index('idx_user_roles_user_id', table_name='user_roles')
    op.drop_index('idx_roles_name', table_name='roles')

    # Drop tables in reverse dependency order
    op.drop_table('user_roles')
    op.drop_table('roles')
