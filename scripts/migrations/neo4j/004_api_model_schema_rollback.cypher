// =============================================================================
// Sprint 2 Task 2.1: API Model Schema Rollback
// =============================================================================
// Purpose: Remove constraints and indexes created for API model schema
//
// WARNING: This will drop all API model constraints and indexes
//          Run this ONLY if you need to completely rollback Sprint 2 schema
//
// Created: 2025-11-29
// Sprint: 2
// Task: 2.1 (API Model Schema Rollback)
// =============================================================================

// -----------------------------------------------------------------------------
// DROP INDEXES
// -----------------------------------------------------------------------------

DROP INDEX endpoint_path IF EXISTS;
DROP INDEX endpoint_method IF EXISTS;
DROP INDEX endpoint_operation_id IF EXISTS;
DROP INDEX endpoint_inferred IF EXISTS;
DROP INDEX api_parameter_location IF EXISTS;
DROP INDEX api_parameter_required IF EXISTS;
DROP INDEX api_schema_name IF EXISTS;
DROP INDEX api_schema_field_required IF EXISTS;

// -----------------------------------------------------------------------------
// DROP CONSTRAINTS
// -----------------------------------------------------------------------------

DROP CONSTRAINT endpoint_unique IF EXISTS;
DROP CONSTRAINT api_parameter_unique IF EXISTS;
DROP CONSTRAINT api_schema_unique IF EXISTS;
DROP CONSTRAINT api_schema_field_unique IF EXISTS;

// -----------------------------------------------------------------------------
// VERIFICATION
// -----------------------------------------------------------------------------

// Verify all API model constraints are removed
CALL db.constraints()
YIELD name
WHERE name STARTS WITH 'endpoint'
   OR name STARTS WITH 'api_parameter'
   OR name STARTS WITH 'api_schema'
RETURN count(*) as remaining_constraints;

// Verify all API model indexes are removed
CALL db.indexes()
YIELD name
WHERE name STARTS WITH 'endpoint'
   OR name STARTS WITH 'api_parameter'
   OR name STARTS WITH 'api_schema'
RETURN count(*) as remaining_indexes;

// =============================================================================
// ROLLBACK COMPLETE
// =============================================================================
// Expected Results:
// - remaining_constraints: 0
// - remaining_indexes: 0
//
// To reapply schema: Execute 004_api_model_schema.cypher
// =============================================================================
