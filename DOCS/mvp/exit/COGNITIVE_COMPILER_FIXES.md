# Cognitive Compiler Fixes

> **Status**: ✅ IMPLEMENTED
> **Date**: 2025-12-02
> **Context**: Post-run analysis of Ariel_test_006_25_026_30.log

---

## 📊 Run Summary (Pre-Fix)

| Metric | Reported | Actual | Gap |
|--------|----------|--------|-----|
| Smoke Tests | 100% (11/11) | 13% (11/85) | IR tests skipped |
| Unit Tests | 66.4% | 66.4% | 88 failing |
| Constraint Compliance | 99.9% semantic | 50-68% IR | Business logic missing |
| Cognitive Compiler | "wired" | NOT EXERCISED | Docker failure |

---

## ✅ FIXES APPLIED

### Fix 1: Docker Compose `version` Attribute Removed ✅

**Files Modified**:
- `src/services/code_generation_service.py` (line 5402)
- `src/services/code_generation_service.py.backup` (line 3577)
- `templates/docker/docker-compose.yml.j2` (line 1)
- `templates/production/docker/docker-compose.yml.j2` (line 1)
- `templates/production/docker/docker-compose.test.yml.j2` (line 1)

**Change**: Removed obsolete `version: '3.8'` line, added comment explaining removal.

```yaml
# Before:
version: '3.8'
services:
  ...

# After:
# Note: 'version' attribute removed - obsolete in Docker Compose v2+
services:
  ...
```

---

### Fix 2: LLM Fallback REMOVED (Compiler Mode) ✅

**File Modified**: `tests/e2e/real_e2e_full_pipeline.py`

**Change**: Removed 112 lines of LLM fallback code. Now the pipeline:
1. REQUIRES TestsIR system to be available
2. REQUIRES Docker/IR smoke test to work
3. Fails explicitly if infrastructure is broken (no silent fallbacks)

```python
# Before:
if use_ir_smoke:
    smoke_result = await self._run_ir_smoke_test()
    if smoke_result is not None:
        # process
    else:
        print("⚠️ IR smoke test failed, falling back to LLM orchestrator")
        # 40+ lines of LLM fallback code
        # Then more fallback to basic validator

# After (COMPILER MODE):
if not TESTS_IR_AVAILABLE:
    raise RuntimeError("TestsIR system not available. Fix imports before retrying.")

if True:  # COMPILER MODE: Always use IR smoke test
    smoke_result = await self._run_ir_smoke_test()
    if smoke_result is not None:
        # process
    else:
        raise RuntimeError("IR smoke test infrastructure failed. Fix Docker/TestsIR before retrying.")
```

**Rationale**: A compiler doesn't have "fallbacks" - it either compiles correctly or fails with clear error messages.

---

### Fix 3: SERVICE Repair Code EXISTS ✅

**Analysis**: The code for injecting RuntimeFlowValidator already exists in:
- `src/services/production_code_generators.py`:
  - `_generate_behavior_guards()` generates `EntityValidator` class with `check_stock_invariant`, `check_status_transition`
  - `_generate_workflow_method_body()` generates methods with precondition checks
  - `find_workflow_operations()` extracts `affects_stock` and status transitions from IR

- `src/validation/smoke_repair_orchestrator.py`:
  - `_fix_business_logic_error()` already injects validation code into service methods
  - `_generate_stock_validation_code()`, `_generate_status_check_code()`, `_generate_empty_check_code()` generate snippets
  - Code injection happens at lines 2104-2122

**Real Issue**: The IR `behavior_model.flows` doesn't have `constraint_types: ['stock_constraint']` populated correctly from spec parsing. This is a spec→IR conversion issue, not a code generation issue.

---

## 📋 Implementation Summary

| # | Fix | File | Status |
|---|-----|------|--------|
| 1 | Remove docker-compose version | 5 files | ✅ Done |
| 2 | Remove LLM fallback (Compiler Mode) | real_e2e_full_pipeline.py | ✅ Done |
| 3 | Inject RuntimeFlowValidator | production_code_generators.py | ✅ Code exists |
| 4 | SERVICE repair injects code | smoke_repair_orchestrator.py | ✅ Code exists |
| 5 | LLM planner covers all endpoints | N/A | ❌ Removed (Compiler Mode) |

---

## 🔬 Root Cause Chain

```
Spec Parsing → ApplicationIR → BehaviorModel.flows
                                      ↓
                              constraint_types: [] (EMPTY!)
                                      ↓
                find_workflow_operations() → affects_stock: False
                                      ↓
               _generate_workflow_method_body() → NO stock check generated
                                      ↓
                        Smoke test fails on stock constraint
                                      ↓
                    Repair loop tries to inject code (works)
                                      ↓
                        BUT Docker was broken, so:
                                      ↓
                        IR smoke test returns None
                                      ↓
                        LLM fallback runs 11 trivial tests
                                      ↓
                        100% pass (fake success)
```

---

---

### Fix 4: ErrorClassifier Missing `constraint_graph` Attribute ✅

**Error**:
```
AttributeError: 'ErrorClassifier' object has no attribute 'constraint_graph'
```

**Root Cause**: `ErrorClassifier.__init__` didn't accept or initialize `constraint_graph`, but `_is_business_logic_error()` tried to use it.

**Fix Applied**:

1. Added `constraint_graph` parameter to `ErrorClassifier.__init__`:
```python
def __init__(self, log_parser=None, constraint_graph=None):
    self.log_parser = log_parser or ServerLogParser()
    self.constraint_graph = constraint_graph
```

2. Updated `SmokeRepairOrchestrator.__init__` to pass the reference after cognitive components are initialized:
```python
if COGNITIVE_COMPILER_AVAILABLE:
    # ... init components ...
    self.constraint_graph = ConstraintGraph()
    # Update error_classifier with constraint_graph reference
    self.error_classifier.constraint_graph = self.constraint_graph
```

---

## 🎯 Next Steps

1. ~~**Run the test again**~~ - ✅ Completado
2. ~~**Verify IR smoke test**~~ - ✅ 85 escenarios ejecutados
3. ~~**Verify repair loop**~~ - ✅ 11 componentes Cognitive Compiler activos
4. ~~**Monitor convergence**~~ - ✅ Convergió a 88.2% (+4.7%)

---

## 📊 Análisis de Mejoras Necesarias (Run: 2025-12-02)

### Resultados del Último Run

| Métrica | Valor |
|---------|-------|
| **IR Smoke Tests** | 85 escenarios |
| **Pass Rate Inicial** | 83.5% (71/85) |
| **Pass Rate Final** | 88.2% (75/85) |
| **Repair Cycles** | 3 |
| **Convergencia** | Sí (plateau) |

### Fallos Categorizados (10 tests) - Análisis Agnóstico

#### Categoría 1: DELETE nested retorna 404 en vez de 204 (4 fallos)

**Patrón IR**: `DELETE /{parent_plural}/{parent_id}/{child_plural}/{child_id}`

**Root Cause**: El generador no verifica existencia del child antes de eliminar.

**Datos requeridos del IR**:
- `endpoint.path_params` → identificar parent_id, child_id
- `ir.get_relationship(parent, child)` → FK field
- `child_entity.name` → nombre del repository

---

#### Categoría 2: POST/PUT nested retorna 422 en happy path (3 fallos)

**Patrón IR**: Operaciones `creates_entity` en flows

**Root Cause**: El método generado tiene guards pero NO ejecuta la operación.

**Datos requeridos del IR**:
- `flow.creates_entity` → child entity a crear
- `ir.get_relationship_fk(child, parent)` → FK field
- `child_entity.fields` → campos requeridos

---

#### Categoría 3: Conversion flow retorna 500 (1 fallo)

**Patrón IR**: Flows con `source_entity` → `target_entity`

**Root Cause**: El flujo de conversión no está implementado.

**Datos requeridos del IR**:
- `flow.source_entity`, `flow.target_entity`
- `flow.field_mappings` → qué campos copiar
- `flow.source_postcondition`, `flow.target_postcondition`

---

#### Categoría 4: PUT retorna 200 cuando debe retornar 422 (2 fallos)

**Patrón IR**: Campos con constraints (`minimum`, `maximum`, `pattern`)

**Root Cause**: Los schemas Pydantic no aplican constraints del IR.

**Datos requeridos del IR**:
- `field.minimum`, `field.maximum` → `Field(ge=X, le=Y)`
- `field.min_length`, `field.max_length` → `Field(min_length=X)`
- `field.pattern` → `Field(pattern=r'...')`

---

## 🛠️ Plan de Mejoras (AGNÓSTICO DEL DOMINIO)

> **PRINCIPIO**: DevMatrix es un compilador. NO debe hardcodear nada del dominio.
> Todo debe derivarse del IR (entities, relationships, fields, flows).

---

### Mejora 1: FlowLogicSynthesizer deriva lógica del IR

**Problema**: `FlowLogicSynthesizer.synthesize()` retorna vacío (0 guards, 0 transitions).

**Solución agnóstica**:
```python
# En flow_logic_synthesizer.py
def synthesize_operation_body(self, flow: IRFlow, parent_entity: IREntity) -> str:
    """Genera código de operación derivado 100% del IR."""

    # 1. Del IR: obtener child entity si es nested operation
    child_entity = self._get_child_entity_from_ir(flow, parent_entity)

    # 2. Del IR: obtener campos requeridos del child
    required_fields = self._get_required_fields_from_ir(child_entity)

    # 3. Del IR: obtener FK que conecta child→parent
    fk_field = self._get_fk_from_ir(child_entity, parent_entity)

    # 4. Generar código agnóstico
    return f'''
        from src.models.entities import {child_entity.name}Entity
        child_data = {{'{fk_field}': id}}
        for field in {required_fields}:
            child_data[field] = data.get(field)
        child = {child_entity.name}Entity(**child_data)
        self.db.add(child)
        await self.db.flush()
    '''
```

**Archivo**: `src/cognitive/flow_logic_synthesizer.py`
**Impacto**: +3 tests (todos los add_item, update_item)

---

### Mejora 2: DELETE nested usa IR para FK/entity

**Problema**: DELETE nested hardcodea nombres de entities.

**Solución agnóstica**:
```python
# En production_code_generators.py
def _generate_delete_nested_route(self, endpoint: IREndpoint, ir: ApplicationIR) -> str:
    """Genera DELETE nested derivado del IR."""

    # Del IR: parent entity y child entity
    parent_entity = ir.get_entity(endpoint.parent_entity_name)
    child_entity = ir.get_entity(endpoint.child_entity_name)

    # Del IR: FK field que conecta child→parent
    fk_field = ir.get_relationship_fk(child_entity, parent_entity)

    # Del IR: ID field del child
    child_id_field = endpoint.path_params[-1]  # último param es el child ID

    return f'''
@router.delete('/{{parent_id}}/{child_entity.plural}/{{child_id}}', status_code=204)
async def delete_{child_entity.snake_name}(parent_id: UUID, child_id: UUID, db=Depends(get_db)):
    # Verificar existencia (derivado de IR)
    child = await {child_entity.name}Repository(db).get(child_id)
    if not child or getattr(child, '{fk_field}') != parent_id:
        raise HTTPException(404, "{child_entity.name} not found")
    await {child_entity.name}Repository(db).delete(child_id)
    return Response(status_code=204)
'''
```

**Archivo**: `src/services/production_code_generators.py`
**Impacto**: +4 tests (todos los DELETE nested)

---

### Mejora 3: Checkout/conversion flows desde IR

**Problema**: POST /orders (checkout) hardcodea lógica de ecommerce.

**Solución agnóstica**:
```python
# En flow_logic_synthesizer.py
def synthesize_conversion_flow(self, flow: IRFlow, ir: ApplicationIR) -> str:
    """Genera flujo de conversión (checkout, submit, etc.) desde IR."""

    # Del IR: source entity (cart) y target entity (order)
    source_entity = flow.source_entity
    target_entity = flow.target_entity

    # Del IR: campos a copiar (definidos en flow.field_mappings)
    field_mappings = flow.field_mappings or self._infer_mappings(source_entity, target_entity)

    # Del IR: status transitions
    source_final_status = flow.source_postcondition  # e.g., "CHECKED_OUT"
    target_initial_status = flow.target_postcondition  # e.g., "PENDING"

    return f'''
        # Conversion flow: {source_entity.name} → {target_entity.name}
        source = await self.repo.get(id)
        if not source:
            raise HTTPException(404, "{source_entity.name} not found")

        # Create target with mapped fields
        target_data = {{{', '.join(f"'{t}': source.{s}" for s, t in field_mappings.items())}}}
        target = {target_entity.name}Entity(**target_data, status='{target_initial_status}')
        self.db.add(target)

        # Update source status
        source.status = '{source_final_status}'
        await self.db.flush()

        return {target_entity.name}Response.model_validate(target)
    '''
```

**Archivo**: `src/cognitive/flow_logic_synthesizer.py`
**Impacto**: +1 test (checkout)

---

### Mejora 4: Validaciones Pydantic desde IR constraints

**Problema**: Schemas no validan rangos porque Field() no tiene constraints.

**Solución agnóstica**:
```python
# En production_code_generators.py
def _generate_field_with_constraints(self, field: IRField) -> str:
    """Genera Field() con constraints derivados del IR."""

    constraints = []

    # Del IR: numeric constraints
    if field.minimum is not None:
        constraints.append(f"ge={field.minimum}")
    if field.maximum is not None:
        constraints.append(f"le={field.maximum}")

    # Del IR: string constraints
    if field.min_length is not None:
        constraints.append(f"min_length={field.min_length}")
    if field.max_length is not None:
        constraints.append(f"max_length={field.max_length}")
    if field.pattern:
        constraints.append(f"pattern=r'{field.pattern}'")

    # Del IR: default
    if field.default is not None:
        constraints.append(f"default={repr(field.default)}")

    if constraints:
        return f"Field({', '.join(constraints)})"
    return "..."
```

**Archivo**: `src/services/production_code_generators.py`
**Impacto**: +2 tests (validation_error scenarios)

---

## 📊 Resumen

| # | Mejora | Fuente de Datos | Impacto |
|---|--------|-----------------|---------|
| 1 | Operation body con child creation | IR: relationships, fields | +3 |
| 2 | DELETE nested con FK check | IR: relationships, path_params | +4 |
| 3 | Conversion flows (checkout) | IR: flows, field_mappings | +1 |
| 4 | Pydantic Field constraints | IR: field.minimum/maximum/pattern | +2 |

**Total**: +10 tests → 100% pass rate

---

## 🔑 Principio Fundamental

```
┌─────────────────────────────────────────────────────────┐
│                    SPEC (OpenAPI/etc)                   │
└─────────────────────────┬───────────────────────────────┘
                          │ parse
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    IR (ApplicationIR)                   │
│  - entities: [{name, fields, relationships}]            │
│  - flows: [{source, target, guards, field_mappings}]    │
│  - endpoints: [{path, method, entity, operation}]       │
└─────────────────────────┬───────────────────────────────┘
                          │ generate (AGNÓSTICO)
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    CÓDIGO GENERADO                      │
│  - NO hardcodea "Cart", "Order", "product_id"           │
│  - TODO viene del IR                                    │
└─────────────────────────────────────────────────────────┘
```

El compilador NUNCA debe saber qué es un "carrito" o una "orden". Solo sabe:
- Entity con name="X" tiene relationship a entity con name="Y"
- Flow "add_item" crea child entity con FK al parent
- Field "price" tiene constraint minimum=0.01


