# FlowLogicSynthesizer - Plan para 100% Pass Rate

**Fecha**: 2025-12-02  
**Estado Actual**: 92.0% (69/75 tests)  
**Objetivo**: 100% (75/75 tests)

---

## 📊 Estado Actual del Pipeline

### Componentes Cognitivos Existentes (100% Wired)

| Componente | Ubicación | Estado | Uso |
|------------|-----------|--------|-----|
| ConstraintGraph | `src/validation/constraint_graph.py` | ✅ Implementado | Bipartite graph constraint↔entity |
| IRBackpropagation | `src/validation/ir_backpropagation_engine.py` | ✅ Implementado | Violation → IR node mapping |
| ValidationRoutingMatrix | `src/validation/validation_routing_matrix.py` | ✅ Implementado | Routes constraints to layers |

### Resultado E2E Run #010 (2025-12-02)

```
Pass Rate: 92.0% (69/75)
Duration: 4.9 minutes
Files Generated: 96
Stratum: TEMPLATE 33%, AST 60.4%, LLM 6.2%
```

---

## 🔴 6 Fallas Restantes

| # | Endpoint | Expected | Got | Categoría | Root Cause |
|---|----------|----------|-----|-----------|------------|
| 1 | PUT /products/{id} | 422 | 200 | VALIDATION | Schema no rechaza datos inválidos |
| 2 | DELETE /carts/{cart_id}/items/{item_id} | 204 | 404 | NESTED_DELETE | Query no encuentra item |
| 3 | PUT /orders/{id}/items/{product_id} | 422 | 200 | VALIDATION | Schema no rechaza datos inválidos |
| 4 | DELETE /orders/{id}/items/{product_id} | 204 | 404 | NESTED_DELETE | Query no encuentra item |
| 5 | DELETE /products/{id} | 204 | 404 | TEST_ORDER | Producto ya eliminado |
| 6 | DELETE /products/{id} | 204 | 404 | TEST_ORDER | Producto ya eliminado |

### Categorías de Fallas

- **VALIDATION (2)**: PUT endpoints devuelven 200 cuando deberían devolver 422 para datos inválidos
- **NESTED_DELETE (2)**: DELETE nested no encuentra el item por query incorrecta
- **TEST_ORDER (2)**: Test ordering issue - productos eliminados por tests anteriores

---

## 🎯 Solución: FlowLogicSynthesizer

### Qué Es

FlowLogicSynthesizer es el componente que traduce las **constraints del IR** a **guards en el código generado**.

```
IR Flow Definition → FlowLogicSynthesizer → Service Method with Guards
```

### Responsabilidades

1. **Leer del IR**:
   - `preconditions`: Guards que deben cumplirse ANTES de ejecutar
   - `postconditions`: Invariantes que deben cumplirse DESPUÉS
   - `invariants`: Condiciones que SIEMPRE deben ser true
   - `transitions`: Cambios de estado válidos

2. **Generar Guards Sintéticos**:
   ```python
   # Ejemplo: stock_constraint
   if quantity > product.stock:
       raise HTTPException(422, "Insufficient stock")
   
   # Ejemplo: status_transition
   if cart.status != "OPEN":
       raise HTTPException(422, "Cart is not open")
   
   # Ejemplo: workflow_constraint
   if len(cart.items) == 0:
       raise HTTPException(422, "Cart is empty")
   ```

3. **Inyectar en Services**:
   - Pre-guards antes de la operación
   - Post-guards después de la operación
   - Calculated fields (e.g., `total_amount = sum(...)`)

---

## 🔧 Plan de Implementación

### Fase 1: Arreglar VALIDATION (PUT 422→200)

**Problema**: Los schemas de update no validan datos inválidos.

**Solución**: Agregar validators al schema generator que detecten campos inválidos.

```python
# En code_generation_service.py - _generate_schema_code()

# Para ProductUpdate:
# Si price < 0 o stock < 0 → ValidationError → 422
class ProductUpdate(BaseModel):
    price: Optional[float] = Field(None, ge=0.01)
    stock: Optional[int] = Field(None, ge=0)
```

**Archivos a Modificar**:
- `src/services/code_generation_service.py`: `_generate_schema_code()`

### Fase 2: Arreglar NESTED_DELETE (204→404)

**Problema**: La query busca por FK en lugar de PK.

**Fix Aplicado (Bug #205)**: Ya cambiamos a usar `Entity.id` en lugar del path param.

**Verificar**: La query debe ser:
```python
# Correcto
stmt = select(CartItemEntity).where(CartItemEntity.id == item_id)

# NO esto (incorrecto)
stmt = select(CartItemEntity).where(CartItemEntity.cart_id == cart_id, CartItemEntity.item_id == item_id)
```

**Diagnóstico**: Revisar el código generado en la app para confirmar.

### Fase 3: Arreglar TEST_ORDER (204→404)

**Problema**: Smoke test ejecuta múltiples DELETE sobre el mismo producto.

**Solución**: El TestsModelIR debe generar IDs únicos por escenario.

**Archivo a Revisar**:
- `src/cognitive/ir/tests_model_ir.py`

---

## 🏗️ Arquitectura de Integración

```
┌─────────────────────────────────────────────────────────────────┐
│                        ApplicationIR                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ behavior: BehaviorModelIR                                │   │
│  │   flows[]:                                               │   │
│  │     - name: "checkout"                                   │   │
│  │       preconditions: ["cart.status == OPEN"]             │   │
│  │       postconditions: ["order.status == PENDING"]        │   │
│  │       steps[]:                                           │   │
│  │         - guards: ["len(cart.items) > 0"]                │   │
│  │         - transitions: ["cart.status: OPEN→CHECKED_OUT"] │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FlowLogicSynthesizer                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1. Parse flow preconditions/postconditions              │   │
│  │ 2. Map to ValidationRoutingMatrix layer                 │   │
│  │ 3. Generate Python guard code                           │   │
│  │ 4. Build ConstraintGraph for cascade detection          │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Generated Service Code                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ async def checkout(self, cart_id: UUID) -> Order:        │   │
│  │     cart = await self.cart_repo.get(cart_id)             │   │
│  │                                                          │   │
│  │     # Pre-guards (from preconditions)                    │   │
│  │     if cart.status != "OPEN":                            │   │
│  │         raise HTTPException(422, "Cart not open")        │   │
│  │     if len(cart.items) == 0:                             │   │
│  │         raise HTTPException(422, "Cart empty")           │   │
│  │                                                          │   │
│  │     # Business logic                                     │   │
│  │     order = await self._create_order_from_cart(cart)     │   │
│  │                                                          │   │
│  │     # Post-guards (from postconditions)                  │   │
│  │     cart.status = "CHECKED_OUT"                          │   │
│  │     return order                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📝 Constraint Type Mapping

| IR Constraint | Python Guard | Layer |
|---------------|--------------|-------|
| `stock_constraint` | `if qty > product.stock: raise 422` | RUNTIME |
| `status_transition` | `if entity.status not in allowed: raise 422` | WORKFLOW |
| `workflow_constraint` | `if not precondition: raise 422` | BEHAVIOR |
| `custom` | Parsed from description | BEHAVIOR |
| `relationship` | `if not exists: raise 404` | RUNTIME |
| `uniqueness` | DB constraint + catch IntegrityError | SCHEMA |
| `format` | Pydantic Field validator | SCHEMA |
| `range` | Pydantic Field(ge=X, le=Y) | SCHEMA |
| `presence` | Pydantic Field(required=True) | SCHEMA |

---

## ✅ Checklist de Implementación

### Inmediato (Para 100%)

- [ ] **Fix #1**: PUT validation - agregar validators a UpdateSchemas
- [ ] **Fix #2**: Verificar DELETE nested usa PK correcto
- [ ] **Fix #3**: TestsModelIR usa IDs únicos por scenario

### FlowLogicSynthesizer (Componente Nuevo)

- [ ] Crear `src/cognitive/flow_logic_synthesizer.py`
- [ ] Parsear preconditions/postconditions del BehaviorModelIR
- [ ] Generar código Python para guards
- [ ] Integrar con `_generate_service_methods()` en code_generation_service.py
- [ ] Usar ValidationRoutingMatrix para routing
- [ ] Usar ConstraintGraph para cascade detection

### Integración

- [ ] Wire FlowLogicSynthesizer en `generate_from_application_ir()`
- [ ] Agregar tests unitarios
- [ ] Ejecutar E2E y verificar 100%

---

## 📈 Métricas de Éxito

| Métrica | Actual | Target |
|---------|--------|--------|
| Pass Rate | 92.0% | 100% |
| Violations | 6 | 0 |
| Repair Cycles | 3 | 0 |
| Compliance | 99.9% | 100% |

---

## 🔗 Referencias

- Bug #205: DELETE nested fixed (usar PK)
- Bug #206: Conversion flow detection fixed (no activar para {Entity}Create)
- `src/validation/constraint_graph.py`: ConstraintGraph
- `src/validation/ir_backpropagation_engine.py`: IRBackpropagation
- `src/validation/validation_routing_matrix.py`: ValidationRoutingMatrix

