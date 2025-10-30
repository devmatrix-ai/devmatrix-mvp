"""
Authentication Middleware for FastAPI

Provides JWT-based authentication for protected endpoints.
Updated with Group 3: Token blacklist checking and correlation_id logging.
Updated with Phase 2 Task Group 4: Session timeout management (idle + absolute).
"""

from typing import Optional
from datetime import datetime
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from src.services.auth_service import AuthService
from src.services.session_service import SessionService
from src.models.user import User
from src.config.settings import get_settings
from src.observability import get_logger

logger = get_logger("auth_middleware")
settings = get_settings()

# HTTP Bearer security scheme
security = HTTPBearer()

# Global session service instance
_session_service: Optional[SessionService] = None


def get_session_service() -> SessionService:
    """
    Get global SessionService instance (singleton).

    Returns:
        SessionService instance
    """
    global _session_service

    if _session_service is None:
        _session_service = SessionService()

    return _session_service


class AuthMiddleware:
    """
    Authentication middleware for FastAPI dependency injection.

    Updated with Phase 2 Task Group 4:
    - Checks idle timeout (30 minutes via Redis session metadata)
    - Checks absolute timeout (12 hours from iat claim)
    - Updates session activity on every request
    - Returns 401 with clear message on timeout

    Usage in route:
        from fastapi import Depends
        from src.api.middleware.auth_middleware import get_current_user, get_current_active_user

        @app.get("/protected")
        async def protected_route(current_user: User = Depends(get_current_user)):
            return {"user_id": current_user.user_id}

        @app.get("/admin")
        async def admin_route(current_user: User = Depends(get_current_superuser)):
            return {"admin": True}
    """

    def __init__(self):
        self.auth_service = AuthService()
        self.session_service = get_session_service()


# Global auth middleware instance
auth_middleware = AuthMiddleware()


async def get_token_from_header(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Extract JWT token from Authorization header.

    Args:
        credentials: HTTP Bearer credentials from header

    Returns:
        JWT token string

    Raises:
        HTTPException: If credentials are missing or invalid
    """
    if not credentials:
        logger.warning("Missing authorization credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if credentials.scheme.lower() != "bearer":
        logger.warning(f"Invalid authorization scheme: {credentials.scheme}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization scheme. Use Bearer token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return credentials.credentials


async def get_current_user(request: Request, token: str = Depends(get_token_from_header)) -> User:
    """
    Get current authenticated user from JWT token.

    Group 3 Update: Now checks token blacklist before user lookup.
    Phase 2 Task Group 4 Update: Checks session timeout (idle + absolute).

    Session Timeout Checks:
    1. Verify JWT is valid (standard JWT validation)
    2. Check token is not blacklisted
    3. Check Redis session metadata exists (idle timeout)
    4. Check absolute timeout from iat claim (12 hours)
    5. Update last activity and reset idle timer

    Args:
        request: FastAPI request (for storing user in state and correlation_id)
        token: JWT access token

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid, blacklisted, or session expired
    """
    correlation_id = getattr(request.state, 'correlation_id', None)

    # Phase 2 Task Group 4: Decode token to get session info
    try:
        # Decode token (standard validation)
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        logger.warning(
            "Expired JWT token",
            extra={"correlation_id": correlation_id}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError as e:
        logger.warning(
            f"Invalid JWT token: {str(e)}",
            extra={"correlation_id": correlation_id}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Extract session info
    user_id = payload.get("sub")
    jti = payload.get("jti")
    iat = payload.get("iat")

    if not jti:
        logger.warning(
            "Token missing jti claim",
            extra={"correlation_id": correlation_id}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not iat:
        logger.warning(
            "Token missing iat claim",
            extra={"correlation_id": correlation_id}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Phase 2 Task Group 4: Check absolute timeout (12 hours from issuance)
    issued_at = datetime.utcfromtimestamp(iat)
    session_service = get_session_service()

    if session_service.check_absolute_timeout(issued_at):
        logger.warning(
            f"Session exceeded absolute timeout for user {user_id}",
            extra={"correlation_id": correlation_id}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Phase 2 Task Group 4: Check idle timeout (Redis session metadata exists)
    from uuid import UUID
    session_metadata = session_service.get_session(UUID(user_id), jti)

    if not session_metadata:
        logger.warning(
            f"Session not found or expired (idle timeout) for user {user_id}",
            extra={"correlation_id": correlation_id}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Get user (includes blacklist check)
    user = auth_middleware.auth_service.get_current_user(token, correlation_id)

    if not user:
        logger.warning(
            "Invalid or expired token",
            extra={"correlation_id": correlation_id}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Phase 2 Task Group 4: Update session activity (reset idle timer)
    session_service.update_activity(user.user_id, jti)

    # Store user in request state for rate limiting middleware
    request.state.user = user

    logger.debug(
        f"Authenticated user: {user.user_id} ({user.email})",
        extra={"correlation_id": correlation_id}
    )
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current active user (account not disabled).

    Args:
        current_user: User from get_current_user dependency

    Returns:
        User object

    Raises:
        HTTPException: If user account is inactive
    """
    if not current_user.is_active:
        logger.warning(f"Inactive user attempted access: {current_user.user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    return current_user


async def get_current_superuser(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Get current superuser (admin privileges).

    Args:
        current_user: User from get_current_active_user dependency

    Returns:
        User object

    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        logger.warning(f"Non-superuser attempted admin access: {current_user.user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges. Admin access required"
        )

    return current_user


async def get_optional_user(request: Request) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise.

    Useful for endpoints that work both with and without authentication.

    Args:
        request: FastAPI request

    Returns:
        User object or None
    """
    correlation_id = getattr(request.state, 'correlation_id', None)

    # Try to get authorization header
    authorization = request.headers.get("Authorization")

    if not authorization:
        return None

    # Extract token
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None

        # Get user
        user = auth_middleware.auth_service.get_current_user(token, correlation_id)
        return user

    except Exception as e:
        logger.debug(
            f"Optional auth failed: {str(e)}",
            extra={"correlation_id": correlation_id}
        )
        return None
