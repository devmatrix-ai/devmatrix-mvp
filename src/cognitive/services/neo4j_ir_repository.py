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
from src.cognitive.ir.domain_model import DomainModelIR, Entity, Attribute
from src.cognitive.ir.api_model import APIModelIR, Endpoint
from src.cognitive.ir.infrastructure_model import InfrastructureModelIR, DatabaseConfig, ObservabilityConfig
from src.cognitive.ir.behavior_model import BehaviorModelIR, Flow, Invariant
from src.cognitive.ir.validation_model import ValidationModelIR, ValidationRule, TestCase, EnforcementType, EnforcementStrategy
from datetime import datetime
import json

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

    def save_application_ir(self, app_ir: ApplicationIR, app_id: str = None) -> None:
        """Persist the entire ApplicationIR into Neo4j.

        Args:
            app_ir: The fully built ApplicationIR instance.
            app_id: Optional override for app_id in tests.
        """
        try:
            with self.driver.session() as session:
                session.write_transaction(self._tx_save_application_ir, app_ir, app_id)
            logger.info("ApplicationIR %s persisted successfully", app_ir.app_id)
        except Exception as exc:
            logger.exception("Failed to persist ApplicationIR %s", app_ir.app_id)
            raise IRPersistenceError(str(exc)) from exc

    @staticmethod
    def _tx_save_application_ir(tx: Transaction, app_ir: ApplicationIR, app_id_override: str = None) -> None:
        # Helper to convert dicts to JSON strings for Neo4j properties when needed

        # ---------- Application node ----------
        tx.run(
            """
            MERGE (a:ApplicationIR {app_id: $app_id})
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
            MERGE (d:DomainModelIR {app_id: $app_id})
            SET d.entities = $entities
            MERGE (a:ApplicationIR {app_id: $app_id})
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
            MERGE (api:APIModelIR {app_id: $app_id})
            SET api.endpoints = $endpoints
            MERGE (a:ApplicationIR {app_id: $app_id})
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
            MERGE (infra:InfrastructureModelIR {app_id: $app_id})
            SET infra.database = $database,
                infra.vector_db = $vector_db,
                infra.graph_db = $graph_db,
                infra.observability = $observability,
                infra.docker_compose_version = $docker_compose_version
            MERGE (a:ApplicationIR {app_id: $app_id})
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
            MERGE (beh:BehaviorModelIR {app_id: $app_id})
            SET beh.flows = $flows,
                beh.invariants = $invariants
            MERGE (a:ApplicationIR {app_id: $app_id})
            MERGE (a)-[:HAS_BEHAVIOR]->(beh)
            """,
            {
                "app_id": str(app_ir.app_id),
                "flows": json.dumps([f.dict() for f in app_ir.behavior_model.flows]),
                "invariants": json.dumps([inv.dict() for inv in app_ir.behavior_model.invariants]),
            },
        )

        # ---------- Validation Model ----------
        # Get the app_id to use (either from override or from app_ir)
        actual_app_id = app_id_override if app_id_override else str(app_ir.app_id)

        tx.run(
            """
            MERGE (val:ValidationModelIR {app_id: $app_id})
            SET val.rules = $rules,
                val.test_cases = $test_cases
            MERGE (a:ApplicationIR {app_id: $app_id})
            MERGE (a)-[:HAS_VALIDATION]->(val)
            """,
            {
                "app_id": actual_app_id,
                "rules": json.dumps([r.dict() for r in app_ir.validation_model.rules]),
                "test_cases": json.dumps([tc.dict() for tc in app_ir.validation_model.test_cases]),
            },
        )

        # ---------- Enforcement Strategies (Phase 4.3) ----------
        # Save enforcement strategies as individual nodes for better graph representation
        for rule in app_ir.validation_model.rules:
            if rule.enforcement and rule.enforcement_type:
                tx.run(
                    """
                    MERGE (rule:ValidationRule {
                        app_id: $app_id,
                        entity: $entity,
                        attribute: $attribute
                    })
                    MERGE (enforcement:EnforcementStrategy {
                        app_id: $app_id,
                        rule_key: $rule_key
                    })
                    SET enforcement.type = $type,
                        enforcement.implementation = $implementation,
                        enforcement.applied_at = $applied_at,
                        enforcement.template_name = $template_name,
                        enforcement.parameters = $parameters,
                        enforcement.code_snippet = $code_snippet,
                        enforcement.description = $description
                    MERGE (rule)-[:HAS_ENFORCEMENT]->(enforcement)
                    """,
                    {
                        "app_id": actual_app_id,
                        "entity": rule.entity or "",
                        "attribute": rule.attribute or "",
                        "rule_key": f"{rule.entity}_{rule.attribute}_{rule.enforcement_type.value}",
                        "type": rule.enforcement.type.value if rule.enforcement.type else "",
                        "implementation": rule.enforcement.implementation or "",
                        "applied_at": json.dumps(rule.enforcement.applied_at or []),
                        "template_name": rule.enforcement.template_name,
                        "parameters": json.dumps(rule.enforcement.parameters or {}),
                        "code_snippet": rule.enforcement.code_snippet,
                        "description": rule.enforcement.description,
                    },
                )

    def load_application_ir(self, app_id: uuid.UUID) -> ApplicationIR:
        """Load ApplicationIR from Neo4j by app_id.

        Args:
            app_id: The UUID of the application to load.

        Returns:
            The fully reconstructed ApplicationIR instance.

        Raises:
            IRPersistenceError: If the application is not found or loading fails.
        """
        try:
            with self.driver.session() as session:
                app_ir = session.read_transaction(self._tx_load_application_ir, app_id)
            logger.info("ApplicationIR %s loaded successfully", app_id)
            return app_ir
        except Exception as exc:
            logger.exception("Failed to load ApplicationIR %s", app_id)
            raise IRPersistenceError(str(exc)) from exc

    @staticmethod
    def _tx_load_application_ir(tx: Transaction, app_id: uuid.UUID) -> ApplicationIR:
        """Transaction function to load ApplicationIR from Neo4j.

        This method deserializes all JSON-stored models and reconstructs the complete
        ApplicationIR with all enforcement strategies preserved.
        """
        import json

        # ---------- 1. Load Application node ----------
        result = tx.run(
            """
            MATCH (a:ApplicationIR {app_id: $app_id})
            RETURN a.name as name,
                   a.description as description,
                   a.created_at as created_at,
                   a.updated_at as updated_at,
                   a.version as version,
                   a.phase_status as phase_status
            """,
            {"app_id": str(app_id)}
        )

        app_record = result.single()
        if not app_record:
            raise IRPersistenceError(f"Application {app_id} not found in Neo4j")

        # ---------- 2. Load DomainModel ----------
        result = tx.run(
            """
            MATCH (a:ApplicationIR {app_id: $app_id})-[:HAS_DOMAIN_MODEL]->(d:DomainModelIR)
            RETURN d.entities as entities
            """,
            {"app_id": str(app_id)}
        )

        domain_record = result.single()
        if not domain_record:
            raise IRPersistenceError(f"DomainModel not found for Application {app_id}")

        entities_json = json.loads(domain_record["entities"])
        entities = [Entity(**entity_data) for entity_data in entities_json]
        domain_model = DomainModelIR(entities=entities)

        # ---------- 3. Load APIModel ----------
        result = tx.run(
            """
            MATCH (a:ApplicationIR {app_id: $app_id})-[:HAS_API_MODEL]->(api:APIModelIR)
            RETURN api.endpoints as endpoints
            """,
            {"app_id": str(app_id)}
        )

        api_record = result.single()
        if not api_record:
            raise IRPersistenceError(f"APIModel not found for Application {app_id}")

        endpoints_json = json.loads(api_record["endpoints"])
        endpoints = [Endpoint(**endpoint_data) for endpoint_data in endpoints_json]
        api_model = APIModelIR(endpoints=endpoints)

        # ---------- 4. Load InfrastructureModel ----------
        result = tx.run(
            """
            MATCH (a:ApplicationIR {app_id: $app_id})-[:HAS_INFRASTRUCTURE]->(infra:InfrastructureModelIR)
            RETURN infra.database as database,
                   infra.vector_db as vector_db,
                   infra.graph_db as graph_db,
                   infra.observability as observability,
                   infra.docker_compose_version as docker_compose_version
            """,
            {"app_id": str(app_id)}
        )

        infra_record = result.single()
        if not infra_record:
            raise IRPersistenceError(f"InfrastructureModel not found for Application {app_id}")

        database = DatabaseConfig(**json.loads(infra_record["database"]))
        observability = ObservabilityConfig(**json.loads(infra_record["observability"]))

        vector_db = None
        if infra_record["vector_db"]:
            vector_db = DatabaseConfig(**json.loads(infra_record["vector_db"]))

        graph_db = None
        if infra_record["graph_db"]:
            graph_db = DatabaseConfig(**json.loads(infra_record["graph_db"]))

        infrastructure_model = InfrastructureModelIR(
            database=database,
            vector_db=vector_db,
            graph_db=graph_db,
            observability=observability,
            docker_compose_version=infra_record["docker_compose_version"]
        )

        # ---------- 5. Load BehaviorModel ----------
        result = tx.run(
            """
            MATCH (a:ApplicationIR {app_id: $app_id})-[:HAS_BEHAVIOR]->(beh:BehaviorModelIR)
            RETURN beh.flows as flows,
                   beh.invariants as invariants
            """,
            {"app_id": str(app_id)}
        )

        beh_record = result.single()
        if not beh_record:
            # BehaviorModel is optional, create empty one
            behavior_model = BehaviorModelIR()
        else:
            flows_json = json.loads(beh_record["flows"])
            invariants_json = json.loads(beh_record["invariants"])

            flows = [Flow(**flow_data) for flow_data in flows_json]
            invariants = [Invariant(**inv_data) for inv_data in invariants_json]

            behavior_model = BehaviorModelIR(flows=flows, invariants=invariants)

        # ---------- 6. Load ValidationModel (CRITICAL: Preserves enforcement with Neo4j nodes!) ----------
        result = tx.run(
            """
            MATCH (a:ApplicationIR {app_id: $app_id})-[:HAS_VALIDATION]->(val:ValidationModelIR)
            RETURN val.rules as rules,
                   val.test_cases as test_cases
            """,
            {"app_id": str(app_id)}
        )

        val_record = result.single()
        if not val_record:
            # ValidationModel is optional, create empty one
            validation_model = ValidationModelIR()
        else:
            rules_json = json.loads(val_record["rules"])
            test_cases_json = json.loads(val_record["test_cases"])

            # ✅ CRITICAL: This preserves enforcement from JSON serialization
            rules = [ValidationRule(**rule_data) for rule_data in rules_json]

            # Enhance rules with enforcement metadata from Neo4j nodes if available
            for rule in rules:
                if rule.enforcement_type:
                    enforce_result = tx.run(
                        """
                        MATCH (enforcement:EnforcementStrategy {
                            app_id: $app_id,
                            rule_key: $rule_key
                        })
                        RETURN enforcement
                        """,
                        {
                            "app_id": str(app_id),
                            "rule_key": f"{rule.entity}_{rule.attribute}_{rule.enforcement_type.value}"
                        }
                    )
                    enforce_record = enforce_result.single()
                    if enforce_record:
                        enforce_node = enforce_record["enforcement"]
                        # Reconstruct EnforcementStrategy from Neo4j node
                        rule.enforcement = EnforcementStrategy(
                            type=EnforcementType(enforce_node["type"]),
                            implementation=enforce_node.get("implementation", ""),
                            applied_at=json.loads(enforce_node.get("applied_at", "[]")),
                            template_name=enforce_node.get("template_name"),
                            parameters=json.loads(enforce_node.get("parameters", "{}")),
                            code_snippet=enforce_node.get("code_snippet"),
                            description=enforce_node.get("description")
                        )

            test_cases = [TestCase(**tc_data) for tc_data in test_cases_json]

            validation_model = ValidationModelIR(rules=rules, test_cases=test_cases)

        # ---------- 7. Reconstruct ApplicationIR ----------
        app_ir = ApplicationIR(
            app_id=app_id,
            name=app_record["name"],
            description=app_record["description"],
            domain_model=domain_model,
            api_model=api_model,
            infrastructure_model=infrastructure_model,
            behavior_model=behavior_model,
            validation_model=validation_model,
            created_at=datetime.fromisoformat(app_record["created_at"]),
            updated_at=datetime.fromisoformat(app_record["updated_at"]),
            version=app_record["version"],
            phase_status=json.loads(app_record["phase_status"])
        )

        logger.info("Successfully deserialized ApplicationIR %s with %d validation rules",
                   app_id, len(validation_model.rules))

        # Verify enforcement_type preservation
        computed_rules = [r for r in validation_model.rules if r.enforcement_type.value == "computed_field"]
        immutable_rules = [r for r in validation_model.rules if r.enforcement_type.value == "immutable"]
        logger.info("  → Computed fields: %d, Immutable fields: %d",
                   len(computed_rules), len(immutable_rules))

        return app_ir

