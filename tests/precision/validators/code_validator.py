"""
Generated Code Validator

Executes contract/acceptance tests against generated code and calculates precision.

Architecture:
    Generated Code + Contract Tests → Execute in Sandbox → Results → Precision Score

Features:
    - Pytest execution with timeout and isolation
    - Stack trace capture and analysis
    - Precision calculation: (passed / total) × 100%
    - Detailed failure reporting
    - Support for must/should requirement prioritization
"""

import subprocess
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import tempfile
import shutil


@dataclass
class TestResult:
    """Single test execution result."""

    test_name: str
    status: str  # "passed" | "failed" | "error" | "timeout"
    duration: float  # seconds
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    requirement_id: Optional[int] = None
    requirement_type: Optional[str] = None  # "must" | "should"


@dataclass
class ValidationResult:
    """Complete validation result for generated code."""

    precision: float  # 0.0 - 1.0
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int
    timeout_tests: int

    # Requirement-level breakdown
    must_tests_passed: int
    must_tests_total: int
    should_tests_passed: int
    should_tests_total: int

    # Gate enforcement
    must_gate_passed: bool  # 100% must requirements
    should_gate_passed: bool  # ≥95% should requirements
    gate_passed: bool  # Overall gate status

    # Detailed results
    test_results: List[TestResult]
    execution_time: float  # Total execution time
    timestamp: datetime


class GeneratedCodeValidator:
    """
    Validates generated code by executing contract tests.

    Provides isolated execution environment, timeout control,
    and comprehensive result analysis.
    """

    def __init__(
        self,
        timeout_per_test: int = 60,
        total_timeout: int = 600,
        should_gate_threshold: float = 0.95,
    ):
        """
        Initialize validator.

        Args:
            timeout_per_test: Max seconds per individual test (default: 60s)
            total_timeout: Max seconds for all tests (default: 600s = 10min)
            should_gate_threshold: Min pass rate for should requirements (default: 0.95)
        """
        self.timeout_per_test = timeout_per_test
        self.total_timeout = total_timeout
        self.should_gate_threshold = should_gate_threshold

    def validate(
        self,
        code_dir: Path,
        test_file: Path,
        module_name: str = "generated_code",
    ) -> ValidationResult:
        """
        Validate generated code by executing contract tests.

        Args:
            code_dir: Directory containing generated code
            test_file: Path to contract test file (pytest)
            module_name: Name of module being tested

        Returns:
            ValidationResult with precision and detailed test results
        """
        print(f"\n🧪 Validating generated code: {module_name}")
        print("=" * 60)

        start_time = datetime.now()

        # Create isolated workspace
        workspace = self._create_workspace(code_dir, test_file)

        try:
            # Execute pytest with JSON reporting
            test_results = self._execute_pytest(workspace, test_file.name)

            # Calculate precision and gates
            validation_result = self._calculate_results(test_results)

            # Add execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            validation_result.execution_time = execution_time
            validation_result.timestamp = start_time

            # Report results
            self._report_results(validation_result, module_name)

            return validation_result

        finally:
            # Cleanup workspace
            self._cleanup_workspace(workspace)

    def _create_workspace(self, code_dir: Path, test_file: Path) -> Path:
        """
        Create isolated workspace for test execution.

        Args:
            code_dir: Directory with generated code
            test_file: Contract test file

        Returns:
            Path to temporary workspace
        """
        workspace = Path(tempfile.mkdtemp(prefix="code_validation_"))

        # Create code directory
        code_workspace = workspace / "code"
        code_workspace.mkdir(exist_ok=True)

        # Copy generated code if exists
        if code_dir.exists():
            shutil.copytree(code_dir, code_workspace, dirs_exist_ok=True)

        # Copy test file
        test_dir = workspace / "tests"
        test_dir.mkdir(exist_ok=True)
        shutil.copy(test_file, test_dir / test_file.name)

        # Create __init__.py for proper imports
        (code_workspace / "__init__.py").touch()
        (test_dir / "__init__.py").touch()

        print(f"  📁 Workspace: {workspace}")
        return workspace

    def _cleanup_workspace(self, workspace: Path) -> None:
        """Remove temporary workspace."""
        if workspace.exists():
            shutil.rmtree(workspace)

    def _execute_pytest(self, workspace: Path, test_filename: str) -> List[TestResult]:
        """
        Execute pytest tests and capture results.

        Args:
            workspace: Temporary workspace directory
            test_filename: Name of test file to execute

        Returns:
            List of TestResult objects
        """
        print(f"  ▶️  Executing tests...")

        test_results = []
        results_file = workspace / "test-results.json"

        # Run pytest with JSON report plugin
        cmd = [
            "pytest",
            f"tests/{test_filename}",
            "--json-report",
            f"--json-report-file={results_file}",
            "-v",
            "--tb=short",
            f"--timeout={self.timeout_per_test}",
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=self.total_timeout,
            )

            # Parse JSON results if available
            if results_file.exists():
                with open(results_file) as f:
                    data = json.load(f)

                # FIX 1: Detect pytest collection errors
                collectors = data.get("collectors", [])
                for collector in collectors:
                    if collector.get("outcome") == "failed":
                        # Collection failed - add error
                        error_details = collector.get("longrepr", "Collection failed")
                        test_results.append(
                            TestResult(
                                test_name="pytest_collection_error",
                                status="error",
                                duration=0.0,
                                error_message=f"Pytest collection failed: {error_details}",
                            )
                        )
                        print(f"    ❌ Collection error detected: {error_details[:100]}")

                for test in data.get("tests", []):
                    test_results.append(self._parse_test_result(test))

            else:
                # Fallback: parse from stdout
                print(f"    ⚠️  JSON report not found, parsing stdout")
                test_results = self._parse_stdout(result.stdout)

        except subprocess.TimeoutExpired:
            print(f"    ⏱️  Tests timed out after {self.total_timeout}s")
            test_results.append(
                TestResult(
                    test_name="all_tests",
                    status="timeout",
                    duration=self.total_timeout,
                    error_message=f"Tests exceeded {self.total_timeout}s timeout",
                )
            )

        except Exception as e:
            print(f"    ❌ Execution error: {e}")
            test_results.append(
                TestResult(
                    test_name="execution_error",
                    status="error",
                    duration=0.0,
                    error_message=str(e),
                )
            )

        return test_results

    def _parse_test_result(self, test_data: Dict[str, Any]) -> TestResult:
        """
        Parse pytest JSON test result.

        Args:
            test_data: Test data from pytest JSON report

        Returns:
            TestResult object
        """
        test_name = test_data.get("nodeid", "unknown")
        outcome = test_data.get("outcome", "unknown")
        duration = test_data.get("duration", 0.0)

        # Map pytest outcomes to our statuses
        status_map = {
            "passed": "passed",
            "failed": "failed",
            "error": "error",
            "skipped": "error",
        }
        status = status_map.get(outcome, "error")

        # Extract error details
        error_message = None
        stack_trace = None

        if status != "passed":
            call = test_data.get("call", {})
            error_message = call.get("longrepr", "Unknown error")

            # Extract stack trace if available
            if "traceback" in call:
                stack_trace = "\n".join(
                    [entry.get("reprcrash", "") for entry in call["traceback"]]
                )

        # Extract requirement metadata from test name
        req_id = self._extract_requirement_id(test_name)
        req_type = self._extract_requirement_type(test_data, test_name)

        return TestResult(
            test_name=test_name,
            status=status,
            duration=duration,
            error_message=error_message,
            stack_trace=stack_trace,
            requirement_id=req_id,
            requirement_type=req_type,
        )

    def _extract_requirement_id(self, test_name: str) -> Optional[int]:
        """Extract requirement ID from test name (e.g., test_requirement_001_*)."""
        match = re.search(r"requirement_(\d+)", test_name)
        return int(match.group(1)) if match else None

    def _extract_requirement_type(
        self, test_data: Dict[str, Any], test_name: str
    ) -> Optional[str]:
        """Extract requirement type (must/should) from test docstring or name."""
        # Check docstring
        docstring = test_data.get("call", {}).get("longrepr", "")
        if "MUST" in docstring.upper():
            return "must"
        elif "SHOULD" in docstring.upper():
            return "should"

        # Default to "must" for safety
        return "must"

    def _parse_stdout(self, stdout: str) -> List[TestResult]:
        """
        Fallback: parse test results from pytest stdout.

        Args:
            stdout: pytest stdout output

        Returns:
            List of TestResult objects
        """
        test_results = []
        lines = stdout.split("\n")

        for line in lines:
            # Match pytest output: test_name PASSED|FAILED [percentage]
            match = re.match(r"(.+?)\s+(PASSED|FAILED|ERROR)", line)
            if match:
                test_name = match.group(1).strip()
                outcome = match.group(2).lower()

                status = "passed" if outcome == "passed" else "failed"

                test_results.append(
                    TestResult(
                        test_name=test_name,
                        status=status,
                        duration=0.0,
                        requirement_id=self._extract_requirement_id(test_name),
                        requirement_type="must",  # Default
                    )
                )

        return test_results

    def _calculate_results(self, test_results: List[TestResult]) -> ValidationResult:
        """
        Calculate validation results and precision metrics.

        Args:
            test_results: List of individual test results

        Returns:
            ValidationResult with all metrics
        """
        total_tests = len(test_results)
        passed_tests = sum(1 for t in test_results if t.status == "passed")
        failed_tests = sum(1 for t in test_results if t.status == "failed")
        error_tests = sum(1 for t in test_results if t.status == "error")
        timeout_tests = sum(1 for t in test_results if t.status == "timeout")

        # FIX 2: Reject 0 tests as error (not success)
        if total_tests == 0:
            # No tests found or executed - this is a failure
            test_results.append(
                TestResult(
                    test_name="no_tests_found",
                    status="error",
                    duration=0.0,
                    error_message="Validation failed: 0 tests were discovered or executed",
                )
            )
            total_tests = 1
            error_tests = 1
            print("    ❌ VALIDATION FAILURE: 0 tests found (treating as error)")

        # Calculate precision
        precision = passed_tests / total_tests if total_tests > 0 else 0.0

        # Must/should breakdown
        must_tests = [t for t in test_results if t.requirement_type == "must"]
        should_tests = [t for t in test_results if t.requirement_type == "should"]

        must_tests_total = len(must_tests)
        must_tests_passed = sum(1 for t in must_tests if t.status == "passed")

        should_tests_total = len(should_tests)
        should_tests_passed = sum(1 for t in should_tests if t.status == "passed")

        # FIX 3: Gate enforcement (reject vacuous truth)
        # If 0 MUST tests, we already added a "no_tests_found" error above
        # So this will never be 0, but keeping it defensive
        must_gate_passed = (
            must_tests_passed == must_tests_total if must_tests_total > 0 else False
        )

        # SHOULD tests: if 0 tests, require explicit tests (not vacuous pass)
        should_rate = (
            should_tests_passed / should_tests_total if should_tests_total > 0 else 0.0
        )
        should_gate_passed = should_rate >= self.should_gate_threshold

        gate_passed = must_gate_passed and should_gate_passed

        return ValidationResult(
            precision=precision,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            error_tests=error_tests,
            timeout_tests=timeout_tests,
            must_tests_passed=must_tests_passed,
            must_tests_total=must_tests_total,
            should_tests_passed=should_tests_passed,
            should_tests_total=should_tests_total,
            must_gate_passed=must_gate_passed,
            should_gate_passed=should_gate_passed,
            gate_passed=gate_passed,
            test_results=test_results,
            execution_time=0.0,  # Will be set by validate()
            timestamp=datetime.now(),
        )

    def _report_results(
        self, result: ValidationResult, module_name: str
    ) -> None:
        """
        Print validation results summary.

        Args:
            result: ValidationResult object
            module_name: Name of module being tested
        """
        print("\n📊 Validation Results:")
        print(f"  Module: {module_name}")
        print(f"  Precision: {result.precision:.1%}")
        print(f"  Tests: {result.passed_tests}/{result.total_tests} passed")

        if result.failed_tests > 0:
            print(f"  ❌ Failed: {result.failed_tests}")
        if result.error_tests > 0:
            print(f"  ⚠️  Errors: {result.error_tests}")
        if result.timeout_tests > 0:
            print(f"  ⏱️  Timeouts: {result.timeout_tests}")

        # Gate status
        print(f"\n🚪 Quality Gates:")
        must_status = "✅" if result.must_gate_passed else "❌"
        should_status = "✅" if result.should_gate_passed else "❌"
        gate_status = "✅ PASSED" if result.gate_passed else "❌ FAILED"

        print(
            f"  {must_status} Must Requirements: {result.must_tests_passed}/{result.must_tests_total}"
        )
        print(
            f"  {should_status} Should Requirements: {result.should_tests_passed}/{result.should_tests_total} ({result.should_tests_passed/result.should_tests_total*100 if result.should_tests_total > 0 else 100:.1f}%)"
        )
        print(f"  Overall: {gate_status}")

        print(f"\n⏱️  Execution Time: {result.execution_time:.2f}s")
        print("=" * 60)


# Example usage
if __name__ == "__main__":
    validator = GeneratedCodeValidator()

    # Example: validate generated task management code
    code_dir = Path("/tmp/generated_code/task_management")
    test_file = Path("/tmp/contract_tests/test_task_management_contracts.py")

    result = validator.validate(
        code_dir=code_dir, test_file=test_file, module_name="task_management"
    )

    print(f"\n✅ Validation complete!")
    print(f"Precision: {result.precision:.1%}")
    print(f"Gate Passed: {result.gate_passed}")
