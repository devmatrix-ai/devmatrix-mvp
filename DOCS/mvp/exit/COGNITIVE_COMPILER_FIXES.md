# Cognitive Compiler Fixes

> **Status**: ✅ IMPLEMENTED
> **Date**: 2025-12-02
> **Context**: Post-run analysis of Ariel_test_006_25_026_30.log

---

## 📊 Run Summary (Pre-Fix)

| Metric | Reported | Actual | Gap |
|--------|----------|--------|-----|
| Smoke Tests | 100% (11/11) | 13% (11/85) | IR tests skipped |
| Unit Tests | 66.4% | 66.4% | 88 failing |
| Constraint Compliance | 99.9% semantic | 50-68% IR | Business logic missing |
| Cognitive Compiler | "wired" | NOT EXERCISED | Docker failure |

---

## ✅ FIXES APPLIED

### Fix 1: Docker Compose `version` Attribute Removed ✅

**Files Modified**:
- `src/services/code_generation_service.py` (line 5402)
- `src/services/code_generation_service.py.backup` (line 3577)
- `templates/docker/docker-compose.yml.j2` (line 1)
- `templates/production/docker/docker-compose.yml.j2` (line 1)
- `templates/production/docker/docker-compose.test.yml.j2` (line 1)

**Change**: Removed obsolete `version: '3.8'` line, added comment explaining removal.

```yaml
# Before:
version: '3.8'
services:
  ...

# After:
# Note: 'version' attribute removed - obsolete in Docker Compose v2+
services:
  ...
```

---

### Fix 2: LLM Fallback REMOVED (Compiler Mode) ✅

**File Modified**: `tests/e2e/real_e2e_full_pipeline.py`

**Change**: Removed 112 lines of LLM fallback code. Now the pipeline:
1. REQUIRES TestsIR system to be available
2. REQUIRES Docker/IR smoke test to work
3. Fails explicitly if infrastructure is broken (no silent fallbacks)

```python
# Before:
if use_ir_smoke:
    smoke_result = await self._run_ir_smoke_test()
    if smoke_result is not None:
        # process
    else:
        print("⚠️ IR smoke test failed, falling back to LLM orchestrator")
        # 40+ lines of LLM fallback code
        # Then more fallback to basic validator

# After (COMPILER MODE):
if not TESTS_IR_AVAILABLE:
    raise RuntimeError("TestsIR system not available. Fix imports before retrying.")

if True:  # COMPILER MODE: Always use IR smoke test
    smoke_result = await self._run_ir_smoke_test()
    if smoke_result is not None:
        # process
    else:
        raise RuntimeError("IR smoke test infrastructure failed. Fix Docker/TestsIR before retrying.")
```

**Rationale**: A compiler doesn't have "fallbacks" - it either compiles correctly or fails with clear error messages.

---

### Fix 3: SERVICE Repair Code EXISTS ✅

**Analysis**: The code for injecting RuntimeFlowValidator already exists in:
- `src/services/production_code_generators.py`:
  - `_generate_behavior_guards()` generates `EntityValidator` class with `check_stock_invariant`, `check_status_transition`
  - `_generate_workflow_method_body()` generates methods with precondition checks
  - `find_workflow_operations()` extracts `affects_stock` and status transitions from IR

- `src/validation/smoke_repair_orchestrator.py`:
  - `_fix_business_logic_error()` already injects validation code into service methods
  - `_generate_stock_validation_code()`, `_generate_status_check_code()`, `_generate_empty_check_code()` generate snippets
  - Code injection happens at lines 2104-2122

**Real Issue**: The IR `behavior_model.flows` doesn't have `constraint_types: ['stock_constraint']` populated correctly from spec parsing. This is a spec→IR conversion issue, not a code generation issue.

---

## 📋 Implementation Summary

| # | Fix | File | Status |
|---|-----|------|--------|
| 1 | Remove docker-compose version | 5 files | ✅ Done |
| 2 | Remove LLM fallback (Compiler Mode) | real_e2e_full_pipeline.py | ✅ Done |
| 3 | Inject RuntimeFlowValidator | production_code_generators.py | ✅ Code exists |
| 4 | SERVICE repair injects code | smoke_repair_orchestrator.py | ✅ Code exists |
| 5 | LLM planner covers all endpoints | N/A | ❌ Removed (Compiler Mode) |

---

## 🔬 Root Cause Chain

```
Spec Parsing → ApplicationIR → BehaviorModel.flows
                                      ↓
                              constraint_types: [] (EMPTY!)
                                      ↓
                find_workflow_operations() → affects_stock: False
                                      ↓
               _generate_workflow_method_body() → NO stock check generated
                                      ↓
                        Smoke test fails on stock constraint
                                      ↓
                    Repair loop tries to inject code (works)
                                      ↓
                        BUT Docker was broken, so:
                                      ↓
                        IR smoke test returns None
                                      ↓
                        LLM fallback runs 11 trivial tests
                                      ↓
                        100% pass (fake success)
```

---

---

### Fix 4: ErrorClassifier Missing `constraint_graph` Attribute ✅

**Error**:
```
AttributeError: 'ErrorClassifier' object has no attribute 'constraint_graph'
```

**Root Cause**: `ErrorClassifier.__init__` didn't accept or initialize `constraint_graph`, but `_is_business_logic_error()` tried to use it.

**Fix Applied**:

1. Added `constraint_graph` parameter to `ErrorClassifier.__init__`:
```python
def __init__(self, log_parser=None, constraint_graph=None):
    self.log_parser = log_parser or ServerLogParser()
    self.constraint_graph = constraint_graph
```

2. Updated `SmokeRepairOrchestrator.__init__` to pass the reference after cognitive components are initialized:
```python
if COGNITIVE_COMPILER_AVAILABLE:
    # ... init components ...
    self.constraint_graph = ConstraintGraph()
    # Update error_classifier with constraint_graph reference
    self.error_classifier.constraint_graph = self.constraint_graph
```

---

## 🎯 Next Steps

1. **Run the test again** - All fixes applied
2. **Verify IR smoke test** - 85 scenarios should execute
3. **Verify repair loop** - Should now use Cognitive Compiler components
4. **Monitor convergence** - Check if violations decrease across cycles


