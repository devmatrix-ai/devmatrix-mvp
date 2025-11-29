"""
Full IR Graph Loader
=====================
Sprint 6: Lineage & Intelligence
Date: 2025-11-29

Unified loader that loads the complete ApplicationIR graph in a single query.

Key Features:
- Single comprehensive Cypher query for all subgraphs
- Optional test model loading (can be heavy)
- In-memory caching support
- Performance metrics and load statistics

Replaces fragmented pattern of:
- DomainModelGraphRepository.load_domain_model()
- APIModelGraphRepository.load_api_model()
- Individual IR loaders

Performance Improvement:
- N queries (6-8 per app) → 1 query
- Faster loads for QA and code generation phases
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import time
import json
import logging

from neo4j import GraphDatabase

from src.cognitive.config.settings import settings
from src.cognitive.ir.application_ir import ApplicationIR
from src.cognitive.ir.domain_model import (
    DomainModelIR,
    Entity,
    Attribute,
    Relationship,
    DataType,
    RelationshipType,
)
from src.cognitive.ir.api_model import (
    APIModelIR,
    Endpoint,
    APIParameter,
    APISchema,
    APISchemaField,
    HttpMethod,
    ParameterLocation,
)
from src.cognitive.ir.behavior_model import BehaviorModelIR, Flow, Step, Invariant, FlowType
from src.cognitive.ir.validation_model import ValidationModelIR, ValidationRule, ValidationType
from src.cognitive.ir.infrastructure_model import InfrastructureModelIR, DatabaseConfig, DatabaseType
from src.cognitive.ir.tests_model import (
    TestsModelIR,
    TestScenarioIR,
    SeedEntityIR,
    SeedFieldValue,
    TestAssertion,
    TestType,
    TestPriority,
    ExpectedOutcome,
)

logger = logging.getLogger(__name__)


@dataclass
class FullIRGraphLoadResult:
    """Result from loading complete ApplicationIR from graph."""
    application_ir: ApplicationIR
    load_time_ms: float
    nodes_loaded: int
    relationships_loaded: int
    cache_hit: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class FullIRGraphLoader:
    """
    Unified loader for complete ApplicationIR graph.

    Loads all subgraphs in a single Cypher query:
    - DomainModelIR with Entities, Attributes, Relationships
    - APIModelIR with Endpoints, Parameters, Schemas
    - BehaviorModelIR with Flows, Steps, Invariants
    - ValidationModelIR with Rules
    - InfrastructureModelIR with DatabaseConfig
    - TestsModelIR with SeedEntities, TestScenarios (optional)

    Usage:
        loader = FullIRGraphLoader()
        result = loader.load_full_ir(app_id)
        app_ir = result.application_ir
    """

    # In-memory cache for loaded IRs
    _cache: Dict[str, ApplicationIR] = {}
    _cache_timestamps: Dict[str, datetime] = {}
    CACHE_TTL_SECONDS = 300  # 5 minutes

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ):
        """
        Initialize loader with Neo4j connection.

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
        logger.info("FullIRGraphLoader initialized with URI %s", self.uri)

    def close(self):
        """Close Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            logger.info("FullIRGraphLoader connection closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _safe_json_loads(self, value: Optional[str]) -> Any:
        """Safely parse JSON value, returning None if invalid or empty."""
        if not value or not isinstance(value, str):
            return None
        value = value.strip()
        if not value:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            # Return the raw value if it's not valid JSON
            return value if value else None

    def load_full_ir(
        self,
        app_id: str,
        include_tests: bool = True,
        use_cache: bool = True,
    ) -> FullIRGraphLoadResult:
        """
        Load complete ApplicationIR from Neo4j graph.

        Args:
            app_id: Application ID to load
            include_tests: Whether to include TestsModelIR (can be heavy)
            use_cache: Whether to check/update in-memory cache

        Returns:
            FullIRGraphLoadResult with ApplicationIR and metadata

        Raises:
            ValueError: If ApplicationIR not found
        """
        start_time = time.perf_counter()

        # Check cache
        if use_cache:
            cached = self._get_from_cache(app_id)
            if cached:
                load_time_ms = (time.perf_counter() - start_time) * 1000
                return FullIRGraphLoadResult(
                    application_ir=cached,
                    load_time_ms=load_time_ms,
                    nodes_loaded=0,
                    relationships_loaded=0,
                    cache_hit=True,
                    metadata={"source": "cache"}
                )

        # Build and execute query
        query = self._build_full_load_query(include_tests)

        with self.driver.session(database=self.database) as session:
            result = session.run(query, app_id=app_id)
            record = result.single()

            if not record:
                raise ValueError(f"ApplicationIR with app_id={app_id} not found")

            # Parse graph into Pydantic models
            app_ir = self._parse_full_graph(record, include_tests)

            # Calculate stats
            nodes_count = record.get("nodes_count", 0) or 0
            rels_count = record.get("relationships_count", 0) or 0

            # Update cache
            if use_cache:
                self._save_to_cache(app_id, app_ir)

            load_time_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "Loaded ApplicationIR %s in %.2fms: %d nodes, %d relationships",
                app_id, load_time_ms, nodes_count, rels_count
            )

            return FullIRGraphLoadResult(
                application_ir=app_ir,
                load_time_ms=load_time_ms,
                nodes_loaded=nodes_count,
                relationships_loaded=rels_count,
                cache_hit=False,
                metadata={
                    "source": "neo4j",
                    "include_tests": include_tests,
                    "entities": len(app_ir.domain_model.entities) if app_ir.domain_model else 0,
                    "endpoints": len(app_ir.api_model.endpoints) if app_ir.api_model else 0,
                }
            )

    def _build_full_load_query(self, include_tests: bool) -> str:
        """
        Build comprehensive Cypher query to load all subgraphs.

        Uses OPTIONAL MATCH for each subgraph allowing partial loads
        when some IRs don't exist yet.
        """
        query = """
        // 1. Match ApplicationIR root
        MATCH (app:ApplicationIR {app_id: $app_id})

        // 2. Load DomainModelIR with Entities, Attributes
        OPTIONAL MATCH (app)-[:HAS_DOMAIN_MODEL]->(dm:DomainModelIR)
        OPTIONAL MATCH (dm)-[:HAS_ENTITY]->(entity:Entity)
        OPTIONAL MATCH (entity)-[:HAS_ATTRIBUTE]->(attr:Attribute)
        OPTIONAL MATCH (entity)-[rel:RELATES_TO]->(target_entity:Entity)

        // 3. Load APIModelIR with Endpoints, Parameters, Schemas
        OPTIONAL MATCH (app)-[:HAS_API_MODEL]->(api:APIModelIR)
        OPTIONAL MATCH (api)-[:HAS_ENDPOINT]->(endpoint:Endpoint)
        OPTIONAL MATCH (endpoint)-[:HAS_PARAMETER]->(param:APIParameter)
        OPTIONAL MATCH (api)-[:HAS_SCHEMA]->(schema:APISchema)
        OPTIONAL MATCH (schema)-[:HAS_FIELD]->(schema_field:APISchemaField)

        // 4. Load BehaviorModelIR with Flows, Steps, Invariants
        OPTIONAL MATCH (app)-[:HAS_BEHAVIOR_MODEL]->(bm:BehaviorModelIR)
        OPTIONAL MATCH (bm)-[:HAS_FLOW]->(flow:Flow)
        OPTIONAL MATCH (flow)-[:HAS_STEP]->(step:Step)
        OPTIONAL MATCH (bm)-[:HAS_INVARIANT]->(inv:Invariant)

        // 5. Load ValidationModelIR with Rules
        OPTIONAL MATCH (app)-[:HAS_VALIDATION_MODEL]->(vm:ValidationModelIR)
        OPTIONAL MATCH (vm)-[:HAS_RULE]->(rule:ValidationRule)

        // 6. Load InfrastructureModelIR
        OPTIONAL MATCH (app)-[:HAS_INFRASTRUCTURE_MODEL]->(im:InfrastructureModelIR)
        """

        if include_tests:
            query += """
        // 7. Load TestsModelIR with SeedEntities, TestScenarios
        OPTIONAL MATCH (app)-[:HAS_TESTS_MODEL]->(tm:TestsModelIR)
        OPTIONAL MATCH (tm)-[:HAS_SEED_ENTITY]->(seed:SeedEntityIR)
        OPTIONAL MATCH (tm)-[:HAS_ENDPOINT_SUITE]->(suite:EndpointTestSuite)
        OPTIONAL MATCH (suite)-[:HAS_SCENARIO]->(scenario:TestScenarioIR)
            """

        query += """
        // 8. Aggregate results
        WITH app, dm, api, bm, vm, im,
             collect(DISTINCT entity) as entities,
             collect(DISTINCT attr) as attributes,
             collect(DISTINCT {source: entity.name, target: target_entity.name, rel: rel}) as relationships,
             collect(DISTINCT endpoint) as endpoints,
             collect(DISTINCT param) as parameters,
             collect(DISTINCT schema) as schemas,
             collect(DISTINCT schema_field) as schema_fields,
             collect(DISTINCT flow) as flows,
             collect(DISTINCT step) as steps,
             collect(DISTINCT inv) as invariants,
             collect(DISTINCT rule) as validation_rules
        """

        if include_tests:
            query += """
             , tm,
             collect(DISTINCT seed) as seed_entities,
             collect(DISTINCT scenario) as test_scenarios
            """

        query += """
        RETURN app,
               dm, entities, attributes, relationships,
               api, endpoints, parameters, schemas, schema_fields,
               bm, flows, steps, invariants,
               vm, validation_rules,
               im
        """

        if include_tests:
            query += """
               , tm, seed_entities, test_scenarios
            """

        query += """
               , size([x IN entities WHERE x IS NOT NULL]) +
                 size([x IN endpoints WHERE x IS NOT NULL]) +
                 size([x IN flows WHERE x IS NOT NULL]) as nodes_count,
               size([x IN attributes WHERE x IS NOT NULL]) +
                 size([x IN parameters WHERE x IS NOT NULL]) +
                 size([x IN steps WHERE x IS NOT NULL]) as relationships_count
        """

        return query

    def _parse_full_graph(self, record, include_tests: bool) -> ApplicationIR:
        """Parse Neo4j record into complete ApplicationIR."""
        # Parse ApplicationIR base
        app_data = dict(record["app"])
        app_id = app_data["app_id"]

        # Parse DomainModelIR
        domain_model = None
        if record["dm"]:
            entities = self._parse_entities(
                record["entities"],
                record["attributes"],
                record["relationships"]
            )
            dm_data = dict(record["dm"])
            metadata = json.loads(dm_data.get("metadata", "{}")) if dm_data.get("metadata") else {}
            domain_model = DomainModelIR(entities=entities, metadata=metadata)
        else:
            # Create empty domain model
            domain_model = DomainModelIR(entities=[])

        # Parse APIModelIR
        api_model = None
        if record["api"]:
            endpoints = self._parse_endpoints(
                record["endpoints"],
                record["parameters"]
            )
            schemas = self._parse_schemas(
                record["schemas"],
                record["schema_fields"]
            )
            api_data = dict(record["api"])
            api_model = APIModelIR(
                endpoints=endpoints,
                schemas=schemas,
                base_path=api_data.get("base_path", ""),
                version=api_data.get("version", "v1")
            )
        else:
            api_model = APIModelIR(endpoints=[], schemas=[])

        # Parse BehaviorModelIR
        behavior_model = None
        if record["bm"]:
            flows = self._parse_flows(record["flows"], record["steps"])
            invariants = self._parse_invariants(record["invariants"])
            behavior_model = BehaviorModelIR(flows=flows, invariants=invariants)
        else:
            behavior_model = BehaviorModelIR()

        # Parse ValidationModelIR
        validation_model = None
        if record["vm"]:
            rules = self._parse_validation_rules(record["validation_rules"])
            validation_model = ValidationModelIR(rules=rules)
        else:
            validation_model = ValidationModelIR()

        # Parse InfrastructureModelIR
        infrastructure_model = None
        if record["im"]:
            im_data = dict(record["im"])
            # Parse database type
            db_type_str = im_data.get("database_type", im_data.get("type", "postgresql"))
            try:
                db_type = DatabaseType(db_type_str)
            except ValueError:
                db_type = DatabaseType.POSTGRESQL

            db_config = DatabaseConfig(
                type=db_type,
                host=im_data.get("host", "localhost"),
                port=im_data.get("port", 5432),
                name=im_data.get("name", im_data.get("database_name", "app_db")),
                user=im_data.get("user", "postgres"),
                password_env_var=im_data.get("password_env_var", "DATABASE_PASSWORD"),
            )
            infrastructure_model = InfrastructureModelIR(database=db_config)
        else:
            # Create default infrastructure model
            db_config = DatabaseConfig(
                type=DatabaseType.POSTGRESQL,
                host="localhost",
                port=5432,
                name="app_db",
                user="postgres",
                password_env_var="DATABASE_PASSWORD",
            )
            infrastructure_model = InfrastructureModelIR(database=db_config)

        # Parse TestsModelIR (optional)
        tests_model = None
        if include_tests and record.get("tm"):
            seed_entities = self._parse_seed_entities(record.get("seed_entities", []))
            test_scenarios = self._parse_test_scenarios(record.get("test_scenarios", []))
            tests_model = TestsModelIR(
                seed_entities=seed_entities,
                endpoint_test_suites=[],  # Built from scenarios
            )
            # Add scenarios to appropriate suites or directly
            for scenario in test_scenarios:
                tests_model.add_scenario(scenario)
        else:
            tests_model = TestsModelIR()

        # Construct complete ApplicationIR
        return ApplicationIR(
            app_id=app_id,
            name=app_data.get("name", ""),
            description=app_data.get("description"),
            domain_model=domain_model,
            api_model=api_model,
            behavior_model=behavior_model,
            validation_model=validation_model,
            infrastructure_model=infrastructure_model,
            tests_model=tests_model,
            version=app_data.get("version", "1.0.0"),
        )

    def _parse_entities(
        self,
        entity_nodes: List,
        attribute_nodes: List,
        relationship_data: List,
    ) -> List[Entity]:
        """Parse Entity nodes with their Attributes and Relationships."""
        if not entity_nodes:
            return []

        # Group attributes by entity
        attrs_by_entity: Dict[str, List[Attribute]] = {}
        for attr_node in attribute_nodes:
            if attr_node is None:
                continue
            entity_id = attr_node.get("entity_id")
            if entity_id:
                if entity_id not in attrs_by_entity:
                    attrs_by_entity[entity_id] = []
                attrs_by_entity[entity_id].append(
                    Attribute(
                        name=attr_node["name"],
                        data_type=DataType(attr_node.get("data_type", "string")),
                        is_primary_key=attr_node.get("is_primary_key", False),
                        is_nullable=attr_node.get("is_nullable", True),
                        is_unique=attr_node.get("is_unique", False),
                        default_value=self._safe_json_loads(attr_node.get("default_value")),
                        description=attr_node.get("description"),
                    )
                )

        # Group relationships by source entity
        rels_by_entity: Dict[str, List[Relationship]] = {}
        for rel_item in relationship_data:
            if rel_item is None or rel_item.get("rel") is None:
                continue
            source = rel_item.get("source")
            target = rel_item.get("target")
            rel = rel_item.get("rel")
            if source and target and rel:
                rel_props = dict(rel) if hasattr(rel, '__iter__') else {}
                if source not in rels_by_entity:
                    rels_by_entity[source] = []
                rels_by_entity[source].append(
                    Relationship(
                        source_entity=source,
                        target_entity=target,
                        type=RelationshipType(rel_props.get("type", "one_to_many")),
                        field_name=rel_props.get("field_name"),
                        back_populates=rel_props.get("back_populates"),
                    )
                )

        # Build Entity list
        entities = []
        for entity_node in entity_nodes:
            if entity_node is None:
                continue
            entity_id = entity_node.get("entity_id")
            entity_name = entity_node.get("name", "")

            entities.append(
                Entity(
                    name=entity_name,
                    attributes=attrs_by_entity.get(entity_id, []),
                    relationships=rels_by_entity.get(entity_name, []),
                    description=entity_node.get("description"),
                    is_aggregate_root=entity_node.get("is_aggregate_root", False),
                )
            )

        return entities

    def _parse_endpoints(
        self,
        endpoint_nodes: List,
        parameter_nodes: List,
    ) -> List[Endpoint]:
        """Parse Endpoint nodes with their Parameters."""
        if not endpoint_nodes:
            return []

        # Group parameters by endpoint
        params_by_endpoint: Dict[str, List[APIParameter]] = {}
        for param_node in parameter_nodes:
            if param_node is None:
                continue
            endpoint_id = param_node.get("endpoint_id")
            if endpoint_id:
                if endpoint_id not in params_by_endpoint:
                    params_by_endpoint[endpoint_id] = []
                params_by_endpoint[endpoint_id].append(
                    APIParameter(
                        name=param_node["name"],
                        location=ParameterLocation(param_node.get("location", "query")),
                        data_type=param_node.get("data_type", "string"),
                        required=param_node.get("required", False),
                        description=param_node.get("description"),
                    )
                )

        # Build Endpoint list
        endpoints = []
        for ep_node in endpoint_nodes:
            if ep_node is None:
                continue
            endpoint_id = ep_node.get("endpoint_id")

            endpoints.append(
                Endpoint(
                    path=ep_node["path"],
                    method=HttpMethod(ep_node.get("method", "GET")),
                    operation_id=ep_node.get("operation_id", ""),
                    summary=ep_node.get("summary"),
                    description=ep_node.get("description"),
                    parameters=params_by_endpoint.get(endpoint_id, []),
                    tags=json.loads(ep_node.get("tags", "[]")) if ep_node.get("tags") else [],
                )
            )

        return endpoints

    def _parse_schemas(
        self,
        schema_nodes: List,
        field_nodes: List,
    ) -> List[APISchema]:
        """Parse APISchema nodes with their fields."""
        if not schema_nodes:
            return []

        # Group fields by schema
        fields_by_schema: Dict[str, List[APISchemaField]] = {}
        for field_node in field_nodes:
            if field_node is None:
                continue
            schema_id = field_node.get("schema_id")
            if schema_id:
                if schema_id not in fields_by_schema:
                    fields_by_schema[schema_id] = []
                fields_by_schema[schema_id].append(
                    APISchemaField(
                        name=field_node["name"],
                        type=field_node.get("type", "string"),
                        required=field_node.get("required", False),
                        description=field_node.get("description"),
                    )
                )

        # Build Schema list
        schemas = []
        for schema_node in schema_nodes:
            if schema_node is None:
                continue
            schema_id = schema_node.get("schema_id")

            schemas.append(
                APISchema(
                    name=schema_node["name"],
                    fields=fields_by_schema.get(schema_id, []),
                )
            )

        return schemas

    def _parse_flows(self, flow_nodes: List, step_nodes: List) -> List[Flow]:
        """Parse Flow nodes with their Steps."""
        if not flow_nodes:
            return []

        # Group steps by flow
        steps_by_flow: Dict[str, List[Step]] = {}
        for step_node in step_nodes:
            if step_node is None:
                continue
            flow_id = step_node.get("flow_id")
            if flow_id:
                if flow_id not in steps_by_flow:
                    steps_by_flow[flow_id] = []
                steps_by_flow[flow_id].append(
                    Step(
                        order=step_node.get("order", step_node.get("sequence", 0)),
                        description=step_node.get("description", ""),
                        action=step_node.get("action", ""),
                        target_entity=step_node.get("target_entity"),
                        condition=step_node.get("condition"),
                    )
                )

        # Build Flow list
        flows = []
        for flow_node in flow_nodes:
            if flow_node is None:
                continue
            flow_id = flow_node.get("flow_id")
            flow_steps = steps_by_flow.get(flow_id, [])
            # Sort steps by order
            flow_steps.sort(key=lambda s: s.order)

            # Parse flow type
            flow_type_str = flow_node.get("type", "workflow")
            try:
                flow_type = FlowType(flow_type_str)
            except ValueError:
                flow_type = FlowType.WORKFLOW

            flows.append(
                Flow(
                    name=flow_node.get("name", ""),
                    type=flow_type,
                    trigger=flow_node.get("trigger", ""),
                    steps=flow_steps,
                    description=flow_node.get("description"),
                )
            )

        return flows

    def _parse_invariants(self, invariant_nodes: List) -> List[Invariant]:
        """Parse Invariant nodes."""
        if not invariant_nodes:
            return []

        invariants = []
        for inv_node in invariant_nodes:
            if inv_node is None:
                continue
            invariants.append(
                Invariant(
                    entity=inv_node.get("entity", inv_node.get("target_entity", "")),
                    description=inv_node.get("description", ""),
                    expression=inv_node.get("expression"),
                    enforcement_level=inv_node.get("enforcement_level", "strict"),
                )
            )

        return invariants

    def _parse_validation_rules(self, rule_nodes: List) -> List[ValidationRule]:
        """Parse ValidationRule nodes."""
        if not rule_nodes:
            return []

        rules = []
        for rule_node in rule_nodes:
            if rule_node is None:
                continue

            # Parse validation type
            rule_type_str = rule_node.get("type", "custom")
            try:
                rule_type = ValidationType(rule_type_str)
            except ValueError:
                rule_type = ValidationType.CUSTOM

            rules.append(
                ValidationRule(
                    entity=rule_node.get("entity", ""),
                    attribute=rule_node.get("attribute", ""),
                    type=rule_type,
                    condition=rule_node.get("condition"),
                    error_message=rule_node.get("error_message"),
                    severity=rule_node.get("severity", "error"),
                )
            )

        return rules

    def _parse_seed_entities(self, seed_nodes: List) -> List[SeedEntityIR]:
        """Parse SeedEntityIR nodes."""
        if not seed_nodes:
            return []

        seeds = []
        for seed_node in seed_nodes:
            if seed_node is None:
                continue

            # Parse fields from JSON
            fields_json = seed_node.get("fields_json", "[]")
            fields_data = json.loads(fields_json) if fields_json else []
            fields = [
                SeedFieldValue(
                    field_name=f.get("field_name", ""),
                    value=f.get("value"),
                    generator=f.get("generator"),
                )
                for f in fields_data
            ]

            seeds.append(
                SeedEntityIR(
                    entity_name=seed_node.get("entity_name", ""),
                    table_name=seed_node.get("table_name", ""),
                    fields=fields,
                    dependencies=json.loads(seed_node.get("dependencies", "[]")),
                    count=seed_node.get("count", 1),
                )
            )

        return seeds

    def _parse_test_scenarios(self, scenario_nodes: List) -> List[TestScenarioIR]:
        """Parse TestScenarioIR nodes."""
        if not scenario_nodes:
            return []

        scenarios = []
        for sc_node in scenario_nodes:
            if sc_node is None:
                continue

            # Parse assertions from JSON
            assertions_json = sc_node.get("assertions_json", "[]")
            assertions_data = json.loads(assertions_json) if assertions_json else []
            assertions = [
                TestAssertion(
                    assertion_type=a.get("assertion_type", "status_code"),
                    path=a.get("path"),
                    operator=a.get("operator", "equals"),
                    expected_value=a.get("expected_value"),
                )
                for a in assertions_data
            ]

            scenarios.append(
                TestScenarioIR(
                    scenario_id=sc_node.get("scenario_id", ""),
                    name=sc_node.get("name", ""),
                    description=sc_node.get("description"),
                    endpoint_path=sc_node.get("endpoint_path", ""),
                    http_method=sc_node.get("http_method", "GET"),
                    operation_id=sc_node.get("operation_id", ""),
                    test_type=TestType(sc_node.get("test_type", "smoke")),
                    priority=TestPriority(sc_node.get("priority", "medium")),
                    expected_status_code=sc_node.get("expected_status_code", 200),
                    assertions=assertions,
                )
            )

        return scenarios

    # ==========================================================================
    # CACHE MANAGEMENT
    # ==========================================================================

    def _get_from_cache(self, app_id: str) -> Optional[ApplicationIR]:
        """Get ApplicationIR from cache if not expired."""
        if app_id not in self._cache:
            return None

        timestamp = self._cache_timestamps.get(app_id)
        if timestamp:
            age_seconds = (datetime.now() - timestamp).total_seconds()
            if age_seconds > self.CACHE_TTL_SECONDS:
                # Cache expired
                del self._cache[app_id]
                del self._cache_timestamps[app_id]
                return None

        logger.debug("Cache hit for app_id=%s", app_id)
        return self._cache[app_id]

    def _save_to_cache(self, app_id: str, app_ir: ApplicationIR):
        """Save ApplicationIR to cache."""
        self._cache[app_id] = app_ir
        self._cache_timestamps[app_id] = datetime.now()
        logger.debug("Cached ApplicationIR for app_id=%s", app_id)

    def invalidate_cache(self, app_id: Optional[str] = None):
        """
        Invalidate cache entries.

        Args:
            app_id: Specific app to invalidate, or None for all
        """
        if app_id:
            self._cache.pop(app_id, None)
            self._cache_timestamps.pop(app_id, None)
            logger.info("Invalidated cache for app_id=%s", app_id)
        else:
            self._cache.clear()
            self._cache_timestamps.clear()
            logger.info("Invalidated all cache entries")

    # ==========================================================================
    # UTILITY METHODS
    # ==========================================================================

    def get_app_ids(self) -> List[str]:
        """Get all available ApplicationIR app_ids."""
        query = """
        MATCH (app:ApplicationIR)
        RETURN app.app_id as app_id
        ORDER BY app.name
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query)
            return [record["app_id"] for record in result]

    def exists(self, app_id: str) -> bool:
        """Check if ApplicationIR exists."""
        query = """
        MATCH (app:ApplicationIR {app_id: $app_id})
        RETURN count(app) > 0 as exists
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, app_id=app_id)
            record = result.single()
            return record["exists"] if record else False

    def get_load_stats(self, app_id: str) -> Dict[str, int]:
        """
        Get statistics about what would be loaded for an app.

        Returns counts without actually loading the full IR.
        """
        query = """
        MATCH (app:ApplicationIR {app_id: $app_id})

        OPTIONAL MATCH (app)-[:HAS_DOMAIN_MODEL]->(dm:DomainModelIR)
        OPTIONAL MATCH (dm)-[:HAS_ENTITY]->(entity:Entity)

        OPTIONAL MATCH (app)-[:HAS_API_MODEL]->(api:APIModelIR)
        OPTIONAL MATCH (api)-[:HAS_ENDPOINT]->(endpoint:Endpoint)

        OPTIONAL MATCH (app)-[:HAS_BEHAVIOR_MODEL]->(bm:BehaviorModelIR)
        OPTIONAL MATCH (bm)-[:HAS_FLOW]->(flow:Flow)

        OPTIONAL MATCH (app)-[:HAS_TESTS_MODEL]->(tm:TestsModelIR)
        OPTIONAL MATCH (tm)-[:HAS_ENDPOINT_SUITE]->(suite:EndpointTestSuite)
        OPTIONAL MATCH (suite)-[:HAS_SCENARIO]->(scenario:TestScenarioIR)

        RETURN
            count(DISTINCT entity) as entities,
            count(DISTINCT endpoint) as endpoints,
            count(DISTINCT flow) as flows,
            count(DISTINCT scenario) as test_scenarios,
            CASE WHEN dm IS NOT NULL THEN 1 ELSE 0 END as has_domain_model,
            CASE WHEN api IS NOT NULL THEN 1 ELSE 0 END as has_api_model,
            CASE WHEN bm IS NOT NULL THEN 1 ELSE 0 END as has_behavior_model,
            CASE WHEN tm IS NOT NULL THEN 1 ELSE 0 END as has_tests_model
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, app_id=app_id)
            record = result.single()

            if not record:
                return {}

            return {
                "entities": record["entities"],
                "endpoints": record["endpoints"],
                "flows": record["flows"],
                "test_scenarios": record["test_scenarios"],
                "has_domain_model": bool(record["has_domain_model"]),
                "has_api_model": bool(record["has_api_model"]),
                "has_behavior_model": bool(record["has_behavior_model"]),
                "has_tests_model": bool(record["has_tests_model"]),
            }
