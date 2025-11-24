"""
Custom Middleware

Request ID tracking, metrics, and security headers.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog
from uuid import uuid4
import time
from prometheus_client import Counter, Histogram

# Initialize logger
logger = structlog.get_logger(__name__)

# Prometheus metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"]
)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to all requests."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))

        # Bind to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path
        )

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Track request metrics for Prometheus."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time

        # Record metrics
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()

        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.

    CSP allows FastAPI docs (/docs, /redoc) to load Swagger UI from CDN.
    In production, use reverse proxy (nginx, ALB) for stricter CSP if needed.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # CSP: Allow Swagger UI resources for /docs and /redoc
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' cdn.jsdelivr.net; "
            "script-src 'self' cdn.jsdelivr.net 'unsafe-inline'; "
            "img-src 'self' fastapi.tiangolo.com data:"
        )

        return response