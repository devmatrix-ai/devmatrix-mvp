"""
Stratum Metrics - Performance and Quality Tracking per Generation Stratum

Phase 3: Captures metrics per stratum for audit and optimization.

Metrics Captured:
- Duration (ms) per stratum
- Errors detected and repaired
- LLM token usage
- Files generated
- Success rate

Output: ASCII table for E2E reports.
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class Stratum(str, Enum):
    """Code generation strata."""
    TEMPLATE = "template"
    AST = "ast"
    LLM = "llm"
    QA = "qa"


@dataclass
class StratumMetrics:
    """
    Metrics for a single stratum.

    Tracks performance, errors, and resource usage.
    """
    stratum: Stratum
    duration_ms: float = 0.0
    errors_detected: int = 0
    errors_repaired: int = 0
    tokens_used: int = 0
    files_generated: int = 0

    # Detailed breakdowns
    generation_calls: int = 0
    repair_calls: int = 0
    validation_calls: int = 0

    # Error details
    error_types: Dict[str, int] = field(default_factory=dict)

    @property
    def repair_rate(self) -> float:
        """Percentage of detected errors that were repaired."""
        if self.errors_detected == 0:
            return 100.0
        return (self.errors_repaired / self.errors_detected) * 100.0

    @property
    def success_rate(self) -> float:
        """Overall success rate based on repairs."""
        if self.errors_detected == 0:
            return 100.0
        remaining_errors = self.errors_detected - self.errors_repaired
        return max(0.0, 100.0 - (remaining_errors * 10.0))  # -10% per unrepaired error

    def add_error(self, error_type: str) -> None:
        """Record an error by type."""
        self.errors_detected += 1
        self.error_types[error_type] = self.error_types.get(error_type, 0) + 1

    def add_repair(self) -> None:
        """Record a successful repair."""
        self.errors_repaired += 1

    def add_duration(self, ms: float) -> None:
        """Add duration to running total."""
        self.duration_ms += ms

    def add_tokens(self, tokens: int) -> None:
        """Add LLM token usage."""
        self.tokens_used += tokens

    def add_file(self) -> None:
        """Record a generated file."""
        self.files_generated += 1


@dataclass
class MetricsSnapshot:
    """
    Complete metrics snapshot across all strata.
    """
    app_id: str
    timestamp: str = ""
    execution_mode: str = "hybrid"

    # Per-stratum metrics
    template_metrics: StratumMetrics = field(default_factory=lambda: StratumMetrics(Stratum.TEMPLATE))
    ast_metrics: StratumMetrics = field(default_factory=lambda: StratumMetrics(Stratum.AST))
    llm_metrics: StratumMetrics = field(default_factory=lambda: StratumMetrics(Stratum.LLM))
    qa_metrics: StratumMetrics = field(default_factory=lambda: StratumMetrics(Stratum.QA))

    # Overall metrics
    total_duration_ms: float = 0.0
    total_files: int = 0
    total_errors: int = 0
    total_repaired: int = 0
    total_llm_tokens: int = 0

    def __post_init__(self):
        if not self.timestamp:
            from datetime import datetime, timezone
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def get_stratum_metrics(self, stratum: Stratum) -> StratumMetrics:
        """Get metrics for a specific stratum."""
        mapping = {
            Stratum.TEMPLATE: self.template_metrics,
            Stratum.AST: self.ast_metrics,
            Stratum.LLM: self.llm_metrics,
            Stratum.QA: self.qa_metrics,
        }
        return mapping.get(stratum, self.template_metrics)

    def finalize(self) -> None:
        """Calculate totals from per-stratum metrics."""
        all_metrics = [
            self.template_metrics,
            self.ast_metrics,
            self.llm_metrics,
            self.qa_metrics,
        ]

        self.total_duration_ms = sum(m.duration_ms for m in all_metrics)
        self.total_files = sum(m.files_generated for m in all_metrics)
        self.total_errors = sum(m.errors_detected for m in all_metrics)
        self.total_repaired = sum(m.errors_repaired for m in all_metrics)
        self.total_llm_tokens = self.llm_metrics.tokens_used

    @property
    def overall_success_rate(self) -> float:
        """Overall success rate across all strata."""
        if self.total_errors == 0:
            return 100.0
        remaining = self.total_errors - self.total_repaired
        return max(0.0, 100.0 - (remaining * 5.0))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "app_id": self.app_id,
            "timestamp": self.timestamp,
            "execution_mode": self.execution_mode,
            "strata": {
                "template": {
                    "duration_ms": self.template_metrics.duration_ms,
                    "files_generated": self.template_metrics.files_generated,
                    "errors_detected": self.template_metrics.errors_detected,
                    "errors_repaired": self.template_metrics.errors_repaired,
                    "tokens_used": self.template_metrics.tokens_used,
                },
                "ast": {
                    "duration_ms": self.ast_metrics.duration_ms,
                    "files_generated": self.ast_metrics.files_generated,
                    "errors_detected": self.ast_metrics.errors_detected,
                    "errors_repaired": self.ast_metrics.errors_repaired,
                    "tokens_used": self.ast_metrics.tokens_used,
                },
                "llm": {
                    "duration_ms": self.llm_metrics.duration_ms,
                    "files_generated": self.llm_metrics.files_generated,
                    "errors_detected": self.llm_metrics.errors_detected,
                    "errors_repaired": self.llm_metrics.errors_repaired,
                    "tokens_used": self.llm_metrics.tokens_used,
                },
                "qa": {
                    "duration_ms": self.qa_metrics.duration_ms,
                    "files_generated": self.qa_metrics.files_generated,
                    "errors_detected": self.qa_metrics.errors_detected,
                    "errors_repaired": self.qa_metrics.errors_repaired,
                    "tokens_used": self.qa_metrics.tokens_used,
                },
            },
            "totals": {
                "duration_ms": self.total_duration_ms,
                "files": self.total_files,
                "errors_detected": self.total_errors,
                "errors_repaired": self.total_repaired,
                "llm_tokens": self.total_llm_tokens,
                "success_rate": self.overall_success_rate,
            },
        }


class MetricsCollector:
    """
    Collects metrics during code generation pipeline.

    Usage:
        collector = MetricsCollector("my-app")

        with collector.track(Stratum.TEMPLATE):
            # generate template files
            collector.record_file(Stratum.TEMPLATE)

        with collector.track(Stratum.AST):
            # generate AST files
            collector.record_file(Stratum.AST)
            collector.record_error(Stratum.AST, "syntax_error")

        snapshot = collector.finalize()
        print(snapshot.get_ascii_table())
    """

    def __init__(self, app_id: str, execution_mode: str = "hybrid"):
        self.app_id = app_id
        self.execution_mode = execution_mode
        self.snapshot = MetricsSnapshot(
            app_id=app_id,
            execution_mode=execution_mode,
        )
        self._active_stratum: Optional[Stratum] = None
        self._stratum_start_time: Optional[float] = None

    @contextmanager
    def track(self, stratum: Stratum):
        """
        Context manager to track duration for a stratum.

        Usage:
            with collector.track(Stratum.AST):
                # do AST generation
        """
        self._active_stratum = stratum
        self._stratum_start_time = time.time()
        metrics = self.snapshot.get_stratum_metrics(stratum)
        metrics.generation_calls += 1

        try:
            yield metrics
        finally:
            elapsed_ms = (time.time() - self._stratum_start_time) * 1000
            metrics.add_duration(elapsed_ms)
            self._active_stratum = None
            self._stratum_start_time = None

    def record_file(
        self,
        stratum: Stratum,
        tokens: int = 0,
        duration_ms: float = 0.0,
    ) -> None:
        """Record a generated file with optional duration tracking (Bug #9 fix)."""
        metrics = self.snapshot.get_stratum_metrics(stratum)
        metrics.add_file()
        if tokens > 0:
            metrics.add_tokens(tokens)
        # Bug #9 Fix: Allow duration tracking without context manager
        if duration_ms > 0:
            metrics.add_duration(duration_ms)

    def record_error(
        self,
        stratum: Stratum,
        error_type: str = "unknown",
    ) -> None:
        """Record an error detected."""
        metrics = self.snapshot.get_stratum_metrics(stratum)
        metrics.add_error(error_type)

    def record_repair(self, stratum: Stratum) -> None:
        """Record a successful error repair."""
        metrics = self.snapshot.get_stratum_metrics(stratum)
        metrics.add_repair()

    def record_tokens(self, stratum: Stratum, tokens: int) -> None:
        """Record LLM token usage."""
        metrics = self.snapshot.get_stratum_metrics(stratum)
        metrics.add_tokens(tokens)

    def record_validation(
        self,
        errors_found: int,
        errors_fixed: int = 0,
    ) -> None:
        """Record QA validation results."""
        qa = self.snapshot.qa_metrics
        qa.errors_detected += errors_found
        qa.errors_repaired += errors_fixed
        qa.validation_calls += 1

    def finalize(self) -> MetricsSnapshot:
        """Finalize and return the metrics snapshot."""
        self.snapshot.finalize()
        return self.snapshot


def format_ascii_table(snapshot: MetricsSnapshot) -> str:
    """
    Generate ASCII table for E2E report.

    Output:
    ```
    📊 Stratum Performance:
    ┌──────────┬─────────┬────────┬──────────┬──────────┬────────────┐
    │ Stratum  │ Files   │ Time   │ Detected │ Repaired │ LLM Tokens │
    ├──────────┼─────────┼────────┼──────────┼──────────┼────────────┤
    │ TEMPLATE │      8  │  150ms │        0 │        0 │          0 │
    │ AST      │     12  │  600ms │        2 │        2 │          0 │
    │ LLM      │      3  │  800ms │        0 │        0 │    120,000 │
    │ QA       │      -  │ 2400ms │        1 │        1 │          0 │
    ├──────────┼─────────┼────────┼──────────┼──────────┼────────────┤
    │ TOTAL    │     23  │ 3950ms │        3 │        3 │    120,000 │
    └──────────┴─────────┴────────┴──────────┴──────────┴────────────┘
    ```
    """
    lines = ["", "📊 Stratum Performance:"]

    # Header
    lines.append("┌──────────┬─────────┬─────────┬──────────┬──────────┬────────────┐")
    lines.append("│ Stratum  │ Files   │ Time    │ Detected │ Repaired │ LLM Tokens │")
    lines.append("├──────────┼─────────┼─────────┼──────────┼──────────┼────────────┤")

    # Rows
    strata_data = [
        ("TEMPLATE", snapshot.template_metrics),
        ("AST", snapshot.ast_metrics),
        ("LLM", snapshot.llm_metrics),
        ("QA", snapshot.qa_metrics),
    ]

    for name, m in strata_data:
        files_str = f"{m.files_generated:>5}" if m.files_generated > 0 else "    -"
        time_str = f"{m.duration_ms:>6.0f}ms" if m.duration_ms > 0 else "      -"
        tokens_str = f"{m.tokens_used:>10,}" if m.tokens_used > 0 else "         0"

        lines.append(
            f"│ {name:<8} │ {files_str} │ {time_str} │ "
            f"{m.errors_detected:>8} │ {m.errors_repaired:>8} │ {tokens_str} │"
        )

    # Total row
    lines.append("├──────────┼─────────┼─────────┼──────────┼──────────┼────────────┤")

    total_files = f"{snapshot.total_files:>5}"
    total_time = f"{snapshot.total_duration_ms:>6.0f}ms"
    total_tokens = f"{snapshot.total_llm_tokens:>10,}" if snapshot.total_llm_tokens > 0 else "         0"

    lines.append(
        f"│ {'TOTAL':<8} │ {total_files} │ {total_time} │ "
        f"{snapshot.total_errors:>8} │ {snapshot.total_repaired:>8} │ {total_tokens} │"
    )

    lines.append("└──────────┴─────────┴─────────┴──────────┴──────────┴────────────┘")

    # Success rate
    lines.append(f"")
    lines.append(f"✅ Overall Success Rate: {snapshot.overall_success_rate:.1f}%")

    if snapshot.execution_mode:
        lines.append(f"🎚️ Execution Mode: {snapshot.execution_mode.upper()}")

    return "\n".join(lines)


# =============================================================================
# SINGLETON COLLECTOR
# =============================================================================

_collector: Optional[MetricsCollector] = None


def get_metrics_collector(
    app_id: Optional[str] = None,
    execution_mode: str = "hybrid",
) -> MetricsCollector:
    """Get or create singleton metrics collector."""
    global _collector
    if _collector is None or app_id is not None:
        _collector = MetricsCollector(
            app_id=app_id or "unknown",
            execution_mode=execution_mode,
        )
    return _collector


def reset_metrics_collector() -> None:
    """Reset the singleton collector."""
    global _collector
    _collector = None


def finalize_metrics() -> MetricsSnapshot:
    """Finalize and return the current metrics snapshot."""
    collector = get_metrics_collector()
    return collector.finalize()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def track_stratum(stratum: Stratum):
    """Context manager shortcut for stratum tracking."""
    return get_metrics_collector().track(stratum)


def record_template_file() -> None:
    """Record a template file generation."""
    get_metrics_collector().record_file(Stratum.TEMPLATE)


def record_ast_file(tokens: int = 0) -> None:
    """Record an AST file generation."""
    get_metrics_collector().record_file(Stratum.AST, tokens=tokens)


def record_llm_file(tokens: int = 0) -> None:
    """Record an LLM file generation."""
    get_metrics_collector().record_file(Stratum.LLM, tokens=tokens)


def record_error(stratum: Stratum, error_type: str = "unknown") -> None:
    """Record an error in a stratum."""
    get_metrics_collector().record_error(stratum, error_type)


def record_repair(stratum: Stratum) -> None:
    """Record a repair in a stratum."""
    get_metrics_collector().record_repair(stratum)


def record_validation_result(errors: int, repaired: int = 0) -> None:
    """Record QA validation results."""
    get_metrics_collector().record_validation(errors, repaired)


def get_stratum_report() -> str:
    """Get ASCII table report for current metrics."""
    snapshot = get_metrics_collector().finalize()
    return format_ascii_table(snapshot)
