# MGE V2 Precision Gaps - Implementation Specs

**Created**: 2025-01-24
**Status**: Ready for Implementation
**Goal**: Close critical gaps in Precision Readiness Checklist to achieve ≥95% alignment and 98% precision target

---

## Overview

Este directorio contiene las especificaciones técnicas completas para cerrar los **7 gaps críticos** identificados en el análisis de alineación con el Precision Readiness Checklist.

**Estado Actual**: 71% alignment → **Target**: ≥95% alignment
**Timeline**: 3 semanas (Weeks 12-14)
**Resultado esperado**: Precision ≥98%, Time <1.5h, Cost <$200

---

## Contents

### Planning Documents

1. **`idea.md`** - Initial gap analysis and requirements discovery
   - 7 gaps identificados (4 P0 CRITICAL, 3 P1 HIGH)
   - Impact assessment y effort estimates
   - Implementation strategy overview

2. **`implementation-plan-e2e.md`** - Master implementation plan
   - Week-by-week breakdown (Weeks 12-14)
   - 3 parallel tracks with resource allocation
   - Critical path analysis
   - Risk management
   - Success metrics and monitoring
   - **READ THIS FIRST** for execution overview

### Technical Specifications (P0 CRITICAL)

3. **`gap-3-acceptance-tests.md`** - Acceptance Tests Autogenerados
   - **Priority**: P0 CRITICAL
   - **Effort**: 7-10 días
   - **Owner**: Eng1 + Eng2
   - **Blocks**: Item 2 (Precision Score), Item 12 (Gate enforcement)
   - **Impact**: Enables 50% of precision score calculation
   - Components:
     - RequirementParser (parse MUST/SHOULD from masterplan)
     - TestTemplateEngine (pytest + Jest generation)
     - AcceptanceTestRunner (parallel execution)
     - AcceptanceTestGate (100% must + ≥95% should enforcement)
   - Database: `acceptance_tests`, `acceptance_test_results`
   - API: 4 endpoints
   - Tests: 55+ tests

4. **`gap-8-concurrency-controller.md`** - Concurrency Controller Adaptativo
   - **Priority**: P0 CRITICAL
   - **Effort**: 4-5 días
   - **Owner**: Eng2
   - **Impact**: Guarantees stable p95 latency, prevents overload
   - Components:
     - MetricsMonitor (Prometheus queries every 30s)
     - LimitAdjuster (adaptive algorithm: decrease 10% / increase 5%)
     - BackpressureQueue (priority queue with timeout)
     - ThunderingHerdPrevention (gradual ramp-up)
   - API: 1 endpoint
   - Tests: 20+ tests

5. **`gap-9-cost-guardrails.md`** - Cost Guardrails
   - **Priority**: P0 CRITICAL
   - **Effort**: 3-4 días
   - **Owner**: Dany
   - **Impact**: Guarantees <$200 per project, prevents cost overruns
   - Components:
     - CostTracker (real-time tracking per atom)
     - CostGuardrails (soft cap 70%, hard cap 100%)
     - Budget override API (superuser approval)
   - Database: `cost_events` table
   - API: 3 endpoints
   - Grafana: 3 alerts (soft cap, hard cap, projected exceed)
   - Tests: 20+ tests

6. **`gap-10-caching-reuse.md`** - Cacheo & Reuso
   - **Priority**: P0 CRITICAL
   - **Effort**: 5-6 días
   - **Owner**: Eng1
   - **Impact**: 40-60% time reduction, 30-50% cost reduction
   - Components:
     - LLMPromptCache (Redis, 24h TTL)
     - RAGQueryCache (Redis, 1h TTL, similarity matching)
     - RequestBatcher (batch 5 atoms, 500ms window)
   - Target: ≥60% combined hit rate
   - Tests: 30+ tests

---

## High Priority Gaps (P1)

**Item 2: Precision Score Compuesto** (3-5d, Dany)
- Depends on Gap 3 (Acceptance Tests)
- Score = 50% Spec Conformance + 30% Integration Pass + 20% Validation Pass
- Included in Week 12 Track 2 with Cost Guardrails

**Item 5: Dependencies Ground Truth** (5-7d, Eng2 + Eng1)
- 80% done, needs: dynamic imports, barrel files, TS path aliases
- Validation vs tsc/bundler
- Target: ≥90% accuracy, 0 false negatives
- Week 13 Track 3

**Item 11: Traceability E2E** (4-5d, Dany)
- 40% done, needs: unified trace_id, cost per atom, correlations dashboard
- Week 13 Track 2

---

## Implementation Timeline

### Week 12: Critical Path (Días 1-10)

**Track 1** (Eng1 + Eng2): Acceptance Tests (Gap 3)
- Days 1-2: Requirement parsing
- Days 3-5: Test generation
- Days 6-8: Test execution
- Days 9-10: Gate enforcement + integration

**Track 2** (Dany): Cost Guardrails (Gap 9) + Precision Score
- Days 1-3: Cost tracking + guardrails
- Days 4-6: Precision score calculation

**Track 3** (Eng2): Concurrency Controller (Gap 8)
- Days 1-2: Metrics monitoring + adaptive adjuster
- Days 3-4: Backpressure queue + thundering herd prevention
- Day 5: Integration

### Week 13: Optimization & Quality (Días 11-17)

**Track 1** (Eng1): Caching & Reuso (Gap 10)
- Days 11-12: LLM prompt cache
- Days 13-14: RAG query cache
- Days 15-16: Request batching

**Track 2** (Dany): Traceability E2E
- Days 11-13: Unified trace_id
- Days 14-15: Correlations dashboard

**Track 3** (Eng2 + Eng1): Dependencies Ground Truth
- Days 11-13: Dynamic imports + barrel files
- Days 14-17: Validation + accuracy measurement

### Week 14: E2E Testing & Production (Días 18-21)

- Day 18: E2E testing setup (10 canary projects)
- Day 19: Validation (all gaps working)
- Day 20: Performance testing (time, cost, precision)
- Day 21: Production migration

---

## Quick Reference

### Critical Paths

**Longest**: Acceptance Tests (10d) → blocks everything
**Shortest**: Concurrency Controller (5d)

**Dependencies**:
- Precision Score depends on Acceptance Tests
- All Week 13 work can start immediately (no dependencies on Week 12)

### Resource Allocation

**Eng1**:
- Week 12: Acceptance Tests (lead) - 10d
- Week 13: Caching - 6d
- Week 13: Dependencies validation - 3d

**Eng2**:
- Week 12: Acceptance Tests (support) - 3d
- Week 12: Concurrency - 5d
- Week 13: Dependencies detection - 5d

**Dany**:
- Week 12: Cost - 4d
- Week 12: Precision - 5d
- Week 13: Traceability - 5d
- Week 14: E2E testing lead - 4d

### Success Metrics

**Week 12 End**:
- ✅ 4 P0 gaps closed (Items 3, 8, 9, 2)
- ✅ 110+ tests passing
- ✅ Gate S enforcing
- ✅ Cost guardrails active
- ✅ Concurrency adaptive

**Week 13 End**:
- ✅ All 7 gaps closed (Items 10, 11, 5)
- ✅ 175+ total tests passing
- ✅ Cache hit rate ≥60%
- ✅ Dependencies accuracy ≥90%
- ✅ Full E2E traceability

**Week 14 End (Production)**:
- ✅ Alignment: 71% → ≥95%
- ✅ Precision: ≥98% on 10 canaries
- ✅ Time: <1.5h per project
- ✅ Cost: <$200 per project (enforced)

---

## Monitoring

### Prometheus Metrics (28 total)

**Acceptance Tests** (6 metrics):
- `v2_acceptance_tests_generated_total`
- `v2_acceptance_test_execution_seconds`
- `v2_acceptance_test_pass_rate`
- `v2_gate_s_status`
- `v2_gate_s_must_pass_rate`
- `v2_gate_s_should_pass_rate`

**Cost Guardrails** (4 metrics):
- `v2_budget_limit_usd`
- `v2_predicted_remaining_cost_usd`
- `v2_cost_guardrail_triggered_total`
- `v2_masterplan_paused_budget`

**Concurrency** (6 metrics):
- `v2_concurrency_limit`
- `v2_concurrency_limit_changes_total`
- `v2_backpressure_queue_size`
- `v2_backpressure_queue_wait_seconds`
- `v2_backpressure_queue_drops_total`
- `v2_backpressure_queue_timeouts_total`

**Caching** (8 metrics):
- `v2_cache_hits_total`
- `v2_cache_misses_total`
- `v2_cache_writes_total`
- `v2_cache_invalidations_total`
- `v2_cache_errors_total`
- `v2_cache_cost_savings_usd_total`
- `v2_batch_size`
- `v2_batch_requests_processed_total`

**Precision** (2 metrics):
- `v2_precision_score`
- `v2_precision_score_components` (3 labels: spec, integration, validation)

**Traceability** (2 metrics):
- `v2_trace_coverage_percentage`
- `v2_correlation_strength` (per correlation type)

### Grafana Alerts (6 total)

**Cost Alerts**:
1. `CostSoftCapExceeded` (warning, 70% budget)
2. `CostHardCapReached` (critical, 100% budget)
3. `CostProjectedExceedsBudget` (warning, projected > budget)

**Performance Alerts**:
4. `LLMLatencyHigh` (warning, p95 >2s)
5. `DBLatencyHigh` (warning, p95 >100ms)

**Quality Alerts**:
6. `CacheHitRateLow` (warning, combined <60%)

---

## Database Changes

### New Tables (3)

1. **`acceptance_tests`** - Generated tests from masterplan requirements
2. **`acceptance_test_results`** - Test execution results
3. **`cost_events`** - Cost tracking events (soft cap, hard cap, overrides)

### Modified Tables

**`masterplans`** - Add budget columns:
- `budget_limit_usd` (default 200.00)
- `soft_cap_percentage` (default 70.00)
- `hard_cap_percentage` (default 100.00)
- `current_cost_usd` (default 0.0)
- `budget_override_approved_by`
- `budget_override_approved_at`

**All tables** - Add traceability:
- `trace_id` (UUID, for E2E correlation)

---

## API Endpoints (9 new)

### Acceptance Testing (4 endpoints)

- `POST /api/v2/testing/generate/{masterplan_id}` - Generate tests from masterplan
- `POST /api/v2/testing/run/{wave_id}` - Run acceptance tests
- `GET /api/v2/testing/gate/{masterplan_id}` - Check Gate S status
- `GET /api/v2/testing/results/{masterplan_id}` - Get test results

### Cost Guardrails (3 endpoints)

- `GET /api/v2/cost/{masterplan_id}` - Get cost status
- `POST /api/v2/cost/{masterplan_id}/override` - Approve budget override
- `GET /api/v2/cost/{masterplan_id}/events` - Get cost event history

### Concurrency (1 endpoint)

- `GET /api/v2/concurrency/status` - Get concurrency controller status

### Precision (1 endpoint)

- `GET /api/v2/precision/{masterplan_id}` - Get precision score breakdown

---

## Testing Strategy

### Unit Tests (135+ total)

- Acceptance Tests: 45 tests
- Cost Guardrails: 20 tests
- Concurrency: 15 tests
- Caching: 20 tests
- Precision Score: 15 tests
- Traceability: 10 tests
- Dependencies: 25 tests

### Integration Tests (40+ total)

- E2E acceptance test pipeline: 10 tests
- Cost tracking + guardrails flow: 5 tests
- Concurrency adaptive execution: 5 tests
- Cache hit/miss scenarios: 10 tests
- Precision score accuracy: 5 tests
- Dependencies validation: 5 tests

### E2E Tests (Week 14)

- 10 canary projects (diverse: Python, TS, monorepo, API, UI)
- Full pipeline execution with all gaps active
- Metrics validation: time, cost, precision

---

## Dependencies

### External

- **Redis**: For caching (LLM prompts, RAG queries)
- **Prometheus**: For metrics collection
- **Grafana**: For dashboards and alerting
- **PostgreSQL**: For database tables

### Internal

- **Phase 1-5**: Complete (Foundation, Atomization, Dependencies, Validation, Execution)
- **Week 11**: Human Review System complete
- **WaveExecutor**: Needs integration with all gaps

---

## Getting Started

### Prerequisites

1. MGE V2 Phases 1-5 complete and tested
2. Human Review System (Week 11) deployed
3. Redis available at `redis://localhost:6379`
4. Prometheus available at `http://localhost:9090`
5. Grafana available at `http://localhost:3000`

### Setup

```bash
# 1. Create feature branches
git checkout -b feature/week-12-acceptance-tests
git checkout -b feature/week-12-cost-guardrails
git checkout -b feature/week-12-concurrency

# 2. Install dependencies
cd src/api
pip install tiktoken redis aiohttp

# 3. Run database migrations
alembic upgrade head

# 4. Setup Redis
docker run -d -p 6379:6379 redis:7-alpine

# 5. Configure Grafana alerts
# Import alert rules from config/grafana/alerts/
```

### Development Workflow

1. **Read the spec** for your assigned gap
2. **Follow day-by-day plan** in the spec
3. **Write tests first** (TDD approach)
4. **Implement components** incrementally
5. **Run tests continuously** (`pytest -v` or `npm test`)
6. **Update metrics** as you go
7. **Document edge cases** and decisions
8. **Daily standup** at 10am (15min max)
9. **EOD update** in Slack with progress

### Testing

```bash
# Unit tests
cd src/api
pytest tests/mge/v2/testing/ -v
pytest tests/mge/v2/cost/ -v
pytest tests/mge/v2/concurrency/ -v
pytest tests/mge/v2/caching/ -v

# Integration tests
pytest tests/mge/v2/integration/ -v

# Coverage
pytest --cov=src/mge/v2 --cov-report=html
```

### Monitoring

```bash
# Check Prometheus metrics
curl http://localhost:9090/api/v1/query?query=v2_gate_s_status

# Check Redis
redis-cli
> KEYS llm_cache:*
> GET llm_cache:abc123...

# Check Grafana dashboards
open http://localhost:3000/d/mge-v2-precision
```

---

## Support

### Questions / Issues

- **Slack**: #mge-v2-gaps
- **Jira**: Project MGE-V2, Epic "Precision Gaps Week 12-14"
- **Lead**: Dany (@dany)

### Escalation

- **Blocker >4h**: Escalate to Dany immediately
- **Risk materialized**: Call immediate meeting
- **Production issue**: Follow incident response process

---

## Related Documents

- **Precision Readiness Checklist**: `DOCS/MGE_V2/precision_readiness_checklist.md`
- **Architecture Analysis**: `claudedocs/mge_v2_architecture_analysis.md`
- **Alignment Analysis**: `claudedocs/precision_checklist_alignment.md`
- **Comprehensive Workflow**: `agent-os/workflows/mge-v2-gaps-critical.md`
- **Original Spec**: `agent-os/specs/mge-v2-direct/`

---

## Status Tracking

### Week 12 Progress

| Gap | Owner | Status | Tests | API | Monitoring |
|-----|-------|--------|-------|-----|------------|
| Gap 3 (Acceptance) | Eng1+Eng2 | ⏳ Not Started | 0/55 | 0/4 | 0/6 |
| Gap 9 (Cost) | Dany | ⏳ Not Started | 0/20 | 0/3 | 0/4 |
| Gap 2 (Precision) | Dany | ⏳ Not Started | 0/15 | 0/1 | 0/2 |
| Gap 8 (Concurrency) | Eng2 | ⏳ Not Started | 0/20 | 0/1 | 0/6 |

### Week 13 Progress

| Gap | Owner | Status | Tests | API | Monitoring |
|-----|-------|--------|-------|-----|------------|
| Gap 10 (Caching) | Eng1 | ⏳ Not Started | 0/30 | 0/0 | 0/8 |
| Gap 11 (Traceability) | Dany | ⏳ Not Started | 0/10 | 0/0 | 0/2 |
| Gap 5 (Dependencies) | Eng2+Eng1 | ⏳ Not Started | 0/25 | 0/0 | 0/0 |

### Overall Progress

- **Alignment**: 71% (target: ≥95%)
- **Tests Passing**: 0/175 (target: 175+)
- **API Endpoints**: 0/9 (target: 9)
- **Monitoring**: 0/28 metrics, 0/6 alerts
- **Estimated Completion**: Week 14 Day 21

---

**Last Updated**: 2025-01-24
**Version**: 1.0
**Status**: ✅ Specs Complete, Ready for Implementation

🚀 **Let's build MGE V2 with 98% precision!**

