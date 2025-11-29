// 006_add_temporal_metadata.cypher
// Sprint: Inmediato (Pre-Sprint 3) - Task IA.5
// Objetivo: Agregar created_at, updated_at, schema_version a nodos sin temporal metadata
// Ejecutar: PYTHONPATH=. python scripts/migrations/neo4j/006_execute_add_temporal_metadata.py
// Fecha: 2025-11-29

// ============================================================================
// PRE-CHECK: Contar nodos sin temporal metadata
// ============================================================================

// Ejecutar primero para verificar estado:
// MATCH (n)
// WHERE (n:Entity OR n:Attribute OR n:Endpoint OR n:APIParameter)
//   AND n.created_at IS NULL
// RETURN labels(n)[0] as label, count(n) as missing_temporal
// ORDER BY label;

// ============================================================================
// MIGRACIÓN: Entity nodes
// ============================================================================

MATCH (n:Entity)
WHERE n.created_at IS NULL
SET n.created_at = datetime(),
    n.updated_at = datetime(),
    n.schema_version = 1
WITH count(n) as entity_count

// ============================================================================
// MIGRACIÓN: Attribute nodes
// ============================================================================

MATCH (n:Attribute)
WHERE n.created_at IS NULL
SET n.created_at = datetime(),
    n.updated_at = datetime(),
    n.schema_version = 1
WITH count(n) as attribute_count

// ============================================================================
// MIGRACIÓN: Endpoint nodes
// ============================================================================

MATCH (n:Endpoint)
WHERE n.created_at IS NULL
SET n.created_at = datetime(),
    n.updated_at = datetime(),
    n.schema_version = 1
WITH count(n) as endpoint_count

// ============================================================================
// MIGRACIÓN: APIParameter nodes
// ============================================================================

MATCH (n:APIParameter)
WHERE n.created_at IS NULL
SET n.created_at = datetime(),
    n.updated_at = datetime(),
    n.schema_version = 1;

// ============================================================================
// VERIFICACIÓN POST-MIGRACIÓN
// ============================================================================

// Verificar que todos los nodos tienen temporal metadata:
// MATCH (n)
// WHERE (n:Entity OR n:Attribute OR n:Endpoint OR n:APIParameter)
// RETURN
//     labels(n)[0] as label,
//     count(n) as total,
//     sum(CASE WHEN n.created_at IS NOT NULL THEN 1 ELSE 0 END) as with_temporal
// ORDER BY label;
// Expected: total = with_temporal para cada label
