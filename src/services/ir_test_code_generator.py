"""
IR Test Code Generator.

Generates pytest code from TestsModelIR.
Single source of truth - paths come directly from IR.

Resolves:
- Path sync: Uses exact paths from TestsModelIR
- Coverage: Generates tests for ALL scenarios in TestsModelIR
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import os

from src.cognitive.ir.tests_model import (
    TestsModelIR,
    TestScenarioIR,
    SeedEntityIR,
    TestType,
    TestPriority,
    ExpectedOutcome,
)


class IRTestCodeGenerator:
    """
    Generates pytest code from TestsModelIR.

    Output files:
    - test_smoke_generated.py: Smoke tests for quick validation
    - test_contract_generated.py: Contract tests for API compliance
    - conftest.py: Fixtures including seed data
    """

    def __init__(self, tests_model: TestsModelIR, output_dir: str):
        self.tests_model = tests_model
        self.output_dir = Path(output_dir)

    def generate_all(self) -> Dict[str, str]:
        """Generate all test files. Returns dict of filename -> content."""
        files = {}

        # Generate conftest with fixtures
        files["conftest.py"] = self._generate_conftest()

        # Generate smoke tests
        files["test_smoke_generated.py"] = self._generate_smoke_tests()

        # Generate contract tests
        files["test_contract_generated.py"] = self._generate_contract_tests()

        return files

    def write_all(self) -> List[str]:
        """Generate and write all test files to output_dir."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        files = self.generate_all()
        written = []

        for filename, content in files.items():
            filepath = self.output_dir / filename
            filepath.write_text(content)
            written.append(str(filepath))

        return written

    # ============================================================
    # Conftest Generation
    # ============================================================

    def _generate_conftest(self) -> str:
        """Generate conftest.py with fixtures."""
        seed_fixtures = self._generate_seed_fixtures()

        return f'''"""
Auto-generated test fixtures from TestsModelIR.
DO NOT EDIT - regenerate from IR.
"""
import pytest
import httpx
import os
from typing import AsyncGenerator

# Base URL from environment or default
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")


@pytest.fixture
def base_url() -> str:
    """Base URL for API requests."""
    return BASE_URL


@pytest.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Async HTTP client for API requests."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        yield client


@pytest.fixture
def auth_headers() -> dict:
    """Authentication headers for protected endpoints."""
    token = os.getenv("TEST_AUTH_TOKEN", "test-token")
    return {{"Authorization": f"Bearer {{token}}"}}


{seed_fixtures}
'''

    def _generate_seed_fixtures(self) -> str:
        """Generate fixtures for seed data."""
        fixtures = []

        for seed in self.tests_model.seed_entities:
            fixture_name = f"seed_{seed.entity_name.lower()}"
            field_dict = self._build_field_dict(seed)

            fixtures.append(f'''
@pytest.fixture
def {fixture_name}() -> dict:
    """Seed data for {seed.entity_name}."""
    return {field_dict}
''')

        return "\n".join(fixtures)

    def _build_field_dict(self, seed: SeedEntityIR) -> str:
        """Build Python dict literal for seed fields."""
        fields = []
        for field in seed.fields:
            value = field.value
            if isinstance(value, str):
                value = f'"{value}"'
            fields.append(f'        "{field.field_name}": {value}')

        return "{\n" + ",\n".join(fields) + "\n    }"

    # ============================================================
    # Smoke Test Generation
    # ============================================================

    def _generate_smoke_tests(self) -> str:
        """Generate smoke test file."""
        scenarios = self.tests_model.get_smoke_scenarios()

        # Group by priority
        critical = [s for s in scenarios if s.priority == TestPriority.CRITICAL]
        high = [s for s in scenarios if s.priority == TestPriority.HIGH]
        medium = [s for s in scenarios if s.priority == TestPriority.MEDIUM]
        low = [s for s in scenarios if s.priority == TestPriority.LOW]

        tests = []

        # Critical tests first (health, auth)
        if critical:
            tests.append("# === CRITICAL PRIORITY ===")
            for scenario in critical:
                tests.append(self._generate_test_function(scenario))

        # High priority
        if high:
            tests.append("\n# === HIGH PRIORITY ===")
            for scenario in high:
                tests.append(self._generate_test_function(scenario))

        # Medium priority
        if medium:
            tests.append("\n# === MEDIUM PRIORITY ===")
            for scenario in medium:
                tests.append(self._generate_test_function(scenario))

        # Low priority
        if low:
            tests.append("\n# === LOW PRIORITY ===")
            for scenario in low:
                tests.append(self._generate_test_function(scenario))

        return f'''"""
Auto-generated smoke tests from TestsModelIR.
DO NOT EDIT - regenerate from IR.

Generated: {self.tests_model.generated_at.isoformat() if self.tests_model.generated_at else "unknown"}
Total scenarios: {len(scenarios)}
"""
import pytest
import httpx


@pytest.mark.smoke
class TestSmokeGenerated:
    """Smoke tests generated from TestsModelIR."""

{chr(10).join(tests)}
'''

    def _generate_test_function(self, scenario: TestScenarioIR) -> str:
        """Generate a single test function."""
        # Build test function name
        func_name = f"test_{scenario.name}"

        # Build path with params substituted
        path = scenario.endpoint_path
        for param_name, param_value in scenario.path_params.items():
            # Handle placeholder values
            if param_value == "{{seed_id}}":
                param_value = "00000000-0000-0000-0000-000000000001"
            path = path.replace(f"{{{param_name}}}", str(param_value))

        # Build request kwargs
        method = scenario.http_method.lower()
        request_kwargs = []

        if scenario.query_params:
            request_kwargs.append(f"params={scenario.query_params}")

        if scenario.request_body:
            request_kwargs.append(f"json={scenario.request_body}")

        if scenario.requires_auth:
            request_kwargs.append("headers=auth_headers")

        kwargs_str = ", ".join(request_kwargs)
        if kwargs_str:
            kwargs_str = ", " + kwargs_str

        # Build assertions
        assertions = [
            f"        assert response.status_code == {scenario.expected_status_code}"
        ]

        # Add timeout assertion if present
        for assertion in scenario.assertions:
            if assertion.assertion_type == "response_time":
                assertions.append(
                    f"        assert response.elapsed.total_seconds() * 1000 < {assertion.expected_value}"
                )

        assertions_str = "\n".join(assertions)

        # Determine fixtures needed
        fixtures = ["self", "client"]
        if scenario.requires_auth:
            fixtures.append("auth_headers")

        fixtures_str = ", ".join(fixtures)

        return f'''
    @pytest.mark.asyncio
    async def {func_name}({fixtures_str}):
        """{scenario.description or scenario.name}"""
        response = await client.{method}("{path}"{kwargs_str})
{assertions_str}
'''

    # ============================================================
    # Contract Test Generation
    # ============================================================

    def _generate_contract_tests(self) -> str:
        """Generate contract test file for API compliance."""
        tests = []

        for suite in self.tests_model.endpoint_suites:
            # Generate existence test
            tests.append(self._generate_endpoint_exists_test(suite))

            # Generate error case tests
            for error_case in suite.error_cases:
                tests.append(self._generate_test_function(error_case))

        return f'''"""
Auto-generated contract tests from TestsModelIR.
DO NOT EDIT - regenerate from IR.

Generated: {self.tests_model.generated_at.isoformat() if self.tests_model.generated_at else "unknown"}
Endpoint suites: {len(self.tests_model.endpoint_suites)}
"""
import pytest
import httpx


@pytest.mark.contract
class TestContractGenerated:
    """Contract tests generated from TestsModelIR."""

{chr(10).join(tests)}
'''

    def _generate_endpoint_exists_test(self, suite) -> str:
        """Generate test that endpoint exists and responds."""
        path = suite.endpoint_path
        method = suite.http_method.lower()

        # For endpoints with path params, use placeholder
        if "{" in path:
            path = path.replace("{id}", "00000000-0000-0000-0000-000000000001")
            for i in range(10):
                path = path.replace(f"{{id{i}}}", f"00000000-0000-0000-0000-00000000000{i}")

        return f'''
    @pytest.mark.asyncio
    async def test_{suite.operation_id}_exists(self, client):
        """Verify {suite.http_method} {suite.endpoint_path} endpoint exists."""
        response = await client.{method}("{path}")
        # Endpoint should exist (not 404 for wrong route)
        assert response.status_code != 404 or "not found" not in response.text.lower()
'''


def generate_tests_from_ir(tests_model: TestsModelIR, output_dir: str) -> List[str]:
    """
    Convenience function to generate test files from TestsModelIR.

    Args:
        tests_model: The TestsModelIR to generate from
        output_dir: Directory to write test files

    Returns:
        List of written file paths
    """
    generator = IRTestCodeGenerator(tests_model, output_dir)
    return generator.write_all()
