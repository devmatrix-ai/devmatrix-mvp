"""
Unit Tests for PrecisionAutoCorrector

Tests auto-correction loop, strategy selection, and iterative improvement.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from tests.precision.correction.auto_corrector import (
    PrecisionAutoCorrector,
    CorrectionIteration,
    CorrectionResult,
)
from tests.precision.correction.failure_analyzer import FailureAnalysis
from tests.precision.validators.code_validator import (
    ValidationResult,
    TestResult,
)


class TestCorrectorInitialization:
    """Test auto-corrector initialization."""

    def test_init_defaults(self):
        """Should initialize with default settings."""
        corrector = PrecisionAutoCorrector()

        assert corrector.target_precision == 0.92
        assert corrector.max_iterations == 5
        assert corrector.api_key is None

    def test_init_custom_settings(self):
        """Should accept custom configuration."""
        corrector = PrecisionAutoCorrector(
            target_precision=0.95,
            max_iterations=3,
            anthropic_api_key="test-key",
        )

        assert corrector.target_precision == 0.95
        assert corrector.max_iterations == 3
        assert corrector.api_key == "test-key"


class TestStrategySelection:
    """Test regeneration strategy selection logic."""

    def test_first_iteration_uses_standard(self):
        """Should use standard strategy for first iteration."""
        corrector = PrecisionAutoCorrector()

        failures = [
            Mock(severity="medium", error_category="wrong_logic"),
        ]

        strategy = corrector._select_strategy(iteration=1, failures=failures)

        assert strategy == "standard"

    def test_high_critical_failures_use_enhanced_context(self):
        """Should use enhanced_context when >50% critical failures."""
        corrector = PrecisionAutoCorrector()

        failures = [
            Mock(severity="critical"),
            Mock(severity="critical"),
            Mock(severity="medium"),
        ]

        strategy = corrector._select_strategy(iteration=2, failures=failures)

        assert strategy == "enhanced_context"

    def test_later_iterations_use_temperature_adjusted(self):
        """Should use temperature_adjusted for iteration 3+."""
        corrector = PrecisionAutoCorrector()

        failures = [
            Mock(severity="medium"),
        ]

        strategy = corrector._select_strategy(iteration=3, failures=failures)

        assert strategy == "temperature_adjusted"

    def test_default_strategy_improved_prompts(self):
        """Should use improved_prompts as default for iteration 2."""
        corrector = PrecisionAutoCorrector()

        failures = [
            Mock(severity="medium"),
        ]

        strategy = corrector._select_strategy(iteration=2, failures=failures)

        assert strategy == "improved_prompts"


class TestMockRegeneration:
    """Test mock atom regeneration."""

    def test_mock_regenerate_counts_atoms(self):
        """Should return count of atoms regenerated."""
        corrector = PrecisionAutoCorrector()

        atoms = {"atom-001", "atom-002", "atom-003"}
        code_dir = Path("/tmp/code")

        count = corrector._mock_regenerate(atoms, code_dir, "standard")

        assert count == 3

    def test_regenerate_atoms_uses_mock_by_default(self):
        """Should use mock regeneration when no custom function provided."""
        corrector = PrecisionAutoCorrector()

        failures = [
            Mock(suspected_atoms=["atom-001", "atom-002"]),
            Mock(suspected_atoms=["atom-002", "atom-003"]),
        ]

        count = corrector._regenerate_atoms(
            failures=failures,
            code_dir=Path("/tmp"),
            strategy="standard",
            regenerate_func=None,
        )

        # Should regenerate unique atoms (001, 002, 003 = 3 unique)
        assert count == 3

    def test_regenerate_atoms_uses_custom_function(self):
        """Should use custom regeneration function when provided."""
        corrector = PrecisionAutoCorrector()

        custom_func = Mock(return_value=5)

        failures = [
            Mock(suspected_atoms=["atom-001"]),
        ]

        count = corrector._regenerate_atoms(
            failures=failures,
            code_dir=Path("/tmp"),
            strategy="standard",
            regenerate_func=custom_func,
        )

        assert count == 5
        custom_func.assert_called_once()


class TestEarlyStoppingSuccess:
    """Test early stopping when already at target."""

    @patch("tests.precision.correction.auto_corrector.GeneratedCodeValidator")
    def test_stops_when_already_at_target(self, mock_validator_class, tmp_path):
        """Should stop immediately if initial precision ≥ target."""
        # Mock validator returning high initial precision
        mock_validator = Mock()
        mock_validation = Mock()
        mock_validation.precision = 0.95  # Above 92% target
        mock_validation.test_results = []
        mock_validation.must_tests_passed = 10
        mock_validation.must_tests_total = 10
        mock_validation.should_tests_passed = 5
        mock_validation.should_tests_total = 5
        mock_validation.must_gate_passed = True
        mock_validation.should_gate_passed = True

        mock_validator.validate.return_value = mock_validation
        mock_validator_class.return_value = mock_validator

        # Execute correction
        corrector = PrecisionAutoCorrector(target_precision=0.92)

        code_dir = tmp_path / "code"
        code_dir.mkdir()
        test_file = tmp_path / "test.py"
        test_file.touch()

        result = corrector.correct(
            code_dir=code_dir,
            test_file=test_file,
            module_name="test",
        )

        # Should stop immediately
        assert result.iterations_executed == 0
        assert result.target_reached is True
        assert result.initial_precision == 0.95
        assert result.final_precision == 0.95


class TestCorrectionLoop:
    """Test complete correction loop execution."""

    @patch("tests.precision.correction.auto_corrector.FailureAnalyzer")
    @patch("tests.precision.correction.auto_corrector.GeneratedCodeValidator")
    def test_correction_improves_precision(
        self, mock_validator_class, mock_analyzer_class, tmp_path
    ):
        """Should improve precision through iterations."""
        # Setup mock validator with improving precision
        mock_validator = Mock()

        # Initial validation: 70% precision
        initial_validation = Mock()
        initial_validation.precision = 0.70
        initial_validation.test_results = [
            Mock(status="failed"),
            Mock(status="failed"),
            Mock(status="failed"),
        ]

        # After iteration 1: 85% precision
        iteration1_validation = Mock()
        iteration1_validation.precision = 0.85
        iteration1_validation.test_results = [
            Mock(status="failed"),
        ]

        # After iteration 2: 93% precision (target reached)
        iteration2_validation = Mock()
        iteration2_validation.precision = 0.93
        iteration2_validation.test_results = []
        iteration2_validation.must_tests_passed = 10
        iteration2_validation.must_tests_total = 10
        iteration2_validation.should_tests_passed = 5
        iteration2_validation.should_tests_total = 5
        iteration2_validation.must_gate_passed = True
        iteration2_validation.should_gate_passed = True

        mock_validator.validate.side_effect = [
            initial_validation,
            iteration1_validation,
            iteration2_validation,
        ]
        mock_validator_class.return_value = mock_validator

        # Setup mock analyzer
        mock_analyzer = Mock()
        mock_failure1 = Mock(suspected_atoms=["atom-001"], severity="medium")
        mock_failure2 = Mock(suspected_atoms=["atom-002"], severity="low")

        mock_analyzer.analyze_failures.side_effect = [
            [mock_failure1, mock_failure2],  # Iteration 1
            [mock_failure2],  # Iteration 2
        ]
        mock_analyzer_class.return_value = mock_analyzer

        # Execute correction
        corrector = PrecisionAutoCorrector(target_precision=0.92, max_iterations=5)

        code_dir = tmp_path / "code"
        code_dir.mkdir()
        test_file = tmp_path / "test.py"
        test_file.touch()

        result = corrector.correct(
            code_dir=code_dir,
            test_file=test_file,
            module_name="test",
        )

        # Should reach target in 2 iterations
        assert result.iterations_executed == 2
        assert result.target_reached is True
        assert result.initial_precision == 0.70
        assert result.final_precision == 0.93
        assert result.total_improvement == pytest.approx(0.23, abs=0.01)
        assert len(result.iterations) == 2

    @patch("tests.precision.correction.auto_corrector.FailureAnalyzer")
    @patch("tests.precision.correction.auto_corrector.GeneratedCodeValidator")
    def test_stops_at_max_iterations(
        self, mock_validator_class, mock_analyzer_class, tmp_path
    ):
        """Should stop at max iterations even if target not reached."""
        # Mock validator that never reaches target
        mock_validator = Mock()

        initial_validation = Mock()
        initial_validation.precision = 0.70
        initial_validation.test_results = [Mock(status="failed")]

        # Always return same low precision
        ongoing_validation = Mock()
        ongoing_validation.precision = 0.75
        ongoing_validation.test_results = [Mock(status="failed")]
        ongoing_validation.must_tests_passed = 7
        ongoing_validation.must_tests_total = 10
        ongoing_validation.should_tests_passed = 5
        ongoing_validation.should_tests_total = 5
        ongoing_validation.must_gate_passed = False
        ongoing_validation.should_gate_passed = True

        mock_validator.validate.side_effect = [
            initial_validation,
            ongoing_validation,
            ongoing_validation,
            ongoing_validation,
        ]
        mock_validator_class.return_value = mock_validator

        # Mock analyzer
        mock_analyzer = Mock()
        mock_failure = Mock(suspected_atoms=["atom-001"], severity="medium")
        mock_analyzer.analyze_failures.return_value = [mock_failure]
        mock_analyzer_class.return_value = mock_analyzer

        # Execute correction with max_iterations=3
        corrector = PrecisionAutoCorrector(target_precision=0.92, max_iterations=3)

        code_dir = tmp_path / "code"
        code_dir.mkdir()
        test_file = tmp_path / "test.py"
        test_file.touch()

        result = corrector.correct(
            code_dir=code_dir,
            test_file=test_file,
            module_name="test",
        )

        # Should stop at max iterations
        assert result.iterations_executed == 3
        assert result.target_reached is False
        assert result.final_precision < result.target_precision

    @patch("tests.precision.correction.auto_corrector.FailureAnalyzer")
    @patch("tests.precision.correction.auto_corrector.GeneratedCodeValidator")
    def test_stops_when_no_failures(
        self, mock_validator_class, mock_analyzer_class, tmp_path
    ):
        """Should stop early if no failures found."""
        # Mock validator
        mock_validator = Mock()

        initial_validation = Mock()
        initial_validation.precision = 0.85
        initial_validation.test_results = [Mock(status="passed")]

        mock_validator.validate.return_value = initial_validation
        mock_validator_class.return_value = mock_validator

        # Mock analyzer returning no failures
        mock_analyzer = Mock()
        mock_analyzer.analyze_failures.return_value = []  # No failures
        mock_analyzer_class.return_value = mock_analyzer

        # Execute correction
        corrector = PrecisionAutoCorrector(target_precision=0.92, max_iterations=5)

        code_dir = tmp_path / "code"
        code_dir.mkdir()
        test_file = tmp_path / "test.py"
        test_file.touch()

        result = corrector.correct(
            code_dir=code_dir,
            test_file=test_file,
            module_name="test",
        )

        # Should stop after 1 iteration (no failures found)
        assert result.iterations_executed == 1
        assert result.final_precision == 0.85


class TestCorrectionHistory:
    """Test correction history tracking."""

    @patch("tests.precision.correction.auto_corrector.FailureAnalyzer")
    @patch("tests.precision.correction.auto_corrector.GeneratedCodeValidator")
    def test_tracks_iteration_history(
        self, mock_validator_class, mock_analyzer_class, tmp_path
    ):
        """Should track detailed iteration history."""
        # Setup mocks for 2 iterations
        mock_validator = Mock()

        initial_validation = Mock()
        initial_validation.precision = 0.70
        initial_validation.test_results = [Mock(status="failed")]

        iteration1_validation = Mock()
        iteration1_validation.precision = 0.80
        iteration1_validation.test_results = [Mock(status="failed")]

        iteration2_validation = Mock()
        iteration2_validation.precision = 0.93
        iteration2_validation.test_results = []
        iteration2_validation.must_tests_passed = 10
        iteration2_validation.must_tests_total = 10
        iteration2_validation.should_tests_passed = 5
        iteration2_validation.should_tests_total = 5
        iteration2_validation.must_gate_passed = True
        iteration2_validation.should_gate_passed = True

        mock_validator.validate.side_effect = [
            initial_validation,
            iteration1_validation,
            iteration2_validation,
        ]
        mock_validator_class.return_value = mock_validator

        mock_analyzer = Mock()
        mock_failure = Mock(suspected_atoms=["atom-001"], severity="medium")
        mock_analyzer.analyze_failures.return_value = [mock_failure]
        mock_analyzer_class.return_value = mock_analyzer

        # Execute correction
        corrector = PrecisionAutoCorrector(target_precision=0.92)

        code_dir = tmp_path / "code"
        code_dir.mkdir()
        test_file = tmp_path / "test.py"
        test_file.touch()

        result = corrector.correct(
            code_dir=code_dir,
            test_file=test_file,
            module_name="test",
        )

        # Should track both iterations
        assert len(result.iterations) == 2

        # Check iteration 1
        iter1 = result.iterations[0]
        assert iter1.iteration == 1
        assert iter1.precision_before == 0.70
        assert iter1.precision_after == 0.80
        assert iter1.improvement == pytest.approx(0.10, abs=0.01)

        # Check iteration 2
        iter2 = result.iterations[1]
        assert iter2.iteration == 2
        assert iter2.precision_before == 0.80
        assert iter2.precision_after == 0.93
        assert iter2.improvement == pytest.approx(0.13, abs=0.01)

    def test_save_correction_history(self, tmp_path):
        """Should save correction history to JSON file."""
        corrector = PrecisionAutoCorrector()

        # Add mock iterations
        corrector.iterations = [
            CorrectionIteration(
                iteration=1,
                precision_before=0.70,
                precision_after=0.85,
                failures_analyzed=5,
                atoms_regenerated=3,
                regeneration_strategy="standard",
                improvement=0.15,
                timestamp=datetime.now(),
            ),
            CorrectionIteration(
                iteration=2,
                precision_before=0.85,
                precision_after=0.93,
                failures_analyzed=2,
                atoms_regenerated=2,
                regeneration_strategy="improved_prompts",
                improvement=0.08,
                timestamp=datetime.now(),
            ),
        ]

        # Save history
        output_file = tmp_path / "correction_history.json"
        corrector.save_correction_history(output_file)

        # Verify file created
        assert output_file.exists()

        # Verify content
        import json

        data = json.loads(output_file.read_text())
        assert "iterations" in data
        assert len(data["iterations"]) == 2
        assert data["iterations"][0]["iteration"] == 1
        assert data["iterations"][1]["iteration"] == 2


class TestResultMetrics:
    """Test correction result metrics calculation."""

    @patch("tests.precision.correction.auto_corrector.FailureAnalyzer")
    @patch("tests.precision.correction.auto_corrector.GeneratedCodeValidator")
    def test_calculates_total_improvement(
        self, mock_validator_class, mock_analyzer_class, tmp_path
    ):
        """Should calculate total precision improvement."""
        # Mock 2 iterations: 70% → 85% → 93%
        mock_validator = Mock()

        initial_validation = Mock()
        initial_validation.precision = 0.70
        initial_validation.test_results = [Mock(status="failed")]

        iter1_validation = Mock()
        iter1_validation.precision = 0.85
        iter1_validation.test_results = [Mock(status="failed")]

        final_validation = Mock()
        final_validation.precision = 0.93
        final_validation.test_results = []
        final_validation.must_tests_passed = 10
        final_validation.must_tests_total = 10
        final_validation.should_tests_passed = 5
        final_validation.should_tests_total = 5
        final_validation.must_gate_passed = True
        final_validation.should_gate_passed = True

        mock_validator.validate.side_effect = [
            initial_validation,
            iter1_validation,
            final_validation,
        ]
        mock_validator_class.return_value = mock_validator

        mock_analyzer = Mock()
        mock_failure = Mock(suspected_atoms=["atom-001"], severity="medium")
        mock_analyzer.analyze_failures.return_value = [mock_failure]
        mock_analyzer_class.return_value = mock_analyzer

        # Execute correction
        corrector = PrecisionAutoCorrector(target_precision=0.92)

        code_dir = tmp_path / "code"
        code_dir.mkdir()
        test_file = tmp_path / "test.py"
        test_file.touch()

        result = corrector.correct(
            code_dir=code_dir,
            test_file=test_file,
            module_name="test",
        )

        # Total improvement: 93% - 70% = 23%
        assert result.total_improvement == pytest.approx(0.23, abs=0.01)

        # Average improvement per iteration: 23% / 2 = 11.5%
        assert result.avg_improvement_per_iteration == pytest.approx(0.115, abs=0.01)

    @patch("tests.precision.correction.auto_corrector.FailureAnalyzer")
    @patch("tests.precision.correction.auto_corrector.GeneratedCodeValidator")
    def test_tracks_total_atoms_regenerated(
        self, mock_validator_class, mock_analyzer_class, tmp_path
    ):
        """Should track total atoms regenerated across iterations."""
        # Mock validator
        mock_validator = Mock()

        initial_validation = Mock()
        initial_validation.precision = 0.70
        initial_validation.test_results = [Mock(status="failed")]

        iter1_validation = Mock()
        iter1_validation.precision = 0.85
        iter1_validation.test_results = [Mock(status="failed")]

        final_validation = Mock()
        final_validation.precision = 0.93
        final_validation.test_results = []
        final_validation.must_tests_passed = 10
        final_validation.must_tests_total = 10
        final_validation.should_tests_passed = 5
        final_validation.should_tests_total = 5
        final_validation.must_gate_passed = True
        final_validation.should_gate_passed = True

        mock_validator.validate.side_effect = [
            initial_validation,
            iter1_validation,
            final_validation,
        ]
        mock_validator_class.return_value = mock_validator

        # Mock analyzer with different atom sets
        mock_analyzer = Mock()

        # Iteration 1: 3 atoms
        iter1_failures = [
            Mock(suspected_atoms=["atom-001", "atom-002"]),
            Mock(suspected_atoms=["atom-003"]),
        ]

        # Iteration 2: 2 atoms
        iter2_failures = [
            Mock(suspected_atoms=["atom-004", "atom-005"]),
        ]

        mock_analyzer.analyze_failures.side_effect = [iter1_failures, iter2_failures]
        mock_analyzer_class.return_value = mock_analyzer

        # Execute correction
        corrector = PrecisionAutoCorrector(target_precision=0.92)

        code_dir = tmp_path / "code"
        code_dir.mkdir()
        test_file = tmp_path / "test.py"
        test_file.touch()

        result = corrector.correct(
            code_dir=code_dir,
            test_file=test_file,
            module_name="test",
        )

        # Total atoms: 3 (iter1) + 2 (iter2) = 5
        assert result.total_atoms_regenerated == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
