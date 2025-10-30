"""
Admin API Endpoints

Provides administrative endpoints for user and quota management.
Task Group 6.1-6.3 - Phase 6: Authentication & Multi-tenancy

SECURITY: All endpoints require superuser privileges and IP whitelist check.
Phase 2 Task Group 5: IP-Based Access Controls applied.
Phase 2 Task Group 7: Role management endpoints added.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from uuid import UUID

from src.models.user import User
from src.api.middleware.auth_middleware import get_current_superuser, get_current_active_user
from src.api.middleware.ip_whitelist_middleware import check_ip_whitelist
from src.services.admin_service import AdminService
from src.services.rbac_service import RBACService
from src.observability import get_logger

logger = get_logger("admin_router")

# Phase 2 Task Group 5: Add IP whitelist dependency to all admin endpoints
router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(check_ip_whitelist)]  # Apply IP whitelist to all routes
)


# ============================================================================
# Request/Response Models
# ============================================================================

class UpdateUserStatusRequest(BaseModel):
    """Update user status request"""
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    is_superuser: Optional[bool] = None

    class Config:
        schema_extra = {
            "example": {
                "is_active": True,
                "is_verified": True,
                "is_superuser": False
            }
        }


class SetQuotaRequest(BaseModel):
    """Set user quota request"""
    llm_tokens_monthly_limit: Optional[int] = None
    masterplans_limit: Optional[int] = None
    storage_bytes_limit: Optional[int] = None
    api_calls_per_minute: int = 30

    class Config:
        schema_extra = {
            "example": {
                "llm_tokens_monthly_limit": 1000000,
                "masterplans_limit": 10,
                "storage_bytes_limit": 10737418240,
                "api_calls_per_minute": 60
            }
        }


# Phase 2 Task Group 7: RBAC Request/Response Models
class AssignRoleRequest(BaseModel):
    """Assign role to user request"""
    role_name: str

    class Config:
        schema_extra = {
            "example": {
                "role_name": "user"
            }
        }


class RoleResponse(BaseModel):
    """Role response"""
    role_id: str
    role_name: str
    description: Optional[str]
    is_system: bool
    created_at: Optional[str]


class UserRoleResponse(BaseModel):
    """User role assignment response"""
    user_role_id: str
    user_id: str
    role_id: str
    role_name: str
    assigned_by: Optional[str]
    assigned_at: str


# ============================================================================
# User Management Endpoints
# ============================================================================

@router.get("/users")
async def list_users(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    is_active: Optional[bool] = None,
    is_verified: Optional[bool] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_superuser)
):
    """
    List all users with optional filtering (Admin only).

    **Example**:
    ```bash
    curl -X GET "http://localhost:8000/api/v1/admin/users?limit=50&is_active=true" \\
      -H "Authorization: Bearer <superuser_token>"
    ```

    **Query Parameters**:
    - limit: Maximum number of users (1-1000, default 100)
    - offset: Number of users to skip (pagination)
    - is_active: Filter by active status
    - is_verified: Filter by verified status
    - search: Search by email or username (partial match)

    **Returns**:
    - users: List of user objects
    - total: Total number of matching users
    - limit: Applied limit
    - offset: Applied offset

    **Errors**:
    - 401: Not authenticated
    - 403: Not a superuser or IP not whitelisted
    """
    admin = AdminService()
    result = admin.list_users(
        limit=limit,
        offset=offset,
        is_active=is_active,
        is_verified=is_verified,
        search=search
    )

    logger.info(f"Superuser {current_user.user_id} listed users")
    return result


@router.get("/users/{user_id}")
async def get_user_details(
    user_id: UUID,
    current_user: User = Depends(get_current_superuser)
):
    """
    Get detailed user information (Admin only).

    Returns user details, quota, current usage, and resource counts.

    **Example**:
    ```bash
    curl -X GET http://localhost:8000/api/v1/admin/users/<user_id> \\
      -H "Authorization: Bearer <superuser_token>"
    ```

    **Returns**:
    - user: User object
    - quota: User quota settings (null if unlimited)
    - current_usage: Current month usage statistics
    - resource_counts: Counts of conversations and masterplans

    **Errors**:
    - 401: Not authenticated
    - 403: Not a superuser or IP not whitelisted
    - 404: User not found
    """
    admin = AdminService()

    try:
        details = admin.get_user_details(user_id)
        logger.info(f"Superuser {current_user.user_id} retrieved details for user {user_id}")
        return details
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: UUID,
    request: UpdateUserStatusRequest,
    current_user: User = Depends(get_current_superuser)
):
    """
    Update user status flags (Admin only).

    **Example**:
    ```bash
    curl -X PATCH http://localhost:8000/api/v1/admin/users/<user_id>/status \\
      -H "Authorization: Bearer <superuser_token>" \\
      -H "Content-Type: application/json" \\
      -d '{
        "is_active": false,
        "is_verified": true
      }'
    ```

    **Request Body**:
    - is_active: Set active status (optional)
    - is_verified: Set verified status (optional)
    - is_superuser: Set superuser status (optional)

    **Returns**:
    - Updated user object

    **Errors**:
    - 401: Not authenticated
    - 403: Not a superuser or IP not whitelisted
    - 404: User not found
    """
    admin = AdminService()

    try:
        user = admin.update_user_status(
            user_id=user_id,
            is_active=request.is_active,
            is_verified=request.is_verified,
            is_superuser=request.is_superuser
        )

        logger.info(f"Superuser {current_user.user_id} updated status for user {user_id}")
        return user.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_superuser)
):
    """
    Delete user and all associated data (Admin only).

    WARNING: This action is irreversible and will delete:
    - User account
    - User quota
    - All usage records
    - All conversations and messages
    - All masterplans

    **Example**:
    ```bash
    curl -X DELETE http://localhost:8000/api/v1/admin/users/<user_id> \\
      -H "Authorization: Bearer <superuser_token>"
    ```

    **Returns**:
    - message: Deletion confirmation

    **Errors**:
    - 401: Not authenticated
    - 403: Not a superuser or IP not whitelisted
    - 404: User not found
    - 400: Cannot delete last superuser
    """
    admin = AdminService()

    try:
        deleted = admin.delete_user(user_id)

        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        logger.warning(f"Superuser {current_user.user_id} deleted user {user_id}")
        return {"message": "User deleted successfully", "user_id": str(user_id)}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# Quota Management Endpoints
# ============================================================================

@router.put("/users/{user_id}/quota")
async def set_user_quota(
    user_id: UUID,
    request: SetQuotaRequest,
    current_user: User = Depends(get_current_superuser)
):
    """
    Set or update user quota (Admin only).

    **Example**:
    ```bash
    curl -X PUT http://localhost:8000/api/v1/admin/users/<user_id>/quota \\
      -H "Authorization: Bearer <superuser_token>" \\
      -H "Content-Type: application/json" \\
      -d '{
        "llm_tokens_monthly_limit": 1000000,
        "masterplans_limit": 10,
        "storage_bytes_limit": 10737418240,
        "api_calls_per_minute": 60
      }'
    ```

    **Request Body**:
    - llm_tokens_monthly_limit: Monthly LLM token limit (null = unlimited)
    - masterplans_limit: Max masterplans (null = unlimited)
    - storage_bytes_limit: Max storage in bytes (null = unlimited)
    - api_calls_per_minute: API rate limit per minute (default 30)

    **Returns**:
    - Quota object

    **Errors**:
    - 401: Not authenticated
    - 403: Not a superuser or IP not whitelisted
    - 404: User not found
    """
    admin = AdminService()

    try:
        quota = admin.set_user_quota(
            user_id=user_id,
            llm_tokens_monthly_limit=request.llm_tokens_monthly_limit,
            masterplans_limit=request.masterplans_limit,
            storage_bytes_limit=request.storage_bytes_limit,
            api_calls_per_minute=request.api_calls_per_minute
        )

        logger.info(f"Superuser {current_user.user_id} set quota for user {user_id}")
        return quota.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/users/{user_id}/quota")
async def delete_user_quota(
    user_id: UUID,
    current_user: User = Depends(get_current_superuser)
):
    """
    Delete user quota (resets to unlimited) (Admin only).

    **Example**:
    ```bash
    curl -X DELETE http://localhost:8000/api/v1/admin/users/<user_id>/quota \\
      -H "Authorization: Bearer <superuser_token>"
    ```

    **Returns**:
    - message: Deletion confirmation

    **Errors**:
    - 401: Not authenticated
    - 403: Not a superuser or IP not whitelisted
    """
    admin = AdminService()
    deleted = admin.delete_user_quota(user_id)

    if deleted:
        logger.info(f"Superuser {current_user.user_id} deleted quota for user {user_id}")
        return {"message": "Quota deleted (user now has unlimited access)", "user_id": str(user_id)}
    else:
        return {"message": "No quota existed for this user", "user_id": str(user_id)}


# ============================================================================
# System Statistics Endpoints
# ============================================================================

@router.get("/stats")
async def get_system_stats(current_user: User = Depends(get_current_superuser)):
    """
    Get system-wide statistics (Admin only).

    Returns statistics about users, resources, and current month usage.

    **Example**:
    ```bash
    curl -X GET http://localhost:8000/api/v1/admin/stats \\
      -H "Authorization: Bearer <superuser_token>"
    ```

    **Returns**:
    - users: User statistics (total, active, verified, superusers)
    - resources: Resource counts (conversations, masterplans)
    - current_month_usage: Current month aggregated usage

    **Errors**:
    - 401: Not authenticated
    - 403: Not a superuser or IP not whitelisted
    """
    admin = AdminService()
    stats = admin.get_system_stats()

    logger.info(f"Superuser {current_user.user_id} retrieved system stats")
    return stats


@router.get("/stats/top-users")
async def get_top_users(
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_superuser)
):
    """
    Get top users by LLM token usage (Admin only).

    **Example**:
    ```bash
    curl -X GET "http://localhost:8000/api/v1/admin/stats/top-users?limit=20" \\
      -H "Authorization: Bearer <superuser_token>"
    ```

    **Query Parameters**:
    - limit: Number of top users to return (1-100, default 10)

    **Returns**:
    - Array of top users with their usage statistics

    **Errors**:
    - 401: Not authenticated
    - 403: Not a superuser or IP not whitelisted
    """
    admin = AdminService()
    top_users = admin.get_top_users_by_usage(limit=limit)

    logger.info(f"Superuser {current_user.user_id} retrieved top {limit} users")
    return top_users


@router.get("/health")
async def admin_health():
    """
    Health check for admin service.

    **Example**:
    ```bash
    curl http://localhost:8000/api/v1/admin/health
    ```

    **Returns**:
    - status: Service status
    - message: Status message
    """
    return {
        "status": "healthy",
        "service": "admin",
        "message": "Admin service is operational"
    }

# ============================================================================
# Phase 2 Task Group 3: Account Lockout Management
# ============================================================================

@router.post("/users/{user_id}/unlock")
async def unlock_user_account(
    user_id: UUID,
    current_user: User = Depends(get_current_superuser)
):
    """
    Manually unlock a locked user account (Admin only).

    Phase 2 Task Group 3: Account Lockout Protection

    **Example**:
    ```bash
    curl -X POST http://localhost:8000/api/v1/admin/users/<user_id>/unlock \\
      -H "Authorization: Bearer <superuser_token>"
    ```

    **Returns**:
    - message: Unlock confirmation
    - user_id: UUID of unlocked user
    - unlocked_by: UUID of admin who performed unlock

    **Errors**:
    - 401: Not authenticated
    - 403: Not a superuser or IP not whitelisted
    - 404: User not found
    """
    from src.services.account_lockout_service import AccountLockoutService

    lockout_service = AccountLockoutService()

    try:
        # Verify user exists
        from src.config.database import get_db_context
        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User {user_id} not found"
                )

            # Check if user is actually locked
            was_locked = user.is_locked()

        # Unlock account (creates audit log internally)
        lockout_service.unlock_account(user_id, admin_user_id=current_user.user_id)

        logger.info(
            f"Superuser {current_user.user_id} unlocked account for user {user_id}"
        )

        return {
            "message": "Account unlocked successfully" if was_locked else "Account was not locked",
            "user_id": str(user_id),
            "unlocked_by": str(current_user.user_id),
            "was_locked": was_locked
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error unlocking account: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unlock account"
        )


# ============================================================================
# Phase 2 Task Group 7: Role Management Endpoints
# ============================================================================

@router.get("/roles", response_model=List[RoleResponse])
async def list_all_roles(
    current_user: User = Depends(get_current_active_user)
):
    """
    List all available roles (requires authentication).

    Phase 2 Task Group 7: RBAC Role Management

    **Example**:
    ```bash
    curl -X GET http://localhost:8000/api/v1/admin/roles \\
      -H "Authorization: Bearer <token>"
    ```

    **Returns**:
    - List of all roles with their descriptions

    **Errors**:
    - 401: Not authenticated
    - 403: IP not whitelisted
    """
    from src.config.database import get_db_context
    from src.models.role import Role

    try:
        with get_db_context() as db:
            roles = db.query(Role).all()

            return [
                {
                    "role_id": str(role.role_id),
                    "role_name": role.role_name,
                    "description": role.description,
                    "is_system": role.is_system,
                    "created_at": role.created_at.isoformat() if role.created_at else None
                }
                for role in roles
            ]

    except Exception as e:
        logger.error(f"Error listing roles: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list roles"
        )


@router.post("/users/{user_id}/roles")
async def assign_role_to_user(
    user_id: UUID,
    request: AssignRoleRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Assign role to user (requires appropriate permissions).

    Phase 2 Task Group 7: RBAC Role Management

    Permission Requirements:
    - superadmin: Can assign any role (including admin and superadmin)
    - admin: Can assign user and viewer roles only
    - user/viewer: Cannot assign any roles (403 error)

    **Example**:
    ```bash
    curl -X POST http://localhost:8000/api/v1/admin/users/<user_id>/roles \\
      -H "Authorization: Bearer <token>" \\
      -H "Content-Type: application/json" \\
      -d '{"role_name": "user"}'
    ```

    **Request Body**:
    - role_name: Name of role to assign (superadmin, admin, user, viewer)

    **Returns**:
    - user_role_id: UUID of role assignment
    - user_id: UUID of user
    - role_id: UUID of role
    - role_name: Name of assigned role
    - assigned_by: UUID of user who performed assignment
    - assigned_at: Timestamp of assignment

    **Errors**:
    - 401: Not authenticated
    - 403: Insufficient permissions to assign this role
    - 404: User or role not found
    - 400: User already has this role
    """
    rbac_service = RBACService()

    try:
        # Check if assigner has permission to assign this role
        if not rbac_service.can_assign_role(current_user.user_id, request.role_name):
            logger.warning(
                f"User {current_user.user_id} attempted to assign role '{request.role_name}' "
                f"without permission"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have permission to assign '{request.role_name}' role"
            )

        # Verify target user exists
        from src.config.database import get_db_context
        with get_db_context() as db:
            target_user = db.query(User).filter(User.user_id == user_id).first()
            if not target_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User {user_id} not found"
                )

        # Assign role
        user_role = rbac_service.assign_role(
            user_id=user_id,
            role_name=request.role_name,
            assigned_by_user_id=current_user.user_id
        )

        logger.info(
            f"User {current_user.user_id} assigned role '{request.role_name}' to user {user_id}"
        )

        # Get role details for response
        from src.config.database import get_db_context
        from src.models.role import Role
        with get_db_context() as db:
            role = db.query(Role).filter(Role.role_id == user_role.role_id).first()

            return {
                "user_role_id": str(user_role.user_role_id),
                "user_id": str(user_role.user_id),
                "role_id": str(user_role.role_id),
                "role_name": role.role_name if role else request.role_name,
                "assigned_by": str(user_role.assigned_by) if user_role.assigned_by else None,
                "assigned_at": user_role.assigned_at.isoformat() if user_role.assigned_at else None
            }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        # Role not found or already assigned
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error assigning role: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign role"
        )


@router.delete("/users/{user_id}/roles/{role_name}")
async def remove_role_from_user(
    user_id: UUID,
    role_name: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Remove role from user (requires appropriate permissions).

    Phase 2 Task Group 7: RBAC Role Management

    Permission Requirements:
    - superadmin: Can remove any role
    - admin: Can remove user and viewer roles only
    - user/viewer: Cannot remove any roles (403 error)

    **Example**:
    ```bash
    curl -X DELETE http://localhost:8000/api/v1/admin/users/<user_id>/roles/viewer \\
      -H "Authorization: Bearer <token>"
    ```

    **Returns**:
    - message: Removal confirmation
    - user_id: UUID of user
    - role_name: Name of removed role
    - removed_by: UUID of user who performed removal

    **Errors**:
    - 401: Not authenticated
    - 403: Insufficient permissions to remove this role
    - 404: User not found or user doesn't have this role
    """
    rbac_service = RBACService()

    try:
        # Check if remover has permission to remove this role
        if not rbac_service.can_assign_role(current_user.user_id, role_name):
            logger.warning(
                f"User {current_user.user_id} attempted to remove role '{role_name}' "
                f"without permission"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have permission to remove '{role_name}' role"
            )

        # Remove role
        removed = rbac_service.remove_role(
            user_id=user_id,
            role_name=role_name,
            removed_by_user_id=current_user.user_id
        )

        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} does not have role '{role_name}'"
            )

        logger.info(
            f"User {current_user.user_id} removed role '{role_name}' from user {user_id}"
        )

        return {
            "message": "Role removed successfully",
            "user_id": str(user_id),
            "role_name": role_name,
            "removed_by": str(current_user.user_id)
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        # Role not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error removing role: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove role"
        )


@router.get("/users/{user_id}/roles", response_model=List[RoleResponse])
async def get_user_roles(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all roles assigned to a user.

    Phase 2 Task Group 7: RBAC Role Management

    **Example**:
    ```bash
    curl -X GET http://localhost:8000/api/v1/admin/users/<user_id>/roles \\
      -H "Authorization: Bearer <token>"
    ```

    **Returns**:
    - List of roles assigned to the user

    **Errors**:
    - 401: Not authenticated
    - 403: Not authorized to view user roles
    - 404: User not found
    """
    rbac_service = RBACService()

    try:
        # Verify user can view roles (must be same user, admin, or superadmin)
        if current_user.user_id != user_id:
            if not rbac_service.user_has_role(current_user.user_id, "admin") and \
               not rbac_service.user_has_role(current_user.user_id, "superadmin"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only view your own roles unless you are an admin"
                )

        # Get user roles
        roles = rbac_service.get_user_roles(user_id)

        return [
            {
                "role_id": str(role.role_id),
                "role_name": role.role_name,
                "description": role.description,
                "is_system": role.is_system,
                "created_at": role.created_at.isoformat() if role.created_at else None
            }
            for role in roles
        ]

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error getting user roles: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user roles"
        )


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get effective permissions for a user based on their roles.

    Phase 2 Task Group 7: RBAC Role Management

    **Example**:
    ```bash
    curl -X GET http://localhost:8000/api/v1/admin/users/<user_id>/permissions \\
      -H "Authorization: Bearer <token>"
    ```

    **Returns**:
    - permissions: List of permission strings (e.g., ["conversation:read", "message:write"])
    - roles: List of roles that grant these permissions

    **Errors**:
    - 401: Not authenticated
    - 403: Not authorized to view user permissions
    - 404: User not found
    """
    rbac_service = RBACService()

    try:
        # Verify user can view permissions (must be same user, admin, or superadmin)
        if current_user.user_id != user_id:
            if not rbac_service.user_has_role(current_user.user_id, "admin") and \
               not rbac_service.user_has_role(current_user.user_id, "superadmin"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only view your own permissions unless you are an admin"
                )

        # Get user roles
        roles = rbac_service.get_user_roles(user_id)

        # Collect all permissions from all roles
        all_permissions = set()
        role_details = []

        for role in roles:
            permissions = rbac_service.get_role_permissions(role.role_name)
            all_permissions.update(permissions)
            role_details.append({
                "role_name": role.role_name,
                "permissions": permissions
            })

        return {
            "user_id": str(user_id),
            "permissions": sorted(list(all_permissions)),
            "roles": role_details
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error getting user permissions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user permissions"
        )

# ============================================================================
# Phase 2 Task Group 15: Log Retention & Management Endpoints
# ============================================================================

class ArchiveLogsRequest(BaseModel):
    """Request to manually trigger log archival"""
    year: int
    month: int  # 1-12
    table_name: str  # "audit_logs" or "security_events"

    class Config:
        schema_extra = {
            "example": {
                "year": 2025,
                "month": 10,
                "table_name": "audit_logs"
            }
        }


class RestoreLogsRequest(BaseModel):
    """Request to restore logs from S3"""
    s3_key: str  # e.g., "audit-logs/2025/10/audit_logs_2025_10.json.gz"

    class Config:
        schema_extra = {
            "example": {
                "s3_key": "audit-logs/2025/10/audit_logs_2025_10.json.gz"
            }
        }


class PurgeLogsRequest(BaseModel):
    """Request to manually purge logs (superadmin only)"""
    table_name: str  # "audit_logs", "security_events", or "alert_history"
    days_retention: int  # e.g., 90
    confirm: bool = False  # Must be True to execute

    class Config:
        schema_extra = {
            "example": {
                "table_name": "audit_logs",
                "days_retention": 90,
                "confirm": True
            }
        }


@router.post("/logs/archive")
async def manually_archive_logs(
    request: ArchiveLogsRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Manually trigger log archival to S3 (Admin only).

    Phase 2 Task Group 15: Log Retention & Management

    Archives logs for a specific month to S3 in compressed JSON format.
    Creates manifest file with checksum.

    **Example**:
    ```bash
    curl -X POST http://localhost:8000/api/v1/admin/logs/archive \\
      -H "Authorization: Bearer <token>" \\
      -H "Content-Type: application/json" \\
      -d '{
        "year": 2025,
        "month": 10,
        "table_name": "audit_logs"
      }'
    ```

    **Request Body**:
    - year: Year to archive (e.g., 2025)
    - month: Month to archive (1-12)
    - table_name: Table to archive ("audit_logs" or "security_events")

    **Returns**:
    - Manifest dictionary with metadata (row_count, file_size, checksum)

    **Errors**:
    - 401: Not authenticated
    - 403: Not admin or IP not whitelisted
    - 400: Invalid table name or S3 not configured
    """
    from src.services.log_archival_service import LogArchivalService

    # Verify user has admin permissions
    rbac_service = RBACService()
    if not rbac_service.user_has_role(current_user.user_id, "admin") and \
       not rbac_service.user_has_role(current_user.user_id, "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires admin role"
        )

    # Validate table name
    valid_tables = ["audit_logs", "security_events"]
    if request.table_name not in valid_tables:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid table_name. Must be one of: {', '.join(valid_tables)}"
        )

    try:
        service = LogArchivalService()

        # Archive based on table name
        if request.table_name == "audit_logs":
            manifest = service.archive_audit_logs(request.year, request.month)
        else:
            manifest = service.archive_security_events(request.year, request.month)

        logger.info(
            f"Admin {current_user.user_id} archived {request.table_name} "
            f"for {request.year}-{request.month:02d}"
        )

        return {
            "message": "Archival completed successfully",
            "manifest": manifest
        }

    except Exception as e:
        logger.error(f"Archival failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Archival failed: {str(e)}"
        )


@router.post("/logs/restore")
async def restore_logs_from_s3(
    request: RestoreLogsRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Restore logs from S3 to temporary table (Admin only).

    Phase 2 Task Group 15: Log Retention & Management

    Downloads logs from S3 and creates a temporary table.
    Temporary table auto-purges after 7 days.

    **Example**:
    ```bash
    curl -X POST http://localhost:8000/api/v1/admin/logs/restore \\
      -H "Authorization: Bearer <token>" \\
      -H "Content-Type: application/json" \\
      -d '{
        "s3_key": "audit-logs/2025/10/audit_logs_2025_10.json.gz"
      }'
    ```

    **Request Body**:
    - s3_key: S3 key of archive file

    **Returns**:
    - temp_table_name: Name of temporary table created
    - message: Restoration confirmation

    **Errors**:
    - 401: Not authenticated
    - 403: Not admin or IP not whitelisted
    - 400: S3 not configured
    - 500: Restoration failed
    """
    from src.services.log_archival_service import LogArchivalService

    # Verify user has admin permissions
    rbac_service = RBACService()
    if not rbac_service.user_has_role(current_user.user_id, "admin") and \
       not rbac_service.user_has_role(current_user.user_id, "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires admin role"
        )

    try:
        service = LogArchivalService()
        temp_table_name = service.restore_logs(request.s3_key)

        logger.info(
            f"Admin {current_user.user_id} restored logs from {request.s3_key} "
            f"to temporary table {temp_table_name}"
        )

        return {
            "message": "Logs restored successfully",
            "temp_table_name": temp_table_name,
            "s3_key": request.s3_key,
            "auto_purge_after_days": 7
        }

    except Exception as e:
        logger.error(f"Restoration failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Restoration failed: {str(e)}"
        )


@router.delete("/logs/purge")
async def manually_purge_logs(
    request: PurgeLogsRequest,
    current_user: User = Depends(get_current_superuser)
):
    """
    Manually purge old logs from database (Superadmin only).

    Phase 2 Task Group 15: Log Retention & Management

    WARNING: This action is irreversible. Requires confirmation.
    Purges logs older than specified retention period.

    **Example**:
    ```bash
    curl -X DELETE http://localhost:8000/api/v1/admin/logs/purge \\
      -H "Authorization: Bearer <superuser_token>" \\
      -H "Content-Type: application/json" \\
      -d '{
        "table_name": "audit_logs",
        "days_retention": 90,
        "confirm": true
      }'
    ```

    **Request Body**:
    - table_name: Table to purge ("audit_logs", "security_events", "alert_history")
    - days_retention: Number of days to retain (older logs will be deleted)
    - confirm: Must be true to execute (safety check)

    **Returns**:
    - rows_deleted: Number of rows deleted
    - message: Purge confirmation

    **Errors**:
    - 401: Not authenticated
    - 403: Not superadmin or IP not whitelisted
    - 400: Invalid table name or confirmation not provided
    - 500: Purge failed
    """
    from src.services.log_archival_service import LogArchivalService

    # Verify confirmation
    if not request.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation required. Set 'confirm' to true."
        )

    # Validate table name
    valid_tables = ["audit_logs", "security_events", "alert_history"]
    if request.table_name not in valid_tables:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid table_name. Must be one of: {', '.join(valid_tables)}"
        )

    try:
        service = LogArchivalService()
        rows_deleted = service.purge_old_logs(request.table_name, request.days_retention)

        logger.warning(
            f"Superadmin {current_user.user_id} purged {rows_deleted} rows from "
            f"{request.table_name} (older than {request.days_retention} days)"
        )

        return {
            "message": "Logs purged successfully",
            "table_name": request.table_name,
            "rows_deleted": rows_deleted,
            "days_retention": request.days_retention,
            "purged_by": str(current_user.user_id)
        }

    except Exception as e:
        logger.error(f"Purge failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Purge failed: {str(e)}"
        )
