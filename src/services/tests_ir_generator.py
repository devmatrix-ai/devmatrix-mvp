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
    DEFAULT_VALUES = {
        DataType.STRING: "test_string",
        DataType.INTEGER: 1,
        DataType.FLOAT: 1.0,
        DataType.BOOLEAN: True,
        DataType.DATETIME: "2025-01-01T00:00:00Z",
        DataType.UUID: "00000000-0000-4000-8000-000000000099",  # Seed-compatible fallback
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
        self._build_entity_map()

    def _build_entity_map(self):
        """Build lookup map for entities."""
        for entity in self.app_ir.get_entities():
            self._entity_map[entity.name.lower()] = entity
            # Also map singular/plural variants
            if entity.name.lower().endswith('s'):
                self._entity_map[entity.name.lower()[:-1]] = entity
            else:
                self._entity_map[entity.name.lower() + 's'] = entity

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
            value = self._get_default_value(attr.data_type, attr.name)

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

    def _get_default_value(self, data_type: DataType, field_name: str) -> Any:
        """Get appropriate default value for field."""
        # Special cases by field name
        if 'email' in field_name.lower():
            return "test@example.com"
        if 'name' in field_name.lower():
            return "Test Name"
        if 'price' in field_name.lower():
            return 99.99
        if 'quantity' in field_name.lower() or 'count' in field_name.lower():
            return 1
        if 'status' in field_name.lower():
            return "active"
        if 'description' in field_name.lower():
            return "Test description"

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
            error_cases.append(TestScenarioIR(
                name=f"{endpoint.operation_id}_not_found",
                description="Test with non-existent resource ID",
                endpoint_path=endpoint.path,
                http_method=endpoint.method.value,
                operation_id=endpoint.operation_id,
                test_type=TestType.SMOKE,
                priority=TestPriority.MEDIUM,
                path_params={p.name: "00000000-0000-0000-0000-000000000000" for p in path_params},
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
            error_cases.append(TestScenarioIR(
                name=f"{endpoint.operation_id}_validation_error",
                description="Test with invalid request body",
                endpoint_path=endpoint.path,
                http_method=endpoint.method.value,
                operation_id=endpoint.operation_id,
                test_type=TestType.SMOKE,
                priority=TestPriority.MEDIUM,
                request_body={},  # Empty body should fail validation
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
            # Bug #144: Use seed-compatible UUIDs based on field name
            # These must match the UUIDs in seed_db.py and smoke_runner_v2.py
            seed_uuids = {
                'product': '00000000-0000-4000-8000-000000000001',
                'customer': '00000000-0000-4000-8000-000000000002',
                'cart': '00000000-0000-4000-8000-000000000003',
                'order': '00000000-0000-4000-8000-000000000005',
                'item': '00000000-0000-4000-8000-000000000006',
                'user': '00000000-0000-4000-8000-000000000002',
            }
            # Derive entity type from field name (e.g., customer_id -> customer)
            for entity, uuid_val in seed_uuids.items():
                if entity in field_lower:
                    return uuid_val
            # Fallback to a valid generic UUID for unknown FK fields
            return "00000000-0000-4000-8000-000000000099"

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
