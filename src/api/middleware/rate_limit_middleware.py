"""
Rate Limiting Middleware

Implements API rate limiting based on Redis sliding window algorithm.
Updated for Phase 1 Critical Security Vulnerabilities - Group 5: API Security Layer

Features:
- Redis-backed distributed rate limiting
- Sliding window rate limiting algorithm
- Per-IP rate limits for anonymous users: 30 req/min global, 10 req/min auth endpoints
- Per-user rate limits for authenticated users: 100 req/min global, 20 req/min auth endpoints
- Rate limit headers in all responses
- HTTP 429 with Retry-After header when limit exceeded
"""

import time
from typing import Optional, Tuple
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response, JSONResponse
import redis

from src.config.settings import get_settings
from src.observability import get_logger

logger = get_logger("rate_limit_middleware")

# Get settings
settings = get_settings()

# Default rate limits (requests per minute)
# Anonymous users
ANONYMOUS_GLOBAL_LIMIT = 30  # 30 req/min for general endpoints
ANONYMOUS_AUTH_LIMIT = 10    # 10 req/min for auth endpoints

# Authenticated users
AUTHENTICATED_GLOBAL_LIMIT = 100  # 100 req/min for general endpoints
AUTHENTICATED_AUTH_LIMIT = 20     # 20 req/min for auth endpoints

# Redis TTL (2 minutes to be safe)
REDIS_TTL = 120


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis sliding window algorithm.

    Applies different rate limits based on:
    - Authentication status (anonymous vs authenticated)
    - Endpoint type (general vs auth endpoints)

    Headers added to all responses:
    - X-RateLimit-Limit: Maximum requests allowed per minute
    - X-RateLimit-Remaining: Requests remaining in current window
    - X-RateLimit-Reset: Unix timestamp when limit resets
    """

    def __init__(self, app, redis_client: Optional[redis.Redis] = None):
        """
        Initialize rate limit middleware.

        Args:
            app: FastAPI application
            redis_client: Optional Redis client (creates new one if None)
        """
        super().__init__(app)

        if redis_client:
            self.redis = redis_client
        else:
            try:
                self.redis = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    password=settings.REDIS_PASSWORD,
                    decode_responses=True,
                    socket_timeout=1,
                    socket_connect_timeout=1
                )
                # Test connection
                self.redis.ping()
                logger.info(f"Rate limiter connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            except Exception as e:
                logger.warning(f"Redis not available for rate limiting: {str(e)}")
                self.redis = None

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Process request and apply rate limiting.

        Args:
            request: Incoming request
            call_next: Next middleware/endpoint

        Returns:
            Response with rate limit headers
        """
        # Skip rate limiting for certain paths
        if self._should_skip_rate_limit(request.url.path):
            return await call_next(request)

        # Get user identifier and rate limit
        user_id, rate_limit = await self._get_user_and_limit(request)

        # Check rate limit if Redis is available
        if self.redis:
            allowed, remaining, reset_time = self._check_rate_limit(user_id, rate_limit)

            if not allowed:
                logger.warning(f"Rate limit exceeded for {user_id}")
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "code": "RATE_001",
                        "error": "Rate limit exceeded",
                        "message": f"Too many requests. Limit: {rate_limit} requests per minute",
                        "retry_after": reset_time - int(time.time())
                    },
                    headers={
                        "X-RateLimit-Limit": str(rate_limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_time),
                        "Retry-After": str(reset_time - int(time.time()))
                    }
                )
        else:
            # Redis not available - allow request but log warning
            remaining = rate_limit
            reset_time = int(time.time()) + 60

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining - 1))
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response

    def _should_skip_rate_limit(self, path: str) -> bool:
        """
        Check if path should skip rate limiting.

        Args:
            path: Request path

        Returns:
            True if should skip rate limiting
        """
        # Skip health checks and static files
        skip_paths = [
            "/health",
            "/api/v1/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/static",
            "/assets"
        ]

        for skip_path in skip_paths:
            if path.startswith(skip_path):
                return True

        return False

    async def _get_user_and_limit(self, request: Request) -> Tuple[str, int]:
        """
        Get user identifier and their rate limit.

        Args:
            request: Incoming request

        Returns:
            Tuple of (user_identifier, rate_limit_per_minute)
        """
        # Try to get user from request state (set by auth middleware)
        user = getattr(request.state, "user", None)

        # Check if this is an auth endpoint
        is_auth_endpoint = "/auth/" in request.url.path

        if user:
            # Authenticated user
            user_id = f"user:{user.user_id}"

            # Apply different limits for auth endpoints
            if is_auth_endpoint:
                rate_limit = AUTHENTICATED_AUTH_LIMIT
            else:
                rate_limit = AUTHENTICATED_GLOBAL_LIMIT
        else:
            # Unauthenticated - use IP address with lower limit
            client_ip = request.client.host if request.client else "unknown"
            user_id = f"ip:{client_ip}"

            # Apply different limits for auth endpoints
            if is_auth_endpoint:
                rate_limit = ANONYMOUS_AUTH_LIMIT
            else:
                rate_limit = ANONYMOUS_GLOBAL_LIMIT

        return user_id, rate_limit

    def _check_rate_limit(self, user_id: str, rate_limit: int) -> Tuple[bool, int, int]:
        """
        Check if request is within rate limit using sliding window.

        Args:
            user_id: User identifier
            rate_limit: Requests allowed per minute

        Returns:
            Tuple of (allowed, remaining_requests, reset_timestamp)
        """
        now = time.time()
        window_start = now - 60  # 60 second window

        # Redis key for this user's requests
        key = f"rate_limit:{user_id}"

        try:
            # Remove old requests outside the sliding window
            self.redis.zremrangebyscore(key, 0, window_start)

            # Count requests in current window
            request_count = self.redis.zcard(key)

            # Check if under limit
            if request_count < rate_limit:
                # Add current request
                self.redis.zadd(key, {str(now): now})

                # Set expiry on key (2 minutes to be safe)
                self.redis.expire(key, REDIS_TTL)

                remaining = rate_limit - request_count - 1
                reset_time = int(now) + 60

                return True, remaining, reset_time
            else:
                # Over limit
                # Calculate when oldest request will expire
                oldest_requests = self.redis.zrange(key, 0, 0, withscores=True)
                if oldest_requests:
                    oldest_time = oldest_requests[0][1]
                    reset_time = int(oldest_time) + 60
                else:
                    reset_time = int(now) + 60

                return False, 0, reset_time

        except Exception as e:
            logger.error(f"Rate limit check failed: {str(e)}")
            # On error, allow request (fail open)
            return True, rate_limit, int(now) + 60


def create_rate_limit_middleware(app):
    """
    Factory function to create and add rate limit middleware.

    Args:
        app: FastAPI application

    Returns:
        App with rate limit middleware added
    """
    app.add_middleware(RateLimitMiddleware)
    return app
