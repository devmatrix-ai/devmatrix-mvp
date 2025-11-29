# Análisis de Sprints 0-2 (Completados)

> **Sprints ya ejecutados - Análisis de gaps y mejoras pendientes**
> **Fecha**: 2025-11-29

---

## Sprint 0 — Schema Alignment & Cleanup ✅

**Estado**: COMPLETADO
**Fecha**: 2025-11-29

### Logros

| Tarea | Estado | Métricas |
|-------|--------|----------|
| Eliminación de orphans | ✅ | 156 nodos eliminados |
| Renombrado a IR suffix | ✅ | 1,084 nodos actualizados |
| Documentación de empty labels | ✅ | - |
| Fixes en neo4j_ir_repository | ✅ | - |
| Scripts idempotentes | ✅ | - |

### Gap Identificado

**Task 0.6: Schema Health Check (FALTANTE)**

```yaml
Problema:
  - Sin validación post-migración automatizada
  - Sin métricas de coherencia del grafo

Queries requeridas:
  - ¿Cuántos ApplicationIR quedaron sin DomainModelIR?
  - ¿Cuántos DomainModelIR sin entidades?
  - ¿Existen endpoints sin APIModelIR?
  - ¿Hay nodos huérfanos?
```

**Query propuesto**:
```cypher
-- Schema Health Check
MATCH (app:ApplicationIR)
OPTIONAL MATCH (app)-[:HAS_DOMAIN_MODEL]->(dm)
OPTIONAL MATCH (app)-[:HAS_API_MODEL]->(am)
WITH
    count(app) as total_apps,
    count(dm) as apps_with_domain,
    count(am) as apps_with_api
RETURN
    total_apps,
    apps_with_domain,
    apps_with_api,
    CASE WHEN total_apps = apps_with_domain AND total_apps = apps_with_api
         THEN 'PASS' ELSE 'FAIL' END as health_status;
```

**Prioridad**: 🟡 MEDIUM
**Esfuerzo**: 2-3 hours

---

## Sprint 1 — DomainModelIR → Graph ✅

**Estado**: COMPLETADO
**Fecha**: 2025-11-29
**Nodos creados**: 6,288 (1,084 Entity + 5,204 Attribute)

### Logros

| Tarea | Estado | Detalles |
|-------|--------|----------|
| Diseño Entity/Attribute | ✅ | Schema correcto |
| RELATES_TO como edge | ✅ | Con properties (tipo, field_name) |
| UNWIND batching | ✅ | Eficiente para volumen |
| ID determinístico | ✅ | `{app_id}|entity|{name}` |
| Migración live | ✅ | 6,288 nodos |
| Verificación | ✅ | Queries de validación |

### Gaps Identificados

#### 1.1 Falta Temporal Metadata

**Problema**:
```cypher
-- ACTUAL (incompleto)
CREATE (e:Entity {
    entity_id: $id,
    name: $name,
    table_name: $table_name
})

-- REQUERIDO
CREATE (e:Entity {
    entity_id: $id,
    name: $name,
    table_name: $table_name,
    created_at: datetime(),      -- CRÍTICO
    updated_at: datetime(),      -- CRÍTICO
    schema_version: 1
})
```

**Impacto**:
- Sin `created_at/updated_at` → imposible rastrear evolución
- Debugging de migraciones muy difícil
- Lineage temporal incompleto

**Solución**: Migración 006 (ver [RISKS.md#r4](./RISKS.md#r4-temporal-metadata-inconsistente))

#### 1.2 Falta Validación de Cardinalidades

```yaml
Constraint faltante:

Entity:
  - MUST have ≥1 Attribute

DomainModelIR:
  - MUST have ≥1 Entity
```

**Query de validación**:
```cypher
-- Entities sin attributes (INVALID)
MATCH (e:Entity)
WHERE NOT (e)-[:HAS_ATTRIBUTE]->(:Attribute)
RETURN count(e) as invalid_entities;
-- Debe retornar 0

-- DomainModels sin entities (INVALID)
MATCH (d:DomainModelIR)
WHERE NOT (d)-[:HAS_ENTITY]->(:Entity)
RETURN count(d) as invalid_domain_models;
-- Debe retornar 0
```

**Tarea**: IA.6
**Esfuerzo**: 1 hour

---

## Sprint 2 — APIModelIR → Graph ✅

**Estado**: COMPLETADO
**Fecha**: 2025-11-29
**Nodos creados**: 4,690 (4,022 Endpoint + 668 APIParameter)

### Logros

| Tarea | Estado | Detalles |
|-------|--------|----------|
| Schema APIParameter | ✅ | Bien diseñado |
| Repositorio completo | ✅ | Testeado |
| Migración live | ✅ | 4,690 nodos |
| Integración neo4j_ir_repository | ✅ | Funcionando |

### Gaps Identificados

#### 2.1 APISchema Real Faltante

**Problema**:
```yaml
Estado:
  - Migración encontró 0 APISchemas (OK para data actual)
  - PERO modelo no prevé:
    * Versioning del schema
    * source field ("spec" | "inferred" | "validated")
    * Linking hacia Entity (schema → Entity mapping)
```

**Modelo requerido**:
```cypher
CREATE (s:APISchema {
    schema_id: string,
    name: string,              -- "ProductSchema"
    version: string,           -- "v1.0"
    source: string,            -- "spec" | "inferred" | "validated"
    created_at: datetime,
    updated_at: datetime
})

-- Relationships
(APISchema)-[:MAPS_TO]->(Entity)
(Endpoint)-[:USES_SCHEMA]->(APISchema)
```

**Tarea**: 2.5.2
**Esfuerzo**: 1 hour

#### 2.2 TARGETS_ENTITY Link Faltante (CRÍTICO)

**Problema**:
```yaml
Missing edge:
  (Endpoint)-[:TARGETS_ENTITY]->(Entity)

Ejemplo:
  POST /products → Entity(Product)
  GET /orders/{id} → Entity(Order)

Sin este edge:
  - ❌ No hay trazabilidad API ↔ Domain
  - ❌ QA no puede validar implementación
  - ❌ Lineage roto
  - ❌ BehaviorModel no puede conectar
```

**Solución**: Sprint 2.5 completo

Ver: [ACTION_PLAN.md#sprint-25](./ACTION_PLAN.md#fase-2-sprint-25)

**Prioridad**: 🔴 CRÍTICO
**Bloqueante para**: Sprint 3, 5, 6

---

## Resumen de Tareas Pendientes (Post Sprints 0-2)

| ID | Tarea | Sprint | Esfuerzo | Prioridad |
|----|-------|--------|----------|-----------|
| 0.6 | Schema Health Check | 0 | 2-3h | 🟡 MEDIUM |
| IA.5 | Temporal metadata Entity/Attribute | 1 | 2-3h | 🟡 HIGH |
| IA.6 | Validation queries cardinalidades | 1 | 1h | 🟡 MEDIUM |
| 2.5.1 | TARGETS_ENTITY inference | 2 | 4-6h | 🔴 CRITICAL |
| 2.5.2 | APISchema.source field | 2 | 1h | 🟡 HIGH |

---

## Métricas Actuales del Grafo

```
┌─────────────────────┬─────────┬──────────────────┐
│ Label               │ Count   │ Sprint           │
├─────────────────────┼─────────┼──────────────────┤
│ ApplicationIR       │   278   │ Sprint 0         │
│ DomainModelIR       │   280   │ Sprint 0-1       │
│ Entity              │ 1,084   │ Sprint 1         │
│ Attribute           │ 5,204   │ Sprint 1         │
│ APIModelIR          │   280   │ Sprint 0-2       │
│ Endpoint            │ 4,022   │ Sprint 2         │
│ APIParameter        │   668   │ Sprint 2         │
├─────────────────────┼─────────┼──────────────────┤
│ TOTAL IR nodes      │11,816   │                  │
└─────────────────────┴─────────┴──────────────────┘

Edges agregados:
  - HAS_ENTITY: 1,084
  - HAS_ATTRIBUTE: 5,204
  - RELATES_TO: 132
  - HAS_ENDPOINT: 280
  - HAS_PARAMETER: 4,690
```

---

*Ver también*: [SPRINT_3-5.md](./SPRINT_3-5.md) para próximos Sprints
