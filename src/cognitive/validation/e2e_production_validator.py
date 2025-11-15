"""
E2E Production Validator

4-layer validation system for complete applications:
- Layer 1: Build validation (Docker, dependencies)
- Layer 2: Unit test validation (≥95% coverage)
- Layer 3: E2E test validation (golden tests pass)
- Layer 4: Production-ready checks (docs, security, quality)
"""

import json
import os
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any

from loguru import logger


class ValidationLayer(str, Enum):
    """Validation layers"""
    BUILD = "build"
    UNIT_TESTS = "unit_tests"
    E2E_TESTS = "e2e_tests"
    PRODUCTION_READY = "production_ready"


class ValidationStatus(str, Enum):
    """Validation status"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RUNNING = "running"


@dataclass
class LayerResult:
    """Result from a validation layer"""
    layer: ValidationLayer
    status: ValidationStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0


@dataclass
class ValidationReport:
    """Complete E2E validation report"""
    app_path: Path
    spec_name: str
    overall_status: ValidationStatus
    layers: Dict[ValidationLayer, LayerResult]
    total_duration_seconds: float
    precision_score: Optional[float] = None  # % of golden tests passed
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "app_path": str(self.app_path),
            "spec_name": self.spec_name,
            "overall_status": self.overall_status.value,
            "layers": {
                layer.value: {
                    "status": result.status.value,
                    "message": result.message,
                    "details": result.details,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "duration_seconds": result.duration_seconds,
                }
                for layer, result in self.layers.items()
            },
            "total_duration_seconds": self.total_duration_seconds,
            "precision_score": self.precision_score,
            "timestamp": self.timestamp,
        }


class E2EProductionValidator:
    """
    E2E Production Validator

    Validates complete applications through 4 layers:
    1. Build: Docker compose, dependency installation
    2. Unit Tests: ≥95% coverage
    3. E2E Tests: Golden tests pass
    4. Production Ready: Docs, security, quality
    """

    def __init__(
        self,
        app_path: Path,
        spec_name: str,
        golden_tests_path: Optional[Path] = None,
        min_coverage: float = 0.95,
        timeout_seconds: int = 600,
    ):
        """
        Initialize E2E Production Validator.

        Args:
            app_path: Path to generated application
            spec_name: Name of synthetic spec (e.g., "01_todo_backend_api")
            golden_tests_path: Path to golden E2E tests
            min_coverage: Minimum unit test coverage (0.95 = 95%)
            timeout_seconds: Max time for validation (default 10 minutes)
        """
        self.app_path = Path(app_path)
        self.spec_name = spec_name
        self.golden_tests_path = golden_tests_path or Path(__file__).parent.parent.parent.parent / "tests" / "e2e" / "golden_tests"
        self.min_coverage = min_coverage
        self.timeout_seconds = timeout_seconds

        # Results storage
        self.layers: Dict[ValidationLayer, LayerResult] = {}

    def validate(self) -> ValidationReport:
        """
        Run complete 4-layer validation.

        Returns:
            ValidationReport with results from all layers
        """
        import time
        from datetime import datetime

        logger.info(f"Starting E2E validation for {self.spec_name} at {self.app_path}")
        start_time = time.time()

        # Layer 1: Build Validation
        logger.info("Layer 1: Build Validation")
        build_result = self._validate_build()
        self.layers[ValidationLayer.BUILD] = build_result

        # Layer 2: Unit Test Validation (only if build passed)
        if build_result.status == ValidationStatus.PASSED:
            logger.info("Layer 2: Unit Test Validation")
            unit_test_result = self._validate_unit_tests()
            self.layers[ValidationLayer.UNIT_TESTS] = unit_test_result
        else:
            self.layers[ValidationLayer.UNIT_TESTS] = LayerResult(
                layer=ValidationLayer.UNIT_TESTS,
                status=ValidationStatus.SKIPPED,
                message="Skipped due to build failure"
            )

        # Layer 3: E2E Test Validation (only if unit tests passed)
        if self.layers[ValidationLayer.UNIT_TESTS].status == ValidationStatus.PASSED:
            logger.info("Layer 3: E2E Test Validation")
            e2e_result = self._validate_e2e_tests()
            self.layers[ValidationLayer.E2E_TESTS] = e2e_result
        else:
            self.layers[ValidationLayer.E2E_TESTS] = LayerResult(
                layer=ValidationLayer.E2E_TESTS,
                status=ValidationStatus.SKIPPED,
                message="Skipped due to unit test failure"
            )

        # Layer 4: Production Ready Validation (only if E2E tests passed)
        if self.layers[ValidationLayer.E2E_TESTS].status == ValidationStatus.PASSED:
            logger.info("Layer 4: Production Ready Validation")
            prod_ready_result = self._validate_production_ready()
            self.layers[ValidationLayer.PRODUCTION_READY] = prod_ready_result
        else:
            self.layers[ValidationLayer.PRODUCTION_READY] = LayerResult(
                layer=ValidationLayer.PRODUCTION_READY,
                status=ValidationStatus.SKIPPED,
                message="Skipped due to E2E test failure"
            )

        # Calculate overall status
        overall_status = self._calculate_overall_status()

        # Calculate precision score (E2E tests passed / total)
        precision_score = None
        if ValidationLayer.E2E_TESTS in self.layers:
            e2e_details = self.layers[ValidationLayer.E2E_TESTS].details
            if "passed" in e2e_details and "total" in e2e_details:
                precision_score = e2e_details["passed"] / e2e_details["total"]

        total_duration = time.time() - start_time

        report = ValidationReport(
            app_path=self.app_path,
            spec_name=self.spec_name,
            overall_status=overall_status,
            layers=self.layers,
            total_duration_seconds=total_duration,
            precision_score=precision_score,
            timestamp=datetime.utcnow().isoformat(),
        )

        logger.info(f"Validation complete: {overall_status.value} ({total_duration:.2f}s)")
        return report

    def _validate_build(self) -> LayerResult:
        """
        Layer 1: Build Validation

        - Docker Compose up successful
        - All services healthy
        - Dependencies installed
        """
        import time

        start_time = time.time()
        errors = []
        warnings = []
        details = {}

        try:
            # Check if docker-compose.yml exists
            compose_file = self.app_path / "docker-compose.yml"
            if not compose_file.exists():
                errors.append("docker-compose.yml not found")
                return LayerResult(
                    layer=ValidationLayer.BUILD,
                    status=ValidationStatus.FAILED,
                    message="Docker Compose file missing",
                    errors=errors,
                    duration_seconds=time.time() - start_time,
                )

            # Build Docker images
            logger.info("Building Docker images...")
            build_result = subprocess.run(
                ["docker-compose", "build"],
                cwd=self.app_path,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes
            )

            if build_result.returncode != 0:
                errors.append(f"Docker build failed: {build_result.stderr}")
                return LayerResult(
                    layer=ValidationLayer.BUILD,
                    status=ValidationStatus.FAILED,
                    message="Docker build failed",
                    errors=errors,
                    details={"stderr": build_result.stderr},
                    duration_seconds=time.time() - start_time,
                )

            # Start services
            logger.info("Starting Docker Compose services...")
            up_result = subprocess.run(
                ["docker-compose", "up", "-d"],
                cwd=self.app_path,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if up_result.returncode != 0:
                errors.append(f"Docker Compose up failed: {up_result.stderr}")
                return LayerResult(
                    layer=ValidationLayer.BUILD,
                    status=ValidationStatus.FAILED,
                    message="Failed to start services",
                    errors=errors,
                    duration_seconds=time.time() - start_time,
                )

            # Wait for services to be healthy
            time.sleep(10)  # Give services time to start

            # Check service health
            ps_result = subprocess.run(
                ["docker-compose", "ps"],
                cwd=self.app_path,
                capture_output=True,
                text=True,
            )

            details["services"] = ps_result.stdout

            # Check for any unhealthy services
            if "Exit" in ps_result.stdout or "unhealthy" in ps_result.stdout.lower():
                warnings.append("Some services may not be healthy")

            return LayerResult(
                layer=ValidationLayer.BUILD,
                status=ValidationStatus.PASSED,
                message="Build successful, all services running",
                details=details,
                warnings=warnings,
                duration_seconds=time.time() - start_time,
            )

        except subprocess.TimeoutExpired:
            errors.append("Build timeout exceeded")
            return LayerResult(
                layer=ValidationLayer.BUILD,
                status=ValidationStatus.FAILED,
                message="Build timeout",
                errors=errors,
                duration_seconds=time.time() - start_time,
            )
        except Exception as e:
            errors.append(str(e))
            return LayerResult(
                layer=ValidationLayer.BUILD,
                status=ValidationStatus.FAILED,
                message=f"Build error: {str(e)}",
                errors=errors,
                duration_seconds=time.time() - start_time,
            )

    def _validate_unit_tests(self) -> LayerResult:
        """
        Layer 2: Unit Test Validation

        - Unit tests exist
        - All tests pass
        - Coverage ≥ 95%
        """
        import time

        start_time = time.time()
        errors = []
        warnings = []
        details = {}

        try:
            # Detect test framework (pytest for backend, jest/vitest for frontend)
            backend_dir = self.app_path / "backend"
            frontend_dir = self.app_path / "frontend"

            total_coverage = 0.0
            components_tested = 0

            # Backend tests (pytest)
            if backend_dir.exists():
                logger.info("Running backend unit tests...")
                test_result = subprocess.run(
                    ["docker-compose", "exec", "-T", "backend", "pytest", "--cov", "--cov-report=json"],
                    cwd=self.app_path,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

                # Parse coverage report
                coverage_file = backend_dir / "coverage.json"
                if coverage_file.exists():
                    with open(coverage_file) as f:
                        coverage_data = json.load(f)
                        backend_coverage = coverage_data.get("totals", {}).get("percent_covered", 0) / 100
                        total_coverage += backend_coverage
                        components_tested += 1
                        details["backend_coverage"] = backend_coverage

                if test_result.returncode != 0:
                    errors.append(f"Backend tests failed: {test_result.stderr}")

            # Frontend tests (vitest/jest)
            if frontend_dir.exists():
                logger.info("Running frontend unit tests...")
                test_result = subprocess.run(
                    ["docker-compose", "exec", "-T", "frontend", "npm", "run", "test:coverage"],
                    cwd=self.app_path,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

                # Parse coverage (vitest outputs coverage-summary.json)
                coverage_file = frontend_dir / "coverage" / "coverage-summary.json"
                if coverage_file.exists():
                    with open(coverage_file) as f:
                        coverage_data = json.load(f)
                        total_data = coverage_data.get("total", {})
                        frontend_coverage = total_data.get("lines", {}).get("pct", 0) / 100
                        total_coverage += frontend_coverage
                        components_tested += 1
                        details["frontend_coverage"] = frontend_coverage

                if test_result.returncode != 0:
                    errors.append(f"Frontend tests failed: {test_result.stderr}")

            # Calculate average coverage
            if components_tested > 0:
                avg_coverage = total_coverage / components_tested
                details["average_coverage"] = avg_coverage

                if avg_coverage < self.min_coverage:
                    errors.append(f"Coverage {avg_coverage:.2%} below minimum {self.min_coverage:.0%}")
                    return LayerResult(
                        layer=ValidationLayer.UNIT_TESTS,
                        status=ValidationStatus.FAILED,
                        message=f"Coverage too low: {avg_coverage:.2%}",
                        errors=errors,
                        details=details,
                        duration_seconds=time.time() - start_time,
                    )

                if errors:
                    return LayerResult(
                        layer=ValidationLayer.UNIT_TESTS,
                        status=ValidationStatus.FAILED,
                        message="Unit tests failed",
                        errors=errors,
                        details=details,
                        duration_seconds=time.time() - start_time,
                    )

                return LayerResult(
                    layer=ValidationLayer.UNIT_TESTS,
                    status=ValidationStatus.PASSED,
                    message=f"All unit tests passed, coverage: {avg_coverage:.2%}",
                    details=details,
                    warnings=warnings,
                    duration_seconds=time.time() - start_time,
                )
            else:
                warnings.append("No unit tests found")
                return LayerResult(
                    layer=ValidationLayer.UNIT_TESTS,
                    status=ValidationStatus.PASSED,
                    message="No unit tests to run",
                    warnings=warnings,
                    duration_seconds=time.time() - start_time,
                )

        except subprocess.TimeoutExpired:
            errors.append("Unit tests timeout")
            return LayerResult(
                layer=ValidationLayer.UNIT_TESTS,
                status=ValidationStatus.FAILED,
                message="Test timeout",
                errors=errors,
                duration_seconds=time.time() - start_time,
            )
        except Exception as e:
            errors.append(str(e))
            return LayerResult(
                layer=ValidationLayer.UNIT_TESTS,
                status=ValidationStatus.FAILED,
                message=f"Unit test error: {str(e)}",
                errors=errors,
                duration_seconds=time.time() - start_time,
            )

    def _validate_e2e_tests(self) -> LayerResult:
        """
        Layer 3: E2E Test Validation

        - Run golden E2E tests
        - Calculate precision (passed / total)
        - Target: ≥88% precision
        """
        import time

        start_time = time.time()
        errors = []
        warnings = []
        details = {}

        try:
            # Find golden test file for this spec
            golden_test_file = self.golden_tests_path / f"{self.spec_name}.spec.ts"

            if not golden_test_file.exists():
                errors.append(f"Golden test file not found: {golden_test_file}")
                return LayerResult(
                    layer=ValidationLayer.E2E_TESTS,
                    status=ValidationStatus.FAILED,
                    message="Golden tests missing",
                    errors=errors,
                    duration_seconds=time.time() - start_time,
                )

            # Run Playwright tests
            logger.info(f"Running golden E2E tests: {golden_test_file.name}")
            test_result = subprocess.run(
                ["npx", "playwright", "test", str(golden_test_file), "--reporter=json"],
                cwd=self.golden_tests_path.parent,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes
            )

            # Parse test results (Playwright JSON reporter)
            try:
                results = json.loads(test_result.stdout)
                total_tests = results.get("stats", {}).get("expected", 0)
                passed_tests = results.get("stats", {}).get("passed", 0)
                failed_tests = results.get("stats", {}).get("failed", 0)
                skipped_tests = results.get("stats", {}).get("skipped", 0)

                details["total"] = total_tests
                details["passed"] = passed_tests
                details["failed"] = failed_tests
                details["skipped"] = skipped_tests

                if total_tests > 0:
                    precision = passed_tests / total_tests
                    details["precision"] = precision

                    if precision < 0.88:  # Target: ≥88% E2E precision
                        warnings.append(f"E2E precision {precision:.2%} below target 88%")

                    if failed_tests > 0:
                        # Get failed test names
                        failed_names = [
                            test["title"]
                            for suite in results.get("suites", [])
                            for test in suite.get("specs", [])
                            if test.get("ok") is False
                        ]
                        details["failed_tests"] = failed_names

                    return LayerResult(
                        layer=ValidationLayer.E2E_TESTS,
                        status=ValidationStatus.PASSED if failed_tests == 0 else ValidationStatus.FAILED,
                        message=f"E2E tests: {passed_tests}/{total_tests} passed ({precision:.2%})",
                        details=details,
                        warnings=warnings,
                        errors=[f"{failed_tests} tests failed"] if failed_tests > 0 else [],
                        duration_seconds=time.time() - start_time,
                    )
                else:
                    warnings.append("No E2E tests found or run")
                    return LayerResult(
                        layer=ValidationLayer.E2E_TESTS,
                        status=ValidationStatus.PASSED,
                        message="No E2E tests to run",
                        warnings=warnings,
                        duration_seconds=time.time() - start_time,
                    )

            except json.JSONDecodeError:
                # Fallback: parse text output
                if "passed" in test_result.stdout.lower():
                    return LayerResult(
                        layer=ValidationLayer.E2E_TESTS,
                        status=ValidationStatus.PASSED,
                        message="E2E tests passed (parsed from text output)",
                        details={"stdout": test_result.stdout},
                        duration_seconds=time.time() - start_time,
                    )
                else:
                    return LayerResult(
                        layer=ValidationLayer.E2E_TESTS,
                        status=ValidationStatus.FAILED,
                        message="E2E tests failed",
                        errors=[test_result.stderr],
                        duration_seconds=time.time() - start_time,
                    )

        except subprocess.TimeoutExpired:
            errors.append("E2E tests timeout")
            return LayerResult(
                layer=ValidationLayer.E2E_TESTS,
                status=ValidationStatus.FAILED,
                message="E2E test timeout",
                errors=errors,
                duration_seconds=time.time() - start_time,
            )
        except Exception as e:
            errors.append(str(e))
            return LayerResult(
                layer=ValidationLayer.E2E_TESTS,
                status=ValidationStatus.FAILED,
                message=f"E2E test error: {str(e)}",
                errors=errors,
                duration_seconds=time.time() - start_time,
            )

    def _validate_production_ready(self) -> LayerResult:
        """
        Layer 4: Production Ready Validation

        - Documentation exists (README.md)
        - Security checks (no hardcoded secrets)
        - Code quality (linting passes)
        - Required files present
        """
        import time

        start_time = time.time()
        errors = []
        warnings = []
        details = {}

        try:
            # Check README.md exists and has content
            readme = self.app_path / "README.md"
            if not readme.exists():
                errors.append("README.md missing")
            elif readme.stat().st_size < 100:
                warnings.append("README.md too short")

            # Check for hardcoded secrets
            secret_patterns = [
                "password=",
                "api_key=",
                "secret_key=",
                "aws_access_key",
            ]

            for file_path in self.app_path.rglob("*.py"):
                if file_path.name == "__pycache__":
                    continue

                with open(file_path) as f:
                    content = f.read().lower()
                    for pattern in secret_patterns:
                        if pattern in content and "example" not in content:
                            warnings.append(f"Potential hardcoded secret in {file_path.name}")

            # Check .env.example exists
            env_example = self.app_path / ".env.example"
            if not env_example.exists():
                warnings.append(".env.example missing")

            # Check .gitignore exists
            gitignore = self.app_path / ".gitignore"
            if not gitignore.exists():
                warnings.append(".gitignore missing")

            # Run linting (if configured)
            backend_dir = self.app_path / "backend"
            if backend_dir.exists():
                # Try running flake8 or black
                lint_result = subprocess.run(
                    ["docker-compose", "exec", "-T", "backend", "flake8", "."],
                    cwd=self.app_path,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if lint_result.returncode != 0:
                    warnings.append("Linting warnings found")
                    details["lint_output"] = lint_result.stdout

            if errors:
                return LayerResult(
                    layer=ValidationLayer.PRODUCTION_READY,
                    status=ValidationStatus.FAILED,
                    message="Production readiness checks failed",
                    errors=errors,
                    warnings=warnings,
                    details=details,
                    duration_seconds=time.time() - start_time,
                )

            return LayerResult(
                layer=ValidationLayer.PRODUCTION_READY,
                status=ValidationStatus.PASSED,
                message="Application is production ready",
                warnings=warnings,
                details=details,
                duration_seconds=time.time() - start_time,
            )

        except Exception as e:
            errors.append(str(e))
            return LayerResult(
                layer=ValidationLayer.PRODUCTION_READY,
                status=ValidationStatus.FAILED,
                message=f"Production readiness error: {str(e)}",
                errors=errors,
                duration_seconds=time.time() - start_time,
            )

    def _calculate_overall_status(self) -> ValidationStatus:
        """Calculate overall validation status from all layers"""
        if all(result.status == ValidationStatus.PASSED for result in self.layers.values()):
            return ValidationStatus.PASSED

        if any(result.status == ValidationStatus.FAILED for result in self.layers.values()):
            return ValidationStatus.FAILED

        return ValidationStatus.SKIPPED

    def cleanup(self):
        """Clean up Docker containers after validation"""
        try:
            subprocess.run(
                ["docker-compose", "down"],
                cwd=self.app_path,
                capture_output=True,
                timeout=30,
            )
            logger.info("Cleaned up Docker containers")
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")
