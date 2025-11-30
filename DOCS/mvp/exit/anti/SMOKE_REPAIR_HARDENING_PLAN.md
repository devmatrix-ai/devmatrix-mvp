# Smoke Repair Hardening Plan

**Date:** 2025-11-30  
**Owner:** Platform / Validation  
**Scope:** Log 053 shows smoke repair stuck at 86.7% with only 4 fixes applied, learning not reused, and Docker rebuild misbehaving. This plan targets those gaps.

---

## Problems Observed (Run 053)
- Repair cycle converges at 86.7% with 4 generic fixes (cart/order endpoints) — no business logic repair.
- NegativePatternStore crashes: `GenerationAntiPattern` has no `wrong_code_pattern`, so learned anti-patterns are not applied.
- FixPatternLearner persist fails: `unhashable type: 'slice'`, so patterns are not stored/reused.
- `with_docker_rebuild=False` is ignored: validator still does `docker compose build --no-cache` each cycle.
- Stack traces sparse: only 1 trace captured; most violations lack exception_class, forcing generic strategy.
- CodeRepair (compliance) only patches constraints; logic/flow errors remain (500/422).

## Additional Failures (Run 054)
- NegativePatternStore still fails to apply patterns: `GenerationAntiPattern` has no attribute `confidence` (even after handling wrong_code_pattern). Result: learned patterns are skipped; only generic fixes applied.
- Stack trace capture remains minimal (1 trace per cycle); most violations lack exception_class → strategies stay generic.
- CodeRepair (phase 6.5) still only patches constraints (274 validations), plateau 99.9%→99.9% — no flow/service fixes.
- Smoke repair still converges at 86.7% (same endpoints failing: carts items/checkout, orders pay/cancel).
- Rebuild flag now respected (allow_rebuild=False skips build), but logic issues persist.

---

## Objectives
1) Make smoke repair use real signal (stack traces, exception_class) and non-generic strategies.  
2) Restore learning loop: FixPatternLearner and NegativePatternStore should persist and reuse patterns.  
3) Respect Docker rebuild toggle to avoid needless rebuilds or missing-Dockerfile failures.  
4) Enable richer fixes for flow/service logic (not just constraints) when plateau is detected.

---

## Plan
1) **Trace Enrichment**  
   - Attach parsed stack traces to each violation (endpoint, exception_class, file, line).  
   - Use exception_class for strategy routing (500→SERVICE/ROUTE, 422→VALIDATION).

2) **Learning Persistence**  
   - Fix FixPatternLearner persistence (`unhashable slice`) and store structured repairs (endpoint/error/exception/fix_type).  
   - Map GenerationAntiPattern fields (`bad_code_snippet`/`correct_code_snippet`) so NegativePatternStore can guide repairs.

3) **Docker Rebuild Control**  
   - Add `allow_rebuild` flag in runtime validator; honor `with_docker_rebuild` from orchestrator.  
   - Default rebuild off unless explicitly enabled.

 4) **Repair Depth**  
    - Prefer strategy-specific fixes over generic; if pass-rate delta = 0, trigger partial regeneration of services/flows for failing endpoints.

 5) **Observability**  
   - Log applied learned patterns (or absence) and skipped rebuilds clearly.

6) **NegativePatternStore Resilience**  
   - Handle missing `confidence` by falling back to `severity_score`/occurrence counts; ensure queries never crash when fields are absent.

7) **Flow/Service Repair Path**  
   - Add targeted repair/regeneration for cart/order flows (checkout, pay, cancel, add_item) instead of constraint-only patches; consider re-synth services or patch flows with IR context when 500s persist.

---

## Acceptance Criteria
- No NegativePatternStore attribute errors; learned patterns can be applied.  
- FixPatternLearner persist succeeds (no slice errors); patterns visible in Neo4j.  
- Rebuild flag respected: no Docker build when `SMOKE_REPAIR_DOCKER_REBUILD=false`.  
- Stack traces attached to violations; strategies are non-generic when possible.  
- Smoke repair applies more than generic fixes or triggers regeneration fallback when plateau persists.
