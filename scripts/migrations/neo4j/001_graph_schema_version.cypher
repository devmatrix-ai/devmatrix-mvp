// 001_graph_schema_version.cypher
// Sprint: Inmediato (Pre-Sprint 3)
// Objetivo: Crear singleton GraphSchemaVersion para tracking de schema evolution
// Ejecutar: cypher-shell -f 001_graph_schema_version.cypher
// Fecha: 2025-11-29

// ============================================================================
// CREAR GRAPHSCHEMAVERSION SINGLETON
// ============================================================================

// 1. Crear nodo singleton con current_version = 2 (post-Sprint 0-2)
MERGE (v:GraphSchemaVersion {singleton: true})
ON CREATE SET
    v.current_version = 2,
    v.last_migration = "005_sprint2_api_model_expansion",
    v.migration_date = datetime(),
    v.sprints_completed = ["Sprint 0", "Sprint 1", "Sprint 2"],
    v.created_at = datetime(),
    v.updated_at = datetime(),
    v.description = "Schema version tracking singleton for Neo4j graph evolution"
ON MATCH SET
    v.updated_at = datetime(),
    v.current_version = 2,
    v.last_migration = "005_sprint2_api_model_expansion";

// 2. Asegurar que solo hay UN singleton
MATCH (v:GraphSchemaVersion {singleton: true})
WITH v
MATCH (other:GraphSchemaVersion)
WHERE other.singleton = true AND id(other) <> id(v)
DELETE other;

// 3. Retornar estado final
MATCH (v:GraphSchemaVersion {singleton: true})
RETURN
    v.current_version as current_version,
    v.last_migration as last_migration,
    v.sprints_completed as sprints_completed,
    v.created_at as created_at,
    v.updated_at as updated_at;

// ============================================================================
// VERIFICACIÓN POST-CREACIÓN
// ============================================================================

// Query de verificación (comentada para ejecución manual)
// MATCH (v:GraphSchemaVersion {singleton: true})
// RETURN count(v) as singleton_count, v.current_version as version;
// Expected: singleton_count = 1, version = 2

// ============================================================================
// SCHEMA VERSION CONVENTION
// ============================================================================
// v0   → Sprint 0: Schema alignment, orphan cleanup, label renaming
// v1   → Sprint 1: DomainModelIR → Entity + Attribute expansion
// v2   → Sprint 2: APIModelIR → Endpoint + APIParameter expansion
// v2.5 → Sprint 2.5: TARGETS_ENTITY + source field (pendiente)
// v3   → Sprint 3: BehaviorModelIR + ValidationModelIR expansion (pendiente)
// v4   → Sprint 4: InfrastructureModelIR expansion (pendiente)
// v5   → Sprint 5: TestsModelIR MVP expansion (pendiente)
// ============================================================================
