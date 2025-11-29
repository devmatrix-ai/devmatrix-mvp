"""
Feedback Collector - Orchestrates the Generation Feedback Loop.

Collects smoke test results, classifies errors, and stores anti-patterns
for use in future code generation prompts.

Reference: DOCS/mvp/exit/learning/GENERATION_FEEDBACK_LOOP.md
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.learning.negative_pattern_store import (
    GenerationAntiPattern,
    NegativePatternStore,
    get_negative_pattern_store,
)
from src.learning.smoke_feedback_classifier import (
    SmokeFeedbackClassifier,
    get_smoke_feedback_classifier,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class FeedbackProcessingResult:
    """Result of processing smoke test feedback."""
    patterns_created: int = 0
    patterns_updated: int = 0
    unclassifiable_errors: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def total_processed(self) -> int:
        """Total patterns processed."""
        return self.patterns_created + self.patterns_updated

    @property
    def classification_rate(self) -> float:
        """Rate of successfully classified errors."""
        total = self.total_processed + len(self.unclassifiable_errors)
        return self.total_processed / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "patterns_created": self.patterns_created,
            "patterns_updated": self.patterns_updated,
            "unclassifiable_errors": len(self.unclassifiable_errors),
            "total_processed": self.total_processed,
            "classification_rate": self.classification_rate,
            "processing_time_ms": self.processing_time_ms,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class FeedbackSessionStats:
    """Statistics for a feedback session (multiple runs)."""
    session_id: str
    runs_processed: int = 0
    total_patterns_created: int = 0
    total_patterns_updated: int = 0
    total_unclassifiable: int = 0
    started_at: datetime = field(default_factory=datetime.now)

    def update(self, result: FeedbackProcessingResult):
        """Update stats with processing result."""
        self.runs_processed += 1
        self.total_patterns_created += result.patterns_created
        self.total_patterns_updated += result.patterns_updated
        self.total_unclassifiable += len(result.unclassifiable_errors)


# =============================================================================
# Feedback Collector
# =============================================================================


class GenerationFeedbackCollector:
    """
    Collects smoke test results and creates anti-patterns.

    Integrates with:
    - RuntimeSmokeTestValidator (source of violations)
    - SmokeFeedbackClassifier (classification)
    - NegativePatternStore (persistence)

    Flow:
        SmokeTestResult → Classifier → Anti-patterns → Store → Next CodeGen
    """

    def __init__(
        self,
        classifier: Optional[SmokeFeedbackClassifier] = None,
        store: Optional[NegativePatternStore] = None,
    ):
        """
        Initialize collector.

        Args:
            classifier: SmokeFeedbackClassifier (or uses singleton)
            store: NegativePatternStore (or uses singleton)
        """
        self.classifier = classifier or get_smoke_feedback_classifier()
        self.store = store or get_negative_pattern_store()
        self.logger = logging.getLogger(f"{__name__}.GenerationFeedbackCollector")

        # Session tracking
        self._session_stats: Optional[FeedbackSessionStats] = None

    # =========================================================================
    # Main Processing Methods
    # =========================================================================

    async def process_smoke_results(
        self,
        smoke_result: Any,
        application_ir: Any,
        generation_manifest: Dict[str, Any] = None,
    ) -> FeedbackProcessingResult:
        """
        Process smoke test results and store anti-patterns.

        Args:
            smoke_result: SmokeTestResult from RuntimeSmokeValidator
            application_ir: ApplicationIR for context
            generation_manifest: Generation manifest (optional)

        Returns:
            FeedbackProcessingResult with statistics
        """
        import time
        start_time = time.time()

        result = FeedbackProcessingResult()

        # Extract violations and stack traces
        violations = self._extract_violations(smoke_result)
        stack_traces = self._extract_stack_traces(smoke_result)

        if not violations:
            self.logger.debug("No violations to process")
            result.processing_time_ms = (time.time() - start_time) * 1000
            return result

        self.logger.info(f"Processing {len(violations)} smoke violations")

        # Build stack trace lookup
        stack_trace_map = self._build_stack_trace_map(stack_traces)

        # Process each violation
        for violation in violations:
            endpoint = violation.get("endpoint", "")
            stack_trace = stack_trace_map.get(endpoint, "")

            # Classify and create anti-pattern
            anti_pattern = self.classifier.classify_for_generation(
                violation=violation,
                stack_trace=stack_trace,
                application_ir=application_ir,
            )

            if anti_pattern:
                # Store or update pattern
                if self.store.exists(anti_pattern.pattern_id):
                    self.store.increment_occurrence(anti_pattern.pattern_id)
                    result.patterns_updated += 1
                else:
                    self.store.store(anti_pattern)
                    result.patterns_created += 1
            else:
                # Could not classify
                error_desc = f"{violation.get('error_type', 'Unknown')}: {violation.get('endpoint', 'N/A')}"
                result.unclassifiable_errors.append(error_desc)

        result.processing_time_ms = (time.time() - start_time) * 1000

        # Update session stats if active
        if self._session_stats:
            self._session_stats.update(result)

        # Log summary
        self._log_processing_result(result)

        return result

    def process_smoke_results_sync(
        self,
        smoke_result: Any,
        application_ir: Any,
        generation_manifest: Dict[str, Any] = None,
    ) -> FeedbackProcessingResult:
        """
        Synchronous version of process_smoke_results.

        For use in non-async contexts.
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, create a new task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.process_smoke_results(
                            smoke_result, application_ir, generation_manifest
                        )
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self.process_smoke_results(
                        smoke_result, application_ir, generation_manifest
                    )
                )
        except RuntimeError:
            # No event loop, run directly
            return asyncio.run(
                self.process_smoke_results(
                    smoke_result, application_ir, generation_manifest
                )
            )

    # =========================================================================
    # Session Management
    # =========================================================================

    def start_session(self, session_id: str = None) -> str:
        """Start a new feedback session for tracking."""
        import uuid
        session_id = session_id or f"feedback_{uuid.uuid4().hex[:8]}"
        self._session_stats = FeedbackSessionStats(session_id=session_id)
        self.logger.info(f"Started feedback session: {session_id}")
        return session_id

    def end_session(self) -> Optional[FeedbackSessionStats]:
        """End current session and return stats."""
        stats = self._session_stats
        self._session_stats = None

        if stats:
            self.logger.info(
                f"Ended feedback session {stats.session_id}: "
                f"{stats.runs_processed} runs, "
                f"{stats.total_patterns_created} created, "
                f"{stats.total_patterns_updated} updated"
            )

        return stats

    def get_session_stats(self) -> Optional[FeedbackSessionStats]:
        """Get current session stats."""
        return self._session_stats

    # =========================================================================
    # Store Statistics
    # =========================================================================

    def get_store_statistics(self) -> Dict[str, Any]:
        """Get statistics from the pattern store."""
        return self.store.get_statistics()

    def get_all_patterns(self, limit: int = 50) -> List[GenerationAntiPattern]:
        """Get all stored patterns."""
        return self.store.get_all_patterns(min_occurrences=1, limit=limit)

    def get_prevention_metrics(self) -> Dict[str, Any]:
        """Calculate prevention metrics."""
        stats = self.store.get_statistics()

        total_occurrences = stats.get("total_occurrences", 0)
        total_preventions = stats.get("total_preventions", 0)
        total = total_occurrences + total_preventions

        return {
            "total_patterns": stats.get("total_patterns", 0),
            "total_occurrences": total_occurrences,
            "total_preventions": total_preventions,
            "prevention_rate": total_preventions / total if total > 0 else 0.0,
            "patterns_by_error_type": stats.get("patterns_by_error_type", {}),
        }

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _extract_violations(self, smoke_result: Any) -> List[Dict[str, Any]]:
        """Extract violations from smoke result."""
        if smoke_result is None:
            return []

        # Handle both dataclass and dict formats
        if hasattr(smoke_result, "violations"):
            return list(smoke_result.violations)
        elif isinstance(smoke_result, dict):
            return smoke_result.get("violations", [])

        return []

    def _extract_stack_traces(self, smoke_result: Any) -> List[Dict[str, Any]]:
        """Extract stack traces from smoke result."""
        if smoke_result is None:
            return []

        if hasattr(smoke_result, "stack_traces"):
            return list(smoke_result.stack_traces)
        elif isinstance(smoke_result, dict):
            return smoke_result.get("stack_traces", [])

        return []

    def _build_stack_trace_map(
        self,
        stack_traces: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Build endpoint → stack_trace mapping."""
        trace_map = {}

        for st in stack_traces:
            endpoint = st.get("endpoint", "")
            trace = st.get("trace", st.get("stack_trace", ""))

            if endpoint:
                trace_map[endpoint] = trace

        return trace_map

    def _log_processing_result(self, result: FeedbackProcessingResult):
        """Log processing result."""
        if result.total_processed == 0 and not result.unclassifiable_errors:
            return

        msg = (
            f"📊 Generation feedback: "
            f"{result.patterns_created} new, "
            f"{result.patterns_updated} updated anti-patterns"
        )

        if result.unclassifiable_errors:
            msg += f" ({len(result.unclassifiable_errors)} unclassifiable)"

        msg += f" [{result.processing_time_ms:.0f}ms]"

        self.logger.info(msg)
        print(msg)  # Also print for visibility


# =============================================================================
# Singleton Instance
# =============================================================================

_feedback_collector: Optional[GenerationFeedbackCollector] = None


def get_feedback_collector() -> GenerationFeedbackCollector:
    """Get singleton instance of GenerationFeedbackCollector."""
    global _feedback_collector
    if _feedback_collector is None:
        _feedback_collector = GenerationFeedbackCollector()
    return _feedback_collector


# =============================================================================
# Convenience Functions
# =============================================================================


async def process_smoke_feedback(
    smoke_result: Any,
    application_ir: Any,
    generation_manifest: Dict[str, Any] = None,
) -> FeedbackProcessingResult:
    """
    Convenience function to process smoke test feedback.

    Usage in E2E pipeline:
        from src.learning.feedback_collector import process_smoke_feedback

        result = await process_smoke_feedback(
            smoke_result=validator.result,
            application_ir=application_ir,
            generation_manifest=manifest.to_dict()
        )
        # Output: "📊 Generation feedback: 5 new, 2 updated anti-patterns"

    Args:
        smoke_result: SmokeTestResult from RuntimeSmokeValidator
        application_ir: ApplicationIR
        generation_manifest: Generation manifest (optional)

    Returns:
        FeedbackProcessingResult
    """
    collector = get_feedback_collector()
    return await collector.process_smoke_results(
        smoke_result=smoke_result,
        application_ir=application_ir,
        generation_manifest=generation_manifest,
    )


def process_smoke_feedback_sync(
    smoke_result: Any,
    application_ir: Any,
    generation_manifest: Dict[str, Any] = None,
) -> FeedbackProcessingResult:
    """
    Synchronous version of process_smoke_feedback.

    For use in non-async code.
    """
    collector = get_feedback_collector()
    return collector.process_smoke_results_sync(
        smoke_result=smoke_result,
        application_ir=application_ir,
        generation_manifest=generation_manifest,
    )
