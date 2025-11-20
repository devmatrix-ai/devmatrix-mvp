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
