"""
Prometheus Metrics for Caching System

Metrics for monitoring cache performance, hit rates, and cost savings.

Metrics Categories:
- Cache hits/misses per layer (LLM, RAG, RAG similarity)
- Cache operations (writes, invalidations, errors)
- Cost savings from cache hits
- Batching statistics

Integration:
- FastAPI Prometheus exporter exposes metrics at /metrics endpoint
- Grafana dashboards visualize cache performance
- Alerts trigger on low hit rates or high error rates
"""

from prometheus_client import Counter, Histogram

# ========================================
# Cache Hit/Miss Rates
# ========================================

CACHE_HIT_RATE = Counter(
    "v2_cache_hits_total",
    "Total number of cache hits",
    ["cache_layer"],  # llm, rag, rag_similarity
)

CACHE_MISS_RATE = Counter(
    "v2_cache_misses_total",
    "Total number of cache misses",
    ["cache_layer"],  # llm, rag
)

# ========================================
# Cache Operations
# ========================================

CACHE_WRITES = Counter(
    "v2_cache_writes_total",
    "Total number of cache writes",
    ["cache_layer"],  # llm, rag
)

CACHE_INVALIDATIONS = Counter(
    "v2_cache_invalidations_total",
    "Total number of cache invalidations",
    ["cache_layer"],  # llm, rag
)

CACHE_ERRORS = Counter(
    "v2_cache_errors_total",
    "Total number of cache operation errors",
    ["cache_layer", "operation"],  # cache_layer: llm/rag, operation: get/set/invalidate
)

# ========================================
# Cost Savings
# ========================================

CACHE_COST_SAVINGS_USD = Counter(
    "v2_cache_cost_savings_usd_total",
    "Total cost saved by cache hits (USD)",
    ["cache_layer"],  # llm, rag
)

# ========================================
# Batching Metrics
# ========================================

BATCH_SIZE = Histogram(
    "v2_batch_size",
    "Distribution of request batch sizes",
    buckets=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],  # Track up to 10 requests per batch
)

BATCH_REQUESTS_PROCESSED = Counter(
    "v2_batch_requests_processed_total", "Total number of requests processed via batching"
)

# ========================================
# Helper Functions
# ========================================


def calculate_hit_rate(cache_layer: str = "llm") -> float:
    """
    Calculate cache hit rate for a specific layer

    Args:
        cache_layer: Cache layer to calculate hit rate for (llm, rag, rag_similarity)

    Returns:
        Hit rate as float (0.0 - 1.0)

    Note:
        This queries Prometheus metrics directly. For production, use
        Prometheus queries via PromQL for better performance.
    """
    try:
        # Get metric samples
        hits = CACHE_HIT_RATE.labels(cache_layer=cache_layer)._value.get()
        misses = CACHE_MISS_RATE.labels(cache_layer=cache_layer)._value.get()

        total = hits + misses
        if total == 0:
            return 0.0

        return hits / total

    except Exception:
        return 0.0


def get_cache_statistics(cache_layer: str = "llm") -> dict:
    """
    Get comprehensive cache statistics

    Args:
        cache_layer: Cache layer to get statistics for

    Returns:
        Dict with cache statistics: {
            'hit_rate': float,
            'total_hits': int,
            'total_misses': int,
            'total_writes': int,
            'total_invalidations': int,
            'total_errors': int
        }
    """
    try:
        hits = CACHE_HIT_RATE.labels(cache_layer=cache_layer)._value.get()
        misses = CACHE_MISS_RATE.labels(cache_layer=cache_layer)._value.get()
        writes = CACHE_WRITES.labels(cache_layer=cache_layer)._value.get()
        invalidations = CACHE_INVALIDATIONS.labels(cache_layer=cache_layer)._value.get()

        # Sum errors across all operations
        total_errors = 0
        for operation in ["get", "set", "invalidate"]:
            try:
                total_errors += (
                    CACHE_ERRORS.labels(cache_layer=cache_layer, operation=operation)
                    ._value.get()
                )
            except Exception:
                pass

        total = hits + misses
        hit_rate = (hits / total) if total > 0 else 0.0

        return {
            "hit_rate": hit_rate,
            "total_hits": int(hits),
            "total_misses": int(misses),
            "total_writes": int(writes),
            "total_invalidations": int(invalidations),
            "total_errors": total_errors,
        }

    except Exception as e:
        return {
            "hit_rate": 0.0,
            "total_hits": 0,
            "total_misses": 0,
            "total_writes": 0,
            "total_invalidations": 0,
            "total_errors": 0,
            "error": str(e),
        }
