"""
Trace Collector for MGE V2

Centralized service for collecting and storing atom execution traces.
"""
import logging
from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime

from .models import (
    AtomTrace,
    TraceEventType,
    TraceCorrelation,
    ValidationTrace,
    AcceptanceTestTrace
)

logger = logging.getLogger(__name__)


class TraceCollector:
    """
    Centralized trace collection service.

    Features:
    - In-memory trace storage (production would use database/distributed tracing)
    - Thread-safe trace management
    - Correlation analysis for dashboard
    - Query capabilities for traces
    """

    def __init__(self):
        """Initialize TraceCollector."""
        self.traces: Dict[UUID, AtomTrace] = {}  # trace_id -> AtomTrace
        self.atom_traces: Dict[UUID, UUID] = {}  # atom_id -> trace_id
        self.masterplan_traces: Dict[UUID, List[UUID]] = {}  # masterplan_id -> [trace_ids]

    def start_trace(
        self,
        atom_id: UUID,
        masterplan_id: UUID,
        wave_id: int,
        atom_name: str,
        context_data: Optional[Dict] = None,
        dependencies: Optional[List[str]] = None
    ) -> AtomTrace:
        """
        Start new trace for atom execution.

        Args:
            atom_id: Atom UUID
            masterplan_id: Masterplan UUID
            wave_id: Wave number
            atom_name: Atom name
            context_data: Optional context data
            dependencies: Optional dependency list

        Returns:
            New AtomTrace instance
        """
        trace = AtomTrace(
            atom_id=atom_id,
            masterplan_id=masterplan_id,
            wave_id=wave_id,
            atom_name=atom_name,
            context_data=context_data or {},
            dependencies=dependencies or []
        )

        # Store trace
        self.traces[trace.trace_id] = trace
        self.atom_traces[atom_id] = trace.trace_id

        # Add to masterplan traces
        if masterplan_id not in self.masterplan_traces:
            self.masterplan_traces[masterplan_id] = []
        self.masterplan_traces[masterplan_id].append(trace.trace_id)

        # Record start event
        trace.add_event(
            event_type=TraceEventType.ATOM_STARTED,
            data={
                "atom_name": atom_name,
                "wave_id": wave_id,
                "dependencies": dependencies or []
            }
        )

        logger.info(
            f"🔍 Started trace {trace.trace_id} for atom {atom_id} ({atom_name})"
        )

        return trace

    def get_trace_by_atom(self, atom_id: UUID) -> Optional[AtomTrace]:
        """Get trace for specific atom."""
        trace_id = self.atom_traces.get(atom_id)
        if not trace_id:
            return None
        return self.traces.get(trace_id)

    def get_trace(self, trace_id: UUID) -> Optional[AtomTrace]:
        """Get trace by ID."""
        return self.traces.get(trace_id)

    def get_masterplan_traces(self, masterplan_id: UUID) -> List[AtomTrace]:
        """Get all traces for a masterplan."""
        trace_ids = self.masterplan_traces.get(masterplan_id, [])
        return [self.traces[tid] for tid in trace_ids if tid in self.traces]

    def record_validation(
        self,
        atom_id: UUID,
        validation_result,  # AtomicValidationResult
        duration_ms: float
    ):
        """
        Record validation trace (L1-L4).

        Args:
            atom_id: Atom UUID
            validation_result: Validation result object
            duration_ms: Validation duration
        """
        trace = self.get_trace_by_atom(atom_id)
        if not trace:
            logger.warning(f"No trace found for atom {atom_id}")
            return

        # Extract L1-L4 metrics from validation result
        trace.validation = ValidationTrace(
            total_duration_ms=duration_ms,
            passed=validation_result.passed,
            issues_count=len(validation_result.issues)
        )

        # Record L1-L4 events based on metrics
        metrics = validation_result.metrics
        if "l1_syntax" in metrics:
            trace.add_event(
                TraceEventType.VALIDATION_L1_COMPLETED,
                data={"passed": metrics["l1_syntax"]["passed"]}
            )

        if "l2_imports" in metrics:
            trace.add_event(
                TraceEventType.VALIDATION_L2_COMPLETED,
                data={"passed": metrics["l2_imports"]["passed"]}
            )

        if "l3_types" in metrics:
            trace.add_event(
                TraceEventType.VALIDATION_L3_COMPLETED,
                data={"passed": metrics["l3_types"]["passed"]}
            )

        if "l4_complexity" in metrics:
            trace.add_event(
                TraceEventType.VALIDATION_L4_COMPLETED,
                data={"passed": metrics["l4_complexity"]["passed"]}
            )

        trace.time.validation_duration_ms = duration_ms

    def record_retry_attempt(
        self,
        atom_id: UUID,
        attempt: int,
        temperature: float,
        success: bool,
        duration_ms: float,
        error_feedback: Optional[List[str]] = None
    ):
        """
        Record retry attempt.

        Args:
            atom_id: Atom UUID
            attempt: Attempt number (1-4)
            temperature: Temperature used
            success: Whether attempt succeeded
            duration_ms: Attempt duration
            error_feedback: Optional error messages from previous attempt
        """
        trace = self.get_trace_by_atom(atom_id)
        if not trace:
            logger.warning(f"No trace found for atom {atom_id}")
            return

        trace.record_retry(
            attempt=attempt,
            temperature=temperature,
            success=success,
            duration_ms=duration_ms,
            error_feedback=error_feedback
        )

        trace.add_event(
            TraceEventType.RETRY_ATTEMPT,
            data={
                "attempt": attempt,
                "temperature": temperature,
                "success": success,
                "error_feedback_count": len(error_feedback) if error_feedback else 0
            },
            duration_ms=duration_ms
        )

        trace.time.retry_overhead_ms += duration_ms

    def record_acceptance_tests(
        self,
        atom_id: UUID,
        total_tests: int,
        passed_tests: int,
        failed_tests: int,
        must_pass_rate: float,
        should_pass_rate: float,
        duration_ms: float
    ):
        """
        Record acceptance test execution.

        Args:
            atom_id: Atom UUID
            total_tests: Total tests executed
            passed_tests: Tests passed
            failed_tests: Tests failed
            must_pass_rate: MUST requirements pass rate
            should_pass_rate: SHOULD requirements pass rate
            duration_ms: Test execution duration
        """
        trace = self.get_trace_by_atom(atom_id)
        if not trace:
            logger.warning(f"No trace found for atom {atom_id}")
            return

        trace.acceptance_tests = AcceptanceTestTrace(
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            must_pass_rate=must_pass_rate,
            should_pass_rate=should_pass_rate,
            duration_ms=duration_ms,
            timestamp=datetime.utcnow()
        )

        trace.add_event(
            TraceEventType.ACCEPTANCE_TESTS_COMPLETED,
            data={
                "total": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "must_pass_rate": must_pass_rate,
                "should_pass_rate": should_pass_rate
            },
            duration_ms=duration_ms
        )

        trace.time.acceptance_duration_ms = duration_ms

    def record_cost(
        self,
        atom_id: UUID,
        llm_api_cost_usd: float,
        prompt_tokens: int,
        completion_tokens: int,
        cache_hit: bool = False
    ):
        """
        Record LLM cost metrics.

        Args:
            atom_id: Atom UUID
            llm_api_cost_usd: Cost in USD
            prompt_tokens: Prompt tokens used
            completion_tokens: Completion tokens used
            cache_hit: Whether cache was hit
        """
        trace = self.get_trace_by_atom(atom_id)
        if not trace:
            logger.warning(f"No trace found for atom {atom_id}")
            return

        trace.cost.llm_api_cost_usd = llm_api_cost_usd
        trace.cost.prompt_tokens = prompt_tokens
        trace.cost.completion_tokens = completion_tokens
        trace.cost.total_tokens = prompt_tokens + completion_tokens
        trace.cost.cache_hit = cache_hit

    def complete_trace(
        self,
        atom_id: UUID,
        success: bool,
        code: Optional[str] = None,
        error: Optional[str] = None
    ):
        """
        Mark trace as completed.

        Args:
            atom_id: Atom UUID
            success: Whether execution succeeded
            code: Generated code (if successful)
            error: Error message (if failed)
        """
        trace = self.get_trace_by_atom(atom_id)
        if not trace:
            logger.warning(f"No trace found for atom {atom_id}")
            return

        status = "success" if success else "failed"
        trace.complete(status=status, code=code)

        trace.add_event(
            TraceEventType.ATOM_COMPLETED if success else TraceEventType.ATOM_FAILED,
            data={"status": status},
            error=error
        )

        logger.info(
            f"✅ Completed trace {trace.trace_id} for atom {atom_id}: {status} "
            f"in {trace.time.total_duration_ms:.1f}ms"
        )

    def calculate_correlations(self, masterplan_id: UUID) -> TraceCorrelation:
        """
        Calculate correlation metrics for dashboard.

        Args:
            masterplan_id: Masterplan UUID

        Returns:
            TraceCorrelation with correlation data
        """
        traces = self.get_masterplan_traces(masterplan_id)

        if not traces:
            return TraceCorrelation(
                masterplan_id=masterplan_id,
                total_atoms=0,
                avg_retries_success=0.0,
                avg_retries_failed=0.0,
                avg_l1_issues_success=0.0,
                avg_l1_issues_failed=0.0
            )

        # Split by success/failure
        success_traces = [t for t in traces if t.final_status == "success"]
        failed_traces = [t for t in traces if t.final_status == "failed"]

        # Calculate averages
        avg_retries_success = (
            sum(t.total_attempts for t in success_traces) / len(success_traces)
            if success_traces else 0.0
        )

        avg_retries_failed = (
            sum(t.total_attempts for t in failed_traces) / len(failed_traces)
            if failed_traces else 0.0
        )

        avg_l1_issues_success = (
            sum(t.validation.issues_count for t in success_traces) / len(success_traces)
            if success_traces else 0.0
        )

        avg_l1_issues_failed = (
            sum(t.validation.issues_count for t in failed_traces) / len(failed_traces)
            if failed_traces else 0.0
        )

        # Complexity vs time data
        complexity_time_data = [
            {
                "atom_name": t.atom_name,
                "complexity": t.context_data.get("complexity", "unknown"),
                "time_ms": t.time.total_duration_ms
            }
            for t in traces
        ]

        # Cost vs success correlation (simplified)
        success_costs = [t.cost.llm_api_cost_usd for t in success_traces]
        failed_costs = [t.cost.llm_api_cost_usd for t in failed_traces]

        avg_cost_success = sum(success_costs) / len(success_costs) if success_costs else 0.0
        avg_cost_failed = sum(failed_costs) / len(failed_costs) if failed_costs else 0.0

        cost_correlation = avg_cost_failed - avg_cost_success  # Higher cost → more likely to fail

        return TraceCorrelation(
            masterplan_id=masterplan_id,
            total_atoms=len(traces),
            avg_retries_success=avg_retries_success,
            avg_retries_failed=avg_retries_failed,
            avg_l1_issues_success=avg_l1_issues_success,
            avg_l1_issues_failed=avg_l1_issues_failed,
            complexity_time_data=complexity_time_data,
            cost_success_correlation=cost_correlation
        )

    def clear_traces(self, masterplan_id: Optional[UUID] = None):
        """
        Clear traces from memory.

        Args:
            masterplan_id: Optional masterplan ID to clear only specific traces
        """
        if masterplan_id:
            # Clear specific masterplan traces
            trace_ids = self.masterplan_traces.get(masterplan_id, [])
            for tid in trace_ids:
                if tid in self.traces:
                    # Remove from atom_traces mapping
                    atom_id = self.traces[tid].atom_id
                    if atom_id in self.atom_traces:
                        del self.atom_traces[atom_id]
                    # Remove trace
                    del self.traces[tid]
            # Remove masterplan entry
            if masterplan_id in self.masterplan_traces:
                del self.masterplan_traces[masterplan_id]
        else:
            # Clear all traces
            self.traces.clear()
            self.atom_traces.clear()
            self.masterplan_traces.clear()


# Global trace collector instance
_global_collector: Optional[TraceCollector] = None


def get_trace_collector() -> TraceCollector:
    """Get global trace collector instance."""
    global _global_collector
    if _global_collector is None:
        _global_collector = TraceCollector()
    return _global_collector
