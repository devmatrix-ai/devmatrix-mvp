# 🎯 Plan: Remaining 8 Smoke Test Failures

**Current Status:** 89.2% pass rate (66/74)
**Target:** 95%+ (70/74)
**Date:** 2025-12-01
**Last Updated:** 2025-12-01 (Bug #199 fix applied)

---

## 📊 Progress Tracker

| Category | Problem | Tests | Status | Bug # |
|----------|---------|-------|--------|-------|
| A | Flow IR generates wrong entity | 2 | ⏳ Pending | - |
| B | Seed ID resolution | 2 | ✅ Fixed | #198 |
| C | Validation schemas too loose | 2 | ⏳ Pending | - |
| D | 422 before 404 (no request_schema) | 1 | ✅ Fixed | #199 |
| E | Checkout business logic | 1 | ⏳ Pending | - |

---

## 📊 Failure Analysis

| # | Scenario | Endpoint | Expected | Actual | Category | Status |
|---|----------|----------|----------|--------|----------|--------|
| 1 | `update_product_validation_error` | PUT /products/{id} | 422 | 200 | C | ⏳ |
| 2 | `update_cart_item_quantity_validation_error` | PUT /carts/{cart_id}/items/{item_id} | 422 | 200 | C | ⏳ |
| 3 | `checkout_happy_path` | POST /orders | 201 | 422 | E | ⏳ |
| 4 | `delete_cart_happy_path` | DELETE /carts/{id} | 204 | 404 | B | ✅ |
| 5 | `add_item_to_order_not_found` | PUT /orders/{id}/items/{product_id} | 404 | 422 | D | ✅ |
| 6 | `remove_item_from_order_happy_path` | DELETE /orders/{id}/items/{product_id} | 204 | 404 | B | ✅ |
| 7 | `F11: Update Item Quantity_3_delete` | DELETE /customers/{id} | 204 | 404 | A | ⏳ |
| 8 | `F12: Empty Cart_2_delete` | DELETE /customers/{id} | 204 | 404 | A | ⏳ |

---

## 🔧 Root Causes & Fixes

### Category A: Flow IR Generation Bug (2 failures)

**Problem:** F11 "Update Item Quantity" and F12 "Empty Cart" flows generate DELETE /customers/{id} steps instead of cart/item operations.

**Root Cause:** `tests_ir_generator.py` incorrectly maps flow steps to Customer entity instead of Cart/CartItem.

**Location:** `src/services/tests_ir_generator.py` → `_generate_flow_scenarios()`

**Fix:**
```python
# In _generate_flow_scenarios():
# Map flow steps to correct entity based on flow name
if "cart" in flow_name.lower() or "item" in flow_name.lower():
    target_entity = "Cart" if "cart" in step_action.lower() else "CartItem"
```

**Impact:** 2 tests fixed

---

### Category B: Seed ID Resolution (2 failures)

**Problem:** `{{seed_id}}` placeholder not resolved to correct UUID for DELETE operations.

**Affected Scenarios:**
- `delete_cart_happy_path`: Uses `{{seed_id}}` but needs `00000000-0000-4000-8000-000000000013`
- `remove_item_from_order_happy_path`: Uses `{{seed_id}}` for both order and product

**Root Cause:** SmokeRunnerV2 doesn't resolve `{{seed_id}}` to delete-specific UUIDs.

**Location:** `src/validation/smoke_runner_v2.py` → `_resolve_path_params()`

**Fix:**
```python
# Map {{seed_id}} to entity-specific delete UUIDs
DELETE_SEED_MAP = {
    "Cart": "00000000-0000-4000-8000-000000000013",
    "Order": "00000000-0000-4000-8000-000000000015",
    "OrderItem": "00000000-0000-4000-8000-000000000023",
}
```

**Impact:** 2 tests fixed

---

### Category C: Validation Error Tests (2 failures)

**Problem:** PUT endpoints accept invalid data (return 200) when they should reject (422).

**Affected Scenarios:**
- `update_product_validation_error`: Empty/invalid body accepted
- `update_cart_item_quantity_validation_error`: Invalid quantity accepted

**Root Cause:** Generated Pydantic schemas lack proper validation rules.

**Location:** `src/models/schemas.py` (generated)

**Fix:** Add validators to generated schemas:
```python
class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    price: Optional[Decimal] = Field(None, gt=0)
    
    @validator('name', 'price', pre=True)
    def reject_empty(cls, v):
        if v is not None and (v == "" or v <= 0):
            raise ValueError("Invalid value")
        return v
```

**Alternative:** Update IR generator to include validation constraints.

**Impact:** 2 tests fixed

---

### Category D: Missing request_schema in Inferred Endpoints (1 failure) ✅ FIXED

**Problem:** `add_item_to_order_not_found` returns 422 (validation) before checking if order exists (404).

**Root Cause:** The `inferred_endpoint_enricher.py` creates nested resource PUT endpoints WITHOUT `request_schema`.
When `tests_ir_generator.py` checks `if endpoint.request_schema:`, it's None, so no body is generated for the `_not_found` test.
FastAPI then rejects the missing body with 422 before the handler can check for 404.

**Location:** `src/services/inferred_endpoint_enricher.py` → `_infer_nested_resource_endpoints()`

**Fix (Bug #199):** Added `_build_request_schema_from_entity()` method that:
1. Extracts updatable fields from child entity (OrderItem, CartItem)
2. Excludes FK fields (they come from path params)
3. Excludes auto-generated fields (id, created_at, updated_at)
4. Creates `APISchema` with proper field types

```python
def _build_request_schema_from_entity(self, entity, parent_singular) -> Optional[APISchema]:
    # Extracts fields like quantity, unit_price from OrderItem
    # Returns APISchema(name="OrderItemUpdate", fields=[...])
```

**Impact:** 1 test fixed

---

### Category E: Business Logic - Checkout (1 failure)

**Problem:** `checkout_happy_path` fails because cart `...03` has items but checkout still returns 422.

**Root Cause:** Checkout validation may require additional conditions (payment method, shipping address, etc.)

**Location:** `src/services/order_service.py` or checkout route

**Investigation Needed:**
1. Check what validation returns 422
2. Verify cart has items in seeded data
3. Update test body with required fields OR relax validation

**Impact:** 1 test fixed

---

## 📋 Implementation Priority

| Priority | Task | Effort | Impact | Dependencies |
|----------|------|--------|--------|--------------|
| P0 | Fix Flow IR Generation (A) | Medium | 2 tests | None |
| P1 | Fix Seed ID Resolution (B) | Low | 2 tests | None |
| P2 | Fix Existence Check Order (D) | Low | 1 test | Pattern in PatternBank |
| P3 | Fix Validation Schemas (C) | Medium | 2 tests | Schema generation |
| P4 | Fix Checkout Logic (E) | High | 1 test | Business logic analysis |

---

## 🎯 Expected Results

After implementing P0-P2 (quick wins):
- **Pass rate: 94.6%** (70/74) ✅ Target achieved

After implementing all:
- **Pass rate: 100%** (74/74)

---

## 📁 Files to Modify

1. `src/services/tests_ir_generator.py` - Flow step mapping (Bug A)
2. `src/validation/smoke_runner_v2.py` - Seed ID resolution (Bug B)
3. `src/cognitive/patterns/pattern_bank.py` - Existence check pattern (Bug D)
4. `src/services/code_generation_service.py` - Schema validators (Bug C)
5. Generated app routes - Checkout logic (Bug E)

---

## 🔄 Verification

```bash
# After each fix, run:
python -m pytest tests/e2e/real_e2e_full_pipeline.py -k ecommerce -v

# Check specific scenarios:
grep -E "validation_error|checkout|delete.*happy" ir_smoke_test_results.json
```

