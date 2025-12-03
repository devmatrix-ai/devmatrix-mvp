"""
Learning Effectiveness Tracker - Measures real improvement from learning.

Phase 5: Verifies that learning actually improves subsequent generations
by comparing metrics across runs.

100% domain-agnostic: tracks patterns, not entities.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RunMetrics:
    """Metrics from a single generation run."""
    run_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Error counts by type
    errors_404: int = 0           # Precondition errors
    errors_422: int = 0           # Business logic errors
    errors_500: int = 0           # Internal errors
    errors_schema: int = 0        # Schema validation errors
    total_errors: int = 0
    
    # Repair metrics
    repair_iterations: int = 0
    successful_repairs: int = 0
    failed_repairs: int = 0
    
    # Learning metrics
    fixes_from_learning: int = 0  # Guards reused from store
    fixes_from_llm: int = 0       # Guards generated fresh
    patterns_applied: int = 0     # Prompt patterns used
    preconditions_learned: int = 0
    
    # Smoke test outcome
    smoke_tests_passed: int = 0
    smoke_tests_total: int = 0
    
    @property
    def learning_reuse_rate(self) -> float:
        """Rate of fixes from learning vs total."""
        total = self.fixes_from_learning + self.fixes_from_llm
        return self.fixes_from_learning / total if total > 0 else 0.0
    
    @property
    def error_rate(self) -> float:
        """Error rate across all tests."""
        if self.smoke_tests_total == 0:
            return 1.0
        return 1.0 - (self.smoke_tests_passed / self.smoke_tests_total)
    
    @property
    def repair_success_rate(self) -> float:
        """Success rate of repairs."""
        total = self.successful_repairs + self.failed_repairs
        return self.successful_repairs / total if total > 0 else 0.0


@dataclass
class RunComparison:
    """Comparison between two runs to measure learning impact."""
    run_before: str
    run_after: str
    
    # Improvement metrics (positive = improvement)
    error_reduction: float = 0.0        # % fewer errors
    iteration_reduction: float = 0.0     # % fewer repair iterations
    learning_reuse_increase: float = 0.0 # Increase in fix reuse
    
    # Counts
    patterns_reused: int = 0
    preconditions_satisfied: int = 0
    
    # Summary
    overall_improvement: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "run_before": self.run_before,
            "run_after": self.run_after,
            "error_reduction_pct": round(self.error_reduction * 100, 1),
            "iteration_reduction_pct": round(self.iteration_reduction * 100, 1),
            "learning_reuse_increase_pct": round(self.learning_reuse_increase * 100, 1),
            "patterns_reused": self.patterns_reused,
            "preconditions_satisfied": self.preconditions_satisfied,
            "overall_improvement_pct": round(self.overall_improvement * 100, 1),
        }


class LearningEffectivenessTracker:
    """
    Tracks if learning actually improves outcomes across runs.
    
    Usage:
        tracker = get_effectiveness_tracker()
        
        # Record run metrics
        tracker.record_run("run_1", metrics1)
        tracker.record_run("run_2", metrics2)
        
        # Compare
        comparison = tracker.compare_runs("run_1", "run_2")
        print(f"Error reduction: {comparison.error_reduction:.1%}")
    """
    
    def __init__(self):
        self._runs: Dict[str, RunMetrics] = {}
        self._neo4j = None
        self._neo4j_enabled = False
        self._init_neo4j()
    
    def _init_neo4j(self) -> None:
        """Initialize Neo4j connection for persistence."""
        try:
            from src.cognitive.services.neo4j_ir_repository import Neo4jIRRepository
            self._neo4j = Neo4jIRRepository()
            self._neo4j_enabled = True
            logger.debug("📊 EffectivenessTracker: Neo4j enabled")
        except Exception as e:
            logger.debug(f"📊 EffectivenessTracker: Neo4j not available ({e})")

    def record_run(self, run_id: str, metrics: RunMetrics) -> None:
        """Record metrics for a run."""
        metrics.run_id = run_id
        self._runs[run_id] = metrics
        self._persist_run(metrics)
        logger.info(f"📊 Recorded run: {run_id} (errors={metrics.total_errors})")

    def get_run(self, run_id: str) -> Optional[RunMetrics]:
        """Get metrics for a run."""
        return self._runs.get(run_id)

    def compare_runs(self, run_before_id: str, run_after_id: str) -> RunComparison:
        """
        Compare two runs to measure learning impact.

        Args:
            run_before_id: ID of the earlier run (baseline)
            run_after_id: ID of the later run (with learning)

        Returns:
            RunComparison with improvement metrics
        """
        before = self._runs.get(run_before_id)
        after = self._runs.get(run_after_id)

        if not before or not after:
            logger.warning(f"Cannot compare: missing run data")
            return RunComparison(run_before=run_before_id, run_after=run_after_id)

        comparison = RunComparison(
            run_before=run_before_id,
            run_after=run_after_id,
        )

        # Error reduction
        if before.total_errors > 0:
            comparison.error_reduction = (
                (before.total_errors - after.total_errors) / before.total_errors
            )

        # Iteration reduction
        if before.repair_iterations > 0:
            comparison.iteration_reduction = (
                (before.repair_iterations - after.repair_iterations) / before.repair_iterations
            )

        # Learning reuse increase
        comparison.learning_reuse_increase = (
            after.learning_reuse_rate - before.learning_reuse_rate
        )

        # Pattern reuse count
        comparison.patterns_reused = after.fixes_from_learning
        comparison.preconditions_satisfied = after.preconditions_learned

        # Overall improvement (weighted average)
        comparison.overall_improvement = (
            comparison.error_reduction * 0.5 +
            comparison.iteration_reduction * 0.3 +
            comparison.learning_reuse_increase * 0.2
        )

        logger.info(
            f"📊 Run comparison: {run_before_id} → {run_after_id}: "
            f"errors {comparison.error_reduction:+.1%}, "
            f"iterations {comparison.iteration_reduction:+.1%}"
        )

        return comparison

    def get_trend(self, last_n: int = 5) -> Dict[str, Any]:
        """Get trend across last N runs."""
        runs = sorted(
            self._runs.values(),
            key=lambda r: r.timestamp,
            reverse=True
        )[:last_n]

        if len(runs) < 2:
            return {"trend": "insufficient_data", "runs": len(runs)}

        # Calculate trends
        error_trend = [r.total_errors for r in reversed(runs)]
        reuse_trend = [r.learning_reuse_rate for r in reversed(runs)]

        # Simple trend detection
        improving = error_trend[-1] < error_trend[0]

        return {
            "trend": "improving" if improving else "stable_or_declining",
            "runs_analyzed": len(runs),
            "error_trend": error_trend,
            "reuse_trend": [round(r, 2) for r in reuse_trend],
            "latest_error_count": runs[0].total_errors,
            "latest_reuse_rate": round(runs[0].learning_reuse_rate, 2),
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics."""
        if not self._runs:
            return {"total_runs": 0}

        runs = list(self._runs.values())
        return {
            "total_runs": len(runs),
            "avg_errors": sum(r.total_errors for r in runs) / len(runs),
            "avg_reuse_rate": sum(r.learning_reuse_rate for r in runs) / len(runs),
            "total_fixes_from_learning": sum(r.fixes_from_learning for r in runs),
            "total_patterns_applied": sum(r.patterns_applied for r in runs),
        }

    def _persist_run(self, metrics: RunMetrics) -> None:
        """Persist run metrics to Neo4j."""
        if not self._neo4j_enabled or not self._neo4j:
            return

        try:
            query = """
            MERGE (r:LearningRun {run_id: $run_id})
            SET r.timestamp = datetime(),
                r.total_errors = $total_errors,
                r.errors_404 = $errors_404,
                r.errors_422 = $errors_422,
                r.repair_iterations = $iterations,
                r.fixes_from_learning = $from_learning,
                r.fixes_from_llm = $from_llm,
                r.learning_reuse_rate = $reuse_rate
            """
            self._neo4j.execute_query(query, {
                "run_id": metrics.run_id,
                "total_errors": metrics.total_errors,
                "errors_404": metrics.errors_404,
                "errors_422": metrics.errors_422,
                "iterations": metrics.repair_iterations,
                "from_learning": metrics.fixes_from_learning,
                "from_llm": metrics.fixes_from_llm,
                "reuse_rate": metrics.learning_reuse_rate,
            })
        except Exception as e:
            logger.warning(f"Could not persist run metrics: {e}")

    def clear(self) -> None:
        """Clear all run data (for testing)."""
        self._runs.clear()


# Singleton instance
_tracker_instance: Optional[LearningEffectivenessTracker] = None


def get_effectiveness_tracker() -> LearningEffectivenessTracker:
    """Get singleton EffectivenessTracker instance."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = LearningEffectivenessTracker()
    return _tracker_instance

