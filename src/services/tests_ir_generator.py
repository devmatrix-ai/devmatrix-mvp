"""
Tests IR Generator.

Generates TestsModelIR deterministically from ApplicationIR.
NO LLM calls - pure algorithmic generation ensuring 100% coverage.

Resolves:
- 7/35 coverage: Deterministic generation covers ALL endpoints
- Path sync: Uses exact paths from APIModelIR
- Seed data: Derives from DomainModelIR fields
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib
import re

from src.cognitive.ir.application_ir import ApplicationIR
from src.cognitive.ir.tests_model import (
    TestsModelIR,
    TestScenarioIR,
    EndpointTestSuite,
    FlowTestSuite,
    SeedEntityIR,
    SeedFieldValue,
    TestAssertion,
    MetricsConfigIR,
    TestType,
    TestPriority,
    ExpectedOutcome,
)
from src.core.uuid_registry import SeedUUIDRegistry
from src.cognitive.ir.api_model import Endpoint, HttpMethod
from src.cognitive.ir.domain_model import Entity, DataType


class TestsIRGenerator:
    """
    Deterministic generator for TestsModelIR.

    Generates:
    1. SeedEntityIR for each entity in DomainModelIR
    2. EndpointTestSuite for each endpoint in APIModelIR
    3. FlowTestSuite for each flow in BehaviorModelIR
    """

    # Default test values by data type
    # Bug #144: UUIDs must use seed-compatible format (4000-8000 pattern)
    # Bug #192: Use SeedUUIDRegistry.NOT_FOUND_UUID for consistency
    DEFAULT_VALUES = {
        DataType.STRING: "test_string",
        DataType.INTEGER: 1,
        DataType.FLOAT: 1.0,
        DataType.BOOLEAN: True,
        DataType.DATETIME: "2025-01-01T00:00:00Z",
        DataType.UUID: SeedUUIDRegistry.NOT_FOUND_UUID,  # Centralized not-found UUID
        DataType.JSON: {},
        DataType.ENUM: None,  # Will use first enum value
    }

    # Priority mapping by endpoint pattern
    PRIORITY_PATTERNS = {
        r"/health": TestPriority.CRITICAL,
        r"/auth": TestPriority.CRITICAL,
        r"/login": TestPriority.CRITICAL,
        r".*": TestPriority.MEDIUM,  # Default
    }

    def __init__(self, app_ir: ApplicationIR):
        self.app_ir = app_ir
        self._entity_map: Dict[str, Entity] = {}
        self._constraint_cache: Dict[str, Dict[str, Any]] = {}  # Phase 1.2: Cache field constraints
        self._build_entity_map()
        self._build_constraint_cache()  # Phase 1.2: Build constraint lookup

    def _build_constraint_cache(self):
        """Phase 1.2: Build cache of field constraints from ValidationModelIR.

        This enables domain-agnostic value generation based on:
        - min/max values for RANGE constraints
        - enum values for STATUS_TRANSITION constraints
        - format patterns for FORMAT constraints
        """
        if not self.app_ir.validation_model:
            return

        for rule in self.app_ir.validation_model.rules:
            key = f"{rule.entity}.{rule.attribute}"
            if key not in self._constraint_cache:
                self._constraint_cache[key] = {}

            # Extract constraint info based on type
            from src.cognitive.ir.validation_model import ValidationType

            if rule.type == ValidationType.RANGE:
                # Parse "min: X, max: Y" or "ge=X" patterns
                condition = rule.condition or ""
                if "min" in condition.lower():
                    try:
                        min_val = float(re.search(r'min[:\s=]*(\d+\.?\d*)', condition, re.I).group(1))
                        self._constraint_cache[key]["min"] = min_val
                    except:
                        pass
                if "max" in condition.lower():
                    try:
                        max_val = float(re.search(r'max[:\s=]*(\d+\.?\d*)', condition, re.I).group(1))
                        self._constraint_cache[key]["max"] = max_val
                    except:
                        pass
                if "ge=" in condition or ">=" in condition:
                    try:
                        ge_val = float(re.search(r'(?:ge=|>=)\s*(\d+\.?\d*)', condition).group(1))
                        self._constraint_cache[key]["min"] = ge_val
                    except:
                        pass

            elif rule.type == ValidationType.STATUS_TRANSITION:
                # Parse "one of: X, Y, Z" pattern
                condition = rule.condition or ""
                if "one of" in condition.lower():
                    values = re.findall(r'[A-Z_]+', condition.split("one of")[-1])
                    if values:
                        self._constraint_cache[key]["enum_values"] = values
                        self._constraint_cache[key]["default_value"] = values[0]  # First is usually initial state

            elif rule.type == ValidationType.FORMAT:
                # Store format type
                condition = rule.condition or ""
                if "email" in condition.lower():
                    self._constraint_cache[key]["format"] = "email"
                elif "uuid" in condition.lower():
                    self._constraint_cache[key]["format"] = "uuid"

            elif rule.type == ValidationType.PRESENCE:
                self._constraint_cache[key]["required"] = True

    def _get_value_from_constraints(self, entity_name: str, field_name: str, data_type: DataType) -> Optional[Any]:
        """Phase 1.2: Get valid value based on IR constraints.

        Returns None if no constraints found (fallback to default).
        """
        key = f"{entity_name}.{field_name}"
        constraints = self._constraint_cache.get(key, {})

        if not constraints:
            return None

        # Enum/status values
        if "default_value" in constraints:
            return constraints["default_value"]

        # Range constraints - generate valid value
        if "min" in constraints:
            min_val = constraints["min"]
            if data_type == DataType.INTEGER:
                return int(min_val) + 1  # min + 1 to be safely valid
            elif data_type == DataType.FLOAT:
                return float(min_val) + 0.01

        # Format constraints
        if constraints.get("format") == "email":
            return "test@example.com"
        elif constraints.get("format") == "uuid":
            return SeedUUIDRegistry.NOT_FOUND_UUID

        return None

    def _build_entity_map(self) -> None:
        """Build lookup map for entities."""
        for entity in self.app_ir.get_entities():
            self._entity_map[entity.name.lower()] = entity
            # Also map singular/plural variants
            if entity.name.lower().endswith('s'):
                self._entity_map[entity.name.lower()[:-1]] = entity
            else:
                self._entity_map[entity.name.lower() + 's'] = entity

    def _build_entity_uuid_map(self) -> Dict[str, str]:
        """Phase 1.2: Build entity → UUID map using centralized SeedUUIDRegistry.

        Bug #192 Fix: Use SeedUUIDRegistry for consistent UUIDs across:
        - tests_ir_generator.py (this file)
        - code_generation_service.py (seed_db.py generation)
        - smoke_runner_v2.py (test execution)
        """
        entities = self.app_ir.get_entities()
        entity_names = [e.name for e in entities]

        # Use centralized registry
        registry = SeedUUIDRegistry.from_entity_names(entity_names)

        uuid_map = {}
        for entity in entities:
            entity_name = entity.name.lower()
            try:
                uuid_val = registry.get_uuid(entity.name, "primary")
                uuid_map[entity_name] = uuid_val

                # Also map singular/plural variants
                if entity_name.endswith('s'):
                    uuid_map[entity_name[:-1]] = uuid_val
                else:
                    uuid_map[entity_name + 's'] = uuid_val
            except ValueError:
                pass  # Entity not in registry

        return uuid_map

    def generate(self) -> TestsModelIR:
        """Generate complete TestsModelIR from ApplicationIR."""
        # Generate IR hash for cache invalidation
        ir_hash = self._compute_ir_hash()

        tests_model = TestsModelIR(
            seed_entities=self._generate_seed_entities(),
            endpoint_suites=self._generate_endpoint_suites(),
            flow_suites=self._generate_flow_suites(),
            standalone_scenarios=self._generate_standalone_scenarios(),
            metrics_config=self._generate_metrics_config(),
            generated_at=datetime.utcnow(),
            generator_version="1.0.0",
            source_ir_hash=ir_hash,
        )

        return tests_model

    def _compute_ir_hash(self) -> str:
        """Compute hash of source IR for cache invalidation."""
        # Hash key components that affect test generation
        components = [
            str(len(self.app_ir.get_entities())),
            str(len(self.app_ir.get_endpoints())),
            str(len(self.app_ir.get_flows())),
        ]
        for ep in self.app_ir.get_endpoints():
            components.append(f"{ep.method.value}:{ep.path}")

        content = "|".join(components)
        return hashlib.md5(content.encode()).hexdigest()[:12]

    # ============================================================
    # Seed Entity Generation
    # ============================================================

    def _generate_seed_entities(self) -> List[SeedEntityIR]:
        """Generate seed entities from DomainModelIR."""
        seed_entities = []

        for entity in self.app_ir.get_entities():
            seed_entity = self._generate_seed_for_entity(entity)
            seed_entities.append(seed_entity)

        # Sort by dependencies (simple topological sort)
        return self._sort_by_dependencies(seed_entities)

    def _generate_seed_for_entity(self, entity: Entity) -> SeedEntityIR:
        """Generate seed data for a single entity."""
        fields = []
        dependencies = []

        for attr in entity.attributes:
            # Skip auto-generated fields
            if attr.is_primary_key and attr.data_type == DataType.UUID:
                continue
            if attr.name in ['created_at', 'updated_at']:
                continue

            # Get default value for type
            # Bug #167: Pass entity name for business-appropriate status values
            value = self._get_default_value(attr.data_type, attr.name, entity.name)

            # Handle foreign keys (detect by name pattern)
            if attr.name.endswith('_id'):
                ref_entity = attr.name[:-3]  # Remove '_id'
                if ref_entity in self._entity_map:
                    dependencies.append(ref_entity)
                    value = f"{{{{ref:{ref_entity}.id}}}}"  # Placeholder for actual ID

            fields.append(SeedFieldValue(
                field_name=attr.name,
                value=value,
                generator=self._get_generator(attr.data_type, attr.name)
            ))

        return SeedEntityIR(
            entity_name=entity.name,
            table_name=self._to_snake_case(entity.name) + 's',  # Pluralize for table
            fields=fields,
            dependencies=dependencies,
            count=1,
            source_entity_id=entity.name,
        )

    def _get_default_value(self, data_type: DataType, field_name: str, entity_name: str = "") -> Any:
        """Get appropriate default value for field.

        100% domain-agnostic: Uses only IR constraints and type information.
        """
        # Try IR constraints FIRST (domain-agnostic)
        if entity_name:
            constraint_value = self._get_value_from_constraints(entity_name, field_name, data_type)
            if constraint_value is not None:
                return constraint_value

        # Type-based defaults only (domain-agnostic)
        return self.DEFAULT_VALUES.get(data_type, "test")

    def _get_generator(self, data_type: DataType, field_name: str) -> Optional[str]:
        """Get generator function name for dynamic values."""
        if data_type == DataType.UUID:
            return "uuid4"
        if 'email' in field_name.lower():
            return "faker.email"
        return None

    def _sort_by_dependencies(self, entities: List[SeedEntityIR]) -> List[SeedEntityIR]:
        """Sort entities by dependencies (topological sort)."""
        sorted_entities = []
        visited = set()
        entity_map = {e.entity_name.lower(): e for e in entities}

        def visit(name: str):
            if name.lower() in visited:
                return
            visited.add(name.lower())

            entity = entity_map.get(name.lower())
            if entity:
                for dep in entity.dependencies:
                    visit(dep)
                sorted_entities.append(entity)

        for entity in entities:
            visit(entity.entity_name)

        return sorted_entities

    # ============================================================
    # Endpoint Test Suite Generation
    # ============================================================

    def _generate_endpoint_suites(self) -> List[EndpointTestSuite]:
        """Generate test suites for all endpoints."""
        suites = []

        for endpoint in self.app_ir.get_endpoints():
            suite = self._generate_suite_for_endpoint(endpoint)
            suites.append(suite)

        return suites

    def _generate_suite_for_endpoint(self, endpoint: Endpoint) -> EndpointTestSuite:
        """Generate complete test suite for a single endpoint."""
        # Generate happy path scenario
        happy_path = self._generate_happy_path(endpoint)

        # Generate edge cases
        edge_cases = self._generate_edge_cases(endpoint)

        # Generate error cases
        error_cases = self._generate_error_cases(endpoint)

        return EndpointTestSuite(
            endpoint_path=endpoint.path,
            http_method=endpoint.method.value,
            operation_id=endpoint.operation_id,
            happy_path=happy_path,
            edge_cases=edge_cases,
            error_cases=error_cases,
            covered_parameters=[p.name for p in endpoint.parameters],
            covered_response_codes=[happy_path.expected_status_code] +
                                   [e.expected_status_code for e in error_cases],
        )

    def _generate_happy_path(self, endpoint: Endpoint) -> TestScenarioIR:
        """Generate happy path test for endpoint."""
        priority = self._get_priority(endpoint.path)

        # Build path params
        path_params = {}
        for param in endpoint.parameters:
            if param.location.value == "path":
                path_params[param.name] = self._get_param_value(param.data_type, param.name)

        # Build request body for POST/PUT/PATCH
        request_body = None
        if endpoint.method in [HttpMethod.POST, HttpMethod.PUT, HttpMethod.PATCH]:
            request_body = self._generate_request_body(endpoint)

        # Expected status code
        expected_status = self._get_expected_status(endpoint.method)

        # Build assertions
        assertions = [
            TestAssertion(
                assertion_type="status_code",
                operator="equals",
                expected_value=expected_status
            )
        ]

        # Add response body assertions for GET/POST
        if endpoint.method in [HttpMethod.GET, HttpMethod.POST]:
            assertions.append(TestAssertion(
                assertion_type="response_time",
                operator="less_than",
                expected_value=5000
            ))

        # Determine required seed data
        requires_seed = self._get_required_seeds(endpoint)

        return TestScenarioIR(
            name=f"{endpoint.operation_id}_happy_path",
            description=f"Happy path test for {endpoint.method.value} {endpoint.path}",
            endpoint_path=endpoint.path,
            http_method=endpoint.method.value,
            operation_id=endpoint.operation_id,
            test_type=TestType.SMOKE,
            priority=priority,
            path_params=path_params,
            request_body=request_body,
            expected_outcome=ExpectedOutcome.SUCCESS,
            expected_status_code=expected_status,
            assertions=assertions,
            requires_auth=endpoint.auth_required,
            requires_seed_data=requires_seed,
            source_endpoint_id=endpoint.operation_id,
        )

    def _generate_edge_cases(self, endpoint: Endpoint) -> List[TestScenarioIR]:
        """Generate edge case tests for endpoint."""
        edge_cases = []

        # Bug #191 Fix: Build path params for edge cases (same as happy_path)
        # Path params are REQUIRED even for edge cases - only query params are optional
        path_params = {}
        for param in endpoint.parameters:
            if param.location.value == "path":
                path_params[param.name] = self._get_param_value(param.data_type, param.name)

        # Empty query params test for GET with optional params
        if endpoint.method == HttpMethod.GET:
            optional_params = [p for p in endpoint.parameters if not p.required]
            if optional_params:
                edge_cases.append(TestScenarioIR(
                    name=f"{endpoint.operation_id}_no_optional_params",
                    description="Test without optional parameters",
                    endpoint_path=endpoint.path,
                    http_method=endpoint.method.value,
                    operation_id=endpoint.operation_id,
                    test_type=TestType.SMOKE,
                    priority=TestPriority.LOW,
                    path_params=path_params,  # Bug #191: Include required path params
                    expected_outcome=ExpectedOutcome.SUCCESS,
                    expected_status_code=200,
                    requires_auth=endpoint.auth_required,
                ))

        return edge_cases

    def _generate_error_cases(self, endpoint: Endpoint) -> List[TestScenarioIR]:
        """Generate error case tests for endpoint."""
        error_cases = []

        # 404 test for endpoints with path params
        path_params = [p for p in endpoint.parameters if p.location.value == "path"]
        if path_params and endpoint.method != HttpMethod.POST:
            # Bug #186 Fix: PUT/PATCH need valid request_body to avoid 422 before 404
            # FastAPI validates body BEFORE executing the handler, so we need a valid body
            # to get past validation and reach the existence check that returns 404
            request_body_for_404 = None
            if endpoint.method in [HttpMethod.PUT, HttpMethod.PATCH] and endpoint.request_schema:
                request_body_for_404 = self._generate_request_body(endpoint)

            error_cases.append(TestScenarioIR(
                name=f"{endpoint.operation_id}_not_found",
                description="Test with non-existent resource ID",
                endpoint_path=endpoint.path,
                http_method=endpoint.method.value,
                operation_id=endpoint.operation_id,
                test_type=TestType.SMOKE,
                priority=TestPriority.MEDIUM,
                path_params={p.name: "00000000-0000-0000-0000-000000000000" for p in path_params},
                request_body=request_body_for_404,  # Bug #186: Include body for PUT/PATCH
                expected_outcome=ExpectedOutcome.CLIENT_ERROR,
                expected_status_code=404,
                assertions=[TestAssertion(
                    assertion_type="status_code",
                    operator="equals",
                    expected_value=404
                )],
                requires_auth=endpoint.auth_required,
            ))

        # 422 validation error for POST/PUT with invalid body
        if endpoint.method in [HttpMethod.POST, HttpMethod.PUT] and endpoint.request_schema:
            # Generate invalid body that will trigger validation error
            invalid_body = self._generate_invalid_request_body(endpoint)
            error_cases.append(TestScenarioIR(
                name=f"{endpoint.operation_id}_validation_error",
                description="Test with invalid request body",
                endpoint_path=endpoint.path,
                http_method=endpoint.method.value,
                operation_id=endpoint.operation_id,
                test_type=TestType.SMOKE,
                priority=TestPriority.MEDIUM,
                request_body=invalid_body,
                expected_outcome=ExpectedOutcome.VALIDATION_ERROR,
                expected_status_code=422,
                assertions=[TestAssertion(
                    assertion_type="status_code",
                    operator="equals",
                    expected_value=422
                )],
                requires_auth=endpoint.auth_required,
            ))

        return error_cases

    def _get_priority(self, path: str) -> TestPriority:
        """Determine test priority based on endpoint path."""
        for pattern, priority in self.PRIORITY_PATTERNS.items():
            if re.match(pattern, path):
                return priority
        return TestPriority.MEDIUM

    def _get_param_value(self, data_type: str, param_name: str) -> Any:
        """Get test value for a parameter."""
        if 'id' in param_name.lower():
            return "{{seed_id}}"  # Placeholder for seeded ID
        if data_type == "integer":
            return 1
        if data_type == "boolean":
            return True
        return "test"

    def _get_expected_status(self, method: HttpMethod) -> int:
        """Get expected status code for HTTP method."""
        return {
            HttpMethod.GET: 200,
            HttpMethod.POST: 201,
            HttpMethod.PUT: 200,
            HttpMethod.PATCH: 200,
            HttpMethod.DELETE: 204,
        }.get(method, 200)

    def _generate_request_body(self, endpoint: Endpoint) -> Dict[str, Any]:
        """Generate request body from endpoint schema."""
        if not endpoint.request_schema:
            return {}

        body = {}
        for field in endpoint.request_schema.fields:
            if field.required:
                body[field.name] = self._get_field_value(field.type, field.name)

        return body

    def _generate_invalid_request_body(self, endpoint: Endpoint) -> Dict[str, Any]:
        """Generate invalid request body that will trigger 422 validation error.

        Strategy (domain-agnostic):
        1. For POST: omit required fields OR send wrong types
        2. For PUT/PATCH: send invalid values for numeric fields (negative when ge=0)

        Uses IR constraints to determine what values are invalid.
        """
        if not endpoint.request_schema:
            return {}

        # For POST, empty body usually fails if there are required fields
        if endpoint.method == HttpMethod.POST:
            has_required = any(f.required for f in endpoint.request_schema.fields)
            if has_required:
                return {}  # Empty body fails required field validation

        # For PUT/PATCH, we need to send invalid values
        # Find a numeric field and send a negative value
        invalid_body = {}
        for field in endpoint.request_schema.fields:
            field_type = field.type.lower() if field.type else ""
            field_name = field.name.lower() if field.name else ""

            # Look for numeric fields that likely have ge=0 or gt=0 constraints
            if field_type in ['integer', 'int', 'float', 'number', 'decimal']:
                # Check if this field has range constraints in IR
                entity_name = self._infer_entity_from_endpoint(endpoint)
                key = f"{entity_name}.{field.name}"
                constraints = self._constraint_cache.get(key, {})

                # If field has min constraint, send value below it
                if "min" in constraints:
                    min_val = constraints["min"]
                    invalid_body[field.name] = min_val - 1  # Below minimum
                    return invalid_body

                # For numeric fields, test with negative value (domain-agnostic)
                if field.data_type and field.data_type.lower() in ['int', 'integer', 'float', 'decimal', 'number']:
                    invalid_body[field.name] = -1  # Negative value
                    return invalid_body

        # Fallback: send wrong type for first field
        if endpoint.request_schema.fields:
            first_field = endpoint.request_schema.fields[0]
            invalid_body[first_field.name] = {"invalid": "type"}  # Object instead of expected type

        return invalid_body

    def _infer_entity_from_endpoint(self, endpoint: Endpoint) -> str:
        """Infer entity name from endpoint path (domain-agnostic)."""
        # Extract from path like /products/{id} -> Product
        path_parts = endpoint.path.strip('/').split('/')
        if path_parts:
            # First segment is usually the entity plural
            entity_plural = path_parts[0]
            # Convert to singular (simple heuristic)
            if entity_plural.endswith('ies'):
                return entity_plural[:-3] + 'y'
            elif entity_plural.endswith('s'):
                return entity_plural[:-1]
            return entity_plural
        return ""

    def _get_field_value(self, field_type: str, field_name: str) -> Any:
        """Get test value for a schema field.

        Bug #144 Fix: Use seed-compatible UUIDs that match seed_db.py data.
        This ensures FK references point to existing entities during smoke tests.
        """
        type_lower = field_type.lower()
        field_lower = field_name.lower()

        # Map string types to values
        if type_lower in ['string', 'str']:
            if 'email' in field_lower:
                return "test@example.com"
            if 'name' in field_lower:
                return "Test Name"
            return "test_value"
        if type_lower in ['integer', 'int']:
            return 1
        if type_lower in ['float', 'number', 'decimal']:
            return 99.99
        if type_lower in ['boolean', 'bool']:
            return True
        if type_lower == 'uuid':
            # Phase 1.2: Domain-agnostic UUID generation from IR
            # Build UUID map dynamically from entities in IR
            seed_uuids = self._build_entity_uuid_map()

            # Derive entity type from field name (e.g., customer_id -> customer)
            for entity, uuid_val in seed_uuids.items():
                if entity.lower() in field_lower:
                    return uuid_val
            # Bug #192: Use centralized NOT_FOUND_UUID for unknown FK fields
            return SeedUUIDRegistry.NOT_FOUND_UUID

        return "test"

    def _get_required_seeds(self, endpoint: Endpoint) -> List[str]:
        """Determine which entities need to be seeded for this endpoint."""
        seeds = []

        # Extract entity from path (e.g., /products/{id} -> Product)
        path_parts = endpoint.path.strip('/').split('/')
        if path_parts:
            entity_name = path_parts[0].rstrip('s').capitalize()
            if entity_name.lower() in self._entity_map:
                seeds.append(entity_name)

        return seeds

    # ============================================================
    # Flow Test Suite Generation
    # ============================================================

    def _generate_flow_suites(self) -> List[FlowTestSuite]:
        """Generate flow test suites from BehaviorModelIR."""
        suites = []

        for flow in self.app_ir.get_flows():
            suite = self._generate_flow_suite(flow)
            if suite:
                suites.append(suite)

        return suites

    def _generate_flow_suite(self, flow) -> Optional[FlowTestSuite]:
        """Generate test suite for a single flow."""
        scenarios = []

        for step in flow.steps:
            # Try to find matching endpoint for step
            endpoint = self._find_endpoint_for_step(step)
            if endpoint:
                scenario = self._generate_happy_path(endpoint)
                scenario.name = f"{flow.name}_{step.order}_{step.action}"
                scenarios.append(scenario)

        if not scenarios:
            return None

        return FlowTestSuite(
            name=f"flow_{flow.name}",
            description=flow.description,
            scenarios=scenarios,
            cleanup_after=True,
            timeout_seconds=60,
            source_flow_name=flow.name,
        )

    def _find_endpoint_for_step(self, step) -> Optional[Endpoint]:
        """Find endpoint that matches a flow step."""
        # Simple heuristic: match by action keyword
        action_lower = step.action.lower()

        for endpoint in self.app_ir.get_endpoints():
            op_id_lower = endpoint.operation_id.lower()
            if action_lower in op_id_lower or op_id_lower in action_lower:
                return endpoint

        return None

    # ============================================================
    # Standalone & Metrics
    # ============================================================

    def _generate_standalone_scenarios(self) -> List[TestScenarioIR]:
        """Generate standalone scenarios for special cases."""
        scenarios = []

        # Health check scenario (if not already in endpoints)
        health_endpoints = [e for e in self.app_ir.get_endpoints()
                          if 'health' in e.path.lower()]

        if not health_endpoints:
            # Add implicit health check
            scenarios.append(TestScenarioIR(
                name="health_check",
                description="Verify application health endpoint",
                endpoint_path="/health",
                http_method="GET",
                operation_id="health_check",
                test_type=TestType.SMOKE,
                priority=TestPriority.CRITICAL,
                expected_outcome=ExpectedOutcome.SUCCESS,
                expected_status_code=200,
                requires_auth=False,
            ))

        return scenarios

    def _generate_metrics_config(self) -> MetricsConfigIR:
        """Generate metrics configuration."""
        endpoint_count = len(self.app_ir.get_endpoints())

        return MetricsConfigIR(
            min_endpoint_coverage=100.0,  # All endpoints must be tested
            min_scenario_pass_rate=80.0,  # 80% pass rate minimum
            max_response_time_ms=5000,
            max_startup_time_ms=30000,
        )

    # ============================================================
    # Utilities
    # ============================================================

    def _to_snake_case(self, name: str) -> str:
        """Convert CamelCase to snake_case."""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def generate_tests_ir(app_ir: ApplicationIR) -> TestsModelIR:
    """
    Convenience function to generate TestsModelIR from ApplicationIR.

    Usage:
        tests_model = generate_tests_ir(app_ir)
        app_ir.tests_model = tests_model
    """
    generator = TestsIRGenerator(app_ir)
    return generator.generate()
