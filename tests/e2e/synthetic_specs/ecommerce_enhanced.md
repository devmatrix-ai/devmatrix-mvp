# E-commerce SaaS Enhanced Specification

> Especificación mejorada para plataforma SaaS de e-commerce con capacidades enterprise-grade

---

## 1. Ciclo de Vida del Tenant (SaaS de verdad)

Ahora tienes tenants, planes y facturación, pero falta especificar claramente el ciclo de vida del tenant:

### 1.1. Estados del Tenant

Agregar estados al Tenant:

#### Estados Disponibles

- **ACTIVE**: funcionamiento normal
- **TRIAL**: periodo de prueba limitado en días
- **SUSPENDED**: el tenant existe, pero:
  - no puede crear nuevas órdenes
  - el catálogo sigue visible o no (configurable)
- **CANCELLED**: tenant dado de baja, solo datos de solo lectura o pendiente borrado

#### Reglas de Transición

**En TRIAL:**
- Fecha de inicio y fin de trial
- Al expirar → pasa a SUSPENDED o FREE, según estrategia

**En SUSPENDED:**
- No se permiten nuevas órdenes ni nuevos productos
- Las órdenes pagadas siguen visibles

**En CANCELLED:**
- Marcar como no accesible para usuarios finales
- Solo accesible para procesos internos (export / borrado)

### 1.2. Borrado / Exportación de Datos

Especificación mínima "GDPR-lite":

#### Capacidades del Tenant

Cada tenant puede solicitar:
- **Exportación de sus datos**: ordenes, facturas, productos, usuarios
- **Borrado lógico**: anónimo de datos personales, marcar registros como borrados

#### Para usuarios (CUSTOMER)

- **"Soft delete"**: marcar como inactive, con email ofuscado
- Mantener facturas/órdenes por razones contables, pero sin datos identificables

---

## 2. Configuración Operativa por Tenant

Tienes StoreConfig básica; hace falta darle un poco más de forma:

### 2.1. Localización

En StoreConfig añadir:
- **locale**: ej: es_ES, en_GB
- **timezone**: ej: Europe/Madrid

#### Uso

- Todos los timestamps de negocio (facturas, órdenes) deben poder renderizarse según timezone del tenant
- La generación de periodos de facturación (SaaSInvoice) usa timezone del tenant

### 2.2. Política de Stock (HARD/SOFT) – Comportamiento

Ya tienes stock_policy pero faltan reglas claras:

#### HARD

- El stock se reserva inmediatamente al crear la Order PENDING_PAYMENT
- Si el pago falla y no hay reintento, la order puede cancelarse y devolver stock

#### SOFT

- El stock solo se descuenta al CAPTURED del Payment
- Si dos clientes intentan comprar el último ítem, el segundo puede recibir error de stock en el momento del capture

---

## 3. Envíos, Costes de Envío y Descuentos (mínimo viable)

Un SaaS e-commerce "tipo reducido" normalmente necesita al menos:

### 3.1. ShippingOption (opcional reducido)

Por tenant:
- **tipo**: FLAT_RATE | FREE
- **flat_amount**: (si aplica)
- **currency**
- **is_active**

#### Reglas

- Cada order tiene un campo shipping_cost y grand_total = total_amount + shipping_cost
- FREE plan puede tener solo una opción básica; PRO podría tener varias (pero puedes dejarlo 1 para todo)

### 3.2. Coupons / Discounts (mínimo)

Entidad simple **DiscountCode**:
- **code** (string)
- **tenant_id**
- **type**: PERCENT | FIXED
- **value**
- **is_active**
- **valid_from / valid_until** (opcional)

#### Reglas

- Una Order puede tener a lo sumo 1 discount_code aplicado
- Validar expiración, estado activo y tenant_id
- El descuento se aplica sobre total_amount antes de impuestos

---

## 4. Notificaciones y Comunicaciones (backend-only)

No necesitas provider (SendGrid, etc.), pero sí el modelo de eventos.

### 4.1. NotificationTemplate (Lógico)

Por tenant:

#### Tipo de evento:
- ORDER_PAID
- ORDER_CANCELLED
- PASSWORD_RESET
- SAAS_INVOICE_ISSUED

**Campos:**
- subject_template
- body_template (texto/HTML simple)

### 4.2. NotificationEvent (Registro)

Cada vez que ocurre un evento enviable:
- **notification_id**
- **tenant_id**
- **event_type**
- **target_email**
- **payload**: datos serializados mínimos
- **status**: PENDING | SENT | FAILED
- **attempts_count**

#### Regla

El sistema no tiene por qué enviar realmente correos en el MVP, pero:
- Debe registrar el evento (para integrar un sender real luego)
- Debe dejar claro que ante ciertos eventos se registra una NotificationEvent

---

## 5. Auditoría y Seguridad Operativa

Para SaaS real, aunque reducido, falta auditoría básica:

### 5.1. AuditLog

Diferente de SystemLog:

**Campos:**
- **audit_id**
- **actor_user_id**
- **tenant_id**
- **action_type**:
  - USER_ROLE_CHANGED
  - PLAN_CHANGED
  - PAYOUT_CREATED
  - REFUND_EXECUTED
  - PRODUCT_DELETED/DISABLED
- **target_id** (opcional: id de lo afectado)
- **metadata** (JSON)
- **created_at**

#### Reglas

- Toda operación sensible debe generar un AuditLog
- AuditLogs nunca se borran (solo archivado)

### 5.2. Controles Anti-Abuso (lógicos)

Límite lógico de:
- intentos de login fallidos por IP/usuario
- intentos de pago fallidos por order/usuario

**Marca de flag_suspicious** en User o Tenant:
- Si se superan ciertos umbrales (ej: 10 pagos fallidos en 1 hora)
- Puede disparar transición del Tenant a SUSPENDED manual o automática

---

## 6. Idempotencia y Concurrencia en Operaciones Críticas

Para que el backend sea "SaaS-grade" aunque simple, es clave especificar:

### 6.1. Idempotencia

**Operaciones críticas:**
- Checkout (creación de Order a partir de Cart)
- Payment capture
- Refund
- Payout

**Especificar:**
- Todas estas operaciones deben aceptar un idempotency_key lógico (aunque no expongas endpoint)

#### Reglas

Si se repite la operación con misma idempotency_key y misma semántica:
- Devolver mismo resultado
- No duplicar efectos (no duplicar Orders, Payments, Payouts)

### 6.2. Concurrencia de Stock

**Reglas a nivel negocio:**

La actualización de stock debe ser atómica por producto:
- No se permite que dos operaciones simultáneas de checkout/payment dejen stock negativo

**Si hay conflicto:**
- La segunda operación falla con error de negocio "STOCK_EXCEEDED"

---

## 7. Tareas en Segundo Plano / Scheduling

El spec ya habla de SaaSInvoices mensuales y Payouts; falta marcar explícitamente los jobs periódicos:

### 7.1. Jobs Programados

Al menos:

#### Generación de SaaSInvoice mensual
- Recorre tenants PRO
- Crea SaaSInvoice por periodo

#### Revisión de Payouts pendientes
- Cambia de PENDING → COMPLETED o FAILED (simulado)

#### Limpieza de datos temporales
- Carts OPEN sin actividad > X días → cleanup
- Tokens refresh expirados → cleanup

#### Recalculo de métricas agregadas
- Totales por tenant (ventas, ingresos, etc.)

> **Nota:** No hace falta especificar cron ni tecnología, solo que el sistema asume estos procesos como parte de la plataforma.

---

## 8. Plataforma (SaaS) vs Tenant: Separación de Roles

Hasta ahora modelamos OWNER/ADMIN/CUSTOMER a nivel tenant. Para SaaS como producto falta el rol PlatformAdmin (muy reducido):

### 8.1. PlatformAdmin (conceptual)

No hace falta usarlo en todos lados, pero sí:

**Puede:**
- Ver lista de tenants
- Ver estado (TRIAL, ACTIVE, SUSPENDED, CANCELLED)
- Forzar suspension/cancelación de un tenant
- Ver métricas globales (número de tenants, órdenes totales, etc.)

> No necesita implementar flujos súper complejos, pero es importante que el modelo conceptual contemple que la plataforma tiene alguien "por encima de los tenants".

---

## 9. Observabilidad de SaaS

Ya tienes logs y métricas por tenant; falta aclarar algunas métricas SaaS-level:

### 9.1. Métricas Globales

**Mínimo:**
- **tenant_count_total**
- **tenant_count_active**
- **tenant_count_trial**
- **orders_total** (global)
- **gmv_total**: sumatoria de pagos CAPTURED
- **mrr_saas**: simulado a partir de SaaSInvoices en estado ISSUED/PAID

> Estas métricas no son imprescindibles para funcionalidad del e-commerce, pero sí para que parezca un SaaS serio, útil para demo VC / comprador.

---

## Resumen de Mejoras

Esta especificación mejorada transforma el e-commerce básico en una plataforma SaaS enterprise-grade con:

1. ✅ Ciclo de vida completo del tenant con estados y transiciones
2. ✅ Políticas de datos GDPR-lite con exportación y borrado
3. ✅ Configuración operativa avanzada (localización, stock)
4. ✅ Sistema de envíos y descuentos
5. ✅ Infraestructura de notificaciones
6. ✅ Auditoría y seguridad operativa
7. ✅ Idempotencia y manejo de concurrencia
8. ✅ Jobs en segundo plano
9. ✅ Separación de roles plataforma/tenant
10. ✅ Métricas y observabilidad SaaS-level

---

**Versión:** 1.0
**Última actualización:** 2025-11-25
