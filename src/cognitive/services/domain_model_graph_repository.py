"""
Domain Model Graph Repository
------------------------------
Specialized Neo4j repository for persisting and querying DomainModelIR with optimized
graph structure for entities, attributes, and relationships.

Graph Schema:
- DomainModelIR node: Root node for the domain model
- Entity nodes: Business entities with HAS_ENTITY relationships
- Attribute nodes: Entity attributes with HAS_ATTRIBUTE relationships
- RELATES_TO edges: Entity relationships with type and metadata
"""

from typing import Dict, Any, List, Optional
import logging
import json

from neo4j import Transaction

from src.cognitive.services.graph_ir_repository import GraphIRRepository, GraphIRPersistenceError
from src.cognitive.ir.domain_model import (
    DomainModelIR,
    Entity,
    Attribute,
    Relationship,
    DataType,
    RelationshipType,
)

logger = logging.getLogger(__name__)


class DomainModelPersistenceError(GraphIRPersistenceError):
    """Raised when persisting or loading DomainModelIR fails."""


class DomainModelGraphRepository(GraphIRRepository):
    """
    Repository for DomainModelIR graph operations.

    Inherits from GraphIRRepository for:
    - Neo4j driver management and context manager pattern
    - Temporal metadata tracking (created_at, updated_at)
    - Batch operations (batch_create_nodes, batch_create_relationships)
    - Subgraph replacement pattern for safe updates
    - Transaction management and error handling

    Provides domain-specific methods for:
    - Saving complete domain models with batch operations
    - Loading domain models with relationship reconstruction
    - Querying entities and relationships
    - Managing entity lifecycle
    """

    def save_domain_model(self, app_id: str, domain_model: DomainModelIR) -> None:
        """
        Persist complete DomainModelIR to Neo4j graph.

        Creates:
        - DomainModelIR root node
        - Entity nodes with HAS_ENTITY relationships
        - Attribute nodes with HAS_ATTRIBUTE relationships
        - RELATES_TO edges between entities for relationships

        Args:
            app_id: Application identifier
            domain_model: DomainModelIR instance to persist

        Raises:
            DomainModelPersistenceError: If persistence fails
        """
        try:
            with self.driver.session(database=self.database) as session:
                session.write_transaction(
                    self._tx_save_domain_model, app_id, domain_model
                )
            logger.info(
                "DomainModelIR for app %s persisted successfully with %d entities",
                app_id,
                len(domain_model.entities),
            )
        except Exception as exc:
            logger.exception("Failed to persist DomainModelIR for app %s", app_id)
            raise DomainModelPersistenceError(str(exc)) from exc

    @staticmethod
    def _tx_save_domain_model(
        tx: Transaction, app_id: str, domain_model: DomainModelIR
    ) -> None:
        """
        Transaction function to save DomainModelIR with batch operations.

        Args:
            tx: Neo4j transaction
            app_id: Application identifier
            domain_model: DomainModelIR to persist
        """
        # 1. Create/update DomainModelIR root node
        tx.run(
            """
            MERGE (dm:DomainModelIR {app_id: $app_id})
            SET dm.entity_count = $entity_count,
                dm.metadata = $metadata,
                dm.updated_at = timestamp()
            """,
            {
                "app_id": app_id,
                "entity_count": len(domain_model.entities),
                "metadata": json.dumps(domain_model.metadata),
            },
        )

        # 2. Batch create Entity nodes with HAS_ENTITY relationships
        entity_batch = []
        for entity in domain_model.entities:
            entity_id = f"{app_id}_{entity.name}"
            entity_batch.append(
                {
                    "entity_id": entity_id,
                    "app_id": app_id,
                    "name": entity.name,
                    "description": entity.description,
                    "is_aggregate_root": entity.is_aggregate_root,
                    "attribute_count": len(entity.attributes),
                    "relationship_count": len(entity.relationships),
                }
            )

        if entity_batch:
            tx.run(
                """
                UNWIND $entities AS entity
                MERGE (e:Entity {entity_id: entity.entity_id})
                SET e.app_id = entity.app_id,
                    e.name = entity.name,
                    e.description = entity.description,
                    e.is_aggregate_root = entity.is_aggregate_root,
                    e.attribute_count = entity.attribute_count,
                    e.relationship_count = entity.relationship_count,
                    e.updated_at = timestamp()
                WITH e, entity
                MERGE (dm:DomainModelIR {app_id: entity.app_id})
                MERGE (dm)-[:HAS_ENTITY]->(e)
                """,
                {"entities": entity_batch},
            )

        # 3. Batch create Attribute nodes with HAS_ATTRIBUTE relationships
        attribute_batch = []
        for entity in domain_model.entities:
            entity_id = f"{app_id}_{entity.name}"
            for attr in entity.attributes:
                attribute_id = f"{entity_id}_{attr.name}"
                attribute_batch.append(
                    {
                        "attribute_id": attribute_id,
                        "entity_id": entity_id,
                        "name": attr.name,
                        "data_type": attr.data_type.value,
                        "is_primary_key": attr.is_primary_key,
                        "is_nullable": attr.is_nullable,
                        "is_unique": attr.is_unique,
                        "default_value": json.dumps(attr.default_value)
                        if attr.default_value is not None
                        else None,
                        "description": attr.description,
                        "constraints": json.dumps(attr.constraints),
                    }
                )

        if attribute_batch:
            tx.run(
                """
                UNWIND $attributes AS attr
                MERGE (a:Attribute {attribute_id: attr.attribute_id})
                SET a.name = attr.name,
                    a.data_type = attr.data_type,
                    a.is_primary_key = attr.is_primary_key,
                    a.is_nullable = attr.is_nullable,
                    a.is_unique = attr.is_unique,
                    a.default_value = attr.default_value,
                    a.description = attr.description,
                    a.constraints = attr.constraints,
                    a.updated_at = timestamp()
                WITH a, attr
                MERGE (e:Entity {entity_id: attr.entity_id})
                MERGE (e)-[:HAS_ATTRIBUTE]->(a)
                """,
                {"attributes": attribute_batch},
            )

        # 4. Batch create RELATES_TO edges between entities
        relationship_batch = []
        for entity in domain_model.entities:
            source_entity_id = f"{app_id}_{entity.name}"
            for rel in entity.relationships:
                target_entity_id = f"{app_id}_{rel.target_entity}"
                relationship_batch.append(
                    {
                        "source_id": source_entity_id,
                        "target_id": target_entity_id,
                        "type": rel.type.value,
                        "field_name": rel.field_name,
                        "back_populates": rel.back_populates,
                    }
                )

        if relationship_batch:
            tx.run(
                """
                UNWIND $relationships AS rel
                MATCH (source:Entity {entity_id: rel.source_id})
                MATCH (target:Entity {entity_id: rel.target_id})
                MERGE (source)-[r:RELATES_TO {field_name: rel.field_name}]->(target)
                SET r.type = rel.type,
                    r.back_populates = rel.back_populates,
                    r.updated_at = timestamp()
                """,
                {"relationships": relationship_batch},
            )

        logger.info(
            "Persisted %d entities, %d attributes, %d relationships for app %s",
            len(entity_batch),
            len(attribute_batch),
            len(relationship_batch),
            app_id,
        )

    def load_domain_model(self, app_id: str) -> DomainModelIR:
        """
        Load DomainModelIR from Neo4j graph by app_id.

        Reconstructs complete domain model including:
        - All entities with attributes
        - All relationships between entities
        - Metadata

        Args:
            app_id: Application identifier

        Returns:
            Reconstructed DomainModelIR instance

        Raises:
            DomainModelPersistenceError: If loading fails or model not found
        """
        try:
            with self.driver.session() as session:
                domain_model = session.read_transaction(
                    self._tx_load_domain_model, app_id
                )
            logger.info(
                "DomainModelIR for app %s loaded successfully with %d entities",
                app_id,
                len(domain_model.entities),
            )
            return domain_model
        except Exception as exc:
            logger.exception("Failed to load DomainModelIR for app %s", app_id)
            raise DomainModelPersistenceError(str(exc)) from exc

    @staticmethod
    def _tx_load_domain_model(tx: Transaction, app_id: str) -> DomainModelIR:
        """
        Transaction function to load DomainModelIR from graph.

        Args:
            tx: Neo4j transaction
            app_id: Application identifier

        Returns:
            Reconstructed DomainModelIR

        Raises:
            DomainModelPersistenceError: If model not found
        """
        # 1. Load DomainModelIR root node
        result = tx.run(
            """
            MATCH (dm:DomainModelIR {app_id: $app_id})
            RETURN dm.metadata as metadata, dm.entity_count as entity_count
            """,
            {"app_id": app_id},
        )

        dm_record = result.single()
        if not dm_record:
            raise DomainModelPersistenceError(
                f"DomainModelIR not found for app {app_id}"
            )

        metadata = json.loads(dm_record["metadata"]) if dm_record["metadata"] else {}

        # 2. Load all entities with their attributes
        result = tx.run(
            """
            MATCH (dm:DomainModelIR {app_id: $app_id})-[:HAS_ENTITY]->(e:Entity)
            OPTIONAL MATCH (e)-[:HAS_ATTRIBUTE]->(a:Attribute)
            RETURN e.entity_id as entity_id,
                   e.name as entity_name,
                   e.description as entity_description,
                   e.is_aggregate_root as is_aggregate_root,
                   collect(a) as attributes
            ORDER BY e.name
            """,
            {"app_id": app_id},
        )

        entities_data = []
        entity_records = list(result)

        for entity_record in entity_records:
            # Parse attributes
            attributes = []
            for attr_node in entity_record["attributes"]:
                if attr_node:
                    attributes.append(
                        Attribute(
                            name=attr_node["name"],
                            data_type=DataType(attr_node["data_type"]),
                            is_primary_key=attr_node.get("is_primary_key", False),
                            is_nullable=attr_node.get("is_nullable", False),
                            is_unique=attr_node.get("is_unique", False),
                            default_value=json.loads(attr_node["default_value"])
                            if attr_node.get("default_value")
                            else None,
                            description=attr_node.get("description"),
                            constraints=json.loads(attr_node.get("constraints", "{}")),
                        )
                    )

            entities_data.append(
                {
                    "entity_id": entity_record["entity_id"],
                    "name": entity_record["entity_name"],
                    "description": entity_record["entity_description"],
                    "is_aggregate_root": entity_record.get("is_aggregate_root", False),
                    "attributes": attributes,
                    "relationships": [],  # Will populate next
                }
            )

        # 3. Load all relationships
        result = tx.run(
            """
            MATCH (dm:DomainModelIR {app_id: $app_id})-[:HAS_ENTITY]->(source:Entity)
            MATCH (source)-[r:RELATES_TO]->(target:Entity)
            RETURN source.name as source_entity,
                   target.name as target_entity,
                   r.type as rel_type,
                   r.field_name as field_name,
                   r.back_populates as back_populates
            """,
            {"app_id": app_id},
        )

        relationships_by_entity = {}
        for rel_record in result:
            source_name = rel_record["source_entity"]
            if source_name not in relationships_by_entity:
                relationships_by_entity[source_name] = []

            relationships_by_entity[source_name].append(
                Relationship(
                    source_entity=source_name,
                    target_entity=rel_record["target_entity"],
                    type=RelationshipType(rel_record["rel_type"]),
                    field_name=rel_record["field_name"],
                    back_populates=rel_record.get("back_populates"),
                )
            )

        # 4. Construct Entity objects with relationships
        entities = []
        for entity_data in entities_data:
            entity_name = entity_data["name"]
            entity_relationships = relationships_by_entity.get(entity_name, [])

            entities.append(
                Entity(
                    name=entity_name,
                    attributes=entity_data["attributes"],
                    relationships=entity_relationships,
                    description=entity_data["description"],
                    is_aggregate_root=entity_data["is_aggregate_root"],
                )
            )

        # 5. Construct and return DomainModelIR
        domain_model = DomainModelIR(entities=entities, metadata=metadata)

        logger.info(
            "Loaded DomainModelIR for app %s: %d entities, %d total relationships",
            app_id,
            len(entities),
            sum(len(e.relationships) for e in entities),
        )

        return domain_model

    def get_entity(self, app_id: str, entity_name: str) -> Optional[Entity]:
        """
        Retrieve single entity with attributes and relationships.

        Args:
            app_id: Application identifier
            entity_name: Entity name to retrieve

        Returns:
            Entity instance or None if not found
        """
        try:
            with self.driver.session() as session:
                return session.read_transaction(
                    self._tx_get_entity, app_id, entity_name
                )
        except Exception as exc:
            logger.error(
                "Failed to get entity %s for app %s: %s", entity_name, app_id, exc
            )
            return None

    @staticmethod
    def _tx_get_entity(
        tx: Transaction, app_id: str, entity_name: str
    ) -> Optional[Entity]:
        """Transaction function to retrieve single entity."""
        entity_id = f"{app_id}_{entity_name}"

        # Get entity with attributes
        result = tx.run(
            """
            MATCH (e:Entity {entity_id: $entity_id})
            OPTIONAL MATCH (e)-[:HAS_ATTRIBUTE]->(a:Attribute)
            RETURN e.name as name,
                   e.description as description,
                   e.is_aggregate_root as is_aggregate_root,
                   collect(a) as attributes
            """,
            {"entity_id": entity_id},
        )

        entity_record = result.single()
        if not entity_record:
            return None

        # Parse attributes
        attributes = []
        for attr_node in entity_record["attributes"]:
            if attr_node:
                attributes.append(
                    Attribute(
                        name=attr_node["name"],
                        data_type=DataType(attr_node["data_type"]),
                        is_primary_key=attr_node.get("is_primary_key", False),
                        is_nullable=attr_node.get("is_nullable", False),
                        is_unique=attr_node.get("is_unique", False),
                        default_value=json.loads(attr_node["default_value"])
                        if attr_node.get("default_value")
                        else None,
                        description=attr_node.get("description"),
                        constraints=json.loads(attr_node.get("constraints", "{}")),
                    )
                )

        # Get relationships
        result = tx.run(
            """
            MATCH (source:Entity {entity_id: $entity_id})-[r:RELATES_TO]->(target:Entity)
            RETURN source.name as source_entity,
                   target.name as target_entity,
                   r.type as rel_type,
                   r.field_name as field_name,
                   r.back_populates as back_populates
            """,
            {"entity_id": entity_id},
        )

        relationships = []
        for rel_record in result:
            relationships.append(
                Relationship(
                    source_entity=rel_record["source_entity"],
                    target_entity=rel_record["target_entity"],
                    type=RelationshipType(rel_record["rel_type"]),
                    field_name=rel_record["field_name"],
                    back_populates=rel_record.get("back_populates"),
                )
            )

        return Entity(
            name=entity_record["name"],
            attributes=attributes,
            relationships=relationships,
            description=entity_record["description"],
            is_aggregate_root=entity_record.get("is_aggregate_root", False),
        )

    def delete_domain_model(self, app_id: str) -> None:
        """
        Delete DomainModelIR and all related nodes for an application.

        Args:
            app_id: Application identifier
        """
        try:
            with self.driver.session() as session:
                session.write_transaction(self._tx_delete_domain_model, app_id)
            logger.info("DomainModelIR for app %s deleted successfully", app_id)
        except Exception as exc:
            logger.exception("Failed to delete DomainModelIR for app %s", app_id)
            raise DomainModelPersistenceError(str(exc)) from exc

    @staticmethod
    def _tx_delete_domain_model(tx: Transaction, app_id: str) -> None:
        """Transaction function to delete domain model and related nodes."""
        # Delete in order: Attributes -> Relationships -> Entities -> DomainModel
        tx.run(
            """
            MATCH (dm:DomainModelIR {app_id: $app_id})-[:HAS_ENTITY]->(e:Entity)
            OPTIONAL MATCH (e)-[:HAS_ATTRIBUTE]->(a:Attribute)
            OPTIONAL MATCH (e)-[r:RELATES_TO]->()
            DETACH DELETE a, r, e, dm
            """,
            {"app_id": app_id},
        )
