// 001_rollback_graph_schema_version.cypher
// Rollback: Eliminar GraphSchemaVersion singleton
// Ejecutar solo si necesitas revertir la creación del singleton
// Fecha: 2025-11-29

// ============================================================================
// ROLLBACK: ELIMINAR GRAPHSCHEMAVERSION
// ============================================================================

MATCH (v:GraphSchemaVersion {singleton: true})
DELETE v
RETURN "GraphSchemaVersion singleton deleted" as status;

// ============================================================================
// VERIFICACIÓN POST-ROLLBACK
// ============================================================================

// Verificar que no queda ningún GraphSchemaVersion
// MATCH (v:GraphSchemaVersion)
// RETURN count(v) as remaining_singletons;
// Expected: 0
