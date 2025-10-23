"""
Rate Limiting Middleware

Implements API rate limiting based on user quotas.
Task Group 7.1-7.2 - Phase 6: Authentication & Multi-tenancy

Features:
- Per-user rate limiting based on quota settings
- Redis-backed distributed rate limiting
- Sliding window rate limiting algorithm
- Rate limit headers in responses
- Configurable default limits
"""

import time
from typing import Optional, Tuple
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response, JSONResponse
import redis

from src.models.user_quota import UserQuota
from src.config.database import get_db_context
from src.config.constants import REDIS_HOST, REDIS_PORT
from src.observability import get_logger

logger = get_logger("rate_limit_middleware")

# Default rate limits (requests per minute)
DEFAULT_RATE_LIMIT = 30
UNAUTHENTICATED_RATE_LIMIT = 10


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis sliding window algorithm.

    Applies per-user rate limits based on UserQuota settings.
    Uses Redis for distributed rate limiting across multiple API instances.

    Headers added to responses:
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
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    decode_responses=True,
                    socket_timeout=1,
                    socket_connect_timeout=1
                )
                # Test connection
                self.redis.ping()
                logger.info(f"Rate limiter connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
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

        if user:
            # Authenticated user - get their quota
            with get_db_context() as db:
                quota = db.query(UserQuota).filter(UserQuota.user_id == user.user_id).first()

                if quota and quota.api_calls_per_minute:
                    rate_limit = quota.api_calls_per_minute
                else:
                    rate_limit = DEFAULT_RATE_LIMIT

            user_id = f"user:{user.user_id}"
        else:
            # Unauthenticated - use IP address with lower limit
            client_ip = request.client.host if request.client else "unknown"
            user_id = f"ip:{client_ip}"
            rate_limit = UNAUTHENTICATED_RATE_LIMIT

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
                self.redis.expire(key, 120)

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
