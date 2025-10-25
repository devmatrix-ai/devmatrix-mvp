"""
Audit Logger Service

Asynchronous service for logging security events to audit_logs table.
Group 4: Authorization & Access Control Layer
"""

import uuid
from typing import Optional, Dict, Any
from datetime import datetime

from src.models.audit_log import AuditLog
from src.config.database import get_db_context
from src.observability import get_logger

logger = get_logger("audit_logger")


class AuditLogger:
    """
    Audit logging service for security event tracking.

    Handles logging of:
    - Authentication events (login, logout, failures, token refresh)
    - Authorization failures (access denied)
    - Modification events (create, update, delete)

    Phase 1 Exclusion: Successful read operations NOT logged (deferred to Phase 2+)

    Features:
    - Asynchronous logging (doesn't block requests)
    - Graceful error handling (logs errors but doesn't fail requests)
    - Correlation ID tracking
    """

    @staticmethod
    async def log_event(
        user_id: Optional[uuid.UUID],
        action: str,
        result: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """
        Log a security event to the audit_logs table.

        Args:
            user_id: UUID of the user (None for anonymous)
            action: Event action (e.g., "auth.login", "conversation.update_denied")
            result: Event result ("success" or "denied")
            resource_type: Type of resource (e.g., "conversation", "message")
            resource_id: UUID of the resource
            ip_address: Client IP address
            user_agent: Client user agent string
            metadata: Additional event metadata
            correlation_id: Request correlation ID for tracing

        Returns:
            bool: True if logged successfully, False otherwise

        Example:
            await AuditLogger.log_event(
                user_id=user.user_id,
                action="auth.login",
                result="success",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0...",
                correlation_id=request.state.correlation_id
            )
        """
        try:
            # Create audit log entry
            audit_log = AuditLog(
                id=uuid.uuid4(),
                timestamp=datetime.utcnow(),
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                result=result,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=metadata or {}
            )

            # Insert into database asynchronously
            with get_db_context() as db:
                db.add(audit_log)
                db.commit()

            logger.info(
                f"Audit event logged: {action} ({result})",
                extra={
                    "audit_id": str(audit_log.id),
                    "user_id": str(user_id) if user_id else None,
                    "action": action,
                    "result": result,
                    "resource_type": resource_type,
                    "resource_id": str(resource_id) if resource_id else None,
                    "correlation_id": correlation_id
                }
            )

            return True

        except Exception as e:
            # Log error but don't fail the request
            logger.error(
                f"Failed to log audit event: {str(e)}",
                extra={
                    "action": action,
                    "result": result,
                    "user_id": str(user_id) if user_id else None,
                    "correlation_id": correlation_id
                },
                exc_info=True
            )
            return False

    @staticmethod
    async def log_auth_event(
        user_id: Optional[uuid.UUID],
        action: str,
        result: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """
        Log authentication event (login, logout, token_refresh, etc).

        Args:
            user_id: UUID of the user
            action: Auth action ("auth.login", "auth.logout", "auth.login_failed", "auth.token_refresh")
            result: "success" or "denied"
            ip_address: Client IP
            user_agent: Client user agent
            correlation_id: Request correlation ID

        Returns:
            bool: True if logged successfully
        """
        return await AuditLogger.log_event(
            user_id=user_id,
            action=action,
            result=result,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id
        )

    @staticmethod
    async def log_authorization_denied(
        user_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
        action_attempted: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """
        Log authorization failure (user attempted to access resource they don't own).

        Args:
            user_id: UUID of the user who was denied
            resource_type: Type of resource ("conversation", "message", etc.)
            resource_id: UUID of the resource
            action_attempted: Action attempted ("read", "update", "delete")
            ip_address: Client IP
            user_agent: Client user agent
            correlation_id: Request correlation ID

        Returns:
            bool: True if logged successfully
        """
        action = f"{resource_type}.{action_attempted}_denied"

        return await AuditLogger.log_event(
            user_id=user_id,
            action=action,
            result="denied",
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id
        )

    @staticmethod
    async def log_modification(
        user_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
        action: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """
        Log modification event (create, update, delete).

        Args:
            user_id: UUID of the user who performed the action
            resource_type: Type of resource ("conversation", "message", etc.)
            resource_id: UUID of the resource
            action: Action performed ("create", "update", "delete")
            ip_address: Client IP
            user_agent: Client user agent
            metadata: Additional metadata
            correlation_id: Request correlation ID

        Returns:
            bool: True if logged successfully
        """
        full_action = f"{resource_type}.{action}"

        return await AuditLogger.log_event(
            user_id=user_id,
            action=full_action,
            result="success",
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata,
            correlation_id=correlation_id
        )


# Convenience instance
audit_logger = AuditLogger()
