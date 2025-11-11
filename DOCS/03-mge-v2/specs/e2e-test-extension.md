# E2E Test Extension - Phases 5-7 Validation

**Gap ID:** Test-01
**Priority:** 🔴 CRITICAL
**Effort:** 3-4 hours
**Owner:** Dany
**Status:** Not Started

---

## Problem Statement

The E2E test `test_mge_v2_complete_pipeline_fastapi` currently validates only phases 1-4:
- ✅ Phase 1: Discovery
- ✅ Phase 2: MasterPlan Generation
- ✅ Phase 3: Code Generation
- ✅ Phase 4: Atomization
- ❌ Phase 5: Wave Execution (NOT TESTED)
- ❌ Phase 6: File Writing (NOT TESTED)
- ❌ Phase 7: Infrastructure Generation (NOT TESTED)

**Root Cause:**
- Test declares all 7 phases in checkpoint array (lines 158-166)
- Implementation stops at line 459 with comment "Continue with remaining phases..."
- No matchers/extractors implemented for phases 5-7

**Impact:**
- Cannot validate end-to-end pipeline completion
- Cannot verify file writing to filesystem
- Cannot validate infrastructure generation (Docker, configs)
- Checkpoint system incomplete for production scenarios

---

## Technical Specification

### Phase 5: Wave Execution

**Event Detection:**
```python
def wave_execution_matcher(event):
    """Check if event signals wave execution completion."""
    return (
        event.get('type') == 'complete' and
        'execution_id' in event
    )
```

**Data Extraction:**
```python
def wave_execution_extractor(event, db):
    """Extract wave execution data."""
    execution_id = event.get('execution_id')
    total_waves = event.get('total_waves', 0)
    total_atoms = event.get('total_atoms', 0)

    return {
        'execution_id': execution_id,
        'total_waves': total_waves,
        'atoms_executed': total_atoms
    }
```

**Expected Events:**
```python
{"type": "status", "phase": "execution", "message": "Starting wave-based execution..."}
{"type": "complete", "execution_id": "...", "total_waves": 5, "total_atoms": 43}
```

---

### Phase 6: File Writing

**Event Detection:**
```python
def file_writing_matcher(event):
    """Check if event signals file writing completion."""
    return (
        event.get('type') == 'status' and
        event.get('phase') == 'file_writing' and
        'files_written' in event
    )
```

**Data Extraction:**
```python
def file_writing_extractor(event, db):
    """Extract file writing data."""
    files_written = event.get('files_written', 0)
    workspace_path = event.get('workspace_path', '')

    # Verify files actually exist on filesystem
    from pathlib import Path
    workspace = Path(workspace_path)
    actual_files = len(list(workspace.rglob('*.py'))) if workspace.exists() else 0

    return {
        'files_written': files_written,
        'workspace_path': workspace_path,
        'files_verified': actual_files
    }
```

**Expected Events:**
```python
{"type": "status", "phase": "file_writing", "message": "Writing N atoms to workspace..."}
{"type": "status", "phase": "file_writing", "files_written": 15, "workspace_path": "/tmp/..."}
```

---

### Phase 7: Infrastructure Generation

**Event Detection:**
```python
def infrastructure_matcher(event):
    """Check if event signals infrastructure generation completion."""
    return (
        event.get('type') == 'status' and
        event.get('phase') == 'infrastructure_generation' and
        'files_generated' in event
    )
```

**Data Extraction:**
```python
def infrastructure_extractor(event, db):
    """Extract infrastructure generation data."""
    files_generated = event.get('files_generated', 0)
    project_type = event.get('project_type', 'unknown')

    return {
        'files_generated': files_generated,
        'project_type': project_type
    }
```

**Expected Events:**
```python
{"type": "status", "phase": "infrastructure_generation", "message": "Generating project infrastructure..."}
{"type": "status", "phase": "infrastructure_generation", "files_generated": 4, "project_type": "fastapi"}
```

---

## Implementation Steps

### Step 1: Add Phase 5 - Wave Execution (30 min)

**Location:** `tests/e2e/test_mge_v2_complete_pipeline.py:457`

```python
# ============================================================================
# PHASE 5: Wave Execution
# ============================================================================
def wave_execution_matcher(event):
    """Check if event signals wave execution completion."""
    return (
        event.get('type') == 'complete' and
        'execution_id' in event
    )

def wave_execution_extractor(event, db):
    """Extract wave execution data."""
    execution_id = event.get('execution_id')
    total_waves = event.get('total_waves', 0)
    total_atoms = event.get('total_atoms', 0)

    return {
        'execution_id': execution_id,
        'total_waves': total_waves,
        'atoms_executed': total_atoms
    }

wave_execution_result = await execute_phase_with_checkpoint(
    "wave_execution",
    wave_execution_matcher,
    wave_execution_extractor
)

print(f"   ✅ Execution ID: {wave_execution_result.get('execution_id', 'N/A')}")
print(f"   ✅ Total waves: {wave_execution_result.get('total_waves', 0)}")
print(f"   ✅ Atoms executed: {wave_execution_result.get('atoms_executed', 0)}")
```

---

### Step 2: Add Phase 6 - File Writing (45 min)

**Location:** After Phase 5 implementation

```python
# ============================================================================
# PHASE 6: File Writing
# ============================================================================
def file_writing_matcher(event):
    """Check if event signals file writing completion."""
    return (
        event.get('type') == 'status' and
        event.get('phase') == 'file_writing' and
        'files_written' in event
    )

def file_writing_extractor(event, db):
    """Extract file writing data."""
    from pathlib import Path

    files_written = event.get('files_written', 0)
    workspace_path = event.get('workspace_path', '')

    # Verify files actually exist on filesystem
    workspace = Path(workspace_path)
    actual_files = len(list(workspace.rglob('*.py'))) if workspace.exists() else 0

    return {
        'files_written': files_written,
        'workspace_path': workspace_path,
        'files_verified': actual_files
    }

file_writing_result = await execute_phase_with_checkpoint(
    "file_writing",
    file_writing_matcher,
    file_writing_extractor
)

print(f"   ✅ Files written: {file_writing_result.get('files_written', 0)}")
print(f"   ✅ Workspace: {file_writing_result.get('workspace_path', 'N/A')}")
print(f"   ✅ Files verified on disk: {file_writing_result.get('files_verified', 0)}")
```

---

### Step 3: Add Phase 7 - Infrastructure Generation (45 min)

**Location:** After Phase 6 implementation

```python
# ============================================================================
# PHASE 7: Infrastructure Generation
# ============================================================================
def infrastructure_matcher(event):
    """Check if event signals infrastructure generation completion."""
    return (
        event.get('type') == 'status' and
        event.get('phase') == 'infrastructure_generation' and
        'files_generated' in event
    )

def infrastructure_extractor(event, db):
    """Extract infrastructure generation data."""
    files_generated = event.get('files_generated', 0)
    project_type = event.get('project_type', 'unknown')

    return {
        'files_generated': files_generated,
        'project_type': project_type
    }

infrastructure_result = await execute_phase_with_checkpoint(
    "infrastructure",
    infrastructure_matcher,
    infrastructure_extractor
)

print(f"   ✅ Infrastructure files: {infrastructure_result.get('files_generated', 0)}")
print(f"   ✅ Project type: {infrastructure_result.get('project_type', 'unknown')}")
```

---

### Step 4: Update Checkpoint Phase Names (15 min)

**Problem:** Test declares `"infrastructure"` but service emits `"infrastructure_generation"`

**Fix:** Change line 165 in test:
```python
# BEFORE
phases = [
    "discovery",
    "masterplan",
    "code_generation",
    "atomization",
    "wave_execution",  # Service emits "execution"
    "file_writing",    # ✅ Matches
    "infrastructure"   # Service emits "infrastructure_generation"
]

# AFTER - Match service event names OR update matchers
# Option A: Keep test names, update matchers to handle both
# Option B: Match service names exactly
phases = [
    "discovery",
    "masterplan",
    "code_generation",
    "atomization",
    "execution",                    # Match service
    "file_writing",                 # ✅ Already matches
    "infrastructure_generation"     # Match service
]
```

**Recommendation:** Option B (match service names) for consistency

---

### Step 5: Test Execution & Validation (45 min)

**Run Test:**
```bash
pytest tests/e2e/test_mge_v2_complete_pipeline.py::test_complete_mge_v2_pipeline_fastapi -v -s
```

**Expected Output:**
```
▶️  Starting phase: execution
  [DEBUG] Event: type=status, phase=execution, message=Starting wave-based execution...
  🎯 MATCHED! Extracting data for phase execution
   ✅ Execution ID: a1b2c3d4-...
   ✅ Total waves: 5
   ✅ Atoms executed: 43

▶️  Starting phase: file_writing
  [DEBUG] Event: type=status, phase=file_writing, message=Writing 43 atoms to workspace...
  🎯 MATCHED! Extracting data for phase file_writing
   ✅ Files written: 12
   ✅ Workspace: /tmp/mge_v2_workspace/...
   ✅ Files verified on disk: 12

▶️  Starting phase: infrastructure_generation
  [DEBUG] Event: type=status, phase=infrastructure_generation, message=Generating project infrastructure...
  🎯 MATCHED! Extracting data for phase infrastructure_generation
   ✅ Infrastructure files: 4
   ✅ Project type: fastapi

================================================================================
✅ E2E Test PASSED! (All 7 phases)
================================================================================
```

**Validation Checklist:**
- [ ] Test completes all 7 phases without errors
- [ ] Checkpoint JSON shows all phases as "completed"
- [ ] Workspace directory exists with files on disk
- [ ] Infrastructure files (Dockerfile, docker-compose.yml, requirements.txt, README.md) present
- [ ] Test duration <60 minutes for FastAPI example
- [ ] No database errors or transaction rollbacks
- [ ] Checkpoint recovery works if test interrupted mid-execution

---

## Acceptance Criteria

### Must Have
- ✅ Test executes all 7 phases end-to-end
- ✅ All phases marked as "completed" in checkpoint
- ✅ Files physically written to filesystem (verified)
- ✅ Infrastructure files generated (Dockerfile, docker-compose.yml, etc.)
- ✅ Test passes with exit code 0

### Should Have
- ✅ Phase timing recorded in checkpoint (for performance tracking)
- ✅ Workspace cleanup on test success (optional flag)
- ✅ Detailed logging for debugging failures

### Could Have
- ✅ Docker build validation (actually build generated Dockerfile)
- ✅ Syntax validation for generated Python files
- ✅ Git repository initialization in workspace

---

## Dependencies

### Blocking
- None - all services already implemented

### Non-Blocking
- Phase 4 (Atomization) must complete successfully
- Database schema with VARCHAR(1000) for atomic_units.name

---

## Risks & Mitigation

### Risk 1: Event name mismatch between test and service
- **Probability:** HIGH (already detected)
- **Impact:** HIGH (test won't detect completion)
- **Mitigation:** Update test phase names to match service OR update matchers to be flexible
- **Solution:** Use service names: "execution", "file_writing", "infrastructure_generation"

### Risk 2: Filesystem permissions for workspace creation
- **Probability:** LOW
- **Impact:** MEDIUM (file writing fails)
- **Mitigation:** Use /tmp/ with proper permissions, test writes file first
- **Solution:** FileWriterService already handles this

### Risk 3: Long execution time (>60 min)
- **Probability:** MEDIUM
- **Impact:** LOW (timeout)
- **Mitigation:** Increase pytest timeout, optimize test project size
- **Solution:** Use simple FastAPI example (current test already does this)

---

## Testing Strategy

### Unit Tests
- Not applicable (E2E test itself is integration test)

### Integration Tests
- Run full E2E test with all 7 phases
- Verify checkpoint persistence at each phase
- Test recovery from failure at each phase

### Performance Tests
- Measure total execution time
- Track time per phase
- Identify bottlenecks (likely code generation with LLM)

---

## Rollout Plan

### Phase 1: Implementation (Day 1 - 3 hours)
1. Add Phase 5 matcher/extractor (30 min)
2. Add Phase 6 matcher/extractor (45 min)
3. Add Phase 7 matcher/extractor (45 min)
4. Update phase names to match service (15 min)
5. Buffer (45 min)

### Phase 2: Testing (Day 1 - 1 hour)
1. Run test end-to-end (45 min)
2. Fix any event matching issues (15 min)
3. Verify checkpoint JSON completeness

### Phase 3: Validation (Day 2 - 1 hour)
1. Verify files on filesystem
2. Check infrastructure files quality
3. Test checkpoint recovery
4. Document results

---

## Success Metrics

- **Test Pass Rate:** 100% (all 7 phases complete)
- **Execution Time:** <60 min for FastAPI example
- **Files Generated:** ≥10 Python files + 4 infrastructure files
- **Checkpoint Coverage:** 7/7 phases tracked
- **Recovery Success:** 100% recovery from any phase failure

---

## Related Documents

- [Test Implementation](../../../tests/e2e/test_mge_v2_complete_pipeline.py)
- [Orchestration Service](../../../src/services/mge_v2_orchestration_service.py)
- [Checkpoint Manager](../../../tests/e2e/checkpoint_manager.py)
- [Completion Plan](../../10-project-status/MGE_V2_COMPLETION_PLAN.md)

---

**Author:** Dany
**Created:** 2025-11-10
**Last Updated:** 2025-11-10
**Status:** Ready for Implementation
