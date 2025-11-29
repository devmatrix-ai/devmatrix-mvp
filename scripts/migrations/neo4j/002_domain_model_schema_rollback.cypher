// =============================================================================
// Sprint 1 Task 1.1: Entity/Attribute Schema Rollback
// =============================================================================
// Purpose: Remove all constraints and indexes created by 002_domain_model_schema.cypher
//
// Created: 2025-11-29
// Sprint: 1
// Task: 1.1 (Entity & Attribute Parsing)
// =============================================================================

// -----------------------------------------------------------------------------
// DROP INDEXES
// -----------------------------------------------------------------------------

// Entity Indexes
DROP INDEX entity_name IF EXISTS;
DROP INDEX entity_aggregate_root IF EXISTS;

// Attribute Indexes
DROP INDEX attribute_pk IF EXISTS;
DROP INDEX attribute_type IF EXISTS;

// -----------------------------------------------------------------------------
// DROP CONSTRAINTS
// -----------------------------------------------------------------------------

// Entity Constraints
DROP CONSTRAINT entity_unique IF EXISTS;

// Attribute Constraints
DROP CONSTRAINT attribute_unique IF EXISTS;

// -----------------------------------------------------------------------------
// VERIFICATION
// -----------------------------------------------------------------------------

// Verify all constraints were removed
CALL db.constraints()
YIELD name, type, entityType, labelsOrTypes, properties
WHERE name STARTS WITH 'entity' OR name STARTS WITH 'attribute'
RETURN name, type, entityType, labelsOrTypes, properties
ORDER BY name;

// Verify all indexes were removed
CALL db.indexes()
YIELD name, type, entityType, labelsOrTypes, properties, state
WHERE name STARTS WITH 'entity' OR name STARTS WITH 'attribute'
RETURN name, type, entityType, labelsOrTypes, properties, state
ORDER BY name;

// -----------------------------------------------------------------------------
// CLEANUP DATA (OPTIONAL - COMMENTED OUT FOR SAFETY)
// -----------------------------------------------------------------------------

// WARNING: Uncommenting these lines will DELETE all Entity and Attribute nodes
// Only execute if you want to completely remove all domain model data

// // Delete all HAS_ATTRIBUTE relationships
// MATCH ()-[r:HAS_ATTRIBUTE]->()
// DELETE r;
//
// // Delete all Attribute nodes
// MATCH (a:Attribute)
// DELETE a;
//
// // Delete all Entity nodes
// MATCH (e:Entity)
// DELETE e;

// =============================================================================
// ROLLBACK COMPLETE
// =============================================================================
// Expected Results:
// - All entity/attribute constraints removed
// - All entity/attribute indexes removed
// - Data preserved (unless cleanup section uncommented)
//
// To re-apply: Execute 002_domain_model_schema.cypher
// =============================================================================
