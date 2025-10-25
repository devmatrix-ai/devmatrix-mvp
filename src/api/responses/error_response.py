"""
Error Response Model

Standardized error response format for all API errors.
Part of Phase 1 Critical Security Vulnerabilities - P0-8.

Error Code Conventions:
- AUTH_xxx: Authentication errors (401)
- AUTHZ_xxx: Authorization errors (403)
- VAL_xxx: Validation errors (400)
- DB_xxx: Database errors (500)
- RATE_xxx: Rate limiting errors (429)
- SYS_xxx: System errors (500)

Usage:
    from src.api.responses import ErrorResponse

    # Create error response
    error = ErrorResponse(
        code="AUTH_001",
        message="Invalid credentials",
        details={"field": "email"}
    )

    # Return as JSON
    return JSONResponse(
        status_code=401,
        content=error.model_dump(),
        headers={"X-Correlation-ID": error.correlation_id}
    )
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any
import uuid


class ErrorResponse(BaseModel):
    """
    Standardized error response model.

    All API errors should use this format for consistency and traceability.
    Each error includes a correlation_id for request tracing.

    Attributes:
        code: Error code following conventions (e.g., AUTH_001)
        message: Human-readable error message
        details: Additional context about the error (optional)
        correlation_id: Unique request identifier for tracing (auto-generated)
        timestamp: ISO 8601 UTC timestamp (auto-generated)

    Examples:
        >>> error = ErrorResponse(code="AUTH_001", message="Invalid credentials")
        >>> error.code
        'AUTH_001'
        >>> error.correlation_id  # Auto-generated UUID v4
        '550e8400-e29b-41d4-a716-446655440000'
        >>> error.timestamp  # Auto-generated ISO 8601 UTC
        '2025-10-25T10:30:00Z'
    """

    code: str = Field(
        ...,
        description="Error code (e.g., AUTH_001, AUTHZ_001, VAL_001, DB_001, RATE_001, SYS_001)",
        examples=["AUTH_001", "AUTHZ_001", "VAL_001"]
    )

    message: str = Field(
        ...,
        description="Human-readable error message",
        examples=["Invalid credentials", "Access denied", "Invalid input"]
    )

    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context about the error",
        examples=[{"field": "email"}, {"resource_id": "123"}]
    )

    correlation_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Request correlation ID for tracing (UUID v4)",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )

    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="ISO 8601 timestamp (UTC)",
        examples=["2025-10-25T10:30:00Z"]
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "code": "AUTH_001",
                "message": "Invalid credentials",
                "details": {},
                "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2025-10-25T10:30:00Z"
            }
        }
