# MasterPlan Generation - Findings & Remediation Plan
**Date**: Nov 4, 2025
**Session**: Debug & Fix Post-P0 Phase
**Status**: 🔴 Critical issues fixed, validation pending

---

## EXECUTIVE SUMMARY

Three critical bugs were identified and fixed during masterplan generation testing:

| Issue | Severity | Status | Impact |
|-------|----------|--------|--------|
| NoneType return from LLM | 🔴 Critical | ✅ Fixed | Blocked all generation |
| Logger type mismatch | 🟡 High | ✅ Fixed | Blocked task calculation |
| Undefined logging module | 🟡 High | ✅ Fixed | Blocked masterplan generation |
| Missing completion event | 🟡 Medium-High | ⚠️ Needs validation | UX broken but data saves |
| Orphan cleanup error | 🟢 Low | ⚠️ Needs fix | Background process fails |
| Redis cache missing | 🟢 Low | ⚠️ Degraded | Performance impact only |
| ChromaDB missing | 🟢 Low | ⚠️ Degraded | RAG disabled |

---

## DETAILED FINDINGS

### BUG #1: NoneType Return from LLM Client ✅ FIXED
**File**: `src/llm/enhanced_anthropic_client.py:256-517`
**Error**: `'NoneType' object is not subscriptable` at `discovery_agent.py:387`

**Root Cause**: Response processing code was ONLY in the exception handler block, so successful API calls returned None implicitly.

**Code Structure (Before)**:
```python
try:
    if use_streaming:
        # Streaming logic
    else:
        # Non-streaming logic
    # ❌ NO RETURN HERE - returns None!
except Exception as outer_exception:
    # Lines 442-502: Process response, set result, RETURN
    return result
```

**Fix**: Moved response processing (lines 442-502) OUTSIDE try-except block so all success paths return properly formatted dict.

**Validation**: ✅ Manually tested, generation proceeded past discovery phase

---

### BUG #2: Logger Type Mismatch ✅ FIXED
**File**: `src/services/masterplan_calculator.py`
**Error**: `Logger._log() got an unexpected keyword argument 'discovery_id'`

**Root Cause**: Used stdlib `logging.getLogger()` which doesn't support structured kwargs, but code called `logger.info(..., discovery_id=..., domain=...)`

**Fix**:
- Changed: `import logging` → `from src.observability import get_logger`
- Changed: `logger = logging.getLogger(__name__)` → `logger = get_logger("masterplan_calculator")`

**Validation**: ✅ StructuredLogger accepts arbitrary kwargs for context

---

### BUG #3: Undefined Module Reference ✅ FIXED
**File**: `src/services/masterplan_calculator.py:91`
**Error**: `NameError: name 'logging' is not defined`

**Root Cause**: Removed `import logging` but `__init__` still referenced undefined `logging.getLogger()`

**Fix**:
- Removed `__init__` definition entirely
- Changed all `self.logger.info()` calls to `logger.info()` (module-level)

**Validation**: ✅ No references to undefined `logging` module remain

---

### ISSUE #4: Missing MasterPlan Completion Event ⚠️ NEEDS VALIDATION
**Component**: `src/websocket/manager.py:327-369` & `src/services/masterplan_generator.py:413`
**Manifestation**: Frontend never receives `masterplan_generation_complete` event

**Evidence**:
- ✅ Backend successfully generates MasterPlan with 52 tasks
- ✅ Database confirms save (ID: `a4a8b6d0-892e-440b-8bbd-da36b666149f`)
- ✅ WebSocket emits `masterplan_generation_start` event
- ❌ WebSocket never emits `masterplan_generation_complete` event
- ❌ Frontend modal doesn't update

**Last Error Log** (from previous test before Bug #3 fix):
```
[ERROR] [masterplan_generator] MasterPlan generation failed: "name 'logging' is not defined"
```

**Most Likely Root Cause**:
One of the fixed bugs (likely #3) was causing generation to fail before reaching the completion event emission at line 413.

**Action Required**:
1. **Restart Docker container** - Ensure latest code with all fixes is running
2. **Retest generation flow** - Should now complete successfully
3. **If event still missing** - Add detailed logging to identify exact failure point

**Note**: Bug #3 was fixed AFTER the last test, so the NameError should no longer occur.

---

### ISSUE #5: Redis Cache Unavailable ⚠️ DEGRADED
**Component**: `src/mge.v2.caching.llm_prompt_cache`
**Error**: `Error 111 connecting to localhost:6379. Connection refused`

**Impact**: ⚠️ Low
- Prompt caching disabled (no cost savings)
- Generation still works without caching

**Fix**: `docker-compose up -d redis`

---

### ISSUE #6: ChromaDB Not Available ⚠️ DEGRADED
**Component**: `src/rag.vector_store`
**Error**: `Could not connect to a Chroma server... port 8000`

**Impact**: ⚠️ Low
- RAG example retrieval fails silently
- Generation uses empty example list
- Quality may be slightly reduced

**Fix**: `docker-compose up -d chromadb`

---

### ISSUE #7: Orphan Cleanup Async Context Manager Error 🔴 NEEDS FIX
**File**: `src/services/orphan_cleanup.py`
**Error**: `'_GeneratorContextManager' object does not support the asynchronous context manager protocol`

**Root Cause**: Using `async with get_db_context()` but `get_db_context()` returns sync context manager

**Impact**: 🟢 Low
- Orphan cleanup doesn't run
- Stale MasterPlans accumulate in database
- No impact on generation process

**Fix Required**:
```python
# Change from:
async with get_db_context() as db:  # ❌ Won't work

# To:
with get_db_context() as db:  # ✅ Correct (already sync)
```

---

## REMEDIATION PLAN

### Phase 1: CRITICAL (30 min)
**Must complete to unblock generation**

**1.1 Verify Latest Code Deployed**
```bash
# Check masterplan_calculator.py in container
docker exec devmatrix-api cat /app/src/services/masterplan_calculator.py | head -25

# Should show: from src.observability import get_logger
# Should NOT show: import logging
```

**1.2 Restart API Container**
```bash
docker-compose restart devmatrix-api
# OR full restart:
docker-compose down && docker-compose up -d devmatrix-api devmatrix-ui
```

**1.3 Test Full Generation Flow**
1. Create discovery document via frontend
2. Click "Generate MasterPlan"
3. Monitor logs: `docker logs devmatrix-api -f`
4. Check database for new MasterPlan
5. Verify WebSocket events in browser console

**Success Criteria**:
- [ ] Generation completes without errors in logs
- [ ] New MasterPlan appears in database
- [ ] Frontend receives completion event
- [ ] Modal displays completion with task count

---

### Phase 2: HIGH (15 min)
**Should fix to prevent database issues**

**2.1 Fix Orphan Cleanup Worker**

File: `src/services/orphan_cleanup.py`

Find the async loop method and change:
```python
# Before (❌ Wrong):
async def _run_cleanup_cycle(self):
    async with get_db_context() as db:
        # ... code

# After (✅ Correct):
async def _run_cleanup_cycle(self):
    with get_db_context() as db:
        # ... code (rest stays same)
```

**Validation**:
```bash
docker-compose restart devmatrix-api
docker logs devmatrix-api -f | grep orphan
# Should NOT see async context manager error
```

---

### Phase 3: MEDIUM (10 min)
**Should restore for optimal performance**

**3.1 Start Redis**
```bash
docker-compose up -d redis
# Verify in logs: [INFO] Redis connection established
```

**3.2 Start ChromaDB**
```bash
docker-compose up -d chromadb
# Verify in logs: [INFO] ChromaDB connection established
```

---

### Phase 4: OPTIONAL (45 min)
**Nice-to-have improvements**

**4.1 Add exception propagation in WebSocket emit**
- Currently swallows exceptions at line 89-96 in `manager.py`
- Consider adding flag to make exception-aware callers aware of failures

**4.2 Add streaming response timeout handling**
- Long-running LLM requests can hang
- Add timeout + error event emission

**4.3 Improve error logging around completion event**
- Add detailed logging before/after completion event emission
- Help debug future similar issues

---

## TESTING CHECKLIST

### Pre-Test Setup
```bash
# Ensure clean state
docker-compose down
docker-compose up -d

# Wait for services to be ready
sleep 10

# Verify services running
docker-compose ps
```

### Test Execution
1. **Access Frontend**: http://localhost:3000
2. **Create Discovery Document**
   - Domain: "Test Project"
   - Entities: 3-4 bounded contexts
3. **Generate MasterPlan**
   - Click "Generate MasterPlan" button
   - Monitor frontend console: F12 → Console tab
4. **Monitor Backend**
   - In separate terminal: `docker logs devmatrix-api -f`
   - Look for: generation start → calculation → LLM gen → save → completion event
5. **Verify Results**
   - [ ] No errors in API logs
   - [ ] WebSocket events appear in browser console
   - [ ] New MasterPlan in `/api/v1/masterplans` list
   - [ ] Frontend modal shows completion
   - [ ] Can view generated MasterPlan details

### Expected WebSocket Event Sequence
```
1. masterplan_generation_start
2. masterplan_parsing_complete
3. masterplan_validation_start (optional)
4. masterplan_saving_start
5. masterplan_generation_complete ← Should receive this
```

---

## QUICK START

**To deploy all fixes and test**:
```bash
# 1. Ensure code changes are committed
git status  # Should be clean or only have docker changes

# 2. Restart containers with fresh code
docker-compose down
docker-compose up -d

# 3. Wait for ready
sleep 15

# 4. Run test scenario
# Create discovery + generate masterplan (see Testing Checklist above)
```

---

## FILES MODIFIED

| File | Changes | Status |
|------|---------|--------|
| `src/llm/enhanced_anthropic_client.py` | Moved response processing outside try-except | ✅ Done |
| `src/services/masterplan_calculator.py` | Fixed logger import + usage | ✅ Done |
| `src/services/orphan_cleanup.py` | Fix async context manager (TODO) | ⏳ Not yet |

---

## ROLLBACK PLAN

If issues occur after deployment:
```bash
# Revert to previous working state
git checkout HEAD~1 -- \
  src/llm/enhanced_anthropic_client.py \
  src/services/masterplan_calculator.py

docker-compose restart devmatrix-api
```

---

## NEXT STEPS

1. **Run Phase 1 validation** - Restart and test generation
2. **Document results** - If successful, mark completion
3. **Run Phase 2 fix** - Fix orphan cleanup async issue
4. **Run Phase 3 setup** - Restore Redis and ChromaDB
5. **Optional Phase 4** - Improve error handling and logging

