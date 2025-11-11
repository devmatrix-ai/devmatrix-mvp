# MGE V2 Caching & Reuso System

Multi-layer caching strategy for LLM prompts and RAG queries with request batching.

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Components](#components)
- [Usage Examples](#usage-examples)
- [Metrics & Monitoring](#metrics--monitoring)
- [Performance Targets](#performance-targets)
- [Configuration](#configuration)

## Overview

The MGE V2 Caching System implements a 3-layer caching strategy to reduce costs and improve performance:

1. **LLM Prompt Cache (L1)**: Caches LLM responses by prompt hash (24h TTL)
2. **RAG Query Cache (L2)**: Caches RAG queries with similarity matching (1h TTL)
3. **Request Batcher (L3)**: Batches multiple atoms' prompts into single LLM call

### Success Metrics (Gap 10)
- **Cache Hit Rate**: ≥60% combined (validated via Prometheus)
- **Cost Reduction**: ≥30% from caching
- **Execution Time Reduction**: ≥40% from caching + batching

## Architecture

```
┌─────────────────────────────────────────────────┐
│         MGE V2 Execution Pipeline               │
└─────────────────────────────────────────────────┘
                      │
                      ▼
         ┌────────────────────────┐
         │  LLM Prompt Cache (L1) │ ← Redis (24h TTL)
         │  - SHA256 cache keys   │
         │  - Masterplan inval.   │
         └────────────────────────┘
                      │ miss
                      ▼
         ┌────────────────────────┐
         │  Request Batcher (L3)  │ ← Batches 2-5 atoms
         │  - 500ms window        │
         │  - Combined prompts    │
         └────────────────────────┘
                      │
                      ▼
         ┌────────────────────────┐
         │   Anthropic API Call   │
         └────────────────────────┘


┌─────────────────────────────────────────────────┐
│         RAG Retrieval Pipeline                  │
└─────────────────────────────────────────────────┘
                      │
                      ▼
         ┌────────────────────────┐
         │  RAG Query Cache (L2)  │ ← Redis (1h TTL)
         │  - Exact match (hash)  │
         │  - Similarity ≥0.95    │
         └────────────────────────┘
                      │ miss
                      ▼
         ┌────────────────────────┐
         │   Vector Store Query   │ ← ChromaDB
         └────────────────────────┘
```

## Components

### 1. LLM Prompt Cache

**Purpose**: Cache LLM responses to avoid redundant API calls

**Key Features**:
- SHA256-based cache keys (prompt + model + temperature)
- 24-hour TTL (balances freshness vs hit rate)
- Masterplan-level invalidation
- Prometheus metrics integration
- Redis async client for non-blocking operations

**Files**:
- `src/mge/v2/caching/llm_prompt_cache.py` (300 LOC)
- `tests/mge/v2/caching/test_llm_prompt_cache.py` (21 tests, 100% passing)

**Integration**:
```python
from src.llm.enhanced_anthropic_client import EnhancedAnthropicClient

# Enable V2 caching (default: enabled)
client = EnhancedAnthropicClient(
    enable_v2_caching=True,
    redis_url="redis://localhost:6379"
)

# Automatically checks cache before API calls
response = await client.generate_with_caching(
    task_type="task_execution",
    complexity="medium",
    cacheable_context={"system_prompt": "..."},
    variable_prompt="Generate code for..."
)

# Check if cached
if response["cached"]:
    print(f"Saved ${response['cost_analysis']['savings']:.2f}")
```

### 2. RAG Query Cache

**Purpose**: Cache RAG query results with similarity matching

**Key Features**:
- Exact match via SHA256 hash
- Similarity-based partial hits (cosine similarity ≥0.95)
- 1-hour TTL (shorter due to code volatility)
- Embedding-based matching for similar queries
- NumPy for efficient vector operations

**Files**:
- `src/mge/v2/caching/rag_query_cache.py` (320 LOC)
- `tests/mge/v2/caching/test_rag_query_cache.py` (19 tests, 100% passing)

**Integration**:
```python
from src.rag.retriever import Retriever

# Enable V2 caching (default: enabled)
retriever = Retriever(
    vector_store=vector_store,
    enable_v2_caching=True,
    redis_url="redis://localhost:6379"
)

# Automatically checks cache before vector store query
results = retriever.retrieve(
    query="find authentication code",
    top_k=5,
    min_similarity=0.7
)
```

### 3. Request Batcher

**Purpose**: Batch multiple atom prompts to reduce API overhead

**Key Features**:
- Configurable batch window (default: 500ms)
- Max batch size (default: 5 atoms)
- Async future-based request handling
- Thread-safe queue with asyncio.Lock
- Automatic prompt combination and response parsing

**Files**:
- `src/mge/v2/caching/request_batcher.py` (250 LOC)
- `tests/mge/v2/caching/test_request_batcher.py` (12 tests)

**Integration**:
```python
from src.llm.enhanced_anthropic_client import EnhancedAnthropicClient

# Enable batching (default: disabled - opt-in feature)
client = EnhancedAnthropicClient(
    enable_v2_batching=True
)

# Requests within 500ms window are automatically batched
response1 = await client.request_batcher.execute_with_batching(
    atom_id=atom_id_1,
    prompt="Generate auth middleware"
)

response2 = await client.request_batcher.execute_with_batching(
    atom_id=atom_id_2,
    prompt="Generate user model"
)

# Both executed in single API call
```

### 4. Prometheus Metrics

**Purpose**: Monitor cache performance and cost savings

**Metrics**:
- `v2_cache_hits_total{cache_layer}` - Total cache hits
- `v2_cache_misses_total{cache_layer}` - Total cache misses
- `v2_cache_writes_total{cache_layer}` - Total cache writes
- `v2_cache_invalidations_total{cache_layer}` - Cache invalidations
- `v2_cache_errors_total{cache_layer, operation}` - Cache errors
- `v2_cache_cost_savings_usd_total{cache_layer}` - Cost saved (USD)
- `v2_batch_size` - Distribution of batch sizes
- `v2_batch_requests_processed_total` - Total batched requests

**Files**:
- `src/mge/v2/caching/metrics.py` (180 LOC)

**API Endpoints**:
```bash
# Get combined statistics for all cache layers
GET /metrics/cache/statistics

# Response:
{
  "llm_cache": {
    "cache_layer": "llm",
    "hit_rate": 0.65,
    "total_hits": 650,
    "total_misses": 350,
    "total_writes": 350,
    "total_invalidations": 12,
    "total_errors": 0
  },
  "rag_cache": { ... },
  "rag_similarity_cache": { ... },
  "combined_hit_rate": 0.62
}

# Get statistics for specific layer
GET /metrics/cache/statistics/llm
GET /metrics/cache/statistics/rag
GET /metrics/cache/statistics/rag_similarity
```

## Usage Examples

### Example 1: LLM Caching Workflow

```python
from src.llm.enhanced_anthropic_client import EnhancedAnthropicClient

client = EnhancedAnthropicClient(enable_v2_caching=True)

# First call - cache MISS (calls API)
response1 = await client.generate_with_caching(
    task_type="task_execution",
    complexity="medium",
    cacheable_context={"system_prompt": TASK_SYSTEM_PROMPT},
    variable_prompt="Create User model with email, password fields"
)
# cached: False, cost_usd: 0.032

# Second call with SAME prompt - cache HIT (no API call)
response2 = await client.generate_with_caching(
    task_type="task_execution",
    complexity="medium",
    cacheable_context={"system_prompt": TASK_SYSTEM_PROMPT},
    variable_prompt="Create User model with email, password fields"
)
# cached: True, cost_usd: 0, savings: $0.032 (100%)
```

### Example 2: RAG Caching with Similarity Matching

```python
from src.rag.retriever import Retriever

retriever = Retriever(vector_store, enable_v2_caching=True)

# First query - cache MISS (queries vector store)
results1 = retriever.retrieve(
    query="find authentication implementation",
    top_k=5
)

# Similar query - cache HIT via similarity matching (≥0.95)
results2 = retriever.retrieve(
    query="locate auth code examples",  # Similar to previous
    top_k=5
)
# Returns cached results without vector store query
```

### Example 3: Request Batching

```python
from src.llm.enhanced_anthropic_client import EnhancedAnthropicClient
import asyncio

client = EnhancedAnthropicClient(enable_v2_batching=True)

# Submit 3 requests within 500ms
tasks = [
    client.request_batcher.execute_with_batching(atom_id_1, "prompt 1"),
    client.request_batcher.execute_with_batching(atom_id_2, "prompt 2"),
    client.request_batcher.execute_with_batching(atom_id_3, "prompt 3"),
]

results = await asyncio.gather(*tasks)

# All 3 executed in single API call
# Overhead: 1 HTTP request instead of 3
# Time: ~2.5s instead of ~7.5s (40% reduction)
```

### Example 4: Cache Invalidation

```python
from src.mge.v2.caching import LLMPromptCache

cache = LLMPromptCache()

# Invalidate all cache entries for a masterplan
# (e.g., when masterplan structure changes)
invalidated_count = await cache.invalidate_masterplan(masterplan_id)
print(f"Invalidated {invalidated_count} cache entries")
```

## Metrics & Monitoring

### Accessing Metrics

**1. Prometheus Endpoint**:
```bash
# Scrape all metrics
curl http://localhost:8000/metrics

# Sample output:
# v2_cache_hits_total{cache_layer="llm"} 650
# v2_cache_misses_total{cache_layer="llm"} 350
# v2_cache_cost_savings_usd_total{cache_layer="llm"} 12.45
```

**2. Cache Statistics API**:
```bash
# Get combined statistics
curl http://localhost:8000/metrics/cache/statistics | jq

# Get layer-specific statistics
curl http://localhost:8000/metrics/cache/statistics/llm | jq
```

**3. Programmatic Access**:
```python
from src.mge.v2.caching.metrics import calculate_hit_rate, get_cache_statistics

# Calculate hit rate
llm_hit_rate = calculate_hit_rate("llm")
rag_hit_rate = calculate_hit_rate("rag")

# Get comprehensive statistics
stats = get_cache_statistics("llm")
# {
#   'hit_rate': 0.65,
#   'total_hits': 650,
#   'total_misses': 350,
#   'total_writes': 350,
#   'total_invalidations': 12,
#   'total_errors': 0
# }
```

### Grafana Dashboards

**Sample Queries**:
```promql
# Overall cache hit rate
sum(rate(v2_cache_hits_total[5m])) /
  (sum(rate(v2_cache_hits_total[5m])) + sum(rate(v2_cache_misses_total[5m])))

# Cost savings per hour
sum(rate(v2_cache_cost_savings_usd_total[1h]))

# Average batch size
histogram_quantile(0.5, rate(v2_batch_size_bucket[5m]))

# Cache error rate
sum(rate(v2_cache_errors_total[5m])) by (cache_layer, operation)
```

## Performance Targets

### Gap 10 Success Criteria

| Metric | Target | Validation |
|--------|--------|------------|
| Combined Hit Rate | ≥60% | Prometheus metrics |
| Cost Reduction | ≥30% | Cost savings metric |
| Execution Time Reduction | ≥40% | Masterplan execution time |

### Expected Performance

**LLM Cache**:
- Hit rate: 60-70% (for repeated tasks)
- Latency reduction: <5ms vs 2-3s API call
- Cost savings: 100% on cache hits

**RAG Cache**:
- Hit rate: 40-50% (exact + similarity)
- Exact match lookup: <5ms
- Similarity search: ~50ms (O(N) but only on miss)

**Request Batcher**:
- Batch size: 2-5 atoms (average: 3)
- Overhead reduction: 60-80% (1 call vs 3-5 calls)
- Time savings: 30-50% (amortized latency)

## Configuration

### Environment Variables

```bash
# Redis connection for caching
REDIS_URL=redis://localhost:6379

# Enable/disable caching per layer
MGE_V2_LLM_CACHE_ENABLED=true
MGE_V2_RAG_CACHE_ENABLED=true
MGE_V2_BATCHING_ENABLED=false  # Opt-in

# Cache TTLs (seconds)
MGE_V2_LLM_CACHE_TTL=86400  # 24 hours
MGE_V2_RAG_CACHE_TTL=3600   # 1 hour

# Batching configuration
MGE_V2_BATCH_WINDOW_MS=500  # Batch window in milliseconds
MGE_V2_MAX_BATCH_SIZE=5     # Maximum atoms per batch
```

### Code Configuration

**EnhancedAnthropicClient**:
```python
from src.llm.enhanced_anthropic_client import EnhancedAnthropicClient

client = EnhancedAnthropicClient(
    enable_v2_caching=True,      # Enable LLM cache
    enable_v2_batching=False,    # Disable batching (default)
    redis_url="redis://localhost:6379"
)
```

**Retriever**:
```python
from src.rag.retriever import Retriever

retriever = Retriever(
    vector_store=vector_store,
    enable_v2_caching=True,
    redis_url="redis://localhost:6379"
)
```

## Testing

### Unit Tests

```bash
# Run all caching unit tests
python -m pytest tests/mge/v2/caching/ -v

# Results:
# test_llm_prompt_cache.py::*     21 PASSED
# test_rag_query_cache.py::*      19 PASSED
# test_request_batcher.py::*      12 PASSED
# test_integration.py::*           6 PASSED
# Total: 58 tests, 100% passing
```

### Integration Tests

```bash
# Run integration tests
python -m pytest tests/mge/v2/caching/test_integration.py -v

# Covers:
# - LLM cache integration with EnhancedAnthropicClient
# - RAG cache integration with Retriever
# - Cache invalidation workflows
# - Cost savings metric emission
```

## Troubleshooting

### Common Issues

**1. Cache not working (0% hit rate)**:
```bash
# Check Redis connection
redis-cli ping
# Expected: PONG

# Check cache metrics
curl http://localhost:8000/metrics/cache/statistics | jq '.llm_cache.total_hits'

# Verify V2 caching is enabled
# Look for log message: "MGE V2 LLM response caching enabled"
```

**2. High error rate**:
```bash
# Check error metrics
curl http://localhost:8000/metrics/cache/statistics | jq '.llm_cache.total_errors'

# Check Redis logs
docker logs devmatrix-redis --tail 50

# Common fixes:
# - Increase Redis memory limit
# - Check network connectivity
# - Verify Redis isn't evicting keys too aggressively
```

**3. Low hit rate (<40%)**:
- Check if prompts are truly identical (SHA256 hash matching is exact)
- Consider adjusting similarity threshold for RAG (default: 0.95)
- Review cache TTL settings (may be too short)
- Check if masterplan invalidation is clearing cache prematurely

## Future Enhancements

### Planned (Post-Gap 10)
- [ ] Distributed caching with Redis Cluster
- [ ] Cache warming strategies (pre-populate high-value queries)
- [ ] Adaptive TTL based on content volatility
- [ ] Cross-masterplan cache sharing (careful invalidation)
- [ ] Cache compression for large responses
- [ ] Tiered caching (memory + Redis)

### Under Consideration
- [ ] LRU eviction policy tuning
- [ ] Cache analytics dashboard
- [ ] A/B testing framework for cache strategies
- [ ] Multi-region cache replication

---

**Authors**: MGE V2 Team
**Last Updated**: 2025-10-24
**Version**: 1.0.0
**Status**: Production-ready (Gap 10 complete)
