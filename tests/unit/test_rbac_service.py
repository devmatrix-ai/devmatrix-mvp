"""
Unit Tests for RBAC Service

Tests role-based access control including role assignment, permission checking,
and role hierarchy enforcement.

Phase 2 - Task Group 7: Role-Based Access Control (RBAC) Service
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from src.services.rbac_service import RBACService
from src.models.user import User
from src.models.role import Role
from src.models.user_role import UserRole


@pytest.fixture
def rbac_service():
    """Create RBACService instance"""
    return RBACService()


@pytest.fixture
def mock_db():
    """Mock database session"""
    return MagicMock(spec=Session)


@pytest.fixture
def sample_user():
    """Create sample user"""
    return User(
        user_id=uuid.uuid4(),
        email="test@example.com",
        username="testuser",
        password_hash="hashed_password",
        is_active=True,
        is_superuser=False
    )


@pytest.fixture
def superadmin_user():
    """Create superadmin user"""
    return User(
        user_id=uuid.uuid4(),
        email="admin@example.com",
        username="admin",
        password_hash="hashed_password",
        is_active=True,
        is_superuser=True
    )


@pytest.fixture
def system_roles():
    """Create system roles"""
    return {
        "superadmin": Role(
            role_id=uuid.uuid4(),
            role_name="superadmin",
            description="Full system access",
            is_system=True,
            created_at=datetime.utcnow()
        ),
        "admin": Role(
            role_id=uuid.uuid4(),
            role_name="admin",
            description="Manage users and view audit logs",
            is_system=True,
            created_at=datetime.utcnow()
        ),
        "user": Role(
            role_id=uuid.uuid4(),
            role_name="user",
            description="Standard user access",
            is_system=True,
            created_at=datetime.utcnow()
        ),
        "viewer": Role(
            role_id=uuid.uuid4(),
            role_name="viewer",
            description="Read-only access",
            is_system=True,
            created_at=datetime.utcnow()
        )
    }


# ============================================================================
# Test user_has_role()
# ============================================================================

def test_user_has_role_returns_true_when_user_has_role(rbac_service, mock_db, sample_user, system_roles):
    """Test user_has_role returns True when user has the specified role"""
    user_role = UserRole(
        user_role_id=uuid.uuid4(),
        user_id=sample_user.user_id,
        role_id=system_roles["user"].role_id,
        assigned_at=datetime.utcnow()
    )

    with patch('src.services.rbac_service.get_db_context') as mock_get_db:
        mock_get_db.return_value.__enter__.return_value = mock_db

        # Mock query chain
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.join.return_value.filter.return_value.filter.return_value
        mock_filter.first.return_value = user_role

        result = rbac_service.user_has_role(sample_user.user_id, "user")

        assert result is True


def test_user_has_role_returns_false_when_user_lacks_role(rbac_service, mock_db, sample_user):
    """Test user_has_role returns False when user doesn't have the specified role"""
    with patch('src.services.rbac_service.get_db_context') as mock_get_db:
        mock_get_db.return_value.__enter__.return_value = mock_db

        # Mock query chain - no role found
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.join.return_value.filter.return_value.filter.return_value
        mock_filter.first.return_value = None

        result = rbac_service.user_has_role(sample_user.user_id, "admin")

        assert result is False


def test_user_has_role_checks_all_four_roles(rbac_service, mock_db, sample_user):
    """Test user_has_role works for all 4 system roles"""
    roles = ["superadmin", "admin", "user", "viewer"]

    with patch('src.services.rbac_service.get_db_context') as mock_get_db:
        mock_get_db.return_value.__enter__.return_value = mock_db

        for role_name in roles:
            # Mock no role found
            mock_query = mock_db.query.return_value
            mock_filter = mock_query.join.return_value.filter.return_value.filter.return_value
            mock_filter.first.return_value = None

            result = rbac_service.user_has_role(sample_user.user_id, role_name)
            assert result is False


# ============================================================================
# Test assign_role()
# ============================================================================

def test_assign_role_creates_user_role_assignment(rbac_service, mock_db, sample_user, superadmin_user, system_roles):
    """Test assign_role creates a new user role assignment"""
    with patch('src.services.rbac_service.get_db_context') as mock_get_db:
        mock_get_db.return_value.__enter__.return_value = mock_db

        # Mock role lookup
        mock_query = mock_db.query.return_value
        mock_query.filter.return_value.first.return_value = system_roles["user"]

        # Mock existing assignment check (none exists)
        mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = None

        with patch('src.observability.audit_logger.AuditLogger.log_event') as mock_audit:
            result = rbac_service.assign_role(
                user_id=sample_user.user_id,
                role_name="user",
                assigned_by_user_id=superadmin_user.user_id
            )

        # Verify database operations
        assert mock_db.add.called
        assert mock_db.commit.called
        assert mock_db.refresh.called


def test_assign_role_logs_audit_event(rbac_service, mock_db, sample_user, superadmin_user, system_roles):
    """Test assign_role logs audit event with assigned_by tracking"""
    with patch('src.services.rbac_service.get_db_context') as mock_get_db:
        mock_get_db.return_value.__enter__.return_value = mock_db

        # Mock role lookup
        mock_query = mock_db.query.return_value
        mock_query.filter.return_value.first.return_value = system_roles["user"]

        # Mock existing assignment check (none exists)
        mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = None

        with patch('src.observability.audit_logger.AuditLogger.log_event') as mock_audit:
            rbac_service.assign_role(
                user_id=sample_user.user_id,
                role_name="user",
                assigned_by_user_id=superadmin_user.user_id
            )

            # Verify audit log was called
            mock_audit.assert_called_once()
            call_kwargs = mock_audit.call_args[1]
            assert call_kwargs['action'] == "role_assigned"
            assert call_kwargs['result'] == "success"
            assert call_kwargs['user_id'] == superadmin_user.user_id
            assert call_kwargs['metadata']['target_user_id'] == str(sample_user.user_id)
            assert call_kwargs['metadata']['role_name'] == "user"


def test_assign_role_raises_error_if_role_not_found(rbac_service, mock_db, sample_user, superadmin_user):
    """Test assign_role raises ValueError if role doesn't exist"""
    with patch('src.services.rbac_service.get_db_context') as mock_get_db:
        mock_get_db.return_value.__enter__.return_value = mock_db

        # Mock role lookup - role not found
        mock_query = mock_db.query.return_value
        mock_query.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Role 'nonexistent' not found"):
            rbac_service.assign_role(
                user_id=sample_user.user_id,
                role_name="nonexistent",
                assigned_by_user_id=superadmin_user.user_id
            )


def test_assign_role_raises_error_if_already_assigned(rbac_service, mock_db, sample_user, superadmin_user, system_roles):
    """Test assign_role raises ValueError if role already assigned"""
    existing_assignment = UserRole(
        user_role_id=uuid.uuid4(),
        user_id=sample_user.user_id,
        role_id=system_roles["user"].role_id,
        assigned_at=datetime.utcnow()
    )

    with patch('src.services.rbac_service.get_db_context') as mock_get_db:
        mock_get_db.return_value.__enter__.return_value = mock_db

        # Mock role lookup
        mock_db.query.return_value.filter.return_value.first.return_value = system_roles["user"]

        # Mock existing assignment check (already exists)
        mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = existing_assignment

        with pytest.raises(ValueError, match="User already has role 'user'"):
            rbac_service.assign_role(
                user_id=sample_user.user_id,
                role_name="user",
                assigned_by_user_id=superadmin_user.user_id
            )


# ============================================================================
# Test remove_role()
# ============================================================================

def test_remove_role_deletes_user_role_assignment(rbac_service, mock_db, sample_user, superadmin_user, system_roles):
    """Test remove_role deletes user role assignment"""
    existing_assignment = UserRole(
        user_role_id=uuid.uuid4(),
        user_id=sample_user.user_id,
        role_id=system_roles["viewer"].role_id,
        assigned_at=datetime.utcnow()
    )

    with patch('src.services.rbac_service.get_db_context') as mock_get_db:
        mock_get_db.return_value.__enter__.return_value = mock_db

        # Mock role lookup
        mock_db.query.return_value.filter.return_value.first.return_value = system_roles["viewer"]

        # Mock existing assignment lookup
        mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = existing_assignment

        with patch('src.observability.audit_logger.AuditLogger.log_event') as mock_audit:
            result = rbac_service.remove_role(
                user_id=sample_user.user_id,
                role_name="viewer",
                removed_by_user_id=superadmin_user.user_id
            )

        assert result is True
        assert mock_db.delete.called
        assert mock_db.commit.called


def test_remove_role_logs_audit_event(rbac_service, mock_db, sample_user, superadmin_user, system_roles):
    """Test remove_role logs audit event"""
    existing_assignment = UserRole(
        user_role_id=uuid.uuid4(),
        user_id=sample_user.user_id,
        role_id=system_roles["viewer"].role_id,
        assigned_at=datetime.utcnow()
    )

    with patch('src.services.rbac_service.get_db_context') as mock_get_db:
        mock_get_db.return_value.__enter__.return_value = mock_db

        # Mock role lookup
        mock_db.query.return_value.filter.return_value.first.return_value = system_roles["viewer"]

        # Mock existing assignment lookup
        mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = existing_assignment

        with patch('src.observability.audit_logger.AuditLogger.log_event') as mock_audit:
            rbac_service.remove_role(
                user_id=sample_user.user_id,
                role_name="viewer",
                removed_by_user_id=superadmin_user.user_id
            )

            # Verify audit log was called
            mock_audit.assert_called_once()
            call_kwargs = mock_audit.call_args[1]
            assert call_kwargs['action'] == "role_removed"
            assert call_kwargs['result'] == "success"


def test_remove_role_returns_false_if_not_assigned(rbac_service, mock_db, sample_user, superadmin_user, system_roles):
    """Test remove_role returns False if role not assigned to user"""
    with patch('src.services.rbac_service.get_db_context') as mock_get_db:
        mock_get_db.return_value.__enter__.return_value = mock_db

        # Mock role lookup
        mock_db.query.return_value.filter.return_value.first.return_value = system_roles["viewer"]

        # Mock no existing assignment
        mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = None

        result = rbac_service.remove_role(
            user_id=sample_user.user_id,
            role_name="viewer",
            removed_by_user_id=superadmin_user.user_id
        )

        assert result is False


# ============================================================================
# Test get_user_roles()
# ============================================================================

def test_get_user_roles_returns_all_user_roles(rbac_service, mock_db, sample_user, system_roles):
    """Test get_user_roles returns all roles assigned to user"""
    with patch('src.services.rbac_service.get_db_context') as mock_get_db:
        mock_get_db.return_value.__enter__.return_value = mock_db

        # Mock query to return user and viewer roles
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.join.return_value.filter.return_value
        mock_filter.all.return_value = [system_roles["user"], system_roles["viewer"]]

        result = rbac_service.get_user_roles(sample_user.user_id)

        assert len(result) == 2
        assert result[0].role_name == "user"
        assert result[1].role_name == "viewer"


def test_get_user_roles_returns_empty_list_if_no_roles(rbac_service, mock_db, sample_user):
    """Test get_user_roles returns empty list if user has no roles"""
    with patch('src.services.rbac_service.get_db_context') as mock_get_db:
        mock_get_db.return_value.__enter__.return_value = mock_db

        # Mock query to return no roles
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.join.return_value.filter.return_value
        mock_filter.all.return_value = []

        result = rbac_service.get_user_roles(sample_user.user_id)

        assert result == []


# ============================================================================
# Test get_role_permissions()
# ============================================================================

def test_get_role_permissions_returns_superadmin_wildcard(rbac_service):
    """Test get_role_permissions returns wildcard for superadmin"""
    permissions = rbac_service.get_role_permissions("superadmin")

    assert "*:*" in permissions
    assert len(permissions) == 1


def test_get_role_permissions_returns_admin_permissions(rbac_service):
    """Test get_role_permissions returns correct permissions for admin"""
    permissions = rbac_service.get_role_permissions("admin")

    assert "user:read" in permissions
    assert "user:write" in permissions
    assert "conversation:read" in permissions
    assert "audit:read" in permissions
    assert len(permissions) == 4


def test_get_role_permissions_returns_user_permissions(rbac_service):
    """Test get_role_permissions returns correct permissions for user"""
    permissions = rbac_service.get_role_permissions("user")

    assert "conversation:read" in permissions
    assert "conversation:write" in permissions
    assert "conversation:delete" in permissions
    assert "conversation:share" in permissions
    assert "message:read" in permissions
    assert "message:write" in permissions
    assert "message:delete" in permissions
    assert len(permissions) == 7


def test_get_role_permissions_returns_viewer_permissions(rbac_service):
    """Test get_role_permissions returns correct permissions for viewer"""
    permissions = rbac_service.get_role_permissions("viewer")

    assert "conversation:read" in permissions
    assert "message:read" in permissions
    assert len(permissions) == 2


def test_get_role_permissions_returns_empty_for_unknown_role(rbac_service):
    """Test get_role_permissions returns empty list for unknown role"""
    permissions = rbac_service.get_role_permissions("nonexistent")

    assert permissions == []


# ============================================================================
# Test user_has_permission()
# ============================================================================

def test_user_has_permission_returns_true_for_superadmin(rbac_service, mock_db, superadmin_user, system_roles):
    """Test user_has_permission returns True for superadmin (wildcard permissions)"""
    with patch('src.services.rbac_service.get_db_context') as mock_get_db:
        mock_get_db.return_value.__enter__.return_value = mock_db

        # Mock user has superadmin role
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.join.return_value.filter.return_value
        mock_filter.all.return_value = [system_roles["superadmin"]]

        result = rbac_service.user_has_permission(superadmin_user.user_id, "system:configure")

        assert result is True


def test_user_has_permission_returns_true_when_permission_granted(rbac_service, mock_db, sample_user, system_roles):
    """Test user_has_permission returns True when user has required permission"""
    with patch('src.services.rbac_service.get_db_context') as mock_get_db:
        mock_get_db.return_value.__enter__.return_value = mock_db

        # Mock user has admin role
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.join.return_value.filter.return_value
        mock_filter.all.return_value = [system_roles["admin"]]

        result = rbac_service.user_has_permission(sample_user.user_id, "user:read")

        assert result is True


def test_user_has_permission_returns_false_when_permission_denied(rbac_service, mock_db, sample_user, system_roles):
    """Test user_has_permission returns False when user lacks required permission"""
    with patch('src.services.rbac_service.get_db_context') as mock_get_db:
        mock_get_db.return_value.__enter__.return_value = mock_db

        # Mock user has viewer role (read-only)
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.join.return_value.filter.return_value
        mock_filter.all.return_value = [system_roles["viewer"]]

        result = rbac_service.user_has_permission(sample_user.user_id, "conversation:write")

        assert result is False


def test_user_has_permission_returns_false_when_no_roles(rbac_service, mock_db, sample_user):
    """Test user_has_permission returns False when user has no roles"""
    with patch('src.services.rbac_service.get_db_context') as mock_get_db:
        mock_get_db.return_value.__enter__.return_value = mock_db

        # Mock user has no roles
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.join.return_value.filter.return_value
        mock_filter.all.return_value = []

        result = rbac_service.user_has_permission(sample_user.user_id, "conversation:read")

        assert result is False


# ============================================================================
# Test can_assign_role() - Role Hierarchy Enforcement
# ============================================================================

def test_can_assign_role_superadmin_can_assign_any_role(rbac_service, mock_db, superadmin_user, system_roles):
    """Test superadmin can assign any role (including admin and superadmin)"""
    with patch('src.services.rbac_service.get_db_context') as mock_get_db:
        mock_get_db.return_value.__enter__.return_value = mock_db

        # Mock user has superadmin role
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.join.return_value.filter.return_value.filter.return_value
        mock_filter.first.return_value = UserRole(
            user_role_id=uuid.uuid4(),
            user_id=superadmin_user.user_id,
            role_id=system_roles["superadmin"].role_id
        )

        # Test all roles
        assert rbac_service.can_assign_role(superadmin_user.user_id, "superadmin") is True
        assert rbac_service.can_assign_role(superadmin_user.user_id, "admin") is True
        assert rbac_service.can_assign_role(superadmin_user.user_id, "user") is True
        assert rbac_service.can_assign_role(superadmin_user.user_id, "viewer") is True


def test_can_assign_role_admin_cannot_assign_admin_or_superadmin(rbac_service, mock_db, sample_user, system_roles):
    """Test admin cannot assign admin or superadmin roles"""
    with patch('src.services.rbac_service.get_db_context') as mock_get_db:
        mock_get_db.return_value.__enter__.return_value = mock_db

        # Mock user has admin role
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.join.return_value.filter.return_value.filter.return_value
        mock_filter.first.return_value = UserRole(
            user_role_id=uuid.uuid4(),
            user_id=sample_user.user_id,
            role_id=system_roles["admin"].role_id
        )

        # Admin can only assign user and viewer roles
        assert rbac_service.can_assign_role(sample_user.user_id, "superadmin") is False
        assert rbac_service.can_assign_role(sample_user.user_id, "admin") is False
        assert rbac_service.can_assign_role(sample_user.user_id, "user") is True
        assert rbac_service.can_assign_role(sample_user.user_id, "viewer") is True


def test_can_assign_role_user_cannot_assign_any_role(rbac_service, mock_db, sample_user, system_roles):
    """Test regular user cannot assign any roles"""
    with patch('src.services.rbac_service.get_db_context') as mock_get_db:
        mock_get_db.return_value.__enter__.return_value = mock_db

        # Mock user has user role
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.join.return_value.filter.return_value.filter.return_value
        mock_filter.first.return_value = UserRole(
            user_role_id=uuid.uuid4(),
            user_id=sample_user.user_id,
            role_id=system_roles["user"].role_id
        )

        # Regular user cannot assign any roles
        assert rbac_service.can_assign_role(sample_user.user_id, "superadmin") is False
        assert rbac_service.can_assign_role(sample_user.user_id, "admin") is False
        assert rbac_service.can_assign_role(sample_user.user_id, "user") is False
        assert rbac_service.can_assign_role(sample_user.user_id, "viewer") is False
