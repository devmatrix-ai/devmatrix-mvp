"""
Error Recovery Strategies

Implements graceful degradation and error recovery patterns
for resilient system operation.
"""

import logging
from enum import Enum
from typing import Callable, TypeVar, Optional, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RecoveryStrategy(Enum):
    """Error recovery strategy types."""

    RETRY = "retry"  # Retry with backoff
    FALLBACK = "fallback"  # Use fallback value/function
    SKIP = "skip"  # Skip operation and continue
    FAIL = "fail"  # Fail fast and propagate error
    DEGRADE = "degrade"  # Graceful degradation


@dataclass
class RecoveryConfig:
    """Configuration for error recovery behavior."""

    strategy: RecoveryStrategy = RecoveryStrategy.RETRY
    """Primary recovery strategy"""

    fallback_strategies: List[RecoveryStrategy] = field(default_factory=list)
    """Additional strategies to try if primary fails"""

    fallback_value: Optional[Any] = None
    """Default value to return on failure"""

    fallback_function: Optional[Callable] = None
    """Fallback function to call on failure"""

    skip_on_error: bool = False
    """Whether to skip and return None on unrecoverable error"""

    log_errors: bool = True
    """Whether to log errors"""

    raise_on_final_failure: bool = True
    """Whether to raise exception after all strategies exhausted"""


class ErrorRecovery:
    """
    Error recovery manager with graceful degradation.

    Implements multiple recovery strategies for resilient operation:
    - Retry with exponential backoff
    - Fallback to default values or alternative functions
    - Graceful degradation
    - Skip and continue

    Example:
        >>> recovery = ErrorRecovery(
        ...     RecoveryConfig(
        ...         strategy=RecoveryStrategy.FALLBACK,
        ...         fallback_value="default"
        ...     )
        ... )
        >>> result = recovery.execute(risky_operation, arg1, arg2)
    """

    def __init__(self, config: Optional[RecoveryConfig] = None):
        """
        Initialize error recovery manager.

        Args:
            config: Recovery configuration
        """
        self.config = config or RecoveryConfig()
        self._recovery_attempts = 0
        self._last_error: Optional[Exception] = None

    def execute(
        self,
        func: Callable[..., T],
        *args,
        **kwargs,
    ) -> Optional[T]:
        """
        Execute function with error recovery.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result or fallback value

        Raises:
            Exception: If all recovery strategies fail and raise_on_final_failure=True
        """
        self._recovery_attempts = 0
        self._last_error = None

        # Try primary strategy
        strategies = [self.config.strategy] + self.config.fallback_strategies

        for strategy in strategies:
            self._recovery_attempts += 1

            try:
                return self._execute_with_strategy(
                    strategy, func, *args, **kwargs
                )

            except Exception as e:
                self._last_error = e
                if self.config.log_errors:
                    logger.warning(
                        f"Strategy {strategy.value} failed: "
                        f"{type(e).__name__}: {str(e)}"
                    )
                continue

        # All strategies exhausted
        if self.config.log_errors:
            logger.error(
                f"All {self._recovery_attempts} recovery strategies failed"
            )

        if self.config.skip_on_error:
            logger.info("Skipping operation due to skip_on_error=True")
            return None

        if self.config.raise_on_final_failure:
            raise self._last_error
        else:
            return self.config.fallback_value

    def _execute_with_strategy(
        self,
        strategy: RecoveryStrategy,
        func: Callable[..., T],
        *args,
        **kwargs,
    ) -> T:
        """
        Execute function using specific recovery strategy.

        Args:
            strategy: Recovery strategy to use
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If strategy fails
        """
        if strategy == RecoveryStrategy.RETRY:
            # Direct execution (retry handled by RetryStrategy externally)
            return func(*args, **kwargs)

        elif strategy == RecoveryStrategy.FALLBACK:
            try:
                return func(*args, **kwargs)
            except Exception:
                if self.config.fallback_function:
                    logger.info("Using fallback function")
                    return self.config.fallback_function(*args, **kwargs)
                elif self.config.fallback_value is not None:
                    logger.info("Using fallback value")
                    return self.config.fallback_value
                else:
                    raise

        elif strategy == RecoveryStrategy.SKIP:
            try:
                return func(*args, **kwargs)
            except Exception:
                logger.info("Skipping operation")
                return None

        elif strategy == RecoveryStrategy.DEGRADE:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Degraded execution: {type(e).__name__}")
                # Return degraded result (simplified version)
                if self.config.fallback_value is not None:
                    return self.config.fallback_value
                raise

        elif strategy == RecoveryStrategy.FAIL:
            # Fail fast, no recovery
            return func(*args, **kwargs)

        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    @property
    def attempts_made(self) -> int:
        """Get number of recovery attempts made."""
        return self._recovery_attempts

    @property
    def last_error(self) -> Optional[Exception]:
        """Get last error encountered."""
        return self._last_error


class ErrorRecoveryBuilder:
    """
    Builder for creating ErrorRecovery with fluent interface.

    Example:
        >>> recovery = (ErrorRecoveryBuilder()
        ...     .with_strategy(RecoveryStrategy.FALLBACK)
        ...     .with_fallback_value("default")
        ...     .skip_on_error()
        ...     .build())
    """

    def __init__(self):
        """Initialize builder with default config."""
        self._config = RecoveryConfig()

    def with_strategy(self, strategy: RecoveryStrategy) -> "ErrorRecoveryBuilder":
        """Set primary recovery strategy."""
        self._config.strategy = strategy
        return self

    def add_fallback_strategy(
        self, strategy: RecoveryStrategy
    ) -> "ErrorRecoveryBuilder":
        """Add fallback strategy."""
        self._config.fallback_strategies.append(strategy)
        return self

    def with_fallback_value(self, value: Any) -> "ErrorRecoveryBuilder":
        """Set fallback value."""
        self._config.fallback_value = value
        return self

    def with_fallback_function(
        self, func: Callable
    ) -> "ErrorRecoveryBuilder":
        """Set fallback function."""
        self._config.fallback_function = func
        return self

    def skip_on_error(self, skip: bool = True) -> "ErrorRecoveryBuilder":
        """Enable/disable skip on error."""
        self._config.skip_on_error = skip
        return self

    def log_errors(self, log: bool = True) -> "ErrorRecoveryBuilder":
        """Enable/disable error logging."""
        self._config.log_errors = log
        return self

    def raise_on_failure(self, raise_: bool = True) -> "ErrorRecoveryBuilder":
        """Enable/disable raising exception on final failure."""
        self._config.raise_on_final_failure = raise_
        return self

    def build(self) -> ErrorRecovery:
        """Build ErrorRecovery instance."""
        return ErrorRecovery(self._config)


def with_recovery(config: Optional[RecoveryConfig] = None):
    """
    Decorator to add error recovery to a function.

    Args:
        config: Recovery configuration

    Returns:
        Decorated function with error recovery

    Example:
        >>> @with_recovery(RecoveryConfig(strategy=RecoveryStrategy.FALLBACK))
        ... def api_call():
        ...     return make_request()
    """

    def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
        def wrapper(*args, **kwargs) -> Optional[T]:
            recovery = ErrorRecovery(config)
            return recovery.execute(func, *args, **kwargs)

        return wrapper

    return decorator
