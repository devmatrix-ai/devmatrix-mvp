"""
Graph IR Repository Base Class
-------------------------------
Template Method pattern base class for all IR graph repositories.

Provides common functionality for:
- Neo4j driver management with context manager pattern
- Temporal metadata tracking (created_at, updated_at)
- Subgraph replacement with cascade delete for safe updates
- Batch node and relationship creation for performance
- Transaction management and error handling

Design Goals:
1. DRY: Eliminate 60-80% code duplication across repositories
2. Consistency: Standardize temporal metadata and update patterns
3. Safety: Atomic transactions with rollback capability
4. Performance: Batch operations with UNWIND for large datasets

Usage Example:
    class DomainModelGraphRepository(GraphIRRepository):
        def save_domain_model(self, app_id, domain_model):
            with self.driver.session() as session:
                # Use inherited batch methods
                self.batch_create_nodes(
                    session, "Entity",
                    [self._add_temporal_metadata(e.dict()) for e in domain_model.entities]
                )
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging

from neo4j import GraphDatabase, Transaction, Session

from src.cognitive.config.settings import settings

logger = logging.getLogger(__name__)


class GraphIRPersistenceError(RuntimeError):
    """Base exception for graph IR persistence operations."""


class GraphIRRepository:
    """
    Base class for all IR graph repositories.

    Implements Template Method pattern to provide common operations
    while allowing subclasses to specialize domain-specific logic.

    Common Patterns:
    - Driver lifecycle management
    - Temporal metadata tracking
    - Batch operations for performance
    - Subgraph replacement for safe updates
    - Transaction management
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ) -> None:
        """
        Initialize repository with Neo4j driver.

        Args:
            uri: Neo4j connection URI (defaults to settings)
            user: Neo4j username (defaults to settings)
            password: Neo4j password (defaults to settings)
            database: Neo4j database name (defaults to settings)
        """
        self.uri = uri or settings.neo4j_uri
        self.user = user or settings.neo4j_user
        self.password = password or settings.neo4j_password
        self.database = database or settings.neo4j_database

        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password),
        )
        logger.info(
            "%s initialized with URI %s, database %s",
            self.__class__.__name__,
            self.uri,
            self.database,
        )

    def close(self) -> None:
        """Close Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            logger.info("%s connection closed", self.__class__.__name__)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with automatic cleanup."""
        self.close()

    # ============================================================================
    # TEMPORAL METADATA MANAGEMENT
    # ============================================================================

    @staticmethod
    def _add_temporal_metadata(properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add temporal metadata to node properties.

        Adds:
        - created_at: ISO 8601 datetime string
        - updated_at: ISO 8601 datetime string (same as created_at initially)

        Args:
            properties: Dictionary of node properties

        Returns:
            Dictionary with temporal metadata added

        Example:
            >>> props = {"name": "Product", "type": "Entity"}
            >>> enhanced = GraphIRRepository._add_temporal_metadata(props)
            >>> "created_at" in enhanced
            True
            >>> "updated_at" in enhanced
            True
        """
        now = datetime.utcnow().isoformat() + "Z"

        result = properties.copy()
        result["created_at"] = now
        result["updated_at"] = now

        return result

    @staticmethod
    def _update_temporal_metadata(properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update temporal metadata for existing node.

        Updates:
        - updated_at: Current ISO 8601 datetime string

        Does NOT modify:
        - created_at: Preserves original creation timestamp

        Args:
            properties: Dictionary of node properties

        Returns:
            Dictionary with updated_at refreshed
        """
        now = datetime.utcnow().isoformat() + "Z"

        result = properties.copy()
        result["updated_at"] = now

        return result

    # ============================================================================
    # BATCH OPERATIONS
    # ============================================================================

    def batch_create_nodes(
        self,
        session: Session,
        label: str,
        properties_list: List[Dict[str, Any]],
        batch_size: int = 500,
    ) -> int:
        """
        Create multiple nodes in batches using UNWIND for performance.

        Uses Neo4j UNWIND pattern for efficient bulk creation:
        - Reduces roundtrips to database
        - Optimized for Neo4j query planner
        - Configurable batch size for memory management

        Args:
            session: Neo4j session
            label: Node label (e.g., "Entity", "Endpoint")
            properties_list: List of property dictionaries
            batch_size: Number of nodes per batch (default 500)

        Returns:
            Total number of nodes created

        Example:
            >>> entities = [{"name": "Product"}, {"name": "Order"}]
            >>> count = repo.batch_create_nodes(session, "Entity", entities)
            >>> count
            2
        """
        if not properties_list:
            return 0

        total_created = 0

        # Process in batches to avoid memory issues
        for i in range(0, len(properties_list), batch_size):
            batch = properties_list[i : i + batch_size]

            query = f"""
            UNWIND $props as properties
            CREATE (n:{label})
            SET n = properties
            RETURN count(n) as created
            """

            result = session.run(query, props=batch)
            record = result.single()
            batch_created = record["created"] if record else 0
            total_created += batch_created

            logger.debug(
                "Batch created %d %s nodes (batch %d/%d)",
                batch_created,
                label,
                i // batch_size + 1,
                (len(properties_list) + batch_size - 1) // batch_size,
            )

        logger.info("Batch created %d %s nodes total", total_created, label)
        return total_created

    def batch_create_relationships(
        self,
        session: Session,
        rel_type: str,
        source_target_pairs: List[Tuple[str, str]],
        source_label: str,
        target_label: str,
        source_key: str = "id",
        target_key: str = "id",
        rel_properties: Optional[Dict[str, Any]] = None,
        batch_size: int = 500,
    ) -> int:
        """
        Create multiple relationships in batches using UNWIND.

        Args:
            session: Neo4j session
            rel_type: Relationship type (e.g., "HAS_ENTITY", "TARGETS_ENTITY")
            source_target_pairs: List of (source_id, target_id) tuples
            source_label: Label of source nodes
            target_label: Label of target nodes
            source_key: Property name for source node matching (default "id")
            target_key: Property name for target node matching (default "id")
            rel_properties: Optional properties to set on all relationships
            batch_size: Number of relationships per batch (default 500)

        Returns:
            Total number of relationships created

        Example:
            >>> pairs = [("app123", "entity1"), ("app123", "entity2")]
            >>> count = repo.batch_create_relationships(
            ...     session, "HAS_ENTITY", pairs, "DomainModelIR", "Entity"
            ... )
            >>> count
            2
        """
        if not source_target_pairs:
            return 0

        total_created = 0
        rel_props_str = ""

        if rel_properties:
            # Build SET clause for relationship properties
            props_items = ", ".join(
                f"r.{key} = ${key}" for key in rel_properties.keys()
            )
            rel_props_str = f"SET {props_items}"

        # Process in batches
        for i in range(0, len(source_target_pairs), batch_size):
            batch = source_target_pairs[i : i + batch_size]

            query = f"""
            UNWIND $pairs as pair
            MATCH (source:{source_label} {{{source_key}: pair.source}})
            MATCH (target:{target_label} {{{target_key}: pair.target}})
            CREATE (source)-[r:{rel_type}]->(target)
            {rel_props_str}
            RETURN count(r) as created
            """

            # Prepare batch data
            batch_data = [
                {"source": source, "target": target} for source, target in batch
            ]

            params = {"pairs": batch_data}
            if rel_properties:
                params.update(rel_properties)

            result = session.run(query, **params)
            record = result.single()
            batch_created = record["created"] if record else 0
            total_created += batch_created

            logger.debug(
                "Batch created %d %s relationships (batch %d/%d)",
                batch_created,
                rel_type,
                i // batch_size + 1,
                (len(source_target_pairs) + batch_size - 1) // batch_size,
            )

        logger.info("Batch created %d %s relationships total", total_created, rel_type)
        return total_created

    # ============================================================================
    # SUBGRAPH REPLACEMENT PATTERN
    # ============================================================================

    def replace_subgraph(
        self,
        session: Session,
        root_label: str,
        root_id: str,
        root_key: str = "app_id",
        child_relationships: Optional[List[str]] = None,
    ) -> Dict[str, int]:
        """
        Delete existing subgraph rooted at a node (cascade delete children).

        Use Case: Safe updates by deleting old structure before creating new.

        Pattern:
        1. MATCH root node by ID
        2. OPTIONALLY MATCH all children via specified relationships
        3. DELETE children first (cascade)
        4. Keep root node (will be updated separately)

        Args:
            session: Neo4j session
            root_label: Label of root node (e.g., "DomainModelIR", "APIModelIR")
            root_id: ID value of root node
            root_key: Property name for root ID (default "app_id")
            child_relationships: List of relationship types to cascade delete
                                 (e.g., ["HAS_ENTITY", "HAS_ENDPOINT"])
                                 If None, deletes ALL outgoing relationships

        Returns:
            Dictionary with deletion statistics:
            - "nodes_deleted": Number of child nodes deleted
            - "relationships_deleted": Number of relationships deleted

        Example:
            >>> stats = repo.replace_subgraph(
            ...     session, "DomainModelIR", "app123",
            ...     child_relationships=["HAS_ENTITY"]
            ... )
            >>> stats["nodes_deleted"]  # e.g., 15 Entity nodes
            15

        Safety:
        - Uses DETACH DELETE to remove relationships first
        - Atomic within transaction
        - Root node preserved for update
        """
        if child_relationships:
            # Specific relationships cascade
            rel_pattern = "|".join(child_relationships)
            rel_clause = f"-[r:{rel_pattern}]->"
        else:
            # All outgoing relationships
            rel_clause = "-[r]->"

        query = f"""
        MATCH (root:{root_label} {{{root_key}: $root_id}})
        OPTIONAL MATCH (root){rel_clause}(child)
        WITH root, collect(DISTINCT child) as children,
             collect(DISTINCT r) as relationships

        // Delete children (DETACH to remove their relationships too)
        FOREACH (c IN children | DETACH DELETE c)

        RETURN
            size(children) as nodes_deleted,
            size(relationships) as relationships_deleted
        """

        result = session.run(query, root_id=root_id)
        record = result.single()

        if not record:
            logger.warning(
                "Root node %s:%s=%s not found for subgraph replacement",
                root_label,
                root_key,
                root_id,
            )
            return {"nodes_deleted": 0, "relationships_deleted": 0}

        stats = {
            "nodes_deleted": record["nodes_deleted"],
            "relationships_deleted": record["relationships_deleted"],
        }

        logger.info(
            "Subgraph replacement for %s:%s=%s: %d nodes deleted, %d relationships deleted",
            root_label,
            root_key,
            root_id,
            stats["nodes_deleted"],
            stats["relationships_deleted"],
        )

        return stats

    # ============================================================================
    # TRANSACTION HELPERS
    # ============================================================================

    def execute_in_transaction(
        self, operation: callable, *args, **kwargs
    ) -> Any:
        """
        Execute operation within a transaction with error handling.

        Args:
            operation: Callable that takes (tx, *args, **kwargs)
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation

        Returns:
            Result from operation

        Raises:
            GraphIRPersistenceError: If operation fails

        Example:
            >>> def save_entity(tx, entity):
            ...     tx.run("CREATE (e:Entity {name: $name})", name=entity.name)
            >>> repo.execute_in_transaction(save_entity, entity)
        """
        try:
            with self.driver.session(database=self.database) as session:
                return session.write_transaction(operation, *args, **kwargs)
        except Exception as exc:
            logger.error(
                "Transaction failed in %s: %s",
                self.__class__.__name__,
                exc,
                exc_info=True,
            )
            raise GraphIRPersistenceError(
                f"Failed to execute transaction: {exc}"
            ) from exc
