"""
Prometheus Metrics Endpoint

Exposes application metrics for Prometheus scraping.

IMPORTANT: HTTP metrics are IMPORTED from middleware.py to avoid duplication.
Only business-specific metrics should be defined here.
"""

from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# IMPORT HTTP metrics from middleware (DO NOT redefine them here)
from src.core.middleware import (
    http_requests_total,
    http_request_duration_seconds
)

router = APIRouter()


@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus exposition format.
    HTTP metrics are defined in middleware.py and imported here.
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )