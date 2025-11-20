"""
Tests for TestResultAdapter - Converts ComplianceReport to TestResult format.

TDD tests for Task Group 1: TestResult Adapter Implementation.
Tests conversion of ComplianceReport (from ComplianceValidator) to TestResult
format expected by CodeRepairAgent.
"""

import pytest
from dataclasses import dataclass, field as dataclass_field
from typing import List, Dict, Any, Optional

from tests.e2e.adapters.test_result_adapter import TestResultAdapter
from src.validation.compliance_validator import ComplianceReport
from tests.precision.validators.code_validator import TestResult


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_compliance_report() -> ComplianceReport:
    """Sample ComplianceReport with mixed compliance issues."""
    return ComplianceReport(
        overall_compliance=0.65,
        entities_implemented=["User", "Order"],
        entities_expected=["User", "Task", "Order"],
        endpoints_implemented=["GET /users", "POST /users"],
        endpoints_expected=["GET /users", "POST /users", "GET /tasks", "POST /tasks"],
        validations_implemented=["email_validation"],
        validations_expected=["email_validation", "price_validation", "stock_validation"],
        missing_requirements=["Entity: Task", "Endpoint: GET /tasks", "Endpoint: POST /tasks"],
        compliance_details={
            "entities": 0.67,
            "endpoints": 0.50,
            "validations": 0.33,
        },
    )


@pytest.fixture
def empty_compliance_report() -> ComplianceReport:
    """Empty ComplianceReport - nothing implemented."""
    return ComplianceReport(
        overall_compliance=0.0,
        entities_implemented=[],
        entities_expected=["User", "Task"],
        endpoints_implemented=[],
        endpoints_expected=["GET /users", "POST /tasks"],
        validations_implemented=[],
        validations_expected=["email_validation"],
        missing_requirements=["Entity: User", "Entity: Task"],
        compliance_details={
            "entities": 0.0,
            "endpoints": 0.0,
            "validations": 0.0,
        },
    )


@pytest.fixture
def perfect_compliance_report() -> ComplianceReport:
    """Perfect ComplianceReport - everything implemented."""
    return ComplianceReport(
        overall_compliance=1.0,
        entities_implemented=["User", "Task"],
        entities_expected=["User", "Task"],
        endpoints_implemented=["GET /users", "POST /tasks"],
        endpoints_expected=["GET /users", "POST /tasks"],
        validations_implemented=["email_validation"],
        validations_expected=["email_validation"],
        missing_requirements=[],
        compliance_details={
            "entities": 1.0,
            "endpoints": 1.0,
            "validations": 1.0,
        },
    )


@pytest.fixture
def partial_entity_compliance_report() -> ComplianceReport:
    """Partial entity compliance - some entities missing."""
    return ComplianceReport(
        overall_compliance=0.70,
        entities_implemented=["User"],
        entities_expected=["User", "Task", "Order"],
        endpoints_implemented=["GET /users"],
        endpoints_expected=["GET /users"],
        validations_implemented=["email_validation"],
        validations_expected=["email_validation"],
        missing_requirements=["Entity: Task", "Entity: Order"],
        compliance_details={
            "entities": 0.33,
            "endpoints": 1.0,
            "validations": 1.0,
        },
    )


# ============================================================================
# Test Cases
# ============================================================================


class TestEntityComplianceConversion:
    """Test entity compliance → TestResult conversion."""

    def test_missing_entities_converted_to_test_failures(
        self, sample_compliance_report: ComplianceReport
    ):
        """Missing entities should create test failures with correct naming."""
        adapter = TestResultAdapter()
        test_results = adapter.convert(sample_compliance_report)

        # Find entity compliance failures
        entity_failures = [
            t for t in test_results if t.test_name.startswith("entity_compliance_")
        ]

        # Should have 1 missing entity (Task)
        assert len(entity_failures) == 1
        assert entity_failures[0].test_name == "entity_compliance_Task"
        assert entity_failures[0].status == "failed"
        assert "Task" in entity_failures[0].error_message
        assert "not found" in entity_failures[0].error_message.lower()

    def test_empty_report_creates_all_entity_failures(
        self, empty_compliance_report: ComplianceReport
    ):
        """Empty report should create failures for all expected entities."""
        adapter = TestResultAdapter()
        test_results = adapter.convert(empty_compliance_report)

        entity_failures = [
            t for t in test_results if t.test_name.startswith("entity_compliance_")
        ]

        # Should have 2 missing entities (User, Task)
        assert len(entity_failures) == 2
        entity_names = {t.test_name.replace("entity_compliance_", "") for t in entity_failures}
        assert entity_names == {"User", "Task"}

    def test_perfect_compliance_has_no_entity_failures(
        self, perfect_compliance_report: ComplianceReport
    ):
        """Perfect compliance should have no entity failures."""
        adapter = TestResultAdapter()
        test_results = adapter.convert(perfect_compliance_report)

        entity_failures = [
            t for t in test_results if t.test_name.startswith("entity_compliance_")
        ]

        assert len(entity_failures) == 0


class TestEndpointComplianceConversion:
    """Test endpoint compliance → TestResult conversion."""

    def test_missing_endpoints_converted_to_test_failures(
        self, sample_compliance_report: ComplianceReport
    ):
        """Missing endpoints should create test failures."""
        adapter = TestResultAdapter()
        test_results = adapter.convert(sample_compliance_report)

        endpoint_failures = [
            t for t in test_results if t.test_name.startswith("endpoint_compliance_")
        ]

        # Should have 2 missing endpoints (GET /tasks, POST /tasks)
        assert len(endpoint_failures) == 2

        # Check specific endpoints
        endpoint_names = {t.test_name for t in endpoint_failures}
        assert "endpoint_compliance_GET_/tasks" in endpoint_names
        assert "endpoint_compliance_POST_/tasks" in endpoint_names

    def test_endpoint_error_messages_include_endpoint_path(
        self, sample_compliance_report: ComplianceReport
    ):
        """Endpoint failures should have descriptive error messages."""
        adapter = TestResultAdapter()
        test_results = adapter.convert(sample_compliance_report)

        endpoint_failures = [
            t for t in test_results if t.test_name.startswith("endpoint_compliance_")
        ]

        for failure in endpoint_failures:
            # Error message should mention the endpoint
            assert "not implemented" in failure.error_message.lower()
            # Should contain HTTP method and path
            assert "/" in failure.error_message


class TestValidationComplianceConversion:
    """Test validation compliance → TestResult conversion."""

    def test_missing_validations_converted_to_test_failures(
        self, sample_compliance_report: ComplianceReport
    ):
        """Missing validations should create test failures."""
        adapter = TestResultAdapter()
        test_results = adapter.convert(sample_compliance_report)

        validation_failures = [
            t for t in test_results if t.test_name.startswith("validation_compliance_")
        ]

        # Should have 2 missing validations (price_validation, stock_validation)
        assert len(validation_failures) == 2

        validation_names = {
            t.test_name.replace("validation_compliance_", "") for t in validation_failures
        }
        assert validation_names == {"price_validation", "stock_validation"}

    def test_validation_error_messages_include_validation_name(
        self, sample_compliance_report: ComplianceReport
    ):
        """Validation failures should have descriptive error messages."""
        adapter = TestResultAdapter()
        test_results = adapter.convert(sample_compliance_report)

        validation_failures = [
            t for t in test_results if t.test_name.startswith("validation_compliance_")
        ]

        for failure in validation_failures:
            # Error message should mention validation
            assert "validation" in failure.error_message.lower()
            assert "not implemented" in failure.error_message.lower()


class TestStackTraceSynthesis:
    """Test stack trace synthesis for TestResult format."""

    def test_stack_trace_includes_file_information(
        self, sample_compliance_report: ComplianceReport
    ):
        """Stack traces should include file and line information."""
        adapter = TestResultAdapter()
        test_results = adapter.convert(sample_compliance_report)

        # All failures should have stack traces
        for test_result in test_results:
            assert test_result.stack_trace is not None
            assert len(test_result.stack_trace) > 0
            # Stack trace should be pytest-style
            assert "File" in test_result.stack_trace or "line" in test_result.stack_trace

    def test_stack_trace_handles_missing_file_info_gracefully(
        self, empty_compliance_report: ComplianceReport
    ):
        """Stack traces should handle missing file information gracefully."""
        adapter = TestResultAdapter()
        test_results = adapter.convert(empty_compliance_report)

        # Should not crash, should generate synthetic stack traces
        for test_result in test_results:
            assert test_result.stack_trace is not None
            # Even without real file info, should have some structure
            assert len(test_result.stack_trace) > 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_convert_handles_empty_report(self, empty_compliance_report: ComplianceReport):
        """Adapter should handle empty compliance reports."""
        adapter = TestResultAdapter()
        test_results = adapter.convert(empty_compliance_report)

        # Should create failures for all expected items
        assert len(test_results) > 0
        assert all(t.status == "failed" for t in test_results)

    def test_convert_handles_perfect_compliance(
        self, perfect_compliance_report: ComplianceReport
    ):
        """Adapter should handle perfect compliance (no failures)."""
        adapter = TestResultAdapter()
        test_results = adapter.convert(perfect_compliance_report)

        # Should return empty list (no failures)
        assert len(test_results) == 0

    def test_adapter_preserves_requirement_context(
        self, sample_compliance_report: ComplianceReport
    ):
        """Adapter should preserve requirement context when available."""
        adapter = TestResultAdapter()
        test_results = adapter.convert(sample_compliance_report)

        # All test results should have proper metadata
        for test_result in test_results:
            assert test_result.test_name is not None
            assert test_result.status == "failed"
            assert test_result.error_message is not None
            assert test_result.stack_trace is not None

    def test_partial_compliance_creates_correct_failure_count(
        self, partial_entity_compliance_report: ComplianceReport
    ):
        """Partial compliance should create correct number of failures."""
        adapter = TestResultAdapter()
        test_results = adapter.convert(partial_entity_compliance_report)

        # Should have exactly 2 failures (Task, Order entities)
        entity_failures = [
            t for t in test_results if t.test_name.startswith("entity_compliance_")
        ]
        assert len(entity_failures) == 2
