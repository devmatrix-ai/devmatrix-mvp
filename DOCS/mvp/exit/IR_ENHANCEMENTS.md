⭐ 1. Auto-Seed Generator — versión 100% agnóstica

El Auto-Seed no puede “saber” que hay products o carts.

Debe derivar todas las precondiciones desde el IR.

✔ ¿Qué datos tiene DevMatrix para deducir estado inicial?

Todo esto ya existe:

Entities (DomainModelIR)

Relationships (DomainModelIR + ValidationModelIR)

Required fields (ValidationModelIR)

“must exist” patterns deducidos de flows (BehaviorModelIR)

Test scenarios (TestsModelIR)

API routes (APIModelIR)

Preconditions inferidas por BehaviorModelIR

Constraints (range, min, max, enum, fk, presence)

Flow DAG (DAGModelIR)

Con eso podés inferir cualquier precondición sin conocer el dominio.

✔ ¿Cómo detectar “qué entidades deben existir”? (agnóstico)
Método universal:
1. Analizar qué endpoints requiere cada test/scenario

Ejemplo de smoke scenario:

PUT /entities/{id}/subentity/{child_id}


Esta ruta implica:

existe un recurso raíz → {id}

existe un recurso hijo → {child_id}

ambos deben existir antes del test

Esto sale del APIModelIR, no del dominio.

2. Extraer relaciones desde ValidationModelIR

Ejemplo genérico:

entity_x.child_id references entity_y.id


Entonces:

si un escenario usa entity_x, la existencia de entity_y se vuelve obligatoria.

3. BehaviorModelIR define “flow invariants”

Un flow:

flow: custom_action
steps:
  - get entity_x
  - check condition on entity_x.field
  - update entity_y


Este flow implica un estado previo, sin saber qué son esos objetos.

✔ ¿Cómo generar los seeds? (agnóstico)
1. Usar APIModelIR para construir payloads mínimos válidos

Cada create_entity se deduce así:

POST /entity → verificar modelo de entrada

buscar en ValidationModelIR los campos requeridos

para enums: elegir el primer valor

para rango numérico: elegir min+1

para strings: generar UUID o random

para booleanos: true

2. Relaciones

Si una entidad A tiene campo fk b_id:

crear primero B

luego A con b_id = created_b.id

Todo inferido del IR.
Cero conocimiento de dominio.

3. Cardinalidades

Si un flow requiere “at least one child”:

deducir del ValidationModelIR
Ej.:

constraints: min_items: 1


Esto te dice que hay que seedear un hijo.

⭐ 2. Runtime Flow Repair — versión 100% agnóstica

De nuevo: sin saber qué es un product o cart.

El Runtime Flow Repair debe funcionar así:

✔ Paso 1 — Clasificación semántica del fallo (agnóstico)

Cada fallo tiene:

método

path

expected_status

actual_status

payload

response

ir_smoke flow definition

IR invariants del flow

IR postconditions

IR preconditions

Con eso podés clasificar:

a) MISSING_PRECONDITION

Detectable cuando:

el escenario falló con 404/422

y la entidad requerida no existe en DB

Esto se deduce dinámicamente:
realizás un GET a la entidad antes de ejecutar el smoke.

Ej.:

GET /entities/{id}
→ 404


→ No importa el dominio: es un missing precondition.

b) WRONG_STATUS_CODE

Detectable cuando:

el IR indica que esa transición es válida

y el servicio devuelve error

Ejemplo genérico:

IR: flow step says transition valid
Actual: 422


→ no necesitás saber si es checkout o add-to-cart, solo que:

IR dice válido

Código dice inválido

c) MISSING_SIDE_EFFECT

Detectable cuando:

la postcondición IR dice que una entidad X debe cambiar

y el smoke snapshot muestra que no cambió

Ejemplo genérico:

IR: After step, field A.x = A.x - 1
Runtime: A.x unchanged


Esto lo podés obtener comparando:

DB snapshot before flow

DB snapshot after flow

IR invariants / postconditions

→ sin dominio.

✔ Paso 2 — Repair (agnóstico)
Repair tipo 1: status code correction

Buscás en AST:

raise HTTPException(status_code=422, ...)


Cambiás a:

status_code=404


Determinista.

Repair tipo 2: missing side effect

Detectás en IR que hay un paso:

entity_x.field_y should change


Si no cambia:

identificás el servicio asociado al endpoint (vía APIModelIR)

buscás en AST el método

agregás/inyectás la línea:

await repo.update_x(field_y=new_value)


Pero lo hacés por semántica del IR, no por dominio.

⭐ 3. El circuito completo, 100% domain-agnostic

Aquí está la belleza de tu sistema:

SPEC (cualquier dominio)
↓
IR multi-estrato (tipos, relaciones, constraints, flows)
↓
Planner + DAG
↓
PatternBank (patrones semánticos universales)
↓
AST synthesis (determinista)
↓
CodeGen
↓
Static validation + Repair
↓
Deployment
↓
Auto-Seed (universal)
↓
Runtime Smoke + IR Smoke
↓
Runtime Flow Repair (universal)
↓
Learning (anti-patterns globales)
↓
Código perfecto → sin saber el dominio


Nada de esto depende de:

ecommerce

cart

productos

ordenes

stock

Todo se infiere de relaciones, constraints, paths, flows, postconditions y invariantes IR.

⭐ Conclusión: el verdadero poder de DevMatrix
**DevMatrix no necesita conocer el dominio.

El IR ya contiene TODA la semántica necesaria.**

Con Auto-Seed y Runtime Flow Repair:

→ DevMatrix puede generar y perfeccionar software de cualquier dominio,
→ sin humanos,
→ sin conocimiento previo,
→ usando solo IR, patterns y validación.

Esto es lo que lo convierte en:

modelo-agnóstico → sí

dominio-agnóstico → sí

reproducible → sí

auto-reparable → sí

validable → sí

auto-evolutivo → sí

estratégico → absolutamente.

---

## ⭐ 4. Nested Resources IR — 100% agnóstico (Bug #218 Fix)

### Problema Original
El código usaba heurísticas para inferir relaciones padre-hijo:
- `/carts/{id}/items/{item_id}` → asumía `CartItem` por convención de nombres
- Fallaba con patrones no estándar: `/playlists/{id}/songs/{song_id}`

### Solución: IR Explícito

El IR ahora define explícitamente todas las relaciones nested:

```python
# En DomainModelIR - Relationship extendido
Relationship(
    source_entity="Cart",
    target_entity="CartItem",
    type=RelationshipType.ONE_TO_MANY,
    field_name="items",
    is_nested_resource=True,      # ← Genera rutas nested
    path_segment="items",         # ← Segmento URL
    fk_field="cart_id",           # ← FK en child
    child_id_param="item_id",     # ← Nombre param en path
    field_mappings={              # ← Auto-population
        "unit_price": "Product.price",
        "_reference_fk": "product_id",
        "_reference_entity": "Product"
    }
)
```

### Clases Agregadas

**`NestedResourceInfo`** (domain_model.py):
```python
class NestedResourceInfo(BaseModel):
    parent_entity: str      # "Cart"
    child_entity: str       # "CartItem"
    path_segment: str       # "items"
    fk_field: str           # "cart_id"
    child_id_param: str     # "item_id"
    reference_fk: Optional[str]       # "product_id"
    reference_entity: Optional[str]   # "Product"
    field_mappings: Dict[str, str]    # {"unit_price": "Product.price"}
```

### Métodos en DomainModelIR

```python
# Obtener todas las nested resources
nested = domain_model.get_nested_resources()

# Buscar por entidad padre
nr = domain_model.get_nested_resource_for_parent("Cart")

# Buscar por entidad hijo
nr = domain_model.get_nested_resource_for_child("CartItem")
```

### TestsModelIR Self-Sufficiency

`TestsModelIR` ahora incluye `nested_resources` para que smoke tests
no dependan de otros IRs:

```python
class TestsModelIR(BaseModel):
    seed_entities: List[SeedEntityIR]
    endpoint_suites: List[EndpointTestSuite]
    nested_resources: List[NestedResourceInfo]  # ← Nuevo
    ...

    def get_nested_resource_for_path(self, path: str) -> Optional[NestedResourceInfo]:
        """Resuelve /orders/{id}/items/{item_id} → OrderItem"""
        ...
```

### Código Afectado (Sin Heurísticas)

| Archivo | Función | Cambio |
|---------|---------|--------|
| `domain_model.py` | `get_nested_resources()` | Solo retorna `is_nested_resource=True` |
| `production_code_generators.py` | `find_child_entity()` | Sin fallback, solo IR |
| `smoke_runner_v2.py` | `_build_seed_uuids()` | Usa `tests_model.nested_resources` |
| `smoke_runner_v2.py` | UUID resolution | Usa `get_nested_resource_for_path()` |
| `spec_to_application_ir.py` | `_enrich_nested_resources_from_endpoints()` | Detecta patterns desde paths |
| `tests_ir_generator.py` | `generate()` | Copia `nested_resources` a TestsModelIR |

### Flujo Completo de Datos

```
Spec Markdown
    ↓
SpecToApplicationIR._build_application_ir()
    ↓
_enrich_nested_resources_from_endpoints()  # Detecta /carts/{id}/items/{item_id}
    ↓
DomainModelIR.entities[].relationships[]   # is_nested_resource=True
    ↓
TestsIRGenerator.generate()
    ↓
domain_model.get_nested_resources()        # Extrae NestedResourceInfo[]
    ↓
TestsModelIR.nested_resources[]            # Self-sufficient para smoke tests
    ↓
SmokeRunnerV2._build_seed_uuids()          # Usa nested_resources
SmokeRunnerV2.get_nested_resource_for_path() # Resuelve child entity
```

### Principio Fundamental

```
Si el IR no define is_nested_resource=True → No se genera ruta nested
Si el IR no define field_mappings → No hay auto-population
```

**Cero heurísticas. Cero convenciones de nombres. 100% IR.**