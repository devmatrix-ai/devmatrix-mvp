// 006_add_temporal_metadata_rollback.cypher
// Rollback para migración 006
// ADVERTENCIA: Esto elimina temporal metadata de todos los nodos afectados
// Solo usar si la migración causó problemas

// ============================================================================
// ROLLBACK: Remover temporal metadata de Entity
// ============================================================================

MATCH (n:Entity)
WHERE n.schema_version IS NOT NULL AND n.schema_version = 1
REMOVE n.created_at, n.updated_at, n.schema_version;

// ============================================================================
// ROLLBACK: Remover temporal metadata de Attribute
// ============================================================================

MATCH (n:Attribute)
WHERE n.schema_version IS NOT NULL AND n.schema_version = 1
REMOVE n.created_at, n.updated_at, n.schema_version;

// ============================================================================
// ROLLBACK: Remover temporal metadata de Endpoint
// ============================================================================

MATCH (n:Endpoint)
WHERE n.schema_version IS NOT NULL AND n.schema_version = 1
REMOVE n.created_at, n.updated_at, n.schema_version;

// ============================================================================
// ROLLBACK: Remover temporal metadata de APIParameter
// ============================================================================

MATCH (n:APIParameter)
WHERE n.schema_version IS NOT NULL AND n.schema_version = 1
REMOVE n.created_at, n.updated_at, n.schema_version;

// ============================================================================
// ROLLBACK: Eliminar MigrationRun
// ============================================================================

MATCH (m:MigrationRun {migration_id: "006_add_temporal_metadata"})
DETACH DELETE m;

// ============================================================================
// ROLLBACK: Actualizar GraphSchemaVersion
// ============================================================================

MATCH (v:GraphSchemaVersion {singleton: true})
SET v.current_version = 2,
    v.last_migration = "005_sprint2_api_model_expansion",
    v.updated_at = datetime();
