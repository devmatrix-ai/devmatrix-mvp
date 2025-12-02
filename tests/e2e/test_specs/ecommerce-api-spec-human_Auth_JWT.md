# E-commerce API - Especificación en Lenguaje Natural

> Una guía amigable de qué necesita hacer el sistema de e-commerce

## ¿Qué vamos a construir?

Un backend API para un e-commerce básico que permite:
- Administrar un catálogo de productos
- Registrar clientes y autenticarlos con JWT (login/refresh/logout)
- Crear carritos de compra
- Hacer órdenes
- Ver historial de compras

**Nota**: Solo backend, sin interfaz web. Usamos simulación para pagos (no hay integración real con gateway de pago).

**Complejidad esperada**: Medio con auth JWT (0.55)

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
Una persona que se registra para comprar y se autentica en el sistema.

Cada cliente tiene:
- **ID único** (UUID)
- **Email** (ej: ariel@example.com) - obligatorio, formato válido, ÚNICO (no duplicados)
- **Nombre completo** (ej: "Ariel Martínez") - obligatorio
- **Password** (solo input; se almacena hasheado, nunca se devuelve) - obligatorio, mínimo 8 caracteres
- **Rol** (CUSTOMER por defecto, ADMIN para gestión de catálogo)
- **Fecha de registro** (automática, solo lectura)

Acciones permitidas:
- Registrar nuevo cliente (signup)
- Ver datos de un cliente específico (solo el dueño autenticado o un ADMIN)
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

Regla importante: Cada cliente solo puede tener UN carrito OPEN. Si ya existe uno, se reutiliza en lugar de crear uno nuevo. El carrito siempre pertenece al cliente autenticado (customer_id tomado del JWT).

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

Regla importante: El monto total se calcula automáticamente: SUM(unit_price × quantity) para cada item. La orden pertenece al cliente autenticado (customer_id tomado del JWT).

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

## Autenticación y Seguridad con JWT

- **Tokens**: JWT HS256. `access_token` expira en ~15 minutos; `refresh_token` expira en ~7 días y se rota en cada uso.
- **Claims mínimos**: `sub` = customer_id, `email`, `role`, `exp`, `token_type` (access o refresh).
- **Password**: Hasheada (bcrypt) y nunca se devuelve en respuestas.
- **Autorización**:
  - Endpoints públicos: `/health`, `/auth/login`, `/auth/refresh`, `/customers` (signup), `GET /products` y `GET /products/{id}`.
  - Todo lo demás requiere `Authorization: Bearer <access_token>`.
  - Rol ADMIN es obligatorio para crear/actualizar/desactivar productos.
  - Cada cliente solo puede ver/modificar sus propios carritos y órdenes (salvo ADMIN que puede ver cualquier orden).
- **Logout**: invalida el refresh token usado; no debe poder reutilizarse.
- **Errores estándar**: sin token o token inválido/expirado → 401; token válido pero sin permiso/rol → 403.

---

## Los 21 Flujos Principales (Casos de Uso)

### Autenticación

**F1: Registrar Cliente (Signup con password)**
Registro público. POST con email, full_name y password (mínimo 8). Crea el cliente con rol CUSTOMER. Devuelve 201 con datos del cliente (sin password). Si el email ya existe → Error 400.

**F2: Login con JWT**
POST /auth/login con email y password. Valida credenciales (password vs hash). Devuelve `access_token` (Bearer, ~15 min), `refresh_token` (~7 días), `token_type` y `expires_in`. Si credenciales incorrectas → 401.

**F3: Refresh de Token**
POST /auth/refresh con `refresh_token`. Si es válido y no expiró/revocado → devuelve nuevo par de tokens (rota refresh). Si está expirado, firmado con clave incorrecta o ya usado → 401.

**F4: Ver Perfil Autenticado**
GET /auth/me (o /customers/me). Requiere `Authorization: Bearer <access_token>`. Devuelve id, email, full_name, role y fechas.

**F5: Logout (Revocar Refresh)**
POST /auth/logout con `refresh_token` y access token válido. Marca el refresh como revocado para que no se pueda volver a usar. Respuesta 204/200. Usar luego ese refresh → 401.

### Productos

**F6: Crear Producto (solo ADMIN)**
ADMIN crea un nuevo producto con nombre, descripción, precio, stock y estado. Requiere access token con rol ADMIN; de lo contrario → 403/401.

**F7: Listar Productos Activos**
Usuarios pueden obtener la lista de productos activos (is_active = true), con paginación. Es público (no requiere token).

**F8: Ver Detalles de Producto**
Obtener toda la información de un producto específico por ID. Si no existe → Error 404.

**F9: Actualizar Producto (solo ADMIN)**
Cambiar nombre, descripción, precio, stock o estado de un producto existente. Requiere rol ADMIN.

**F10: Desactivar Producto (solo ADMIN)**
Marcar un producto como inactivo (is_active = false). No se elimina, solo se oculta. Requiere rol ADMIN.

### Clientes

**F11: Ver Detalles del Cliente**
Obtener información completa de un cliente por ID. Requiere access token. Solo el dueño o un ADMIN pueden verlo; de lo contrario → 403. Si no existe → Error 404.

### Carrito

**F12: Crear Carrito**
El sistema crea un carrito OPEN para el cliente autenticado. Si ya existe uno OPEN, lo reutiliza. Requiere token válido; si no → 401.

**F13: Agregar Ítem al Carrito**
Agregar un producto específico con cantidad. Validaciones:
- Si el producto está inactivo → Error 400
- Si no hay stock suficiente → Error 400
- Si el producto ya está en el carrito → aumentar cantidad en lugar de duplicar
- Guardar el precio actual como unit_price  
Requiere token y solo puede operar el carrito del propio cliente; si intenta otro → 403.

**F14: Ver Carrito Actual**
Obtener el carrito OPEN del cliente con todos los items y subtotales. Solo el dueño o un ADMIN (lectura) pueden verlo.

**F15: Actualizar Cantidad de Ítem**
Cambiar la cantidad de un producto en el carrito.
- Si cantidad ≤ 0 → eliminar el item
- Si cantidad > stock disponible → Error 400  
Requiere token y pertenencia del carrito.

**F16: Vaciar Carrito**
Eliminar todos los items del carrito OPEN.

### Órdenes

**F17: Checkout (Crear Orden)**
El cliente finaliza su compra. El sistema:
1. Valida que el carrito no esté vacío
2. Valida que hay stock para TODOS los items
3. Resta el stock de los productos
4. Crea la orden con status PENDING_PAYMENT
5. Marca el carrito como CHECKED_OUT
6. Calcula monto total automáticamente  
Solo puede hacer checkout el dueño del carrito (o un ADMIN en representación); de lo contrario → 403.

**F18: Pagar Orden (Simulado)**
Marcar una orden como pagada.
- Status actual debe ser PENDING_PAYMENT
- Cambiar a PAID + payment_status a SIMULATED_OK
- Solo permitido si la orden está esperando pago  
Solo el dueño de la orden (o ADMIN) puede pagar; si no → 403.

**F19: Cancelar Orden**
Cancelar una orden y devolver el stock.
- Status actual debe ser PENDING_PAYMENT
- Cambiar a CANCELLED
- Sumar de vuelta la cantidad a los productos  
Solo el dueño (o ADMIN) puede cancelarla; si no → 403.

**F20: Listar Órdenes del Cliente**
Ver todas las órdenes de un cliente autenticado, opcionalmente filtradas por status. Un ADMIN puede listar las órdenes de cualquier cliente (pasando customer_id). Usuarios comunes solo pueden ver las suyas.

**F21: Ver Detalles de Orden**
Obtener toda la información de una orden por ID. Solo dueño o ADMIN; si no → 403. Si no existe → Error 404.

---

## Reglas de Validación (Lo Importante)

### En los Datos

- **Precio de producto**: Debe ser > 0 (no se puede vender gratis)
- **Stock de producto**: Debe ser ≥ 0 (no negativo)
- **Cantidad en carrito**: Debe ser > 0 (mínimo 1)
- **Cantidad en orden**: Debe ser > 0
- **Email de cliente**: Formato válido de email, ÚNICO (sin duplicados)
- **Password**: Mínimo 8 caracteres, se almacena hasheada (bcrypt), nunca en texto plano
- **Roles**: Solo valores CUSTOMER o ADMIN
- **Campos requeridos**: name (producto), email (cliente), full_name (cliente), etc.

### En los Procesos

- **JWT requerido**: Todas las rutas protegidas deben validar access token (firma, expiración, token_type = access)
- **Propiedad de recursos**: Carritos y órdenes solo pueden ser accedidos por su dueño; ADMIN puede acceder a cualquier recurso
- **Rol ADMIN**: Obligatorio para crear/actualizar/desactivar productos
- **Refresh tokens**: Deben validarse y rotarse; un refresh revocado o expirado no puede reutilizarse
- **Producto inactivo**: No se puede agregar a un carrito
- **Stock insuficiente**: No se puede agregar más unidades de las disponibles
- **Un carrito OPEN por cliente**: Si existe uno, se reutiliza
- **Checkout valida todo**: Antes de crear la orden, valida stock para todos los items
- **Stock se descuenta en checkout**: Cuando se crea la orden, el stock baja
- **Stock se devuelve en cancelación**: Si cancelas la orden, el stock vuelve
- **Unit price es snapshot**: Captura el precio en ese momento, cambios futuros no afectan

### En las Respuestas

- **401 Unauthorized**: Falta token, token inválido/expirado, refresh token reusado o inválido
- **403 Forbidden**: Token válido pero sin permisos (no es dueño o no es ADMIN)
- **404 Not Found**: Cuando algo no existe (producto, cliente, orden)
- **400 Bad Request**: Cuando hay un error de validación (precio ≤ 0, email duplicado, etc.)
- **422 Unprocessable Entity**: Cuando hay un error de lógica de negocio (stock insuficiente)

---

## Ejemplo Completo: Un Cliente Compra Algo

1. **Admin se loguea**: POST /auth/login → obtiene tokens con rol ADMIN.
2. **Admin crea productos**: POST /products (Bearer token ADMIN) → Crea "iPhone 15" y "AirPods Pro".
3. **Cliente se registra**: POST /customers → ariel@example.com, "Ariel Martínez", password seguro.
4. **Cliente hace login**: POST /auth/login → obtiene `access_token` y `refresh_token`.
5. **Cliente crea carrito**: POST /carts (Bearer access_token) → Se crea carrito OPEN asociado al cliente.
6. **Cliente ve productos**: GET /products → Ve lista de productos activos.
7. **Cliente agrega producto**: POST /carts/{id}/items (Bearer) → Agrega "iPhone 15" cantidad 1, precio capturado $999.
8. **Cliente agrega otro**: POST /carts/{id}/items (Bearer) → Agrega "AirPods Pro" cantidad 2, precio capturado $249.
9. **Cliente ve carrito**: GET /carts/{id} (Bearer) → Ve carrito con 2 items, total $1,497.
10. **Cliente compra**: POST /orders (Bearer) → Crea orden, resta stock, carrito pasa a CHECKED_OUT.
11. **Sistema simula pago**: POST /orders/{id}/pay (Bearer) → Marca como PAID.
12. **Cliente ve su orden**: GET /orders/{id} (Bearer) → Ve detalles, monto total, estado PAID.

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
- **JWT**: Usar HS256 y un secreto configurado (`JWT_SECRET`). Expiración sugerida: 15 min access, 7 días refresh. Incluir claim `role`.
- **Password hashing**: Usar bcrypt (o similar) con sal. Nunca guardar ni loguear el password en texto plano.
- **Autorización**: Middleware/dependency que valide bearer token y rol; reutilizarlo en endpoints protegidos.

---

## Resumen de Validaciones Esperadas

El sistema debe validar:

### Nivel de Campo
- Precios > 0
- Stocks ≥ 0
- Cantidades > 0
- Emails válidos
- Password mínimo 8 caracteres (solo hash)
- Roles válidos
- UUIDs válidos
- IDs de referencia que existan

### Nivel de Negocio
- Token de acceso válido y no expirado en rutas protegidas
- Refresh token válido y no reutilizado para emitir nuevos tokens
- Solo ADMIN modifica productos
- Un cliente solo accede a sus carritos/órdenes (salvo ADMIN)
- Sin productos inactivos en carritos
- Sin stock insuficiente
- Transiciones de estado válidas (OPEN → CHECKED_OUT)
- Un carrito OPEN por cliente
- Pagos solo en órdenes PENDING

### Nivel de API
- 401 si falta token, está vencido o es inválido
- 403 si el token es válido pero no tiene permisos (no dueño / no ADMIN)
- 404 si no existe
- 400 si datos inválidos
- 422 si regla de negocio viola
- Paginación por defecto (página 1, 20 items)

---

## ¿Qué Debería Pasar en el Sistema?

✅ **Debería Funcionar**:
- Signup y login devolviendo access/refresh
- Refresh que rota tokens y sigue funcionando hasta expirar
- Rutas protegidas responden 200/201 con token válido
- Admin puede crear/actualizar/desactivar productos
- Crear múltiples productos
- Registrar clientes
- Agregar/quitar items del carrito
- Hacer checkout exitoso
- Ver historial de órdenes
- Pagos simulados
- Cancelaciones con devolución de stock

❌ **Debería Fallar Correctamente**:
- Login con password incorrecto → 401
- Llamar a rutas protegidas sin token o con token expirado → 401
- Cliente CUSTOMER creando producto → 403
- Usar refresh token ya revocado → 401
- Crear producto con precio 0 → Error 400
- Registrar con email duplicado → Error 400
- Ver producto que no existe → Error 404
- Agregar producto inactivo al carrito → Error 400
- Checkout sin stock → Error 422
- Pagar orden ya pagada → Error 400

---

**Este es el spec. Todo lo que está aquí DEBE estar validado en el código generado.**

Si el generador de código implementa correctamente todas estas validaciones, entonces tenemos un sistema confiable que DevMatrix puede usar.
