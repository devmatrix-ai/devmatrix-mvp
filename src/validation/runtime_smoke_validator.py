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


class RuntimeSmokeTestValidator:
    """
    Validates generated app by actually running it and calling endpoints.
    Feeds failures back to Code Repair for automated fixes.

    Phase 7.5 in the E2E pipeline.
    """

    def __init__(
        self,
        app_dir: Path,
        host: str = "127.0.0.1",
        port: int = 8099,  # Use high port to avoid conflicts
        max_iterations: int = 3,
        startup_timeout: float = 30.0,
        request_timeout: float = 10.0
    ):
        self.app_dir = Path(app_dir)
        self.host = host
        self.port = port
        self.max_iterations = max_iterations
        self.startup_timeout = startup_timeout
        self.request_timeout = request_timeout
        self.server_process: Optional[subprocess.Popen] = None
        self.base_url = f"http://{host}:{port}"

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

        try:
            # 2. Get endpoints from IR
            endpoints = self._get_endpoints_from_ir(ir)
            logger.info(f"🔍 Testing {len(endpoints)} endpoints...")

            # 3. Test each endpoint
            for endpoint in endpoints:
                result = await self._test_endpoint(endpoint)
                results.append(result)

                if not result.success:
                    violation = self._create_violation(endpoint, result)
                    violations.append(violation)
                    logger.warning(f"  ❌ {result.method} {result.endpoint_path}: {result.error_type}")
                else:
                    logger.info(f"  ✅ {result.method} {result.endpoint_path}: {result.status_code}")

        finally:
            # 4. Stop server (always)
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
            server_startup_time_ms=server_startup_time
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
        """Start uvicorn server for the generated app."""
        # Ensure any previous server is stopped
        await self._stop_server()

        # Prepare environment
        env = {
            **dict(__import__('os').environ),
            'PYTHONPATH': str(self.app_dir),
            'DATABASE_URL': 'sqlite+aiosqlite:///./smoke_test.db',  # Use SQLite for smoke test
            'TESTING': 'true',
        }

        # Start uvicorn
        cmd = [
            sys.executable, '-m', 'uvicorn',
            'src.main:app',
            '--host', self.host,
            '--port', str(self.port),
            '--log-level', 'warning',
        ]

        logger.info(f"Starting server: {' '.join(cmd)}")

        self.server_process = subprocess.Popen(
            cmd,
            cwd=str(self.app_dir),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=__import__('os').setsid if hasattr(__import__('os'), 'setsid') else None
        )

        # Wait for server to be ready
        await self._wait_for_server()

    async def _wait_for_server(self) -> None:
        """Wait for server to be ready to accept connections."""
        health_endpoints = [
            f"{self.base_url}/health/health",
            f"{self.base_url}/health",
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

    async def _stop_server(self) -> None:
        """Stop the uvicorn server."""
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
        # Replace common path parameters
        substitutions = {
            r'\{id\}': 'test-id-123',
            r'\{product_id\}': 'test-product-123',
            r'\{customer_id\}': 'test-customer-123',
            r'\{cart_id\}': 'test-cart-123',
            r'\{order_id\}': 'test-order-123',
            r'\{item_id\}': 'test-item-123',
            r'\{user_id\}': 'test-user-123',
            r'\{[a-z_]+_id\}': 'test-id-123',  # Generic *_id pattern
            r'\{[a-z_]+\}': 'test-value',  # Any other parameter
        }

        result = path
        for pattern, replacement in substitutions.items():
            result = re.sub(pattern, replacement, result)

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
            return {
                'customer_id': 'test-customer-123'
            }
        elif entity in ['order', 'order']:
            return {
                'customer_id': 'test-customer-123'
            }
        elif 'item' in (entity or ''):
            return {
                'product_id': 'test-product-123',
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

        # Try to extract specific Python error types
        error_patterns = [
            (r'NameError:\s*(.+)', 'NameError'),
            (r'TypeError:\s*(.+)', 'TypeError'),
            (r'AttributeError:\s*(.+)', 'AttributeError'),
            (r'KeyError:\s*(.+)', 'KeyError'),
            (r'ValueError:\s*(.+)', 'ValueError'),
            (r'ImportError:\s*(.+)', 'ImportError'),
            (r'ModuleNotFoundError:\s*(.+)', 'ModuleNotFoundError'),
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
            "error_type": result.error_type,
            "error_message": result.error_message,
            "stack_trace": result.stack_trace,
            "file": file_path,
            "status_code": result.status_code,
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
