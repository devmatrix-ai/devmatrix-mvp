"""
MGE V2 Execution Module

Wave-based parallel execution with intelligent retry orchestration.
"""

from .retry_orchestrator import RetryOrchestrator, RetryResult
from .wave_executor import WaveExecutor, ExecutionResult, WaveResult
from .metrics import (
    RETRY_ATTEMPTS_TOTAL,
    RETRY_SUCCESS_RATE,
    RETRY_TEMPERATURE_CHANGES,
    WAVE_COMPLETION_PERCENT,
    WAVE_ATOM_THROUGHPUT,
    WAVE_TIME_SECONDS,
    EXECUTION_PRECISION_PERCENT,
    EXECUTION_TIME_SECONDS,
    EXECUTION_COST_USD_TOTAL,
    ATOMS_SUCCEEDED_TOTAL,
    ATOMS_FAILED_TOTAL,
    ATOM_EXECUTION_TIME_SECONDS,
    ATOM_VALIDATION_PASS_RATE,
)

__all__ = [
    "RetryOrchestrator",
    "RetryResult",
    "WaveExecutor",
    "ExecutionResult",
    "WaveResult",
    "RETRY_ATTEMPTS_TOTAL",
    "RETRY_SUCCESS_RATE",
    "RETRY_TEMPERATURE_CHANGES",
    "WAVE_COMPLETION_PERCENT",
    "WAVE_ATOM_THROUGHPUT",
    "WAVE_TIME_SECONDS",
    "EXECUTION_PRECISION_PERCENT",
    "EXECUTION_TIME_SECONDS",
    "EXECUTION_COST_USD_TOTAL",
    "ATOMS_SUCCEEDED_TOTAL",
    "ATOMS_FAILED_TOTAL",
    "ATOM_EXECUTION_TIME_SECONDS",
    "ATOM_VALIDATION_PASS_RATE",
]
