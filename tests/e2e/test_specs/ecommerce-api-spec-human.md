# E-commerce API - Especificación en Lenguaje Natural

> Una guía amigable de qué necesita hacer el sistema de e-commerce

## ¿Qué vamos a construir?

Un backend API para un e-commerce básico que permite:
- Administrar un catálogo de productos
- Registrar clientes
- Crear carritos de compra
- Hacer órdenes
- Ver historial de compras

**Nota**: Solo backend, sin interfaz web. Usamos simulación para pagos (no hay integración real con gateway de pago).

**Complejidad esperada**: Medio-simple (0.45)

---

## Las 6 Entidades Principales

### 1. Producto (Product)
Un artículo en el catálogo que los clientes pueden comprar.

Cada producto tiene:
- **ID único** (código UUID para identificarlo)
- **Nombre** (ej: "iPhone 15 Pro") - obligatorio
- **Descripción** (ej: "Teléfono de última generación") - opcional
- **Precio** (ej: $999.99) - obligatorio, debe ser mayor a 0
- **Stock** (ej: 50 unidades) - obligatorio, no puede ser negativo
- **Estado activo** (sí/no) - por defecto SÍ

Acciones permitidas:
- Crear nuevo producto
- Ver lista de productos activos (con paginación)
- Ver detalles de un producto específico
- Actualizar información del producto
- Desactivar un producto (sin eliminarlo físicamente)

### 2. Cliente (Customer)
Una persona que se registra para comprar.

Cada cliente tiene:
- **ID único** (UUID)
- **Email** (ej: ariel@example.com) - obligatorio, formato válido, ÚNICO (no duplicados)
- **Nombre completo** (ej: "Ariel Martínez") - obligatorio
- **Fecha de registro** (automática, solo lectura)

Acciones permitidas:
- Registrar nuevo cliente
- Ver datos de un cliente específico
- Si el email ya existe → Error 400 (rechazado)

### 3. Carrito (Cart)
El carrito de compras temporal de un cliente.

Cada carrito tiene:
- **ID único** (UUID)
- **Cliente propietario** (referencia al customer)
- **Estado** (OPEN o CHECKED_OUT)
  - OPEN = carrito activo, el cliente puede agregar/quitar items
  - CHECKED_OUT = se convirtió en orden, no se puede modificar
- **Ítems** dentro del carrito (lista de productos con cantidades)

Regla importante: Cada cliente solo puede tener UN carrito OPEN. Si ya existe uno, se reutiliza en lugar de crear uno nuevo.

Acciones permitidas:
- Crear carrito para un cliente
- Ver el carrito actual de un cliente
- Agregar productos al carrito
- Aumentar/disminuir cantidad
- Eliminar items
- Vaciar todo el carrito

### 4. Ítem del Carrito (CartItem)
Una entrada en el carrito: "este producto, en esta cantidad".

Cada item tiene:
- **Producto** (referencia a qué se está comprando)
- **Cantidad** (ej: 2) - debe ser positivo (> 0)
- **Precio unitario** (captura el precio del producto EN ESE MOMENTO)

Regla importante: Si el cliente intenta agregar un producto que ya está en el carrito, en lugar de crear un nuevo item, aumentamos la cantidad del existente.

### 5. Orden (Order)
Una compra confirmada. Se crea desde un carrito cuando el cliente hace checkout.

Cada orden tiene:
- **ID único** (UUID)
- **Cliente propietario**
- **Estado de la orden** (PENDING_PAYMENT, PAID, CANCELLED)
  - PENDING_PAYMENT = se creó, esperando pago
  - PAID = pago confirmado
  - CANCELLED = cliente canceló la orden
- **Estado del pago** (PENDING, SIMULATED_OK, FAILED)
  - PENDING = en espera
  - SIMULATED_OK = "pagado" (simulado)
  - FAILED = simulación de fallo
- **Monto total** (suma de todos los items × cantidad)
- **Ítems** en la orden (copia del carrito en ese momento)
- **Fecha de creación** (automática, solo lectura)

Regla importante: El monto total se calcula automáticamente: SUM(unit_price × quantity) para cada item.

Acciones permitidas:
- Crear orden desde un carrito (checkout)
- Marcar orden como pagada (solo si está en PENDING_PAYMENT)
- Cancelar orden (solo si está en PENDING_PAYMENT)
- Ver detalles de una orden
- Listar todas las órdenes de un cliente

### 6. Ítem de la Orden (OrderItem)
Una línea en la orden: "este producto, en esta cantidad, a este precio".

Es similar a CartItem pero es parte de la orden (inmutable). Captura:
- **Producto** (qué se compró)
- **Cantidad** (cuánto)
- **Precio unitario** (el precio que tenía EN EL MOMENTO de la compra)

---

## Los 17 Flujos Principales (Casos de Uso)

### Productos

**F1: Crear Producto**
El sistema permite crear un nuevo producto con nombre, descripción, precio, stock e estado.

**F2: Listar Productos Activos**
Los usuarios pueden obtener una lista de todos los productos disponibles (is_active = true), con paginación.

**F3: Ver Detalles de Producto**
Obtener toda la información de un producto específico por ID. Si no existe → Error 404.

**F4: Actualizar Producto**
Cambiar nombre, descripción, precio, stock o estado de un producto existente.

**F5: Desactivar Producto**
Marcar un producto como inactivo (is_active = false). No se elimina, solo se oculta.

### Clientes

**F6: Registrar Cliente**
Crear nueva cuenta con email y nombre. Si el email ya existe → Error 400.

**F7: Ver Detalles del Cliente**
Obtener información completa de un cliente por ID. Si no existe → Error 404.

### Carrito

**F8: Crear Carrito**
El sistema crea un carrito OPEN para un cliente. Si ya existe uno OPEN, lo reutiliza.

**F9: Agregar Ítem al Carrito**
Agregar un producto específico con cantidad. Validaciones:
- Si el producto está inactivo → Error 400
- Si no hay stock suficiente → Error 400
- Si el producto ya está en el carrito → aumentar cantidad en lugar de duplicar
- Guardar el precio actual como unit_price

**F10: Ver Carrito Actual**
Obtener el carrito OPEN del cliente con todos los items y subtotales.

**F11: Actualizar Cantidad de Ítem**
Cambiar la cantidad de un producto en el carrito.
- Si cantidad ≤ 0 → eliminar el item
- Si cantidad > stock disponible → Error 400

**F12: Vaciar Carrito**
Eliminar todos los items del carrito OPEN.

### Órdenes

**F13: Checkout (Crear Orden)**
El cliente finaliza su compra. El sistema:
1. Valida que el carrito no esté vacío
2. Valida que hay stock para TODOS los items
3. Resta el stock de los productos
4. Crea la orden con status PENDING_PAYMENT
5. Marca el carrito como CHECKED_OUT
6. Calcula monto total automáticamente

**F14: Pagar Orden (Simulado)**
Marcar una orden como pagada.
- Status actual debe ser PENDING_PAYMENT
- Cambiar a PAID + payment_status a SIMULATED_OK
- Solo permitido si la orden está esperando pago

**F15: Cancelar Orden**
Cancelar una orden y devolver el stock.
- Status actual debe ser PENDING_PAYMENT
- Cambiar a CANCELLED
- Sumar de vuelta la cantidad a los productos

**F16: Listar Órdenes del Cliente**
Ver todas las órdenes de un cliente, opcionalmente filtradas por status.

**F17: Ver Detalles de Orden**
Obtener toda la información de una orden por ID. Si no existe → Error 404.

---

## Reglas de Validación (Lo Importante)

### En los Datos

- **Precio de producto**: Debe ser > 0 (no se puede vender gratis)
- **Stock de producto**: Debe ser ≥ 0 (no negativo)
- **Cantidad en carrito**: Debe ser > 0 (mínimo 1)
- **Cantidad en orden**: Debe ser > 0
- **Email de cliente**: Formato válido de email, ÚNICO (sin duplicados)
- **Campos requeridos**: name (producto), email (cliente), full_name (cliente), etc.

### En los Procesos

- **Producto inactivo**: No se puede agregar a un carrito
- **Stock insuficiente**: No se puede agregar más unidades de las disponibles
- **Un carrito OPEN por cliente**: Si existe uno, se reutiliza
- **Checkout valida todo**: Antes de crear la orden, valida stock para todos los items
- **Stock se descuenta en checkout**: Cuando se crea la orden, el stock baja
- **Stock se devuelve en cancelación**: Si cancelas la orden, el stock vuelve
- **Unit price es snapshot**: Captura el precio en ese momento, cambios futuros no afectan

### En las Respuestas

- **404 Not Found**: Cuando algo no existe (producto, cliente, orden)
- **400 Bad Request**: Cuando hay un error de validación (precio ≤ 0, email duplicado, etc.)
- **422 Unprocessable Entity**: Cuando hay un error de lógica de negocio (stock insuficiente)

---

## Ejemplo Completo: Un Cliente Compra Algo

1. **Cliente se registra**: POST /customers → ariel@example.com, "Ariel Martínez"
2. **Cliente crea carrito**: POST /carts → Se crea carrito OPEN
3. **Cliente ve productos**: GET /products → Ve lista de productos
4. **Cliente agrega producto**: POST /carts/{id}/items → Agrega "iPhone 15" cantidad 1, precio capturado $999
5. **Cliente agrega otro**: POST /carts/{id}/items → Agrega "AirPods Pro" cantidad 2, precio capturado $249
6. **Cliente ve carrito**: GET /carts/{id} → Ve carrito con 2 items, total $1,497
7. **Cliente compra**: POST /orders → Crea orden, resta stock, carrito pasa a CHECKED_OUT
8. **Sistema simula pago**: POST /orders/{id}/pay → Marca como PAID
9. **Cliente ve su orden**: GET /orders/{id} → Ve detalles, monto total, estado PAID

Si en paso 8 el cliente cancelara:
- POST /orders/{id}/cancel → Orden pasa a CANCELLED
- Stock se devuelve al inventario

---

## Notas Técnicas Importantes

- **Framework**: FastAPI (moderno, bien documentado)
- **Almacenamiento**: En memoria está ok para demo (pero diseñado como si fuera persistente)
- **Validación**: Usar Pydantic (schemas con tipos)
- **Errores claros**: Responder con mensajes específicos (no genéricos)
- **Documentación automática**: FastAPI genera OpenAPI/Swagger automáticamente
- **Healthcheck**: /health debe responder {"message": "Ecommerce API", "status": "running"}

---

## Resumen de Validaciones Esperadas

El sistema debe validar:

### Nivel de Campo
- Precios > 0
- Stocks ≥ 0
- Cantidades > 0
- Emails válidos
- UUIDs válidos
- IDs de referencia que existan

### Nivel de Negocio
- Sin productos inactivos en carritos
- Sin stock insuficiente
- Transiciones de estado válidas (OPEN → CHECKED_OUT)
- Un carrito OPEN por cliente
- Pagos solo en órdenes PENDING

### Nivel de API
- 404 si no existe
- 400 si datos inválidos
- 422 si regla de negocio viola
- Paginación por defecto (página 1, 20 items)

---

## ¿Qué Debería Pasar en el Sistema?

✅ **Debería Funcionar**:
- Crear múltiples productos
- Registrar clientes
- Agregar/quitar items del carrito
- Hacer checkout exitoso
- Ver historial de órdenes
- Pagos simulados
- Cancelaciones con devolución de stock

❌ **Debería Fallar Correctamente**:
- Crear producto con precio 0 → Error 400
- Registrar con email duplicado → Error 400
- Ver producto que no existe → Error 404
- Agregar producto inactivo al carrito → Error 400
- Checkout sin stock → Error 422
- Pagar orden ya pagada → Error 400

---

**Este es el spec. Todo lo que está aquí DEBE estar validado en el código generado.**

Si el generador de código implementa correctamente todas estas validaciones, entonces tenemos un sistema confiable que DevMatrix puede usar.
