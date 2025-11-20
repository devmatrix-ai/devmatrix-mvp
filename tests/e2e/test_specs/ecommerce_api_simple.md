# Ecommerce API - Simple Spec

## 1. Descripción General

Construir una **API backend de e-commerce básico** (solo backend, sin frontend) que permita:

- Gestionar productos
- Gestionar clientes
- Gestionar carritos de compra
- Crear órdenes a partir del carrito
- Consultar el historial de órdenes

No es necesario integrar pagos reales: se usará un estado `payment_status` simulado.

Complejidad esperada: **0.45 (Simple–Medium)**.

---

## 2. Modelo de Dominio (Conceptual)

Entidades principales:

1. **Product**
   - id (UUID)
   - name (string, obligatorio)
   - description (string, opcional)
   - price (decimal, obligatorio, > 0)
   - stock (int, obligatorio, >= 0)
   - is_active (bool, por defecto true)

2. **Customer**
   - id (UUID)
   - email (string, obligatorio, formato email, único)
   - full_name (string, obligatorio)
   - created_at (datetime, solo lectura)

3. **Cart**
   - id (UUID)
   - customer_id (UUID, referencia a Customer)
   - items: lista de CartItem
   - status: enum ["OPEN", "CHECKED_OUT"] (default "OPEN")

4. **CartItem**
   - product_id (UUID, referencia a Product)
   - quantity (int, obligatorio, > 0)
   - unit_price (decimal, copia del precio del producto al momento de agregar)

5. **Order**
   - id (UUID)
   - customer_id (UUID)
   - items: lista de OrderItem
   - total_amount (decimal, calculado)
   - status: enum ["PENDING_PAYMENT", "PAID", "CANCELLED"]
   - payment_status: enum ["PENDING", "SIMULATED_OK", "FAILED"]
   - created_at (datetime)

6. **OrderItem**
   - product_id (UUID)
   - quantity (int, > 0)
   - unit_price (decimal, copia del precio del producto al momento de la orden)

---

## 3. Requerimientos Funcionales

### Productos

**F1. Crear producto**  
La API debe permitir crear productos con `name`, `description`, `price`, `stock` e `is_active`.

**F2. Listar productos activos**  
Endpoint para listar productos con `is_active = true`, con paginación simple (`page`, `page_size`).

**F3. Obtener detalle de producto**  
Endpoint para obtener un producto por `id`. Si no existe, devolver 404.

**F4. Actualizar producto**  
Permitir actualizar `name`, `description`, `price`, `stock` e `is_active`.

**F5. Desactivar producto**  
Permitir desactivar un producto (`is_active = false`) sin borrarlo físicamente.

---

### Clientes

**F6. Registrar cliente**  
Endpoint para crear un `Customer` con `email` y `full_name`.  
Si el `email` ya existe, devolver 400.

**F7. Obtener cliente por id**  
Endpoint para obtener un cliente por `id`. Si no existe, 404.

---

### Carrito

**F8. Crear carrito para cliente**  
Crear un carrito `OPEN` para un `customer_id`.  
Si ya existe un carrito `OPEN` para ese cliente, reutilizarlo (no crear uno nuevo).

**F9. Agregar item al carrito**  
Permitir agregar un producto al carrito:
- Si el producto está inactivo o sin stock, devolver 400.
- Si el item ya existe en el carrito, sumar la cantidad.
- Guardar `unit_price` tomando el precio actual del producto.

**F10. Ver carrito actual**  
Endpoint para obtener el carrito `OPEN` de un cliente, con items y subtotales.

**F11. Actualizar cantidad de un item**  
Permitir cambiar `quantity`:
- Si `quantity` <= 0, eliminar el item del carrito.
- Si la nueva cantidad es mayor que el stock disponible, devolver 400.

**F12. Vaciar carrito**  
Endpoint para eliminar todos los items de un carrito `OPEN`.

---

### Órdenes

**F13. Checkout del carrito**  
Crear una `Order` a partir del carrito `OPEN`:

- Calcular `total_amount` como suma de (`unit_price * quantity`).
- Verificar stock de todos los productos.
- Descontar stock al confirmar la orden.
- Cambiar estado del carrito a `CHECKED_OUT`.
- Crear la orden con `status = "PENDING_PAYMENT"` y `payment_status = "PENDING"`.

**F14. Simular pago exitoso**  
Endpoint para marcar una orden como pagada:
- Cambiar `status` a `"PAID"` y `payment_status` a `"SIMULATED_OK"`.
- Solo permitido si la orden está en `"PENDING_PAYMENT"`.

**F15. Cancelar orden**  
Endpoint para cancelar una orden:
- Solo permitido si `status` es `"PENDING_PAYMENT"`.
- Devolver stock de los productos (sumar cantidades).

**F16. Listar órdenes de un cliente**  
Endpoint para listar todas las órdenes de un cliente, con filtro opcional por `status`.

**F17. Obtener detalle de orden**  
Endpoint para obtener una orden por `id`. Si no existe, 404.

---

## 4. Requerimientos No Funcionales

**NF1. Framework**  
Usar un framework web moderno tipo **FastAPI** o similar (según plantillas del sistema).

**NF2. Persistencia**  
Puede usarse almacenamiento en memoria (para este demo), pero la API debe estar diseñada como si fuera persistente.

**NF3. Validación**  
Usar modelos de datos tipados (p. ej. Pydantic) y devolver errores 422/400 con mensajes claros.

**NF4. Estructura de código**  
Separar:
- modelos / esquemas
- rutas / controladores
- lógica de negocio donde aplique

**NF5. Tests**  
Incluir un conjunto mínimo de tests automatizados:

- Crear y listar productos.
- Registrar cliente.
- Flujo completo: crear carrito → agregar producto → checkout → marcar pago OK.
- Intentar checkout sin stock suficiente (debe fallar).

**NF6. Documentación**  
Exponer documentación automática del API (OpenAPI/Swagger).

**NF7. Healthcheck**  
Incluir endpoint de healthcheck simple que devuelva:
```json
{ "message": "Ecommerce API", "status": "running" }
```

---

## Classification Ground Truth

**Purpose**: Ground truth for classification validation (Task Group 1.2)  
**Format**: requirement_id → {domain: <domain>, risk: <risk>}

### Products (F1-F5)

**F1_create_product**:
  - domain: crud
  - risk: low
  - rationale: Simple CRUD create operation

**F2_list_products**:
  - domain: crud
  - risk: low
  - rationale: Simple CRUD list/read operation with pagination

**F3_get_product**:
  - domain: crud
  - risk: low
  - rationale: Simple CRUD read operation by ID

**F4_update_product**:
  - domain: crud
  - risk: low
  - rationale: Simple CRUD update operation

**F5_deactivate_product**:
  - domain: crud
  - risk: low
  - rationale: Simple CRUD soft-delete operation

### Customers (F6-F7)

**F6_register_customer**:
  - domain: crud
  - risk: low
  - rationale: Simple CRUD create operation with email uniqueness validation

**F7_get_customer**:
  - domain: crud
  - risk: low
  - rationale: Simple CRUD read operation by ID

### Cart (F8-F12)

**F8_create_cart**:
  - domain: workflow
  - risk: medium
  - rationale: Workflow operation with state management (reuse existing OPEN cart)

**F9_add_item_to_cart**:
  - domain: workflow
  - risk: medium
  - rationale: Workflow operation with business logic (stock check, price snapshot, quantity aggregation)

**F10_view_cart**:
  - domain: workflow
  - risk: low
  - rationale: Simple read operation within workflow context

**F11_update_cart_item**:
  - domain: workflow
  - risk: medium
  - rationale: Workflow operation with business logic (stock validation, item removal)

**F12_clear_cart**:
  - domain: workflow
  - risk: low
  - rationale: Simple workflow operation (delete all items)

### Orders (F13-F17)

**F13_checkout_cart**:
  - domain: payment
  - risk: high
  - rationale: Payment workflow with critical business logic (stock deduction, cart state transition, order creation)

**F14_simulate_payment**:
  - domain: payment
  - risk: high
  - rationale: Payment state transition with financial implications

**F15_cancel_order**:
  - domain: payment
  - risk: high
  - rationale: Payment reversal with stock restoration logic

**F16_list_customer_orders**:
  - domain: workflow
  - risk: low
  - rationale: Simple list operation with filtering

**F17_get_order**:
  - domain: workflow
  - risk: low
  - rationale: Simple read operation for order details

---

## Expected Dependency Graph (Ground Truth)

**Purpose**: Ground truth for DAG construction validation (Task Group 6.2)
**Format**: Explicit nodes and edges defining the expected dependency graph

### Nodes (10 expected)

```yaml
nodes: 10
node_list:
  - create_product      # F1
  - list_products       # F2
  - create_customer     # F6
  - create_cart         # F8
  - add_to_cart         # F9
  - checkout_cart       # F13
  - simulate_payment    # F14
  - cancel_order        # F15
  - list_orders         # F16
  - get_order           # F17
```

**Rationale**: Core API operations representing the main workflow paths. Excludes simple CRUD operations that don't have dependencies (F3_get_product, F4_update_product, F5_deactivate_product, F7_get_customer, F10_view_cart, F11_update_cart_item, F12_clear_cart).

### Edges (12 explicit dependencies)

```yaml
edges: 12
edge_list:
  # Customer → Cart dependency
  - from: create_customer
    to: create_cart
    reason: "Cart requires customer to exist"

  # Product → Cart workflow
  - from: create_product
    to: add_to_cart
    reason: "Cannot add non-existent product to cart"

  - from: create_cart
    to: add_to_cart
    reason: "Cart must exist before adding items"

  # Cart → Checkout workflow
  - from: add_to_cart
    to: checkout_cart
    reason: "Cart must have items before checkout"

  # Checkout → Payment workflow
  - from: checkout_cart
    to: simulate_payment
    reason: "Order must be created before payment"

  - from: checkout_cart
    to: cancel_order
    reason: "Order must exist before cancellation"

  # Customer → Orders queries
  - from: create_customer
    to: list_orders
    reason: "Customer must exist to list their orders"

  - from: checkout_cart
    to: list_orders
    reason: "Orders must be created to appear in list"

  - from: checkout_cart
    to: get_order
    reason: "Order must exist to be retrieved"

  # Product → Product queries
  - from: create_product
    to: list_products
    reason: "Products must exist to be listed"

  # Additional customer dependencies
  - from: create_customer
    to: get_order
    reason: "Customer must exist to retrieve their orders"

  # Additional cart dependencies
  - from: create_cart
    to: checkout_cart
    reason: "Cart must exist to be checked out"
```

**Dependency Patterns Explained**:

1. **CRUD Dependencies**: Create operations must precede read/list operations for the same entity
   - `create_product → list_products` (products must exist to be listed)
   - `create_customer → list_orders` (customer must exist to list their orders)

2. **Workflow Dependencies**: Multi-step business processes have strict ordering
   - `create_customer → create_cart` (cart needs customer)
   - `create_cart → add_to_cart` (items need cart)
   - `add_to_cart → checkout_cart` (checkout needs items)
   - `checkout_cart → simulate_payment` (payment needs order)

3. **Entity Reference Dependencies**: Operations on related entities
   - `create_product → add_to_cart` (product must exist to add to cart)
   - `checkout_cart → cancel_order` (order must exist to cancel)

**Expected DAG Accuracy Target**: 80%+ (Baseline: 57.6%)

**Common Missing Edges** (to watch for in DAG construction):
- Missing `create_cart → checkout_cart` (cart existence check)
- Missing `create_customer → get_order` (customer ownership)
- Incorrect `create_product → checkout_cart` (too loose, should be via `add_to_cart`)

**Wave Structure Expectation**:
```
Wave 1: create_product, create_customer
Wave 2: list_products, create_cart
Wave 3: add_to_cart
Wave 4: checkout_cart
Wave 5: simulate_payment, cancel_order, list_orders, get_order
```
