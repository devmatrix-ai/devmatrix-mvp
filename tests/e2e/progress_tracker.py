"""
Progress Tracker for E2E Pipeline
Real-time visualization of pipeline execution with animated progress bars
"""

import sys
import time
import psutil
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum


class PhaseStatus(Enum):
    """Phase execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PhaseMetrics:
    """Metrics for a single phase"""
    name: str
    status: PhaseStatus = PhaseStatus.PENDING
    progress: float = 0.0  # 0.0 to 1.0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    current_step: str = ""
    substeps_completed: int = 0
    substeps_total: int = 0
    errors: int = 0
    items_processed: Dict[str, Tuple[int, int]] = field(default_factory=dict)  # {name: (completed, total)}

    @property
    def duration_ms(self) -> float:
        """Duration in milliseconds"""
        if not self.start_time:
            return 0
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000

    @property
    def is_active(self) -> bool:
        """Is phase currently running"""
        return self.status == PhaseStatus.IN_PROGRESS


@dataclass
class LiveMetrics:
    """Live system metrics during execution"""
    timestamp: float = field(default_factory=time.time)
    memory_mb: float = 0.0
    memory_percent: float = 0.0
    cpu_percent: float = 0.0
    neo4j_queries: int = 0
    qdrant_queries: int = 0
    tokens_used: int = 0

    @classmethod
    def collect(cls, neo4j_count: int = 0, qdrant_count: int = 0, tokens: int = 0) -> "LiveMetrics":
        """Collect current system metrics"""
        process = psutil.Process()
        mem_info = process.memory_info()

        return cls(
            timestamp=time.time(),
            memory_mb=mem_info.rss / 1024 / 1024,
            memory_percent=process.memory_percent(),
            cpu_percent=process.cpu_percent(interval=0.1),
            neo4j_queries=neo4j_count,
            qdrant_queries=qdrant_count,
            tokens_used=tokens
        )


class ProgressTracker:
    """
    Real-time progress tracking for E2E pipeline
    Displays animated progress bars and live metrics
    """

    PHASES = [
        "Spec Ingestion",
        "Requirements Analysis",
        "Multi-Pass Planning",
        "Atomization",
        "DAG Construction",
        "Code Generation",
        "Deployment",
        "Code Repair",
        "Validation",
        "Health Verification",
        "Learning"
    ]

    PROGRESS_BLOCK_LINES = 19  # Lines occupied by progress block (header + 11 phases + metrics + footer)

    def __init__(self):
        self.phases: Dict[str, PhaseMetrics] = {
            name: PhaseMetrics(name=name) for name in self.PHASES
        }
        self.start_time = time.time()
        self.live_metrics: Optional[LiveMetrics] = None
        self.enable_display = True
        self.last_phase_shown = None
        self.progress_block_printed = False

    def start_phase(self, phase_name: str, substeps_total: int = 1):
        """Mark phase as started"""
        if phase_name in self.phases:
            self.phases[phase_name].status = PhaseStatus.IN_PROGRESS
            self.phases[phase_name].start_time = time.time()
            self.phases[phase_name].substeps_total = substeps_total
            self.phases[phase_name].substeps_completed = 0
            self.phases[phase_name].progress = 0.0

    def update_phase(self, phase_name: str, current_step: str = "", progress: Optional[float] = None):
        """Update phase progress"""
        if phase_name in self.phases:
            phase = self.phases[phase_name]
            phase.current_step = current_step
            if progress is not None:
                phase.progress = max(0.0, min(1.0, progress))
            else:
                # Auto-calculate from substeps
                if phase.substeps_total > 0:
                    phase.progress = phase.substeps_completed / phase.substeps_total

    def increment_step(self, phase_name: str, increment: int = 1):
        """Increment completed substeps"""
        if phase_name in self.phases:
            phase = self.phases[phase_name]
            phase.substeps_completed = min(
                phase.substeps_total,
                phase.substeps_completed + increment
            )
            if phase.substeps_total > 0:
                phase.progress = phase.substeps_completed / phase.substeps_total

    def add_item(self, phase_name: str, item_type: str, completed: int, total: int):
        """Track specific items (entities, endpoints, etc)"""
        if phase_name in self.phases:
            self.phases[phase_name].items_processed[item_type] = (completed, total)

    def complete_phase(self, phase_name: str, success: bool = True):
        """Mark phase as completed"""
        if phase_name in self.phases:
            phase = self.phases[phase_name]
            phase.status = PhaseStatus.COMPLETED if success else PhaseStatus.FAILED
            phase.end_time = time.time()
            phase.progress = 1.0 if success else phase.progress

    def add_error(self, phase_name: str):
        """Record an error in phase"""
        if phase_name in self.phases:
            self.phases[phase_name].errors += 1

    def update_metrics(self, neo4j_queries: int = 0, qdrant_queries: int = 0, tokens: int = 0):
        """Update live system metrics"""
        self.live_metrics = LiveMetrics.collect(
            neo4j_count=neo4j_queries,
            qdrant_count=qdrant_queries,
            tokens=tokens
        )

    def _render_progress_bar(self, progress: float, width: int = 20, char: str = "█") -> str:
        """Render a single progress bar"""
        filled = int(width * progress)
        bar = char * filled + "░" * (width - filled)
        percent = int(progress * 100)
        return f"[{bar}] {percent:3d}%"

    def _get_phase_icon(self, phase: PhaseMetrics) -> str:
        """Get icon for phase status"""
        if phase.status == PhaseStatus.COMPLETED:
            return "✅"
        elif phase.status == PhaseStatus.FAILED:
            return "❌"
        elif phase.status == PhaseStatus.IN_PROGRESS:
            return "🔷"
        else:
            return "⏳"

    def display(self, clear: bool = False):
        """Display current progress to console"""
        if not self.enable_display:
            return

        # Find the currently active phase
        active_phase = None
        for phase in self.phases.values():
            if phase.status == PhaseStatus.IN_PROGRESS:
                active_phase = phase
                break

        # If phase changed, clear the previous progress block completely
        if sys.stdout.isatty() and active_phase and self.last_phase_shown != active_phase.name:
            if self.progress_block_printed:
                # Move cursor up to start of previous progress block and clear it
                try:
                    # Use ANSI escape codes to move up and clear
                    sys.stdout.write(f"\033[{self.PROGRESS_BLOCK_LINES}A")  # Move up N lines
                    sys.stdout.write("\033[J")  # Clear from cursor to end of screen
                    sys.stdout.flush()
                except:
                    pass  # Silently fail on unsupported terminals

        elapsed = time.time() - self.start_time
        elapsed_str = self._format_time(elapsed)

        # Header
        print("=" * 80)
        print(" " * 20 + "📊 E2E PIPELINE PROGRESS" + " " * 20)
        print("=" * 80)
        print()

        # Phases
        for phase_name in self.PHASES:
            phase = self.phases[phase_name]
            icon = self._get_phase_icon(phase)
            bar = self._render_progress_bar(phase.progress, width=18)

            # Phase line
            print(f"  {icon} {phase_name:25s} {bar}", end="")

            # Show stats when completed, current step when in progress
            if phase.status == PhaseStatus.COMPLETED and phase.items_processed:
                # Show items stats for completed phases
                stats_parts = []
                for item_type, (completed, total) in phase.items_processed.items():
                    pct = (completed / total * 100) if total > 0 else 0
                    stats_parts.append(f"{item_type}: {completed}/{total}")
                if stats_parts:
                    print(f"  ({', '.join(stats_parts)})", end="")
            elif phase.current_step and phase.status == PhaseStatus.IN_PROGRESS:
                print(f"  ({phase.current_step})", end="")

            print()

        print()
        print("=" * 80)
        print("📈 LIVE STATISTICS")
        print("-" * 80)

        if self.live_metrics:
            # System metrics
            print(f"  ⏱️  Elapsed: {elapsed_str:>12s} | "
                  f"💾 Memory: {self.live_metrics.memory_mb:6.1f} MB ({self.live_metrics.memory_percent:5.1f}%) | "
                  f"🔥 CPU: {self.live_metrics.cpu_percent:5.1f}%")

            print(f"  🔄 Neo4j Queries: {self.live_metrics.neo4j_queries:>6d} | "
                  f"🔍 Qdrant Queries: {self.live_metrics.qdrant_queries:>6d} | "
                  f"🚀 Tokens Used: {self.live_metrics.tokens_used:>8d}")

        # Overall progress
        completed_phases = sum(1 for p in self.phases.values() if p.status == PhaseStatus.COMPLETED)
        total_phases = len(self.PHASES)
        overall_progress = completed_phases / total_phases if total_phases > 0 else 0

        print()
        print(f"  📊 Overall Progress: {self._render_progress_bar(overall_progress, width=25)}")
        print(f"     {completed_phases}/{total_phases} phases completed")

        # Estimate
        if completed_phases > 0 and elapsed > 0:
            avg_phase_time = elapsed / completed_phases
            remaining_phases = total_phases - completed_phases
            estimated_remaining = avg_phase_time * remaining_phases
            eta_time = datetime.now() + timedelta(seconds=estimated_remaining)
            estimated_total = elapsed + estimated_remaining

            print(f"  🕐 Estimated Total: {self._format_time(estimated_total):>12s} | "
                  f"ETA: {eta_time.strftime('%H:%M:%S')}")

        print()
        print("=" * 80)
        print()

        # Update last phase shown and mark that block was printed
        if active_phase:
            self.last_phase_shown = active_phase.name
        self.progress_block_printed = True

    def _format_time(self, seconds: float) -> str:
        """Format seconds to HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}h {minutes:02d}m {secs:02d}s"

    def get_summary(self) -> Dict:
        """Get summary of all phases"""
        summary = {}
        for phase_name, phase in self.phases.items():
            summary[phase_name] = {
                "status": phase.status.value,
                "progress": phase.progress,
                "duration_ms": phase.duration_ms,
                "errors": phase.errors,
                "items": phase.items_processed
            }
        return summary


# Convenience functions for easy integration
_tracker: Optional[ProgressTracker] = None


def get_tracker() -> ProgressTracker:
    """Get or create global tracker"""
    global _tracker
    if _tracker is None:
        _tracker = ProgressTracker()
    return _tracker


def start_phase(phase_name: str, substeps: int = 1):
    """Start a phase"""
    get_tracker().start_phase(phase_name, substeps)


def update_phase(phase_name: str, step: str = "", progress: Optional[float] = None):
    """Update phase progress"""
    get_tracker().update_phase(phase_name, step, progress)


def increment_step(phase_name: str, count: int = 1):
    """Increment substeps"""
    get_tracker().increment_step(phase_name, count)


def add_item(phase_name: str, item_type: str, completed: int, total: int):
    """Add item tracking"""
    get_tracker().add_item(phase_name, item_type, completed, total)


def complete_phase(phase_name: str, success: bool = True):
    """Complete a phase"""
    get_tracker().complete_phase(phase_name, success)


def add_error(phase_name: str):
    """Record error in phase"""
    get_tracker().add_error(phase_name)


def update_metrics(neo4j: int = 0, qdrant: int = 0, tokens: int = 0):
    """Update live metrics"""
    get_tracker().update_metrics(neo4j, qdrant, tokens)


def display_progress(clear: bool = True):
    """Display progress"""
    get_tracker().display(clear)
