"""
Smoke Runner V2 - IR-Centric Smoke Test Execution.

Executes smoke tests directly from TestsModelIR.
No LLM, no external planning - pure deterministic execution.

Resolves:
- Path sync: Executes exact paths from TestsModelIR
- Coverage: Tests ALL scenarios in TestsModelIR
- Metrics: Unified metrics compatible with Code Repair
"""
import asyncio
import logging
import httpx
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.cognitive.ir.tests_model import (
    TestsModelIR,
    TestScenarioIR,
    TestPriority,
    ExpectedOutcome,
)

# Bug #9: Silence httpx verbose logging - only show errors
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


class ScenarioStatus(str, Enum):
    """Status of a scenario execution."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class ScenarioResult:
    """Result of executing a single scenario."""
    scenario_id: str
    scenario_name: str
    endpoint_path: str
    http_method: str
    status: ScenarioStatus
    expected_status_code: int
    actual_status_code: Optional[int] = None
    response_time_ms: float = 0.0
    error_message: Optional[str] = None
    response_body: Optional[str] = None


@dataclass
class SmokeTestReport:
    """Complete smoke test execution report."""
    total_scenarios: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    pass_rate: float = 0.0
    total_duration_ms: float = 0.0
    results: List[ScenarioResult] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # IR-centric metrics for Code Repair compatibility
    endpoint_coverage: float = 0.0
    scenarios_by_priority: Dict[str, int] = field(default_factory=dict)
    failed_endpoints: List[str] = field(default_factory=list)


class SmokeRunnerV2:
    """
    IR-centric smoke test runner.

    Executes scenarios directly from TestsModelIR with:
    - Priority-based ordering (critical first)
    - Parallel execution support
    - Unified metrics for Code Repair
    """

    def __init__(
        self,
        tests_model: TestsModelIR,
        base_url: str = "http://localhost:8000",
        timeout_seconds: float = 30.0,
        auth_token: Optional[str] = None,
    ):
        self.tests_model = tests_model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_seconds
        self.auth_token = auth_token

    async def run(
        self,
        priority_filter: Optional[List[TestPriority]] = None,
        max_scenarios: Optional[int] = None,
        stop_on_critical_failure: bool = True,
    ) -> SmokeTestReport:
        """
        Execute smoke tests from TestsModelIR.

        Args:
            priority_filter: Only run scenarios with these priorities
            max_scenarios: Maximum scenarios to run (for quick checks)
            stop_on_critical_failure: Stop if critical priority test fails

        Returns:
            SmokeTestReport with all results and metrics
        """
        report = SmokeTestReport(started_at=datetime.utcnow())

        # Get scenarios in priority order
        scenarios = self._get_ordered_scenarios(priority_filter, max_scenarios)
        report.total_scenarios = len(scenarios)

        if not scenarios:
            report.completed_at = datetime.utcnow()
            return report

        # Execute scenarios
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
        ) as client:
            start_time = time.time()

            for scenario in scenarios:
                result = await self._execute_scenario(client, scenario)
                report.results.append(result)

                # Update counters
                if result.status == ScenarioStatus.PASSED:
                    report.passed += 1
                elif result.status == ScenarioStatus.FAILED:
                    report.failed += 1
                    report.failed_endpoints.append(f"{scenario.http_method} {scenario.endpoint_path}")
                    # Bug #9: Only print failures (not all HTTP requests)
                    print(f"    ❌ {result.http_method} {result.endpoint_path}: expected {result.expected_status_code}, got {result.actual_status_code}")
                elif result.status == ScenarioStatus.SKIPPED:
                    report.skipped += 1
                else:
                    report.errors += 1

                # Stop on critical failure if requested
                if (stop_on_critical_failure and
                    scenario.priority == TestPriority.CRITICAL and
                    result.status != ScenarioStatus.PASSED):
                    break

            report.total_duration_ms = (time.time() - start_time) * 1000

        # Calculate metrics
        report.completed_at = datetime.utcnow()
        report.pass_rate = (report.passed / report.total_scenarios * 100) if report.total_scenarios > 0 else 0.0
        report.endpoint_coverage = self._calculate_endpoint_coverage(report)
        report.scenarios_by_priority = self._count_by_priority(scenarios)

        return report

    def _get_ordered_scenarios(
        self,
        priority_filter: Optional[List[TestPriority]],
        max_scenarios: Optional[int],
    ) -> List[TestScenarioIR]:
        """Get scenarios ordered by priority."""
        scenarios = self.tests_model.get_smoke_scenarios()

        # Filter by priority if specified
        if priority_filter:
            scenarios = [s for s in scenarios if s.priority in priority_filter]

        # Sort by priority (critical first)
        priority_order = {
            TestPriority.CRITICAL: 0,
            TestPriority.HIGH: 1,
            TestPriority.MEDIUM: 2,
            TestPriority.LOW: 3,
        }
        scenarios.sort(key=lambda s: priority_order.get(s.priority, 99))

        # Limit if specified
        if max_scenarios:
            scenarios = scenarios[:max_scenarios]

        return scenarios

    def _build_seed_uuids(self, is_delete: bool = False) -> Dict[str, str]:
        """
        Build seed UUIDs from IR entities (domain-agnostic).

        Phase 1: Generates deterministic UUIDs based on entity order in IR.
        This replaces hardcoded entity name mappings.

        Args:
            is_delete: If True, return delete variant UUIDs (offset by 10)

        Returns:
            Dict mapping entity name (lowercase) to UUID string
        """
        uuid_base = "00000000-0000-4000-8000-0000000000"
        offset = 10 if is_delete else 0
        item_offset = 20 if not is_delete else 21  # Item entities start at 20/21

        seed_uuids = {}
        item_counter = 0

        # Get entities from TestsModelIR seed_scenarios
        if hasattr(self.tests_model, 'seed_scenarios'):
            for idx, seed in enumerate(self.tests_model.seed_scenarios, start=1):
                entity_name = seed.entity_name.lower()
                # Detect join tables (entities ending with 'item')
                if 'item' in entity_name:
                    uuid_num = item_offset + item_counter
                    item_counter += 1
                else:
                    uuid_num = idx + offset
                seed_uuids[entity_name] = f"{uuid_base}{uuid_num:02d}"

        # Fallback: Extract from scenarios if no seed_scenarios
        if not seed_uuids and hasattr(self.tests_model, 'scenarios'):
            seen_entities = set()
            idx = 1
            for scenario in self.tests_model.scenarios:
                entity = self._derive_entity_from_path(scenario.endpoint_path)
                if entity and entity not in seen_entities:
                    seen_entities.add(entity)
                    if 'item' in entity:
                        uuid_num = item_offset + item_counter
                        item_counter += 1
                    else:
                        uuid_num = idx + offset
                        idx += 1
                    seed_uuids[entity] = f"{uuid_base}{uuid_num:02d}"

        # Add 'item' alias for generic item references
        if 'item' not in seed_uuids:
            seed_uuids['item'] = f"{uuid_base}{item_offset:02d}"

        return seed_uuids

    async def _execute_scenario(
        self,
        client: httpx.AsyncClient,
        scenario: TestScenarioIR,
    ) -> ScenarioResult:
        """Execute a single test scenario."""
        # Build actual path with params
        # Phase 1: Domain-agnostic UUID generation from IR entities
        # Bug #136 Fix: Use predictable UUIDs that match seed_db.py
        # Bug #187 Fix: DELETE tests use secondary UUIDs to not destroy seed data
        seed_uuids_primary = self._build_seed_uuids(is_delete=False)
        seed_uuids_delete = self._build_seed_uuids(is_delete=True)

        # Bug #187: Choose UUID set based on HTTP method
        is_delete = scenario.http_method.upper() == "DELETE"
        seed_uuids = seed_uuids_delete if is_delete else seed_uuids_primary

        path = scenario.endpoint_path

        # Bug #191: Auto-detect missing path params from endpoint_path
        # Some edge_cases have empty path_params but still have {param} in path
        import re
        path_param_names = re.findall(r'\{(\w+)\}', scenario.endpoint_path)
        effective_path_params = dict(scenario.path_params)
        for param_name in path_param_names:
            if param_name not in effective_path_params:
                # Auto-fill with seed UUID based on param name
                effective_path_params[param_name] = "{{seed_id}}"

        for param_name, param_value in effective_path_params.items():
            # Handle placeholder values (e.g., {{seed_id}})
            if isinstance(param_value, str) and param_value.startswith("{{"):
                # Bug #137 Fix: Derive entity type from param name OR path context
                if param_name == 'id':
                    # Generic {id} - derive from path (e.g., /products/{id} -> product)
                    entity_type = self._derive_entity_from_path(scenario.endpoint_path)
                else:
                    # Specific param name (e.g., product_id -> product)
                    entity_type = param_name.replace('_id', '').lower()

                # Domain-agnostic: For item subresource paths, use PRIMARY parent UUID
                # Item entities reference primary parent entity, not delete variant
                is_item_subpath = '/items/' in scenario.endpoint_path
                if is_item_subpath and param_name.endswith('_id') and param_name != 'id':
                    # Use primary UUID for the referenced parent entity
                    parent_entity = param_name.replace('_id', '')
                    param_value = seed_uuids_primary.get(parent_entity, seed_uuids_primary.get(list(seed_uuids_primary.keys())[0] if seed_uuids_primary else 'unknown', '00000000-0000-4000-8000-000000000001'))
                else:
                    param_value = seed_uuids.get(entity_type, '00000000-0000-4000-8000-000000000099')
            # Bug #137: Do NOT convert zero UUIDs - they're intentional for _not_found tests
            path = path.replace(f"{{{param_name}}}", str(param_value))

        # Build headers
        headers = dict(scenario.headers)
        if scenario.requires_auth and self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        # Execute request
        start_time = time.time()
        try:
            response = await self._make_request(
                client,
                method=scenario.http_method,
                path=path,
                headers=headers,
                params=scenario.query_params or None,
                json_body=scenario.request_body,
            )

            elapsed_ms = (time.time() - start_time) * 1000

            # Check result
            status = self._evaluate_response(scenario, response)

            return ScenarioResult(
                scenario_id=scenario.scenario_id,
                scenario_name=scenario.name,
                endpoint_path=scenario.endpoint_path,
                http_method=scenario.http_method,
                status=status,
                expected_status_code=scenario.expected_status_code,
                actual_status_code=response.status_code,
                response_time_ms=elapsed_ms,
                response_body=response.text[:500] if response.text else None,
            )

        except httpx.TimeoutException as e:
            return ScenarioResult(
                scenario_id=scenario.scenario_id,
                scenario_name=scenario.name,
                endpoint_path=scenario.endpoint_path,
                http_method=scenario.http_method,
                status=ScenarioStatus.ERROR,
                expected_status_code=scenario.expected_status_code,
                error_message=f"Timeout: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
            )

        except httpx.RequestError as e:
            return ScenarioResult(
                scenario_id=scenario.scenario_id,
                scenario_name=scenario.name,
                endpoint_path=scenario.endpoint_path,
                http_method=scenario.http_method,
                status=ScenarioStatus.ERROR,
                expected_status_code=scenario.expected_status_code,
                error_message=f"Request error: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            return ScenarioResult(
                scenario_id=scenario.scenario_id,
                scenario_name=scenario.name,
                endpoint_path=scenario.endpoint_path,
                http_method=scenario.http_method,
                status=ScenarioStatus.ERROR,
                expected_status_code=scenario.expected_status_code,
                error_message=f"Unexpected error: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
            )

    async def _make_request(
        self,
        client: httpx.AsyncClient,
        method: str,
        path: str,
        headers: Dict[str, str],
        params: Optional[Dict[str, Any]],
        json_body: Optional[Dict[str, Any]],
    ) -> httpx.Response:
        """Make HTTP request."""
        method_upper = method.upper()

        if method_upper == "GET":
            return await client.get(path, headers=headers, params=params)
        elif method_upper == "POST":
            return await client.post(path, headers=headers, json=json_body)
        elif method_upper == "PUT":
            return await client.put(path, headers=headers, json=json_body)
        elif method_upper == "PATCH":
            return await client.patch(path, headers=headers, json=json_body)
        elif method_upper == "DELETE":
            return await client.delete(path, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

    def _evaluate_response(
        self,
        scenario: TestScenarioIR,
        response: httpx.Response,
    ) -> ScenarioStatus:
        """Evaluate if response matches expected outcome.

        QA-strict mode: Only exact status code match is accepted.
        This ensures:
        - 201 (Created with body) is not confused with 204 (No Content)
        - 200 (OK with body) is not confused with 204 (No Content)
        - If IR says 201, the code MUST return 201
        """
        # QA-strict: Only exact match is accepted
        if response.status_code == scenario.expected_status_code:
            return ScenarioStatus.PASSED

        # Log mismatch for debugging (but still fail)
        # This helps identify if it's a "close miss" vs completely wrong
        if scenario.expected_outcome == ExpectedOutcome.SUCCESS:
            if 200 <= response.status_code < 300:
                # Close miss - right category but wrong code
                # e.g., expected 201 got 200, or expected 200 got 204
                pass  # Still fails, but could be logged

        return ScenarioStatus.FAILED

    def _derive_entity_from_path(self, path: str) -> str:
        """Bug #138 Fix: Derive entity type from path for generic {id} params.

        Examples:
            /products/{id} -> product
            /customers/{id} -> customer
            /carts/{id}/items/{product_id} -> cart (first entity in path)
        """
        import re
        # Extract first resource segment (e.g., /products/{id} -> products)
        match = re.match(r'^/(\w+)', path)
        if match:
            resource = match.group(1)
            # Remove trailing 's' to get singular entity name
            if resource.endswith('s') and len(resource) > 1:
                return resource[:-1]  # products -> product
            return resource
        return 'unknown'

    def _calculate_endpoint_coverage(self, report: SmokeTestReport) -> float:
        """Calculate endpoint coverage percentage."""
        # Get unique endpoints tested
        tested_endpoints = set()
        for result in report.results:
            tested_endpoints.add(f"{result.http_method} {result.endpoint_path}")

        # Get total endpoints from IR
        total_endpoints = len(self.tests_model.endpoint_suites)

        if total_endpoints == 0:
            return 100.0

        return len(tested_endpoints) / total_endpoints * 100

    def _count_by_priority(self, scenarios: List[TestScenarioIR]) -> Dict[str, int]:
        """Count scenarios by priority."""
        counts = {}
        for priority in TestPriority:
            counts[priority.value] = len([s for s in scenarios if s.priority == priority])
        return counts


async def run_smoke_tests_v2(
    tests_model: TestsModelIR,
    base_url: str = "http://localhost:8000",
    auth_token: Optional[str] = None,
) -> SmokeTestReport:
    """
    Convenience function to run smoke tests from TestsModelIR.

    Args:
        tests_model: The TestsModelIR to execute
        base_url: Base URL of the API server
        auth_token: Optional auth token for protected endpoints

    Returns:
        SmokeTestReport with results
    """
    runner = SmokeRunnerV2(tests_model, base_url, auth_token=auth_token)
    return await runner.run()


def format_smoke_report(report: SmokeTestReport) -> str:
    """Format smoke test report as string."""
    lines = [
        "=" * 60,
        "SMOKE TEST REPORT (IR-Centric V2)",
        "=" * 60,
        f"Total Scenarios: {report.total_scenarios}",
        f"Passed: {report.passed}",
        f"Failed: {report.failed}",
        f"Errors: {report.errors}",
        f"Pass Rate: {report.pass_rate:.1f}%",
        f"Endpoint Coverage: {report.endpoint_coverage:.1f}%",
        f"Duration: {report.total_duration_ms:.0f}ms",
        "-" * 60,
    ]

    # Failed endpoints
    if report.failed_endpoints:
        lines.append("Failed Endpoints:")
        for ep in report.failed_endpoints:
            lines.append(f"  - {ep}")
        lines.append("-" * 60)

    # Priority breakdown
    if report.scenarios_by_priority:
        lines.append("By Priority:")
        for priority, count in report.scenarios_by_priority.items():
            lines.append(f"  {priority}: {count}")

    lines.append("=" * 60)

    return "\n".join(lines)
