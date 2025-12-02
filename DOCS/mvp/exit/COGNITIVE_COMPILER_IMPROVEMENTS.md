# Cognitive Compiler Improvements (Domain-Agnostic)

> **Status**: 📋 PLANNED
> **Date**: 2025-12-02
> **Principio**: DevMatrix es agnóstico del dominio. TODO viene del IR.

---

## 📊 Estado Actual

| Métrica | Valor |
|---------|-------|
| Pass Rate | 88.2% (75/85) |
| Tests Fallando | 10 |
| Cognitive Compiler | ✅ 11 componentes activos |
| Convergencia | Sí (plateau) |

---

## 🔧 Mejoras Requeridas (Agnósticas)

### Mejora 1: FlowLogicSynthesizer genera operaciones desde IR

**Problema**: Métodos generados tienen guards pero NO ejecutan operaciones.

**Datos del IR requeridos**:

- `flow.creates_entity` → qué child entity crear
- `ir.get_relationship_fk(child, parent)` → FK field
- `child_entity.required_fields` → campos a copiar de data

**Implementación agnóstica**:

```python
def synthesize_create_child(self, flow: IRFlow, ir: ApplicationIR) -> str:
    child = ir.get_entity(flow.creates_entity)
    fk_field = ir.get_relationship_fk(child, flow.parent_entity)
    fields = [f.name for f in child.fields if f.required]

    return f'''
        from src.models.entities import {child.name}Entity
        child_data = {{'{fk_field}': id}}
        for field in {fields}:
            if field in data:
                child_data[field] = data[field]
        child = {child.name}Entity(**child_data)
        self.db.add(child)
        await self.db.flush()
    '''
```

**Archivo**: `src/cognitive/flow_logic_synthesizer.py`

---

### Mejora 2: DELETE nested verifica FK desde IR

**Problema**: DELETE nested no verifica que child pertenece al parent.

**Datos del IR requeridos**:

- `endpoint.path_params` → parent_id, child_id
- `ir.get_relationship_fk(child, parent)` → FK field

**Implementación agnóstica**:

```python
def _generate_delete_nested(self, endpoint: IREndpoint, ir: ApplicationIR) -> str:
    parent = ir.get_entity(endpoint.parent_entity)
    child = ir.get_entity(endpoint.child_entity)
    fk_field = ir.get_relationship_fk(child, parent)

    return f'''
    child = await {child.name}Repository(db).get(child_id)
    if not child or getattr(child, '{fk_field}') != parent_id:
        raise HTTPException(404, "{child.name} not found")
    await {child.name}Repository(db).delete(child_id)
    return Response(status_code=204)
    '''
```

**Archivo**: `src/services/production_code_generators.py`

---

### Mejora 3: Field constraints desde IR

**Problema**: Schemas Pydantic no tienen validaciones.

**Datos del IR requeridos**:

- `field.minimum`, `field.maximum` → `ge=`, `le=`
- `field.min_length`, `field.max_length` → string constraints
- `field.pattern` → regex validation

**Implementación agnóstica**:

```python
def _generate_field(self, field: IRField) -> str:
    constraints = []
    if field.minimum is not None:
        constraints.append(f"ge={field.minimum}")
    if field.maximum is not None:
        constraints.append(f"le={field.maximum}")
    if field.min_length is not None:
        constraints.append(f"min_length={field.min_length}")

    if constraints:
        return f"{field.name}: {field.type} = Field({', '.join(constraints)})"
    return f"{field.name}: {field.type}"
```

**Archivo**: `src/services/production_code_generators.py`

---

### Mejora 4: Conversion flows desde IR

**Problema**: Flows de conversión (source→target) no implementados.

**Datos del IR requeridos**:

- `flow.source_entity`, `flow.target_entity`
- `flow.field_mappings` → qué campos copiar
- `flow.source_postcondition`, `flow.target_postcondition`

**Implementación agnóstica**:

```python
def synthesize_conversion(self, flow: IRFlow, ir: ApplicationIR) -> str:
    source = ir.get_entity(flow.source_entity)
    target = ir.get_entity(flow.target_entity)
    mappings = flow.field_mappings or {}

    return f'''
        source = await self.repo.get(id)
        target_data = {{{', '.join(f"'{t}': source.{s}" for s, t in mappings.items())}}}
        target = {target.name}Entity(**target_data, status='{flow.target_postcondition}')
        self.db.add(target)
        source.status = '{flow.source_postcondition}'
        await self.db.flush()
    '''
```

**Archivo**: `src/cognitive/flow_logic_synthesizer.py`

---

## 📁 Archivos a Modificar

| Archivo | Mejora |
|---------|--------|
| `src/cognitive/flow_logic_synthesizer.py` | #1, #4 |
| `src/services/production_code_generators.py` | #2, #3 |

---

## 🔑 Principio Fundamental

```text
SPEC → IR → CÓDIGO

El compilador NUNCA sabe qué es un "carrito" o "producto".
Solo conoce:
- Entity con name="X" tiene relationship a entity con name="Y"
- Flow "add_item" tiene creates_entity="XItem"
- Field "price" tiene minimum=0.01
```

---

## 🔴 AUDIT: Referencias Hardcodeadas de Dominio

> **Fecha**: 2025-12-02
> **Total archivos afectados**: 15+
> **Total referencias**: 100+

### Categoría 1: Entity Names Hardcodeados

| Archivo | Líneas | Problema |
|---------|--------|----------|
| `src/services/production_code_generators.py` | 79, 830, 865, 878, 882, 1152, 1154, 1227, 1286 | `CartItem`, `OrderItem`, `ProductItemEntity` |
| `src/services/code_generation_service.py` | 3995, 4024, 4155, 4766, 5579, 5586, 5589 | `CartItem`, `OrderItem` conversiones |
| `src/services/inferred_endpoint_enricher.py` | 359, 484, 485 | `Cart`, `CartItems` en comentarios |
| `src/services/modular_architecture_generator.py` | 597 | `Cart → CartItems` |
| `src/parsing/spec_parser.py` | 1393, 1396, 1397, 1473, 1475, 1478 | Ejemplos con `CartItem`, `Product` |
| `src/cognitive/ir/behavior_model.py` | 55, 58 | Comentarios con `Cart`, `CartItem` |
| `src/mge/v2/agents/code_repair_agent.py` | 1510, 1511 | Ejemplo `CartItem.unit_price` |
| `src/core/uuid_registry.py` | 26, 119 | `Product`, `Customer`, `Cart`, `CartItem` |
| `src/validation/compliance_validator.py` | 1241 | `CartItem-Input/Output` |

### Categoría 2: Field Names Hardcodeados

| Archivo | Líneas | Problema |
|---------|--------|----------|
| `src/services/production_code_generators.py` | 549, 550 | `'quantity'`, `'product_id'` |
| `src/services/code_generation_service.py` | 5704, 5709, 5846, 5852 | `'quantity'`, `'stock'`, `'price'` |
| `src/services/tests_ir_generator.py` | 316, 318 | `'price'`, `'quantity'`, `'stock'` |
| `src/validation/runtime_smoke_validator.py` | 819, 821, 873 | `'price'`, `'quantity'`, `'stock'` |
| `src/validation/validation_routing_matrix.py` | 122, 161, 165 | `'stock'`, `'quantity'` |
| `src/cognitive/invariant_inferencer.py` | 64 | `STOCK_FIELDS` set hardcodeado |
| `src/services/business_logic_extractor.py` | 40 | `'stock'` regex |

### Categoría 3: Status Values Hardcodeados

| Archivo | Líneas | Problema |
|---------|--------|----------|
| `src/validation/smoke_repair_orchestrator.py` | 2246, 2269, 2270, 2293, 2329 | `'OPEN'`, `'COMPLETED'`, `'PAID'`, `'CANCELLED'` |
| `src/validation/agents/planner_agent.py` | 119, 120 | `'PAID'`, `'CHECKED_OUT'` |
| `src/services/production_code_generators.py` | 381 | Pattern `'OPEN'` |

### Categoría 4: Flow/Operation Names Hardcodeados

| Archivo | Líneas | Problema |
|---------|--------|----------|
| `src/specs/spec_to_application_ir.py` | 1110, 1123, 1163 | `checkout`, `payment` |
| `src/validation/smoke_repair_orchestrator.py` | 338, 340, 395, 478, 484 | Action verbs list |
| `src/learning/anti_pattern_advisor.py` | 256 | `['checkout', 'activate', ...]` |
| `src/validation/validation_routing_matrix.py` | 181 | `'/checkout', '/pay', '/cancel'` |

### Categoría 5: Scripts con Ejemplos Ecommerce

| Archivo | Problema |
|---------|----------|
| `scripts/repopulate_patterns.py` | 50+ líneas de `Cart`, `Order`, `Product`, `CartItem` |
| `scripts/validate_llm_extractor_phase2.py` | Ejemplos con `Customer`, `Product`, `Order` |
| `scripts/test_behavior_integration.py` | Tests con `Order`, `Product`, `Customer` |
| `scripts/seed_enhanced_patterns.py` | Patrones con `Product`, `Order` |

### Categoría 6: Validation/Golden Path

| Archivo | Líneas | Problema |
|---------|--------|----------|
| `src/validation/golden_path_validator.py` | 5-6, 89-109 | Golden paths hardcodeados |
| `src/validation/runtime_flow_validator.py` | 96, 205 | `product.stock`, referencias |
| `src/validation/db_snapshot.py` | 74 | Ejemplo `["Product", "Cart"]` |

---

## 📋 Plan de Refactoring

### Prioridad Alta (Core del compilador)

- **production_code_generators.py** - 17 referencias
- **code_generation_service.py** - 8 referencias
- **smoke_repair_orchestrator.py** - 10+ referencias
- **inferred_endpoint_enricher.py** - 4 referencias

### Prioridad Media (Heurísticas)

- **validation_routing_matrix.py** - Listas de keywords
- **invariant_inferencer.py** - `STOCK_FIELDS` set
- **business_logic_extractor.py** - Regexes

### Prioridad Baja (Scripts/Ejemplos)

- **scripts/*.py** - Son ejemplos, no código de producción
- **golden_path_validator.py** - Podría parametrizarse

---

## ✅ Solución Agnóstica

Para cada categoría, la solución es:

1. **Entity names**: Derivar de `ir.entities[i].name`
2. **Field names**: Derivar de `entity.fields[i].name` + `field.semantic_type`
3. **Status values**: Derivar de `flow.precondition_status`, `flow.postcondition_status`
4. **Flow names**: Derivar de `ir.behavior_model.flows[i].name`
5. **Relationships**: Derivar de `ir.get_relationship(parent, child)`
