# Gap 10: Cacheo & Reuso

**Status**: 🔴 P0 CRITICAL - 0% implementado
**Effort**: 5-6 días
**Owner**: Eng1
**Dependencies**: Redis (ya disponible en stack)

---

## Executive Summary

**Problema**: Sin caching, cada LLM call y RAG query es expensive + slow:
- Mismo prompt ejecutado múltiples veces → redundant cost
- Mismas RAG queries → redundant embeddings computation
- No request batching → overhead alto

**Solución**: Multi-layer caching strategy:
- **L1: LLM Cache** (prompt hash → response) en Redis
- **L2: RAG Cache** (query embeddings → results) en Redis
- **L3: Request Batching** para reducir overhead
- Target: ≥60% combined hit rate

**Impacto**:
- ⚡ 40-60% reduction en execution time
- 💰 30-50% reduction en cost
- 📉 <1.5h target execution time alcanzable

---

## Requirements

### Functional Requirements

**FR1: LLM Prompt Cache**
- Cache key: SHA256(prompt + model + temperature)
- Cache hit → return cached response (no LLM call)
- Cache miss → call LLM + store in cache
- TTL: 24 hours (configurable)
- Invalidation: manual per masterplan

**FR2: RAG Query Cache**
- Cache key: SHA256(query + embedding_model + top_k)
- Cache embeddings + retrieved documents
- TTL: 1 hour (shorter due to code changes)
- Similarity threshold for partial hits: 0.95 cosine similarity

**FR3: Request Batching**
- Batch multiple atoms' prompts into single LLM call
- Max batch size: 5 atoms
- Batch window: 500ms (wait for more requests)
- Parse batched response back to individual atoms

**FR4: Cache Analytics**
- Track hit rate per cache layer
- Emit Prometheus metrics
- Report savings (time + cost)

### Non-Functional Requirements

**NFR1: Performance**
- Cache lookup latency: <5ms (Redis local)
- Cache write latency: <10ms
- Combined hit rate: ≥60% target

**NFR2: Reliability**
- Redis unavailable → fallback to no cache (continue execution)
- Cache corruption → invalidate + regenerate
- Cache warming for common patterns

---

## Architecture

### Component Diagram

```
┌────────────────────────────────────────────────────────┐
│                  Caching & Reuso System                │
├────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────┐                                  │
│  │ LLM Client       │                                  │
│  │ (with caching)   │                                  │
│  └──────────────────┘                                  │
│           │                                             │
│           ▼                                             │
│  ┌──────────────────┐      ┌────────────────────────┐ │
│  │ LLMPromptCache   │─────▶│ Redis                  │ │
│  │ (L1)             │      │ (key-value store)      │ │
│  └──────────────────┘      └────────────────────────┘ │
│           │                          ▲                  │
│           │ miss                     │ hit              │
│           ▼                          │                  │
│  ┌──────────────────┐               │                  │
│  │ OpenAI API       │───────────────┘                  │
│  └──────────────────┘                                  │
│                                                          │
│  ┌──────────────────┐      ┌────────────────────────┐ │
│  │ RAG Engine       │─────▶│ Redis                  │ │
│  │ (with caching)   │      │ (embeddings + docs)    │ │
│  └──────────────────┘      └────────────────────────┘ │
│           │                          ▲                  │
│           │ miss                     │ hit              │
│           ▼                          │                  │
│  ┌──────────────────┐               │                  │
│  │ Vector DB Query  │───────────────┘                  │
│  └──────────────────┘                                  │
│                                                          │
│  ┌──────────────────┐                                  │
│  │ RequestBatcher   │                                  │
│  │ (batch atoms)    │                                  │
│  └──────────────────┘                                  │
│                                                          │
└────────────────────────────────────────────────────────┘
```

---

## Implementation

### Phase 1: LLM Prompt Cache (Days 1-2)

**src/mge/v2/caching/llm_prompt_cache.py**

```python
"""
LLM prompt caching with Redis backend
"""
import hashlib
import json
from typing import Optional
import redis.asyncio as redis
from dataclasses import dataclass

@dataclass
class CachedLLMResponse:
    """Cached LLM response"""
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cached_at: float

class LLMPromptCache:
    """
    Cache LLM responses by prompt hash

    Cache key format: llm:{hash}
    where hash = SHA256(prompt + model + temperature)
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client = redis.from_url(redis_url, decode_responses=False)
        self.default_ttl = 86400  # 24 hours
        self.prefix = "llm_cache:"

    def _generate_cache_key(self, prompt: str, model: str, temperature: float) -> str:
        """
        Generate cache key from prompt + params

        Args:
            prompt: LLM prompt text
            model: Model name (gpt-4, etc.)
            temperature: Temperature parameter

        Returns:
            SHA256 hash as hex string
        """
        content = f"{prompt}|{model}|{temperature}"
        hash_obj = hashlib.sha256(content.encode('utf-8'))
        return f"{self.prefix}{hash_obj.hexdigest()}"

    async def get(self, prompt: str, model: str, temperature: float) -> Optional[CachedLLMResponse]:
        """
        Get cached response if available

        Returns:
            CachedLLMResponse or None if cache miss
        """
        cache_key = self._generate_cache_key(prompt, model, temperature)

        try:
            cached_data = await self.redis_client.get(cache_key)

            if cached_data:
                data = json.loads(cached_data)

                # Emit cache hit metric
                CACHE_HIT_RATE.labels(cache_layer='llm').inc()

                logger.info(f"LLM cache HIT: {cache_key[:16]}...")

                return CachedLLMResponse(
                    text=data['text'],
                    model=data['model'],
                    prompt_tokens=data['prompt_tokens'],
                    completion_tokens=data['completion_tokens'],
                    cached_at=data['cached_at']
                )

            # Cache miss
            CACHE_MISS_RATE.labels(cache_layer='llm').inc()
            logger.debug(f"LLM cache MISS: {cache_key[:16]}...")

            return None

        except redis.RedisError as e:
            logger.error(f"Redis error on cache get: {e}")
            CACHE_ERRORS.labels(cache_layer='llm', operation='get').inc()
            return None

    async def set(
        self,
        prompt: str,
        model: str,
        temperature: float,
        response_text: str,
        prompt_tokens: int,
        completion_tokens: int,
        ttl: Optional[int] = None
    ):
        """
        Store LLM response in cache

        Args:
            prompt: LLM prompt
            model: Model name
            temperature: Temperature parameter
            response_text: LLM response text
            prompt_tokens: Input tokens used
            completion_tokens: Output tokens used
            ttl: Time-to-live in seconds (default: 24h)
        """
        cache_key = self._generate_cache_key(prompt, model, temperature)

        cached_response = {
            'text': response_text,
            'model': model,
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'cached_at': time.time()
        }

        try:
            await self.redis_client.setex(
                cache_key,
                ttl or self.default_ttl,
                json.dumps(cached_response)
            )

            CACHE_WRITES.labels(cache_layer='llm').inc()

            logger.debug(f"LLM cache SET: {cache_key[:16]}... (TTL={ttl or self.default_ttl}s)")

        except redis.RedisError as e:
            logger.error(f"Redis error on cache set: {e}")
            CACHE_ERRORS.labels(cache_layer='llm', operation='set').inc()

    async def invalidate_masterplan(self, masterplan_id: str):
        """
        Invalidate all cache entries for a masterplan

        Use pattern matching: llm_cache:*{masterplan_id}*
        """
        pattern = f"{self.prefix}*{masterplan_id}*"

        try:
            cursor = 0
            deleted_count = 0

            while True:
                cursor, keys = await self.redis_client.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100
                )

                if keys:
                    await self.redis_client.delete(*keys)
                    deleted_count += len(keys)

                if cursor == 0:
                    break

            logger.info(f"Invalidated {deleted_count} cache entries for masterplan {masterplan_id}")

            CACHE_INVALIDATIONS.labels(cache_layer='llm').inc()

        except redis.RedisError as e:
            logger.error(f"Redis error on cache invalidation: {e}")
            CACHE_ERRORS.labels(cache_layer='llm', operation='invalidate').inc()

    async def get_hit_rate(self) -> float:
        """
        Calculate cache hit rate

        Returns:
            Hit rate as float (0.0 - 1.0)
        """
        try:
            # Query Prometheus for hit/miss counts
            hits = await prometheus_query('cache_hits_total{cache_layer="llm"}')
            misses = await prometheus_query('cache_misses_total{cache_layer="llm"}')

            total = hits + misses
            if total == 0:
                return 0.0

            return hits / total

        except Exception as e:
            logger.error(f"Failed to calculate hit rate: {e}")
            return 0.0
```

### Phase 2: RAG Query Cache (Days 3-4)

**src/mge/v2/caching/rag_query_cache.py**

```python
"""
RAG query caching with embedding similarity matching
"""
import hashlib
import json
import numpy as np
from typing import Optional, List, Dict
import redis.asyncio as redis

@dataclass
class CachedRAGResult:
    """Cached RAG query result"""
    query: str
    query_embedding: List[float]
    documents: List[Dict]
    cached_at: float

class RAGQueryCache:
    """
    Cache RAG queries with similarity-based partial hits

    For exact matches: hash(query + embedding_model + top_k)
    For partial matches: cosine similarity ≥0.95 on query embeddings
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client = redis.from_url(redis_url, decode_responses=False)
        self.default_ttl = 3600  # 1 hour (shorter than LLM cache)
        self.prefix = "rag_cache:"
        self.similarity_threshold = 0.95

    def _generate_cache_key(self, query: str, embedding_model: str, top_k: int) -> str:
        """Generate cache key from query params"""
        content = f"{query}|{embedding_model}|{top_k}"
        hash_obj = hashlib.sha256(content.encode('utf-8'))
        return f"{self.prefix}{hash_obj.hexdigest()}"

    async def get(
        self,
        query: str,
        query_embedding: List[float],
        embedding_model: str,
        top_k: int
    ) -> Optional[CachedRAGResult]:
        """
        Get cached RAG result

        First tries exact match, then similarity-based partial match
        """
        cache_key = self._generate_cache_key(query, embedding_model, top_k)

        try:
            # Try exact match
            cached_data = await self.redis_client.get(cache_key)

            if cached_data:
                data = json.loads(cached_data)

                CACHE_HIT_RATE.labels(cache_layer='rag').inc()

                logger.info(f"RAG cache HIT (exact): {cache_key[:16]}...")

                return CachedRAGResult(
                    query=data['query'],
                    query_embedding=data['query_embedding'],
                    documents=data['documents'],
                    cached_at=data['cached_at']
                )

            # Try similarity-based partial match
            similar_result = await self._find_similar_cached_query(query_embedding, top_k)

            if similar_result:
                CACHE_HIT_RATE.labels(cache_layer='rag_similarity').inc()

                logger.info(f"RAG cache HIT (similarity): {cache_key[:16]}...")

                return similar_result

            # Cache miss
            CACHE_MISS_RATE.labels(cache_layer='rag').inc()
            logger.debug(f"RAG cache MISS: {cache_key[:16]}...")

            return None

        except redis.RedisError as e:
            logger.error(f"Redis error on RAG cache get: {e}")
            CACHE_ERRORS.labels(cache_layer='rag', operation='get').inc()
            return None

    async def set(
        self,
        query: str,
        query_embedding: List[float],
        embedding_model: str,
        top_k: int,
        documents: List[Dict],
        ttl: Optional[int] = None
    ):
        """
        Store RAG query result in cache
        """
        cache_key = self._generate_cache_key(query, embedding_model, top_k)

        cached_result = {
            'query': query,
            'query_embedding': query_embedding,
            'embedding_model': embedding_model,
            'top_k': top_k,
            'documents': documents,
            'cached_at': time.time()
        }

        try:
            await self.redis_client.setex(
                cache_key,
                ttl or self.default_ttl,
                json.dumps(cached_result)
            )

            CACHE_WRITES.labels(cache_layer='rag').inc()

            logger.debug(f"RAG cache SET: {cache_key[:16]}... (TTL={ttl or self.default_ttl}s)")

        except redis.RedisError as e:
            logger.error(f"Redis error on RAG cache set: {e}")
            CACHE_ERRORS.labels(cache_layer='rag', operation='set').inc()

    async def _find_similar_cached_query(
        self,
        query_embedding: List[float],
        top_k: int
    ) -> Optional[CachedRAGResult]:
        """
        Find cached query with similar embedding (cosine similarity ≥0.95)

        This is expensive (O(N) scan) but only runs on cache miss
        """
        try:
            pattern = f"{self.prefix}*"
            cursor = 0

            query_embedding_np = np.array(query_embedding)

            while True:
                cursor, keys = await self.redis_client.scan(
                    cursor=cursor,
                    match=pattern,
                    count=50
                )

                for key in keys:
                    cached_data = await self.redis_client.get(key)
                    if not cached_data:
                        continue

                    data = json.loads(cached_data)

                    if data['top_k'] != top_k:
                        continue

                    cached_embedding_np = np.array(data['query_embedding'])

                    # Compute cosine similarity
                    similarity = np.dot(query_embedding_np, cached_embedding_np) / (
                        np.linalg.norm(query_embedding_np) * np.linalg.norm(cached_embedding_np)
                    )

                    if similarity >= self.similarity_threshold:
                        logger.info(f"Found similar cached query (similarity={similarity:.3f})")

                        return CachedRAGResult(
                            query=data['query'],
                            query_embedding=data['query_embedding'],
                            documents=data['documents'],
                            cached_at=data['cached_at']
                        )

                if cursor == 0:
                    break

            return None

        except Exception as e:
            logger.error(f"Error finding similar cached query: {e}")
            return None
```

### Phase 3: Request Batching (Days 5-6)

**src/mge/v2/caching/request_batcher.py**

```python
"""
Batch multiple atoms' prompts into single LLM call for efficiency
"""
import asyncio
from typing import List, Dict
from uuid import UUID
from dataclasses import dataclass

@dataclass
class BatchedRequest:
    """Single request in batch"""
    atom_id: UUID
    prompt: str
    future: asyncio.Future

class RequestBatcher:
    """
    Batch multiple atoms' prompts into single LLM call

    Strategy:
    1. Collect requests for 500ms (batch window)
    2. Combine prompts with separator
    3. Send single LLM call
    4. Parse response back to individual atoms
    5. Resolve each future with its response

    Benefits:
    - Reduce overhead (fewer HTTP requests)
    - Better throughput (more tokens per request)
    - Lower latency per atom (amortized)
    """

    def __init__(self, llm_client, max_batch_size: int = 5, batch_window_ms: int = 500):
        self.llm_client = llm_client
        self.max_batch_size = max_batch_size
        self.batch_window_ms = batch_window_ms / 1000  # Convert to seconds

        self._pending_requests: List[BatchedRequest] = []
        self._batch_lock = asyncio.Lock()
        self._batch_task = None

    async def execute_with_batching(self, atom_id: UUID, prompt: str) -> str:
        """
        Execute atom prompt with batching

        Returns:
            LLM response text for this atom
        """
        # Create future for this request
        future = asyncio.Future()

        batched_request = BatchedRequest(
            atom_id=atom_id,
            prompt=prompt,
            future=future
        )

        async with self._batch_lock:
            self._pending_requests.append(batched_request)

            # Start batch task if not running
            if not self._batch_task or self._batch_task.done():
                self._batch_task = asyncio.create_task(self._process_batch())

        # Wait for result
        response = await future
        return response

    async def _process_batch(self):
        """
        Wait for batch window, then process all pending requests
        """
        # Wait for batch window to collect more requests
        await asyncio.sleep(self.batch_window_ms)

        async with self._batch_lock:
            if not self._pending_requests:
                return

            # Take up to max_batch_size requests
            batch = self._pending_requests[:self.max_batch_size]
            self._pending_requests = self._pending_requests[self.max_batch_size:]

        logger.info(f"Processing batch of {len(batch)} requests")

        try:
            # Combine prompts
            combined_prompt = self._combine_prompts(batch)

            # Send single LLM call
            response = await self.llm_client.generate(
                prompt=combined_prompt,
                model="gpt-4",
                temperature=0.7
            )

            # Parse response back to individual atoms
            individual_responses = self._parse_batched_response(response.text, len(batch))

            # Resolve each future
            for batched_request, response_text in zip(batch, individual_responses):
                batched_request.future.set_result(response_text)

            # Emit metrics
            BATCH_SIZE.observe(len(batch))
            BATCH_REQUESTS_PROCESSED.inc(len(batch))

        except Exception as e:
            logger.error(f"Batch processing failed: {e}")

            # Fail all futures
            for batched_request in batch:
                batched_request.future.set_exception(e)

    def _combine_prompts(self, batch: List[BatchedRequest]) -> str:
        """
        Combine multiple prompts into single batched prompt

        Format:
        ---
        PROMPT 1:
        {prompt_1}

        PROMPT 2:
        {prompt_2}
        ---
        """
        combined = "Process the following prompts separately and return responses in the same order:\n\n"

        for idx, batched_request in enumerate(batch):
            combined += f"--- PROMPT {idx + 1} (atom: {batched_request.atom_id}) ---\n"
            combined += f"{batched_request.prompt}\n\n"

        combined += "--- END PROMPTS ---\n\n"
        combined += "Return responses in format:\n"
        combined += "RESPONSE 1:\n{response_1}\n\n"
        combined += "RESPONSE 2:\n{response_2}\n\n"
        combined += "etc."

        return combined

    def _parse_batched_response(self, response_text: str, expected_count: int) -> List[str]:
        """
        Parse batched response back to individual responses
        """
        import re

        # Split by RESPONSE markers
        pattern = r'RESPONSE (\d+):\s*(.*?)(?=RESPONSE \d+:|$)'
        matches = re.findall(pattern, response_text, re.DOTALL)

        if len(matches) != expected_count:
            logger.warning(
                f"Expected {expected_count} responses, got {len(matches)}"
            )

        # Extract response texts
        responses = [match[1].strip() for match in matches]

        # Pad with empty responses if needed
        while len(responses) < expected_count:
            responses.append("")

        return responses[:expected_count]
```

### Phase 4: Integration (Day 6)

**Modified src/mge/v2/execution/llm_client.py**

```python
from ..caching.llm_prompt_cache import LLMPromptCache
from ..caching.request_batcher import RequestBatcher

class LLMClient:
    """LLM client with caching and batching"""

    def __init__(self, api_key: str):
        self.openai_client = openai.AsyncOpenAI(api_key=api_key)

        # NEW: Caching layers
        self.prompt_cache = LLMPromptCache()
        self.request_batcher = RequestBatcher(llm_client=self)

    async def generate(
        self,
        prompt: str,
        model: str = "gpt-4",
        temperature: float = 0.7,
        use_cache: bool = True,
        use_batching: bool = False,
        atom_id: Optional[UUID] = None
    ) -> LLMResponse:
        """
        Generate LLM response with caching and optional batching
        """
        # Check cache first
        if use_cache:
            cached_response = await self.prompt_cache.get(prompt, model, temperature)

            if cached_response:
                logger.info(f"Returning cached LLM response")

                # Emit cache savings metric
                CACHE_COST_SAVINGS_USD.labels(cache_layer='llm').inc(
                    self._calculate_cost(
                        cached_response.prompt_tokens,
                        cached_response.completion_tokens
                    )
                )

                return LLMResponse(
                    text=cached_response.text,
                    model=cached_response.model,
                    usage=Usage(
                        prompt_tokens=cached_response.prompt_tokens,
                        completion_tokens=cached_response.completion_tokens
                    ),
                    cached=True
                )

        # Cache miss → call LLM (with optional batching)
        if use_batching and atom_id:
            response_text = await self.request_batcher.execute_with_batching(atom_id, prompt)

            # Estimate tokens (not exact for batched responses)
            prompt_tokens = len(prompt) // 4
            completion_tokens = len(response_text) // 4

        else:
            # Direct LLM call
            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature
            )

            response_text = response.choices[0].message.content
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens

        # Store in cache
        if use_cache:
            await self.prompt_cache.set(
                prompt=prompt,
                model=model,
                temperature=temperature,
                response_text=response_text,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens
            )

        return LLMResponse(
            text=response_text,
            model=model,
            usage=Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens
            ),
            cached=False
        )
```

---

## Prometheus Metrics

```python
# Cache hit/miss rates
CACHE_HIT_RATE = Counter(
    'v2_cache_hits_total',
    'Cache hits',
    ['cache_layer']
)

CACHE_MISS_RATE = Counter(
    'v2_cache_misses_total',
    'Cache misses',
    ['cache_layer']
)

# Cache operations
CACHE_WRITES = Counter(
    'v2_cache_writes_total',
    'Cache writes',
    ['cache_layer']
)

CACHE_INVALIDATIONS = Counter(
    'v2_cache_invalidations_total',
    'Cache invalidations',
    ['cache_layer']
)

CACHE_ERRORS = Counter(
    'v2_cache_errors_total',
    'Cache operation errors',
    ['cache_layer', 'operation']
)

# Cost savings from cache
CACHE_COST_SAVINGS_USD = Counter(
    'v2_cache_cost_savings_usd_total',
    'Cost saved by cache hits',
    ['cache_layer']
)

# Batching metrics
BATCH_SIZE = Histogram(
    'v2_batch_size',
    'Request batch sizes'
)

BATCH_REQUESTS_PROCESSED = Counter(
    'v2_batch_requests_processed_total',
    'Requests processed via batching'
)
```

---

## Testing Strategy

**Unit Tests**: 20+ tests for cache operations, similarity matching, batching logic
**Integration Tests**: 10+ tests for E2E caching flow, hit rate validation

---

## Deliverables

✅ **Code**: LLMPromptCache, RAGQueryCache, RequestBatcher, LLMClient integration
✅ **Tests**: 30+ tests
✅ **Monitoring**: 8 Prometheus metrics

---

## Definition of Done

- [ ] LLM cache with 24h TTL
- [ ] RAG cache with 1h TTL + similarity matching
- [ ] Request batching (max 5 atoms, 500ms window)
- [ ] Cache hit rate ≥60% measured via Prometheus
- [ ] Cost savings ≥30% measured via cost tracking
- [ ] Execution time reduction ≥40% measured via metrics
- [ ] 30+ tests passing
- [ ] Redis fallback working (continue without cache)
- [ ] Integration with WaveExecutor complete

---

## Success Metrics

**Target**:
- ✅ Item 10 alignment: 0% → 100%
- ✅ Combined hit rate ≥60%
- ✅ Cost reduction ≥30%
- ✅ Execution time reduction ≥40%
- ✅ <1.5h execution time achieved

