"""
Unit Tests for GeneratedCodeValidator

Tests code validation, test execution, and precision calculation.
"""

import pytest
from pathlib import Path
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from tests.precision.validators.code_validator import (
    GeneratedCodeValidator,
    TestResult,
    ValidationResult,
)


class TestTestResultParsing:
    """Test parsing of pytest test results."""

    def test_parse_passed_test(self):
        """Should parse passed test from pytest JSON."""
        validator = GeneratedCodeValidator()

        test_data = {
            "nodeid": "tests/test_example.py::test_requirement_001_contract_validation",
            "outcome": "passed",
            "duration": 0.123,
        }

        result = validator._parse_test_result(test_data)

        assert result.test_name == "tests/test_example.py::test_requirement_001_contract_validation"
        assert result.status == "passed"
        assert result.duration == 0.123
        assert result.error_message is None
        assert result.requirement_id == 1

    def test_parse_failed_test(self):
        """Should parse failed test with error details."""
        validator = GeneratedCodeValidator()

        test_data = {
            "nodeid": "tests/test_example.py::test_requirement_002_contract_validation",
            "outcome": "failed",
            "duration": 0.5,
            "call": {
                "longrepr": "AssertionError: User not created",
                "traceback": [
                    {"reprcrash": "assert user is not None"},
                    {"reprcrash": "AssertionError"},
                ],
            },
        }

        result = validator._parse_test_result(test_data)

        assert result.status == "failed"
        assert result.error_message == "AssertionError: User not created"
        assert result.stack_trace is not None
        assert "assert user is not None" in result.stack_trace
        assert result.requirement_id == 2

    def test_extract_requirement_id(self):
        """Should extract requirement ID from test name."""
        validator = GeneratedCodeValidator()

        # Standard format
        req_id = validator._extract_requirement_id(
            "test_requirement_042_contract_validation"
        )
        assert req_id == 42

        # Different format
        req_id = validator._extract_requirement_id(
            "tests/test_module.py::test_requirement_005_check"
        )
        assert req_id == 5

        # No requirement ID
        req_id = validator._extract_requirement_id("test_something_else")
        assert req_id is None

    def test_extract_requirement_type_must(self):
        """Should identify MUST requirements from docstring."""
        validator = GeneratedCodeValidator()

        test_data = {
            "call": {"longrepr": "Requirement: MUST create user with email"}
        }

        req_type = validator._extract_requirement_type(test_data, "test_001")
        assert req_type == "must"

    def test_extract_requirement_type_should(self):
        """Should identify SHOULD requirements from docstring."""
        validator = GeneratedCodeValidator()

        test_data = {"call": {"longrepr": "Requirement: SHOULD send notification"}}

        req_type = validator._extract_requirement_type(test_data, "test_002")
        assert req_type == "should"

    def test_extract_requirement_type_default(self):
        """Should default to MUST when type unclear."""
        validator = GeneratedCodeValidator()

        test_data = {"call": {"longrepr": "Some test description"}}

        req_type = validator._extract_requirement_type(test_data, "test_003")
        assert req_type == "must"  # Default to must for safety


class TestPrecisionCalculation:
    """Test precision and metrics calculation."""

    def test_calculate_perfect_precision(self):
        """Should calculate 100% precision when all tests pass."""
        validator = GeneratedCodeValidator()

        test_results = [
            TestResult(
                test_name="test_001",
                status="passed",
                duration=0.1,
                requirement_type="must",
            ),
            TestResult(
                test_name="test_002",
                status="passed",
                duration=0.2,
                requirement_type="must",
            ),
            TestResult(
                test_name="test_003",
                status="passed",
                duration=0.15,
                requirement_type="should",
            ),
        ]

        result = validator._calculate_results(test_results)

        assert result.precision == 1.0
        assert result.total_tests == 3
        assert result.passed_tests == 3
        assert result.failed_tests == 0
        assert result.gate_passed is True

    def test_calculate_partial_precision(self):
        """Should calculate correct precision with failures."""
        validator = GeneratedCodeValidator()

        test_results = [
            TestResult(
                test_name="test_001",
                status="passed",
                duration=0.1,
                requirement_type="must",
            ),
            TestResult(
                test_name="test_002",
                status="failed",
                duration=0.2,
                requirement_type="must",
                error_message="Assertion failed",
            ),
            TestResult(
                test_name="test_003",
                status="passed",
                duration=0.15,
                requirement_type="should",
            ),
            TestResult(
                test_name="test_004",
                status="passed",
                duration=0.12,
                requirement_type="should",
            ),
        ]

        result = validator._calculate_results(test_results)

        assert result.precision == 0.75  # 3/4
        assert result.total_tests == 4
        assert result.passed_tests == 3
        assert result.failed_tests == 1

    def test_must_gate_enforcement(self):
        """Should enforce 100% must requirement gate."""
        validator = GeneratedCodeValidator()

        # All must tests pass - gate passes
        test_results_pass = [
            TestResult(
                test_name="test_001", status="passed", duration=0.1, requirement_type="must"
            ),
            TestResult(
                test_name="test_002", status="passed", duration=0.1, requirement_type="must"
            ),
        ]

        result = validator._calculate_results(test_results_pass)
        assert result.must_gate_passed is True
        assert result.gate_passed is True

        # One must test fails - gate fails
        test_results_fail = [
            TestResult(
                test_name="test_001", status="passed", duration=0.1, requirement_type="must"
            ),
            TestResult(
                test_name="test_002", status="failed", duration=0.1, requirement_type="must"
            ),
        ]

        result = validator._calculate_results(test_results_fail)
        assert result.must_gate_passed is False
        assert result.gate_passed is False

    def test_should_gate_enforcement(self):
        """Should enforce ≥95% should requirement gate."""
        validator = GeneratedCodeValidator(should_gate_threshold=0.95)

        # 96% should tests pass (24/25) - gate passes
        test_results_pass = [
            TestResult(
                test_name=f"test_{i:03d}",
                status="passed" if i < 24 else "failed",
                duration=0.1,
                requirement_type="should",
            )
            for i in range(25)
        ]

        result = validator._calculate_results(test_results_pass)
        assert result.should_tests_passed == 24
        assert result.should_tests_total == 25
        assert result.should_gate_passed is True  # 96% ≥ 95%

        # 90% should tests pass (18/20) - gate fails
        test_results_fail = [
            TestResult(
                test_name=f"test_{i:03d}",
                status="passed" if i < 18 else "failed",
                duration=0.1,
                requirement_type="should",
            )
            for i in range(20)
        ]

        result = validator._calculate_results(test_results_fail)
        assert result.should_tests_passed == 18
        assert result.should_tests_total == 20
        assert result.should_gate_passed is False  # 90% < 95%

    def test_mixed_must_should_requirements(self):
        """Should handle mixed must/should requirements correctly."""
        validator = GeneratedCodeValidator()

        test_results = [
            # Must requirements (2 pass, 0 fail)
            TestResult(
                test_name="test_001", status="passed", duration=0.1, requirement_type="must"
            ),
            TestResult(
                test_name="test_002", status="passed", duration=0.1, requirement_type="must"
            ),
            # Should requirements (18 pass, 2 fail = 90%)
            *[
                TestResult(
                    test_name=f"test_should_{i:03d}",
                    status="passed" if i < 18 else "failed",
                    duration=0.1,
                    requirement_type="should",
                )
                for i in range(20)
            ],
        ]

        result = validator._calculate_results(test_results)

        assert result.must_tests_total == 2
        assert result.must_tests_passed == 2
        assert result.must_gate_passed is True

        assert result.should_tests_total == 20
        assert result.should_tests_passed == 18
        assert result.should_gate_passed is False  # 90% < 95%

        assert result.gate_passed is False  # Must passed but should failed

    def test_zero_tests_edge_case(self):
        """Should handle edge case with no tests."""
        validator = GeneratedCodeValidator()

        result = validator._calculate_results([])

        assert result.precision == 0.0
        assert result.total_tests == 0
        assert result.passed_tests == 0
        assert result.gate_passed is True  # No tests = vacuous truth


class TestWorkspaceManagement:
    """Test workspace creation and cleanup."""

    def test_create_workspace(self, tmp_path):
        """Should create isolated workspace with code and tests."""
        validator = GeneratedCodeValidator()

        # Create mock code directory
        code_dir = tmp_path / "code"
        code_dir.mkdir()
        (code_dir / "module.py").write_text("def func(): pass")

        # Create mock test file
        test_file = tmp_path / "test_contracts.py"
        test_file.write_text("def test_001(): assert True")

        # Create workspace
        workspace = validator._create_workspace(code_dir, test_file)

        assert workspace.exists()
        assert (workspace / "code" / "module.py").exists()
        assert (workspace / "tests" / "test_contracts.py").exists()
        assert (workspace / "code" / "__init__.py").exists()
        assert (workspace / "tests" / "__init__.py").exists()

        # Cleanup
        validator._cleanup_workspace(workspace)
        assert not workspace.exists()

    def test_workspace_with_nonexistent_code_dir(self, tmp_path):
        """Should handle nonexistent code directory gracefully."""
        validator = GeneratedCodeValidator()

        code_dir = tmp_path / "nonexistent"  # Doesn't exist
        test_file = tmp_path / "test.py"
        test_file.write_text("def test(): pass")

        workspace = validator._create_workspace(code_dir, test_file)

        assert workspace.exists()
        assert (workspace / "tests" / "test.py").exists()

        validator._cleanup_workspace(workspace)


class TestStdoutParsing:
    """Test fallback stdout parsing."""

    def test_parse_stdout_basic(self):
        """Should parse basic pytest stdout output."""
        validator = GeneratedCodeValidator()

        stdout = """
tests/test_example.py::test_requirement_001_contract_validation PASSED
tests/test_example.py::test_requirement_002_contract_validation FAILED
tests/test_example.py::test_requirement_003_contract_validation PASSED
"""

        results = validator._parse_stdout(stdout)

        assert len(results) == 3
        assert results[0].status == "passed"
        assert results[0].requirement_id == 1
        assert results[1].status == "failed"
        assert results[1].requirement_id == 2
        assert results[2].status == "passed"
        assert results[2].requirement_id == 3

    def test_parse_stdout_empty(self):
        """Should handle empty stdout."""
        validator = GeneratedCodeValidator()

        results = validator._parse_stdout("")
        assert results == []

    def test_parse_stdout_no_tests(self):
        """Should handle stdout with no test results."""
        validator = GeneratedCodeValidator()

        stdout = """
=============================== test session starts ================================
platform linux -- Python 3.10.12, pytest-8.3.0
No tests ran in 0.01s
"""

        results = validator._parse_stdout(stdout)
        assert results == []


class TestIntegration:
    """Integration tests with mocked pytest execution."""

    @patch("subprocess.run")
    def test_validate_success(self, mock_run, tmp_path):
        """Should validate code successfully with all tests passing."""
        # Setup mock pytest execution
        results_file = tmp_path / "test-results.json"
        results_data = {
            "tests": [
                {
                    "nodeid": "test_requirement_001_contract_validation",
                    "outcome": "passed",
                    "duration": 0.1,
                },
                {
                    "nodeid": "test_requirement_002_contract_validation",
                    "outcome": "passed",
                    "duration": 0.15,
                },
            ]
        }

        # Mock subprocess to write results file
        def write_results(*args, **kwargs):
            results_file.write_text(json.dumps(results_data))
            return Mock(stdout="Tests passed", stderr="", returncode=0)

        mock_run.side_effect = write_results

        # Create test inputs
        code_dir = tmp_path / "code"
        code_dir.mkdir()
        (code_dir / "module.py").write_text("def func(): pass")

        test_file = tmp_path / "test_contracts.py"
        test_file.write_text("def test_001(): assert True")

        # Execute validation
        validator = GeneratedCodeValidator()

        # Patch workspace creation to use tmp_path
        with patch.object(
            validator, "_create_workspace", return_value=tmp_path
        ), patch.object(validator, "_cleanup_workspace"):
            result = validator.validate(code_dir, test_file, "test_module")

        assert result.precision == 1.0
        assert result.total_tests == 2
        assert result.passed_tests == 2
        assert result.gate_passed is True

    @patch("subprocess.run")
    def test_validate_timeout(self, mock_run, tmp_path):
        """Should handle test execution timeout."""
        # Mock timeout
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("pytest", 600)

        code_dir = tmp_path / "code"
        code_dir.mkdir()
        test_file = tmp_path / "test.py"
        test_file.write_text("def test(): pass")

        validator = GeneratedCodeValidator(total_timeout=600)

        with patch.object(
            validator, "_create_workspace", return_value=tmp_path
        ), patch.object(validator, "_cleanup_workspace"):
            result = validator.validate(code_dir, test_file, "test_module")

        assert result.timeout_tests == 1
        assert result.precision == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
