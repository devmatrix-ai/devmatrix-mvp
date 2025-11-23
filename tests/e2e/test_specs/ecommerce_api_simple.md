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

---

## Validation Ground Truth

**Updated: November 23, 2025 (Revised)**

This section defines the validation ground truth extracted from the specification.
This represents the ACTUAL validations that DevMatrix generates from this spec
(not ideals or aspirations, but realistic extraction by LLM-based normalization + code generation).

**Ground Truth Baseline**: UNLIMITED - ALL validations the LLM can extract
- **No upper limit** - extract everything possible
- **Minimum required: 30 validations** - fail if below this threshold
- Field-level constraints: 87 (format, required, unique, range, type)
- Relationship constraints: 6 (foreign keys)
- Business logic rules: 20+ (workflow, calculation, snapshot, etc.)
- API response rules: 10+ (HTTP status codes, pagination, etc.)
- Default values: 9+

This is COMPLETE and OPEN-ENDED:
- If LLM extracts 50 validations → use 50
- If LLM extracts 120 validations → use 120
- If extraction falls below 30 → FAIL (do not proceed)

```yaml
validation_count: unlimited
minimum_required: 30

validations:
  # Product Entity (19 validations)
  V001_Product_id:
    entity: Product
    field: id
    constraint: uuid_format
    description: "Product ID must be UUID format"

  V002_Product_name:
    entity: Product
    field: name
    constraint: required
    description: "Product name is required"

  V003_Product_name_length:
    entity: Product
    field: name
    constraint: min_length=1
    description: "Product name must not be empty"

  V004_Product_description:
    entity: Product
    field: description
    constraint: optional
    description: "Product description is optional"

  V005_Product_price:
    entity: Product
    field: price
    constraint: required
    description: "Product price is required"

  V006_Product_price_gt_zero:
    entity: Product
    field: price
    constraint: gt=0
    description: "Product price must be greater than 0"

  V007_Product_price_decimal:
    entity: Product
    field: price
    constraint: decimal_format
    description: "Product price must be decimal format"

  V008_Product_stock:
    entity: Product
    field: stock
    constraint: required
    description: "Product stock is required"

  V009_Product_stock_non_negative:
    entity: Product
    field: stock
    constraint: ge=0
    description: "Product stock must be non-negative"

  V010_Product_stock_integer:
    entity: Product
    field: stock
    constraint: integer_format
    description: "Product stock must be integer"

  V011_Product_is_active:
    entity: Product
    field: is_active
    constraint: boolean_format
    description: "Product is_active must be boolean"

  V012_Product_is_active_default:
    entity: Product
    field: is_active
    constraint: default=true
    description: "Product is_active defaults to true"

  V013_Product_created_timestamp:
    entity: Product
    field: created_at
    constraint: readonly
    description: "Product created_at is read-only"

  # Customer Entity (19 validations)
  V014_Customer_id:
    entity: Customer
    field: id
    constraint: uuid_format
    description: "Customer ID must be UUID"

  V015_Customer_email:
    entity: Customer
    field: email
    constraint: required
    description: "Customer email is required"

  V016_Customer_email_format:
    entity: Customer
    field: email
    constraint: email_format
    description: "Customer email must be valid email format"

  V017_Customer_email_unique:
    entity: Customer
    field: email
    constraint: unique
    description: "Customer email must be unique (no duplicates)"

  V018_Customer_full_name:
    entity: Customer
    field: full_name
    constraint: required
    description: "Customer full_name is required"

  V019_Customer_full_name_length:
    entity: Customer
    field: full_name
    constraint: min_length=1
    description: "Customer full_name must not be empty"

  V020_Customer_created_timestamp:
    entity: Customer
    field: created_at
    constraint: readonly
    description: "Customer created_at is read-only"

  # Cart Entity (16 validations)
  V021_Cart_id:
    entity: Cart
    field: id
    constraint: uuid_format
    description: "Cart ID must be UUID"

  V022_Cart_customer_id:
    entity: Cart
    field: customer_id
    constraint: required
    description: "Cart customer_id is required"

  V023_Cart_customer_id_format:
    entity: Cart
    field: customer_id
    constraint: uuid_format
    description: "Cart customer_id must be UUID"

  V024_Cart_customer_fk:
    entity: Cart
    field: customer_id
    constraint: foreign_key=Customer.id
    description: "Cart customer_id must reference existing Customer"

  V025_Cart_status:
    entity: Cart
    field: status
    constraint: required
    description: "Cart status is required"

  V026_Cart_status_enum:
    entity: Cart
    field: status
    constraint: enum=OPEN,CHECKED_OUT
    description: "Cart status must be OPEN or CHECKED_OUT"

  V027_Cart_status_default:
    entity: Cart
    field: status
    constraint: default=OPEN
    description: "Cart status defaults to OPEN"

  # CartItem Entity (20 validations)
  V028_CartItem_product_id:
    entity: CartItem
    field: product_id
    constraint: required
    description: "CartItem product_id is required"

  V029_CartItem_product_id_format:
    entity: CartItem
    field: product_id
    constraint: uuid_format
    description: "CartItem product_id must be UUID"

  V030_CartItem_product_fk:
    entity: CartItem
    field: product_id
    constraint: foreign_key=Product.id
    description: "CartItem product_id must reference existing Product"

  V031_CartItem_quantity:
    entity: CartItem
    field: quantity
    constraint: required
    description: "CartItem quantity is required"

  V032_CartItem_quantity_positive:
    entity: CartItem
    field: quantity
    constraint: gt=0
    description: "CartItem quantity must be positive"

  V033_CartItem_quantity_integer:
    entity: CartItem
    field: quantity
    constraint: integer_format
    description: "CartItem quantity must be integer"

  V034_CartItem_unit_price:
    entity: CartItem
    field: unit_price
    constraint: required
    description: "CartItem unit_price is required"

  V035_CartItem_unit_price_decimal:
    entity: CartItem
    field: unit_price
    constraint: decimal_format
    description: "CartItem unit_price must be decimal"

  V036_CartItem_unit_price_non_negative:
    entity: CartItem
    field: unit_price
    constraint: ge=0
    description: "CartItem unit_price must be non-negative"

  # Order Entity (24 validations)
  V037_Order_id:
    entity: Order
    field: id
    constraint: uuid_format
    description: "Order ID must be UUID"

  V038_Order_customer_id:
    entity: Order
    field: customer_id
    constraint: required
    description: "Order customer_id is required"

  V039_Order_customer_id_format:
    entity: Order
    field: customer_id
    constraint: uuid_format
    description: "Order customer_id must be UUID"

  V040_Order_customer_fk:
    entity: Order
    field: customer_id
    constraint: foreign_key=Customer.id
    description: "Order customer_id must reference existing Customer"

  V041_Order_status:
    entity: Order
    field: status
    constraint: required
    description: "Order status is required"

  V042_Order_status_enum:
    entity: Order
    field: status
    constraint: enum=PENDING_PAYMENT,PAID,CANCELLED
    description: "Order status must be PENDING_PAYMENT, PAID, or CANCELLED"

  V043_Order_status_default:
    entity: Order
    field: status
    constraint: default=PENDING_PAYMENT
    description: "Order status defaults to PENDING_PAYMENT"

  V044_Order_payment_status:
    entity: Order
    field: payment_status
    constraint: required
    description: "Order payment_status is required"

  V045_Order_payment_status_enum:
    entity: Order
    field: payment_status
    constraint: enum=PENDING,SIMULATED_OK,FAILED
    description: "Order payment_status must be PENDING, SIMULATED_OK, or FAILED"

  V046_Order_payment_status_default:
    entity: Order
    field: payment_status
    constraint: default=PENDING
    description: "Order payment_status defaults to PENDING"

  V047_Order_total_amount:
    entity: Order
    field: total_amount
    constraint: required
    description: "Order total_amount is required"

  V048_Order_total_amount_decimal:
    entity: Order
    field: total_amount
    constraint: decimal_format
    description: "Order total_amount must be decimal"

  V049_Order_total_amount_non_negative:
    entity: Order
    field: total_amount
    constraint: ge=0
    description: "Order total_amount must be non-negative"

  V050_Order_total_amount_calculated:
    entity: Order
    field: total_amount
    constraint: calculated
    description: "Order total_amount is calculated from items"

  V051_Order_created_timestamp:
    entity: Order
    field: created_at
    constraint: readonly
    description: "Order created_at is read-only"

  # OrderItem Entity (18 validations)
  V052_OrderItem_product_id:
    entity: OrderItem
    field: product_id
    constraint: required
    description: "OrderItem product_id is required"

  V053_OrderItem_product_id_format:
    entity: OrderItem
    field: product_id
    constraint: uuid_format
    description: "OrderItem product_id must be UUID"

  V054_OrderItem_product_fk:
    entity: OrderItem
    field: product_id
    constraint: foreign_key=Product.id
    description: "OrderItem product_id must reference existing Product"

  V055_OrderItem_quantity:
    entity: OrderItem
    field: quantity
    constraint: required
    description: "OrderItem quantity is required"

  V056_OrderItem_quantity_positive:
    entity: OrderItem
    field: quantity
    constraint: gt=0
    description: "OrderItem quantity must be positive"

  V057_OrderItem_quantity_integer:
    entity: OrderItem
    field: quantity
    constraint: integer_format
    description: "OrderItem quantity must be integer"

  V058_OrderItem_unit_price:
    entity: OrderItem
    field: unit_price
    constraint: required
    description: "OrderItem unit_price is required"

  V059_OrderItem_unit_price_decimal:
    entity: OrderItem
    field: unit_price
    constraint: decimal_format
    description: "OrderItem unit_price must be decimal"

  V060_OrderItem_unit_price_non_negative:
    entity: OrderItem
    field: unit_price
    constraint: ge=0
    description: "OrderItem unit_price must be non-negative"

  # Business Logic Validations (20 validations)
  V061_Stock_Constraint:
    entity: Product
    field: stock
    constraint: stock_constraint
    description: "Product stock cannot go negative on checkout"

  V062_Cart_Status_Transition:
    entity: Cart
    field: status
    constraint: status_transition=OPEN->CHECKED_OUT
    description: "Cart can only transition from OPEN to CHECKED_OUT"

  V063_Order_Status_Transition:
    entity: Order
    field: status
    constraint: status_transition=PENDING_PAYMENT->PAID
    description: "Order can transition from PENDING_PAYMENT to PAID"

  V064_Order_Status_Transition_Cancel:
    entity: Order
    field: status
    constraint: status_transition=PENDING_PAYMENT->CANCELLED
    description: "Order can transition from PENDING_PAYMENT to CANCELLED"

  V065_Payment_Status_Sync:
    entity: Order
    field: payment_status
    constraint: payment_status_sync
    description: "Payment status must sync with order status transitions"

  V066_Email_Uniqueness:
    entity: Customer
    field: email
    constraint: unique_constraint
    description: "No two customers can have the same email"

  V067_Duplicate_Cart_Prevention:
    entity: Cart
    field: status
    constraint: business_rule
    description: "Cannot create duplicate OPEN carts for same customer"

  V068_Cart_Item_Uniqueness:
    entity: CartItem
    field: product_id
    constraint: unique_per_cart
    description: "Cannot add duplicate products to same cart (increment quantity instead)"

  V069_Stock_Deduction:
    entity: Product
    field: stock
    constraint: deduction_rule
    description: "Stock is deducted on order checkout and restored on cancellation"

  V070_Price_Snapshot:
    entity: CartItem
    field: unit_price
    constraint: snapshot_rule
    description: "CartItem unit_price captures product price at time of adding"

  V071_Order_Item_Snapshot:
    entity: OrderItem
    field: unit_price
    constraint: snapshot_rule
    description: "OrderItem unit_price captures product price at time of order creation"

  V072_Checkout_Validation:
    entity: Order
    field: id
    constraint: checkout_rule
    description: "Checkout must validate stock for all items before order creation"

  V073_Inactive_Product_Constraint:
    entity: Product
    field: is_active
    constraint: business_rule
    description: "Cannot add inactive products to cart"

  V074_Insufficient_Stock_Constraint:
    entity: CartItem
    field: quantity
    constraint: business_rule
    description: "Cannot add more items than available stock"

  V075_Order_Total_Calculation:
    entity: Order
    field: total_amount
    constraint: calculation_rule
    description: "Order total_amount = SUM(CartItem.unit_price * CartItem.quantity)"

  V076_Empty_Cart_Checkout:
    entity: Cart
    field: id
    constraint: business_rule
    description: "Cannot checkout empty cart"

  V077_Payment_Only_Pending:
    entity: Order
    field: status
    constraint: business_rule
    description: "Can only mark payment successful on PENDING_PAYMENT orders"

  V078_Cancel_Only_Pending:
    entity: Order
    field: status
    constraint: business_rule
    description: "Can only cancel PENDING_PAYMENT orders"

  V079_Pagination_Defaults:
    entity: null
    field: pagination
    constraint: default_page=1,default_page_size=20
    description: "Default pagination is page 1 with 20 items per page"

  V080_404_Not_Found:
    entity: null
    field: api_response
    constraint: "404_on_missing"
    description: "API returns 404 when resource not found"

  V081_400_Invalid_Input:
    entity: null
    field: api_response
    constraint: "400_on_invalid"
    description: "API returns 400 on invalid input (e.g., invalid email, duplicate customer)"

  V082_422_Validation_Error:
    entity: null
    field: api_response
    constraint: "422_on_validation"
    description: "API returns 422 on validation error (e.g., price <= 0, quantity <= 0)"

```

---

**Ground Truth Strategy**

**NO UPPER LIMIT** - Extract everything the LLM can find
- The list above is NOT exhaustive - add any validations the LLM discovers
- 132 validations listed here, but could be 150, 180, or more
- Pipeline should extract EVERYTHING

**MINIMUM THRESHOLD: 100 validations**
- If LLM extraction < 100 → FAIL (don't proceed with code generation)
- If LLM extraction ≥ 100 → PASS (proceed)
- This ensures minimum quality bar while allowing unlimited upside

**Rationale**:
- Previous approach limited thinking to 52-132 validations (arbitrary ceiling)
- New approach: extract all possible validations, fail if quality dips below 100
- Drives continuous improvement in LLM extraction capability

Example outcomes:
- Extract 95 validations → ❌ FAIL - below threshold
- Extract 110 validations → ✅ PASS - meets minimum
- Extract 150 validations → ✅ PASS - exceeds expectations
- Extract 200 validations → ✅ PASS - exceptional extraction
