# Smoke Test Failure Analysis - Run 1764323550

**Date**: 2025-11-28
**Test Run ID**: ecommerce-api-spec-human_1764323550
**Pass Rate**: 72.6% (58/84 passed, 26 failed)

---

## Executive Summary

Analysis of 26 smoke test failures reveals **4 root cause categories**:

| Category | Count | % | Responsible Component |
|----------|-------|---|----------------------|
| Code Generation Bugs | 13 | 50% | `production_code_generators.py`, `modular_architecture_generator.py` |
| Seed Data Sync Issues | 5 | 19% | `ir_test_generator.py` (seed_db generation) |
| Validation Not Implemented | 5 | 19% | `production_code_generators.py` (service layer) |
| Test Plan Bugs (LLM) | 3 | 12% | LLM Smoke Test Planner |

---

## Category 1: Code Generation Bugs (13 failures)

### Bug #120: Health Router Has CRUD Routes
**Severity**: HIGH
**Endpoint**: `GET /health` → 500 Internal Server Error
**Expected**: 200

**Root Cause**:
```python
# health.py:53-57 - THIS SHOULD NOT EXIST
@router.get('/')
async def list_healths(db: AsyncSession=Depends(get_db)):
    service = HealthService(db)  # ❌ HealthService doesn't exist!
    result = await service.list(page=1, size=100)
    return result.items
```

**Fix Location**: `src/services/production_code_generators.py`
- Health router template should NOT include CRUD routes
- Health endpoints are infrastructure, not entity endpoints

---

### Bug #127: CartItemCreate Requires unit_price
**Severity**: HIGH
**Endpoint**: `POST /carts/{cart_id}/items` → 422
**Expected**: 201

**Root Cause**:
```python
# schemas.py:26-31
class CartItemCreate(BaseSchema):
    cart_id: UUID
    product_id: UUID
    quantity: int = Field(..., gt=0, ge=1)
    unit_price: float = Field(..., gt=0, ge=0.01)  # ❌ Should be Optional or auto-calculated
```

**Test Payload**:
```json
{"product_id": "...", "quantity": 1}  // Missing unit_price
```

**Fix**: `unit_price` should be auto-calculated from Product.price in the service layer, not required in create schema.

---

### Bug #128: OrderCreate Schema Incompatible with Checkout Flow
**Severity**: HIGH
**Endpoint**: `POST /orders` → 422
**Expected**: 201

**Root Cause**:
```python
# schemas.py:224-229
class OrderCreate(BaseSchema):
    customer_id: UUID  # ❌ Test sends cart_id instead
    order_status: str = Field('PENDING_PAYMENT')
    payment_status: str = Field('PENDING')
    total_amount: float = Field(..., ge=0)  # ❌ Should be auto-calculated
```

**Test Payload**:
```json
{"cart_id": "00000000-0000-4000-8000-000000000003"}
```

**Fix**: OrderCreate should accept `cart_id` for checkout flow. The service extracts customer_id from cart and calculates total_amount.

---

### Bug #129: PUT Nested Resource Routes Broken
**Severity**: MEDIUM
**Endpoint**: `PUT /carts/{id}/items/{product_id}` → 422
**Expected**: 200

**Root Cause**: Route expects body with full CartItemUpdate but test sends no body (expecting upsert behavior).

**Fix**: Nested PUT routes should support upsert pattern without required body.

---

### Bug #130: GET /customers/{id}/orders Returns Wrong Type
**Severity**: HIGH
**Endpoint**: `GET /customers/{customer_id}/orders` → Returns CustomerResponse
**Expected**: List[OrderResponse]

**Root Cause**:
```python
# customer.py:59-76
@router.get("/{customer_id}/orders", response_model=CustomerResponse)  # ❌ Wrong response model
async def returns_all_orders_for_a_customer(...):
    customer = await service.get_by_id(customer_id)
    return customer  # ❌ Returns customer, not orders!
```

**Fix**: Should query OrderService for orders where customer_id matches.

---

### Bug #131: PUT /orders/{id}/items/{product_id} Broken
**Severity**: MEDIUM
**Endpoint**: `PUT /orders/{id}/items/{product_id}` → 422
**Expected**: 200

**Same issue as Bug #129** - nested resource pattern not properly implemented.

---

### Bug #132: DELETE /orders/{id}/items/{product_id} Deletes Order
**Severity**: HIGH
**Endpoint**: `DELETE /orders/{id}/items/{product_id}` → 404
**Expected**: 204

**Root Cause**:
```python
# order.py:153-170
@router.delete("/{id}/items/{product_id}")
async def remove_item_from_order(...):
    success = await service.delete(id)  # ❌ Deletes the ORDER, not the item!
```

**Fix**: Should delete OrderItem where order_id=id AND product_id=product_id.

---

### Bug #133: Checkout Flow Error
**Severity**: HIGH
**Endpoint**: `POST /carts/{id}/checkout` → 500
**Expected**: 200

**Root Cause**: Internal error in checkout service - likely related to Bug #128 (schema mismatch).

---

### Bug #134: Action Endpoints Return 201 Instead of 200
**Severity**: MEDIUM
**Endpoints**: `/pay`, `/cancel` return 201
**Expected**: 200

**Root Cause**:
```python
# order.py:39
@router.post("/{order_id}/pay", status_code=status.HTTP_201_CREATED)  # ❌ Should be 200
```

**Fix**: Action endpoints (pay, cancel, deactivate, etc.) should return 200, not 201.

---

## Category 2: Test Plan Bugs - LLM (3 failures)

### Bug #121a/b: max_length Validation Tests Use Placeholder Strings
**Severity**: MEDIUM
**Endpoints**:
- `POST /products` validation_error_name_too_long → 201 (expected 422)
- `POST /products` validation_error_description_too_long → 201 (expected 422)

**Root Cause**:
```json
// llm_smoke_test_plan.json:258
{
  "name": "validation_error_name_too_long",
  "payload": {
    "name": "TOO_LONG_STRING",  // ❌ Only 15 chars! max_length=255
    ...
  }
}
```

**Fix**: LLM smoke test planner should generate actual long strings, not placeholder text.

---

### Bug #135: PATCH with Empty Body is Valid
**Severity**: LOW
**Endpoint**: `PATCH /carts/{cart_id}/items/{item_id}` validation_error_missing_quantity
**Test sends**: `{}`
**Got**: 200 (expected 422)

**Root Cause**: Empty body is valid for PATCH - it just doesn't update anything. This is correct HTTP semantics.

**Fix**: Test plan should not expect 422 for empty PATCH body.

---

## Category 3: Seed Data Sync Issues (5 failures)

### Bug #122: Product ...0011 Not Seeded
**Endpoint**: `DELETE /products/{id}` → 404
**Test Uses**: UUID `00000000-0000-4000-8000-000000000011`

**Root Cause**: Test plan defines this product but seed_db.py doesn't create it.

**Test Plan Seed Data**:
```json
{
  "entity_name": "Product",
  "uuid": "00000000-0000-4000-8000-000000000011",
  "fields": {
    "name": "Inactive Product",
    "is_active": false
  }
}
```

**seed_db.py Only Creates**:
```python
# Only creates ...0001, NOT ...0011
test_product = ProductEntity(
    id=UUID("00000000-0000-4000-8000-000000000001"),
    ...
)
```

---

### Bug #123: Same as #122
**Endpoint**: `PATCH /products/{id}/activate` → 404
**Same root cause**: Product ...0011 not seeded.

---

### Bug #136: Cart ...0013 Not Seeded
**Endpoint**: `DELETE /carts/{id}` → 404
**Test Uses**: UUID `00000000-0000-4000-8000-000000000013`

**Same pattern**: Test plan defines it, seed_db.py doesn't create it.

---

### Bug #137/138: Order Action Endpoints Return 404
**Endpoints**:
- `POST /orders/{order_id}/pay` → 404
- `POST /orders/{order_id}/cancel` → 404

**Possible Causes**:
1. Seed data race condition
2. Order state invalidated by prior test
3. Route parameter name mismatch

---

## Category 4: Validation Not Implemented (5 failures)

### Bug #124: Duplicate Email Not Rejected
**Endpoint**: `POST /customers` with existing email → 201
**Expected**: 400

**Fix**: CustomerService.create() should check for existing email.

---

### Bug #125: Invalid Customer FK Not Rejected
**Endpoint**: `POST /carts` with non-existent customer_id → 201
**Expected**: 400

**Fix**: CartService.create() should validate customer exists.

---

### Bug #126: Inactive Product Added to Cart
**Endpoint**: `POST /carts/{id}/items` with inactive product → Success
**Expected**: 400

**Fix**: CartItemService should check product.is_active.

---

## Fix Priority Matrix

| Priority | Bug IDs | Impact | Effort |
|----------|---------|--------|--------|
| P0 | #120 | Breaks health checks | Low |
| P1 | #127, #128 | Core CRUD broken | Medium |
| P1 | #130, #132 | Nested resources broken | Medium |
| P2 | #122, #123, #136 | Seed sync | Low |
| P2 | #121a/b | Test accuracy | Low |
| P3 | #124-126 | Business validation | Medium |
| P3 | #134 | Status codes | Low |

---

## Recommended Fixes by Component

### 1. production_code_generators.py
- [ ] Bug #120: Don't add CRUD routes to health router
- [ ] Bug #134: Use 200 for action endpoints, not 201
- [ ] Bug #130: Fix nested GET routes to return correct type
- [ ] Bug #132: Fix nested DELETE to delete child, not parent

### 2. modular_architecture_generator.py (schemas)
- [ ] Bug #127: Make CartItemCreate.unit_price optional
- [ ] Bug #128: Add cart_id to OrderCreate for checkout flow

### 3. ir_test_generator.py (seed_db)
- [ ] Bug #122/123/136: Sync seed_db.py with test plan seed_data

### 4. LLM Smoke Test Planner (planner_agent.py)
- [ ] Bug #121: Generate actual long strings for max_length tests
- [ ] Bug #135: Don't expect 422 for empty PATCH body

### 5. Service Layer Templates
- [ ] Bug #124: Add uniqueness validation for Customer.email
- [ ] Bug #125: Add FK validation for Cart.customer_id
- [ ] Bug #126: Add is_active check for CartItem.product_id

---

## Files Modified in This Analysis

- `tests/e2e/generated_apps/ecommerce-api-spec-human_1764323550/src/api/routes/health.py`
- `tests/e2e/generated_apps/ecommerce-api-spec-human_1764323550/src/api/routes/product.py`
- `tests/e2e/generated_apps/ecommerce-api-spec-human_1764323550/src/api/routes/order.py`
- `tests/e2e/generated_apps/ecommerce-api-spec-human_1764323550/src/api/routes/customer.py`
- `tests/e2e/generated_apps/ecommerce-api-spec-human_1764323550/src/models/schemas.py`
- `tests/e2e/generated_apps/ecommerce-api-spec-human_1764323550/scripts/seed_db.py`
- `tests/e2e/generated_apps/ecommerce-api-spec-human_1764323550/llm_smoke_test_plan.json`
