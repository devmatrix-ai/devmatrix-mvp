
**Sprint**: Pre-Sprint 3 (Tareas Inmediatas)
**Fecha inicio**: 2025-11-29
**Última actualización**: 2025-11-29 14:01

---

## Estado Actual

### ✅ Migraciones y Tareas Completadas

| ID | Tarea/Migración | Estado | Fecha | Detalles |
|----|-----------------|--------|-------|----------|
| 001 | GraphSchemaVersion Singleton | ✅ DONE | 2025-11-29 12:56 | 1 node created |
| 002 | Register Past Migrations | ✅ DONE | 2025-11-29 13:57 | 5 MigrationRun nodes |
| IA.3 | GraphIRRepository base class | ✅ DONE | 2025-11-29 14:00 | ~420 lines, 6 métodos |
| IA.3b | Refactor DomainModelGraphRepository | ✅ DONE | 2025-11-29 14:01 | Hereda de base class |
| IA.3c | Refactor APIModelGraphRepository | ✅ DONE | 2025-11-29 14:01 | Hereda de base class |
| IA.4 | Roundtrip tests (DomainModelIR + APIModelIR) | ✅ DONE | 2025-11-29 | 4 tests passing |
| IA.5 | Add temporal metadata to Entity/Attribute | ✅ DONE | 2025-11-29 | 10,982 nodes updated |
| 006 | Add temporal metadata migration | ✅ DONE | 2025-11-29 | Schema v3 |
| IA.6 | Validation queries (cardinalidades) | ✅ DONE | 2025-11-29 | 7 checks, 3 errors found |
| 007 | TARGETS_ENTITY inference | ✅ DONE | 2025-11-29 | 3,394 relationships, Schema v4 |
| 2.5.1 | TARGETS_ENTITY inference engine | ✅ DONE | 2025-11-29 | 84.3% coverage |
| 2.5.2 | APISchema.source field migration | ✅ DONE | 2025-11-29 | 2 schemas updated |
| 2.5.3 | Coverage QA dashboard queries | ✅ DONE | 2025-11-29 | Dashboard implementado |
| IA.7 | Graph Shape Contract implementation | ✅ DONE | 2025-11-29 | Validation script + 12 pytest tests |

### ⏳ Tareas Pendientes

| ID | Tarea | Estimado | Prioridad |
|----|-------|----------|-----------|
| IA.4b | Document DUAL_WRITE retirement policy | 30 min | 🟢 LOW |

---

## Resumen de Objetos Creados

### 001_graph_schema_version

**Nodos:**
- `GraphSchemaVersion` (singleton): 1 node
  - `current_version`: 4
  - `last_migration`: "007_infer_targets_entity"
  - `sprints_completed`: ["Sprint 0", "Sprint 1", "Sprint 2"]

**Propiedades:**
- Singleton lock pattern: `{singleton: true}`
- Temporal tracking: `created_at`, `updated_at`

### 002_register_past_migrations

**Nodos:**
- `MigrationRun`: 5 nodes

**Relaciones:**
- `RESULTED_IN_VERSION`: 5 edges (MigrationRun → GraphSchemaVersion)

**Métricas Retroactivas:**
```
Sprint 0:
  - 001_sprint0_cleanup_orphans: 156 deleted
  - 002_sprint0_domain_label_rename: 1,084 updated

Sprint 1:
  - 003_sprint1_domain_model_expansion: 1,084 created (Entity nodes)
  - 004_sprint1_attribute_expansion: 5,834 created (Attribute nodes)

Sprint 2:
  - 005_sprint2_api_model_expansion: 4,022 created (Endpoint nodes)

TOTAL:
  - Created: 10,940 nodes
  - Updated: 1,084 nodes
  - Deleted: 156 nodes
```

### IA.3: GraphIRRepository Base Class

**Archivo**: `src/cognitive/services/graph_ir_repository.py`

**Clase Base (~420 líneas):**

```python
class GraphIRRepository:
    # Driver management
    def __init__(uri, user, password, database)
    def close()
    def __enter__() / __exit__()

    # Temporal metadata
    @staticmethod _add_temporal_metadata(properties) → Dict
    @staticmethod _update_temporal_metadata(properties) → Dict

    # Batch operations
    def batch_create_nodes(session, label, properties_list, batch_size=500) → int
    def batch_create_relationships(session, rel_type, pairs, ...) → int

    # Subgraph replacement
    def replace_subgraph(session, root_label, root_id, child_rels) → Dict[str, int]

    # Transaction helpers
    def execute_in_transaction(operation, *args, **kwargs) → Any
```

**Repositorios Refactorizados:**

1. **DomainModelGraphRepository** (ahora hereda de GraphIRRepository):
   - Eliminadas ~70 líneas de código duplicado
   - Constructor, close(), context managers → heredados
   - Usa database=self.database en sessions

2. **APIModelGraphRepository** (ahora hereda de GraphIRRepository):
   - Eliminadas ~70 líneas de código duplicado
   - Constructor, close(), context managers → heredados
   - Usa database=self.database en sessions

**Beneficios:**

- **DRY**: ~140 líneas eliminadas de código duplicado
- **Consistencia**: Mismo patrón para temporal metadata en todos los repos
- **Reusabilidad**: Futuros repos (BehaviorModelIR, ValidationModelIR) heredarán métodos comunes
- **Mantenibilidad**: Cambios en base class se propagan a todos los repos

---

## Queries de Verificación

### Ver estado de GraphSchemaVersion

```cypher
MATCH (v:GraphSchemaVersion {singleton: true})
RETURN
    v.current_version as version,
    v.last_migration as last_migration,
    v.sprints_completed as sprints,
    v.created_at as created,
    v.updated_at as updated;
```

**Output esperado:**
```
version: 2
last_migration: "005_sprint2_api_model_expansion"
sprints: ["Sprint 0", "Sprint 1", "Sprint 2"]
```

### Ver todas las migraciones registradas

```cypher
MATCH (m:MigrationRun)-[:RESULTED_IN_VERSION]->(v:GraphSchemaVersion)
RETURN
    m.migration_id as migration,
    m.schema_version_before as from_version,
    m.schema_version_after as to_version,
    m.status as status,
    m.objects_created as created,
    m.objects_updated as updated,
    m.objects_deleted as deleted,
    m.duration_seconds as duration,
    v.current_version as current_schema_version
ORDER BY m.started_at;
```

### Resumen de métricas por Sprint

```cypher
MATCH (m:MigrationRun)
WITH
    CASE
        WHEN m.migration_id CONTAINS "sprint0" THEN "Sprint 0"
        WHEN m.migration_id CONTAINS "sprint1" THEN "Sprint 1"
        WHEN m.migration_id CONTAINS "sprint2" THEN "Sprint 2"
        ELSE "Unknown"
    END as sprint,
    sum(m.objects_created) as total_created,
    sum(m.objects_updated) as total_updated,
    sum(m.objects_deleted) as total_deleted,
    sum(m.duration_seconds) as total_duration
RETURN
    sprint,
    total_created,
    total_updated,
    total_deleted,
    total_duration
ORDER BY sprint;
```

### Verificar coherencia del grafo

```cypher
// Contar todos los nodos de infraestructura
MATCH (v:GraphSchemaVersion)
WITH count(v) as schema_count
MATCH (m:MigrationRun)
WITH schema_count, count(m) as migration_count
MATCH (m:MigrationRun)-[:RESULTED_IN_VERSION]->()
RETURN
    schema_count as GraphSchemaVersion_count,
    migration_count as MigrationRun_count,
    count(m) as RESULTED_IN_VERSION_count;
```

**Output esperado:**
```
GraphSchemaVersion_count: 1
MigrationRun_count: 5
RESULTED_IN_VERSION_count: 5
```

---

## Próximos Pasos (Orden Recomendado)

### ✅ GraphIRRepository Base Class (IA.3) - COMPLETADO

**Archivo**: `src/cognitive/services/graph_ir_repository.py` (~420 líneas)

**Completado 2025-11-29 14:00:**

- ✅ Clase base GraphIRRepository con 6 métodos principales
- ✅ DomainModelGraphRepository refactorizado (eliminadas ~70 líneas)
- ✅ APIModelGraphRepository refactorizado (eliminadas ~70 líneas)
- ✅ Template Method pattern implementado
- ✅ DRY: Total ~140 líneas de código duplicado eliminadas

### 1️⃣ Tests de Integración (IA.4) - SIGUIENTE

**Casos de prueba:**

```python
# Test roundtrip DomainModelIR
def test_domain_model_roundtrip():
    # 1. Save DomainModelIR to graph
    # 2. Load DomainModelIR from graph
    # 3. Assert equality (deep comparison)

# Test roundtrip APIModelIR
def test_api_model_roundtrip():
    # 1. Save APIModelIR to graph
    # 2. Load APIModelIR from graph
    # 3. Assert equality (deep comparison)

# Test DUAL_WRITE coherence
def test_dual_write_coherence():
    # 1. Save IR via new method
    # 2. Verify old JSON still accessible
    # 3. Assert both representations match
```

### 4️⃣ DUAL_WRITE Retirement Policy (IA.4b)

**Documento**: `DOCS/mvp/exit/neo4j/DUAL_WRITE_RETIREMENT.yml`

**Contenido**:
- 5 fases de retirement (100% → 0% legacy)
- Criterios de exit por fase
- Rollback plan por fase
- Timeline estimado

---

## Archivos Relacionados

### Documentación Principal

- `IMPLEMENTATION_PLAN.md` - Plan maestro (255KB)
- `DATABASE_ARCHITECTURE.md` - Arquitectura del grafo
- `DATA_STRUCTURES_INVENTORY.md` - Inventario de estructuras de datos
- `GRAPH_SHAPE_CONTRACT.yml` - Contrato de integridad del grafo

### Análisis de Mejoras (`improvements/`)

- [SUMMARY.md](improvements/SUMMARY.md) - Resumen ejecutivo (entry point)
- [RISKS.md](improvements/RISKS.md) - 5 riesgos críticos
- [SPRINT_0-2.md](improvements/SPRINT_0-2.md) - Análisis Sprints completados
- [SPRINT_3-5.md](improvements/SPRINT_3-5.md) - Análisis Sprints core
- [SPRINT_6-8.md](improvements/SPRINT_6-8.md) - Análisis Sprints avanzados
- [ACTION_PLAN.md](improvements/ACTION_PLAN.md) - Plan de acción con timeline
- [PIPELINE_DB_GAPS.md](improvements/PIPELINE_DB_GAPS.md) - Gaps de uso de DBs en pipeline
- [VISION_2.0.md](improvements/VISION_2.0.md) - Visión estratégica "Pipeline con Memoria"

### Scripts de Migración
- `001_graph_schema_version.cypher` - Singleton creation
- `001_rollback_graph_schema_version.cypher` - Rollback
- `001_execute_graph_schema_version.py` - Execution script
- `README_001.md` - Documentation

- `002_register_past_migrations.cypher` - MigrationRun retroactive
- `002_execute_register_past_migrations.py` - Execution script
- `006_add_temporal_metadata.cypher` - Temporal metadata
- `006_execute_add_temporal_metadata.py` - Execution script
- `007_infer_targets_entity.py` - TARGETS_ENTITY inference (Sprint 2.5)
- `008_validate_graph_shape_contract.py` - Graph Shape Contract validation (IA.7)
- `validate_graph_integrity.py` - Graph validation (IA.6)

### Tests de Integración
- `tests/integration/test_ir_repositories_roundtrip.py` - IR roundtrip tests (IA.4)
- `tests/integration/test_graph_shape_contract.py` - Contract validation tests (IA.7)

### Código Fuente
- `src/cognitive/infrastructure/neo4j_client.py` - Neo4j client
- `src/cognitive/services/domain_model_graph_repository.py` - Domain repo
- `src/cognitive/services/api_model_graph_repository.py` - API repo

---

## Warnings y Consideraciones

### Neo4j Deprecation Warnings

Durante las migraciones se recibieron warnings de Neo4j 5.x:

1. **`id()` function deprecated**:
   ```
   The query used a deprecated function: `id`
   ```

   **Solución**: En futuras migraciones usar `elementId()` en lugar de `id()`:
   ```cypher
   // ANTES
   WHERE id(other) <> id(v)

   // DESPUÉS
   WHERE elementId(other) <> elementId(v)
   ```

2. **UnknownLabel/UnknownProperty warnings**:
   - Son esperados en pre-checks de migraciones
   - No afectan la ejecución
   - Indican que el label/property no existía aún (correcto para migraciones)

### Performance Considerations

Con ~75K nodes totales en el grafo:
- Queries con MATCH completo pueden tardar >1s
- Usar entrypoints específicos (ApplicationIR, DomainModelIR, etc.)
- Crear índices para búsquedas frecuentes
- Usar LIMIT para queries exploratorias

### Coherencia del Schema

**Crítico**: Mantener coherencia entre:
- `GraphSchemaVersion.current_version`
- `GraphSchemaVersion.last_migration`
- `MigrationRun.migration_id` del último registro

**Verificación**:
```cypher
MATCH (v:GraphSchemaVersion {singleton: true})
MATCH (m:MigrationRun {migration_id: v.last_migration})
RETURN v.current_version = m.schema_version_after as coherent;
```

Debe retornar `coherent: true`.

---

## 🎯 Sprint 2.5 - TARGETS_ENTITY & API Coverage (CRÍTICO)

**Estado**: PENDIENTE
**Prioridad**: 🔴 CRÍTICO
**Bloqueante para**: Sprint 3, 5, 6

### Objetivo

Conectar APIModelIR con DomainModelIR antes de continuar con BehaviorModelIR.

### Deliverables

#### 2.5.1 TARGETS_ENTITY Inference (4-6 hours)

**Script**: `007_infer_targets_entity.py`

**Estrategias de inferencia**:

1. **Path Analysis**: `/products` → `Entity(Product)`
2. **Schema Matching**: `request_body_schema="ProductCreate"` → `Entity(Product)`
3. **Operation Semantic**: `POST /api/v1/products` → `"create Product"`
4. **LLM Validation**: Para casos ambiguos

**Edge creado**:
```cypher
(Endpoint)-[:TARGETS_ENTITY {
    confidence: float,
    inference_method: string,
    validated: bool
}]->(Entity)
```

#### 2.5.2 APISchema.source Field (1 hour)

**Migración**: `007b_add_source_field.cypher`

```cypher
MATCH (s:APISchema)
SET s.source = CASE
    WHEN s.from_spec = true THEN 'spec'
    WHEN s.validated = true THEN 'validated'
    ELSE 'inferred'
END;
```

#### 2.5.3 Coverage QA Dashboard (2 hours)

**Query de cobertura**:
```cypher
MATCH (api:APIModelIR)-[:HAS_ENDPOINT]->(e:Endpoint)
OPTIONAL MATCH (e)-[:TARGETS_ENTITY]->(entity:Entity)
WITH api, count(e) as total_endpoints, count(entity) as linked_endpoints
RETURN
    api.app_id,
    total_endpoints,
    linked_endpoints,
    (100.0 * linked_endpoints / total_endpoints) as coverage_percent
ORDER BY coverage_percent ASC;
```

**Objetivo de cobertura**: ≥80%

### Impacto si no se implementa

Sin `TARGETS_ENTITY`:

- ❌ No hay trazabilidad API ↔ Domain
- ❌ QA no puede validar "endpoint implementa entity correctamente"
- ❌ Lineage roto: cambios en Entity no alertan sobre Endpoints afectados
- ❌ BehaviorModel no puede conectar Flow → Step → Entity

---

## Timeline Estimado

**Día 1 (HOY - 2025-11-29)**:

- ✅ IA.1: GraphSchemaVersion (30 min) ✓ DONE 12:56
- ✅ IA.2: Register Past Migrations (30 min) ✓ DONE 13:57
- ✅ IA.3: GraphIRRepository base class (2 hours) ✓ DONE 14:00
- ✅ IA.3b/c: Refactor repositories (1 hour) ✓ DONE 14:01
- ✅ IA.4: Roundtrip tests ✓ DONE (4 tests passing)
- ✅ IA.5: Temporal metadata ✓ DONE (10,982 nodes updated)
- ✅ IA.6: Validation queries ✓ DONE (7 checks implemented)
- ⏳ IA.4b: DUAL_WRITE policy (30 min)

**Día 1-2 (2025-11-29/30)**:

- 🎯 **Sprint 2.5**: TARGETS_ENTITY inference (4-6 hours)

**Total Tareas Inmediatas**: ~1 día (8/9 completadas - 88.9%)
**Total Sprint 2.5**: ~0.5-1 día

---

## IA.6: Graph Validation Results

**Script**: `scripts/migrations/neo4j/validate_graph_integrity.py`

**Estadísticas del Grafo** (46,701 nodos totales):
```
Pattern: 31,811 | Attribute: 5,204 | Endpoint: 4,024 | Entity: 1,084
APIModelIR: 561 | APIParameter: 670 | DomainModelIR: 278 | ApplicationIR: 278
```

**Validaciones Implementadas**:
1. ✅ Entities must have ≥1 Attribute → 6 violaciones
2. ✅ DomainModelIR must have ≥1 Entity → 10 violaciones
3. ✅ APIModelIR must have ≥1 Endpoint → 308 violaciones
4. ✅ ApplicationIR must have DomainModelIR and APIModelIR → OK
5. ⚠️ No orphan nodes → 3,373 huérfanos (Pattern, SuccessfulCode, etc.)
6. ✅ Nodes have temporal metadata → OK
7. ✅ Schema version coherence → OK

**Hallazgos**: Data inconsistente de ejecuciones anteriores. Sprint 2.5 debería limpiar estas inconsistencias.

---

*Última actualización: 2025-11-29*
*Progreso: 8/9 tareas completadas (88.9%)*
