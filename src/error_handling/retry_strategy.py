"""
Retry Strategy with Exponential Backoff

Implements configurable retry logic with exponential backoff and jitter
for resilient API calls and operation recovery.
"""

import time
import random
import logging
from typing import Callable, TypeVar, Optional, Type
from dataclasses import dataclass, field
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    """Maximum number of retry attempts"""

    initial_delay: float = 1.0
    """Initial delay in seconds before first retry"""

    max_delay: float = 60.0
    """Maximum delay in seconds between retries"""

    exponential_base: float = 2.0
    """Base for exponential backoff calculation"""

    jitter: bool = True
    """Whether to add random jitter to delays"""

    retryable_exceptions: tuple = (Exception,)
    """Tuple of exception types that should trigger retry"""

    on_retry: Optional[Callable[[Exception, int, float], None]] = None
    """Callback function called on each retry attempt"""


class RetryStrategy:
    """
    Retry strategy with exponential backoff and jitter.

    Provides resilient execution of operations that may fail transiently.
    Uses exponential backoff to avoid overwhelming failing services.

    Example:
        >>> config = RetryConfig(max_attempts=5, initial_delay=0.5)
        >>> strategy = RetryStrategy(config)
        >>> result = strategy.execute(api_call, arg1, arg2)
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Initialize retry strategy.

        Args:
            config: Retry configuration. Uses defaults if None.
        """
        self.config = config or RetryConfig()
        self._attempt_count = 0
        self._total_delay = 0.0

    def execute(
        self,
        func: Callable[..., T],
        *args,
        **kwargs,
    ) -> T:
        """
        Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of successful function execution

        Raises:
            Exception: Last exception if all retries exhausted
        """
        last_exception: Optional[Exception] = None
        self._attempt_count = 0
        self._total_delay = 0.0

        for attempt in range(1, self.config.max_attempts + 1):
            self._attempt_count = attempt

            try:
                logger.debug(f"Attempt {attempt}/{self.config.max_attempts}")
                result = func(*args, **kwargs)
                if attempt > 1:
                    logger.info(
                        f"Success on attempt {attempt} after "
                        f"{self._total_delay:.2f}s total delay"
                    )
                return result

            except self.config.retryable_exceptions as e:
                last_exception = e
                logger.warning(
                    f"Attempt {attempt} failed: {type(e).__name__}: {str(e)}"
                )

                # Don't sleep after last attempt
                if attempt < self.config.max_attempts:
                    delay = self._calculate_delay(attempt)
                    self._total_delay += delay

                    # Call retry callback if provided
                    if self.config.on_retry:
                        self.config.on_retry(e, attempt, delay)

                    logger.debug(f"Retrying in {delay:.2f}s...")
                    time.sleep(delay)

        # All retries exhausted
        logger.error(
            f"All {self.config.max_attempts} attempts failed. "
            f"Total delay: {self._total_delay:.2f}s"
        )
        raise last_exception

    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for next retry using exponential backoff.

        Args:
            attempt: Current attempt number (1-indexed)

        Returns:
            Delay in seconds
        """
        # Exponential backoff: initial_delay * base^(attempt-1)
        delay = self.config.initial_delay * (
            self.config.exponential_base ** (attempt - 1)
        )

        # Cap at max_delay
        delay = min(delay, self.config.max_delay)

        # Add jitter to avoid thundering herd
        if self.config.jitter:
            # Random jitter: ±25% of delay
            jitter = delay * 0.25 * (2 * random.random() - 1)
            delay += jitter
            delay = max(0, delay)  # Ensure non-negative

        return delay

    @property
    def attempts_made(self) -> int:
        """Get number of attempts made in last execution."""
        return self._attempt_count

    @property
    def total_delay(self) -> float:
        """Get total delay time in last execution."""
        return self._total_delay


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator to add retry logic to a function.

    Args:
        config: Retry configuration. Uses defaults if None.

    Returns:
        Decorated function with retry logic

    Example:
        >>> @with_retry(RetryConfig(max_attempts=5))
        ... def api_call():
        ...     return make_request()
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            strategy = RetryStrategy(config)
            return strategy.execute(func, *args, **kwargs)

        return wrapper

    return decorator
