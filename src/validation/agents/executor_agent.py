"""
Scenario Executor Agent

Phase 4 of Bug #107: LLM-Driven Smoke Test Generation

Executes HTTP requests for each test scenario and collects results.
No LLM needed - pure HTTP execution with timing.
"""
import time
import re
import structlog
from typing import List, Union, Optional, Dict, Any
import httpx

from src.validation.smoke_test_models import (
    SmokeTestPlan,
    TestScenario,
    ScenarioResult
)

logger = structlog.get_logger(__name__)


class ScenarioExecutorAgent:
    """
    Agent for executing HTTP test scenarios.

    Handles request building, timing, and response capture.
    No LLM needed - deterministic HTTP execution.
    """

    # Bug #115: Define equivalent status codes for flexible matching
    # These represent semantically equivalent responses
    SUCCESS_CODES = {200, 201, 204}  # All success responses
    VALIDATION_ERROR_CODES = {400, 422}  # Both mean validation failed
    CLIENT_ERROR_CODES = {400, 404, 422}  # Client-side errors
    REDIRECT_CODES = {301, 302, 307, 308}  # Redirects

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0
    ):
        """
        Initialize executor with target server.

        Args:
            base_url: Server base URL (e.g., "http://localhost:8000")
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        # Bug #115: Follow redirects automatically (handles FastAPI trailing slash redirects)
        self.client = httpx.AsyncClient(timeout=self.timeout, follow_redirects=True)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def execute_all(
        self,
        plan: SmokeTestPlan,
        stop_on_first_failure: bool = False
    ) -> List[ScenarioResult]:
        """
        Execute all scenarios in the plan.

        Args:
            plan: SmokeTestPlan with scenarios to execute
            stop_on_first_failure: Stop on first failed scenario

        Returns:
            List of ScenarioResult for each scenario
        """
        logger.info(f"🧪 Executor Agent: Running {len(plan.scenarios)} scenarios")

        results = []

        # Ensure client is created
        if not self.client:
            # Bug #115: Follow redirects automatically
            self.client = httpx.AsyncClient(timeout=self.timeout, follow_redirects=True)

        try:
            for scenario in plan.scenarios:
                result = await self._execute_scenario(scenario)
                results.append(result)

                # Log progress
                icon = "✅" if result.status_matches else "❌"
                expected = scenario.expected_status
                logger.info(
                    f"   {icon} {scenario.endpoint} [{scenario.name}]: "
                    f"{result.actual_status} (expected {expected})"
                )

                if stop_on_first_failure and not result.status_matches:
                    logger.warning("   ⚠️ Stopping on first failure")
                    break

        finally:
            if self.client:
                await self.client.aclose()
                self.client = None

        return results

    async def _execute_scenario(
        self,
        scenario: TestScenario
    ) -> ScenarioResult:
        """Execute a single scenario and return result."""
        # Build URL with path params
        url = self._build_url(scenario)
        method = scenario.method

        start_time = time.time()

        try:
            response = await self._make_request(
                method=method,
                url=url,
                payload=scenario.payload,
                query_params=scenario.query_params
            )

            elapsed_ms = (time.time() - start_time) * 1000

            # Check if status matches expected (Bug #115: flexible matching)
            status_matches = self._check_status_match(
                response.status_code,
                scenario.expected_status,
                scenario  # Bug #115: Pass scenario for flexible matching
            )

            return ScenarioResult(
                scenario=scenario,
                actual_status=response.status_code,
                response_body=response.text[:2000] if response.text else None,
                response_time_ms=elapsed_ms,
                status_matches=status_matches,
                error=None if status_matches else (
                    f"Expected {scenario.expected_status}, got {response.status_code}"
                )
            )

        except httpx.ConnectError as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return ScenarioResult(
                scenario=scenario,
                actual_status=None,
                response_time_ms=elapsed_ms,
                status_matches=False,
                error=f"Connection failed: {e}"
            )

        except httpx.TimeoutException as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return ScenarioResult(
                scenario=scenario,
                actual_status=None,
                response_time_ms=elapsed_ms,
                status_matches=False,
                error=f"Request timeout: {e}"
            )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return ScenarioResult(
                scenario=scenario,
                actual_status=None,
                response_time_ms=elapsed_ms,
                status_matches=False,
                error=f"Request error: {type(e).__name__}: {e}"
            )

    def _build_url(self, scenario: TestScenario) -> str:
        """Build full URL with path parameters substituted."""
        path = scenario.path

        # Substitute path parameters
        for param_name, param_value in scenario.path_params.items():
            # Handle both {id} and {param_name} formats
            path = path.replace(f"{{{param_name}}}", str(param_value))

        # Ensure path starts with /
        if not path.startswith('/'):
            path = '/' + path

        return f"{self.base_url}{path}"

    async def _make_request(
        self,
        method: str,
        url: str,
        payload: Optional[Dict[str, Any]] = None,
        query_params: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """Make HTTP request."""
        method = method.upper()

        if method == "GET":
            return await self.client.get(url, params=query_params)
        elif method == "POST":
            return await self.client.post(url, json=payload, params=query_params)
        elif method == "PUT":
            return await self.client.put(url, json=payload, params=query_params)
        elif method == "PATCH":
            return await self.client.patch(url, json=payload, params=query_params)
        elif method == "DELETE":
            return await self.client.delete(url, params=query_params)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

    def _check_status_match(
        self,
        actual: int,
        expected: Union[int, List[int]],
        scenario: Optional[TestScenario] = None
    ) -> bool:
        """
        Check if actual status matches expected with flexible matching.

        Bug #115: Implements flexible status matching based on scenario type:
        - success scenarios: 200, 201, 204 are all considered success
        - validation_error: 400, 422 both mean validation failed
        - not_found: 404, 422 (invalid UUID) are acceptable
        """
        # Direct match always wins
        if isinstance(expected, list):
            if actual in expected:
                return True
        elif actual == expected:
            return True

        # If no scenario info, fall back to strict matching
        if scenario is None:
            return False

        scenario_name = scenario.name.lower()

        # Bug #115: Flexible matching based on scenario type
        # Success scenarios: any 2xx is acceptable
        if 'happy_path' in scenario_name or 'flow_' in scenario_name:
            # Expected success -> any success code is OK
            if expected in self.SUCCESS_CODES or (isinstance(expected, list) and any(e in self.SUCCESS_CODES for e in expected)):
                if actual in self.SUCCESS_CODES:
                    return True

        # Validation error scenarios: 400/422 are equivalent
        if 'validation_error' in scenario_name:
            if expected in self.VALIDATION_ERROR_CODES or expected == 400 or expected == 422:
                if actual in self.VALIDATION_ERROR_CODES:
                    return True

        # Not found scenarios: 404/422 (invalid UUID) are equivalent
        if 'not_found' in scenario_name:
            if expected == 404:
                # 422 is also acceptable (Pydantic validation error on invalid UUID)
                if actual in {404, 422}:
                    return True

        return False
