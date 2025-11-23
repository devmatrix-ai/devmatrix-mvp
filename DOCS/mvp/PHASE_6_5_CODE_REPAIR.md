# Phase 6.5: Code Repair (Optional)

**Purpose**: Fix syntax errors and test failures in generated code

**Status**: ✅ Optional (Graceful degradation if unavailable)

---

## Overview

Phase 6.5 is an optional improvement phase that runs tests on generated code and attempts to repair any failures. If CodeRepairAgent is available, it automatically fixes issues; otherwise, code proceeds to validation with potential failures.

## Input

- **Source**: Generated code files from Phase 6
- **Contains**: 40-60 files with potential syntax errors

## Processing

```python
async def _phase_6_5_code_repair(self):
    # 1. Run tests on generated code
    test_results = test_executor.run_tests(generated_code)

    # 2. If tests pass, skip repair
    if test_results.all_passed:
        return  # Skip repair

    # 3. If available, attempt repair
    if code_repair_agent:
        repaired_code = code_repair_agent.repair(
            code=generated_code,
            test_failures=test_results.failures
        )

    # 4. Update generated code with repairs
    generated_code = repaired_code
```

## Output

### Repair Results

```python
class RepairResults:
    original_failures: int       # Tests failed before repair
    repaired_failures: int       # Tests failed after repair
    repair_success_rate: float   # Percentage of fixed tests
    fixed_files: List[str]       # Files that were repaired
```

## Service Dependencies

### Required
- **TestResultAdapter** (`tests/e2e/adapters/test_result_adapter.py`)
  - Parse test execution results
  - Extract failure information
  - Format for repair agent

### Optional
- **CodeRepairAgent** (`src/mge/v2/agents/code_repair_agent.py`)
  - Repair broken code
  - Fix syntax errors
  - Resolve test failures
  - Learn from failures

## Repair Strategy

### Test Failure Types

| Type | Example | Fix |
|------|---------|-----|
| **Syntax** | `def func( missing colon` | Add missing syntax |
| **Import** | `from x import y (not found)` | Fix import path |
| **Type** | `str passed where int expected` | Add type conversion |
| **Logic** | `AssertionError in test` | Fix logic error |
| **Reference** | `NameError: undefined variable` | Define variable |

### Repair Iteration

```
Generated Code
    ↓
    └─ Run Tests
        ├─ Pass: Continue to Phase 7
        └─ Fail: Extract failures
            ↓
            └─ CodeRepairAgent.repair()
                ├─ Analyze failure
                ├─ Generate fix
                ├─ Apply patch
                └─ Return repaired code
                    ↓
                    └─ Re-run Tests
                        ├─ Pass: Continue to Phase 7
                        └─ Fail: Log, continue anyway
```

## Metrics Collected

- Tests run count
- Tests passed
- Tests failed (before repair)
- Tests failed (after repair)
- Repair success rate
- Repair time
- Files modified

## Performance Characteristics

- **Time**: 5-15 seconds (LLM dependent)
- **Memory**: ~200-400 MB
- **API Calls**: 2-5 Claude API calls
- **Cost**: $0.50-2 per repair attempt

## Error Handling

### Repair Failure

If repair agent fails:
1. Log failure details
2. Continue with original generated code
3. Phase 7 validation may catch issues
4. Phase 8 deployment may fail

### Test Execution Error

If tests cannot run:
1. Skip repair phase
2. Continue with generated code
3. Assume no critical failures

## Data Flow

```
Generated Project Files
    ↓
    └─ Run Tests
        ├─ test_models.py
        ├─ test_api.py
        └─ test_validation.py
            ↓
            └─ Test Results
                ├─ Failed: 3
                ├─ Passed: 47
                └─ Errors: [...]
                    ↓
                    If failures > 0 and CodeRepairAgent available:
                    └─ CodeRepairAgent.repair(failures)
                        ├─ Analyze each failure
                        ├─ Generate fix
                        ├─ Apply patch
                        └─ Return repaired code
                            ↓
                            └─ Re-run tests
                                ├─ Pass: Success
                                └─ Fail: Log, continue
                                    ↓
                                    Feeds to Phase 7
```

## Success Criteria

✅ Tests executed successfully
✅ Repair attempted if failures detected
✅ Repair success rate > 0% (any improvement)
✅ Code remains valid Python
✅ No new errors introduced

## Typical Repair Output

```
Code Repair Summary:
  Initial Test Run:
    - Tests executed: 50
    - Tests passed: 47
    - Tests failed: 3
    - Tests errors: 0
    - Pass rate: 94%

  Failures Detected:
    1. test_user_creation: ImportError (models.py:5)
    2. test_task_api: KeyError (routes.py:23)
    3. test_validation: NameError (validation.py:12)

  Repair Attempted (CodeRepairAgent):
    - Failures analyzed: 3
    - Fixes generated: 3
    - Patches applied: 3
    - Files modified: 3

  After Repair:
    - Tests executed: 50
    - Tests passed: 49
    - Tests failed: 1
    - Tests errors: 0
    - Pass rate: 98% (↑ 4%)

  Repair Success Rate: 67% (2 of 3 fixed)
```

## When to Skip Repair

Phase 6.5 is skipped if:
- ❌ CodeRepairAgent not available (optional service)
- ✅ All tests pass (no failures)
- ✅ User has `SKIP_CODE_REPAIR=true` env var

## Known Limitations

- ⚠️ Not all errors can be fixed automatically
- ⚠️ Repair may introduce new bugs
- ⚠️ Some failures require domain expertise
- ⚠️ Complex logic errors may not be fixable

## Fallback Behavior

If CodeRepairAgent unavailable:
1. Skip repair phase entirely
2. Continue with original generated code
3. Phase 7 validation will identify issues
4. Phase 8 deployment may fail

## Learning Integration

If available, repair attempts feed into learning system (Phase 10):
- Record what errors occurred
- Record what fixes worked
- Update error pattern store
- Improve future generation

## Next Phase

Output feeds to **Phase 7: Validation** which:
- Validates all generated code against spec
- Checks compliance
- Generates compliance report

---

**Last Updated**: 2025-11-23
**Source**: tests/e2e/real_e2e_full_pipeline.py:1913-2555
**Status**: Verified ✅
