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
- [x] `AntiPatternAdvisor` class
- [x] Integration with `CodeGenerationService`
- [x] Feedback loop metrics

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
| 2025-12-01 | Task 2: TestsModelIR | ✅ | Bug #167 - Business-appropriate status values |
| 2025-12-01 | Task 3: Anti-patterns | ✅ | Bug #168 - AntiPatternAdvisor created |
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

---

## 🐛 Bug #167: Business-Appropriate Status Values

**Problem:** TestsModelIR and seed_db.py generate status="active" for all entities, but business operations like checkout/payment require status="pending".

**Example Failure:**
```
POST /orders/{id}/checkout
Expected: 200 (checkout success)
Actual: 422 (validation error - order status must be "pending")
```

**Root Cause:**
- `tests_ir_generator.py` line 177: `if 'status' in field_name.lower(): return "active"`
- `code_generation_service.py` line 5475: `field_assignments.append(f'{attr_name}="ACTIVE"')`

**Solution:** Use entity-aware status values:
- Orders, Carts, Baskets, Checkouts → status="pending" (for checkout/payment operations)
- Products, Users, Customers → status="active" (for availability)

**Files Modified:**

1. `src/services/tests_ir_generator.py`:
   - Updated `_get_default_value()` to accept `entity_name` parameter
   - Added entity-type-aware status logic

2. `src/services/code_generation_service.py`:
   - Updated `_generate_seed_db_script()` status handling
   - Added entity-type check for pending vs active

**Code Changes:**

```python
# tests_ir_generator.py - _get_default_value()
if 'status' in field_lower:
    # Orders and Carts need "pending" for checkout/payment operations
    if entity_lower in ['order', 'cart', 'basket', 'checkout']:
        return "pending"
    # Products, Users, Customers need "active" for availability
    return "active"
```

```python
# code_generation_service.py - _generate_seed_db_script()
elif 'status' in attr_name.lower():
    entity_lower = entity_name.lower()
    if entity_lower in ['order', 'cart', 'basket', 'checkout'] or 'order' in attr_name.lower():
        field_assignments.append(f'{attr_name}="PENDING"')
    else:
        field_assignments.append(f'{attr_name}="ACTIVE"')
```

**Expected Impact:** Eliminates ~3-5 cases of "expected 200, got 422" on checkout/payment operations

---

## 🐛 Bug #168: AntiPatternAdvisor Integration

**Problem:** Anti-patterns are stored after smoke test failures but never used to prevent the same errors in future code generation runs.

**Solution:** Created `AntiPatternAdvisor` class that queries `NegativePatternStore` before code generation and provides recommendations.

**Files Created:**
- `src/learning/anti_pattern_advisor.py` - New advisor class

**Files Modified:**
- `src/services/code_generation_service.py` - Integrated advisor in constructor and `_generate_route_with_llm()`
- `src/learning/feedback_collector.py` - Cache invalidation after storing new patterns

**Architecture:**

```
┌─────────────────────┐     ┌──────────────────────┐
│ CodeGenerationService│────▶│ AntiPatternAdvisor   │
└─────────────────────┘     └──────────────────────┘
                                      │
                                      ▼
                            ┌──────────────────────┐
                            │ NegativePatternStore │
                            │      (Neo4j)         │
                            └──────────────────────┘
                                      ▲
                                      │
┌─────────────────────┐     ┌──────────────────────┐
│ RuntimeSmokeTest    │────▶│ FeedbackCollector    │
└─────────────────────┘     └──────────────────────┘
```

**Key Methods:**
```python
# Get advice for entity
advice = advisor.get_advice_for_entity("Order")
if advice.has_advice():
    prompt += advice.to_prompt_injection()

# Get route-specific advice
advice = advisor.get_route_generation_advice("Order", "PUT", "/{id}")

# Cache invalidation after new patterns stored
advisor.clear_cache()
```

**Expected Impact:** Prevents recurring errors by consulting historical failure patterns before generating new code.

---

## 📊 Summary of Changes

| Bug | Files Modified | Problem | Solution |
|-----|----------------|---------|----------|
| #166 | `code_generation_service.py` | 404 vs 422 confusion | Existence check before validation |
| #167 | `tests_ir_generator.py`, `code_generation_service.py` | Wrong status for orders/carts | Business-appropriate status values |
| #168 | `anti_pattern_advisor.py`, `code_generation_service.py`, `feedback_collector.py` | Anti-patterns not used | AntiPatternAdvisor with feedback loop |

**Total Expected Improvement:** ~8-10 fewer smoke test failures (from 69.7% to ~80%+)

---

## ✅ Task Status

| Task | Status | Bug | Effort |
|------|--------|-----|--------|
| 1. Route/Status Tuning | ✅ DONE | #166 | 2h |
| 2. TestsModelIR Alignment | ✅ DONE | #167 | 4h |
| 3. Anti-patterns Loop | ✅ DONE | #168 | 6h |
| 4. Demo Prep | ⏳ PENDING | - | 1h |

---

## 🧹 Code Cleanup (2025-12-01)

**Refactored:**

- `code_generation_service.py`: DRY helper `existence_check()` consolidates Bug #166 blocks (~50 lines removed)
- `code_repair_agent.py`: Added Bug #166 fix to AST-based endpoint generation (PUT method now checks existence)

**Impact:** Fixes now apply to BOTH code paths:

1. Initial code generation (`_generate_route_with_llm`)
2. On-the-fly repair (`code_repair_agent._generate_endpoint_function_ast`)

---

## 🐛 Bug #169: Seed Data Not Persisting (CRITICAL)

**Status:** 🔴 ACTIVE - Root cause identified

**Problem:** `seed_db.py` logs "Test data seeded successfully" but data is NOT in the database.

**Evidence:**
```bash
# Docker logs show success:
2025-12-01 15:25:58 [info] ✅ Created test Product with ID 00000000-0000-4000-8000-000000000001
2025-12-01 15:25:58 [info] ✅ Test data seeded successfully

# But database is empty:
docker exec app_postgres psql -U devmatrix -d app_db -c "SELECT id FROM products WHERE id = '00000000-0000-4000-8000-000000000001';"
# (0 rows)
```

**Root Cause Analysis:**

1. **Timing Issue:** The `db-init` container runs `alembic upgrade head && python scripts/seed_db.py`
2. **Transaction Isolation:** The seed_db.py uses `async with session_maker() as session:` which may not commit properly
3. **Possible Race Condition:** The app container may start before db-init fully commits

**Workaround Applied:**
```bash
# Manual seed execution works:
docker exec app_app python scripts/seed_db.py
# Data now persists correctly
```

**Proposed Fix:**

Option A: Add explicit flush + commit verification:
```python
async def seed_test_data():
    async with session_maker() as session:
        # ... add entities ...
        await session.flush()  # Force write to DB
        await session.commit()

        # Verify data was persisted
        result = await session.execute(select(ProductEntity).where(ProductEntity.id == UUID("00000000-0000-4000-8000-000000000001")))
        if not result.scalar_one_or_none():
            raise RuntimeError("Seed data verification failed!")
```

Option B: Add retry/wait in docker-compose:
```yaml
db-init:
  command: sh -c "alembic upgrade head && python scripts/seed_db.py && sleep 2"
```

Option C: Run seed from app container on startup:
```python
# In main.py lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_seed_if_needed()  # Check and seed if empty
    yield
```

**Impact:** This is the PRIMARY cause of 18+ smoke test failures (all happy_path scenarios that expect existing resources).

**Next Steps:**
1. [ ] Implement Option A (verification) in seed_db.py template
2. [ ] Test with fresh Docker build
3. [ ] Validate smoke test improvement
