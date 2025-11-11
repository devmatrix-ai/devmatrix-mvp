# Frontend Integration Tasks - MasterPlan Real-Time Updates

**Specification**: FRONTEND_INTEGRATION_SPEC.md
**Created**: November 4, 2025
**Status**: 🔴 CRITICAL - READY FOR IMPLEMENTATION
**Total Effort**: 19 hours (Days 1-3)

---

## Task Breakdown by Priority

### ✅ COMPLETED (Session 2)
- [x] **P0.1**: WebSocket null check exception → `src/websocket/manager.py` (1h)
- [x] **P0.2**: Enforce calculated task count ±15% → `src/services/masterplan_generator.py` (2h)

### 🔄 PENDING IMPLEMENTATION (Days 1-3)

---

## Phase 1: Core Hooks Implementation (Days 1-2, 18 hours)

### Task P0.3: Implement useWebSocket Hook
**Priority**: 🔴 CRITICAL
**Duration**: 4-6 hours
**Status**: NOT STARTED
**Effort**: 150-200 lines of TypeScript

#### Objective
Create foundational React hook for Socket.IO event subscription. This is the base layer that all other hooks depend on.

#### Input Requirements
- Access to socket.io-client singleton
- Knowledge of all 13 WebSocket event types (from src/websocket/manager.py)
- React hooks best practices (useEffect, useState)

#### Deliverables
**File to Create**: `src/ui/src/hooks/useWebSocket.ts`

**Exports**:
```typescript
export interface MasterPlanProgressEvent {
  type: EventType;           // 13 types
  data: Record<string, any>; // Event payload
  timestamp: number;         // Added by hook
}

export interface UseWebSocketResult {
  events: MasterPlanProgressEvent[];
  latestEvent: MasterPlanProgressEvent | null;
  isConnected: boolean;
  connectionError: string | null;
}

export const useWebSocket = (): UseWebSocketResult => {
  // Implementation
}
```

#### Implementation Checklist
- [ ] Import socket.io-client
- [ ] Create useState for events array, latestEvent, isConnected, connectionError
- [ ] Subscribe to all 13 event types in useEffect:
  - discovery_generation_start
  - discovery_tokens_progress
  - discovery_entity_discovered
  - discovery_parsing_complete
  - discovery_validation_start
  - discovery_saving_start
  - discovery_generation_complete
  - masterplan_generation_start
  - masterplan_tokens_progress
  - masterplan_entity_discovered
  - masterplan_parsing_complete
  - masterplan_validation_start
  - masterplan_saving_start
  - masterplan_generation_complete
- [ ] Implement circular buffer (max 100 events)
- [ ] Add timestamp to each event
- [ ] Handle connection errors
- [ ] Implement cleanup (socket.off on unmount)
- [ ] Add type safety with strict TypeScript
- [ ] Optimize re-renders (useCallback)

#### Acceptance Criteria
- ✅ All 13 event types subscribable
- ✅ Events stored in array with timestamps
- ✅ Latest event always available
- ✅ Connection status tracked
- ✅ Errors caught and reported
- ✅ Full cleanup on unmount (no memory leaks)
- ✅ Circular buffer prevents memory bloat
- ✅ TypeScript strict mode compliant

#### Testing
- [ ] Unit test: Verify subscriptions created
- [ ] Unit test: Verify event storage
- [ ] Unit test: Verify cleanup on unmount
- [ ] Unit test: Verify connection error handling
- [ ] Integration test: Real Socket.IO connection

#### Dependencies
- socket.io-client (already installed)
- React hooks (already available)

#### Block/Unblock
- **Blocks**: Task P0.4 (useMasterPlanProgress)
- **Blocks**: Task P0.5 (useMasterPlanStore)
- **Blocked by**: None (can start immediately)

---

### Task P0.4: Implement useMasterPlanProgress Hook
**Priority**: 🔴 CRITICAL
**Duration**: 8-10 hours
**Status**: NOT STARTED
**Effort**: 250-350 lines of TypeScript

#### Objective
Create state machine hook that interprets WebSocket events and manages generation progress, metrics, and error handling. This is the core business logic layer.

#### Input Requirements
- Output from Task P0.3 (useWebSocket hook)
- Understanding of state machines and async flows
- Knowledge of progress metrics (token counts, entity counts, ETA calculation)

#### Deliverables
**File to Create**: `src/ui/src/hooks/useMasterPlanProgress.ts`

**Exports**:
```typescript
export type ProgressState =
  | 'idle'
  | 'discovery_generating' | 'discovery_parsing' | 'discovery_validating'
  | 'discovery_saving' | 'discovery_complete'
  | 'masterplan_generating' | 'masterplan_parsing' | 'masterplan_validating'
  | 'masterplan_saving' | 'masterplan_complete'
  | 'error' | 'retrying';

export interface PhaseStatus {
  id: string;
  name: string;
  status: 'pending' | 'in_progress' | 'complete' | 'error';
  progress: number; // 0-100
  startTime?: number;
  endTime?: number;
}

export interface ProgressMetrics {
  tokensReceived: number;
  estimatedTotal: number;
  percentage: number; // 0-95 (conservative)
  entitiesDiscovered: Record<string, number>;
  estimatedCost: number;
  estimatedDuration: number; // seconds
  currentPhase: string;
}

export interface UseMasterPlanProgressResult {
  state: ProgressState;
  sessionId: string | null;
  phases: PhaseStatus[];
  metrics: ProgressMetrics;
  currentPhase: PhaseStatus | null;
  error: string | null;
  handleRetry: () => Promise<void>;
  clearError: () => void;
  isLoading: boolean;
}

export const useMasterPlanProgress = (
  sessionId?: string
): UseMasterPlanProgressResult => {
  // Implementation
}
```

#### Implementation Checklist
- [ ] Call useWebSocket() hook
- [ ] Create state: state, phases, metrics, error, retryCount
- [ ] Implement state machine transitions:
  - idle → masterplan_generating (on masterplan_generation_start)
  - masterplan_generating → masterplan_parsing (on masterplan_parsing_complete)
  - masterplan_parsing → masterplan_validating (on masterplan_validation_start)
  - masterplan_validating → masterplan_saving (on masterplan_saving_start)
  - masterplan_saving → masterplan_complete (on masterplan_generation_complete)
  - Any state → error (on error event)
- [ ] Parse metrics from events:
  - From masterplan_generation_start: estimatedCost, estimatedDuration
  - From masterplan_tokens_progress: tokensReceived, estimatedTotal, percentage
  - From masterplan_entity_discovered: Update entitiesDiscovered counts
- [ ] Calculate phases (5 phases total):
  - Phase 1: Token streaming (0-30%)
  - Phase 2: JSON parsing (30-50%)
  - Phase 3: Validation (50-75%)
  - Phase 4: Database saving (75-95%)
  - Phase 5: Completion (95-100%)
- [ ] Implement ETA calculation:
  - Track phase completion times
  - Calculate average seconds per phase
  - Estimate remaining time
- [ ] Implement error handling:
  - Catch error events
  - Store error message
  - Implement handleRetry() function
  - Implement clearError() function
- [ ] Implement percentage capping (max 95% until complete)
- [ ] Persist state to useMasterPlanStore after each update
- [ ] Debounce metrics updates (max 10 per second)

#### Acceptance Criteria
- ✅ State machine transitions correct for all 11 event types
- ✅ Metrics calculated accurately from event data
- ✅ Phases initialized with correct names
- ✅ Phase progress updates as state transitions
- ✅ ETA calculation produces realistic estimates
- ✅ Percentage capped at 95% until completion
- ✅ Error handling catches all error scenarios
- ✅ Retry functionality works
- ✅ State persisted to store
- ✅ No memory leaks on unmount

#### Testing
- [ ] Unit test: State transitions (11 test cases)
- [ ] Unit test: Metrics calculation (5 test cases)
- [ ] Unit test: Phase progress (3 test cases)
- [ ] Unit test: ETA calculation (2 test cases)
- [ ] Unit test: Error handling (3 test cases)
- [ ] Integration test: Complete event sequence
- [ ] Integration test: Error recovery

#### Dependencies
- Task P0.3 (useWebSocket hook) - MUST COMPLETE FIRST
- Task P0.5 (useMasterPlanStore) - Can run in parallel

#### Block/Unblock
- **Blocks**: Task P0.6 (MasterPlanProgressModal)
- **Blocked by**: Task P0.3 (useWebSocket)

---

### Task P0.5: Implement useMasterPlanStore (Zustand)
**Priority**: 🔴 CRITICAL
**Duration**: 6-8 hours
**Status**: NOT STARTED
**Effort**: 200-280 lines of TypeScript

#### Objective
Create centralized state management using Zustand. This allows state to be shared across components and persisted to browser storage.

#### Input Requirements
- Understanding of Zustand state management
- Knowledge of persistence patterns (IndexedDB)
- React hooks best practices

#### Deliverables
**File to Create**: `src/ui/src/stores/masterplanStore.ts`

**Exports**:
```typescript
export interface MasterPlanStoreState {
  // State
  currentMasterPlanId: string | null;
  generationProgress: ProgressState;
  phases: PhaseStatus[];
  currentPhase: PhaseStatus | null;
  metrics: ProgressMetrics;
  events: MasterPlanProgressEvent[];
  error: string | null;
  retryCount: number;

  // Actions
  setCurrentMasterPlan: (id: string) => void;
  updateProgress: (event: MasterPlanProgressEvent) => void;
  setPhases: (phases: PhaseStatus[]) => void;
  updateMetrics: (metrics: Partial<ProgressMetrics>) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
  incrementRetry: () => void;
  reset: () => void;

  // Persistence
  persist: () => Promise<void>;
  hydrate: () => Promise<void>;
}

export const useMasterPlanStore = create<MasterPlanStoreState>(
  persist(
    (set) => ({
      // Implementation
    }),
    { name: 'masterplan-store' }
  )
);
```

#### Implementation Checklist
- [ ] Create Zustand store with initial state
- [ ] Implement all 9 actions (setCurrentMasterPlan, updateProgress, etc.)
- [ ] Add Zustand persist middleware for IndexedDB
- [ ] Implement state hydration on app start
- [ ] Add derived state selectors for React optimization
- [ ] Calculate currentPhase from phases array
- [ ] Implement reset() function (clears all state)
- [ ] Add type-safe selectors:
  - `useMasterPlanStore(s => s.currentPhase)`
  - `useMasterPlanStore(s => s.error)`
- [ ] Handle large event arrays (limit stored events to 50)
- [ ] Add error recovery (validate state on hydration)

#### Acceptance Criteria
- ✅ All 9 actions working correctly
- ✅ State persisted to IndexedDB
- ✅ State restored on app reload
- ✅ Derived state (currentPhase) calculated correctly
- ✅ Selectors optimized for React rendering
- ✅ Reset clears all state
- ✅ No memory leaks
- ✅ TypeScript strict mode compliant

#### Testing
- [ ] Unit test: Initial state
- [ ] Unit test: All actions
- [ ] Unit test: Selectors
- [ ] Unit test: Persistence to IndexedDB
- [ ] Unit test: Hydration on startup
- [ ] Integration test: Store with hooks
- [ ] Integration test: Multiple components reading same state

#### Dependencies
- zustand (already installed)
- indexeddb (browser API, already available)

#### Block/Unblock
- **Blocks**: Task P0.6 (MasterPlanProgressModal)
- **Blocked by**: None (can start immediately)

---

### Task P0.6: Update MasterPlanProgressModal Component
**Priority**: 🔴 CRITICAL
**Duration**: 2-3 hours
**Status**: NOT STARTED
**Effort**: 30-50 lines modified

#### Objective
Connect all three hooks to the modal component, removing static props and enabling real-time updates.

#### Input Requirements
- Output from Tasks P0.3, P0.4, P0.5 (all hooks)
- Current modal implementation
- React component patterns

#### Deliverables
**File to Modify**: `src/ui/src/components/chat/MasterPlanProgressModal.tsx`

**Current Implementation** (BROKEN):
```typescript
<MasterPlanProgressModal
  event={event}                    // Static prop
  isOpen={isOpen}
  projectName={projectName}
/>
```

**Target Implementation** (FIXED):
```typescript
const MasterPlanProgressModal: React.FC<Props> = ({ isOpen, onClose }) => {
  const {
    state,
    phases,
    metrics,
    error,
    handleRetry,
    clearError,
    isLoading
  } = useMasterPlanProgress();

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      {state === 'error' ? (
        <ErrorPanel error={error} onRetry={handleRetry} onDismiss={clearError} />
      ) : state === 'masterplan_complete' ? (
        <SuccessPanel />
      ) : (
        <>
          <ProgressTimeline phases={phases} />
          <ProgressMetrics metrics={metrics} />
        </>
      )}
    </Modal>
  );
}
```

#### Implementation Checklist
- [ ] Remove static `event` prop from component
- [ ] Call useMasterPlanProgress() hook
- [ ] Destructure all returned values
- [ ] Conditional render based on state:
  - error → ErrorPanel
  - masterplan_complete → SuccessPanel
  - generating → ProgressTimeline + ProgressMetrics
- [ ] Pass hook functions to child components:
  - handleRetry to ErrorPanel
  - clearError to ErrorPanel on dismiss
- [ ] Auto-close modal or show success view on completion
- [ ] Update TypeScript types
- [ ] Remove old prop types

#### Acceptance Criteria
- ✅ Modal no longer uses static props
- ✅ Real-time updates visible
- ✅ Error panel displays when state === 'error'
- ✅ Success panel shows on completion
- ✅ Error can be cleared
- ✅ Retry button works
- ✅ Modal closes appropriately
- ✅ No TypeScript errors

#### Testing
- [ ] Component test: Renders with state
- [ ] Component test: Error panel shows
- [ ] Component test: Success panel shows
- [ ] Component test: Retry button functional
- [ ] Component test: Close button functional
- [ ] Integration test: Real hook integration

#### Dependencies
- Task P0.3 (useWebSocket hook)
- Task P0.4 (useMasterPlanProgress hook)
- Task P0.5 (useMasterPlanStore)

#### Block/Unblock
- **Blocks**: Task P0.7 (E2E testing)
- **Blocked by**: Tasks P0.3, P0.4, P0.5

---

### Task P0.7: Connect Hooks to Chat Service
**Priority**: 🔴 CRITICAL
**Duration**: 1-2 hours
**Status**: NOT STARTED
**Effort**: 10-15 lines modified

#### Objective
Ensure that when chat service generates MasterPlans, it passes the sessionId to the frontend for WebSocket subscription.

#### Input Requirements
- Current chat service implementation
- Understanding of sessionId generation
- How modal is triggered

#### Deliverables
**File to Modify**: `src/services/chat.ts` (or equivalent)

**Changes**:
```typescript
// Before: Just return result
const result = await chatService.generateMasterplan(discovery);

// After: Include sessionId for WebSocket subscription
const result = await chatService.generateMasterplan(discovery);
return {
  ...result,
  sessionId: sessionId,  // Pass to frontend
  event: 'masterplan_generation_start'
}

// In component that shows modal:
setMasterPlanSessionId(response.sessionId);
useMasterPlanProgress(sessionId);  // Pass to hook
```

#### Implementation Checklist
- [ ] Identify where /masterplan API is called
- [ ] Identify sessionId generation point
- [ ] Pass sessionId in response to frontend
- [ ] Store sessionId in component state
- [ ] Pass sessionId to useMasterPlanProgress hook
- [ ] Verify WebSocket connection uses sessionId

#### Acceptance Criteria
- ✅ sessionId passed from backend to frontend
- ✅ sessionId used to subscribe to WebSocket events
- ✅ Events routed to correct session
- ✅ No cross-session event leakage

#### Testing
- [ ] Integration test: sessionId flow
- [ ] Integration test: Multiple sessions isolated

#### Dependencies
- Task P0.6 (Modal component updated)

#### Block/Unblock
- **Blocks**: Task P0.8 (E2E testing)
- **Blocked by**: Task P0.6

---

### Task P0.8: End-to-End Testing (Playwright)
**Priority**: 🔴 CRITICAL
**Duration**: 3-4 hours
**Status**: NOT STARTED
**Effort**: 5 test scenarios, ~200 lines

#### Objective
Verify complete flow from chat command through real-time progress to completion using browser automation.

#### Input Requirements
- Output from Tasks P0.3-P0.7 (all implementation)
- Playwright testing experience
- DevMatrix test environment

#### Deliverables
**Files to Create/Modify**:
- `tests/e2e/masterplan-generation.spec.ts` (new)
- Update test fixtures if needed

**Test Scenarios**:

**E2E Test 1: Happy Path**
```typescript
// 1. User logs in
// 2. User types "/masterplan"
// 3. Modal appears with "Generating..."
// 4. Verify progress updates in real-time
//    - Percentage increases
//    - Phase timeline updates
//    - Metrics change
// 5. Modal closes on completion
// 6. Verify MasterPlan appears in sidebar
```

**E2E Test 2: Error Handling**
```typescript
// 1. Mock API to return error
// 2. Modal shows error message
// 3. User clicks retry button
// 4. Generation restarts
// 5. Modal closes on success
```

**E2E Test 3: WebSocket Disconnection**
```typescript
// 1. Start generation
// 2. Simulate network disconnection
// 3. Verify error message appears
// 4. User can retry or close modal
```

**E2E Test 4: Long Generation (timeout)**
```typescript
// 1. Start generation
// 2. Wait 5+ minutes
// 3. Verify progress still updating
// 4. Verify no timeout errors
```

**E2E Test 5: Concurrent Generations**
```typescript
// 1. Two users start /masterplan simultaneously
// 2. Both see their own progress
// 3. Events don't cross-contaminate
// 4. Both complete successfully
```

#### Implementation Checklist
- [ ] Create Playwright test file
- [ ] Set up test fixtures (login, etc.)
- [ ] Implement Test 1 (happy path)
- [ ] Implement Test 2 (error recovery)
- [ ] Implement Test 3 (disconnection)
- [ ] Implement Test 4 (timeout)
- [ ] Implement Test 5 (concurrency)
- [ ] Add assertions for progress updates
- [ ] Add assertions for modal UI state
- [ ] Add visual regression testing

#### Acceptance Criteria
- ✅ All 5 test scenarios pass
- ✅ Progress updates visible in real-time
- ✅ Error handling works
- ✅ Retry functionality works
- ✅ No flaky tests
- ✅ Tests run in < 10 minutes total

#### Testing
- [ ] Local test execution
- [ ] CI/CD pipeline execution
- [ ] Headless browser validation

#### Dependencies
- Tasks P0.3-P0.7 (all implementation)
- Playwright (already installed)

#### Block/Unblock
- **Blocks**: Deployment to staging
- **Blocked by**: Tasks P0.3-P0.7

---

## Phase 2: Backend Retry Logic (Days 3-4, 8 hours)

### Task P1.1: Implement Retry Decorator
**Priority**: 🟡 HIGH
**Duration**: 2-3 hours
**Status**: NOT STARTED
**Effort**: 50-70 lines

#### Objective
Create reusable Python decorator for retrying failed LLM calls with exponential backoff.

#### Deliverables
**File to Create**: `src/utils/retry.py`

**Interface**:
```python
from typing import Callable, TypeVar, Any
from functools import wraps
import asyncio

T = TypeVar('T')

def retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Decorator for retrying async functions with exponential backoff.

    Usage:
        @retry(max_attempts=3, backoff_factor=2)
        async def generate_masterplan():
            ...
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        raise
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed: {str(e)}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    delay *= backoff_factor
        return wrapper
    return decorator
```

#### Implementation Checklist
- [ ] Create retry.py with decorator
- [ ] Implement exponential backoff logic
- [ ] Support max_attempts configuration
- [ ] Support backoff_factor configuration
- [ ] Support custom exception types
- [ ] Add logging for each retry
- [ ] Handle async functions
- [ ] Add type hints

#### Acceptance Criteria
- ✅ Decorator works with async functions
- ✅ Exponential backoff calculated correctly
- ✅ Max attempts respected
- ✅ Logging shows retry attempts
- ✅ Final exception re-raised if all attempts fail
- ✅ Type hints complete

#### Testing
- [ ] Unit test: Successful retry
- [ ] Unit test: Max attempts exceeded
- [ ] Unit test: Exponential backoff timing

#### Dependencies
- None

#### Block/Unblock
- **Blocks**: Task P1.2 (Apply decorator)
- **Blocked by**: None

---

### Task P1.2: Apply Retry Logic to MasterPlanGenerator
**Priority**: 🟡 HIGH
**Duration**: 1-2 hours
**Status**: NOT STARTED
**Effort**: 5-10 lines modified

#### Objective
Apply retry decorator to discovery and MasterPlan generation methods.

#### Deliverables
**File to Modify**: `src/services/masterplan_generator.py`

**Changes**:
```python
from src.utils.retry import retry

class MasterPlanGenerator:
    @retry(max_attempts=3, backoff_factor=2)
    async def _generate_discovery(self, ...):
        # Existing code
        pass

    @retry(max_attempts=3, backoff_factor=2)
    async def _generate_masterplan_llm_with_progress(self, ...):
        # Existing code
        pass
```

#### Implementation Checklist
- [ ] Import retry decorator
- [ ] Add @retry to _generate_discovery
- [ ] Add @retry to _generate_masterplan_llm_with_progress
- [ ] Set max_attempts=3, backoff_factor=2
- [ ] Verify retry logic doesn't conflict with WebSocket emissions

#### Acceptance Criteria
- ✅ Decorator applied to both methods
- ✅ Retries happen transparently
- ✅ WebSocket events emitted on final attempt only
- ✅ Logging shows retry attempts

#### Testing
- [ ] Unit test: Retry on LLM failure
- [ ] Integration test: Full retry flow

#### Dependencies
- Task P1.1 (Retry decorator)

#### Block/Unblock
- **Blocks**: None
- **Blocked by**: Task P1.1

---

### Task P1.3: Implement Discovery Orphan Cleanup
**Priority**: 🟡 HIGH
**Duration**: 3-4 hours
**Status**: NOT STARTED
**Effort**: 100-150 lines

#### Objective
Create scheduled job that finds and removes orphaned Discovery documents (those with no linked MasterPlan).

#### Deliverables
**Files to Create**:
- `src/jobs/cleanup_orphaned_discoveries.py` (new)
- Update `src/main.py` to register scheduled job

**Job Interface**:
```python
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from src.models import Discovery, MasterPlan

async def cleanup_orphaned_discoveries(db: Session):
    """
    Find discoveries with no linked MasterPlan and delete them.
    Runs daily at 2 AM.
    """
    orphaned = db.query(Discovery).filter(
        ~Discovery.masterplans.any()
    ).all()

    count = len(orphaned)
    for discovery in orphaned:
        logger.warning(f"Deleting orphaned discovery: {discovery.discovery_id}")
        db.delete(discovery)

    db.commit()
    logger.info(f"Cleanup complete: deleted {count} orphaned discoveries")

# Register with APScheduler
scheduler.add_job(
    cleanup_orphaned_discoveries,
    'cron',
    hour=2,
    minute=0,
    kwargs={'db': get_db_context()}
)
```

#### Implementation Checklist
- [ ] Create cleanup_orphaned_discoveries.py
- [ ] Query discoveries with no masterplans
- [ ] Implement deletion logic
- [ ] Add logging for auditing
- [ ] Register with APScheduler (daily 2 AM)
- [ ] Add configuration option to disable
- [ ] Handle database transaction safety

#### Acceptance Criteria
- ✅ Finds all orphaned discoveries
- ✅ Deletes them safely
- ✅ Logs all deletions for audit trail
- ✅ Runs on schedule (daily 2 AM)
- ✅ No false positives
- ✅ Database transaction safe

#### Testing
- [ ] Unit test: Create orphaned discovery, verify cleanup finds it
- [ ] Unit test: Don't delete discoveries with masterplans
- [ ] Integration test: Full cleanup cycle

#### Dependencies
- APScheduler (already installed)
- SQLAlchemy ORM (already in use)

#### Block/Unblock
- **Blocks**: None
- **Blocked by**: None

---

### Task P1.4: Create Status Recovery Endpoint
**Priority**: 🟡 HIGH
**Duration**: 2-3 hours
**Status**: NOT STARTED
**Effort**: 40-60 lines

#### Objective
Create API endpoint to check MasterPlan generation status, enabling recovery if WebSocket disconnects.

#### Deliverables
**File to Modify**: `src/api/routers/masterplans.py`

**Endpoint**:
```python
from fastapi import APIRouter, HTTPException
from src.models import MasterPlan

router = APIRouter(prefix="/masterplans", tags=["masterplans"])

@router.get("/{masterplan_id}/status")
async def get_masterplan_status(
    masterplan_id: str,
    db: Session = Depends(get_db)
):
    """
    Get current generation status of a MasterPlan.

    Used for WebSocket recovery when connection is interrupted.
    Allows frontend to know if generation completed while offline.
    """
    masterplan = db.query(MasterPlan).filter(
        MasterPlan.masterplan_id == masterplan_id
    ).first()

    if not masterplan:
        raise HTTPException(status_code=404, detail="MasterPlan not found")

    return {
        "masterplan_id": masterplan.masterplan_id,
        "status": masterplan.status,  # draft, approved, rejected, in_progress, complete
        "created_at": masterplan.created_at,
        "completed_at": masterplan.completed_at,
        "total_tasks": len(masterplan.tasks),
        "completed_tasks": sum(1 for t in masterplan.tasks if t.status == 'complete'),
        "error": masterplan.error_message if masterplan.status == 'error' else None
    }
```

#### Implementation Checklist
- [ ] Create GET /masterplans/{masterplan_id}/status endpoint
- [ ] Return current status
- [ ] Return task completion counts
- [ ] Return error message if applicable
- [ ] Add proper error handling (404 if not found)
- [ ] Add authentication if needed
- [ ] Update API documentation

#### Acceptance Criteria
- ✅ Endpoint returns correct status
- ✅ 404 for non-existent masterplans
- ✅ Includes all necessary status information
- ✅ Allows frontend to recover state
- ✅ Works even if WebSocket was disconnected

#### Testing
- [ ] Unit test: Status endpoint with draft masterplan
- [ ] Unit test: Status endpoint with complete masterplan
- [ ] Unit test: 404 for non-existent masterplan
- [ ] Integration test: Recovery flow

#### Dependencies
- None (uses existing MasterPlan model)

#### Block/Unblock
- **Blocks**: None
- **Blocked by**: None

---

## Phase 3: Final Validation (Day 5, 3 hours)

### Task P0.9: Comprehensive Testing & Validation
**Priority**: 🔴 CRITICAL
**Duration**: 3-4 hours
**Status**: NOT STARTED
**Effort**: Integration of all tests

#### Objective
Run all unit, integration, and E2E tests. Verify complete system working end-to-end.

#### Test Suite
- [ ] All 20+ unit tests passing
- [ ] All 10+ integration tests passing
- [ ] All 5 E2E tests passing
- [ ] No TypeScript compilation errors
- [ ] No console warnings or errors
- [ ] Test coverage > 90%

#### Performance Validation
- [ ] Hook initialization < 50ms
- [ ] Event processing < 10ms
- [ ] Modal render < 100ms
- [ ] Real-time update lag < 500ms

#### Accessibility Validation
- [ ] WCAG AA compliance
- [ ] Keyboard navigation working
- [ ] Screen reader compatible

#### Documentation
- [ ] All types documented
- [ ] All functions have JSDoc
- [ ] Architecture documented
- [ ] Deployment guide created

#### Acceptance Criteria
- ✅ All tests passing
- ✅ No TypeScript errors
- ✅ Performance baselines met
- ✅ Accessibility verified
- ✅ Ready for production

---

## Summary by Day

### Day 1 (Monday): Core Hooks Part 1
- [ ] Task P0.3: useWebSocket (4-6h)
- [ ] Task P0.5: useMasterPlanStore (6-8h)
- **Total**: 10-14 hours → Next day: P0.4

### Day 2 (Tuesday): Core Hooks Part 2 & Component Integration
- [ ] Task P0.4: useMasterPlanProgress (8-10h)
- [ ] Task P0.6: MasterPlanProgressModal (2-3h)
- [ ] Task P0.7: Chat Service Integration (1-2h)
- **Total**: 11-15 hours → Next day: Testing

### Day 3 (Wednesday): Backend & E2E Testing
- [ ] Task P0.8: E2E Testing (3-4h)
- [ ] Task P1.1: Retry Decorator (2-3h)
- [ ] Task P1.2: Apply Retry Logic (1-2h)
- **Total**: 6-9 hours → Next day: Cleanup

### Day 4 (Thursday): Cleanup & Recovery
- [ ] Task P1.3: Discovery Orphan Cleanup (3-4h)
- [ ] Task P1.4: Status Recovery Endpoint (2-3h)
- **Total**: 5-7 hours → Next day: Validation

### Day 5 (Friday): Final Validation
- [ ] Task P0.9: Comprehensive Testing (3-4h)
- [ ] Deploy to staging
- [ ] Monitor for issues

---

## Completed vs Remaining

### ✅ Already Done (Session 2)
1. WebSocket null check exception (1h) - `src/websocket/manager.py`
2. Task count enforcement ±15% (2h) - `src/services/masterplan_generator.py`

### 🔄 Remaining (Days 1-5)
1. useWebSocket hook (4-6h)
2. useMasterPlanProgress hook (8-10h)
3. useMasterPlanStore (6-8h)
4. MasterPlanProgressModal (2-3h)
5. Chat Service Integration (1-2h)
6. E2E Testing (3-4h)
7. Retry Decorator (2-3h)
8. Apply Retry Logic (1-2h)
9. Discovery Cleanup (3-4h)
10. Status Recovery Endpoint (2-3h)
11. Final Validation (3-4h)

**Total Remaining**: 35-46 hours (5-6 days full-time)

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Real-time updates | 0% | 100% |
| WebSocket event handling | 0% | 100% |
| Task count enforcement | 0% | 100% |
| Test coverage | 60% | 90% |
| System reliability | 70% | 99% |

---

**Status**: ✅ Ready to start implementation
**Next Action**: Begin Task P0.3 (useWebSocket hook)
