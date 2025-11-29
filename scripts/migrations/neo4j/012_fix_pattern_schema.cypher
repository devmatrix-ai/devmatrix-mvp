// Migration 012: FixPattern Schema for Code Repair Learning
// Gap 4 Implementation: Stores successful fixes for reuse
//
// Reference: DOCS/mvp/exit/learning/LEARNING_GAPS_IMPLEMENTATION_PLAN.md Gap 4

// ============================================================================
// CONSTRAINTS
// ============================================================================

// FixPattern unique constraint on error_signature
CREATE CONSTRAINT fix_pattern_signature IF NOT EXISTS
FOR (fp:FixPattern) REQUIRE fp.error_signature IS UNIQUE;

// ============================================================================
// INDEXES
// ============================================================================

// Index for querying by confidence (for high-confidence lookups)
CREATE INDEX fix_pattern_confidence IF NOT EXISTS
FOR (fp:FixPattern) ON (fp.confidence);

// Index for querying by error_type
CREATE INDEX fix_pattern_error_type IF NOT EXISTS
FOR (fp:FixPattern) ON (fp.error_type);

// Index for querying by fix_strategy
CREATE INDEX fix_pattern_fix_strategy IF NOT EXISTS
FOR (fp:FixPattern) ON (fp.fix_strategy);

// Composite index for common query pattern
CREATE INDEX fix_pattern_lookup IF NOT EXISTS
FOR (fp:FixPattern) ON (fp.confidence, fp.error_type);

// Index on last_used for temporal queries
CREATE INDEX fix_pattern_last_used IF NOT EXISTS
FOR (fp:FixPattern) ON (fp.last_used);

// Index on success_count for statistics
CREATE INDEX fix_pattern_success_count IF NOT EXISTS
FOR (fp:FixPattern) ON (fp.success_count);
