"""
Runtime Smoke Test Validator - Task 10 Implementation.

Validates generated apps by actually running them and calling endpoints.
Catches HTTP 500, NameError, TypeError that static validation misses.
Feeds failures back to Code Repair for automated fixes.

Reference: IMPROVEMENT_ROADMAP.md Task 10
Evidence: Bugs #71-73 passed static validation but would crash at runtime.
"""
import asyncio
import logging
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from src.cognitive.ir.application_ir import ApplicationIR
from src.cognitive.ir.api_model import Endpoint, HttpMethod

# Active Learning imports (optional - graceful degradation if Neo4j unavailable)
try:
    from src.cognitive.services.error_knowledge_repository import ErrorKnowledgeRepository
    ACTIVE_LEARNING_AVAILABLE = True
except ImportError:
    ErrorKnowledgeRepository = None
    ACTIVE_LEARNING_AVAILABLE = False

# Pattern Feedback Integration (optional - for score adjustments)
try:
    from src.cognitive.patterns.pattern_feedback_integration import (
        PatternFeedbackIntegration,
        get_pattern_feedback_integration,
    )
    PATTERN_FEEDBACK_AVAILABLE = True
except ImportError:
    PatternFeedbackIntegration = None
    get_pattern_feedback_integration = None
    PATTERN_FEEDBACK_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class EndpointTestResult:
    """Result of testing a single endpoint."""
    endpoint_path: str
    method: str
    success: bool
    status_code: Optional[int] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    response_time_ms: float = 0.0


@dataclass
class SmokeTestResult:
    """Overall result of smoke testing all endpoints."""
    passed: bool
    endpoints_tested: int
    endpoints_passed: int
    endpoints_failed: int
    violations: List[Dict[str, Any]] = field(default_factory=list)
    results: List[EndpointTestResult] = field(default_factory=list)
    total_time_ms: float = 0.0
    server_startup_time_ms: float = 0.0
    # NEW: Server logs for smoke-driven repair
    server_logs: str = ""
    stack_traces: List[Dict[str, Any]] = field(default_factory=list)


class RuntimeSmokeTestValidator:
    """
    Validates generated app by actually running it and calling endpoints.
    Feeds failures back to Code Repair for automated fixes.

    Phase 7.5 in the E2E pipeline.

    Bug #85 Fix: Uses Docker with seed data for realistic testing.
    Docker's db-init service creates tables + test data before app starts.
    Falls back to uvicorn if docker-compose.yml is not available.
    """

    def __init__(
        self,
        app_dir: Path,
        host: str = "127.0.0.1",
        port: int = 8002,  # Bug #85: Docker exposes on 8002
        max_iterations: int = 3,
        startup_timeout: float = 90.0,  # Bug #85: Docker needs more time
        request_timeout: float = 10.0,
        error_knowledge_repo: Optional["ErrorKnowledgeRepository"] = None,
        pattern_feedback: Optional["PatternFeedbackIntegration"] = None,
        enforce_docker: bool = False,
    ):
        self.app_dir = Path(app_dir)
        self.host = host
        self.port = port
        self.max_iterations = max_iterations
        self.startup_timeout = startup_timeout
        self.request_timeout = request_timeout
        self.server_process: Optional[subprocess.Popen] = None
        self.base_url = f"http://{host}:{port}"
        # Bug #85: Track if using Docker for proper cleanup
        self._using_docker = False
        # Optional strictness: fail fast if Docker assets are missing/broken
        self.enforce_docker = enforce_docker
        # Active Learning: Repository for learning from failures
        self._error_knowledge_repo = error_knowledge_repo
        self._learning_enabled = error_knowledge_repo is not None and ACTIVE_LEARNING_AVAILABLE
        # Pattern Feedback: For score adjustments on failures
        self._pattern_feedback = pattern_feedback
        self._pattern_feedback_enabled = pattern_feedback is not None and PATTERN_FEEDBACK_AVAILABLE

    async def validate(self, ir: ApplicationIR) -> SmokeTestResult:
        """
        Run smoke tests against all endpoints.
        Returns violations in Code Repair compatible format.
        """
        start_time = time.time()
        violations: List[Dict[str, Any]] = []
        results: List[EndpointTestResult] = []
        server_startup_time = 0.0

        # 1. Start uvicorn server
        try:
            startup_start = time.time()
            await self._start_server()
            server_startup_time = (time.time() - startup_start) * 1000
            logger.info(f"✅ Server started in {server_startup_time:.0f}ms at {self.base_url}")
        except Exception as e:
            logger.error(f"❌ Failed to start server: {e}")
            # Bug #91 Fix: Always cleanup Docker even when startup fails
            # Docker may have started but _wait_for_server timed out
            await self._stop_server()
            return SmokeTestResult(
                passed=False,
                endpoints_tested=0,
                endpoints_passed=0,
                endpoints_failed=0,
                violations=[{
                    "type": "runtime_error",
                    "severity": "critical",
                    "error_type": "ServerStartupError",
                    "error_message": str(e),
                    "fix_hint": "Check main.py imports and app initialization"
                }],
                results=[],
                total_time_ms=(time.time() - start_time) * 1000,
                server_startup_time_ms=server_startup_time
            )

        server_logs = ""
        stack_traces: List[StackTrace] = []

        try:
            # 2. Get endpoints from IR
            endpoints = self._get_endpoints_from_ir(ir)
            logger.info(f"🔍 Testing {len(endpoints)} endpoints...")

            # Bug #85: With Docker, seed data is created by db-init service
            # No need to create resources manually - they exist in the database

            # 3. Test each endpoint
            for endpoint in endpoints:
                result = await self._test_endpoint(endpoint)
                results.append(result)

                if not result.success:
                    violation = self._create_violation(endpoint, result)
                    violations.append(violation)
                    logger.warning(f"  ❌ {result.method} {result.endpoint_path}: {result.error_type}")

                    # Active Learning: Learn from this failure
                    self._learn_from_error(endpoint, result, violation)
                else:
                    logger.info(f"  ✅ {result.method} {result.endpoint_path}: {result.status_code}")

            # 4. Capture server logs BEFORE stopping (for smoke-driven repair)
            if violations:  # Only capture if there are failures
                server_logs = await self._capture_server_logs()
                stack_trace_dicts = self._extract_stack_traces(server_logs)
                stack_traces = [self._to_stack_trace(t) for t in stack_trace_dicts if t]
                logger.info(f"📝 Captured {len(stack_traces)} stack traces from server logs")
                # Attach best-effort traces to violations
                self._attach_traces_to_violations(violations, stack_traces)

        finally:
            # 5. Stop server (always)
            await self._stop_server()

        total_time = (time.time() - start_time) * 1000
        passed_count = len([r for r in results if r.success])
        failed_count = len([r for r in results if not r.success])

        return SmokeTestResult(
            passed=len(violations) == 0,
            endpoints_tested=len(results),
            endpoints_passed=passed_count,
            endpoints_failed=failed_count,
            violations=violations,
            results=results,
            total_time_ms=total_time,
            server_startup_time_ms=server_startup_time,
            server_logs=server_logs,
            stack_traces=stack_traces
        )

    def _get_endpoints_from_ir(self, ir: ApplicationIR) -> List[Endpoint]:
        """Extract testable endpoints from ApplicationIR."""
        endpoints = []

        if ir.api_model and ir.api_model.endpoints:
            for ep in ir.api_model.endpoints:
                # Skip health/metrics for smoke test (they're infrastructure)
                if '/health' in ep.path or '/metrics' in ep.path:
                    continue
                endpoints.append(ep)

        return endpoints

    async def _start_server(self) -> None:
        """
        Start the generated app using docker-compose.

        Bug #85 Fix: Uses Docker instead of uvicorn for realistic testing.
        Docker runs migrations + seed data before starting the app.
        """
        # Ensure any previous server is stopped
        await self._stop_server()

        docker_dir = self.app_dir / "docker"

        # Check if docker-compose.yml exists
        if not (docker_dir / "docker-compose.yml").exists():
            msg = "⚠️ docker-compose.yml not found"
            if self.enforce_docker:
                logger.error(msg)
                raise RuntimeError("docker-compose.yml missing and Docker enforcement enabled")
            logger.warning(f"{msg}, falling back to uvicorn")
            await self._start_uvicorn_server()
            return

        # Check for Dockerfile presence (common build failure)
        dockerfile_candidates = [
            docker_dir / "Dockerfile",
            self.app_dir / "Dockerfile",
        ]
        has_dockerfile = any(p.exists() for p in dockerfile_candidates)
        if not has_dockerfile:
            msg = "⚠️ Dockerfile not found"
            if self.enforce_docker:
                logger.error(msg)
                raise RuntimeError("Dockerfile missing and Docker enforcement enabled")
            logger.warning(f"{msg}, falling back to uvicorn")
            await self._start_uvicorn_server()
            return

        # Bug #145 Fix: Clean up existing volumes BEFORE building to ensure fresh DB state.
        # Without this cleanup, the named volume 'postgres-data' persists across runs
        # and contains stale data with random UUIDs instead of seed-compatible UUIDs.
        # This causes smoke tests to fail with 404 errors when looking for seeded entities.
        cleanup_cmd = [
            'docker', 'compose',
            '-f', 'docker/docker-compose.yml',
            'down', '-v', '--remove-orphans'
        ]
        logger.info(f"🧹 Cleaning up previous containers/volumes: {' '.join(cleanup_cmd)}")
        subprocess.run(cleanup_cmd, cwd=str(self.app_dir), capture_output=True, timeout=30)

        # Start docker compose
        # Bug #85 Fix: Use relative path from app_dir since cwd=app_dir
        # Bug #86 Fix: Use 'docker compose' (v2) instead of 'docker-compose' for WSL 2
        # Bug #132 Fix: Force rebuild with --no-cache to prevent using stale cached images
        #   When code changes (like Bug #131 fix), docker may use cached layers from
        #   previous builds, causing smoke tests to run against old code.
        cmd = [
            'docker', 'compose',
            '-f', 'docker/docker-compose.yml',
            'build', '--no-cache'
        ]

        logger.info(f"🐳 Building Docker (no cache): {' '.join(cmd)}")

        build_result = subprocess.run(
            cmd,
            cwd=str(self.app_dir),
            capture_output=True,
            text=True,
            timeout=180  # 3 min timeout for build
        )

        if build_result.returncode != 0:
            logger.error(f"Docker build failed: {build_result.stderr}")
            if self.enforce_docker:
                raise RuntimeError(f"Docker build failed (enforced): {build_result.stderr[:500]}")
            # Fallback to uvicorn to avoid hard failure when Dockerfile is missing/misconfigured
            await self._start_uvicorn_server()
            return

        # Now start containers
        cmd = [
            'docker', 'compose',
            '-f', 'docker/docker-compose.yml',
            'up', '-d'
        ]

        logger.info(f"🐳 Starting Docker: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            cwd=str(self.app_dir),
            capture_output=True,
            text=True,
            timeout=120  # 2 min timeout for build
        )

        # Bug #89 Fix: Don't treat stderr warnings as errors when Docker succeeds
        # Docker compose v2 outputs "version is obsolete" warning on stderr even on success
        # Also check combined output for success indicators regardless of returncode
        stderr_lower = (result.stderr or '').lower()
        stdout_combined = f"{result.stdout or ''}\n{result.stderr or ''}"

        # Check if this is actually a success with warnings
        success_indicators = ['built', 'started', 'running', 'created']
        has_success = any(ind in stdout_combined.lower() for ind in success_indicators)

        # Known harmless warnings to ignore
        harmless_warnings = ['version is obsolete', 'pull access denied', 'network already exists']
        is_harmless = any(warn in stderr_lower for warn in harmless_warnings)

        # Only fail if returncode != 0 AND no success indicators AND error is not harmless
        if result.returncode != 0 and not has_success and not is_harmless:
            error_msg = result.stderr or result.stdout or "Unknown error"
            raise RuntimeError(f"Docker-compose failed: {error_msg[:500]}")

        # Mark that we're using Docker (for cleanup)
        self._using_docker = True
        self.server_process = None  # No process to track with Docker

        # Wait for server to be ready
        await self._wait_for_server()

    async def _start_uvicorn_server(self) -> None:
        """Fallback: Start uvicorn directly (for apps without Docker)."""
        env = {
            **dict(__import__('os').environ),
            'PYTHONPATH': str(self.app_dir),
            'DATABASE_URL': 'sqlite+aiosqlite:///:memory:?cache=shared',
            'TESTING': 'true',
        }

        cmd = [
            sys.executable, '-m', 'uvicorn',
            'src.main:app',
            '--host', self.host,
            '--port', str(self.port),
            '--log-level', 'warning',
        ]

        logger.info(f"Starting uvicorn: {' '.join(cmd)}")

        self.server_process = subprocess.Popen(
            cmd,
            cwd=str(self.app_dir),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=__import__('os').setsid if hasattr(__import__('os'), 'setsid') else None
        )
        self._using_docker = False

        # Wait for server to be ready
        await self._wait_for_server()

    async def _wait_for_server(self) -> None:
        """Wait for server to be ready to accept connections."""
        # Bug #130 Fix: Use correct health endpoint path
        health_endpoints = [
            f"{self.base_url}/health",
            f"{self.base_url}/health/ready",
            f"{self.base_url}/",
        ]

        start_time = time.time()
        last_error = None

        while (time.time() - start_time) < self.startup_timeout:
            # Check if process died
            if self.server_process and self.server_process.poll() is not None:
                stdout, stderr = self.server_process.communicate()
                error_msg = stderr.decode() if stderr else stdout.decode() if stdout else "Unknown error"
                raise RuntimeError(f"Server process died during startup: {error_msg[:500]}")

            # Try health endpoints
            for health_url in health_endpoints:
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(health_url, timeout=2.0)
                        if response.status_code < 500:
                            return  # Server is ready
                except Exception as e:
                    last_error = e

            await asyncio.sleep(0.5)

        raise TimeoutError(f"Server did not become ready within {self.startup_timeout}s. Last error: {last_error}")

    async def _capture_server_logs(self) -> str:
        """
        Capture server logs for smoke-driven repair.

        Returns logs from Docker container or uvicorn process.
        These logs contain stack traces needed to identify root causes.
        """
        if self._using_docker:
            try:
                # Get logs from the app container
                cmd = [
                    'docker', 'compose',
                    '-f', 'docker/docker-compose.yml',
                    'logs', 'app', '--no-color', '--tail', '500'
                ]
                result = subprocess.run(
                    cmd,
                    cwd=str(self.app_dir),
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                logs = result.stdout + result.stderr
                logger.debug(f"📝 Captured {len(logs)} bytes of server logs")
                return logs
            except Exception as e:
                logger.warning(f"Failed to capture Docker logs: {e}")
                return ""

        # For uvicorn, logs would be in process stdout/stderr (not implemented)
        return ""

    def _extract_stack_traces(self, logs: str) -> List[Dict[str, Any]]:
        """Extract stack traces from server logs."""
        traces = []
        # Regex for Python tracebacks
        traceback_pattern = re.compile(
            r'Traceback \(most recent call last\):.*?(?=\n\n|\Z)',
            re.DOTALL
        )

        for match in traceback_pattern.finditer(logs):
            trace_text = match.group()
            trace_info = self._parse_error_response(trace_text)
            traces.append({
                'full_trace': trace_text,
                'error_type': trace_info.get('type', 'Unknown'),
                'error_message': trace_info.get('message', ''),
                'file': trace_info.get('file', ''),
                'line': trace_info.get('line', 0)
            })

        return traces

    def _to_stack_trace(self, trace_dict: Dict[str, Any]) -> StackTrace:
        """Convert raw trace dict to StackTrace dataclass."""
        error_type = trace_dict.get("error_type", "Unknown")
        exception_class = trace_dict.get("type", None) or error_type
        return StackTrace(
            endpoint=trace_dict.get("endpoint", "unknown"),
            error_type=error_type,
            exception_class=exception_class,
            exception_message=trace_dict.get("error_message", ""),
            file_path=trace_dict.get("file", ""),
            line_number=trace_dict.get("line", 0),
            full_trace=trace_dict.get("full_trace", "")
        )

    def _attach_traces_to_violations(
        self,
        violations: List[Dict[str, Any]],
        stack_traces: List[StackTrace]
    ) -> None:
        """Best-effort match of stack traces to violations by file/endpoint."""
        if not stack_traces or not violations:
            return

        # Index by file for quick lookup
        traces_by_file = {t.file_path: t for t in stack_traces if t.file_path}

        for violation in violations:
            file_path = violation.get("file", "")
            matched_trace = None

            if file_path and file_path in traces_by_file:
                matched_trace = traces_by_file[file_path]
            else:
                # Fallback: match by endpoint substring in full_trace
                endpoint = violation.get("endpoint", "")
                for trace in stack_traces:
                    if endpoint and endpoint in trace.full_trace:
                        matched_trace = trace
                        break

            if matched_trace:
                violation["stack_trace"] = matched_trace.full_trace
                violation["stack_trace_obj"] = matched_trace
                violation["exception_class"] = matched_trace.exception_class

    async def _stop_server(self) -> None:
        """Stop the server (Docker or uvicorn)."""
        # Bug #85: Handle Docker shutdown
        if self._using_docker:
            try:
                # Bug #85 Fix: Use relative path from app_dir since cwd=app_dir
                # Bug #86 Fix: Use 'docker compose' (v2) for WSL 2
                cmd = [
                    'docker', 'compose',
                    '-f', 'docker/docker-compose.yml',
                    'down', '-v', '--remove-orphans'
                ]
                logger.info(f"🐳 Stopping Docker: {' '.join(cmd)}")
                subprocess.run(cmd, cwd=str(self.app_dir), capture_output=True, timeout=30)
            except Exception as e:
                logger.warning(f"Error stopping Docker: {e}")
            finally:
                self._using_docker = False
            return

        # Handle uvicorn shutdown
        if self.server_process:
            try:
                # Try graceful shutdown first
                if hasattr(__import__('os'), 'killpg'):
                    __import__('os').killpg(__import__('os').getpgid(self.server_process.pid), signal.SIGTERM)
                else:
                    self.server_process.terminate()

                # Wait for graceful shutdown
                try:
                    self.server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill
                    if hasattr(__import__('os'), 'killpg'):
                        __import__('os').killpg(__import__('os').getpgid(self.server_process.pid), signal.SIGKILL)
                    else:
                        self.server_process.kill()
                    self.server_process.wait()

            except Exception as e:
                logger.warning(f"Error stopping server: {e}")
            finally:
                self.server_process = None

    async def _test_endpoint(self, endpoint: Endpoint) -> EndpointTestResult:
        """
        Call endpoint with minimal test data.
        Catch 500s, parse error messages.
        """
        method = endpoint.method.value.lower()

        # Replace path parameters with test values
        path = self._substitute_path_params(endpoint.path)
        url = f"{self.base_url}{path}"

        # Generate minimal payload for POST/PUT/PATCH
        payload = None
        if endpoint.method in [HttpMethod.POST, HttpMethod.PUT, HttpMethod.PATCH]:
            payload = self._generate_minimal_payload(endpoint)

        start_time = time.time()

        try:
            async with httpx.AsyncClient() as client:
                if method == 'get':
                    response = await client.get(url, timeout=self.request_timeout)
                elif method == 'post':
                    response = await client.post(url, json=payload, timeout=self.request_timeout)
                elif method == 'put':
                    response = await client.put(url, json=payload, timeout=self.request_timeout)
                elif method == 'patch':
                    response = await client.patch(url, json=payload, timeout=self.request_timeout)
                elif method == 'delete':
                    response = await client.delete(url, timeout=self.request_timeout)
                else:
                    response = await client.request(method, url, json=payload, timeout=self.request_timeout)

            response_time = (time.time() - start_time) * 1000

            # Check for server errors
            if response.status_code >= 500:
                error_info = self._parse_error_response(response.text)
                return EndpointTestResult(
                    endpoint_path=endpoint.path,
                    method=endpoint.method.value,
                    success=False,
                    status_code=response.status_code,
                    error_type=error_info.get('type', 'HTTP_500'),
                    error_message=error_info.get('message', response.text[:500]),
                    stack_trace=error_info.get('stack_trace'),
                    response_time_ms=response_time
                )

            # Success (including 4xx which might be expected for invalid test data)
            return EndpointTestResult(
                endpoint_path=endpoint.path,
                method=endpoint.method.value,
                success=True,
                status_code=response.status_code,
                response_time_ms=response_time
            )

        except httpx.ConnectError as e:
            return EndpointTestResult(
                endpoint_path=endpoint.path,
                method=endpoint.method.value,
                success=False,
                error_type="ConnectionError",
                error_message=f"Failed to connect: {e}",
                response_time_ms=(time.time() - start_time) * 1000
            )
        except httpx.TimeoutException:
            return EndpointTestResult(
                endpoint_path=endpoint.path,
                method=endpoint.method.value,
                success=False,
                error_type="TimeoutError",
                error_message=f"Request timed out after {self.request_timeout}s",
                response_time_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return EndpointTestResult(
                endpoint_path=endpoint.path,
                method=endpoint.method.value,
                success=False,
                error_type=type(e).__name__,
                error_message=str(e),
                response_time_ms=(time.time() - start_time) * 1000
            )

    def _substitute_path_params(self, path: str) -> str:
        """Replace path parameters like {id} with test values."""
        # Bug #85: Use predictable UUIDs that match seed data
        # Each resource type gets its own UUID
        uuid_product = '00000000-0000-4000-8000-000000000001'
        uuid_customer = '00000000-0000-4000-8000-000000000002'
        uuid_cart = '00000000-0000-4000-8000-000000000003'
        uuid_order = '00000000-0000-4000-8000-000000000005'  # Bug #107: Was 004, seed uses 005
        uuid_item = '00000000-0000-4000-8000-000000000006'
        uuid_generic = '00000000-0000-4000-8000-000000000099'

        # Map path patterns to their specific UUIDs
        # Order matters: specific patterns first, generic last
        substitutions = [
            (r'\{product_id\}', uuid_product),
            (r'\{customer_id\}', uuid_customer),
            (r'\{cart_id\}', uuid_cart),
            (r'\{order_id\}', uuid_order),
            (r'\{item_id\}', uuid_item),
            (r'\{user_id\}', uuid_customer),  # user_id often maps to customer
        ]

        result = path

        # Apply specific substitutions first
        for pattern, replacement in substitutions:
            result = re.sub(pattern, replacement, result)

        # Handle generic {id} based on path context
        if '{id}' in result:
            if '/products' in path:
                result = result.replace('{id}', uuid_product)
            elif '/customers' in path:
                result = result.replace('{id}', uuid_customer)
            elif '/carts' in path:
                result = result.replace('{id}', uuid_cart)
            elif '/orders' in path:
                result = result.replace('{id}', uuid_order)
            else:
                result = result.replace('{id}', uuid_generic)

        # Handle any remaining *_id patterns
        result = re.sub(r'\{[a-z_]+_id\}', uuid_generic, result)

        # Non-ID parameters can be strings
        result = re.sub(r'\{[a-z_]+\}', 'test-value', result)

        return result

    def _generate_minimal_payload(self, endpoint: Endpoint) -> Dict[str, Any]:
        """
        Generate minimal valid JSON payload for endpoint testing.
        Uses endpoint schema to create realistic test data.
        """
        payload: Dict[str, Any] = {}

        # Try to infer from request schema
        if endpoint.request_schema and endpoint.request_schema.fields:
            for field in endpoint.request_schema.fields:
                if field.required:
                    payload[field.name] = self._generate_field_value(field.name, field.type)

        # If no schema, infer from operation_id and path
        if not payload:
            payload = self._infer_payload_from_context(endpoint)

        return payload

    def _generate_field_value(self, field_name: str, field_type: str) -> Any:
        """Generate appropriate test value based on field name and type."""
        field_lower = field_name.lower()
        type_lower = field_type.lower()

        # Name-based inference (most reliable)
        if 'email' in field_lower:
            return 'test@example.com'
        if 'id' in field_lower and 'uuid' in type_lower:
            return '00000000-0000-0000-0000-000000000001'
        if 'id' in field_lower:
            return 'test-id-123'
        if 'name' in field_lower:
            return 'Test Name'
        if 'description' in field_lower:
            return 'Test description'
        if 'price' in field_lower or 'amount' in field_lower or 'cost' in field_lower:
            return 99.99
        if 'quantity' in field_lower or 'stock' in field_lower or 'count' in field_lower:
            return 10
        if 'status' in field_lower:
            return 'active'
        if 'date' in field_lower or 'time' in field_lower:
            return '2025-01-01T00:00:00Z'
        if 'url' in field_lower or 'link' in field_lower:
            return 'https://example.com'
        if 'is_' in field_lower or 'has_' in field_lower:
            return True

        # Type-based defaults
        if 'int' in type_lower:
            return 1
        if 'float' in type_lower or 'decimal' in type_lower or 'number' in type_lower:
            return 1.0
        if 'bool' in type_lower:
            return True
        if 'list' in type_lower or 'array' in type_lower:
            return []
        if 'dict' in type_lower or 'object' in type_lower:
            return {}

        # Default to string
        return 'test_value'

    def _infer_payload_from_context(self, endpoint: Endpoint) -> Dict[str, Any]:
        """Infer minimal payload from endpoint context when no schema available."""
        path_parts = endpoint.path.lower().split('/')
        operation_id = (endpoint.operation_id or '').lower()

        # Detect entity from path (e.g., /products -> Product)
        entity = None
        for part in path_parts:
            if part and not part.startswith('{') and part not in ['api', 'v1', 'v2']:
                entity = part.rstrip('s')  # products -> product
                break

        # Generate payload based on entity type
        if entity == 'product':
            return {
                'name': 'Test Product',
                'description': 'Test description',
                'price': 99.99,
                'stock': 10,
                'is_active': True
            }
        elif entity == 'customer':
            return {
                'email': 'test@example.com',
                'full_name': 'Test Customer'
            }
        elif entity == 'cart':
            # Bug #85: Use UUID that matches seed data for customer
            return {
                'customer_id': '00000000-0000-4000-8000-000000000002'  # Customer UUID
            }
        elif entity in ['order', 'order']:
            # Bug #85: Use UUID that matches seed data for customer
            return {
                'customer_id': '00000000-0000-4000-8000-000000000002'  # Customer UUID
            }
        elif 'item' in (entity or ''):
            # Bug #85: Use UUIDs that match seed data
            return {
                'product_id': '00000000-0000-4000-8000-000000000001',  # Product UUID
                'quantity': 1
            }

        # Generic fallback
        return {'name': 'Test'}

    def _parse_error_response(self, response_text: str) -> Dict[str, Any]:
        """Parse error response to extract error type and stack trace."""
        result: Dict[str, Any] = {
            'type': 'HTTP_500',
            'message': response_text[:500] if response_text else 'Unknown error'
        }

        # Try to extract specific Python error types (ordered by specificity)
        error_patterns = [
            # Database errors (high priority - common in generated code)
            (r'IntegrityError[:\s]+(.+)', 'IntegrityError'),
            (r'OperationalError[:\s]+(.+)', 'OperationalError'),
            (r'ProgrammingError[:\s]+(.+)', 'ProgrammingError'),
            # Validation errors
            (r'ValidationError[:\s]+(.+)', 'ValidationError'),
            (r'RequestValidationError[:\s]+(.+)', 'RequestValidationError'),
            (r'pydantic.*ValidationError[:\s]+(.+)', 'ValidationError'),
            # Standard Python errors
            (r'NameError[:\s]+(.+)', 'NameError'),
            (r'TypeError[:\s]+(.+)', 'TypeError'),
            (r'AttributeError[:\s]+(.+)', 'AttributeError'),
            (r'KeyError[:\s]+(.+)', 'KeyError'),
            (r'ValueError[:\s]+(.+)', 'ValueError'),
            (r'ImportError[:\s]+(.+)', 'ImportError'),
            (r'ModuleNotFoundError[:\s]+(.+)', 'ModuleNotFoundError'),
            (r'RuntimeError[:\s]+(.+)', 'RuntimeError'),
            (r'SyntaxError[:\s]+(.+)', 'SyntaxError'),
            (r'IndentationError[:\s]+(.+)', 'IndentationError'),
            # HTTP-specific errors in response
            (r'HTTPException[:\s]+(.+)', 'HTTPException'),
            (r'detail["\']:\s*["\'](.+?)["\']', 'HTTPDetail'),
        ]

        for pattern, error_type in error_patterns:
            match = re.search(pattern, response_text)
            if match:
                result['type'] = error_type
                result['message'] = match.group(1).strip()
                break

        # Extract stack trace if present
        if 'Traceback' in response_text:
            result['stack_trace'] = response_text

            # Try to extract file and line number
            file_line_match = re.search(r'File "([^"]+)", line (\d+)', response_text)
            if file_line_match:
                result['file'] = file_line_match.group(1)
                result['line'] = int(file_line_match.group(2))

        return result

    def _learn_from_error(
        self,
        endpoint: Endpoint,
        result: EndpointTestResult,
        violation: Dict[str, Any],
    ) -> None:
        """
        Learn from a smoke test failure using Active Learning.

        Stores the error in ErrorKnowledge for future generations to avoid.
        Also notifies PatternFeedback to penalize pattern scores.
        Gracefully degrades if Neo4j or PatternFeedback is unavailable.

        Args:
            endpoint: The endpoint that was tested
            result: Test result with error details
            violation: The created violation dict
        """
        # Extract common data for both learning paths
        entity_name = self._extract_entity_from_path(endpoint.path)
        endpoint_path = f"{endpoint.method.value} {endpoint.path}"
        file_path = violation.get("file", "")
        error_type = result.error_type or "Unknown"
        error_message = result.error_message or ""

        # Path 1: Store in ErrorKnowledge repository
        if self._learning_enabled and self._error_knowledge_repo:
            try:
                signature = self._error_knowledge_repo.learn_from_failure(
                    pattern_id=None,  # No pattern tracking yet
                    error_type=error_type,
                    error_message=error_message,
                    endpoint_path=endpoint_path,
                    entity_name=entity_name,
                    failed_code=result.stack_trace,
                    file_path=file_path,
                )
                logger.debug(f"🧠 Active Learning: Stored error {signature[:8]}... for {endpoint_path}")
            except Exception as e:
                logger.warning(f"⚠️ Active Learning (ErrorKnowledge) failed (non-blocking): {e}")

        # Path 2: Notify PatternFeedback to penalize scores
        if self._pattern_feedback_enabled and self._pattern_feedback:
            try:
                # Determine pattern category based on error location
                pattern_category = self._infer_pattern_category_from_file(file_path)

                # Use asyncio to run the async method
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Already in async context, create task
                    asyncio.create_task(
                        self._pattern_feedback.register_generation_failure(
                            candidate_id=None,  # No specific candidate yet
                            error_type=error_type,
                            error_message=error_message,
                            endpoint_pattern=endpoint_path,
                            entity_type=entity_name,
                            pattern_category=pattern_category,
                            failed_code=result.stack_trace,
                            file_path=file_path,
                        )
                    )
                else:
                    # Not in async context, run synchronously
                    loop.run_until_complete(
                        self._pattern_feedback.register_generation_failure(
                            candidate_id=None,
                            error_type=error_type,
                            error_message=error_message,
                            endpoint_pattern=endpoint_path,
                            entity_type=entity_name,
                            pattern_category=pattern_category,
                            failed_code=result.stack_trace,
                            file_path=file_path,
                        )
                    )
                logger.debug(f"🧠 Active Learning: Notified PatternFeedback for {endpoint_path}")
            except Exception as e:
                logger.warning(f"⚠️ Active Learning (PatternFeedback) failed (non-blocking): {e}")

    def _infer_pattern_category_from_file(self, file_path: str) -> str:
        """Infer pattern category from file path."""
        if not file_path:
            return "service"
        fp = file_path.lower()
        if "repository" in fp or "repositories" in fp:
            return "repository"
        elif "service" in fp or "services" in fp:
            return "service"
        elif "route" in fp or "routes" in fp or "api" in fp:
            return "route"
        elif "model" in fp or "entities" in fp:
            return "model"
        elif "schema" in fp:
            return "schema"
        else:
            return "service"

    def _extract_entity_from_path(self, path: str) -> Optional[str]:
        """Extract entity name from endpoint path."""
        # /products → product
        # /carts/{id}/items → cart
        # /api/v1/customers → customer
        parts = [p for p in path.split('/') if p and not p.startswith('{')]
        for part in parts:
            if part not in ['api', 'v1', 'v2', 'health', 'metrics']:
                # Remove trailing 's' for singular
                return part.rstrip('s').lower()
        return None

    def _create_violation(self, endpoint: Endpoint, result: EndpointTestResult) -> Dict[str, Any]:
        """
        Create violation in Code Repair compatible format.
        Same structure as IR compliance violations.
        """
        # Infer file from endpoint path
        file_path = self._infer_file_from_endpoint(endpoint)

        return {
            "type": "runtime_error",
            "severity": "critical",
            "endpoint": f"{endpoint.method.value} {endpoint.path}",
            "method": endpoint.method.value,
            "error_type": result.error_type,
            "error_message": result.error_message,
            "stack_trace": result.stack_trace,
            "file": file_path,
            "status_code": result.status_code,
            "expected_status": result.status_code or 200,
            "fix_hint": self._generate_fix_hint(result)
        }

    def _infer_file_from_endpoint(self, endpoint: Endpoint) -> str:
        """Infer source file from endpoint path."""
        # Extract resource name from path
        path_parts = [p for p in endpoint.path.split('/') if p and not p.startswith('{')]

        if path_parts:
            resource = path_parts[0].lower()
            if resource in ['api', 'v1', 'v2']:
                resource = path_parts[1].lower() if len(path_parts) > 1 else 'unknown'

            # Remove trailing 's' for singular
            resource_singular = resource.rstrip('s')
            return f"src/api/routes/{resource_singular}.py"

        return "src/api/routes/unknown.py"

    def _generate_fix_hint(self, result: EndpointTestResult) -> str:
        """Generate actionable fix hint based on error type."""
        hints = {
            "NameError": "Variable undefined - remove unused parameter or define variable before use",
            "TypeError": "Type mismatch - check function signature and call arguments match",
            "AttributeError": "Missing attribute - verify service method exists or check import",
            "KeyError": "Missing key - ensure dictionary has required key or use .get() with default",
            "ValueError": "Invalid value - check input validation and type conversion",
            "ImportError": "Import failed - verify module path and installation",
            "ModuleNotFoundError": "Module not found - check dependencies in requirements.txt",
            "HTTP_500": "Server error - check function implementation completeness and return statement",
            "ConnectionError": "Server not responding - check server startup and port availability",
            "TimeoutError": "Request too slow - check for infinite loops or blocking operations"
        }
        return hints.get(result.error_type, "Review endpoint implementation for runtime errors")


async def run_smoke_test(
    app_dir: Path,
    ir: ApplicationIR,
    port: int = 8099
) -> SmokeTestResult:
    """
    Convenience function to run smoke tests.

    Usage:
        result = await run_smoke_test(app_dir, ir)
        if not result.passed:
            print(f"Failed endpoints: {result.endpoints_failed}")
            for v in result.violations:
                print(f"  - {v['endpoint']}: {v['error_type']}")
    """
    validator = RuntimeSmokeTestValidator(app_dir, port=port)
    return await validator.validate(ir)
