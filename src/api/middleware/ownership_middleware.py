"""
Ownership Middleware for Resource Access Control

Provides decorator to validate that users can only access their own resources.
Superusers can access all resources.

Group 4: Authorization & Access Control Layer
"""

import functools
from typing import Callable
from uuid import UUID
from fastapi import HTTPException, status, Request

from src.models.conversation import Conversation
from src.models.user import User
from src.config.database import get_db_context
from src.observability import get_logger
from src.observability.audit_logger import audit_logger

logger = get_logger("ownership_middleware")


def require_resource_ownership(resource_type: str) -> Callable:
    """
    Decorator to validate resource ownership before accessing endpoints.

    Security behavior:
    - Returns 404 if resource doesn't exist (don't reveal existence)
    - Returns 403 if user doesn't own resource (and is not superuser)
    - Allows access if user owns resource OR is superuser

    Args:
        resource_type: Type of resource ("conversation", "message", etc.)

    Returns:
        Decorator function

    Usage:
        @require_resource_ownership("conversation")
        async def get_conversation(conversation_id: str, current_user: User):
            # Ownership validated before this runs
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
            # Extract request object (for audit logging)
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

            # Load conversation from database
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

                # Check ownership: conversation.user_id == current_user.user_id
                if conversation.user_id != current_user.user_id:
                    # If superuser, allow access
                    if current_user.is_superuser:
                        logger.info(
                            f"Superuser access granted: {current_user.user_id} accessing {conversation_id}",
                            extra={
                                "user_id": str(current_user.user_id),
                                "conversation_id": str(conversation_id),
                                "conversation_owner_id": str(conversation.user_id),
                                "resource_type": resource_type,
                                "is_superuser": True
                            }
                        )
                    else:
                        # Not owner and not superuser - deny access
                        logger.warning(
                            f"Access denied: User {current_user.user_id} attempted to access conversation {conversation_id} owned by {conversation.user_id}",
                            extra={
                                "user_id": str(current_user.user_id),
                                "conversation_id": str(conversation_id),
                                "conversation_owner_id": str(conversation.user_id),
                                "resource_type": resource_type,
                                "is_superuser": False
                            }
                        )

                        # Log authorization denial to audit logs
                        if request:
                            # Determine action from HTTP method
                            method_to_action = {
                                "GET": "read",
                                "PUT": "update",
                                "PATCH": "update",
                                "DELETE": "delete",
                                "POST": "create"
                            }
                            action_attempted = method_to_action.get(
                                request.method if hasattr(request, 'method') else "unknown",
                                "access"
                            )

                            await audit_logger.log_authorization_denied(
                                user_id=current_user.user_id,
                                resource_type=resource_type,
                                resource_id=conversation_id,
                                action_attempted=action_attempted,
                                ip_address=request.client.host if hasattr(request, 'client') and request.client else None,
                                user_agent=request.headers.get("user-agent") if hasattr(request, 'headers') else None,
                                correlation_id=getattr(request.state, 'correlation_id', None) if hasattr(request, 'state') else None
                            )

                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Access denied: You do not own this {resource_type}"
                        )

            # Ownership validated - proceed to endpoint
            return await func(*args, **kwargs)

        return wrapper

    return decorator
