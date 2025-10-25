"""
Metrics Router

Endpoints for Prometheus-compatible metrics export and MGE V2 cache statistics.
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


# ========================================
# MGE V2 Cache Statistics
# ========================================


class CacheStatistics(BaseModel):
    """Cache statistics response for a specific layer."""
    cache_layer: str
    hit_rate: float
    total_hits: int
    total_misses: int
    total_writes: int
    total_invalidations: int
    total_errors: int


class CombinedCacheStatistics(BaseModel):
    """Combined cache statistics across all layers."""
    llm_cache: CacheStatistics
    rag_cache: CacheStatistics
    rag_similarity_cache: CacheStatistics
    combined_hit_rate: float


@router.get(
    "/cache/statistics",
    response_model=CombinedCacheStatistics,
    summary="Get MGE V2 cache statistics",
    description="Get comprehensive statistics for all cache layers (LLM, RAG, RAG similarity)",
)
async def get_cache_statistics() -> CombinedCacheStatistics:
    """
    Get MGE V2 cache statistics across all layers.

    Returns comprehensive metrics including:
    - Hit rates per layer
    - Total hits/misses/writes
    - Cache invalidations
    - Error counts

    Returns:
        Combined cache statistics for LLM, RAG, and RAG similarity caches
    """
    from src.mge.v2.caching.metrics import get_cache_statistics

    # Get statistics for each cache layer
    llm_stats = get_cache_statistics("llm")
    rag_stats = get_cache_statistics("rag")
    rag_similarity_stats = get_cache_statistics("rag_similarity")

    # Calculate combined hit rate
    total_hits = (
        llm_stats["total_hits"]
        + rag_stats["total_hits"]
        + rag_similarity_stats["total_hits"]
    )
    total_misses = (
        llm_stats["total_misses"]
        + rag_stats["total_misses"]
        + rag_similarity_stats["total_misses"]
    )
    total = total_hits + total_misses
    combined_hit_rate = (total_hits / total) if total > 0 else 0.0

    return CombinedCacheStatistics(
        llm_cache=CacheStatistics(cache_layer="llm", **llm_stats),
        rag_cache=CacheStatistics(cache_layer="rag", **rag_stats),
        rag_similarity_cache=CacheStatistics(
            cache_layer="rag_similarity", **rag_similarity_stats
        ),
        combined_hit_rate=combined_hit_rate,
    )


@router.get(
    "/cache/statistics/{cache_layer}",
    response_model=CacheStatistics,
    summary="Get cache statistics for specific layer",
    description="Get statistics for a specific cache layer (llm, rag, rag_similarity)",
)
async def get_cache_layer_statistics(cache_layer: str) -> CacheStatistics:
    """
    Get cache statistics for a specific layer.

    Args:
        cache_layer: Cache layer to query (llm, rag, rag_similarity)

    Returns:
        Cache statistics for the specified layer
    """
    from src.mge.v2.caching.metrics import get_cache_statistics

    if cache_layer not in ["llm", "rag", "rag_similarity"]:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail=f"Invalid cache_layer. Must be one of: llm, rag, rag_similarity",
        )

    stats = get_cache_statistics(cache_layer)
    return CacheStatistics(cache_layer=cache_layer, **stats)
