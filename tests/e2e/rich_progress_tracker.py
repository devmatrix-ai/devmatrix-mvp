"""
Rich Progress Tracker for E2E Pipeline
Real-time animated visualization with Rich library
Works even when output is piped (force_terminal=True)
"""
import sys
import time
import threading
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.layout import Layout
from rich.text import Text
from rich.style import Style


class PhaseStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PhaseMetrics:
    name: str
    display_name: str = ""
    status: PhaseStatus = PhaseStatus.PENDING
    progress: float = 0.0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    current_step: str = ""
    substeps_completed: int = 0
    substeps_total: int = 0
    errors: int = 0
    items: Dict[str, Tuple[int, int]] = field(default_factory=dict)

    def __post_init__(self):
        if not self.display_name:
            self.display_name = self.name

    @property
    def duration_str(self) -> str:
        if not self.start_time:
            return "-"
        end = self.end_time or time.time()
        duration = end - self.start_time
        if duration < 60:
            return f"{duration:.1f}s"
        return f"{int(duration // 60)}m {int(duration % 60)}s"


class RichProgressTracker:
    """
    Real-time progress tracking with Rich library.
    Provides animated progress bars and live metrics.
    """

    # Phase names must match exactly what the pipeline uses in start_phase() calls
    PHASES = [
        ("Spec Ingestion", "1. Spec Ingestion"),
        ("Validation Scaling", "2. Validation Scaling"),
        ("Requirements Analysis", "3. Requirements Analysis"),
        ("Multi-Pass Planning", "4. Multi-Pass Planning"),
        ("Atomization", "5. Atomization"),
        ("DAG Construction", "6. DAG Construction"),
        ("Code Generation", "7. Code Generation"),
        ("Deployment", "8. Deployment"),
        ("Code Repair", "9. Code Repair"),
        ("Runtime Smoke Test", "10. Smoke Tests"),
        ("Validation", "11. Validation"),
        ("Health Verification", "12. Health Check"),
        ("Learning", "13. Learning"),
    ]

    STATUS_ICONS = {
        PhaseStatus.PENDING: ("⏳", "dim"),
        PhaseStatus.IN_PROGRESS: ("🔄", "yellow bold"),
        PhaseStatus.COMPLETED: ("✅", "green"),
        PhaseStatus.FAILED: ("❌", "red bold"),
    }

    def __init__(self, title: str = "E2E Pipeline", force_terminal: bool = True):
        self.title = title
        self.console = Console(force_terminal=force_terminal)
        self.phases: Dict[str, PhaseMetrics] = {
            key: PhaseMetrics(name=key, display_name=name)
            for key, name in self.PHASES
        }
        self.start_time = time.time()
        self.live: Optional[Live] = None
        self.metrics = {
            "files": 0,
            "loc": 0,
            "tokens": 0,
            "endpoints": 0,
            "tests_passed": 0,
            "tests_total": 0,
            "memory_mb": 0,
            "cpu_percent": 0,
        }
        self.activities: List[Tuple[str, str, str]] = []
        self._lock = threading.Lock()

    def start(self):
        """Start the live display"""
        self.start_time = time.time()
        self.live = Live(
            self._render(),
            console=self.console,
            refresh_per_second=4,
            transient=False
        )
        self.live.start()
        self._add_activity("🚀 Pipeline started", "green bold")

    def stop(self):
        """Stop the live display"""
        if self.live:
            self.live.stop()
            self.live = None

    def start_phase(self, phase_key: str, substeps: int = 1):
        """Mark phase as started"""
        with self._lock:
            if phase_key in self.phases:
                phase = self.phases[phase_key]
                phase.status = PhaseStatus.IN_PROGRESS
                phase.start_time = time.time()
                phase.substeps_total = substeps
                phase.substeps_completed = 0
                phase.progress = 0.0
                self._add_activity(f"▶️  Starting {phase.display_name}", "cyan")
                self._refresh()

    def update_phase(self, phase_key: str, step: str = "", progress: Optional[float] = None):
        """Update phase progress"""
        with self._lock:
            if phase_key in self.phases:
                phase = self.phases[phase_key]
                if step:
                    phase.current_step = step
                if progress is not None:
                    phase.progress = max(0.0, min(1.0, progress))
                elif phase.substeps_total > 0:
                    phase.progress = phase.substeps_completed / phase.substeps_total
                self._refresh()

    def increment_step(self, phase_key: str, count: int = 1):
        """Increment completed substeps"""
        with self._lock:
            if phase_key in self.phases:
                phase = self.phases[phase_key]
                phase.substeps_completed = min(
                    phase.substeps_total,
                    phase.substeps_completed + count
                )
                if phase.substeps_total > 0:
                    phase.progress = phase.substeps_completed / phase.substeps_total
                self._refresh()

    def complete_phase(self, phase_key: str, success: bool = True):
        """Mark phase as completed"""
        with self._lock:
            if phase_key in self.phases:
                phase = self.phases[phase_key]
                phase.status = PhaseStatus.COMPLETED if success else PhaseStatus.FAILED
                phase.end_time = time.time()
                phase.progress = 1.0 if success else phase.progress
                icon = "✅" if success else "❌"
                style = "green" if success else "red"
                self._add_activity(f"{icon} {phase.display_name} ({phase.duration_str})", style)
                self._refresh()

    def add_error(self, phase_key: str, message: str = ""):
        """Record an error"""
        with self._lock:
            if phase_key in self.phases:
                self.phases[phase_key].errors += 1
            if message:
                self._add_activity(f"⚠️  {message}", "yellow")
            self._refresh()

    def update_metrics(self, **kwargs):
        """Update metrics (files, loc, tokens, endpoints, etc)"""
        with self._lock:
            self.metrics.update(kwargs)
            if PSUTIL_AVAILABLE:
                try:
                    process = psutil.Process()
                    self.metrics["memory_mb"] = process.memory_info().rss / 1024 / 1024
                    self.metrics["cpu_percent"] = process.cpu_percent(interval=0)
                except:
                    pass
            self._refresh()

    def add_item(self, phase_key: str, item_type: str, completed: int, total: int):
        """Track specific items"""
        with self._lock:
            if phase_key in self.phases:
                self.phases[phase_key].items[item_type] = (completed, total)
            self._refresh()

    def _add_activity(self, message: str, style: str = "white"):
        """Add activity to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.activities.append((timestamp, message, style))
        # Keep only last 10 activities
        if len(self.activities) > 10:
            self.activities = self.activities[-10:]

    def _refresh(self):
        """Refresh the display"""
        if self.live:
            self.live.update(self._render())

    def _render(self) -> Layout:
        """Render the full layout"""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )
        layout["body"].split_row(
            Layout(name="phases", ratio=2),
            Layout(name="sidebar", ratio=1),
        )
        layout["sidebar"].split_column(
            Layout(name="metrics"),
            Layout(name="activity"),
        )

        # Header
        elapsed = time.time() - self.start_time
        elapsed_str = f"{int(elapsed // 60)}:{int(elapsed % 60):02d}"
        header = Text()
        header.append("🏗️  ", style="bold")
        header.append(self.title, style="bold magenta")
        header.append(f"  |  ⏱️  {elapsed_str}", style="cyan")
        layout["header"].update(Panel(header, style="bold"))

        # Phases table
        layout["phases"].update(self._render_phases_table())

        # Metrics
        layout["metrics"].update(self._render_metrics_panel())

        # Activity
        layout["activity"].update(self._render_activity_panel())

        # Footer
        completed = sum(1 for p in self.phases.values() if p.status == PhaseStatus.COMPLETED)
        total = len(self.phases)
        overall = completed / total if total > 0 else 0
        footer = Text()
        footer.append(f"Overall: ", style="dim")
        footer.append(f"{'█' * int(overall * 20)}{'░' * (20 - int(overall * 20))}", style="cyan")
        footer.append(f" {int(overall * 100)}%", style="bold cyan")
        footer.append(f"  |  {completed}/{total} phases", style="dim")
        layout["footer"].update(Panel(footer))

        return layout

    def _render_phases_table(self) -> Table:
        """Render phases table"""
        table = Table(
            title="Pipeline Phases",
            show_header=True,
            header_style="bold magenta",
            expand=True
        )
        table.add_column("Phase", style="cyan", width=25)
        table.add_column("Status", justify="center", width=10)
        table.add_column("Progress", width=25)
        table.add_column("Time", justify="right", width=8)
        table.add_column("Info", style="dim", width=20)

        for phase_key, _ in self.PHASES:
            phase = self.phases[phase_key]
            icon, style = self.STATUS_ICONS[phase.status]

            # Progress bar
            filled = int(phase.progress * 15)
            bar = f"[{'cyan' if phase.status == PhaseStatus.IN_PROGRESS else 'green' if phase.status == PhaseStatus.COMPLETED else 'dim'}]"
            bar += "█" * filled + "░" * (15 - filled)
            bar += f"[/] {int(phase.progress * 100):3d}%"

            # Info column
            info = ""
            if phase.current_step and phase.status == PhaseStatus.IN_PROGRESS:
                info = phase.current_step[:18] + "..." if len(phase.current_step) > 20 else phase.current_step
            elif phase.items:
                parts = [f"{k}:{v[0]}/{v[1]}" for k, v in list(phase.items.items())[:2]]
                info = ", ".join(parts)

            table.add_row(
                phase.display_name,
                f"{icon}",
                bar,
                phase.duration_str,
                info,
                style=style if phase.status != PhaseStatus.PENDING else "dim"
            )

        return table

    def _render_metrics_panel(self) -> Panel:
        """Render metrics panel"""
        content = Text()
        content.append("📊 Metrics\n\n", style="bold")
        content.append(f"  📁 Files: ", style="dim")
        content.append(f"{self.metrics.get('files', 0)}\n", style="cyan")
        content.append(f"  📝 LOC: ", style="dim")
        content.append(f"{self.metrics.get('loc', 0):,}\n", style="cyan")
        content.append(f"  🎯 Endpoints: ", style="dim")
        content.append(f"{self.metrics.get('endpoints', 0)}\n", style="green")
        content.append(f"  🔤 Tokens: ", style="dim")
        content.append(f"{self.metrics.get('tokens', 0):,}\n", style="yellow")
        content.append(f"\n  💾 Memory: ", style="dim")
        content.append(f"{self.metrics.get('memory_mb', 0):.0f} MB\n", style="magenta")

        return Panel(content, title="[blue]Stats[/]", border_style="blue")

    def _render_activity_panel(self) -> Panel:
        """Render activity panel"""
        content = Text()
        for timestamp, message, style in self.activities[-6:]:
            content.append(f"[{timestamp}] ", style="dim")
            content.append(f"{message}\n", style=style)

        return Panel(content, title="[green]Activity[/]", border_style="green")

    def print_summary(self):
        """Print final summary after stopping"""
        elapsed = time.time() - self.start_time
        completed = sum(1 for p in self.phases.values() if p.status == PhaseStatus.COMPLETED)
        failed = sum(1 for p in self.phases.values() if p.status == PhaseStatus.FAILED)

        self.console.print()
        self.console.print(Panel.fit(
            f"[bold {'green' if failed == 0 else 'red'}]"
            f"{'✅ Pipeline Completed!' if failed == 0 else '❌ Pipeline Failed!'}"
            f"[/]\n\n"
            f"📁 Files: {self.metrics.get('files', 0)} | "
            f"📝 LOC: {self.metrics.get('loc', 0):,} | "
            f"🎯 Endpoints: {self.metrics.get('endpoints', 0)}\n"
            f"🧪 Tests: {self.metrics.get('tests_passed', 0)}/{self.metrics.get('tests_total', 0)} | "
            f"⏱️  Time: {int(elapsed // 60)}m {int(elapsed % 60)}s\n"
            f"✅ Phases: {completed}/{len(self.phases)} | "
            f"❌ Failed: {failed}",
            title="Summary",
            border_style="green" if failed == 0 else "red"
        ))


# Global tracker instance
_tracker: Optional[RichProgressTracker] = None


def get_tracker() -> RichProgressTracker:
    """Get or create global tracker"""
    global _tracker
    if _tracker is None:
        _tracker = RichProgressTracker()
    return _tracker


def start_tracking(title: str = "E2E Pipeline"):
    """Start tracking with optional title"""
    global _tracker
    _tracker = RichProgressTracker(title=title)
    _tracker.start()
    return _tracker


def stop_tracking():
    """Stop tracking and print summary"""
    if _tracker:
        _tracker.stop()
        _tracker.print_summary()


# Compatibility functions (same interface as old progress_tracker)
def start_phase(phase_name: str, substeps: int = 1):
    get_tracker().start_phase(phase_name, substeps)


def update_phase(phase_name: str, step: str = "", progress: Optional[float] = None):
    get_tracker().update_phase(phase_name, step, progress)


def increment_step(phase_name: str, count: int = 1):
    get_tracker().increment_step(phase_name, count)


def complete_phase(phase_name: str, success: bool = True):
    get_tracker().complete_phase(phase_name, success)


def add_error(phase_name: str, message: str = ""):
    get_tracker().add_error(phase_name, message)


def update_metrics(**kwargs):
    get_tracker().update_metrics(**kwargs)


def add_item(phase_name: str, item_type: str, completed: int, total: int):
    get_tracker().add_item(phase_name, item_type, completed, total)


def display_progress(clear: bool = True):
    """Compatibility - Rich handles refresh automatically"""
    pass  # No-op, Rich Live handles this


if __name__ == "__main__":
    import asyncio

    async def demo():
        tracker = start_tracking("Demo Pipeline")

        for phase_key, phase_name in RichProgressTracker.PHASES:
            tracker.start_phase(phase_key, substeps=5)

            for i in range(5):
                tracker.update_phase(phase_key, step=f"Step {i + 1}/5")
                tracker.increment_step(phase_key)
                tracker.update_metrics(
                    files=tracker.metrics["files"] + 1,
                    loc=tracker.metrics["loc"] + 50,
                    tokens=tracker.metrics["tokens"] + 100,
                )
                await asyncio.sleep(0.2)

            tracker.complete_phase(phase_key, success=True)

        stop_tracking()

    asyncio.run(demo())
