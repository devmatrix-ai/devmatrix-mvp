# Domain Model Expansion Migration (003)

**Sprint 1 Task 1.3**: Migrate DomainModelIR from JSON storage to graph nodes

## Overview

This migration transforms DomainModelIR entities from JSON string properties into proper Neo4j graph structure:

- **Entity nodes** with `HAS_ENTITY` relationships to DomainModelIR
- **Attribute nodes** with `HAS_ATTRIBUTE` relationships to Entity
- **RELATES_TO relationships** between entities

## Migration Scripts

### 1. Main Migration: `003_domain_model_expansion.py`

Expands ~280 DomainModelIR nodes into graph structure.

**Usage:**

```bash
# Dry run (recommended first)
DRY_RUN=true python scripts/migrations/neo4j/003_domain_model_expansion.py

# Live migration
python scripts/migrations/neo4j/003_domain_model_expansion.py
```

**What it does:**
- Parses entities JSON from DomainModelIR nodes
- Creates Entity nodes with properties: name, description, is_aggregate_root
- Creates Attribute nodes with properties: name, data_type, is_primary_key, etc.
- Creates RELATES_TO edges for entity relationships
- Keeps original JSON for safety (allows rollback)
- Sets `migrated_to_graph=true` flag on DomainModelIR

**Progress:**
- Reports every 50 records
- Shows entity/attribute/relationship counts
- Provides verification at end

### 2. Rollback: `003_domain_model_expansion_rollback.py`

Reverses the migration if issues are found.

**Usage:**

```bash
# Dry run
DRY_RUN=true python scripts/migrations/neo4j/003_domain_model_expansion_rollback.py

# Live rollback
python scripts/migrations/neo4j/003_domain_model_expansion_rollback.py
```

**What it does:**
- Deletes all Entity nodes created by migration
- Deletes all Attribute nodes created by migration
- Removes HAS_ENTITY, HAS_ATTRIBUTE, RELATES_TO relationships
- Clears `migrated_to_graph` flag from DomainModelIR
- Original entities JSON is preserved

### 3. Cleanup (Optional): `003_cleanup_json.py`

Removes entities JSON after verifying migration success.

**⚠️ WARNING: This is destructive! Only run after thorough verification.**

**Usage:**

```bash
# Dry run
DRY_RUN=true python scripts/migrations/neo4j/003_cleanup_json.py

# Live cleanup (requires confirmation)
python scripts/migrations/neo4j/003_cleanup_json.py

# Skip confirmation prompt
SKIP_CONFIRMATION=true python scripts/migrations/neo4j/003_cleanup_json.py
```

**What it does:**
- Verifies graph structure exists for each app
- Removes entities JSON property from DomainModelIR
- Sets `json_cleaned_timestamp` flag
- Cannot be undone (no rollback after this)

## Migration Workflow

### Step 1: Dry Run

```bash
DRY_RUN=true python scripts/migrations/neo4j/003_domain_model_expansion.py
```

Review output to ensure:
- Entity/attribute counts match expectations
- No parsing errors
- All ~280 DomainModelIR nodes are found

### Step 2: Live Migration

```bash
python scripts/migrations/neo4j/003_domain_model_expansion.py
```

Monitor output for:
- Success rate (should be 100%)
- Entity/attribute counts
- Any error messages

### Step 3: Verification

Run queries in Neo4j Browser to verify:

```cypher
// Count migrated nodes
MATCH (dm:DomainModelIR)
WHERE dm.migrated_to_graph = true
RETURN count(dm) as migrated_count

// Sample Entity structure
MATCH (dm:DomainModelIR)-[:HAS_ENTITY]->(e:Entity)-[:HAS_ATTRIBUTE]->(a:Attribute)
RETURN dm.app_id, e.name, collect(a.name) as attributes
LIMIT 10

// Check relationships between entities
MATCH (e1:Entity)-[r:RELATES_TO]->(e2:Entity)
RETURN e1.name, type(r), r.type, e2.name
LIMIT 20

// Verify counts
MATCH (e:Entity) RETURN count(e) as total_entities
MATCH (a:Attribute) RETURN count(a) as total_attributes
MATCH ()-[r:RELATES_TO]->() RETURN count(r) as total_relationships
```

### Step 4a: Success - Optional JSON Cleanup

If verification passes:

```bash
# Dry run first
DRY_RUN=true python scripts/migrations/neo4j/003_cleanup_json.py

# Live cleanup (with confirmation)
python scripts/migrations/neo4j/003_cleanup_json.py
```

### Step 4b: Issues Found - Rollback

If issues are found:

```bash
python scripts/migrations/neo4j/003_domain_model_expansion_rollback.py
```

Then investigate and fix issues before re-running migration.

## Node Structure

### Entity Node

```cypher
(:Entity {
  entity_id: "app123_User",          // Format: {app_id}_{entity_name}
  name: "User",
  description: "User account entity",
  is_aggregate_root: true,
  app_id: "app123"
})
```

### Attribute Node

```cypher
(:Attribute {
  attribute_id: "app123_User_id",    // Format: {entity_id}_{attribute_name}
  name: "id",
  data_type: "UUID",
  is_primary_key: true,
  is_nullable: false,
  is_unique: true,
  default_value: null,
  description: "Primary key",
  constraints: "{}",                  // JSON string
  entity_id: "app123_User",
  app_id: "app123"
})
```

### Relationships

```cypher
// DomainModelIR to Entity
(:DomainModelIR)-[:HAS_ENTITY]->(:Entity)

// Entity to Attribute
(:Entity)-[:HAS_ATTRIBUTE]->(:Attribute)

// Entity to Entity
(:Entity)-[:RELATES_TO {
  type: "one_to_many",
  field_name: "posts",
  back_populates: "author"
}]->(:Entity)
```

## Environment Variables

All scripts support:

- `NEO4J_URI` - Neo4j connection URI (default: bolt://localhost:7687)
- `NEO4J_USER` - Neo4j username (default: neo4j)
- `NEO4J_PASSWORD` - Neo4j password (default: devmatrix123)
- `DRY_RUN` - Enable dry run mode (default: false)

Cleanup script also supports:

- `SKIP_CONFIRMATION` - Skip confirmation prompt (default: false)

## Troubleshooting

### Migration fails with JSON parse errors

Check entities JSON format:

```cypher
MATCH (dm:DomainModelIR {app_id: "failing_app_id"})
RETURN dm.entities
```

Verify JSON is valid and matches DomainModelIR schema.

### Entity counts don't match

Compare JSON entities with created nodes:

```cypher
// Get JSON entity count
MATCH (dm:DomainModelIR {app_id: "app123"})
RETURN size(apoc.convert.fromJsonList(dm.entities)) as json_count

// Get graph entity count
MATCH (e:Entity {app_id: "app123"})
RETURN count(e) as graph_count
```

### Rollback doesn't remove all nodes

Check for orphaned nodes:

```cypher
// Find Entity nodes without app_id
MATCH (e:Entity)
WHERE e.app_id IS NULL
RETURN e

// Find Attribute nodes without Entity
MATCH (a:Attribute)
WHERE NOT EXISTS {MATCH ()-[:HAS_ATTRIBUTE]->(a)}
RETURN a
```

## Performance

- **Migration**: ~5-10 seconds per 100 DomainModelIR nodes
- **Rollback**: ~2-5 seconds per 100 nodes
- **Total expected**: 30-90 seconds for ~280 nodes

All operations use MERGE for idempotency, so re-running is safe but slightly slower.

## Safety

✅ **Safe operations:**
- Main migration (keeps original JSON)
- Rollback (restores to pre-migration state)
- Dry run mode on all scripts

⚠️ **Destructive operation:**
- JSON cleanup (cannot be undone)

Always run with `DRY_RUN=true` first to verify behavior.
