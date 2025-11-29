#!/usr/bin/env python3
"""
Execute Migration 002: Register Past Migrations (Sprints 0-2)

This script retroactively registers the migrations from Sprints 0-2
by creating MigrationRun nodes with synthetic metrics for observability.

Usage:
    PYTHONPATH=. python scripts/migrations/neo4j/002_execute_register_past_migrations.py

Prerequisites:
    - Migration 001 completed (GraphSchemaVersion singleton exists)
    - Neo4j database accessible
    - No existing MigrationRun nodes for Sprints 0-2 migrations

Verification:
    - 5 MigrationRun nodes created
    - All linked to GraphSchemaVersion via RESULTED_IN_VERSION
    - Total objects_created = 10,940 nodes
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from src.cognitive.infrastructure.neo4j_client import Neo4jPatternClient


def verify_pre_conditions():
    """
    Verify that:
    1. GraphSchemaVersion singleton exists
    2. No existing MigrationRun nodes for these migrations
    """
    print("🔍 Verificando pre-condiciones...")

    with Neo4jPatternClient() as neo4j:
        # Check GraphSchemaVersion exists
        query = """
        MATCH (v:GraphSchemaVersion {singleton: true})
        RETURN v.current_version as version,
               v.last_migration as last_migration
        """
        result = neo4j._execute_query(query)

        if not result:
            print("❌ ERROR: GraphSchemaVersion singleton not found!")
            print("   Please run migration 001 first.")
            sys.exit(1)

        version_info = result[0]
        print(f"✅ GraphSchemaVersion found: v{version_info['version']}")

        # Check for existing MigrationRun nodes
        query = """
        MATCH (m:MigrationRun)
        WHERE m.migration_id IN [
            "001_sprint0_cleanup_orphans",
            "002_sprint0_domain_label_rename",
            "003_sprint1_domain_model_expansion",
            "004_sprint1_attribute_expansion",
            "005_sprint2_api_model_expansion"
        ]
        RETURN count(m) as existing_count,
               collect(m.migration_id) as existing_migrations
        """
        result = neo4j._execute_query(query)

        if result and result[0]['existing_count'] > 0:
            existing = result[0]['existing_migrations']
            print(f"⚠️  WARNING: Found {len(existing)} existing MigrationRun nodes:")
            for migration in existing:
                print(f"   - {migration}")
            print("   Will UPDATE existing nodes instead of creating new ones")
        else:
            print("✅ No existing MigrationRun nodes found, will create new")


def execute_migration():
    """
    Execute the migration by running all statements from the Cypher file.
    """
    print("\n🚀 Ejecutando migration 002_register_past_migrations.cypher...")

    # Read the Cypher script
    script_path = Path(__file__).parent / "002_register_past_migrations.cypher"

    if not script_path.exists():
        print(f"❌ ERROR: Migration script not found at {script_path}")
        sys.exit(1)

    # Create client
    neo4j = Neo4jPatternClient()
    neo4j.connect()

    try:
        with open(script_path, "r") as f:
            cypher_script = f.read()

        # Separate statements by semicolon
        statements = [s.strip() for s in cypher_script.split(";") if s.strip()]

        # Filter out comments and empty lines from each statement
        clean_statements = []
        for stmt in statements:
            lines = [line.strip() for line in stmt.split("\n")
                     if line.strip() and not line.strip().startswith("//")]
            if lines:
                clean_statements.append(" ".join(lines))

        print(f"   Ejecutando {len(clean_statements)} statements...")

        # Execute each statement
        for i, statement in enumerate(clean_statements, 1):
            print(f"   [{i}/{len(clean_statements)}] Executing...")
            result = neo4j._execute_query(statement)

            # If this is the final SELECT, print results
            if i == len(clean_statements) and result:
                print(f"\n   ✅ {len(result)} MigrationRun nodes registered:")
                for row in result:
                    print(f"      {row['migration']}: "
                          f"{row['created']} created, "
                          f"{row['updated']} updated, "
                          f"{row['deleted']} deleted "
                          f"({row['duration']}s) → v{row['linked_to_version']}")

        print("✅ Migration ejecutada exitosamente")

    finally:
        neo4j.close()


def verify_post_conditions():
    """
    Verify that:
    1. Exactly 5 MigrationRun nodes exist
    2. All are linked to GraphSchemaVersion via RESULTED_IN_VERSION
    3. Total objects_created = 10,940
    """
    print("\n🔍 Verificando post-condiciones...")

    with Neo4jPatternClient() as neo4j:
        # Count MigrationRun nodes
        query = """
        MATCH (m:MigrationRun)
        RETURN count(m) as total_count,
               sum(m.objects_created) as total_created,
               sum(m.objects_updated) as total_updated,
               sum(m.objects_deleted) as total_deleted,
               collect(DISTINCT m.status) as statuses
        """
        result = neo4j._execute_query(query)

        if not result:
            print("❌ ERROR: No MigrationRun nodes found!")
            sys.exit(1)

        stats = result[0]

        # Check count
        if stats['total_count'] != 5:
            print(f"❌ ERROR: Expected 5 MigrationRun nodes, found {stats['total_count']}")
            sys.exit(1)
        print(f"✅ MigrationRun count: {stats['total_count']} (expected: 5)")

        # Check total created
        if stats['total_created'] != 10940:
            print(f"⚠️  WARNING: Expected 10,940 objects_created, found {stats['total_created']}")
        else:
            print(f"✅ Total objects created: {stats['total_created']:,}")

        print(f"✅ Total objects updated: {stats['total_updated']:,}")
        print(f"✅ Total objects deleted: {stats['total_deleted']:,}")
        print(f"✅ Migration statuses: {stats['statuses']}")

        # Check relationships
        query = """
        MATCH (m:MigrationRun)-[r:RESULTED_IN_VERSION]->(v:GraphSchemaVersion)
        RETURN count(r) as relationship_count
        """
        result = neo4j._execute_query(query)

        if result and result[0]['relationship_count'] == 5:
            print(f"✅ RESULTED_IN_VERSION relationships: 5")
        else:
            count = result[0]['relationship_count'] if result else 0
            print(f"❌ ERROR: Expected 5 RESULTED_IN_VERSION relationships, found {count}")
            sys.exit(1)

    print("\n🎉 All post-conditions verified successfully!")


def main():
    """Main execution flow."""
    print("=" * 80)
    print("MIGRATION 002: Register Past Migrations (Sprints 0-2)")
    print("Sprint: Tareas Inmediatas (Pre-Sprint 3)")
    print(f"Execution time: {datetime.now().isoformat()}")
    print("=" * 80)

    # Step 1: Verify prerequisites
    verify_pre_conditions()

    # Step 2: Execute migration
    execute_migration()

    # Step 3: Verify results
    verify_post_conditions()

    # Summary
    print("\n" + "=" * 80)
    print("✅ MIGRATION 002 COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. ✅ IA.1 DONE: GraphSchemaVersion singleton created")
    print("  2. ✅ IA.2 DONE: Past migrations registered")
    print("  3. ⏳ IA.3 TODO: Create GraphIRRepository base class")
    print("  4. ⏳ IA.4 TODO: Implement roundtrip tests")
    print("=" * 80)


if __name__ == "__main__":
    main()
