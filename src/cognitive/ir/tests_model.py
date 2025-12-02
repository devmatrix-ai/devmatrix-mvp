"""
Tests Model Intermediate Representation.

Centralizes all testing logic as a sub-model of ApplicationIR.
Single source of truth for test scenarios, seed data, and validation metrics.

Resolves:
- Bug #129/#130: Path synchronization between IR and generated code
- Code Repair 0%: Unified metrics between repair and compliance
- 7/35 coverage: Deterministic generation from IR (no LLM gaps)
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import uuid


class TestType(str, Enum):
    """Type of test scenario."""
    UNIT = "unit"
    INTEGRATION = "integration"
    SMOKE = "smoke"
    CONTRACT = "contract"
    E2E = "e2e"


class TestPriority(str, Enum):
    """Priority for test execution order."""
    CRITICAL = "critical"  # Health, auth - run first
    HIGH = "high"          # Core CRUD operations
    MEDIUM = "medium"      # Business logic
    LOW = "low"            # Edge cases


class ExpectedOutcome(str, Enum):
    """Expected result of a test scenario."""
    SUCCESS = "success"           # 2xx response
    CLIENT_ERROR = "client_error" # 4xx response
    SERVER_ERROR = "server_error" # 5xx response (for negative tests)
    VALIDATION_ERROR = "validation_error"  # 422


class SeedFieldValue(BaseModel):
    """Value for a seed data field."""
    field_name: str
    value: Any
    generator: Optional[str] = None  # e.g., "uuid4", "random_string", "faker.email"


class SeedEntityIR(BaseModel):
    """
    Seed data entity derived from DomainModelIR.
    Each entity in domain model gets corresponding seed data.
    """
    entity_name: str
    table_name: str  # Actual DB table name (snake_case)
    fields: List[SeedFieldValue] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)  # Entities that must be seeded first
    count: int = 1  # How many instances to seed
    scenario: str = "default"  # Bug #184: Test scenario context (e.g., "smoke_test", "integration")

    # Traceability
    source_entity_id: Optional[str] = None  # Reference to DomainModelIR entity


class TestAssertion(BaseModel):
    """Single assertion in a test scenario."""
    assertion_type: str  # "status_code", "json_path", "header", "response_time"
    path: Optional[str] = None  # JSON path for json_path assertions
    operator: str = "equals"  # "equals", "contains", "greater_than", "exists"
    expected_value: Any


class TestScenarioIR(BaseModel):
    """
    Single test scenario derived deterministically from APIModelIR endpoint.
    """
    scenario_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    description: Optional[str] = None

    # Target endpoint (from APIModelIR)
    endpoint_path: str  # The ACTUAL path to test (single source of truth)
    http_method: str
    operation_id: str

    # Test classification
    test_type: TestType = TestType.SMOKE
    priority: TestPriority = TestPriority.MEDIUM

    # Request configuration
    path_params: Dict[str, Any] = Field(default_factory=dict)
    query_params: Dict[str, Any] = Field(default_factory=dict)
    headers: Dict[str, str] = Field(default_factory=dict)
    request_body: Optional[Dict[str, Any]] = None

    # Expected outcome
    expected_outcome: ExpectedOutcome = ExpectedOutcome.SUCCESS
    expected_status_code: int = 200
    assertions: List[TestAssertion] = Field(default_factory=list)

    # Dependencies
    requires_auth: bool = False
    requires_seed_data: List[str] = Field(default_factory=list)  # Entity names
    depends_on_scenarios: List[str] = Field(default_factory=list)  # scenario_ids

    # Traceability
    source_endpoint_id: Optional[str] = None  # Reference to APIModelIR endpoint


class EndpointTestSuite(BaseModel):
    """
    Collection of test scenarios for a single endpoint.
    Includes happy path + edge cases.
    """
    endpoint_path: str
    http_method: str
    operation_id: str

    # Scenarios
    happy_path: TestScenarioIR  # Primary success case
    edge_cases: List[TestScenarioIR] = Field(default_factory=list)
    error_cases: List[TestScenarioIR] = Field(default_factory=list)

    # Coverage tracking
    covered_parameters: List[str] = Field(default_factory=list)
    covered_response_codes: List[int] = Field(default_factory=list)


class FlowTestSuite(BaseModel):
    """
    Multi-endpoint test flow derived from BehaviorModelIR.
    Tests business workflows spanning multiple endpoints.
    """
    flow_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    description: Optional[str] = None

    # Ordered sequence of scenarios
    scenarios: List[TestScenarioIR]

    # Flow configuration
    cleanup_after: bool = True
    timeout_seconds: int = 60

    # Traceability
    source_flow_name: Optional[str] = None  # Reference to BehaviorModelIR flow


class MetricThreshold(BaseModel):
    """Threshold configuration for a metric."""
    metric_name: str
    warning_threshold: float
    critical_threshold: float
    unit: str = "percent"  # "percent", "ms", "count"


class MetricsConfigIR(BaseModel):
    """
    Metrics and thresholds for test validation.
    Unified metrics for compliance checker, code repair, and smoke tests.
    """
    # Coverage thresholds
    min_endpoint_coverage: float = 100.0  # All endpoints must be tested
    min_scenario_pass_rate: float = 80.0  # Minimum pass rate

    # Performance thresholds
    max_response_time_ms: int = 5000
    max_startup_time_ms: int = 30000

    # Quality thresholds
    thresholds: List[MetricThreshold] = Field(default_factory=lambda: [
        MetricThreshold(
            metric_name="endpoint_coverage",
            warning_threshold=90.0,
            critical_threshold=80.0,
            unit="percent"
        ),
        MetricThreshold(
            metric_name="smoke_pass_rate",
            warning_threshold=90.0,
            critical_threshold=70.0,
            unit="percent"
        ),
        MetricThreshold(
            metric_name="response_time_p95",
            warning_threshold=2000,
            critical_threshold=5000,
            unit="ms"
        ),
    ])


class TestsModelIR(BaseModel):
    """
    Root model for all testing configuration.
    Single source of truth for test generation, execution, and validation.
    """
    # Seed data (derived from DomainModelIR)
    seed_entities: List[SeedEntityIR] = Field(default_factory=list)

    # Endpoint tests (derived from APIModelIR)
    endpoint_suites: List[EndpointTestSuite] = Field(default_factory=list)

    # Flow tests (derived from BehaviorModelIR)
    flow_suites: List[FlowTestSuite] = Field(default_factory=list)

    # Standalone scenarios (for special cases)
    standalone_scenarios: List[TestScenarioIR] = Field(default_factory=list)

    # Metrics configuration
    metrics_config: MetricsConfigIR = Field(default_factory=MetricsConfigIR)

    # Generation metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    generator_version: str = "1.0.0"
    source_ir_hash: Optional[str] = None  # Hash of source IR for cache invalidation

    # ============================================================
    # Convenience Methods
    # ============================================================

    def get_all_scenarios(self) -> List[TestScenarioIR]:
        """Get all test scenarios (endpoint + flow + standalone)."""
        scenarios = []

        for suite in self.endpoint_suites:
            scenarios.append(suite.happy_path)
            scenarios.extend(suite.edge_cases)
            scenarios.extend(suite.error_cases)

        for flow in self.flow_suites:
            scenarios.extend(flow.scenarios)

        scenarios.extend(self.standalone_scenarios)

        return scenarios

    def get_scenarios_by_priority(self, priority: TestPriority) -> List[TestScenarioIR]:
        """Get scenarios filtered by priority."""
        return [s for s in self.get_all_scenarios() if s.priority == priority]

    def get_scenarios_for_endpoint(self, path: str, method: str) -> List[TestScenarioIR]:
        """Get all scenarios for a specific endpoint."""
        return [
            s for s in self.get_all_scenarios()
            if s.endpoint_path == path and s.http_method.upper() == method.upper()
        ]

    def get_smoke_scenarios(self) -> List[TestScenarioIR]:
        """Get only smoke test scenarios (quick validation)."""
        return [s for s in self.get_all_scenarios() if s.test_type == TestType.SMOKE]

    def get_seed_order(self) -> List[str]:
        """Get entity names in dependency order for seeding."""
        # Topological sort based on dependencies
        ordered = []
        visited = set()

        def visit(entity_name: str):
            if entity_name in visited:
                return
            visited.add(entity_name)

            entity = next((e for e in self.seed_entities if e.entity_name == entity_name), None)
            if entity:
                for dep in entity.dependencies:
                    visit(dep)
                ordered.append(entity_name)

        for entity in self.seed_entities:
            visit(entity.entity_name)

        return ordered

    def get_coverage_stats(self) -> Dict[str, Any]:
        """Get test coverage statistics."""
        all_scenarios = self.get_all_scenarios()

        unique_endpoints = set()
        for s in all_scenarios:
            unique_endpoints.add(f"{s.http_method} {s.endpoint_path}")

        return {
            "total_scenarios": len(all_scenarios),
            "endpoint_suites": len(self.endpoint_suites),
            "flow_suites": len(self.flow_suites),
            "unique_endpoints_tested": len(unique_endpoints),
            "seed_entities": len(self.seed_entities),
            "by_type": {
                t.value: len([s for s in all_scenarios if s.test_type == t])
                for t in TestType
            },
            "by_priority": {
                p.value: len([s for s in all_scenarios if s.priority == p])
                for p in TestPriority
            }
        }
