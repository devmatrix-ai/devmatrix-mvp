"""
MGE V2 Caching & Reuso System

Multi-layer caching strategy for LLM prompts and RAG queries with request batching.

Components:
- LLMPromptCache: Cache LLM responses by prompt hash (24h TTL)
- RAGQueryCache: Cache RAG queries with similarity matching (1h TTL)
- RequestBatcher: Batch multiple atoms' prompts into single LLM call
- Metrics: Prometheus metrics for monitoring cache performance

Target:
- ≥60% combined hit rate
- ≥30% cost reduction
- ≥40% execution time reduction
"""

__version__ = "1.0.0"

from .llm_prompt_cache import LLMPromptCache, CachedLLMResponse
from .rag_query_cache import RAGQueryCache, CachedRAGResult
from .request_batcher import RequestBatcher, BatchedRequest
from .metrics import (
    CACHE_HIT_RATE,
    CACHE_MISS_RATE,
    CACHE_WRITES,
    CACHE_INVALIDATIONS,
    CACHE_ERRORS,
    CACHE_COST_SAVINGS_USD,
    BATCH_SIZE,
    BATCH_REQUESTS_PROCESSED,
    calculate_hit_rate,
    get_cache_statistics,
)

__all__ = [
    "LLMPromptCache",
    "CachedLLMResponse",
    "RAGQueryCache",
    "CachedRAGResult",
    "RequestBatcher",
    "BatchedRequest",
    "CACHE_HIT_RATE",
    "CACHE_MISS_RATE",
    "CACHE_WRITES",
    "CACHE_INVALIDATIONS",
    "CACHE_ERRORS",
    "CACHE_COST_SAVINGS_USD",
    "BATCH_SIZE",
    "BATCH_REQUESTS_PROCESSED",
    "calculate_hit_rate",
    "get_cache_statistics",
]
