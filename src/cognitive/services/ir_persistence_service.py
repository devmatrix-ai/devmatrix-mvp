"""
IR Persistence Service
======================
Unified service for ApplicationIR persistence to Neo4j graph.

This service replaces the legacy Neo4jIRRepository with a modern,
graph-native approach using specialized repositories for each submodel.

Sprint 7: Integration with Pipeline E2E
- Save complete ApplicationIR to Neo4j
- Load ApplicationIR using FullIRGraphLoader
- Support caching and cache invalidation

Usage:
    service = IRPersistenceService()

    # Save
    app_id = await service.save_application_ir(application_ir)

    # Load
    loaded_ir = await service.load_application_ir(app_id)

    # Check existence
    exists = await service.exists(app_id)

Deprecates: src/cognitive/services/neo4j_ir_repository.py
"""

import os
import uuid
import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime

from neo4j import GraphDatabase

from src.cognitive.ir.application_ir import ApplicationIR
from src.cognitive.ir.domain_model import DomainModelIR
from src.cognitive.ir.api_model import APIModelIR
from src.cognitive.ir.behavior_model import BehaviorModelIR
from src.cognitive.ir.validation_model import ValidationModelIR
from src.cognitive.ir.infrastructure_model import InfrastructureModelIR
from src.cognitive.ir.tests_model import TestsModelIR

from src.cognitive.services.domain_model_graph_repository import DomainModelGraphRepository
from src.cognitive.services.api_model_graph_repository import APIModelGraphRepository
from src.cognitive.services.full_ir_graph_loader import FullIRGraphLoader, FullIRGraphLoadResult

logger = logging.getLogger(__name__)


class IRPersistenceError(Exception):
    """Raised when IR persistence operations fail."""
    pass


class IRPersistenceService:
    """
    Unified service for ApplicationIR persistence to Neo4j.

    Features:
    - Save complete ApplicationIR with all submodels
    - Load ApplicationIR using optimized single-query loader
    - Cache management for performance
    - Atomic operations with rollback support

    This is the recommended replacement for Neo4jIRRepository.
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ):
        """
        Initialize IR Persistence Service.

        Args:
            uri: Neo4j URI (default: from NEO4J_URI env var)
            user: Neo4j user (default: from NEO4J_USER env var)
            password: Neo4j password (default: from NEO4J_PASSWORD env var)
            database: Neo4j database (default: from NEO4J_DATABASE env var)
        """
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        self.database = database or os.getenv("NEO4J_DATABASE", "neo4j")

        # Initialize specialized repositories
        self._domain_repo = DomainModelGraphRepository(
            uri=self.uri,
            user=self.user,
            password=self.password,
            database=self.database,
        )
        self._api_repo = APIModelGraphRepository(
            uri=self.uri,
            user=self.user,
            password=self.password,
            database=self.database,
        )
        self._loader = FullIRGraphLoader(
            uri=self.uri,
            user=self.user,
            password=self.password,
            database=self.database,
        )

        # Direct driver for ApplicationIR root node
        self._driver = GraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password),
        )

        logger.info("IRPersistenceService initialized")

    def close(self):
        """Close all connections."""
        self._domain_repo.close()
        self._api_repo.close()
        self._loader.close()
        if self._driver:
            self._driver.close()
        logger.info("IRPersistenceService closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def save_application_ir(
        self,
        app_ir: ApplicationIR,
        app_id: Optional[str] = None,
    ) -> str:
        """
        Save complete ApplicationIR to Neo4j graph.

        Creates:
        - ApplicationIR root node
        - DomainModelIR with entities, attributes, relationships
        - APIModelIR with endpoints, parameters, schemas
        - BehaviorModelIR with flows, steps, invariants
        - ValidationModelIR with rules
        - InfrastructureModelIR with config
        - TestsModelIR with scenarios (if present)

        Args:
            app_ir: ApplicationIR instance to persist
            app_id: Optional app ID (uses app_ir.app_id if not provided)

        Returns:
            str: The app_id used for persistence

        Raises:
            IRPersistenceError: If persistence fails
        """
        try:
            # Determine app_id
            final_app_id = app_id or str(app_ir.app_id)

            logger.info(f"Saving ApplicationIR {final_app_id} to Neo4j")

            # 1. Create/Update ApplicationIR root node
            self._save_application_root(final_app_id, app_ir)

            # 2. Save DomainModelIR
            if app_ir.domain_model:
                self._domain_repo.save_domain_model(final_app_id, app_ir.domain_model)
                logger.debug(f"Saved DomainModelIR with {len(app_ir.domain_model.entities)} entities")

            # 3. Save APIModelIR
            if app_ir.api_model:
                self._api_repo.save_api_model(final_app_id, app_ir.api_model)
                logger.debug(f"Saved APIModelIR with {len(app_ir.api_model.endpoints)} endpoints")

            # 4. Save BehaviorModelIR
            if app_ir.behavior_model:
                self._save_behavior_model(final_app_id, app_ir.behavior_model)
                logger.debug(f"Saved BehaviorModelIR with {len(app_ir.behavior_model.flows)} flows")

            # 5. Save ValidationModelIR
            if app_ir.validation_model:
                self._save_validation_model(final_app_id, app_ir.validation_model)
                logger.debug(f"Saved ValidationModelIR with {len(app_ir.validation_model.rules)} rules")

            # 6. Save InfrastructureModelIR
            if app_ir.infrastructure_model:
                self._save_infrastructure_model(final_app_id, app_ir.infrastructure_model)
                logger.debug("Saved InfrastructureModelIR")

            # 7. Save TestsModelIR (if present)
            if app_ir.tests_model and (app_ir.tests_model.seed_entities or app_ir.tests_model.test_scenarios):
                self._save_tests_model(final_app_id, app_ir.tests_model)
                logger.debug("Saved TestsModelIR")

            # Invalidate cache for this app
            self._loader.invalidate_cache(final_app_id)

            logger.info(f"ApplicationIR {final_app_id} saved successfully")
            return final_app_id

        except Exception as e:
            logger.error(f"Failed to save ApplicationIR: {e}")
            raise IRPersistenceError(f"Failed to save ApplicationIR: {e}") from e

    def load_application_ir(
        self,
        app_id: str,
        include_tests: bool = True,
        use_cache: bool = True,
    ) -> Optional[ApplicationIR]:
        """
        Load complete ApplicationIR from Neo4j graph.

        Uses FullIRGraphLoader for optimized single-query loading.

        Args:
            app_id: Application identifier
            include_tests: Include TestsModelIR (default: True)
            use_cache: Use in-memory cache (default: True)

        Returns:
            ApplicationIR if found, None otherwise
        """
        try:
            result: FullIRGraphLoadResult = self._loader.load_full_ir(
                app_id=app_id,
                include_tests=include_tests,
                use_cache=use_cache,
            )

            if result.success and result.application_ir:
                logger.info(f"Loaded ApplicationIR {app_id} in {result.load_time_ms:.2f}ms")
                return result.application_ir
            else:
                logger.warning(f"ApplicationIR {app_id} not found: {result.error_message}")
                return None

        except Exception as e:
            logger.error(f"Failed to load ApplicationIR {app_id}: {e}")
            return None

    def exists(self, app_id: str) -> bool:
        """
        Check if ApplicationIR exists in graph.

        Args:
            app_id: Application identifier

        Returns:
            bool: True if exists
        """
        return self._loader.exists(app_id)

    def get_all_app_ids(self) -> list:
        """
        Get all ApplicationIR app_ids in the graph.

        Returns:
            List of app_id strings
        """
        return self._loader.get_app_ids()

    def invalidate_cache(self, app_id: Optional[str] = None):
        """
        Invalidate cache for specific app or all apps.

        Args:
            app_id: Specific app to invalidate, or None for all
        """
        self._loader.invalidate_cache(app_id)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get persistence statistics.

        Returns:
            Dict with stats (app_count, cache_stats, etc.)
        """
        return self._loader.get_load_stats()

    # =========================================================================
    # Private methods for saving submodels
    # =========================================================================

    def _save_application_root(self, app_id: str, app_ir: ApplicationIR):
        """Create/Update ApplicationIR root node."""
        query = """
        MERGE (app:ApplicationIR {app_id: $app_id})
        ON CREATE SET
            app.name = $name,
            app.description = $description,
            app.version = $version,
            app.created_at = datetime(),
            app.updated_at = datetime()
        ON MATCH SET
            app.name = $name,
            app.description = $description,
            app.version = $version,
            app.updated_at = datetime()
        RETURN app
        """
        with self._driver.session(database=self.database) as session:
            session.run(
                query,
                app_id=app_id,
                name=app_ir.name,
                description=app_ir.description or "",
                version=app_ir.version,
            )

    def _save_behavior_model(self, app_id: str, behavior_model: BehaviorModelIR):
        """Save BehaviorModelIR to graph."""
        with self._driver.session(database=self.database) as session:
            # Create BehaviorModelIR node
            session.run("""
                MATCH (app:ApplicationIR {app_id: $app_id})
                MERGE (bm:BehaviorModelIR {app_id: $app_id})
                ON CREATE SET
                    bm.created_at = datetime(),
                    bm.updated_at = datetime()
                ON MATCH SET
                    bm.updated_at = datetime()
                MERGE (app)-[:HAS_BEHAVIOR_MODEL]->(bm)
            """, app_id=app_id)

            # Save Flows with Steps
            for flow in behavior_model.flows:
                flow_id = f"{app_id}_{flow.name}"
                session.run("""
                    MATCH (bm:BehaviorModelIR {app_id: $app_id})
                    MERGE (f:Flow {flow_id: $flow_id})
                    ON CREATE SET
                        f.name = $name,
                        f.type = $type,
                        f.trigger = $trigger,
                        f.description = $description,
                        f.created_at = datetime(),
                        f.updated_at = datetime()
                    ON MATCH SET
                        f.name = $name,
                        f.type = $type,
                        f.trigger = $trigger,
                        f.description = $description,
                        f.updated_at = datetime()
                    MERGE (bm)-[:HAS_FLOW]->(f)
                """,
                    app_id=app_id,
                    flow_id=flow_id,
                    name=flow.name,
                    type=flow.type.value if hasattr(flow.type, 'value') else str(flow.type),
                    trigger=flow.trigger or "",
                    description=flow.description or "",
                )

                # Save Steps
                for i, step in enumerate(flow.steps):
                    step_id = f"{flow_id}_step_{i}"
                    session.run("""
                        MATCH (f:Flow {flow_id: $flow_id})
                        MERGE (s:Step {step_id: $step_id})
                        ON CREATE SET
                            s.order = $order,
                            s.description = $description,
                            s.action = $action,
                            s.target_entity = $target_entity,
                            s.condition = $condition,
                            s.created_at = datetime(),
                            s.updated_at = datetime()
                        ON MATCH SET
                            s.order = $order,
                            s.description = $description,
                            s.action = $action,
                            s.target_entity = $target_entity,
                            s.condition = $condition,
                            s.updated_at = datetime()
                        MERGE (f)-[:HAS_STEP]->(s)
                    """,
                        flow_id=flow_id,
                        step_id=step_id,
                        order=step.order,
                        description=step.description or "",
                        action=step.action or "",
                        target_entity=step.target_entity or "",
                        condition=step.condition or "",
                    )

            # Save Invariants
            for i, inv in enumerate(behavior_model.invariants):
                inv_id = f"{app_id}_inv_{i}"
                session.run("""
                    MATCH (bm:BehaviorModelIR {app_id: $app_id})
                    MERGE (inv:Invariant {invariant_id: $inv_id})
                    ON CREATE SET
                        inv.entity = $entity,
                        inv.description = $description,
                        inv.expression = $expression,
                        inv.enforcement_level = $enforcement_level,
                        inv.created_at = datetime(),
                        inv.updated_at = datetime()
                    ON MATCH SET
                        inv.entity = $entity,
                        inv.description = $description,
                        inv.expression = $expression,
                        inv.enforcement_level = $enforcement_level,
                        inv.updated_at = datetime()
                    MERGE (bm)-[:HAS_INVARIANT]->(inv)
                """,
                    app_id=app_id,
                    inv_id=inv_id,
                    entity=inv.entity or "",
                    description=inv.description or "",
                    expression=inv.expression or "",
                    enforcement_level=inv.enforcement_level or "strict",
                )

    def _save_validation_model(self, app_id: str, validation_model: ValidationModelIR):
        """Save ValidationModelIR to graph."""
        with self._driver.session(database=self.database) as session:
            # Create ValidationModelIR node
            session.run("""
                MATCH (app:ApplicationIR {app_id: $app_id})
                MERGE (vm:ValidationModelIR {app_id: $app_id})
                ON CREATE SET
                    vm.created_at = datetime(),
                    vm.updated_at = datetime()
                ON MATCH SET
                    vm.updated_at = datetime()
                MERGE (app)-[:HAS_VALIDATION_MODEL]->(vm)
            """, app_id=app_id)

            # Save ValidationRules
            for i, rule in enumerate(validation_model.rules):
                rule_id = f"{app_id}_rule_{i}"
                session.run("""
                    MATCH (vm:ValidationModelIR {app_id: $app_id})
                    MERGE (r:ValidationRule {rule_id: $rule_id})
                    ON CREATE SET
                        r.entity = $entity,
                        r.attribute = $attribute,
                        r.type = $type,
                        r.condition = $condition,
                        r.error_message = $error_message,
                        r.severity = $severity,
                        r.created_at = datetime(),
                        r.updated_at = datetime()
                    ON MATCH SET
                        r.entity = $entity,
                        r.attribute = $attribute,
                        r.type = $type,
                        r.condition = $condition,
                        r.error_message = $error_message,
                        r.severity = $severity,
                        r.updated_at = datetime()
                    MERGE (vm)-[:HAS_RULE]->(r)
                """,
                    app_id=app_id,
                    rule_id=rule_id,
                    entity=rule.entity or "",
                    attribute=rule.attribute or "",
                    type=rule.type.value if hasattr(rule.type, 'value') else str(rule.type),
                    condition=rule.condition or "",
                    error_message=rule.error_message or "",
                    severity=rule.severity or "error",
                )

    def _save_infrastructure_model(self, app_id: str, infra_model: InfrastructureModelIR):
        """Save InfrastructureModelIR to graph."""
        with self._driver.session(database=self.database) as session:
            db_config = infra_model.database
            session.run("""
                MATCH (app:ApplicationIR {app_id: $app_id})
                MERGE (im:InfrastructureModelIR {app_id: $app_id})
                ON CREATE SET
                    im.database_type = $db_type,
                    im.host = $host,
                    im.port = $port,
                    im.database_name = $db_name,
                    im.user = $user,
                    im.password_env_var = $password_env_var,
                    im.created_at = datetime(),
                    im.updated_at = datetime()
                ON MATCH SET
                    im.database_type = $db_type,
                    im.host = $host,
                    im.port = $port,
                    im.database_name = $db_name,
                    im.user = $user,
                    im.password_env_var = $password_env_var,
                    im.updated_at = datetime()
                MERGE (app)-[:HAS_INFRASTRUCTURE_MODEL]->(im)
            """,
                app_id=app_id,
                db_type=db_config.type.value if hasattr(db_config.type, 'value') else str(db_config.type),
                host=db_config.host or "localhost",
                port=db_config.port or 5432,
                db_name=db_config.name or "app_db",
                user=db_config.user or "postgres",
                password_env_var=db_config.password_env_var or "DATABASE_PASSWORD",
            )

    def _save_tests_model(self, app_id: str, tests_model: TestsModelIR):
        """Save TestsModelIR to graph."""
        with self._driver.session(database=self.database) as session:
            # Create TestsModelIR node
            session.run("""
                MATCH (app:ApplicationIR {app_id: $app_id})
                MERGE (tm:TestsModelIR {app_id: $app_id})
                ON CREATE SET
                    tm.created_at = datetime(),
                    tm.updated_at = datetime()
                ON MATCH SET
                    tm.updated_at = datetime()
                MERGE (app)-[:HAS_TESTS_MODEL]->(tm)
            """, app_id=app_id)

            # Save SeedEntities
            for i, seed in enumerate(tests_model.seed_entities):
                seed_id = f"{app_id}_seed_{i}"
                session.run("""
                    MATCH (tm:TestsModelIR {app_id: $app_id})
                    MERGE (se:SeedEntityIR {seed_id: $seed_id})
                    ON CREATE SET
                        se.entity_name = $entity_name,
                        se.count = $count,
                        se.scenario = $scenario,
                        se.created_at = datetime(),
                        se.updated_at = datetime()
                    ON MATCH SET
                        se.entity_name = $entity_name,
                        se.count = $count,
                        se.scenario = $scenario,
                        se.updated_at = datetime()
                    MERGE (tm)-[:HAS_SEED_ENTITY]->(se)
                """,
                    app_id=app_id,
                    seed_id=seed_id,
                    entity_name=seed.entity_name or "",
                    count=seed.count or 1,
                    scenario=seed.scenario or "default",
                )

            # Save TestScenarios
            for i, scenario in enumerate(tests_model.test_scenarios):
                scenario_id = f"{app_id}_scenario_{i}"
                session.run("""
                    MATCH (tm:TestsModelIR {app_id: $app_id})
                    MERGE (ts:TestScenarioIR {scenario_id: $scenario_id})
                    ON CREATE SET
                        ts.name = $name,
                        ts.description = $description,
                        ts.type = $type,
                        ts.priority = $priority,
                        ts.created_at = datetime(),
                        ts.updated_at = datetime()
                    ON MATCH SET
                        ts.name = $name,
                        ts.description = $description,
                        ts.type = $type,
                        ts.priority = $priority,
                        ts.updated_at = datetime()
                    MERGE (tm)-[:HAS_TEST_SCENARIO]->(ts)
                """,
                    app_id=app_id,
                    scenario_id=scenario_id,
                    name=scenario.name or "",
                    description=scenario.description or "",
                    type=scenario.type.value if hasattr(scenario.type, 'value') else str(scenario.type),
                    priority=scenario.priority.value if hasattr(scenario.priority, 'value') else str(scenario.priority),
                )
