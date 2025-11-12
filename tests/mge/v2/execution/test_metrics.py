"""
Tests for MGE V2 Execution Metrics

Tests for Prometheus metrics and success rate calculation.
"""
import pytest
from unittest.mock import Mock, patch
from src.mge.v2.execution.metrics import (
    calculate_success_rate,
    update_success_rate,
    RETRY_SUCCESS_RATE,
    RETRY_ATTEMPTS_TOTAL
)


class TestSuccessRateCalculation:
    """Test success rate calculation logic."""

    def test_calculate_success_rate_with_no_attempts(self):
        """Test that success rate returns 0.0 when no attempts have been made."""
        # Mock RETRY_ATTEMPTS_TOTAL.collect() to return empty samples
        with patch('src.mge.v2.execution.metrics.RETRY_ATTEMPTS_TOTAL') as mock_counter:
            # Create mock metric with no samples (total_attempts = 0)
            mock_metric = Mock()
            mock_metric.samples = []
            mock_counter.collect.return_value = [mock_metric]

            result = calculate_success_rate()

            # Should return 0.0 when no attempts (line 122)
            assert result == 0.0

    def test_calculate_success_rate_with_attempts(self):
        """Test that success rate is calculated when attempts exist."""
        with patch('src.mge.v2.execution.metrics.RETRY_ATTEMPTS_TOTAL') as mock_counter:
            # Create mock metric with sample value > 0
            mock_sample = Mock()
            mock_sample.value = 10.0

            mock_metric = Mock()
            mock_metric.samples = [mock_sample]
            mock_counter.collect.return_value = [mock_metric]

            result = calculate_success_rate()

            # Should return placeholder value 0.95 when attempts exist
            assert result == 0.95

    def test_calculate_success_rate_exception_handling(self):
        """Test that exceptions in calculate_success_rate are caught and return 0.0."""
        with patch('src.mge.v2.execution.metrics.RETRY_ATTEMPTS_TOTAL') as mock_counter:
            # Make collect() raise an exception
            mock_counter.collect.side_effect = Exception("Metrics collection failed")

            result = calculate_success_rate()

            # Should return 0.0 on exception (lines 128-129)
            assert result == 0.0

    def test_update_success_rate_calls_calculate(self):
        """Test that update_success_rate calls calculate_success_rate and sets gauge."""
        with patch('src.mge.v2.execution.metrics.calculate_success_rate') as mock_calc:
            mock_calc.return_value = 0.85

            with patch('src.mge.v2.execution.metrics.RETRY_SUCCESS_RATE') as mock_gauge:
                update_success_rate()

                # Should call calculate_success_rate
                mock_calc.assert_called_once()

                # Should set the gauge value
                mock_gauge.set.assert_called_once_with(0.85)


class TestMetricsExistence:
    """Test that all expected metrics are defined."""

    def test_retry_success_rate_metric_exists(self):
        """Test that RETRY_SUCCESS_RATE metric is defined."""
        from src.mge.v2.execution.metrics import RETRY_SUCCESS_RATE
        assert RETRY_SUCCESS_RATE is not None

    def test_retry_attempts_total_metric_exists(self):
        """Test that RETRY_ATTEMPTS_TOTAL metric is defined."""
        from src.mge.v2.execution.metrics import RETRY_ATTEMPTS_TOTAL
        assert RETRY_ATTEMPTS_TOTAL is not None

    def test_retry_temperature_changes_metric_exists(self):
        """Test that RETRY_TEMPERATURE_CHANGES metric is defined."""
        from src.mge.v2.execution.metrics import RETRY_TEMPERATURE_CHANGES
        assert RETRY_TEMPERATURE_CHANGES is not None

    def test_wave_completion_percent_metric_exists(self):
        """Test that WAVE_COMPLETION_PERCENT metric is defined."""
        from src.mge.v2.execution.metrics import WAVE_COMPLETION_PERCENT
        assert WAVE_COMPLETION_PERCENT is not None

    def test_wave_atom_throughput_metric_exists(self):
        """Test that WAVE_ATOM_THROUGHPUT metric is defined."""
        from src.mge.v2.execution.metrics import WAVE_ATOM_THROUGHPUT
        assert WAVE_ATOM_THROUGHPUT is not None

    def test_wave_time_seconds_metric_exists(self):
        """Test that WAVE_TIME_SECONDS metric is defined."""
        from src.mge.v2.execution.metrics import WAVE_TIME_SECONDS
        assert WAVE_TIME_SECONDS is not None

    def test_atoms_succeeded_total_metric_exists(self):
        """Test that ATOMS_SUCCEEDED_TOTAL metric is defined."""
        from src.mge.v2.execution.metrics import ATOMS_SUCCEEDED_TOTAL
        assert ATOMS_SUCCEEDED_TOTAL is not None

    def test_atoms_failed_total_metric_exists(self):
        """Test that ATOMS_FAILED_TOTAL metric is defined."""
        from src.mge.v2.execution.metrics import ATOMS_FAILED_TOTAL
        assert ATOMS_FAILED_TOTAL is not None

    def test_atom_execution_time_seconds_metric_exists(self):
        """Test that ATOM_EXECUTION_TIME_SECONDS metric is defined."""
        from src.mge.v2.execution.metrics import ATOM_EXECUTION_TIME_SECONDS
        assert ATOM_EXECUTION_TIME_SECONDS is not None

    def test_execution_precision_percent_metric_exists(self):
        """Test that EXECUTION_PRECISION_PERCENT metric is defined."""
        from src.mge.v2.execution.metrics import EXECUTION_PRECISION_PERCENT
        assert EXECUTION_PRECISION_PERCENT is not None

    def test_execution_time_seconds_metric_exists(self):
        """Test that EXECUTION_TIME_SECONDS metric is defined."""
        from src.mge.v2.execution.metrics import EXECUTION_TIME_SECONDS
        assert EXECUTION_TIME_SECONDS is not None

    def test_execution_cost_usd_total_metric_exists(self):
        """Test that EXECUTION_COST_USD_TOTAL metric is defined."""
        from src.mge.v2.execution.metrics import EXECUTION_COST_USD_TOTAL
        assert EXECUTION_COST_USD_TOTAL is not None
