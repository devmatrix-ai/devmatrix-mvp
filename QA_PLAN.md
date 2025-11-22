# Plan para robustecer generación en PRODUCTION_MODE

## Objetivo
Evitar fallos recurrentes (migraciones incompletas, esquemas de creación que exigen campos de servidor, rutas que llaman métodos inexistentes) en cualquier spec.

## Acciones propuestas
1) **Migraciones coherentes con modelos**
   - Generar alembic inicial iterando los modelos emitidos (campos/tipos/defaults), no un stub fijo.
   - Validar que todas las columnas de los modelos existen en la migración antes de finalizar (AST simple) y ejecutar `alembic upgrade head` en contenedor efímero.
2) **Esquemas de creación sin campos de servidor**
   - Marcar `id/created_at` como opcionales en `*Create`.
   - Permitir `items` vacíos en `CartCreate/OrderCreate` (sin `min_items` en create), defaults para `status`/`payment_status`.
   - Usar DTO específicos para ítems (p.ej. `CartItem` en `/carts/{id}/items`), no el contenedor completo.
3) **Servicios y rutas consistentes**
   - Asegurar que los métodos invocados existen (añadir alias `get_by_id` si rutas lo usan).
   - Rutas de items deben recibir el schema del ítem, no del cart/order.
4) **Validación post-generación (sanity)**
   - Revisar `schemas.py`: en `Create` no debe haber `id/created_at` requeridos ni `min_items` en `items`.
   - Revisar rutas vs services: métodos llamados existen.
   - Revisar migración vs modelos: todas las columnas/tipos presentes.
5) **Repair dirigida**
   - Si hay 500 por `UndefinedColumnError`, regenerar migración desde modelos y revalidar.
   - Si hay 422 por `id/items/status` requeridos en create, reescribir esquemas para server-managed fields opcionales/default.
6) **Smoke QA automático**
   - Ejecutar (vía `docker exec` o cliente interno) un flujo: crear producto → cliente → cart vacío → agregar ítem → checkout → pago.
   - Fallo en smoke = bloqueo del pipeline y disparo de repair/regen.
7) **Enums y defaults**
   - Aplicar `Literal[...]` a enums detectados.
   - Defaults para `status`/`payment_status` y otros enums en create para evitar required innecesario.
8) **Checklist permanente**
   - Usar `MIGRATION_CHECKLIST.md` como gate manual/automático antes de marcar la build como OK.

## Entregables
- Actualización de generador (`production_code_generators.py`) para migraciones completas y esquemas de creación corregidos.
- Validaciones de coherencia post-build.
- Script smoke QA reutilizable en `tests/e2e/generated_apps/<app>/` (docker exec).

## Métrica de salida
- Crear/cliente/cart/checkout/pago exitosos en smoke.
- Sin errores de columna faltante en logs.
- Sin 422 por campos de servidor en creates.***
