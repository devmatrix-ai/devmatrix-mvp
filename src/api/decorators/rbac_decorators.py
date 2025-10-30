"""
RBAC Decorators for Role and Permission-Based Access Control

Provides decorators for enforcing role and permission requirements on API endpoints.
Phase 2 - Task Group 7: Role-Based Access Control (RBAC) Service

Usage:
    @router.get("/admin/users")
    @require_role("admin")
    async def list_users(current_user: User = Depends(get_current_active_user)):
        ...

    @router.get("/conversations/{conversation_id}")
    @require_permission("conversation:read")
    async def get_conversation(
        conversation_id: str,
        current_user: User = Depends(get_current_active_user)
    ):
        ...
"""

from functools import wraps
from typing import Callable
from fastapi import HTTPException, status, Depends

from src.models.user import User
from src.api.middleware.auth_middleware import get_current_active_user
from src.services.rbac_service import RBACService
from src.observability import get_logger

logger = get_logger("rbac_decorators")


def require_role(required_role: str) -> Callable:
    """
    Decorator to require a specific role for endpoint access.

    Checks if the current user has the required role. Returns 403 Forbidden
    if the user lacks the role.

    Args:
        required_role: Name of required role (e.g., "admin", "superadmin")

    Returns:
        Decorator function

    Usage:
        @router.get("/admin/users")
        @require_role("admin")
        async def list_users(current_user: User = Depends(get_current_active_user)):
            ...

    Raises:
        HTTPException: 403 Forbidden if user lacks required role
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_active_user), **kwargs):
            rbac_service = RBACService()

            # Check if user has required role
            if not rbac_service.user_has_role(current_user.user_id, required_role):
                logger.warning(
                    f"Access denied: User {current_user.user_id} lacks required role '{required_role}'"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requires '{required_role}' role"
                )

            # User has required role - proceed
            return await func(*args, current_user=current_user, **kwargs)

        return wrapper
    return decorator


def require_permission(permission: str) -> Callable:
    """
    Decorator to require a specific permission for endpoint access.

    Checks if the current user has the required permission based on their roles.
    Returns 403 Forbidden if the user lacks the permission.

    Args:
        permission: Permission string in "resource:action" format (e.g., "conversation:write")

    Returns:
        Decorator function

    Usage:
        @router.get("/conversations/{conversation_id}")
        @require_permission("conversation:read")
        async def get_conversation(
            conversation_id: str,
            current_user: User = Depends(get_current_active_user)
        ):
            ...

    Raises:
        HTTPException: 403 Forbidden if user lacks required permission

    Note:
        This decorator checks role-based permissions only. For resource-specific
        ownership checks (e.g., user can only edit their own conversations),
        use PermissionService.user_can() in the endpoint logic.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_active_user), **kwargs):
            rbac_service = RBACService()

            # Check if user has required permission
            if not rbac_service.user_has_permission(current_user.user_id, permission):
                logger.warning(
                    f"Access denied: User {current_user.user_id} lacks permission '{permission}'"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions: {permission}"
                )

            # User has required permission - proceed
            return await func(*args, current_user=current_user, **kwargs)

        return wrapper
    return decorator


def require_any_role(*required_roles: str) -> Callable:
    """
    Decorator to require ANY of the specified roles for endpoint access.

    Checks if the current user has at least one of the required roles.
    Returns 403 Forbidden if the user lacks all roles.

    Args:
        *required_roles: Variable number of role names

    Returns:
        Decorator function

    Usage:
        @router.get("/shared/conversations")
        @require_any_role("admin", "user")
        async def list_shared_conversations(
            current_user: User = Depends(get_current_active_user)
        ):
            ...

    Raises:
        HTTPException: 403 Forbidden if user lacks all required roles
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_active_user), **kwargs):
            rbac_service = RBACService()

            # Check if user has any of the required roles
            for role in required_roles:
                if rbac_service.user_has_role(current_user.user_id, role):
                    # User has at least one required role - proceed
                    return await func(*args, current_user=current_user, **kwargs)

            # User lacks all required roles
            roles_str = ", ".join(required_roles)
            logger.warning(
                f"Access denied: User {current_user.user_id} lacks any of required roles: {roles_str}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {roles_str}"
            )

        return wrapper
    return decorator


def require_all_roles(*required_roles: str) -> Callable:
    """
    Decorator to require ALL of the specified roles for endpoint access.

    Checks if the current user has all of the required roles.
    Returns 403 Forbidden if the user lacks any role.

    Args:
        *required_roles: Variable number of role names

    Returns:
        Decorator function

    Usage:
        @router.post("/admin/security/critical")
        @require_all_roles("admin", "security_officer")
        async def perform_critical_action(
            current_user: User = Depends(get_current_active_user)
        ):
            ...

    Raises:
        HTTPException: 403 Forbidden if user lacks any required role
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_active_user), **kwargs):
            rbac_service = RBACService()

            # Check if user has all required roles
            for role in required_roles:
                if not rbac_service.user_has_role(current_user.user_id, role):
                    roles_str = ", ".join(required_roles)
                    logger.warning(
                        f"Access denied: User {current_user.user_id} lacks required role '{role}' "
                        f"(needs all of: {roles_str})"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Requires all of: {roles_str}"
                    )

            # User has all required roles - proceed
            return await func(*args, current_user=current_user, **kwargs)

        return wrapper
    return decorator
