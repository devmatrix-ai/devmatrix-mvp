# Week 1 Implementation Guide - E2E Test & Quick Fixes

**Dates:** Nov 11-15, 2025
**Owner:** Dany
**Focus:** E2E Test Extension + FileWriter JS/TS + Execution API

---

## Day 1 (Monday, Nov 11) - 6 hours

### Morning: E2E Test Phase 5 (3 hours)

**Task:** Implement Wave Execution phase in E2E test

**Steps:**
1. Open `tests/e2e/test_mge_v2_complete_pipeline.py`
2. Navigate to line 457 (after atomization phase)
3. Add wave execution matcher/extractor (see [spec](../../03-mge-v2/specs/e2e-test-extension.md#phase-5-wave-execution))
4. Test event matching with debug logs

**Code to add:**
```python
# ============================================================================
# PHASE 5: Wave Execution
# ============================================================================
def wave_execution_matcher(event):
    return (
        event.get('type') == 'complete' and
        'execution_id' in event
    )

def wave_execution_extractor(event, db):
    return {
        'execution_id': event.get('execution_id'),
        'total_waves': event.get('total_waves', 0),
        'atoms_executed': event.get('total_atoms', 0)
    }

wave_execution_result = await execute_phase_with_checkpoint(
    "wave_execution",
    wave_execution_matcher,
    wave_execution_extractor
)

print(f"   ✅ Execution ID: {wave_execution_result.get('execution_id')}")
print(f"   ✅ Total waves: {wave_execution_result.get('total_waves')}")
print(f"   ✅ Atoms executed: {wave_execution_result.get('atoms_executed')}")
```

**Validation:**
- Run test: `pytest tests/e2e/test_mge_v2_complete_pipeline.py::test_complete_mge_v2_pipeline_fastapi -v -s`
- Check logs for wave execution events
- Verify checkpoint JSON has wave_execution: "completed"

---

### Afternoon: E2E Test Phases 6-7 (3 hours)

**Task:** Implement File Writing and Infrastructure phases

**Phase 6: File Writing**
```python
def file_writing_matcher(event):
    return (
        event.get('type') == 'status' and
        event.get('phase') == 'file_writing' and
        'files_written' in event
    )

def file_writing_extractor(event, db):
    from pathlib import Path
    files_written = event.get('files_written', 0)
    workspace_path = event.get('workspace_path', '')
    workspace = Path(workspace_path)
    actual_files = len(list(workspace.rglob('*.py'))) if workspace.exists() else 0

    return {
        'files_written': files_written,
        'workspace_path': workspace_path,
        'files_verified': actual_files
    }
```

**Phase 7: Infrastructure**
```python
def infrastructure_matcher(event):
    return (
        event.get('type') == 'status' and
        event.get('phase') == 'infrastructure_generation' and
        'files_generated' in event
    )

def infrastructure_extractor(event, db):
    return {
        'files_generated': event.get('files_generated', 0),
        'project_type': event.get('project_type', 'unknown')
    }
```

---

## Day 2 (Tuesday, Nov 12) - 6 hours

### Morning: Fix Phase Names (1 hour)

**Problem:** Test declares "wave_execution" but service emits "execution"

**Fix:** Update checkpoint phase names to match service
```python
# Line 158-166
phases = [
    "discovery",
    "masterplan",
    "code_generation",
    "atomization",
    "execution",                    # Changed from "wave_execution"
    "file_writing",
    "infrastructure_generation"     # Changed from "infrastructure"
]
```

**Update all matchers to use correct phase names**

---

### Afternoon: Full E2E Test Run (5 hours)

**Run complete test:**
```bash
pytest tests/e2e/test_mge_v2_complete_pipeline.py::test_complete_mge_v2_pipeline_fastapi -v -s
```

**Monitor for:**
- All 7 phases completing
- Checkpoint JSON correct
- Files on disk
- Infrastructure files present

**Debug common issues:**
- Event name mismatches → Check service event names
- Checkpoint not updating → Verify checkpoint_manager.complete_phase() called
- Files not found → Check workspace_path permissions

---

## Day 3 (Wednesday, Nov 13) - 4 hours

### FileWriter JS/TS Path Inference (4 hours)

**Location:** `src/services/file_writer_service.py:282-284`

**Current code:**
```python
if language != 'python':
    # TODO: Add JS/TS support
    return None
```

**Updated code:**
```python
if language == 'typescript' or language == 'javascript':
    # Basic path inference for TS/JS
    if 'controller' in code.lower() or 'route' in code.lower():
        return f"src/controllers/{atom_name.lower()}.ts"
    elif 'model' in code.lower() or 'schema' in code.lower():
        return f"src/models/{atom_name.lower()}.ts"
    elif 'service' in code.lower():
        return f"src/services/{atom_name.lower()}.ts"
    else:
        return f"src/{atom_name.lower()}.ts"

elif language != 'python':
    # Unsupported language
    return None
```

**Testing:**
1. Create test with JS/TS atoms
2. Verify paths inferred correctly
3. Validate files written to correct locations

---

## Day 4 (Thursday, Nov 14) - 6 hours

### Execution API Endpoints (6 hours)

**Task:** REST API for execution status and WebSocket progress

**Endpoint 1: GET /api/v2/execution/status/{masterplan_id}**
```python
# src/api/routers/execution_v2.py

@router.get("/status/{masterplan_id}")
async def get_execution_status(
    masterplan_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Get execution status for masterplan."""
    from src.mge.v2.services.execution_service_v2 import ExecutionServiceV2

    execution = db.query(Execution).filter(
        Execution.masterplan_id == masterplan_id
    ).first()

    if not execution:
        raise HTTPException(404, "Execution not found")

    return {
        "execution_id": str(execution.execution_id),
        "status": execution.status,
        "current_wave": execution.current_wave,
        "total_waves": execution.total_waves,
        "atoms_completed": execution.atoms_completed,
        "atoms_total": execution.atoms_total,
        "started_at": execution.started_at,
        "completed_at": execution.completed_at
    }
```

**WebSocket Events:**
```python
# Emit during wave execution
await websocket_manager.send_to_session(
    session_id,
    {
        "type": "execution_progress",
        "wave": current_wave,
        "total_waves": total_waves,
        "atoms_completed": completed,
        "atoms_total": total
    }
)
```

---

## Day 5 (Friday, Nov 15) - 4 hours

### Week 1 Retrospective (4 hours)

**Demo:**
1. Run E2E test with all 7 phases ✅
2. Show checkpoint JSON with all phases completed
3. Show workspace with files + infrastructure
4. Demo execution API endpoint

**Metrics:**
- E2E test duration: <60 min ✅
- All phases passing ✅
- Files on disk: ≥10 Python files + 4 infra files ✅
- Checkpoint recovery: Working ✅

**Next Week Planning:**
- Acceptance Tests design (Week 2 focus)
- Contract schema finalization
- Template creation

---

## Success Criteria

### Must Have (Week 1)
- ✅ E2E test validates all 7 phases
- ✅ All phases marked "completed" in checkpoint
- ✅ Files physically written to filesystem
- ✅ Infrastructure files generated
- ✅ Test passes with exit code 0

### Should Have
- ✅ FileWriter JS/TS basic inference
- ✅ Execution API GET endpoint
- ✅ WebSocket progress events

### Could Have
- ⬜ Docker build validation
- ⬜ Python syntax validation

---

## Troubleshooting

### Test fails at Phase 5
**Symptom:** Test hangs or times out at wave execution
**Solution:** Check if WaveExecutor is completing, verify execution_id in events

### Files not found in Phase 6
**Symptom:** files_verified = 0
**Solution:** Check workspace_path, verify FileWriterService permissions

### Infrastructure Phase skipped
**Symptom:** Phase shows "pending"
**Solution:** Verify workspace_path passed to infra service, check template files exist

---

**Author:** Dany
**Last Updated:** 2025-11-10
