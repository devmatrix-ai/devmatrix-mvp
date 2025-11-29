#!/usr/bin/env python3
"""
Sprint 1 Task 1.3: Domain Model Expansion Rollback

Reverses the migration from 003_domain_model_expansion.py by:
- Removing Entity nodes and HAS_ENTITY relationships
- Removing Attribute nodes and HAS_ATTRIBUTE relationships
- Removing RELATES_TO relationships between entities
- Clearing migration flags from DomainModelIR nodes

The original entities JSON property is preserved, so this is a safe rollback.

This script:
1. Finds all DomainModelIR nodes marked as migrated
2. Deletes associated Entity and Attribute nodes
3. Deletes all related relationships
4. Clears migration flags
5. Provides verification of rollback

The script is idempotent - it can be run multiple times safely.
"""
import asyncio
import os
import sys
from typing import Dict, Any
from neo4j import AsyncGraphDatabase

# Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "devmatrix123")

# Dry run mode
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"


async def count_migration_artifacts(driver) -> Dict[str, int]:
    """
    Count all nodes and relationships created by migration.

    Returns:
        Dict with counts of entities, attributes, and relationships
    """
    async with driver.session() as session:
        # Count Entity nodes
        result = await session.run("MATCH (e:Entity) RETURN count(e) as count")
        record = await result.single()
        entity_count = record["count"] if record else 0

        # Count Attribute nodes
        result = await session.run("MATCH (a:Attribute) RETURN count(a) as count")
        record = await result.single()
        attribute_count = record["count"] if record else 0

        # Count RELATES_TO relationships
        result = await session.run("MATCH ()-[r:RELATES_TO]->() RETURN count(r) as count")
        record = await result.single()
        relates_to_count = record["count"] if record else 0

        # Count HAS_ENTITY relationships
        result = await session.run("MATCH ()-[r:HAS_ENTITY]->() RETURN count(r) as count")
        record = await result.single()
        has_entity_count = record["count"] if record else 0

        # Count HAS_ATTRIBUTE relationships
        result = await session.run("MATCH ()-[r:HAS_ATTRIBUTE]->() RETURN count(r) as count")
        record = await result.single()
        has_attribute_count = record["count"] if record else 0

        # Count migrated DomainModelIR nodes
        result = await session.run("""
            MATCH (dm:DomainModelIR)
            WHERE dm.migrated_to_graph = true
            RETURN count(dm) as count
        """)
        record = await result.single()
        migrated_count = record["count"] if record else 0

        return {
            "entities": entity_count,
            "attributes": attribute_count,
            "relates_to": relates_to_count,
            "has_entity": has_entity_count,
            "has_attribute": has_attribute_count,
            "migrated_domain_models": migrated_count
        }


async def delete_entity_and_attributes(driver, app_id: str, dry_run: bool = False) -> Dict[str, int]:
    """
    Delete all Entity and Attribute nodes for a specific app.

    Args:
        driver: Neo4j driver
        app_id: Application ID
        dry_run: If True, only count without deleting

    Returns:
        Dict with counts of deleted nodes
    """
    stats = {
        "entities": 0,
        "attributes": 0,
        "has_entity_rels": 0,
        "has_attribute_rels": 0,
        "relates_to_rels": 0
    }

    async with driver.session() as session:
        if dry_run:
            # Count what would be deleted
            result = await session.run("""
                MATCH (e:Entity {app_id: $app_id})
                RETURN count(e) as count
            """, app_id=app_id)
            record = await result.single()
            stats["entities"] = record["count"] if record else 0

            result = await session.run("""
                MATCH (a:Attribute {app_id: $app_id})
                RETURN count(a) as count
            """, app_id=app_id)
            record = await result.single()
            stats["attributes"] = record["count"] if record else 0

            return stats

        # Delete HAS_ATTRIBUTE relationships and Attribute nodes
        result = await session.run("""
            MATCH (e:Entity {app_id: $app_id})-[r:HAS_ATTRIBUTE]->(a:Attribute)
            WITH e, r, a, count(r) as rel_count
            DELETE r
            RETURN rel_count
        """, app_id=app_id)
        async for record in result:
            stats["has_attribute_rels"] += record.get("rel_count", 0)

        result = await session.run("""
            MATCH (a:Attribute {app_id: $app_id})
            WITH a, count(a) as attr_count
            DELETE a
            RETURN attr_count
        """, app_id=app_id)
        async for record in result:
            stats["attributes"] += record.get("attr_count", 0)

        # Delete RELATES_TO relationships between entities
        result = await session.run("""
            MATCH (e1:Entity {app_id: $app_id})-[r:RELATES_TO]->(e2:Entity {app_id: $app_id})
            WITH r, count(r) as rel_count
            DELETE r
            RETURN rel_count
        """, app_id=app_id)
        async for record in result:
            stats["relates_to_rels"] += record.get("rel_count", 0)

        # Delete HAS_ENTITY relationships and Entity nodes
        result = await session.run("""
            MATCH (dm:DomainModelIR {app_id: $app_id})-[r:HAS_ENTITY]->(e:Entity)
            WITH dm, r, e, count(r) as rel_count
            DELETE r
            RETURN rel_count
        """, app_id=app_id)
        async for record in result:
            stats["has_entity_rels"] += record.get("rel_count", 0)

        result = await session.run("""
            MATCH (e:Entity {app_id: $app_id})
            WITH e, count(e) as entity_count
            DELETE e
            RETURN entity_count
        """, app_id=app_id)
        async for record in result:
            stats["entities"] += record.get("entity_count", 0)

    return stats


async def clear_migration_flags(driver, app_id: str, dry_run: bool = False) -> bool:
    """
    Clear migration flags from DomainModelIR node.

    Args:
        driver: Neo4j driver
        app_id: Application ID
        dry_run: If True, don't modify

    Returns:
        True if flag was cleared, False otherwise
    """
    if dry_run:
        return True

    async with driver.session() as session:
        result = await session.run("""
            MATCH (dm:DomainModelIR {app_id: $app_id})
            WHERE dm.migrated_to_graph = true
            REMOVE dm.migrated_to_graph, dm.migration_timestamp
            RETURN count(dm) as count
        """, app_id=app_id)
        record = await result.single()
        return (record["count"] if record else 0) > 0


async def get_migrated_domain_models(driver):
    """
    Get all DomainModelIR nodes that were migrated.

    Returns:
        List of app_ids
    """
    async with driver.session() as session:
        result = await session.run("""
            MATCH (dm:DomainModelIR)
            WHERE dm.migrated_to_graph = true
            RETURN dm.app_id as app_id
            ORDER BY dm.app_id
        """)
        app_ids = [record["app_id"] async for record in result]
        return app_ids


async def run_rollback():
    """
    Main rollback logic.

    Process:
    1. Connect to Neo4j
    2. Get all migrated DomainModelIR nodes
    3. For each, delete Entity and Attribute nodes
    4. Clear migration flags
    5. Verify rollback
    """
    mode_str = "DRY RUN" if DRY_RUN else "ROLLBACK"
    print(f"🔄 Starting Domain Model Migration {mode_str}...")
    print(f"📊 Configuration:")
    print(f"   Neo4j: {NEO4J_URI}")
    print(f"   Mode: {'DRY RUN' if DRY_RUN else 'LIVE ROLLBACK'}")
    print()

    driver = AsyncGraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD)
    )

    try:
        # Count before rollback
        print("🔍 Counting migration artifacts before rollback...")
        before_counts = await count_migration_artifacts(driver)
        print(f"📊 Before Rollback:")
        print(f"   Entity nodes: {before_counts['entities']}")
        print(f"   Attribute nodes: {before_counts['attributes']}")
        print(f"   RELATES_TO relationships: {before_counts['relates_to']}")
        print(f"   HAS_ENTITY relationships: {before_counts['has_entity']}")
        print(f"   HAS_ATTRIBUTE relationships: {before_counts['has_attribute']}")
        print(f"   Migrated DomainModelIR nodes: {before_counts['migrated_domain_models']}")
        print()

        # Get migrated domain models
        print("🔍 Fetching migrated DomainModelIR nodes...")
        app_ids = await get_migrated_domain_models(driver)
        print(f"📝 Found {len(app_ids)} migrated domain models")

        if not app_ids:
            print("✅ No migrated domain models to rollback!")
            return

        print()

        # Statistics
        total_deleted = {
            "entities": 0,
            "attributes": 0,
            "has_entity_rels": 0,
            "has_attribute_rels": 0,
            "relates_to_rels": 0
        }
        successful = 0
        failed = 0

        # Process each domain model
        for i, app_id in enumerate(app_ids, 1):
            try:
                # Delete entities and attributes
                stats = await delete_entity_and_attributes(driver, app_id, dry_run=DRY_RUN)

                # Update totals
                total_deleted["entities"] += stats["entities"]
                total_deleted["attributes"] += stats["attributes"]
                total_deleted["has_entity_rels"] += stats.get("has_entity_rels", 0)
                total_deleted["has_attribute_rels"] += stats.get("has_attribute_rels", 0)
                total_deleted["relates_to_rels"] += stats.get("relates_to_rels", 0)

                # Clear migration flags
                await clear_migration_flags(driver, app_id, dry_run=DRY_RUN)

                successful += 1

                # Progress report
                if i % 50 == 0 or i == len(app_ids):
                    print(f"✅ [{i}/{len(app_ids)}] {app_id}")
                    print(f"   Deleted: {stats['entities']} entities, {stats['attributes']} attributes")

            except Exception as e:
                failed += 1
                print(f"❌ Error processing {app_id}: {e}")
                continue

        # Verification
        print("\n🔍 Verifying rollback...")
        after_counts = await count_migration_artifacts(driver)

        # Final report
        print("\n" + "=" * 60)
        print(f"📊 {mode_str} COMPLETE")
        print("=" * 60)
        print(f"Domain models processed: {len(app_ids)}")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print()
        print("Deletion Statistics:")
        print(f"   Entities deleted: {total_deleted['entities']}")
        print(f"   Attributes deleted: {total_deleted['attributes']}")
        print(f"   HAS_ENTITY relationships deleted: {total_deleted['has_entity_rels']}")
        print(f"   HAS_ATTRIBUTE relationships deleted: {total_deleted['has_attribute_rels']}")
        print(f"   RELATES_TO relationships deleted: {total_deleted['relates_to_rels']}")
        print()
        print("Verification Counts (After Rollback):")
        print(f"   Entity nodes: {after_counts['entities']}")
        print(f"   Attribute nodes: {after_counts['attributes']}")
        print(f"   RELATES_TO edges: {after_counts['relates_to']}")
        print(f"   HAS_ENTITY edges: {after_counts['has_entity']}")
        print(f"   HAS_ATTRIBUTE edges: {after_counts['has_attribute']}")
        print(f"   Migrated DomainModelIR nodes: {after_counts['migrated_domain_models']}")
        print("=" * 60)

        if DRY_RUN:
            print("\n💡 This was a DRY RUN - no changes were made")
            print("   Run without DRY_RUN=true to apply rollback")
        else:
            print("\n💡 Rollback complete!")
            print("   Original entities JSON properties are still intact")
            print("   You can re-run the migration if needed")

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        await driver.close()
        print("\n🔌 Connection closed")


if __name__ == "__main__":
    asyncio.run(run_rollback())
