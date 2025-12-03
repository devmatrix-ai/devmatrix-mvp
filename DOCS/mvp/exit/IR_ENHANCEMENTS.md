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

---

## ⭐ 5. Auto-Seed IR-Céntrico — Implementación Definitiva (Bug #203 Fix)

### Diagnóstico del Problema

El E2E pipeline alcanzó **98.5% pass rate** pero falla en:
- `POST /orders` → 422 (cart vacío, sin customer, sin stock)
- `PUT/DELETE /carts/{id}/items/{item_id}` → 404 (no existe CartItem)
- `PUT/DELETE /orders/{id}/items/{item_id}` → 404 (no existe OrderItem)

**Causa raíz**: El `seed_db.py` NO deriva estado desde BehaviorModelIR.flows.preconditions.

El Repair Agent no puede arreglar esto porque:
```
Constraint not auto-repairable: custom
Constraint not auto-repairable: stock_constraint
Constraint not auto-repairable: workflow_constraint
```

Estas son **faltas de datos**, no bugs de código.

### Solución: Pre-Smoke IR State Builder

El seed debe ser 100% derivado del IR:

```
DomainModelIR.entities        → Qué entidades crear
DomainModelIR.relationships   → Orden topológico + FKs
BehaviorModelIR.flows         → Preconditions del estado
ValidationModelIR.constraints → Valores válidos (enums, ranges, min)
TestsModelIR.nested_resources → Child entities con parent FKs
```

### Estructura de Datos

```python
@dataclass
class SeedRequirement:
    """Requirement derivado del IR para una entidad."""
    entity_name: str
    uuid: str                           # UUID predecible
    uuid_delete: str                    # UUID para DELETE tests
    fields: Dict[str, Any]              # Valores derivados del IR
    fk_refs: Dict[str, str]             # {fk_field: parent_entity}
    is_nested_child: bool               # True si es CartItem, OrderItem
    parent_entity: Optional[str]        # "Cart" si is_nested_child
    cardinality_min: int = 1            # Mínimo de instancias
    flow_preconditions: List[str]       # Preconditions que satisface

@dataclass
class SeedPlan:
    """Plan completo de seeds derivado del IR."""
    requirements: List[SeedRequirement]  # Ordenados topológicamente
    flow_states: Dict[str, List[str]]    # flow_name -> entities requeridas
```

### Algoritmo de Derivación

```python
def derive_seed_plan(ir: ApplicationIR) -> SeedPlan:
    """Deriva plan de seeds 100% desde IR."""
    requirements = []

    # 1. Extraer entidades y ordenar topológicamente
    entities = topological_sort(ir.domain_model.entities)

    # 2. Para cada entidad, derivar campos válidos
    for entity in entities:
        fields = {}
        for attr in entity.attributes:
            # Saltar auto-generados
            if attr.name in ('id', 'created_at', 'updated_at'):
                continue
            # Derivar valor desde ValidationModelIR
            fields[attr.name] = derive_valid_value(attr, ir.validation_model)

        # 3. Resolver FKs desde relationships
        fk_refs = {}
        for rel in entity.relationships:
            if rel.type == 'many_to_one':
                fk_field = f"{rel.target_entity.lower()}_id"
                fk_refs[fk_field] = rel.target_entity

        # 4. Detectar si es nested child
        nr = ir.domain_model.get_nested_resource_for_child(entity.name)

        requirements.append(SeedRequirement(
            entity_name=entity.name,
            fields=fields,
            fk_refs=fk_refs,
            is_nested_child=nr is not None,
            parent_entity=nr.parent_entity if nr else None
        ))

    # 5. Analizar flow preconditions
    flow_states = analyze_flow_preconditions(ir.behavior_model.flows)

    return SeedPlan(requirements=requirements, flow_states=flow_states)
```

### Análisis de Flow Preconditions

```python
def analyze_flow_preconditions(flows: List[Flow]) -> Dict[str, List[str]]:
    """Extrae preconditions de flows para determinar estado inicial."""
    flow_states = {}

    for flow in flows:
        required_entities = []

        for precondition in flow.preconditions:
            # Parse IR preconditions (domain-agnostic)
            # Ejemplos:
            #   "{entity}.status == 'OPEN'"     → entity debe existir con status OPEN
            #   "{ref}.exists"                  → ref entity debe existir
            #   "quantity > 0"                  → atributo con valor > 0
            #   "{container}.items.count >= 1" → child entities deben existir

            entities = extract_entities_from_precondition(precondition)
            required_entities.extend(entities)

        flow_states[flow.name] = required_entities

    return flow_states
```

### Derivación de Valores Válidos

```python
def derive_valid_value(attr: Attribute, validation: ValidationModelIR) -> Any:
    """Deriva valor válido desde constraints del IR."""

    # Buscar constraints para este campo
    constraint = validation.get_constraint_for_field(attr.name)

    if constraint:
        # Enum: primer valor
        if constraint.allowed_values:
            return constraint.allowed_values[0]

        # Range numérico: min + 1
        if constraint.min_value is not None:
            return constraint.min_value + 1

        # String con pattern: generar match
        if constraint.pattern:
            return generate_matching_string(constraint.pattern)

    # Fallbacks por tipo (domain-agnostic)
    type_defaults = {
        'string': f"Test {attr.name}",
        'integer': 1,
        'decimal': Decimal("99.99"),
        'boolean': True,
        'uuid': None,  # Se genera automáticamente
        'datetime': None,  # Se genera automáticamente
    }

    return type_defaults.get(attr.data_type.value, "test_value")
```

### Generación de Nested Children

```python
def generate_nested_children(ir: ApplicationIR, parent_seeds: Dict[str, str]) -> List[str]:
    """Genera seeds para child entities usando nested_resources del IR."""
    child_seeds = []

    for nr in ir.domain_model.get_nested_resources():
        parent_uuid = parent_seeds[nr.parent_entity.lower()]

        # Campos base
        fields = {
            nr.fk_field: f'UUID("{parent_uuid}")',  # FK al padre
        }

        # Auto-populate fields desde reference entity
        if nr.field_mappings:
            ref_entity = nr.field_mappings.get('_reference_entity')
            ref_fk = nr.field_mappings.get('_reference_fk')

            if ref_entity and ref_fk:
                ref_uuid = parent_seeds[ref_entity.lower()]
                fields[ref_fk] = f'UUID("{ref_uuid}")'

                # Copiar campos mapeados
                for child_field, ref_path in nr.field_mappings.items():
                    if child_field.startswith('_'):
                        continue
                    # Derivar valor del reference entity
                    fields[child_field] = derive_from_reference(ref_path, ir)

        child_seeds.append(generate_seed_block(nr.child_entity, fields))

    return child_seeds
```

### Seeds Requeridos por Endpoint

| Endpoint Pattern | Seeds Requeridos |
|------------------|------------------|
| `GET /entities/{id}` | 1 entity con UUID predecible |
| `PUT /entities/{id}` | 1 entity con UUID predecible |
| `DELETE /entities/{id}` | 1 entity con UUID_DELETE |
| `POST /parent/{id}/children` | 1 parent + FK válidos |
| `PUT /parent/{pid}/children/{cid}` | 1 parent + 1 child con FK correcto |
| `DELETE /parent/{pid}/children/{cid}` | 1 parent + 1 child (DELETE UUIDs) |
| `POST /orders` (checkout flow) | customer + cart(OPEN) + cart_items + products(stock>0) |

### Flow-Specific Seeds (Checkout Example)

El IR define el flow `checkout`:

```yaml
flow: checkout
preconditions:
  - "{cart}.status == 'OPEN'"
  - "{cart}.items.count >= 1"
  - "{product}.stock >= {cart_item}.quantity"
  - "{customer}.exists"
```

Derivación automática:

```python
# Del precondition "{cart}.items.count >= 1"
# → Crear CartItem con cart_id = cart.id

# Del precondition "{product}.stock >= {cart_item}.quantity"
# → Crear Product con stock >= 1, cart_item.quantity = 1

# Del precondition "{customer}.exists"
# → Crear Customer (ya existe por relación Cart.customer_id)
```

### Código Generado (seed_db.py)

```python
# Auto-generated from IR - NO domain knowledge

# 1. Base entities (order: topological)
test_product = ProductEntity(
    id=UUID("00000000-0000-4000-8000-000000000001"),
    name="Test Product",
    price=Decimal("99.99"),
    stock=100,           # >= cart_item.quantity (from flow precondition)
    is_active=True
)

test_customer = CustomerEntity(
    id=UUID("00000000-0000-4000-8000-000000000002"),
    email="test@example.com",
    name="Test Customer"
)

test_cart = CartEntity(
    id=UUID("00000000-0000-4000-8000-000000000003"),
    customer_id=UUID("00000000-0000-4000-8000-000000000002"),  # FK
    status="OPEN"        # From flow precondition
)

# 2. Nested children (from nested_resources)
test_cartitem = CartItemEntity(
    id=UUID("00000000-0000-4000-8000-000000000020"),
    cart_id=UUID("00000000-0000-4000-8000-000000000003"),      # Parent FK
    product_id=UUID("00000000-0000-4000-8000-000000000001"),   # Reference FK
    quantity=1,          # <= product.stock
    unit_price=Decimal("99.99")  # Auto-populated from Product.price
)

# Similar for Order + OrderItem...
```

### Sincronización UUID Registry ↔ seed_db

El smoke runner DEBE usar los mismos UUIDs que seed_db:

```python
# smoke_runner_v2.py - _build_seed_uuids()

# Base entities: registry sequential (1, 2, 3...)
seed_uuids['product'] = "00000000-0000-4000-8000-000000000001"
seed_uuids['customer'] = "00000000-0000-4000-8000-000000000002"
seed_uuids['cart'] = "00000000-0000-4000-8000-000000000003"

# Nested children: offset 20+ (from nested_resources)
seed_uuids['cartitem'] = "00000000-0000-4000-8000-000000000020"
seed_uuids['orderitem'] = "00000000-0000-4000-8000-000000000022"
```

### Principio Fundamental

```
El seed_db.py es la MATERIALIZACIÓN del estado IR en la base de datos.

Cada entidad seeded satisface:
  1. Constraints de ValidationModelIR
  2. Relaciones de DomainModelIR
  3. Preconditions de BehaviorModelIR.flows

Si el IR define un invariante → el seed lo satisface.
Si el IR define un flow → el seed crea el estado previo.

100% IR-driven. 0% domain knowledge.
```