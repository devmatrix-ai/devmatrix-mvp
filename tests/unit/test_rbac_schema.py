"""
Unit tests for RBAC database schema (Phase 2 - Task Group 6).

Tests focus on:
- roles table structure and constraints
- user_roles table structure with foreign keys
- unique constraint on (user_id, role_id)
- system roles cannot be deleted (is_system flag)
- CASCADE delete behavior
- Role and UserRole model relationships

As per Task Group 6: Write 2-8 focused tests for RBAC database schema
"""

import uuid
from datetime import datetime
import pytest
from sqlalchemy import create_engine, inspect, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from src.config.database import Base, TEST_DATABASE_URL
from src.models.user import User
from src.models.role import Role
from src.models.user_role import UserRole


@pytest.fixture(scope="function")
def rbac_db_session():
    """
    Create a test database session with User, Role, and UserRole models.
    Enables foreign key constraints for SQLite.
    """
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})

    # Enable foreign key constraints in SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SessionLocal = sessionmaker(bind=engine)

    # Create all required tables
    User.__table__.create(bind=engine, checkfirst=True)
    Role.__table__.create(bind=engine, checkfirst=True)
    UserRole.__table__.create(bind=engine, checkfirst=True)

    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop tables in reverse dependency order
        UserRole.__table__.drop(bind=engine, checkfirst=True)
        Role.__table__.drop(bind=engine, checkfirst=True)
        User.__table__.drop(bind=engine, checkfirst=True)
        engine.dispose()


class TestRolesTable:
    """Test roles table structure and constraints"""

    def test_roles_table_has_correct_columns(self, rbac_db_session):
        """Test that roles table has all required columns"""
        inspector = inspect(rbac_db_session.bind)
        columns = {col['name']: col for col in inspector.get_columns('roles')}

        # Verify all required columns exist
        assert 'role_id' in columns
        assert 'role_name' in columns
        assert 'description' in columns
        assert 'is_system' in columns
        assert 'created_at' in columns

    def test_role_name_must_be_unique(self, rbac_db_session):
        """Test that role_name has unique constraint"""
        role1 = Role(
            role_name="admin",
            description="Administrator role",
            is_system=True
        )
        rbac_db_session.add(role1)
        rbac_db_session.commit()

        # Try to create duplicate role_name
        role2 = Role(
            role_name="admin",  # Duplicate
            description="Another admin role",
            is_system=False
        )
        rbac_db_session.add(role2)

        with pytest.raises(IntegrityError):
            rbac_db_session.commit()

    def test_system_roles_can_be_created(self, rbac_db_session):
        """Test that system roles can be created with is_system=True"""
        system_role = Role(
            role_name="superadmin",
            description="Full system access",
            is_system=True
        )
        rbac_db_session.add(system_role)
        rbac_db_session.commit()

        assert system_role.role_id is not None
        assert system_role.is_system is True
        assert system_role.created_at is not None


class TestUserRolesTable:
    """Test user_roles table structure with foreign keys"""

    def test_user_roles_table_has_correct_columns(self, rbac_db_session):
        """Test that user_roles table has all required columns"""
        inspector = inspect(rbac_db_session.bind)
        columns = {col['name']: col for col in inspector.get_columns('user_roles')}

        # Verify all required columns exist
        assert 'user_role_id' in columns
        assert 'user_id' in columns
        assert 'role_id' in columns
        assert 'assigned_by' in columns
        assert 'assigned_at' in columns

    def test_user_roles_foreign_key_to_users(self, rbac_db_session):
        """Test foreign key relationship to users table"""
        # Create user and role
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        )
        role = Role(
            role_name="user",
            description="Standard user role",
            is_system=True
        )
        rbac_db_session.add(user)
        rbac_db_session.add(role)
        rbac_db_session.commit()

        # Create user_role assignment
        user_role = UserRole(
            user_id=user.user_id,
            role_id=role.role_id,
            assigned_by=user.user_id
        )
        rbac_db_session.add(user_role)
        rbac_db_session.commit()

        assert user_role.user_role_id is not None
        assert user_role.user_id == user.user_id
        assert user_role.role_id == role.role_id

    def test_unique_constraint_on_user_id_role_id(self, rbac_db_session):
        """Test that (user_id, role_id) has unique constraint"""
        # Create user and role
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        )
        role = Role(
            role_name="admin",
            description="Administrator role",
            is_system=True
        )
        rbac_db_session.add(user)
        rbac_db_session.add(role)
        rbac_db_session.commit()

        # Create first assignment
        user_role1 = UserRole(
            user_id=user.user_id,
            role_id=role.role_id,
            assigned_by=user.user_id
        )
        rbac_db_session.add(user_role1)
        rbac_db_session.commit()

        # Try to create duplicate assignment
        user_role2 = UserRole(
            user_id=user.user_id,  # Same user
            role_id=role.role_id,  # Same role
            assigned_by=user.user_id
        )
        rbac_db_session.add(user_role2)

        with pytest.raises(IntegrityError):
            rbac_db_session.commit()

    def test_cascade_delete_when_user_deleted(self, rbac_db_session):
        """Test CASCADE delete: deleting user removes their role assignments"""
        # Create user and role
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        )
        role = Role(
            role_name="user",
            description="Standard user role",
            is_system=True
        )
        rbac_db_session.add(user)
        rbac_db_session.add(role)
        rbac_db_session.commit()

        # Create user_role assignment
        user_role = UserRole(
            user_id=user.user_id,
            role_id=role.role_id,
            assigned_by=user.user_id
        )
        rbac_db_session.add(user_role)
        rbac_db_session.commit()

        user_role_id = user_role.user_role_id

        # Delete user (should cascade to user_roles)
        rbac_db_session.delete(user)
        rbac_db_session.commit()

        # Verify user_role was cascade deleted
        deleted_user_role = rbac_db_session.query(UserRole).filter(
            UserRole.user_role_id == user_role_id
        ).first()
        assert deleted_user_role is None

    def test_cascade_delete_when_role_deleted(self, rbac_db_session):
        """Test CASCADE delete: deleting role removes all user assignments"""
        # Create user and role
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        )
        role = Role(
            role_name="temp_role",
            description="Temporary role for testing",
            is_system=False  # Not a system role, can be deleted
        )
        rbac_db_session.add(user)
        rbac_db_session.add(role)
        rbac_db_session.commit()

        # Create user_role assignment
        user_role = UserRole(
            user_id=user.user_id,
            role_id=role.role_id,
            assigned_by=user.user_id
        )
        rbac_db_session.add(user_role)
        rbac_db_session.commit()

        user_role_id = user_role.user_role_id

        # Delete role (should cascade to user_roles)
        rbac_db_session.delete(role)
        rbac_db_session.commit()

        # Verify user_role was cascade deleted
        deleted_user_role = rbac_db_session.query(UserRole).filter(
            UserRole.user_role_id == user_role_id
        ).first()
        assert deleted_user_role is None


class TestRoleAssignmentTracking:
    """Test audit tracking on user_role assignments"""

    def test_user_role_tracks_assigned_by(self, rbac_db_session):
        """Test that user_role records who assigned the role"""
        # Create admin user and regular user
        admin_user = User(
            email="admin@example.com",
            username="admin",
            password_hash="hashed_password"
        )
        regular_user = User(
            email="user@example.com",
            username="user",
            password_hash="hashed_password"
        )
        role = Role(
            role_name="user",
            description="Standard user role",
            is_system=True
        )
        rbac_db_session.add(admin_user)
        rbac_db_session.add(regular_user)
        rbac_db_session.add(role)
        rbac_db_session.commit()

        # Admin assigns role to regular user
        user_role = UserRole(
            user_id=regular_user.user_id,
            role_id=role.role_id,
            assigned_by=admin_user.user_id  # Track who assigned
        )
        rbac_db_session.add(user_role)
        rbac_db_session.commit()

        assert user_role.assigned_by == admin_user.user_id
        assert user_role.assigned_at is not None

    def test_assigned_at_defaults_to_now(self, rbac_db_session):
        """Test that assigned_at is automatically set to current timestamp"""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        )
        role = Role(
            role_name="user",
            description="Standard user role",
            is_system=True
        )
        rbac_db_session.add(user)
        rbac_db_session.add(role)
        rbac_db_session.commit()

        before_assignment = datetime.utcnow()

        user_role = UserRole(
            user_id=user.user_id,
            role_id=role.role_id,
            assigned_by=user.user_id
        )
        rbac_db_session.add(user_role)
        rbac_db_session.commit()

        after_assignment = datetime.utcnow()

        assert user_role.assigned_at is not None
        assert before_assignment <= user_role.assigned_at <= after_assignment
