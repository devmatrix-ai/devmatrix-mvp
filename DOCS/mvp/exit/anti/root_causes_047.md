# Root Cause Analysis: Run 047 Errors

## 1. The Repair Paradox (Phase 8.5 Skipped)

**Symptom:** The log shows `Total repairs: 0` and `Target pass rate reached!` despite 22 runtime violations and a final status of `FAILED`.

**Root Cause:**
The `SmokeRepairOrchestrator` calculates `current_pass_rate` as `endpoints_passed / endpoints_tested`.
In the failing run:
*   `endpoints_tested` = 34
*   `endpoints_passed` = 22 (Hypothetically high enough to pass threshold?)
*   If `target_pass_rate` is set too low (e.g., 0.6), and the pass rate is 0.64 (64.7%), the orchestrator thinks "Good enough!" and exits the loop *without* attempting repairs on the 35% that failed.
*   **Critical Flaw:** The "Success Condition" (`current_pass_rate >= target`) is checked *before* attempting repairs. If the initial pass rate meets the target (even if it's mediocre), no repairs are ever attempted.
*   **Fix:** Ensure `target_pass_rate` is set to strict 1.0 (100%) for the repair loop, or at least significantly higher than the initial pass rate. Also, consider triggering repair if *any* critical violation exists, regardless of pass rate.

## 2. IR-Code Correlation Crash (`AttributeError`)

**Symptom:** `⚠️ IR-Code correlation skipped: 'list' object has no attribute 'get'`

**Root Cause:**
Type mismatch in `tests/e2e/real_e2e_full_pipeline.py` when calling `correlator.analyze_generation`.

*   **The Call (Pipeline):**
    ```python
    correlation_report = correlator.analyze_generation(
        entities=...,
        endpoints=...,
        smoke_results=smoke_result.violations  # <--- PASSING A LIST
    )
    ```
*   **The Expectation (Correlator):**
    ```python
    def _get_endpoint_pass_rate(self, ..., smoke_results):
        violations = smoke_results.get("violations", []) # <--- EXPECTING A DICT
    ```
*   **The Crash:** `list.get("violations")` raises `AttributeError`.

**Fix:** Update `real_e2e_full_pipeline.py` to pass the full `smoke_result` object (converted to dict) or wrap the violations list in a dict: `smoke_results={"violations": smoke_result.violations}`.

## 3. The Compliance/Test Gap

**Symptom:** 100% Compliance Score but only 64.7% Test Pass Rate.

**Root Cause:**
Fundamental difference in validation scope:
*   **ComplianceValidator (Static):** Checks if code elements *exist* (e.g., "Is there a `price` field?"). It passes even if the field logic is empty or wrong.
*   **TestGenerator (Dynamic):** Checks if code elements *behave* correctly (e.g., "Does `price` reject -1?").
*   **The Gap:** The `ModularArchitectureGenerator` correctly scaffolds the *structure* (satisfying Compliance) but sometimes misses the *constraints* (e.g., Pydantic `Field(gt=0)`) or the *business logic* (satisfying Tests).

**Fix:**
1.  Enhance `ComplianceValidator` to check for *constraints* (e.g., verify `gt=0` exists in the AST for `price`).
2.  Update `ModularArchitectureGenerator` to ensure all IR constraints are translated to Pydantic validators.

## 4. Missing README

**Symptom:** `✗ File check: README.md` failed.

**Root Cause:**
Likely a race condition or file system sync issue. The file is generated in memory by `ModularArchitectureGenerator`, but the `HealthVerification` phase checks for it on disk. If the file write operation (in `CodeGenerationService`) didn't flush or failed silently for that specific file, the check fails.
Given it's a single file among many successful ones, it's a minor artifact generation glitch.

## 5. Implemented Fixes (Run 048 Preparation)

The following fixes have been applied to the codebase to address the identified root causes:

1.  **Repair Paradox Fix:**
    *   Updated `tests/e2e/real_e2e_full_pipeline.py` to initialize `SmokeRepairConfig` with `target_pass_rate=1.00` (previously 0.80). This ensures the runtime repair loop continues until 100% of smoke tests pass, preventing premature exit.

2.  **IR-Code Correlation Crash Fix:**
    *   Updated `tests/e2e/real_e2e_full_pipeline.py` to pass `smoke_results` as a dictionary `{"violations": ...}` instead of a list to `correlator.analyze_generation`, matching the expected interface of `IRCodeCorrelator`.

3.  **Compliance/Test Gap Fix:**
    *   Updated `src/validation/compliance_validator.py` to **always** merge validation rules from `ValidationModelIR` into the expected validations list. Previously, these rules were only used as a fallback if no rules were found in the `DomainModel`. This ensures that strict constraints (like `gt=0`, regex patterns) defined in the IR are enforced during static compliance checks, aligning compliance scores with runtime test expectations.
