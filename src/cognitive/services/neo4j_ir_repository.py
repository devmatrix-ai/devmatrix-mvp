"""
Neo4j IR Repository
-------------------
Provides a thin persistence layer for the ApplicationIR (including BehaviorIR and ValidationIR).
It creates/updates nodes and relationships in the Neo4j graph database using the
settings defined in `src.cognitive.config.settings.CognitiveSettings`.
"""

from typing import Dict, Any
import uuid
import logging

from neo4j import GraphDatabase, Transaction

from src.cognitive.config.settings import settings
from src.cognitive.ir.application_ir import ApplicationIR

logger = logging.getLogger(__name__)

class IRPersistenceError(RuntimeError):
    """Raised when persisting the IR to Neo4j fails."""

class Neo4jIRRepository:
    """Repository responsible for persisting an ApplicationIR graph.

    The repository uses a single transaction to write the whole IR atomically.
    Nodes are merged (``MERGE``) to avoid duplicates.  Relationships are also merged.
    """

    def __init__(self) -> None:
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            database=settings.neo4j_database,
        )
        logger.info("Neo4jIRRepository initialized with URI %s", settings.neo4j_uri)

    def close(self) -> None:
        self.driver.close()
        logger.info("Neo4j driver closed")

    def save_application_ir(self, app_ir: ApplicationIR) -> None:
        """Persist the entire ApplicationIR into Neo4j.

        Args:
            app_ir: The fully built ApplicationIR instance.
        """
        try:
            with self.driver.session() as session:
                session.write_transaction(self._tx_save_application_ir, app_ir)
            logger.info("ApplicationIR %s persisted successfully", app_ir.app_id)
        except Exception as exc:
            logger.exception("Failed to persist ApplicationIR %s", app_ir.app_id)
            raise IRPersistenceError(str(exc)) from exc

    @staticmethod
    def _tx_save_application_ir(tx: Transaction, app_ir: ApplicationIR) -> None:
        # Helper to convert dicts to JSON strings for Neo4j properties when needed
        import json

        # ---------- Application node ----------
        tx.run(
            """
            MERGE (a:Application {app_id: $app_id})
            SET a.name = $name,
                a.description = $description,
                a.created_at = $created_at,
                a.updated_at = $updated_at,
                a.version = $version,
                a.ir_version = $ir_version,
                a.phase_status = $phase_status
            """,
            {
                "app_id": str(app_ir.app_id),
                "name": app_ir.name,
                "description": app_ir.description,
                "created_at": app_ir.created_at.isoformat(),
                "updated_at": app_ir.updated_at.isoformat(),
                "version": app_ir.version,
                "ir_version": str(uuid.uuid4()),  # generate a new version identifier
                "phase_status": json.dumps(app_ir.phase_status),
            },
        )

        # ---------- Domain Model ----------
        tx.run(
            """
            MERGE (d:DomainModel {app_id: $app_id})
            SET d.entities = $entities
            MERGE (a:Application {app_id: $app_id})
            MERGE (a)-[:HAS_DOMAIN_MODEL]->(d)
            """,
            {
                "app_id": str(app_ir.app_id),
                "entities": json.dumps([e.dict() for e in app_ir.domain_model.entities]),
            },
        )

        # ---------- API Model ----------
        tx.run(
            """
            MERGE (api:APIModel {app_id: $app_id})
            SET api.endpoints = $endpoints
            MERGE (a:Application {app_id: $app_id})
            MERGE (a)-[:HAS_API_MODEL]->(api)
            """,
            {
                "app_id": str(app_ir.app_id),
                "endpoints": json.dumps([ep.dict() for ep in app_ir.api_model.endpoints]),
            },
        )

        # ---------- Infrastructure Model ----------
        tx.run(
            """
            MERGE (infra:InfrastructureModel {app_id: $app_id})
            SET infra.database = $database,
                infra.vector_db = $vector_db,
                infra.graph_db = $graph_db,
                infra.observability = $observability,
                infra.docker_compose_version = $docker_compose_version
            MERGE (a:Application {app_id: $app_id})
            MERGE (a)-[:HAS_INFRASTRUCTURE]->(infra)
            """,
            {
                "app_id": str(app_ir.app_id),
                "database": json.dumps(app_ir.infrastructure_model.database.dict()),
                "vector_db": json.dumps(app_ir.infrastructure_model.vector_db.dict()) if app_ir.infrastructure_model.vector_db else None,
                "graph_db": json.dumps(app_ir.infrastructure_model.graph_db.dict()) if app_ir.infrastructure_model.graph_db else None,
                "observability": json.dumps(app_ir.infrastructure_model.observability.dict()),
                "docker_compose_version": app_ir.infrastructure_model.docker_compose_version,
            },
        )

        # ---------- Behavior Model ----------
        # Store flows and invariants as JSON strings for simplicity.
        tx.run(
            """
            MERGE (beh:BehaviorModel {app_id: $app_id})
            SET beh.flows = $flows,
                beh.invariants = $invariants
            MERGE (a:Application {app_id: $app_id})
            MERGE (a)-[:HAS_BEHAVIOR]->(beh)
            """,
            {
                "app_id": str(app_ir.app_id),
                "flows": json.dumps([f.dict() for f in app_ir.behavior_model.flows]),
                "invariants": json.dumps([inv.dict() for inv in app_ir.behavior_model.invariants]),
            },
        )

        # ---------- Validation Model ----------
        tx.run(
            """
            MERGE (val:ValidationModel {app_id: $app_id})
            SET val.rules = $rules,
                val.test_cases = $test_cases
            MERGE (a:Application {app_id: $app_id})
            MERGE (a)-[:HAS_VALIDATION]->(val)
            """,
            {
                "app_id": str(app_ir.app_id),
                "rules": json.dumps([r.dict() for r in app_ir.validation_model.rules]),
                "test_cases": json.dumps([tc.dict() for tc in app_ir.validation_model.test_cases]),
            },
        )

