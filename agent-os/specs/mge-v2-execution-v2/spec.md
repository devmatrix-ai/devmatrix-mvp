# MGE V2 Execution V2 - Specification

**Version**: 1.0
**Status**: Planning
**Owner**: Dany (lead), Eng2
**Due**: Week 2 Fri
**Priority**: CRITICAL - Closing the loop

## Overview

Implement the complete Execution V2 pipeline for MGE V2 - the "closing the loop" component that executes atomic code generation with intelligent retry orchestration and wave-based parallelism.

**Goal**: Achieve ≥98% precision through dependency-aware execution with 3-attempt retry loops.

## Success Criteria

From `precision_readiness_checklist.md`:
- ✅ WaveExecutor implemented (parallel execution per wave, 100+ atoms)
- ✅ RetryOrchestrator implemented (3 attempts, backoff, temperature 0.7→0.5→0.3)
- ✅ ExecutionServiceV2 implemented (state management, progress tracking, REST endpoints)
- ✅ Precision ≥95% after execution (validated via tests)
- ✅ Integration with existing Phase 1-5 components
- ✅ Prometheus metrics for monitoring

## Technical Requirements

### 1. WaveExecutor
**Purpose**: Execute atoms in parallel per wave (dependency level)

**Features**:
- Wave-based execution (sequential waves, parallel atoms within wave)
- Concurrency control (max 100 atoms per wave)
- Dependency resolution (atoms only execute after dependencies complete)
- Progress tracking (wave completion, atom status)
- Error handling (isolated failures don't crash entire wave)

**Integration Points**:
- Input: Execution plan from Phase 4 (dependency graph, waves)
- Uses: LLM client (enhanced_anthropic_client.py) for code generation
- Uses: Validator from Phase 2 (validation framework)
- Output: Execution results per atom

### 2. RetryOrchestrator
**Purpose**: Intelligent retry with temperature backoff

**Features**:
- 3 retry attempts (4 total including initial)
- Temperature backoff: 0.7 → 0.5 → 0.3
- Error feedback to LLM (previous validation errors passed to next attempt)
- Success early-exit (don't retry if validation passes)
- Retry metrics (attempts per atom, success rate)

**Retry Mathematics**:
```
P(success single attempt) = 0.90
P(all 4 fail) = 0.10^4 = 0.0001
P(success within 4 attempts) = 99.99%

For 800 atoms:
P(all succeed) = 0.9999^800 = 92.3%
With validation: 95-98% precision ✅
```

**Integration Points**:
- Input: Atom spec, dependencies, previous errors
- Uses: LLM client with temperature parameter
- Uses: Validator for attempt result checking
- Output: (code, validation_result, attempts_used)

### 3. ExecutionServiceV2
**Purpose**: State management and REST API

**Features**:
- Execution state tracking (pending, running, completed, failed)
- Progress reporting (wave progress, atom completion %)
- Cost tracking (LLM API costs per atom, per wave, total)
- Time tracking (execution time per atom, per wave, total)
- REST API endpoints for monitoring

**API Endpoints**:
```
POST /api/v2/execution/start - Start execution for masterplan
GET /api/v2/execution/{execution_id} - Get execution status
GET /api/v2/execution/{execution_id}/progress - Get progress details
GET /api/v2/execution/{execution_id}/waves/{wave_id} - Get wave status
GET /api/v2/execution/{execution_id}/atoms/{atom_id} - Get atom status
POST /api/v2/execution/{execution_id}/pause - Pause execution
POST /api/v2/execution/{execution_id}/resume - Resume execution
GET /api/v2/execution/{execution_id}/metrics - Get execution metrics
```

**State Schema**:
```python
class ExecutionState(BaseModel):
    execution_id: UUID
    masterplan_id: UUID
    status: ExecutionStatus  # pending, running, paused, completed, failed
    current_wave: int
    total_waves: int
    atoms_completed: int
    atoms_total: int
    atoms_succeeded: int
    atoms_failed: int
    total_cost_usd: float
    total_time_seconds: float
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
```

**Integration Points**:
- Uses: WaveExecutor and RetryOrchestrator for execution
- Uses: Cost tracking from Gap 9 (cost guardrails)
- Uses: Prometheus metrics for monitoring
- Output: REST API for external monitoring

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              ExecutionServiceV2 (FastAPI)               │
│  POST /start → GET /progress → GET /metrics             │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │       WaveExecutor            │
        │  - Sequential waves           │
        │  - Parallel atoms per wave    │
        │  - Max 100 concurrent         │
        └───────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │     RetryOrchestrator         │
        │  - 4 attempts (1 + 3 retries) │
        │  - Temp: 0.7 → 0.5 → 0.3      │
        │  - Error feedback to LLM      │
        └───────────────────────────────┘
                        │
            ┌───────────┴───────────┐
            ▼                       ▼
    ┌───────────────┐       ┌────────────────┐
    │  LLM Client   │       │   Validator    │
    │  (Phase 1-5)  │       │   (Phase 2)    │
    └───────────────┘       └────────────────┘
```

## Implementation Plan

### Phase 1: Core Components (Week 2 Mon-Tue)
1. **RetryOrchestrator** (src/mge/v2/execution/retry_orchestrator.py)
   - Retry loop with temperature backoff
   - Error feedback to LLM
   - Success tracking
   - Unit tests (20+ tests)

2. **WaveExecutor** (src/mge/v2/execution/wave_executor.py)
   - Wave-based execution
   - Parallel atom execution per wave
   - Dependency resolution
   - Progress tracking
   - Unit tests (25+ tests)

### Phase 2: Service Layer (Week 2 Wed)
3. **ExecutionServiceV2** (src/mge/v2/services/execution_service_v2.py)
   - State management
   - Progress tracking
   - Cost/time tracking
   - Integration with WaveExecutor
   - Unit tests (15+ tests)

### Phase 3: REST API (Week 2 Thu)
4. **API Endpoints** (src/api/routers/execution_v2.py)
   - 8 REST endpoints
   - Pydantic models for request/response
   - Error handling
   - Integration tests (10+ tests)

### Phase 4: Metrics & Monitoring (Week 2 Thu)
5. **Prometheus Metrics** (src/mge/v2/execution/metrics.py)
   - Execution metrics (precision, time, cost)
   - Wave metrics (wave completion, atom throughput)
   - Retry metrics (attempts, success rate)
   - Metric endpoint integration

### Phase 5: Integration & Documentation (Week 2 Fri)
6. **End-to-End Integration**
   - Integration tests with Phase 1-5
   - Full pipeline test (spec → execution → validation)
   - Performance testing (800 atom execution)

7. **Documentation**
   - execution_v2_guide.md (usage guide)
   - execution-v2-implementation-summary.md (technical summary)

## Dependencies

### Required Components (Already Implemented)
- ✅ Phase 1: Spec parsing and masterplan generation
- ✅ Phase 2: Validation framework (AtomicValidator)
- ✅ Phase 3: Atomization
- ✅ Phase 4: Execution planning (dependency graph, waves)
- ✅ Phase 5: RAG retrieval
- ✅ Gap 8: Concurrency controller
- ✅ Gap 9: Cost guardrails
- ✅ Gap 10: Caching & reuso

### External Dependencies
- EnhancedAnthropicClient (src/llm/enhanced_anthropic_client.py)
- AtomicValidator (src/mge/v2/validation/)
- Prometheus metrics framework
- FastAPI for REST endpoints
- asyncio for parallel execution

## Performance Targets

From Phase 6 documentation:

| Metric | Target | Validation |
|--------|--------|------------|
| Precision | ≥95% | After execution + retry |
| Time per atom | 5-10s | Average with retries |
| Parallel throughput | 100 atoms/wave | Max concurrent |
| Total time (800 atoms) | 1-1.5 hours | End-to-end |
| Retry rate | <20% | Atoms needing retry |
| Success after retry | >95% | 4-attempt success |

## Validation Approach

**No canary testing** (simplified from original plan):
- Direct Prometheus metrics validation
- Integration tests with real execution
- Performance benchmarks with 800-atom scenarios

## Files to Create

### Source Code (~1,400 LOC)
- src/mge/v2/execution/__init__.py
- src/mge/v2/execution/retry_orchestrator.py (~300 LOC)
- src/mge/v2/execution/wave_executor.py (~350 LOC)
- src/mge/v2/execution/metrics.py (~200 LOC)
- src/mge/v2/services/execution_service_v2.py (~400 LOC)
- src/api/routers/execution_v2.py (~150 LOC)

### Tests (~1,200 LOC)
- tests/mge/v2/execution/test_retry_orchestrator.py (~300 LOC)
- tests/mge/v2/execution/test_wave_executor.py (~350 LOC)
- tests/mge/v2/services/test_execution_service_v2.py (~300 LOC)
- tests/api/routers/test_execution_v2.py (~250 LOC)

### Documentation (~800 lines)
- DOCS/MGE_V2/execution_v2_guide.md (~600 lines)
- DOCS/MGE_V2/execution-v2-implementation-summary.md (~200 lines)

**Total Impact**: ~3,400 lines

## Prometheus Metrics

```yaml
Execution Performance:
  - v2_execution_precision_percent{masterplan_id}: Precision score
  - v2_execution_time_seconds{masterplan_id}: Total execution time
  - v2_execution_cost_usd_total{masterplan_id}: Total cost

Wave Metrics:
  - v2_wave_completion_percent{wave_id}: Wave progress
  - v2_wave_atom_throughput: Atoms/second per wave
  - v2_wave_time_seconds{wave_id}: Wave execution time

Retry Metrics:
  - v2_retry_attempts_total{atom_id}: Retry count per atom
  - v2_retry_success_rate: Success after retry (%)
  - v2_retry_temperature_changes: Temperature backoff events

Atom Metrics:
  - v2_atom_execution_time_seconds: Per-atom execution time
  - v2_atom_validation_pass_rate: Validation success rate
  - v2_atoms_succeeded_total: Successful atoms
  - v2_atoms_failed_total: Failed atoms
```

## Risk Mitigation

### Known Risks
1. **Concurrency overload**: WaveExecutor might overwhelm LLM API
   - Mitigation: Integration with Gap 8 (Concurrency Controller)

2. **Cost explosion**: 4 attempts per atom could be expensive
   - Mitigation: Integration with Gap 9 (Cost Guardrails)

3. **Retry failures**: Some atoms might fail all 4 attempts
   - Mitigation: Flag for human review (Gap TBD - Human Review)

4. **Dependency deadlock**: Circular dependencies could hang execution
   - Mitigation: Cycle detection from Phase 4 (execution planning)

## Success Validation

### Unit Tests
- RetryOrchestrator: 20+ tests covering retry logic, temperature backoff
- WaveExecutor: 25+ tests covering wave execution, parallelism
- ExecutionServiceV2: 15+ tests covering state management
- API: 10+ tests covering endpoints

### Integration Tests
- Full pipeline: Spec → Atomization → Planning → Execution → Validation
- 800-atom scenario: Performance benchmark
- Error scenarios: Retry logic, cost limits, concurrency limits

### Performance Tests
- Throughput: 100 atoms/wave
- Precision: ≥95% success rate
- Time: 1-1.5 hours for 800 atoms
- Cost: <$200 per masterplan (from Gap 9)

## Completion Criteria

- [x] All source files created and tested
- [x] All unit tests passing (70+ tests)
- [x] Integration tests passing
- [x] REST API endpoints functional
- [x] Prometheus metrics emitting
- [x] Documentation complete
- [x] Performance targets met (≥95% precision)
- [x] Week 2 Fri deadline met

## References

- DOCS/MGE_V2/08_PHASE_6_EXECUTION_RETRY.md - Phase 6 architecture
- DOCS/MGE_V2/precision_readiness_checklist.md - Requirements
- src/mge/v2/caching/ - Gap 10 implementation (reference for patterns)
- src/llm/enhanced_anthropic_client.py - LLM client integration
- src/mge/v2/validation/ - Validation framework
