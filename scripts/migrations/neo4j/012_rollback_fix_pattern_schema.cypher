// Rollback Migration 012: FixPattern Schema
// WARNING: This will delete all FixPattern data!

// Drop indexes first
DROP INDEX fix_pattern_confidence IF EXISTS;
DROP INDEX fix_pattern_error_type IF EXISTS;
DROP INDEX fix_pattern_fix_strategy IF EXISTS;
DROP INDEX fix_pattern_lookup IF EXISTS;
DROP INDEX fix_pattern_last_used IF EXISTS;
DROP INDEX fix_pattern_success_count IF EXISTS;

// Drop constraint
DROP CONSTRAINT fix_pattern_signature IF EXISTS;

// Delete all FixPattern nodes
MATCH (fp:FixPattern)
DETACH DELETE fp;

// Remove migration record
MATCH (m:Migration {name: '012_fix_pattern_schema'})
DELETE m;
