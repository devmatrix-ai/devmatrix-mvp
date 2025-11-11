# MasterPlan Flow - Prioritized Issues & Action Plan
**Date:** 2025-11-04
**Analysis:** Complete E2E flow investigation results
**Status:** Production-ready generation, broken execution

---

## 🎯 Executive Summary

### Current State
- ✅ **Chat → Generation → Persistence**: 100% functional, production-ready
- ✅ **WebSocket real-time updates**: Working for generation phase
- ✅ **Review system**: 95% complete, needs integration
- ❌ **Execution**: MVP stub only, NOT executing real code
- ❌ **MGE V2 integration**: Isolated, 84/84 tests passing but not connected

### Critical Finding
**El sistema genera MasterPlans perfectamente pero NO los ejecuta.** La ejecución actual es un STUB que solo marca tareas como "completed" sin generar código.

---

## 🔥 Critical Issues (P0 - Must Fix)

### Issue #1: MasterPlan Execution is STUB
**Severity:** P0 - BLOCKER
**Component:** `src/services/masterplan_execution_service.py`
**Line:** 656

**Problem:**
```python
def _execute_single_task(self, task, masterplan_id) -> bool:
    """
    This is a stub implementation for Group 3. Full implementation with
    OrchestratorAgent integration will be completed in a future iteration.
    """
    # TODO: Integrate with OrchestratorAgent for actual execution
    # For now, mark task as completed (stub)
    task.status = TaskStatus.COMPLETED
    return True
```

**Impact:**
- MasterPlans are generated but NOT executed
- No code is actually created
- Tasks are falsely marked as "completed"
- User sees progress but gets no output

**Root Cause:**
- MGE V2 execution exists (WaveExecutor, RetryOrchestrator) but is NOT connected
- No adapter layer to convert MasterPlanTask → AtomicUnit
- Missing orchestration between old and new systems

**Fix Required:**
Create bridge service to connect MasterPlan to MGE V2:
```python
# NEW FILE: src/services/masterplan_execution_v2.py

class MasterplanExecutionV2Service:
    """Bridge between MasterPlan system and MGE V2 execution."""

    def __init__(self, db_session, wave_executor, retry_orchestrator):
        self.db = db_session
        self.wave_executor = wave_executor
        self.retry_orchestrator = retry_orchestrator
        self.adapter = MasterplanAdapter()

    async def execute(self, masterplan_id: UUID):
        # 1. Load masterplan
        masterplan = self._load_masterplan(masterplan_id)

        # 2. Convert tasks → atoms
        atoms = self.adapter.convert_tasks_to_atoms(masterplan.tasks)

        # 3. Build dependency graph
        dep_graph = self._build_dependency_graph(atoms)

        # 4. Create waves
        waves = self._create_waves(atoms, dep_graph)

        # 5. Execute with WaveExecutor
        for wave in waves:
            results = await self.wave_executor.execute_wave(wave)

            # 6. Update task status from atom results
            self._update_task_status(results)

            # 7. Check acceptance tests
            gate_passed = await self._check_gate(wave)
            if not gate_passed:
                break

            # 8. Trigger review for low-confidence
            await self._trigger_review(results)
```

**Estimated Effort:** 3-4 days
**Dependencies:** None
**Tests:**
- Integration test: MasterPlan → Atoms → Execution
- E2E test: Full flow from approval to code generation

---

### Issue #2: Missing MGE V2 Adapter Layer
**Severity:** P0 - BLOCKER
**Component:** Missing file
**Location:** `src/mge/v2/adapters/masterplan_adapter.py` (needs creation)

**Problem:**
No component exists to convert MasterPlan structure to MGE V2 AtomicUnits.

**Data Mismatch:**
```python
# MasterPlan structure:
MasterPlan
  └─ Phase (3)
      └─ Milestone (variable)
          └─ Task (120 total)
              └─ Subtask (3-7 per task)

# MGE V2 structure:
AtomicUnit
  ├─ unit_id
  ├─ code_content
  ├─ language
  ├─ dependencies (list of unit_ids)
  └─ validation_results
```

**Fix Required:**
```python
# NEW FILE: src/mge/v2/adapters/masterplan_adapter.py

class MasterplanAdapter:
    """Convert MasterPlan tasks to AtomicUnits for MGE V2 execution."""

    def convert_tasks_to_atoms(
        self,
        tasks: List[MasterPlanTask]
    ) -> List[AtomicUnit]:
        """
        Convert MasterPlan tasks to atomic units.

        Strategy:
        - Each subtask → 1 AtomicUnit
        - Task dependencies → atom dependencies
        - target_files → atom file paths
        - complexity → execution priority
        """
        atoms = []

        for task in tasks:
            for subtask in task.subtasks:
                atom = AtomicUnit(
                    unit_id=str(uuid.uuid4()),
                    name=f"{task.name} - {subtask.name}",
                    description=subtask.description,
                    language=self._detect_language(task.target_files),
                    file_path=task.target_files[0] if task.target_files else None,
                    dependencies=self._map_dependencies(task.depends_on_tasks),
                    complexity=task.complexity,
                    # Store reference to original task
                    metadata={
                        "task_id": str(task.task_id),
                        "subtask_id": str(subtask.subtask_id),
                        "task_number": task.task_number,
                        "subtask_number": subtask.subtask_number,
                    }
                )
                atoms.append(atom)

        return atoms

    def _detect_language(self, target_files: List[str]) -> str:
        """Detect language from file extensions."""
        if not target_files:
            return "python"  # default

        ext = Path(target_files[0]).suffix
        language_map = {
            ".py": "python",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
        }
        return language_map.get(ext, "python")

    def _map_dependencies(
        self,
        task_dependencies: List[str]
    ) -> List[str]:
        """Map task dependencies to atom dependencies."""
        # Task UUIDs → Atom UUIDs
        # Need to maintain mapping during conversion
        return self.task_to_atom_map.get(task_dependencies, [])
```

**Estimated Effort:** 2-3 days
**Dependencies:** Issue #1
**Tests:**
- Unit test: Task → Atom conversion correctness
- Integration test: Dependency mapping accuracy

---

### Issue #3: WebSocket Events Missing for Execution
**Severity:** P0 - CRITICAL
**Component:** `src/websocket/websocket_manager.py`

**Problem:**
Frontend has listeners for wave/atom execution events, but backend doesn't emit them.

**Missing Events:**
```python
# Generation events (✅ EXIST):
- discovery_start, discovery_progress, discovery_complete
- masterplan_generation_start, masterplan_tokens_progress, masterplan_generation_complete

# Execution events (❌ MISSING):
- wave_execution_start(wave_id, total_atoms)
- atom_execution_progress(atom_id, status, current, total)
- atom_execution_complete(atom_id, result)
- wave_execution_complete(wave_id, stats)
- acceptance_test_start(test_id)
- acceptance_test_result(test_id, passed)
- gate_validation_result(gate_passed, must_rate, should_rate)
- review_created(review_id, atom_id, confidence)
```

**Fix Required:**
```python
# MODIFY: src/websocket/websocket_manager.py

class WebSocketManager:
    # Add MGE V2 execution events

    async def emit_wave_execution_start(
        self,
        session_id: str,
        wave_id: str,
        wave_number: int,
        total_atoms: int
    ):
        await self.sio.emit(
            'wave_execution_start',
            {
                'wave_id': wave_id,
                'wave_number': wave_number,
                'total_atoms': total_atoms,
                'timestamp': datetime.utcnow().isoformat()
            },
            room=f"chat_{session_id}"
        )

    async def emit_atom_execution_progress(
        self,
        session_id: str,
        atom_id: str,
        status: str,
        current: int,
        total: int
    ):
        await self.sio.emit(
            'atom_execution_progress',
            {
                'atom_id': atom_id,
                'status': status,
                'current': current,
                'total': total,
                'progress_percent': (current / total * 100) if total > 0 else 0
            },
            room=f"chat_{session_id}"
        )

    # ... add remaining events ...
```

**Estimated Effort:** 1-2 days
**Dependencies:** Issue #1
**Tests:**
- Integration test: Verify events emitted during execution
- E2E test: Frontend receives events correctly

---

## ⚠️ High Priority Issues (P1 - Should Fix)

### Issue #4: Acceptance Tests Not Auto-Executed
**Severity:** P1
**Component:** `src/mge/v2/execution/wave_executor.py`

**Problem:**
Acceptance testing system is complete but not integrated into execution flow.

**What Exists:**
- ✅ `acceptance_gate.py` - Gate validation logic
- ✅ `test_generator.py` - Auto-generate tests from masterplan
- ✅ `test_runner.py` - Execute tests
- ✅ API endpoints - 8 endpoints for test management

**What's Missing:**
- ❌ Automatic test generation after masterplan approval
- ❌ Automatic test execution after wave completion
- ❌ Gate S validation before next wave
- ❌ Block execution if tests fail

**Fix Required:**
```python
# MODIFY: src/mge/v2/execution/wave_executor.py

class WaveExecutor:
    async def execute_wave(self, wave: ExecutionWave):
        # ... existing execution ...

        # NEW: After wave completion
        if self.config.enable_acceptance_tests:
            # 1. Run acceptance tests for this wave
            test_results = await self.test_runner.run_tests_for_wave(
                wave_id=wave.wave_id
            )

            # 2. Check Gate S
            gate_result = self.acceptance_gate.check_gate(
                test_results=test_results,
                require_must_100=True,
                require_should_95=True
            )

            # 3. Block if gate fails
            if not gate_result.passed:
                self.logger.error(
                    f"Wave {wave.wave_id} failed Gate S",
                    must_pass_rate=gate_result.must_pass_rate,
                    should_pass_rate=gate_result.should_pass_rate
                )
                raise GateFailedException(
                    f"Gate S failed: {gate_result.failure_reason}"
                )

            # 4. Emit WebSocket event
            await self.ws_manager.emit_gate_validation_result(
                session_id=wave.session_id,
                gate_result=gate_result
            )
```

**Estimated Effort:** 2-3 days
**Dependencies:** Issue #1
**Tests:**
- Integration test: Tests auto-execute after wave
- E2E test: Gate S blocks bad waves

---

### Issue #5: Review System Not Auto-Triggered
**Severity:** P1
**Component:** `src/mge/v2/execution/retry_orchestrator.py`

**Problem:**
Review system is 95% complete but requires manual creation of review entries.

**What Exists:**
- ✅ Confidence scoring (40% validation + 30% retries + 20% complexity + 10% integration)
- ✅ Review queue management
- ✅ AI suggestions generation
- ✅ Complete API (10 endpoints)
- ✅ React UI (ReviewQueue.tsx)

**What's Missing:**
- ❌ Automatic review creation for low-confidence atoms
- ❌ Integration with execution flow

**Fix Required:**
```python
# MODIFY: src/mge/v2/execution/retry_orchestrator.py

class RetryOrchestrator:
    async def execute_with_retry(
        self,
        atom: AtomicUnit,
        max_retries: int = 3
    ) -> ExecutionResult:
        # ... existing retry logic ...

        # NEW: After final execution
        # 1. Calculate confidence score
        confidence = self.confidence_scorer.calculate_confidence(
            atom=atom,
            validation_results=result.validation_results,
            retry_count=attempt,
            complexity=atom.complexity,
            integration_passed=result.integration_passed
        )

        # 2. Auto-create review if low confidence
        if confidence < 0.70:
            review = await self.review_service.create_review(
                atom_id=atom.atom_id,
                auto_add_suggestions=True,
                priority="high" if confidence < 0.50 else "medium",
                metadata={
                    "confidence_score": confidence,
                    "retry_count": attempt,
                    "validation_errors": result.validation_errors
                }
            )

            # 3. Emit WebSocket event
            await self.ws_manager.emit_review_created(
                session_id=atom.session_id,
                review_id=review.review_id,
                atom_id=atom.atom_id,
                confidence=confidence
            )

            self.logger.info(
                f"Review created for low-confidence atom",
                atom_id=atom.atom_id,
                confidence=confidence,
                review_id=review.review_id
            )
```

**Estimated Effort:** 1-2 days
**Dependencies:** Issue #1
**Tests:**
- Integration test: Review auto-created for confidence < 0.70
- E2E test: Review appears in UI

---

### Issue #6: Cost Guardrails Not Enforced
**Severity:** P1
**Component:** `src/mge/v2/execution/wave_executor.py`

**Problem:**
Cost guardrails exist but are not checked during execution.

**What Exists:**
- ✅ `cost_guardrails.py` - Soft/hard limit enforcement
- ✅ Default limits: $50 soft, $100 hard
- ✅ Per-masterplan custom limits

**What's Missing:**
- ❌ Pre-execution cost check
- ❌ Alert on soft limit approach
- ❌ Block execution at hard limit

**Fix Required:**
```python
# MODIFY: src/mge/v2/execution/wave_executor.py

class WaveExecutor:
    async def execute_wave(self, wave: ExecutionWave):
        # NEW: Before wave execution
        # 1. Check cost limits
        cost_status = self.cost_guardrails.check_before_execution(
            masterplan_id=wave.masterplan_id,
            estimated_cost=wave.estimated_cost
        )

        if cost_status.hard_limit_exceeded:
            raise CostLimitExceeded(
                f"Hard limit exceeded: ${cost_status.current_cost} / ${cost_status.hard_limit}"
            )

        if cost_status.soft_limit_exceeded:
            # Emit warning
            await self.ws_manager.emit_cost_warning(
                session_id=wave.session_id,
                current_cost=cost_status.current_cost,
                soft_limit=cost_status.soft_limit,
                remaining_budget=cost_status.remaining_budget
            )

        # ... existing execution ...

        # 2. Track actual cost after wave
        actual_cost = sum(atom.execution_cost for atom in wave.atoms)
        self.cost_guardrails.update_actual_cost(
            masterplan_id=wave.masterplan_id,
            additional_cost=actual_cost
        )
```

**Estimated Effort:** 1 day
**Dependencies:** Issue #1
**Tests:**
- Unit test: Cost limits enforced
- Integration test: Execution blocked at hard limit

---

## 📊 Medium Priority Issues (P2 - Nice to Have)

### Issue #7: Frontend Missing Wave/Atom Progress Display
**Severity:** P2
**Component:** `src/ui/src/components/chat/MasterPlanProgressModal.tsx`

**Problem:**
UI shows generation progress but not execution progress at wave/atom level.

**Fix Required:**
Add new section to progress modal:
```typescript
// ADD: WaveProgressSection component
<div className="wave-progress">
  <h3>Wave {currentWave}/{totalWaves}</h3>
  <ProgressBar value={waveProgress} />

  <div className="atom-list">
    {atoms.map(atom => (
      <AtomProgressItem
        key={atom.atom_id}
        atom={atom}
        status={atom.status}
      />
    ))}
  </div>

  <AcceptanceTestResults tests={acceptanceTests} />
</div>
```

**Estimated Effort:** 1-2 days
**Dependencies:** Issue #3

---

### Issue #8: Missing E2E Tracing
**Severity:** P2
**Component:** Multiple

**Problem:**
No unified trace ID connecting chat → discovery → generation → execution → review.

**Fix Required:**
Implement distributed tracing:
- Add trace_id to all database tables
- Propagate trace_id through all services
- Add to WebSocket events
- Create correlation dashboard

**Estimated Effort:** 3-4 days
**Dependencies:** None

---

## 📅 Implementation Roadmap

### Week 1: Core Execution (P0)
**Goal:** Make execution work

**Day 1-2:**
- ✅ Create `MasterplanExecutionV2Service`
- ✅ Create `MasterplanAdapter` (tasks → atoms)
- ✅ Add tests

**Day 3-4:**
- ✅ Integrate with `WaveExecutor`
- ✅ Update `/execute` endpoint
- ✅ Integration tests

**Day 5:**
- ✅ E2E test: Approval → Execution → Code generation
- ✅ Verify workspace files created

---

### Week 2: WebSocket & Testing (P0 + P1)
**Goal:** Real-time updates and quality gates

**Day 1-2:**
- ✅ Add WebSocket events to `WebSocketManager`
- ✅ Emit events from `WaveExecutor` and `RetryOrchestrator`
- ✅ Update frontend listeners

**Day 3-4:**
- ✅ Integrate acceptance tests with wave execution
- ✅ Implement Gate S validation
- ✅ Test gate blocking

**Day 5:**
- ✅ Frontend updates for wave/atom progress
- ✅ E2E test with UI

---

### Week 3: Review & Cost (P1)
**Goal:** Human review automation and cost control

**Day 1-2:**
- ✅ Auto-trigger review for low confidence
- ✅ Test review creation workflow
- ✅ Verify UI integration

**Day 3-4:**
- ✅ Implement cost guardrails in execution
- ✅ Add alerts and blocking
- ✅ Test cost limits

**Day 5:**
- ✅ Complete E2E testing
- ✅ Performance optimization
- ✅ Documentation updates

---

### Week 4: Polish & Deploy (P2)
**Goal:** Production readiness

**Day 1-2:**
- Frontend polish
- E2E tracing implementation
- Metrics dashboards

**Day 3-4:**
- Load testing
- Performance tuning
- Bug fixes

**Day 5:**
- Production deployment
- Monitoring setup
- User acceptance testing

---

## 🎯 Success Criteria

### Must Have (End of Week 2)
- [ ] MasterPlan execution generates real code (not stub)
- [ ] WebSocket events work for wave/atom progress
- [ ] Acceptance tests auto-execute after waves
- [ ] Gate S blocks bad waves
- [ ] E2E test passes: Chat → Code generation

### Should Have (End of Week 3)
- [ ] Review auto-created for confidence < 0.70
- [ ] Cost limits enforced
- [ ] UI shows wave/atom progress
- [ ] Complete documentation

### Nice to Have (End of Week 4)
- [ ] E2E tracing implemented
- [ ] Performance optimized
- [ ] Load tested
- [ ] Production deployed

---

## 📈 Metrics to Track

### Generation (Already Tracking)
- ✅ Discovery duration
- ✅ MasterPlan generation tokens
- ✅ Generation cost

### Execution (Need to Add)
- ❌ Wave execution duration
- ❌ Atom success rate
- ❌ Average retries per atom
- ❌ Acceptance test pass rate
- ❌ Review queue size
- ❌ Average confidence score
- ❌ Total execution cost per masterplan

---

## 🚨 Risk Assessment

### High Risk
- **Integration complexity:** Multiple systems to connect
  - Mitigation: Incremental integration with tests

- **Breaking changes:** Might affect existing generation flow
  - Mitigation: Feature flag for V2 execution

### Medium Risk
- **Performance:** Wave execution might be slow
  - Mitigation: Parallel execution, caching

- **Cost overruns:** LLM costs could exceed limits
  - Mitigation: Hard limits, monitoring

### Low Risk
- **UI updates:** Frontend changes are isolated
  - Mitigation: Component tests

---

## 📝 Summary

### What's Working
1. Chat → Discovery → MasterPlan generation: **Production-ready**
2. WebSocket real-time updates: **Working for generation**
3. Review system components: **95% complete**
4. Acceptance testing components: **100% complete**
5. MGE V2 execution: **100% complete (84/84 tests)**

### What's Broken
1. **MasterPlan execution is STUB** - P0 BLOCKER
2. **No MGE V2 integration** - P0 BLOCKER
3. **Missing WebSocket events** - P0 CRITICAL
4. **Tests not auto-executed** - P1
5. **Review not auto-triggered** - P1
6. **Cost not enforced** - P1

### Bottom Line
**Tenemos todos los componentes, pero están desconectados.** Necesitamos 2-3 semanas para crear el **orchestration layer** que los una y hacer que el sistema realmente ejecute código.

**Próximo paso inmediato:** Implementar `MasterplanExecutionV2Service` (Issue #1) en Week 1.
