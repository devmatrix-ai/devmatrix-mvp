# Coverage Audit Baseline - November 3, 2025

## Executive Summary

**Overall Coverage: 29%** (when including all source modules)
**Test Status:** 5 collection errors preventing full test execution
**Target:** Increase to 95%+ coverage as per Constitution requirements

## Critical Findings

### API Routers Coverage (Lowest Priority - Biggest Impact)

| Router | Coverage | Lines | Missing | Priority |
|--------|----------|-------|---------|----------|
| `execution.py` | **0%** | 66 | 66 | HIGH |
| `websocket.py` | **21%** | 243 | 192 | HIGH |
| `masterplans.py` | **26%** | 215 | 160 | HIGH |
| `testing.py` | **26%** | 109 | 81 | MEDIUM |
| `chat.py` | **28%** | 178 | 128 | HIGH |
| `rag.py` | **29%** | 182 | 129 | MEDIUM |
| `validation.py` | **30%** | 79 | 55 | HIGH |
| `auth.py` | **32%** | 493 | 337 | HIGH |
| `admin.py` | **33%** | 283 | 189 | LOW |
| `review.py` | **35%** | 133 | 86 | MEDIUM |
| `conversations.py` | **36%** | 166 | 107 | HIGH |
| `metrics.py` | **44%** | 68 | 38 | MEDIUM |
| `atomization.py` | **46%** | 112 | 61 | MEDIUM |
| `executions.py` | **47%** | 101 | 54 | HIGH |
| `execution_v2.py` | **51%** | 198 | 98 | MEDIUM |
| `dependency.py` | **55%** | 88 | 40 | MEDIUM |
| `usage.py` | **55%** | 75 | 34 | LOW |
| `health.py` | **58%** | 24 | 10 | MEDIUM |
| `workflows.py` | **62%** | 68 | 26 | LOW |

**Total Router Gap:** ~1,800 uncovered lines

### Service Layer Coverage (Critical Business Logic)

| Service | Coverage | Lines | Missing | Priority |
|---------|----------|-------|---------|----------|
| `tenancy_service.py` | **0%** | 95 | 95 | HIGH |
| `security_monitoring_service.py` | **10%** | 221 | 199 | HIGH |
| `masterplan_generation_service.py` | **11%** | 237 | 208 | HIGH |
| `masterplan_execution_service.py` | **12%** | 206 | 184 | HIGH |
| `log_archival_service.py` | **12%** | 220 | 193 | MEDIUM |
| `code_validator.py` | **14%** | 146 | 126 | HIGH |
| `task_executor.py` | **14%** | 170 | 146 | HIGH |
| `auth_service.py` | **15%** | 282 | 241 | HIGH |
| `review_service.py` | **15%** | 117 | 99 | MEDIUM |
| `sharing_service.py` | **15%** | 129 | 110 | MEDIUM |
| `account_lockout_service.py` | **16%** | 116 | 97 | HIGH |
| `alert_service.py` | **16%** | 154 | 129 | MEDIUM |
| `admin_service.py` | **18%** | 119 | 97 | LOW |
| `rbac_service.py` | **19%** | 99 | 80 | HIGH |
| `permission_service.py` | **20%** | 83 | 66 | HIGH |
| `session_service.py` | **20%** | 102 | 82 | HIGH |
| `chat_service.py` | **22%** | 285 | 221 | HIGH |

**Total Service Gap:** ~3,000 uncovered lines

### RAG System Coverage (ML Pipeline)

| Component | Coverage | Lines | Missing |
|-----------|----------|-------|---------|
| `embeddings.py` | **18%** | 90 | 74 |
| `vector_store.py` | **19%** | 183 | 149 |
| `context_builder.py` | **23%** | 151 | 116 |
| `retriever.py` | **23%** | 204 | 158 |
| `metrics.py` | **24%** | 94 | 71 |
| `persistent_cache.py` | **24%** | 197 | 149 |
| `feedback_service.py` | **36%** | 147 | 94 |

**Total RAG Gap:** ~800 uncovered lines

### MGE V2 Pipeline Coverage

| Component | Coverage | Lines | Missing |
|-----------|----------|-------|---------|
| `llm_prompt_cache.py` | **21%** | 115 | 91 |
| `rag_query_cache.py` | **19%** | 124 | 100 |
| `request_batcher.py` | **23%** | 84 | 65 |
| `retry_orchestrator.py` | **26%** | 108 | 80 |
| `wave_executor.py` | **31%** | 98 | 68 |
| `execution_service_v2.py` | **33%** | 138 | 92 |

**Total MGE V2 Gap:** ~500 uncovered lines

### Atomization/Parsing Coverage

| Component | Coverage | Lines | Missing |
|-----------|----------|-------|---------|
| `parser.py` | **25%** | 204 | 154 |
| `decomposer.py` | **26%** | 145 | 108 |
| `validator.py` | **22%** | 157 | 123 |
| `context_injector.py` | **17%** | 184 | 153 |

**Total Atomization Gap:** ~540 uncovered lines

### Test Collection Errors (Must Fix)

1. `tests/api/test_auth_endpoints.py` - Collection error
2. `tests/e2e/test_validation_postgres.py` - Collection error
3. `tests/integration/phase1/test_phase1_integration.py` - Collection error
4. `tests/security/test_penetration.py` - Collection error
5. `tests/unit/test_api_security.py` - FileNotFoundError

## Coverage Improvement Plan

### Phase 1: Fix Collection Errors (CRITICAL)
- Fix 5 broken test files preventing test execution
- Estimated impact: +100-200 tests

### Phase 2: High-Traffic API Routers (HIGH IMPACT)
- `execution.py`, `websocket.py`, `masterplans.py`, `chat.py`, `conversations.py`
- Estimated impact: +5-7% overall coverage

### Phase 3: Critical Services (HIGH IMPACT)
- Authentication, RBAC, Security Monitoring, Masterplan services
- Estimated impact: +8-10% overall coverage

### Phase 4: Supporting Components (MEDIUM IMPACT)
- RAG system, MGE V2 pipeline, Atomization
- Estimated impact: +5-8% overall coverage

### Phase 5: Error Paths & Edge Cases (POLISH)
- Exception handling, circuit breakers, fallbacks
- Estimated impact: +3-5% overall coverage

## Expected Outcomes

- **Current:** 29% overall (with collection errors)
- **After Phase 1:** 35-40% (errors fixed)
- **After Phase 2:** 45-50% (routers covered)
- **After Phase 3:** 60-70% (services covered)
- **After Phase 4:** 80-90% (components covered)
- **After Phase 5:** **95%+** (constitution compliant)

## Next Steps

1. ✅ Complete baseline audit
2. Create feature branch `002-comprehensive-test-suite`
3. Fix 5 collection errors
4. Implement router tests (15 files)
5. Implement service tests (20+ files)
6. Add error path coverage
7. Verify 95%+ target achieved

