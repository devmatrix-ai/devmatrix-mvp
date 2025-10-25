# MGE V2 Execution V2 - Implementation Tasks

**Generated**: 2025-10-25
**Strategy**: Adaptive with deep analysis
**Total Phases**: 5
**Estimated Duration**: 5 days (Week 2 Mon-Fri)
**Total Tasks**: 28

---

## Phase 1: RetryOrchestrator Core (Day 1 - Mon)

### Task 1.1: Create retry_orchestrator.py module
**Complexity**: Medium
**Duration**: 2 hours
**Dependencies**: None

**Actions**:
- Create `src/mge/v2/execution/__init__.py`
- Create `src/mge/v2/execution/retry_orchestrator.py`
- Define `RetryOrchestrator` class with constructor
- Define retry configuration (MAX_ATTEMPTS=4, temperature backoff)

**Acceptance Criteria**:
- Module imports successfully
- Class instantiates with LLM client and validator
- Configuration constants defined

**Code Structure**:
```python
class RetryOrchestrator:
    MAX_ATTEMPTS = 4
    TEMPERATURE_SCHEDULE = [0.7, 0.5, 0.3, 0.3]  # Initial + 3 retries

    def __init__(self, llm_client, validator):
        self.llm_client = llm_client
        self.validator = validator
```

---

### Task 1.2: Implement retry loop logic
**Complexity**: High
**Duration**: 3 hours
**Dependencies**: Task 1.1

**Actions**:
- Implement `execute_with_retry()` method
- Temperature backoff logic (0.7 → 0.5 → 0.3)
- Error collection from validation results
- Success early-exit (don't retry if validation passes)
- Return tuple: (code, validation_result, attempts_used)

**Acceptance Criteria**:
- Retry loop executes up to 4 attempts
- Temperature decreases on each retry
- Previous errors passed to LLM on retries
- Early exit on validation success
- All attempts tracked

**Key Logic**:
```python
async def execute_with_retry(
    self,
    atom_spec: AtomicUnit,
    dependencies: List[AtomicUnit]
) -> Tuple[str, ValidationResult, int]:
    errors = []

    for attempt in range(1, self.MAX_ATTEMPTS + 1):
        temperature = self.TEMPERATURE_SCHEDULE[attempt - 1]

        # Generate code with current temperature
        code = await self.llm_client.generate(
            atom_spec=atom_spec,
            dependencies=dependencies,
            temperature=temperature,
            previous_errors=errors if attempt > 1 else None
        )

        # Validate
        atom_spec.code = code
        validation_result = await self.validator.validate(atom_spec)

        if validation_result.passed:
            return code, validation_result, attempt

        # Collect errors for next attempt
        errors = [issue.message for issue in validation_result.issues
                 if issue.severity in [CRITICAL, ERROR]]

    return code, validation_result, self.MAX_ATTEMPTS
```

---

### Task 1.3: Add retry metrics emission
**Complexity**: Low
**Duration**: 1 hour
**Dependencies**: Task 1.2

**Actions**:
- Create `src/mge/v2/execution/metrics.py`
- Define Prometheus metrics for retries
- Emit metrics on each attempt
- Track success/failure rates

**Metrics**:
```python
RETRY_ATTEMPTS_TOTAL = Counter("v2_retry_attempts_total", "Retry attempts", ["atom_id"])
RETRY_SUCCESS_RATE = Gauge("v2_retry_success_rate", "Retry success rate")
RETRY_TEMPERATURE_CHANGES = Counter("v2_retry_temperature_changes", "Temperature backoff events")
```

**Acceptance Criteria**:
- Metrics module created
- Metrics emit on each retry attempt
- Success rate calculated correctly

---

### Task 1.4: Write RetryOrchestrator unit tests
**Complexity**: Medium
**Duration**: 3 hours
**Dependencies**: Task 1.3

**Actions**:
- Create `tests/mge/v2/execution/test_retry_orchestrator.py`
- Test successful first attempt (no retries)
- Test retry after validation failure
- Test temperature backoff schedule
- Test error feedback to LLM
- Test max attempts exhaustion
- Test metrics emission

**Test Coverage**:
- 20+ unit tests
- Success scenarios (attempt 1, 2, 3, 4)
- Failure scenarios (all attempts fail)
- Temperature backoff verification
- Error feedback verification
- Metrics verification

**Acceptance Criteria**:
- All 20+ tests passing
- 100% code coverage for retry logic
- All edge cases covered

---

## Phase 2: WaveExecutor Core (Day 2 - Tue)

### Task 2.1: Create wave_executor.py module
**Complexity**: Medium
**Duration**: 2 hours
**Dependencies**: Task 1.4 (RetryOrchestrator complete)

**Actions**:
- Create `src/mge/v2/execution/wave_executor.py`
- Define `WaveExecutor` class
- Define wave configuration (max_concurrency=100)
- Integration with RetryOrchestrator

**Acceptance Criteria**:
- Module created and imports successfully
- Class instantiates with RetryOrchestrator
- Concurrency configuration defined

**Code Structure**:
```python
class WaveExecutor:
    def __init__(
        self,
        retry_orchestrator: RetryOrchestrator,
        max_concurrency: int = 100
    ):
        self.retry_orchestrator = retry_orchestrator
        self.max_concurrency = max_concurrency
```

---

### Task 2.2: Implement wave execution logic
**Complexity**: High
**Duration**: 4 hours
**Dependencies**: Task 2.1

**Actions**:
- Implement `execute_wave()` method
- Parallel execution with asyncio (max 100 concurrent)
- Dependency resolution (get completed dependencies)
- Per-atom execution via RetryOrchestrator
- Progress tracking (atoms completed/total)
- Error isolation (one atom failure doesn't crash wave)

**Acceptance Criteria**:
- Wave executes atoms in parallel
- Respects max_concurrency limit (100 atoms)
- Dependencies resolved before atom execution
- Progress tracked accurately
- Isolated error handling

**Key Logic**:
```python
async def execute_wave(
    self,
    wave_atoms: List[AtomicUnit],
    all_atoms: Dict[str, AtomicUnit]
) -> Dict[str, ExecutionResult]:
    results = {}

    # Create semaphore for concurrency control
    semaphore = asyncio.Semaphore(self.max_concurrency)

    async def execute_atom(atom: AtomicUnit):
        async with semaphore:
            # Get dependencies (already completed)
            deps = [all_atoms[dep_id] for dep_id in atom.depends_on]

            # Execute with retry
            code, validation, attempts = await self.retry_orchestrator.execute_with_retry(
                atom_spec=atom,
                dependencies=deps
            )

            return ExecutionResult(
                atom_id=atom.id,
                success=validation.passed,
                code=code,
                validation=validation,
                attempts=attempts
            )

    # Execute all atoms in parallel
    tasks = [execute_atom(atom) for atom in wave_atoms]
    atom_results = await asyncio.gather(*tasks, return_exceptions=True)

    for atom, result in zip(wave_atoms, atom_results):
        if isinstance(result, Exception):
            results[atom.id] = ExecutionResult(
                atom_id=atom.id,
                success=False,
                error=str(result)
            )
        else:
            results[atom.id] = result

    return results
```

---

### Task 2.3: Implement multi-wave orchestration
**Complexity**: Medium
**Duration**: 2 hours
**Dependencies**: Task 2.2

**Actions**:
- Implement `execute_plan()` method
- Sequential wave execution (wave N after wave N-1)
- Progress tracking across waves
- Wave-level metrics emission
- Summary statistics (precision, time, cost)

**Acceptance Criteria**:
- Waves execute sequentially
- Progress tracked across all waves
- Metrics emitted per wave
- Summary calculated correctly

**Key Logic**:
```python
async def execute_plan(
    self,
    execution_plan: List[ExecutionWave],
    atoms: Dict[str, AtomicUnit]
) -> Dict[str, ExecutionResult]:
    all_results = {}
    total_atoms = sum(len(wave.atom_ids) for wave in execution_plan)
    completed = 0

    for wave in execution_plan:
        wave_atoms = [atoms[aid] for aid in wave.atom_ids]

        # Execute wave
        wave_results = await self.execute_wave(wave_atoms, atoms)
        all_results.update(wave_results)

        # Update progress
        completed += len(wave.atom_ids)
        success_count = sum(1 for r in wave_results.values() if r.success)

        # Emit metrics
        self._emit_wave_metrics(wave, wave_results, completed, total_atoms)

    return all_results
```

---

### Task 2.4: Add wave metrics emission
**Complexity**: Low
**Duration**: 1 hour
**Dependencies**: Task 2.3

**Actions**:
- Add wave metrics to `metrics.py`
- Emit metrics per wave
- Track wave completion, throughput, time

**Metrics**:
```python
WAVE_COMPLETION_PERCENT = Gauge("v2_wave_completion_percent", "Wave progress", ["wave_id"])
WAVE_ATOM_THROUGHPUT = Gauge("v2_wave_atom_throughput", "Atoms/second per wave")
WAVE_TIME_SECONDS = Histogram("v2_wave_time_seconds", "Wave execution time", ["wave_id"])
```

**Acceptance Criteria**:
- Wave metrics defined
- Metrics emit after each wave
- Throughput calculated correctly

---

### Task 2.5: Write WaveExecutor unit tests
**Complexity**: High
**Duration**: 4 hours
**Dependencies**: Task 2.4

**Actions**:
- Create `tests/mge/v2/execution/test_wave_executor.py`
- Test single wave execution
- Test multi-wave execution
- Test concurrency limits (max 100)
- Test dependency resolution
- Test error isolation
- Test progress tracking
- Test metrics emission

**Test Coverage**:
- 25+ unit tests
- Single wave scenarios
- Multi-wave scenarios
- Concurrency scenarios (50, 100, 150 atoms)
- Dependency scenarios
- Error scenarios
- Metrics verification

**Acceptance Criteria**:
- All 25+ tests passing
- 100% code coverage for wave logic
- Performance tests verify concurrency limits

---

## Phase 3: ExecutionServiceV2 (Day 3 - Wed)

### Task 3.1: Create execution_service_v2.py module
**Complexity**: Medium
**Duration**: 2 hours
**Dependencies**: Task 2.5 (WaveExecutor complete)

**Actions**:
- Create `src/mge/v2/services/execution_service_v2.py`
- Define `ExecutionServiceV2` class
- Define state models (ExecutionState, AtomStatus, WaveStatus)
- State storage (in-memory dict for MVP, can extend to DB later)

**Acceptance Criteria**:
- Module created
- Class instantiates with WaveExecutor
- State models defined with Pydantic

**State Models**:
```python
class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

class ExecutionState(BaseModel):
    execution_id: UUID
    masterplan_id: UUID
    status: ExecutionStatus
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

---

### Task 3.2: Implement execution start/stop methods
**Complexity**: High
**Duration**: 3 hours
**Dependencies**: Task 3.1

**Actions**:
- Implement `start_execution()` method
- Implement `pause_execution()` method
- Implement `resume_execution()` method
- State transitions (pending → running → paused → completed)
- Integration with WaveExecutor

**Acceptance Criteria**:
- Start creates new execution state
- Pause stops execution gracefully
- Resume continues from paused state
- State transitions correct

**Key Logic**:
```python
async def start_execution(
    self,
    masterplan_id: UUID,
    execution_plan: List[ExecutionWave],
    atoms: Dict[str, AtomicUnit]
) -> UUID:
    execution_id = uuid4()

    # Initialize state
    state = ExecutionState(
        execution_id=execution_id,
        masterplan_id=masterplan_id,
        status=ExecutionStatus.RUNNING,
        current_wave=0,
        total_waves=len(execution_plan),
        atoms_total=sum(len(w.atom_ids) for w in execution_plan),
        atoms_completed=0,
        atoms_succeeded=0,
        atoms_failed=0,
        total_cost_usd=0.0,
        total_time_seconds=0.0,
        started_at=datetime.utcnow()
    )

    self.executions[execution_id] = state

    # Execute in background
    asyncio.create_task(self._execute_background(execution_id, execution_plan, atoms))

    return execution_id
```

---

### Task 3.3: Implement progress tracking
**Complexity**: Medium
**Duration**: 2 hours
**Dependencies**: Task 3.2

**Actions**:
- Implement `get_execution_state()` method
- Implement `get_wave_status()` method
- Implement `get_atom_status()` method
- Track progress in real-time during execution
- Calculate completion percentages

**Acceptance Criteria**:
- Progress retrieved accurately
- Wave status reflects current state
- Atom status reflects individual results
- Percentages calculated correctly

---

### Task 3.4: Implement cost and time tracking
**Complexity**: Low
**Duration**: 2 hours
**Dependencies**: Task 3.3

**Actions**:
- Track cost per atom (from LLM client)
- Track time per atom
- Aggregate cost and time per wave
- Total cost and time for execution
- Integration with Gap 9 (cost guardrails)

**Acceptance Criteria**:
- Cost tracked per atom and aggregated
- Time tracked per atom and aggregated
- Cost guardrails integration (pause if limit exceeded)
- Metrics emitted

---

### Task 3.5: Write ExecutionServiceV2 unit tests
**Complexity**: Medium
**Duration**: 3 hours
**Dependencies**: Task 3.4

**Actions**:
- Create `tests/mge/v2/services/test_execution_service_v2.py`
- Test execution start/pause/resume
- Test state transitions
- Test progress tracking
- Test cost tracking
- Test time tracking
- Test error handling

**Test Coverage**:
- 15+ unit tests
- State transition scenarios
- Progress tracking scenarios
- Cost/time tracking scenarios
- Error scenarios

**Acceptance Criteria**:
- All 15+ tests passing
- 100% code coverage for service logic
- State management verified

---

## Phase 4: REST API Endpoints (Day 4 - Thu)

### Task 4.1: Create execution_v2.py router
**Complexity**: Medium
**Duration**: 2 hours
**Dependencies**: Task 3.5 (ExecutionServiceV2 complete)

**Actions**:
- Create `src/api/routers/execution_v2.py`
- Define FastAPI router with prefix `/api/v2/execution`
- Define request/response Pydantic models
- Integration with ExecutionServiceV2

**Acceptance Criteria**:
- Router created and registered in app
- Request/response models defined
- Service integration configured

---

### Task 4.2: Implement execution control endpoints
**Complexity**: Medium
**Duration**: 3 hours
**Dependencies**: Task 4.1

**Actions**:
- POST `/api/v2/execution/start` - Start execution
- POST `/api/v2/execution/{execution_id}/pause` - Pause execution
- POST `/api/v2/execution/{execution_id}/resume` - Resume execution
- Error handling and validation

**Acceptance Criteria**:
- All 3 endpoints functional
- Request validation working
- Error responses proper (400, 404, 500)
- OpenAPI docs generated

**Endpoint Example**:
```python
@router.post("/start")
async def start_execution(request: StartExecutionRequest) -> StartExecutionResponse:
    execution_id = await execution_service.start_execution(
        masterplan_id=request.masterplan_id,
        execution_plan=request.execution_plan,
        atoms=request.atoms
    )
    return StartExecutionResponse(execution_id=execution_id)
```

---

### Task 4.3: Implement status and progress endpoints
**Complexity**: Low
**Duration**: 2 hours
**Dependencies**: Task 4.2

**Actions**:
- GET `/api/v2/execution/{execution_id}` - Get execution status
- GET `/api/v2/execution/{execution_id}/progress` - Get progress details
- GET `/api/v2/execution/{execution_id}/waves/{wave_id}` - Get wave status
- GET `/api/v2/execution/{execution_id}/atoms/{atom_id}` - Get atom status

**Acceptance Criteria**:
- All 4 GET endpoints functional
- Response models match state models
- 404 handling for non-existent IDs

---

### Task 4.4: Implement metrics endpoint
**Complexity**: Low
**Duration**: 1 hour
**Dependencies**: Task 4.3

**Actions**:
- GET `/api/v2/execution/{execution_id}/metrics` - Get execution metrics
- Return precision, cost, time, retry stats
- Integration with Prometheus metrics

**Acceptance Criteria**:
- Metrics endpoint returns comprehensive stats
- Prometheus metrics accessible
- Response includes precision, cost, time, retries

---

### Task 4.5: Write API integration tests
**Complexity**: Medium
**Duration**: 3 hours
**Dependencies**: Task 4.4

**Actions**:
- Create `tests/api/routers/test_execution_v2.py`
- Test all 8 endpoints
- Test request validation
- Test error scenarios (404, 400, 500)
- Test authentication (if applicable)

**Test Coverage**:
- 10+ integration tests
- Happy path scenarios for all endpoints
- Error scenarios
- Validation scenarios

**Acceptance Criteria**:
- All 10+ tests passing
- All endpoints verified
- Error handling verified

---

## Phase 5: Integration, Metrics & Documentation (Day 5 - Fri)

### Task 5.1: Add execution performance metrics
**Complexity**: Low
**Duration**: 1 hour
**Dependencies**: Task 4.5

**Actions**:
- Add execution metrics to `metrics.py`
- Precision metric (% atoms succeeded)
- Execution time histogram
- Cost counter
- Atom success/failure counters

**Metrics**:
```python
EXECUTION_PRECISION_PERCENT = Gauge("v2_execution_precision_percent", "Precision", ["masterplan_id"])
EXECUTION_TIME_SECONDS = Histogram("v2_execution_time_seconds", "Execution time", ["masterplan_id"])
EXECUTION_COST_USD_TOTAL = Counter("v2_execution_cost_usd_total", "Total cost", ["masterplan_id"])
ATOMS_SUCCEEDED_TOTAL = Counter("v2_atoms_succeeded_total", "Successful atoms")
ATOMS_FAILED_TOTAL = Counter("v2_atoms_failed_total", "Failed atoms")
ATOM_EXECUTION_TIME_SECONDS = Histogram("v2_atom_execution_time_seconds", "Per-atom time")
ATOM_VALIDATION_PASS_RATE = Gauge("v2_atom_validation_pass_rate", "Validation pass rate")
```

**Acceptance Criteria**:
- All 7 metrics defined
- Metrics emit during execution
- Prometheus endpoint exposes metrics

---

### Task 5.2: End-to-end integration test
**Complexity**: High
**Duration**: 3 hours
**Dependencies**: Task 5.1

**Actions**:
- Create `tests/mge/v2/integration/test_execution_pipeline.py`
- Full pipeline test: Spec → Atomization → Planning → Execution → Validation
- 800-atom performance benchmark
- Verify precision ≥95%
- Verify performance targets (1-1.5 hours)

**Acceptance Criteria**:
- Full pipeline test passes
- Precision ≥95% achieved
- Performance within targets
- Cost within limits (<$200 from Gap 9)

---

### Task 5.3: Integration with existing components
**Complexity**: Medium
**Duration**: 2 hours
**Dependencies**: Task 5.2

**Actions**:
- Verify integration with Gap 8 (Concurrency Controller)
- Verify integration with Gap 9 (Cost Guardrails)
- Verify integration with Gap 10 (Caching)
- Test concurrent execution limits
- Test cost pause/resume
- Test cache hit benefits

**Acceptance Criteria**:
- Concurrency limits respected (from Gap 8)
- Cost limits enforced (from Gap 9)
- Cache hits reduce cost (from Gap 10)
- All integrations working

---

### Task 5.4: Write execution_v2_guide.md
**Complexity**: Low
**Duration**: 2 hours
**Dependencies**: Task 5.3

**Actions**:
- Create `DOCS/MGE_V2/execution_v2_guide.md`
- Document architecture and components
- Usage examples for all 3 components
- API endpoint documentation
- Metrics documentation
- Configuration options
- Troubleshooting guide

**Sections**:
1. Overview
2. Architecture
3. Components (RetryOrchestrator, WaveExecutor, ExecutionServiceV2)
4. Usage Examples
5. REST API Documentation
6. Metrics & Monitoring
7. Configuration
8. Performance Targets
9. Troubleshooting
10. Integration Points

**Acceptance Criteria**:
- Complete documentation (~600 lines)
- All components documented
- Examples provided
- Troubleshooting guide included

---

### Task 5.5: Write execution-v2-implementation-summary.md
**Complexity**: Low
**Duration**: 1 hour
**Dependencies**: Task 5.4

**Actions**:
- Create `DOCS/MGE_V2/execution-v2-implementation-summary.md`
- Technical implementation summary
- Files created/modified
- Code statistics
- Test coverage
- Performance results
- Success criteria checklist

**Sections**:
1. Overview
2. Implementation Details (by phase)
3. Files Created
4. Files Modified
5. Code Statistics
6. Test Coverage
7. Performance Results
8. Success Criteria Checklist
9. Known Limitations
10. Future Enhancements

**Acceptance Criteria**:
- Complete summary (~200 lines)
- All stats accurate
- Success criteria verified

---

### Task 5.6: Final validation and checklist
**Complexity**: Low
**Duration**: 1 hour
**Dependencies**: Task 5.5

**Actions**:
- Run all unit tests (70+ tests)
- Run all integration tests
- Verify Prometheus metrics
- Check performance benchmarks
- Validate against precision_readiness_checklist.md requirements
- Mark Week 2 Fri deadline complete

**Validation**:
- [x] RetryOrchestrator: 20+ tests passing
- [x] WaveExecutor: 25+ tests passing
- [x] ExecutionServiceV2: 15+ tests passing
- [x] API: 10+ tests passing
- [x] Integration: Full pipeline test passing
- [x] Precision: ≥95% achieved
- [x] Performance: 1-1.5 hours for 800 atoms
- [x] Cost: <$200 per masterplan
- [x] Prometheus metrics: All 15+ metrics emitting
- [x] Documentation: Complete

**Acceptance Criteria**:
- All validation checks pass
- Precision readiness checklist updated
- Implementation complete and production-ready

---

## Summary

**Total Tasks**: 28
**Total Phases**: 5
**Estimated Duration**: 5 days

### Phase Breakdown
- **Phase 1**: RetryOrchestrator (4 tasks, Day 1)
- **Phase 2**: WaveExecutor (5 tasks, Day 2)
- **Phase 3**: ExecutionServiceV2 (5 tasks, Day 3)
- **Phase 4**: REST API (5 tasks, Day 4)
- **Phase 5**: Integration & Docs (6 tasks, Day 5)

### Code Statistics (Estimated)
- **Source Code**: ~1,400 LOC
  - retry_orchestrator.py: ~300 LOC
  - wave_executor.py: ~350 LOC
  - execution_service_v2.py: ~400 LOC
  - execution_v2.py (API): ~150 LOC
  - metrics.py: ~200 LOC

- **Tests**: ~1,200 LOC
  - test_retry_orchestrator.py: ~300 LOC
  - test_wave_executor.py: ~350 LOC
  - test_execution_service_v2.py: ~300 LOC
  - test_execution_v2.py: ~250 LOC

- **Documentation**: ~800 lines
  - execution_v2_guide.md: ~600 lines
  - execution-v2-implementation-summary.md: ~200 lines

**Total Impact**: ~3,400 lines

### Success Metrics
- **Precision**: ≥95% (target from checklist)
- **Performance**: 1-1.5 hours for 800 atoms
- **Cost**: <$200 per masterplan (Gap 9 limit)
- **Retry Rate**: <20%
- **Success After Retry**: >95%

### Dependencies
- ✅ Phase 1-5 components (already implemented)
- ✅ Gap 8: Concurrency Controller
- ✅ Gap 9: Cost Guardrails
- ✅ Gap 10: Caching & Reuso
- ✅ EnhancedAnthropicClient
- ✅ AtomicValidator
