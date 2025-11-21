# Ecommerce API - Simple Spec

## 1. Overview

Build a **basic e-commerce backend API** (backend only, no frontend) that allows:

- Manage products
- Manage customers
- Manage shopping carts
- Create orders from the cart
- Query order history

No real payment integration is required: a simulated `payment_status` will be used.

Expected complexity: **0.45 (Simple–Medium)**.

---

## 2. Domain Model (Conceptual)

Main entities:

1. **Product**
   - id (UUID)
   - name (string, required)
   - description (string, optional)
   - price (decimal, required, > 0)
   - stock (int, required, >= 0)
   - is_active (bool, default true)

2. **Customer**
   - id (UUID)
   - email (string, required, email format, unique)
   - full_name (string, required)
   - created_at (datetime, read-only)

3. **Cart**
   - id (UUID)
   - customer_id (UUID, reference to Customer)
   - items: list of CartItem
   - status: enum ["OPEN", "CHECKED_OUT"] (default "OPEN")

4. **CartItem**
   - product_id (UUID, reference to Product)
   - quantity (int, required, > 0)
   - unit_price (decimal, copy of product price at time of adding)

5. **Order**
   - id (UUID)
   - customer_id (UUID)
   - items: list of OrderItem
   - total_amount (decimal, calculated)
   - status: enum ["PENDING_PAYMENT", "PAID", "CANCELLED"]
   - payment_status: enum ["PENDING", "SIMULATED_OK", "FAILED"]
   - created_at (datetime)

6. **OrderItem**
   - product_id (UUID)
   - quantity (int, > 0)
   - unit_price (decimal, copy of price at time of order)

---

## 3. Functional Requirements

### Products

**F1. Create product**  
API must allow creating products with `name`, `description`, `price`, `stock`, and `is_active`.

**F2. List active products**  
Endpoint to list products where `is_active = true` with simple pagination (`page`, `page_size`).

**F3. Get product detail**  
Endpoint to get a product by `id`. If not found, return 404.

**F4. Update product**  
Allow updating `name`, `description`, `price`, `stock`, and `is_active`.

**F5. Deactivate product**  
Allow deactivating a product (`is_active = false`) without physically deleting it.

---

### Customers

**F6. Register customer**  
Endpoint to create a `Customer` with `email` and `full_name`.  
If `email` already exists, return 400.

**F7. Get customer by id**  
Endpoint to get a customer by `id`. If not found, return 404.

---

### Cart

**F8. Create cart for customer**  
Create an `OPEN` cart for a `customer_id`.  
If an `OPEN` cart already exists for that customer, reuse it (do not create a new one).

**F9. Add item to cart**  
Allow adding a product to the cart:
- If the product is inactive or out of stock, return 400.
- If the item already exists in the cart, increase quantity.
- Store `unit_price` using the current product price.

**F10. View current cart**  
Endpoint to get the customer's `OPEN` cart, including items and subtotals.

**F11. Update item quantity**  
Allow modifying `quantity`:
- If `quantity <= 0`, remove the item.
- If new quantity exceeds available stock, return 400.

**F12. Clear cart**  
Endpoint to delete all items from an `OPEN` cart.

---

### Orders

**F13. Checkout cart**  
Create an `Order` from the `OPEN` cart:

- Compute `total_amount` as the sum of (`unit_price * quantity`).
- Validate stock for all products.
- Deduct stock when confirming the order.
- Change cart status to `CHECKED_OUT`.
- Create the order with:
  - `status = "PENDING_PAYMENT"`
  - `payment_status = "PENDING"`

**F14. Simulate successful payment**  
Endpoint to mark an order as paid:
- Change `status` to `"PAID"` and `payment_status` to `"SIMULATED_OK"`.
- Only allowed if order is `"PENDING_PAYMENT"`.

**F15. Cancel order**  
Endpoint to cancel an order:
- Only allowed if `status` is `"PENDING_PAYMENT"`.
- Restore product stock (sum quantities back).

**F16. List customer orders**  
Endpoint to list all orders for a customer, with optional filter by `status`.

**F17. Get order detail**
Endpoint to get an order by `id`. If not found, return 404.

---

## 3.5. Business Validations

**V1. Price validation**
Product price must be greater than 0. Price > 0 is enforced.

**V2. Stock validation**
Product stock must be non-negative. Stock >= 0 is enforced.

**V3. Quantity validation**
Cart item quantity must be positive. Quantity > 0 is required.

**V4. Order quantity validation**
Order item quantity must be positive. Quantity > 0 is required.

**V5. Email format validation**
Customer email must be valid email format.

---

## 4. Non-Functional Requirements

**NF1. Framework**  
Use a modern web framework such as **FastAPI** or similar (depending on system templates).

**NF2. Persistence**  
In-memory storage is acceptable for this demo, but the API must be designed as if persistent.

**NF3. Validation**  
Use typed data models (e.g., Pydantic) and return clear 422/400 errors.

**NF4. Code structure**  
Separate:
- models / schemas
- routes / controllers
- business logic where applicable

**NF5. Tests**  
Include a minimal set of automated tests:

- Create and list products
- Register customer
- Full flow: create cart → add product → checkout → mark payment OK
- Attempt checkout without sufficient stock (should fail)

**NF6. Documentation**  
Expose automatic API documentation (OpenAPI/Swagger).

**NF7. Healthcheck**
Include a simple healthcheck endpoint returning:
```json
{ "message": "Ecommerce API", "status": "running" }
```

---

## Classification Ground Truth

F1_create_product:
  domain: crud
  risk: high

F2_list_products:
  domain: crud
  risk: medium

F3_get_product:
  domain: crud
  risk: low

F4_update_product:
  domain: crud
  risk: high

F5_deactivate_product:
  domain: crud
  risk: medium

F6_register_customer:
  domain: authentication
  risk: high

F7_get_customer:
  domain: crud
  risk: low

F8_create_cart:
  domain: workflow
  risk: medium

F9_add_item:
  domain: workflow
  risk: high

F10_view_cart:
  domain: crud
  risk: low

F11_update_quantity:
  domain: workflow
  risk: medium

F12_clear_cart:
  domain: crud
  risk: medium

F13_checkout:
  domain: payment
  risk: high

F14_payment:
  domain: payment
  risk: high

F15_cancel_order:
  domain: payment
  risk: medium

F16_list_orders:
  domain: crud
  risk: low

F17_get_order:
  domain: crud
  risk: low

## Expected Dependency Graph (Ground Truth)

node_count: 17
nodes:
  - create_product
  - list_products
  - get_product
  - update_product
  - deactivate_product
  - register_customer
  - get_customer
  - create_cart
  - add_item
  - view_cart
  - update_quantity
  - clear_cart
  - checkout
  - payment
  - cancel_order
  - list_orders
  - get_order

edge_count: 15
edges:
  - create_product → list_products
  - create_product → get_product
  - create_product → update_product
  - create_product → deactivate_product
  - register_customer → get_customer
  - register_customer → create_cart
  - register_customer → list_orders
  - create_cart → add_item
  - add_item → view_cart
  - add_item → update_quantity
  - add_item → clear_cart
  - view_cart → checkout
  - checkout → payment
  - checkout → cancel_order
  - checkout → get_order
