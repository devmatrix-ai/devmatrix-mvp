"""
Global Exception Handlers

Centralized exception handling with structured logging.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
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
        JSONResponse: Standard error response with request_id
    """
    logger.error('unhandled_exception', exception_type=type(exc).__name__, exception_message=str(exc), path=request.url.path, method=request.method, exc_info=True)
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=jsonable_encoder({'error': 'internal_server_error', 'message': 'An unexpected error occurred', 'request_id': request.headers.get('X-Request-ID', 'unknown')}))

async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle HTTP exceptions with structured logging.

    Args:
        request: The request that caused the exception
        exc: The HTTP exception

    Returns:
        JSONResponse: Standard error response
    """
    logger.warning('http_exception', status_code=exc.status_code, detail=exc.detail, path=request.url.path, method=request.method)
    return JSONResponse(status_code=exc.status_code, content=jsonable_encoder({'error': f'http_{exc.status_code}', 'message': exc.detail, 'request_id': request.headers.get('X-Request-ID', 'unknown')}))

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle validation errors from Pydantic.

    Args:
        request: The request that caused the validation error
        exc: The validation error

    Returns:
        JSONResponse: Validation error details
    """
    logger.warning('validation_error', errors=exc.errors(), path=request.url.path, method=request.method)
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=jsonable_encoder({'error': 'validation_error', 'message': 'Request validation failed', 'details': exc.errors(), 'request_id': request.headers.get('X-Request-ID', 'unknown')}))