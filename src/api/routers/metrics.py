"""
Metrics Router

Endpoints for Prometheus-compatible metrics export.
"""

from typing import Dict, Any

from fastapi import APIRouter, Response
from pydantic import BaseModel


router = APIRouter(prefix="/metrics", tags=["metrics"])


class MetricsSummary(BaseModel):
    """Metrics summary response."""
    total_workflows: int
    total_executions: int
    executions_by_status: Dict[str, int]
    avg_execution_time_seconds: float


@router.get(
    "",
    response_class=Response,
    summary="Export Prometheus metrics",
    description="Export metrics in Prometheus exposition format",
)
async def get_prometheus_metrics() -> Response:
    """
    Export metrics in Prometheus format.

    Returns:
        Prometheus-formatted metrics
    """
    from ..app import metrics_collector
    from .workflows import workflows_db
    from .executions import executions_db, ExecutionStatus

    # Update metrics
    metrics_collector.set_gauge("workflows_total", len(workflows_db))
    metrics_collector.set_gauge("executions_total", len(executions_db))

    # Count executions by status
    for execution in executions_db.values():
        status = execution["status"]
        metrics_collector.increment_counter(
            "executions_by_status_total",
            1,
            labels={"status": status.value},
        )

    # Export in Prometheus format
    prometheus_text = metrics_collector.export_prometheus()

    return Response(
        content=prometheus_text,
        media_type="text/plain; version=0.0.4",
    )


@router.get(
    "/summary",
    response_model=MetricsSummary,
    summary="Get metrics summary",
    description="Get human-readable metrics summary",
)
async def get_metrics_summary() -> MetricsSummary:
    """
    Get metrics summary.

    Returns:
        Metrics summary with counts and averages
    """
    from .workflows import workflows_db
    from .executions import executions_db, ExecutionStatus
    from datetime import datetime

    # Count executions by status
    status_counts = {}
    execution_times = []

    for execution in executions_db.values():
        status = execution["status"].value
        status_counts[status] = status_counts.get(status, 0) + 1

        # Calculate execution time if completed
        if execution["started_at"] and execution["completed_at"]:
            delta = execution["completed_at"] - execution["started_at"]
            execution_times.append(delta.total_seconds())

    avg_time = sum(execution_times) / len(execution_times) if execution_times else 0.0

    return MetricsSummary(
        total_workflows=len(workflows_db),
        total_executions=len(executions_db),
        executions_by_status=status_counts,
        avg_execution_time_seconds=avg_time,
    )
