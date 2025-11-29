#!/usr/bin/env python3
"""
Migration 011: ErrorKnowledge Schema for Active Learning

Executes the Cypher schema file and registers the migration.
Creates constraints and indexes for ErrorKnowledge nodes.

Usage:
    python scripts/migrations/neo4j/011_execute_error_knowledge_schema.py
"""
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from neo4j import GraphDatabase


MIGRATION_NAME = "011_error_knowledge_schema"
MIGRATION_DESCRIPTION = "ErrorKnowledge schema for Active Learning"


def get_neo4j_driver():
    """Get Neo4j driver from environment."""
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "devmatrix")
    return GraphDatabase.driver(uri, auth=(user, password))


def check_if_migrated(driver) -> bool:
    """Check if migration was already applied."""
    with driver.session() as session:
        result = session.run("""
            MATCH (m:Migration {name: $name})
            RETURN m.applied_at as applied_at
        """, name=MIGRATION_NAME)
        record = result.single()
        return record is not None


def register_migration(driver):
    """Register migration as applied."""
    with driver.session() as session:
        session.run("""
            MERGE (m:Migration {name: $name})
            ON CREATE SET
                m.description = $description,
                m.applied_at = datetime(),
                m.version = '011'
            ON MATCH SET
                m.last_run = datetime()
        """,
            name=MIGRATION_NAME,
            description=MIGRATION_DESCRIPTION,
        )


def execute_cypher_file(driver, cypher_path: Path):
    """Execute a Cypher file statement by statement."""
    with open(cypher_path, 'r') as f:
        content = f.read()

    # Split by semicolons, filter comments and empty statements
    statements = []
    for stmt in content.split(';'):
        # Remove comments
        lines = []
        for line in stmt.split('\n'):
            line = line.strip()
            if not line.startswith('//') and line:
                lines.append(line)
        cleaned = ' '.join(lines).strip()
        if cleaned:
            statements.append(cleaned)

    with driver.session() as session:
        for i, stmt in enumerate(statements, 1):
            try:
                session.run(stmt)
                print(f"  ✓ Statement {i}/{len(statements)} executed")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"  ⚡ Statement {i}/{len(statements)} skipped (already exists)")
                else:
                    print(f"  ✗ Statement {i}/{len(statements)} failed: {e}")
                    raise


def verify_schema(driver) -> dict:
    """Verify that schema was created correctly."""
    with driver.session() as session:
        # Check constraints
        constraints = session.run("""
            SHOW CONSTRAINTS
            WHERE name CONTAINS 'error_knowledge'
            RETURN name
        """)
        constraint_names = [r["name"] for r in constraints]

        # Check indexes
        indexes = session.run("""
            SHOW INDEXES
            WHERE name CONTAINS 'error_knowledge'
            RETURN name
        """)
        index_names = [r["name"] for r in indexes]

        return {
            "constraints": constraint_names,
            "indexes": index_names,
        }


def main():
    print(f"\n{'='*60}")
    print(f"Migration {MIGRATION_NAME}")
    print(f"{'='*60}\n")

    driver = get_neo4j_driver()

    try:
        # Check if already migrated
        if check_if_migrated(driver):
            print("⚡ Migration already applied, skipping...")
            return 0

        # Execute cypher file
        cypher_path = Path(__file__).parent / "011_error_knowledge_schema.cypher"
        if not cypher_path.exists():
            print(f"✗ Cypher file not found: {cypher_path}")
            return 1

        print(f"📄 Executing: {cypher_path.name}")
        execute_cypher_file(driver, cypher_path)

        # Verify schema
        print("\n🔍 Verifying schema...")
        schema = verify_schema(driver)
        print(f"  Constraints: {len(schema['constraints'])}")
        for c in schema['constraints']:
            print(f"    - {c}")
        print(f"  Indexes: {len(schema['indexes'])}")
        for i in schema['indexes']:
            print(f"    - {i}")

        # Register migration
        print("\n📝 Registering migration...")
        register_migration(driver)

        print(f"\n✅ Migration {MIGRATION_NAME} completed successfully!\n")
        return 0

    except Exception as e:
        print(f"\n✗ Migration failed: {e}\n")
        return 1
    finally:
        driver.close()


if __name__ == "__main__":
    sys.exit(main())
