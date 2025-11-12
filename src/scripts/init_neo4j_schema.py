"""
Initialize complete Neo4j 5.26 schema for DevMatrix V2.1

This script creates:
- 11 Uniqueness Constraints (node ID constraints)
- 8 Range Indexes (single property indexes)
- 4 Composite Indexes (multi-property indexes)
- 3 Full-Text Indexes (text search indexes)

Run this ONCE during initial setup, or when schema needs rebuilding.
"""

import asyncio
import logging
import sys
from datetime import datetime

# Assume Neo4jClient is importable
try:
    from src.neo4j_client import Neo4jClient
except ImportError:
    print("Error: Cannot import Neo4jClient. Make sure src/neo4j_client.py exists.")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# UNIQUENESS CONSTRAINTS (11 total)
# ============================================================================
UNIQUENESS_CONSTRAINTS = [
    ("Template", "id", "template_id_unique"),
    ("TrezoComponent", "id", "trezo_component_id_unique"),
    ("CustomComponent", "id", "custom_component_id_unique"),
    ("Pattern", "id", "pattern_id_unique"),
    ("Framework", "id", "framework_id_unique"),
    ("Dependency", "id", "dependency_id_unique"),
    ("Category", "id", "category_id_unique"),
    ("MasterPlan", "id", "masterplan_id_unique"),
    ("Atom", "id", "atom_id_unique"),
    ("User", "id", "user_id_unique"),
    ("Project", "id", "project_id_unique"),
]

# ============================================================================
# RANGE INDEXES (8 total)
# ============================================================================
RANGE_INDEXES = [
    ("Template", "precision", "template_precision"),
    ("Template", "created_at", "template_created_at"),
    ("Template", "category", "template_category"),
    ("Template", "framework", "template_framework"),
    ("Template", "status", "template_status"),
    ("TrezoComponent", "precision", "trezo_component_precision"),
    ("Atom", "precision", "atom_precision"),
    ("Atom", "status", "atom_status"),
]

# ============================================================================
# COMPOSITE INDEXES (4 total)
# ============================================================================
COMPOSITE_INDEXES = [
    ("Template", ["category", "framework"], "template_category_framework"),
    ("Template", ["category", "precision"], "template_category_precision"),
    ("Template", ["framework", "status"], "template_framework_status"),
    ("Atom", ["masterplan_id", "status"], "atom_masterplan_status"),
]

# ============================================================================
# FULL-TEXT INDEXES (3 total)
# ============================================================================
FULLTEXT_INDEXES = [
    ("template_name_description", "Template", ["name", "description"]),
    ("trezo_component_name", "TrezoComponent", ["name"]),
    ("pattern_name_description", "Pattern", ["name", "description"]),
]


async def create_uniqueness_constraints(client: Neo4jClient) -> dict:
    """Create all uniqueness constraints."""
    logger.info("Creating uniqueness constraints...")
    results = {}

    async with client.driver.session() as session:
        for label, property_name, constraint_name in UNIQUENESS_CONSTRAINTS:
            try:
                query = f"""
                CREATE CONSTRAINT {constraint_name} IF NOT EXISTS
                FOR (n:{label}) REQUIRE n.{property_name} IS UNIQUE
                """
                await session.run(query)
                results[constraint_name] = True
                logger.info(f"✅ Created constraint: {constraint_name}")
            except Exception as e:
                logger.error(f"❌ Failed to create constraint {constraint_name}: {e}")
                results[constraint_name] = False

    return results


async def create_range_indexes(client: Neo4jClient) -> dict:
    """Create all range indexes."""
    logger.info("Creating range indexes...")
    results = {}

    async with client.driver.session() as session:
        for label, property_name, index_name in RANGE_INDEXES:
            try:
                query = f"""
                CREATE INDEX {index_name} IF NOT EXISTS
                FOR (n:{label}) ON (n.{property_name})
                """
                await session.run(query)
                results[index_name] = True
                logger.info(f"✅ Created range index: {index_name}")
            except Exception as e:
                logger.error(f"❌ Failed to create range index {index_name}: {e}")
                results[index_name] = False

    return results


async def create_composite_indexes(client: Neo4jClient) -> dict:
    """Create all composite indexes."""
    logger.info("Creating composite indexes...")
    results = {}

    async with client.driver.session() as session:
        for label, properties, index_name in COMPOSITE_INDEXES:
            try:
                props_str = ", ".join([f"n.{p}" for p in properties])
                query = f"""
                CREATE INDEX {index_name} IF NOT EXISTS
                FOR (n:{label}) ON ({props_str})
                """
                await session.run(query)
                results[index_name] = True
                logger.info(f"✅ Created composite index: {index_name}")
            except Exception as e:
                logger.error(f"❌ Failed to create composite index {index_name}: {e}")
                results[index_name] = False

    return results


async def create_fulltext_indexes(client: Neo4jClient) -> dict:
    """Create all full-text indexes."""
    logger.info("Creating full-text indexes...")
    results = {}

    async with client.driver.session() as session:
        for index_name, label, properties in FULLTEXT_INDEXES:
            try:
                props_str = ", ".join([f"{label}.{p}" for p in properties])
                query = f"""
                CREATE FULLTEXT INDEX {index_name} IF NOT EXISTS
                FOR ({label}:{label})
                ON EACH [{props_str}]
                """
                await session.run(query)
                results[index_name] = True
                logger.info(f"✅ Created full-text index: {index_name}")
            except Exception as e:
                logger.error(f"❌ Failed to create full-text index {index_name}: {e}")
                results[index_name] = False

    return results


async def verify_schema(client: Neo4jClient) -> dict:
    """Verify all constraints and indexes were created."""
    logger.info("\nVerifying schema...")
    stats = {}

    async with client.driver.session() as session:
        # Count constraints
        constraints_result = await session.run("SHOW CONSTRAINTS")
        constraints = [record async for record in constraints_result]
        stats["constraints_count"] = len(constraints)
        logger.info(f"Found {len(constraints)} constraints")

        # Count indexes
        indexes_result = await session.run("SHOW INDEXES")
        indexes = [record async for record in indexes_result]
        stats["indexes_count"] = len(indexes)
        logger.info(f"Found {len(indexes)} indexes")

        # Get database statistics
        try:
            stats_result = await session.run(
                "CALL apoc.meta.stats() YIELD nodeCount, relCount"
            )
            stats_record = await stats_result.single()
            if stats_record:
                stats["node_count"] = stats_record["nodeCount"]
                stats["relationship_count"] = stats_record["relCount"]
                logger.info(f"Database has {stats['node_count']} nodes, "
                           f"{stats['relationship_count']} relationships")
        except Exception as e:
            logger.warning(f"Could not get detailed stats: {e}")

    return stats


async def main():
    """Main execution."""
    logger.info("=" * 70)
    logger.info("Neo4j Schema Initialization - DevMatrix V2.1")
    logger.info("=" * 70)
    logger.info(f"Start time: {datetime.now().isoformat()}")

    # Initialize client
    client = Neo4jClient(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="devmatrix123"
    )

    # Connect to database
    logger.info("\nConnecting to Neo4j...")
    connected = await client.connect()
    if not connected:
        logger.error("Failed to connect to Neo4j. Exiting.")
        return False

    logger.info("✅ Connected to Neo4j successfully")

    try:
        # Create constraints
        constraint_results = await create_uniqueness_constraints(client)
        successful_constraints = sum(1 for v in constraint_results.values() if v)
        logger.info(f"\nConstraints: {successful_constraints}/{len(constraint_results)} created")

        # Create range indexes
        range_results = await create_range_indexes(client)
        successful_range = sum(1 for v in range_results.values() if v)
        logger.info(f"Range indexes: {successful_range}/{len(range_results)} created")

        # Create composite indexes
        composite_results = await create_composite_indexes(client)
        successful_composite = sum(1 for v in composite_results.values() if v)
        logger.info(f"Composite indexes: {successful_composite}/{len(composite_results)} created")

        # Create full-text indexes
        fulltext_results = await create_fulltext_indexes(client)
        successful_fulltext = sum(1 for v in fulltext_results.values() if v)
        logger.info(f"Full-text indexes: {successful_fulltext}/{len(fulltext_results)} created")

        # Verify schema
        stats = await verify_schema(client)

        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("SCHEMA INITIALIZATION SUMMARY")
        logger.info("=" * 70)
        logger.info(f"✅ Uniqueness Constraints: {successful_constraints}/{len(constraint_results)}")
        logger.info(f"✅ Range Indexes: {successful_range}/{len(range_results)}")
        logger.info(f"✅ Composite Indexes: {successful_composite}/{len(composite_results)}")
        logger.info(f"✅ Full-Text Indexes: {successful_fulltext}/{len(fulltext_results)}")
        logger.info(f"✅ Total Constraints & Indexes: "
                   f"{successful_constraints + successful_range + successful_composite + successful_fulltext}/"
                   f"{len(constraint_results) + len(range_results) + len(composite_results) + len(fulltext_results)}")
        logger.info(f"\nDatabase Statistics:")
        logger.info(f"  - Nodes: {stats.get('node_count', 0)}")
        logger.info(f"  - Relationships: {stats.get('relationship_count', 0)}")
        logger.info(f"\n✅ Schema initialization COMPLETE")
        logger.info(f"End time: {datetime.now().isoformat()}")
        logger.info("=" * 70)

        # Check if all successful
        all_successful = (
            successful_constraints == len(constraint_results)
            and successful_range == len(range_results)
            and successful_composite == len(composite_results)
            and successful_fulltext == len(fulltext_results)
        )

        return all_successful

    finally:
        await client.close()


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
