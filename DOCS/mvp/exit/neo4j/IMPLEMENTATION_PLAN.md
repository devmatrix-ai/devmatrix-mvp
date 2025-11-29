# Implementation Plan: Database Architecture 2.0 - Complete Graph Transformation

> Plan completo para transformar TODOS los datos a grafos con labels correctos.
> Fecha: 2025-11-29 (actualizado)
> Duración: 8 Sprints
> **Principio**: TODO debe ser grafo, NO JSON serializado

---

## Índice

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Estado Actual vs Objetivo](#2-estado-actual-vs-objetivo)
3. [Sprint 0: Schema Alignment & Cleanup](#3-sprint-0-schema-alignment--cleanup)
4. [Sprint 1: Graph Expansion - DomainModelIR](#4-sprint-1-graph-expansion---domainmodelir)
5. [Sprint 2: Graph Expansion - APIModelIR](#5-sprint-2-graph-expansion---apimodelir)
6. [Sprint 3: Graph Expansion - BehaviorModelIR](#6-sprint-3-graph-expansion---behaviormodelir)
7. [Sprint 4: Graph Expansion - ValidationModelIR + InfrastructureModelIR](#7-sprint-4-graph-expansion---validationmodelir--infrastructuremodelir)
8. [Sprint 5: Graph Expansion - TestsModelIR](#8-sprint-5-graph-expansion---testsmodelir)
9. [Sprint 6: Lineage & Intelligence](#9-sprint-6-lineage--intelligence)
10. [Sprint 7: Real-Time Tracking](#10-sprint-7-real-time-tracking)
11. [Sprint 8: Analytics & Optimization](#11-sprint-8-analytics--optimization)
12. [Archivos a Crear/Modificar](#12-archivos-a-crearmodificar)
13. [Testing Strategy](#13-testing-strategy)
14. [Rollback Plan](#14-rollback-plan)
15. [Métricas de Éxito](#15-métricas-de-éxito)

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
| 0 | Cleanup & Alignment | Orphans eliminados, labels renombrados |
| 1 | DomainModelIR → Graph | Entity, Attribute, Relationship como nodos |
| 2 | APIModelIR → Graph | Endpoint, APISchema, APIParameter como nodos |
| 3 | BehaviorModelIR → Graph | Flow, Step, Invariant como nodos |
| 4 | ValidationModelIR + InfrastructureModelIR | ValidationRule, DatabaseConfig como nodos |
| 5 | TestsModelIR → Graph | SeedEntityIR, TestScenarioIR como nodos |
| 6 | Lineage & Intelligence | Spec→IR→Files tracking |
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
| `EntityRelationship` | Entity.relationships | ~2,800 |
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
| **TOTAL NUEVOS** | | **~48,720 nodos** |

### 2.4 Métricas Target

| Métrica | Actual | Post-Sprint 5 | Post-Sprint 8 |
|---------|--------|---------------|---------------|
| Nodos totales | 35,358 | ~84,000 | ~100,000 |
| JSON en properties | ~2,240 | 0 | 0 |
| Labels con IR suffix | 0% | 100% | 100% |
| Graph traversal queries | 0 | 100% | 100% |
| IR cache hit rate | 0% | 80% | 95% |
| First-pass success | ~60% | 75% | 90% |

---

## 3. Sprint 0: Schema Alignment & Cleanup

**Objetivo:** Limpiar datos huérfanos y alinear labels con código Python.

**Prioridad:** P0 (CRÍTICO - prerequisito de todo lo demás)

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
- [ ] Script de identificación de orphans
- [ ] Script de limpieza (idempotent)
- [ ] Verificación post-limpieza

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
- [ ] Script de verificación
- [ ] Documentar en schema que están deprecated

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
- [ ] Migration script (label_renaming.cypher)
- [ ] Rollback script
- [ ] Verification queries

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
- [ ] neo4j_ir_repository.py actualizado
- [ ] Tests actualizados
- [ ] Backward compatibility verificada

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
- [ ] Pattern classification script
- [ ] Report de patterns clasificados
- [ ] Tests

---

### 3.2 Sprint 0 Checklist

```
[ ] Task 0.1: Eliminar Orphan Nodes
[ ] Task 0.2: Eliminar/Documentar Empty Labels
[ ] Task 0.3: Renaming de Labels IR
[ ] Task 0.4: Actualizar neo4j_ir_repository.py
[ ] Task 0.5: Clasificar Patterns Sin Tags
[ ] Verification: Todos labels usan IR suffix
[ ] Tests pasan con nuevos labels
```

---

## 4. Sprint 1: Graph Expansion - DomainModelIR

**Objetivo:** Expandir DomainModelIR de JSON a nodos Entity, Attribute, Relationship.

**Prioridad:** P0

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
- [ ] Schema creation script
- [ ] Migration script
- [ ] Verification queries

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
- [ ] DomainModelGraphRepository class
- [ ] Unit tests
- [ ] Integration tests

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
- [ ] Migration script
- [ ] Rollback script
- [ ] Progress logging
- [ ] Verification queries

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
- [ ] Updated neo4j_ir_repository.py
- [ ] Backward compatibility layer
- [ ] Tests updated

---

### 4.3 Sprint 1 Checklist

```
[ ] Task 1.1: Create Entity Nodes Schema
[ ] Task 1.2: Domain Model Repository (Graph Version)
[ ] Task 1.3: Migration Script - JSON to Graph
[ ] Task 1.4: Update neo4j_ir_repository.py
[ ] Verification: 0 JSON domain_model_data properties
[ ] Verification: ~1,400 Entity nodes created
[ ] Verification: ~7,000 Attribute nodes created
[ ] All tests pass
```

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
[ ] Task 2.1: Create API Nodes Schema
[ ] Task 2.2: API Model Repository (Graph Version)
[ ] Task 2.3: Migration Script - API JSON to Graph
[ ] Task 2.4: Update neo4j_ir_repository.py
[ ] Verification: ~5,600 Endpoint nodes
[ ] Verification: ~11,200 APIParameter nodes
[ ] Verification: ~2,800 APISchema nodes
```

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

## 12. Archivos a Crear/Modificar

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

## 13. Testing Strategy

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

## 14. Rollback Plan

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

## 15. Métricas de Éxito

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

| Sprint | Label | Count | Cumulative |
|--------|-------|-------|------------|
| Existing | Pattern | 31,811 | 31,811 |
| Existing | ApplicationIR | 278 | 32,089 |
| 0 | (cleanup) | -2 | 32,087 |
| 1 | Entity | 1,400 | 33,487 |
| 1 | Attribute | 7,000 | 40,487 |
| 1 | EntityRelationship | 2,800 | 43,287 |
| 2 | Endpoint | 5,600 | 48,887 |
| 2 | APIParameter | 11,200 | 60,087 |
| 2 | APISchema | 2,800 | 62,887 |
| 2 | APISchemaField | 8,400 | 71,287 |
| 3 | Flow | 840 | 72,127 |
| 3 | Step | 4,200 | 76,327 |
| 3 | Invariant | 560 | 76,887 |
| 4 | ValidationRule | 2,800 | 79,687 |
| 4 | TestCase | 1,400 | 81,087 |
| 4 | EnforcementStrategy | 2,800 | 83,887 |
| 4 | DatabaseConfig | 280 | 84,167 |
| 4 | ContainerService | 840 | 85,007 |
| 5 | TestsModelIR | 280 | 85,287 |
| 5 | SeedEntityIR | 1,400 | 86,687 |
| 5 | TestScenarioIR | 5,600 | 92,287 |
| 5 | EndpointTestSuite | 5,600 | 97,887 |
| 5 | FlowTestSuite | 840 | 98,727 |
| 6+ | Spec, GeneratedFile, etc | ~5,000 | ~104,000 |

**Total proyectado: ~104,000 nodos** (vs 35,358 actuales)

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
