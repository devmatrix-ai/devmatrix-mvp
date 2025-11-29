# Smoke Test Failures Investigation Report

**Date:** 2025-11-28
**App ID:** ecommerce-api-spec-human_1764360586
**Phase:** 8.5 (Runtime Smoke Testing)

## Executive Summary

| Metric | Value |
|--------|-------|
| Endpoints Tested | 85 |
| Endpoints Passed | 31 |
| Endpoints Failed | 54 |
| **Pass Rate** | **36.5%** |

### Error Distribution

| HTTP Status | Count | Percentage | Root Cause |
|-------------|-------|------------|------------|
| 500 (Server Error) | 18 | 33.3% | Bug #131 - Pydantic to Repository |
| 404 (Not Found) | 32 | 59.3% | Multiple issues (see below) |
| 422 (Validation Error) | 3 | 5.6% | Missing request body fields |
| 405 (Method Not Allowed) | 1 | 1.8% | Route not implemented |

---

## Category 1: HTTP 500 - Server Errors (18 failures)

### Root Cause: Bug #131
**File:** `src/services/production_code_generators.py`

The Service layer template passes a Pydantic model directly to the Repository, but SQLAlchemy entities expect a `dict`:

```python
# WRONG (Bug #131)
db_obj = await self.repo.create(data)  # data is Pydantic model

# CORRECT (Fix applied)
db_obj = await self.repo.create(data.model_dump())
```

### Affected Endpoints

| Endpoint | Scenario | Expected | Actual |
|----------|----------|----------|--------|
| POST /products | create_product_happy_path | 201 | 500 |
| POST /products | F1: Create Product_2_create | 201 | 500 |
| POST /products | F1: Create Product_3_create | 201 | 500 |
| POST /customers | register_customer_happy_path | 201 | 500 |
| POST /products | F6: Register Customer_3_create | 201 | 500 |
| POST /products | F6: Register Customer_4_create | 201 | 500 |
| POST /carts | create_cart_happy_path | 201 | 500 |
| POST /products | F8: Create Cart_3_create | 201 | 500 |
| POST /products | F8: Create Cart_4_create | 201 | 500 |
| POST /products | F9: Add Item to Cart_6_create | 201 | 500 |
| POST /products | F9: Add Item to Cart_7_create | 201 | 500 |
| POST /products | F13: Checkout (Create Order)_5_create | 201 | 500 |
| POST /products | F13: Checkout (Create Order)_6_create | 201 | 500 |
| POST /products | F13: Checkout (Create Order)_9_create | 201 | 500 |

**Note:** Some F* scenarios incorrectly call POST /products when they should call other endpoints (bug in test scenario generator).

---

## Category 2: HTTP 404 - Not Found (32 failures)

### Overview

404 errors occur when:
1. The seed data doesn't exist in the database
2. Path parameter substitution doesn't match route definitions
3. Routes use inconsistent parameter names

### Path Parameter Inconsistency Analysis

**File:** `src/api/routes/product.py`

```python
# Lines 51, 71, 92 use {product_id}:
@router.get("/{product_id}", ...)
@router.put("/{product_id}", ...)
@router.post("/{product_id}/deactivate", ...)

# Lines 112, 132, 152 use {id}:
@router.delete("/{id}", ...)
@router.patch("/{id}/deactivate", ...)
@router.patch("/{id}/activate", ...)
```

This inconsistency is replicated across all route files:
- `customer.py`: `{customer_id}` vs `{id}`
- `cart.py`: `{cart_id}` vs `{id}`
- `order.py`: `{order_id}` vs `{id}`

### Validator Substitution Logic

**File:** `src/validation/runtime_smoke_validator.py:461-508`

```python
def _substitute_path_params(self, path: str) -> str:
    uuid_product = '00000000-0000-4000-8000-000000000001'
    uuid_customer = '00000000-0000-4000-8000-000000000002'
    uuid_cart = '00000000-0000-4000-8000-000000000003'
    uuid_order = '00000000-0000-4000-8000-000000000005'

    substitutions = [
        (r'\{product_id\}', uuid_product),
        (r'\{customer_id\}', uuid_customer),
        # ...
    ]

    # Handle generic {id} based on path context
    if '{id}' in result:
        if '/products' in path:
            result = result.replace('{id}', uuid_product)
        # ...
```

The validator handles BOTH patterns correctly, so substitution should work.

### Seed Data UUIDs

**File:** `scripts/seed_db.py`

```python
Product:  00000000-0000-4000-8000-000000000001
Customer: 00000000-0000-4000-8000-000000000002
Cart:     00000000-0000-4000-8000-000000000003
Order:    00000000-0000-4000-8000-000000000005
```

These UUIDs MATCH the validator substitution values.

### Hypothesis for 404 Errors

**Bug #133 (New):** Seed data may not be reaching the Docker container.

Evidence:
1. Path substitution is correct (both `{product_id}` and `{id}` handled)
2. Seed UUIDs match validator UUIDs
3. But GET requests to valid UUIDs return 404

Possible causes:
- `seed_db.py` not executing in Docker
- Database connection issue between db-init and app container
- Alembic migrations not creating tables before seed

### Affected Endpoints (404)

| Endpoint | Scenario | Expected | Actual |
|----------|----------|----------|--------|
| GET /products/{product_id} | get_product_happy_path | 200 | 404 |
| PUT /products/{product_id} | update_product_happy_path | 200 | 404 |
| POST /products/{product_id}/deactivate | deactivate_product_happy_path | 201 | 404 |
| GET /customers/{customer_id} | get_customer_happy_path | 200 | 404 |
| GET /carts/{cart_id} | get_cart_happy_path | 200 | 404 |
| GET /orders/{order_id} | get_order_happy_path | 200 | 404 |
| POST /orders/{order_id}/pay | pay_order_happy_path | 201 | 404 |
| POST /orders/{order_id}/cancel | cancel_order_happy_path | 201 | 404 |
| GET /customers/{customer_id}/orders | list_customer_orders_happy_path | 200 | 404 |
| DELETE /customers/{id} | delete_customer_happy_path | 204 | 404 |
| DELETE /orders/{id} | delete_order_happy_path | 204 | 404 |
| DELETE /carts/{id} | delete_cart_happy_path | 204 | 404 |
| DELETE /products/{id} | delete_product_happy_path | 204 | 404 |
| PATCH /products/{id}/deactivate | deactivate_product_happy_path | 200 | 404 |
| PATCH /products/{id}/activate | activate_product_happy_path | 200 | 404 |
| POST /carts/{id}/checkout | checkout_cart_happy_path | 201 | 404 |
| PUT /carts/{id}/items/{product_id} | add_item_to_cart_happy_path | 200 | 404 |
| DELETE /carts/{id}/items/{product_id} | remove_item_from_cart_happy_path | 204 | 404 |
| PUT /orders/{id}/items/{product_id} | add_item_to_order_happy_path | 200 | 404 |
| DELETE /orders/{id}/items/{product_id} | remove_item_from_order_happy_path | 204 | 404 |
| POST /carts/{cart_id}/clear | clear_cart_happy_path | 201 | 404 |
| PUT /products/{product_id} | F4: Update Product_3_update | 200 | 404 |
| PUT /products/{product_id} | F4: Update Product_4_update | 200 | 404 |
| PUT /products/{product_id} | F5: Deactivate Product_2_update | 200 | 404 |
| PUT /products/{product_id} | F5: Deactivate Product_3_update | 200 | 404 |
| DELETE /customers/{id} | F11: Update Item Quantity_3_delete | 204 | 404 |
| PUT /products/{product_id} | F11: Update Item Quantity_5_update | 200 | 404 |
| PUT /products/{product_id} | F11: Update Item Quantity_6_update | 200 | 404 |
| DELETE /customers/{id} | F12: Clear Cart_2_delete | 204 | 404 |
| PUT /products/{product_id} | F13: Checkout (Create Order)_4_update | 200 | 404 |
| PUT /products/{product_id} | F13: Checkout (Create Order)_8_update | 200 | 404 |
| PUT /products/{product_id} | F14: Pay Order (Simulated)_3_update | 200 | 404 |
| PUT /products/{product_id} | F14: Pay Order (Simulated)_4_update | 200 | 404 |
| PUT /products/{product_id} | F15: Cancel Order_3_update | 200 | 404 |
| PUT /products/{product_id} | F15: Cancel Order_4_update | 200 | 404 |
| PUT /products/{product_id} | F15: Cancel Order_5_update | 200 | 404 |

---

## Category 3: HTTP 422 - Validation Errors (3 failures)

### Root Cause: Missing Request Body Fields

The validator generates minimal payloads based on endpoint schemas. When schemas are incomplete or the endpoint expects complex nested data, 422 errors occur.

### Affected Endpoints

| Endpoint | Scenario | Expected | Actual |
|----------|----------|----------|--------|
| POST /carts/{cart_id}/items | add_item_to_cart_happy_path | 201 | 422 |
| POST /orders | checkout_happy_path | 201 | 422 |
| GET /customers/{customer_id}/orders | list_customer_orders_no_optional_params | 200 | 422 |

### Analysis

**POST /carts/{cart_id}/items:**

Looking at `cart.py:59-77`:
```python
@router.post("/{cart_id}/items", response_model=CartResponse, status_code=status.HTTP_201_CREATED)
async def adds_a_specific_product_with_quantity_to_the_cart(...):
    cart_data: CartCreate,  # WRONG: Should be CartItemCreate
```

**Bug #134 (New):** The route incorrectly expects `CartCreate` instead of `CartItemCreate` schema for adding items.

**POST /orders:**
The checkout endpoint likely needs `cart_id` and `payment_info` fields that aren't being generated.

---

## Category 4: HTTP 405 - Method Not Allowed (1 failure)

### Affected Endpoint

| Endpoint | Scenario | Expected | Actual |
|----------|----------|----------|--------|
| PATCH /carts/{cart_id}/items/{item_id} | update_cart_item_quantity_happy_path | 200 | 405 |

### Analysis

Looking at `cart.py`, the route `@router.patch("/{cart_id}/items/{item_id}")` exists at line 80.

**Hypothesis:** Route registration issue or path conflict with another route.

---

## New Bugs Identified

### Bug #133: Seed Data Not Persisting in Docker
- **Severity:** High
- **Impact:** All GET/PUT/DELETE with path parameters fail with 404
- **Location:** `docker/docker-compose.yml` → db-init service
- **Investigation:** Check if seed_db.py runs successfully and commits data

### Bug #134: Wrong Schema for POST /carts/{cart_id}/items
- **Severity:** Medium
- **Impact:** Cannot add items to cart
- **Location:** `src/api/routes/cart.py:59`
- **Fix:** Change `CartCreate` to `CartItemCreate`

### Bug #135: Inconsistent Path Parameter Names
- **Severity:** Low
- **Impact:** Code maintainability
- **Location:** All route files
- **Note:** Currently handled by validator, but should be standardized

---

## Files Analyzed

| File | Location | Purpose |
|------|----------|---------|
| smoke_test_results.json | generated_app/ | Test results |
| runtime_smoke_validator.py | src/validation/ | Path substitution logic |
| product.py | src/api/routes/ | Product endpoint definitions |
| customer.py | src/api/routes/ | Customer endpoint definitions |
| cart.py | src/api/routes/ | Cart endpoint definitions |
| seed_db.py | scripts/ | Seed data creation |
| docker-compose.yml | docker/ | Container orchestration |

---

## Recommended Investigation Steps

1. **Verify Docker seed execution:**
   ```bash
   docker logs app_db_init 2>&1 | grep -E "(seed|Created|Error)"
   ```

2. **Check database content after seed:**
   ```bash
   docker exec app_postgres psql -U devmatrix -d app_db -c "SELECT id FROM products;"
   ```

3. **Test API manually:**
   ```bash
   curl http://localhost:8002/products/00000000-0000-4000-8000-000000000001
   ```

4. **Check Alembic migrations:**
   ```bash
   docker exec app_app alembic current
   ```

---

## Summary

The 54 smoke test failures fall into two main categories:

1. **Bug #131 (Fixed):** POST endpoints returning 500 due to Pydantic→Repository issue
2. **Bug #133 (New):** GET/PUT/DELETE endpoints returning 404 - likely seed data issue

After fixing Bug #131, the pass rate improved from 36.5% to 52.3% (as documented in SESSION_2025-11-28_BUG131_132.md).

The remaining 404 errors require investigation into the Docker seed process to understand why test data isn't being found.
