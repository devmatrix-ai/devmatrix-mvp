#!/usr/bin/env python3
"""
Sprint 1 Task 1.3: Domain Model JSON Cleanup (Optional)

OPTIONAL cleanup script to remove the entities JSON property from DomainModelIR nodes
after verifying the migration was successful.

WARNING: This is a destructive operation. Only run after:
1. Verifying migration completed successfully
2. Testing that Entity/Attribute nodes are accessible
3. Confirming relationships are correct

This script:
1. Finds all DomainModelIR nodes marked as migrated
2. Removes the entities JSON property
3. Keeps metadata and other properties intact

The script is idempotent - it can be run multiple times safely.
"""
import asyncio
import os
import sys
from typing import List
from neo4j import AsyncGraphDatabase

# Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "devmatrix123")

# Dry run mode
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# Require explicit confirmation
REQUIRE_CONFIRMATION = os.getenv("SKIP_CONFIRMATION", "false").lower() != "true"


async def get_migrated_with_json(driver) -> List[str]:
    """
    Get all DomainModelIR nodes that are migrated and still have JSON.

    Returns:
        List of app_ids
    """
    async with driver.session() as session:
        result = await session.run("""
            MATCH (dm:DomainModelIR)
            WHERE dm.migrated_to_graph = true
              AND dm.entities IS NOT NULL
              AND dm.entities <> ''
            RETURN dm.app_id as app_id
            ORDER BY dm.app_id
        """)
        app_ids = [record["app_id"] async for record in result]
        return app_ids


async def remove_entities_json(driver, app_id: str, dry_run: bool = False) -> bool:
    """
    Remove entities JSON property from a DomainModelIR node.

    Args:
        driver: Neo4j driver
        app_id: Application ID
        dry_run: If True, don't modify

    Returns:
        True if property was removed, False otherwise
    """
    if dry_run:
        return True

    async with driver.session() as session:
        result = await session.run("""
            MATCH (dm:DomainModelIR {app_id: $app_id})
            WHERE dm.migrated_to_graph = true
              AND dm.entities IS NOT NULL
            REMOVE dm.entities
            SET dm.json_cleaned_timestamp = datetime()
            RETURN count(dm) as count
        """, app_id=app_id)
        record = await result.single()
        return (record["count"] if record else 0) > 0


async def verify_graph_structure(driver, app_id: str) -> dict:
    """
    Verify that graph structure exists for an app before cleaning JSON.

    Args:
        driver: Neo4j driver
        app_id: Application ID

    Returns:
        Dict with entity and attribute counts
    """
    async with driver.session() as session:
        result = await session.run("""
            MATCH (dm:DomainModelIR {app_id: $app_id})-[:HAS_ENTITY]->(e:Entity)
            RETURN count(e) as entity_count
        """, app_id=app_id)
        record = await result.single()
        entity_count = record["entity_count"] if record else 0

        result = await session.run("""
            MATCH (e:Entity {app_id: $app_id})-[:HAS_ATTRIBUTE]->(a:Attribute)
            RETURN count(a) as attribute_count
        """, app_id=app_id)
        record = await result.single()
        attribute_count = record["attribute_count"] if record else 0

        return {
            "entities": entity_count,
            "attributes": attribute_count
        }


def confirm_cleanup():
    """
    Ask user to confirm cleanup operation.

    Returns:
        True if user confirms, False otherwise
    """
    print("\n⚠️  WARNING: This will permanently remove entities JSON from DomainModelIR nodes")
    print("   This operation CANNOT be undone!")
    print()
    print("   Before proceeding, ensure you have:")
    print("   1. ✅ Verified migration completed successfully")
    print("   2. ✅ Tested that Entity/Attribute nodes are accessible")
    print("   3. ✅ Confirmed relationships are correct")
    print("   4. ✅ Backed up your database (if needed)")
    print()

    response = input("Type 'YES' to proceed with cleanup: ")
    return response.strip() == "YES"


async def run_cleanup():
    """
    Main cleanup logic.

    Process:
    1. Connect to Neo4j
    2. Get all migrated DomainModelIR nodes with JSON
    3. Verify graph structure exists
    4. Remove entities JSON property
    5. Report results
    """
    mode_str = "DRY RUN" if DRY_RUN else "JSON CLEANUP"
    print(f"🧹 Starting Domain Model {mode_str}...")
    print(f"📊 Configuration:")
    print(f"   Neo4j: {NEO4J_URI}")
    print(f"   Mode: {'DRY RUN' if DRY_RUN else 'LIVE CLEANUP'}")
    print()

    # Require confirmation in live mode
    if not DRY_RUN and REQUIRE_CONFIRMATION:
        if not confirm_cleanup():
            print("\n❌ Cleanup cancelled by user")
            return

    driver = AsyncGraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD)
    )

    try:
        # Get migrated domain models with JSON
        print("\n🔍 Fetching migrated DomainModelIR nodes with JSON...")
        app_ids = await get_migrated_with_json(driver)
        print(f"📝 Found {len(app_ids)} nodes to clean")

        if not app_ids:
            print("✅ No JSON to clean - all nodes already cleaned or not migrated!")
            return

        print()

        # Statistics
        successful = 0
        failed = 0
        skipped_no_graph = 0

        # Process each domain model
        for i, app_id in enumerate(app_ids, 1):
            try:
                # Verify graph structure exists
                graph_stats = await verify_graph_structure(driver, app_id)

                if graph_stats["entities"] == 0:
                    skipped_no_graph += 1
                    print(f"⚠️  [{i}/{len(app_ids)}] {app_id} - SKIPPED (no graph structure found)")
                    continue

                # Remove JSON property
                removed = await remove_entities_json(driver, app_id, dry_run=DRY_RUN)

                if removed:
                    successful += 1
                    if i % 50 == 0 or i == len(app_ids):
                        print(f"✅ [{i}/{len(app_ids)}] {app_id}")
                        print(f"   Graph has {graph_stats['entities']} entities, "
                              f"{graph_stats['attributes']} attributes")
                else:
                    failed += 1

            except Exception as e:
                failed += 1
                print(f"❌ Error processing {app_id}: {e}")
                continue

        # Final report
        print("\n" + "=" * 60)
        print(f"📊 {mode_str} COMPLETE")
        print("=" * 60)
        print(f"Domain models processed: {len(app_ids)}")
        print(f"✅ JSON removed: {successful}")
        print(f"⚠️  Skipped (no graph): {skipped_no_graph}")
        print(f"❌ Failed: {failed}")
        print("=" * 60)

        if DRY_RUN:
            print("\n💡 This was a DRY RUN - no changes were made")
            print("   Run without DRY_RUN=true to apply cleanup")
        else:
            print("\n✅ Cleanup complete!")
            print("   Entities JSON properties have been removed")
            print("   Graph structure is now the primary storage")

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        await driver.close()
        print("\n🔌 Connection closed")


if __name__ == "__main__":
    asyncio.run(run_cleanup())
