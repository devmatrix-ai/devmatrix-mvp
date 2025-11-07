# WebSocket Sync - Fixes Requeridos

Basado en auditoría del 6 Nov 2025.

## Fix #1: COST NOT SYNCED (CRITICAL)

**Archivo:** `src/ui/src/hooks/useMasterPlanProgress.ts`  
**Línea:** ~225  
**Severidad:** CRITICAL

### Problema
```typescript
// ACTUAL (INCORRECTO)
case 'masterplan_generation_start': {
  setProgressState((prev) => ({
    ...prev,
    cost: eventData.estimated_cost_usd || eventData.estimated_cost || prev.cost,
                    ↑ Este campo NO existe en masterplan_generation_complete
```

En `masterplan_generation_complete`, el backend envía:
- `generation_cost_usd`: Costo real de generar el MasterPlan
- `estimated_total_cost_usd`: Costo estimado del proyecto completo
- NO envía `estimated_cost_usd`

### Solución

```typescript
// Fix: Aceptar generation_cost_usd
case 'masterplan_generation_complete': {
  setProgressState((prev) => ({
    ...prev,
    currentPhase: 'Complete',
    percentage: 100,
    isSaving: false,
    isComplete: true,
    elapsedSeconds: calculateElapsedSeconds(),
    phasesFound: eventData.total_phases || prev.phasesFound,
    milestonesFound: eventData.total_milestones || prev.milestonesFound,
    tasksFound: eventData.total_tasks || prev.tasksFound,
    
    // FIX: Add cost update
    cost: eventData.generation_cost_usd || eventData.estimated_total_cost_usd || prev.cost,
  }))
  break
}
```

---

## Fix #2: DISCOVERY_ID NOT STORED (MINOR)

**Archivo:** `src/ui/src/hooks/useMasterPlanProgress.ts`  
**Línea:** ~218  
**Severidad:** MINOR

### Problema
```typescript
case 'masterplan_generation_start': {
  // discovery_id is sent but never stored
  const discovery_id = eventData.discovery_id  // ← enviado pero nunca usado
  setProgressState((prev) => ({
    // discovery_id se pierde aquí
  }))
}
```

### Solución

**Paso 1:** Extender `ProgressState` type

```typescript
// Define en useMasterPlanProgress.ts o en types/masterplan.ts
interface ProgressState {
  // ... existing fields
  discoveryId?: string  // Add this
  masterplanId?: string // Add this
}

const initialProgressState: ProgressState = {
  // ... existing
  discoveryId: undefined,
  masterplanId: undefined,
}
```

**Paso 2:** Guardar en eventos

```typescript
case 'masterplan_generation_start': {
  setProgressState((prev) => ({
    ...prev,
    discoveryId: eventData.discovery_id || prev.discoveryId,  // SAVE IT
    masterplanId: eventData.masterplan_id || prev.masterplanId,
    currentPhase: 'MasterPlan Generation',
    // ... rest
  }))
}

case 'masterplan_generation_complete': {
  setProgressState((prev) => ({
    ...prev,
    masterplanId: eventData.masterplan_id || prev.masterplanId,  // SAVE IT
    // ... rest
  }))
}
```

---

## Fix #3: DURATION UNITS STANDARDIZATION (MINOR)

**Archivos:**
- `src/websocket/manager.py` (backend)
- `src/ui/src/hooks/useMasterPlanProgress.ts` (frontend)

**Severidad:** MINOR

### Problema

Backend envía duraciones en diferentes unidades:
```python
# Discovery
"estimated_duration_seconds": 30,  # SEGUNDOS
"duration_seconds": 28.5           # SEGUNDOS

# MasterPlan  
"estimated_duration_seconds": 90,  # SEGUNDOS
"duration_seconds": 45.2,          # SEGUNDOS
"estimated_duration_minutes": 45   # MINUTOS ← INCONSISTENTE!
```

### Solución

**Backend Fix:** `src/websocket/manager.py`

```python
async def emit_masterplan_generation_complete(
    self,
    session_id: str,
    masterplan_id: str,
    project_name: str,
    total_phases: int,
    total_milestones: int,
    total_tasks: int,
    generation_cost_usd: float,
    duration_seconds: float,
    estimated_total_cost_usd: float,
    estimated_duration_minutes: int  # ← PROBLEMA: unidad diferente
):
    # SOLUCIÓN: Convertir a segundos ANTES de enviar
    estimated_duration_seconds = estimated_duration_minutes * 60  # Convert!
    
    await self.emit_to_session(
        session_id=session_id,
        event="masterplan_generation_complete",
        data={
            "session_id": session_id,
            "masterplan_id": masterplan_id,
            "project_name": project_name,
            "total_phases": total_phases,
            "total_milestones": total_milestones,
            "total_tasks": total_tasks,
            "generation_cost_usd": generation_cost_usd,
            "duration_seconds": duration_seconds,
            "estimated_total_cost_usd": estimated_total_cost_usd,
            "estimated_duration_seconds": estimated_duration_seconds,  # FIXED!
        }
    )
```

**Frontend:** No cambios necesarios si backend envía segundos consistentemente

---

## Fix #4: ADD LLM_MODEL TO EVENTS (FUTURE)

**Archivos:**
- `src/websocket/manager.py` (add new method)
- `src/ui/src/hooks/useMasterPlanProgress.ts` (handle event)

**Severidad:** LOW (feature enhancement)

### Solución

**Backend:** Add event method
```python
async def emit_generation_info(
    self,
    session_id: str,
    llm_model: str,
    generation_cost_usd: float,
    generation_tokens: int
):
    """Emit LLM generation info after MasterPlan completes."""
    await self.emit_to_session(
        session_id=session_id,
        event="generation_info",
        data={
            "session_id": session_id,
            "llm_model": llm_model,
            "generation_cost_usd": generation_cost_usd,
            "generation_tokens": generation_tokens,
        }
    )
```

**Backend:** Call in masterplan_generator.py
```python
if self.ws_manager:
    await self.ws_manager.emit_generation_info(
        session_id=session_id,
        llm_model=masterplan_json.get("model", "unknown"),
        generation_cost_usd=masterplan_json.get("cost_usd", 0),
        generation_tokens=masterplan_json.get("tokens_used", 0),
    )
```

**Frontend:** Handle in useMasterPlanProgress.ts
```typescript
export interface ProgressState {
  // ... existing
  llmModel?: string
  generationTokens?: number
}

// Add handler
case 'generation_info': {
  setProgressState((prev) => ({
    ...prev,
    llmModel: eventData.llm_model,
    generationTokens: eventData.generation_tokens,
  }))
  break
}
```

---

## Testing Changes

### Unit Test for Cost Sync

```typescript
// src/ui/src/hooks/__tests__/useMasterPlanProgress.test.ts

test('should update cost on masterplan_generation_complete', () => {
  const { result } = renderHook(() => useMasterPlanProgress('session-123'), {
    wrapper: WebSocketProvider,
  })

  // Simulate event
  const event = {
    type: 'masterplan_generation_complete',
    data: {
      session_id: 'session-123',
      generation_cost_usd: 0.32,  // Main cost to test
      total_phases: 3,
      total_milestones: 12,
      total_tasks: 120,
    },
    timestamp: Date.now(),
  }

  // Trigger event processing
  // This would normally come from WebSocket
  
  // Assert: cost should be updated
  expect(result.current.state.cost).toBe(0.32)
})
```

### Integration Test for WebSocket Events

```python
# tests/test_websocket_events.py

def test_masterplan_generation_complete_sends_all_fields():
    """Verify all required fields are sent in completion event."""
    manager = WebSocketManager(sio_server)
    
    # Call the method
    await manager.emit_masterplan_generation_complete(
        session_id="test-session",
        masterplan_id="test-mp-123",
        project_name="E-Commerce",
        total_phases=3,
        total_milestones=12,
        total_tasks=120,
        generation_cost_usd=0.32,
        duration_seconds=45.2,
        estimated_total_cost_usd=15.80,
        estimated_duration_minutes=45,
    )
    
    # Assert: event was emitted with correct fields
    # (Mock sio_server to capture emit calls)
```

---

## Deployment Checklist

- [ ] Fix #1: Cost sync in `useMasterPlanProgress.ts`
- [ ] Fix #2: Store discovery_id and masterplan_id
- [ ] Fix #3: Standardize duration units in backend
- [ ] Add tests for cost sync
- [ ] Test modal displays correct costs
- [ ] Verify no regression in other fields

---

## Estimated Effort

| Fix | Effort | Time |
|-----|--------|------|
| #1: Cost sync | Trivial | 5 min |
| #2: discovery_id | Small | 15 min |
| #3: Duration units | Small | 20 min |
| Tests | Small | 30 min |
| Total | --- | ~70 min |

