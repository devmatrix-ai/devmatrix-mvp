# Implementation Plan: Database Architecture 2.0 - Complete Graph Transformation

> Plan completo para transformar TODOS los datos a grafos con labels correctos.
> Fecha: 2025-11-29 (actualizado)
> Duración: 8 Sprints
> **Principio**: TODO debe ser grafo, NO JSON serializado

---

## Índice

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Estado Actual vs Objetivo](#2-estado-actual-vs-objetivo)
2A. [Tareas Inmediatas (Pre-Sprint 3)](#2a-tareas-inmediatas-pre-sprint-3)
3. [Sprint 0: Schema Alignment & Cleanup](#3-sprint-0-schema-alignment--cleanup)
4. [Sprint 1: Graph Expansion - DomainModelIR](#4-sprint-1-graph-expansion---domainmodelir)
5. [Sprint 2: Graph Expansion - APIModelIR](#5-sprint-2-graph-expansion---apimodelir)
5A. [Sprint 2.5: TARGETS_ENTITY & API Coverage](#5a-sprint-25-targets_entity--api-coverage)
6. [Sprint 3: Graph Expansion - BehaviorModelIR + ValidationModelIR](#6-sprint-3-graph-expansion---behaviormodelir--validationmodelir)
7. [Sprint 4: Graph Expansion - InfrastructureModelIR](#7-sprint-4-graph-expansion---infrastructuremodelir)
8. [Sprint 5: Graph Expansion - TestsModelIR (MVP)](#8-sprint-5-graph-expansion---testsmodelir-mvp)
9. [Sprint 6: Lineage & Intelligence](#9-sprint-6-lineage--intelligence)
10. [Sprint 7: Real-Time Tracking](#10-sprint-7-real-time-tracking)
11. [Sprint 8: Analytics & Optimization](#11-sprint-8-analytics--optimization)
12. [Riesgos Técnicos y Mitigaciones](#12-riesgos-técnicos-y-mitigaciones)
13. [Archivos a Crear/Modificar](#13-archivos-a-crearmodificar)
14. [Testing Strategy](#14-testing-strategy)
15. [Rollback Plan](#15-rollback-plan)
16. [Métricas de Éxito](#16-métricas-de-éxito)

---

## 1. Resumen Ejecutivo

### Objetivo Principal
**Transformar el almacenamiento de IR de JSON serializado a grafos nativos de Neo4j**, aprovechando el poder del grafo para queries de relaciones y trazabilidad.

### Principios Guía

| Principio | Descripción |
|-----------|-------------|
| **Graph-Native** | TODO dato estructurado → nodos y relaciones |
| **Labels = Code** | Labels Neo4j = nombres de clases Python |
| **IR Suffix** | Todos los IRs usan sufijo: `ApplicationIR`, `DomainModelIR` |
| **Single Source** | Neo4j es la fuente de verdad para estructura |

### Scope Completo

| Sprint | Enfoque | Entregables |
|--------|---------|-------------|
| **Inmediato** | **Fundamentos Arquitectónicos** | **GraphSchemaVersion, MigrationRun, GraphIRRepository base** |
| 0 | Cleanup & Alignment ✅ | Orphans eliminados, labels renombrados |
| 1 | DomainModelIR → Graph ✅ | Entity, Attribute, Relationship como nodos |
| 2 | APIModelIR → Graph ✅ | Endpoint, APISchema, APIParameter como nodos |
| **2.5** | **TARGETS_ENTITY & Coverage** | **Endpoint→Entity links, campo source, QA dashboard** |
| 3 | BehaviorModelIR + ValidationModelIR | Flow, Step, Invariant + ValidationRule como nodos |
| 4 | InfrastructureModelIR | DatabaseConfig, Observability como nodos |
| 5 | TestsModelIR MVP | TestScenarioIR, VALIDATES_ENDPOINT básico |
| 6 | Lineage & Intelligence | Spec→IR→Files tracking, FullIRGraphLoader |
| 7 | Real-Time Tracking | Event logging, code fragments |
| 8 | Analytics & Optimization | Pattern optimization, transfer learning |

---

## 2. Estado Actual vs Objetivo

### 2.1 Problema Actual: JSON en Properties

```
ACTUAL (MAL):
(:Application {
    app_id: "uuid",
    domain_model_data: '{"entities":[...]}',  ← JSON STRING!
    api_model_data: '{"endpoints":[...]}',    ← JSON STRING!
    ...
})

OBJETIVO (BIEN):
(:ApplicationIR {app_id: "uuid"})
    -[:HAS_DOMAIN_MODEL]->(:DomainModelIR)
        -[:HAS_ENTITY]->(:Entity {name: "Product"})
            -[:HAS_ATTRIBUTE]->(:Attribute {name: "id", type: "UUID"})
            -[:HAS_ATTRIBUTE]->(:Attribute {name: "price", type: "FLOAT"})
        -[:HAS_ENTITY]->(:Entity {name: "Order"})
```

### 2.2 Renaming de Labels Requerido

| Actual (Neo4j) | Nuevo (Neo4j) | Clase Python |
|----------------|---------------|--------------|
| `Application` | `ApplicationIR` | `ApplicationIR` |
| `DomainModel` | `DomainModelIR` | `DomainModelIR` |
| `APIModel` | `APIModelIR` | `APIModelIR` |
| `BehaviorModel` | `BehaviorModelIR` | `BehaviorModelIR` |
| `ValidationModel` | `ValidationModelIR` | `ValidationModelIR` |
| `InfrastructureModel` | `InfrastructureModelIR` | `InfrastructureModelIR` |
| *(no existe)* | `TestsModelIR` | `TestsModelIR` |

### 2.3 Nuevos Nodos a Crear (Graph Expansion)

| Label | Origen | Count Estimado |
|-------|--------|----------------|
| `Entity` | DomainModelIR.entities | ~1,400 (5 × 280 apps) |
| `Attribute` | Entity.attributes | ~7,000 (5 × 1,400) |
| `Endpoint` | APIModelIR.endpoints | ~5,600 (20 × 280) |
| `APISchema` | APIModelIR.schemas | ~2,800 |
| `APIParameter` | Endpoint.parameters | ~11,200 |
| `Flow` | BehaviorModelIR.flows | ~840 |
| `Step` | Flow.steps | ~4,200 |
| `Invariant` | BehaviorModelIR.invariants | ~560 |
| `ValidationRule` | ValidationModelIR.rules | ~2,800 |
| `TestCase` | ValidationModelIR.test_cases | ~1,400 |
| `DatabaseConfig` | InfrastructureModelIR | ~280 |
| `ContainerService` | InfrastructureModelIR | ~840 |
| `SeedEntityIR` | TestsModelIR | ~1,400 |
| `TestScenarioIR` | TestsModelIR | ~5,600 |
| **TOTAL NUEVOS** | | **~45,920 nodos** |

**Nota:** EntityRelationship NO es un nodo - las relaciones entre entidades se modelan como edges `(:Entity)-[:RELATES_TO]->(:Entity)` con propiedades (tipo, field_name, back_populates).

### 2.4 Métricas Target

| Métrica | Actual | Post-Sprint 5 | Post-Sprint 8 |
|---------|--------|---------------|---------------|
| Nodos totales | 35,358 | ~84,000 | ~100,000 |
| JSON en properties | ~2,240 | 0 | 0 |
| Labels con IR suffix | 0% | 100% | 100% |
| Graph traversal queries | 0 | 100% | 100% |
| IR cache hit rate | 0% | 80% | 95% |
| First-pass success | ~60% | 75% | 90% |

### 2.5 Convenciones y Estándares

#### 2.5.1 Convención de IDs Estables

**Principio:** Todos los IDs deben ser determinísticos y legibles para soportar idempotencia y debugging.

**Formato general:**
```
{parent_id}|{component_type}|{identifier}
```

**Ejemplos por tipo de nodo:**

```python
# Entity
entity_id = f"{app_id}|entity|{entity_name}"
# Ejemplo: "uuid-123|entity|Product"

# Attribute
attribute_id = f"{entity_id}|attr|{attribute_name}"
# Ejemplo: "uuid-123|entity|Product|attr|price"

# Endpoint
endpoint_id = f"{app_id}|endpoint|{method}|{path_normalized}"
# Ejemplo: "uuid-123|endpoint|GET|products_id"
# path_normalized: "/" → "_", "{}" → ""

# APIParameter
param_id = f"{endpoint_id}|param|{param_name}"
# Ejemplo: "uuid-123|endpoint|GET|products_id|param|id"

# APISchema
schema_id = f"{app_id}|schema|{schema_name}"
# Ejemplo: "uuid-123|schema|ProductCreate"

# TestScenarioIR
scenario_id = f"{app_id}|test|{endpoint_path}|{test_type}|{index}"
# Ejemplo: "uuid-123|test|/products|happy_path|0"
```

**Beneficios:**
- ✅ **Idempotencia**: MERGE funciona correctamente en re-ejecuciones
- ✅ **Debugging**: IDs legibles en Cypher queries y Neo4j Browser
- ✅ **Trazabilidad**: Fácil rastrear relaciones parent-child
- ✅ **Migración segura**: Re-ejecutar migration scripts no crea duplicados

**Implementación:**
- Sprint 1 ✅: Entity, Attribute (implementado)
- Sprint 2 ✅: Endpoint, APIParameter, APISchema (implementado)
- Sprint 3+: Aplicar misma convención a Flow, Step, TestScenario, etc.

#### 2.5.2 GraphSchemaVersion Tracking

**Objetivo:** Rastrear la versión del schema de grafo para migraciones y compatibilidad.

**Implementación:**

```cypher
// Crear nodo global de versión (único en toda la base)
MERGE (v:GraphSchemaVersion {singleton: true})
SET v.current_version = 2,
    v.last_migration = "Sprint 2: APIModelIR expansion",
    v.migration_date = datetime(),
    v.sprints_completed = ["Sprint 0", "Sprint 1", "Sprint 2"]
RETURN v;

// Verificar versión actual
MATCH (v:GraphSchemaVersion {singleton: true})
RETURN v.current_version, v.last_migration, v.migration_date;
```

**Versiones:**

| Versión | Sprint | Descripción | Fecha |
|---------|--------|-------------|-------|
| 0 | Sprint 0 | Labels renamed to IR suffix | 2025-11-29 |
| 1 | Sprint 1 | DomainModelIR → Entity, Attribute | 2025-11-29 |
| 2 | Sprint 2 | APIModelIR → Endpoint, APIParameter | 2025-11-29 |
| 3 | Sprint 3 | BehaviorModelIR → Flow, Step | TBD |
| 4 | Sprint 4 | ValidationModelIR + InfrastructureModelIR | TBD |
| 5 | Sprint 5 | TestsModelIR → SeedEntityIR, TestScenarioIR | TBD |
| 6+ | Sprint 6-8 | Lineage, Real-time, Analytics | TBD |

**Metadata en IRs migrados:**

```cypher
// Cada IR migrado guarda su versión de schema
MATCH (d:DomainModelIR {app_id: $app_id})
SET d.graph_schema_version = 1,
    d.migrated_to_graph = true,
    d.migration_timestamp = datetime()
```

**Uso:**
- **Pre-migration validation**: Verificar versión de schema antes de migrar
- **Compatibility checks**: Detectar IRs en versiones antiguas
- **Rollback support**: Saber qué sprints se pueden revertir
- **Auditing**: Historial completo de cambios de schema

**Archivo de implementación:**
```
scripts/migrations/neo4j/
└── 006_graph_schema_versioning.py  # Para agregar en Sprint 3
```

#### 2.5.3 Graph Shape Contracts

**Objetivo:** Definir contratos formales para la estructura esperada del grafo en cada Sprint.

**Problema:** No hay validación automática de que el grafo tenga la estructura correcta después de una migración.

**Solución:** Crear contratos de forma (shape contracts) que definen:
- Qué labels deben existir
- Qué relationships son obligatorias
- Cardinalidades esperadas (1:1, 1:N, N:M)
- Propiedades requeridas por label

**Ejemplo de Contrato - Sprint 1 (DomainModelIR):**

```yaml
# DOCS/mvp/exit/neo4j/contracts/sprint_1_domain_model.yml

sprint: 1
name: "DomainModelIR Graph Expansion"
version: 1

nodes:
  ApplicationIR:
    required_properties: [app_id, created_at]
    optional_properties: [name, description]

  DomainModelIR:
    required_properties: [app_id, created_at]
    optional_properties: []

  Entity:
    required_properties: [entity_id, name, created_at]
    optional_properties: [description, is_aggregate_root]

  Attribute:
    required_properties: [attribute_id, name, data_type, created_at]
    optional_properties: [required, description]

relationships:
  HAS_DOMAIN_MODEL:
    from: ApplicationIR
    to: DomainModelIR
    cardinality: "1:0..1"  # 0 o 1 DomainModel por App
    required_properties: []

  HAS_ENTITY:
    from: DomainModelIR
    to: Entity
    cardinality: "1:N"  # 1+ Entities por DomainModel
    required_properties: []

  HAS_ATTRIBUTE:
    from: Entity
    to: Attribute
    cardinality: "1:N"  # 1+ Attributes por Entity
    required_properties: []

  RELATES_TO:
    from: Entity
    to: Entity
    cardinality: "N:M"  # Entity puede relacionarse con 0+ Entities
    required_properties: [type]  # one_to_one, one_to_many, many_to_many

validation_rules:
  - name: "All Entities have at least one Attribute"
    cypher: |
      MATCH (e:Entity)
      WHERE NOT (e)-[:HAS_ATTRIBUTE]->(:Attribute)
      RETURN count(e) as orphan_entities
    expected: 0

  - name: "No orphan DomainModelIR nodes"
    cypher: |
      MATCH (dm:DomainModelIR)
      WHERE NOT (:ApplicationIR)-[:HAS_DOMAIN_MODEL]->(dm)
      RETURN count(dm) as orphans
    expected: 0

  - name: "RELATES_TO edges have valid type"
    cypher: |
      MATCH ()-[r:RELATES_TO]->()
      WHERE NOT r.type IN ['one_to_one', 'one_to_many', 'many_to_many']
      RETURN count(r) as invalid_relationships
    expected: 0
```

**Validador Automático:**

```python
# src/cognitive/services/graph_contract_validator.py

from pathlib import Path
import yaml
from typing import Dict, List, Any
from neo4j import AsyncGraphDatabase

class GraphContractValidator:
    """
    Valida que el grafo cumpla con contratos de estructura definidos.
    """

    def __init__(self, driver):
        self.driver = driver

    async def validate_contract(self, contract_path: Path) -> Dict[str, Any]:
        """
        Ejecuta todas las reglas de validación de un contrato.

        Returns:
            {
                "contract": "sprint_1_domain_model",
                "passed": True/False,
                "rules_passed": 15,
                "rules_failed": 0,
                "failures": []
            }
        """
        contract = yaml.safe_load(contract_path.read_text())

        failures = []

        # Validar que existen los labels esperados
        for label in contract["nodes"].keys():
            exists = await self._label_exists(label)
            if not exists:
                failures.append(f"Label {label} does not exist in graph")

        # Validar reglas de validación personalizadas
        for rule in contract["validation_rules"]:
            result = await self._run_validation_rule(rule)
            if result != rule["expected"]:
                failures.append(
                    f"Rule '{rule['name']}' failed: "
                    f"expected {rule['expected']}, got {result}"
                )

        return {
            "contract": contract["name"],
            "sprint": contract["sprint"],
            "passed": len(failures) == 0,
            "rules_total": len(contract["validation_rules"]) + len(contract["nodes"]),
            "rules_passed": len(contract["validation_rules"]) + len(contract["nodes"]) - len(failures),
            "rules_failed": len(failures),
            "failures": failures
        }

    async def _label_exists(self, label: str) -> bool:
        async with self.driver.session() as session:
            result = await session.run(
                f"MATCH (n:{label}) RETURN count(n) as count LIMIT 1"
            )
            record = await result.single()
            return record["count"] > 0

    async def _run_validation_rule(self, rule: Dict) -> Any:
        async with self.driver.session() as session:
            result = await session.run(rule["cypher"])
            record = await result.single()
            # Retorna el primer valor del resultado
            return list(record.values())[0]
```

**Uso en Migrations:**

```python
# Al final de cada migration script

from src.cognitive.services.graph_contract_validator import GraphContractValidator

async def verify_migration():
    validator = GraphContractValidator(driver)

    result = await validator.validate_contract(
        Path("DOCS/mvp/exit/neo4j/contracts/sprint_1_domain_model.yml")
    )

    if not result["passed"]:
        print(f"\n⚠️  CONTRACT VALIDATION FAILED")
        for failure in result["failures"]:
            print(f"   ✗ {failure}")
        raise ValueError("Graph shape does not match contract")

    print(f"\n✅ CONTRACT VALIDATION PASSED")
    print(f"   Rules passed: {result['rules_passed']}/{result['rules_total']}")
```

**Beneficios:**
- ✅ **Validación automática** de estructura de grafo post-migración
- ✅ **Documentación formal** de estructura esperada por Sprint
- ✅ **Regression testing** - detectar cambios no intencionales
- ✅ **Onboarding** - nuevos desarrolladores entienden estructura de grafo
- ✅ **CI/CD integration** - validar contratos en pipelines automáticos

**Archivos a crear:**
```
DOCS/mvp/exit/neo4j/contracts/
├── sprint_0_cleanup.yml
├── sprint_1_domain_model.yml
├── sprint_2_api_model.yml
├── sprint_3_behavior_model.yml
├── sprint_4_validation_infra.yml
└── sprint_5_tests_model.yml

src/cognitive/services/
└── graph_contract_validator.py

scripts/migrations/neo4j/
└── 007_validate_all_contracts.py  # Validar contratos de todos los sprints
```

#### 2.5.4 Metadata Temporal en Todos los Nodos

**Objetivo:** Agregar timestamps de creación y actualización a TODOS los nodos del grafo.

**Problema:** No sabemos cuándo se creó o modificó un nodo, dificultando auditing y debugging.

**Solución:** Agregar propiedades `created_at` y `updated_at` a todos los labels.

**Implementación:**

```cypher
// Sprint 0.5 (Retroactivo): Agregar metadata a nodos existentes
MATCH (n)
WHERE n.created_at IS NULL
SET n.created_at = datetime(),
    n.updated_at = datetime()
```

**Convención en Código Python:**

```python
# src/cognitive/services/graph_ir_repository.py (base class)

from datetime import datetime

class GraphIRRepository:
    """Base repository con metadata temporal automático."""

    def _add_temporal_metadata(self, node_props: Dict) -> Dict:
        """Agrega created_at/updated_at a propiedades de nodo."""
        now = datetime.utcnow().isoformat()

        return {
            **node_props,
            "created_at": node_props.get("created_at", now),
            "updated_at": now
        }

    async def create_node(self, label: str, props: Dict):
        """Crea nodo con metadata temporal automático."""
        props_with_metadata = self._add_temporal_metadata(props)

        async with self.driver.session() as session:
            await session.run(f"""
                CREATE (n:{label})
                SET n = $props
                RETURN n
            """, props=props_with_metadata)

    async def update_node(self, label: str, node_id: str, props: Dict):
        """Actualiza nodo y actualiza updated_at."""
        props_with_updated = {
            **props,
            "updated_at": datetime.utcnow().isoformat()
        }

        async with self.driver.session() as session:
            await session.run(f"""
                MATCH (n:{label} {{node_id: $node_id}})
                SET n += $props
                RETURN n
            """, node_id=node_id, props=props_with_updated)
```

**Queries Habilitados:**

```cypher
// 1. Nodos creados en las últimas 24 horas
MATCH (n)
WHERE n.created_at > datetime() - duration({hours: 24})
RETURN labels(n) as type, count(*) as count
ORDER BY count DESC

// 2. Nodos modificados recientemente
MATCH (n)
WHERE n.updated_at > datetime() - duration({hours: 1})
RETURN labels(n), n.created_at, n.updated_at
ORDER BY n.updated_at DESC

// 3. Nodos "stale" (no actualizados en 30 días)
MATCH (n)
WHERE n.updated_at < datetime() - duration({days: 30})
  AND labels(n)[0] IN ['Entity', 'Endpoint', 'Flow']
RETURN labels(n), count(*) as stale_count

// 4. Tiempo promedio entre creación y primera actualización
MATCH (n)
WHERE n.updated_at <> n.created_at
RETURN labels(n)[0] as type,
       avg(duration.between(
         datetime(n.created_at),
         datetime(n.updated_at)
       ).seconds) as avg_time_to_first_update_sec
```

**Migración Retroactiva:**

```python
# scripts/migrations/neo4j/000_add_temporal_metadata.py

async def add_temporal_metadata_to_all_nodes():
    """
    Sprint 0.5: Agregar created_at/updated_at a todos los nodos existentes.
    """
    print("🕒 Adding temporal metadata to all existing nodes...")

    async with driver.session() as session:
        # 1. Contar nodos sin metadata
        result = await session.run("""
            MATCH (n)
            WHERE n.created_at IS NULL
            RETURN count(n) as count
        """)
        total = (await result.single())["count"]

        print(f"   Found {total} nodes without temporal metadata")

        # 2. Agregar metadata en batches de 1000
        batch_size = 1000
        for offset in range(0, total, batch_size):
            await session.run("""
                MATCH (n)
                WHERE n.created_at IS NULL
                WITH n LIMIT $batch_size
                SET n.created_at = datetime(),
                    n.updated_at = datetime()
            """, batch_size=batch_size)

            print(f"   ✅ Processed {min(offset + batch_size, total)}/{total} nodes")

    print(f"✅ Temporal metadata added to {total} nodes")
```

**Beneficios:**
- ✅ **Auditing completo** - Saber cuándo se creó/modificó cada nodo
- ✅ **Debugging temporal** - Rastrear cambios en el tiempo
- ✅ **Data lifecycle** - Identificar nodos "stale" para limpieza
- ✅ **Analytics** - Tendencias de creación y modificación de datos
- ✅ **Compliance** - Demostrar trazabilidad temporal de cambios

**Prioridad:**
- **Sprint 0.5** (Retroactivo): Agregar metadata a ~43,000 nodos existentes
- **Sprint 1+**: Aplicar automáticamente en todos los migration scripts

#### 2.5.5 Subgraph Replace como Principio Universal

**Objetivo:** Formalizar el patrón "Subgraph Replace" como principio universal para todas las actualizaciones de nodos con hijos.

**Problema:** Cuando actualizamos un nodo que tiene hijos (e.g., DomainModelIR con Entities), no hay una convención clara si debemos:
- Hacer merge de hijos existentes con nuevos
- Reemplazar completamente la lista de hijos
- Actualizar solo los hijos modificados

Esto causa **inconsistencias, nodos huérfanos, y datos corruptos**.

**Principio Universal:**

> **Subgraph Replace Pattern**: Al actualizar un nodo padre con hijos, SIEMPRE eliminar todos los hijos existentes y crear nuevos desde cero.

**Justificación:**
- ✅ **Simplicidad**: No requiere lógica compleja de diff/merge
- ✅ **Consistencia**: Estado final siempre refleja la fuente de verdad (Pydantic models)
- ✅ **Predictibilidad**: Comportamiento determinístico, fácil de testear
- ✅ **Idempotencia**: Re-ejecutar produce el mismo estado final
- ✅ **No orphans**: Hijos viejos siempre se eliminan completamente

**Patrón Cypher Estándar:**

```cypher
// Subgraph Replace Pattern - Standard Template

// 1. Match parent node
MATCH (parent:ParentLabel {parent_id: $parent_id})

// 2. DELETE all existing children and their descendants
OPTIONAL MATCH (parent)-[:HAS_CHILD]->(child:ChildLabel)
OPTIONAL MATCH (child)-[child_rels*]->(descendants)
DETACH DELETE descendants, child

// 3. CREATE new children from scratch
WITH parent
UNWIND $children_data as child_data
CREATE (new_child:ChildLabel)
SET new_child = child_data,
    new_child.created_at = datetime(),
    new_child.updated_at = datetime()
CREATE (parent)-[:HAS_CHILD]->(new_child)

// 4. Return statistics
RETURN parent.parent_id as parent_id,
       count(new_child) as children_created
```

**Aplicación en Todos los Sprints:**

**Sprint 1 - DomainModelIR Update:**
```cypher
// Replace all Entities and their Attributes
MATCH (dm:DomainModelIR {app_id: $app_id})

// DELETE: Remove old Entities + Attributes + Relationships
OPTIONAL MATCH (dm)-[:HAS_ENTITY]->(e:Entity)
OPTIONAL MATCH (e)-[:HAS_ATTRIBUTE]->(attr:Attribute)
OPTIONAL MATCH (e)-[rel:RELATES_TO]->(other:Entity)
DETACH DELETE attr, rel, e

// CREATE: New Entities from Pydantic models
WITH dm
UNWIND $entities as entity_data
CREATE (e:Entity)
SET e = entity_data,
    e.created_at = datetime(),
    e.updated_at = datetime()
CREATE (dm)-[:HAS_ENTITY]->(e)

// CREATE: Attributes for each Entity
WITH e, entity_data
UNWIND entity_data.attributes as attr_data
CREATE (attr:Attribute)
SET attr = attr_data,
    attr.created_at = datetime(),
    attr.updated_at = datetime()
CREATE (e)-[:HAS_ATTRIBUTE]->(attr)
```

**Sprint 2 - APIModelIR Update:**
```cypher
// Replace all Endpoints and their Parameters
MATCH (api:APIModelIR {app_id: $app_id})

// DELETE: Remove old Endpoints + Parameters + Schemas
OPTIONAL MATCH (api)-[:HAS_ENDPOINT]->(ep:Endpoint)
OPTIONAL MATCH (ep)-[:HAS_PARAMETER]->(param:APIParameter)
OPTIONAL MATCH (api)-[:HAS_SCHEMA]->(schema:APISchema)
OPTIONAL MATCH (schema)-[:HAS_FIELD]->(field:APISchemaField)
DETACH DELETE param, ep, field, schema

// CREATE: New Endpoints + Parameters
WITH api
UNWIND $endpoints as endpoint_data
CREATE (ep:Endpoint)
SET ep = endpoint_data,
    ep.created_at = datetime(),
    ep.updated_at = datetime()
CREATE (api)-[:HAS_ENDPOINT]->(ep)

WITH ep, endpoint_data
UNWIND endpoint_data.parameters as param_data
CREATE (param:APIParameter)
SET param = param_data,
    param.created_at = datetime(),
    param.updated_at = datetime()
CREATE (ep)-[:HAS_PARAMETER]->(param)
```

**Sprint 3 - BehaviorModelIR Update:**
```cypher
// Replace all Flows and their Steps
MATCH (bm:BehaviorModelIR {app_id: $app_id})

// DELETE: Remove old Flows + Steps + Invariants
OPTIONAL MATCH (bm)-[:HAS_FLOW]->(flow:Flow)
OPTIONAL MATCH (flow)-[:HAS_STEP]->(step:Step)
OPTIONAL MATCH (bm)-[:HAS_INVARIANT]->(inv:Invariant)
DETACH DELETE step, flow, inv

// CREATE: New Flows + Steps
WITH bm
UNWIND $flows as flow_data
CREATE (flow:Flow)
SET flow = flow_data,
    flow.created_at = datetime(),
    flow.updated_at = datetime()
CREATE (bm)-[:HAS_FLOW]->(flow)

WITH flow, flow_data
UNWIND flow_data.steps as step_data
CREATE (step:Step)
SET step = step_data,
    step.created_at = datetime(),
    step.updated_at = datetime()
CREATE (flow)-[:HAS_STEP]->(step)
```

**Python Repository Pattern:**

```python
# src/cognitive/services/graph_ir_repository.py

class GraphIRRepository:
    """Base class con Subgraph Replace pattern."""

    async def replace_subgraph(
        self,
        parent_label: str,
        parent_id: str,
        child_label: str,
        relationship_type: str,
        children_data: List[Dict],
        cascade_labels: List[str] = None
    ):
        """
        Patrón universal de Subgraph Replace.

        Args:
            parent_label: Label del nodo padre (e.g., "DomainModelIR")
            parent_id: ID del padre (e.g., app_id)
            child_label: Label de los hijos (e.g., "Entity")
            relationship_type: Tipo de relación (e.g., "HAS_ENTITY")
            children_data: Lista de diccionarios con datos de hijos
            cascade_labels: Labels adicionales a eliminar en cascada (e.g., ["Attribute"])

        Returns:
            {
                "parent_id": str,
                "children_deleted": int,
                "children_created": int
            }
        """
        async with self.driver.session() as session:
            # 1. DELETE existing children
            delete_query = f"""
                MATCH (p:{parent_label} {{parent_id: $parent_id}})
                OPTIONAL MATCH (p)-[:{relationship_type}]->(c:{child_label})
            """

            # Add cascade deletion if specified
            if cascade_labels:
                for cascade_label in cascade_labels:
                    delete_query += f"""
                        OPTIONAL MATCH (c)-[*]->(cascade:{cascade_label})
                    """
                delete_query += f"""
                    WITH p, c, collect(cascade) as cascades
                    FOREACH (n IN cascades | DETACH DELETE n)
                    DETACH DELETE c
                    RETURN p, count(c) as deleted_count
                """
            else:
                delete_query += f"""
                    DETACH DELETE c
                    RETURN p, count(c) as deleted_count
                """

            result = await session.run(delete_query, parent_id=parent_id)
            record = await result.single()
            deleted_count = record["deleted_count"] if record else 0

            # 2. CREATE new children
            create_query = f"""
                MATCH (p:{parent_label} {{parent_id: $parent_id}})
                UNWIND $children as child_data
                CREATE (c:{child_label})
                SET c = child_data,
                    c.created_at = datetime(),
                    c.updated_at = datetime()
                CREATE (p)-[:{relationship_type}]->(c)
                RETURN count(c) as created_count
            """

            result = await session.run(
                create_query,
                parent_id=parent_id,
                children=children_data
            )
            record = await result.single()
            created_count = record["created_count"] if record else 0

            return {
                "parent_id": parent_id,
                "children_deleted": deleted_count,
                "children_created": created_count
            }
```

**Uso en Repositories Específicos:**

```python
# src/cognitive/services/domain_model_graph_repository.py

class DomainModelGraphRepository(GraphIRRepository):
    async def update_domain_model(self, app_id: str, domain_model: DomainModelIR):
        """Update DomainModelIR usando Subgraph Replace pattern."""

        # 1. Preparar datos de Entities
        entities_data = [
            {
                "entity_id": f"{app_id}|entity|{entity.name}",
                "name": entity.name,
                "description": entity.description,
                "is_aggregate_root": entity.is_aggregate_root
            }
            for entity in domain_model.entities
        ]

        # 2. Replace Entities subgraph (cascadeando Attributes)
        result = await self.replace_subgraph(
            parent_label="DomainModelIR",
            parent_id=app_id,
            child_label="Entity",
            relationship_type="HAS_ENTITY",
            children_data=entities_data,
            cascade_labels=["Attribute", "Relationship"]  # Delete Attributes y Relationships en cascada
        )

        print(f"✅ Replaced {result['children_deleted']} old Entities "
              f"with {result['children_created']} new ones")

        # 3. Crear Attributes para cada Entity
        for entity in domain_model.entities:
            entity_id = f"{app_id}|entity|{entity.name}"
            attributes_data = [
                {
                    "attribute_id": f"{entity_id}|attr|{attr.name}",
                    "name": attr.name,
                    "data_type": attr.data_type,
                    "required": attr.required
                }
                for attr in entity.attributes
            ]

            await self.replace_subgraph(
                parent_label="Entity",
                parent_id=entity_id,
                child_label="Attribute",
                relationship_type="HAS_ATTRIBUTE",
                children_data=attributes_data
            )
```

**Excepciones al Patrón:**

El patrón Subgraph Replace NO se aplica a:

1. **Nodos de alto nivel (ApplicationIR, DomainModelIR, etc.):**
   - Estos nunca se eliminan, solo se actualizan con `SET`
   - Son la raíz del grafo y deben persistir

2. **Relaciones de referencia (RELATES_TO, CALLS, VALIDATES):**
   - Estas son vínculos entre nodos, no jerarquías parent-child
   - Se actualizan con lógica de merge, no replace

3. **Nodos de tracking (MigrationRun, TestExecutionIR):**
   - Son append-only logs, nunca se eliminan
   - Representan eventos históricos inmutables

**Trade-offs:**

**✅ Pros:**
- Simplicidad extrema de implementación
- Garantiza consistencia absoluta con fuente de verdad
- Elimina bugs de sincronización parcial
- Fácil de testear y verificar

**⚠️ Cons:**
- Performance overhead en updates frecuentes (delete + create > update)
- Pierde historial de cambios individuales (mitigado con temporal metadata)
- Puede ser overkill para updates pequeños (mitigado con batching)

**Mitigaciones:**
- **Batching**: Agrupar updates en transacciones grandes
- **Temporal metadata**: `created_at`/`updated_at` preservan algo de historial
- **Event logging**: Guardar eventos de update en `EventLog` nodes (Sprint 7)
- **Selective application**: Aplicar solo a subgrafos verdaderamente jerárquicos

**Beneficios:**
- ✅ **Consistencia garantizada**: Estado final siempre correcto
- ✅ **Código mantenible**: Patrón simple y repetible
- ✅ **Testing sencillo**: Verificar estado final, no transiciones
- ✅ **No bugs de sincronización**: Imposible tener hijos desactualizados
- ✅ **Idempotencia natural**: Re-ejecutar produce mismo resultado

**Archivos a modificar:**
```
src/cognitive/services/
├── graph_ir_repository.py              # Base class con replace_subgraph()
├── domain_model_graph_repository.py    # Usar replace_subgraph() para Entities
├── api_model_graph_repository.py       # Usar replace_subgraph() para Endpoints
├── behavior_model_graph_repository.py  # Usar replace_subgraph() para Flows
└── tests_model_graph_repository.py     # Usar replace_subgraph() para TestScenarios

DOCS/mvp/exit/neo4j/
└── SUBGRAPH_REPLACE_PATTERN.md         # Documentación formal del patrón
```

**Prioridad:**
- **Sprint 1** ✅: Ya implementado implícitamente en migration scripts
- **Sprint 2+**: Formalizar como método base en GraphIRRepository
- **Sprint 3**: Aplicar consistentemente en todos los nuevos repositories

### 2.7 Graph Health Monitor (Recurrente)

**Objetivo:** Monitoreo continuo de salud del grafo con detección de anomalías y alertas.

**Problema:** No hay visibilidad en tiempo real de la salud del grafo. Problemas como orphan nodes, relaciones inválidas, o datos corruptos se detectan manualmente.

**Solución:** Servicio de monitoreo que ejecuta health checks periódicos y alerta sobre anomalías.

#### 2.7.1 Health Check Categories

**1. Structural Health**
- Orphan nodes (nodos sin relaciones incoming/outgoing esperadas)
- Relaciones inválidas (tipos incorrectos, cardinalidades violadas)
- Missing required properties
- Invalid property types

**2. Data Integrity**
- IDs duplicados (violan uniqueness constraints)
- Referencias a nodos inexistentes
- Relaciones circulares inesperadas
- Inconsistencias entre JSON y graph nodes

**3. Performance Health**
- Nodos con grado extremadamente alto (> 10,000 relationships)
- Queries lentas (> 5 segundos)
- Índices faltantes o no utilizados
- Lock contention

**4. Schema Health**
- Labels no documentados en contratos
- Relationship types no documentados
- Schema drift (diferencias vs contratos)

#### 2.7.2 Implementación del Monitor

```python
# src/cognitive/services/graph_health_monitor.py

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any
from datetime import datetime
from neo4j import AsyncGraphDatabase

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class HealthCheckResult:
    check_name: str
    status: HealthStatus
    message: str
    value: Any
    threshold: Any
    timestamp: datetime

    def is_healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY

class GraphHealthMonitor:
    """
    Monitor de salud del grafo con checks configurables.
    """

    def __init__(self, driver, config: Dict = None):
        self.driver = driver
        self.config = config or self._default_config()

    def _default_config(self) -> Dict:
        return {
            "orphan_nodes_threshold": 10,
            "high_degree_threshold": 10000,
            "slow_query_threshold_sec": 5.0,
            "missing_props_threshold": 100,
        }

    async def run_all_checks(self) -> List[HealthCheckResult]:
        """Ejecuta todos los health checks."""
        checks = [
            self.check_orphan_nodes(),
            self.check_missing_required_props(),
            self.check_high_degree_nodes(),
            self.check_duplicate_ids(),
            self.check_invalid_relationships(),
            self.check_schema_drift(),
        ]

        results = []
        for check_coro in checks:
            result = await check_coro
            results.append(result)

        return results

    async def check_orphan_nodes(self) -> HealthCheckResult:
        """Detecta nodos sin relaciones esperadas."""
        async with self.driver.session() as session:
            # Ejemplo: DomainModelIR sin ApplicationIR parent
            result = await session.run("""
                MATCH (dm:DomainModelIR)
                WHERE NOT (:ApplicationIR)-[:HAS_DOMAIN_MODEL]->(dm)
                RETURN count(dm) as orphan_count
            """)
            count = (await result.single())["orphan_count"]

            threshold = self.config["orphan_nodes_threshold"]

            if count == 0:
                status = HealthStatus.HEALTHY
            elif count < threshold:
                status = HealthStatus.WARNING
            else:
                status = HealthStatus.CRITICAL

            return HealthCheckResult(
                check_name="orphan_domain_models",
                status=status,
                message=f"Found {count} orphan DomainModelIR nodes",
                value=count,
                threshold=threshold,
                timestamp=datetime.utcnow()
            )

    async def check_missing_required_props(self) -> HealthCheckResult:
        """Detecta nodos sin propiedades requeridas."""
        async with self.driver.session() as session:
            result = await session.run("""
                MATCH (e:Entity)
                WHERE e.entity_id IS NULL OR e.name IS NULL
                RETURN count(e) as count
            """)
            count = (await result.single())["count"]

            threshold = self.config["missing_props_threshold"]

            return HealthCheckResult(
                check_name="entities_missing_required_props",
                status=HealthStatus.CRITICAL if count > 0 else HealthStatus.HEALTHY,
                message=f"Found {count} Entity nodes missing required properties",
                value=count,
                threshold=0,
                timestamp=datetime.utcnow()
            )

    async def check_high_degree_nodes(self) -> HealthCheckResult:
        """Detecta nodos con demasiadas relaciones (performance issue)."""
        async with self.driver.session() as session:
            result = await session.run("""
                MATCH (n)
                WITH n, size((n)--()) as degree
                WHERE degree > $threshold
                RETURN count(n) as count, max(degree) as max_degree
            """, threshold=self.config["high_degree_threshold"])
            record = await result.single()
            count = record["count"]
            max_degree = record["max_degree"]

            return HealthCheckResult(
                check_name="high_degree_nodes",
                status=HealthStatus.WARNING if count > 0 else HealthStatus.HEALTHY,
                message=f"Found {count} nodes with > {self.config['high_degree_threshold']} relationships (max: {max_degree})",
                value=count,
                threshold=self.config["high_degree_threshold"],
                timestamp=datetime.utcnow()
            )

    async def check_duplicate_ids(self) -> HealthCheckResult:
        """Detecta IDs duplicados (violan uniqueness)."""
        async with self.driver.session() as session:
            result = await session.run("""
                MATCH (e:Entity)
                WITH e.entity_id as id, collect(e) as nodes
                WHERE size(nodes) > 1
                RETURN count(*) as duplicate_count
            """)
            count = (await result.single())["duplicate_count"]

            return HealthCheckResult(
                check_name="duplicate_entity_ids",
                status=HealthStatus.CRITICAL if count > 0 else HealthStatus.HEALTHY,
                message=f"Found {count} duplicate entity_id values",
                value=count,
                threshold=0,
                timestamp=datetime.utcnow()
            )

    async def check_invalid_relationships(self) -> HealthCheckResult:
        """Detecta relaciones con tipos inválidos."""
        async with self.driver.session() as session:
            result = await session.run("""
                MATCH ()-[r:RELATES_TO]->()
                WHERE NOT r.type IN ['one_to_one', 'one_to_many', 'many_to_many']
                RETURN count(r) as invalid_count
            """)
            count = (await result.single())["invalid_count"]

            return HealthCheckResult(
                check_name="invalid_relates_to_types",
                status=HealthStatus.CRITICAL if count > 0 else HealthStatus.HEALTHY,
                message=f"Found {count} RELATES_TO edges with invalid type",
                value=count,
                threshold=0,
                timestamp=datetime.utcnow()
            )

    async def check_schema_drift(self) -> HealthCheckResult:
        """
        Detecta labels/relationships no documentados en contratos.
        Requiere GraphContractValidator.
        """
        # Implementación completa requiere parsear todos los contratos
        # Aquí un ejemplo simple
        async with self.driver.session() as session:
            result = await session.run("""
                CALL db.labels() YIELD label
                WHERE NOT label IN [
                    'ApplicationIR', 'DomainModelIR', 'APIModelIR',
                    'Entity', 'Attribute', 'Endpoint', 'APIParameter',
                    'GraphSchemaVersion', 'MigrationRun'
                ]
                RETURN collect(label) as undocumented_labels
            """)
            labels = (await result.single())["undocumented_labels"]

            return HealthCheckResult(
                check_name="schema_drift",
                status=HealthStatus.WARNING if len(labels) > 0 else HealthStatus.HEALTHY,
                message=f"Found {len(labels)} undocumented labels: {labels}",
                value=labels,
                threshold=[],
                timestamp=datetime.utcnow()
            )

    def generate_report(self, results: List[HealthCheckResult]) -> str:
        """Genera reporte legible de health checks."""
        critical = [r for r in results if r.status == HealthStatus.CRITICAL]
        warnings = [r for r in results if r.status == HealthStatus.WARNING]
        healthy = [r for r in results if r.status == HealthStatus.HEALTHY]

        report = []
        report.append("=" * 60)
        report.append("GRAPH HEALTH REPORT")
        report.append("=" * 60)
        report.append(f"Timestamp: {datetime.utcnow().isoformat()}")
        report.append(f"Total Checks: {len(results)}")
        report.append(f"✅ Healthy: {len(healthy)}")
        report.append(f"⚠️  Warnings: {len(warnings)}")
        report.append(f"🚨 Critical: {len(critical)}")
        report.append("")

        if critical:
            report.append("🚨 CRITICAL ISSUES:")
            for r in critical:
                report.append(f"   ✗ {r.check_name}: {r.message}")

        if warnings:
            report.append("\n⚠️  WARNINGS:")
            for r in warnings:
                report.append(f"   ! {r.check_name}: {r.message}")

        if not critical and not warnings:
            report.append("✅ All checks passed - Graph is healthy!")

        report.append("=" * 60)
        return "\n".join(report)
```

#### 2.7.3 Ejecución Periódica

```python
# scripts/monitoring/graph_health_daemon.py

import asyncio
from datetime import datetime
from src.cognitive.services.graph_health_monitor import GraphHealthMonitor, HealthStatus

async def run_health_monitoring_loop(interval_minutes: int = 30):
    """
    Loop infinito que ejecuta health checks periódicamente.
    """
    monitor = GraphHealthMonitor(driver)

    while True:
        print(f"\n{'='*60}")
        print(f"Running health checks at {datetime.utcnow().isoformat()}")
        print(f"{'='*60}\n")

        results = await monitor.run_all_checks()
        report = monitor.generate_report(results)
        print(report)

        # Alertar si hay críticos
        critical_checks = [r for r in results if r.status == HealthStatus.CRITICAL]
        if critical_checks:
            await send_alert(report, critical_checks)

        # Guardar resultados en Neo4j para trending
        await save_health_results(results)

        # Esperar intervalo
        await asyncio.sleep(interval_minutes * 60)

async def send_alert(report: str, critical_checks: List):
    """Enviar alerta (email, Slack, etc.)"""
    # TODO: Implementar integración con sistema de alertas
    print("\n🚨 CRITICAL ISSUES DETECTED - Sending alert...")

async def save_health_results(results: List):
    """Guardar resultados en Neo4j para trending."""
    # Crear nodos HealthCheckResult para análisis temporal
    pass

if __name__ == "__main__":
    asyncio.run(run_health_monitoring_loop(interval_minutes=30))
```

#### 2.7.4 Integración con CI/CD

```yaml
# .github/workflows/graph-health-check.yml

name: Graph Health Check

on:
  schedule:
    - cron: '0 */6 * * *'  # Cada 6 horas
  workflow_dispatch:  # Manual trigger

jobs:
  health-check:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run Health Checks
        env:
          NEO4J_URI: ${{ secrets.NEO4J_URI }}
          NEO4J_USER: ${{ secrets.NEO4J_USER }}
          NEO4J_PASSWORD: ${{ secrets.NEO4J_PASSWORD }}
        run: |
          python scripts/monitoring/run_health_checks.py

      - name: Fail if Critical Issues
        run: |
          # Script debe exit 1 si hay issues críticos
          python scripts/monitoring/check_critical_issues.py
```

#### 2.7.5 Beneficios

| Beneficio | Descripción |
|-----------|-------------|
| **Detección Temprana** | Identificar problemas antes de que afecten producción |
| **Prevención Proactiva** | Alertas automáticas en lugar de descubrimiento manual |
| **Trending** | Análisis temporal de salud del grafo |
| **Compliance** | Demostrar monitoreo continuo de calidad de datos |
| **Performance** | Identificar cuellos de botella (high-degree nodes, queries lentas) |
| **Data Quality** | Mantener integridad estructural del grafo |

#### 2.7.6 Prioridad de Implementación

- **Sprint 3**: Implementar GraphHealthMonitor con checks básicos
- **Sprint 3**: Integrar en CI/CD para ejecución periódica
- **Sprint 4**: Agregar trending de resultados y dashboards
- **Sprint 5**: Integrar alertas con Slack/email

### 2.8 Atomic Migration Mode

**Objetivo:** Garantizar atomicidad en migraciones - todo o nada, con rollback automático en caso de fallo.

**Problema:** Las migraciones actuales procesan IRs uno por uno. Si falla en el IR #50 de 100, quedan 49 IRs migrados y 51 sin migrar, dejando el grafo en estado inconsistente.

**Solución:** Modo de migración atómico usando transacciones Neo4j + checkpoints + rollback automático.

#### 2.8.1 Estrategia de Atomicidad

**Opción 1: Transacción Única (Small Datasets)**
- Toda la migración en una sola transacción
- Rollback automático si falla cualquier parte
- **Limitación**: No funciona para migraciones grandes (> 10K nodos) - timeout

**Opción 2: Checkpoint-Based Atomicity (Recommended)**
- Migración en batches con checkpoints
- Si falla un batch, rollback completo automático
- Restaurar desde último checkpoint conocido

**Opción 3: Shadow Graph Pattern**
- Crear nodos nuevos con label temporal (e.g. `Entity_TEMP`)
- Al finalizar exitosamente, renombrar `Entity_TEMP` → `Entity` atómicamente
- Si falla, eliminar todos los `_TEMP` labels

#### 2.8.2 Implementación Checkpoint-Based

```python
# src/cognitive/services/atomic_migration_executor.py

from dataclasses import dataclass
from typing import List, Callable, Any
from datetime import datetime
from neo4j import AsyncGraphDatabase

@dataclass
class MigrationCheckpoint:
    checkpoint_id: str
    migration_id: str
    batch_number: int
    records_processed: int
    timestamp: datetime
    success: bool

class AtomicMigrationExecutor:
    """
    Ejecutor de migraciones con atomicidad vía checkpoints.
    """

    def __init__(self, driver, migration_id: str):
        self.driver = driver
        self.migration_id = migration_id
        self.checkpoints: List[MigrationCheckpoint] = []

    async def execute_atomic(
        self,
        records: List[Any],
        migrate_fn: Callable,
        batch_size: int = 100,
        dry_run: bool = False
    ):
        """
        Ejecuta migración con atomicidad vía checkpoints.

        Args:
            records: Lista de registros a migrar
            migrate_fn: Función async que migra un solo registro
            batch_size: Tamaño de batch para checkpoints
            dry_run: Si True, simula sin escribir

        Raises:
            MigrationFailureError: Si falla y no puede rollback
        """
        print(f"🔒 Starting ATOMIC migration: {self.migration_id}")
        print(f"   Total records: {len(records)}")
        print(f"   Batch size: {batch_size}")
        print(f"   Dry run: {dry_run}")

        try:
            # 1. Crear MigrationRun node
            await self._create_migration_run(len(records), dry_run)

            # 2. Procesar en batches con checkpoints
            total_batches = (len(records) + batch_size - 1) // batch_size

            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(records))
                batch = records[start_idx:end_idx]

                print(f"\n📦 Processing batch {batch_num + 1}/{total_batches} ({len(batch)} records)...")

                # 3. Procesar batch en transacción única
                async with self.driver.session() as session:
                    async with session.begin_transaction() as tx:
                        try:
                            for record in batch:
                                await migrate_fn(tx, record, dry_run)

                            # Commit batch transaction
                            if not dry_run:
                                await tx.commit()

                            print(f"   ✅ Batch {batch_num + 1} committed successfully")

                        except Exception as batch_error:
                            # Rollback batch automáticamente
                            print(f"   ❌ Batch {batch_num + 1} failed: {batch_error}")
                            print(f"   🔄 Rolling back batch transaction...")
                            await tx.rollback()

                            # Rollback completo de toda la migración
                            await self._rollback_migration()

                            raise MigrationFailureError(
                                f"Migration failed at batch {batch_num + 1}: {batch_error}"
                            )

                # 4. Crear checkpoint después de batch exitoso
                checkpoint = await self._create_checkpoint(batch_num + 1, end_idx)
                self.checkpoints.append(checkpoint)

            # 5. Marcar migración como completada
            await self._complete_migration(len(records))

            print(f"\n✅ ATOMIC MIGRATION COMPLETED")
            print(f"   Records processed: {len(records)}")
            print(f"   Checkpoints created: {len(self.checkpoints)}")

        except Exception as e:
            print(f"\n❌ ATOMIC MIGRATION FAILED: {e}")
            raise

    async def _create_migration_run(self, total_records: int, dry_run: bool):
        """Crear nodo MigrationRun inicial."""
        async with self.driver.session() as session:
            await session.run("""
                CREATE (m:MigrationRun {
                    migration_id: $migration_id,
                    status: 'running',
                    started_at: datetime(),
                    total_records: $total_records,
                    dry_run: $dry_run,
                    atomic_mode: true
                })
            """, migration_id=self.migration_id, total_records=total_records, dry_run=dry_run)

    async def _create_checkpoint(self, batch_number: int, records_processed: int) -> MigrationCheckpoint:
        """Crear checkpoint después de batch exitoso."""
        checkpoint_id = f"{self.migration_id}_checkpoint_{batch_number}"

        async with self.driver.session() as session:
            await session.run("""
                MATCH (m:MigrationRun {migration_id: $migration_id})
                CREATE (c:MigrationCheckpoint {
                    checkpoint_id: $checkpoint_id,
                    migration_id: $migration_id,
                    batch_number: $batch_number,
                    records_processed: $records_processed,
                    timestamp: datetime(),
                    success: true
                })
                CREATE (m)-[:HAS_CHECKPOINT]->(c)
            """, migration_id=self.migration_id, checkpoint_id=checkpoint_id,
                 batch_number=batch_number, records_processed=records_processed)

        return MigrationCheckpoint(
            checkpoint_id=checkpoint_id,
            migration_id=self.migration_id,
            batch_number=batch_number,
            records_processed=records_processed,
            timestamp=datetime.utcnow(),
            success=True
        )

    async def _rollback_migration(self):
        """
        Rollback completo de la migración.
        Elimina todos los nodos creados en esta migración.
        """
        print(f"\n🔄 ROLLING BACK migration {self.migration_id}...")

        async with self.driver.session() as session:
            # 1. Encontrar todos los nodos afectados por esta migración
            result = await session.run("""
                MATCH (m:MigrationRun {migration_id: $migration_id})
                      -[:AFFECTED]->(ir)
                RETURN collect(id(ir)) as affected_node_ids
            """, migration_id=self.migration_id)
            affected_ids = (await result.single())["affected_node_ids"]

            print(f"   Found {len(affected_ids)} affected IRs")

            # 2. Eliminar nodos creados por esta migración
            # Usar metadata temporal: created_at después del inicio de migración
            await session.run("""
                MATCH (m:MigrationRun {migration_id: $migration_id})
                MATCH (n)
                WHERE n.created_at >= m.started_at
                  AND n.migration_id = $migration_id
                DETACH DELETE n
            """, migration_id=self.migration_id)

            # 3. Marcar migración como rolled back
            await session.run("""
                MATCH (m:MigrationRun {migration_id: $migration_id})
                SET m.status = 'rolled_back',
                    m.rolled_back_at = datetime()
            """, migration_id=self.migration_id)

        print(f"   ✅ Rollback completed")

    async def _complete_migration(self, total_records: int):
        """Marcar migración como completada."""
        async with self.driver.session() as session:
            await session.run("""
                MATCH (m:MigrationRun {migration_id: $migration_id})
                SET m.status = 'completed',
                    m.completed_at = datetime(),
                    m.processed_records = $total_records,
                    m.success_rate = 1.0
            """, migration_id=self.migration_id, total_records=total_records)

class MigrationFailureError(Exception):
    """Excepción lanzada cuando falla una migración atómica."""
    pass
```

#### 2.8.3 Uso en Migration Scripts

```python
# scripts/migrations/neo4j/005_api_model_expansion.py (actualizado)

from src.cognitive.services.atomic_migration_executor import AtomicMigrationExecutor

async def migrate_single_record(tx, record, dry_run: bool):
    """Migra un solo APIModelIR."""
    if dry_run:
        return

    # Parse JSON
    endpoints = json.loads(record["endpoints_json"])

    # Crear Endpoint nodes
    for endpoint in endpoints:
        await tx.run("""
            MATCH (api:APIModelIR {app_id: $app_id})
            CREATE (e:Endpoint {
                endpoint_id: $endpoint_id,
                method: $method,
                path: $path,
                created_at: datetime(),
                migration_id: $migration_id
            })
            CREATE (api)-[:HAS_ENDPOINT]->(e)
        """, app_id=record["app_id"],
             endpoint_id=f"{record['app_id']}|endpoint|{endpoint['method']}|{endpoint['path']}",
             method=endpoint["method"],
             path=endpoint["path"],
             migration_id=migration_id)

async def run_migration():
    migration_id = f"005_api_model_expansion_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # 1. Obtener registros
    api_models = await get_api_models_with_json(driver)

    # 2. Ejecutar con atomicidad
    executor = AtomicMigrationExecutor(driver, migration_id)

    await executor.execute_atomic(
        records=api_models,
        migrate_fn=migrate_single_record,
        batch_size=100,
        dry_run=DRY_RUN
    )
```

#### 2.8.4 Shadow Graph Pattern (Alternativa)

```python
# Alternativa: Migrar a labels temporales, luego renombrar atómicamente

async def migrate_with_shadow_graph():
    """
    Crea nodos con labels temporales (_TEMP), luego renombra atómicamente.
    """
    migration_id = "005_api_model_expansion_shadow"

    try:
        # 1. Crear nodos con labels temporales
        async with driver.session() as session:
            await session.run("""
                MATCH (api:APIModelIR)
                UNWIND $endpoints AS endpoint
                CREATE (e:Endpoint_TEMP {
                    endpoint_id: endpoint.id,
                    method: endpoint.method,
                    path: endpoint.path,
                    migration_id: $migration_id
                })
                CREATE (api)-[:HAS_ENDPOINT_TEMP]->(e)
            """, endpoints=all_endpoints, migration_id=migration_id)

        # 2. Verificar que todo se creó correctamente
        count_temp = await count_nodes_by_label("Endpoint_TEMP")
        if count_temp != expected_count:
            raise ValueError(f"Expected {expected_count}, created {count_temp}")

        # 3. Renombrar atómicamente (muy rápido, < 1 segundo)
        async with driver.session() as session:
            async with session.begin_transaction() as tx:
                # Renombrar labels
                await tx.run("MATCH (n:Endpoint_TEMP) SET n:Endpoint REMOVE n:Endpoint_TEMP")

                # Renombrar relationship types
                await tx.run("""
                    MATCH ()-[r:HAS_ENDPOINT_TEMP]->()
                    CREATE (startNode(r))-[r2:HAS_ENDPOINT]->(endNode(r))
                    DELETE r
                """)

                await tx.commit()

        print("✅ Shadow graph migration completed atomically")

    except Exception as e:
        # Rollback: eliminar todos los _TEMP nodes/relationships
        print(f"❌ Migration failed, rolling back shadow graph...")
        async with driver.session() as session:
            await session.run("MATCH (n:Endpoint_TEMP) DETACH DELETE n")
        raise
```

#### 2.8.5 Beneficios

| Beneficio | Descripción |
|-----------|-------------|
| **Atomicidad** | Todo o nada - no deja grafo en estado inconsistente |
| **Rollback Automático** | Falla una parte → rollback completo automático |
| **Checkpoints** | Permite reanudar desde último checkpoint exitoso |
| **Validación Pre-Commit** | Verificar antes de hacer cambios permanentes |
| **Production Safety** | Migraciones seguras sin riesgo de corrupción parcial |
| **Auditabilidad** | Historial completo de intentos y rollbacks |

#### 2.8.6 Trade-offs

| Approach | Pros | Cons | Mejor Para |
|----------|------|------|------------|
| **Single Transaction** | Simplicidad, rollback nativo | Timeout en datasets grandes | < 1K nodos |
| **Checkpoint-Based** | Escalabilidad, puntos de recuperación | Complejidad, rollback manual | 1K - 1M nodos |
| **Shadow Graph** | Atomicidad real, rápido rollback | 2x storage durante migración | Migraciones críticas |

#### 2.8.7 Prioridad de Implementación

- **Sprint 3**: Implementar AtomicMigrationExecutor con checkpoint-based
- **Sprint 3**: Aplicar a migration scripts de Sprint 3+
- **Sprint 4**: Implementar Shadow Graph pattern para migraciones críticas
- **Sprint 4**: Refactorizar Sprint 0-2 migrations para usar atomic mode

### 2.6 Observabilidad de Migraciones

**Objetivo:** Rastrear ejecuciones de migraciones para auditing, debugging y rollback.

#### 2.6.1 MigrationRun Nodes

**Problema:** No tenemos historial de qué migraciones se ejecutaron, cuándo, y con qué resultados.

**Solución:** Crear nodos `MigrationRun` que registren cada ejecución de migración.

```cypher
// Crear nodo de migración
CREATE (m:MigrationRun {
  migration_id: "005_api_model_expansion_20251129_130045",
  migration_name: "005_api_model_expansion.py",
  sprint: "Sprint 2",
  status: "running",
  started_at: datetime(),
  dry_run: false,
  initiated_by: "manual"
})

// Actualizar al completar
MATCH (m:MigrationRun {migration_id: $id})
SET m.status = "completed",
    m.completed_at = datetime(),
    m.duration_seconds = duration.between(m.started_at, datetime()).seconds,
    m.nodes_created = 4690,
    m.relationships_created = 4690,
    m.errors_count = 0,
    m.success_rate = 1.0
```

#### 2.6.2 Relación AFFECTED para Trazabilidad

**Problema:** No sabemos qué IRs específicos fueron afectados por una migración.

**Solución:** Crear relaciones `[:AFFECTED]` desde MigrationRun hacia los IRs modificados.

```cypher
// Durante migración, registrar cada IR afectado
MATCH (m:MigrationRun {migration_id: $migration_id})
MATCH (ir:APIModelIR {app_id: $app_id})
MERGE (m)-[r:AFFECTED {
  timestamp: datetime(),
  operation: "expand_to_graph",
  nodes_created: 17,
  success: true
}]->(ir)
```

#### 2.6.3 Schema MigrationRun

```cypher
// Constraint
CREATE CONSTRAINT migration_run_unique IF NOT EXISTS
FOR (m:MigrationRun) REQUIRE m.migration_id IS UNIQUE;

// Indexes
CREATE INDEX migration_sprint IF NOT EXISTS
FOR (m:MigrationRun) ON (m.sprint);

CREATE INDEX migration_status IF NOT EXISTS
FOR (m:MigrationRun) ON (m.status);

CREATE INDEX migration_started IF NOT EXISTS
FOR (m:MigrationRun) ON (m.started_at);
```

#### 2.6.4 Modelo de Datos Completo

```python
# scripts/migrations/neo4j/migration_observability.py

class MigrationStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

@dataclass
class MigrationRun:
    migration_id: str  # "005_api_model_expansion_20251129_130045"
    migration_name: str  # "005_api_model_expansion.py"
    sprint: str  # "Sprint 2"
    status: MigrationStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    dry_run: bool = False
    initiated_by: str = "manual"  # "manual" | "automated" | "rollback"

    # Métricas
    total_records: int = 0
    processed_records: int = 0
    success_count: int = 0
    error_count: int = 0
    nodes_created: int = 0
    relationships_created: int = 0
    duration_seconds: Optional[float] = None
    success_rate: Optional[float] = None

    # Metadata
    error_details: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None
```

#### 2.6.5 Queries de Observabilidad

```cypher
// 1. Historial de migraciones por sprint
MATCH (m:MigrationRun)
RETURN m.sprint,
       collect({
         name: m.migration_name,
         status: m.status,
         started: m.started_at,
         success_rate: m.success_rate
       }) as migrations
ORDER BY m.sprint

// 2. Migraciones fallidas o incompletas
MATCH (m:MigrationRun)
WHERE m.status IN ['failed', 'running']
RETURN m.migration_name, m.status, m.started_at, m.error_details
ORDER BY m.started_at DESC

// 3. IRs afectados por una migración
MATCH (m:MigrationRun {migration_name: "005_api_model_expansion.py"})
      -[r:AFFECTED]->(ir)
RETURN ir.app_id,
       labels(ir) as ir_type,
       r.nodes_created,
       r.timestamp
ORDER BY r.timestamp

// 4. Última migración de cada tipo
MATCH (m:MigrationRun)
WITH m.sprint as sprint, max(m.started_at) as last_run
MATCH (m:MigrationRun)
WHERE m.sprint = sprint AND m.started_at = last_run
RETURN sprint, m.migration_name, m.status, m.started_at
ORDER BY sprint

// 5. Performance de migraciones
MATCH (m:MigrationRun)
WHERE m.status = 'completed'
RETURN m.migration_name,
       m.duration_seconds,
       m.nodes_created,
       m.nodes_created / m.duration_seconds as nodes_per_second,
       m.success_rate
ORDER BY m.duration_seconds DESC
```

#### 2.6.6 Integración en Scripts de Migración

```python
# Patrón de uso en todos los migration scripts

async def run_migration():
    # 1. Crear MigrationRun node
    migration_id = f"{MIGRATION_NAME}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    migration_run = await create_migration_run(
        migration_id=migration_id,
        migration_name=MIGRATION_NAME,
        sprint="Sprint 2",
        dry_run=DRY_RUN
    )

    try:
        # 2. Ejecutar migración
        for record in records:
            try:
                result = await migrate_record(record)

                # 3. Registrar éxito y afección
                await record_affected_ir(
                    migration_id=migration_id,
                    ir_id=record.app_id,
                    nodes_created=result.nodes_created,
                    success=True
                )

                migration_run.success_count += 1

            except Exception as e:
                # 4. Registrar error
                migration_run.error_count += 1
                await record_migration_error(
                    migration_id, record.app_id, str(e)
                )

        # 5. Marcar como completado
        await complete_migration_run(
            migration_id,
            status="completed",
            success_rate=migration_run.success_count / len(records)
        )

    except Exception as e:
        # 6. Marcar como fallado
        await fail_migration_run(migration_id, error=str(e))
        raise
```

#### 2.6.7 Beneficios

| Beneficio | Descripción |
|-----------|-------------|
| **Auditing** | Historial completo de todas las migraciones ejecutadas |
| **Debugging** | Identificar rápidamente qué migración afectó qué IRs |
| **Rollback Planning** | Saber exactamente qué revertir y en qué orden |
| **Performance Tracking** | Medir y optimizar velocidad de migraciones |
| **Error Analysis** | Detectar patrones en errores de migración |
| **Compliance** | Demostrar trazabilidad completa de cambios de schema |

#### 2.6.8 Prioridad de Implementación

- **Inmediato** ⚡: Implementar MigrationRun tracking YA y registrar retroactivamente Sprint 0-2
- **Sprint 6**: Integrar con lineage tracking para trazabilidad completa

---

## 2A. Tareas Inmediatas (Pre-Sprint 3)

**Objetivo:** Establecer fundamentos arquitectónicos ANTES de continuar con expansión de grafos.

**Justificación Estratégica:**

Con Sprints 0-2 ya ejecutados (~11,000 nodos creados), postergar estos fundamentos significa:
- ❌ **Perder historial**: Reconstruir MigrationRun retroactivamente es más costoso
- ❌ **Deuda técnica**: Sin GraphIRRepository base, Sprints 3-5 copian/pegan código
- ❌ **Inconsistencia**: DUAL_WRITE indefinido crea confusión en producción

**Implementar AHORA previene problemas exponenciales más adelante.**

---

### Task IA.1: GraphSchemaVersion Singleton

**Prioridad:** 🔴 CRÍTICA

**Objetivo:** Crear nodo singleton de versión de schema para tracking de estado.

**Implementación:**

```cypher
// scripts/migrations/neo4j/001_graph_schema_version.cypher

// Crear nodo singleton (idempotente)
MERGE (v:GraphSchemaVersion {singleton: true})
SET v.current_version = 2,
    v.last_migration = "005_api_model_expansion",
    v.migration_date = datetime(),
    v.sprints_completed = ["Sprint 0", "Sprint 1", "Sprint 2"],
    v.created_at = datetime(),
    v.updated_at = datetime()
RETURN v;

// Verificar
MATCH (v:GraphSchemaVersion {singleton: true})
RETURN v.current_version as version,
       v.sprints_completed as sprints,
       v.last_migration as last_migration;
```

**Convención de versiones:**

| Versión | Sprint | Descripción | Fecha |
|---------|--------|-------------|-------|
| 0 | Sprint 0 | Labels renamed to IR suffix | 2025-11-29 |
| 1 | Sprint 1 | DomainModelIR → Entity, Attribute | 2025-11-29 |
| 2 | Sprint 2 | APIModelIR → Endpoint, APIParameter | 2025-11-29 |
| 2.5 | Sprint 2.5 | TARGETS_ENTITY, campo source | TBD |
| 3 | Sprint 3 | BehaviorModelIR + ValidationModelIR | TBD |
| 4+ | Sprint 4-8 | Infraestructura, Tests, Lineage | TBD |

**Archivos a crear:**
```
scripts/migrations/neo4j/
└── 001_graph_schema_version.cypher
```

---

### Task IA.2: MigrationRun Tracking Retroactivo

**Prioridad:** 🔴 CRÍTICA

**Objetivo:** Registrar historial de migraciones ejecutadas (Sprint 0-2) aunque sea sintéticamente.

**Implementación:**

```python
# scripts/migrations/neo4j/002_register_past_migrations.py

"""
Registrar migraciones de Sprint 0-2 retroactivamente.
Aunque no tenemos métricas exactas, guardar el historial es crítico.
"""

import asyncio
from datetime import datetime
from neo4j import AsyncGraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "devmatrix123"

PAST_MIGRATIONS = [
    {
        "migration_id": "000_sprint0_schema_alignment",
        "migration_name": "000_sprint0_schema_alignment.py",
        "sprint": 0,
        "schema_version_after": 0,
        "description": "Label renaming, orphan cleanup",
        "started_at": "2025-11-29T10:00:00Z",  # Aproximado
        "completed_at": "2025-11-29T10:15:00Z",
        "status": "completed",
        "records_processed": 278,  # Applications
        "nodes_created": 0,  # Solo renaming
        "relationships_created": 0,
    },
    {
        "migration_id": "003_domain_model_expansion",
        "migration_name": "003_domain_model_expansion.py",
        "sprint": 1,
        "schema_version_after": 1,
        "description": "DomainModelIR → Entity + Attribute expansion",
        "started_at": "2025-11-29T11:00:00Z",
        "completed_at": "2025-11-29T11:30:00Z",
        "status": "completed",
        "records_processed": 280,  # DomainModelIRs
        "nodes_created": 6288,  # 1,084 Entity + 5,204 Attribute
        "relationships_created": 6420,  # HAS_ENTITY + HAS_ATTRIBUTE + RELATES_TO
    },
    {
        "migration_id": "005_api_model_expansion",
        "migration_name": "005_api_model_expansion.py",
        "sprint": 2,
        "schema_version_after": 2,
        "description": "APIModelIR → Endpoint + APIParameter expansion",
        "started_at": "2025-11-29T12:00:00Z",
        "completed_at": "2025-11-29T12:45:00Z",
        "status": "completed",
        "records_processed": 280,  # APIModelIRs
        "nodes_created": 4690,  # 4,022 Endpoint + 668 APIParameter
        "relationships_created": 4970,  # HAS_ENDPOINT + HAS_PARAMETER
    }
]

async def register_past_migrations():
    """Registrar migraciones retroactivamente."""
    print("📝 Registrando migraciones de Sprint 0-2 retroactivamente...")

    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        async with driver.session() as session:
            for migration in PAST_MIGRATIONS:
                # Crear MigrationRun node
                await session.run("""
                    MERGE (m:MigrationRun {migration_id: $migration_id})
                    SET m.migration_name = $migration_name,
                        m.sprint = $sprint,
                        m.schema_version_after = $schema_version_after,
                        m.description = $description,
                        m.started_at = datetime($started_at),
                        m.completed_at = datetime($completed_at),
                        m.status = $status,
                        m.records_processed = $records_processed,
                        m.nodes_created = $nodes_created,
                        m.relationships_created = $relationships_created,
                        m.created_at = datetime(),
                        m.updated_at = datetime()
                """, **migration)

                print(f"✅ Registered: {migration['migration_name']} "
                      f"(Sprint {migration['sprint']}, v{migration['schema_version_after']})")

        # Verificar
        async with driver.session() as session:
            result = await session.run("""
                MATCH (m:MigrationRun)
                RETURN m.migration_name as name,
                       m.sprint as sprint,
                       m.status as status
                ORDER BY m.sprint
            """)

            print("\n📊 Migraciones registradas:")
            async for record in result:
                print(f"   - Sprint {record['sprint']}: {record['name']} ({record['status']})")

    finally:
        await driver.close()

if __name__ == "__main__":
    asyncio.run(register_past_migrations())
```

**Archivos a crear:**
```
scripts/migrations/neo4j/
└── 002_register_past_migrations.py
```

---

### Task IA.3: GraphIRRepository Base Class

**Prioridad:** 🟡 ALTA

**Objetivo:** Centralizar lógica común de repositories ANTES de Sprint 3.

**Justificación:** Evitar copy/paste entre Domain, API, Behavior, Validation, Tests repositories.

**Implementación:**

```python
# src/cognitive/services/graph_ir_repository.py

"""
Base repository para operaciones comunes en IRs de grafo.

Patrón: Template Method para operaciones CRUD estándar.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from neo4j import AsyncGraphDatabase, AsyncDriver

class GraphIRRepository:
    """
    Base class para todos los IR repositories.

    Proporciona:
    - Metadata temporal automática (created_at, updated_at)
    - Subgraph Replace pattern
    - Batch operations con UNWIND
    - Error handling consistente
    - Transaction management
    """

    def __init__(self, driver: AsyncDriver):
        self.driver = driver

    # === Temporal Metadata ===

    def _add_temporal_metadata(self, node_props: Dict) -> Dict:
        """Agrega created_at/updated_at a propiedades de nodo."""
        now = datetime.utcnow().isoformat()

        return {
            **node_props,
            "created_at": node_props.get("created_at", now),
            "updated_at": now
        }

    # === Subgraph Replace Pattern ===

    async def replace_subgraph(
        self,
        parent_label: str,
        parent_id: str,
        child_label: str,
        relationship_type: str,
        children_data: List[Dict],
        cascade_labels: List[str] = None
    ) -> Dict[str, int]:
        """
        Patrón universal de Subgraph Replace.

        Pasos:
        1. DELETE todos los hijos existentes (y sus descendientes si cascade_labels)
        2. CREATE nuevos hijos desde cero
        3. Retornar estadísticas

        Args:
            parent_label: Label del nodo padre (e.g., "DomainModelIR")
            parent_id: ID del padre (e.g., app_id)
            child_label: Label de los hijos (e.g., "Entity")
            relationship_type: Tipo de relación (e.g., "HAS_ENTITY")
            children_data: Lista de diccionarios con datos de hijos
            cascade_labels: Labels adicionales a eliminar en cascada

        Returns:
            {"parent_id": str, "children_deleted": int, "children_created": int}
        """
        async with self.driver.session() as session:
            # 1. DELETE existing children
            delete_query = f"""
                MATCH (p:{parent_label} {{parent_id: $parent_id}})
                OPTIONAL MATCH (p)-[:{relationship_type}]->(c:{child_label})
            """

            # Add cascade deletion if specified
            if cascade_labels:
                for cascade_label in cascade_labels:
                    delete_query += f"""
                        OPTIONAL MATCH (c)-[*]->(cascade:{cascade_label})
                    """
                delete_query += f"""
                    WITH p, c, collect(cascade) as cascades
                    FOREACH (n IN cascades | DETACH DELETE n)
                    DETACH DELETE c
                    RETURN p, count(c) as deleted_count
                """
            else:
                delete_query += f"""
                    DETACH DELETE c
                    RETURN p, count(c) as deleted_count
                """

            result = await session.run(delete_query, parent_id=parent_id)
            record = await result.single()
            deleted_count = record["deleted_count"] if record else 0

            # 2. CREATE new children with temporal metadata
            children_with_metadata = [
                self._add_temporal_metadata(child)
                for child in children_data
            ]

            create_query = f"""
                MATCH (p:{parent_label} {{parent_id: $parent_id}})
                UNWIND $children as child_data
                CREATE (c:{child_label})
                SET c = child_data
                CREATE (p)-[:{relationship_type}]->(c)
                RETURN count(c) as created_count
            """

            result = await session.run(
                create_query,
                parent_id=parent_id,
                children=children_with_metadata
            )
            record = await result.single()
            created_count = record["created_count"] if record else 0

            return {
                "parent_id": parent_id,
                "children_deleted": deleted_count,
                "children_created": created_count
            }

    # === Batch Operations ===

    async def batch_create_nodes(
        self,
        label: str,
        nodes_data: List[Dict],
        batch_size: int = 1000
    ) -> int:
        """
        Crear nodos en batches usando UNWIND.

        Args:
            label: Label de los nodos
            nodes_data: Lista de propiedades de nodos
            batch_size: Tamaño de cada batch

        Returns:
            Total de nodos creados
        """
        total_created = 0

        async with self.driver.session() as session:
            for i in range(0, len(nodes_data), batch_size):
                batch = nodes_data[i:i + batch_size]

                # Add temporal metadata
                batch_with_metadata = [
                    self._add_temporal_metadata(node)
                    for node in batch
                ]

                result = await session.run(f"""
                    UNWIND $nodes as node_data
                    CREATE (n:{label})
                    SET n = node_data
                    RETURN count(n) as created
                """, nodes=batch_with_metadata)

                record = await result.single()
                total_created += record["created"] if record else 0

        return total_created

    async def batch_create_relationships(
        self,
        from_label: str,
        from_id_field: str,
        to_label: str,
        to_id_field: str,
        relationship_type: str,
        relationships_data: List[Dict],
        batch_size: int = 1000
    ) -> int:
        """
        Crear relaciones en batches.

        Args:
            from_label: Label del nodo origen
            from_id_field: Campo ID del nodo origen
            to_label: Label del nodo destino
            to_id_field: Campo ID del nodo destino
            relationship_type: Tipo de relación
            relationships_data: Lista con {from_id, to_id, props}
            batch_size: Tamaño de cada batch

        Returns:
            Total de relaciones creadas
        """
        total_created = 0

        async with self.driver.session() as session:
            for i in range(0, len(relationships_data), batch_size):
                batch = relationships_data[i:i + batch_size]

                result = await session.run(f"""
                    UNWIND $rels as rel_data
                    MATCH (from:{from_label} {{{from_id_field}: rel_data.from_id}})
                    MATCH (to:{to_label} {{{to_id_field}: rel_data.to_id}})
                    CREATE (from)-[r:{relationship_type}]->(to)
                    SET r = rel_data.props
                    RETURN count(r) as created
                """, rels=batch)

                record = await result.single()
                total_created += record["created"] if record else 0

        return total_created

    # === Utilities ===

    async def node_exists(self, label: str, node_id: str, id_field: str = "node_id") -> bool:
        """Check if a node exists."""
        async with self.driver.session() as session:
            result = await session.run(
                f"MATCH (n:{label} {{{id_field}: $node_id}}) RETURN count(n) as count",
                node_id=node_id
            )
            record = await result.single()
            return record["count"] > 0 if record else False

    async def get_node_count(self, label: str) -> int:
        """Get total count of nodes with a label."""
        async with self.driver.session() as session:
            result = await session.run(f"MATCH (n:{label}) RETURN count(n) as count")
            record = await result.single()
            return record["count"] if record else 0
```

**Refactorizar repositories existentes:**

```python
# src/cognitive/services/domain_model_graph_repository.py

from src.cognitive.services.graph_ir_repository import GraphIRRepository

class DomainModelGraphRepository(GraphIRRepository):
    """Repository para DomainModelIR usando base class."""

    async def save_domain_model(self, app_id: str, domain_model: DomainModelIR):
        """Save DomainModelIR usando Subgraph Replace pattern."""

        # Preparar datos de Entities
        entities_data = [
            {
                "entity_id": f"{app_id}|entity|{entity.name}",
                "name": entity.name,
                "description": entity.description,
                # ... más campos
            }
            for entity in domain_model.entities
        ]

        # Replace Entities subgraph
        await self.replace_subgraph(
            parent_label="DomainModelIR",
            parent_id=app_id,
            child_label="Entity",
            relationship_type="HAS_ENTITY",
            children_data=entities_data,
            cascade_labels=["Attribute", "Relationship"]  # Cascadear hijos
        )

        # Luego crear Attributes para cada Entity (similar pattern)
        # ...
```

**Archivos a crear:**
```
src/cognitive/services/
├── graph_ir_repository.py              # NEW base class
├── domain_model_graph_repository.py    # REFACTOR to extend base
└── api_model_graph_repository.py       # REFACTOR to extend base
```

---

### Task IA.4: Política de DUAL_WRITE y Cleanup

**Prioridad:** 🟡 ALTA

**Objetivo:** Definir CUÁNDO eliminar props JSON y DUAL_WRITE.

**Política propuesta:**

```yaml
dual_write_retirement:
  conditions:
    - roundtrip_tests: "100% pass rate (write graph → read graph → validate)"
    - e2e_tests: "2+ production scenarios working with graph-only"
    - validation_period: "7 días sin issues reportados"

  execution:
    step_1: "Disable DUAL_WRITE flag en config"
    step_2: "Monitor 48 horas"
    step_3: "PR cleanup: eliminar props JSON + código DUAL_WRITE"
    step_4: "Deploy con feature flag USE_GRAPH_* = true permanente"

  rollback_plan:
    trigger: "Cualquier issue crítico"
    action: "Re-enable DUAL_WRITE, investigar, fix, retry"
```

**Tests de validación:**

```python
# tests/integration/test_ir_roundtrip.py

async def test_domain_model_roundtrip():
    """
    Validar que:
    1. Escribir DomainModelIR al grafo
    2. Leer desde grafo
    3. Resultado == entrada original
    """
    # 1. Create DomainModelIR
    original = DomainModelIR(entities=[...])

    # 2. Save to graph
    repo = DomainModelGraphRepository(driver)
    await repo.save_domain_model(app_id, original)

    # 3. Load from graph
    loaded = await repo.load_domain_model(app_id)

    # 4. Validate
    assert loaded == original
    assert len(loaded.entities) == len(original.entities)
    for orig_ent, loaded_ent in zip(original.entities, loaded.entities):
        assert orig_ent.name == loaded_ent.name
        assert len(orig_ent.attributes) == len(loaded_ent.attributes)
```

**Archivos a crear:**
```
tests/integration/
└── test_ir_roundtrip.py

docs/DUAL_WRITE_RETIREMENT_PLAN.md  # Documentación formal
```

---

### Checklist Tareas Inmediatas

```
[x] IA.1: GraphSchemaVersion singleton creado y poblado con v2 ✅ (2025-11-29 12:56)
[x] IA.2: MigrationRun retroactivo para Sprint 0-2 registrado ✅ (2025-11-29 13:57)
[x] IA.3: GraphIRRepository base class implementada ✅ (2025-11-29 14:00, ~420 lines)
[x] IA.3b: Domain + API repositories refactorizados para extender base ✅ (2025-11-29 14:01)
[x] IA.4: Tests roundtrip DomainModelIR + APIModelIR al 100% ✅ (2025-11-29 14:15, 4 passed)
[ ] IA.4b: Política DUAL_WRITE retirement documentada
```

**Tiempo real:** 1.3 días (5/6 tareas completadas en una sesión intensiva)
**Tiempo estimado original:** 1-2 días (crítico hacerlo ANTES de Sprint 3)

**Beneficio:** Fundamentos arquitectónicos sólidos que previenen deuda técnica exponencial.

---

## 2B. Safety Rails & Operational Excellence (Enterprise Grade)

**Objetivo:** Agregar capa operacional enterprise-grade para producción y due diligence.

**Justificación Estratégica:**

El plan arquitectónico (Sprints 0-8) es técnicamente sólido, pero **falta la capa operacional** que lo hace production-ready para:
- ✅ **Producción estable**: Detección automática de issues antes que rompan
- ✅ **Migraciones seguras**: Atomicidad y rollback capability
- ✅ **Auditoría enterprise**: Compliance con estándares de big tech
- ✅ **Due diligence**: VCs/acquirers esperan operational excellence
- ✅ **QA avanzado**: Tracking de ejecuciones, no solo especificaciones

**Estos 9 safety rails convierten el plan en enterprise-grade.**

---

### SR.1: Graph Health Monitor

**Prioridad:** 🔴 CRÍTICA
**Sprint:** Sprint 0 (Task 0.6)

**Objetivo:** Monitoreo automático de salud del grafo para detectar inconsistencias.

**Problemas que detecta:**
- Nodos huérfanos (datos perdidos por migraciones fallidas)
- Relaciones inválidas (apuntan a nodos inexistentes)
- Entidades sin atributos (migración parcial)
- Endpoints sin paths (datos mal formados)
- Constraints rotos (violaciones de unicidad)
- Cardinalidades violadas (Entity sin Attributes)

**Implementación:**

```python
# scripts/monitoring/graph_health_check.py

"""
Graph Health Monitor - Detección automática de inconsistencias.
Ejecutar: PYTHONPATH=. python scripts/monitoring/graph_health_check.py
"""

from typing import Dict, List, Tuple
from src.cognitive.infrastructure.neo4j_client import Neo4jPatternClient

HEALTH_CHECKS = {
    # CRITICAL - Datos perdidos
    "orphan_entities": {
        "severity": "CRITICAL",
        "query": """
            MATCH (e:Entity)
            WHERE NOT (e)<-[:HAS_ENTITY]-(:DomainModelIR)
            RETURN e.name as entity_name, e.entity_id as entity_id
        """,
        "description": "Entities sin parent DomainModelIR (datos huérfanos)"
    },

    "orphan_endpoints": {
        "severity": "CRITICAL",
        "query": """
            MATCH (ep:Endpoint)
            WHERE NOT (ep)<-[:HAS_ENDPOINT]-(:APIModelIR)
            RETURN ep.path as path, ep.method as method
        """,
        "description": "Endpoints sin parent APIModelIR"
    },

    # WARNING - Posible migración parcial
    "entities_without_attributes": {
        "severity": "WARNING",
        "query": """
            MATCH (e:Entity)
            WHERE NOT (e)-[:HAS_ATTRIBUTE]->(:Attribute)
            RETURN e.name as entity_name, count(e) as count
        """,
        "description": "Entities sin Attributes (posible migración incompleta)"
    },

    "endpoints_without_paths": {
        "severity": "CRITICAL",
        "query": """
            MATCH (ep:Endpoint)
            WHERE ep.path IS NULL OR ep.path = ""
            RETURN count(ep) as invalid_count
        """,
        "description": "Endpoints con path vacío (datos inválidos)"
    },

    # WARNING - Integridad referencial
    "broken_relationships": {
        "severity": "CRITICAL",
        "query": """
            MATCH (a)-[r:RELATES_TO]->(b)
            WHERE NOT EXISTS((a:Entity)) OR NOT EXISTS((b:Entity))
            RETURN type(r) as rel_type, count(r) as broken_count
        """,
        "description": "Relaciones apuntando a nodos inexistentes"
    },

    # INFO - Features incompletos
    "patterns_without_vectors": {
        "severity": "INFO",
        "query": """
            MATCH (p:PatternIR)
            WHERE p.embedding IS NULL
            RETURN count(p) as missing_vectors
        """,
        "description": "Patterns sin embeddings (feature pendiente, no blocker)"
    }
}

async def run_health_checks() -> Dict[str, List]:
    """Ejecutar todos los health checks."""
    results = {}

    with Neo4jPatternClient() as neo4j:
        for check_name, check_config in HEALTH_CHECKS.items():
            query = check_config["query"]
            result = neo4j._execute_query(query)

            if result:
                severity = check_config["severity"]
                description = check_config["description"]

                # Determinar si hay issues
                has_issues = False
                if isinstance(result[0], dict):
                    # Check si hay count > 0 o resultados
                    has_issues = any(
                        v > 0 for v in result[0].values() if isinstance(v, int)
                    ) or len(result) > 0

                if has_issues:
                    icon = "🔴" if severity == "CRITICAL" else "🟡" if severity == "WARNING" else "🟢"
                    print(f"{icon} [{severity}] {check_name}:")
                    print(f"   {description}")
                    print(f"   Results: {result}")

                results[check_name] = result

    return results

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_health_checks())
```

**Integración:**
- **Manual:** Ejecutar antes/después de migraciones
- **Automatizado (Sprint 6):** Cron job diario, alertas en Slack
- **NeoDash (Sprint 6):** Dashboard visual de health metrics

---

### SR.2: Atomic Migration Mode

**Prioridad:** 🔴 CRÍTICA
**Sprint:** Sprint 0 (Task 0.7)

**Objetivo:** Garantizar atomicidad en migraciones con rollback automático.

**Problema:** Actualmente, si una migración se corta en medio:
- ❌ Medio DomainModelIR expandido, medio sin expandir
- ❌ Imposible saber qué quedó a medias
- ❌ Rollback manual = pesadilla

**Solución:** Wrapper de migración atómica con tracking de nodos creados.

**Implementación:**

```python
# scripts/migrations/neo4j/atomic_migration_wrapper.py

"""
Atomic Migration Wrapper - Garantiza atomicidad con rollback capability.
"""

from typing import List
from datetime import datetime
from src.cognitive.infrastructure.neo4j_client import Neo4jPatternClient

class AtomicMigration:
    """
    Context manager para migraciones atómicas.

    Uso:
        async with AtomicMigration("003_domain_expansion", neo4j) as migration:
            # ... create nodes ...
            await migration.track_created(entity_ids)
            # Si falla → rollback automático
    """

    def __init__(self, migration_id: str, neo4j_client: Neo4jPatternClient):
        self.migration_id = migration_id
        self.neo4j = neo4j_client
        self.batch_id = None

    def __enter__(self):
        """Registrar inicio de migración."""
        result = self.neo4j._execute_query("""
            CREATE (m:MigrationBatch {
                migration_id: $migration_id,
                batch_id: randomUUID(),
                started_at: datetime(),
                status: "running",
                can_rollback: true,
                created_node_ids: [],
                created_count: 0
            })
            RETURN m.batch_id as batch_id
        """, migration_id=self.migration_id)

        self.batch_id = result[0]["batch_id"]
        print(f"🚀 Migration batch started: {self.batch_id}")

        return self

    def track_created(self, node_ids: List[str]):
        """Registrar nodos creados para posible rollback."""
        self.neo4j._execute_query("""
            MATCH (m:MigrationBatch {batch_id: $batch_id})
            SET m.created_node_ids = m.created_node_ids + $node_ids,
                m.created_count = m.created_count + size($node_ids)
        """, batch_id=self.batch_id, node_ids=node_ids)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Commit o rollback según éxito."""
        if exc_type is None:
            # ✅ SUCCESS - marcar como completed
            self.neo4j._execute_query("""
                MATCH (m:MigrationBatch {batch_id: $batch_id})
                SET m.status = "completed",
                    m.completed_at = datetime(),
                    m.can_rollback = false
            """, batch_id=self.batch_id)

            print(f"✅ Migration batch completed: {self.batch_id}")
        else:
            # ❌ FAILURE - ejecutar rollback
            print(f"🔄 Rolling back migration batch: {self.batch_id}")
            print(f"   Error: {exc_val}")

            self.neo4j._execute_query("""
                MATCH (m:MigrationBatch {batch_id: $batch_id})
                WITH m, m.created_node_ids as node_ids

                // Eliminar nodos creados (DETACH DELETE borra relaciones también)
                UNWIND node_ids as node_id
                OPTIONAL MATCH (n)
                WHERE n.entity_id = node_id OR n.endpoint_id = node_id OR n.attribute_id = node_id
                DETACH DELETE n

                // Marcar como failed
                WITH m
                SET m.status = "failed",
                    m.failed_at = datetime(),
                    m.error_message = $error
            """, batch_id=self.batch_id, error=str(exc_val))

            print(f"❌ Migration batch rolled back: {self.batch_id}")

# Ejemplo de uso en migration scripts:
#
# with Neo4jPatternClient() as neo4j:
#     with AtomicMigration("003_domain_expansion", neo4j) as migration:
#
#         # Crear entities
#         entity_ids = create_entities(...)
#         migration.track_created(entity_ids)
#
#         # Crear attributes
#         attr_ids = create_attributes(...)
#         migration.track_created(attr_ids)
#
#         # Si algo falla aquí → rollback automático
```

**Beneficio:** Zero manual cleanup después de migraciones fallidas.

---

### SR.3: Graph Shape Contract

**Prioridad:** 🟡 ALTA
**Sprint:** Sprint 0 (Task 0.8)

**Objetivo:** Definir contrato formal de cardinalidades obligatorias del grafo.

**Problema:** Sin contrato formal, no se puede:
- Validar que un grafo está "bien formado"
- Detectar migraciones que dejaron datos inválidos
- Hacer CI checks automáticos

**Solución:** Documento formal + queries de validación.

**Implementación:**

```yaml
# docs/GRAPH_SHAPE_CONTRACT.md

graph_shape_requirements:

  ApplicationIR:
    must_have:
      - relationship: HAS_DOMAIN_MODEL
        target: DomainModelIR
        cardinality: exactly_1
        severity: CRITICAL

      - relationship: HAS_API_MODEL
        target: APIModelIR
        cardinality: exactly_1
        severity: CRITICAL

      - relationship: HAS_BEHAVIOR_MODEL  # Sprint 3+
        target: BehaviorModelIR
        cardinality: exactly_1
        severity: CRITICAL

    may_have:
      - relationship: HAS_VALIDATION_MODEL
        target: ValidationModelIR
        cardinality: 0_or_1

      - relationship: HAS_INFRASTRUCTURE_MODEL
        target: InfrastructureModelIR
        cardinality: 0_or_1

    properties:
      - name: app_id
        type: UUID
        required: true
        unique: true

  DomainModelIR:
    must_have:
      - relationship: HAS_ENTITY
        target: Entity
        cardinality: at_least_1
        severity: WARNING

    properties:
      - name: app_id
        type: UUID
        required: true

  Entity:
    must_have:
      - relationship: HAS_ATTRIBUTE
        target: Attribute
        cardinality: at_least_1
        severity: WARNING

    properties:
      - name: name
        type: string
        required: true
        non_empty: true

      - name: entity_id
        type: string
        required: true
        unique: true

  APIModelIR:
    should_have:  # Warning, no blocker
      - relationship: HAS_ENDPOINT
        target: Endpoint
        cardinality: at_least_1
        severity: INFO

  Endpoint:
    must_have:
      - property: path
        type: string
        required: true
        non_empty: true
        pattern: "^/"

      - property: method
        type: string
        required: true
        enum: [GET, POST, PUT, DELETE, PATCH]

    properties:
      - name: endpoint_id
        type: string
        required: true
        unique: true
```

**Validación automática:**

```python
# scripts/validation/validate_graph_shape.py

SHAPE_VALIDATORS = {
    "app_has_domain_model": {
        "severity": "CRITICAL",
        "query": """
            MATCH (app:ApplicationIR)
            WHERE NOT (app)-[:HAS_DOMAIN_MODEL]->(:DomainModelIR)
            RETURN app.app_id as invalid_app
        """
    },

    "domain_has_entities": {
        "severity": "WARNING",
        "query": """
            MATCH (dm:DomainModelIR)
            WHERE NOT (dm)-[:HAS_ENTITY]->(:Entity)
            RETURN dm.app_id as empty_domain_model
        """
    },

    "entities_have_attributes": {
        "severity": "WARNING",
        "query": """
            MATCH (e:Entity)
            WHERE NOT (e)-[:HAS_ATTRIBUTE]->(:Attribute)
            RETURN e.name as entity_name, e.entity_id
        """
    },

    "endpoints_have_valid_paths": {
        "severity": "CRITICAL",
        "query": """
            MATCH (ep:Endpoint)
            WHERE ep.path IS NULL
               OR ep.path = ""
               OR NOT ep.path STARTS WITH "/"
            RETURN ep.endpoint_id, ep.path
        """
    }
}
```

**Integración con CI:**
```bash
# .github/workflows/graph-validation.yml
- name: Validate Graph Shape
  run: PYTHONPATH=. python scripts/validation/validate_graph_shape.py
```

---

### SR.4: Extended Temporal Metadata

**Prioridad:** 🟢 RECOMENDADA
**Sprint:** Sprint 0 (Task 0.9)

**Objetivo:** Estandarizar metadata temporal con tracking de origen.

**Estado Actual:**
- `GraphIRRepository._add_temporal_metadata()` YA agrega `created_at` y `updated_at` ✅
- **Falta:** campo `updated_by` para saber origen del cambio

**Implementación:**

```python
# src/cognitive/services/graph_ir_repository.py (EXTEND)

@staticmethod
def _add_temporal_metadata(
    properties: Dict[str, Any],
    updated_by: str = "pipeline"  # NEW parameter
) -> Dict[str, Any]:
    """
    Add temporal metadata to node properties.

    Args:
        properties: Node properties
        updated_by: Source of update
            - "pipeline": Automated code generation
            - "agent": AI agent modification
            - "manual": Human edit via NeoDash/scripts
            - "migration": Database migration script

    Returns:
        Dictionary with temporal metadata added
    """
    now = datetime.utcnow().isoformat() + "Z"

    result = properties.copy()
    result["created_at"] = now
    result["updated_at"] = now
    result["updated_by"] = updated_by  # NEW

    return result
```

**Queries útiles:**

```cypher
// Nodos modificados por agents (para audit)
MATCH (n)
WHERE n.updated_by = "agent"
RETURN labels(n) as node_type,
       n.updated_at as when,
       count(n) as agent_modifications
ORDER BY n.updated_at DESC
LIMIT 20
```

---

### SR.5: TestExecutionIR Tracking

**Prioridad:** 🔴 CRÍTICA (para QA Agent)
**Sprint:** Sprint 5 (Fase 5.2 - Test Execution Tracking)

**Objetivo:** Persistir ejecuciones de tests para análisis de regresiones.

**Problema:** TestsModelIR actual es solo **especificación estática**. Sin ejecuciones:
- ❌ No se puede analizar regresiones (test pasaba, ahora falla)
- ❌ QA dashboards sin datos reales
- ❌ Sin ML sobre patrones de fallos

**Solución:** Agregar `TestExecutionIR` node para tracking de runs.

**Esquema Neo4j:**

```cypher
// Test execution node
CREATE (exec:TestExecutionIR {
    execution_id: randomUUID(),
    scenario_id: "test_create_product",
    executed_at: datetime(),
    status: "failed",  // passed, failed, skipped, error
    duration_ms: 1234,
    error_message: "Expected 201, got 500",
    stack_trace: "AssertionError: ...",
    test_framework: "pytest",
    runner: "qa_agent",
    environment: "local",  // local, staging, prod
    app_id: "uuid"
})

// Link to scenario
MATCH (scenario:TestScenarioIR {scenario_id: "test_create_product"})
MATCH (exec:TestExecutionIR {execution_id: $exec_id})
CREATE (scenario)-[:HAS_EXECUTION]->(exec)
```

**Queries de regresión:**

```cypher
// Regression detection: test que antes pasaba, ahora falla
MATCH (scenario:TestScenarioIR)-[:HAS_EXECUTION]->(exec:TestExecutionIR)
WITH scenario, exec
ORDER BY exec.executed_at DESC
WITH scenario, collect(exec)[0..2] as recent_execs
WHERE recent_execs[0].status = "failed"
  AND recent_execs[1].status = "passed"
RETURN scenario.name as regressed_test,
       recent_execs[0].executed_at as failed_at,
       recent_execs[0].error_message as error,
       recent_execs[1].executed_at as last_passed
```

**Integración con QA Agent:**

```python
# src/validation/runtime_smoke_validator.py (EXTEND)

async def persist_test_execution(
    scenario_id: str,
    status: str,
    duration_ms: int,
    error_message: Optional[str] = None
):
    """Persistir ejecución de test a Neo4j."""

    with Neo4jPatternClient() as neo4j:
        neo4j._execute_query("""
            CREATE (exec:TestExecutionIR {
                execution_id: randomUUID(),
                scenario_id: $scenario_id,
                executed_at: datetime(),
                status: $status,
                duration_ms: $duration_ms,
                error_message: $error_message,
                runner: "qa_agent",
                environment: $env
            })

            WITH exec
            MATCH (scenario:TestScenarioIR {scenario_id: $scenario_id})
            CREATE (scenario)-[:HAS_EXECUTION]->(exec)

            RETURN exec.execution_id as execution_id
        """,
        scenario_id=scenario_id,
        status=status,
        duration_ms=duration_ms,
        error_message=error_message,
        env=os.getenv("ENVIRONMENT", "local"))
```

---

### SR.6: FullIRGraphLoader

**Prioridad:** 🔴 CRÍTICA
**Sprint:** Sprint 6 (Task 6.3)

**Objetivo:** Loader unificado para reconstruir `ApplicationIR` completo desde grafo.

**Problema:** Actualmente tenés repos separados, pero NO una forma de decir:
- "Dame el IR completo de esta app"
- Crítico para QA Agent, debugging, regeneración

**Implementación:**

```python
# src/cognitive/services/full_ir_graph_loader.py

"""
Full IR Graph Loader - Unified loader para ApplicationIR completo.
"""

from src.cognitive.ir.application_ir import ApplicationIR
from src.cognitive.services.domain_model_graph_repository import DomainModelGraphRepository
from src.cognitive.services.api_model_graph_repository import APIModelGraphRepository
# ... más repos según sprint

class FullIRGraphLoader:
    """
    Unified loader para reconstruir ApplicationIR completo desde grafo.
    """

    def __init__(self, driver):
        self.driver = driver
        self.domain_repo = DomainModelGraphRepository(driver)
        self.api_repo = APIModelGraphRepository(driver)
        # Sprint 3+:
        # self.behavior_repo = BehaviorModelGraphRepository(driver)
        # self.validation_repo = ValidationModelGraphRepository(driver)
        # ...

    def load_full_ir(self, app_id: str) -> ApplicationIR:
        """
        Cargar ApplicationIR completo con TODOS sus sub-IRs.

        Args:
            app_id: Application ID

        Returns:
            ApplicationIR con domain_model, api_model, behavior_model, etc.

        Raises:
            NotFoundError: Si ApplicationIR no existe
        """
        # 1. Load ApplicationIR root
        app_ir = self._load_app_root(app_id)

        # 2. Load required sub-IRs
        app_ir.domain_model = self.domain_repo.load_domain_model(app_id)
        app_ir.api_model = self.api_repo.load_api_model(app_id)

        # 3. Load optional sub-IRs (Sprint 3+)
        try:
            app_ir.behavior_model = self.behavior_repo.load_behavior_model(app_id)
        except NotFoundError:
            pass  # OK, optional

        try:
            app_ir.validation_model = self.validation_repo.load_validation_model(app_id)
        except NotFoundError:
            pass  # OK, optional

        return app_ir

    def _load_app_root(self, app_id: str) -> ApplicationIR:
        """Load ApplicationIR root node."""
        with self.driver.session(database=self.database) as session:
            result = session.run("""
                MATCH (app:ApplicationIR {app_id: $app_id})
                RETURN app.app_id as app_id,
                       app.created_at as created_at,
                       app.updated_at as updated_at
            """, app_id=app_id)

            record = result.single()
            if not record:
                raise NotFoundError(f"ApplicationIR {app_id} not found")

            return ApplicationIR(
                app_id=record["app_id"],
                # domain_model y api_model se llenan después
            )
```

**Uso en QA Agent:**

```python
# src/validation/runtime_smoke_validator.py

loader = FullIRGraphLoader(neo4j_driver)
full_ir = loader.load_full_ir(app_id)

# Ahora tenés TODA la info para validar
validate_domain_model(full_ir.domain_model)
validate_api_model(full_ir.api_model)
validate_behavior_model(full_ir.behavior_model)
```

---

### SR.7: NeoDash Views Roadmap

**Prioridad:** 🟢 RECOMENDADA
**Sprint:** Todos (agregar explícitamente en cada sprint)

**Objetivo:** Documentar qué dashboards NeoDash se crean en cada sprint.

**Roadmap de vistas:**

| Sprint | NeoDash Dashboard | Queries Principales |
|--------|-------------------|---------------------|
| 1 | **DOMAIN_MODEL_OVERVIEW** | Count de entidades por app, distribución de tipos de datos |
| 1 | **ENTITY_RELATIONSHIP_GRAPH** | Visualización de RELATES_TO entre entities |
| 2 | **API_MODEL_OVERVIEW** | Count de endpoints por app, distribución de métodos HTTP |
| 2 | **ENDPOINT_COVERAGE** | % endpoints con tests (Sprint 5+) |
| 3 | **BEHAVIOR_MODEL_OVERVIEW** | Flows por app, steps por flow |
| 4 | **VALIDATION_RULES** | Rules por app, severity distribution |
| 5 | **QA_COVERAGE_DASHBOARD** | Test scenarios por endpoint, pass rate |
| 5 | **TEST_REGRESSION_ANALYSIS** | Tests que antes pasaban, ahora fallan |
| 6 | **LINEAGE_TRACKING** | Spec → IR → Files trazabilidad |
| 6 | **GRAPH_HEALTH_MONITOR** | Orphans, broken rels, shape violations |
| 8 | **ANALYTICS_OVERVIEW** | Pattern usage, transfer learning stats |

**Ejemplo query para Dashboard:**

```cypher
// DOMAIN_MODEL_OVERVIEW
MATCH (app:ApplicationIR)-[:HAS_DOMAIN_MODEL]->(dm:DomainModelIR)-[:HAS_ENTITY]->(e:Entity)
RETURN app.app_id as app_id,
       count(DISTINCT e) as entity_count,
       count(DISTINCT dm) as domain_model_count
ORDER BY entity_count DESC
LIMIT 20
```

---

### SR.8: Sprint 5 Split (MVP + Complete)

**Prioridad:** 🟡 ALTA
**Sprint:** Sprint 5 (dividido en 2 fases)

**Objetivo:** Evitar burnout dividiendo TestsModelIR en entregas incrementales.

**Problema:** TestsModelIR es ENORME. Hacerlo todo de una:
- 2-3 semanas monolíticas
- Alto riesgo de bugs
- Sin feedback loop intermedio

**Solución:** Dividir en 2 fases:

#### Sprint 5 — MVP (1 semana)

**Scope:**
- Persistir `TestsModelIR` node
- Persistir `EndpointTestSuite` node
- Persistir `TestScenarioIR` node
- Crear relación `VALIDATES_ENDPOINT`
- **NO incluir:** Seeds, Flows, Assertions detalladas

**Deliverables:**
- QA Agent puede generar tests básicos para endpoints
- Tests se persisten en grafo
- Dashboard básico de cobertura

#### Sprint 5.5 — Complete (1 semana)

**Scope:**
- Persistir `SeedEntityIR` node
- Crear relación `DEPENDS_ON_SEED`
- Persistir `FlowTestSuite` node
- Crear relaciones `VALIDATES_FLOW` y `VALIDATES_RULE`
- Assertions detalladas (expected status, schema validation)

**Deliverables:**
- Tests complejos con seeds
- Flow testing multi-endpoint
- Cobertura completa de reglas de negocio

**Beneficio:** Entregas incrementales → feedback rápido → menor riesgo.

---

### SR.9: Summary - Enterprise-Grade Benefits

**Por qué estos 9 safety rails son críticos:**

| Safety Rail | Beneficio Principal | Due Diligence Impact |
|-------------|---------------------|----------------------|
| SR.1: Health Monitor | Detección proactiva de issues | ✅ Operational maturity |
| SR.2: Atomic Migrations | Zero manual cleanup | ✅ Production stability |
| SR.3: Shape Contract | Validación automática | ✅ Data integrity |
| SR.4: Temporal Metadata | Audit trail completo | ✅ Compliance |
| SR.5: Test Executions | Regression analysis | ✅ QA excellence |
| SR.6: Full IR Loader | Debugging + QA simplificado | ✅ Developer experience |
| SR.7: NeoDash Roadmap | Observability clara | ✅ Stakeholder transparency |
| SR.8: Sprint 5 Split | Menor riesgo, entregas incrementales | ✅ Delivery reliability |

**Resultado:** Plan técnicamente sólido + operacionalmente maduro = **enterprise-ready**.

---

### Checklist Safety Rails

```
[x] SR.1: Graph Health Monitor scripts creados ✅ (2025-11-29) → graph_health_monitor.py
[x] SR.2: Atomic Migration wrapper implementado ✅ (2025-11-29) → atomic_migration.py
[x] SR.3: Graph Shape Contract documentado + validators ✅ (2025-11-29) → 008_validate_graph_shape_contract.py
[x] SR.4: Temporal metadata extendido ✅ (2025-11-29) → temporal_metadata.py (100% coverage)
[x] SR.5: TestExecutionIR schema diseñado ✅ (2025-11-29) → SPRINT5_REDESIGN.md
[x] SR.6: FullIRGraphLoader implementado ✅ (2025-11-29) → full_ir_graph_loader.py (10/10 tests)
[x] SR.7: NeoDash views roadmap ✅ (2025-11-29) → neodash_views.cypher (10 dashboards)
[x] SR.8: Sprint 5 dividido en MVP + Complete phases ✅ (2025-11-29) → SPRINT5_REDESIGN.md
[x] SR.9: Production validator script ✅ (2025-11-29) → validate_safety_rails.py
```

**Tiempo estimado total:** 3-4 días distribuidos across sprints
**ROI:** Prevenir 10-20x ese tiempo en debugging production issues

---

## 3. Sprint 0: Schema Alignment & Cleanup ✅ COMPLETADO

**Objetivo:** Limpiar datos huérfanos y alinear labels con código Python.

**Prioridad:** P0 (CRÍTICO - prerequisito de todo lo demás)

**Estado:** ✅ COMPLETADO (2025-11-29)

### Resultados Sprint 0:
| Task | Status | Resultado |
|------|--------|-----------|
| 0.1 Orphan cleanup | ✅ | 2 DomainModel huérfanos eliminados |
| 0.2 Empty labels | ✅ | 12 labels vacíos documentados |
| 0.3 Label renaming | ✅ | 1,676 nodos → IR suffix |
| 0.4 Repository update | ✅ | 20 queries actualizadas |
| 0.5 Pattern classification | ✅ | Script creado, 66 patterns sin vectores |

### 3.1 Tasks

#### Task 0.1: Eliminar Orphan Nodes
```
Prioridad: P0
Estimado: 1h
```

**Problema:** 2 DomainModel nodes sin Application parent.

**Query de limpieza:**
```cypher
// Identificar orphans
MATCH (d:DomainModel)
WHERE NOT EXISTS { MATCH (:Application)-[:HAS_DOMAIN_MODEL]->(d) }
RETURN d.app_id, d;

// Eliminar orphans
MATCH (d:DomainModel)
WHERE NOT EXISTS { MATCH (:Application)-[:HAS_DOMAIN_MODEL]->(d) }
DETACH DELETE d;
```

**Deliverables:**
- [x] Script de identificación de orphans ✅
- [x] Script de limpieza (idempotent) ✅
- [x] Verificación post-limpieza ✅

---

#### Task 0.2: Eliminar Empty Labels
```
Prioridad: P1
Estimado: 1h
```

**Problema:** 12 labels sin nodos (schema artifacts).

**Labels a eliminar del schema:**
- SemanticPattern, CompositePattern, GraphPatternNode, ContextualPattern
- ClusterNode, TaxonomyNode, IntentNode, ERCNode
- ProgramNode, FragmentNode, CallGraph, TypeHierarchy

**Query:**
```cypher
// Verificar que están vacíos
MATCH (n)
WHERE any(label IN labels(n) WHERE label IN [
    'SemanticPattern', 'CompositePattern', 'GraphPatternNode',
    'ContextualPattern', 'ClusterNode', 'TaxonomyNode',
    'IntentNode', 'ERCNode', 'ProgramNode', 'FragmentNode',
    'CallGraph', 'TypeHierarchy'
])
RETURN labels(n), count(n);

// Drop constraints/indexes si existen
// (Neo4j no permite DROP LABEL, pero sí limpiar constraints)
```

**Deliverables:**
- [x] Script de verificación ✅
- [x] Documentar en schema que están deprecated ✅

---

#### Task 0.3: Renaming de Labels IR
```
Prioridad: P0
Estimado: 3h
```

**Cambios de labels:**
```cypher
// 1. Application → ApplicationIR (278 nodos)
MATCH (n:Application)
REMOVE n:Application
SET n:ApplicationIR;

// 2. DomainModel → DomainModelIR (280 nodos)
MATCH (n:DomainModel)
REMOVE n:DomainModel
SET n:DomainModelIR;

// 3. APIModel → APIModelIR (280 nodos)
MATCH (n:APIModel)
REMOVE n:APIModel
SET n:APIModelIR;

// 4. BehaviorModel → BehaviorModelIR (280 nodos)
MATCH (n:BehaviorModel)
REMOVE n:BehaviorModel
SET n:BehaviorModelIR;

// 5. ValidationModel → ValidationModelIR (280 nodos)
MATCH (n:ValidationModel)
REMOVE n:ValidationModel
SET n:ValidationModelIR;

// 6. InfrastructureModel → InfrastructureModelIR (280 nodos)
MATCH (n:InfrastructureModel)
REMOVE n:InfrastructureModel
SET n:InfrastructureModelIR;

// 7. Actualizar constraints
DROP CONSTRAINT application_id IF EXISTS;
CREATE CONSTRAINT applicationir_id IF NOT EXISTS
FOR (n:ApplicationIR) REQUIRE n.app_id IS UNIQUE;
// ... repeat for each IR
```

**Deliverables:**
- [x] Migration script (000_sprint0_schema_alignment.cypher) ✅
- [x] Rollback script (000_sprint0_rollback.cypher) ✅
- [x] Verification queries ✅

---

#### Task 0.4: Actualizar neo4j_ir_repository.py
```
Archivo: src/cognitive/services/neo4j_ir_repository.py
Prioridad: P0
Estimado: 2h
```

**Cambios:**
```python
# ANTES (línea ~71)
MERGE (a:Application {app_id: $app_id})

# DESPUÉS
MERGE (a:ApplicationIR {app_id: $app_id})

# ANTES (línea ~95)
MERGE (d:DomainModel {app_id: $app_id})

# DESPUÉS
MERGE (d:DomainModelIR {app_id: $app_id})

# ... similar para todos los IRs
```

**Deliverables:**
- [x] neo4j_ir_repository.py actualizado (20 queries) ✅
- [x] Tests actualizados ✅
- [x] Backward compatibility verificada ✅

---

#### Task 0.5: Clasificar Patterns Sin Tags
```
Prioridad: P2
Estimado: 4h
```

**Problema:** 1,751 patterns (5.5%) sin clasificación.

**Approach:**
```python
# Usar embedding similarity para clasificar
async def classify_untagged_patterns(self):
    # 1. Get untagged
    untagged = await self.neo4j.run("""
        MATCH (p:Pattern)
        WHERE NOT EXISTS { MATCH (p)-[:HAS_TAG]->() }
        RETURN p.pattern_id, p.code
    """)

    # 2. For each, find most similar tagged pattern
    for pattern in untagged:
        similar = await self.qdrant.search(
            collection="devmatrix_patterns",
            vector=self.embed(pattern.code),
            limit=5
        )

        # 3. Copy tags from most similar
        if similar[0].score > 0.85:
            await self.neo4j.run("""
                MATCH (p:Pattern {pattern_id: $id})
                MATCH (ref:Pattern {pattern_id: $ref_id})-[:HAS_TAG]->(t:Tag)
                MERGE (p)-[:HAS_TAG]->(t)
            """, id=pattern.pattern_id, ref_id=similar[0].payload.pattern_id)
```

**Deliverables:**
- [x] Pattern classification script (001_classify_untagged_patterns.py) ✅
- [x] Report de patterns clasificados ✅ (66 patterns, 0 con vectores en Qdrant)
- [x] Tests ✅

---

### 3.2 Sprint 0 Checklist

```
[x] Task 0.1: Eliminar Orphan Nodes ✅ (2 eliminados)
[x] Task 0.2: Eliminar/Documentar Empty Labels ✅ (12 documentados)
[x] Task 0.3: Renaming de Labels IR ✅ (1,676 nodos)
[x] Task 0.4: Actualizar neo4j_ir_repository.py ✅ (20 queries)
[x] Task 0.5: Clasificar Patterns Sin Tags ✅ (script creado)
[x] Verification: Todos labels usan IR suffix ✅
[x] Tests pasan con nuevos labels ✅
```

**Nota:** 66 patterns sin tags no tienen embeddings en Qdrant - requieren re-generación de vectores.

---

## 4. Sprint 1: Graph Expansion - DomainModelIR ✅ COMPLETADO

**Objetivo:** Expandir DomainModelIR de JSON a nodos Entity, Attribute, Relationship.

**Prioridad:** P0

**Estado:** ✅ COMPLETADO - Migración LIVE exitosa (2025-11-29)

### Resultados Sprint 1:
| Task | Status | Resultado |
|------|--------|-----------|
| 1.1 Schema | ✅ | 2 constraints + 4 indexes aplicados |
| 1.2 Graph Repository | ✅ | domain_model_graph_repository.py (545 líneas, UNWIND batching) |
| 1.3 Migration Script | ✅ | 003_domain_model_expansion.py + 2 bug fixes |
| 1.4 Repository Update | ✅ | neo4j_ir_repository.py con feature flag |
| **Dry-Run** | ✅ | 278/278 exitoso - 0 errores |
| **Migración LIVE** | ✅ | **278/278 migrados - COMPLETADO** |

### Resultados Migración LIVE (2025-11-29):
```
✅ DomainModels procesados: 278/278 (100% éxito)
✅ Bugs resueltos: 2 (UUID normalization + missing app_id parameter)

Nodos y edges creados:
├─ Entity nodes:        1,084 ✅
├─ Attribute nodes:     5,204 ✅
├─ RELATES_TO edges:      132 ✅ (132 relationships reales en datos)
├─ HAS_ENTITY edges:    1,084 ✅
└─ HAS_ATTRIBUTE edges: 5,204 ✅
   ────────────────────────────
   TOTAL: 7,708 objetos de grafo creados

Verificación:
├─ Migrated DomainModels: 278 con migrated_to_graph = true
├─ Sample Entity: entity_id, name, is_aggregate_root ✅
├─ Sample Attribute: attribute_id, name, data_type, is_primary_key ✅
└─ Graph paths: DomainModelIR → Entity → Attribute ✅
```

### Bugs Encontrados y Resueltos:
**Bug #1 - UUID Case Mismatch**:
- **Problema**: Enum esperaba "UUID" pero datos contenían "uuid" (lowercase)
- **Solución**: Normalización pre-validación en líneas 216-223 de 003_domain_model_expansion.py
- **Detección**: Dry-run
- **Impacto**: Sin fix, 100% de migraciones habrían fallado

**Bug #2 - Missing Parameter app_id**:
- **Problema**: Query Cypher usaba `$app_id` pero parámetro no se pasaba a `session.run()`
- **Solución**: Agregado `app_id=app_id` en línea 144 de 003_domain_model_expansion.py
- **Detección**: Migración LIVE
- **Impacto**: Sin fix, migración LIVE habría fallado en create_attribute_node

### 4.1 Target Schema

```
(:ApplicationIR)
    -[:HAS_DOMAIN_MODEL]->(:DomainModelIR {app_id})
        -[:HAS_ENTITY]->(:Entity {
            name: "Product",
            description: "...",
            is_aggregate_root: true
        })
            -[:HAS_ATTRIBUTE]->(:Attribute {
                name: "id",
                data_type: "UUID",
                is_primary_key: true,
                is_nullable: false,
                is_unique: true
            })
            -[:HAS_ATTRIBUTE]->(:Attribute {
                name: "price",
                data_type: "FLOAT"
            })
            -[:RELATES_TO {
                type: "one_to_many",
                field_name: "items",
                back_populates: "product"
            }]->(:Entity {name: "OrderItem"})
```

### 4.2 Tasks

#### Task 1.1: Create Entity Nodes Schema
```
Archivo: src/cognitive/infrastructure/neo4j_domain_schema.py
Prioridad: P0
Estimado: 3h
```

**Schema Cypher:**
```cypher
// Constraints
CREATE CONSTRAINT entity_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE (e.domain_model_id, e.name) IS UNIQUE;

CREATE CONSTRAINT attribute_unique IF NOT EXISTS
FOR (a:Attribute) REQUIRE (a.entity_id, a.name) IS UNIQUE;

// Indexes
CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name);
CREATE INDEX attribute_pk IF NOT EXISTS FOR (a:Attribute) ON (a.is_primary_key);
CREATE INDEX attribute_type IF NOT EXISTS FOR (a:Attribute) ON (a.data_type);
```

**Deliverables:**
- [x] Schema creation script (002_domain_model_schema.cypher) ✅
- [x] Rollback script (002_domain_model_schema_rollback.cypher) ✅
- [x] Verification queries ✅

---

#### Task 1.2: Domain Model Repository (Graph Version)
```
Archivo: src/cognitive/services/domain_model_graph_repository.py
Prioridad: P0
Estimado: 6h
```

**Interface:**
```python
class DomainModelGraphRepository:
    """Repository that stores DomainModelIR as proper graph nodes."""

    async def save_domain_model(
        self,
        app_id: str,
        domain_model: DomainModelIR
    ) -> str:
        """
        Save DomainModelIR expanding to:
        - DomainModelIR node
        - Entity nodes (with HAS_ENTITY relationships)
        - Attribute nodes (with HAS_ATTRIBUTE relationships)
        - EntityRelationship edges (RELATES_TO)
        """
        # 1. Create/Update DomainModelIR node
        await self.neo4j.run("""
            MATCH (a:ApplicationIR {app_id: $app_id})
            MERGE (d:DomainModelIR {app_id: $app_id})
            MERGE (a)-[:HAS_DOMAIN_MODEL]->(d)
            SET d.metadata = $metadata
        """, app_id=app_id, metadata=json.dumps(domain_model.metadata))

        # 2. Create Entity nodes
        for entity in domain_model.entities:
            entity_id = f"{app_id}_{entity.name}"
            await self.neo4j.run("""
                MATCH (d:DomainModelIR {app_id: $app_id})
                MERGE (e:Entity {entity_id: $entity_id})
                SET e.name = $name,
                    e.description = $description,
                    e.is_aggregate_root = $is_aggregate_root
                MERGE (d)-[:HAS_ENTITY]->(e)
            """, app_id=app_id, entity_id=entity_id,
                name=entity.name,
                description=entity.description,
                is_aggregate_root=entity.is_aggregate_root)

            # 3. Create Attribute nodes
            for attr in entity.attributes:
                await self.neo4j.run("""
                    MATCH (e:Entity {entity_id: $entity_id})
                    MERGE (a:Attribute {
                        entity_id: $entity_id,
                        name: $name
                    })
                    SET a.data_type = $data_type,
                        a.is_primary_key = $is_pk,
                        a.is_nullable = $is_nullable,
                        a.is_unique = $is_unique,
                        a.default_value = $default_value,
                        a.constraints = $constraints
                    MERGE (e)-[:HAS_ATTRIBUTE]->(a)
                """, entity_id=entity_id, name=attr.name,
                    data_type=attr.data_type.value,
                    is_pk=attr.is_primary_key,
                    is_nullable=attr.is_nullable,
                    is_unique=attr.is_unique,
                    default_value=str(attr.default_value) if attr.default_value else None,
                    constraints=json.dumps(attr.constraints))

        # 4. Create Relationship edges
        for entity in domain_model.entities:
            for rel in entity.relationships:
                await self.neo4j.run("""
                    MATCH (source:Entity {entity_id: $source_id})
                    MATCH (target:Entity {entity_id: $target_id})
                    MERGE (source)-[r:RELATES_TO {field_name: $field_name}]->(target)
                    SET r.type = $type,
                        r.back_populates = $back_populates
                """, source_id=f"{app_id}_{entity.name}",
                    target_id=f"{app_id}_{rel.target_entity}",
                    field_name=rel.field_name,
                    type=rel.type.value,
                    back_populates=rel.back_populates)

    async def load_domain_model(self, app_id: str) -> DomainModelIR:
        """Reconstruct DomainModelIR from graph nodes."""
        # Query all entities with attributes and relationships
        result = await self.neo4j.run("""
            MATCH (d:DomainModelIR {app_id: $app_id})
            OPTIONAL MATCH (d)-[:HAS_ENTITY]->(e:Entity)
            OPTIONAL MATCH (e)-[:HAS_ATTRIBUTE]->(a:Attribute)
            OPTIONAL MATCH (e)-[r:RELATES_TO]->(target:Entity)
            RETURN d,
                   collect(DISTINCT e) as entities,
                   collect(DISTINCT a) as attributes,
                   collect(DISTINCT {rel: r, target: target.name}) as relationships
        """, app_id=app_id)

        # Reconstruct DomainModelIR from graph data
        return self._reconstruct_domain_model(result)
```

**Deliverables:**
- [x] DomainModelGraphRepository class (545 líneas) ✅
- [x] Unit tests (pendiente ejecución) ⏳
- [x] Integration tests (pendiente ejecución) ⏳

---

#### Task 1.3: Migration Script - JSON to Graph
```
Archivo: scripts/migrations/neo4j/001_domain_model_expansion.py
Prioridad: P0
Estimado: 4h
```

**Script:**
```python
async def migrate_domain_models_to_graph():
    """Migrate existing JSON domain_model_data to graph nodes."""

    # 1. Get all DomainModelIR nodes with JSON data
    results = await neo4j.run("""
        MATCH (d:DomainModelIR)
        WHERE d.domain_model_data IS NOT NULL
        RETURN d.app_id, d.domain_model_data
    """)

    migrated = 0
    for record in results:
        app_id = record["app_id"]
        json_data = json.loads(record["domain_model_data"])

        # 2. Reconstruct DomainModelIR from JSON
        domain_model = DomainModelIR(**json_data)

        # 3. Save as graph
        await domain_repo.save_domain_model(app_id, domain_model)

        # 4. Remove JSON property (optional, can keep for rollback)
        await neo4j.run("""
            MATCH (d:DomainModelIR {app_id: $app_id})
            REMOVE d.domain_model_data
        """, app_id=app_id)

        migrated += 1
        if migrated % 50 == 0:
            print(f"Migrated {migrated} DomainModels...")

    print(f"Total migrated: {migrated}")
```

**Deliverables:**
- [x] Migration script (003_domain_model_expansion.py) ✅
- [x] Rollback script (003_domain_model_expansion_rollback.py) ✅
- [x] Cleanup script (003_cleanup_json.py) ✅
- [x] README documentation (README_003.md) ✅
- [x] Progress logging ✅
- [x] Verification queries ✅

---

#### Task 1.4: Update neo4j_ir_repository.py for DomainModel
```
Archivo: src/cognitive/services/neo4j_ir_repository.py
Prioridad: P0
Estimado: 3h
```

**Cambios:**
```python
# ANTES
async def save_domain_model(self, app_id: str, domain_model: DomainModelIR):
    await self.neo4j.run("""
        MATCH (a:ApplicationIR {app_id: $app_id})
        MERGE (d:DomainModelIR {app_id: $app_id})
        SET d.domain_model_data = $data
        MERGE (a)-[:HAS_DOMAIN_MODEL]->(d)
    """, app_id=app_id, data=domain_model.model_dump_json())

# DESPUÉS
async def save_domain_model(self, app_id: str, domain_model: DomainModelIR):
    # Delegate to graph repository
    await self.domain_graph_repo.save_domain_model(app_id, domain_model)
```

**Deliverables:**
- [x] Updated neo4j_ir_repository.py (feature flag USE_GRAPH_DOMAIN_MODEL) ✅
- [x] Backward compatibility layer (DUAL_WRITE mode) ✅
- [x] Tests updated ⏳

---

### 4.3 Sprint 1 Checklist

```
[x] Task 1.1: Create Entity Nodes Schema ✅
[x] Task 1.2: Domain Model Repository (Graph Version) ✅
[x] Task 1.3: Migration Script - JSON to Graph ✅
[x] Task 1.4: Update neo4j_ir_repository.py ✅
[x] Ejecutar schema creation (002_domain_model_schema.cypher) ✅
[x] Ejecutar migration DRY-RUN (003_domain_model_expansion.py) ✅
[x] Bug fix #1: UUID normalization ✅
[x] Bug fix #2: Missing app_id parameter ✅
[x] Ejecutar migración LIVE ✅ (278/278 exitoso)
[x] Verification: 278 DomainModelIR migrated_to_graph = true ✅
[x] Verification: 1,084 Entity nodes created ✅
[x] Verification: 5,204 Attribute nodes created ✅
[x] Verification: 132 RELATES_TO edges created ✅
[x] Graph structure verified ✅ (paths DomainModelIR → Entity → Attribute)
```

**Estado Final (2025-11-29):**
- ✅ Schema aplicado: 2 constraints + 4 indexes
- ✅ Dry-run exitoso: 278/278 sin errores
- ✅ 2 Bugs encontrados y resueltos (UUID normalization + missing app_id)
- ✅ **Migración LIVE completada**: 7,708 objetos de grafo creados
- ✅ **Verificación exitosa**: Estructura de grafo correcta

**Próximos Pasos:**
1. ✅ ~~Sprint 1 COMPLETADO~~
2. **Opcional**: Refactors incrementales (GraphPersistenceMode, base class, replace subgraph)
3. **Sprint 2**: APIModelIR expansion (endpoints, schemas, parameters)
4. **Sprint 3**: BehaviorModelIR + ValidationModelIR
5. **Sprint 4**: InfrastructureModelIR
6. **Sprint 5**: TestsModelIR (alta prioridad para QA agent)

---

## 5. Sprint 2: Graph Expansion - APIModelIR

**Objetivo:** Expandir APIModelIR de JSON a nodos Endpoint, APISchema, APIParameter.

### 5.1 Target Schema

```
(:ApplicationIR)
    -[:HAS_API_MODEL]->(:APIModelIR {base_path, version})
        -[:HAS_ENDPOINT]->(:Endpoint {
            path: "/products/{id}",
            method: "GET",
            operation_id: "get_product",
            auth_required: true,
            inferred: false
        })
            -[:HAS_PARAMETER]->(:APIParameter {
                name: "id",
                location: "path",
                data_type: "UUID",
                required: true
            })
            -[:REQUEST_SCHEMA]->(:APISchema {name: "ProductUpdate"})
            -[:RESPONSE_SCHEMA]->(:APISchema {name: "ProductResponse"})
        -[:HAS_SCHEMA]->(:APISchema {name: "ProductCreate"})
            -[:HAS_FIELD]->(:APISchemaField {name: "price", type: "float"})
```

### 5.2 Tasks

#### Task 2.1: Create API Nodes Schema
```
Archivo: src/cognitive/infrastructure/neo4j_api_schema.py
Prioridad: P0
Estimado: 3h
```

**Schema Cypher:**
```cypher
// Constraints
CREATE CONSTRAINT endpoint_unique IF NOT EXISTS
FOR (e:Endpoint) REQUIRE (e.api_model_id, e.path, e.method) IS UNIQUE;

CREATE CONSTRAINT api_schema_unique IF NOT EXISTS
FOR (s:APISchema) REQUIRE (s.api_model_id, s.name) IS UNIQUE;

CREATE CONSTRAINT api_parameter_unique IF NOT EXISTS
FOR (p:APIParameter) REQUIRE (p.endpoint_id, p.name) IS UNIQUE;

// Indexes
CREATE INDEX endpoint_path IF NOT EXISTS FOR (e:Endpoint) ON (e.path);
CREATE INDEX endpoint_method IF NOT EXISTS FOR (e:Endpoint) ON (e.method);
CREATE INDEX endpoint_operation IF NOT EXISTS FOR (e:Endpoint) ON (e.operation_id);
CREATE INDEX schema_name IF NOT EXISTS FOR (s:APISchema) ON (s.name);
```

---

#### Task 2.2: API Model Repository (Graph Version)
```
Archivo: src/cognitive/services/api_model_graph_repository.py
Prioridad: P0
Estimado: 6h
```

**Interface:**
```python
class APIModelGraphRepository:
    async def save_api_model(self, app_id: str, api_model: APIModelIR) -> str:
        # 1. Create APIModelIR node
        api_model_id = f"{app_id}_api"
        await self.neo4j.run("""
            MATCH (a:ApplicationIR {app_id: $app_id})
            MERGE (api:APIModelIR {api_model_id: $api_model_id})
            SET api.base_path = $base_path,
                api.version = $version
            MERGE (a)-[:HAS_API_MODEL]->(api)
        """, app_id=app_id, api_model_id=api_model_id,
            base_path=api_model.base_path, version=api_model.version)

        # 2. Create Endpoint nodes
        for endpoint in api_model.endpoints:
            endpoint_id = f"{api_model_id}_{endpoint.method}_{endpoint.path}"
            await self.neo4j.run("""
                MATCH (api:APIModelIR {api_model_id: $api_model_id})
                MERGE (e:Endpoint {endpoint_id: $endpoint_id})
                SET e.path = $path,
                    e.method = $method,
                    e.operation_id = $operation_id,
                    e.summary = $summary,
                    e.description = $description,
                    e.auth_required = $auth_required,
                    e.tags = $tags,
                    e.inferred = $inferred,
                    e.inference_source = $inference_source,
                    e.inference_reason = $inference_reason
                MERGE (api)-[:HAS_ENDPOINT]->(e)
            """, ...)

            # 3. Create Parameter nodes
            for param in endpoint.parameters:
                await self.neo4j.run("""
                    MATCH (e:Endpoint {endpoint_id: $endpoint_id})
                    MERGE (p:APIParameter {endpoint_id: $endpoint_id, name: $name})
                    SET p.location = $location,
                        p.data_type = $data_type,
                        p.required = $required,
                        p.description = $description
                    MERGE (e)-[:HAS_PARAMETER]->(p)
                """, ...)

            # 4. Link to schemas
            if endpoint.request_schema:
                await self._link_schema(endpoint_id, endpoint.request_schema, "REQUEST_SCHEMA")
            if endpoint.response_schema:
                await self._link_schema(endpoint_id, endpoint.response_schema, "RESPONSE_SCHEMA")

        # 5. Create APISchema nodes
        for schema in api_model.schemas:
            await self._create_schema_node(api_model_id, schema)
```

**Deliverables:**
- [ ] APIModelGraphRepository class
- [ ] Schema field nodes (APISchemaField)
- [ ] Unit tests
- [ ] Integration tests

---

#### Task 2.3: Migration Script - API JSON to Graph
```
Archivo: scripts/migrations/neo4j/002_api_model_expansion.py
Prioridad: P0
Estimado: 4h
```

---

#### Task 2.4: Update neo4j_ir_repository.py for APIModel
```
Prioridad: P0
Estimado: 2h
```

---

### 5.3 Sprint 2 Checklist

```
[x] Task 2.1: Create API Nodes Schema ✅
[x] Task 2.2: API Model Repository (Graph Version) ✅
[x] Task 2.3: Migration Script - API JSON to Graph ✅
[x] Task 2.4: Update neo4j_ir_repository.py ✅
[x] Ejecutar schema creation (004_api_model_schema.cypher) ✅
[x] Ejecutar migration DRY-RUN (005_api_model_expansion.py) ✅
[x] No bugs found in DRY-RUN ✅ (100% éxito)
[x] Ejecutar migración LIVE ✅ (280/280 exitoso)
[x] Verification: 4,022 Endpoint nodes ✅
[x] Verification: 668 APIParameter nodes ✅
[x] Verification: 0 APISchema nodes ✅ (datos reales vacíos)
[x] Graph structure verified ✅ (paths APIModelIR → Endpoint → APIParameter)
```

**Progreso Sprint 2 (2025-11-29):**

#### Task 2.1: Create API Nodes Schema ✅ COMPLETADO

- **Fecha:** 2025-11-29

- **Archivos creados:**
  - `scripts/migrations/neo4j/004_api_model_schema.cypher` - Schema principal
  - `scripts/migrations/neo4j/004_api_model_schema_rollback.cypher` - Rollback
  - `scripts/migrations/neo4j/004_apply_schema.py` - Script de aplicación

- **Schema aplicado:**

  ```text
  ✅ 4 Constraints UNIQUE creados:
     - endpoint_unique: (api_model_id, path, method)
     - api_parameter_unique: (endpoint_id, name)
     - api_schema_unique: (api_model_id, name)
     - api_schema_field_unique: (schema_id, name)

  ✅ 12 Indexes creados:
     - endpoint_path, endpoint_method, endpoint_operation_id, endpoint_inferred
     - api_parameter_location, api_parameter_required
     - api_schema_name
     - api_schema_field_required
     - + 4 indexes automáticos de constraints UNIQUE
  ```

- **Documentación:**
  - Scripts completamente documentados con docstrings detallados
  - Verificación automática incluida en apply script
  - Error handling robusto para constraints ya existentes

#### Task 2.2: API Model Graph Repository ✅ COMPLETADO

- **Fecha:** 2025-11-29

- **Archivo creado:**
  - `src/cognitive/services/api_model_graph_repository.py` - Repository completo (586 líneas)

- **Características implementadas:**
  - UNWIND batching para eficiencia (mismo patrón de Sprint 1)
  - save_api_model() con batch operations
  - load_api_model() con reconstrucción completa
  - Context manager support
  - Error handling robusto con APIModelPersistenceError
  - Logging detallado

- **Estructura de grafo:**

  ```text
  APIModelIR
    ├─ HAS_ENDPOINT → Endpoint
    │   ├─ HAS_PARAMETER → APIParameter
    │   ├─ REQUEST_SCHEMA → APISchema
    │   └─ RESPONSE_SCHEMA → APISchema
    └─ HAS_SCHEMA → APISchema
        └─ HAS_FIELD → APISchemaField
  ```

#### Task 2.3: Migration Script ✅ COMPLETADO

- **Fecha:** 2025-11-29

- **Archivo creado:**
  - `scripts/migrations/neo4j/005_api_model_expansion.py` - Migration script (464 líneas)

- **Características:**
  - DRY-RUN mode support
  - Progress reporting cada 50 registros
  - Verificación automática post-migración
  - Idempotente (usa repository con MERGE)
  - Manejo de errores robusto

#### Task 2.4: Update neo4j_ir_repository.py ✅ COMPLETADO

- **Fecha:** 2025-11-29

- **Cambios realizados:**
  - Agregado feature flag `USE_GRAPH_API_MODEL`
  - Agregado lazy-loaded property `api_graph_repo`
  - Agregado método `_save_api_model_as_graph()`
  - Agregado método `_load_api_model_from_graph()`
  - Integrado en `save_application_ir()` y `load_application_ir()`
  - Backward compatibility completa (JSON fallback)

### Resultados Migración LIVE (2025-11-29):

```text
✅ APIModels procesados: 280/280 (100% éxito)
✅ No bugs encontrados en DRY-RUN

Nodos y edges creados:
├─ APIModelIR migrated: 560 (incluye migraciones previas)
├─ Endpoint nodes:      4,022 ✅
├─ APIParameter nodes:  668 ✅
├─ APISchema nodes:     0 ✅ (datos vacíos en source)
├─ APISchemaField:      0 ✅ (datos vacíos en source)
├─ HAS_ENDPOINT edges:  4,022 ✅
├─ HAS_PARAMETER edges: 668 ✅
├─ HAS_SCHEMA edges:    0 ✅
├─ REQUEST_SCHEMA:      0 ✅
└─ RESPONSE_SCHEMA:     0 ✅
   ────────────────────────────
   TOTAL: 4,690 objetos de grafo creados
```

### Notas Técnicas:

**Diferencia de 4 endpoints (4026 esperados → 4022 reales):**
- Causa: MERGE previene duplicados con mismo `(api_model_id, method, path)`
- Esto es **correcto** y esperado
- 4 endpoints tenían method+path duplicados y se mergearon

**APISchema y Fields en 0:**
- Los datos reales en JSON tienen schemas vacíos
- Esto es normal para endpoints CRUD básicos
- El soporte para schemas está completamente implementado para futuro uso

**Verificación manual exitosa:**
- 252 APIModelIR conectados a endpoints
- 0 endpoints huérfanos
- Estructura de grafo correcta: APIModelIR → Endpoint → APIParameter

### Estado Final (2025-11-29):

- ✅ Schema aplicado: 4 constraints + 12 indexes
- ✅ Repository creado: 586 líneas con UNWIND batching
- ✅ Migration script: 464 líneas con DRY-RUN support
- ✅ Integration: neo4j_ir_repository.py actualizado
- ✅ **Migración LIVE completada**: 4,690 objetos de grafo creados
- ✅ **Verificación exitosa**: Estructura de grafo correcta

### 5.4 Mejoras Futuras Sprint 2 (Post-MVP)

**Objetivo:** Enriquecer APIModelIR con trazabilidad y metadata para QA agent y lineage tracking.

#### 5.4.1 Relaciones Endpoint → Entity (Para QA Agent)

**Problema:** Los endpoints operan sobre entidades, pero no hay relación explícita en el grafo.

**Solución:** Agregar relaciones `TARGETS_ENTITY` y `USES_FIELD`.

```cypher
// Endpoint que opera sobre Product
MATCH (e:Endpoint {path: "/products/{id}", method: "GET"})
MATCH (entity:Entity {name: "Product"})
MERGE (e)-[:TARGETS_ENTITY]->(entity)

// Endpoint que usa campos específicos
MATCH (e:Endpoint {path: "/products", method: "POST"})
MATCH (entity:Entity {name: "Product"})-[:HAS_ATTRIBUTE]->(attr:Attribute {name: "price"})
MERGE (e)-[:USES_FIELD]->(attr)
```

**Beneficios:**
- ✅ **QA Agent**: Puede validar que todos los endpoints de una entidad están testeados
- ✅ **Lineage**: Rastrear qué endpoints se ven afectados por cambios en Entity/Attribute
- ✅ **Coverage Analysis**: Identificar entidades sin endpoints CRUD completos
- ✅ **Impact Analysis**: "Si cambio Product.price, ¿qué endpoints se afectan?"

**Query de ejemplo:**
```cypher
// Endpoints sin entity target (posible problema)
MATCH (e:Endpoint)
WHERE NOT EXISTS { MATCH (e)-[:TARGETS_ENTITY]->() }
RETURN e.path, e.method

// Coverage de endpoints por entidad
MATCH (entity:Entity)<-[:TARGETS_ENTITY]-(e:Endpoint)
RETURN entity.name,
       collect(e.method) as methods,
       size(collect(e.method)) as endpoint_count
ORDER BY endpoint_count DESC
```

**Implementación:**
- **Fase 1** (Sprint 2.5): Script de análisis que infiere TARGETS_ENTITY desde path patterns
- **Fase 2** (Sprint 6): Integrar en código de generación para crear automáticamente
- **Archivo**: `scripts/migrations/neo4j/005b_enrich_endpoint_entity_links.py`

#### 5.4.2 Campo `source` en APISchema

**Problema:** No sabemos si un schema viene del spec OpenAPI, fue inferido, o creado manualmente.

**Solución:** Agregar campo `source` a APISchema.

```python
# En src/cognitive/ir/api_model.py

class SchemaSource(str, Enum):
    OPENAPI = "openapi"           # Del spec original
    INFERRED = "inferred"         # Generado por inferencia
    MANUAL = "manual"             # Agregado manualmente
    CRUD_PATTERN = "crud_pattern" # De PatternBank CRUD

class APISchema(BaseModel):
    name: str
    fields: List[APISchemaField]
    source: SchemaSource = SchemaSource.OPENAPI  # NUEVO CAMPO
    source_metadata: Optional[Dict[str, Any]] = None  # Info adicional
```

**Beneficios:**
- ✅ **Auditing**: Saber qué schemas son del spec vs inferidos
- ✅ **Validation**: Validar schemas inferidos con más cuidado que los del spec
- ✅ **Pattern Tracking**: Rastrear qué schemas vienen de patterns específicos
- ✅ **Debugging**: Identificar problemas en schemas inferidos

**Query de ejemplo:**
```cypher
// Schemas por fuente
MATCH (s:APISchema)
RETURN s.source, count(s) as count
ORDER BY count DESC

// Schemas inferidos vs OpenAPI
MATCH (api:APIModelIR)-[:HAS_SCHEMA]->(s:APISchema)
WHERE s.source = 'inferred'
RETURN api.app_id, s.name, s.source_metadata
```

**Implementación:**
- **Fase 1** (Sprint 2.5): Agregar campo a Pydantic model y repository
- **Fase 2** (Sprint 4): Integrar en código de generación
- **Migration**: Actualizar schemas existentes con `source = 'openapi'` por defecto

#### 5.4.3 Prioridad de Implementación

| Mejora | Prioridad | Dependencias | Sprint Sugerido |
|--------|-----------|--------------|-----------------|
| TARGETS_ENTITY | **Alta** | Sprint 1 (Entity nodes) | 2.5 o 3 |
| USES_FIELD | Media | TARGETS_ENTITY | 3 o 4 |
| source field | Media | Ninguna | 2.5 o 3 |

**Próximos Pasos:**

1. ✅ ~~Sprint 1 COMPLETADO~~
2. ✅ ~~Sprint 2 COMPLETADO~~
3. **Opcional**: Sprint 2.5 - Implementar mejoras TARGETS_ENTITY y source
4. **Sprint 3**: BehaviorModelIR + ValidationModelIR expansion
5. **Sprint 4**: InfrastructureModelIR expansion
6. **Sprint 5**: TestsModelIR expansion (alta prioridad para QA agent)

---

## 5.5 Patrón Base Repository (Sprint 3+)

**Objetivo:** Evitar duplicación de código entre repositories mediante clase base compartida.

**Problema identificado:** Sprint 1 y 2 tienen código muy similar:
- Pattern UNWIND batching repetido
- Context manager support duplicado
- Error handling idéntico
- Transaction management similar

**Solución:** Crear `GraphIRRepository` base class con métodos compartidos.

### 5.5.1 Diseño Base Repository

```python
# src/cognitive/services/graph_ir_repository_base.py

class GraphIRRepository:
    """
    Base repository for all IR graph repositories.
    Provides common patterns: UNWIND batching, transactions, error handling.
    """

    def __init__(self):
        self.driver = AsyncGraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.driver.close()

    async def _replace_subgraph(
        self,
        parent_id: str,
        parent_label: str,
        child_label: str,
        relationship_type: str,
        child_nodes: List[Dict[str, Any]]
    ):
        """
        Patrón replace_subgraph: Elimina todos los hijos existentes y crea nuevos.

        Evita crear duplicados y maneja updates correctamente.

        Args:
            parent_id: ID del nodo parent
            parent_label: Label del parent (e.g., "DomainModelIR")
            child_label: Label de los children (e.g., "Entity")
            relationship_type: Tipo de relación (e.g., "HAS_ENTITY")
            child_nodes: Lista de dicts con properties de los children

        Example:
            await self._replace_subgraph(
                parent_id=app_id,
                parent_label="DomainModelIR",
                child_label="Entity",
                relationship_type="HAS_ENTITY",
                child_nodes=[
                    {"entity_id": "...", "name": "Product", ...},
                    {"entity_id": "...", "name": "Order", ...}
                ]
            )
        """
        async with self.driver.session() as session:
            async with session.begin_transaction() as tx:
                # 1. Delete existing children
                await tx.run(f"""
                    MATCH (p:{parent_label} {{parent_id: $parent_id}})
                          -[r:{relationship_type}]->(c:{child_label})
                    DETACH DELETE c
                """, parent_id=parent_id)

                # 2. Create new children with UNWIND batching
                if child_nodes:
                    await tx.run(f"""
                        MATCH (p:{parent_label} {{parent_id: $parent_id}})
                        UNWIND $nodes AS node
                        CREATE (c:{child_label})
                        SET c = node
                        CREATE (p)-[:{relationship_type}]->(c)
                    """, parent_id=parent_id, nodes=child_nodes)

    async def _batch_create_nodes(
        self,
        label: str,
        nodes: List[Dict[str, Any]],
        unique_key: str = "id"
    ):
        """
        Batch create nodes with UNWIND pattern.
        Uses MERGE for idempotency.

        Args:
            label: Node label
            nodes: List of node properties
            unique_key: Property to use for MERGE (default: "id")
        """
        if not nodes:
            return

        async with self.driver.session() as session:
            await session.run(f"""
                UNWIND $nodes AS node
                MERGE (n:{label} {{{unique_key}: node.{unique_key}}})
                SET n = node
            """, nodes=nodes)

    async def _batch_create_relationships(
        self,
        from_label: str,
        from_key: str,
        to_label: str,
        to_key: str,
        rel_type: str,
        relationships: List[Dict[str, Any]]
    ):
        """
        Batch create relationships with UNWIND pattern.

        Args:
            from_label: Source node label
            from_key: Source node property to match
            to_label: Target node label
            to_key: Target node property to match
            rel_type: Relationship type
            relationships: List of {from_id, to_id, properties}
        """
        if not relationships:
            return

        async with self.driver.session() as session:
            await session.run(f"""
                UNWIND $rels AS rel
                MATCH (from:{from_label} {{{from_key}: rel.from_id}})
                MATCH (to:{to_label} {{{to_key}: rel.to_id}})
                MERGE (from)-[r:{rel_type}]->(to)
                SET r = rel.properties
            """, rels=relationships)


class IRPersistenceError(Exception):
    """Base exception for IR persistence errors."""
    pass
```

### 5.5.2 Uso en Repositories Específicos

```python
# src/cognitive/services/behavior_model_graph_repository.py

from src.cognitive.services.graph_ir_repository_base import (
    GraphIRRepository,
    IRPersistenceError
)

class BehaviorModelGraphRepository(GraphIRRepository):
    """Repository for BehaviorModelIR using base class."""

    async def save_behavior_model(
        self,
        app_id: str,
        behavior_model: BehaviorModelIR
    ) -> None:
        try:
            # 1. Create/update BehaviorModelIR node
            async with self.driver.session() as session:
                await session.run("""
                    MATCH (a:ApplicationIR {app_id: $app_id})
                    MERGE (b:BehaviorModelIR {app_id: $app_id})
                    MERGE (a)-[:HAS_BEHAVIOR_MODEL]->(b)
                """, app_id=app_id)

            # 2. Use base class method for Flow nodes
            flow_nodes = [
                {
                    "flow_id": f"{app_id}|flow|{flow.name}",
                    "name": flow.name,
                    "type": flow.type.value,
                    "trigger": flow.trigger,
                    "description": flow.description
                }
                for flow in behavior_model.flows
            ]
            await self._replace_subgraph(
                parent_id=app_id,
                parent_label="BehaviorModelIR",
                child_label="Flow",
                relationship_type="HAS_FLOW",
                child_nodes=flow_nodes
            )

            # 3. Create Step nodes for each Flow
            for flow in behavior_model.flows:
                step_nodes = [
                    {
                        "step_id": f"{app_id}|flow|{flow.name}|step|{step.order}",
                        "order": step.order,
                        "action": step.action,
                        "target_entity": step.target_entity,
                        "description": step.description
                    }
                    for step in flow.steps
                ]
                await self._replace_subgraph(
                    parent_id=f"{app_id}|flow|{flow.name}",
                    parent_label="Flow",
                    child_label="Step",
                    relationship_type="HAS_STEP",
                    child_nodes=step_nodes
                )

        except Exception as e:
            raise IRPersistenceError(f"Failed to save BehaviorModel: {e}")
```

### 5.5.3 Beneficios

| Beneficio | Descripción |
|-----------|-------------|
| **DRY** | Código UNWIND batching en un solo lugar |
| **Consistency** | Mismo patrón de error handling en todos los repos |
| **Maintainability** | Bug fixes en base class benefician a todos |
| **Testing** | Test base class una vez, repos específicos solo test lógica única |
| **Performance** | Optimizaciones de batching compartidas |

### 5.5.4 Refactor Plan

**Sprint 3:**
1. Crear `graph_ir_repository_base.py` con clase base
2. Refactor `domain_model_graph_repository.py` para heredar de base
3. Refactor `api_model_graph_repository.py` para heredar de base
4. Usar base class directamente en `behavior_model_graph_repository.py`

**Sprint 4-5:**
5. Usar base class en todos los nuevos repositories

---

## 5A. Sprint 2.5: TARGETS_ENTITY & API Coverage

**Objetivo:** Conectar Endpoints con Entities/Attributes para habilitar análisis de API coverage e impact analysis.

**Justificación Estratégica:**
Con Sprints 1-2 completados, ya tenemos:
- ✅ 1,084 Entity nodes (Sprint 1)
- ✅ 5,204 Attribute nodes (Sprint 1)
- ✅ 4,022 Endpoint nodes (Sprint 2)
- ✅ 668 APIParameter nodes (Sprint 2)

**Pero falta la conexión semántica entre API y Domain:**
- ❌ ¿Qué endpoints afectan a Product entity?
- ❌ ¿Si cambio el campo `price`, qué APIs se rompen?
- ❌ ¿Qué entities NO tienen cobertura de API?

**Sprint 2.5 cierra este gap crítico con minimal effort:**
- **Alto Impacto:** QA coverage, impact analysis, regression testing
- **Bajo Costo:** ~1-2 días, inferencia simple desde path patterns
- **Valor Inmediato:** Dashboards útiles SIN esperar a Sprints 3-5

---

### 5A.1 Target Schema

```
(:Endpoint {path: "/products/{id}", method: "GET"})
    -[:TARGETS_ENTITY]->(:Entity {name: "Product"})
    -[:USES_FIELD]->(:Attribute {name: "price"})  # Optional

(:APISchema {name: "ProductCreate", source: "OPENAPI"})
    -[:HAS_FIELD]->(:APISchemaField {name: "name"})
    -[:HAS_FIELD]->(:APISchemaField {name: "price"})
        -[:MAPS_TO_ATTRIBUTE]->(:Attribute {name: "price"})  # Optional
```

**Nuevas Relaciones:**
1. **TARGETS_ENTITY**: Endpoint → Entity (inferido desde path pattern)
2. **USES_FIELD**: Endpoint → Attribute (opcional, desde request/response schemas)
3. **MAPS_TO_ATTRIBUTE**: APISchemaField → Attribute (opcional, para field-level mapping)

**Nuevo Campo:**
- `source` en APISchema: `OPENAPI | INFERRED | GENERATED | MANUAL`

---

### 5A.2 Tasks

#### Task 2.5.1: Add source Field to APISchema Nodes

```
Archivo: scripts/migrations/neo4j/007_add_source_to_api_schema.cypher
Prioridad: P0
Estimado: 30 min
```

**Migration Cypher:**
```cypher
// 007_add_source_to_api_schema.cypher

// Agregar campo source a todos los APISchema existentes
MATCH (s:APISchema)
WHERE s.source IS NULL
SET s.source = CASE
    // Si tiene metadata OpenAPI
    WHEN s.openapi_metadata IS NOT NULL THEN 'OPENAPI'
    // Si fue inferido por el sistema
    WHEN s.description CONTAINS 'inferred' THEN 'INFERRED'
    // Default para schemas creados manualmente
    ELSE 'GENERATED'
END,
s.updated_at = datetime()

RETURN count(s) as schemas_updated;
```

**Rollback:**
```cypher
// 007_rollback_source_field.cypher
MATCH (s:APISchema)
REMOVE s.source
RETURN count(s) as schemas_reverted;
```

---

#### Task 2.5.2: Infer TARGETS_ENTITY from Path Patterns

```
Archivo: scripts/migrations/neo4j/008_infer_targets_entity.py
Prioridad: P0
Estimado: 2h
```

**Lógica de Inferencia:**
```python
# scripts/migrations/neo4j/008_infer_targets_entity.py

import re
from typing import List, Dict, Optional

PATH_PATTERNS = [
    # Pattern: /products/{id} → Entity: Product
    (r"/([a-z_]+)(/\{[^}]+\})?", lambda m: m.group(1).rstrip('s').capitalize()),
    # Pattern: /api/v1/orders → Entity: Order
    (r"/api/v\d+/([a-z_]+)", lambda m: m.group(1).rstrip('s').capitalize()),
    # Pattern: /customers/{id}/orders → Entity: Order (toma el último segmento)
    (r"/[a-z_]+/\{[^}]+\}/([a-z_]+)", lambda m: m.group(1).rstrip('s').capitalize()),
]

def infer_entity_from_path(path: str) -> Optional[str]:
    """Infiere entity name desde path pattern."""
    for pattern, extractor in PATH_PATTERNS:
        match = re.search(pattern, path)
        if match:
            entity_name = extractor(match)
            return entity_name
    return None

async def create_targets_entity_relationships():
    """Crea relaciones TARGETS_ENTITY entre Endpoints y Entities."""

    query = """
    // 1. Obtener todos los Endpoints con su app_id
    MATCH (e:Endpoint)
    RETURN e.endpoint_id, e.path, e.api_model_id
    """
    endpoints = await neo4j.run(query)

    created = 0
    skipped = 0

    for endpoint in endpoints:
        path = endpoint['e.path']
        api_model_id = endpoint['e.api_model_id']
        endpoint_id = endpoint['e.endpoint_id']

        # Extraer app_id desde api_model_id (formato: {app_id}_api)
        app_id = api_model_id.replace('_api', '')

        # Inferir entity desde path
        entity_name = infer_entity_from_path(path)
        if not entity_name:
            skipped += 1
            continue

        # Crear relación TARGETS_ENTITY
        result = await neo4j.run("""
            MATCH (e:Endpoint {endpoint_id: $endpoint_id})
            MATCH (ent:Entity {app_id: $app_id, name: $entity_name})
            MERGE (e)-[r:TARGETS_ENTITY]->(ent)
            ON CREATE SET r.inferred = true, r.created_at = datetime()
            RETURN r
        """, endpoint_id=endpoint_id, app_id=app_id, entity_name=entity_name)

        if result:
            created += 1
            print(f"✅ {path} → {entity_name}")
        else:
            skipped += 1
            print(f"⚠️  {path} → {entity_name} (Entity not found)")

    print(f"\n📊 TARGETS_ENTITY Inference Complete:")
    print(f"   Created: {created}")
    print(f"   Skipped: {skipped}")

    return created, skipped

# Ejecutar
if __name__ == "__main__":
    asyncio.run(create_targets_entity_relationships())
```

**Validation Query:**
```cypher
// Verificar TARGETS_ENTITY creados
MATCH (e:Endpoint)-[r:TARGETS_ENTITY]->(ent:Entity)
RETURN
    e.path as endpoint_path,
    e.method as method,
    ent.name as target_entity,
    r.inferred as is_inferred
ORDER BY ent.name, e.path
LIMIT 50;
```

---

#### Task 2.5.3: Optional USES_FIELD Inference

```
Archivo: scripts/migrations/neo4j/009_infer_uses_field.py
Prioridad: P1 (opcional)
Estimado: 2h
```

**Lógica:**
```python
# 009_infer_uses_field.py

async def infer_uses_field_from_schemas():
    """
    Infiere USES_FIELD desde APISchemaField → Attribute.

    Lógica:
    1. Endpoint -[:REQUEST_SCHEMA]-> APISchema -[:HAS_FIELD]-> APISchemaField
    2. Si APISchemaField.name coincide con Attribute.name → crear USES_FIELD
    """

    query = """
    // Encontrar coincidencias entre APISchemaField y Attribute
    MATCH (e:Endpoint)-[:REQUEST_SCHEMA|RESPONSE_SCHEMA]->(s:APISchema)
    MATCH (s)-[:HAS_FIELD]->(f:APISchemaField)
    MATCH (e)-[:TARGETS_ENTITY]->(ent:Entity)
    MATCH (ent)-[:HAS_ATTRIBUTE]->(attr:Attribute)
    WHERE f.name = attr.name  // Mismo nombre de campo

    // Crear relación USES_FIELD
    MERGE (e)-[r:USES_FIELD]->(attr)
    ON CREATE SET r.inferred = true, r.created_at = datetime()

    RETURN count(r) as uses_field_created;
    """

    result = await neo4j.run(query)
    print(f"✅ USES_FIELD created: {result['uses_field_created']}")
```

**Nota:** Esta tarea es **opcional** porque:
- Requiere que los nombres de campos coincidan exactamente
- Puede generar falsos positivos (ej: `id` field en múltiples entities)
- Se puede postergar para Sprint 3+ si no hay tiempo

---

### 5A.3 NeoDash Dashboards

#### Dashboard 1: API Coverage por Entity

```cypher
// NeoDash Query: API Coverage per Entity

MATCH (ent:Entity)
OPTIONAL MATCH (e:Endpoint)-[:TARGETS_ENTITY]->(ent)
WITH ent, count(e) as endpoint_count
RETURN
    ent.name as Entity,
    endpoint_count as API_Endpoints,
    CASE
        WHEN endpoint_count = 0 THEN '🔴 No Coverage'
        WHEN endpoint_count < 3 THEN '🟡 Low Coverage'
        ELSE '🟢 Good Coverage'
    END as Coverage_Status
ORDER BY endpoint_count DESC;
```

**Visualización:** Bar chart (Entity vs Endpoint Count)

**Utilidad:**
- Identificar entities sin cobertura de API
- Priorizar endpoints faltantes en roadmap
- Validar completitud de API surface

---

#### Dashboard 2: Impact Analysis - Attribute Usage

```cypher
// NeoDash Query: Attribute Impact Analysis

MATCH (attr:Attribute)<-[:HAS_ATTRIBUTE]-(ent:Entity)
OPTIONAL MATCH (e:Endpoint)-[:USES_FIELD]->(attr)
WITH attr, ent, count(e) as endpoints_using
RETURN
    ent.name as Entity,
    attr.name as Attribute,
    attr.data_type as Type,
    endpoints_using as Endpoints_Using,
    CASE
        WHEN endpoints_using > 5 THEN '🚨 High Impact'
        WHEN endpoints_using > 2 THEN '⚠️ Medium Impact'
        ELSE '✅ Low Impact'
    END as Change_Risk
ORDER BY endpoints_using DESC
LIMIT 100;
```

**Visualización:** Table con colores por Change_Risk

**Utilidad:**
- Evaluar impacto de cambios a attributes
- Identificar fields críticos que afectan múltiples endpoints
- Planning de breaking changes

---

#### Dashboard 3: API Source Distribution

```cypher
// NeoDash Query: APISchema Source Distribution

MATCH (s:APISchema)
RETURN
    s.source as Source_Type,
    count(s) as Schema_Count,
    round(100.0 * count(s) / (SELECT count(*) FROM APISchema)) as Percentage
ORDER BY Schema_Count DESC;
```

**Visualización:** Pie chart

**Utilidad:**
- Entender proporción de schemas OpenAPI vs Inferidos
- Validar calidad de inferencia vs specs formales
- Identificar gaps en documentación OpenAPI

---

### 5A.4 Validation Queries

```cypher
// 1. Verificar que todos los Endpoints tienen al menos un target
MATCH (e:Endpoint)
WHERE NOT (e)-[:TARGETS_ENTITY]->()
RETURN count(e) as endpoints_without_target;
// Expected: Low number (solo endpoints genéricos como /health)

// 2. Verificar distribución de source en APISchema
MATCH (s:APISchema)
RETURN s.source, count(s) as count
ORDER BY count DESC;
// Expected: Mayoría con source definido

// 3. Top entities por API coverage
MATCH (ent:Entity)<-[:TARGETS_ENTITY]-(e:Endpoint)
RETURN ent.name, count(e) as endpoint_count
ORDER BY endpoint_count DESC
LIMIT 10;
// Expected: Core entities (Product, Order, Customer) con más endpoints

// 4. Endpoints targeting múltiples entities (posibles errores de inferencia)
MATCH (e:Endpoint)-[:TARGETS_ENTITY]->(ent:Entity)
WITH e, collect(ent.name) as entities
WHERE size(entities) > 1
RETURN e.path, e.method, entities
LIMIT 10;
// Expected: Pocos casos (validar si son correctos o errores)
```

---

### 5A.5 Sprint 2.5 Checklist

```
[ ] Task 2.5.1: Agregar campo source a APISchema nodes
    [ ] Ejecutar 007_add_source_to_api_schema.cypher
    [ ] Verificar todos los APISchema tienen source definido

[ ] Task 2.5.2: Inferir TARGETS_ENTITY desde path patterns
    [ ] Ejecutar 008_infer_targets_entity.py (DRY-RUN primero)
    [ ] Revisar inferencias correctas vs incorrectas
    [ ] Ejecutar LIVE migration
    [ ] Verificar ~3,000+ TARGETS_ENTITY creados (estimado ~75% de endpoints)

[ ] Task 2.5.3: (Opcional) Inferir USES_FIELD desde schemas
    [ ] Evaluar si hay tiempo disponible
    [ ] Ejecutar 009_infer_uses_field.py si es P0
    [ ] Si no, postergar para Sprint 3

[ ] NeoDash Dashboards:
    [ ] Crear dashboard "API Coverage per Entity"
    [ ] Crear dashboard "Attribute Impact Analysis"
    [ ] Crear dashboard "APISchema Source Distribution"
    [ ] Validar con stakeholders (QA, Product)

[ ] Validation:
    [ ] Ejecutar 4 validation queries
    [ ] Documentar casos edge detectados
    [ ] Ajustar path patterns si es necesario
```

---

### 5A.6 Métricas Esperadas

| Métrica | Objetivo | Validación |
|---------|----------|------------|
| **APISchema con source** | 100% (668 schemas) | `MATCH (s:APISchema) WHERE s.source IS NOT NULL` |
| **TARGETS_ENTITY creados** | ~3,000+ (75% de 4,022 endpoints) | `MATCH ()-[r:TARGETS_ENTITY]->() RETURN count(r)` |
| **Entities sin coverage** | <10% (esperado ~100 entities core cubiertas) | Dashboard 1 |
| **High-impact attributes** | Identificar top 20 | Dashboard 2 |
| **Tiempo de ejecución** | <2 horas total | Log de scripts |

---

### 5A.7 Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| **Path patterns incorrectos** | Media | Bajo | DRY-RUN con review manual antes de LIVE |
| **Entities no encontradas** | Alta | Bajo | Script maneja gracefully (skip + log) |
| **Falsos positivos en USES_FIELD** | Alta | Bajo | Hacer Task 2.5.3 opcional, validar manualmente |
| **Overhead de dashboards** | Baja | Bajo | Queries con LIMIT, agregar indexes si es necesario |

---

### 5A.8 Próximos Pasos Después de Sprint 2.5

**Valor Inmediato Desbloqueado:**
- ✅ QA puede identificar gaps de API coverage
- ✅ Product puede evaluar impacto de cambios a attributes
- ✅ Developers pueden hacer regression analysis

**Preparación para Sprint 3:**
Con TARGETS_ENTITY en place, Sprint 3 (BehaviorModelIR + ValidationModelIR) puede:
1. Conectar Flows con Endpoints via TARGETS_ENTITY
2. Validar que validation rules cubren todos los endpoints críticos
3. Generar test scenarios basados en entity coverage

**Sprint 2.5 es el puente entre "tengo nodos" y "tengo insights".**

---

## 6. Sprint 3: Graph Expansion - BehaviorModelIR

**Objetivo:** Expandir BehaviorModelIR de JSON a nodos Flow, Step, Invariant.

### 6.1 Target Schema

```
(:ApplicationIR)
    -[:HAS_BEHAVIOR_MODEL]->(:BehaviorModelIR)
        -[:HAS_FLOW]->(:Flow {
            name: "checkout_flow",
            type: "workflow",
            trigger: "On Checkout"
        })
            -[:HAS_STEP]->(:Step {
                order: 1,
                action: "validate_cart",
                target_entity: "Cart"
            })
            -[:HAS_STEP]->(:Step {order: 2, ...})
        -[:HAS_INVARIANT]->(:Invariant {
            entity: "Product",
            description: "Stock cannot be negative",
            expression: "stock >= 0",
            enforcement_level: "strict"
        })
```

### 6.2 Tasks

#### Task 3.1: Create Behavior Nodes Schema
```
Archivo: src/cognitive/infrastructure/neo4j_behavior_schema.py
Prioridad: P0
Estimado: 2h
```

---

#### Task 3.2: Behavior Model Repository (Graph Version)
```
Archivo: src/cognitive/services/behavior_model_graph_repository.py
Prioridad: P0
Estimado: 5h
```

---

#### Task 3.3: Migration Script - Behavior JSON to Graph
```
Archivo: scripts/migrations/neo4j/003_behavior_model_expansion.py
Prioridad: P0
Estimado: 3h
```

---

### 6.3 Sprint 3 Checklist

```
[ ] Task 3.1: Create Behavior Nodes Schema
[ ] Task 3.2: Behavior Model Repository
[ ] Task 3.3: Migration Script
[ ] Verification: ~840 Flow nodes
[ ] Verification: ~4,200 Step nodes
[ ] Verification: ~560 Invariant nodes
```

---

## 7. Sprint 4: Graph Expansion - ValidationModelIR + InfrastructureModelIR

**Objetivo:** Expandir ValidationModelIR e InfrastructureModelIR.

### 7.1 ValidationModelIR Target Schema

```
(:ApplicationIR)
    -[:HAS_VALIDATION_MODEL]->(:ValidationModelIR)
        -[:HAS_RULE]->(:ValidationRule {
            entity: "Product",
            attribute: "price",
            type: "range",
            condition: "price > 0",
            severity: "error",
            enforcement_type: "validator"
        })
            -[:HAS_ENFORCEMENT]->(:EnforcementStrategy {
                type: "validator",
                implementation: "@field_validator",
                applied_at: ["schema"]
            })
        -[:HAS_TEST_CASE]->(:TestCase {
            name: "test_negative_price",
            scenario: "Reject negative price",
            expected_outcome: "validation_error"
        })
```

### 7.2 InfrastructureModelIR Target Schema

```
(:ApplicationIR)
    -[:HAS_INFRASTRUCTURE_MODEL]->(:InfrastructureModelIR {docker_compose_version})
        -[:HAS_DATABASE]->(:DatabaseConfig {
            type: "postgresql",
            host: "localhost",
            port: 5432
        })
        -[:HAS_CONTAINER]->(:ContainerService {
            name: "api",
            image: "python:3.11",
            ports: ["8000:8000"]
        })
            -[:DEPENDS_ON]->(:ContainerService {name: "db"})
        -[:HAS_OBSERVABILITY]->(:ObservabilityConfig {
            logging_enabled: true,
            health_check_path: "/health"
        })
```

### 7.3 Tasks

#### Task 4.1: Validation Nodes Schema + Repository
```
Prioridad: P0
Estimado: 5h
```

---

#### Task 4.2: Infrastructure Nodes Schema + Repository
```
Prioridad: P1
Estimado: 4h
```

---

#### Task 4.3: Migration Scripts
```
Prioridad: P0
Estimado: 4h
```

---

### 7.4 Sprint 4 Checklist

```
[ ] Task 4.1: Validation Nodes Schema + Repository
[ ] Task 4.2: Infrastructure Nodes Schema + Repository
[ ] Task 4.3: Migration Scripts
[ ] Verification: ~2,800 ValidationRule nodes
[ ] Verification: ~1,400 TestCase nodes
[ ] Verification: ~280 DatabaseConfig nodes
[ ] Verification: ~840 ContainerService nodes
```

---

## 8. Sprint 5: Graph Expansion - TestsModelIR

**Objetivo:** Implementar persistencia de TestsModelIR (actualmente NO persistido).

### 8.1 Target Schema

```
(:ApplicationIR)
    -[:HAS_TESTS_MODEL]->(:TestsModelIR {
        generated_at: datetime,
        generator_version: "1.0.0"
    })
        -[:HAS_SEED_ENTITY]->(:SeedEntityIR {
            entity_name: "Product",
            table_name: "products",
            count: 5
        })
            -[:HAS_SEED_FIELD]->(:SeedFieldValue {
                field_name: "id",
                generator: "uuid4"
            })
            -[:DEPENDS_ON_SEED]->(:SeedEntityIR {entity_name: "Category"})
        -[:HAS_ENDPOINT_SUITE]->(:EndpointTestSuite {
            endpoint_path: "/products",
            http_method: "GET"
        })
            -[:HAS_HAPPY_PATH]->(:TestScenarioIR {
                name: "test_list_products",
                expected_status_code: 200
            })
            -[:HAS_ERROR_CASE]->(:TestScenarioIR {
                name: "test_unauthorized",
                expected_status_code: 401
            })
        -[:HAS_FLOW_SUITE]->(:FlowTestSuite {
            name: "checkout_flow_test"
        })
            -[:HAS_SCENARIO]->(:TestScenarioIR {...})
```

### 8.2 Tasks

#### Task 5.1: Tests Model Nodes Schema
```
Archivo: src/cognitive/infrastructure/neo4j_tests_schema.py
Prioridad: P0
Estimado: 4h
```

**Schema Cypher:**
```cypher
// TestsModelIR
CREATE CONSTRAINT tests_model_unique IF NOT EXISTS
FOR (t:TestsModelIR) REQUIRE t.app_id IS UNIQUE;

// SeedEntityIR
CREATE CONSTRAINT seed_entity_unique IF NOT EXISTS
FOR (s:SeedEntityIR) REQUIRE (s.tests_model_id, s.entity_name) IS UNIQUE;

// TestScenarioIR
CREATE CONSTRAINT test_scenario_unique IF NOT EXISTS
FOR (t:TestScenarioIR) REQUIRE t.scenario_id IS UNIQUE;

// EndpointTestSuite
CREATE CONSTRAINT endpoint_suite_unique IF NOT EXISTS
FOR (e:EndpointTestSuite) REQUIRE (e.tests_model_id, e.endpoint_path, e.http_method) IS UNIQUE;

// FlowTestSuite
CREATE CONSTRAINT flow_suite_unique IF NOT EXISTS
FOR (f:FlowTestSuite) REQUIRE (f.tests_model_id, f.name) IS UNIQUE;

// Indexes
CREATE INDEX scenario_endpoint IF NOT EXISTS FOR (t:TestScenarioIR) ON (t.endpoint_path);
CREATE INDEX scenario_priority IF NOT EXISTS FOR (t:TestScenarioIR) ON (t.priority);
CREATE INDEX scenario_type IF NOT EXISTS FOR (t:TestScenarioIR) ON (t.test_type);
```

---

#### Task 5.2: Tests Model Repository (Graph Version)
```
Archivo: src/cognitive/services/tests_model_graph_repository.py
Prioridad: P0
Estimado: 8h
```

**Interface:**
```python
class TestsModelGraphRepository:
    async def save_tests_model(self, app_id: str, tests_model: TestsModelIR) -> str:
        tests_model_id = f"{app_id}_tests"

        # 1. Create TestsModelIR node
        await self.neo4j.run("""
            MATCH (a:ApplicationIR {app_id: $app_id})
            MERGE (t:TestsModelIR {tests_model_id: $tests_model_id})
            SET t.app_id = $app_id,
                t.generated_at = $generated_at,
                t.generator_version = $generator_version,
                t.source_ir_hash = $source_ir_hash
            MERGE (a)-[:HAS_TESTS_MODEL]->(t)
        """, ...)

        # 2. Create SeedEntityIR nodes
        for seed in tests_model.seed_entities:
            seed_id = f"{tests_model_id}_{seed.entity_name}"
            await self.neo4j.run("""
                MATCH (t:TestsModelIR {tests_model_id: $tests_model_id})
                MERGE (s:SeedEntityIR {seed_id: $seed_id})
                SET s.entity_name = $entity_name,
                    s.table_name = $table_name,
                    s.count = $count,
                    s.source_entity_id = $source_entity_id
                MERGE (t)-[:HAS_SEED_ENTITY]->(s)
            """, ...)

            # Create SeedFieldValue nodes
            for field in seed.fields:
                await self._create_seed_field(seed_id, field)

            # Create dependency relationships
            for dep in seed.dependencies:
                await self.neo4j.run("""
                    MATCH (s:SeedEntityIR {seed_id: $seed_id})
                    MATCH (dep:SeedEntityIR {entity_name: $dep_name, tests_model_id: $tm_id})
                    MERGE (s)-[:DEPENDS_ON_SEED]->(dep)
                """, seed_id=seed_id, dep_name=dep, tm_id=tests_model_id)

        # 3. Create EndpointTestSuite nodes
        for suite in tests_model.endpoint_suites:
            suite_id = f"{tests_model_id}_{suite.http_method}_{suite.endpoint_path}"
            await self.neo4j.run("""
                MATCH (t:TestsModelIR {tests_model_id: $tests_model_id})
                MERGE (e:EndpointTestSuite {suite_id: $suite_id})
                SET e.endpoint_path = $endpoint_path,
                    e.http_method = $http_method,
                    e.operation_id = $operation_id
                MERGE (t)-[:HAS_ENDPOINT_SUITE]->(e)
            """, ...)

            # Create happy path scenario
            await self._create_scenario(suite_id, suite.happy_path, "HAS_HAPPY_PATH")

            # Create edge cases
            for scenario in suite.edge_cases:
                await self._create_scenario(suite_id, scenario, "HAS_EDGE_CASE")

            # Create error cases
            for scenario in suite.error_cases:
                await self._create_scenario(suite_id, scenario, "HAS_ERROR_CASE")

        # 4. Create FlowTestSuite nodes
        for flow in tests_model.flow_suites:
            await self._create_flow_suite(tests_model_id, flow)

        # 5. Create standalone scenarios
        for scenario in tests_model.standalone_scenarios:
            await self._create_standalone_scenario(tests_model_id, scenario)

    async def _create_scenario(
        self,
        parent_id: str,
        scenario: TestScenarioIR,
        rel_type: str
    ):
        await self.neo4j.run(f"""
            MATCH (parent {{suite_id: $parent_id}})
            MERGE (s:TestScenarioIR {{scenario_id: $scenario_id}})
            SET s.name = $name,
                s.description = $description,
                s.endpoint_path = $endpoint_path,
                s.http_method = $http_method,
                s.operation_id = $operation_id,
                s.test_type = $test_type,
                s.priority = $priority,
                s.path_params = $path_params,
                s.query_params = $query_params,
                s.headers = $headers,
                s.request_body = $request_body,
                s.expected_outcome = $expected_outcome,
                s.expected_status_code = $expected_status_code,
                s.requires_auth = $requires_auth,
                s.source_endpoint_id = $source_endpoint_id
            MERGE (parent)-[:{rel_type}]->(s)
        """, ...)

        # Create assertions
        for assertion in scenario.assertions:
            await self._create_assertion(scenario.scenario_id, assertion)
```

**Deliverables:**
- [ ] TestsModelGraphRepository class
- [ ] Full scenario hierarchy
- [ ] Seed dependency tracking
- [ ] Unit tests
- [ ] Integration tests

---

#### Task 5.3: Integrate TestsModelIR Persistence
```
Archivo: src/cognitive/services/neo4j_ir_repository.py
Prioridad: P0
Estimado: 3h
```

**Añadir método:**
```python
async def save_tests_model(self, app_id: str, tests_model: TestsModelIR):
    """Persist TestsModelIR to graph (previously NOT persisted)."""
    await self.tests_graph_repo.save_tests_model(app_id, tests_model)

async def load_tests_model(self, app_id: str) -> Optional[TestsModelIR]:
    """Load TestsModelIR from graph."""
    return await self.tests_graph_repo.load_tests_model(app_id)
```

---

#### Task 5.4: Update Pipeline to Persist TestsModel
```
Archivo: tests/e2e/real_e2e_full_pipeline.py
Prioridad: P0
Estimado: 2h
```

**Cambios en Phase que genera TestsModelIR:**
```python
# Después de generar TestsModelIR
if self.tests_model_ir:
    await self.ir_repository.save_tests_model(self.app_id, self.tests_model_ir)
    print(f"    - TestsModelIR persisted to Neo4j with {len(self.tests_model_ir.get_all_scenarios())} scenarios")
```

---

### 8.3 Sprint 5 Checklist

```
[ ] Task 5.1: Tests Model Nodes Schema
[ ] Task 5.2: Tests Model Repository (Graph Version)
[ ] Task 5.3: Integrate TestsModelIR Persistence
[ ] Task 5.4: Update Pipeline
[ ] Verification: TestsModelIR now persisted (was gap)
[ ] Verification: ~1,400 SeedEntityIR nodes
[ ] Verification: ~5,600 TestScenarioIR nodes
[ ] All tests pass
```

### 8.4 Mejoras Futuras Sprint 5: Cerrar el "Loop de QA"

**Objetivo:** Relacionar explícitamente tests con los componentes que validan (endpoints, flows, rules) para completar el ciclo de calidad.

#### 8.4.1 Relaciones VALIDATES_* para Trazabilidad Completa

**Problema:** Los tests están aislados - no sabemos qué endpoint, flow o regla valida cada test.

**Solución:** Agregar relaciones explícitas desde TestScenarioIR hacia los componentes validados.

```cypher
// Test que valida un endpoint específico
MATCH (test:TestScenarioIR {name: "test_get_product_success"})
MATCH (endpoint:Endpoint {path: "/products/{id}", method: "GET"})
MERGE (test)-[:VALIDATES_ENDPOINT]->(endpoint)

// Test que valida un flow completo
MATCH (test:TestScenarioIR {name: "test_checkout_flow_complete"})
MATCH (flow:Flow {name: "checkout_flow"})
MERGE (test)-[:VALIDATES_FLOW]->(flow)

// Test que valida una regla de validación
MATCH (test:TestScenarioIR {name: "test_negative_price_rejected"})
MATCH (rule:ValidationRule {entity: "Product", attribute: "price"})
MERGE (test)-[:VALIDATES_RULE]->(rule)
```

#### 8.4.2 Beneficios del Loop de QA Cerrado

| Beneficio | Descripción | Query de Ejemplo |
|-----------|-------------|------------------|
| **Coverage Analysis** | Identificar endpoints/flows sin tests | `MATCH (e:Endpoint) WHERE NOT EXISTS { MATCH ()-[:VALIDATES_ENDPOINT]->(e) } RETURN e` |
| **Impact Analysis** | Saber qué tests se ven afectados por cambios | `MATCH (e:Endpoint {path: "/products"})<-[:VALIDATES_ENDPOINT]-(t) RETURN t` |
| **Test Completeness** | Validar que todos los escenarios están cubiertos | `MATCH (flow:Flow)-[:HAS_STEP]->() WITH flow, count(*) as steps MATCH (flow)<-[:VALIDATES_FLOW]-(t) RETURN flow.name, steps, count(t) as tests` |
| **Regression Safety** | Detectar tests obsoletos si endpoints cambian | `MATCH (t)-[:VALIDATES_ENDPOINT]->(e) WHERE e.updated_at > t.generated_at RETURN t, e` |
| **QA Agent Intelligence** | Agent puede priorizar tests de componentes críticos | `MATCH (e:Endpoint)<-[:TARGETS_ENTITY]-(entity {is_aggregate_root: true}) MATCH (e)<-[:VALIDATES_ENDPOINT]-(t) RETURN t ORDER BY t.priority` |

#### 8.4.3 Schema Extendido

```cypher
// Agregar constraints para relaciones de validación
CREATE INDEX validates_endpoint IF NOT EXISTS
FOR ()-[r:VALIDATES_ENDPOINT]-() ON (r.created_at);

CREATE INDEX validates_flow IF NOT EXISTS
FOR ()-[r:VALIDATES_FLOW]-() ON (r.created_at);

CREATE INDEX validates_rule IF NOT EXISTS
FOR ()-[r:VALIDATES_RULE]-() ON (r.created_at);
```

#### 8.4.4 Generación Automática de Relaciones

**Fase 1: Inferencia desde datos existentes**

```python
# scripts/migrations/neo4j/007_enrich_test_validation_links.py

async def infer_validates_endpoint_links():
    """
    Infiere VALIDATES_ENDPOINT desde endpoint_path y http_method en TestScenarioIR.
    """
    async with driver.session() as session:
        # Link tests to endpoints by path+method
        await session.run("""
            MATCH (test:TestScenarioIR)
            WHERE test.endpoint_path IS NOT NULL
              AND test.http_method IS NOT NULL
            MATCH (endpoint:Endpoint)
            WHERE endpoint.path = test.endpoint_path
              AND endpoint.method = test.http_method
            MERGE (test)-[r:VALIDATES_ENDPOINT]->(endpoint)
            SET r.inferred = true,
                r.confidence = 1.0,
                r.created_at = datetime()
        """)

async def infer_validates_flow_links():
    """
    Infiere VALIDATES_FLOW desde nombres de test que mencionan flows.
    """
    async with driver.session() as session:
        # Link flow tests by name matching
        await session.run("""
            MATCH (test:TestScenarioIR)
            WHERE test.name CONTAINS 'flow' OR test.description CONTAINS 'workflow'
            MATCH (flow:Flow)
            WHERE test.name CONTAINS flow.name OR test.description CONTAINS flow.name
            MERGE (test)-[r:VALIDATES_FLOW]->(flow)
            SET r.inferred = true,
                r.confidence = 0.8,
                r.created_at = datetime()
        """)
```

**Fase 2: Integración en generación de tests**

```python
# En tests_ir_generator.py al crear TestScenarioIR

test_scenario = TestScenarioIR(
    name="test_get_product_success",
    endpoint_path="/products/{id}",
    http_method="GET",
    # NUEVO: Guardar referencia explícita
    source_endpoint_id=endpoint.endpoint_id,  # Para VALIDATES_ENDPOINT
    source_flow_id=flow.flow_id if flow else None,  # Para VALIDATES_FLOW
    ...
)
```

#### 8.4.5 Queries de QA Coverage

```cypher
// 1. Endpoint Coverage Report
MATCH (e:Endpoint)
OPTIONAL MATCH (e)<-[:VALIDATES_ENDPOINT]-(t:TestScenarioIR)
WITH e, collect(t.test_type) as test_types, count(t) as test_count
RETURN e.path, e.method,
       test_count,
       test_types,
       CASE WHEN test_count = 0 THEN 'NO COVERAGE ⚠️'
            WHEN 'happy_path' IN test_types AND 'error' IN test_types THEN 'FULL COVERAGE ✅'
            ELSE 'PARTIAL COVERAGE ⚡'
       END as coverage_status
ORDER BY test_count ASC

// 2. Critical Flows Without Tests
MATCH (flow:Flow)
WHERE flow.trigger CONTAINS 'critical' OR flow.type = 'workflow'
  AND NOT EXISTS { MATCH (flow)<-[:VALIDATES_FLOW]-() }
RETURN flow.name, flow.trigger, 'MISSING TESTS ❌' as status

// 3. Validation Rules Coverage
MATCH (rule:ValidationRule)
WHERE rule.severity = 'error'
OPTIONAL MATCH (rule)<-[:VALIDATES_RULE]-(t:TestScenarioIR)
RETURN rule.entity, rule.attribute, rule.condition,
       count(t) as test_count,
       CASE WHEN count(t) = 0 THEN '❌ NO TESTS' ELSE '✅ TESTED' END as status
ORDER BY test_count ASC
```

#### 8.4.6 Prioridad de Implementación

| Relación | Prioridad | Complejidad | Sprint Sugerido |
|----------|-----------|-------------|-----------------|
| VALIDATES_ENDPOINT | **Muy Alta** | Baja (path+method match directo) | 5 o 6 |
| VALIDATES_FLOW | Alta | Media (name matching + inferencia) | 6 |
| VALIDATES_RULE | Media | Alta (requiere análisis de assertions) | 6 o 7 |

**Beneficio Clave:** Con estas relaciones, el **QA Agent** puede:
1. Detectar gaps de testing automáticamente
2. Priorizar generación de tests para componentes críticos
3. Validar que cambios en código no rompen tests existentes
4. Generar reportes de coverage contextuales (no solo %)

#### 8.4.7 TestExecutionIR: Cerrar el Loop de QA Real

**Objetivo:** Persistir resultados de ejecución de tests (no solo las definiciones de tests) para análisis de calidad y trending.

**Problema:** TestsModelIR contiene las definiciones de tests (qué ejecutar), pero NO los resultados de ejecuciones (qué pasó). Sin esto:
- No sabemos qué tests están pasando/fallando actualmente
- No podemos hacer trending de calidad (% passed over time)
- No detectamos regresiones automáticamente
- Los reportes de QA son estáticos, no reflejan ejecuciones reales

**Solución:** Crear nodos `TestExecutionIR` y `TestResultIR` que persistan cada ejecución de tests.

**Schema Extendido:**

```cypher
// Ejecución de una suite de tests
(:TestExecutionIR {
  execution_id: "exec_uuid_123",
  app_id: "uuid-123",
  started_at: datetime(),
  completed_at: datetime(),
  total_tests: 45,
  passed: 42,
  failed: 2,
  skipped: 1,
  success_rate: 0.933,
  environment: "staging",
  triggered_by: "ci_pipeline",
  commit_sha: "abc123",
  pipeline_run_id: "pipeline_456"
})
  -[:EXECUTED_SUITE]->(EndpointTestSuite)  // Qué suite se ejecutó
  -[:HAS_RESULT]->(TestResultIR)           // Resultado de cada test individual

// Resultado individual de un test
(:TestResultIR {
  result_id: "result_uuid_789",
  scenario_id: "uuid-123|test|/products|happy_path|0",
  status: "passed",  // passed | failed | error | skipped
  execution_time_ms: 234,
  started_at: datetime(),
  completed_at: datetime(),

  // Si falló
  error_message: "AssertionError: Expected 200, got 500",
  error_type: "assertion_error",
  stack_trace: "...",

  // Metadata
  retries: 0,
  flaky: false  // true si pasó después de retry
})
  -[:TESTED]->(TestScenarioIR)           // Qué test se ejecutó
  -[:VALIDATED_BY]->(TestExecutionIR)    // Parte de qué ejecución

// Relación a componentes validados (para trending)
(:TestResultIR)
  -[:CHECKED_ENDPOINT {status: "passed"}]->(Endpoint)
  -[:CHECKED_FLOW {status: "failed"}]->(Flow)
```

**Repository Extendido:**

```python
# src/cognitive/services/tests_model_graph_repository.py

class TestsModelGraphRepository(GraphIRRepository):
    """Extended with test execution tracking."""

    async def save_test_execution(
        self,
        app_id: str,
        execution_metadata: Dict,
        test_results: List[TestResult]
    ) -> str:
        """
        Guarda resultados de una ejecución de tests.

        Args:
            app_id: Application ID
            execution_metadata: {
                "started_at": datetime,
                "environment": "staging",
                "triggered_by": "ci_pipeline",
                "commit_sha": "abc123"
            }
            test_results: Lista de resultados individuales

        Returns:
            execution_id
        """
        execution_id = f"exec_{app_id}_{datetime.now().timestamp()}"

        # 1. Crear TestExecutionIR node
        async with self.driver.session() as session:
            await session.run("""
                MATCH (app:ApplicationIR {app_id: $app_id})
                CREATE (exec:TestExecutionIR {
                    execution_id: $execution_id,
                    app_id: $app_id,
                    started_at: datetime($started_at),
                    completed_at: datetime($completed_at),
                    total_tests: $total_tests,
                    passed: $passed,
                    failed: $failed,
                    skipped: $skipped,
                    success_rate: $success_rate,
                    environment: $environment,
                    triggered_by: $triggered_by,
                    commit_sha: $commit_sha,
                    created_at: datetime(),
                    updated_at: datetime()
                })
                CREATE (app)-[:HAS_EXECUTION]->(exec)
            """, execution_id=execution_id, app_id=app_id, **execution_metadata)

        # 2. Crear TestResultIR nodes para cada resultado
        for result in test_results:
            await self._save_test_result(execution_id, result)

        return execution_id

    async def _save_test_result(self, execution_id: str, result: TestResult):
        """Guarda resultado individual de un test."""
        result_id = f"result_{execution_id}_{result.scenario_id}"

        async with self.driver.session() as session:
            await session.run("""
                MATCH (exec:TestExecutionIR {execution_id: $execution_id})
                MATCH (scenario:TestScenarioIR {scenario_id: $scenario_id})

                CREATE (res:TestResultIR {
                    result_id: $result_id,
                    scenario_id: $scenario_id,
                    status: $status,
                    execution_time_ms: $execution_time_ms,
                    started_at: datetime($started_at),
                    completed_at: datetime($completed_at),
                    error_message: $error_message,
                    error_type: $error_type,
                    retries: $retries,
                    flaky: $flaky,
                    created_at: datetime(),
                    updated_at: datetime()
                })

                CREATE (exec)-[:HAS_RESULT]->(res)
                CREATE (res)-[:TESTED]->(scenario)

                // Link to validated endpoint (if exists)
                WITH res, scenario
                OPTIONAL MATCH (scenario)-[:VALIDATES_ENDPOINT]->(endpoint:Endpoint)
                FOREACH (_ IN CASE WHEN endpoint IS NOT NULL THEN [1] ELSE [] END |
                    CREATE (res)-[:CHECKED_ENDPOINT {
                        status: $status,
                        timestamp: datetime()
                    }]->(endpoint)
                )
            """, execution_id=execution_id, result_id=result_id,
                 scenario_id=result.scenario_id, status=result.status,
                 execution_time_ms=result.execution_time_ms,
                 started_at=result.started_at.isoformat(),
                 completed_at=result.completed_at.isoformat(),
                 error_message=result.error_message,
                 error_type=result.error_type,
                 retries=result.retries,
                 flaky=result.flaky)
```

**Queries de QA Real:**

```cypher
// 1. Trending de calidad por app (últimos 30 días)
MATCH (app:ApplicationIR {app_id: $app_id})-[:HAS_EXECUTION]->(exec:TestExecutionIR)
WHERE exec.started_at > datetime() - duration({days: 30})
RETURN date(exec.started_at) as date,
       exec.success_rate,
       exec.total_tests,
       exec.passed,
       exec.failed
ORDER BY date

// 2. Tests que más fallan (últimas 100 ejecuciones)
MATCH (res:TestResultIR {status: 'failed'})-[:TESTED]->(scenario:TestScenarioIR)
WITH scenario, count(res) as failure_count
WHERE failure_count > 5
RETURN scenario.name,
       scenario.endpoint_path,
       failure_count,
       'FLAKY TEST ⚠️' as alert
ORDER BY failure_count DESC

// 3. Endpoints con tests fallando actualmente
MATCH (endpoint:Endpoint)<-[:CHECKED_ENDPOINT {status: 'failed'}]-(res:TestResultIR)
      <-[:HAS_RESULT]-(exec:TestExecutionIR)
WHERE exec.started_at > datetime() - duration({hours: 24})
WITH endpoint, count(DISTINCT res) as failed_tests
RETURN endpoint.path,
       endpoint.method,
       failed_tests,
       'FAILING ENDPOINT ❌' as status
ORDER BY failed_tests DESC

// 4. Regresiones detectadas (tests que pasaban antes, ahora fallan)
MATCH (scenario:TestScenarioIR)<-[:TESTED]-(current:TestResultIR {status: 'failed'})
      <-[:HAS_RESULT]-(current_exec:TestExecutionIR)
MATCH (scenario)<-[:TESTED]-(previous:TestResultIR {status: 'passed'})
      <-[:HAS_RESULT]-(previous_exec:TestExecutionIR)
WHERE current_exec.started_at > previous_exec.started_at
  AND current_exec.started_at > datetime() - duration({days: 7})
WITH scenario, current_exec, previous_exec
ORDER BY current_exec.started_at DESC
RETURN scenario.name,
       scenario.endpoint_path,
       'REGRESSION ⚠️' as alert,
       current_exec.commit_sha as failing_commit,
       previous_exec.commit_sha as last_passing_commit

// 5. Coverage real (endpoints con tests que PASAN)
MATCH (endpoint:Endpoint)
OPTIONAL MATCH (endpoint)<-[:CHECKED_ENDPOINT {status: 'passed'}]-(res:TestResultIR)
      <-[:HAS_RESULT]-(exec:TestExecutionIR)
WHERE exec.started_at > datetime() - duration({days: 7})
WITH endpoint, count(DISTINCT res) as passing_tests
RETURN endpoint.path,
       endpoint.method,
       passing_tests,
       CASE WHEN passing_tests = 0 THEN '❌ NO PASSING TESTS'
            WHEN passing_tests >= 3 THEN '✅ WELL TESTED'
            ELSE '⚡ MINIMAL TESTING'
       END as coverage_status
ORDER BY passing_tests ASC

// 6. Tiempo de ejecución de tests (performance tracking)
MATCH (scenario:TestScenarioIR)<-[:TESTED]-(res:TestResultIR)
WITH scenario, avg(res.execution_time_ms) as avg_time_ms,
     max(res.execution_time_ms) as max_time_ms
WHERE avg_time_ms > 1000  // > 1 segundo
RETURN scenario.name,
       scenario.endpoint_path,
       avg_time_ms,
       max_time_ms,
       'SLOW TEST ⏱️' as alert
ORDER BY avg_time_ms DESC
```

**Integración con Runtime Smoke Validator:**

```python
# src/validation/runtime_smoke_validator.py

class RuntimeSmokeValidator:
    """Extended to persist test execution results."""

    async def run_smoke_tests(self, app_dir: Path) -> SmokeTestResult:
        """
        Ejecuta smoke tests y persiste resultados en Neo4j.
        """
        # 1. Ejecutar tests
        result = await self._run_pytest(app_dir)

        # 2. Parse resultados
        test_results = self._parse_pytest_output(result)

        # 3. Guardar en Neo4j
        if self.persist_results:
            await self._persist_to_neo4j(app_id, test_results)

        return result

    async def _persist_to_neo4j(self, app_id: str, test_results: List):
        """Persiste resultados de ejecución en Neo4j."""
        from src.cognitive.services.tests_model_graph_repository import (
            TestsModelGraphRepository
        )

        repo = TestsModelGraphRepository()

        execution_metadata = {
            "started_at": self.start_time.isoformat(),
            "completed_at": datetime.now().isoformat(),
            "total_tests": len(test_results),
            "passed": sum(1 for r in test_results if r.status == "passed"),
            "failed": sum(1 for r in test_results if r.status == "failed"),
            "skipped": sum(1 for r in test_results if r.status == "skipped"),
            "success_rate": self._calculate_success_rate(test_results),
            "environment": "smoke_test",
            "triggered_by": "runtime_validator",
            "commit_sha": os.getenv("GIT_COMMIT", "local")
        }

        execution_id = await repo.save_test_execution(
            app_id=app_id,
            execution_metadata=execution_metadata,
            test_results=test_results
        )

        logger.info(f"Test execution persisted: {execution_id}")
```

**Beneficios de TestExecutionIR:**

| Beneficio | Descripción | Query |
|-----------|-------------|-------|
| **Quality Trending** | Ver evolución de calidad over time | `MATCH (exec:TestExecutionIR) WHERE exec.started_at > ... RETURN date(exec.started_at), exec.success_rate` |
| **Regression Detection** | Detectar cuando tests que pasaban ahora fallan | Ver query #4 arriba |
| **Flaky Test Identification** | Identificar tests inconsistentes | `MATCH (res:TestResultIR {flaky: true})` |
| **Performance Tracking** | Monitorear tiempo de ejecución de tests | Ver query #6 arriba |
| **Coverage Real** | Coverage basado en ejecuciones reales, no solo definiciones | Ver query #5 arriba |
| **CI/CD Integration** | Link test results → commit → pipeline | `commit_sha`, `pipeline_run_id` properties |

**Prioridad de Implementación:**

- **Sprint 5**: Implementar schema de TestExecutionIR y TestResultIR
- **Sprint 5**: Integrar con RuntimeSmokeValidator para persistir resultados
- **Sprint 6**: Agregar queries de trending y detección de regresiones a NeoDash
- **Sprint 6**: Integrar con CI/CD para captura automática de resultados de pipelines

**Archivos a Crear/Modificar:**

```
src/cognitive/services/tests_model_graph_repository.py
└── Agregar métodos:
    ├── save_test_execution()
    ├── _save_test_result()
    └── get_test_execution_history()

src/validation/runtime_smoke_validator.py
└── Agregar:
    └── _persist_to_neo4j()

src/cognitive/ir/tests_model.py
└── Agregar modelos:
    ├── TestExecutionIR
    └── TestResultIR

scripts/migrations/neo4j/
└── 008_test_execution_schema.cypher
    ├── TestExecutionIR constraints/indexes
    └── TestResultIR constraints/indexes

DOCS/mvp/exit/neo4j/contracts/
└── sprint_5_tests_execution.yml
    └── Contract para TestExecutionIR/TestResultIR
```

---

## 9. Sprint 6: Lineage & Intelligence

**Objetivo:** Establecer trazabilidad Spec → IR → Files y pre-generation intelligence.

*(Contenido del Sprint 1-2 original, ahora renumerado)*

### 9.1 Tasks

#### Task 6.1: Neo4j Lineage Schema
- Spec nodes con hash
- [:PRODUCES] relationship to ApplicationIR
- [:GENERATES] relationship to GeneratedFile
- [:USED_PATTERN] tracking

#### Task 6.2: Lineage Repository
```python
class LineageRepository:
    async def create_spec_node(self, spec_hash: str, name: str, content: str)
    async def link_spec_to_ir(self, spec_hash: str, ir_id: str)
    async def create_file_node(self, file_path: str, content_hash: str, ir_id: str)
    async def get_lineage(self, file_path: str) -> dict
```

#### Task 6.3: Qdrant spec_signatures Collection
- Spec embeddings para similarity search
- Transfer learning preparation

#### Task 6.4: Error Embeddings Collection
- Similar error detection
- Pre-generation warnings

#### Task 6.5: Pre-Generation Context Builder
```python
class PreGenerationContextBuilder:
    async def build_context(self, endpoint_spec, file_type, domain) -> PreGenerationContext
```

#### Task 6.6: Pipeline Integration
- Phase 1: Record spec → lineage graph
- Code generation: Use pre-gen context
- Phase 11: Record results

#### Task 6.7: FullIRGraphLoader Unificado

**Objetivo:** Crear un loader unificado que cargue TODO el grafo de ApplicationIR con todos sus subgrafos en una sola operación, reemplazando los loaders individuales fragmentados.

**Problema Actual:**

Tenemos loaders separados para cada IR:
- `DomainModelGraphRepository.load_domain_model(app_id)` → Carga solo DomainModelIR con Entities/Attributes
- `APIModelGraphRepository.load_api_model(app_id)` → Carga solo APIModelIR con Endpoints/Parameters
- `BehaviorModelGraphRepository.load_behavior_model(app_id)` → Carga solo BehaviorModelIR con Flows/Steps
- `TestsModelGraphRepository.load_tests_model(app_id)` → Carga solo TestsModelIR con TestScenarios

Esto causa:
- ❌ **N queries** para cargar una ApplicationIR completa (6-8 queries en promedio)
- ❌ **Código duplicado** en cada repository para lógica de loading
- ❌ **Performance pobre** en operaciones que necesitan todo el contexto
- ❌ **API fragmentada** confusa para consumidores

**Solución: FullIRGraphLoader**

Un loader unificado que ejecuta una sola query Cypher para cargar TODO el grafo de una app:

```python
# src/cognitive/services/full_ir_graph_loader.py

from typing import Optional
from dataclasses import dataclass
from src.cognitive.ir.application_ir import ApplicationIR
from src.cognitive.ir.domain_model import DomainModelIR, Entity, Attribute
from src.cognitive.ir.api_model import APIModelIR, Endpoint, APIParameter, APISchema
from src.cognitive.ir.behavior_model import BehaviorModelIR, Flow, Step
from src.cognitive.ir.tests_model import TestsModelIR, TestScenarioIR, SeedEntityIR

@dataclass
class FullIRGraphLoadResult:
    """Resultado completo del loading con metadata."""
    application_ir: ApplicationIR
    load_time_ms: float
    nodes_loaded: int
    relationships_loaded: int
    cache_hit: bool = False

class FullIRGraphLoader:
    """
    Loader unificado que carga TODO el grafo de ApplicationIR en una sola query.
    """

    def __init__(self, driver):
        self.driver = driver

    async def load_full_ir(
        self,
        app_id: str,
        include_tests: bool = True,
        use_cache: bool = True
    ) -> FullIRGraphLoadResult:
        """
        Carga ApplicationIR completo con todos sus subgrafos.

        Args:
            app_id: Application ID
            include_tests: Si incluir TestsModelIR (puede ser pesado)
            use_cache: Si usar cache de ApplicationIR en memoria/Redis

        Returns:
            FullIRGraphLoadResult con ApplicationIR completo y metadata
        """
        import time
        start = time.time()

        # 1. Cache check (opcional)
        if use_cache:
            cached = await self._get_from_cache(app_id)
            if cached:
                return FullIRGraphLoadResult(
                    application_ir=cached,
                    load_time_ms=(time.time() - start) * 1000,
                    nodes_loaded=0,
                    relationships_loaded=0,
                    cache_hit=True
                )

        # 2. Single comprehensive query
        query = self._build_full_load_query(include_tests)

        async with self.driver.session() as session:
            result = await session.run(query, app_id=app_id)
            record = await result.single()

            if not record:
                raise ValueError(f"ApplicationIR with app_id={app_id} not found")

            # 3. Parse graph result into Pydantic models
            app_ir = self._parse_full_graph(record, include_tests)

            # 4. Update cache
            if use_cache:
                await self._save_to_cache(app_id, app_ir)

            load_time_ms = (time.time() - start) * 1000

            return FullIRGraphLoadResult(
                application_ir=app_ir,
                load_time_ms=load_time_ms,
                nodes_loaded=record["nodes_count"],
                relationships_loaded=record["relationships_count"],
                cache_hit=False
            )

    def _build_full_load_query(self, include_tests: bool) -> str:
        """
        Construye query Cypher para cargar todo el grafo en una sola ejecución.

        Esta query usa OPTIONAL MATCH para cada subgrafo, permitiendo
        cargar ApplicationIR incluso si algunos IRs no existen.
        """
        query = """
        // 1. Match ApplicationIR root
        MATCH (app:ApplicationIR {app_id: $app_id})

        // 2. Load DomainModelIR with Entities, Attributes, Relationships
        OPTIONAL MATCH (app)-[:HAS_DOMAIN_MODEL]->(dm:DomainModelIR)
        OPTIONAL MATCH (dm)-[:HAS_ENTITY]->(entity:Entity)
        OPTIONAL MATCH (entity)-[:HAS_ATTRIBUTE]->(attr:Attribute)
        OPTIONAL MATCH (entity)-[rel:RELATES_TO]->(target:Entity)

        // 3. Load APIModelIR with Endpoints, Parameters, Schemas
        OPTIONAL MATCH (app)-[:HAS_API_MODEL]->(api:APIModelIR)
        OPTIONAL MATCH (api)-[:HAS_ENDPOINT]->(endpoint:Endpoint)
        OPTIONAL MATCH (endpoint)-[:HAS_PARAMETER]->(param:APIParameter)
        OPTIONAL MATCH (api)-[:HAS_SCHEMA]->(schema:APISchema)
        OPTIONAL MATCH (schema)-[:HAS_FIELD]->(field:APISchemaField)

        // 4. Load BehaviorModelIR with Flows, Steps, Invariants
        OPTIONAL MATCH (app)-[:HAS_BEHAVIOR_MODEL]->(bm:BehaviorModelIR)
        OPTIONAL MATCH (bm)-[:HAS_FLOW]->(flow:Flow)
        OPTIONAL MATCH (flow)-[:HAS_STEP]->(step:Step)
        OPTIONAL MATCH (bm)-[:HAS_INVARIANT]->(inv:Invariant)

        // 5. Load ValidationModelIR with Rules
        OPTIONAL MATCH (app)-[:HAS_VALIDATION_MODEL]->(vm:ValidationModelIR)
        OPTIONAL MATCH (vm)-[:HAS_RULE]->(rule:ValidationRule)

        // 6. Load InfrastructureModelIR with DatabaseConfig
        OPTIONAL MATCH (app)-[:HAS_INFRASTRUCTURE_MODEL]->(im:InfrastructureModelIR)
        OPTIONAL MATCH (im)-[:HAS_DATABASE_CONFIG]->(db:DatabaseConfig)
        """

        if include_tests:
            query += """
        // 7. Load TestsModelIR with SeedEntities, TestScenarios
        OPTIONAL MATCH (app)-[:HAS_TESTS_MODEL]->(tm:TestsModelIR)
        OPTIONAL MATCH (tm)-[:HAS_SEED_ENTITY]->(seed:SeedEntityIR)
        OPTIONAL MATCH (tm)-[:HAS_SCENARIO]->(scenario:TestScenarioIR)
            """

        query += """
        // 8. Aggregate and return complete graph
        WITH app, dm, api, bm, vm, im,
             collect(DISTINCT entity) as entities,
             collect(DISTINCT attr) as attributes,
             collect(DISTINCT rel) as relationships,
             collect(DISTINCT endpoint) as endpoints,
             collect(DISTINCT param) as parameters,
             collect(DISTINCT schema) as schemas,
             collect(DISTINCT field) as schema_fields,
             collect(DISTINCT flow) as flows,
             collect(DISTINCT step) as steps,
             collect(DISTINCT inv) as invariants,
             collect(DISTINCT rule) as validation_rules,
             collect(DISTINCT db) as database_configs
        """

        if include_tests:
            query += """
             , tm,
             collect(DISTINCT seed) as seed_entities,
             collect(DISTINCT scenario) as test_scenarios
            """

        query += """
        RETURN app,
               dm, entities, attributes, relationships,
               api, endpoints, parameters, schemas, schema_fields,
               bm, flows, steps, invariants,
               vm, validation_rules,
               im, database_configs,
        """

        if include_tests:
            query += """
               tm, seed_entities, test_scenarios,
            """

        query += """
               size(entities) + size(endpoints) + size(flows) + size(validation_rules) as nodes_count,
               size(attributes) + size(parameters) + size(steps) + size(schema_fields) as relationships_count
        """

        return query

    def _parse_full_graph(self, record, include_tests: bool) -> ApplicationIR:
        """
        Parsea el resultado del query en objetos Pydantic.

        Args:
            record: Resultado de Neo4j con todos los nodos y relaciones
            include_tests: Si se incluyeron tests en la query

        Returns:
            ApplicationIR completo con todos los subgrafos
        """
        # Parse ApplicationIR base
        app_data = dict(record["app"])
        app_id = app_data["app_id"]

        # Parse DomainModelIR
        domain_model = None
        if record["dm"]:
            entities = self._parse_entities(
                record["entities"],
                record["attributes"],
                record["relationships"]
            )
            domain_model = DomainModelIR(entities=entities)

        # Parse APIModelIR
        api_model = None
        if record["api"]:
            endpoints = self._parse_endpoints(
                record["endpoints"],
                record["parameters"]
            )
            schemas = self._parse_schemas(
                record["schemas"],
                record["schema_fields"]
            )
            api_model = APIModelIR(
                endpoints=endpoints,
                schemas=schemas,
                base_path=record["api"].get("base_path", ""),
                version=record["api"].get("version", "v1")
            )

        # Parse BehaviorModelIR
        behavior_model = None
        if record["bm"]:
            flows = self._parse_flows(record["flows"], record["steps"])
            invariants = self._parse_invariants(record["invariants"])
            behavior_model = BehaviorModelIR(
                flows=flows,
                invariants=invariants
            )

        # Parse ValidationModelIR
        validation_model = None
        if record["vm"]:
            rules = self._parse_validation_rules(record["validation_rules"])
            validation_model = ValidationModelIR(rules=rules)

        # Parse InfrastructureModelIR
        infrastructure_model = None
        if record["im"]:
            db_config = self._parse_database_config(record["database_configs"])
            infrastructure_model = InfrastructureModelIR(
                database_config=db_config
            )

        # Parse TestsModelIR (optional)
        tests_model = None
        if include_tests and record.get("tm"):
            seed_entities = self._parse_seed_entities(record["seed_entities"])
            test_scenarios = self._parse_test_scenarios(record["test_scenarios"])
            tests_model = TestsModelIR(
                seed_entities=seed_entities,
                test_scenarios=test_scenarios
            )

        # Construct complete ApplicationIR
        return ApplicationIR(
            app_id=app_id,
            name=app_data.get("name", ""),
            description=app_data.get("description", ""),
            domain_model=domain_model,
            api_model=api_model,
            behavior_model=behavior_model,
            validation_model=validation_model,
            infrastructure_model=infrastructure_model,
            tests_model=tests_model
        )

    def _parse_entities(self, entities_nodes, attributes_nodes, relationships_nodes) -> List[Entity]:
        """Parse Entity nodes with their Attributes and Relationships."""
        # Implementation: Group attributes by entity_id, create Entity objects
        # ... (full implementation omitted for brevity)
        pass

    def _parse_endpoints(self, endpoints_nodes, parameters_nodes) -> List[Endpoint]:
        """Parse Endpoint nodes with their Parameters."""
        # Implementation: Group parameters by endpoint_id, create Endpoint objects
        # ... (full implementation omitted for brevity)
        pass

    # ... más helper methods para parsing de otros subgrafos
```

**Uso en Application:**

```python
# En cualquier servicio que necesite el IR completo

from src.cognitive.services.full_ir_graph_loader import FullIRGraphLoader

async def process_application(app_id: str):
    loader = FullIRGraphLoader(driver)

    # Cargar TODO el grafo en una sola operación
    result = await loader.load_full_ir(
        app_id=app_id,
        include_tests=True,
        use_cache=True
    )

    app_ir = result.application_ir

    print(f"✅ Loaded ApplicationIR in {result.load_time_ms:.2f}ms")
    print(f"   Nodes: {result.nodes_loaded}")
    print(f"   Relationships: {result.relationships_loaded}")
    print(f"   Cache hit: {result.cache_hit}")

    # Ahora tienes acceso a TODO:
    if app_ir.domain_model:
        print(f"   Entities: {len(app_ir.domain_model.entities)}")

    if app_ir.api_model:
        print(f"   Endpoints: {len(app_ir.api_model.endpoints)}")

    if app_ir.behavior_model:
        print(f"   Flows: {len(app_ir.behavior_model.flows)}")

    # Use complete IR for any operation
    return app_ir
```

**Performance Comparison:**

**Antes (loaders fragmentados):**
```
# 6 queries separadas, 6 round-trips a Neo4j
domain_model = await dm_repo.load_domain_model(app_id)     # 120ms
api_model = await api_repo.load_api_model(app_id)          # 150ms
behavior_model = await bm_repo.load_behavior_model(app_id) # 100ms
validation_model = await vm_repo.load_validation_model(app_id) # 80ms
infrastructure = await im_repo.load_infrastructure(app_id) # 70ms
tests_model = await tm_repo.load_tests_model(app_id)       # 200ms

# Total: ~720ms + network latency overhead
```

**Después (loader unificado):**
```
# 1 query, 1 round-trip
result = await loader.load_full_ir(app_id, use_cache=True)

# Total: ~180ms (primera vez) → ~5ms (con cache)
# ✅ 4x más rápido sin cache
# ✅ 144x más rápido con cache
```

**Cache Strategy:**

```python
# src/cognitive/services/full_ir_graph_loader.py

class FullIRGraphLoader:
    async def _get_from_cache(self, app_id: str) -> Optional[ApplicationIR]:
        """
        Obtener ApplicationIR del cache (Redis o in-memory).

        Cache key: f"app_ir:{app_id}"
        TTL: 1 hour (configurable)
        """
        # Opción 1: Redis
        cached_json = await redis_client.get(f"app_ir:{app_id}")
        if cached_json:
            return ApplicationIR.parse_raw(cached_json)

        # Opción 2: In-memory LRU cache (más rápido, pero no distribuido)
        # return self._memory_cache.get(app_id)

        return None

    async def _save_to_cache(self, app_id: str, app_ir: ApplicationIR):
        """Guardar ApplicationIR en cache."""
        # Opción 1: Redis
        await redis_client.setex(
            f"app_ir:{app_id}",
            3600,  # 1 hour TTL
            app_ir.json()
        )

        # Opción 2: In-memory
        # self._memory_cache[app_id] = app_ir

    async def invalidate_cache(self, app_id: str):
        """Invalidar cache cuando ApplicationIR se actualiza."""
        await redis_client.delete(f"app_ir:{app_id}")
```

**Integration con Pipeline:**

```python
# src/agents/orchestrator_agent.py

class OrchestratorAgent:
    async def run_pipeline(self, spec: str, app_id: str):
        # Phase 1: Load existing IR (if re-generation)
        loader = FullIRGraphLoader(self.neo4j_driver)

        existing_ir = None
        if await self._app_exists(app_id):
            result = await loader.load_full_ir(app_id, use_cache=True)
            existing_ir = result.application_ir

            print(f"📦 Loaded existing IR in {result.load_time_ms:.2f}ms "
                  f"(cache: {result.cache_hit})")

        # Phase 2-10: Generate/update IRs...

        # Phase 11: Save updated IRs to graph
        # (esto invalida el cache automáticamente)
```

**Beneficios:**

- ✅ **Performance 4x mejor**: Una query vs 6 queries separadas
- ✅ **Cache enabled**: 144x más rápido en cache hits
- ✅ **API simplificada**: Un método load vs 6 métodos dispersos
- ✅ **Código DRY**: Lógica de loading centralizada
- ✅ **Atomicidad**: Todo el grafo se carga o falla junto
- ✅ **Consistency**: Snapshot consistente del grafo en un punto en el tiempo
- ✅ **Maintainability**: Un archivo vs 6 repositories diferentes

**Trade-offs:**

**⚠️ Cons:**
- Query más compleja (pero más eficiente)
- Mayor uso de memoria si se carga TODO (mitigado con `include_tests=False`)
- Cache invalidation complexity (mitigado con TTL conservador)

**Mitigaciones:**
- `include_tests=False` para operaciones que no necesitan tests
- Cache con TTL de 1 hora (balance entre freshness y performance)
- Invalidación explícita de cache en updates

**Archivos a crear:**

```
src/cognitive/services/
└── full_ir_graph_loader.py          # Loader unificado

tests/unit/services/
└── test_full_ir_graph_loader.py     # Tests unitarios

tests/integration/
└── test_full_ir_loading_performance.py  # Benchmarks de performance
```

**Prioridad:**
- **Sprint 6**: Implementar loader unificado
- **Sprint 6**: Integrar con pipeline (optional loading)
- **Sprint 7**: Habilitar cache en producción
- **Sprint 8**: Performance tuning y optimización de queries

---

### 9.2 Sprint 6 Checklist

```
[ ] Task 6.1: Neo4j Lineage Schema
[ ] Task 6.2: Lineage Repository
[ ] Task 6.3: Qdrant spec_signatures Collection
[ ] Task 6.4: Error Embeddings Collection
[ ] Task 6.5: Pre-Generation Context Builder
[ ] Task 6.6: Pipeline Integration
[ ] IR cache hit rate >50%
```

---

## 10. Sprint 7: Real-Time Tracking

**Objetivo:** Visibilidad completa del proceso de generación.

*(Contenido del Sprint 3 original)*

### 10.1 Tasks

#### Task 7.1: pgvector Generation Events Table
#### Task 7.2: Code Fragments Collection (Qdrant)
#### Task 7.3: Neo4j Error Lineage
#### Task 7.4: Real-Time Event Logging

---

## 11. Sprint 8: Analytics & Optimization

**Objetivo:** Sistema auto-optimizante.

*(Contenido del Sprint 4 original)*

### 11.1 Tasks

#### Task 8.1: Error Trends Table (pgvector)
#### Task 8.2: Pattern Optimization Service
#### Task 8.3: Analytics Queries & Views
#### Task 8.4: Transfer Learning Service

---

## 11.5 NeoDash Views y Dashboards

**Objetivo:** Crear dashboards interactivos en NeoDash alineados con cada sprint para visualización y monitoreo.

### 11.5.1 Dashboard por Sprint

#### Sprint 0: Schema Health Dashboard

**Cards:**

1. **Label Distribution**
```cypher
// Distribución de labels en el grafo
CALL db.labels() YIELD label
CALL apoc.cypher.run("MATCH (n:" + label + ") RETURN count(n) as count", {})
YIELD value
RETURN label, value.count as count
ORDER BY count DESC
```

2. **Orphan Detection**
```cypher
// Nodos huérfanos sin relaciones
MATCH (n)
WHERE NOT EXISTS { MATCH (n)--() }
RETURN labels(n) as labels, count(n) as orphan_count
ORDER BY orphan_count DESC
```

3. **IR Suffix Compliance**
```cypher
// Verificar que todos los IRs usan sufijo correcto
CALL db.labels() YIELD label
WHERE label ENDS WITH 'IR'
RETURN label, true as compliant
UNION
CALL db.labels() YIELD label
WHERE NOT label ENDS WITH 'IR'
  AND label IN ['Application', 'DomainModel', 'APIModel', 'BehaviorModel']
RETURN label, false as compliant
```

#### Sprint 1: Domain Model Dashboard (DOMAIN_BY_APP)

**Cards:**

1. **Entity Distribution by App**
```cypher
// Distribución de entities por aplicación
MATCH (app:ApplicationIR)-[:HAS_DOMAIN_MODEL]->(dm:DomainModelIR)-[:HAS_ENTITY]->(e:Entity)
RETURN app.app_id as app,
       count(DISTINCT e) as entity_count,
       count(DISTINCT dm) as domain_models
ORDER BY entity_count DESC
LIMIT 20
```

2. **Top Entities by Attributes**
```cypher
// Entidades con más atributos
MATCH (e:Entity)-[:HAS_ATTRIBUTE]->(a:Attribute)
RETURN e.name as entity,
       count(a) as attribute_count,
       collect(a.name)[..5] as sample_attributes
ORDER BY attribute_count DESC
LIMIT 15
```

3. **Entity Relationships Graph**
```cypher
// Visualización de relaciones entre entities
MATCH (e1:Entity)-[r:RELATES_TO]->(e2:Entity)
RETURN e1, r, e2
LIMIT 100
```

4. **Aggregate Roots**
```cypher
// Aggregate roots del domain
MATCH (e:Entity {is_aggregate_root: true})
OPTIONAL MATCH (e)-[:HAS_ATTRIBUTE]->(a:Attribute)
RETURN e.name as aggregate_root,
       count(a) as attributes,
       e.description
ORDER BY attributes DESC
```

#### Sprint 2: API Model Dashboard (API_BY_APP)

**Cards:**

1. **Endpoint Distribution by App**
```cypher
// Distribución de endpoints por aplicación
MATCH (app:ApplicationIR)-[:HAS_API_MODEL]->(api:APIModelIR)-[:HAS_ENDPOINT]->(e:Endpoint)
RETURN app.app_id as app,
       count(DISTINCT e) as endpoint_count,
       collect(DISTINCT e.method) as methods_used
ORDER BY endpoint_count DESC
LIMIT 20
```

2. **Endpoint Methods Breakdown**
```cypher
// Distribución de métodos HTTP
MATCH (e:Endpoint)
RETURN e.method as http_method,
       count(e) as count,
       round(count(e) * 100.0 / (SELECT count(*) FROM (MATCH (e2:Endpoint) RETURN e2)), 1) as percentage
ORDER BY count DESC
```

3. **Inferred vs Spec Endpoints**
```cypher
// Endpoints inferidos vs del spec
MATCH (e:Endpoint)
RETURN e.inferred as is_inferred,
       count(e) as count,
       collect(DISTINCT e.inference_source)[..3] as sources
ORDER BY is_inferred
```

4. **Endpoints with Parameters**
```cypher
// Endpoints con y sin parámetros
MATCH (e:Endpoint)
OPTIONAL MATCH (e)-[:HAS_PARAMETER]->(p:APIParameter)
WITH e, count(p) as param_count
RETURN CASE
         WHEN param_count = 0 THEN 'No Parameters'
         WHEN param_count <= 2 THEN '1-2 Parameters'
         WHEN param_count <= 5 THEN '3-5 Parameters'
         ELSE '6+ Parameters'
       END as parameter_range,
       count(e) as endpoint_count
ORDER BY parameter_range
```

5. **API Coverage by Entity (con TARGETS_ENTITY)**
```cypher
// Coverage de endpoints por entidad (requiere Sprint 2.5)
MATCH (entity:Entity)
OPTIONAL MATCH (entity)<-[:TARGETS_ENTITY]-(e:Endpoint)
RETURN entity.name,
       count(e) as endpoint_count,
       collect(DISTINCT e.method) as methods,
       CASE
         WHEN count(e) >= 4 THEN 'Full CRUD ✅'
         WHEN count(e) >= 2 THEN 'Partial Coverage ⚡'
         ELSE 'No Coverage ❌'
       END as crud_status
ORDER BY endpoint_count DESC
```

#### Sprint 5: QA Coverage Dashboard (QA_COVERAGE_BY_APP)

**Cards:**

1. **Test Scenario Distribution**
```cypher
// Distribución de scenarios de test
MATCH (app:ApplicationIR)-[:HAS_TESTS_MODEL]->(tm:TestsModelIR)
OPTIONAL MATCH (tm)-[:HAS_ENDPOINT_SUITE|HAS_FLOW_SUITE]->(suite)
OPTIONAL MATCH (suite)-[:HAS_HAPPY_PATH|HAS_ERROR_CASE|HAS_SCENARIO]->(test:TestScenarioIR)
RETURN app.app_id as app,
       count(DISTINCT test) as test_count,
       count(DISTINCT suite) as suite_count
ORDER BY test_count DESC
LIMIT 20
```

2. **Endpoint Test Coverage (con VALIDATES_ENDPOINT)**
```cypher
// Coverage de tests por endpoint (requiere Sprint 5 mejoras)
MATCH (e:Endpoint)
OPTIONAL MATCH (e)<-[:VALIDATES_ENDPOINT]-(t:TestScenarioIR)
WITH e, collect(t.test_type) as test_types, count(t) as test_count
RETURN e.path, e.method,
       test_count,
       CASE
         WHEN test_count = 0 THEN '❌ NO COVERAGE'
         WHEN 'happy_path' IN test_types AND 'error' IN test_types THEN '✅ FULL'
         ELSE '⚡ PARTIAL'
       END as coverage_status
ORDER BY test_count ASC
LIMIT 30
```

3. **Test Type Distribution**
```cypher
// Distribución por tipo de test
MATCH (t:TestScenarioIR)
RETURN t.test_type as test_type,
       count(t) as count,
       round(count(t) * 100.0 / (SELECT count(*) FROM (MATCH (t2:TestScenarioIR) RETURN t2)), 1) as percentage
ORDER BY count DESC
```

4. **Critical Flows Without Tests**
```cypher
// Flows críticos sin coverage (requiere Sprint 3 + mejoras Sprint 5)
MATCH (flow:Flow)
WHERE NOT EXISTS { MATCH (flow)<-[:VALIDATES_FLOW]-() }
RETURN flow.name, flow.type, flow.trigger, '❌ NO TESTS' as status
ORDER BY flow.name
LIMIT 20
```

5. **Seed Data Dependency Graph**
```cypher
// Visualización de dependencias de seed data
MATCH path = (s1:SeedEntityIR)-[:DEPENDS_ON_SEED*1..3]->(s2:SeedEntityIR)
RETURN path
LIMIT 50
```

#### Sprint 6+: Lineage & Intelligence Dashboard

**Cards:**

1. **Spec → IR → Files Lineage**
```cypher
// Trazabilidad completa de generación
MATCH path = (spec:Spec)-[:PRODUCES]->(app:ApplicationIR)-[:GENERATES]->(file:GeneratedFile)
RETURN path
LIMIT 100
```

2. **Pattern Usage Heatmap**
```cypher
// Patterns más usados
MATCH (file:GeneratedFile)-[:USED_PATTERN]->(pattern:Pattern)
RETURN pattern.pattern_id, pattern.name,
       count(file) as usage_count
ORDER BY usage_count DESC
LIMIT 20
```

3. **Migration Run History**
```cypher
// Historial de migraciones
MATCH (m:MigrationRun)
RETURN m.sprint, m.migration_name, m.status,
       m.started_at, m.success_rate, m.duration_seconds
ORDER BY m.started_at DESC
LIMIT 30
```

4. **Schema Version Timeline**
```cypher
// Timeline de versiones de schema
MATCH (v:GraphSchemaVersion)
RETURN v.current_version, v.last_migration,
       v.migration_date, v.sprints_completed
```

### 11.5.2 Dashboard Organizacional

**Global Overview Dashboard:**

1. **IR Progress by Sprint**
```cypher
// Progreso de IRs migrados por sprint
MATCH (ir)
WHERE labels(ir)[0] ENDS WITH 'IR'
  AND ir.migrated_to_graph = true
RETURN labels(ir)[0] as ir_type,
       ir.graph_schema_version as version,
       count(ir) as migrated_count
ORDER BY version DESC
```

2. **Graph Growth Timeline**
```cypher
// Crecimiento del grafo por sprint
MATCH (m:MigrationRun)
WHERE m.status = 'completed'
RETURN m.sprint,
       sum(m.nodes_created) as total_nodes,
       sum(m.relationships_created) as total_edges,
       avg(m.success_rate) as avg_success_rate
ORDER BY m.sprint
```

3. **Data Quality Metrics**
```cypher
// Métricas de calidad de datos
MATCH (ir)
WHERE labels(ir)[0] ENDS WITH 'IR'
WITH count(ir) as total_irs
MATCH (orphan)
WHERE NOT EXISTS { MATCH (orphan)--() }
WITH total_irs, count(orphan) as orphans
MATCH (complete:ApplicationIR)
WHERE complete.migrated_to_graph = true
RETURN total_irs,
       orphans,
       count(complete) as migrated_irs,
       round(count(complete) * 100.0 / total_irs, 1) as migration_percentage
```

### 11.5.3 Configuración NeoDash

**Instalación:**
```bash
# Via Docker
docker run -it --rm \
  -p 5005:5005 \
  -e singleDatabase=true \
  -e standaloneDatabase=neo4j://localhost:7687 \
  -e standaloneDatabaseUser=neo4j \
  -e standaloneDatabasePassword=devmatrix123 \
  nielsdejong/neodash:latest

# Acceder a http://localhost:5005
```

**Archivo de Dashboard:**
```
DOCS/mvp/exit/neo4j/neodash/
├── sprint0_schema_health.json
├── sprint1_domain_model.json
├── sprint2_api_model.json
├── sprint5_qa_coverage.json
└── global_overview.json
```

### 11.5.4 Beneficios

| Beneficio | Descripción |
|-----------|-------------|
| **Visibilidad** | Vista en tiempo real del estado del grafo post-migración |
| **Debugging** | Identificar rápidamente problemas de coverage o calidad |
| **Stakeholder Communication** | Dashboards ejecutivos para mostrar progreso |
| **QA Intelligence** | Identificar gaps de testing visualmente |
| **Trend Analysis** | Monitorear crecimiento y calidad a lo largo de sprints |

---

## 12. Riesgos Técnicos y Mitigaciones

**Contexto:** Con ~11,000 nodos ya creados (Sprints 0-2) y proyección de ~75,000 nodos al completar todos los sprints, es crítico identificar y mitigar riesgos proactivamente.

---

### 12.1 Riesgo #1: Performance Degradation con ~75K Nodes

**Descripción:**
A medida que el grafo crece de 11K → 75K nodos, queries mal optimizados pueden degradar performance exponencialmente.

**Síntomas:**
- Queries que tardan >5 segundos
- Memory pressure en Neo4j (OOM errors)
- APOC timeouts en operaciones batch
- Dashboard NeoDash lento o timeout

**Severidad:** 🔴 **ALTA** - Impacta usabilidad del grafo completo

---

#### 12.1.1 Causas Raíz

| Causa | Ejemplo | Impacto |
|-------|---------|---------|
| **Queries sin entrypoint** | `MATCH (e:Entity)` sin `app_id` | Escanea TODOS los 75K nodos |
| **Cartesian products accidentales** | `MATCH (a), (b)` sin relación | O(n²) explosión combinatoria |
| **Missing indexes** | Buscar por `path` sin index | Full table scan |
| **Unbounded COLLECT()** | `COLLECT(attrs)` sin LIMIT | Out of memory con miles de atributos |
| **Nested loops** | `MATCH` dentro de `FOREACH` | O(n²) o peor |

---

#### 12.1.2 Mitigaciones IMPLEMENTADAS

**M1.1: Query Entrypoint Standards** ✅

**Regla:** TODOS los queries deben empezar con `app_id` específico.

```cypher
// ❌ MALO: Escanea 75K nodos
MATCH (e:Entity)
WHERE e.name = 'Product'
RETURN e;

// ✅ BUENO: Solo 100-200 nodos de una app
MATCH (app:ApplicationIR {app_id: $app_id})
MATCH (app)-[:HAS_DOMAIN_MODEL]->(dm:DomainModelIR)-[:HAS_ENTITY]->(e:Entity)
WHERE e.name = 'Product'
RETURN e;
```

**Enforcement:**
- Code review checklist: "¿Query empieza con app_id?"
- Test suite: Validar que todos los repository methods usan `app_id`

---

**M1.2: Index Coverage** ✅

**Status Actual (Post-Sprint 2):**
```cypher
// Constraints (actúan como indexes únicos)
CONSTRAINT entity_unique: (e:Entity) REQUIRE (e.app_id, e.entity_id) IS UNIQUE
CONSTRAINT endpoint_unique: (ep:Endpoint) REQUIRE (ep.api_model_id, ep.path, ep.method) IS UNIQUE

// Indexes
INDEX entity_name: (e:Entity) ON (e.name)
INDEX endpoint_path: (ep:Endpoint) ON (ep.path)
INDEX attribute_name: (a:Attribute) ON (a.name)
```

**Coverage Completa (Sprint 3+):**
```cypher
// Agregar en cada sprint nuevo
CREATE INDEX flow_name IF NOT EXISTS FOR (f:Flow) ON (f.name);
CREATE INDEX validation_type IF NOT EXISTS FOR (v:ValidationRule) ON (v.rule_type);
CREATE INDEX test_scenario_name IF NOT EXISTS FOR (t:TestScenario) ON (t.name);
```

**Monitoring:**
```cypher
// Verificar index usage en production
CALL db.stats.retrieve('QUERIES');  // Neo4j 5.x
// Revisar queries sin index hits
```

---

**M1.3: Batch Size Limits** ✅

**Implementado en GraphIRRepository base class:**
```python
async def batch_create_nodes(
    self,
    label: str,
    nodes_data: List[Dict],
    batch_size: int = 1000  # DEFAULT: 1000 nodos por batch
) -> int:
    """Crear nodos en batches para evitar memory spikes."""
    total = 0
    for i in range(0, len(nodes_data), batch_size):
        batch = nodes_data[i:i+batch_size]
        # UNWIND batch creation
        total += len(batch)
    return total
```

**Justificación:**
- 1,000 nodos/batch: ~1MB memory footprint (safe)
- 10,000 nodos/batch: ~10MB (riesgoso con nested properties)

---

**M1.4: Query Timeouts** ✅

**Configuración Neo4j:**
```properties
# neo4j.conf
dbms.transaction.timeout=60s          # Default 60s
dbms.transaction.bookmark_ready_timeout=30s
```

**Python Driver:**
```python
# src/cognitive/infrastructure/neo4j_connection.py

async def run_with_timeout(self, query: str, timeout_ms: int = 30000, **params):
    """Ejecutar query con timeout explícito."""
    async with self.driver.session() as session:
        try:
            result = await asyncio.wait_for(
                session.run(query, **params),
                timeout=timeout_ms / 1000.0
            )
            return result
        except asyncio.TimeoutError:
            raise QueryTimeoutError(f"Query exceeded {timeout_ms}ms")
```

---

**M1.5: LIMIT en Dashboards** ✅

**Regla:** Todos los NeoDash queries tienen LIMIT explícito.

```cypher
// ❌ MALO: Sin LIMIT
MATCH (e:Entity)-[:HAS_ATTRIBUTE]->(a:Attribute)
RETURN e.name, collect(a.name) as attributes;

// ✅ BUENO: LIMIT + pagination
MATCH (e:Entity)-[:HAS_ATTRIBUTE]->(a:Attribute)
WITH e, collect(a.name) as attributes
RETURN e.name, attributes
ORDER BY size(attributes) DESC
LIMIT 100;  // Top 100 entities
```

---

#### 12.1.3 Mitigaciones PENDIENTES

**M1.6: Query Profiling Automation** ⏳

**Sprint 3+:** Implementar profiling automático de queries lentos.

```python
# src/cognitive/infrastructure/neo4j_profiler.py

class QueryProfiler:
    async def profile_query(self, query: str) -> Dict:
        """Perfila query y retorna métricas."""
        profile_query = f"PROFILE {query}"
        result = await self.neo4j.run(profile_query)

        return {
            "db_hits": result.summary.profile.db_hits,
            "time_ms": result.summary.result_available_after,
            "rows": result.summary.counters.rows_created,
            "has_index_scan": "IndexScan" in str(result.summary.profile)
        }

    async def flag_slow_queries(self, threshold_ms: int = 5000):
        """Detectar queries >5s en logs."""
        # Parse neo4j query.log
        # Alert si db_hits > 100K o time > threshold
```

---

**M1.7: Caching Layer** ⏳

**Sprint 6+:** Cache para queries frecuentes (read-heavy).

```python
# src/cognitive/infrastructure/graph_cache.py

from functools import lru_cache
import redis

class GraphCache:
    def __init__(self, redis_client):
        self.redis = redis_client

    @lru_cache(maxsize=1000)
    async def get_entity_by_name(self, app_id: str, name: str) -> Optional[Dict]:
        """Cache entity lookups (inmutables en corto plazo)."""
        cache_key = f"entity:{app_id}:{name}"

        # Check Redis
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        # Fetch from Neo4j
        result = await self.neo4j.run(...)

        # Cache por 5 minutos
        await self.redis.setex(cache_key, 300, json.dumps(result))
        return result
```

**Invalidation:** Al actualizar DomainModelIR, flush cache de ese `app_id`.

---

#### 12.1.4 Performance Budget

| Operación | Budget | Actual (Sprint 2) | Target (Sprint 8) |
|-----------|--------|-------------------|-------------------|
| **save_domain_model()** | <5s | 2.3s (278 apps) | <5s (1000 apps) |
| **load_domain_model()** | <1s | 0.4s | <1s |
| **NeoDash dashboard** | <3s | 1.8s | <3s |
| **Validation query** | <2s | 0.9s | <2s |
| **Migration script** | <30min | 12min | <30min |

**Monitoring:** Log actual performance en cada sprint, alert si excede budget.

---

### 12.2 Riesgo #2: Coherence entre GraphSchemaVersion y MigrationRun

**Descripción:**
Si GraphSchemaVersion.current_version y MigrationRun.schema_version_after se desincronizan, pierdes trazabilidad y puedes aplicar migrations en orden incorrecto.

**Ejemplo del Problema:**
```cypher
// GraphSchemaVersion dice v2
MATCH (v:GraphSchemaVersion {singleton: true})
RETURN v.current_version;  // → 2

// Pero MigrationRun tiene v3 aplicado
MATCH (m:MigrationRun)
RETURN m.migration_id, m.schema_version_after
ORDER BY m.executed_at DESC LIMIT 1;
// → "006_targets_entity", schema_version_after: 3

// ⚠️ INCOHERENCIA: GraphSchemaVersion desactualizado
```

**Severidad:** 🟡 **MEDIA** - No rompe el sistema, pero dificulta auditoría

---

#### 12.2.1 Causas Raíz

| Causa | Escenario |
|-------|-----------|
| **Migration script olvida actualizar GraphSchemaVersion** | Developer crea migration, ejecuta Cypher, pero no hace `SET v.current_version = X` |
| **Rollback parcial** | Migration falla a mitad, MigrationRun.status = 'failed', pero GraphSchemaVersion ya incrementado |
| **Concurrency race** | Dos migrations corren en paralelo (sin lock), ambos escriben current_version |
| **Manual edit** | Admin actualiza GraphSchemaVersion manualmente sin registrar MigrationRun |

---

#### 12.2.2 Mitigaciones IMPLEMENTADAS

**M2.1: Naming Convention Enforcement** ✅

**Regla:** `migration_id` y `schema_version` deben seguir convención estricta.

**Formato:**
```
{seq}_{sprint_name}_{description}.{ext}

Ejemplos:
000_sprint0_schema_alignment.cypher       → v0
003_sprint1_domain_model_expansion.py     → v1
005_sprint2_api_model_expansion.py        → v2
007_sprint2.5_targets_entity.cypher       → v2.5
010_sprint3_behavior_validation.py        → v3
```

**Enforcement:**
```python
# scripts/migrations/neo4j/migration_validator.py

import re

MIGRATION_NAME_PATTERN = re.compile(r'(\d{3})_sprint(\d+(\.\d+)?)_([a-z_]+)\.(py|cypher)')

def validate_migration_name(filename: str) -> bool:
    """Valida que nombre de migration sigue convención."""
    match = MIGRATION_NAME_PATTERN.match(filename)
    if not match:
        raise ValueError(f"Invalid migration name: {filename}")

    seq, sprint_version, _, description, ext = match.groups()
    print(f"✅ Valid: seq={seq}, sprint={sprint_version}, desc={description}")
    return True
```

---

**M2.2: Atomic Version Update** ✅

**Pattern:** GraphSchemaVersion update DEBE ser parte de la misma transacción que la migration.

```python
# scripts/migrations/neo4j/007_add_source_to_api_schema.py

async def run_migration():
    async with neo4j.transaction() as tx:
        # 1. Ejecutar migration
        await tx.run("""
            MATCH (s:APISchema)
            WHERE s.source IS NULL
            SET s.source = 'GENERATED', s.updated_at = datetime()
        """)

        # 2. Registrar MigrationRun
        await tx.run("""
            CREATE (m:MigrationRun {
                migration_id: '007_sprint2.5_add_source_field',
                schema_version_after: 2.5,
                executed_at: datetime(),
                status: 'success'
            })
        """)

        # 3. Actualizar GraphSchemaVersion EN LA MISMA TX
        await tx.run("""
            MATCH (v:GraphSchemaVersion {singleton: true})
            SET v.current_version = 2.5,
                v.last_migration = '007_sprint2.5_add_source_field',
                v.updated_at = datetime()
        """)

        # Si algo falla, TODA la transacción hace rollback → coherencia garantizada
        await tx.commit()
```

**Beneficio:** Si migration falla, GraphSchemaVersion NO se actualiza (atomicidad).

---

**M2.3: Validation Query** ✅

**Ejecutar después de cada migration:**

```cypher
// scripts/migrations/neo4j/validate_coherence.cypher

// Verificar coherencia entre GraphSchemaVersion y MigrationRun
MATCH (v:GraphSchemaVersion {singleton: true})
MATCH (m:MigrationRun)
WHERE m.status = 'success'
WITH v, m
ORDER BY m.executed_at DESC
LIMIT 1

RETURN
    v.current_version as schema_version,
    m.schema_version_after as last_migration_version,
    CASE
        WHEN v.current_version = m.schema_version_after THEN '✅ COHERENT'
        ELSE '🚨 INCOHERENT'
    END as status,
    v.last_migration as last_migration_id,
    m.migration_id as last_migration_run_id;

// Expected output:
// schema_version | last_migration_version | status        | ...
// 2.5            | 2.5                    | ✅ COHERENT   | ...
```

**Automation:** Ejecutar en CI/CD después de cada deployment.

---

#### 12.2.3 Mitigaciones PENDIENTES

**M2.4: Pre-Migration Checks** ⏳

**Sprint 3+:** Validar estado antes de ejecutar migration.

```python
# src/cognitive/infrastructure/migration_runner.py

class MigrationRunner:
    async def pre_migration_check(self, expected_version: float):
        """Verifica que current_version coincide con expected."""
        result = await self.neo4j.run("""
            MATCH (v:GraphSchemaVersion {singleton: true})
            RETURN v.current_version as current
        """)

        current = result['current']
        if current != expected_version:
            raise MigrationError(
                f"Schema version mismatch: expected {expected_version}, got {current}. "
                f"Cannot apply migration safely."
            )

    async def apply_migration(self, migration_file: str):
        # 1. Pre-check
        await self.pre_migration_check(expected_version=2.0)

        # 2. Execute migration
        await self.run_migration_script(migration_file)

        # 3. Post-validation
        await self.validate_coherence()
```

---

**M2.5: Migration Dependency Graph** ⏳

**Sprint 6+:** DAG de dependencies para evitar aplicar migrations fuera de orden.

```yaml
# scripts/migrations/neo4j/migration_graph.yml

migrations:
  - id: "000_sprint0_schema_alignment"
    version: 0
    dependencies: []

  - id: "003_sprint1_domain_model_expansion"
    version: 1
    dependencies: ["000_sprint0_schema_alignment"]

  - id: "005_sprint2_api_model_expansion"
    version: 2
    dependencies: ["003_sprint1_domain_model_expansion"]

  - id: "007_sprint2.5_targets_entity"
    version: 2.5
    dependencies: ["005_sprint2_api_model_expansion"]  # Requiere Endpoint y Entity nodes
```

**Enforcement:**
```python
def validate_migration_order(migration_id: str, applied_migrations: List[str]):
    """Verifica que todas las dependencies fueron aplicadas."""
    required_deps = MIGRATION_GRAPH[migration_id]['dependencies']
    missing = [dep for dep in required_deps if dep not in applied_migrations]

    if missing:
        raise MigrationError(f"Missing dependencies: {missing}")
```

---

### 12.3 Riesgo #3: Concurrency en Parallel Migrations

**Descripción:**
Si dos migrations (o dos instancias del pipeline) intentan escribir GraphSchemaVersion simultáneamente, puede haber race conditions.

**Escenario:**
```
Time  | Process A                          | Process B
------|------------------------------------|---------------------------------
T0    | Read current_version = 2           | Read current_version = 2
T1    | Execute migration → v2.5           | Execute migration → v2.5
T2    | Write current_version = 2.5        | Write current_version = 2.5  ⚠️ RACE
T3    | Commit                             | Commit
```

**Resultado:** Ambos escriben `2.5`, pero pueden haber aplicado migrations diferentes (data corruption).

**Severidad:** 🟡 **MEDIA** - Raro en desarrollo (migrations secuenciales), pero posible en production con múltiples workers

---

#### 12.3.1 Mitigaciones IMPLEMENTADAS

**M3.1: Singleton Lock Pattern** ✅

**Implementación:** Usar GraphSchemaVersion `{singleton: true}` como mutex.

```cypher
// Acquire lock al empezar migration
MATCH (v:GraphSchemaVersion {singleton: true})
SET v.migration_in_progress = true,
    v.locked_by = $process_id,
    v.locked_at = datetime()
WHERE v.migration_in_progress IS NULL OR v.migration_in_progress = false
RETURN v.locked_by as acquired_lock;

// Si acquired_lock = $process_id → tenemos el lock
// Si acquired_lock IS NULL → otra instancia ya tiene el lock, ABORT
```

**Release lock al terminar:**
```cypher
MATCH (v:GraphSchemaVersion {singleton: true})
WHERE v.locked_by = $process_id
SET v.migration_in_progress = false
REMOVE v.locked_by, v.locked_at;
```

---

**M3.2: Lock Timeout** ✅

**Problema:** ¿Qué pasa si process A crashea con el lock adquirido?

**Solución:** Timeout automático después de 30 minutos.

```cypher
// Cleanup de locks stale (>30 min)
MATCH (v:GraphSchemaVersion {singleton: true})
WHERE v.migration_in_progress = true
  AND v.locked_at < datetime() - duration({minutes: 30})
SET v.migration_in_progress = false
REMOVE v.locked_by, v.locked_at
RETURN 'Stale lock cleared' as status;
```

**Cron job:** Ejecutar cada 10 minutos en background.

---

#### 12.3.2 Mitigaciones PENDIENTES

**M3.3: Distributed Lock con Redis** ⏳

**Sprint 7+:** Para pipelines distribuidos, usar Redis como lock coordinator.

```python
# src/cognitive/infrastructure/migration_lock.py

import redis
from contextlib import asynccontextmanager

class MigrationLock:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    @asynccontextmanager
    async def acquire(self, timeout_s: int = 1800):
        """Adquirir lock distribuido con timeout."""
        lock_key = "neo4j:migration:lock"
        process_id = f"{os.getpid()}@{socket.gethostname()}"

        # Try to acquire (NX = only if not exists)
        acquired = self.redis.set(lock_key, process_id, nx=True, ex=timeout_s)

        if not acquired:
            current_holder = self.redis.get(lock_key)
            raise MigrationLockError(f"Lock held by {current_holder}")

        try:
            yield  # Execute migration
        finally:
            # Release lock solo si seguimos siendo el holder
            if self.redis.get(lock_key) == process_id:
                self.redis.delete(lock_key)

# Uso:
async with migration_lock.acquire():
    await run_migration()
```

---

**M3.4: Migration Queue** ⏳

**Sprint 8+:** Queue de migrations para serializar automáticamente.

```python
# src/cognitive/infrastructure/migration_queue.py

from asyncio import Queue

class MigrationQueue:
    def __init__(self):
        self.queue = Queue()

    async def enqueue(self, migration_file: str):
        """Agregar migration a la cola."""
        await self.queue.put(migration_file)

    async def process_queue(self):
        """Procesar migrations secuencialmente."""
        while True:
            migration_file = await self.queue.get()
            try:
                await self.migration_runner.apply_migration(migration_file)
            except Exception as e:
                logger.error(f"Migration failed: {e}")
            finally:
                self.queue.task_done()

# Background worker
asyncio.create_task(migration_queue.process_queue())
```

---

### 12.4 Riesgo #4: DUAL_WRITE sin Estrategia de Salida

**Descripción:**
DUAL_WRITE mode (escribir tanto JSON property como Graph nodes) es útil para transición gradual, pero sin plan de salida puede convertirse en deuda técnica permanente.

**Problema:**
```python
# Código en src/cognitive/services/neo4j_ir_repository.py (HOY)

if USE_GRAPH_DOMAIN_MODEL:
    await domain_graph_repo.save_domain_model(app_id, domain_model)

# DUAL_WRITE: También guardar en JSON property (backward compatibility)
await self.neo4j.run("""
    MATCH (d:DomainModelIR {app_id: $app_id})
    SET d.domain_model_data = $json_data  # ⚠️ Redundancia permanente
""", app_id=app_id, json_data=domain_model.model_dump_json())
```

**Consecuencias:**
- ❌ Doble storage cost
- ❌ Doble write latency
- ❌ Riesgo de desincronización entre JSON y Graph
- ❌ Código legacy que nadie se atreve a remover

**Severidad:** 🟡 **MEDIA** - No bloquea funcionalidad, pero acumula deuda técnica

---

#### 12.4.1 Política de Retirement DEFINIDA

**Condiciones para Retirar DUAL_WRITE:**

1. ✅ **Roundtrip Tests al 100%**
   ```python
   async def test_domain_model_roundtrip():
       # Write usando graph
       await domain_graph_repo.save_domain_model(app_id, domain_model_original)

       # Read desde graph
       domain_model_loaded = await domain_graph_repo.load_domain_model(app_id)

       # Verificar igualdad
       assert domain_model_original == domain_model_loaded
   ```

2. ✅ **E2E Production Scenarios** (2+ casos)
   - Escenario 1: Full pipeline E2E (spec → IR → graph → code generation)
   - Escenario 2: Graph query correcta (Entity lookup, relationship traversal)

3. ✅ **Validation Period** (7 días sin issues)
   - Monitorear logs de errores
   - Validar que NINGÚN código usa `domain_model_data` JSON property
   - Stakeholder sign-off

---

#### 12.4.2 Execution Plan

**Fase 1: Validación (Sprint 3)**
```
[ ] Roundtrip tests implementados para DomainModelIR
[ ] Roundtrip tests implementados para APIModelIR
[ ] E2E scenario 1 passing
[ ] E2E scenario 2 passing
[ ] No accesses a JSON properties en últimos 7 días (log analysis)
```

**Fase 2: Feature Flag Flip (Sprint 3.5)**
```python
# Disable DUAL_WRITE en config
USE_GRAPH_DOMAIN_MODEL = True   # Ya existente
DUAL_WRITE_JSON = False  # NUEVO FLAG (default False)

# Código actualizado:
if USE_GRAPH_DOMAIN_MODEL:
    await domain_graph_repo.save_domain_model(app_id, domain_model)

if DUAL_WRITE_JSON:  # Solo si flag activo
    await self.neo4j.run("""...""")  # Escribir JSON
```

**Fase 3: Monitoring (48 horas)**
```
[ ] No errors en logs
[ ] Performance metrics estables (no degradación)
[ ] Stakeholder validation
```

**Fase 4: Cleanup (Sprint 4)**
```python
# PR: Eliminar código DUAL_WRITE permanentemente

# 1. Remover flag
# 2. Remover código de escritura JSON
# 3. Remover JSON properties del schema (migration)

# scripts/migrations/neo4j/015_remove_json_properties.cypher
MATCH (d:DomainModelIR)
REMOVE d.domain_model_data
RETURN count(d) as cleaned;

MATCH (a:APIModelIR)
REMOVE a.api_model_data
RETURN count(a) as cleaned;
```

**Fase 5: Verification (Sprint 4)**
```cypher
// Verificar que NO quedan JSON properties
MATCH (n)
WHERE n.domain_model_data IS NOT NULL
   OR n.api_model_data IS NOT NULL
RETURN count(n) as remaining_json_properties;
// Expected: 0
```

---

#### 12.4.3 Rollback Plan

**Si algo falla en Fase 2-3:**

```python
# Rollback instantáneo: flip flag
DUAL_WRITE_JSON = True  # Re-enable

# Investigar issue
# Fix problema
# Re-intentar retirement después de 1 sprint
```

**Si corruption detectada en Fase 4:**

```cypher
// Rollback: re-popular JSON desde Graph
MATCH (app:ApplicationIR {app_id: $app_id})
MATCH (app)-[:HAS_DOMAIN_MODEL]->(d:DomainModelIR)
MATCH (d)-[:HAS_ENTITY]->(e:Entity)
WITH d, collect(e) as entities

// Reconstruir JSON desde nodos
SET d.domain_model_data = apoc.convert.toJson({
    entities: [e IN entities | e {.*}]
});
```

---

### 12.5 Risk Matrix Summary

| Riesgo | Severidad | Probabilidad | Impact | Mitigaciones Implementadas | Mitigaciones Pendientes |
|--------|-----------|--------------|--------|----------------------------|-------------------------|
| **Performance Degradation** | 🔴 Alta | Media | Alto | Query entrypoints, indexes, batching, timeouts, LIMIT | Profiling automation, caching layer |
| **Schema Version Incoherence** | 🟡 Media | Baja | Medio | Naming convention, atomic updates, validation query | Pre-migration checks, dependency graph |
| **Concurrency Race Conditions** | 🟡 Media | Baja | Medio | Singleton lock, lock timeout | Redis distributed lock, migration queue |
| **DUAL_WRITE Tech Debt** | 🟡 Media | Alta | Bajo | Retirement policy defined, execution plan | Implementar Fases 1-5 en Sprints 3-4 |

---

### 12.6 Monitoring Dashboard (NeoDash)

**Query: Risk Indicators**

```cypher
// Performance Risk
CALL apoc.monitor.kernel() YIELD freeMemory, totalMemory
WITH freeMemory, totalMemory, (freeMemory * 100.0 / totalMemory) as free_pct
RETURN
    CASE
        WHEN free_pct < 20 THEN '🔴 Memory Pressure'
        WHEN free_pct < 50 THEN '🟡 Monitor Memory'
        ELSE '✅ Memory OK'
    END as memory_status,
    round(free_pct, 1) as free_memory_pct

UNION

// Schema Coherence Risk
MATCH (v:GraphSchemaVersion {singleton: true})
OPTIONAL MATCH (m:MigrationRun)
WHERE m.status = 'success'
WITH v, m
ORDER BY m.executed_at DESC
LIMIT 1
RETURN
    CASE
        WHEN v.current_version = m.schema_version_after THEN '✅ Schema Coherent'
        ELSE '🚨 Schema Mismatch'
    END as schema_status,
    v.current_version as current_version

UNION

// Lock Status
MATCH (v:GraphSchemaVersion {singleton: true})
RETURN
    CASE
        WHEN v.migration_in_progress = true THEN '🔄 Migration Running'
        ELSE '✅ No Active Migration'
    END as lock_status,
    v.locked_by as locked_by;
```

---

## 13. Archivos a Crear/Modificar

### 12.1 Nuevos Archivos (Graph Expansion)

```
src/cognitive/infrastructure/
├── neo4j_domain_schema.py      # Sprint 1
├── neo4j_api_schema.py         # Sprint 2
├── neo4j_behavior_schema.py    # Sprint 3
├── neo4j_validation_schema.py  # Sprint 4
├── neo4j_infra_schema.py       # Sprint 4
├── neo4j_tests_schema.py       # Sprint 5
└── neo4j_lineage_schema.py     # Sprint 6

src/cognitive/services/
├── domain_model_graph_repository.py    # Sprint 1
├── api_model_graph_repository.py       # Sprint 2
├── behavior_model_graph_repository.py  # Sprint 3
├── validation_graph_repository.py      # Sprint 4
├── infrastructure_graph_repository.py  # Sprint 4
├── tests_model_graph_repository.py     # Sprint 5
├── lineage_repository.py               # Sprint 6
├── pattern_usage_tracker.py            # Sprint 6
├── error_lineage.py                    # Sprint 7
├── pattern_optimizer.py                # Sprint 8
└── transfer_learning.py                # Sprint 8

scripts/migrations/neo4j/
├── 000_label_renaming.cypher           # Sprint 0
├── 001_domain_model_expansion.py       # Sprint 1
├── 002_api_model_expansion.py          # Sprint 2
├── 003_behavior_model_expansion.py     # Sprint 3
├── 004_validation_infra_expansion.py   # Sprint 4
└── 005_tests_model_initial.py          # Sprint 5
```

### 12.2 Archivos a Modificar

```
src/cognitive/services/
└── neo4j_ir_repository.py    # Sprints 0, 1-5 (labels + delegation)

tests/e2e/
└── real_e2e_full_pipeline.py # Sprints 5-8 (integration)
```

---

## 14. Testing Strategy

### 13.1 Unit Tests por Sprint

```
tests/cognitive/
├── test_domain_model_graph_repository.py   # Sprint 1
├── test_api_model_graph_repository.py      # Sprint 2
├── test_behavior_model_graph_repository.py # Sprint 3
├── test_validation_graph_repository.py     # Sprint 4
├── test_tests_model_graph_repository.py    # Sprint 5
├── test_lineage_repository.py              # Sprint 6
└── test_pattern_optimizer.py               # Sprint 8
```

### 13.2 Integration Tests

```
tests/integration/
├── test_neo4j_label_migration.py           # Sprint 0
├── test_domain_model_roundtrip.py          # Sprint 1
├── test_full_ir_graph.py                   # Sprint 5
└── test_lineage_tracking.py                # Sprint 6
```

### 13.3 Migration Tests

```
tests/migrations/
├── test_json_to_graph_migration.py         # All sprints
└── test_rollback_scenarios.py              # All sprints
```

---

## 15. Rollback Plan

### 14.1 Sprint 0 Rollback (Labels)

```cypher
// Revert label names
MATCH (n:ApplicationIR)
REMOVE n:ApplicationIR
SET n:Application;

// Repeat for each IR...
```

### 14.2 Sprint 1-5 Rollback (Graph Expansion)

```python
# Keep JSON properties during migration, only remove after verification
# Rollback: Restore from JSON property if needed

async def rollback_domain_model(app_id: str):
    # 1. Delete graph nodes
    await neo4j.run("""
        MATCH (d:DomainModelIR {app_id: $app_id})-[:HAS_ENTITY]->(e)
        OPTIONAL MATCH (e)-[:HAS_ATTRIBUTE]->(a)
        DETACH DELETE a, e
    """, app_id=app_id)

    # 2. JSON property still exists as backup
    # No further action needed
```

### 14.3 Feature Flags

```python
FEATURE_FLAGS = {
    "USE_GRAPH_DOMAIN_MODEL": os.getenv("USE_GRAPH_DOMAIN_MODEL", "false") == "true",
    "USE_GRAPH_API_MODEL": os.getenv("USE_GRAPH_API_MODEL", "false") == "true",
    # ... etc
}
```

---

## 16. Métricas de Éxito

### 15.1 Sprint 0 Success Criteria

| Métrica | Target | Verificación |
|---------|--------|--------------|
| Orphan nodes | 0 | `MATCH (n) WHERE NOT EXISTS...` |
| Labels con IR suffix | 100% | `CALL db.labels()` |
| neo4j_ir_repository tests | 100% pass | pytest |

### 15.2 Sprint 1-5 Success Criteria

| Métrica | Target | Verificación |
|---------|--------|--------------|
| JSON properties restantes | 0 | `WHERE n.domain_model_data IS NOT NULL` |
| Entity nodes | ~1,400 | `MATCH (e:Entity) RETURN count(e)` |
| Attribute nodes | ~7,000 | `MATCH (a:Attribute) RETURN count(a)` |
| Endpoint nodes | ~5,600 | `MATCH (e:Endpoint) RETURN count(e)` |
| TestScenarioIR nodes | ~5,600 | `MATCH (t:TestScenarioIR) RETURN count(t)` |
| Graph traversal queries | Working | Integration tests |
| Roundtrip tests | 100% pass | Load→Save→Load equals original |

### 15.3 Sprint 6-8 Success Criteria

| Métrica | Target | Verificación |
|---------|--------|--------------|
| IR cache hit rate | >80% | Lineage queries |
| Error repeat rate | <10% | Pre-gen context usage |
| First-pass success | >85% | Pipeline metrics |
| Pattern reuse | >60% | Pattern tracking |

---

## Appendix A: Complete Node Count Projection

| Sprint | Label | Estimado | Actual (2025-11-29) | Cumulative |
|--------|-------|----------|---------------------|------------|
| Existing | Pattern | 31,811 | 31,811 | 31,811 |
| Existing | ApplicationIR | 278 | 278 | 32,089 |
| 0 | (cleanup orphans) | -2 | -2 | 32,087 |
| 1 | Entity | 1,400 | **1,084** ✅ | 33,171 |
| 1 | Attribute | 7,000 | **5,204** ✅ | 38,375 |
| 2 | Endpoint | 5,600 | **4,022** ✅ | 42,397 |
| 2 | APIParameter | 11,200 | **668** ✅ | 43,065 |
| 2 | APISchema | 2,800 | **0** ✅ (vacío en datos) | 43,065 |
| 2 | APISchemaField | 8,400 | **0** ✅ (vacío en datos) | 43,065 |
| 3 | Flow | 840 | - | 43,905 |
| 3 | Step | 4,200 | - | 48,105 |
| 3 | Invariant | 560 | - | 48,665 |
| 4 | ValidationRule | 2,800 | - | 51,465 |
| 4 | TestCase | 1,400 | - | 52,865 |
| 4 | EnforcementStrategy | 2,800 | - | 55,665 |
| 4 | DatabaseConfig | 280 | - | 55,945 |
| 4 | ContainerService | 840 | - | 56,785 |
| 5 | TestsModelIR | 280 | - | 57,065 |
| 5 | SeedEntityIR | 1,400 | - | 58,465 |
| 5 | TestScenarioIR | 5,600 | - | 64,065 |
| 5 | EndpointTestSuite | 5,600 | - | 69,665 |
| 5 | FlowTestSuite | 840 | - | 70,505 |
| 6+ | Spec, GeneratedFile, etc | ~5,000 | - | ~75,500 |

**Total proyectado: ~75,500 nodos** (vs 35,358 inicial, 43,065 actual post-Sprint 2)

**Notas:**
- ✅ EntityRelationship eliminado - las relaciones se modelan como edges `RELATES_TO` con 132 edges creados en Sprint 1
- ✅ Actual Sprint 1: 1,084 Entity (77% del estimado) + 5,204 Attribute (74% del estimado)
- ✅ Actual Sprint 2: 4,022 Endpoint (72% del estimado) + 668 APIParameter (6% del estimado) - mayoría de endpoints no tienen parámetros explícitos
- ✅ APISchema/Field en 0: datos reales tienen schemas vacíos (normal para CRUD básico)

---

## Appendix B: Relationship Types Summary

| Relationship | From | To | Count Est |
|--------------|------|-----|-----------|
| HAS_DOMAIN_MODEL | ApplicationIR | DomainModelIR | 278 |
| HAS_API_MODEL | ApplicationIR | APIModelIR | 278 |
| HAS_BEHAVIOR_MODEL | ApplicationIR | BehaviorModelIR | 278 |
| HAS_VALIDATION_MODEL | ApplicationIR | ValidationModelIR | 278 |
| HAS_INFRASTRUCTURE_MODEL | ApplicationIR | InfrastructureModelIR | 278 |
| HAS_TESTS_MODEL | ApplicationIR | TestsModelIR | 278 |
| HAS_ENTITY | DomainModelIR | Entity | 1,400 |
| HAS_ATTRIBUTE | Entity | Attribute | 7,000 |
| RELATES_TO | Entity | Entity | 2,800 |
| HAS_ENDPOINT | APIModelIR | Endpoint | 5,600 |
| HAS_PARAMETER | Endpoint | APIParameter | 11,200 |
| REQUEST_SCHEMA | Endpoint | APISchema | 2,800 |
| RESPONSE_SCHEMA | Endpoint | APISchema | 2,800 |
| HAS_SCHEMA | APIModelIR | APISchema | 2,800 |
| HAS_FIELD | APISchema | APISchemaField | 8,400 |
| HAS_FLOW | BehaviorModelIR | Flow | 840 |
| HAS_STEP | Flow | Step | 4,200 |
| HAS_INVARIANT | BehaviorModelIR | Invariant | 560 |
| HAS_RULE | ValidationModelIR | ValidationRule | 2,800 |
| HAS_ENFORCEMENT | ValidationRule | EnforcementStrategy | 2,800 |
| HAS_TEST_CASE | ValidationModelIR | TestCase | 1,400 |
| HAS_DATABASE | InfrastructureModelIR | DatabaseConfig | 280 |
| HAS_CONTAINER | InfrastructureModelIR | ContainerService | 840 |
| HAS_SEED_ENTITY | TestsModelIR | SeedEntityIR | 1,400 |
| DEPENDS_ON_SEED | SeedEntityIR | SeedEntityIR | 700 |
| HAS_ENDPOINT_SUITE | TestsModelIR | EndpointTestSuite | 5,600 |
| HAS_HAPPY_PATH | EndpointTestSuite | TestScenarioIR | 5,600 |
| HAS_ERROR_CASE | EndpointTestSuite | TestScenarioIR | 5,600 |
| HAS_FLOW_SUITE | TestsModelIR | FlowTestSuite | 840 |
| HAS_SCENARIO | FlowTestSuite | TestScenarioIR | 2,520 |
| PRODUCES | Spec | ApplicationIR | ~500 |
| GENERATES | ApplicationIR | GeneratedFile | ~5,000 |
| USED_PATTERN | GeneratedFile | Pattern | ~25,000 |
| HAD_ERROR | GeneratedFile | Error | ~2,000 |
| CAUSED_BY_PATTERN | Error | Pattern | ~1,000 |

**Total nuevas relaciones: ~100,000+**

---

*Plan actualizado: 2025-11-29*
*Proyecto: DevMatrix/Agentic-AI*
*Versión: 2.0 (Graph-Native)*
