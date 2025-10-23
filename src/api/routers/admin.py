"""
Admin API Endpoints

Provides administrative endpoints for user and quota management.
Task Group 6.1-6.3 - Phase 6: Authentication & Multi-tenancy

SECURITY: All endpoints require superuser privileges.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from uuid import UUID

from src.models.user import User
from src.api.middleware.auth_middleware import get_current_superuser
from src.services.admin_service import AdminService
from src.observability import get_logger

logger = get_logger("admin_router")

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


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
    - 403: Not a superuser
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
    - 403: Not a superuser
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
    - 403: Not a superuser
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
    - 403: Not a superuser
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
    - 403: Not a superuser
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
    - 403: Not a superuser
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
    - 403: Not a superuser
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
    - 403: Not a superuser
    """
    admin = AdminService()
    top_users = admin.get_top_users_by_usage(limit=limit)

    logger.info(f"Superuser {current_user.user_id} retrieved top {limit} users")
    return {"top_users": top_users, "limit": limit}


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
