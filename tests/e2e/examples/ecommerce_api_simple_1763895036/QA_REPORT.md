# QA EXHAUSTIVO - ECOMMERCE API FASTAPI
**Fecha**: 23 de Noviembre 2025
**Versión**: 1.0.0
**Entorno**: Docker Compose (PostgreSQL 16, Prometheus, Grafana, Uvicorn)

---

## 📊 RESUMEN EJECUTIVO

| Categoría | Estado | Detalle |
|-----------|--------|---------|
| **Salud Crítica** | 🔴 CRÍTICA | 5 bugs bloqueantes que impiden CRUD completo |
| **Testing** | 🔴 CRÍTICA | Suite de tests no funciona (archivo template Jinja2) |
| **Seguridad** | 🟡 MEDIA | Sin autenticación/autorización implementada |
| **API Design** | 🟡 MEDIA | Inconsistencias entre rutas y servicios |
| **Database** | 🟢 OK | Migraciones aplicadas, esquema básico OK |
| **Monitoring** | 🟢 OK | Prometheus/Grafana integrados correctamente |

---

## 🔴 ISSUES CRÍTICAS (Bloquean Producción)

### ISSUE #1: AttributeError en Productos - `get_all()` no existe
**Severidad**: 🔴 CRÍTICA
**Ubicación**: `src/api/routes/product.py:46`
**Problema**:
```python
# ❌ ACTUAL (FALLA):
products = await service.get_all(skip=0, limit=100)

# ✅ EXISTE:
async def list(self, page: int = 1, size: int = 10) -> ProductList
```

**Impacto**: GET /products/ retorna 500 Internal Server Error
**Análisis**: El servicio tiene método `list()` con paginación por página/tamaño, pero la ruta llama `get_all()` que no existe.
**Error registrado en logs**:
```
AttributeError: 'ProductService' object has no attribute 'get_all'
```

---

### ISSUE #2: Validación de Schema de Clientes - Campo `full_name` Requerido
**Severidad**: 🔴 CRÍTICA
**Ubicación**: `src/models/schemas.py:146`
**Problema**:
```python
# Schema requiere:
class CustomerBase(BaseSchema):
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$", max_length=255)
    full_name: str = Field(..., min_length=1, max_length=255)  # REQUERIDO

# Pero la ruta documenta:
POST /customers/
{
    "name": "John Doe",              # ❌ EXISTE PERO NO ESPERADO
    "email": "john@example.com",
    "address": "123 Main St"         # ❌ NO EXISTE EN SCHEMA
}
```

**Impacto**: Cualquier POST a /customers/ retorna 422 Validation Error
**Error de validación**:
```json
{
  "type": "missing",
  "loc": ["body", "full_name"],
  "msg": "Field required"
}
```

---

### ISSUE #3: Ruta de Carrito Incorrecta - Crea Nuevo en Lugar de Añadir Item
**Severidad**: 🔴 CRÍTICA
**Ubicación**: `src/api/routes/cart.py:38-49`
**Problema**: La ruta `POST /carts/{id}/items` está documentada para añadir un item, pero implementa crear nuevo carrito.

**Análisis del Código**:
```python
# Docstring promete:
"""Add item to cart"""

# Pero CREA NUEVO CARRITO:
cart_response = await service.create(
    CartCreate(customer_id=customer_id, items=[...], status="OPEN")
)
```

**Impacto**: No se puede añadir items a carritos existentes
**Patrón esperado**: `POST /carts/{id}/items` → Añade item al carrito ID
**Patrón actual**: Comportamiento indefinido/incorrecto

---

### ISSUE #4: Endpoints de Órdenes No Implementados Correctamente
**Severidad**: 🔴 CRÍTICA
**Ubicación**: `src/api/routes/order.py`
**Problemas**:

#### a) `POST /orders/{id}/payment` crea orden en lugar de confirmar pago
```python
# Docstring:
"""Simulate successful payment"""

# Implementación:
order = await service.create(OrderCreate(...))  # ❌ CREA, no actualiza
```

#### b) `POST /orders/{id}/cancel` crea orden en lugar de cancelar
```python
# Docstring:
"""Cancel order"""

# Implementación:
order = await service.create(OrderCreate(...))  # ❌ CREA, no cancela
```

#### c) **FALTA** endpoint `POST /orders/` para crear órdenes
- README documenta: `POST /orders - Create a new order`
- No existe en rutas

#### d) **FALTA** endpoint `PUT /orders/{id}` para actualizar estado
- README documenta: `PUT /orders/{id} - Update order status`
- No existe en rutas

**Impacto**: Flujo completo de órdenes no funciona

---

### ISSUE #5: Métodos de Carrito No Existen en Servicio
**Severidad**: 🔴 CRÍTICA
**Ubicación**: `src/api/routes/cart.py` vs `src/services/cart_service.py`
**Problema**: Las rutas llaman métodos que no existen:

```python
# Ruta intenta:
await service.add_item(...)  # ❌ No existe

# Servicio ofrece:
async def create(...)
async def get(...)
async def list(...)
async def update(...)
async def delete(...)
# Pero no add_item, remove_item, etc.
```

**Impacto**: Gestión de items de carrito completamente rota

---

## 🟡 ISSUES IMPORTANTES (Alta Prioridad)

### ISSUE #6: Falta Métodos en Rutas de Clientes
**Severidad**: 🟡 IMPORTANTE
**Ubicación**: `src/api/routes/customer.py`
**Problema**:

```python
# Ruta #58-75: list_customer_orders() tiene problemas
async def list_customer_orders(...) -> CustomerResponse:  # TIPO RETORNO INCORRECTO
    # Debería retornar List[OrderResponse]
    # Pero retorna CustomerResponse

    # Además: ¿Cuál es el customer_id? No es parámetro en ruta.
    return customer_response  # Incorrecto
```

**Impacto**: No se puede listar órdenes de un cliente

---

### ISSUE #7: Tests No Son Ejecutables - Archivo Template Jinja2
**Severidad**: 🟡 IMPORTANTE
**Ubicación**: `tests/integration/test_api.py`
**Problema**:
```python
# El archivo es un TEMPLATE, no código Python:
{% for entity in entities %}
def test_create_{{ entity.name }}():
    ...
{% endfor %}

# Esto causa:
SyntaxError: invalid syntax (line 10)
```

**Impacto**:
- Suite de tests no puede ejecutarse
- Cobertura de tests = 0%
- No hay validación automatizada

**Solución requerida**: Generar tests desde template o reemplazar con tests reales

---

### ISSUE #8: Métodos de Servicio con Firmas Inconsistentes
**Severidad**: 🟡 IMPORTANTE
**Ubicación**: Múltiples servicios
**Problema**:

```python
# ProductService.list():
async def list(self, page: int = 1, size: int = 10) -> ProductList
# Retorna ProductList (objeto con items, total, page, size)

# Pero ruta espera:
response_model=List[ProductResponse]
# Espera lista simple

# Mismatch causa: Type validation errors
```

---

### ISSUE #9: Sin Autenticación ni Autorización
**Severidad**: 🟡 IMPORTANTE
**Ubicación**: Toda la app
**Problema**:
- ✗ Sin JWT o session tokens
- ✗ Sin verificación de identidad
- ✗ Sin isolación de datos por usuario
- ✗ Sin RBAC (admin vs cliente)

**Riesgo**:
- Un cliente puede ver órdenes de otro
- Cualquiera puede crear productos (admin function)
- No hay auditoría de cambios

---

## 🟠 ISSUES MEDIANOS (Media Prioridad)

### ISSUE #10: Parámetros de Ruta Aceptan STRING en Lugar de UUID
**Severidad**: 🟠 MEDIA
**Ubicación**: `src/api/routes/*.py` (todas las rutas)
**Ejemplo**:
```python
# ❌ ACTUAL:
async def get_product_detail(id: str, ...)

# ✅ DEBERÍA SER:
from uuid import UUID
async def get_product_detail(id: UUID, ...)
```

**Impacto**:
- FastAPI no valida UUIDs automáticamente
- Peticiones con IDs inválidas llegan al servicio
- La BD rechaza luego el insert/query

---

### ISSUE #11: Redirección 307 Automática en Rutas POST
**Severidad**: 🟠 MEDIA
**Ubicación**: Starlette/FastAPI middleware
**Problema**:
```bash
# POST /products (sin trailing slash)
HTTP/1.1 307 Temporary Redirect
location: /products/

# Obliga a clientes a seguir redirect
# Algunos clientes (curl sin -L) fallan
```

**Solución**: Permitir ambos con o sin trailing slash o ser consistente

---

### ISSUE #12: Email Regex Pattern Insuficiente
**Severidad**: 🟠 MEDIA
**Ubicación**: `src/models/schemas.py:145`
**Problema**:
```python
# Patrón actual:
pattern=r"^[^@]+@[^@]+\.[^@]+$"

# Acepta emails inválidos:
# "test@test.c" (TLD de 1 char)
# "test@@test.com" (dobla @)
# "test@.com" (sin domain)

# RFC 5322 es complejo, pero al menos:
pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
```

---

### ISSUE #13: Swagger/ReDoc Expuestos en Producción
**Severidad**: 🟠 MEDIA
**Ubicación**: `src/main.py:40-47`
**Problema**:
```python
app = FastAPI(
    docs_url="/docs",      # ✗ SIEMPRE HABILITADO
    redoc_url="/redoc"     # ✗ SIEMPRE HABILITADO
)
```

**Comentario del código**: "Reverse proxy should handle this"
**Realidad**: Defense-in-depth, debe protegerse en app
**Solución**:
```python
docs_url="/docs" if not settings.PRODUCTION else None
```

---

### ISSUE #14: Métodos de Repositorio Ineficientes
**Severidad**: 🟠 MEDIA
**Ubicación**: `src/repositories/*.py`
**Ejemplo - count() carga TODOS los registros en memoria**:
```python
async def count(self) -> int:
    result = await self.db.execute(select(ProductEntity))
    return len(result.scalars().all())  # ❌ O(n) memory usage
```

**Corrección SQL nativa**:
```python
from sqlalchemy import func

async def count(self) -> int:
    result = await self.db.execute(select(func.count(ProductEntity.id)))
    return result.scalar()  # ✓ O(1) - database handles it
```

---

### ISSUE #15: Configuración Incompleta
**Severidad**: 🟠 MEDIA
**Ubicación**: `src/core/config.py`
**Problemas**:
```python
# Falta:
SECRET_KEY = "..."  # Para JWT
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 30

# Configurado pero no usado:
redis_url = "redis://localhost:6379/0"
slowapi_key_func = ...  # Rate limiting no aplicado
```

---

## 🟢 AREAS QUE FUNCIONAN BIEN

### ✓ Infrastructure & Deployment
- ✅ Docker Compose bien configurado
- ✅ PostgreSQL 16 Alpine corriendo sano
- ✅ Healthchecks implementados
- ✅ Volúmenes persistentes para datos

### ✓ Monitoring & Observability
- ✅ Prometheus metrics endpoint disponible
- ✅ Grafana dashboard integrado
- ✅ Logging estructurado con structlog
- ✅ Request tracing con x-request-id

### ✓ Database Migrations
- ✅ Alembic inicializado
- ✅ Migraciones aplicadas en startup
- ✅ Schema básico funcional

### ✓ Security Headers
- ✅ X-Frame-Options: DENY
- ✅ X-Content-Type-Options: nosniff
- ✅ X-XSS-Protection: 1; mode=block
- ✅ Strict-Transport-Security habilitado

### ✓ Error Handling
- ✅ Excepciones globales manejadas
- ✅ Validaciones Pydantic activas
- ✅ Mensajes de error informativos

### ✓ Documentation
- ✅ Swagger UI accesible
- ✅ ReDoc disponible
- ✅ OpenAPI schema generado

---

## 📋 RESULTADOS DE TESTING EN VIVO

### Test 1: Health Checks
```
GET /health/health → 200 OK ✓
GET /health/ready → 200 OK (DB: ok) ✓
GET / → 200 OK ✓
```

### Test 2: Products API
```
POST /products/ → 500 (AttributeError: no get_all) ✗
GET /products/ → 500 (AttributeError: no get_all) ✗
GET /products/{id} → 404 (como se espera, pero nunca hay datos) ✗
```

### Test 3: Customers API
```
POST /customers/ → 422 (missing full_name) ✗
GET /customers/{id} → Depende de crear cliente (imposible) ✗
```

### Test 4: Carts API
```
POST /carts/ → No se probó (sin customer ID válido) ✗
POST /carts/{id}/items → Lógica incorrecta (crea en lugar de añadir) ✗
```

### Test 5: Orders API
```
POST /orders/ → ENDPOINT NO EXISTE ✗
GET /orders/{id} → Endpoint falta ✗
POST /orders/{id}/payment → Crea en lugar de confirmar pago ✗
```

### Test 6: Security Headers
```
Content-Security-Policy: ✓ (pero con unsafe-inline)
X-Frame-Options: ✓
X-Content-Type-Options: ✓
Strict-Transport-Security: ✓
```

### Test 7: Documentation
```
/docs (Swagger) → 200 OK ✓
/redoc (ReDoc) → 200 OK ✓
/openapi.json → 200 OK ✓
```

### Test 8: Metrics
```
/metrics/metrics → 404 Not Found ✗
Expected: /metrics (según OpenAPI y README)
```

### Test 9: Validation
```
Invalid email → 422 ✓ (rechaza correctamente)
Missing fields → 422 ✓
Non-existent resource → 404 ✓
```

---

## 🗂️ DATABASE STATE

### Migraciones
```
Alembic version: 001_initial
Status: Applied ✓
Tables created:
  - products
  - customers
  - carts
  - orders
  - cart_items
  - order_items
```

### Integridad de Datos
- ✗ Foreign keys NOT enforced at DB level
- ✗ Unique constraints missing (emails)
- ✓ Data types mostly correct

---

## 📊 COBERTURA DE CÓDIGO

| Componente | Cobertura | Estado |
|-----------|-----------|--------|
| Routes (API) | 0% | Tests template no funciona |
| Services | 0% | No hay tests de unidad |
| Repositories | 0% | No hay tests de integración |
| Models | N/A | Validación Pydantic cubre |
| **Total** | **0%** | 🔴 No testeable |

---

## 🎯 MATRIZ DE REGRESIÓN - QA EN VIVO

| Feature | Esperado | Actual | Estado |
|---------|----------|--------|--------|
| Create Product | 201 + ID | 500 Error | 🔴 |
| List Products | 200 + [items] | 500 Error | 🔴 |
| Get Product | 200 + item | 404 (sin datos) | 🔴 |
| Create Customer | 201 + ID | 422 Validation | 🔴 |
| Get Customer | 200 + customer | Imposible | 🔴 |
| Create Cart | 201 + ID | No probado | ⚠️ |
| Add Cart Item | 200 + item | Lógica mala | 🔴 |
| Create Order | 201 + ID | ENDPOINT FALTA | 🔴 |
| Get Order | 200 + order | ENDPOINT FALTA | 🔴 |
| Payment | Update status | Crea nuevo | 🔴 |

---

## 🔧 RECOMENDACIONES POR PRIORIDAD

### 🚨 BLOQUEANTES (Resolver Inmediatamente)

1. **FIX: ProductService.get_all() → list()**
   ```python
   # En src/api/routes/product.py:46
   products = await service.list(page=1, size=100)
   # Return como List[ProductResponse], no ProductList
   ```

2. **FIX: CustomerCreate Schema - Parámetro `full_name`**
   ```python
   # Actualizar ruta para aceptar full_name
   # O actualizar schema para aceptar name + address
   ```

3. **FIX: CartService - Métodos Faltantes**
   ```python
   async def add_item(self, cart_id: UUID, product_id: UUID, qty: int)
   async def remove_item(self, cart_id: UUID, item_id: UUID)
   async def checkout(self, cart_id: UUID) -> OrderResponse
   ```

4. **FIX: Order Routes - Implementación Correcta**
   ```python
   async def create_order(...) → OrderResponse  # Agregar
   async def update_order_status(...) → OrderResponse  # Agregar
   # Corregir payment y cancel
   ```

5. **FIX: Tests - Ejecutables**
   - Reemplazar test_api.py template con tests reales
   - Añadir tests de integración para CRUD completo

### 🟠 IMPORTANTES (Plan: 1-2 semanas)

6. Autenticación JWT + Autorización
7. UUID type hints en todas las rutas
8. Corrección de métodos count() en repos
9. Paginación consistente en todos los endpoints
10. Email validation pattern mejorado

### 🟢 MEJORAS (Plan: 2-3 semanas)

11. Rate limiting con slowapi
12. Mejor manejo de errores de DB
13. Métricas de negocio en Prometheus
14. Soft deletes para datos críticos

---

## 📝 CHECKLIST DE CORRECIÓN

- [ ] Crear producto y recuperarlo
- [ ] Listar productos con paginación
- [ ] Crear cliente con email válido
- [ ] Listar órdenes por cliente
- [ ] Crear carrito y añadir items
- [ ] Crear orden desde carrito
- [ ] Confirmar pago de orden
- [ ] Cancelar orden existente
- [ ] Tests pasan 100%
- [ ] Cobertura > 80%

---

## 🎬 CONCLUSIÓN

**Estado Actual**: 🔴 **NO PRODUCCIÓN**

La aplicación tiene una **arquitectura sólida** pero presenta **5 bugs críticos que impiden operación básica**. Ninguna operación CRUD completa funciona actualmente.

**ETA Corrección**: 2-3 días (1 developer) para issues críticas
**ETA Production-Ready**: 3-4 semanas (incluye tests, auth, hardening)

**Recomendación**: Pausar cualquier deployment hasta que se cierren issues bloqueantes.

---

**Reportado por**: Claude QA
**Timestamp**: 2025-11-23 12:00 UTC
