// =============================================================================
// Sprint 2 Task 2.1: API Model Schema Migration
// =============================================================================
// Purpose: Create constraints and indexes for Endpoint, APISchema, and APIParameter nodes
//          to support API model parsing and validation
//
// Created: 2025-11-29
// Sprint: 2
// Task: 2.1 (API Model Schema)
// =============================================================================

// -----------------------------------------------------------------------------
// CONSTRAINTS
// -----------------------------------------------------------------------------

// Endpoint Constraints
// Ensures that endpoints are unique within an API model by path and method
CREATE CONSTRAINT endpoint_unique IF NOT EXISTS
FOR (e:Endpoint) REQUIRE (e.api_model_id, e.path, e.method) IS UNIQUE;

// APIParameter Constraints
// Ensures that parameters are unique within an endpoint context
CREATE CONSTRAINT api_parameter_unique IF NOT EXISTS
FOR (p:APIParameter) REQUIRE (p.endpoint_id, p.name) IS UNIQUE;

// APISchema Constraints
// Ensures that schemas are unique within an API model context
CREATE CONSTRAINT api_schema_unique IF NOT EXISTS
FOR (s:APISchema) REQUIRE (s.api_model_id, s.name) IS UNIQUE;

// APISchemaField Constraints
// Ensures that schema fields are unique within a schema context
CREATE CONSTRAINT api_schema_field_unique IF NOT EXISTS
FOR (f:APISchemaField) REQUIRE (f.schema_id, f.name) IS UNIQUE;

// -----------------------------------------------------------------------------
// INDEXES
// -----------------------------------------------------------------------------

// Endpoint Indexes
// Index for quick endpoint lookup by path
CREATE INDEX endpoint_path IF NOT EXISTS
FOR (e:Endpoint) ON (e.path);

// Index for endpoint lookup by HTTP method
CREATE INDEX endpoint_method IF NOT EXISTS
FOR (e:Endpoint) ON (e.method);

// Index for endpoint lookup by operation_id
CREATE INDEX endpoint_operation_id IF NOT EXISTS
FOR (e:Endpoint) ON (e.operation_id);

// Index for filtering inferred endpoints
CREATE INDEX endpoint_inferred IF NOT EXISTS
FOR (e:Endpoint) ON (e.inferred);

// APIParameter Indexes
// Index for quick parameter lookup by location (query, path, header, cookie)
CREATE INDEX api_parameter_location IF NOT EXISTS
FOR (p:APIParameter) ON (p.location);

// Index for filtering required parameters
CREATE INDEX api_parameter_required IF NOT EXISTS
FOR (p:APIParameter) ON (p.required);

// APISchema Indexes
// Index for quick schema lookup by name
CREATE INDEX api_schema_name IF NOT EXISTS
FOR (s:APISchema) ON (s.name);

// APISchemaField Indexes
// Index for filtering required fields
CREATE INDEX api_schema_field_required IF NOT EXISTS
FOR (f:APISchemaField) ON (f.required);

// -----------------------------------------------------------------------------
// VERIFICATION
// -----------------------------------------------------------------------------

// Verify all constraints were created successfully
CALL db.constraints()
YIELD name, type, entityType, labelsOrTypes, properties
WHERE name STARTS WITH 'endpoint'
   OR name STARTS WITH 'api_parameter'
   OR name STARTS WITH 'api_schema'
RETURN name, type, entityType, labelsOrTypes, properties
ORDER BY name;

// Verify all indexes were created successfully
CALL db.indexes()
YIELD name, type, entityType, labelsOrTypes, properties, state
WHERE name STARTS WITH 'endpoint'
   OR name STARTS WITH 'api_parameter'
   OR name STARTS WITH 'api_schema'
RETURN name, type, entityType, labelsOrTypes, properties, state
ORDER BY name;

// =============================================================================
// MIGRATION COMPLETE
// =============================================================================
// Expected Results:
// - 4 unique constraints created (endpoint_unique, api_parameter_unique,
//   api_schema_unique, api_schema_field_unique)
// - 9 indexes created (4 endpoint, 2 parameter, 1 schema, 2 schema_field indexes)
//
// To rollback: Execute 004_api_model_schema_rollback.cypher
// =============================================================================
