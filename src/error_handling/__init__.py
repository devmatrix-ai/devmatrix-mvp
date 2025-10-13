"""
Error Handling & Recovery Module

Provides advanced error recovery strategies including:
- Retry strategies with exponential backoff
- Circuit breaker pattern for API protection
- Graceful degradation strategies
- Checkpoint/restore mechanisms
"""

from .retry_strategy import RetryStrategy, RetryConfig
from .circuit_breaker import CircuitBreaker, CircuitBreakerState, CircuitBreakerConfig
from .error_recovery import ErrorRecovery, RecoveryStrategy, RecoveryConfig
from .checkpoint import CheckpointManager, WorkflowCheckpoint

__all__ = [
    "RetryStrategy",
    "RetryConfig",
    "CircuitBreaker",
    "CircuitBreakerState",
    "CircuitBreakerConfig",
    "ErrorRecovery",
    "RecoveryStrategy",
    "RecoveryConfig",
    "CheckpointManager",
    "WorkflowCheckpoint",
]
