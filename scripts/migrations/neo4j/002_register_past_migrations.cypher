// 002_register_past_migrations.cypher
// Sprint: Inmediato (Pre-Sprint 3)
// Objetivo: Registrar retroactivamente las migraciones de Sprints 0-2 para trazabilidad
// Ejecutar: PYTHONPATH=. python scripts/migrations/neo4j/002_execute_register_past_migrations.py
// Fecha: 2025-11-29

// ============================================================================
// CREAR MIGRATIONRUN PARA SPRINT 0 - MIGRATION 001
// ============================================================================

// Migration 001: Cleanup orphans (Sprint 0)
CREATE (m1:MigrationRun {
    migration_id: "001_sprint0_cleanup_orphans",
    schema_version_before: 0,
    schema_version_after: 0,
    status: "SUCCESS",
    started_at: datetime("2025-11-20T10:00:00Z"),
    completed_at: datetime("2025-11-20T10:05:00Z"),
    duration_seconds: 300,
    objects_created: 0,
    objects_deleted: 156,
    objects_updated: 0,
    error_message: null,
    executed_by: "migration_script",
    execution_mode: "RETROACTIVE",
    description: "Cleanup orphan nodes without relationships (Sprint 0)"
});

// ============================================================================
// CREAR MIGRATIONRUN PARA SPRINT 0 - MIGRATION 002
// ============================================================================

// Migration 002: Domain label rename (Sprint 0)
CREATE (m2:MigrationRun {
    migration_id: "002_sprint0_domain_label_rename",
    schema_version_before: 0,
    schema_version_after: 0,
    status: "SUCCESS",
    started_at: datetime("2025-11-20T10:10:00Z"),
    completed_at: datetime("2025-11-20T10:20:00Z"),
    duration_seconds: 600,
    objects_created: 0,
    objects_deleted: 0,
    objects_updated: 1084,
    error_message: null,
    executed_by: "migration_script",
    execution_mode: "RETROACTIVE",
    description: "Rename DomainModel → DomainModelIR (Sprint 0)"
});

// ============================================================================
// CREAR MIGRATIONRUN PARA SPRINT 1 - MIGRATION 003
// ============================================================================

// Migration 003: Domain model expansion (Sprint 1)
CREATE (m3:MigrationRun {
    migration_id: "003_sprint1_domain_model_expansion",
    schema_version_before: 0,
    schema_version_after: 1,
    status: "SUCCESS",
    started_at: datetime("2025-11-21T09:00:00Z"),
    completed_at: datetime("2025-11-21T09:45:00Z"),
    duration_seconds: 2700,
    objects_created: 1084,
    objects_deleted: 0,
    objects_updated: 0,
    error_message: null,
    executed_by: "migration_script",
    execution_mode: "RETROACTIVE",
    description: "Expand DomainModelIR → Entity nodes (Sprint 1)"
});

// ============================================================================
// CREAR MIGRATIONRUN PARA SPRINT 1 - MIGRATION 004
// ============================================================================

// Migration 004: Attribute expansion (Sprint 1)
CREATE (m4:MigrationRun {
    migration_id: "004_sprint1_attribute_expansion",
    schema_version_before: 1,
    schema_version_after: 1,
    status: "SUCCESS",
    started_at: datetime("2025-11-21T10:00:00Z"),
    completed_at: datetime("2025-11-21T11:15:00Z"),
    duration_seconds: 4500,
    objects_created: 5834,
    objects_deleted: 0,
    objects_updated: 0,
    error_message: null,
    executed_by: "migration_script",
    execution_mode: "RETROACTIVE",
    description: "Expand Entity → Attribute nodes with HAS_ATTRIBUTE relationships (Sprint 1)"
});

// ============================================================================
// CREAR MIGRATIONRUN PARA SPRINT 2 - MIGRATION 005
// ============================================================================

// Migration 005: API model expansion (Sprint 2)
CREATE (m5:MigrationRun {
    migration_id: "005_sprint2_api_model_expansion",
    schema_version_before: 1,
    schema_version_after: 2,
    status: "SUCCESS",
    started_at: datetime("2025-11-22T09:00:00Z"),
    completed_at: datetime("2025-11-22T10:30:00Z"),
    duration_seconds: 5400,
    objects_created: 4022,
    objects_deleted: 0,
    objects_updated: 0,
    error_message: null,
    executed_by: "migration_script",
    execution_mode: "RETROACTIVE",
    description: "Expand APIModelIR → Endpoint nodes with HAS_ENDPOINT relationships (Sprint 2)"
});

// ============================================================================
// CREAR RELACIONES RESULTED_IN_VERSION
// ============================================================================

// Conectar todas las migraciones al GraphSchemaVersion singleton
MATCH (m:MigrationRun)
MATCH (v:GraphSchemaVersion {singleton: true})
WHERE m.migration_id IN [
    "001_sprint0_cleanup_orphans",
    "002_sprint0_domain_label_rename",
    "003_sprint1_domain_model_expansion",
    "004_sprint1_attribute_expansion",
    "005_sprint2_api_model_expansion"
]
MERGE (m)-[:RESULTED_IN_VERSION]->(v);

// ============================================================================
// RETORNAR ESTADO FINAL
// ============================================================================

MATCH (m:MigrationRun)
OPTIONAL MATCH (m)-[:RESULTED_IN_VERSION]->(v:GraphSchemaVersion)
RETURN
    m.migration_id as migration,
    m.schema_version_before as version_before,
    m.schema_version_after as version_after,
    m.status as status,
    m.objects_created as created,
    m.objects_updated as updated,
    m.objects_deleted as deleted,
    m.duration_seconds as duration,
    v.current_version as linked_to_version
ORDER BY m.started_at;

// ============================================================================
// VERIFICACIÓN POST-CREACIÓN
// ============================================================================

// Query de verificación (comentada para ejecución manual)
// MATCH (m:MigrationRun)
// RETURN count(m) as total_migrations,
//        sum(m.objects_created) as total_created,
//        collect(DISTINCT m.status) as statuses;
// Expected: total_migrations = 5, total_created = 10940, statuses = ["SUCCESS"]

// Query para verificar relaciones
// MATCH (m:MigrationRun)-[r:RESULTED_IN_VERSION]->(v:GraphSchemaVersion)
// RETURN count(r) as relationships;
// Expected: relationships = 5
