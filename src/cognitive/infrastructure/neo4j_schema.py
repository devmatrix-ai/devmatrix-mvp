"""
Neo4j Schema Setup for Cognitive Architecture

Extends existing Neo4j schema (30K+ Pattern nodes) with new node types
and relationships for cognitive architecture DAG construction.

Existing Schema (DO NOT MODIFY):
- Pattern nodes (30,071)
- Dependency relationships (84)
- Tag, Category, Framework, Repository nodes

New Schema (Task 0.3.3):
- AtomicTask node type for generated tasks
- DEPENDS_ON relationship for task dependencies
- Constraints for AtomicTask uniqueness
"""

from typing import Dict, Any
import logging
from neo4j import GraphDatabase

from src.cognitive.config.settings import settings

logger = logging.getLogger(__name__)


class Neo4jSchemaSetup:
    """Setup Neo4j schema for cognitive architecture."""

    def __init__(self):
        """Initialize Neo4j schema setup."""
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )

    def close(self):
        """Close Neo4j driver."""
        self.driver.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def create_atomic_task_constraints(self) -> None:
        """
        Create uniqueness constraint for AtomicTask nodes.

        Ensures task_id is unique across all AtomicTask nodes.
        """
        with self.driver.session(database=settings.neo4j_database) as session:
            # Create unique constraint on task_id
            try:
                session.run("""
                    CREATE CONSTRAINT atomic_task_unique_id IF NOT EXISTS
                    FOR (t:AtomicTask) REQUIRE t.task_id IS UNIQUE
                """)
                logger.info("Created AtomicTask unique constraint on task_id")
            except Exception as e:
                logger.warning(f"Constraint creation skipped (may already exist): {e}")

    def create_indexes(self) -> None:
        """
        Create indexes for efficient querying.

        Indexes:
        - AtomicTask.status for filtering by status
        - AtomicTask.created_at for time-based queries
        """
        with self.driver.session(database=settings.neo4j_database) as session:
            # Index on status
            try:
                session.run("""
                    CREATE INDEX atomic_task_status_idx IF NOT EXISTS
                    FOR (t:AtomicTask) ON (t.status)
                """)
                logger.info("Created index on AtomicTask.status")
            except Exception as e:
                logger.warning(f"Index creation skipped: {e}")

            # Index on created_at
            try:
                session.run("""
                    CREATE INDEX atomic_task_created_at_idx IF NOT EXISTS
                    FOR (t:AtomicTask) ON (t.created_at)
                """)
                logger.info("Created index on AtomicTask.created_at")
            except Exception as e:
                logger.warning(f"Index creation skipped: {e}")

    def verify_existing_schema(self) -> Dict[str, Any]:
        """
        Verify existing Pattern nodes are intact.

        Returns:
            Dictionary with counts of existing nodes
        """
        with self.driver.session(database=settings.neo4j_database) as session:
            # Count Pattern nodes
            result = session.run("MATCH (p:Pattern) RETURN count(p) AS count")
            pattern_count = result.single()["count"]

            # Count Dependency relationships
            result = session.run("MATCH ()-[r:DEPENDS_ON]->() RETURN count(r) AS count")
            dep_count = result.single()["count"]

            # Count Category nodes
            result = session.run("MATCH (c:Category) RETURN count(c) AS count")
            category_count = result.single()["count"]

            stats = {
                "pattern_nodes": pattern_count,
                "dependency_relationships": dep_count,
                "category_nodes": category_count
            }

            logger.info(f"Existing schema verified: {stats}")
            return stats

    def setup_schema(self) -> None:
        """
        Complete schema setup for cognitive architecture.

        Steps:
        1. Verify existing schema (30K+ Pattern nodes)
        2. Create AtomicTask constraints
        3. Create indexes
        """
        logger.info("Starting Neo4j schema setup for cognitive architecture")

        # Verify existing schema intact
        existing_stats = self.verify_existing_schema()
        if existing_stats["pattern_nodes"] < 1000:
            logger.warning(f"Expected 30K+ Pattern nodes, found {existing_stats['pattern_nodes']}")

        # Create new schema elements
        self.create_atomic_task_constraints()
        self.create_indexes()

        logger.info("Neo4j schema setup complete")

    def rollback_schema(self) -> None:
        """
        Rollback cognitive architecture schema changes.

        WARNING: Only removes AtomicTask nodes and constraints.
        Does NOT touch existing Pattern nodes (30K+).
        """
        with self.driver.session(database=settings.neo4j_database) as session:
            # Drop constraints
            try:
                session.run("DROP CONSTRAINT atomic_task_unique_id IF EXISTS")
                logger.info("Dropped AtomicTask constraint")
            except Exception as e:
                logger.warning(f"Constraint drop failed: {e}")

            # Drop indexes
            try:
                session.run("DROP INDEX atomic_task_status_idx IF EXISTS")
                session.run("DROP INDEX atomic_task_created_at_idx IF EXISTS")
                logger.info("Dropped AtomicTask indexes")
            except Exception as e:
                logger.warning(f"Index drop failed: {e}")

            # Delete all AtomicTask nodes (but NOT Pattern nodes)
            result = session.run("MATCH (t:AtomicTask) DETACH DELETE t RETURN count(t) AS deleted")
            deleted_count = result.single()["deleted"]
            logger.info(f"Deleted {deleted_count} AtomicTask nodes")

        logger.info("Schema rollback complete")


def main():
    """
    CLI entry point for Neo4j schema setup.

    Usage:
        python -m src.cognitive.infrastructure.neo4j_schema
    """
    import sys

    with Neo4jSchemaSetup() as setup:
        if len(sys.argv) > 1 and sys.argv[1] == "rollback":
            setup.rollback_schema()
        else:
            setup.setup_schema()


if __name__ == "__main__":
    main()
