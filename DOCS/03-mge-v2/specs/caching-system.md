# Caching System - Gap 10

**Gap ID:** Gap-10
**Priority:** 🟡 HIGH (Cost & Performance Impact)
**Effort:** 1 week
**Owner:** Eng1
**Target:** ≥60% cache hit rate

---

## Problem Statement

Without caching:
- LLM requests cost $0.15-0.30 per 1K tokens output
- RAG queries repeat expensive embedding calculations
- Similar code generation requests processed independently
- Project costs exceed $200 target

**Impact:**
- High cost per project
- Slow response times (no reuse)
- Wasted compute resources

---

## Solution Architecture

```
Request
  ↓
CacheManager
  ├─ LLMCache (Redis) - Prompt hash → Response
  ├─ RAGCache (Redis) - Query embedding → Results
  └─ BatchingQueue - Group similar requests
  ↓
Cache Hit (60%+) → Instant Response
Cache Miss (40%-) → LLM/RAG → Store → Response
```

---

## Components

### 1. LLM Cache

**Key:** `SHA256(prompt + model + temperature + system_prompt)`
**TTL:** 7 days
**Storage:** Redis

```python
# src/services/llm_cache.py

class LLMCache:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def get(self, prompt: str, model: str, temp: float) -> Optional[str]:
        key = self._generate_key(prompt, model, temp)
        cached = await self.redis.get(key)
        return json.loads(cached) if cached else None

    async def set(self, prompt: str, model: str, temp: float, response: str):
        key = self._generate_key(prompt, model, temp)
        await self.redis.setex(key, 604800, json.dumps(response))  # 7 days
```

### 2. RAG Cache

**Key:** `SHA256(query_embedding + top_k + filters)`
**TTL:** 24 hours
**Storage:** Redis

```python
# src/services/rag_cache.py

class RAGCache:
    async def get_cached_results(self, query_embedding: List[float]) -> Optional[List]:
        key = self._hash_embedding(query_embedding)
        return await self.redis.get(f"rag:{key}")
```

### 3. Request Batching

**Strategy:** Collect similar requests for 100ms → Single LLM call

```python
# src/services/request_batcher.py

class RequestBatcher:
    async def batch_requests(self, requests: List[Request]) -> List[Response]:
        # Group by similarity (embedding distance < 0.1)
        groups = self._cluster_similar(requests)

        # Single LLM call per group
        responses = []
        for group in groups:
            combined_prompt = self._combine_prompts(group)
            response = await llm_client.generate(combined_prompt)
            responses.extend(self._split_response(response, group))

        return responses
```

---

## Implementation Plan

### Week 1: Redis Setup & LLM Cache
- Day 1: Redis deployment (Docker Compose)
- Day 2-3: LLMCache implementation + tests
- Day 4: Integration with EnhancedAnthropicClient
- Day 5: Metrics collection

### Week 2: RAG Cache & Batching
- Day 1-2: RAGCache implementation
- Day 3: Request batching logic
- Day 4-5: Load testing, tuning TTLs

---

## Success Metrics

- **Hit Rate:** ≥60% for LLM cache
- **Cost Reduction:** 40-50% decrease
- **Latency:** p95 <500ms for cache hits
- **Storage:** <2GB Redis memory for 1000 projects

---

**Status:** Ready for Implementation
