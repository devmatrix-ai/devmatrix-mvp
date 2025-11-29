// =============================================================================
// Sprint 1 Task 1.1: Entity/Attribute Schema Migration
// =============================================================================
// Purpose: Create constraints and indexes for Entity and Attribute nodes
//          to support domain model parsing and validation
//
// Created: 2025-11-29
// Sprint: 1
// Task: 1.1 (Entity & Attribute Parsing)
// =============================================================================

// -----------------------------------------------------------------------------
// CONSTRAINTS
// -----------------------------------------------------------------------------

// Entity Constraints
// Ensures that entity names are unique within a domain model context
CREATE CONSTRAINT entity_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE (e.domain_model_id, e.name) IS UNIQUE;

// Attribute Constraints
// Ensures that attribute names are unique within an entity context
CREATE CONSTRAINT attribute_unique IF NOT EXISTS
FOR (a:Attribute) REQUIRE (a.entity_id, a.name) IS UNIQUE;

// -----------------------------------------------------------------------------
// INDEXES
// -----------------------------------------------------------------------------

// Entity Indexes
// Index for quick entity lookup by name
CREATE INDEX entity_name IF NOT EXISTS
FOR (e:Entity) ON (e.name);

// Index for identifying aggregate roots in DDD patterns
CREATE INDEX entity_aggregate_root IF NOT EXISTS
FOR (e:Entity) ON (e.is_aggregate_root);

// Attribute Indexes
// Index for quick identification of primary key attributes
CREATE INDEX attribute_pk IF NOT EXISTS
FOR (a:Attribute) ON (a.is_primary_key);

// Index for filtering attributes by data type
CREATE INDEX attribute_type IF NOT EXISTS
FOR (a:Attribute) ON (a.data_type);

// -----------------------------------------------------------------------------
// VERIFICATION
// -----------------------------------------------------------------------------

// Verify all constraints were created successfully
CALL db.constraints()
YIELD name, type, entityType, labelsOrTypes, properties
WHERE name STARTS WITH 'entity' OR name STARTS WITH 'attribute'
RETURN name, type, entityType, labelsOrTypes, properties
ORDER BY name;

// Verify all indexes were created successfully
CALL db.indexes()
YIELD name, type, entityType, labelsOrTypes, properties, state
WHERE name STARTS WITH 'entity' OR name STARTS WITH 'attribute'
RETURN name, type, entityType, labelsOrTypes, properties, state
ORDER BY name;

// =============================================================================
// MIGRATION COMPLETE
// =============================================================================
// Expected Results:
// - 2 unique constraints created (entity_unique, attribute_unique)
// - 4 indexes created (entity_name, entity_aggregate_root, attribute_pk, attribute_type)
//
// To rollback: Execute 002_domain_model_schema_rollback.cypher
// =============================================================================
