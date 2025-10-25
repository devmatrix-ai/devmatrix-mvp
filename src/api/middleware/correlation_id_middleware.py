"""
Correlation ID Middleware

Generates unique correlation ID for each request to enable request tracing.
Part of Phase 1 Critical Security Vulnerabilities - P0-8.

The correlation ID is:
- Generated as UUID v4 for each request
- Stored in request.state.correlation_id
- Added to response headers as X-Correlation-ID
- Used in logs and error responses for tracing

This middleware MUST run before all other middleware to ensure
correlation_id is available throughout the request lifecycle.

Usage:
    from src.api.middleware.correlation_id_middleware import correlation_id_middleware

    app = FastAPI()
    app.middleware("http")(correlation_id_middleware)

    # In request handlers
    @app.get("/example")
    async def example(request: Request):
        correlation_id = request.state.correlation_id
        logger.info("Processing request", extra={"correlation_id": correlation_id})
        return {"status": "ok"}
"""

import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


async def correlation_id_middleware(request: Request, call_next):
    """
    Middleware to add correlation ID to each request.

    Generates a unique UUID v4 for each request and adds it to:
    - request.state.correlation_id (accessible in handlers)
    - X-Correlation-ID response header (visible to clients)

    Args:
        request: FastAPI Request object
        call_next: Next middleware/handler in chain

    Returns:
        Response with X-Correlation-ID header
    """
    # Generate unique correlation ID for this request
    correlation_id = str(uuid.uuid4())

    # Store in request state for access in handlers
    request.state.correlation_id = correlation_id

    # Process request
    response = await call_next(request)

    # Add correlation ID to response headers
    response.headers["X-Correlation-ID"] = correlation_id

    return response
