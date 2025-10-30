"""
Ownership Middleware for Resource Access Control

Provides decorator to validate that users can only access their own resources.
Integrates with PermissionService for granular permission checking.

Phase 2 - Task Group 8: Granular Permission System
- Ownership-based access (users can access own resources)
- Shared resource access (users can access shared conversations)
- Role-based bypass (admin/superadmin can access all resources)
- Permission level enforcement (view/comment/edit)

Group 4: Authorization & Access Control Layer
"""

import functools
from typing import Callable
from uuid import UUID
from fastapi import HTTPException, status, Request

from src.models.conversation import Conversation
from src.models.user import User
from src.config.database import get_db_context
from src.services.permission_service import PermissionService
from src.observability import get_logger
from src.observability.audit_logger import audit_logger

logger = get_logger("ownership_middleware")


def require_resource_ownership(resource_type: str) -> Callable:
    """
    Decorator to validate resource ownership and permissions before accessing endpoints.

    Security behavior (Phase 2 enhanced):
    - Returns 404 if resource doesn't exist (don't reveal existence)
    - Returns 403 if user doesn't have permission (not owner, not shared, not admin)
    - Allows access if:
        * User owns resource (full access)
        * Resource is shared with user (based on permission level)
        * User has admin/superadmin role (full access)

    Permission levels (for shared resources):
    - view: Read-only access
    - comment: Read + write messages
    - edit: Read + write (no delete/re-share)

    Args:
        resource_type: Type of resource ("conversation", "message", etc.)

    Returns:
        Decorator function

    Usage:
        @require_resource_ownership("conversation")
        async def get_conversation(conversation_id: str, current_user: User):
            # Permission validated before this runs
            ...

    Example in chat.py:
        @router.get("/conversations/{conversation_id}")
        @require_resource_ownership("conversation")
        async def get_conversation(
            conversation_id: str,
            current_user: User = Depends(get_current_user)
        ):
            return {"conversation_id": conversation_id}
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request object (for audit logging and HTTP method)
            request = kwargs.get('request')

            # Extract conversation_id from kwargs
            conversation_id_str = kwargs.get('conversation_id')
            if not conversation_id_str:
                logger.error(f"conversation_id not found in kwargs for {func.__name__}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal error: conversation_id not provided"
                )

            # Extract current_user from kwargs
            current_user = kwargs.get('current_user')
            if not current_user:
                logger.error(f"current_user not found in kwargs for {func.__name__}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            # Convert conversation_id to UUID
            try:
                conversation_id = UUID(conversation_id_str)
            except ValueError:
                logger.warning(f"Invalid conversation_id format: {conversation_id_str}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{resource_type.capitalize()} not found"
                )

            # Determine action from HTTP method
            method_to_action = {
                "GET": "read",
                "PUT": "write",
                "PATCH": "write",
                "DELETE": "delete",
                "POST": "write"
            }
            action = method_to_action.get(
                request.method if request and hasattr(request, 'method') else "GET",
                "read"
            )

            # Load conversation from database (ensure it exists)
            with get_db_context() as db:
                conversation = db.query(Conversation).filter(
                    Conversation.conversation_id == conversation_id
                ).first()

                # If conversation not found, return 404 (don't reveal existence)
                if not conversation:
                    logger.info(
                        f"Conversation not found: {conversation_id}",
                        extra={
                            "user_id": str(current_user.user_id),
                            "conversation_id": str(conversation_id),
                            "resource_type": resource_type
                        }
                    )
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"{resource_type.capitalize()} not found"
                    )

            # Check permissions using PermissionService
            permission_service = PermissionService()
            has_permission = permission_service.user_can_access_conversation(
                current_user.user_id,
                conversation_id,
                action
            )

            if not has_permission:
                # Access denied - user doesn't own, isn't admin, and doesn't have share
                logger.warning(
                    f"Access denied: User {current_user.user_id} attempted to {action} "
                    f"conversation {conversation_id} owned by {conversation.user_id}",
                    extra={
                        "user_id": str(current_user.user_id),
                        "conversation_id": str(conversation_id),
                        "conversation_owner_id": str(conversation.user_id),
                        "resource_type": resource_type,
                        "action": action,
                        "is_superuser": current_user.is_superuser
                    }
                )

                # Log authorization denial to audit logs
                if request:
                    await audit_logger.log_authorization_denied(
                        user_id=current_user.user_id,
                        resource_type=resource_type,
                        resource_id=conversation_id,
                        action_attempted=action,
                        ip_address=request.client.host if hasattr(request, 'client') and request.client else None,
                        user_agent=request.headers.get("user-agent") if hasattr(request, 'headers') else None,
                        correlation_id=getattr(request.state, 'correlation_id', None) if hasattr(request, 'state') else None
                    )

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied: Insufficient permissions to {action} this {resource_type}"
                )

            # Permission validated - log successful access for audit
            # Determine access reason for logging
            is_owner = permission_service.is_conversation_owner(current_user.user_id, conversation_id)
            is_shared = permission_service.is_conversation_shared_with(current_user.user_id, conversation_id)

            access_reason = "owner" if is_owner else ("shared" if is_shared else "admin")

            logger.info(
                f"Access granted: User {current_user.user_id} can {action} "
                f"conversation {conversation_id} (reason: {access_reason})",
                extra={
                    "user_id": str(current_user.user_id),
                    "conversation_id": str(conversation_id),
                    "conversation_owner_id": str(conversation.user_id),
                    "resource_type": resource_type,
                    "action": action,
                    "access_reason": access_reason
                }
            )

            # Proceed to endpoint
            return await func(*args, **kwargs)

        return wrapper

    return decorator
