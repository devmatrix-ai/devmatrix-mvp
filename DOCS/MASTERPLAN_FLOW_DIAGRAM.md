# MasterPlan Flow - Visual Diagram
**Date:** 2025-11-04

---

## 🎯 High-Level Flow (Simplified)

```
USER
  │
  │ "crear app FastAPI con auth JWT"
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│ FRONTEND: ChatWindow.tsx                                     │
│  ├─ Socket.IO connect                                        │
│  ├─ send_message(content)                                    │
│  └─ Listen: discovery_*, masterplan_*, message events        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ WEBSOCKET: Socket.IO Server (websocket.py)                   │
│  ├─ JWT auth validation                                      │
│  ├─ Event: send_message → ChatService                        │
│  └─ Emit: Real-time progress events                          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ CHAT SERVICE (chat_service.py)                               │
│  │                                                            │
│  ├─ Is command? (/masterplan, /orchestrate)                  │
│  │   ├─ YES → _execute_masterplan_generation()               │
│  │   │          │                                             │
│  │   │          ├─ PHASE 1: Discovery                        │
│  │   │          │   └─ DiscoveryAgent.conduct_discovery()    │
│  │   │          │                                             │
│  │   │          └─ PHASE 2: MasterPlan                       │
│  │   │              └─ MasterPlanGenerator.generate()        │
│  │   │                                                        │
│  │   └─ NO → Regular chat with Sonnet                        │
│  │                                                            │
│  └─ Save to: conversations + messages tables                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ MASTERPLAN GENERATOR (masterplan_generator.py)               │
│  │                                                            │
│  ├─ 1. Load Discovery from DB                                │
│  │                                                            │
│  ├─ 2. WebSocket: masterplan_generation_start                │
│  │                                                            │
│  ├─ 3. RAG: Retrieve 5 similar examples (ChromaDB)           │
│  │                                                            │
│  ├─ 4. LLM: Generate with Sonnet 4.5                         │
│  │    ├─ System: MASTERPLAN_SYSTEM_PROMPT (215 lines)        │
│  │    ├─ Context: Discovery + RAG examples                   │
│  │    ├─ Output: ~17K tokens JSON                            │
│  │    │   ├─ 3 phases (Setup/Core/Polish)                    │
│  │    │   ├─ 120 tasks                                       │
│  │    │   └─ 3-7 subtasks per task                           │
│  │    │                                                       │
│  │    └─ WebSocket: masterplan_tokens_progress (5s interval) │
│  │                                                            │
│  ├─ 5. Parse & Validate JSON                                 │
│  │                                                            │
│  ├─ 6. Save to Database (PostgreSQL)                         │
│  │    ├─ masterplans table                                   │
│  │    ├─ masterplan_phases (3)                               │
│  │    ├─ masterplan_milestones (per phase)                   │
│  │    ├─ masterplan_tasks (120)                              │
│  │    └─ masterplan_subtasks (per task)                      │
│  │                                                            │
│  └─ 7. WebSocket: masterplan_generation_complete             │
│       └─ Returns: masterplan_id                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ DATABASE: PostgreSQL (masterplan.py models)                  │
│  ├─ discovery_documents                                      │
│  ├─ masterplans (status: DRAFT)                              │
│  ├─ masterplan_phases                                        │
│  ├─ masterplan_milestones                                    │
│  ├─ masterplan_tasks (status: PENDING)                       │
│  ├─ masterplan_subtasks                                      │
│  ├─ masterplan_versions                                      │
│  └─ masterplan_history                                       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
         ┌─────────────────────────────────────┐
         │   USER REVIEWS MASTERPLAN IN UI     │
         │   ├─ GET /api/v1/masterplans/{id}   │
         │   └─ UI: MasterPlanDetailPage.tsx   │
         └─────────────┬───────────────────────┘
                       │
                       ├─ APPROVE ──────────────────┐
                       │                             │
                       └─ REJECT ───────────────┐   │
                                                 │   │
                                                 ▼   ▼
┌─────────────────────────────────────────────────────────────┐
│ MASTERPLAN API (masterplans.py)                              │
│  │                                                            │
│  ├─ POST /api/v1/masterplans/{id}/approve                    │
│  │   └─ Update: status → APPROVED                            │
│  │                                                            │
│  ├─ POST /api/v1/masterplans/{id}/reject                     │
│  │   └─ Update: status → REJECTED                            │
│  │                                                            │
│  └─ POST /api/v1/masterplans/{id}/execute                    │
│      ├─ Validate: status == APPROVED                         │
│      ├─ Create workspace                                     │
│      └─ Call: MasterplanExecutionService.execute()           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ ⚠️ EXECUTION SERVICE - MVP (STUB)                            │
│    masterplan_execution_service.py                           │
│  │                                                            │
│  ├─ 1. create_workspace()                                    │
│  │    └─ Save: workspace_path to masterplans table           │
│  │                                                            │
│  ├─ 2. execute(masterplan_id)                                │
│  │    ├─ Load: All tasks from DB                             │
│  │    ├─ Build: Dependency graph                             │
│  │    ├─ Sort: Topological order                             │
│  │    ├─ WebSocket: masterplan_execution_start               │
│  │    │                                                       │
│  │    └─ For each task:                                      │
│  │        ├─ WebSocket: task_execution_progress              │
│  │        ├─ _execute_single_task() → ⚠️ STUB!              │
│  │        │   ├─ TODO: Use OrchestratorAgent                 │
│  │        │   └─ For now: Just mark completed                │
│  │        ├─ Retry logic (1 retry max)                       │
│  │        └─ WebSocket: task_execution_complete              │
│  │                                                            │
│  └─ 3. Update: status → COMPLETED                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ ❌ MISSING CONNECTION
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ ❌ MGE V2 EXECUTION (NOT CONNECTED!)                         │
│    src/mge/v2/execution/                                     │
│  │                                                            │
│  ├─ WaveExecutor (100+ atoms parallel) ✅                    │
│  ├─ RetryOrchestrator (3 attempts, temp decay) ✅            │
│  ├─ ExecutionServiceV2 (state, progress, API) ✅             │
│  └─ Metrics (Prometheus) ✅                                  │
│  │                                                            │
│  │ ⚠️ 84/84 tests passing                                    │
│  │ ⚠️ But NOT integrated with MasterPlan execution!          │
│  │                                                            │
│  └─ Should connect here:                                     │
│      1. Convert MasterPlanTask → AtomicUnit                  │
│      2. Build dependency graph                               │
│      3. Create execution waves                               │
│      4. Execute with WaveExecutor                            │
│      5. Retry with RetryOrchestrator                         │
│      6. Validate with AcceptanceGate                         │
│      7. Update task status in DB                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ ❌ SHOULD AUTO-TRIGGER
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ ❌ ACCEPTANCE TESTS (NOT AUTO-EXECUTED!)                     │
│    src/testing/                                              │
│  │                                                            │
│  ├─ acceptance_gate.py (Gate S validation) ✅                │
│  ├─ test_generator.py (Auto-generate from plan) ✅           │
│  ├─ test_runner.py (Execute tests) ✅                        │
│  └─ API: /api/v2/testing/* (8 endpoints) ✅                  │
│  │                                                            │
│  │ ⚠️ Components exist but NOT auto-triggered                │
│  │                                                            │
│  └─ Should happen after wave execution:                      │
│      1. Generate acceptance tests from masterplan            │
│      2. Run tests after wave completion                      │
│      3. Check Gate S (100% must, ≥95% should)                │
│      4. Block next wave if gate fails                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ ❌ SHOULD AUTO-TRIGGER
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ ⚠️ REVIEW SYSTEM (NOT AUTO-TRIGGERED!)                      │
│    src/review/ + src/services/review_service.py              │
│  │                                                            │
│  ├─ confidence_scorer.py ✅                                  │
│  │   └─ 40% validation + 30% retries +                       │
│  │       20% complexity + 10% integration                    │
│  │                                                            │
│  ├─ queue_manager.py ✅                                      │
│  │   └─ Bottom 15-20% by confidence                          │
│  │                                                            │
│  ├─ ai_assistant.py ✅                                       │
│  │   └─ Generate AI suggestions                              │
│  │                                                            │
│  ├─ API: /api/v2/review/* (10 endpoints) ✅                  │
│  └─ UI: ReviewQueue.tsx ✅                                   │
│  │                                                            │
│  │ ⚠️ 95% complete but NOT auto-triggered                    │
│  │                                                            │
│  └─ Should happen after atom execution:                      │
│      1. Calculate confidence score                           │
│      2. If < 0.70 → create_review()                          │
│      3. Add AI suggestions                                   │
│      4. Human review workflow                                │
│      5. Approve/Edit/Regenerate                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔥 Critical Integration Points

### 1. MasterPlan → MGE V2 Execution
```python
# FILE: src/services/masterplan_execution_v2.py (NEW)

class MasterplanExecutionV2Service:
    """
    Bridge between MasterPlan (tasks) and MGE V2 (atoms).
    """

    def __init__(self, db_session, wave_executor, retry_orchestrator):
        self.db = db_session
        self.wave_executor = wave_executor
        self.retry_orchestrator = retry_orchestrator

    async def execute(self, masterplan_id: UUID):
        # 1. Load masterplan with all tasks
        masterplan = self._load_masterplan(masterplan_id)

        # 2. Convert MasterPlanTask → AtomicUnit
        atoms = self._convert_tasks_to_atoms(masterplan.tasks)

        # 3. Build dependency graph
        dep_graph = self._build_dependency_graph(atoms)

        # 4. Create execution waves
        waves = self._create_waves(atoms, dep_graph)

        # 5. Execute waves with WaveExecutor
        for wave in waves:
            results = await self.wave_executor.execute_wave(wave)

            # 6. Check acceptance tests after wave
            gate_result = await self._check_acceptance_gate(wave.wave_id)
            if not gate_result.passed:
                # Block next wave
                break

            # 7. Trigger review for low-confidence atoms
            await self._trigger_review_for_low_confidence(results)

        # 8. Update masterplan status
        self._update_masterplan_status(masterplan_id)
```

### 2. Wave Execution → Acceptance Tests
```python
# FILE: src/mge/v2/execution/wave_executor.py (MODIFY)

class WaveExecutor:
    async def execute_wave(self, wave: ExecutionWave):
        # ... existing execution logic ...

        # NEW: After wave completion
        if self.config.enable_acceptance_tests:
            test_results = await self._run_acceptance_tests(wave.wave_id)

            gate_passed = self.acceptance_gate.check_gate(
                test_results,
                require_must_100=True,
                require_should_95=True
            )

            if not gate_passed:
                raise GateFailedException(
                    f"Wave {wave.wave_id} failed Gate S"
                )
```

### 3. Atom Execution → Review Queue
```python
# FILE: src/mge/v2/execution/retry_orchestrator.py (MODIFY)

class RetryOrchestrator:
    async def execute_with_retry(self, atom: AtomicUnit):
        # ... existing retry logic ...

        # NEW: After final execution
        confidence = self._calculate_confidence(atom, result)

        if confidence < 0.70:
            # Auto-create review
            await self.review_service.create_review(
                atom_id=atom.atom_id,
                auto_add_suggestions=True,
                priority="high" if confidence < 0.50 else "medium"
            )
```

### 4. WebSocket Events for MGE V2
```python
# FILE: src/websocket/websocket_manager.py (ADD)

class WebSocketManager:
    # Existing: masterplan_generation_start/complete ✅
    # Existing: task_execution_progress/complete ✅

    # NEW: MGE V2 events
    async def emit_wave_execution_start(self, session_id, wave_id, total_atoms):
        ...

    async def emit_atom_execution_progress(self, session_id, atom_id, status):
        ...

    async def emit_atom_execution_complete(self, session_id, atom_id, result):
        ...

    async def emit_acceptance_test_result(self, session_id, test_id, passed):
        ...

    async def emit_gate_validation_result(self, session_id, gate_result):
        ...

    async def emit_review_created(self, session_id, review_id, atom_id):
        ...
```

---

## 📊 Data Flow Summary

### Generation Phase (✅ WORKING)
```
User Input
  → ChatService
  → DiscoveryAgent (emit: discovery_*)
  → MasterPlanGenerator (emit: masterplan_*)
  → PostgreSQL (masterplans, tasks)
  → WebSocket (generation_complete)
  → Frontend (MasterPlanProgressModal)
```

### Execution Phase (❌ BROKEN - STUB)
```
User Approval
  → POST /api/v1/masterplans/{id}/execute
  → MasterplanExecutionService (MVP STUB)
  → _execute_single_task() → Just marks completed ❌
  → Should be:
      → MasterplanExecutionV2Service (NEW)
      → Convert tasks → atoms
      → WaveExecutor.execute_wave()
      → RetryOrchestrator.execute_with_retry()
      → AcceptanceGate.check_gate()
      → ReviewService.create_review() (if low confidence)
```

### Review Phase (⚠️ MANUAL ONLY)
```
Low-confidence atom ❌ NOT AUTO-TRIGGERED
  → Should auto-create review
  → ReviewQueue.tsx
  → Human review (approve/reject/edit)
  → Update atom
```

---

## 🎯 Files to Create/Modify

### NEW Files (Create)
1. `src/services/masterplan_execution_v2.py`
   - Bridge between MasterPlan and MGE V2
   - Convert tasks → atoms
   - Orchestrate wave execution

2. `src/mge/v2/adapters/masterplan_adapter.py`
   - Convert MasterPlanTask → AtomicUnit
   - Map dependencies
   - Handle subtasks

### MODIFY Files
1. `src/mge/v2/execution/wave_executor.py`
   - Add acceptance test hook after wave
   - Emit new WebSocket events

2. `src/mge/v2/execution/retry_orchestrator.py`
   - Add review creation for low confidence
   - Emit atom execution events

3. `src/websocket/websocket_manager.py`
   - Add MGE V2 WebSocket events

4. `src/api/routers/masterplans.py`
   - Update /execute endpoint to use V2 service

5. `src/ui/src/components/chat/MasterPlanProgressModal.tsx`
   - Add listeners for wave/atom execution events

---

## 📈 Metrics to Track

### Current (Generation)
- ✅ Discovery duration
- ✅ MasterPlan generation tokens
- ✅ Total tasks generated
- ✅ Generation cost

### Missing (Execution)
- ❌ Wave execution progress
- ❌ Atom success/failure rate
- ❌ Retry attempts per atom
- ❌ Acceptance test pass rate
- ❌ Review queue size
- ❌ Average confidence score
- ❌ Execution cost per masterplan

---

## 🚀 Implementation Priority

### Week 1: Core Integration
1. Create `MasterplanExecutionV2Service`
2. Create `MasterplanAdapter` (tasks → atoms)
3. Connect to `WaveExecutor`
4. Update `/execute` endpoint

### Week 2: Acceptance Tests
1. Add hook in `WaveExecutor` after wave
2. Auto-generate tests from masterplan
3. Implement Gate S validation
4. Block progression on failure

### Week 3: Review System
1. Auto-trigger review for low confidence
2. Connect to execution flow
3. Test approve/reject/edit workflow

### Week 4: WebSocket & UI
1. Add MGE V2 WebSocket events
2. Update frontend components
3. Real-time progress tracking
4. E2E testing

---

**Bottom Line:** El flujo está **90% completo** pero con un **critical gap** en la ejecución. Necesitamos crear el **bridge layer** entre MasterPlan y MGE V2.
