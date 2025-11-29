# Migration 001: GraphSchemaVersion Singleton

**Fecha:** 2025-11-29
**Sprint:** Tareas Inmediatas (Pre-Sprint 3)
**Objetivo:** Crear singleton para tracking de schema evolution

---

## Descripción

Crea un nodo `GraphSchemaVersion` singleton para mantener tracking del estado actual del schema de Neo4j. Este nodo es fundamental para:

- **Coherencia:** Sincronizar con `MigrationRun` nodes (Task IA.2)
- **Auditoría:** Saber qué versión de schema está activa
- **Safety:** Validar pre-condiciones antes de aplicar migrations
- **Historial:** Registro de sprints completados

---

## Estado Actual del Schema

**Post-Sprint 0-2:**
- ✅ Sprint 0: ApplicationIR schema cleanup (278 apps)
- ✅ Sprint 1: DomainModelIR → Entity (1,084) + Attribute (5,204)
- ✅ Sprint 2: APIModelIR → Endpoint (4,022) + APIParameter (668)
- **Total:** ~11,000 nodos + ~11,400 edges creados

**Schema Version:** `v2` (post-Sprint 2)

---

## Ejecución

### Opción 1: Cypher-Shell (Manual)

```bash
# Conectarse a Neo4j
cypher-shell -u neo4j -p devmatrix123

# Ejecutar migration
:source scripts/migrations/neo4j/001_graph_schema_version.cypher

# Verificar resultado
MATCH (v:GraphSchemaVersion {singleton: true})
RETURN v;
```

### Opción 2: Python Script (Recomendado)

```bash
# Ejecutar con script Python (crear en Task IA.2)
PYTHONPATH=. python scripts/migrations/neo4j/001_execute_graph_schema_version.py
```

---

## Verificación

### Query de Verificación

```cypher
// 1. Verificar que existe exactamente 1 singleton
MATCH (v:GraphSchemaVersion {singleton: true})
RETURN count(v) as singleton_count;
// Expected: 1

// 2. Verificar contenido
MATCH (v:GraphSchemaVersion {singleton: true})
RETURN
    v.current_version as version,
    v.last_migration as last_migration,
    v.sprints_completed as sprints,
    v.created_at as created,
    v.updated_at as updated;

// Expected output:
// version: 2
// last_migration: "005_sprint2_api_model_expansion"
// sprints: ["Sprint 0", "Sprint 1", "Sprint 2"]
// created: [timestamp]
// updated: [timestamp]
```

---

## Rollback

Si necesitas revertir:

```bash
cypher-shell -u neo4j -p devmatrix123 < scripts/migrations/neo4j/001_rollback_graph_schema_version.cypher
```

**⚠️ WARNING:** Solo hacer rollback si el singleton está corrupto. Normalmente NO es necesario.

---

## Schema Version Convention

| Versión | Sprint | Descripción | Fecha |
|---------|--------|-------------|-------|
| **v0** | Sprint 0 | Labels renamed to IR suffix, orphans removed | 2025-11-29 |
| **v1** | Sprint 1 | DomainModelIR → Entity, Attribute | 2025-11-29 |
| **v2** | Sprint 2 | APIModelIR → Endpoint, APIParameter | 2025-11-29 |
| v2.5 | Sprint 2.5 | TARGETS_ENTITY, campo source | TBD |
| v3 | Sprint 3 | BehaviorModelIR + ValidationModelIR | TBD |
| v4 | Sprint 4 | InfrastructureModelIR | TBD |
| v5 | Sprint 5 | TestsModelIR MVP | TBD |

---

## Próximos Pasos

Después de ejecutar esta migration:

1. ✅ **IA.1 Completado:** GraphSchemaVersion creado
2. ⏳ **IA.2 Siguiente:** Crear MigrationRun nodes retroactivos (002_register_past_migrations.py)
3. ⏳ **IA.3 Siguiente:** GraphIRRepository base class
4. ⏳ **IA.4 Siguiente:** Tests roundtrip + DUAL_WRITE policy

---

## Troubleshooting

### Problema: "Node already exists"

```cypher
// Si el nodo ya existe, verificar su estado
MATCH (v:GraphSchemaVersion)
RETURN v;

// Si es correcto, no hacer nada
// Si está corrupto, ejecutar rollback y volver a crear
```

### Problema: "Multiple singletons detected"

```cypher
// Eliminar duplicados, mantener el más reciente
MATCH (v:GraphSchemaVersion)
WITH v
ORDER BY v.updated_at DESC
SKIP 1
DELETE v;
```

---

**Estado:** ✅ Script listo para ejecución
**Bloqueadores:** Ninguno
**Dependencies:** Neo4j 5.x con APOC plugin
