"""
Unit Tests for E2EPrecisionPipeline

Tests complete end-to-end pipeline orchestration.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from tests.precision.e2e.precision_pipeline import (
    E2EPrecisionPipeline,
    PipelineResult,
)


class TestPipelineInitialization:
    """Test pipeline initialization and configuration."""

    def test_init_defaults(self):
        """Should initialize with default settings."""
        pipeline = E2EPrecisionPipeline(anthropic_api_key="test-key")

        assert pipeline.auto_correct is False
        assert pipeline.target_precision == 0.92
        assert pipeline.max_iterations == 5

    def test_init_custom_settings(self):
        """Should accept custom settings."""
        pipeline = E2EPrecisionPipeline(
            anthropic_api_key="test-key",
            auto_correct=True,
            target_precision=0.95,
            max_iterations=3,
        )

        assert pipeline.auto_correct is True
        assert pipeline.target_precision == 0.95
        assert pipeline.max_iterations == 3


class TestMockCodeGeneration:
    """Test mock code generation (for testing)."""

    def test_generate_code_mock(self, tmp_path):
        """Should generate mock Python code."""
        pipeline = E2EPrecisionPipeline(anthropic_api_key="test-key")

        code_dir = tmp_path / "code"
        success = pipeline._generate_code_mock(code_dir, "test_module")

        assert success is True
        assert code_dir.exists()
        assert (code_dir / "test_module.py").exists()
        assert (code_dir / "__init__.py").exists()

        # Verify mock code content
        code_content = (code_dir / "test_module.py").read_text()
        assert "class MockAPI" in code_content
        assert "def create" in code_content

    def test_generate_code_mge_v2_not_implemented(self):
        """Should raise NotImplementedError for MGE V2 integration."""
        pipeline = E2EPrecisionPipeline(anthropic_api_key="test-key")

        with pytest.raises(NotImplementedError, match="MGE V2 integration"):
            pipeline._generate_code_mge_v2("discovery doc", Path("/tmp"), "module")


class TestResultsSaving:
    """Test results saving and reporting."""

    def test_save_results(self, tmp_path):
        """Should save pipeline results to JSON file."""
        pipeline = E2EPrecisionPipeline(anthropic_api_key="test-key")

        result = PipelineResult(
            discovery_doc="Test discovery document",
            module_name="test_module",
            tests_generated=10,
            contracts_extracted=25,
            test_file="/path/to/test_file.py",
            code_generated=True,
            code_generation_time=5.5,
            code_directory="/path/to/code",
            precision=0.95,
            total_tests=10,
            passed_tests=9,
            failed_tests=1,
            gate_passed=True,
            must_gate_passed=True,
            should_gate_passed=True,
            total_time=12.5,
            timestamp=datetime.now(),
        )

        pipeline._save_results(result, tmp_path)

        results_file = tmp_path / "pipeline_results.json"
        assert results_file.exists()

        # Verify JSON content
        import json

        results_data = json.loads(results_file.read_text())
        assert results_data["module_name"] == "test_module"
        assert results_data["validation"]["precision"] == 0.95
        assert results_data["validation"]["total_tests"] == 10


class TestEndToEndExecution:
    """Test complete E2E pipeline execution."""

    @patch("tests.precision.e2e.precision_pipeline.ContractTestGenerator")
    @patch("tests.precision.e2e.precision_pipeline.GeneratedCodeValidator")
    def test_execute_success(
        self, mock_validator_class, mock_generator_class, tmp_path
    ):
        """Should execute complete pipeline successfully."""
        # Mock contract generator
        mock_generator = Mock()
        mock_generator.generate_from_discovery.return_value = {
            "tests_generated": 5,
            "contracts_extracted": 15,
            "test_file": "test_module_contracts.py",
        }
        mock_generator_class.return_value = mock_generator

        # Mock code validator
        mock_validator = Mock()
        mock_validation_result = Mock()
        mock_validation_result.precision = 0.95
        mock_validation_result.total_tests = 5
        mock_validation_result.passed_tests = 5
        mock_validation_result.failed_tests = 0
        mock_validation_result.gate_passed = True
        mock_validation_result.must_gate_passed = True
        mock_validation_result.should_gate_passed = True
        mock_validator.validate.return_value = mock_validation_result
        mock_validator_class.return_value = mock_validator

        # Execute pipeline
        pipeline = E2EPrecisionPipeline(anthropic_api_key="test-key")

        result = pipeline.execute(
            discovery_doc="Test discovery document",
            module_name="test_module",
            output_dir=tmp_path,
            mge_v2_enabled=False,  # Use mock
        )

        # Verify result
        assert result.module_name == "test_module"
        assert result.tests_generated == 5
        assert result.contracts_extracted == 15
        assert result.code_generated is True
        assert result.precision == 0.95
        assert result.gate_passed is True

        # Verify calls
        mock_generator.generate_from_discovery.assert_called_once()
        mock_validator.validate.assert_called_once()

    @patch("tests.precision.e2e.precision_pipeline.ContractTestGenerator")
    @patch("tests.precision.e2e.precision_pipeline.GeneratedCodeValidator")
    def test_execute_with_failures(
        self, mock_validator_class, mock_generator_class, tmp_path
    ):
        """Should handle test failures and calculate precision correctly."""
        # Mock contract generator
        mock_generator = Mock()
        mock_generator.generate_from_discovery.return_value = {
            "tests_generated": 10,
            "contracts_extracted": 30,
            "test_file": "test_module_contracts.py",
        }
        mock_generator_class.return_value = mock_generator

        # Mock code validator with failures
        mock_validator = Mock()
        mock_validation_result = Mock()
        mock_validation_result.precision = 0.70  # 70% precision
        mock_validation_result.total_tests = 10
        mock_validation_result.passed_tests = 7
        mock_validation_result.failed_tests = 3
        mock_validation_result.gate_passed = False
        mock_validation_result.must_gate_passed = False
        mock_validation_result.should_gate_passed = True
        mock_validator.validate.return_value = mock_validation_result
        mock_validator_class.return_value = mock_validator

        # Execute pipeline
        pipeline = E2EPrecisionPipeline(
            anthropic_api_key="test-key", auto_correct=False
        )

        result = pipeline.execute(
            discovery_doc="Test discovery document",
            module_name="test_module",
            output_dir=tmp_path,
            mge_v2_enabled=False,
        )

        # Verify result shows failures
        assert result.precision == 0.70
        assert result.passed_tests == 7
        assert result.failed_tests == 3
        assert result.gate_passed is False
        assert result.must_gate_passed is False

    @patch("tests.precision.e2e.precision_pipeline.ContractTestGenerator")
    @patch("tests.precision.e2e.precision_pipeline.GeneratedCodeValidator")
    def test_execute_creates_output_structure(
        self, mock_validator_class, mock_generator_class, tmp_path
    ):
        """Should create proper output directory structure."""
        # Mock components
        mock_generator = Mock()
        mock_generator.generate_from_discovery.return_value = {
            "tests_generated": 5,
            "contracts_extracted": 15,
            "test_file": "test.py",
        }
        mock_generator_class.return_value = mock_generator

        mock_validator = Mock()
        mock_validation_result = Mock()
        mock_validation_result.precision = 0.95
        mock_validation_result.total_tests = 5
        mock_validation_result.passed_tests = 5
        mock_validation_result.failed_tests = 0
        mock_validation_result.gate_passed = True
        mock_validation_result.must_gate_passed = True
        mock_validation_result.should_gate_passed = True
        mock_validator.validate.return_value = mock_validation_result
        mock_validator_class.return_value = mock_validator

        # Execute
        pipeline = E2EPrecisionPipeline(anthropic_api_key="test-key")

        result = pipeline.execute(
            discovery_doc="Test doc",
            module_name="test_module",
            output_dir=tmp_path,
            mge_v2_enabled=False,
        )

        # Verify directory structure
        assert tmp_path.exists()
        assert (tmp_path / "code").exists()
        assert (tmp_path / "code" / "test_module.py").exists()
        assert (tmp_path / "pipeline_results.json").exists()

    def test_execute_creates_temp_dir_if_not_provided(self):
        """Should create temporary directory if output_dir not provided."""
        with patch(
            "tests.precision.e2e.precision_pipeline.ContractTestGenerator"
        ), patch("tests.precision.e2e.precision_pipeline.GeneratedCodeValidator"):
            # Mock everything
            mock_gen = Mock()
            mock_gen.generate_from_discovery.return_value = {
                "tests_generated": 1,
                "contracts_extracted": 1,
                "test_file": "test.py",
            }

            mock_val = Mock()
            mock_val_result = Mock()
            mock_val_result.precision = 1.0
            mock_val_result.total_tests = 1
            mock_val_result.passed_tests = 1
            mock_val_result.failed_tests = 0
            mock_val_result.gate_passed = True
            mock_val_result.must_gate_passed = True
            mock_val_result.should_gate_passed = True
            mock_val.validate.return_value = mock_val_result

            pipeline = E2EPrecisionPipeline(anthropic_api_key="test-key")
            pipeline.contract_generator = mock_gen
            pipeline.code_validator = mock_val

            # Execute without output_dir
            result = pipeline.execute(
                discovery_doc="Test",
                module_name="test",
                output_dir=None,  # Should create temp dir
                mge_v2_enabled=False,
            )

            # Result should have a valid output directory
            assert result.code_directory is not None
            assert "/tmp/" in result.code_directory or "/var/" in result.code_directory


class TestPipelineMetrics:
    """Test pipeline metrics calculation."""

    @patch("tests.precision.e2e.precision_pipeline.ContractTestGenerator")
    @patch("tests.precision.e2e.precision_pipeline.GeneratedCodeValidator")
    def test_timing_metrics(
        self, mock_validator_class, mock_generator_class, tmp_path
    ):
        """Should track timing metrics correctly."""
        # Mock components with delays
        import time

        mock_generator = Mock()

        def slow_generate(*args, **kwargs):
            time.sleep(0.1)  # Simulate work
            return {
                "tests_generated": 5,
                "contracts_extracted": 15,
                "test_file": "test.py",
            }

        mock_generator.generate_from_discovery = slow_generate
        mock_generator_class.return_value = mock_generator

        mock_validator = Mock()
        mock_validation_result = Mock()
        mock_validation_result.precision = 1.0
        mock_validation_result.total_tests = 5
        mock_validation_result.passed_tests = 5
        mock_validation_result.failed_tests = 0
        mock_validation_result.gate_passed = True
        mock_validation_result.must_gate_passed = True
        mock_validation_result.should_gate_passed = True
        mock_validator.validate.return_value = mock_validation_result
        mock_validator_class.return_value = mock_validator

        # Execute
        pipeline = E2EPrecisionPipeline(anthropic_api_key="test-key")

        result = pipeline.execute(
            discovery_doc="Test",
            module_name="test",
            output_dir=tmp_path,
            mge_v2_enabled=False,
        )

        # Verify timing
        assert result.total_time > 0
        assert result.code_generation_time > 0
        assert result.timestamp is not None


class TestAutoCorrection:
    """Test auto-correction configuration (placeholder)."""

    @patch("tests.precision.e2e.precision_pipeline.ContractTestGenerator")
    @patch("tests.precision.e2e.precision_pipeline.GeneratedCodeValidator")
    def test_auto_correction_disabled(
        self, mock_validator_class, mock_generator_class, tmp_path
    ):
        """Should not apply auto-correction when disabled."""
        # Mock low precision result
        mock_generator = Mock()
        mock_generator.generate_from_discovery.return_value = {
            "tests_generated": 10,
            "contracts_extracted": 30,
            "test_file": "test.py",
        }
        mock_generator_class.return_value = mock_generator

        mock_validator = Mock()
        mock_validation_result = Mock()
        mock_validation_result.precision = 0.80  # Below target
        mock_validation_result.total_tests = 10
        mock_validation_result.passed_tests = 8
        mock_validation_result.failed_tests = 2
        mock_validation_result.gate_passed = False
        mock_validation_result.must_gate_passed = True
        mock_validation_result.should_gate_passed = False
        mock_validator.validate.return_value = mock_validation_result
        mock_validator_class.return_value = mock_validator

        # Execute with auto_correct=False
        pipeline = E2EPrecisionPipeline(
            anthropic_api_key="test-key", auto_correct=False, target_precision=0.92
        )

        result = pipeline.execute(
            discovery_doc="Test",
            module_name="test",
            output_dir=tmp_path,
            mge_v2_enabled=False,
        )

        # Auto-correction should NOT be applied
        assert result.auto_correction_applied is False
        assert result.correction_iterations == 0
        assert result.precision == 0.80  # Unchanged


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
