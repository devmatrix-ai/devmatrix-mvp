#!/usr/bin/env python3
"""
Sprint 1 Task 1.3: Domain Model Expansion Migration

Migrates DomainModelIR nodes from JSON string storage to proper graph structure:
- Creates Entity nodes with HAS_ENTITY relationships
- Creates Attribute nodes with HAS_ATTRIBUTE relationships
- Creates RELATES_TO relationships between entities

This script:
1. Queries all DomainModelIR nodes with entities JSON property
2. Parses JSON and creates graph nodes for entities and attributes
3. Establishes proper relationships between nodes
4. Keeps original JSON for rollback capability
5. Provides verification and dry-run modes

The script is idempotent - it uses MERGE to avoid duplicates and can be run multiple times safely.
"""
import asyncio
import json
import os
import sys
from typing import List, Dict, Any, Optional
from neo4j import AsyncGraphDatabase

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.cognitive.ir.domain_model import (
    DomainModelIR,
    Entity,
    Attribute,
    Relationship,
    DataType,
    RelationshipType
)

# Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "devmatrix123")

# Progress reporting interval
PROGRESS_INTERVAL = 50

# Dry run mode
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"


async def get_domain_models_with_json(driver) -> List[Dict[str, Any]]:
    """
    Retrieve all DomainModelIR nodes that have entities as JSON property.

    Returns:
        List of records with app_id and entities JSON string
    """
    async with driver.session() as session:
        result = await session.run("""
            MATCH (dm:DomainModelIR)
            WHERE dm.entities IS NOT NULL
              AND dm.entities <> ''
              AND dm.app_id IS NOT NULL
            RETURN dm.app_id as app_id,
                   dm.entities as entities_json,
                   dm.metadata as metadata
            ORDER BY dm.app_id
        """)
        records = [
            {
                "app_id": record["app_id"],
                "entities_json": record["entities_json"],
                "metadata": record["metadata"]
            }
            async for record in result
        ]
        return records


async def create_entity_node(
    session,
    app_id: str,
    entity: Entity
) -> None:
    """
    Create or update an Entity node and link it to DomainModelIR.

    Args:
        session: Neo4j session
        app_id: Application ID
        entity: Entity object from IR
    """
    entity_id = f"{app_id}_{entity.name}"

    await session.run("""
        MATCH (dm:DomainModelIR {app_id: $app_id})
        MERGE (e:Entity {entity_id: $entity_id})
        SET e.name = $name,
            e.description = $description,
            e.is_aggregate_root = $is_aggregate_root,
            e.app_id = $app_id
        MERGE (dm)-[:HAS_ENTITY]->(e)
    """,
        app_id=app_id,
        entity_id=entity_id,
        name=entity.name,
        description=entity.description,
        is_aggregate_root=entity.is_aggregate_root
    )


async def create_attribute_node(
    session,
    app_id: str,
    entity_name: str,
    attribute: Attribute
) -> None:
    """
    Create or update an Attribute node and link it to Entity.

    Args:
        session: Neo4j session
        app_id: Application ID
        entity_name: Parent entity name
        attribute: Attribute object from IR
    """
    entity_id = f"{app_id}_{entity_name}"
    attr_id = f"{entity_id}_{attribute.name}"

    await session.run("""
        MATCH (e:Entity {entity_id: $entity_id})
        MERGE (a:Attribute {attribute_id: $attr_id})
        SET a.name = $name,
            a.data_type = $data_type,
            a.is_primary_key = $is_primary_key,
            a.is_nullable = $is_nullable,
            a.is_unique = $is_unique,
            a.default_value = $default_value,
            a.description = $description,
            a.constraints = $constraints,
            a.entity_id = $entity_id,
            a.app_id = $app_id
        MERGE (e)-[:HAS_ATTRIBUTE]->(a)
    """,
        entity_id=entity_id,
        attr_id=attr_id,
        name=attribute.name,
        data_type=attribute.data_type.value,
        is_primary_key=attribute.is_primary_key,
        is_nullable=attribute.is_nullable,
        is_unique=attribute.is_unique,
        default_value=attribute.default_value,
        description=attribute.description,
        constraints=json.dumps(attribute.constraints)
    )


async def create_relationship_edge(
    session,
    app_id: str,
    relationship: Relationship
) -> None:
    """
    Create RELATES_TO relationship between two entities.

    Args:
        session: Neo4j session
        app_id: Application ID
        relationship: Relationship object from IR
    """
    source_id = f"{app_id}_{relationship.source_entity}"
    target_id = f"{app_id}_{relationship.target_entity}"

    await session.run("""
        MATCH (source:Entity {entity_id: $source_id})
        MATCH (target:Entity {entity_id: $target_id})
        MERGE (source)-[r:RELATES_TO {field_name: $field_name}]->(target)
        SET r.type = $rel_type,
            r.back_populates = $back_populates
    """,
        source_id=source_id,
        target_id=target_id,
        field_name=relationship.field_name,
        rel_type=relationship.type.value,
        back_populates=relationship.back_populates
    )


async def migrate_domain_model(
    driver,
    app_id: str,
    entities_json: str,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Migrate a single DomainModelIR from JSON to graph nodes.

    Args:
        driver: Neo4j driver
        app_id: Application ID
        entities_json: JSON string containing entities
        dry_run: If True, only parse and validate without writing

    Returns:
        Statistics dict with counts of created nodes/relationships
    """
    stats = {
        "entities": 0,
        "attributes": 0,
        "relationships": 0
    }

    try:
        # Parse JSON to DomainModelIR
        entities_data = json.loads(entities_json)
        domain_model = DomainModelIR(entities=entities_data)

        if dry_run:
            # Just count what would be created
            stats["entities"] = len(domain_model.entities)
            for entity in domain_model.entities:
                stats["attributes"] += len(entity.attributes)
                stats["relationships"] += len(entity.relationships)
            return stats

        # Create nodes and relationships
        async with driver.session() as session:
            # Create Entity nodes
            for entity in domain_model.entities:
                await create_entity_node(session, app_id, entity)
                stats["entities"] += 1

                # Create Attribute nodes for this entity
                for attribute in entity.attributes:
                    await create_attribute_node(session, app_id, entity.name, attribute)
                    stats["attributes"] += 1

                # Create relationships from this entity
                for relationship in entity.relationships:
                    await create_relationship_edge(session, app_id, relationship)
                    stats["relationships"] += 1

        return stats

    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON for {app_id}: {e}")
        return stats
    except Exception as e:
        print(f"❌ Error migrating {app_id}: {e}")
        import traceback
        traceback.print_exc()
        return stats


async def verify_migration(driver) -> Dict[str, int]:
    """
    Verify the migration by counting created nodes and relationships.

    Returns:
        Dict with verification counts
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
        relationship_count = record["count"] if record else 0

        # Count HAS_ENTITY relationships
        result = await session.run("MATCH ()-[r:HAS_ENTITY]->() RETURN count(r) as count")
        record = await result.single()
        has_entity_count = record["count"] if record else 0

        # Count HAS_ATTRIBUTE relationships
        result = await session.run("MATCH ()-[r:HAS_ATTRIBUTE]->() RETURN count(r) as count")
        record = await result.single()
        has_attribute_count = record["count"] if record else 0

        return {
            "entities": entity_count,
            "attributes": attribute_count,
            "relates_to": relationship_count,
            "has_entity": has_entity_count,
            "has_attribute": has_attribute_count
        }


async def mark_migration_complete(driver, app_id: str) -> None:
    """
    Mark a DomainModelIR as migrated by setting a flag.

    Args:
        driver: Neo4j driver
        app_id: Application ID
    """
    async with driver.session() as session:
        await session.run("""
            MATCH (dm:DomainModelIR {app_id: $app_id})
            SET dm.migrated_to_graph = true,
                dm.migration_timestamp = datetime()
        """, app_id=app_id)


async def run_migration():
    """
    Main migration logic.

    Process:
    1. Connect to Neo4j
    2. Get all DomainModelIR nodes with JSON entities
    3. For each, parse JSON and create graph structure
    4. Report progress every PROGRESS_INTERVAL records
    5. Verify migration with counts
    """
    mode_str = "DRY RUN" if DRY_RUN else "MIGRATION"
    print(f"🚀 Starting Domain Model {mode_str}...")
    print(f"📊 Configuration:")
    print(f"   Neo4j: {NEO4J_URI}")
    print(f"   Mode: {'DRY RUN' if DRY_RUN else 'LIVE MIGRATION'}")
    print(f"   Progress interval: {PROGRESS_INTERVAL}")
    print()

    driver = AsyncGraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD)
    )

    try:
        # Get DomainModelIR nodes with JSON
        print("🔍 Fetching DomainModelIR nodes with JSON entities...")
        domain_models = await get_domain_models_with_json(driver)
        print(f"📝 Found {len(domain_models)} DomainModelIR nodes to migrate")

        if not domain_models:
            print("✅ No domain models to process!")
            return

        print()

        # Statistics
        total_stats = {
            "entities": 0,
            "attributes": 0,
            "relationships": 0
        }
        successful = 0
        failed = 0

        # Process each domain model
        for i, record in enumerate(domain_models, 1):
            app_id = record["app_id"]
            entities_json = record["entities_json"]

            try:
                # Migrate this domain model
                stats = await migrate_domain_model(
                    driver,
                    app_id,
                    entities_json,
                    dry_run=DRY_RUN
                )

                # Update totals
                total_stats["entities"] += stats["entities"]
                total_stats["attributes"] += stats["attributes"]
                total_stats["relationships"] += stats["relationships"]
                successful += 1

                # Mark as migrated (only in live mode)
                if not DRY_RUN:
                    await mark_migration_complete(driver, app_id)

                # Progress report
                if i % PROGRESS_INTERVAL == 0 or i == len(domain_models):
                    print(f"✅ [{i}/{len(domain_models)}] {app_id}")
                    print(f"   Entities: {stats['entities']}, "
                          f"Attributes: {stats['attributes']}, "
                          f"Relationships: {stats['relationships']}")

                # Summary progress
                if i % PROGRESS_INTERVAL == 0:
                    print(f"\n📊 Progress: {i}/{len(domain_models)}")
                    print(f"   ✅ Successful: {successful}")
                    print(f"   ❌ Failed: {failed}")
                    print(f"   Total created:")
                    print(f"      Entities: {total_stats['entities']}")
                    print(f"      Attributes: {total_stats['attributes']}")
                    print(f"      Relationships: {total_stats['relationships']}")
                    print()

            except Exception as e:
                failed += 1
                print(f"❌ Error processing {app_id}: {e}")
                continue

        # Verification
        print("\n🔍 Verifying migration...")
        verification = await verify_migration(driver)

        # Final report
        print("\n" + "=" * 60)
        print(f"📊 {mode_str} COMPLETE")
        print("=" * 60)
        print(f"Domain models processed: {len(domain_models)}")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print()
        print("Migration Statistics:")
        print(f"   Entities created: {total_stats['entities']}")
        print(f"   Attributes created: {total_stats['attributes']}")
        print(f"   Relationships created: {total_stats['relationships']}")
        print()
        print("Verification Counts:")
        print(f"   Entity nodes: {verification['entities']}")
        print(f"   Attribute nodes: {verification['attributes']}")
        print(f"   RELATES_TO edges: {verification['relates_to']}")
        print(f"   HAS_ENTITY edges: {verification['has_entity']}")
        print(f"   HAS_ATTRIBUTE edges: {verification['has_attribute']}")
        print("=" * 60)

        if DRY_RUN:
            print("\n💡 This was a DRY RUN - no changes were made")
            print("   Run without DRY_RUN=true to apply migration")
        else:
            print("\n💡 Next steps:")
            print("   1. Verify graph structure in Neo4j Browser")
            print("   2. Check Entity and Attribute nodes")
            print("   3. Review relationships between entities")
            print("   4. If satisfied, you can remove entities JSON with:")
            print("      scripts/migrations/neo4j/003_cleanup_json.py")
            print("   5. If issues found, rollback with:")
            print("      scripts/migrations/neo4j/003_domain_model_expansion_rollback.py")

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        await driver.close()
        print("\n🔌 Connection closed")


if __name__ == "__main__":
    asyncio.run(run_migration())
