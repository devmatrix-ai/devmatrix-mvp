"""
Role-Based Access Control (RBAC) Service

Implements role assignment, permission checking, and role hierarchy enforcement.
Phase 2 - Task Group 7: Role-Based Access Control (RBAC) Service

Features:
- 4 hierarchical roles: superadmin > admin > user > viewer
- Many-to-many user-role relationships
- Permission mapping by role
- Audit logging for role assignments
- Role hierarchy enforcement
"""

import uuid
from typing import List, Optional
from datetime import datetime

from src.models.user import User
from src.models.role import Role
from src.models.user_role import UserRole
from src.config.database import get_db_context
from src.observability import get_logger
from src.observability.audit_logger import AuditLogger

logger = get_logger("rbac_service")


class RBACService:
    """
    RBAC Service for role and permission management.

    Role Hierarchy:
        superadmin > admin > user > viewer

    Permission Format:
        resource:action (e.g., "conversation:read")

    Permission Mappings:
        - superadmin: ["*:*"] (all permissions)
        - admin: ["user:read", "user:write", "conversation:read", "audit:read"]
        - user: ["conversation:read", "conversation:write", "conversation:delete",
                 "conversation:share", "message:read", "message:write", "message:delete"]
        - viewer: ["conversation:read", "message:read"]

    Usage:
        rbac = RBACService()

        # Assign role
        rbac.assign_role(user_id, "user", assigned_by_user_id)

        # Check role
        if rbac.user_has_role(user_id, "admin"):
            # Allow admin action

        # Check permission
        if rbac.user_has_permission(user_id, "conversation:write"):
            # Allow write operation
    """

    # Permission mappings for each role
    ROLE_PERMISSIONS = {
        "superadmin": ["*:*"],  # Wildcard - all permissions
        "admin": [
            "user:read",
            "user:write",
            "conversation:read",
            "audit:read"
        ],
        "user": [
            "conversation:read",
            "conversation:write",
            "conversation:delete",
            "conversation:share",
            "message:read",
            "message:write",
            "message:delete"
        ],
        "viewer": [
            "conversation:read",
            "message:read"
        ]
    }

    def assign_role(
        self,
        user_id: uuid.UUID,
        role_name: str,
        assigned_by_user_id: Optional[uuid.UUID] = None
    ) -> UserRole:
        """
        Assign a role to a user.

        Args:
            user_id: UUID of user to assign role to
            role_name: Name of role to assign
            assigned_by_user_id: UUID of user performing the assignment (None for system)

        Returns:
            UserRole object

        Raises:
            ValueError: If role doesn't exist or user already has role
        """
        try:
            with get_db_context() as db:
                # Find role by name
                role = db.query(Role).filter(Role.role_name == role_name).first()

                if not role:
                    logger.warning(f"Role assignment failed: Role '{role_name}' not found")
                    raise ValueError(f"Role '{role_name}' not found")

                # Check if user already has this role
                existing_assignment = db.query(UserRole).filter(
                    UserRole.user_id == user_id,
                    UserRole.role_id == role.role_id
                ).first()

                if existing_assignment:
                    logger.warning(
                        f"Role assignment failed: User {user_id} already has role '{role_name}'"
                    )
                    raise ValueError(f"User already has role '{role_name}'")

                # Create role assignment
                user_role = UserRole(
                    user_role_id=uuid.uuid4(),
                    user_id=user_id,
                    role_id=role.role_id,
                    assigned_by=assigned_by_user_id,
                    assigned_at=datetime.utcnow()
                )

                db.add(user_role)
                db.commit()
                db.refresh(user_role)

                logger.info(
                    f"Role assigned: {role_name} to user {user_id} "
                    f"by {assigned_by_user_id or 'system'}"
                )

                # Audit log the role assignment
                AuditLogger.log_event(
                    user_id=assigned_by_user_id,
                    action="role_assigned",
                    result="success",
                    resource_type="user_role",
                    resource_id=user_role.user_role_id,
                    metadata={
                        "target_user_id": str(user_id),
                        "role_name": role_name,
                        "assigned_by": str(assigned_by_user_id) if assigned_by_user_id else "system"
                    }
                )

                return user_role

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error assigning role: {str(e)}", exc_info=True)
            raise

    def remove_role(
        self,
        user_id: uuid.UUID,
        role_name: str,
        removed_by_user_id: Optional[uuid.UUID] = None
    ) -> bool:
        """
        Remove a role from a user.

        Args:
            user_id: UUID of user to remove role from
            role_name: Name of role to remove
            removed_by_user_id: UUID of user performing the removal (None for system)

        Returns:
            True if role was removed, False if user didn't have the role

        Raises:
            ValueError: If role doesn't exist
        """
        try:
            with get_db_context() as db:
                # Find role by name
                role = db.query(Role).filter(Role.role_name == role_name).first()

                if not role:
                    logger.warning(f"Role removal failed: Role '{role_name}' not found")
                    raise ValueError(f"Role '{role_name}' not found")

                # Find existing assignment
                user_role = db.query(UserRole).filter(
                    UserRole.user_id == user_id,
                    UserRole.role_id == role.role_id
                ).first()

                if not user_role:
                    logger.warning(
                        f"Role removal skipped: User {user_id} doesn't have role '{role_name}'"
                    )
                    return False

                # Delete assignment
                db.delete(user_role)
                db.commit()

                logger.info(
                    f"Role removed: {role_name} from user {user_id} "
                    f"by {removed_by_user_id or 'system'}"
                )

                # Audit log the role removal
                AuditLogger.log_event(
                    user_id=removed_by_user_id,
                    action="role_removed",
                    result="success",
                    resource_type="user_role",
                    resource_id=user_role.user_role_id,
                    metadata={
                        "target_user_id": str(user_id),
                        "role_name": role_name,
                        "removed_by": str(removed_by_user_id) if removed_by_user_id else "system"
                    }
                )

                return True

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error removing role: {str(e)}", exc_info=True)
            raise

    def user_has_role(self, user_id: uuid.UUID, role_name: str) -> bool:
        """
        Check if user has a specific role.

        Args:
            user_id: UUID of user
            role_name: Name of role to check

        Returns:
            True if user has the role, False otherwise
        """
        try:
            with get_db_context() as db:
                # Query for user role assignment
                user_role = db.query(UserRole).join(
                    Role, UserRole.role_id == Role.role_id
                ).filter(
                    UserRole.user_id == user_id,
                    Role.role_name == role_name
                ).first()

                return user_role is not None

        except Exception as e:
            logger.error(f"Error checking user role: {str(e)}", exc_info=True)
            return False

    def get_user_roles(self, user_id: uuid.UUID) -> List[Role]:
        """
        Get all roles assigned to a user.

        Args:
            user_id: UUID of user

        Returns:
            List of Role objects
        """
        try:
            with get_db_context() as db:
                # Query all roles for user
                roles = db.query(Role).join(
                    UserRole, Role.role_id == UserRole.role_id
                ).filter(
                    UserRole.user_id == user_id
                ).all()

                return roles

        except Exception as e:
            logger.error(f"Error fetching user roles: {str(e)}", exc_info=True)
            return []

    def get_role_permissions(self, role_name: str) -> List[str]:
        """
        Get all permissions for a role.

        Args:
            role_name: Name of role

        Returns:
            List of permission strings (e.g., ["conversation:read", "message:write"])
        """
        return self.ROLE_PERMISSIONS.get(role_name, [])

    def user_has_permission(self, user_id: uuid.UUID, permission: str) -> bool:
        """
        Check if user has a specific permission.

        Checks all roles assigned to user and returns True if any role grants the permission.
        Superadmin role with "*:*" wildcard grants all permissions.

        Args:
            user_id: UUID of user
            permission: Permission string (e.g., "conversation:write")

        Returns:
            True if user has the permission, False otherwise
        """
        try:
            # Get all user roles
            user_roles = self.get_user_roles(user_id)

            if not user_roles:
                return False

            # Check permissions for each role
            for role in user_roles:
                role_permissions = self.get_role_permissions(role.role_name)

                # Check for wildcard permission (superadmin)
                if "*:*" in role_permissions:
                    return True

                # Check for specific permission
                if permission in role_permissions:
                    return True

            return False

        except Exception as e:
            logger.error(f"Error checking user permission: {str(e)}", exc_info=True)
            return False

    def can_assign_role(self, assigner_user_id: uuid.UUID, target_role_name: str) -> bool:
        """
        Check if a user can assign a specific role (role hierarchy enforcement).

        Role Hierarchy:
            - superadmin: Can assign any role (including admin and superadmin)
            - admin: Can assign user and viewer roles only (NOT admin or superadmin)
            - user/viewer: Cannot assign any roles

        Args:
            assigner_user_id: UUID of user attempting to assign role
            target_role_name: Name of role to be assigned

        Returns:
            True if user can assign the role, False otherwise
        """
        try:
            # Check if assigner is superadmin
            if self.user_has_role(assigner_user_id, "superadmin"):
                return True  # Superadmin can assign any role

            # Check if assigner is admin
            if self.user_has_role(assigner_user_id, "admin"):
                # Admin can only assign user and viewer roles
                return target_role_name in ["user", "viewer"]

            # Regular users cannot assign any roles
            return False

        except Exception as e:
            logger.error(f"Error checking role assignment permission: {str(e)}", exc_info=True)
            return False
