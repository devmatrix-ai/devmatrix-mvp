#!/usr/bin/env python3
"""
006_execute_add_temporal_metadata.py
Sprint: Inmediato (Pre-Sprint 3) - Task IA.5

Ejecuta la migración para agregar temporal metadata a:
- Entity
- Attribute
- Endpoint
- APIParameter

Usage:
    PYTHONPATH=. python scripts/migrations/neo4j/006_execute_add_temporal_metadata.py
    PYTHONPATH=. python scripts/migrations/neo4j/006_execute_add_temporal_metadata.py --dry-run
"""

import argparse
import sys
from datetime import datetime, timezone

from neo4j import GraphDatabase

from src.cognitive.config.settings import settings


def get_driver():
    """Create Neo4j driver from settings."""
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )


def pre_check(tx):
    """Count nodes missing temporal metadata."""
    query = """
    MATCH (n)
    WHERE (n:Entity OR n:Attribute OR n:Endpoint OR n:APIParameter)
      AND n.created_at IS NULL
    RETURN labels(n)[0] as label, count(n) as missing_count
    ORDER BY label
    """
    result = tx.run(query)
    return {record["label"]: record["missing_count"] for record in result}


def add_temporal_metadata(tx, label: str) -> int:
    """Add temporal metadata to nodes of given label."""
    query = f"""
    MATCH (n:{label})
    WHERE n.created_at IS NULL
    SET n.created_at = datetime(),
        n.updated_at = datetime(),
        n.schema_version = 1
    RETURN count(n) as updated_count
    """
    result = tx.run(query)
    record = result.single()
    return record["updated_count"] if record else 0


def register_migration(tx, stats: dict) -> None:
    """Register migration in MigrationRun."""
    total_updated = sum(stats.values())

    query = """
    CREATE (m:MigrationRun {
        migration_id: "006_add_temporal_metadata",
        schema_version_before: 2,
        schema_version_after: 3,
        status: "SUCCESS",
        started_at: $started_at,
        completed_at: datetime(),
        duration_seconds: $duration,
        objects_created: 0,
        objects_deleted: 0,
        objects_updated: $updated,
        error_message: null,
        executed_by: "migration_script",
        execution_mode: "LIVE",
        description: "Add temporal metadata (created_at, updated_at, schema_version) to Entity, Attribute, Endpoint, APIParameter",
        details: $details
    })
    """

    tx.run(
        query,
        started_at=datetime.now(timezone.utc).isoformat(),
        duration=0,  # Will be calculated properly in real execution
        updated=total_updated,
        details=str(stats),
    )


def update_schema_version(tx) -> None:
    """Update GraphSchemaVersion singleton."""
    query = """
    MATCH (v:GraphSchemaVersion {singleton: true})
    SET v.current_version = 3,
        v.last_migration = "006_add_temporal_metadata",
        v.updated_at = datetime()
    RETURN v.current_version as version
    """
    result = tx.run(query)
    record = result.single()
    return record["version"] if record else None


def link_migration_to_version(tx) -> None:
    """Create RESULTED_IN_VERSION relationship."""
    query = """
    MATCH (m:MigrationRun {migration_id: "006_add_temporal_metadata"})
    MATCH (v:GraphSchemaVersion {singleton: true})
    MERGE (m)-[:RESULTED_IN_VERSION]->(v)
    """
    tx.run(query)


def verify_migration(tx) -> dict:
    """Verify all nodes have temporal metadata."""
    query = """
    MATCH (n)
    WHERE (n:Entity OR n:Attribute OR n:Endpoint OR n:APIParameter)
    RETURN
        labels(n)[0] as label,
        count(n) as total,
        sum(CASE WHEN n.created_at IS NOT NULL THEN 1 ELSE 0 END) as with_temporal
    ORDER BY label
    """
    result = tx.run(query)
    return {
        record["label"]: {
            "total": record["total"],
            "with_temporal": record["with_temporal"],
            "complete": record["total"] == record["with_temporal"],
        }
        for record in result
    }


def main():
    parser = argparse.ArgumentParser(
        description="Add temporal metadata to Entity, Attribute, Endpoint, APIParameter nodes"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("Migration 006: Add Temporal Metadata")
    print("=" * 70)
    print()

    driver = get_driver()
    database = settings.neo4j_database

    try:
        with driver.session(database=database) as session:
            # Pre-check
            print("📊 Pre-check: Nodes missing temporal metadata")
            print("-" * 50)

            missing = session.execute_read(pre_check)

            if not missing:
                print("✅ All nodes already have temporal metadata!")
                print("   Nothing to do.")
                return 0

            total_missing = sum(missing.values())
            for label, count in sorted(missing.items()):
                print(f"   {label}: {count:,} nodes")
            print(f"   TOTAL: {total_missing:,} nodes")
            print()

            if args.dry_run:
                print("🔍 DRY RUN - No changes will be made")
                print()
                print("Would update:")
                for label, count in sorted(missing.items()):
                    print(f"   - {count:,} {label} nodes")
                print()
                print("Would set on each node:")
                print("   - created_at: datetime()")
                print("   - updated_at: datetime()")
                print("   - schema_version: 1")
                return 0

            # Execute migration
            print("🚀 Executing migration...")
            print("-" * 50)

            start_time = datetime.now(timezone.utc)
            stats = {}

            labels = ["Entity", "Attribute", "Endpoint", "APIParameter"]
            for label in labels:
                if label in missing and missing[label] > 0:
                    count = session.execute_write(add_temporal_metadata, label)
                    stats[label] = count
                    print(f"   ✅ {label}: {count:,} nodes updated")
                else:
                    print(f"   ⏭️  {label}: 0 nodes (already complete)")

            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            print()
            print(f"⏱️  Duration: {duration:.2f}s")
            print()

            # Register migration
            print("📝 Registering migration...")
            session.execute_write(register_migration, stats)
            print("   ✅ MigrationRun created")

            # Update schema version
            new_version = session.execute_write(update_schema_version)
            print(f"   ✅ GraphSchemaVersion updated to {new_version}")

            # Link migration
            session.execute_write(link_migration_to_version)
            print("   ✅ RESULTED_IN_VERSION relationship created")
            print()

            # Verify
            print("🔍 Verification...")
            print("-" * 50)

            verification = session.execute_read(verify_migration)
            all_complete = True

            for label, data in sorted(verification.items()):
                status = "✅" if data["complete"] else "❌"
                print(f"   {status} {label}: {data['with_temporal']:,}/{data['total']:,}")
                if not data["complete"]:
                    all_complete = False

            print()
            if all_complete:
                print("✅ Migration completed successfully!")
            else:
                print("⚠️  Migration completed with warnings - some nodes missing metadata")

            return 0 if all_complete else 1

    finally:
        driver.close()


if __name__ == "__main__":
    sys.exit(main())
