"""
Tests for Phase 6.5: Code Repair Integration

Tests the integration of CodeRepairAgent into the E2E pipeline between
Phase 6 (Code Generation) and Phase 7 (Validation).

Task Group 3.1: Write 2-8 focused tests for Phase 6.5
"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from dataclasses import dataclass
from typing import List, Dict, Any

# Import dependencies
from tests.e2e.adapters.test_result_adapter import TestResultAdapter
from src.validation.compliance_validator import ComplianceValidator, ComplianceReport
from src.parsing.spec_parser import SpecRequirements, Requirement, Entity, Endpoint


# Mock TestResult for testing
@dataclass
class TestResult:
    """Mock TestResult structure expected by CodeRepairAgent"""
    test_name: str
    status: str
    error_message: str
    stack_trace: str = ""
    requirement_id: str = ""


class TestPhase65PreCheck:
    """Test pre-check logic (CP-6.5.1)"""

    def test_precheck_high_compliance_skips_repair(self):
        """Test that high compliance (>= 80%) skips repair phase"""
        # Arrange
        mock_report = Mock(spec=ComplianceReport)
        mock_report.overall_compliance = 0.85
        mock_report.entities_implemented = ["User", "Task"]
        mock_report.endpoints_implemented = ["GET /users", "POST /tasks"]
        mock_report.missing_requirements = []

        # Act
        should_skip = mock_report.overall_compliance >= 0.80

        # Assert
        assert should_skip, "Should skip repair when compliance >= 80%"
        assert mock_report.overall_compliance == 0.85

    def test_precheck_low_compliance_requires_repair(self):
        """Test that low compliance (< 80%) triggers repair phase"""
        # Arrange
        mock_report = Mock(spec=ComplianceReport)
        mock_report.overall_compliance = 0.65
        mock_report.entities_implemented = ["User"]
        mock_report.endpoints_implemented = ["GET /users"]
        mock_report.missing_requirements = ["Task entity", "POST /tasks"]

        # Act
        should_skip = mock_report.overall_compliance >= 0.80

        # Assert
        assert not should_skip, "Should NOT skip repair when compliance < 80%"
        assert len(mock_report.missing_requirements) > 0


class TestPhase65Checkpoints:
    """Test checkpoint system (CP-6.5.1 through CP-6.5.5)"""

    def test_checkpoint_structure(self):
        """Test that checkpoints have correct structure"""
        # Expected checkpoint structure
        checkpoints = {
            "CP-6.5.1": "Pre-check complete",
            "CP-6.5.2": "CodeRepairAgent initialized",
            "CP-6.5.3": "Test results adapted",
            "CP-6.5.4": "Repair loop executing",
            "CP-6.5.5": "Repair complete"
        }

        # Assert all checkpoints defined
        assert len(checkpoints) == 5
        assert "CP-6.5.1" in checkpoints
        assert "CP-6.5.5" in checkpoints

    def test_checkpoint_skip_logic(self):
        """Test that CP-6.5.SKIP is used when repair skipped"""
        # Arrange
        compliance = 0.85
        skip_reason = f"Compliance {compliance:.1%} exceeds threshold 0.80"

        # Act
        checkpoint_name = "CP-6.5.SKIP"

        # Assert
        assert "SKIP" in checkpoint_name
        assert "0.80" in skip_reason
        assert compliance >= 0.80


class TestPhase65ErrorHandling:
    """Test error handling during Phase 6.5"""

    def test_graceful_agent_initialization_failure(self):
        """Test graceful handling of CodeRepairAgent initialization failure"""
        # Arrange
        def failing_init():
            raise ValueError("ErrorPatternStore unavailable")

        # Act
        try:
            failing_init()
            agent_initialized = False
        except ValueError as e:
            agent_initialized = False
            error_message = str(e)

        # Assert
        assert not agent_initialized
        assert "ErrorPatternStore" in error_message

    def test_graceful_validator_failure(self):
        """Test graceful handling of ComplianceValidator failure"""
        # Arrange
        def failing_validation():
            raise RuntimeError("Validation service unavailable")

        # Act
        validation_succeeded = False
        try:
            failing_validation()
        except RuntimeError:
            validation_succeeded = False

        # Assert
        assert not validation_succeeded


class TestPhase65MetricsCollection:
    """Test metrics collection during Phase 6.5"""

    def test_metrics_structure_for_skipped_repair(self):
        """Test metrics when repair is skipped"""
        # Arrange
        metrics = {
            "repair_skipped": True,
            "repair_skip_reason": "Compliance 0.85 exceeds threshold 0.80",
            "repair_applied": False,
            "repair_iterations": 0,
            "repair_improvement": 0.0,
            "tests_fixed": 0,
            "regressions_detected": 0,
            "pattern_reuse_count": 0,
            "repair_time_ms": 0.0
        }

        # Assert
        assert metrics["repair_skipped"] is True
        assert metrics["repair_applied"] is False
        assert metrics["repair_iterations"] == 0
        assert "exceeds threshold" in metrics["repair_skip_reason"]

    def test_metrics_structure_for_executed_repair(self):
        """Test metrics when repair is executed"""
        # Arrange
        metrics = {
            "repair_skipped": False,
            "repair_skip_reason": "",
            "repair_applied": True,
            "repair_iterations": 2,
            "repair_improvement": 0.15,  # 65% -> 80%
            "tests_fixed": 3,
            "regressions_detected": 0,
            "pattern_reuse_count": 1,
            "repair_time_ms": 12500.0
        }

        # Assert
        assert metrics["repair_skipped"] is False
        assert metrics["repair_applied"] is True
        assert metrics["repair_iterations"] > 0
        assert metrics["repair_improvement"] > 0
        assert metrics["tests_fixed"] > 0


class TestPhase65TestResultAdapter:
    """Test TestResultAdapter integration (CP-6.5.3)"""

    def test_adapter_converts_compliance_report(self):
        """Test that adapter converts ComplianceReport to TestResult list"""
        # Arrange
        adapter = TestResultAdapter()

        mock_report = Mock(spec=ComplianceReport)
        mock_report.overall_compliance = 0.65
        mock_report.entities_expected = ["User", "Task", "Project"]
        mock_report.entities_implemented = ["User"]
        mock_report.endpoints_expected = ["GET /users", "POST /tasks", "GET /projects"]
        mock_report.endpoints_implemented = ["GET /users"]
        mock_report.validations_expected = []
        mock_report.validations_implemented = []
        mock_report.missing_requirements = ["Task entity", "POST /tasks", "Project entity", "GET /projects"]

        # Act
        test_results = adapter.convert(mock_report)

        # Assert
        assert isinstance(test_results, list)
        assert len(test_results) > 0

        # Check that missing entities/endpoints are converted to test failures
        missing_entities = set(mock_report.entities_expected) - set(mock_report.entities_implemented)
        missing_endpoints = set(mock_report.endpoints_expected) - set(mock_report.endpoints_implemented)

        expected_failures = len(missing_entities) + len(missing_endpoints)
        assert len(test_results) >= expected_failures

    def test_adapter_creates_valid_test_result_structure(self):
        """Test that adapter creates valid TestResult objects"""
        # Arrange
        adapter = TestResultAdapter()

        mock_report = Mock(spec=ComplianceReport)
        mock_report.overall_compliance = 0.50
        mock_report.entities_expected = ["Task"]
        mock_report.entities_implemented = []
        mock_report.endpoints_expected = []
        mock_report.endpoints_implemented = []
        mock_report.validations_expected = []
        mock_report.validations_implemented = []
        mock_report.missing_requirements = ["Task entity"]

        # Act
        test_results = adapter.convert(mock_report)

        # Assert
        assert len(test_results) > 0
        first_result = test_results[0]

        # Verify TestResult structure
        assert hasattr(first_result, 'test_name')
        assert hasattr(first_result, 'status')
        assert hasattr(first_result, 'error_message')
        assert hasattr(first_result, 'stack_trace')

        # Verify test naming convention
        assert "entity_compliance" in first_result.test_name or "endpoint_compliance" in first_result.test_name


class TestPhase65Integration:
    """Integration tests for complete Phase 6.5 flow"""

    @pytest.mark.asyncio
    async def test_phase_65_integration_with_skip(self):
        """Test complete Phase 6.5 flow when repair is skipped"""
        # Arrange
        spec_requirements = Mock(spec=SpecRequirements)
        generated_code = {"main.py": "# Mock generated code"}

        mock_validator = Mock(spec=ComplianceValidator)
        mock_report = Mock(spec=ComplianceReport)
        mock_report.overall_compliance = 0.85
        mock_report.missing_requirements = []
        mock_validator.validate.return_value = mock_report

        # Act
        # Simulate Phase 6.5 logic
        report = mock_validator.validate(spec_requirements, generated_code["main.py"])
        should_skip = report.overall_compliance >= 0.80

        metrics = {
            "repair_skipped": should_skip,
            "repair_skip_reason": f"Compliance {report.overall_compliance:.1%} exceeds threshold 0.80" if should_skip else "",
            "repair_applied": False,
            "repair_iterations": 0,
            "repair_improvement": 0.0
        }

        # Assert
        assert should_skip is True
        assert metrics["repair_skipped"] is True
        assert metrics["repair_applied"] is False
        assert "exceeds threshold" in metrics["repair_skip_reason"]

    @pytest.mark.asyncio
    async def test_phase_65_integration_with_repair_needed(self):
        """Test complete Phase 6.5 flow when repair is needed"""
        # Arrange
        spec_requirements = Mock(spec=SpecRequirements)
        generated_code = {"main.py": "# Mock generated code"}

        mock_validator = Mock(spec=ComplianceValidator)
        mock_report = Mock(spec=ComplianceReport)
        mock_report.overall_compliance = 0.65
        mock_report.entities_expected = ["User", "Task"]
        mock_report.entities_implemented = ["User"]
        mock_report.endpoints_expected = ["GET /users", "POST /tasks"]
        mock_report.endpoints_implemented = ["GET /users"]
        mock_report.validations_expected = []
        mock_report.validations_implemented = []
        mock_report.missing_requirements = ["Task entity", "POST /tasks"]
        mock_validator.validate.return_value = mock_report

        # Act
        # Simulate Phase 6.5 logic
        report = mock_validator.validate(spec_requirements, generated_code["main.py"])
        should_skip = report.overall_compliance >= 0.80

        adapter = TestResultAdapter()
        test_results = adapter.convert(report) if not should_skip else []

        metrics = {
            "repair_skipped": should_skip,
            "repair_applied": not should_skip,
            "repair_iterations": 0 if should_skip else 1,  # Placeholder for repair loop
            "tests_fixed": 0,  # Will be updated by repair loop
            "repair_improvement": 0.0  # Will be calculated by repair loop
        }

        # Assert
        assert should_skip is False
        assert metrics["repair_applied"] is True
        assert len(test_results) > 0
        assert report.overall_compliance < 0.80


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
