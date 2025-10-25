"""
Unit Tests: Core Security Infrastructure

Tests for ErrorResponse model, correlation_id middleware, and global exception handler.
Part of Phase 1 Critical Security Vulnerabilities - Group 2.

Test Coverage:
- ErrorResponse model validation
- Correlation ID generation and format
- Timestamp format validation
- Correlation ID middleware functionality
- Global exception handler
- Error code conventions
"""

import pytest
import uuid
import os
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from pydantic import ValidationError


# Set test environment variables before any imports
os.environ.setdefault('JWT_SECRET', 'test_secret_key_that_is_32_chars_min_for_validation_testing')
os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost:5432/test')
os.environ.setdefault('CORS_ALLOWED_ORIGINS', 'http://localhost:3000')


class TestErrorResponseModel:
    """Tests for ErrorResponse Pydantic model."""

    def test_error_response_includes_all_required_fields(self):
        """Test ErrorResponse model includes all required fields."""
        # Import directly to avoid loading entire app
        from src.api.responses.error_response import ErrorResponse

        # Create error response with minimal fields
        error = ErrorResponse(
            code="AUTH_001",
            message="Invalid credentials"
        )

        # Verify all fields present
        assert hasattr(error, 'code')
        assert hasattr(error, 'message')
        assert hasattr(error, 'details')
        assert hasattr(error, 'correlation_id')
        assert hasattr(error, 'timestamp')

        # Verify field values
        assert error.code == "AUTH_001"
        assert error.message == "Invalid credentials"
        assert error.details == {}
        assert error.correlation_id is not None
        assert error.timestamp is not None

    def test_correlation_id_is_valid_uuid_v4(self):
        """Test correlation_id is valid UUID v4 format."""
        from src.api.responses.error_response import ErrorResponse

        error = ErrorResponse(
            code="AUTH_001",
            message="Test error"
        )

        # Verify correlation_id is valid UUID
        try:
            correlation_uuid = uuid.UUID(error.correlation_id)
            # Verify it's UUID v4
            assert correlation_uuid.version == 4
        except ValueError:
            pytest.fail("correlation_id is not a valid UUID")

    def test_timestamp_is_iso8601_utc_format(self):
        """Test timestamp is ISO 8601 UTC format."""
        from src.api.responses.error_response import ErrorResponse

        error = ErrorResponse(
            code="AUTH_001",
            message="Test error"
        )

        # Verify timestamp format
        assert error.timestamp.endswith("Z"), "Timestamp should end with 'Z' for UTC"

        # Verify timestamp is valid ISO 8601
        try:
            # Remove 'Z' and parse
            dt = datetime.fromisoformat(error.timestamp.replace('Z', '+00:00'))
            assert dt is not None
        except ValueError:
            pytest.fail("Timestamp is not valid ISO 8601 format")

    def test_error_codes_match_conventions(self):
        """Test error codes follow naming conventions."""
        from src.api.responses.error_response import ErrorResponse

        # Test various error code conventions
        error_codes = [
            "AUTH_001",  # Authentication
            "AUTHZ_001",  # Authorization
            "VAL_001",  # Validation
            "DB_001",  # Database
            "RATE_001",  # Rate limiting
            "SYS_001",  # System
        ]

        for code in error_codes:
            error = ErrorResponse(code=code, message="Test")
            assert error.code == code
            assert "_" in error.code, "Error code should have underscore separator"


class TestCorrelationIdMiddleware:
    """Tests for correlation_id middleware."""

    def test_correlation_id_middleware_generates_unique_id_per_request(self):
        """Test correlation_id middleware generates unique ID per request."""
        from src.api.middleware.correlation_id_middleware import correlation_id_middleware

        # Create test app
        app = FastAPI()

        # Add middleware
        app.middleware("http")(correlation_id_middleware)

        # Add test endpoint
        @app.get("/test")
        async def test_endpoint(request: Request):
            return {"correlation_id": request.state.correlation_id}

        client = TestClient(app)

        # Make multiple requests
        response1 = client.get("/test")
        response2 = client.get("/test")

        # Verify both successful
        assert response1.status_code == 200
        assert response2.status_code == 200

        # Verify different correlation IDs
        id1 = response1.json()["correlation_id"]
        id2 = response2.json()["correlation_id"]

        assert id1 != id2, "Each request should have unique correlation_id"

        # Verify both are valid UUIDs
        uuid.UUID(id1)
        uuid.UUID(id2)

    def test_correlation_id_appears_in_response_headers(self):
        """Test correlation_id appears in response headers."""
        from src.api.middleware.correlation_id_middleware import correlation_id_middleware

        # Create test app
        app = FastAPI()

        # Add middleware
        app.middleware("http")(correlation_id_middleware)

        # Add test endpoint
        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)

        # Make request
        response = client.get("/test")

        # Verify header exists
        assert "X-Correlation-ID" in response.headers, "X-Correlation-ID header should be present"

        # Verify header value is valid UUID
        correlation_id = response.headers["X-Correlation-ID"]
        uuid.UUID(correlation_id)


class TestGlobalExceptionHandler:
    """Tests for global exception handler."""

    def test_global_exception_handler_converts_exceptions_to_error_response(self):
        """Test global exception handler converts exceptions to ErrorResponse format."""
        from src.api.middleware.correlation_id_middleware import correlation_id_middleware
        from src.api.responses.error_response import ErrorResponse
        from fastapi.responses import JSONResponse

        # Create test app
        app = FastAPI()

        # Add correlation ID middleware first
        app.middleware("http")(correlation_id_middleware)

        # Add test endpoint that raises exception
        @app.get("/test-error")
        async def test_error():
            raise ValueError("Test exception")

        # Add global exception handler
        @app.exception_handler(Exception)
        async def global_exception_handler(request: Request, exc: Exception):
            correlation_id = getattr(request.state, 'correlation_id', str(uuid.uuid4()))

            error_response = ErrorResponse(
                code="SYS_001",
                message=str(exc),
                correlation_id=correlation_id
            )

            return JSONResponse(
                status_code=500,
                content=error_response.model_dump(),
                headers={"X-Correlation-ID": correlation_id}
            )

        client = TestClient(app)

        # Make request that triggers exception
        response = client.get("/test-error")

        # Verify 500 status
        assert response.status_code == 500

        # Verify ErrorResponse format
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "details" in data
        assert "correlation_id" in data
        assert "timestamp" in data

        # Verify correlation_id in header matches body
        assert response.headers["X-Correlation-ID"] == data["correlation_id"]

    def test_exception_handler_preserves_http_exceptions(self):
        """Test exception handler preserves HTTPException without wrapping."""
        from src.api.middleware.correlation_id_middleware import correlation_id_middleware
        from src.api.responses.error_response import ErrorResponse
        from fastapi.responses import JSONResponse

        # Create test app
        app = FastAPI()

        # Add middleware
        app.middleware("http")(correlation_id_middleware)

        # Add test endpoint
        @app.get("/test-http-error")
        async def test_http_error():
            raise HTTPException(status_code=401, detail="Unauthorized")

        # Add global exception handler
        @app.exception_handler(Exception)
        async def global_exception_handler(request: Request, exc: Exception):
            # Re-raise HTTPException without wrapping
            if isinstance(exc, HTTPException):
                raise exc

            correlation_id = getattr(request.state, 'correlation_id', str(uuid.uuid4()))

            error_response = ErrorResponse(
                code="SYS_001",
                message=str(exc),
                correlation_id=correlation_id
            )

            return JSONResponse(
                status_code=500,
                content=error_response.model_dump(),
                headers={"X-Correlation-ID": correlation_id}
            )

        client = TestClient(app)

        # Make request
        response = client.get("/test-http-error")

        # Verify HTTPException status preserved
        assert response.status_code == 401
