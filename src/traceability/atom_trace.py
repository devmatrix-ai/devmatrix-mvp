"""
Atom Traceability System

End-to-end tracing for atomic units through the complete MGE V2 pipeline.
Tracks context, validation, acceptance tests, retries, cost, and timing.
"""

import time
from typing import Dict, List, Optional, Any
from uuid import UUID
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationTrace:
    """Validation results across L1-L4 layers."""
    l1_syntax: Optional[Dict[str, Any]] = None
    l2_imports: Optional[Dict[str, Any]] = None
    l3_types: Optional[Dict[str, Any]] = None
    l4_complexity: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "l1_syntax": self.l1_syntax,
            "l2_imports": self.l2_imports,
            "l3_types": self.l3_types,
            "l4_complexity": self.l4_complexity
        }


@dataclass
class AcceptanceTrace:
    """Acceptance test execution trace."""
    tests_executed: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    failed_test_ids: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tests_executed": self.tests_executed,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "failed_test_ids": self.failed_test_ids,
            "execution_time_ms": self.execution_time_ms
        }


@dataclass
class RetryTrace:
    """Retry attempts trace."""
    total_attempts: int = 0
    successful_attempt: Optional[int] = None
    failed_attempts: List[Dict[str, Any]] = field(default_factory=list)
    total_retry_time_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_attempts": self.total_attempts,
            "successful_attempt": self.successful_attempt,
            "failed_attempts": self.failed_attempts,
            "total_retry_time_seconds": self.total_retry_time_seconds
        }


@dataclass
class CostTrace:
    """Cost and resource usage trace."""
    total_cost_usd: float = 0.0
    llm_tokens_input: int = 0
    llm_tokens_output: int = 0
    llm_calls: int = 0
    rag_retrievals: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_cost_usd": self.total_cost_usd,
            "llm_tokens_input": self.llm_tokens_input,
            "llm_tokens_output": self.llm_tokens_output,
            "llm_calls": self.llm_calls,
            "rag_retrievals": self.rag_retrievals,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses
        }


@dataclass
class TimingTrace:
    """Timing breakdown across pipeline stages."""
    code_generation_seconds: float = 0.0
    validation_seconds: float = 0.0
    acceptance_testing_seconds: float = 0.0
    retry_seconds: float = 0.0
    total_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "code_generation_seconds": self.code_generation_seconds,
            "validation_seconds": self.validation_seconds,
            "acceptance_testing_seconds": self.acceptance_testing_seconds,
            "retry_seconds": self.retry_seconds,
            "total_seconds": self.total_seconds
        }


@dataclass
class ContextTrace:
    """Context used for atom generation."""
    context_size_bytes: int = 0
    context_sources: List[str] = field(default_factory=list)
    rag_chunks_used: int = 0
    rag_relevance_scores: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "context_size_bytes": self.context_size_bytes,
            "context_sources": self.context_sources,
            "rag_chunks_used": self.rag_chunks_used,
            "rag_relevance_scores": self.rag_relevance_scores
        }


class AtomTrace:
    """
    Complete end-to-end trace for an atomic unit.

    Tracks full lifecycle:
    1. Context gathering (RAG, dependencies)
    2. Code generation
    3. L1-L4 validation
    4. Acceptance testing
    5. Retry attempts (if needed)
    6. Cost and timing
    """

    def __init__(
        self,
        atom_id: UUID,
        masterplan_id: UUID,
        atom_number: int,
        description: str
    ):
        """
        Initialize atom trace.

        Args:
            atom_id: Atom UUID
            masterplan_id: Parent masterplan UUID
            atom_number: Atom sequence number
            description: Atom description
        """
        self.atom_id = atom_id
        self.masterplan_id = masterplan_id
        self.atom_number = atom_number
        self.description = description

        # Trace components
        self.context = ContextTrace()
        self.validation = ValidationTrace()
        self.acceptance = AcceptanceTrace()
        self.retry = RetryTrace()
        self.cost = CostTrace()
        self.timing = TimingTrace()

        # Lifecycle timestamps
        self.created_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None

        # Status
        self.status = "pending"  # pending, in_progress, completed, failed

        # Internal timing
        self._start_time: Optional[float] = None

    def start(self):
        """Start trace timing."""
        self._start_time = time.time()
        self.status = "in_progress"
        logger.info(
            f"Atom trace started: {self.atom_id}",
            extra={"atom_id": str(self.atom_id), "atom_number": self.atom_number}
        )

    def complete(self, success: bool = True):
        """
        Mark trace as complete.

        Args:
            success: Whether atom completed successfully
        """
        if self._start_time:
            self.timing.total_seconds = time.time() - self._start_time

        self.completed_at = datetime.utcnow()
        self.status = "completed" if success else "failed"

        logger.info(
            f"Atom trace completed: {self.atom_id} (status={self.status})",
            extra={
                "atom_id": str(self.atom_id),
                "status": self.status,
                "total_seconds": self.timing.total_seconds
            }
        )

    def record_context(
        self,
        context_size: int,
        sources: List[str],
        rag_chunks: int = 0,
        rag_scores: List[float] = None
    ):
        """
        Record context gathering details.

        Args:
            context_size: Size of context in bytes
            sources: List of context sources
            rag_chunks: Number of RAG chunks used
            rag_scores: Relevance scores for RAG chunks
        """
        self.context.context_size_bytes = context_size
        self.context.context_sources = sources
        self.context.rag_chunks_used = rag_chunks
        self.context.rag_relevance_scores = rag_scores or []

    def record_validation(
        self,
        l1: Optional[Dict] = None,
        l2: Optional[Dict] = None,
        l3: Optional[Dict] = None,
        l4: Optional[Dict] = None,
        validation_time: float = 0.0
    ):
        """
        Record validation results.

        Args:
            l1: L1 syntax validation results
            l2: L2 import validation results
            l3: L3 type validation results
            l4: L4 complexity validation results
            validation_time: Time spent in validation (seconds)
        """
        self.validation.l1_syntax = l1
        self.validation.l2_imports = l2
        self.validation.l3_types = l3
        self.validation.l4_complexity = l4
        self.timing.validation_seconds = validation_time

    def record_acceptance_tests(
        self,
        executed: int,
        passed: int,
        failed: int,
        failed_ids: List[str],
        execution_time: float
    ):
        """
        Record acceptance test execution.

        Args:
            executed: Number of tests executed
            passed: Number of tests passed
            failed: Number of tests failed
            failed_ids: IDs of failed tests
            execution_time: Execution time in milliseconds
        """
        self.acceptance.tests_executed = executed
        self.acceptance.tests_passed = passed
        self.acceptance.tests_failed = failed
        self.acceptance.failed_test_ids = failed_ids
        self.acceptance.execution_time_ms = execution_time
        self.timing.acceptance_testing_seconds = execution_time / 1000.0

    def record_retry(
        self,
        attempt_number: int,
        success: bool,
        error: Optional[str] = None,
        retry_time: float = 0.0
    ):
        """
        Record retry attempt.

        Args:
            attempt_number: Attempt number (1-based)
            success: Whether retry succeeded
            error: Error message if failed
            retry_time: Time spent in this retry (seconds)
        """
        self.retry.total_attempts += 1
        self.timing.retry_seconds += retry_time

        if success:
            self.retry.successful_attempt = attempt_number
        else:
            self.retry.failed_attempts.append({
                "attempt": attempt_number,
                "error": error,
                "time_seconds": retry_time
            })

    def record_cost(
        self,
        llm_cost: float = 0.0,
        tokens_in: int = 0,
        tokens_out: int = 0,
        llm_calls: int = 0,
        rag_retrievals: int = 0,
        cache_hits: int = 0,
        cache_misses: int = 0
    ):
        """
        Record cost and resource usage.

        Args:
            llm_cost: LLM cost in USD
            tokens_in: Input tokens
            tokens_out: Output tokens
            llm_calls: Number of LLM calls
            rag_retrievals: Number of RAG retrievals
            cache_hits: Cache hit count
            cache_misses: Cache miss count
        """
        self.cost.total_cost_usd += llm_cost
        self.cost.llm_tokens_input += tokens_in
        self.cost.llm_tokens_output += tokens_out
        self.cost.llm_calls += llm_calls
        self.cost.rag_retrievals += rag_retrievals
        self.cost.cache_hits += cache_hits
        self.cost.cache_misses += cache_misses

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert trace to dictionary for serialization.

        Returns:
            Complete trace as dictionary
        """
        return {
            "atom_id": str(self.atom_id),
            "masterplan_id": str(self.masterplan_id),
            "atom_number": self.atom_number,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "context": self.context.to_dict(),
            "validation": self.validation.to_dict(),
            "acceptance": self.acceptance.to_dict(),
            "retry": self.retry.to_dict(),
            "cost": self.cost.to_dict(),
            "timing": self.timing.to_dict()
        }

    def to_json(self) -> str:
        """
        Convert trace to JSON string.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict(), indent=2)

    def log_summary(self):
        """Log concise summary of trace."""
        logger.info(
            f"Atom {self.atom_number} trace summary",
            extra={
                "atom_id": str(self.atom_id),
                "status": self.status,
                "total_time": self.timing.total_seconds,
                "cost_usd": self.cost.total_cost_usd,
                "validation_passed": all([
                    self.validation.l1_syntax,
                    self.validation.l2_imports,
                    self.validation.l3_types,
                    self.validation.l4_complexity
                ]),
                "acceptance_pass_rate": (
                    self.acceptance.tests_passed / self.acceptance.tests_executed
                    if self.acceptance.tests_executed > 0 else 0.0
                ),
                "retry_attempts": self.retry.total_attempts
            }
        )
