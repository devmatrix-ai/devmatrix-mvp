// Migration 011: ErrorKnowledge Schema for Active Learning
// Creates the ErrorKnowledge node type and relationships for tracking
// learned error patterns from code generation failures.
//
// Reference: DOCS/mvp/exit/learning/LEARNING_SYSTEM_REDESIGN.md Section 7

// ============================================================================
// CONSTRAINTS
// ============================================================================

// ErrorKnowledge unique constraint on error_signature
CREATE CONSTRAINT error_knowledge_signature IF NOT EXISTS
FOR (ek:ErrorKnowledge) REQUIRE ek.error_signature IS UNIQUE;

// ============================================================================
// INDEXES
// ============================================================================

// Index for querying by confidence (for high-confidence lookups)
CREATE INDEX error_knowledge_confidence IF NOT EXISTS
FOR (ek:ErrorKnowledge) ON (ek.confidence);

// Index for querying by error_type
CREATE INDEX error_knowledge_error_type IF NOT EXISTS
FOR (ek:ErrorKnowledge) ON (ek.error_type);

// Index for querying by endpoint_pattern
CREATE INDEX error_knowledge_endpoint_pattern IF NOT EXISTS
FOR (ek:ErrorKnowledge) ON (ek.endpoint_pattern);

// Index for querying by entity_type
CREATE INDEX error_knowledge_entity_type IF NOT EXISTS
FOR (ek:ErrorKnowledge) ON (ek.entity_type);

// Index for querying by pattern_category
CREATE INDEX error_knowledge_pattern_category IF NOT EXISTS
FOR (ek:ErrorKnowledge) ON (ek.pattern_category);

// Composite index for common query pattern
CREATE INDEX error_knowledge_lookup IF NOT EXISTS
FOR (ek:ErrorKnowledge) ON (ek.confidence, ek.pattern_category, ek.entity_type);

// ============================================================================
// RELATIONSHIP INDEXES
// ============================================================================

// Index on CAUSED_ERROR relationship timestamp for temporal queries
// Note: Neo4j 5.x supports relationship property indexes

// ============================================================================
// SAMPLE DATA (for testing - comment out in production)
// ============================================================================

// Uncomment to create sample ErrorKnowledge node:
// CREATE (ek:ErrorKnowledge {
//     knowledge_id: 'sample-001',
//     error_signature: 'sample_signature_001',
//     error_type: '500',
//     pattern_category: 'service',
//     entity_type: 'product',
//     endpoint_pattern: 'POST /{entity}',
//     description: 'Sample error for testing',
//     avoidance_hint: 'Always call db.commit() after create',
//     occurrence_count: 1,
//     confidence: 0.5,
//     created_at: datetime(),
//     last_seen: datetime()
// });
