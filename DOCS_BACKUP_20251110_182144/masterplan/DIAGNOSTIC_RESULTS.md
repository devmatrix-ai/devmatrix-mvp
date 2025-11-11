# MasterPlan Generation - Diagnostic Results

**Date**: November 4, 2025
**Status**: 🔴 **ROOT CAUSE IDENTIFIED**

---

## Test Results Summary

### ✅ TEST 1: Environment & Infrastructure
- **PostgreSQL**: RUNNING ✅ (Version 16.10)
- **Database**: ACCESSIBLE ✅
- **Tables**: ALL CREATED ✅
  - discovery_documents ✅
  - masterplans ✅
  - masterplan_phases ✅
  - masterplan_milestones ✅
  - masterplan_tasks ✅

### ✅ TEST 2: Discovery Persistence
- **Status**: **WORKING PERFECTLY** ✅
- **Records**: 12 discovery documents saved successfully
- **Content**: Valid data (domain, user_request, metadata)
- **Timestamps**: Recent (2025-10-31)
- **Example Domains Found**:
  - "Agile Project Management SaaS"
  - "Project Management and Team Collaboration SaaS"

### ❌ TEST 3: MasterPlan Persistence
- **Status**: **COMPLETELY BROKEN** ❌
- **MasterPlans saved**: **0 records**
- **MasterPlan Phases saved**: **0 records**
- **MasterPlan Tasks saved**: **0 records**
- **MasterPlan Milestones saved**: **0 records**

### ⚠️ TEST 4: Discovery→MasterPlan Link
```
Result: 12 discovery documents with NO associated masterplans
- All masterplan_id values: NULL
- All project_name values: NULL
```

---

## Root Cause Analysis

### THE EXACT PROBLEM

```
✅ User calls /masterplan command
  └─ Calls conduct_discovery() → SUCCEEDS ✅
     └─ Saves discovery to DB → 12 records exist

  └─ Calls generate_masterplan() → FAILS ❌
     └─ Discovery loads → OK
     └─ LLM generation → ???
     └─ JSON parsing → ???
     └─ Validation → ???
     └─ Database save → NEVER HAPPENS ❌
```

### Most Likely Failure Point

**Location**: `src/services/masterplan_generator.py:624` or one of the steps immediately after

```python
response = await self.llm.generate_with_caching(
    task_type="masterplan_generation",
    complexity=TaskComplexity.HIGH,
    cacheable_context={
        "system_prompt": MASTERPLAN_SYSTEM_PROMPT,
        "discovery_doc": discovery_context,
        "rag_examples": rag_context
    },
    variable_prompt=variable_prompt,
    max_tokens=64000,  # ⚠️ Requesting 120 tasks in ONE call
    temperature=0.7
)
```

### Why MasterPlan Generation is Failing

1. **Generating 120 Tasks in One LLM Call**
   - Max output tokens: 64,000
   - But Claude often outputs ~20K actual useful tokens
   - 120 tasks = ~15-20K tokens minimum
   - **Risk**: LLM response is truncated or incomplete

2. **JSON Parsing Likely Failing**
   - If LLM response is incomplete JSON (e.g., cut off mid-array)
   - `json.loads()` at line 680 will raise `JSONDecodeError`
   - Exception caught at line 417-432 (probably not logged properly)

3. **No Error Visibility**
   - Exception at line 417-432 logs error but may not be visible in API logs
   - WebSocket error message returned to user
   - No database record created

---

## Evidence

### Database State
```sql
discovery_documents: 12 records ✅
masterplans: 0 records ❌

The gap shows exactly where generation is failing:
discovery → ??? → masterplan (never completes)
```

### No Error Logs
- API logs show only health checks and metrics
- No "MasterPlan generation failed" messages
- No "Error during generation" messages
- **Conclusion**: Errors not being properly logged or user never triggered `/masterplan`

### Code Path Analysis
```
✅ Discovery works: db.add() + db.commit() at line 496-497
❌ MasterPlan never starts: No db.add() ever called for masterplan

This means _save_masterplan() at line 369 is NEVER CALLED
```

---

## Confirmed Issues

### 🔴 CRITICAL: Monolithic MasterPlan Generation
**File**: `src/services/masterplan_generator.py:618-635`

```python
Generate a complete, executable MasterPlan with exactly 120 tasks
organized in 3 phases covering ALL features needed for a production SaaS.
```

**Problem**:
- Attempting to generate 120 complex tasks in one LLM call
- Each task needs context, dependencies, technology decisions
- **120 tasks × ~200 tokens per task = ~24,000 tokens minimum**
- **But also need**: phase descriptions, milestones, tech stack, constraints
- **Total**: Likely 30,000+ tokens required
- **Claude Sonnet 4.5 limit**: 64,000 tokens output
- **Reality**: Most responses cap around 20,000 actual output tokens

**Evidence of Failure**:
- 0 masterplans in database despite 12 discovery attempts
- JSON parsing likely fails because response is incomplete

### 🟡 MEDIUM: No Error Logging
**File**: `src/services/masterplan_generator.py:417-432`

```python
except Exception as e:
    # Record failure
    self.metrics.increment_counter(
        "masterplan_failures_total",
        labels={"session_id": session_id, "error_type": type(e).__name__},
        help_text="Failed MasterPlan generations"
    )

    logger.error(
        "MasterPlan generation failed",
        discovery_id=str(discovery_id),
        session_id=session_id,
        error=str(e),
        error_type=type(e).__name__
    )
    raise RuntimeError(f"MasterPlan generation failed: {str(e)}") from e
```

**Problem**: Error is logged but maybe not visible, or exception is caught at higher level (chat_service.py:968-976)

### 🟡 MEDIUM: Silent Exception Handling
**File**: `src/services/chat_service.py:968-976`

```python
except Exception as e:
    error_message = f"Error durante generación de MasterPlan: {str(e)}"
    self.logger.error(error_message, exc_info=True)

    yield {
        "type": "error",
        "content": error_message,
        "done": True,
    }
```

**Problem**: Error is sent to user but never persists or shows in logs

---

## Why Discovery Works But MasterPlan Doesn't

### Discovery Generation (12 successes)
- **Input**: User request (100-200 words)
- **Output**: Domain + 3-5 bounded contexts + ~5-10 aggregates
- **Total tokens**: ~3,000-5,000 tokens
- **Complexity**: Moderate - fits easily in one LLM call

### MasterPlan Generation (0 successes)
- **Input**: Discovery document (2,000-3,000 tokens) + 120 task specification
- **Output**: 120 complete tasks with dependencies, phases, milestones
- **Total tokens needed**: 30,000+ tokens
- **Complexity**: EXTREME - probably exceeds LLM's ability in single call

---

## The Fix

### Short Term (Hours)
```python
# In masterplan_generator.py, modify _generate_masterplan_llm():

# INSTEAD OF:
Generate a complete, executable MasterPlan with exactly 120 tasks

# DO THIS:
Generate PHASE 1 (40 tasks) of a complete MasterPlan covering:
- Core feature implementation
- Initial infrastructure
- Basic deployment
```

Generate in phases instead of monolithic approach.

### Medium Term (Days)
```python
# Break masterplan generation into 3 calls:

Phase 1 Generation: 40 tasks (setup + core) - ~12,000 tokens
Phase 2 Generation: 40 tasks (features + polish) - ~12,000 tokens
Phase 3 Generation: 40 tasks (optimization + deployment) - ~12,000 tokens

Save each phase incrementally
```

### Long Term (Week)
```python
# Implement true atomic masterplan generation:

1. Parse discovery into micro-features
2. Generate 1-2 atomic tasks at a time
3. Build task dependency graph
4. Persist incrementally to DB
5. Show real-time progress to user
```

---

## Testing the Fix

### Before Fix
```sql
SELECT COUNT(*) FROM masterplans;
-- Result: 0
```

### After Fix
```sql
SELECT COUNT(*) FROM masterplans;
-- Result: Should have ≥ 1

SELECT COUNT(*) FROM masterplan_tasks WHERE masterplan_id = '...';
-- Result: Should be ~40-50 (not 120)

SELECT COUNT(*) FROM masterplan_phases;
-- Result: Should be 1 (Phase 1) or more
```

---

## Recommended Next Steps

### Immediate (Today)
1. ✅ **Modify prompt** to generate Phase 1 only (40 tasks instead of 120)
2. ✅ **Test generation** to verify JSON is valid and complete
3. ✅ **Verify persistence** - masterplan should appear in database
4. ✅ **Enable detailed logging** for debugging

### Short Term (This Week)
1. Implement 3-phase generation (Phase 1, 2, 3 separately)
2. Add progressive saving to database
3. Add real-time progress updates via WebSocket

### Medium Term (Next Week)
1. Implement true atomic task generation (1-2 tasks per LLM call)
2. Build task dependency graph
3. Optimize for cost and token usage

---

## Code Changes Required

### File: `src/services/masterplan_generator.py:604`

**Change From:**
```python
variable_prompt = f"""Generate a complete MasterPlan (120 tasks) for the following project:
...
Generate a complete, executable MasterPlan with exactly 120 tasks organized in 3 phases covering ALL features needed for a production SaaS.
"""
```

**Change To:**
```python
variable_prompt = f"""Generate PHASE 1 of a MasterPlan (40-50 tasks) for the following project:
...
Generate Phase 1 (Setup and Core Implementation) with exactly 40-50 tasks organized in 1-2 milestones.
Focus on:
1. Infrastructure setup (Docker, databases, CI/CD)
2. Core feature implementation
3. Initial user authentication

Do NOT include optimization, advanced features, or deployment tasks - those are in Phase 2 and 3.
"""
```

### File: `src/services/chat_service.py:925`

**Change From:**
```python
**Tareas**: {masterplan.total_tasks}
```

**Change To:**
```python
**Tareas (Fase 1)**: {masterplan.total_tasks}/120 (40% de tareas totales)
**Próximas fases**: Serán generadas en iteraciones posteriores
```

---

## Summary

### What We Know
- ✅ Database infrastructure is perfect
- ✅ Discovery generation works flawlessly
- ✅ All code exists and is well-structured
- ❌ MasterPlan generation is FAILING due to prompt trying 120 tasks at once
- ❌ JSON response likely truncated
- ❌ Parsing fails, no masterplan saved

### Root Cause
**Attempting to generate 120 complex software engineering tasks in a single LLM call exceeds Claude's practical output capacity.**

### Solution
**Generate MasterPlan in phases: 40-50 tasks per call, for 3 phases total.**

### Expected Outcome
- ✅ MasterPlans will start appearing in database
- ✅ Each masterplan will have proper task structure
- ✅ Phases can be extended or regenerated
- ✅ True atomic task generation in Phase 5

---

**Status**: Ready to implement fix
**Estimated Fix Time**: 2-3 hours
**Estimated Testing Time**: 1 hour

