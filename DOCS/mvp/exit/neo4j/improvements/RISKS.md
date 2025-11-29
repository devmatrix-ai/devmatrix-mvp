# Riesgos Críticos - Neo4j Migration

> **5 riesgos identificados con soluciones concretas**
> **Fecha**: 2025-11-29

---

## R1: Falta Atomicidad en Migraciones

**Severidad**: 🔴 CRÍTICO
**Impacto**: Inconsistencia del grafo en caso de fallo
**Sprints afectados**: Todos

### Problema

```yaml
Escenario:
  1. Script empieza a crear 1,000 Entity nodes
  2. En node 500, falla (network issue, OOM, etc)
  3. Grafo queda con 500 entities (parcial)
  4. Re-ejecutar script → duplicados o inconsistencia
```

### Solución: Batch Checkpoints + Rollback Automático

```python
class AtomicMigration:

    async def execute_with_checkpoints(
        self,
        migration_id: str,
        batches: list[Batch],
        checkpoint_interval: int = 100
    ):
        """
        Si falla:
        - Rollback automático al último checkpoint
        - Log de progreso para resume manual si necesario
        """
        checkpoint_state = {
            "migration_id": migration_id,
            "batches_completed": 0,
            "last_checkpoint": None
        }

        try:
            for i, batch in enumerate(batches):
                result = await self._execute_batch(batch)

                if i % checkpoint_interval == 0:
                    await self._create_checkpoint(checkpoint_state)

        except Exception as e:
            await self._rollback_to_checkpoint(checkpoint_state["last_checkpoint"])
            raise MigrationError(f"Failed at batch {i}, rolled back")
```

**Cypher para Checkpoint Node**:
```cypher
CREATE (cp:MigrationCheckpoint {
    checkpoint_id: string,
    migration_id: string,
    batch_number: integer,
    nodes_created: integer,
    edges_created: integer,
    created_at: datetime
})
```

**Esfuerzo**: 1 día
**Prioridad**: Implementar antes de Sprint 3

---

## R2: Interconexión IR Insuficiente

**Severidad**: 🔴 CRÍTICO (EL MÁS GRAVE)
**Impacto**: Grafo fragmentado sin inteligencia real
**Sprints afectados**: 2-7

### Problema

```yaml
Estado actual:
  - 6 subgrafos potencialmente aislados
  - DomainModelIR ↔ APIModelIR: SIN CONEXIÓN
  - BehaviorModelIR ↔ DomainModelIR: SIN CONEXIÓN
  - ValidationModelIR ↔ DomainModelIR: SIN CONEXIÓN

Consecuencias:
  - No hay lineage real
  - QA imposible
  - Cambios en Entity no alertan sobre Endpoints
```

### Solución: Edges Críticos por Sprint

| Sprint | Edge | From | To |
|--------|------|------|-----|
| **2.5** | `TARGETS_ENTITY` | Endpoint | Entity |
| **3** | `TARGETS_ENTITY` | Step | Entity |
| **3** | `CALLS_ENDPOINT` | Step | Endpoint |
| **3** | `APPLIES_TO` | Invariant | Entity |
| **3** | `CHECKS_ATTRIBUTE` | Invariant | Attribute |
| **4** | `VALIDATES_FIELD` | ValidationRule | Attribute |
| **5** | `VALIDATES_ENDPOINT` | TestScenarioIR | Endpoint |
| **5** | `VALIDATES_RULE` | TestScenarioIR | ValidationRule |

### Ejemplo Visual

```
ANTES (fragmentado):
[ApplicationIR]──→[DomainModelIR]──→[Entity]
[ApplicationIR]──→[APIModelIR]──→[Endpoint]
[ApplicationIR]──→[BehaviorModelIR]──→[Flow]
# ↑ Sin conexiones entre IRs

DESPUÉS (conectado):
[Entity]←──TARGETS_ENTITY──[Endpoint]
[Entity]←──TARGETS_ENTITY──[Step]──CALLS_ENDPOINT──→[Endpoint]
[Attribute]←──VALIDATES_FIELD──[ValidationRule]
```

**Esfuerzo**: Distribuido en Sprints 2.5-5
**Bloqueante**: Sprint 2.5 bloquea Sprint 3

---

## R3: Falta Graph Shape Contract

**Severidad**: 🟡 ALTO
**Impacto**: Sin validación de integridad estructural
**Sprints afectados**: Todos

### Problema

```yaml
Sin contrato formal:
  - No se puede validar integridad post-migración
  - No se detectan inconsistencias automáticamente
  - No hay enforcement de reglas arquitectónicas

Ejemplos de violaciones no detectadas:
  - Entity sin Attributes
  - DomainModelIR sin Entities
  - Endpoint sin APIModelIR parent
```

### Solución: GRAPH_SHAPE_CONTRACT.yml

**Ya creado**: `DOCS/mvp/exit/neo4j/GRAPH_SHAPE_CONTRACT.yml`

**Contenido**:
- Cardinalidades para todos los nodos
- Propiedades requeridas
- Queries de validación
- Estrategia de migración

**Ejemplo de contrato**:
```yaml
Entity:
  cardinality:
    HAS_ATTRIBUTE: [1, null]  # At least 1

  required_properties:
    - entity_id: string
    - name: string
    - created_at: datetime
    - updated_at: datetime

  validation_rules:
    - "MUST have at least 1 Attribute"
```

**Esfuerzo**: ✅ COMPLETADO (documento creado)
**Pendiente**: Implementar validator en Python

---

## R4: Temporal Metadata Inconsistente

**Severidad**: 🟡 ALTO
**Impacto**: Sin lineage temporal confiable
**Sprints afectados**: 1-5

### Problema

```yaml
Estado actual:
  - ApplicationIR: ✅ Tiene created_at/updated_at
  - DomainModelIR: ✅ Tiene created_at/updated_at
  - Entity: ❌ NO tiene
  - Attribute: ❌ NO tiene
  - Endpoint: ❌ NO tiene
  - APIParameter: ❌ NO tiene

Consecuencias:
  - Imposible rastrear evolución
  - Debugging de migraciones muy difícil
  - Lineage temporal incompleto
```

### Solución: Migración 006

```cypher
-- Add temporal metadata to existing nodes
MATCH (n)
WHERE n:Entity OR n:Attribute OR n:Endpoint OR n:APIParameter
  AND NOT EXISTS(n.created_at)
SET
  n.created_at = datetime(),
  n.updated_at = datetime(),
  n.schema_version = 1;
```

**Enforcement en repositorios**:
```python
# En GraphIRRepository base class
@staticmethod
def _add_temporal_metadata(properties: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        **properties,
        "created_at": now,
        "updated_at": now,
        "schema_version": 1
    }
```

**Esfuerzo**: 2-3 hours
**Tarea**: IA.5

---

## R5: Sprint 5 Sobrecargado

**Severidad**: 🟡 ALTO
**Impacto**: Alto riesgo de retraso/incompletitud
**Sprint afectado**: 5

### Problema

```yaml
TestsModelIR es el módulo más complejo:
  - 7 tipos de nodos diferentes
  - 15+ tipos de relaciones
  - Dependencias complejas (seeds, scenarios, validations)
  - Assertions con múltiples targets

Riesgo:
  - Sprint time > 2 semanas
  - Testing inadecuado
  - Incompletitud
```

### Solución: Dividir en 2 Sprints

#### Sprint 5 — MVP (1 semana)

```yaml
Scope:
  Nodos:
    - TestsModelIR
    - EndpointTestSuite
    - TestScenarioIR (básico)

  Edges:
    - VALIDATES_ENDPOINT

  Objetivo:
    - Validación básica endpoint-level
    - Sin seeds, sin flows, sin assertions complejas
```

#### Sprint 5.5 — Complete (1 semana)

```yaml
Scope:
  Nodos:
    - SeedEntityIR
    - FlowTestSuite
    - Assertions
    - TestExecutionIR  # ← CRÍTICO

  Edges:
    - DEPENDS_ON_SEED
    - VALIDATES_FLOW
    - VALIDATES_RULE
    - HAS_EXECUTION

  Objetivo:
    - Testing end-to-end completo
    - Seeds y dependencias
    - Métricas de ejecución reales
```

### TestExecutionIR (Gap Crítico)

El plan original solo contempla escenarios, no ejecuciones:

```cypher
CREATE (exec:TestExecutionIR {
    execution_id: string,
    scenario_id: string,
    status: string,           # "pass" | "fail" | "error"
    duration_ms: integer,
    environment: string,      # "dev" | "staging" | "prod"
    code_branch: string,
    started_at: datetime,
    completed_at: datetime
})

(TestScenarioIR)-[:HAS_EXECUTION]->(TestExecutionIR)
```

**Esfuerzo**: Replanning ~2h, implementación distribuida
**Impacto**: Reduce riesgo significativamente

---

## Matriz de Priorización

| Riesgo | Severidad | Esfuerzo | Prioridad | Cuándo |
|--------|-----------|----------|-----------|--------|
| R2 | 🔴 CRÍTICO | Alto | 1 | Sprint 2.5 (ahora) |
| R1 | 🔴 CRÍTICO | Medio | 2 | Antes de Sprint 3 |
| R4 | 🟡 ALTO | Bajo | 3 | Esta semana (IA.5) |
| R3 | 🟡 ALTO | Bajo | 4 | Ya completado (doc) |
| R5 | 🟡 ALTO | Bajo | 5 | Replanning Sprint 5 |

---

*Ver también*: [ACTION_PLAN.md](./ACTION_PLAN.md) para timeline detallado
