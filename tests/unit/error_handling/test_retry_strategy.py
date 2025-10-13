"""
Tests for RetryStrategy with exponential backoff
"""

import pytest
import time
from unittest.mock import Mock, patch

from src.error_handling.retry_strategy import (
    RetryStrategy,
    RetryConfig,
    with_retry,
)


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert config.retryable_exceptions == (Exception,)
        assert config.on_retry is None

    def test_custom_config(self):
        """Test custom configuration."""
        callback = Mock()
        config = RetryConfig(
            max_attempts=5,
            initial_delay=0.5,
            max_delay=30.0,
            exponential_base=3.0,
            jitter=False,
            retryable_exceptions=(ValueError, TypeError),
            on_retry=callback,
        )

        assert config.max_attempts == 5
        assert config.initial_delay == 0.5
        assert config.max_delay == 30.0
        assert config.exponential_base == 3.0
        assert config.jitter is False
        assert config.retryable_exceptions == (ValueError, TypeError)
        assert config.on_retry == callback


class TestRetryStrategy:
    """Tests for RetryStrategy."""

    def test_immediate_success(self):
        """Test successful execution on first attempt."""
        config = RetryConfig(max_attempts=3)
        strategy = RetryStrategy(config)

        func = Mock(return_value="success")
        result = strategy.execute(func, "arg1", kwarg="value")

        assert result == "success"
        func.assert_called_once_with("arg1", kwarg="value")
        assert strategy.attempts_made == 1
        assert strategy.total_delay == 0.0

    def test_retry_success_on_second_attempt(self):
        """Test success after one retry."""
        config = RetryConfig(max_attempts=3, initial_delay=0.01, jitter=False)
        strategy = RetryStrategy(config)

        func = Mock(side_effect=[ValueError("error"), "success"])
        result = strategy.execute(func)

        assert result == "success"
        assert func.call_count == 2
        assert strategy.attempts_made == 2
        assert strategy.total_delay > 0

    def test_all_attempts_fail(self):
        """Test all attempts exhausted."""
        config = RetryConfig(max_attempts=3, initial_delay=0.01, jitter=False)
        strategy = RetryStrategy(config)

        func = Mock(side_effect=ValueError("persistent error"))

        with pytest.raises(ValueError, match="persistent error"):
            strategy.execute(func)

        assert func.call_count == 3
        assert strategy.attempts_made == 3

    def test_exponential_backoff(self):
        """Test exponential backoff delay calculation."""
        config = RetryConfig(
            max_attempts=4,
            initial_delay=0.1,
            exponential_base=2.0,
            jitter=False,
        )
        strategy = RetryStrategy(config)

        # Delays should be: 0.1, 0.2, 0.4
        expected_delays = [0.1, 0.2, 0.4]

        for attempt in range(1, 4):
            delay = strategy._calculate_delay(attempt)
            assert pytest.approx(delay, abs=0.001) == expected_delays[attempt - 1]

    def test_max_delay_cap(self):
        """Test delay is capped at max_delay."""
        config = RetryConfig(
            initial_delay=1.0,
            max_delay=5.0,
            exponential_base=2.0,
            jitter=False,
        )
        strategy = RetryStrategy(config)

        # With base 2, attempt 10 would be 2^9 = 512 seconds
        # Should be capped at 5.0
        delay = strategy._calculate_delay(10)
        assert delay == 5.0

    def test_jitter_adds_randomness(self):
        """Test jitter adds randomness to delays."""
        config = RetryConfig(initial_delay=1.0, jitter=True)
        strategy = RetryStrategy(config)

        # Run multiple times to check variation
        delays = [strategy._calculate_delay(1) for _ in range(10)]

        # Not all delays should be exactly the same
        assert len(set(delays)) > 1
        # All delays should be roughly around initial_delay
        assert all(0.75 <= d <= 1.25 for d in delays)

    def test_on_retry_callback(self):
        """Test on_retry callback is called."""
        callback = Mock()
        config = RetryConfig(
            max_attempts=3,
            initial_delay=0.01,
            jitter=False,
            on_retry=callback,
        )
        strategy = RetryStrategy(config)

        func = Mock(side_effect=[ValueError("error1"), "success"])
        strategy.execute(func)

        # Callback should be called once (after first failure)
        callback.assert_called_once()
        args = callback.call_args[0]
        assert isinstance(args[0], ValueError)
        assert args[1] == 1  # attempt number
        assert isinstance(args[2], float)  # delay

    def test_specific_exception_types(self):
        """Test retry only on specific exception types."""
        config = RetryConfig(
            max_attempts=3,
            retryable_exceptions=(ValueError,),
            initial_delay=0.01,
        )
        strategy = RetryStrategy(config)

        # ValueError should be retried
        func = Mock(side_effect=[ValueError(), "success"])
        result = strategy.execute(func)
        assert result == "success"
        assert func.call_count == 2

        # TypeError should not be retried
        func = Mock(side_effect=TypeError("type error"))
        with pytest.raises(TypeError):
            strategy.execute(func)
        assert func.call_count == 1  # No retry

    def test_retry_with_args_and_kwargs(self):
        """Test retry preserves function arguments."""
        config = RetryConfig(max_attempts=2, initial_delay=0.01)
        strategy = RetryStrategy(config)

        func = Mock(side_effect=[ValueError(), "success"])
        result = strategy.execute(func, "arg1", "arg2", key1="val1", key2="val2")

        assert result == "success"
        # Both calls should have same arguments
        for call in func.call_args_list:
            assert call[0] == ("arg1", "arg2")
            assert call[1] == {"key1": "val1", "key2": "val2"}


class TestWithRetryDecorator:
    """Tests for @with_retry decorator."""

    def test_decorator_basic(self):
        """Test decorator with default config."""

        @with_retry()
        def flaky_function():
            if not hasattr(flaky_function, "call_count"):
                flaky_function.call_count = 0
            flaky_function.call_count += 1
            if flaky_function.call_count < 2:
                raise ValueError("error")
            return "success"

        result = flaky_function()
        assert result == "success"
        assert flaky_function.call_count == 2

    def test_decorator_with_custom_config(self):
        """Test decorator with custom configuration."""
        config = RetryConfig(max_attempts=5, initial_delay=0.01)

        @with_retry(config)
        def flaky_function():
            raise ValueError("always fails")

        with pytest.raises(ValueError):
            flaky_function()

    def test_decorator_preserves_function_metadata(self):
        """Test decorator preserves function name and docstring."""

        @with_retry()
        def my_function():
            """This is my function."""
            return "result"

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "This is my function."


class TestRetryIntegration:
    """Integration tests for retry strategy."""

    @patch("time.sleep")  # Mock sleep to speed up tests
    def test_real_world_api_retry(self, mock_sleep):
        """Test realistic API retry scenario."""
        config = RetryConfig(
            max_attempts=3,
            initial_delay=1.0,
            exponential_base=2.0,
            jitter=False,
        )
        strategy = RetryStrategy(config)

        # Simulate API that fails twice then succeeds
        api_mock = Mock(
            side_effect=[
                ConnectionError("network error"),
                TimeoutError("timeout"),
                {"status": "success"},
            ]
        )

        result = strategy.execute(api_mock)

        assert result == {"status": "success"}
        assert api_mock.call_count == 3
        assert mock_sleep.call_count == 2  # Sleep called between retries

    def test_no_retry_on_success(self):
        """Test no delay or retry when function succeeds immediately."""
        config = RetryConfig(max_attempts=3)
        strategy = RetryStrategy(config)

        start = time.time()
        func = Mock(return_value="immediate success")
        result = strategy.execute(func)
        elapsed = time.time() - start

        assert result == "immediate success"
        assert elapsed < 0.1  # Should be very fast
        assert strategy.attempts_made == 1
        assert strategy.total_delay == 0.0
