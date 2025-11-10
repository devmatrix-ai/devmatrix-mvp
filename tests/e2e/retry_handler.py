"""
Retry Handler for E2E Test Resilience

Implements exponential backoff and retry logic for transient failures.
"""
import time
import logging
from typing import Any, Callable, Optional, Type, Tuple
from functools import wraps


logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        """Initialize retry configuration.

        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds before first retry
            max_delay: Maximum delay between retries
            exponential_base: Base for exponential backoff calculation
            jitter: Add random jitter to avoid thundering herd
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


class RetryableError(Exception):
    """Base class for errors that should trigger retries."""
    pass


class ConnectionError(RetryableError):
    """Network/connection errors."""
    pass


class TimeoutError(RetryableError):
    """Timeout errors."""
    pass


class RateLimitError(RetryableError):
    """Rate limit errors."""
    pass


class TransientAPIError(RetryableError):
    """Transient API errors (5xx status codes)."""
    pass


# Mapping of exception types to retryable errors
RETRYABLE_EXCEPTIONS = {
    # Standard library
    ConnectionResetError: ConnectionError,
    ConnectionAbortedError: ConnectionError,
    ConnectionRefusedError: ConnectionError,
    TimeoutError: TimeoutError,
    # HTTP errors (would need to check status code)
    # These would be caught and re-raised as appropriate retryable errors
}


def calculate_backoff_delay(
    attempt: int,
    config: RetryConfig
) -> float:
    """Calculate delay before next retry attempt.

    Args:
        attempt: Current retry attempt number (0-indexed)
        config: Retry configuration

    Returns:
        Delay in seconds
    """
    import random

    # Exponential backoff: initial_delay * (base ^ attempt)
    delay = config.initial_delay * (config.exponential_base ** attempt)

    # Cap at max_delay
    delay = min(delay, config.max_delay)

    # Add jitter to avoid thundering herd
    if config.jitter:
        jitter_range = delay * 0.1  # ±10% jitter
        delay += random.uniform(-jitter_range, jitter_range)

    return max(0, delay)


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None
):
    """Decorator for automatic retry with exponential backoff.

    Args:
        config: Retry configuration (uses defaults if None)
        retryable_exceptions: Tuple of exception types to retry on

    Returns:
        Decorated function with retry logic
    """
    if config is None:
        config = RetryConfig()

    if retryable_exceptions is None:
        retryable_exceptions = tuple(RETRYABLE_EXCEPTIONS.keys())

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    # Attempt execution
                    result = func(*args, **kwargs)
                    return result

                except retryable_exceptions as e:
                    last_exception = e

                    # Check if we should retry
                    if attempt < config.max_retries:
                        delay = calculate_backoff_delay(attempt, config)

                        logger.warning(
                            f"⚠️ {func.__name__} failed (attempt {attempt + 1}/{config.max_retries + 1}): {e}"
                        )
                        logger.info(f"⏳ Retrying in {delay:.1f}s...")

                        time.sleep(delay)
                    else:
                        # Max retries exceeded
                        logger.error(
                            f"❌ {func.__name__} failed after {config.max_retries + 1} attempts"
                        )
                        raise

                except Exception as e:
                    # Non-retryable exception
                    logger.error(f"❌ {func.__name__} failed with non-retryable error: {e}")
                    raise

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


class PhaseRetryHandler:
    """Handles retries for individual pipeline phases."""

    def __init__(self, config: Optional[RetryConfig] = None):
        """Initialize phase retry handler.

        Args:
            config: Retry configuration
        """
        self.config = config or RetryConfig(
            max_retries=3,
            initial_delay=5.0,
            max_delay=120.0,
            exponential_base=2.0,
            jitter=True
        )

    def execute_with_retry(
        self,
        phase_name: str,
        phase_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute phase with automatic retry on transient failures.

        Args:
            phase_name: Name of the phase for logging
            phase_func: Phase function to execute
            *args: Positional arguments for phase_func
            **kwargs: Keyword arguments for phase_func

        Returns:
            Result from phase_func

        Raises:
            Exception: If all retries exhausted or non-retryable error
        """
        last_exception = None
        retryable_exceptions = (
            ConnectionResetError,
            ConnectionAbortedError,
            ConnectionRefusedError,
            BrokenPipeError,
            OSError,  # Catch general OS errors
        )

        for attempt in range(self.config.max_retries + 1):
            try:
                logger.info(f"🔄 Executing phase: {phase_name} (attempt {attempt + 1})")

                # Execute phase
                result = phase_func(*args, **kwargs)

                # Success
                if attempt > 0:
                    logger.info(f"✅ Phase {phase_name} succeeded after {attempt + 1} attempts")
                else:
                    logger.info(f"✅ Phase {phase_name} completed successfully")

                return result

            except retryable_exceptions as e:
                last_exception = e
                error_msg = str(e)

                # Check if we should retry
                if attempt < self.config.max_retries:
                    delay = calculate_backoff_delay(attempt, self.config)

                    logger.warning(
                        f"⚠️ Phase {phase_name} failed (attempt {attempt + 1}/{self.config.max_retries + 1})"
                    )
                    logger.warning(f"   Error: {error_msg}")
                    logger.info(f"⏳ Retrying in {delay:.1f}s with exponential backoff...")

                    time.sleep(delay)
                else:
                    # Max retries exceeded
                    logger.error(
                        f"❌ Phase {phase_name} failed after {self.config.max_retries + 1} attempts"
                    )
                    logger.error(f"   Final error: {error_msg}")
                    raise

            except Exception as e:
                # Non-retryable exception
                logger.error(f"❌ Phase {phase_name} failed with non-retryable error: {e}")
                raise

        # Should never reach here
        if last_exception:
            raise last_exception


# Convenience function for phase execution with retry
def execute_phase_with_retry(
    phase_name: str,
    phase_func: Callable,
    retry_config: Optional[RetryConfig] = None,
    *args,
    **kwargs
) -> Any:
    """Execute a pipeline phase with automatic retry.

    Args:
        phase_name: Name of the phase
        phase_func: Function to execute
        retry_config: Optional retry configuration
        *args: Positional arguments for phase_func
        **kwargs: Keyword arguments for phase_func

    Returns:
        Result from phase_func
    """
    handler = PhaseRetryHandler(config=retry_config)
    return handler.execute_with_retry(phase_name, phase_func, *args, **kwargs)


# Convenience decorator for phase functions
def phase_with_retry(
    phase_name: str,
    config: Optional[RetryConfig] = None
):
    """Decorator to add retry logic to phase functions.

    Args:
        phase_name: Name of the phase for logging
        config: Optional retry configuration

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            return execute_phase_with_retry(
                phase_name,
                func,
                config,
                *args,
                **kwargs
            )
        return wrapper
    return decorator
