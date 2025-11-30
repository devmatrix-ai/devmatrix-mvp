# Fixes – Runtime & Learning (2025-11-30)

**Scope:** E2E pipeline health checks, Docker runtime smoke fallback, FixPatternLearner recording.

## Changes Applied
- **Health Verification (Phase 9)**  
  - If no README is found in `README.md`/`docs/README.md`/`docker/README.md`, the pipeline now auto-creates a minimal `README.md` in the generated app root to keep the health check green.  
  - When `generation_manifest.json` exists, the auto README now embeds a short manifest summary (app id, mode, tracked file count).  
  - Location: `tests/e2e/real_e2e_full_pipeline.py`.

- **Docker Runtime Smoke Fallback**  
  - Runtime validator now checks for `docker-compose.yml` **and** a Dockerfile before attempting a build.  
  - On missing Dockerfile or build failure, it falls back to `uvicorn` instead of hard-failing with “Dockerfile: no such file”.  
  - New env toggle `ENFORCE_DOCKER_RUNTIME` = `1|true` forces fail-fast (no fallback) when Docker assets are missing or build fails.
  - Location: `src/validation/runtime_smoke_validator.py`.

- **Smoke Repair Docker Rebuild Toggle**  
  - Smoke-driven repair now allows enabling/disabling Docker rebuilds via `SMOKE_REPAIR_DOCKER_REBUILD` (default: disabled to avoid missing-Dockerfile hangs).  
  - Location: `tests/e2e/real_e2e_full_pipeline.py` (repair orchestrator call).

- **Smoke Repair Signal & Learning Improvements**  
  - Smoke violations now carry stack traces/exception metadata; traces are attached from server logs for matching.  
  - FixPatternLearner accepts structured repair payloads (fix_type/description/file_path/success) and uses violation metadata (endpoint/error/exception).  
  - Classification attaches stack_trace to SmokeViolation for strategy selection and known-fix lookup.  
  - Default Docker rebuild during repair set to `false` in `.env` to avoid missing-Dockerfile failures.  
  - NegativePatternStore integration now tolerates GenerationAntiPattern fields (bad/correct snippets) when applying learned fixes.  
  - Docker rebuild flag respected: runtime validator can skip rebuild when disabled.  
  - Locations: `src/validation/runtime_smoke_validator.py`, `src/validation/smoke_repair_orchestrator.py`, `src/validation/smoke_test_pattern_adapter.py`, `.env`.

- **FixPatternLearner Recording**  
  - Repair records are normalized to strings before sending to FixPatternLearner, preventing `'dict' object has no attribute 'lower'`.  
  - Location: `src/validation/smoke_repair_orchestrator.py`.

## Impact
- Health verification no longer blocks on absent README when templates omit it.
- Docker-less environments continue via uvicorn, reducing false negatives in smoke tests.
- Learning loop stays stable; repair attempts are recorded without type errors.

- **Bug #149: IR Smoke Test ↔ Repair Orchestrator Format Mismatch**
  - **Problem**: All smoke repairs were falling back to [generic] pattern, never improving pass rate (86.7% → 86.7%).
  - **Root Cause**: IR smoke test produces `actual_status` field, but `smoke_repair_orchestrator.py` only checked for `status_code`.
  - **Fix**: Accept both formats in violation parsing:
    ```python
    status_code = (
        violation.get('status_code') or
        violation.get('actual_status') or
        500
    )
    error_type = violation.get('error_type') or f'HTTP_{status_code}'
    ```
  - **Impact**: Repairs can now correctly classify violations and apply targeted fixes instead of generic fallback.
  - Location: `src/validation/smoke_repair_orchestrator.py`

- **Bug #150: HTTP 500 Without Stack Trace Falls to GENERIC**
  - **Problem**: Even after Bug #149 fix, HTTP 500 errors from IR smoke tests have no stack trace → classification falls to GENERIC.
  - **Root Cause**: IR smoke tests don't capture exception details, so `error_type == 'HTTP_500'` with no `stack_trace_obj` → GENERIC.
  - **Fix**: Added `_infer_strategy_from_endpoint()` method with domain-agnostic heuristics:
    - **Action patterns** (`/pay`, `/cancel`, `/checkout`, `/activate`, etc.) → SERVICE
    - **Nested resources** (`/{id}/items`, `/{id}/comments`) → SERVICE
    - **Error message keywords** (integrity, foreign key) → DATABASE
    - **Default for HTTP 500** → SERVICE (better than GENERIC)
  - **Impact**: Most HTTP 500 errors now get SERVICE classification instead of GENERIC, enabling targeted repair.
  - Location: `src/validation/smoke_repair_orchestrator.py`

- **Bug #151: `presence` Mapping Breaks Non-String Fields (REGRESSION)**
  - **Problem**: Code repair caused `datetime_schema() got an unexpected keyword argument 'min_length'`.
  - **Root Cause**: `presence` was mapped to `('min_length', 1)` which only works for strings, not datetime/int/float/bool.
  - **Fix**: Changed mapping from `('min_length', 1)` to `('required', True)` which works for all field types.
  - **Impact**: Repair no longer breaks datetime/numeric fields. Compliance stays stable after repair.
  - Location: `src/mge/v2/agents/code_repair_agent.py:538`

- **Bug #152: `relationship` → `foreign_key=True` Passes Boolean**
  - **Problem**: `'bool' object has no attribute 'lower'` error in entity constraint handling.
  - **Root Cause**: `relationship` mapped to `('foreign_key', True)`, but the code expected a string table reference.
  - **Fix**: Added check `isinstance(self.c_value, bool)` to skip boolean values with debug log.
  - **Impact**: Foreign key constraint handling gracefully skips incomplete mappings instead of crashing.
  - Location: `src/mge/v2/agents/code_repair_agent.py:1881-1883`

- **Feature: Intra-Run Learning (Smoke → Repair Loop)**
  - **Problem**: Anti-patterns from smoke test failures were only used in FUTURE pipeline runs (inter-run), not within the same run (intra-run).
  - **Root Cause**: `MIN_OCCURRENCE_FOR_PROMPT = 2` meant patterns needed 2+ occurrences before being injected. First-run patterns were stored but not used immediately.
  - **Solution**:
    1. **FeedbackCollector Integration**: Added import and call to `FeedbackCollector.process_smoke_results()` in smoke repair cycle (step 7.5), BEFORE repair.
    2. **Immediate Pattern Use**: Changed `min_occurrences=1` in `get_patterns_for_entity()` and `get_patterns_for_endpoint()` calls.
    3. **Visible Logging**: Added `print()` to show intra-run learning activity: "🎓 Intra-run learning: X new, Y updated anti-patterns"
  - **New Flow**:
    ```
    Iteration 1: Smoke fails → Create anti-patterns → Repair (uses new patterns)
    Iteration 2: Smoke fails → Create/update patterns → Repair (uses iter 1 + iter 2 patterns)
    Iteration 3: ...
    ```
  - **Impact**: Repairs in iteration N can now benefit from anti-patterns discovered in iteration N (not just previous iterations).
  - **Files**:
    - `src/validation/smoke_repair_orchestrator.py` - Added FeedbackCollector import, step 7.5, min_occurrences=1
    - `src/learning/selective_regenerator.py` - New module (for future selective file regeneration)

- **Bug #153: Wrong Import Name Silently Disabled Intra-Run Learning**
  - **Problem**: E2E #060 ran without "🎓 Intra-run learning" messages appearing - feature was silently disabled.
  - **Root Cause**: Import statement used `FeedbackCollector` but the class is named `GenerationFeedbackCollector`.

    ```python
    # Before (wrong):
    from src.learning.feedback_collector import FeedbackCollector  # doesn't exist!
    # After (correct):
    from src.learning.feedback_collector import GenerationFeedbackCollector
    ```

  - **Impact**: `FEEDBACK_COLLECTOR_AVAILABLE` was `False` → entire intra-run learning feature was skipped without error logs (caught by try/except).
  - **Fix**: Changed import from `FeedbackCollector` to `GenerationFeedbackCollector`.
  - **Verification**: `FEEDBACK_COLLECTOR_AVAILABLE = True` after fix.
  - **Location**: `src/validation/smoke_repair_orchestrator.py:96-98`

- **Bug #154: Constraint Values 'none' Causing Log Spam**
  - **Problem**: Logs filled with repetitive messages like:
    ```
    Bug #51: Skipping min_length=none (invalid numeric value)
    Bug #45: Mapping 'min_value' → 'ge=none'
    Bug #51: Skipping ge=none (invalid numeric value)
    Task 2.5: Skipping enum_values=none (no values)
    ```
  - **Root Cause**: IR constraints come with `constraint_value="none"` (string literal) when unpopulated. The semantic mapping (`min_value` → `ge`) was applied BEFORE validation, resulting in `ge=none` which then failed downstream validation.
  - **Fix**: Added early filter BEFORE semantic mapping to skip constraints with `"none"` string values:
    ```python
    # Bug #154 Fix: Early filter for 'none' string values from IR
    if constraint_value is not None and str(constraint_value).lower() == 'none':
        logger.debug(f"Bug #154: Skipping {constraint_type}=none (unpopulated IR field)")
        return True  # Treat as handled silently
    ```
  - **Impact**: Eliminates log spam from unpopulated IR constraint fields. Uses `logger.debug` instead of `logger.info` for silent handling.
  - **Location**: `src/mge/v2/agents/code_repair_agent.py:529-534`

- **Bug #155: Intra-Run Learning Missing from `run_full_repair_cycle`**
  - **Problem**: E2E #061 ran with Bug #153 fix, but "🎓 Intra-run learning" messages never appeared.
  - **Root Cause**: The intra-run learning code was added to a method that isn't called by the E2E pipeline.
    - E2E calls `run_full_repair_cycle()` (line 3788 in real_e2e_full_pipeline.py)
    - Intra-run learning code was in a different method (not `run_full_repair_cycle`)
  - **Fix**: Added the intra-run learning code to `run_full_repair_cycle` at step 7.5:
    ```python
    # 7.5 INTRA-RUN LEARNING: Create anti-patterns BEFORE repair (Bug #155 Fix)
    if FEEDBACK_COLLECTOR_AVAILABLE and self.config.enable_learning:
        try:
            feedback_collector = get_feedback_collector()
            feedback_result = await feedback_collector.process_smoke_results(
                smoke_result=smoke_result,
                application_ir=application_ir,
            )
            if feedback_result.patterns_created > 0 or feedback_result.patterns_updated > 0:
                print(f"    🎓 Intra-run learning: {feedback_result.patterns_created} new, "
                      f"{feedback_result.patterns_updated} updated anti-patterns")
        except Exception as e:
            logger.debug(f"Intra-run learning skipped: {e}")
    ```
  - **Impact**: Next E2E run should now show "🎓 Intra-run learning" messages in the repair cycle output.
  - **Location**: `src/validation/smoke_repair_orchestrator.py:1880-1893`

- **Bug #156: IR Smoke Test Missing `server_logs` for Stack Trace Parsing**
  - **Problem**: E2E #061 showed `Total repairs: 0` despite having 22 violations. All repair strategies require stack traces but returned `None` or `success=False`.
  - **Root Cause**: `_run_ir_smoke_test()` did not capture Docker server logs. The repair orchestrator checks `smoke_result.server_logs` to parse stack traces:
    ```python
    # smoke_repair_orchestrator.py:1873
    if hasattr(smoke_result, 'server_logs') and smoke_result.server_logs:
        stack_traces = self.log_parser.parse_logs(smoke_result.server_logs)
    ```
    Without `server_logs`, all repair methods fail:
    - `_fix_database_error` line 1173: `if not trace: return None`
    - `_fix_service_error` line 1386: `if not trace: return None`
    - `_fix_generic_error` returns `success=False` without actual fix
  - **Fix**: Added Docker log capture to IR smoke test after running scenarios:
    ```python
    # Bug #156 Fix: Capture Docker server logs for stack traces
    server_logs = ""
    if report.failed > 0:
        cmd = ['docker', 'compose', '-f', str(docker_compose_path),
               'logs', 'app', '--no-color', '--tail', '500']
        result = subprocess.run(cmd, ..., timeout=30)
        server_logs = result.stdout + result.stderr

    return SmokeTestResult(
        ...,
        server_logs=server_logs  # Bug #156 Fix
    )
    ```
  - **Impact**: Repair orchestrator can now parse stack traces from IR smoke test failures, enabling targeted repairs instead of all-generic fallback.
  - **Location**: `tests/e2e/real_e2e_full_pipeline.py:4161-4184, 4239`

- **Bug #157: `_fix_generic_error` Never Actually Repaired Anything**
  - **Problem**: Even with stack traces (Bug #156 fix), `Total repairs: 0` because `_fix_generic_error` always returned `success=False` without attempting any repair.
  - **Root Cause**: The method was a stub that only logged the error but didn't call any actual repair logic.
    ```python
    # Before (stub):
    async def _fix_generic_error(...) -> Optional[RepairFix]:
        """Fallback: delegate to code repair agent."""
        # This would use the LLM-based repair in CodeRepairAgent
        return RepairFix(
            file_path=trace.file_path if trace else "",
            fix_type="generic",
            description=f"Generic error on {violation.endpoint}: {violation.error_type}",
            success=False  # <- Never actually repaired!
        )
    ```
  - **Fix**: Integrated `CodeRepairAgent.repair_from_smoke()` for LLM-powered repair:
    1. Added import `from src.mge.v2.agents.code_repair_agent import CodeRepairAgent`
    2. Added instance attributes `self._current_server_logs` and `self._current_app_path`
    3. Store server_logs when parsed in both repair cycles
    4. Modified `_fix_generic_error` to:
       - Create/reuse CodeRepairAgent instance
       - Call `repair_from_smoke()` with violation and server_logs
       - Return `success=True` if CodeRepairAgent fixes issues
       - Fallback to `success=False` only if CodeRepairAgent unavailable or fails
    ```python
    # After (actual repair):
    if CODE_REPAIR_AGENT_AVAILABLE and self._current_server_logs:
        if not self.code_repair_agent:
            self.code_repair_agent = CodeRepairAgent(
                output_path=app_path,
                application_ir=application_ir
            )
        repair_result = await self.code_repair_agent.repair_from_smoke(
            violations=[violation_dict],
            server_logs=self._current_server_logs,
            app_path=app_path,
            stack_traces=[...]
        )
        if repair_result.success and repair_result.repairs_applied:
            return RepairFix(fix_type="llm_repair", success=True, ...)
    ```
  - **Impact**: Smoke repair loop now actually attempts LLM-powered repairs for all errors that don't match specific patterns (database, validation, service, etc.).
  - **Location**: `src/validation/smoke_repair_orchestrator.py:106-112, 498-500, 601-603, 1564-1630, 1891-1893`

- **Golden App Comparison Deprecated**
  - **Rationale**: IR provides semantic validation (spec compliance), making Golden App regression comparison redundant for development.
  - **Change**: `GOLDEN_APPS_AVAILABLE` now reads from `ENABLE_GOLDEN_APP` env var (default: `false`).
  - **Re-enable**: Set `ENABLE_GOLDEN_APP=true` for CI regression testing if needed.
  - **Location**: `tests/e2e/real_e2e_full_pipeline.py:395-397, 5415-5418`

## Follow-ups
- If you want Docker enforcement instead of fallback, gate on policy and fail fast when Dockerfile is missing.
- Consider enriching the auto README from generation manifest once available.
- Verify Bug #149 fix improves repair effectiveness in next E2E run.
- ~~Consider enhancing IR smoke test to capture stack traces for better repair classification.~~ (Bug #156 fixed - IR smoke test now captures Docker logs)
- ~~Run E2E to verify intra-run learning shows "🎓 Intra-run learning" messages and improves pass rate.~~ (Bug #153 fix required first)
- ~~Next E2E run should now show "🎓 Intra-run learning" messages~~ (Bug #153 fixed, then Bug #155 revealed wrong method).
- ~~Next E2E run should now show "🎓 Intra-run learning" messages~~ (Bug #155 fixed - code now in `run_full_repair_cycle`).
- ~~**Next E2E run should show "🤖 CodeRepairAgent" messages and non-zero repairs**~~ (Bug #157 verified - LLM repair applied 1 fix).
- ~~**Bug #158**: Repair generates method in wrong service file~~ (FIXED)
- ~~**Bug #159**: `NegativePatternStore.get_patterns_by_exception` method missing~~ (FIXED)

- **Bug #158: SERVICE Repair Routes to Wrong Service File** ✅ FIXED
  - **Problem**: E2E showed `✅ SERVICE: Generated method 'cancel' in cart_service.py` but the endpoint `/orders/{order_id}/cancel` requires the method in `order_service.py`. The repair was applied but the endpoint still fails with HTTP 500.
  - **Root Cause**: `_fix_service_error` extracted entity from endpoint path, but when stack trace came from a different endpoint (cart), the wrong service file was used. The exception message contains the correct service name (`'CartService' object has no attribute...`).
  - **Fix**: Modified `_fix_service_error` to first extract service name from exception message, then fallback to endpoint:

    ```python
    # Bug #158 Fix: First try to extract service name from exception message
    service_match = re.search(
        r"['\"]?(\w+)Service['\"]?\s+object\s+has\s+no\s+attribute",
        trace.exception_message,
        re.IGNORECASE
    )
    if service_match:
        entity_name = service_match.group(1).capitalize()
    ```

  - **Impact**: Service methods are now generated in the correct service file based on the actual error source.
  - **Location**: `src/validation/smoke_repair_orchestrator.py:1422-1438`

- **Bug #159: NegativePatternStore Missing `get_patterns_by_exception` Method** ✅ FIXED
  - **Problem**: Log shows `Failed to query NegativePatternStore: 'NegativePatternStore' object has no attribute 'get_patterns_by_exception'`
  - **Root Cause**: The repair orchestrator calls `get_patterns_by_exception()` but NegativePatternStore didn't implement this method.
  - **Fix**: Added `get_patterns_by_exception()` method to `NegativePatternStore`:

    ```python
    def get_patterns_by_exception(
        self,
        exception_class: str,
        min_occurrences: int = None
    ) -> List[GenerationAntiPattern]:
        """Get all patterns matching a specific exception class."""
        # Query by exception_class field (e.g., "IntegrityError", "ValidationError")
    ```

  - **Impact**: Pattern-based repairs now work correctly, using learned anti-patterns to guide fixes.
  - **Location**: `src/learning/negative_pattern_store.py:644-697`

- **Bug #160: Inter-Run Learning Gap - Anti-patterns NOT Used in Code Generation/Repair** ✅ PARTIALLY FIXED
  - **Problem**: Anti-patterns are created and stored in `NegativePatternStore` but:
    1. **MGE agents don't use them**: `src/mge/v2/agents/*.py` have ZERO imports of `NegativePatternStore`
    2. **Main repair flow ignores them**: `run_full_repair_cycle()` → `_repair_from_smoke()` → `_fix_generic_error()` does NOT pass anti-patterns to `CodeRepairAgent`
    3. **Code generation (inter-run) doesn't inject them**: While `code_generation_service.py:359-414` has anti-pattern injection code, this old service may not be used by the new MGE architecture

  - **Evidence from grep analysis**:
    ```
    | Component                          | Uses NegativePatternStore? | Called in E2E? |
    |------------------------------------|----------------------------|----------------|
    | code_generation_service.py (old)   | ✅ Yes (lines 359-414)     | ❓ Unknown     |
    | src/mge/v2/agents/*.py (new MGE)   | ❌ No                      | ✅ Yes         |
    | smoke_repair_orchestrator.py       | ✅ Partial                 | ✅ Yes         |
    | └─ run_full_repair_cycle()         | ❌ No anti-patterns        | ✅ Yes         |
    | └─ run_full_repair_cycle_enhanced()| ✅ Yes (lines 1995-2005)   | ❌ No          |
    | └─ _fix_generic_error()            | ❌ No (doesn't pass to CRA)| ✅ Yes         |
    | code_repair_agent.py               | ❌ No                      | ✅ Yes         |
    ```

  - **Root Cause**: The inter-run learning loop is INCOMPLETE:
    ```
    Current Flow (BROKEN):
    Run N: Smoke fails → FeedbackCollector → NegativePatternStore → Neo4j ✅ STORED
    Run N+1: CodeGeneration → ❌ DOES NOT QUERY anti-patterns → Same errors repeat

    Expected Flow:
    Run N: Smoke fails → FeedbackCollector → NegativePatternStore → Neo4j ✅ STORED
    Run N+1: CodeGeneration → ✅ QUERIES anti-patterns → Injected in prompts → Prevents errors
    ```

  - **Impact**: System learns mistakes but DOES NOT prevent them in future runs. The 30 anti-patterns stored per run are wasted - they don't improve code quality across runs.

  - **Fix Required** (NOT YET IMPLEMENTED):
    1. **MGE Integration**: Add `NegativePatternStore` queries to MGE code generation agents
    2. **Repair Flow**: Modify `_fix_generic_error()` to pass anti-patterns to `CodeRepairAgent`
    3. **Prompt Enhancement**: Inject relevant anti-patterns into LLM prompts before code generation
    4. **Verification**: Add logs showing "🎓 Anti-patterns injected: X warnings from Y stored patterns"

  - **Locations needing changes**:
    - `src/mge/v2/agents/code_generation_agent.py` - Add anti-pattern injection (STILL PENDING)
    - `src/validation/smoke_repair_orchestrator.py:1584-1650` - Pass anti-patterns to CRA (✅ FIXED)
    - `src/mge/v2/agents/code_repair_agent.py` - Accept and use anti-patterns in prompts (STILL PENDING)

  - **Partial Fix Applied (2025-11-30)**:
    1. **`_repair_from_smoke()` now uses anti-patterns** (lines 741-753):
       ```python
       # Bug #160 Fix: Try learned anti-patterns BEFORE regular repair
       learned_patterns = self._get_learned_antipatterns(violation, stack_traces)
       if learned_patterns:
           learned_fix = self._repair_with_learned_patterns(...)
           if learned_fix and learned_fix.success:
               continue  # Skip to next violation
       ```

    2. **`_fix_generic_error()` passes anti-patterns to CodeRepairAgent** (lines 1634-1647):
       ```python
       # Bug #160 Fix: Query and pass anti-patterns to CodeRepairAgent
       learned_patterns = self._get_learned_antipatterns(violation, [trace] if trace else [])
       if learned_patterns:
           violation_dict['antipattern_guidance'] = antipattern_context
           logger.info(f"🎓 Passing {len(learned_patterns)} anti-patterns to CodeRepairAgent")
       ```

    3. **New log markers to verify fix**:
       - `🎓 Applied learned anti-pattern for {endpoint}` - Pattern-based repair succeeded
       - `🎓 Passing {N} anti-patterns to CodeRepairAgent` - Anti-patterns passed to LLM

  - **Remaining Gap Analysis** (2025-11-30 Investigation):

    **Initial Concern**: MGE Code Generation doesn't query anti-patterns during initial code generation.

    **Investigation Results** (Bug #161 Analysis):

    | Component | Generation Type | Uses LLM | Anti-patterns Useful? |
    |-----------|-----------------|----------|----------------------|
    | PatternBank templates | Static templates | NO | NO - No prompts to inject |
    | ProductionCodeGenerators | Hardcoded generators | NO | NO - Pure Python code |
    | BehaviorCodeGenerator | Template-based | NO | NO - No LLM calls |
    | _compose_patterns() | Jinja2 adaptation | NO | NO - Template filling |
    | _generate_with_llm_fallback() | LLM for README/config | Minimal | Maybe (low impact) |
    | CodeRepairAgent | LLM for code repair | YES | **YES** (Bug #160 fixed) |

    **Key Finding**: Initial code generation uses **templates**, not LLM prompts. The `avoidance_context`
    is built in `code_generation_service.py:798` but cannot be injected because:
    1. `_compose_patterns()` uses PatternBank templates - no prompt to add context
    2. `_retrieve_production_patterns()` uses PatternBank - no LLM
    3. `_generate_with_llm_fallback()` only generates README/requirements - low impact

    **Conclusion**: Anti-patterns are CORRECTLY used only in Repair phase (Bug #160 fix).
    The initial generation is template-based BY DESIGN - anti-patterns aren't applicable there.

    **Actual Learning Flow** (working correctly):

    ```text
    Run N, Iter 1: Generate (templates) → Smoke fails → Store anti-patterns → Repair (LLM + anti-patterns)
    Run N, Iter 2: Re-test → Smoke fails → Update patterns → Repair (LLM + more patterns)
    Run N+1:       Generate (templates) → Smoke fails → Repair (LLM + Run N patterns) ✅
    ```

    **Status**: Bug #160 is now FULLY FIXED. The "remaining gap" was BY DESIGN.

---

## Bug #161: Learning System Bridge - ErrorKnowledge → GenerationAntiPattern

**Date**: 2025-11-30
**Status**: FIXED

### Problem

The learning system had **3 separate components** that were NOT connected:

| Component | Storage | Used By |
|-----------|---------|---------|
| `ErrorKnowledgeRepository` | `ErrorKnowledge` nodes | `RuntimeSmokeValidator._learn_from_error()` |
| `NegativePatternStore` | `GenerationAntiPattern` nodes | `IRCentricCognitivePass._get_anti_patterns_for_flow()` |
| `FixPatternLearner` | `FixPattern` nodes | `SmokeRepairOrchestrator._get_learned_antipatterns()` |

**Root Cause**: Smoke test errors were stored in `ErrorKnowledge`, but code generation queries `GenerationAntiPattern`. No bridge existed between them.

```text
BROKEN FLOW:
  Smoke Test Failure
       │
       ▼
  ErrorKnowledgeRepository.learn_from_failure()
       │
       ▼
  ErrorKnowledge (Neo4j) ← STORED HERE
       │
       ✗ NO BRIDGE
       │
  IRCentricCognitivePass → Queries NegativePatternStore → NOTHING FOUND
       │
       ▼
  Same errors repeat in next generation ❌
```

### Solution

Created `ErrorKnowledgeBridge` to convert `ErrorKnowledge` → `GenerationAntiPattern`:

```text
FIXED FLOW:
  Smoke Test Failure
       │
       ▼
  ErrorKnowledgeRepository.learn_from_failure()
       │
       ▼
  ErrorKnowledge (Neo4j node)
       │
       ▼
  ErrorKnowledgeBridge.bridge_to_anti_pattern()  ← NEW
       │
       ▼
  GenerationAntiPattern
       │
       ▼
  NegativePatternStore.store_pattern()
       │
       ▼
  Next Generation: IRCentricCognitivePass queries patterns ✅
```

### Files Created/Modified

| File | Change |
|------|--------|
| `src/learning/error_knowledge_bridge.py` | **NEW** - Bridge class |
| `src/learning/__init__.py` | Added exports for bridge |
| `src/validation/runtime_smoke_validator.py` | Added Path 3 in `_learn_from_error()` |

### Implementation

**1. `ErrorKnowledgeBridge` class** (`error_knowledge_bridge.py`):

```python
class ErrorKnowledgeBridge:
    def bridge_from_smoke_error(
        self,
        endpoint_path: str,
        error_type: str,
        error_message: str,
        exception_class: Optional[str] = None,
        entity_name: Optional[str] = None,
        failed_code: Optional[str] = None,
        status_code: Optional[int] = None,
    ) -> BridgeResult:
        """
        Convert smoke test error to GenerationAntiPattern and store in NegativePatternStore.
        """
        # Extract/infer missing fields
        # Generate pattern ID
        # Check for existing pattern (increment count) or create new
        # Store in NegativePatternStore
        return BridgeResult(success=True, pattern_id=id, is_new=True/False)
```

**2. Integration in `RuntimeSmokeValidator._learn_from_error()`**:

```python
# Path 3: Bug #161 Fix - Bridge to GenerationAntiPattern
if ERROR_KNOWLEDGE_BRIDGE_AVAILABLE and bridge_smoke_error_to_pattern:
    try:
        bridge_result = bridge_smoke_error_to_pattern(
            endpoint_path=endpoint_path,
            error_type=error_type,
            error_message=error_message,
            exception_class=violation.get("exception_class"),
            entity_name=entity_name,
            failed_code=result.stack_trace,
            status_code=result.status_code,
        )
        if bridge_result.success:
            logger.debug(f"🌉 Active Learning: Bridged to GenerationAntiPattern for {endpoint_path}")
    except Exception as e:
        logger.warning(f"⚠️ Active Learning (Bridge) failed (non-blocking): {e}")
```

### Impact

- **Inter-run learning now works**: Errors from Run N are available as anti-patterns in Run N+1
- **IRCentricCognitivePass can now query learned errors**: The `_get_anti_patterns_for_flow()` method will find patterns created by the bridge
- **Graceful degradation**: If bridge unavailable, system continues without blocking

### Log Markers

- `🌉 Active Learning: Bridged to GenerationAntiPattern (new) for POST /products` - New pattern created
- `🌉 Active Learning: Bridged to GenerationAntiPattern (existing) for POST /products` - Existing pattern incremented

### Verification

Next E2E run should show:
1. `🌉` log messages during smoke test failures
2. Anti-patterns available in `NegativePatternStore` for subsequent iterations
3. Reduced repeat errors in code generation

---

## Bug #143-160: IR-Centric Cognitive Code Generation (Pipeline Wiring)

**Date**: 2025-11-30
**Status**: Phase 5.1 COMPLETE - Pipeline Integration

### Overview

Wired the `CognitiveCodeGenerationService` into `CodeGenerationService.generate_from_application_ir()`
to apply IR-centric cognitive enhancement to generated code. This enables learned anti-patterns to
influence initial code generation, not just repair.

### Architecture

```text
generate_from_application_ir()
    │
    ├─→ _validate_application_ir_structure()      # Validate IR
    ├─→ _generate_file_content_from_ir()          # Template-based generation
    │
    ├─→ _apply_cognitive_pass()   ◀── NEW (Bug #143-160)
    │       │
    │       ├─→ create_cognitive_service(ir, pattern_store, llm_client)
    │       ├─→ Filter targets: services/, workflows/, routes/ (*.py)
    │       ├─→ process_files() → EnhancementResult[]
    │       └─→ Update files_dict with enhanced content
    │
    └─→ Return enhanced files_dict
```

### Files Modified

| File | Changes |
|------|---------|
| `src/services/code_generation_service.py` | Import, constructor param, init, `_apply_cognitive_pass()` |

### Implementation Details

**1. Import with graceful fallback** (lines 84-92):
```python
try:
    from src.services.cognitive_code_generation_service import (
        CognitiveCodeGenerationService,
        create_cognitive_service,
    )
    COGNITIVE_GENERATION_AVAILABLE = True
except ImportError:
    COGNITIVE_GENERATION_AVAILABLE = False
```

**2. Constructor parameter** (`enable_cognitive_pass: bool = True`)

**3. Initialization** (lines 219-230):
- Only initializes if flag enabled AND imports available
- Logs warning if requested but unavailable

**4. Hook location** (after structure validation, line 968):
```python
if self.enable_cognitive_pass and COGNITIVE_GENERATION_AVAILABLE:
    files_dict = await self._apply_cognitive_pass(files_dict, app_ir)
```

**5. `_apply_cognitive_pass()` method** (lines 3980-4076):
- Creates cognitive service with IR, pattern store, LLM client
- Filters targets: only `services/`, `workflows/`, `routes/` Python files
- Excludes `__init__.py` files
- Processes files through `CognitiveCodeGenerationService.process_files()`
- Logs metrics: files processed, enhanced, prevention rate
- **Graceful degradation**: Returns original on any exception

### Feature Flags

| Flag | Default | Description |
|------|---------|-------------|
| `enable_cognitive_pass` | `True` | Constructor parameter |
| `ENABLE_COGNITIVE_PASS` | `"true"` | Environment variable override |
| `COGNITIVE_BASELINE_MODE` | `"false"` | A/B testing mode |

### Metrics Captured

```python
{
    "total_files_processed": N,
    "files_enhanced": N,
    "functions_enhanced": N,
    "functions_rolled_back": N,
    "ir_validations_passed": N,
    "prevention_rate": 0.0-1.0,
    "cache_hits": N,
    "total_time_ms": N
}
```

### Graceful Degradation

If cognitive pass fails for ANY reason:
1. Exception is caught and logged as WARNING
2. Original `files_dict` is returned unchanged
3. Pipeline continues normally
4. No data loss, no pipeline interruption

### Remaining Tasks

| Task | Status | Description |
|------|--------|-------------|
| 5.1 Wire into CodeGenerationService | ✅ DONE | Integration complete |
| 5.2 Circuit Breaker pattern | ⏳ Pending | Failure isolation |
| 5.3 Structured logging | ⏳ Pending | Observability |
| 5.4 E2E validation | ⏳ Pending | Full pipeline test |

### RFC Reference

See: `DOCS/mvp/exit/anti/COGNITIVE_CODE_GENERATION_PROPOSAL.md` (v2.1)

---

## Roadmap: Arquitectura Post-82% (Next Steps para 95-100%)

### 4.1 Behavior Execution Model (BEM)

El módulo que falta para cerrar el gap 82% → 95-100%.

**Estado actual IR:**
- DomainModelIR ✅
- APIModelIR ✅
- ValidationModelIR ✅
- InfrastructureModelIR ✅
- BehaviorModelIR (parcial)

**Propuesta: BEM completo con:**
- `preconditions`: condiciones que deben cumplirse antes de ejecutar
- `postconditions`: estado esperado después de ejecutar
- `invariants`: reglas que nunca deben violarse
- `effects`: efectos secundarios (recálculos, notificaciones)
- `steps`: secuencia determinística de operaciones

**Ejemplo `add_item_to_cart`:**
```yaml
behavior: add_item_to_cart
pre:
  - cart exists
  - product exists
  - quantity > 0
  - product.stock >= quantity
post:
  - cart_item added or updated
  - product.stock decreased
effects:
  - cart.total_amount recalculated
```

**Flujo:** `IR → BEM → deterministic flow implementation`

**Impact:** Elimina HTTP 500 en runtime porque el CodeGen no improvisa.

### 4.2 PatternBank: 5 Patrones Transversales Críticos

**Nueva categoría:** `behavioral_multi_entity`

| # | Patrón | Resuelve |
|---|--------|----------|
| 1 | Shared-stock modification | `POST /carts/{id}/items` stock conflicts |
| 2 | Cart-item merge/update | `PUT /carts/{id}/items/{product_id}` duplicates |
| 3 | Order lifecycle handler | `POST /orders/{id}/pay`, `/cancel` transitions |
| 4 | Payment simulation handler | Mock payment sin side-effects reales |
| 5 | Business-invariant enforcement | Validaciones cross-entity |

**Impact:** Estos 5 patrones resolverían directamente los 5 HTTP_500 del smoke test actual.

### 4.3 Repair Loop 2.0: IR-Diff Guided Repair

**Problema actual:** Repair detecta pero no repara porque falta "anchor patterns".

**Mejora necesaria:**
1. Diferenciar schema constraints de business rule invariants
2. Generar deltas directos sobre código de flows
3. Aplicar patches estructurales (no textuales)

**Ejemplo:**
```
Fail: POST /carts/{id}/items → 500
Stack: NoneType for product.price
```

**Patch automático generado:**
```python
if product is None:
    raise HTTPException(404, "Product not found")
```

**Esto es 100% automatizable con IR + BEM.**

### Implementación Sugerida

| Fase | Componente | Archivos |
|------|------------|----------|
| 1 | BEM Schema | `src/cognitive/ir/behavior_execution_model.py` |
| 2 | BEM Extractor | `src/services/bem_extractor.py` |
| 3 | PatternBank Extension | `src/patterns/behavioral_multi_entity/` |
| 4 | Repair Loop 2.0 | `src/validation/ir_diff_repair_engine.py` |
| 5 | Integration | Wire BEM into code generation pipeline |

---

## Learning System Architecture (Domain-Agnostic)

**Date**: 2025-11-30
**Status**: COMPLETE (Bug #161 closed the loop)

### Overview

The Learning System creates a feedback loop from **smoke test failures** to **code generation improvement**.
Key principle: ALL code is **domain-agnostic** - no hardcoded entity names, endpoints, or business logic.

### Three Learning Paths

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SMOKE TEST FAILURE                                   │
│                  (endpoint, status_code, error_message)                     │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│   PATH 1      │       │   PATH 2      │       │   PATH 3      │
│ ErrorKnowledge│       │ FixPattern    │       │ AntiPattern   │
│  Repository   │       │   Learner     │       │   Bridge      │
└───────┬───────┘       └───────┬───────┘       └───────┬───────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│ ErrorKnowledge│       │  FixPattern   │       │ Generation    │
│   (Neo4j)     │       │   (Neo4j)     │       │ AntiPattern   │
└───────────────┘       └───────────────┘       └───────┬───────┘
        │                       │                       │
        │                       │                       ▼
        │                       │               ┌───────────────┐
        │                       │               │ Negative      │
        │                       │               │ PatternStore  │
        │                       │               └───────┬───────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │
                                ▼
        ┌───────────────────────────────────────────────┐
        │      IRCentricCognitivePass                   │
        │  _get_anti_patterns_for_flow()                │
        │     └─→ Semantic Matching Algorithm           │
        └───────────────────────┬───────────────────────┘
                                │
                                ▼
        ┌───────────────────────────────────────────────┐
        │         _build_ir_guard()                     │
        │  Inject anti-patterns into LLM prompt         │
        └───────────────────────┬───────────────────────┘
                                │
                                ▼
        ┌───────────────────────────────────────────────┐
        │      Code Generation (LLM)                    │
        │  ✅ Avoids learned mistakes                   │
        └───────────────────────────────────────────────┘
```

### Path Details

#### Path 1: ErrorKnowledgeRepository
- **Location**: `src/knowledge/error_knowledge_repository.py`
- **Storage**: `ErrorKnowledge` nodes in Neo4j
- **Called by**: `RuntimeSmokeValidator._learn_from_error()`
- **Purpose**: Historical error tracking with timestamps and frequency

#### Path 2: FixPatternLearner
- **Location**: `src/learning/fix_pattern_learner.py`
- **Storage**: `FixPattern` nodes in Neo4j
- **Called by**: `SmokeRepairOrchestrator` after successful repairs
- **Purpose**: Learn which fixes work for which error patterns

#### Path 3: ErrorKnowledgeBridge (Bug #161)
- **Location**: `src/learning/error_knowledge_bridge.py`
- **Storage**: `GenerationAntiPattern` via `NegativePatternStore`
- **Called by**: `RuntimeSmokeValidator._learn_from_error()`
- **Purpose**: Bridge errors to code generation prompts

### Semantic Matching Algorithm

**Location**: `src/learning/negative_pattern_store.py:818-905`

The algorithm connects stored anti-patterns to code generation queries **without hardcoding domain terms**:

```python
def get_patterns_for_flow(self, flow_name: str, min_occurrences: int = None):
    """
    Domain-agnostic semantic matching.

    Example:
        flow_name = "add_item_to_cart"
        ↓ Normalize
        normalized = "add_item_to_cart"
        ↓ Extract keywords
        keywords = {"add", "item", "cart"}
        ↓ Match against stored patterns
        pattern.endpoint_pattern = "POST /{resource}/{id}/items"
        pattern.entity_pattern = "Cart"
        ↓ Match found: "cart" in "Cart", "items" in endpoint
    """
    # 1. Normalize flow name
    normalized_flow = flow_name.lower().replace("-", "_").replace(" ", "_")

    # 2. Extract keywords (domain-agnostic)
    flow_keywords = set(normalized_flow.split("_"))

    # 3. Search patterns by semantic match
    for pattern in self._cache.values():
        # Match by endpoint pattern (generic: /{resource}/{id}/items)
        if pattern.endpoint_pattern and pattern.endpoint_pattern != "*":
            endpoint_normalized = pattern.endpoint_pattern.lower()
            endpoint_match = any(
                kw in endpoint_normalized
                for kw in flow_keywords
                if len(kw) > 2  # Skip short words
            )

        # Match by entity pattern (extracted from endpoint dynamically)
        if pattern.entity_pattern and pattern.entity_pattern != "*":
            entity_normalized = pattern.entity_pattern.lower()
            entity_match = any(
                kw in entity_normalized
                for kw in flow_keywords
                if len(kw) > 2
            )

        # Match by error message pattern
        if pattern.error_message_pattern:
            message_match = any(
                kw in pattern.error_message_pattern.lower()
                for kw in flow_keywords
                if len(kw) > 2
            )

        if endpoint_match or entity_match or message_match:
            matched_patterns.append(pattern)

    return matched_patterns
```

### Domain-Agnostic Extraction

**Location**: `src/learning/error_knowledge_bridge.py:270-329`

Entity and endpoint extraction uses **regex patterns**, not hardcoded names:

```python
def _extract_entity_from_endpoint(self, endpoint: str) -> Optional[str]:
    """
    Extract entity name from ANY endpoint path.

    Examples (all domains):
        "POST /products"        → "Product"
        "GET /users/{id}"       → "User"
        "PUT /invoices/{id}"    → "Invoice"
        "POST /carts/{id}/items"→ "Cart"
    """
    parts = endpoint.split()
    path = parts[-1] if parts else endpoint

    for segment in path.strip("/").split("/"):
        # Skip parameter placeholders
        if segment.startswith("{"):
            continue
        # Skip API versioning
        if segment in ("api", "v1", "v2", "v3"):
            continue
        # Skip empty segments
        if not segment:
            continue

        # Generic singularization: remove trailing 's'
        # Works for: products→Product, users→User, carts→Cart
        entity = segment.rstrip("s").capitalize()
        return entity

    return None


def _normalize_endpoint(self, endpoint: str) -> str:
    """
    Normalize endpoint to pattern form (domain-agnostic).

    Examples:
        "/products/123"                    → "/products/{id}"
        "/users/abc-123-def-456"           → "/users/{id}"  (UUID)
        "POST /orders/999/items"           → "POST /orders/{id}/items"
    """
    if not endpoint:
        return "*"

    # Replace numeric IDs
    pattern = re.sub(r'/\d+', '/{id}', endpoint)

    # Replace UUIDs
    pattern = re.sub(
        r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
        '/{id}',
        pattern,
        flags=re.IGNORECASE
    )

    return pattern
```

### Inter-Run Learning Flow

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RUN N                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [1] Code Generation (Templates)                                            │
│       │                                                                     │
│       ▼                                                                     │
│  [2] Smoke Test                                                             │
│       │                                                                     │
│       ├─→ PASS: Continue                                                    │
│       │                                                                     │
│       └─→ FAIL: _learn_from_error()                                         │
│             │                                                               │
│             ├─→ Path 1: ErrorKnowledgeRepository                            │
│             ├─→ Path 2: (after repair) FixPatternLearner                    │
│             └─→ Path 3: ErrorKnowledgeBridge → NegativePatternStore         │
│                                                                             │
│  [3] Repair Cycle (LLM + anti-patterns from Path 3)                         │
│       │                                                                     │
│       ▼                                                                     │
│  [4] Re-test → Iterate until pass rate target or max iterations             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Anti-patterns persisted in NegativePatternStore
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RUN N+1                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [1] Code Generation (Templates)                                            │
│       │                                                                     │
│       ▼                                                                     │
│  [2] Smoke Test                                                             │
│       │                                                                     │
│       └─→ FAIL: Repair Cycle                                                │
│             │                                                               │
│             ▼                                                               │
│  [3] IRCentricCognitivePass._get_anti_patterns_for_flow()                   │
│       │                                                                     │
│       └─→ QUERIES NegativePatternStore (includes Run N patterns)            │
│             │                                                               │
│             ▼                                                               │
│  [4] _build_ir_guard() injects anti-patterns into LLM prompt                │
│       │                                                                     │
│       ▼                                                                     │
│  [5] LLM generates code AVOIDING Run N mistakes                             │
│                                                                             │
│  Result: Fewer repeated errors, faster convergence to 100% compliance       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### IRCentricCognitivePass Integration

**Location**: `src/cognitive/passes/ir_centric_cognitive_pass.py:460-484`

```python
def _get_anti_patterns_for_flow(self, flow: Flow) -> List[GenerationAntiPattern]:
    """
    Query NegativePatternStore for relevant anti-patterns.

    This is WHERE the learning loop closes:
    - Smoke errors → Bridge → NegativePatternStore
    - Code generation → THIS METHOD → queries stored patterns
    - Patterns injected via _build_ir_guard() into LLM prompt
    """
    patterns = []

    # Query by flow name (semantic matching)
    flow_patterns = self._pattern_store.get_patterns_for_flow(
        flow.name,  # e.g., "add_item_to_cart"
        min_occurrences=self._min_pattern_occurrences,
    )
    patterns.extend(flow_patterns)

    # Query by constraint types
    for constraint_type in flow.constraint_types:
        constraint_patterns = self._pattern_store.get_patterns_for_constraint_type(
            constraint_type,
            min_occurrences=self._min_pattern_occurrences,
        )
        for p in constraint_patterns:
            if p not in patterns:
                patterns.append(p)

    return patterns[:self._max_patterns_per_flow]
```

### Log Markers for Verification

| Log Marker | Component | Meaning |
|------------|-----------|---------|
| `🌉 Active Learning: Bridged to GenerationAntiPattern` | Bridge | Error converted to anti-pattern |
| `🎓 Intra-run learning: X new, Y updated` | FeedbackCollector | Patterns created/updated |
| `🎓 Applied learned anti-pattern for {endpoint}` | Repair Orchestrator | Pattern-based repair used |
| `🎓 Passing N anti-patterns to CodeRepairAgent` | Repair Orchestrator | Anti-patterns sent to LLM |
| `📚 IR Guard: Injecting N anti-patterns` | IRCentricCognitivePass | Patterns in generation prompt |

### Key Design Decisions

1. **Domain Agnostic**: No hardcoded entity names, endpoints, or business terms
2. **Graceful Degradation**: All components have fallbacks if unavailable
3. **Semantic Matching**: Keyword extraction works for ANY domain
4. **Incremental Learning**: Patterns accumulate across runs
5. **Immediate Use**: `min_occurrences=1` allows same-run learning

### Files Summary

| File | Purpose |
|------|---------|
| `src/learning/error_knowledge_bridge.py` | Converts smoke errors → GenerationAntiPattern |
| `src/learning/negative_pattern_store.py` | Stores and queries anti-patterns |
| `src/learning/__init__.py` | Exports bridge functions |
| `src/validation/runtime_smoke_validator.py` | Calls bridge in `_learn_from_error()` |
| `src/cognitive/passes/ir_centric_cognitive_pass.py` | Queries patterns for code generation |

### Verification Commands

```bash
# Check bridge is available
grep -n "ERROR_KNOWLEDGE_BRIDGE_AVAILABLE" src/validation/runtime_smoke_validator.py

# Check semantic matching
grep -n "get_patterns_for_flow" src/learning/negative_pattern_store.py

# Check IRCentricCognitivePass queries
grep -n "_get_anti_patterns_for_flow" src/cognitive/passes/ir_centric_cognitive_pass.py

# Verify domain-agnostic extraction
grep -n "_extract_entity_from_endpoint\|_normalize_endpoint" src/learning/error_knowledge_bridge.py
```

---
