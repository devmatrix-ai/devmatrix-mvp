"""
Authentication Middleware for FastAPI

Provides JWT-based authentication for protected endpoints.
"""

from typing import Optional
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.services.auth_service import AuthService
from src.models.user import User
from src.observability import get_logger

logger = get_logger("auth_middleware")

# HTTP Bearer security scheme
security = HTTPBearer()


class AuthMiddleware:
    """
    Authentication middleware for FastAPI dependency injection.

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

    Args:
        request: FastAPI request (for storing user in state)
        token: JWT access token

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    user = auth_middleware.auth_service.get_current_user(token)

    if not user:
        logger.warning("Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Store user in request state for rate limiting middleware
    request.state.user = user

    logger.debug(f"Authenticated user: {user.user_id} ({user.email})")
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
        user = auth_middleware.auth_service.get_current_user(token)
        return user

    except Exception as e:
        logger.debug(f"Optional auth failed: {str(e)}")
        return None
