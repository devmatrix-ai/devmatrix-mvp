"""
Global Exception Handlers

Centralized error handling for consistent API responses.
Uses jsonable_encoder for proper UUID serialization.
"""
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from starlette.exceptions import HTTPException as StarletteHTTPException
import structlog

logger = structlog.get_logger(__name__)


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all unhandled exceptions.

    Args:
        request: The request that caused the exception
        exc: The exception that was raised

    Returns:
        JSON response with error details
    """
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder({
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "path": request.url.path,
            "request_id": request.headers.get("X-Request-ID")
        })
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle HTTP exceptions (4xx, 5xx).

    Args:
        request: The request that caused the exception
        exc: The HTTP exception that was raised

    Returns:
        JSON response with error details
    """
    log_level = "warning" if 400 <= exc.status_code < 500 else "error"
    getattr(logger, log_level)(
        "http_exception",
        path=request.url.path,
        method=request.method,
        status_code=exc.status_code,
        detail=exc.detail
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder({
            "error": f"http_{exc.status_code}",
            "message": exc.detail,
            "path": request.url.path,
            "request_id": request.headers.get("X-Request-ID")
        })
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle request validation errors.

    Args:
        request: The request that caused the validation error
        exc: The validation exception that was raised

    Returns:
        JSON response with validation error details
    """
    logger.warning(
        "validation_error",
        path=request.url.path,
        method=request.method,
        errors=exc.errors()
    )
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({
            "error": "validation_error",
            "message": "Request validation failed",
            "errors": errors,
            "path": request.url.path,
            "request_id": request.headers.get("X-Request-ID")
        })
    )