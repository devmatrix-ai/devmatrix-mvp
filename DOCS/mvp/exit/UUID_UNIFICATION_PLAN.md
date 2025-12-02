# UUID Unification Plan

## Problema Identificado

**Fecha**: 2025-12-02
**Síntoma**: seed_db.py genera UUIDs empezando en `000000000020` en lugar de `000000000001`

### Causa Raíz

Existen **DOS generadores de seed_db.py** que no comparten lógica de UUIDs:

| Componente | Ubicación | UUIDs Generados |
|------------|-----------|-----------------|
| `_generate_seed_db_script()` | `code_generation_service.py:5540` | ✅ Correctos (0001, 0002...) |
| `SeedDataAgent.generate_seed_script()` | `seed_data_agent.py:112` | ❌ Desde LLM (puede variar) |

**Flujo problemático**:
1. `code_generation_service.py` genera `seed_db.py` con UUIDs correctos
2. `SmokeTestOrchestrator` (línea 92-93) **sobrescribe** con output del LLM
3. LLM genera UUIDs inconsistentes → FK violations

### Conclusión Clave

> **El LLM nunca debe ser productor de UUIDs, sólo consumidor de un mapping fijo.**

---

## Tabla de Progreso

| Fase | Tarea | Estado | Fecha |
|------|-------|--------|-------|
| 1 | Crear UUIDRegistry centralizado | ✅ Completado | 2025-12-02 |
| 2 | Refactorizar code_generation_service.py | ✅ Completado | 2025-12-02 |
| 3 | Refactorizar smoke test orchestrator | ✅ Completado | 2025-12-02 |
| 4 | Actualizar prompts del LLM planner | ✅ Completado | 2025-12-02 |
| 5 | Validar con E2E test | 🔄 En Progreso | - |

**Leyenda**: ⬜ Pendiente | 🔄 En Progreso | ✅ Completado | ❌ Bloqueado

---

## Fase 1: Crear UUIDRegistry Centralizado ✅

**Objetivo**: Módulo único que genere UUIDs deterministas por entidad.

**Ubicación**: `src/core/uuid_registry.py`

### Principios de Diseño

1. **Determinismo**: Orden de entities viene del IR ordenado canónicamente
2. **Formato**: Estilo `00000000-0000-4000-8000-000000000001` (UUID v4 válido)
3. **Variantes**: `primary` y `delete` por entidad (suficiente para 99% de tests)
4. **FKs**: `get_fk_uuid()` siempre apunta al `primary` de la entidad target
5. **No I/O, No LLM**: Lógica pura determinista

### API Implementada

```python
class SeedUUIDRegistry:
    """Fuente única de UUIDs deterministas para seed data, tests y prompts."""

    UUID_BASE = "00000000-0000-4000-8000-00000000000"       # + 1 dígito
    UUID_BASE_DELETE = "00000000-0000-4000-8000-0000000000" # + 2 dígitos
    NOT_FOUND_UUID = "99999999-9999-4000-8000-999999999999"

    @classmethod
    def from_entity_names(cls, entity_names: List[str]) -> "SeedUUIDRegistry":
        """Crea registry desde lista de nombres de entidades."""

    @classmethod
    def from_ir(cls, ir: ApplicationIR) -> "SeedUUIDRegistry":
        """Crea registry desde ApplicationIR."""

    def get_uuid(self, entity: str, variant: str = "primary") -> str:
        """Obtiene UUID para entidad. Variantes: 'primary', 'delete'."""

    def get_fk_uuid(self, target_entity: str) -> str:
        """Obtiene UUID para referencia FK (siempre primary)."""

    def get_next_item_uuid(self) -> str:
        """UUID para join tables (CartItem, OrderItem). Empieza en 20."""

    def to_dict(self) -> Dict[str, Tuple[str, str]]:
        """Exporta mapeo entity -> (primary, delete)."""

    def to_prompt_json(self) -> str:
        """Exporta JSON para inyección en prompts LLM."""
```

### Esquema de UUIDs

| Entidad | Primary | Delete | Uso |
|---------|---------|--------|-----|
| Product (idx=1) | `...0001` | `...0011` | CRUD normal |
| Customer (idx=2) | `...0002` | `...0012` | CRUD normal |
| Cart (idx=3) | `...0003` | `...0013` | CRUD normal |
| Order (idx=5) | `...0005` | `...0015` | CRUD normal |
| CartItem (join) | `...0020+` | `...0021+` | Items de join tables |
| _not_found | `99999...9999` | - | Tests 404 |

---

## Fase 2: Refactorizar code_generation_service.py ✅

### Cambios Realizados

1. **Importar registry** al inicio de `_generate_seed_db_script()`
2. **Eliminar lógica inline** de `uuid_base`, `entity_uuids`, `item_uuid_counter`
3. **Usar métodos del registry**:
   - `uuid_registry.get_uuid(entity)` para primary
   - `uuid_registry.get_uuid(entity, "delete")` para delete
   - `uuid_registry.get_fk_uuid(target)` para FKs
   - `uuid_registry.get_next_item_uuid()` para join tables

### Código Antes vs Después

**Antes** (lógica duplicada):
```python
uuid_base = "00000000-0000-4000-8000-00000000000"
entity_uuids = {}
for idx, entity in enumerate(entities_list, start=1):
    entity_uuids[entity.name.lower()] = f"{uuid_base}{idx}"
```

**Después** (registry centralizado):
```python
from src.core.uuid_registry import SeedUUIDRegistry
uuid_registry = SeedUUIDRegistry.from_entity_names([e.name for e in entities_list])
entity_uuids = uuid_registry.to_dict()
```

---

## Fase 3: Refactorizar Smoke Test Orchestrator ✅

### Decisión: Opción A - Prohibir sobrescritura

**Flujo Anterior** (problemático):
```
code_generation → seed_db.py ✅
                      ↓
smoke_test_orchestrator → SOBRESCRIBE con LLM output ❌
```

**Flujo Nuevo** (correcto):
```
code_generation → seed_db.py ✅
                      ↓
smoke_test_orchestrator → USA el existente ✅
```

### Cambio en smoke_test_orchestrator.py

```python
# Antes: siempre sobrescribía
seed_script = self.seed_generator.generate_seed_script(plan, ir)
seed_path.write_text(seed_script)

# Después: usa existente si está disponible
if seed_path.exists():
    logger.info("Using existing seed_db.py (from code_generation_service)")
else:
    # Fallback solo si no existe
    seed_script = self.seed_generator.generate_seed_script(plan, ir)
    seed_path.write_text(seed_script)
```

---

## Fase 4: Actualizar Prompts del LLM Planner ✅

### Prompt Endurecido

Los prompts ahora incluyen reglas "militares" para que el LLM NUNCA invente UUIDs:

```python
PLANNER_USER_PROMPT = """...
## Pre-assigned UUIDs (USE THESE EXACTLY - DO NOT MODIFY)
{uuid_assignments}

IMPORTANT: Use the UUIDs above exactly as shown. Do NOT generate your own UUIDs.
Use the "primary" UUID for normal tests, "delete" UUID for DELETE tests.
"""
```

### Reglas Inyectadas

1. **NEVER** generate your own UUIDs
2. **ALWAYS** use `primary` value for main records
3. **ALWAYS** use `primary` of target entity for FKs
4. Use `delete` variant **ONLY** for DELETE tests
5. If you need more examples, re-use existing UUIDs

---

## Fase 5: Validación E2E ✅ COMPLETADA

### Comando de Validación

```bash
rm -rf tests/e2e/generated_apps/ecommerce-* && python tests/e2e/real_e2e_full_pipeline.py
```

### Criterios de Éxito - UUIDs

| Check | Descripción | Estado |
|-------|-------------|--------|
| ✅ | Product ID = `000000000001` | ✅ PASS |
| ✅ | Customer ID = `000000000002` | ✅ PASS |
| ✅ | Cart ID = `000000000003` | ✅ PASS |
| ✅ | Order ID = `000000000005` | ✅ PASS |
| ✅ | FKs referencian UUIDs correctos | ✅ PASS |
| ✅ | CartItem/OrderItem usan UUIDs 0020+ | ✅ PASS |
| ✅ | seed_db.py no modificado entre generación y ejecución | ✅ PASS |

### UUIDs Generados (Verificado 2025-12-02)

```
id=UUID("00000000-0000-4000-8000-000000000001"),  # Product primary
id=UUID("00000000-0000-4000-8000-000000000011"),  # Product delete
id=UUID("00000000-0000-4000-8000-000000000002"),  # Customer primary
id=UUID("00000000-0000-4000-8000-000000000012"),  # Customer delete
id=UUID("00000000-0000-4000-8000-000000000003"),  # Cart primary
customer_id=UUID("00000000-0000-4000-8000-000000000002"),  # FK → Customer
id=UUID("00000000-0000-4000-8000-000000000005"),  # Order primary
id=UUID("00000000-0000-4000-8000-000000000020"),  # CartItem (join table)
cart_id=UUID("00000000-0000-4000-8000-000000000003"),  # FK → Cart
product_id=UUID("00000000-0000-4000-8000-000000000001"),  # FK → Product
```

### Bug Encontrado Durante Validación

El bug `is_join_table()` clasificaba erróneamente TODAS las entidades como join tables:

**Bug (línea 5580):**
```python
# INCORRECTO: Contaba one_to_many Y many_to_one
fk_count = sum(1 for r in rels if 'many' in str(r.type).lower())
```

**Fix aplicado:**
```python
# CORRECTO: Solo cuenta many_to_one (FKs reales)
fk_count = sum(1 for r in rels if 'many_to_one' in str(r.type).lower())
```

### Test Unitario de Determinismo

```python
def test_seed_uuid_registry_is_deterministic():
    entities = ["product", "customer", "order"]
    r1 = SeedUUIDRegistry.from_entity_names(entities)
    r2 = SeedUUIDRegistry.from_entity_names(entities)

    assert r1.to_dict() == r2.to_dict()
    assert r1.get_fk_uuid("customer") == r2.get_fk_uuid("customer")
```

---

## ⚠️ Bug Detectado Post-Validación: `product_data` undefined

### Síntoma
```
NameError: name 'product_data' is not defined
```
En `src/api/routes/product.py`, línea 28.

### Causa
El generador de código crea un parámetro con un nombre pero lo referencia con otro:

```python
# Línea 22-23: Parámetro se llama product_create_data
async def creates_a_new_product_with_name__description__price__stock_and_status(
    product_create_data: ProductCreate, ...):

# Línea 28: Pero se usa product_data (NO EXISTE)
    product = await service.create(product_data)  # ❌ NameError
```

### Origen del Bug
Este NO es un bug de UUIDs. Es un bug en la generación de rutas en `code_generation_service.py`.

El patrón `{entity}_create_data` vs `{entity}_data` no es consistente.

### Archivo Afectado
- `src/services/code_generation_service.py` - sección de generación de routes

### Estado
- 🔴 **Crítico**: Bloquea POST /products y otros endpoints
- 📍 **Scope**: Fuera del UUID Unification Plan
- 📌 **Siguiente Bug a Investigar**

---

## Archivos Afectados

| Archivo | Acción | Estado |
|---------|--------|--------|
| `src/core/uuid_registry.py` | CREAR | ✅ |
| `src/services/code_generation_service.py` | MODIFICAR | ✅ |
| `src/validation/smoke_test_orchestrator.py` | MODIFICAR | ✅ |
| `src/validation/agents/planner_agent.py` | MODIFICAR | ✅ |
| `src/validation/agents/seed_data_agent.py` | NO TOCAR (fallback) | ⬜ |

---

## Resultado Esperado

Cuando se cierre este plan:

1. **seed_db.py** será 100% determinista y único por app/spec
2. **Cualquier agente** que necesite IDs será **consumidor** del `SeedUUIDRegistry`, nunca generador
3. **Problemas eliminados**:
   - UUIDs empezando en `000000000020`
   - FKs rotas
   - "Seed data verification failed"

