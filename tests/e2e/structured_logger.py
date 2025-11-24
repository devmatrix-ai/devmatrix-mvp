"""
Structured Logger for E2E Pipeline
Integrates with ProgressTracker to provide clean, hierarchical logging
without duplication while maintaining full technical detail.
"""

import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
from tests.e2e.progress_tracker import (
    get_tracker,
    update_phase,
    add_item,
    update_metrics,
)


class StructuredLogger:
    """
    Hierarchical logger that integrates with ProgressTracker.

    Features:
    - Eliminate duplicate logs
    - Hierarchical indentation for context
    - Integrate detailed logs with progress bars
    - Keep all technical information organized
    """

    def __init__(self, phase_name: str, indent_level: int = 0):
        """Initialize logger for a phase"""
        self.phase_name = phase_name
        self.indent_level = indent_level
        self.base_indent = "  " * indent_level
        self.tracker = get_tracker()
        self._log_buffer: List[str] = []
        self._metrics: Dict[str, Any] = {}

    def section(self, title: str, emoji: str = "📋") -> None:
        """Log a section header"""
        self._print(f"{emoji} {title}")

    def step(self, description: str, emoji: str = "📝") -> None:
        """Log a step/substep"""
        self._print(f"{emoji} {description}")
        update_phase(self.phase_name, step=description)

    def success(self, message: str, details: Optional[Dict] = None) -> None:
        """Log a success with optional details"""
        self._print(f"✓ {message}")
        if details:
            for key, value in details.items():
                self._print(f"  ├─ {key}: {value}", indent=1)

    def info(self, message: str, details: Optional[Dict] = None) -> None:
        """Log info with optional details"""
        self._print(f"ℹ️ {message}")
        if details:
            for key, value in details.items():
                self._print(f"  ├─ {key}: {value}", indent=1)

    def warning(self, message: str, details: Optional[Dict] = None) -> None:
        """Log warning with optional details"""
        self._print(f"⚠️ {message}")
        if details:
            for key, value in details.items():
                self._print(f"  ├─ {key}: {value}", indent=1)

    def error(self, message: str, details: Optional[Dict] = None) -> None:
        """Log error with optional details"""
        self._print(f"❌ {message}")
        if details:
            for key, value in details.items():
                self._print(f"  ├─ {key}: {value}", indent=1)

    def metric(self, name: str, value: Any, unit: str = "", emoji: str = "📊") -> None:
        """Log a metric"""
        formatted_value = f"{value}{unit}" if unit else str(value)
        self._print(f"{emoji} {name}: {formatted_value}")
        self._metrics[name] = value

    def metrics_group(self, title: str, metrics: Dict[str, Any], emoji: str = "📊") -> None:
        """Log a group of metrics"""
        self._print(f"{emoji} {title}")
        for key, value in metrics.items():
            self._print(f"  ├─ {key}: {value}", indent=1)
            self._metrics[key] = value

    def accuracy_metrics(
        self,
        accuracy: float = None,
        precision: float = None,
        recall: float = None,
        f1: float = None,
    ) -> None:
        """Log classification metrics in standard format"""
        metrics = {}
        if accuracy is not None:
            metrics["Accuracy"] = f"{accuracy:.1%}"
        if precision is not None:
            metrics["Precision"] = f"{precision:.1%}"
        if recall is not None:
            metrics["Recall"] = f"{recall:.1%}"
        if f1 is not None:
            metrics["F1-Score"] = f"{f1:.1%}"

        self.metrics_group("Classification Metrics", metrics, "📊")

    def data_structure(
        self,
        title: str,
        items: Dict[str, int],
        emoji: str = "📦",
    ) -> None:
        """Log a data structure with item counts"""
        self._print(f"{emoji} {title}")
        for item_type, count in items.items():
            self._print(f"  ├─ {item_type}: {count}", indent=1)
            add_item(self.phase_name, item_type, count, count)

    def checkpoint(self, name: str, description: str = "", status: str = "✓") -> None:
        """Log a checkpoint"""
        if description:
            self._print(f"{status} Checkpoint {name}: {description}")
        else:
            self._print(f"{status} Checkpoint {name}")

    def phase_summary(
        self,
        duration_ms: float,
        key_metrics: Optional[Dict[str, str]] = None,
        status: str = "✅",
    ) -> None:
        """Log phase completion summary"""
        duration_sec = duration_ms / 1000
        self._print(f"\n{status} Phase Completed: {self.phase_name} ({duration_sec:.1f}s)")

        if key_metrics:
            for metric_name, metric_value in key_metrics.items():
                self._print(f"  ├─ {metric_name}: {metric_value}", indent=1)

    def separator(self, char: str = "─", width: int = 80) -> None:
        """Log a separator line"""
        print(self.base_indent + char * width)

    def blank_line(self) -> None:
        """Log a blank line"""
        print()

    def update_live_metrics(
        self,
        neo4j: int = None,
        qdrant: int = None,
        tokens: int = None,
    ) -> None:
        """Update live metrics in progress tracker"""
        if neo4j is not None or qdrant is not None or tokens is not None:
            update_metrics(
                neo4j=neo4j or 0,
                qdrant=qdrant or 0,
                tokens=tokens or 0,
            )

    def _print(self, message: str, indent: int = 0) -> None:
        """Internal print with indentation"""
        full_indent = self.base_indent + ("  " * indent)
        print(f"{full_indent}{message}")
        self._log_buffer.append(message)

    def get_logs(self) -> List[str]:
        """Get all logged messages for this phase"""
        return self._log_buffer.copy()

    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics recorded for this phase"""
        return self._metrics.copy()


class ContextLogger:
    """Multi-phase logger with context management"""

    def __init__(self):
        """Initialize context logger"""
        self._phase_loggers: Dict[str, StructuredLogger] = {}
        self._current_phase: Optional[str] = None

    def create_phase_logger(self, phase_name: str) -> StructuredLogger:
        """Create or get logger for a phase"""
        if phase_name not in self._phase_loggers:
            self._phase_loggers[phase_name] = StructuredLogger(phase_name)
        self._current_phase = phase_name
        return self._phase_loggers[phase_name]

    def get_phase_logger(self, phase_name: str) -> Optional[StructuredLogger]:
        """Get logger for a phase"""
        return self._phase_loggers.get(phase_name)

    def current(self) -> Optional[StructuredLogger]:
        """Get current phase logger"""
        if self._current_phase:
            return self._phase_loggers.get(self._current_phase)
        return None

    def get_all_logs(self) -> Dict[str, List[str]]:
        """Get all logs from all phases"""
        return {
            phase: logger.get_logs()
            for phase, logger in self._phase_loggers.items()
        }

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all metrics from all phases"""
        return {
            phase: logger.get_metrics()
            for phase, logger in self._phase_loggers.items()
        }


# Global context logger instance
_context_logger: Optional[ContextLogger] = None


def get_context_logger() -> ContextLogger:
    """Get or create global context logger"""
    global _context_logger
    if _context_logger is None:
        _context_logger = ContextLogger()
    return _context_logger


def create_phase_logger(phase_name: str) -> StructuredLogger:
    """Create logger for a phase"""
    return get_context_logger().create_phase_logger(phase_name)


def log_phase_header(phase_name: str, emoji: str = "🔍") -> None:
    """Log phase header with separator"""
    print("\n" + "=" * 80)
    print(f"{emoji} {phase_name}")
    print("=" * 80)


def log_completion_section(title: str, emoji: str = "✅") -> None:
    """Log completion section"""
    print(f"\n{emoji} {title}")
    print("-" * 80)
