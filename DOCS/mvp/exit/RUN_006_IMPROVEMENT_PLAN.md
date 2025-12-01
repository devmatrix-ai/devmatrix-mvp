# Run 006 Improvement Plan

## ✅ RESOLVED - Run 008 Results (2025-12-01)

| Métrica | Run 007 | Run 008 | Cambio |
|---------|---------|---------|--------|
| **Smoke Test Pass Rate** | 86.7% (stuck) | **100.0%** ✅ | +13.3% |
| **Semantic Compliance** | 99.9% | **99.9%** ✅ | = |
| **Test Pass Rate** | 67.2% | **64.6%** | -2.6% |

### Bugs Fixed:
- **Bug #165**: IR parameter not passed to service generator
- **Bug #165**: Trailing prepositions in method names
- **Bug #166**: Parenthetical expressions creating invalid Python identifiers

---

**Date**: 2025-12-01
**Log**: `logs/runs/Ariel_test_006_25_026_07.log`
**Status**: 🔴 IN PROGRESS
**Owner**: Platform

---

## Executive Summary

Run 006 achieved **99.9% semantic compliance** but smoke tests stalled at **86.7%** with **0 repairs applied**. This plan addresses the 5 root causes identified.

| Metric | Current | Target |
|--------|---------|--------|
| Smoke Test Pass Rate | 86.7% | 95%+ |
| Repairs Applied | 0 | >0 per cycle |
| Learned Patterns Applied | 0 | >0 |
| Constraints Parsed | ~60% | 95%+ |
| Stack Traces Captured | 1/cycle | 5+/cycle |

---

## 🚨 ROOT CAUSE ANALYSIS

After investigating the generated apps, the **true root cause** was identified:

### Routes Call Non-Existent Service Methods (DOMAIN-AGNOSTIC)

**The Problem (applies to ANY spec):**

```python
# Routes generator creates:
result = await service.{flow_method}(id, ...)   # ❌ Method DOES NOT EXIST

# Services generator only creates:
create(), get(), list(), update(), delete()      # ✅ CRUD only
```

**Gap**: When BehaviorModelIR defines flows, the route generator creates calls to flow methods,
but the service generator only produces CRUD methods.

**Flow methods exist in `*_flow_methods.py` but:**

1. They are **STUBS with placeholder `pass`** - no real implementation
2. They are **NOT INTEGRATED** as mixins into the Services
3. Even the method names don't match (e.g., `f13_checkout_create_order` vs `checkout`)

**This causes HTTP 500** - AttributeError when route calls non-existent service method.

---

## Problems Identified

### P0: ⚡ Routes Call Non-Existent Service Methods (CRITICAL)
```python
# Routes expect these but they don't exist:
CartService.add_item()    # → AttributeError → HTTP 500
CartService.checkout()    # → AttributeError → HTTP 500
OrderService.pay()        # → AttributeError → HTTP 500
OrderService.cancel()     # → AttributeError → HTTP 500
```
**Impact**: 100% of workflow endpoints broken. This is the BLOCKING issue.

### P1: Flow Methods Are Stubs (Not Implemented)
```python
# cart_flow_methods.py:
async def f9_add_item_to_cart(self, **kwargs):
    pass  # Validation placeholder
    pass  # Create placeholder
    return {'status': 'completed'}  # Returns dummy data!
```
**Impact**: Even if integrated, flows return dummy data, not real business logic.

### P2: Unparsed Constraints
```
⚠️ Unparsed constraint 'presence: required' - SKIPPING
⚠️ Unparsed constraint 'status_transition: OPEN -> CHECKED_OUT' - SKIPPING
```
**Impact**: Ground truth validations ignored (but secondary to P0/P1).

### P3: Learning Loop Not Reusing Patterns
```
Loaded 16 historical fix patterns
Learned patterns applied: 0
```
**Impact**: No cross-session learning benefit.

### P4: Smoke Repair Applies 0 Repairs
```
Total repairs: 0
Learned patterns applied: 0
```
**Impact**: Loop converges without fixing anything (because there's no repair strategy for "method doesn't exist").

---

## Implementation Plan

### Phase 0: Service-Route Method Alignment (P0) 🚨 CRITICAL
**Effort**: 30 min
**Priority**: BLOCKING
**Status**: ✅ COMPLETE

| Task | File | Status |
|------|------|--------|
| 0.1 **Bug #165**: Fix IR not passed to service generator | `src/services/code_generation_service.py:3135` | ✅ DONE |
| 0.2 **Bug #165**: Fix trailing preposition in method name | `src/services/production_code_generators.py:432` | ✅ DONE |

**Fixes Applied:**

1. **IR Parameter Fix** (`code_generation_service.py:3135`):
```python
# BEFORE: ir_to_pass = getattr(self, 'app_ir', None)  # Always None!
# AFTER:
ir_to_pass = spec_or_ir if is_app_ir else getattr(self, 'app_ir', None)
```

2. **Method Name Extraction Fix** (`production_code_generators.py:432`):
```python
# Added: Remove trailing prepositions after entity removal
name = re.sub(r'\s+(to|from|in|at|for)$', '', name.strip())
```

**Verification:**
```
'Add Item to Cart' + 'Cart' → 'add_item' ✅
'Pay Order' + 'Order' → 'pay' ✅
'Cancel Order' + 'Order' → 'cancel' ✅
'Checkout Cart' + 'Cart' → 'checkout' ✅
```

### Phase 1: Constraint Parser Enhancement (P2)
**Effort**: 2-3 hours
**Priority**: HIGH

| Task | File | Status |
|------|------|--------|
| 1.1 Parse `type: value` format | `src/services/production_code_generators.py` | 🔲 TODO |
| 1.2 Handle `presence: required` | `src/services/production_code_generators.py` | 🔲 TODO |
| 1.3 Handle `status_transition: X -> Y` | `src/services/production_code_generators.py` | 🔲 TODO |
| 1.4 Handle `workflow_constraint: ...` | `src/services/production_code_generators.py` | 🔲 TODO |

### Phase 2: Learning Loop Fix (P3)
**Effort**: 2-3 hours
**Priority**: HIGH

| Task | File | Status |
|------|------|--------|
| 2.1 Debug pattern matching in NegativePatternStore | `src/learning/negative_pattern_store.py` | 🔲 TODO |
| 2.2 Fix pattern application in SmokeRepairOrchestrator | `src/validation/smoke_repair_orchestrator.py` | 🔲 TODO |
| 2.3 Add logging for pattern match/skip reasons | `src/learning/negative_pattern_store.py` | 🔲 TODO |

### Phase 3: Smoke Repair Strategy Enhancement (P1)
**Effort**: 3-4 hours
**Priority**: CRITICAL

| Task | File | Status |
|------|------|--------|
| 3.1 Add "method_missing" repair strategy | `src/validation/smoke_repair_orchestrator.py` | 🔲 TODO |
| 3.2 Detect AttributeError from stack traces | `src/validation/runtime_smoke_validator.py` | 🔲 TODO |
| 3.3 Trigger service regeneration on AttributeError | `src/validation/smoke_repair_orchestrator.py` | 🔲 TODO |

---

## Acceptance Criteria

- [ ] Constraint parser recognizes `type: value` format (0 "Unparsed" warnings)
- [ ] Learning loop applies at least 1 pattern per cycle when available
- [ ] Smoke repair applies >0 repairs when violations exist
- [ ] Stack trace capture gets 5+ traces per cycle
- [ ] Workflow endpoints (checkout/pay/cancel) return 2xx/4xx, not 500
- [ ] Smoke test pass rate reaches 95%+

---

## Verification Commands

```bash
# Run E2E and check improvements
python -m pytest tests/e2e/real_e2e_full_pipeline.py -v -s 2>&1 | tee logs/runs/run_007.log

# Check constraint parsing
grep -c "Unparsed constraint" logs/runs/run_007.log  # Should be 0

# Check learning patterns applied
grep "Learned patterns applied" logs/runs/run_007.log  # Should be >0

# Check repairs applied
grep "Total repairs" logs/runs/run_007.log  # Should be >0
```

---

## Progress Tracking

| Phase | Status | Completion |
|-------|--------|------------|
| Phase 1: Constraint Parser | 🔲 TODO | 0% |
| Phase 2: Learning Loop | 🔲 TODO | 0% |
| Phase 3: Smoke Repair Strategy | 🔲 TODO | 0% |
| Phase 4: Stack Trace Capture | 🔲 TODO | 0% |
| Phase 5: Workflow Services | 🔲 TODO | 0% |
| **Overall** | 🔲 TODO | **0%** |

---

## Changelog

| Date | Change |
|------|--------|
| 2025-12-01 | Initial plan created from Run 006 analysis |

