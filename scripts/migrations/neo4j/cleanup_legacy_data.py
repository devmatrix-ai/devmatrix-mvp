#!/usr/bin/env python3
"""
Legacy Data Cleanup Script
===========================
Cleans up legacy data to achieve 10/10 Safety Rails compliance.

Operations:
1. Remove orphan nodes (not connected to anything useful)
2. Add temporal metadata to nodes missing it
3. Remove empty APIModelIR, DomainModelIR nodes
4. Create GraphSchemaVersion if missing

IMPORTANT: Run backup_neo4j.py BEFORE running this script!

Usage:
    python scripts/migrations/neo4j/cleanup_legacy_data.py

Date: 2025-11-29
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from neo4j import GraphDatabase


class LegacyDataCleanup:
    """Cleans up legacy data for Safety Rails compliance."""

    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password")
        self.database = os.getenv("NEO4J_DATABASE", "neo4j")

        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password),
        )
        self.stats = {
            "orphans_deleted": 0,
            "temporal_added": 0,
            "empty_models_deleted": 0,
            "schema_version_created": False,
        }

    def close(self):
        if self.driver:
            self.driver.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _run_query(self, query: str, params: dict = None):
        """Execute a query and return results."""
        with self.driver.session(database=self.database) as session:
            result = session.run(query, params or {})
            return [dict(record) for record in result]

    def _run_write(self, query: str, params: dict = None) -> int:
        """Execute a write query and return affected count."""
        with self.driver.session(database=self.database) as session:
            result = session.run(query, params or {})
            summary = result.consume()
            return (
                summary.counters.nodes_deleted +
                summary.counters.nodes_created +
                summary.counters.properties_set +
                summary.counters.relationships_deleted
            )

    def ensure_schema_version(self):
        """Create GraphSchemaVersion if missing."""
        print("\n📌 Checking GraphSchemaVersion...")

        check = self._run_query("""
            MATCH (v:GraphSchemaVersion)
            RETURN v.version as version
            ORDER BY v.version DESC
            LIMIT 1
        """)

        if not check or check[0].get("version") is None:
            print("   Creating GraphSchemaVersion node...")
            self._run_write("""
                MERGE (v:GraphSchemaVersion {version: 6})
                ON CREATE SET
                    v.description = 'Sprint 6 - FullIRGraphLoader',
                    v.applied_at = datetime(),
                    v.applied_by = 'cleanup_legacy_data.py',
                    v.created_at = datetime(),
                    v.updated_at = datetime()
            """)
            self.stats["schema_version_created"] = True
            print("   ✅ Created GraphSchemaVersion v6")
        else:
            print(f"   ✅ Schema version exists: v{check[0]['version']}")

    def add_temporal_metadata(self):
        """Add created_at/updated_at to nodes missing them."""
        print("\n📌 Adding temporal metadata...")

        # Get count of nodes without temporal metadata
        count_result = self._run_query("""
            MATCH (n)
            WHERE n.created_at IS NULL
            RETURN count(n) as count
        """)
        missing_count = count_result[0]["count"] if count_result else 0
        print(f"   Nodes without temporal metadata: {missing_count}")

        if missing_count > 0:
            # Add in batches to avoid timeout
            batch_size = 10000
            total_updated = 0

            while True:
                affected = self._run_write(f"""
                    MATCH (n)
                    WHERE n.created_at IS NULL
                    WITH n LIMIT {batch_size}
                    SET n.created_at = datetime(),
                        n.updated_at = datetime()
                    RETURN count(n) as updated
                """)

                if affected == 0:
                    break

                total_updated += affected // 2  # Each node gets 2 properties
                print(f"   Updated batch... (total: ~{total_updated})")

            self.stats["temporal_added"] = total_updated
            print(f"   ✅ Added temporal metadata to {total_updated} nodes")

    def delete_orphan_nodes(self):
        """Delete nodes not connected to anything useful."""
        print("\n📌 Removing orphan nodes...")

        # First, identify orphan types
        orphan_types = self._run_query("""
            MATCH (n)
            WHERE NOT (n)--()
              AND NOT n:GraphSchemaVersion
              AND NOT n:MigrationRun
              AND NOT n:MigrationCheckpoint
            RETURN labels(n)[0] as label, count(n) as count
            ORDER BY count DESC
        """)

        if orphan_types:
            print("   Orphan node types found:")
            for t in orphan_types[:10]:
                print(f"      - {t['label']}: {t['count']}")

        # Delete orphans in batches
        batch_size = 5000
        total_deleted = 0

        while True:
            result = self._run_query(f"""
                MATCH (n)
                WHERE NOT (n)--()
                  AND NOT n:GraphSchemaVersion
                  AND NOT n:MigrationRun
                  AND NOT n:MigrationCheckpoint
                WITH n LIMIT {batch_size}
                DETACH DELETE n
                RETURN count(*) as deleted
            """)

            deleted = result[0]["deleted"] if result else 0
            if deleted == 0:
                break

            total_deleted += deleted
            print(f"   Deleted batch of {deleted}... (total: {total_deleted})")

        self.stats["orphans_deleted"] = total_deleted
        print(f"   ✅ Deleted {total_deleted} orphan nodes")

    def delete_empty_models(self):
        """Delete APIModelIR/DomainModelIR without children."""
        print("\n📌 Removing empty model nodes...")

        # Delete APIModels without endpoints
        api_result = self._run_query("""
            MATCH (a:APIModelIR)
            WHERE NOT (a)-[:HAS_ENDPOINT]->(:Endpoint)
              AND NOT (a)<-[:HAS_API_MODEL]-(:ApplicationIR)
            WITH a LIMIT 1000
            DETACH DELETE a
            RETURN count(*) as deleted
        """)
        api_deleted = api_result[0]["deleted"] if api_result else 0

        # Delete DomainModels without entities
        domain_result = self._run_query("""
            MATCH (d:DomainModelIR)
            WHERE NOT (d)-[:HAS_ENTITY]->(:Entity)
              AND NOT (d)<-[:HAS_DOMAIN_MODEL]-(:ApplicationIR)
            WITH d LIMIT 1000
            DETACH DELETE d
            RETURN count(*) as deleted
        """)
        domain_deleted = domain_result[0]["deleted"] if domain_result else 0

        # Delete Entities without attributes (only if orphaned)
        entity_result = self._run_query("""
            MATCH (e:Entity)
            WHERE NOT (e)-[:HAS_ATTRIBUTE]->(:Attribute)
              AND NOT (e)<-[:HAS_ENTITY]-(:DomainModelIR)
            WITH e LIMIT 1000
            DETACH DELETE e
            RETURN count(*) as deleted
        """)
        entity_deleted = entity_result[0]["deleted"] if entity_result else 0

        total = api_deleted + domain_deleted + entity_deleted
        self.stats["empty_models_deleted"] = total

        print(f"   Deleted empty APIModels: {api_deleted}")
        print(f"   Deleted empty DomainModels: {domain_deleted}")
        print(f"   Deleted orphan Entities: {entity_deleted}")
        print(f"   ✅ Total empty models removed: {total}")

    def run_cleanup(self):
        """Run all cleanup operations."""
        print("\n" + "=" * 60)
        print("Legacy Data Cleanup")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("=" * 60)

        # Step 1: Ensure schema version exists
        self.ensure_schema_version()

        # Step 2: Add temporal metadata
        self.add_temporal_metadata()

        # Step 3: Delete empty models
        self.delete_empty_models()

        # Step 4: Delete orphan nodes
        self.delete_orphan_nodes()

        # Summary
        print("\n" + "=" * 60)
        print("CLEANUP COMPLETE")
        print("=" * 60)
        print(f"   Schema version created: {self.stats['schema_version_created']}")
        print(f"   Temporal metadata added: {self.stats['temporal_added']}")
        print(f"   Empty models deleted: {self.stats['empty_models_deleted']}")
        print(f"   Orphan nodes deleted: {self.stats['orphans_deleted']}")
        print("=" * 60 + "\n")

        return self.stats


def main():
    print("\n⚠️  WARNING: This script modifies the database!")
    print("   Make sure you have run backup_neo4j.py first!\n")

    with LegacyDataCleanup() as cleanup:
        stats = cleanup.run_cleanup()

    print("✅ Cleanup completed. Run validate_safety_rails.py to verify.")


if __name__ == "__main__":
    main()
