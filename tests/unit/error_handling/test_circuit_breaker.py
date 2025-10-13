"""
Tests for CircuitBreaker pattern
"""

import pytest
import time
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from src.error_handling.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerState,
    CircuitBreakerConfig,
    CircuitBreakerError,
    with_circuit_breaker,
)


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CircuitBreakerConfig()

        assert config.failure_threshold == 5
        assert config.success_threshold == 2
        assert config.timeout == 60.0
        assert config.expected_exception == Exception
        assert config.on_open is None
        assert config.on_close is None

    def test_custom_config(self):
        """Test custom configuration."""
        on_open = Mock()
        on_close = Mock()
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=1,
            timeout=30.0,
            expected_exception=ValueError,
            on_open=on_open,
            on_close=on_close,
        )

        assert config.failure_threshold == 3
        assert config.success_threshold == 1
        assert config.timeout == 30.0
        assert config.expected_exception == ValueError
        assert config.on_open == on_open
        assert config.on_close == on_close


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    def test_initial_state(self):
        """Test circuit breaker starts in CLOSED state."""
        breaker = CircuitBreaker()

        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.success_count == 0

    def test_successful_call_in_closed_state(self):
        """Test successful calls pass through in CLOSED state."""
        breaker = CircuitBreaker()
        func = Mock(return_value="success")

        result = breaker.call(func, "arg1", kwarg="value")

        assert result == "success"
        func.assert_called_once_with("arg1", kwarg="value")
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_count == 0

    def test_failure_increments_count(self):
        """Test failures increment failure count."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker(config)
        func = Mock(side_effect=Exception("error"))

        # First failure
        with pytest.raises(Exception):
            breaker.call(func)
        assert breaker.failure_count == 1
        assert breaker.state == CircuitBreakerState.CLOSED

        # Second failure
        with pytest.raises(Exception):
            breaker.call(func)
        assert breaker.failure_count == 2
        assert breaker.state == CircuitBreakerState.CLOSED

    def test_opens_after_threshold_failures(self):
        """Test circuit opens after threshold failures."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker(config)
        func = Mock(side_effect=Exception("error"))

        # Cause failures to reach threshold
        for _ in range(3):
            with pytest.raises(Exception):
                breaker.call(func)

        assert breaker.state == CircuitBreakerState.OPEN
        assert breaker.failure_count == 3

    def test_rejects_calls_when_open(self):
        """Test circuit rejects calls when OPEN."""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker(config)
        func = Mock(side_effect=Exception("error"))

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                breaker.call(func)

        assert breaker.state == CircuitBreakerState.OPEN

        # New calls should fail immediately with CircuitBreakerError
        func.reset_mock()
        with pytest.raises(CircuitBreakerError):
            breaker.call(func)

        # Original function should NOT be called
        func.assert_not_called()

    def test_transitions_to_half_open_after_timeout(self):
        """Test circuit transitions to HALF_OPEN after timeout."""
        config = CircuitBreakerConfig(failure_threshold=2, timeout=0.1)
        breaker = CircuitBreaker(config)
        func = Mock(side_effect=Exception("error"))

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                breaker.call(func)

        assert breaker.state == CircuitBreakerState.OPEN

        # Wait for timeout
        time.sleep(0.15)

        # Check state (should transition to HALF_OPEN)
        assert breaker.state == CircuitBreakerState.HALF_OPEN

    def test_half_open_success_increments_count(self):
        """Test successful calls in HALF_OPEN increment success count."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=2,
            timeout=0.1,
        )
        breaker = CircuitBreaker(config)

        # Open circuit
        func = Mock(side_effect=Exception("error"))
        for _ in range(2):
            with pytest.raises(Exception):
                breaker.call(func)

        # Wait for timeout
        time.sleep(0.15)
        assert breaker.state == CircuitBreakerState.HALF_OPEN

        # Successful call should increment success count
        func = Mock(return_value="success")
        result = breaker.call(func)

        assert result == "success"
        assert breaker.success_count == 1
        assert breaker.state == CircuitBreakerState.HALF_OPEN

    def test_closes_after_success_threshold_in_half_open(self):
        """Test circuit closes after success threshold in HALF_OPEN."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=2,
            timeout=0.1,
        )
        breaker = CircuitBreaker(config)

        # Open circuit
        func = Mock(side_effect=Exception("error"))
        for _ in range(2):
            with pytest.raises(Exception):
                breaker.call(func)

        time.sleep(0.15)
        assert breaker.state == CircuitBreakerState.HALF_OPEN

        # Successful calls to close circuit
        func = Mock(return_value="success")
        breaker.call(func)
        assert breaker.state == CircuitBreakerState.HALF_OPEN

        breaker.call(func)
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_count == 0

    def test_reopens_on_failure_in_half_open(self):
        """Test circuit reopens immediately on failure in HALF_OPEN."""
        config = CircuitBreakerConfig(failure_threshold=2, timeout=0.1)
        breaker = CircuitBreaker(config)

        # Open circuit
        func = Mock(side_effect=Exception("error"))
        for _ in range(2):
            with pytest.raises(Exception):
                breaker.call(func)

        time.sleep(0.15)
        assert breaker.state == CircuitBreakerState.HALF_OPEN

        # Failure in HALF_OPEN should reopen circuit
        with pytest.raises(Exception):
            breaker.call(func)

        assert breaker.state == CircuitBreakerState.OPEN

    def test_on_open_callback(self):
        """Test on_open callback is called when circuit opens."""
        on_open = Mock()
        config = CircuitBreakerConfig(failure_threshold=2, on_open=on_open)
        breaker = CircuitBreaker(config)

        func = Mock(side_effect=Exception("error"))
        for _ in range(2):
            with pytest.raises(Exception):
                breaker.call(func)

        on_open.assert_called_once()

    def test_on_close_callback(self):
        """Test on_close callback is called when circuit closes."""
        on_close = Mock()
        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=1,
            timeout=0.1,
            on_close=on_close,
        )
        breaker = CircuitBreaker(config)

        # Open circuit
        func = Mock(side_effect=Exception("error"))
        for _ in range(2):
            with pytest.raises(Exception):
                breaker.call(func)

        time.sleep(0.15)

        # Close circuit
        func = Mock(return_value="success")
        breaker.call(func)

        on_close.assert_called_once()

    def test_reset_method(self):
        """Test reset() resets circuit to initial state."""
        breaker = CircuitBreaker()

        # Cause some failures
        func = Mock(side_effect=Exception("error"))
        with pytest.raises(Exception):
            breaker.call(func)

        assert breaker.failure_count > 0

        # Reset
        breaker.reset()

        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.success_count == 0

    def test_get_stats(self):
        """Test get_stats() returns current statistics."""
        breaker = CircuitBreaker()

        stats = breaker.get_stats()

        assert stats["state"] == "closed"
        assert stats["failure_count"] == 0
        assert stats["success_count"] == 0
        assert "config" in stats
        assert stats["config"]["failure_threshold"] == 5

    def test_success_resets_failure_count_in_closed(self):
        """Test success resets failure count in CLOSED state."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker(config)

        # Cause a failure
        func = Mock(side_effect=Exception("error"))
        with pytest.raises(Exception):
            breaker.call(func)

        assert breaker.failure_count == 1

        # Successful call should reset failure count
        func = Mock(return_value="success")
        breaker.call(func)

        assert breaker.failure_count == 0
        assert breaker.state == CircuitBreakerState.CLOSED

    def test_specific_exception_type(self):
        """Test circuit only opens on specific exception type."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            expected_exception=ValueError,
        )
        breaker = CircuitBreaker(config)

        # ValueError should count as failure
        func = Mock(side_effect=ValueError("value error"))
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(func)

        assert breaker.state == CircuitBreakerState.OPEN

        # Reset breaker
        breaker.reset()

        # TypeError should not count as failure (different exception type)
        func = Mock(side_effect=TypeError("type error"))
        with pytest.raises(TypeError):
            breaker.call(func)

        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_count == 0


class TestWithCircuitBreakerDecorator:
    """Tests for @with_circuit_breaker decorator."""

    def test_decorator_basic(self):
        """Test decorator with default config."""

        @with_circuit_breaker()
        def flaky_function():
            return "success"

        result = flaky_function()
        assert result == "success"

    def test_decorator_with_custom_config(self):
        """Test decorator with custom configuration."""
        config = CircuitBreakerConfig(failure_threshold=2)

        @with_circuit_breaker(config)
        def flaky_function():
            raise Exception("error")

        # Open circuit after failures
        for _ in range(2):
            with pytest.raises(Exception):
                flaky_function()

        # Should reject with CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            flaky_function()

    def test_decorator_exposes_circuit_breaker(self):
        """Test decorator exposes circuit breaker for inspection."""

        @with_circuit_breaker()
        def my_function():
            return "success"

        assert hasattr(my_function, "circuit_breaker")
        assert isinstance(my_function.circuit_breaker, CircuitBreaker)
        assert my_function.circuit_breaker.state == CircuitBreakerState.CLOSED


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker."""

    def test_protects_failing_api(self):
        """Test circuit breaker protects against failing API."""
        config = CircuitBreakerConfig(failure_threshold=3, timeout=0.1)
        breaker = CircuitBreaker(config)

        # Simulate failing API
        api_calls = []

        def failing_api():
            api_calls.append(1)
            raise ConnectionError("API down")

        # Make failures to open circuit
        for _ in range(3):
            with pytest.raises(ConnectionError):
                breaker.call(failing_api)

        assert len(api_calls) == 3
        assert breaker.state == CircuitBreakerState.OPEN

        # Additional calls should fail fast without hitting API
        with pytest.raises(CircuitBreakerError):
            breaker.call(failing_api)

        assert len(api_calls) == 3  # No additional API call

    def test_recovery_after_service_restored(self):
        """Test circuit recovers when service is restored."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=2,
            timeout=0.1,
        )
        breaker = CircuitBreaker(config)

        # Open circuit
        func = Mock(side_effect=Exception("error"))
        for _ in range(2):
            with pytest.raises(Exception):
                breaker.call(func)

        assert breaker.state == CircuitBreakerState.OPEN

        # Wait for timeout
        time.sleep(0.15)

        # Service restored
        func = Mock(return_value="restored")
        result1 = breaker.call(func)
        result2 = breaker.call(func)

        assert result1 == "restored"
        assert result2 == "restored"
        assert breaker.state == CircuitBreakerState.CLOSED
