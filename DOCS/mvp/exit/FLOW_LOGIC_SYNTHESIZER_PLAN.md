# FlowLogicSynthesizer - Plan para 100% Pass Rate

**Fecha**: 2025-12-02 (Actualizado - Bugs #210-213 Fixed)
**Estado Actual**: ~90% (estimado post-fix)
**Objetivo**: 100%

---

## 🎯 Principio Fundamental: Domain-Agnostic

> **FlowLogicSynthesizer NUNCA puede "saber" que existe Cart, Order, Product.**
> Solo razona sobre IR genérico: entidades, campos, constraints, roles.

---

## 🏗️ Arquitectura de 2 Capas

| Capa | Responsabilidad | Input | Output |
|------|-----------------|-------|--------|
| **FlowLogicSynthesizer** | Sintetiza constraints → Guard IR | `ApplicationIR`, `ConstraintGraph` | `Dict[FlowKey, FlowGuards]` con `GuardExpr` |
| **CodeGenerationService** | Traduce Guard IR → Python | `FlowGuards` + `varmap` | Código Python (FastAPI) |

### Separación de Concerns

| Componente | Responsabilidad | Constraints |
|------------|-----------------|-------------|
| **FlowLogicSynthesizer** | Comportamiento/flujo (Guard IR genérico) | `status_transition`, `workflow_constraint`, `stock_constraint`, `custom` |
| **Schema Generator** | Estructura/tipos (Pydantic) | `format`, `range`, `presence`, `uniqueness` |
| **TestsModelIR** | Orden de tests | IDs únicos por escenario |

---

## 📊 Guard IR Genérico (No Python, No Nombres Concretos)

```python
# src/cognitive/guard_ir.py

from dataclasses import dataclass
from typing import Literal, Union, Tuple

# Referencias abstractas - NO variables Python
EntityRef = Tuple[str, str]   # ("entity:Order", "status")
ContextRef = Tuple[str, str]  # ("input", "quantity")
Ref = Union[EntityRef, ContextRef]

@dataclass
class ComparisonExpr:
    """Comparación entre dos referencias o ref vs literal"""
    left: Ref                  # ej: ("entity:CartItem", "quantity")
    op: Literal["<", "<=", "==", "!=", ">=", ">"]
    right: Union[Ref, float, int, str]  # otra ref o literal

@dataclass
class MembershipExpr:
    """Pertenencia a conjunto de valores"""
    left: Ref                  # ej: ("entity:Order", "status")
    op: Literal["in", "not in"]
    right: list[str]           # ej: ["PENDING", "PAID"]

@dataclass
class ExistsExpr:
    """Existencia de entidad relacionada"""
    target: Ref                # ej: ("entity:Product", "id")
    kind: Literal["entity", "relation"]

GuardExpr = Union[ComparisonExpr, MembershipExpr, ExistsExpr]

@dataclass
class GuardSpec:
    expr: GuardExpr
    error_code: int              # 422 / 404 / 409
    message: str
    source_constraint_id: str    # trazabilidad al IR
    phase: Literal["pre", "post", "invariant"]

@dataclass
class FlowGuards:
    pre: list[GuardSpec]
    post: list[GuardSpec]
    invariants: list[GuardSpec]
```

**Clave**: Aquí NO existen variables Python. Solo referencias a entidades/campos del IR.

---

## 🔧 FlowLogicSynthesizer (100% Agnóstico)

```python
# src/cognitive/flow_logic_synthesizer.py

FlowKey = Tuple[str, str]  # (entity_name, operation_name)

class FlowLogicSynthesizer:
    def __init__(self, constraint_graph, routing_matrix):
        self._graph = constraint_graph
        self._routing = routing_matrix

    def synthesize_for_app(self, app_ir) -> Dict[FlowKey, FlowGuards]:
        guards_by_flow: Dict[FlowKey, FlowGuards] = {}
        for flow in app_ir.behavior.flows:
            key = (flow.entity_name, flow.operation_name)
            guards_by_flow[key] = self._build_guards_for_flow(app_ir, flow)
        return guards_by_flow

    def _build_guards_for_flow(self, app_ir, flow) -> FlowGuards:
        pre, post, invariants = [], [], []
        constraints = self._graph.get_constraints_for_flow(flow.id)

        for c in constraints:
            layer = self._routing.get_layer_for_constraint(c.type)
            if layer not in ("WORKFLOW", "BEHAVIOR", "RUNTIME"):
                continue
            g = self._constraint_to_guard(flow, c)
            if g:
                {"pre": pre, "post": post, "invariant": invariants}[g.phase].append(g)

        return FlowGuards(pre=pre, post=post, invariants=invariants)
```

### Constraint → Guard (Sin Lógica de Dominio)

```python
def _constraint_to_guard(self, flow, constraint) -> GuardSpec | None:
    t = constraint.type
    if t == "status_transition":
        return self._status_transition_guard(constraint)
    if t == "stock_constraint":
        return self._stock_constraint_guard(constraint)
    if t == "workflow_constraint":
        return self._workflow_guard(constraint)
    if t == "custom":
        return self._custom_guard(constraint)
    return None

def _status_transition_guard(self, c) -> GuardSpec:
    # metadata: {"entity": "X", "field": "status", "allowed_from": ["A", "B"]}
    expr = MembershipExpr(
        left=("entity:" + c.metadata["entity"], c.metadata["field"]),
        op="in",
        right=c.metadata.get("allowed_from", [])
    )
    return GuardSpec(expr=expr, error_code=422,
                     message="Invalid status transition",
                     source_constraint_id=c.id, phase="pre")

def _stock_constraint_guard(self, c) -> GuardSpec:
    # metadata: {"lhs": {"entity": "X", "field": "qty"},
    #            "rhs": {"entity": "Y", "field": "stock"}, "op": "<="}
    expr = ComparisonExpr(
        left=("entity:" + c.metadata["lhs"]["entity"], c.metadata["lhs"]["field"]),
        op=c.metadata.get("op", "<="),
        right=("entity:" + c.metadata["rhs"]["entity"], c.metadata["rhs"]["field"])
    )
    return GuardSpec(expr=expr, error_code=422,
                     message="Business rule violated",
                     source_constraint_id=c.id, phase="pre")
```

---

## � CodeGenerationService como Adaptador

El generador es el **único** que sabe cómo se llaman las variables en el stack:

```python
# En code_generation_service.py

def _python_expr_from_guard_expr(expr: GuardExpr, varmap: Dict[str, str]) -> str:
    """Traduce GuardExpr → código Python usando varmap"""
    # varmap: {"entity:Order": "order", ("input", "qty"): "payload.quantity"}

    if isinstance(expr, ComparisonExpr):
        left = _ref_to_python(expr.left, varmap)
        right = _ref_to_python(expr.right, varmap) if isinstance(expr.right, tuple) else repr(expr.right)
        return f"{left} {expr.op} {right}"

    if isinstance(expr, MembershipExpr):
        left = _ref_to_python(expr.left, varmap)
        values = ", ".join(repr(v) for v in expr.right)
        return f"{left} {'in' if expr.op == 'in' else 'not in'} [{values}]"

    if isinstance(expr, ExistsExpr):
        return f"{_ref_to_python(expr.target, varmap)} is not None"

def _generate_workflow_method_body(entity_name, operation, flow_guards, ...):
    varmap = {
        f"entity:{entity_name}": entity_snake,
        ("input", "..."): "payload...."
    }
    guards = flow_guards.get((entity_name, operation), FlowGuards([], [], []))

    for g in guards.pre:
        cond = _python_expr_from_guard_expr(g.expr, varmap)
        lines.append(f"    if not ({cond}):")
        lines.append(f"        raise HTTPException({g.error_code}, {g.message!r})")
```

---

## ✅ Checklist de Implementación

### A. Fixes Inmediatos (Ortogonales a FlowLogicSynthesizer)

#### A.1 Schema Generator - PUT Validation
- [x] Endurecer UpdateSchemas con `gt`/`ge` para campos numéricos
- **Archivo**: `src/services/production_code_generators.py` (líneas 1836-1870, 2209-2230)
- **Estado**: ✅ Ya implementado - constraints se preservan en UpdateSchemas

#### A.2 TestsModelIR - DELETE Test Ordering
- [ ] Cada DELETE crea su propia entidad (POST → DELETE)
- **Archivo**: `src/services/tests_ir_generator.py`
- **Estado**: 🔄 Pendiente - DELETE tests usan UUIDs separados pero múltiples DELETE del mismo tipo fallan

#### A.3 Nested DELETE - Bug #205
- [ ] Verificar query usa PK del child
- **Estado**: 🔄 Pendiente - DELETE /carts/{id}/items/{item_id} retorna 404

### B. FlowLogicSynthesizer v2 (Completo)

- [x] Crear `src/cognitive/guard_ir.py` con modelo de expresiones
- [x] Crear `src/cognitive/flow_logic_synthesizer.py` agnóstico
- [x] Definir contrato de `constraint.metadata` en IR
- [x] Integrar con CodeGenerationService (varmap + traducción)
- [x] **v2: Parsear `flow.preconditions`/`flow.postconditions` strings → Guard IR**
- [x] **v2: Merge guards por entity de todos los flows**
- **Estado**: ✅ v2 Implementado
  - `src/cognitive/flow_logic_synthesizer.py`: `_parse_condition_string()` parsea 7 patterns agnósticos
  - `src/services/production_code_generators.py`: líneas 2559-2589 merging de guards

### C. Validación Final

- [ ] E2E → 100% smoke tests (actual: 93.3% - 70/75)
- [ ] Sin regresiones

### D. Fallos Actuales (5 escenarios)

1. `DELETE /carts/{cart_id}/items/{item_id}` - 404 (item no seeded)
2. `POST /orders` (checkout) - 422 (validation error)
3. `DELETE /orders/{id}/items/{item_id}` - 404 (item no seeded)
4. `DELETE /carts/{id}` x2 - 404 (cart ya eliminado por test anterior)

---

## 📈 Métricas de Éxito

| Métrica | Actual | Target |
|---------|--------|--------|
| Pass Rate | 92.0% | 100% |
| Violations | 6 | 0 |
| Repair Cycles | 3 | 0 |

---

## 📋 Historial de Bugs

| Bug | Descripción | Estado |
|-----|-------------|--------|
| #205 | DELETE nested usaba FK en lugar de PK | ✅ Fixed |
| #206 | Conversion flow se activaba para {Entity}Create | ✅ Fixed |
| #207 | PUT validation no rechaza datos inválidos | 🔄 Pendiente |
| #208 | Test ordering causa DELETE 404 | 🔄 Pendiente |
| #210 | Flow methods generados para entidades incorrectas | ✅ Fixed (find_workflow_operations solo primary_entity) |
| #211 | POST /{id}/items creaba Cart nuevo en vez de agregar item | ✅ Fixed (path detection para 2 segmentos) |
| #212 | POST /{id}/clear creaba Cart nuevo en vez de limpiar | ✅ Fixed (map 'clear' → 'clear_items') |
| #213 | DELETE nested 404 - UUID mismatch entre registry y seed_db | ✅ Fixed (item UUIDs usan secuencia 20+) |

---

## 🔗 Referencias

- `src/validation/constraint_graph.py`: ConstraintGraph
- `src/validation/ir_backpropagation_engine.py`: IRBackpropagation
- `src/validation/validation_routing_matrix.py`: ValidationRoutingMatrix

---

## 📚 Diagrama de Flujo (Arquitectura Agnóstica)

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
│  │ 3. Generate Guard IR (GuardExpr) - NOT Python code      │   │
│  │ 4. Build ConstraintGraph for cascade detection          │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               CodeGenerationService (Adaptador)                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1. Recibe Guard IR + varmap del stack (FastAPI)         │   │
│  │ 2. Traduce GuardExpr → Python concreto                  │   │
│  │ 3. Inyecta guards en métodos de servicio                │   │
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
│  │     # Pre-guards (from Guard IR)                         │   │
│  │     if cart.status != "OPEN":                            │   │
│  │         raise HTTPException(422, "Cart not open")        │   │
│  │     if len(cart.items) == 0:                             │   │
│  │         raise HTTPException(422, "Cart empty")           │   │
│  │                                                          │   │
│  │     # Business logic                                     │   │
│  │     order = await self._create_order_from_cart(cart)     │   │
│  │                                                          │   │
│  │     # Post-guards (transitions)                          │   │
│  │     cart.status = "CHECKED_OUT"                          │   │
│  │     return order                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 Contrato Explícito de constraint.metadata

> **Clave para que FlowLogicSynthesizer sea agnóstico**: no inventa nada,
> solo traduce estructuras normalizadas que vienen del extractor de constraints.

### status_transition
```json
{
  "type": "status_transition",
  "entity": "Order",
  "field": "order_status",
  "allowed_from": ["PENDING_PAYMENT"],
  "allowed_to": ["PAID", "CANCELLED"]
}
```

### stock_constraint
```json
{
  "type": "stock_constraint",
  "lhs": {"entity": "CartItem", "field": "quantity", "role": "entity"},
  "rhs": {"entity": "Product", "field": "stock", "role": "entity"},
  "op": "<="
}
```

### workflow_constraint
```json
{
  "type": "workflow_constraint",
  "flow_id": "checkout",
  "expr_kind": "min_length",
  "target": {"entity": "Cart", "field": "items", "role": "entity"},
  "min": 1
}
```

### custom (fallback genérico)
```json
{
  "type": "custom",
  "entity": "Order",
  "field": "total_amount",
  "pattern": ">= 0",
  "description": "Total must be non-negative"
}
```

---

## 🛠️ Helpers para Refs (guard_ir.py)

```python
def make_entity_ref(entity: str, field: str) -> EntityRef:
    """Crea referencia a campo de entidad"""
    return (f"entity:{entity}", field)

def make_input_ref(field: str) -> ContextRef:
    """Crea referencia a campo de input/payload"""
    return ("input", field)
```

---

## 🚀 Implementación Progresiva

### Paso 1: guard_ir.py + interfaces mínimas
- Modelo de expresiones (ya definido)
- Helpers `make_entity_ref`, `make_input_ref`

### Paso 2: FlowLogicSynthesizer v0 (solo status_transition)
- Primera versión mínima
- Prueba E2E: IR → ConstraintGraph → Guard IR → Codegen

### Paso 3: Extender con stock_constraint y workflow_constraint
- Agregar `_stock_constraint_guard()`
- Agregar `_workflow_guard()`

### Paso 4: Adaptador en CodeGenerationService
- `_ref_to_python(ref, varmap)` centralizado
- Bucle de inyección de guards en service methods
