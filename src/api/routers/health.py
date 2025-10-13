"""
Health Check Router

Endpoints for health and readiness checks.
"""

from typing import Dict, Any

from fastapi import APIRouter, Response, status
from pydantic import BaseModel


router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    components: Dict[str, Any]


@router.get(
    "",
    response_model=HealthResponse,
    summary="Health check",
    description="Check application and component health",
)
async def health_check() -> HealthResponse:
    """
    Perform health check.

    Returns:
        Health status for all components
    """
    from ..app import health_check

    result = health_check.check_all()
    return HealthResponse(**result)


@router.get(
    "/live",
    summary="Liveness probe",
    description="Kubernetes liveness probe endpoint",
)
async def liveness_probe() -> Dict[str, str]:
    """
    Liveness probe for Kubernetes.

    Returns:
        Simple alive status
    """
    return {"status": "alive"}


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Kubernetes readiness probe endpoint",
)
async def readiness_probe(response: Response) -> Dict[str, str]:
    """
    Readiness probe for Kubernetes.

    Returns:
        Ready status based on health checks
    """
    from ..app import health_check

    result = health_check.check_all()

    if result["status"] == "healthy":
        return {"status": "ready"}
    else:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "reason": result["status"]}
