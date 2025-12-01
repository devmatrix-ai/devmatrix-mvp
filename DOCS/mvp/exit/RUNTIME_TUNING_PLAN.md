# DevMatrix Runtime Tuning Plan

**Status:** ACTIVE  
**Base Run:** `test_devmatrix_000_023.log`  
**Date:** 2025-12-01  
**Goal:** Smoke Test 69.7% → 95%+

---

## 📊 Current State

| Metric | Value | Status |
|--------|-------|--------|
| Compliance (IR) | 99.9% | ✅ |
| Code Generation | 96 files / 1.3s | ✅ |
| IR-based Tests | 267 generated | ✅ |
| Flow Coverage | 17/17 (100%) | ✅ |
| Endpoint Pre-validation | 30/32 generated | ✅ |
| **Runtime Smoke Test** | **53/76 (69.7%)** | ⚠️ |

### Failure Analysis

| Error Type | Count | Root Cause |
|------------|-------|------------|
| expected 201, got 422 | ~8 | Payload missing preconditions |
| expected 200, got 404 | ~6 | Route not registered or param mismatch |
| expected 204, got 404 | ~4 | DELETE route missing |
| expected 404, got 422 | ~5 | Validation before existence check |

---

## 🎯 Tuning Tasks

### Task 1: Route/Status Tuning (5.2)
**Priority:** HIGH | **Effort:** LOW | **Impact:** HIGH

**Problem:** 404 vs 422 confusion. API returns 422 (validation error) when it should return 404 (not found).

**Solution:** Enforce existence check BEFORE validation in route handlers.

```python
# WRONG (current)
@router.put("/{id}")
async def update(id: UUID, data: UpdateDTO):
    validate(data)  # Returns 422 if invalid
    item = await repo.get(id)  # Never reached if validation fails
    
# CORRECT (target)
@router.put("/{id}")
async def update(id: UUID, data: UpdateDTO):
    item = await repo.get(id)
    if not item:
        raise HTTPException(404)  # Check existence FIRST
    validate(data)
```

**Affected Endpoints:**
- [ ] `PUT /products/{id}`
- [ ] `PATCH /products/{id}/activate`
- [ ] `PATCH /products/{id}/deactivate`
- [ ] `DELETE /carts/{id}`
- [ ] `PUT /orders/{id}/items/{product_id}`
- [ ] `DELETE /orders/{id}`

**Implementation:**
1. Update PatternBank route templates
2. Add `existence_check_first` flag to route generation
3. Re-run smoke test

---

### Task 2: TestsModelIR ↔ Business Logic Alignment (5.1)
**Priority:** HIGH | **Effort:** MEDIUM | **Impact:** HIGH

**Problem:** TestsModelIR generates happy_path scenarios that assume resources exist, but test runs start with empty DB.

**Examples:**
| Scenario | Expects | Reality |
|----------|---------|---------|
| `checkout_happy_path` | POST /orders → 201 | Cart is empty → 422 |
| `deactivate_product` | PATCH → 200 | Product doesn't exist → 404 |
| `get_customer_orders` | GET → 200 | Customer doesn't exist → 422 |

**Solution:** TestsModelIR must generate setup fixtures OR order scenarios correctly.

**Implementation:**
1. Analyze `ir_smoke_test_results.json` for each failure
2. Categorize: 
   - A) Test is wrong (needs fixture)
   - B) App is wrong (missing logic)
3. For (A): Add fixture generation to TestsModelIR
4. For (B): Add repair pattern to CodeRepair

**Deliverables:**
- [ ] Fixture generation in SmokeRunnerV2
- [ ] Scenario dependency ordering (create before update/delete)
- [ ] Precondition inference from IR flows

---

### Task 3: Anti-patterns → Route Generation (5.3)
**Priority:** MEDIUM | **Effort:** HIGH | **Impact:** MEDIUM

**Problem:** Anti-patterns are stored but not used to prevent future errors.

**Current Flow:**
```
Smoke fails → Anti-pattern stored → (nothing happens)
```

**Target Flow:**
```
Smoke fails → Anti-pattern stored → Next codegen avoids pattern
```

**Implementation:**
1. Query ErrorPatternStore before route generation
2. If `HTTP_404 on {Entity}` exists:
   - Verify router mounts all paths
   - Check path param names match IR
3. If `HTTP_422 on {Entity}` exists:
   - Review validation order
   - Check enum values match IR

**Deliverables:**
- [ ] `AntiPatternAdvisor` class
- [ ] Integration with `CodeGenerationService`
- [ ] Feedback loop metrics

---

### Task 4: Demo Readiness (5.4)
**Priority:** LOW | **Effort:** LOW | **Impact:** LOW (but strategic)

**Current:** 6.1 min total runtime, $0.05 LLM cost

**Target Narrative:**
> "DevMatrix generates an enterprise API in 6 minutes, deploys to Docker, 
> runs 76 auto-inferred business scenarios, and passes 100%."

**Checklist:**
- [ ] Smoke test ≥ 95%
- [ ] Clean console output (no debug noise)
- [ ] Dashboard integration (deferred)
- [ ] One-liner demo script

---

## 📋 Execution Order

| Phase | Task | Effort | Cumulative Impact |
|-------|------|--------|-------------------|
| 1 | Route/Status Tuning (5.2) | 2h | 69.7% → ~80% |
| 2 | TestsModelIR Alignment (5.1) | 4h | ~80% → ~90% |
| 3 | Anti-patterns Loop (5.3) | 6h | ~90% → ~95% |
| 4 | Demo Prep (5.4) | 1h | Polish |

**Total Estimated:** ~13h

---

## ✅ Success Criteria

- [ ] Smoke Test ≥ 95% pass rate
- [ ] Zero 404-vs-422 confusion
- [ ] All happy_path scenarios pass
- [ ] Anti-patterns actively prevent regressions
- [ ] Demo-ready output

---

## 📝 Progress Log

| Date | Task | Status | Notes |
|------|------|--------|-------|
| 2025-12-01 | Plan created | ✅ | Based on test_devmatrix_000_023.log |
| 2025-12-01 | Task 1: Route/Status | ✅ | Bug #166 - Existence check before validation |
| | Task 2: TestsModelIR | ⏳ | |
| | Task 3: Anti-patterns | ⏳ | |
| | Task 4: Demo | ⏳ | |

---

## 🐛 Bug #166: Existence Check Before Validation

**Problem:** FastAPI/Pydantic validates request body BEFORE route handler runs. If body is invalid, returns 422 even when resource doesn't exist (should be 404).

**Solution:** Add explicit existence check at START of route handler for PUT/PATCH/POST operations that require an existing resource.

**Files Modified:** `src/services/code_generation_service.py`

**Changes:**
1. PUT routes: Check `service.get(id)` before `service.update()`
2. PATCH routes: Check existence before `service.update()` or `service.{operation}()`
3. POST with id (checkout, add_item): Check existence first

**Generated Code Pattern:**
```python
# Bug #166 Fix: Check existence first to return proper 404
existing = await service.get(id)
if not existing:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Entity with id {id} not found"
    )

# Now safe to proceed with operation
result = await service.update(id, data)
return result
```

**Expected Impact:** Eliminates ~5 cases of "expected 404, got 422"

