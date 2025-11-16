"""
Unit Tests for MGEV2PrecisionPhase

Tests Phase 8 integration with MGE V2 pipeline.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from tests.precision.integration.mge_v2_precision_phase import (
    MGEV2PrecisionPhase,
    Phase8Result,
)


class TestPhase8Initialization:
    """Test Phase 8 initialization."""

    def test_init_defaults(self):
        """Should initialize with default settings."""
        phase8 = MGEV2PrecisionPhase()

        assert phase8.target_precision == 0.92
        assert phase8.auto_correct is True

    def test_init_custom_settings(self):
        """Should accept custom configuration."""
        phase8 = MGEV2PrecisionPhase(
            target_precision=0.95,
            max_correction_iterations=3,
            auto_correct=False,
            anthropic_api_key="test-key",
        )

        assert phase8.target_precision == 0.95
        assert phase8.auto_correct is False


class TestPhase8Execution:
    """Test complete Phase 8 execution."""

    @pytest.mark.asyncio
    @patch("tests.precision.integration.mge_v2_precision_phase.ContractTestGenerator")
    @patch("tests.precision.integration.mge_v2_precision_phase.GeneratedCodeValidator")
    @patch("tests.precision.integration.mge_v2_precision_phase.PrecisionAutoCorrector")
    async def test_phase8_execution_success(
        self,
        mock_corrector_class,
        mock_validator_class,
        mock_generator_class,
        tmp_path,
    ):
        """Should execute Phase 8 successfully with high precision."""
        # Mock contract generator
        mock_generator = Mock()
        mock_generator.generate_from_discovery.return_value = {
            "tests_generated": 10,
            "contracts_extracted": 30,
        }
        mock_generator_class.return_value = mock_generator

        # Mock validator with high precision (no correction needed)
        mock_validator = Mock()
        mock_validation = Mock()
        mock_validation.precision = 0.95  # Above target
        mock_validation.total_tests = 10
        mock_validation.passed_tests = 10
        mock_validation.failed_tests = 0
        mock_validation.must_gate_passed = True
        mock_validation.should_gate_passed = True
        mock_validation.gate_passed = True

        mock_validator.validate.return_value = mock_validation
        mock_validator_class.return_value = mock_validator

        # Mock corrector (should not be called)
        mock_corrector = Mock()
        mock_corrector_class.return_value = mock_corrector

        # Execute Phase 8
        phase8 = MGEV2PrecisionPhase(target_precision=0.92, auto_correct=True)

        code_dir = tmp_path / "code"
        code_dir.mkdir()
        output_dir = tmp_path / "output"

        result = await phase8.execute_phase_8(
            masterplan_id="mp-001",
            discovery_doc="Test discovery document",
            code_directory=code_dir,
            module_name="test_module",
            output_dir=output_dir,
        )

        # Verify result
        assert result.masterplan_id == "mp-001"
        assert result.module_name == "test_module"
        assert result.tests_generated == 10
        assert result.contracts_extracted == 30
        assert result.initial_precision == 0.95
        assert result.final_precision == 0.95
        assert result.precision_gate_passed is True
        assert result.auto_correction_applied is False
        assert result.correction_iterations == 0
        assert result.gate_passed is True

        # Verify contract generator was called
        mock_generator.generate_from_discovery.assert_called_once()

        # Verify validator was called
        mock_validator.validate.assert_called_once()

        # Verify corrector was NOT called (precision already above target)
        mock_corrector.correct.assert_not_called()

    @pytest.mark.asyncio
    @patch("tests.precision.integration.mge_v2_precision_phase.ContractTestGenerator")
    @patch("tests.precision.integration.mge_v2_precision_phase.GeneratedCodeValidator")
    @patch("tests.precision.integration.mge_v2_precision_phase.PrecisionAutoCorrector")
    async def test_phase8_with_auto_correction(
        self,
        mock_corrector_class,
        mock_validator_class,
        mock_generator_class,
        tmp_path,
    ):
        """Should apply auto-correction when precision below target."""
        # Mock contract generator
        mock_generator = Mock()
        mock_generator.generate_from_discovery.return_value = {
            "tests_generated": 10,
            "contracts_extracted": 30,
        }
        mock_generator_class.return_value = mock_generator

        # Mock validator with low initial precision
        mock_validator = Mock()

        initial_validation = Mock()
        initial_validation.precision = 0.75  # Below target
        initial_validation.total_tests = 10
        initial_validation.passed_tests = 7
        initial_validation.failed_tests = 3

        # Final validation after correction (called twice: once for re-validation)
        final_validation = Mock()
        final_validation.precision = 0.93  # Above target
        final_validation.total_tests = 10
        final_validation.passed_tests = 9
        final_validation.failed_tests = 1
        final_validation.must_gate_passed = True
        final_validation.should_gate_passed = True
        final_validation.gate_passed = True

        mock_validator.validate.side_effect = [
            initial_validation,
            final_validation,  # Re-validation after auto-correction
        ]
        mock_validator_class.return_value = mock_validator

        # Mock corrector
        mock_corrector = Mock()
        mock_correction_result = Mock()
        mock_correction_result.iterations_executed = 2
        mock_correction_result.total_improvement = 0.18
        mock_correction_result.final_precision = 0.93

        mock_corrector.correct.return_value = mock_correction_result
        mock_corrector_class.return_value = mock_corrector

        # Execute Phase 8
        phase8 = MGEV2PrecisionPhase(target_precision=0.92, auto_correct=True)

        code_dir = tmp_path / "code"
        code_dir.mkdir()
        output_dir = tmp_path / "output"

        result = await phase8.execute_phase_8(
            masterplan_id="mp-002",
            discovery_doc="Test discovery document",
            code_directory=code_dir,
            module_name="test_module",
            output_dir=output_dir,
        )

        # Verify result shows correction was applied
        assert result.initial_precision == 0.75
        assert result.final_precision == 0.93
        assert result.auto_correction_applied is True
        assert result.correction_iterations == 2
        assert result.total_improvement == pytest.approx(0.18, abs=0.01)
        assert result.precision_gate_passed is True

        # Verify corrector was called
        mock_corrector.correct.assert_called_once()

    @pytest.mark.asyncio
    @patch("tests.precision.integration.mge_v2_precision_phase.ContractTestGenerator")
    @patch("tests.precision.integration.mge_v2_precision_phase.GeneratedCodeValidator")
    async def test_phase8_auto_correction_disabled(
        self, mock_validator_class, mock_generator_class, tmp_path
    ):
        """Should skip auto-correction when disabled."""
        # Mock contract generator
        mock_generator = Mock()
        mock_generator.generate_from_discovery.return_value = {
            "tests_generated": 5,
            "contracts_extracted": 15,
        }
        mock_generator_class.return_value = mock_generator

        # Mock validator with low precision
        mock_validator = Mock()
        mock_validation = Mock()
        mock_validation.precision = 0.75  # Below target
        mock_validation.total_tests = 5
        mock_validation.passed_tests = 3
        mock_validation.failed_tests = 2
        mock_validation.must_gate_passed = False
        mock_validation.should_gate_passed = True
        mock_validation.gate_passed = False

        mock_validator.validate.return_value = mock_validation
        mock_validator_class.return_value = mock_validator

        # Execute Phase 8 with auto_correct=False
        phase8 = MGEV2PrecisionPhase(target_precision=0.92, auto_correct=False)

        code_dir = tmp_path / "code"
        code_dir.mkdir()
        output_dir = tmp_path / "output"

        result = await phase8.execute_phase_8(
            masterplan_id="mp-003",
            discovery_doc="Test discovery document",
            code_directory=code_dir,
            module_name="test_module",
            output_dir=output_dir,
        )

        # Verify correction was NOT applied
        assert result.auto_correction_applied is False
        assert result.correction_iterations == 0
        assert result.total_improvement == 0.0
        assert result.initial_precision == 0.75
        assert result.final_precision == 0.75
        assert result.precision_gate_passed is False


class TestMetricsSaving:
    """Test metrics saving functionality."""

    @pytest.mark.asyncio
    @patch("tests.precision.integration.mge_v2_precision_phase.ContractTestGenerator")
    @patch("tests.precision.integration.mge_v2_precision_phase.GeneratedCodeValidator")
    async def test_saves_metrics_to_json(
        self, mock_validator_class, mock_generator_class, tmp_path
    ):
        """Should save precision metrics to JSON file."""
        # Mock components
        mock_generator = Mock()
        mock_generator.generate_from_discovery.return_value = {
            "tests_generated": 8,
            "contracts_extracted": 24,
        }
        mock_generator_class.return_value = mock_generator

        mock_validator = Mock()
        mock_validation = Mock()
        mock_validation.precision = 0.95
        mock_validation.total_tests = 8
        mock_validation.passed_tests = 8
        mock_validation.failed_tests = 0
        mock_validation.must_gate_passed = True
        mock_validation.should_gate_passed = True
        mock_validation.gate_passed = True

        mock_validator.validate.return_value = mock_validation
        mock_validator_class.return_value = mock_validator

        # Execute Phase 8
        phase8 = MGEV2PrecisionPhase()

        code_dir = tmp_path / "code"
        code_dir.mkdir()
        output_dir = tmp_path / "output"

        result = await phase8.execute_phase_8(
            masterplan_id="mp-004",
            discovery_doc="Test doc",
            code_directory=code_dir,
            module_name="test",
            output_dir=output_dir,
        )

        # Verify metrics file created
        metrics_file = Path(result.metrics_file)
        assert metrics_file.exists()

        # Verify metrics content
        import json

        metrics = json.loads(metrics_file.read_text())
        assert metrics["masterplan_id"] == "mp-004"
        assert metrics["module_name"] == "test"
        assert metrics["phase"] == 8
        assert metrics["phase_name"] == "precision_validation"
        assert metrics["validation"]["final_precision"] == 0.95
        assert metrics["contract_generation"]["tests_generated"] == 8


class TestGateEnforcement:
    """Test quality gate enforcement."""

    @pytest.mark.asyncio
    @patch("tests.precision.integration.mge_v2_precision_phase.ContractTestGenerator")
    @patch("tests.precision.integration.mge_v2_precision_phase.GeneratedCodeValidator")
    async def test_precision_gate_passed(
        self, mock_validator_class, mock_generator_class, tmp_path
    ):
        """Should pass precision gate when ≥ target."""
        # Mock components
        mock_generator = Mock()
        mock_generator.generate_from_discovery.return_value = {
            "tests_generated": 5,
            "contracts_extracted": 15,
        }
        mock_generator_class.return_value = mock_generator

        mock_validator = Mock()
        mock_validation = Mock()
        mock_validation.precision = 0.93  # Above 92% target
        mock_validation.total_tests = 5
        mock_validation.passed_tests = 5
        mock_validation.failed_tests = 0
        mock_validation.must_gate_passed = True
        mock_validation.should_gate_passed = True
        mock_validation.gate_passed = True

        mock_validator.validate.return_value = mock_validation
        mock_validator_class.return_value = mock_validator

        # Execute Phase 8
        phase8 = MGEV2PrecisionPhase(target_precision=0.92)

        code_dir = tmp_path / "code"
        code_dir.mkdir()
        output_dir = tmp_path / "output"

        result = await phase8.execute_phase_8(
            masterplan_id="mp-005",
            discovery_doc="Test",
            code_directory=code_dir,
            module_name="test",
            output_dir=output_dir,
        )

        # Verify gates
        assert result.precision_gate_passed is True
        assert result.must_gate_passed is True
        assert result.should_gate_passed is True
        assert result.gate_passed is True

    @pytest.mark.asyncio
    @patch("tests.precision.integration.mge_v2_precision_phase.ContractTestGenerator")
    @patch("tests.precision.integration.mge_v2_precision_phase.GeneratedCodeValidator")
    async def test_precision_gate_failed(
        self, mock_validator_class, mock_generator_class, tmp_path
    ):
        """Should fail precision gate when < target."""
        # Mock components
        mock_generator = Mock()
        mock_generator.generate_from_discovery.return_value = {
            "tests_generated": 5,
            "contracts_extracted": 15,
        }
        mock_generator_class.return_value = mock_generator

        mock_validator = Mock()
        mock_validation = Mock()
        mock_validation.precision = 0.85  # Below 92% target
        mock_validation.total_tests = 5
        mock_validation.passed_tests = 4
        mock_validation.failed_tests = 1
        mock_validation.must_gate_passed = True
        mock_validation.should_gate_passed = False
        mock_validation.gate_passed = False

        mock_validator.validate.return_value = mock_validation
        mock_validator_class.return_value = mock_validator

        # Execute Phase 8 with auto_correct disabled
        phase8 = MGEV2PrecisionPhase(target_precision=0.92, auto_correct=False)

        code_dir = tmp_path / "code"
        code_dir.mkdir()
        output_dir = tmp_path / "output"

        result = await phase8.execute_phase_8(
            masterplan_id="mp-006",
            discovery_doc="Test",
            code_directory=code_dir,
            module_name="test",
            output_dir=output_dir,
        )

        # Verify gates
        assert result.precision_gate_passed is False
        assert result.gate_passed is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
