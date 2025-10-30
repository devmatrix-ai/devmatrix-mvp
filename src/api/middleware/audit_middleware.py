"""
Audit Middleware for Read Operations

Task Group 12 - Phase 2: Enhanced Audit Logging (Read Operations)

Intercepts all GET requests and logs read operations to audit_logs table.
Excludes health checks, metrics, keep-alive, and static assets.

Logged operations:
- GET /conversations/{id} -> conversation.read
- GET /conversations/{id}/messages -> message.read
- GET /users/{id} -> user.read
- GET /admin/users -> user.read

Excluded paths:
- /health, /api/v1/health
- /metrics, /api/v1/metrics
- /auth/session/keep-alive
- /static/*, /assets/*, /favicon.ico
"""

import re
import uuid
from typing import Optional, Tuple
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from src.observability.audit_logger import AuditLogger
from src.observability import get_logger
from src.config.settings import get_settings

logger = get_logger("audit_middleware")


def should_log_read_operation(path: str, method: str) -> bool:
    """
    Determine if the request should be logged.

    Args:
        path: Request path
        method: HTTP method

    Returns:
        bool: True if should log, False if excluded
    """
    # Only log GET requests (read operations)
    if method != "GET":
        return False

    # Load excluded paths from settings
    try:
        settings = get_settings()
        excluded_paths = settings.AUDIT_EXCLUDED_PATHS.split(",")
        excluded_paths = [p.strip() for p in excluded_paths if p.strip()]
    except Exception:
        # Fallback to hardcoded list if settings not available
        excluded_paths = ["/health", "/metrics", "/auth/session/keep-alive"]

    # Check if path matches excluded patterns
    excluded_patterns = [
        r"^/health$",
        r"^/api/v[0-9]+/health$",
        r"^/metrics$",
        r"^/api/v[0-9]+/metrics$",
        r"^/api/v[0-9]+/auth/session/keep-alive$",
        r"^/auth/session/keep-alive$",
        r"^/static/",
        r"^/assets/",
        r"^/favicon\.ico$",
        r"^/docs",
        r"^/redoc",
        r"^/openapi\.json$",
        r"^/$",  # Root path
        r"^/api$",  # API info endpoint
    ]

    # Add configured excluded paths
    for excluded_path in excluded_paths:
        if excluded_path:
            # Escape special regex characters except *
            pattern = re.escape(excluded_path).replace(r"\*", ".*")
            excluded_patterns.append(f"^{pattern}$")

    # Check if path matches any excluded pattern
    for pattern in excluded_patterns:
        if re.match(pattern, path):
            return False

    return True


def map_endpoint_to_resource_type(path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Map endpoint path to resource type and resource ID.

    Args:
        path: Request path

    Returns:
        Tuple of (resource_type, resource_id)
        Returns (None, None) if path doesn't match known patterns
    """
    # Pattern: /conversations/{uuid}
    conversation_pattern = r"/(?:api/v[0-9]+/)?conversations/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(?:/(?!messages|shares).*)?$"
    match = re.match(conversation_pattern, path, re.IGNORECASE)
    if match:
        return ("conversation", match.group(1))

    # Pattern: /conversations/{uuid}/messages
    messages_pattern = r"/(?:api/v[0-9]+/)?conversations/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/messages"
    match = re.match(messages_pattern, path, re.IGNORECASE)
    if match:
        return ("message", match.group(1))

    # Pattern: /conversations/{uuid}/shares
    shares_pattern = r"/(?:api/v[0-9]+/)?conversations/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/shares"
    match = re.match(shares_pattern, path, re.IGNORECASE)
    if match:
        return ("conversation", match.group(1))

    # Pattern: /users/{uuid}
    user_pattern = r"/(?:api/v[0-9]+/)?users/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
    match = re.match(user_pattern, path, re.IGNORECASE)
    if match:
        return ("user", match.group(1))

    # Pattern: /admin/users (list users)
    admin_users_pattern = r"/(?:api/v[0-9]+/)?admin/users"
    if re.match(admin_users_pattern, path, re.IGNORECASE):
        return ("user", None)

    # Pattern: /conversations/shared-with-me
    shared_pattern = r"/(?:api/v[0-9]+/)?conversations/shared-with-me"
    if re.match(shared_pattern, path, re.IGNORECASE):
        return ("conversation", None)

    return (None, None)


def extract_client_ip(request: Request) -> Optional[str]:
    """
    Extract client IP address from request.

    Checks X-Forwarded-For header first (for cloud deployments),
    then falls back to client.host.

    Args:
        request: FastAPI request

    Returns:
        Client IP address or None
    """
    # Check X-Forwarded-For header (set by proxies/load balancers)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can be a comma-separated list
        # First IP is the original client
        return forwarded_for.split(",")[0].strip()

    # Fallback to direct client IP
    if request.client:
        return request.client.host

    return None


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log read operations to audit logs.

    Intercepts all GET requests and logs read operations for:
    - Conversations
    - Messages
    - Users

    Excludes health checks, metrics, keep-alive, and static assets.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Process request and log read operations.

        Args:
            request: FastAPI request
            call_next: Next middleware in chain

        Returns:
            Response from next middleware
        """
        # Get method and path
        method = request.method
        path = request.url.path

        # Check if read operation logging is enabled
        try:
            settings = get_settings()
            if not settings.AUDIT_READ_OPERATIONS:
                # Logging disabled, skip
                return await call_next(request)
        except Exception:
            # If settings not available, default to enabled
            pass

        # Process request first
        response = await call_next(request)

        # Only log if request succeeded (2xx status code)
        if not (200 <= response.status_code < 300):
            return response

        # Check if should log this operation
        if not should_log_read_operation(path, method):
            return response

        # Map endpoint to resource type
        resource_type, resource_id = map_endpoint_to_resource_type(path)

        if resource_type is None:
            # Unknown endpoint, don't log
            return response

        # Extract user ID from request state (set by auth middleware)
        user_id = None
        if hasattr(request.state, "user"):
            user = request.state.user
            user_id = user.user_id if hasattr(user, "user_id") else None

        # Extract request metadata
        client_ip = extract_client_ip(request)
        user_agent = request.headers.get("User-Agent")
        correlation_id = getattr(request.state, "correlation_id", None)

        # Parse resource_id as UUID if present
        resource_uuid = None
        if resource_id:
            try:
                resource_uuid = uuid.UUID(resource_id)
            except ValueError:
                # Invalid UUID, log without resource_id
                pass

        # Log read operation asynchronously (non-blocking)
        try:
            await AuditLogger.log_read_operation(
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_uuid,
                ip_address=client_ip,
                user_agent=user_agent,
                metadata={
                    "endpoint": path,
                    "method": method,
                    "status_code": response.status_code
                },
                correlation_id=correlation_id
            )
        except Exception as e:
            # Log error but don't fail the request
            logger.error(
                f"Failed to log read operation: {str(e)}",
                extra={
                    "path": path,
                    "method": method,
                    "user_id": str(user_id) if user_id else None,
                    "correlation_id": correlation_id
                },
                exc_info=True
            )

        return response
