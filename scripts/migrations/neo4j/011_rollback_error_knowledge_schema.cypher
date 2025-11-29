// Rollback Migration 011: ErrorKnowledge Schema
// WARNING: This will delete all ErrorKnowledge data!

// Drop indexes first
DROP INDEX error_knowledge_confidence IF EXISTS;
DROP INDEX error_knowledge_error_type IF EXISTS;
DROP INDEX error_knowledge_endpoint_pattern IF EXISTS;
DROP INDEX error_knowledge_entity_type IF EXISTS;
DROP INDEX error_knowledge_pattern_category IF EXISTS;
DROP INDEX error_knowledge_lookup IF EXISTS;

// Drop constraint
DROP CONSTRAINT error_knowledge_signature IF EXISTS;

// Delete all ErrorKnowledge nodes and relationships
MATCH (ek:ErrorKnowledge)
DETACH DELETE ek;

// Remove migration record
MATCH (m:Migration {name: '011_error_knowledge_schema'})
DELETE m;
