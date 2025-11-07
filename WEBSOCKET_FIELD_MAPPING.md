# MATRIZ DETALLADA: Campo BD → WebSocket → Frontend

Mapeo exhaustivo campo por campo de TODOS los datos sincronizados.

---

## DISCOVERY GENERATION WORKFLOW

### discovery_generation_start EVENT

```
BACKEND EMIT (masterplan_generator.py:445):
await ws_manager.emit_discovery_generation_start(
    session_id=session_id,
    estimated_tokens=8000,
    estimated_duration_seconds=30,
    estimated_cost_usd=0.09
)

EVENT PAYLOAD (websocket/manager.py:464-470):
{
  "session_id": "string",
  "estimated_tokens": 8000,
  "estimated_duration_seconds": 30,
  "estimated_cost_usd": 0.09
}

FRONTEND HANDLER (useMasterPlanProgress.ts:348-362):
case 'discovery_generation_start': {
  setProgressState((prev) => ({
    ...prev,
    currentPhase: 'Generating',
    startTime: new Date(),
    estimatedTotalTokens: eventData.estimated_tokens || 8000,  ← FROM WS
    estimatedDurationSeconds: eventData.estimated_duration_seconds || 30,  ← FROM WS
    cost: eventData.estimated_cost_usd || 0.09,  ← FROM WS
  }))
}

COMPONENT USAGE (MasterPlanProgressModal.tsx:283-286):
<ProgressMetrics
  tokensUsed={progressState.tokensReceived}  ← SYNCED ✓
  estimatedTokens={progressState.estimatedTotalTokens}  ← SYNCED ✓
  cost={progressState.cost}  ← SYNCED ✓
  duration={progressState.elapsedSeconds}  ← SYNCED ✓
  estimatedDuration={progressState.estimatedDurationSeconds}  ← SYNCED ✓
/>

MATCH: ✓ PERFECT (100%)
```

---

### discovery_tokens_progress EVENT

```
BACKEND EMIT (discovery_agent.py):
await ws_manager.emit_discovery_tokens_progress(
    session_id=session_id,
    tokens_received=tokens_received,
    estimated_total=estimated_total_tokens,
    current_phase=current_phase
)

EVENT PAYLOAD (websocket/manager.py:494-502):
{
  "session_id": "string",
  "tokens_received": 5000,
  "estimated_total": 8000,
  "percentage": 62,  ← CALCULATED BY WS
  "current_phase": "Entity extraction"
}

FRONTEND HANDLER (useMasterPlanProgress.ts:365-379):
case 'discovery_tokens_progress': {
  const tokensReceived = eventData.tokens_received || 0  ← FROM WS
  const estimatedTotal = eventData.estimated_total || 1  ← FROM WS
  const calculatedPercentage = Math.min((tokensReceived / estimatedTotal) * 100, 95)  ← RECALCULATED
  
  setProgressState((prev) => ({
    ...prev,
    tokensReceived,  ← SYNCED ✓
    estimatedTotalTokens: estimatedTotal,  ← SYNCED ✓
    percentage: Math.max(prev.percentage, calculatedPercentage),  ← SYNCED ✓
    elapsedSeconds: calculateElapsedSeconds(),
  }))
}

MATCH: ✓ PERFECT (100%)
```

---

### discovery_entity_discovered EVENT

```
BACKEND EMIT (discovery_agent.py):
await ws_manager.emit_discovery_entity_discovered(
    session_id=session_id,
    entity_type="bounded_context",
    count=3,
    name="Payment Context"
)

EVENT PAYLOAD (websocket/manager.py:520-533):
{
  "session_id": "string",
  "type": "bounded_context",  ← snake_case
  "count": 3,
  "name": "Payment Context"
}

FRONTEND HANDLER (useMasterPlanProgress.ts:381-407):
case 'discovery_entity_discovered': {
  const entityType = (eventData.entity_type || eventData.type)  ← TRIES entity_type FIRST
    ?.toLowerCase()
    ?.replace(/([a-z])([A-Z])/g, '$1_$2')  ← UNNECESSARY CONVERSION
    ?.toLowerCase() || 'entity'
  const count = eventData.count || 1  ← SYNCED ✓
  
  setProgressState((prev) => {
    if (entityType === 'domain') { ... }
    else if (entityType === 'bounded_context' || entityType === 'context') {
      return { ...prev, boundedContexts: Math.max(prev.boundedContexts, count) }  ← SYNCED ✓
    }
    else if (entityType === 'aggregate') {
      return { ...prev, aggregates: Math.max(prev.aggregates, count) }  ← SYNCED ✓
    }
    else if (entityType === 'entity') {
      return { ...prev, entities: Math.max(prev.entities, count) }  ← SYNCED ✓
    }
  })
}

DISCREPANCY: ⚠️ MINOR
- WS sends "type" but code looks for "entity_type" first (defensive)
- Regex conversion is unnecessary since WS already sends snake_case
- Logic is correct but inefficient
```

---

### discovery_parsing_complete EVENT

```
BACKEND EMIT (discovery_agent.py):
await ws_manager.emit_discovery_parsing_complete(
    session_id=session_id,
    domain="E-Commerce Platform",
    total_bounded_contexts=5,
    total_aggregates=12,
    total_entities=25
)

EVENT PAYLOAD (websocket/manager.py:556-563):
{
  "session_id": "string",
  "domain": "E-Commerce Platform",
  "total_bounded_contexts": 5,  ← SYNCED
  "total_aggregates": 12,  ← SYNCED
  "total_entities": 25  ← SYNCED
}

FRONTEND HANDLER (useMasterPlanProgress.ts:409-420):
case 'discovery_parsing_complete': {
  setProgressState((prev) => ({
    ...prev,
    currentPhase: 'Parsing Discovery',
    percentage: 15,
    boundedContexts: eventData.total_bounded_contexts || 0,  ← SYNCED ✓
    aggregates: eventData.total_aggregates || 0,  ← SYNCED ✓
    entities: eventData.total_entities || 0,  ← SYNCED ✓
    elapsedSeconds: calculateElapsedSeconds(),
  }))
}

MATCH: ✓ PERFECT (100%)
```

---

## MASTERPLAN GENERATION WORKFLOW

### masterplan_generation_start EVENT

```
BACKEND EMIT (masterplan_generator.py:318-324):
await ws_manager.emit_masterplan_generation_start(
    session_id=session_id,
    discovery_id=str(discovery_id),
    estimated_tokens=17000,
    estimated_duration_seconds=90,
    estimated_cost_usd=0.25
)

EVENT PAYLOAD (websocket/manager.py:252-266):
{
  "discovery_id": "UUID-string",  ← SENT BUT NOT USED
  "session_id": "string",
  "estimated_tokens": 17000,
  "estimated_duration_seconds": 90,
  "estimated_cost_usd": 0.25,
  "masterplan_id": null  ← OPTIONAL, NOT YET CREATED
}

FRONTEND HANDLER (useMasterPlanProgress.ts:218-230):
case 'masterplan_generation_start': {
  setProgressState((prev) => ({
    ...prev,
    currentPhase: 'MasterPlan Generation',
    percentage: Math.max(prev.percentage, 30),
    cost: eventData.estimated_cost_usd || eventData.estimated_cost || prev.cost,  ← SYNCED ✓
    estimatedDurationSeconds: eventData.estimated_duration_seconds || 600,  ← SYNCED ✓
    estimatedTotalTokens: eventData.estimated_tokens || prev.estimatedTotalTokens,  ← SYNCED ✓
    elapsedSeconds: calculateElapsedSeconds(),
  }))
}

DISCREPANCY: ⚠️ discovery_id SENT BUT NEVER PROCESSED
- Backend sends discovery_id
- Frontend ignores it
- Cannot correlate Discovery → MasterPlan completion
```

---

### masterplan_generation_complete EVENT

```
BACKEND EMIT (masterplan_generator.py:414-425):
await ws_manager.emit_masterplan_generation_complete(
    session_id=session_id,
    masterplan_id=str(masterplan_id),
    project_name=masterplan_data.get("project_name", "Unknown"),
    total_phases=len(phases),
    total_milestones=total_milestones,
    total_tasks=masterplan_data.get("total_tasks", 50),
    generation_cost_usd=masterplan_json.get("cost_usd", 0),
    duration_seconds=total_duration,
    estimated_total_cost_usd=masterplan_data.get("estimated_cost", 0),
    estimated_duration_minutes=masterplan_data.get("estimated_duration", 0)
)

DATABASE FIELDS NOT SENT (masterplan.py):
- llm_model (generated with MasterPlan, NOT synced)
- workspace_path (stored in DB, NOT synced)
- actual_cost_usd (stored in DB, NOT synced)
- actual_duration_minutes (stored in DB, NOT synced)
- tech_stack (stored in DB, NOT synced)
- complexity_metrics (stored in DB, NOT synced)

EVENT PAYLOAD (websocket/manager.py:427-439):
{
  "session_id": "string",
  "masterplan_id": "UUID-string",
  "project_name": "E-Commerce Platform",
  "total_phases": 3,  ← SYNCED
  "total_milestones": 12,  ← SYNCED
  "total_tasks": 120,  ← SYNCED
  "generation_cost_usd": 0.32,  ← SYNCED (but naming confusing)
  "duration_seconds": 45.2,  ← SYNCED (seconds, not minutes!)
  "estimated_total_cost_usd": 15.80,  ← SYNCED
  "estimated_duration_minutes": 45  ← SYNCED (minutes!)
}

FRONTEND HANDLER (useMasterPlanProgress.ts:328-346):
case 'masterplan_generation_complete': {
  setProgressState((prev) => ({
    ...prev,
    currentPhase: 'Complete',
    percentage: 100,
    isSaving: false,
    isComplete: true,
    elapsedSeconds: calculateElapsedSeconds(),
    phasesFound: eventData.total_phases || prev.phasesFound,  ← SYNCED ✓
    milestonesFound: eventData.total_milestones || prev.milestonesFound,  ← SYNCED ✓
    tasksFound: eventData.total_tasks || prev.tasksFound,  ← SYNCED ✓
  }))
}

CRITICAL ISSUES: ❌ 3
1. COST NOT UPDATED IN STATE - generation_cost_usd never copied to progressState.cost
2. UNIT MISMATCH - duration_seconds vs estimated_duration_minutes (seconds vs minutes!)
3. MISSING FIELDS - project_name not stored in progressState
```

---

## FIELD MAPPING SUMMARY TABLE

### PERFECTLY SYNCED FIELDS (90%)

| DB Field | WS Event | WS Field | Frontend State | Status |
|----------|----------|----------|----------------|--------|
| discovery_id | discovery_generation_complete | discovery_id | N/A (ignored) | ⚠️ Sent but unused |
| session_id | * all * | session_id | event.sessionId | ✓ Perfect |
| total_bounded_contexts | discovery_parsing_complete | total_bounded_contexts | boundedContexts | ✓ Perfect |
| total_aggregates | discovery_parsing_complete | total_aggregates | aggregates | ✓ Perfect |
| total_entities | discovery_parsing_complete | total_entities | entities | ✓ Perfect |
| tokens (progress) | *_tokens_progress | tokens_received | tokensReceived | ✓ Perfect |
| estimated tokens | *_generation_start | estimated_tokens | estimatedTotalTokens | ✓ Perfect |
| estimated duration | *_generation_start | estimated_duration_seconds | estimatedDurationSeconds | ✓ Perfect |
| estimated cost | *_generation_start | estimated_cost_usd | cost | ✓ Perfect |
| total_phases | masterplan_parsing_complete | total_phases | phasesFound | ✓ Perfect |
| total_milestones | masterplan_parsing_complete | total_milestones | milestonesFound | ✓ Perfect |
| total_tasks | masterplan_parsing_complete | total_tasks | tasksFound | ✓ Perfect |

### PROBLEMATICALLY SYNCED FIELDS (10%)

| DB Field | WS Event | Issue | Impact |
|----------|----------|-------|--------|
| llm_model | (NONE) | Not emitted in any event | Cannot display model used |
| generation_cost_usd | masterplan_generation_complete | Sent but not stored in progressState | Cost not shown at completion |
| actual_duration_minutes | masterplan_generation_complete | Sent as duration_seconds (unit mismatch) | Confusion between seconds/minutes |
| workspace_path | (NONE) | Never synced | Frontend cannot know execution path |
| validation_passed | (NONE) | Task validations never emitted | Cannot report validation status |
| task status | (NONE) | Individual task status never emitted | Only totals visible, not progress per task |
| complexity_metrics | (NONE) | Never synced | Frontend cannot show complexity breakdown |
| tech_stack | (NONE) | Never synced | Frontend cannot display stack info |

---

## SPECIFIC FIELD DISCREPANCIES

### 1. COST SYNC (CRITICAL)

**Database:**
```python
# MasterPlan model
estimated_cost_usd: Float          # Estimated cost
actual_cost_usd: Float = 0.0       # Actual cost after generation
generation_cost_usd: Float         # Cost to generate plan
```

**WebSocket Sent:**
```json
// masterplan_generation_complete
{
  "generation_cost_usd": 0.32,
  "estimated_total_cost_usd": 15.80
}
```

**Frontend Receives:**
```typescript
// useMasterPlanProgress.ts line 225
cost: eventData.estimated_cost_usd || eventData.estimated_cost || prev.cost

// But eventData in masterplan_generation_complete has:
// - generation_cost_usd (actual generation cost)
// - estimated_total_cost_usd (estimated project cost)
// - NOT estimated_cost_usd (this field doesn't exist!)

// RESULT: cost is NOT updated from generation_cost_usd
// progressState.cost remains from discovery phase
```

**Impact:** ❌ Final cost shown in modal is INCOMPLETE


### 2. DURATION SYNC (CONFUSING)

**Database:**
```python
estimated_duration_minutes: Integer  # Estimated execution time
actual_duration_minutes: Integer     # Actual execution time
```

**WebSocket Sent (discovery):**
```json
{
  "estimated_duration_seconds": 30,  // seconds!
  "duration_seconds": 28.5           // seconds!
}
```

**WebSocket Sent (masterplan):**
```json
{
  "estimated_duration_seconds": 90,  // seconds!
  "duration_seconds": 45.2,          // seconds!
  "estimated_duration_minutes": 45   // minutes! (INCONSISTENT!)
}
```

**Frontend Receives:**
```typescript
estimatedDurationSeconds: eventData.estimated_duration_seconds || 600
// Frontend does NOT convert to minutes
// So progressState has MIX of seconds and minutes

// ProgressMetrics.tsx uses:
// {Math.ceil(duration / 60)}min  // assumes duration is in seconds
// But some values are already in minutes!
```

**Impact:** ⚠️ Duration display may show wrong values


### 3. ENTITY TYPE NAMING (MINOR)

**Backend Sends:**
```python
entity_type="bounded_context"  # Parameter name
# But WS event uses:
"type": "bounded_context"  # JSON field name
```

**Frontend Expects:**
```typescript
const entityType = (eventData.entity_type || eventData.type)  // DEFENSIVE
  ?.toLowerCase()
  ?.replace(/([a-z])([A-Z])/g, '$1_$2')  // Unnecessary conversion
  ?.toLowerCase()

// Since WS already sends snake_case, the regex is pointless
// But code is defensive so it works anyway
```

**Impact:** ✓ Works but inefficient


### 4. MISSING DISCOVERY CONTEXT (CRITICAL)

**Should Be Synced:**
```json
// masterplan_generation_complete should include:
{
  "discovery_id": "...",
  "domain": "E-Commerce",
  "user_request": "Build a complete e-commerce platform"
}
```

**Actually Synced:**
```json
{
  "masterplan_id": "...",
  "project_name": "E-Commerce Platform",
  // discovery context lost!
}
```

**Frontend Impact:** ❌ Cannot correlate Discovery → MasterPlan in completion event


### 5. SUBTASK PROGRESS (NOT SYNCED)

**Database Has:**
```python
class MasterPlanSubtask(Base):
    task_id: UUID
    subtask_number: Integer
    name: String(300)
    status: Enum(TaskStatus)  # PENDING, IN_PROGRESS, COMPLETED, etc
    completed: Boolean
```

**WebSocket Emits:** (NONE)

**Frontend Displays:** (NOTHING)

**Impact:** ❌ Subtask progress completely invisible


### 6. TASK VALIDATION (NOT SYNCED)

**Database Has:**
```python
class MasterPlanTask(Base):
    validation_passed: Boolean
    validation_errors: JSON
    validation_logs: Text
    last_error: Text
```

**WebSocket Emits:** (NONE)

**Frontend Displays:** (NOTHING)

**Impact:** ❌ Validation results invisible during generation


---

## RECOMMENDATIONS

### HIGH PRIORITY (Fix immediately)

1. **Fix Cost Sync in masterplan_generation_complete**
   ```python
   # Add to frontend handler
   cost: eventData.generation_cost_usd || prev.cost
   ```

2. **Standardize Duration Units**
   ```python
   # Always use seconds in all events
   # Frontend converts to minutes for display
   "duration_seconds": 45.2,
   "estimated_duration_seconds": 90
   ```

3. **Add discovery_id to Completion Events**
   ```python
   # masterplan_generation_complete should include
   "discovery_id": str(discovery_id)
   ```

### MEDIUM PRIORITY (Add soon)

4. **Emit llm_model in Events**
   ```python
   "llm_model": "claude-sonnet-4.5"
   ```

5. **Emit Validation Status**
   ```python
   await ws_manager.emit_masterplan_validation_status(
       session_id, validation_passed, validation_errors
   )
   ```

6. **Emit Task Progress**
   ```python
   await ws_manager.emit_task_progress(
       session_id, task_number, status, validation_passed
   )
   ```

### LOW PRIORITY (Nice to have)

7. Emit workspace_path for execution routing
8. Emit complexity_metrics for analytics
9. Emit tech_stack for frontend display
10. Emit subtask progress for granular tracking

