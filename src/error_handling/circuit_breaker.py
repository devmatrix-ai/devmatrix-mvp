"""
Circuit Breaker Pattern

Implements circuit breaker pattern to prevent cascading failures
and protect systems from repeated failed operations.
"""

import time
import logging
from enum import Enum
from typing import Callable, TypeVar, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitBreakerState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Failure threshold exceeded, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5
    """Number of failures before opening circuit"""

    success_threshold: int = 2
    """Number of successes in half-open to close circuit"""

    timeout: float = 60.0
    """Seconds to wait before attempting half-open from open"""

    expected_exception: type = Exception
    """Exception type that counts as failure"""

    on_open: Optional[Callable[[], None]] = None
    """Callback when circuit opens"""

    on_close: Optional[Callable[[], None]] = None
    """Callback when circuit closes"""


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""

    pass


class CircuitBreaker:
    """
    Circuit breaker implementation for fault tolerance.

    Prevents cascading failures by stopping requests to failing services
    and allowing time for recovery.

    States:
        - CLOSED: Normal operation, all requests pass through
        - OPEN: Too many failures, requests fail immediately
        - HALF_OPEN: Testing recovery, limited requests allowed

    Example:
        >>> breaker = CircuitBreaker()
        >>> result = breaker.call(api_function, arg1, arg2)
    """

    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        """
        Initialize circuit breaker.

        Args:
            config: Circuit breaker configuration
        """
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._opened_at: Optional[datetime] = None

    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        self._update_state()
        return self._state

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count

    @property
    def success_count(self) -> int:
        """Get current success count (in half-open state)."""
        return self._success_count

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function through circuit breaker.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result of function execution

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Original exception from function
        """
        self._update_state()

        if self._state == CircuitBreakerState.OPEN:
            logger.warning("Circuit breaker is OPEN, rejecting request")
            raise CircuitBreakerError(
                f"Circuit breaker is OPEN. Opened at: {self._opened_at}. "
                f"Retry after {self.config.timeout}s"
            )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except self.config.expected_exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Handle successful execution."""
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._success_count += 1
            logger.debug(
                f"Success in HALF_OPEN: {self._success_count}/"
                f"{self.config.success_threshold}"
            )

            if self._success_count >= self.config.success_threshold:
                self._close_circuit()
        else:
            # Reset failure count on success in CLOSED state
            self._failure_count = 0

    def _on_failure(self):
        """Handle failed execution."""
        self._failure_count += 1
        self._last_failure_time = datetime.now()

        if self._state == CircuitBreakerState.HALF_OPEN:
            # Failure in half-open immediately reopens circuit
            logger.warning("Failure in HALF_OPEN, reopening circuit")
            self._open_circuit()

        elif self._failure_count >= self.config.failure_threshold:
            logger.warning(
                f"Failure threshold reached ({self._failure_count}/"
                f"{self.config.failure_threshold}), opening circuit"
            )
            self._open_circuit()
        else:
            logger.debug(
                f"Failure count: {self._failure_count}/"
                f"{self.config.failure_threshold}"
            )

    def _open_circuit(self):
        """Open the circuit (failures exceed threshold)."""
        self._state = CircuitBreakerState.OPEN
        self._opened_at = datetime.now()
        self._success_count = 0

        logger.error(
            f"Circuit breaker OPENED. Timeout: {self.config.timeout}s"
        )

        if self.config.on_open:
            self.config.on_open()

    def _close_circuit(self):
        """Close the circuit (service recovered)."""
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._opened_at = None

        logger.info("Circuit breaker CLOSED, service recovered")

        if self.config.on_close:
            self.config.on_close()

    def _update_state(self):
        """Update state based on timeout (OPEN → HALF_OPEN)."""
        if self._state == CircuitBreakerState.OPEN:
            if self._opened_at:
                elapsed = (datetime.now() - self._opened_at).total_seconds()
                if elapsed >= self.config.timeout:
                    logger.info(
                        f"Timeout elapsed ({elapsed:.1f}s), "
                        "transitioning to HALF_OPEN"
                    )
                    self._state = CircuitBreakerState.HALF_OPEN
                    self._success_count = 0

    def reset(self):
        """Reset circuit breaker to initial state."""
        logger.info("Resetting circuit breaker")
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._opened_at = None

    def get_stats(self) -> dict:
        """
        Get circuit breaker statistics.

        Returns:
            Dictionary with current stats
        """
        return {
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure": (
                self._last_failure_time.isoformat()
                if self._last_failure_time
                else None
            ),
            "opened_at": (
                self._opened_at.isoformat() if self._opened_at else None
            ),
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout,
            },
        }


def with_circuit_breaker(config: Optional[CircuitBreakerConfig] = None):
    """
    Decorator to add circuit breaker protection to a function.

    Args:
        config: Circuit breaker configuration

    Returns:
        Decorated function with circuit breaker

    Example:
        >>> breaker_config = CircuitBreakerConfig(failure_threshold=3)
        >>> @with_circuit_breaker(breaker_config)
        ... def api_call():
        ...     return make_request()
    """
    breaker = CircuitBreaker(config)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return breaker.call(func, *args, **kwargs)

        # Attach breaker to function for external access
        wrapper.circuit_breaker = breaker
        return wrapper

    return decorator
