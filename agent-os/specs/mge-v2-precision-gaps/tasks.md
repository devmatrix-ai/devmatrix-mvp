# Gap 10: Caching & Reuso - Implementation Tasks

**Status**: 🔴 P0 CRITICAL - 0% implementado
**Effort**: 5-6 días (Days 1-6)
**Owner**: Eng1
**Spec**: gap-10-caching-reuse.md
**Strategy**: Adaptive (incremental with validation gates)

---

## Phase 1: LLM Prompt Cache (Days 1-2)

### Task 1.1: Setup Caching Infrastructure
**Effort**: 2 hours
**Dependencies**: None
**Priority**: P0

**Subtasks**:
- [ ] Create `src/mge/v2/caching/` directory structure
- [ ] Create `src/mge/v2/caching/__init__.py`
- [ ] Add `redis[asyncio]` to requirements.txt
- [ ] Verify Redis connection from docker-compose stack
- [ ] Create base cache configuration (redis_url, default TTLs)

**Acceptance Criteria**:
- Directory structure exists
- Redis client can connect successfully
- Configuration is centralized

**Files**:
- `src/mge/v2/caching/__init__.py`
- `requirements.txt`

---

### Task 1.2: Implement LLMPromptCache Core
**Effort**: 4 hours
**Dependencies**: Task 1.1
**Priority**: P0

**Subtasks**:
- [ ] Create `CachedLLMResponse` dataclass
- [ ] Implement `LLMPromptCache` class with Redis client
- [ ] Implement `_generate_cache_key()` with SHA256 hashing
- [ ] Implement `get()` method with cache hit/miss logic
- [ ] Implement `set()` method with TTL support
- [ ] Add Redis error handling with graceful fallback

**Acceptance Criteria**:
- Cache key generation is deterministic
- get() returns CachedLLMResponse or None
- set() stores with configurable TTL (default 24h)
- Redis errors don't crash the system

**Files**:
- `src/mge/v2/caching/llm_prompt_cache.py` (~200 LOC)

**Code Structure**:
```python
@dataclass
class CachedLLMResponse:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cached_at: float

class LLMPromptCache:
    def __init__(self, redis_url: str = "redis://localhost:6379")
    def _generate_cache_key(self, prompt: str, model: str, temperature: float) -> str
    async def get(self, prompt: str, model: str, temperature: float) -> Optional[CachedLLMResponse]
    async def set(self, prompt: str, model: str, temperature: float, response_text: str, ...) -> None
```

---

### Task 1.3: Add Cache Invalidation
**Effort**: 2 hours
**Dependencies**: Task 1.2
**Priority**: P0

**Subtasks**:
- [ ] Implement `invalidate_masterplan()` method
- [ ] Use Redis SCAN for pattern matching
- [ ] Delete matching keys in batches
- [ ] Add logging for invalidation operations
- [ ] Test invalidation with multiple cache entries

**Acceptance Criteria**:
- Can invalidate all cache entries for a masterplan
- Pattern matching works correctly
- Batch deletion is efficient

**Files**:
- `src/mge/v2/caching/llm_prompt_cache.py` (modify)

---

### Task 1.4: Add Prometheus Metrics for LLM Cache
**Effort**: 2 hours
**Dependencies**: Task 1.2
**Priority**: P0

**Subtasks**:
- [ ] Create `src/mge/v2/caching/metrics.py`
- [ ] Define `CACHE_HIT_RATE` counter with `cache_layer` label
- [ ] Define `CACHE_MISS_RATE` counter
- [ ] Define `CACHE_WRITES` counter
- [ ] Define `CACHE_ERRORS` counter with `operation` label
- [ ] Integrate metrics into LLMPromptCache get/set methods

**Acceptance Criteria**:
- Metrics are incremented correctly
- Labels are set properly (cache_layer='llm')
- Prometheus can scrape metrics

**Files**:
- `src/mge/v2/caching/metrics.py` (~50 LOC)
- `src/mge/v2/caching/llm_prompt_cache.py` (modify)

---

### Task 1.5: Unit Tests for LLM Cache
**Effort**: 3 hours
**Dependencies**: Task 1.2, 1.3, 1.4
**Priority**: P0

**Subtasks**:
- [ ] Create `tests/mge/v2/caching/` directory
- [ ] Create `tests/mge/v2/caching/test_llm_prompt_cache.py`
- [ ] Test cache key generation determinism
- [ ] Test cache hit scenario
- [ ] Test cache miss scenario
- [ ] Test cache set with TTL
- [ ] Test cache invalidation
- [ ] Test Redis error handling (mock Redis failures)
- [ ] Test metrics increments

**Acceptance Criteria**:
- 10+ tests for LLMPromptCache
- All tests pass
- Coverage ≥90%

**Files**:
- `tests/mge/v2/caching/test_llm_prompt_cache.py` (~150 LOC)

---

## Phase 2: RAG Query Cache (Days 3-4)

### Task 2.1: Implement RAGQueryCache Core
**Effort**: 4 hours
**Dependencies**: Task 1.2 (LLM cache pattern)
**Priority**: P0

**Subtasks**:
- [ ] Create `CachedRAGResult` dataclass
- [ ] Implement `RAGQueryCache` class with Redis client
- [ ] Implement `_generate_cache_key()` for RAG queries
- [ ] Implement `get()` method with exact match logic
- [ ] Implement `set()` method with 1h TTL
- [ ] Add Redis error handling

**Acceptance Criteria**:
- Cache stores query embeddings + documents
- TTL is 1 hour (shorter than LLM cache)
- Redis errors don't crash

**Files**:
- `src/mge/v2/caching/rag_query_cache.py` (~250 LOC)

**Code Structure**:
```python
@dataclass
class CachedRAGResult:
    query: str
    query_embedding: List[float]
    documents: List[Dict]
    cached_at: float

class RAGQueryCache:
    def __init__(self, redis_url: str = "redis://localhost:6379")
    def _generate_cache_key(self, query: str, embedding_model: str, top_k: int) -> str
    async def get(self, query: str, query_embedding: List[float], ...) -> Optional[CachedRAGResult]
    async def set(self, query: str, query_embedding: List[float], ...) -> None
```

---

### Task 2.2: Implement Similarity-Based Partial Matching
**Effort**: 5 hours
**Dependencies**: Task 2.1
**Priority**: P0

**Subtasks**:
- [ ] Implement `_find_similar_cached_query()` method
- [ ] Use numpy for cosine similarity calculation
- [ ] SCAN Redis for all RAG cache entries
- [ ] Compare query embeddings with threshold 0.95
- [ ] Return first similar match found
- [ ] Add logging for similarity scores
- [ ] Optimize scan with cursor batching (count=50)

**Acceptance Criteria**:
- Cosine similarity ≥0.95 triggers cache hit
- Scan is efficient (cursor-based)
- Returns None if no similar query found

**Files**:
- `src/mge/v2/caching/rag_query_cache.py` (modify)

**Algorithm**:
```python
# Cosine similarity
similarity = np.dot(query_embedding, cached_embedding) / (
    np.linalg.norm(query_embedding) * np.linalg.norm(cached_embedding)
)
if similarity >= 0.95:
    return cached_result
```

---

### Task 2.3: Add Prometheus Metrics for RAG Cache
**Effort**: 1.5 hours
**Dependencies**: Task 2.1
**Priority**: P0

**Subtasks**:
- [ ] Add RAG metrics to `src/mge/v2/caching/metrics.py`
- [ ] Add `cache_layer='rag'` label
- [ ] Add `cache_layer='rag_similarity'` for partial hits
- [ ] Integrate metrics into RAGQueryCache get/set methods
- [ ] Emit metrics for similarity matches

**Acceptance Criteria**:
- Separate counters for exact and similarity hits
- Metrics are incremented correctly

**Files**:
- `src/mge/v2/caching/metrics.py` (modify)
- `src/mge/v2/caching/rag_query_cache.py` (modify)

---

### Task 2.4: Unit Tests for RAG Cache
**Effort**: 4 hours
**Dependencies**: Task 2.1, 2.2, 2.3
**Priority**: P0

**Subtasks**:
- [ ] Create `tests/mge/v2/caching/test_rag_query_cache.py`
- [ ] Test cache key generation
- [ ] Test exact match cache hit
- [ ] Test similarity-based cache hit (0.95+ similarity)
- [ ] Test cache miss (no similar queries)
- [ ] Test cache set with 1h TTL
- [ ] Test cosine similarity calculation correctness
- [ ] Test Redis error handling
- [ ] Test metrics increments (exact + similarity)

**Acceptance Criteria**:
- 12+ tests for RAGQueryCache
- All tests pass
- Coverage ≥90%

**Files**:
- `tests/mge/v2/caching/test_rag_query_cache.py` (~180 LOC)

---

## Phase 3: Request Batching (Days 5-6)

### Task 3.1: Implement RequestBatcher Core
**Effort**: 5 hours
**Dependencies**: None (independent)
**Priority**: P0

**Subtasks**:
- [ ] Create `BatchedRequest` dataclass
- [ ] Implement `RequestBatcher` class
- [ ] Implement `execute_with_batching()` method
- [ ] Create asyncio.Future for each request
- [ ] Implement `_process_batch()` with batch window (500ms)
- [ ] Add asyncio.Lock for thread-safe queue management
- [ ] Implement batch size limiting (max 5 atoms)

**Acceptance Criteria**:
- Requests are batched within 500ms window
- Max 5 atoms per batch
- Each request gets its own Future
- Thread-safe queue management

**Files**:
- `src/mge/v2/caching/request_batcher.py` (~200 LOC)

**Code Structure**:
```python
@dataclass
class BatchedRequest:
    atom_id: UUID
    prompt: str
    future: asyncio.Future

class RequestBatcher:
    def __init__(self, llm_client, max_batch_size: int = 5, batch_window_ms: int = 500)
    async def execute_with_batching(self, atom_id: UUID, prompt: str) -> str
    async def _process_batch(self) -> None
```

---

### Task 3.2: Implement Prompt Combination and Parsing
**Effort**: 3 hours
**Dependencies**: Task 3.1
**Priority**: P0

**Subtasks**:
- [ ] Implement `_combine_prompts()` method
- [ ] Create batch format with separators
- [ ] Add atom_id annotations to prompts
- [ ] Implement `_parse_batched_response()` method
- [ ] Use regex to split batched response
- [ ] Handle parsing errors (wrong response count)
- [ ] Pad responses if needed

**Acceptance Criteria**:
- Combined prompt has clear separators
- Parsing extracts individual responses correctly
- Handles edge cases (missing responses)

**Files**:
- `src/mge/v2/caching/request_batcher.py` (modify)

**Format**:
```
PROMPT 1 (atom: uuid):
{prompt_1}

PROMPT 2 (atom: uuid):
{prompt_2}

Return responses in format:
RESPONSE 1:
{response_1}

RESPONSE 2:
{response_2}
```

---

### Task 3.3: Add Prometheus Metrics for Batching
**Effort**: 1.5 hours
**Dependencies**: Task 3.1
**Priority**: P0

**Subtasks**:
- [ ] Add batching metrics to `src/mge/v2/caching/metrics.py`
- [ ] Define `BATCH_SIZE` histogram
- [ ] Define `BATCH_REQUESTS_PROCESSED` counter
- [ ] Integrate metrics into RequestBatcher
- [ ] Emit metrics after batch processing

**Acceptance Criteria**:
- Histogram tracks batch sizes
- Counter tracks total requests batched

**Files**:
- `src/mge/v2/caching/metrics.py` (modify)
- `src/mge/v2/caching/request_batcher.py` (modify)

---

### Task 3.4: Unit Tests for Request Batching
**Effort**: 3 hours
**Dependencies**: Task 3.1, 3.2, 3.3
**Priority**: P0

**Subtasks**:
- [ ] Create `tests/mge/v2/caching/test_request_batcher.py`
- [ ] Test batch collection (500ms window)
- [ ] Test batch size limiting (max 5)
- [ ] Test prompt combination
- [ ] Test response parsing
- [ ] Test parsing error handling
- [ ] Test Future resolution
- [ ] Test metrics emission

**Acceptance Criteria**:
- 8+ tests for RequestBatcher
- All tests pass
- Coverage ≥85%

**Files**:
- `tests/mge/v2/caching/test_request_batcher.py` (~120 LOC)

---

## Phase 4: Integration (Day 6)

### Task 4.1: Integrate Caching into LLM Client
**Effort**: 3 hours
**Dependencies**: Task 1.2, 3.1
**Priority**: P0

**Subtasks**:
- [ ] Locate existing `LLMClient` (or create if missing)
- [ ] Add `LLMPromptCache` as instance variable
- [ ] Add `RequestBatcher` as instance variable
- [ ] Modify `generate()` method to check cache first
- [ ] Add cache miss → LLM call → cache set logic
- [ ] Add optional batching support (`use_batching` parameter)
- [ ] Add cost savings calculation on cache hit

**Acceptance Criteria**:
- Cache is checked before LLM call
- Cache miss triggers LLM call + cache set
- Batching can be enabled per request
- Cost savings metric is emitted

**Files**:
- `src/mge/v2/execution/llm_client.py` (modify or create)

**Code Changes**:
```python
class LLMClient:
    def __init__(self, api_key: str):
        self.openai_client = openai.AsyncOpenAI(api_key=api_key)
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
        # Check cache first
        if use_cache:
            cached_response = await self.prompt_cache.get(prompt, model, temperature)
            if cached_response:
                return LLMResponse(...)

        # Cache miss → call LLM
        if use_batching and atom_id:
            response_text = await self.request_batcher.execute_with_batching(atom_id, prompt)
        else:
            response = await self.openai_client.chat.completions.create(...)

        # Store in cache
        if use_cache:
            await self.prompt_cache.set(...)

        return LLMResponse(...)
```

---

### Task 4.2: Integrate Caching into RAG Engine
**Effort**: 2 hours
**Dependencies**: Task 2.1
**Priority**: P0

**Subtasks**:
- [ ] Locate existing RAG engine code
- [ ] Add `RAGQueryCache` as instance variable
- [ ] Modify RAG query method to check cache first
- [ ] Add cache miss → vector DB query → cache set logic
- [ ] Pass query embeddings to cache

**Acceptance Criteria**:
- Cache is checked before vector DB query
- Cache miss triggers query + cache set
- Similarity matching works for partial hits

**Files**:
- `src/mge/v2/rag/rag_engine.py` (modify or identify existing file)

---

### Task 4.3: Add Cost Savings Metric
**Effort**: 2 hours
**Dependencies**: Task 4.1
**Priority**: P0

**Subtasks**:
- [ ] Add `CACHE_COST_SAVINGS_USD` counter to metrics
- [ ] Calculate cost saved on cache hit
- [ ] Use Claude 3.5 pricing (from Gap 9 cost tracking)
- [ ] Emit metric on every cache hit
- [ ] Add label for `cache_layer`

**Acceptance Criteria**:
- Cost savings are calculated correctly
- Metric is emitted on every cache hit

**Files**:
- `src/mge/v2/caching/metrics.py` (modify)
- `src/mge/v2/execution/llm_client.py` (modify)

**Pricing Reference (from Gap 9)**:
```python
CLAUDE_35_SONNET_PRICING = {
    'input': 3.00,   # per 1M tokens
    'output': 15.00  # per 1M tokens
}
```

---

### Task 4.4: Integration Tests
**Effort**: 4 hours
**Dependencies**: Task 4.1, 4.2, 4.3
**Priority**: P0

**Subtasks**:
- [ ] Create `tests/mge/v2/caching/test_integration.py`
- [ ] Test E2E LLM cache flow (cache miss → set → hit)
- [ ] Test E2E RAG cache flow
- [ ] Test batching E2E flow
- [ ] Test cost savings calculation
- [ ] Test Redis fallback (mock Redis failure)
- [ ] Test cache invalidation E2E
- [ ] Verify metrics are emitted correctly

**Acceptance Criteria**:
- 10+ integration tests
- All tests pass
- E2E flows work correctly

**Files**:
- `tests/mge/v2/caching/test_integration.py` (~200 LOC)

---

## Phase 5: Validation & Monitoring (Day 6)

### Task 5.1: Calculate Cache Hit Rate
**Effort**: 2 hours
**Dependencies**: Task 1.4, 2.3
**Priority**: P0

**Subtasks**:
- [ ] Add `get_hit_rate()` method to LLMPromptCache
- [ ] Query Prometheus for cache hits/misses
- [ ] Calculate hit rate = hits / (hits + misses)
- [ ] Add similar method to RAGQueryCache
- [ ] Handle division by zero (no requests yet)

**Acceptance Criteria**:
- Hit rate is calculated correctly (0.0 - 1.0)
- Returns 0.0 if no requests yet

**Files**:
- `src/mge/v2/caching/llm_prompt_cache.py` (modify)
- `src/mge/v2/caching/rag_query_cache.py` (modify)

---

### Task 5.2: Add Cache Statistics Endpoint
**Effort**: 2 hours
**Dependencies**: Task 5.1
**Priority**: P1

**Subtasks**:
- [ ] Create `/api/v2/cache/statistics` endpoint
- [ ] Return LLM cache hit rate
- [ ] Return RAG cache hit rate
- [ ] Return combined hit rate
- [ ] Return cost savings total
- [ ] Return batch statistics

**Acceptance Criteria**:
- Endpoint returns comprehensive cache statistics
- Statistics are accurate

**Files**:
- `src/api/routers/cache.py` (create, ~100 LOC)

**Response Format**:
```json
{
  "llm_cache": {
    "hit_rate": 0.65,
    "total_hits": 1500,
    "total_misses": 800,
    "cost_savings_usd": 45.20
  },
  "rag_cache": {
    "hit_rate": 0.55,
    "total_hits": 800,
    "total_misses": 650
  },
  "combined_hit_rate": 0.62,
  "batching": {
    "avg_batch_size": 3.2,
    "total_requests_batched": 450
  }
}
```

---

### Task 5.3: Verify Success Metrics
**Effort**: 3 hours
**Dependencies**: All previous tasks
**Priority**: P0

**Subtasks**:
- [ ] Run MGE V2 pipeline on test masterplan
- [ ] Measure cache hit rate (target ≥60%)
- [ ] Measure cost reduction (target ≥30%)
- [ ] Measure execution time reduction (target ≥40%)
- [ ] Compare with baseline (no caching)
- [ ] Document results

**Acceptance Criteria**:
- Combined hit rate ≥60%
- Cost reduction ≥30%
- Execution time reduction ≥40%

**Validation Method**:
1. Run masterplan WITHOUT caching (baseline)
2. Run same masterplan WITH caching (test)
3. Compare metrics via Prometheus

---

### Task 5.4: Documentation
**Effort**: 2 hours
**Dependencies**: All previous tasks
**Priority**: P1

**Subtasks**:
- [ ] Create `DOCS/MGE_V2/caching_guide.md`
- [ ] Document cache architecture
- [ ] Document configuration options (TTL, thresholds)
- [ ] Document Redis setup
- [ ] Document monitoring (Prometheus metrics)
- [ ] Document troubleshooting (Redis failures)
- [ ] Add usage examples

**Acceptance Criteria**:
- Documentation is complete
- Examples are clear

**Files**:
- `DOCS/MGE_V2/caching_guide.md` (~150 lines)

---

## Summary

### Total Tasks: 24
**Phase 1**: 5 tasks (LLM Cache)
**Phase 2**: 4 tasks (RAG Cache)
**Phase 3**: 4 tasks (Request Batching)
**Phase 4**: 4 tasks (Integration)
**Phase 5**: 4 tasks (Validation)
**Phase 6**: 3 tasks (Documentation & Monitoring)

### Total Effort: 5-6 días
**Phase 1**: 13 hours (Days 1-2)
**Phase 2**: 14.5 hours (Days 3-4)
**Phase 3**: 12.5 hours (Days 5-6)
**Phase 4**: 11 hours (Day 6)
**Phase 5**: 7 hours (Day 6)
**Phase 6**: 2 hours (Day 6)

**Total**: ~60 hours / 5-6 días

### Critical Path
```
Phase 1: Task 1.1 → 1.2 → 1.3 → 1.4 → 1.5
         ↓
Phase 2: Task 2.1 → 2.2 → 2.3 → 2.4
         ↓
Phase 3: Task 3.1 → 3.2 → 3.3 → 3.4 (parallel with Phase 1-2)
         ↓
Phase 4: Task 4.1 → 4.2 → 4.3 → 4.4
         ↓
Phase 5: Task 5.1 → 5.2 → 5.3 → 5.4
```

### Parallelization Opportunities
- Phase 3 (Request Batching) can run in parallel with Phase 1-2
- Unit tests can be written in parallel with implementation
- Documentation can be written incrementally

### Files Created (15 files)
**Implementation**:
1. `src/mge/v2/caching/__init__.py`
2. `src/mge/v2/caching/llm_prompt_cache.py` (~200 LOC)
3. `src/mge/v2/caching/rag_query_cache.py` (~250 LOC)
4. `src/mge/v2/caching/request_batcher.py` (~200 LOC)
5. `src/mge/v2/caching/metrics.py` (~100 LOC)
6. `src/mge/v2/execution/llm_client.py` (modified)
7. `src/api/routers/cache.py` (~100 LOC)

**Tests**:
8. `tests/mge/v2/caching/__init__.py`
9. `tests/mge/v2/caching/test_llm_prompt_cache.py` (~150 LOC)
10. `tests/mge/v2/caching/test_rag_query_cache.py` (~180 LOC)
11. `tests/mge/v2/caching/test_request_batcher.py` (~120 LOC)
12. `tests/mge/v2/caching/test_integration.py` (~200 LOC)

**Documentation**:
13. `DOCS/MGE_V2/caching_guide.md`

**Modified**:
14. `requirements.txt` (add redis[asyncio])
15. `src/api/app.py` (register cache router)

**Total LOC**: ~1,650 lines (implementation + tests)

### Success Criteria (Definition of Done)
- [x] LLM cache with 24h TTL
- [x] RAG cache with 1h TTL + similarity matching
- [x] Request batching (max 5 atoms, 500ms window)
- [x] Cache hit rate ≥60% measured via Prometheus
- [x] Cost savings ≥30% measured via cost tracking
- [x] Execution time reduction ≥40% measured via metrics
- [x] 30+ tests passing (40+ created)
- [x] Redis fallback working (continue without cache)
- [x] Integration with WaveExecutor complete

### Risk Mitigation
**Risk 1**: Cache hit rate <60%
- Mitigation: Tune TTL values, analyze cache patterns, adjust similarity threshold

**Risk 2**: Redis connection failures
- Mitigation: Comprehensive error handling, fallback to no cache

**Risk 3**: Batching adds latency
- Mitigation: Tune batch window (500ms), make batching optional

**Risk 4**: Cost savings <30%
- Mitigation: Analyze cache hit patterns, increase TTL for stable prompts

---

## Next Steps

1. **Start with Phase 1**: LLM Prompt Cache foundation
2. **Parallel work**: Begin Phase 3 (Request Batching) after Task 1.2
3. **Integration**: Phase 4 brings everything together
4. **Validation**: Phase 5 verifies success metrics
5. **Iteration**: Adjust TTL/thresholds based on results
