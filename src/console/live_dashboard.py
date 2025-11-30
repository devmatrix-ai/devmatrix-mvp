"""Rich-powered live dashboard for DevMatrix pipeline execution.

This replaces the ad-hoc test dashboard with a focused, professional
console view that surfaces:
- Phase progress with status and elapsed time
- Key metrics (tests, LLM tokens/cost, compliance, errors)
- Infra/agent health signals
- Live log tail for debugging

API is intentionally small and matches what the CLI already expects:
    - update(): returns a Rich renderable for Live()
    - set_status(), set_current_task()
    - update_phase()
    - update_metrics()
    - add_log()
    - update_infra_status()
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


# Default phase catalog aligned with real_e2e_full_pipeline.py phases
DEFAULT_PHASES: Dict[int, str] = {
    1: "Spec Ingestion",
    2: "Validation Scaling",
    3: "Requirements Analysis",
    4: "Multi-Pass Planning",
    5: "Atomization",
    6: "DAG Construction",
    7: "Code Generation",
    8: "Deployment",
    9: "Code Repair",
    10: "Runtime Smoke Test",
    11: "Validation",
    12: "Health Verification",
    13: "Learning",
}


STATUS_ICON = {
    "pending": "⏳",
    "running": "🔵",
    "completed": "✅",
    "failed": "❌",
    "skipped": "⊘",
    "warning": "⚠️",
}

STATUS_COLOR = {
    "pending": "yellow",
    "running": "blue",
    "completed": "green",
    "failed": "red",
    "skipped": "grey54",
    "warning": "yellow",
}

LOG_COLOR = {
    "info": "white",
    "success": "green",
    "warning": "yellow",
    "error": "red",
}


@dataclass
class PhaseState:
    """Mutable state for a pipeline phase."""

    name: str
    total: int = 1
    progress: int = 0
    status: str = "pending"
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    checkpoints_completed: int = 0
    checkpoints_total: int = 0

    def as_percent(self) -> float:
        if self.total <= 0:
            return 0.0
        return min(max(self.progress / self.total, 0.0), 1.0)

    def duration_ms(self) -> int:
        if self.started_at and self.ended_at:
            return int((self.ended_at - self.started_at) * 1000)
        if self.started_at:
            return int((time.time() - self.started_at) * 1000)
        return 0


class LiveDashboard:
    """Live terminal dashboard with Rich."""

    def __init__(self, console: Optional[Console] = None, spec_name: str = "Pipeline Execution"):
        self.console = console or Console()
        self.spec_name = spec_name
        self.status = "running"
        self.current_task = "Awaiting events..."
        self.started_at = time.time()

        # Phase state keyed by phase number
        self.phases: Dict[int, PhaseState] = {
            num: PhaseState(name=title, total=1, progress=0, status="pending")
            for num, title in DEFAULT_PHASES.items()
        }

        # Metrics snapshot (numbers are defaults, updated as data arrives)
        self.metrics: Dict[str, Any] = {
            "tests_passed": 0,
            "tests_failed": 0,
            "test_pass_rate": 0.0,
            "ir_compliance": 0.0,
            "pipeline_precision": 0.0,
            "pattern_f1": 0.0,
            "llm_tokens": 0,
            "llm_cost": 0.0,
            "duration_ms": 0,
            "errors": 0,
            "artifacts": 0,
        }

        # Infra/agent health
        self.infra: Dict[str, Dict[str, str]] = {
            "docker": {"status": "unknown", "detail": ""},
            "neo4j": {"status": "unknown", "detail": ""},
            "qdrant": {"status": "unknown", "detail": ""},
            "redis": {"status": "unknown", "detail": ""},
        }

        # Rolling log buffer
        self.logs: List[Dict[str, str]] = []
        self.max_logs = 30

    # ------------------------------------------------------------------ API --
    def set_status(self, status: str) -> None:
        self.status = status
        if status in ("completed", "failed") and not self.metrics.get("duration_ms"):
            self.metrics["duration_ms"] = int((time.time() - self.started_at) * 1000)

    def set_current_task(self, task: str) -> None:
        self.current_task = task

    def update_phase(self, phase_num: int, progress: Optional[int] = None, status: Optional[str] = None) -> None:
        """Update a phase by number, creating it if not present."""
        if phase_num not in self.phases:
            self.phases[phase_num] = PhaseState(name=f"Phase {phase_num}")

        phase = self.phases[phase_num]
        if phase.started_at is None and status == "running":
            phase.started_at = time.time()
        if progress is not None:
            phase.progress = progress
        if status:
            phase.status = status
            if status in ("completed", "failed", "skipped"):
                phase.ended_at = time.time()

    def update_metrics(self, **kwargs: Any) -> None:
        self.metrics.update(kwargs)

    def add_log(self, message: str, level: str = "info") -> None:
        self.logs.append(
            {
                "ts": datetime.now().strftime("%H:%M:%S"),
                "level": level,
                "message": message,
            }
        )
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs :]

    def update_infra_status(self, name: str, status: str, detail: str = "") -> None:
        self.infra[name] = {"status": status, "detail": detail}

    def update(self):
        """Render the full dashboard layout (for Live.update)."""
        layout = Layout(name="root")
        layout.split(
            Layout(name="header", size=5),
            Layout(name="body", ratio=2),
            Layout(name="footer", size=10),
        )

        layout["body"].split_row(
            Layout(name="progress", ratio=2),
            Layout(name="side", ratio=1),
        )

        layout["progress"].split(
            Layout(name="phases", ratio=3),
            Layout(name="current", size=4),
        )

        layout["side"].split(
            Layout(name="metrics", ratio=2),
            Layout(name="infra", ratio=1),
        )

        layout["footer"].split(Layout(name="logs"))

        layout["header"].update(self._render_header())
        layout["phases"].update(self._render_phases())
        layout["current"].update(self._render_current())
        layout["metrics"].update(self._render_metrics())
        layout["infra"].update(self._render_infra())
        layout["logs"].update(self._render_logs())

        return layout

    # ----------------------------------------------------------- RENDERING --
    def _render_header(self) -> Panel:
        elapsed_ms = int((time.time() - self.started_at) * 1000)
        status_icon = STATUS_ICON.get(self.status, "❓")
        status_color = STATUS_COLOR.get(self.status, "white")

        text = Text()
        text.append(f"{status_icon} DevMatrix Pipeline\n", style=f"bold {status_color}")
        text.append(f"Spec: {self.spec_name}\n", style="cyan")
        text.append(f"Status: {self.status}\n", style=status_color)
        text.append(f"Elapsed: {self._format_ms(elapsed_ms)}", style="white")

        return Panel(Align.center(text), border_style="cyan", padding=(0, 1))

    def _render_phases(self) -> Panel:
        table = Table(
            title="Phase Progress",
            show_header=True,
            header_style="bold cyan",
            box=box.SIMPLE_HEAVY,
            expand=True,
        )
        table.add_column("#", width=3)
        table.add_column("Phase", style="white", min_width=18)
        table.add_column("Status", justify="center", width=10)
        table.add_column("Progress", justify="center", min_width=20)
        table.add_column("ETA/Time", justify="right", width=10)

        for num in sorted(self.phases.keys()):
            phase = self.phases[num]
            percent = phase.as_percent()
            icon = STATUS_ICON.get(phase.status, "❓")
            color = STATUS_COLOR.get(phase.status, "white")
            bar = self._progress_bar(percent)
            duration = phase.duration_ms()
            duration_str = self._format_ms(duration) if duration else "--"

            table.add_row(
                str(num),
                phase.name,
                f"[{color}]{icon} {phase.status}[/{color}]",
                bar,
                duration_str,
            )

        overall = f"[bold]Overall:[/bold] {self._progress_bar(self._overall_progress())}"
        return Panel(Group(table, Text(overall, style="bold yellow")), border_style="green")

    def _render_current(self) -> Panel:
        body = Text()
        body.append("Now: ", style="dim")
        body.append(self.current_task or "Idle", style="white")
        body.append("\n\n")
        body.append("Next actions:\n", style="dim")
        body.append("- Use /approve to handle pending ops\n", style="white")
        body.append("- Watch infra panel for offline services\n", style="white")
        return Panel(body, title="Live Context", border_style="blue")

    def _render_metrics(self) -> Panel:
        table = Table.grid(padding=(0, 1))
        table.add_column(justify="left", no_wrap=True)
        table.add_column(justify="right")

        metrics = self.metrics
        table.add_row("Tests", f"{metrics.get('tests_passed', 0)}/{metrics.get('tests_failed', 0) + metrics.get('tests_passed', 0)}")
        table.add_row("Test Pass Rate", f"{metrics.get('test_pass_rate', 0.0):.1%}")
        table.add_row("IR Compliance", f"{metrics.get('ir_compliance', 0.0):.1%}")
        table.add_row("Pipeline Precision", f"{metrics.get('pipeline_precision', 0.0):.1%}")
        table.add_row("Pattern F1", f"{metrics.get('pattern_f1', 0.0):.1%}")
        table.add_row("LLM Tokens", f"{metrics.get('llm_tokens', 0):,}")
        table.add_row("LLM Cost", f"${metrics.get('llm_cost', 0.0):.3f}")
        table.add_row("Artifacts", str(metrics.get("artifacts", 0)))
        table.add_row("Errors", str(metrics.get("errors", 0)))
        table.add_row("Elapsed", self._format_ms(metrics.get("duration_ms", 0) or int((time.time() - self.started_at) * 1000)))

        return Panel(table, title="Metrics & Quality", border_style="magenta")

    def _render_infra(self) -> Panel:
        table = Table.grid(expand=True)
        table.add_column("Service", style="cyan", no_wrap=True)
        table.add_column("Status", justify="right")
        for name, state in self.infra.items():
            status = state.get("status", "unknown")
            detail = state.get("detail", "")
            color = {
                "ok": "green",
                "running": "green",
                "degraded": "yellow",
                "offline": "red",
                "unknown": "grey54",
            }.get(status, "grey54")
            label = f"[{color}]{status}[/{color}]"
            if detail:
                label += f" ({detail})"
            table.add_row(name.capitalize(), label)
        return Panel(table, title="Infra / Agents", border_style="yellow")

    def _render_logs(self) -> Panel:
        if not self.logs:
            return Panel("Waiting for events...", title="Event Stream", border_style="white")

        table = Table(
            show_header=True,
            header_style="dim",
            expand=True,
            box=box.MINIMAL,
        )
        table.add_column("Time", width=8)
        table.add_column("Level", width=8)
        table.add_column("Message", overflow="fold")

        for log in self.logs[-15:]:
            level = log["level"]
            color = LOG_COLOR.get(level, "white")
            table.add_row(log["ts"], f"[{color}]{level}[/]", log["message"])

        return Panel(table, title="Event Stream", border_style="white")

    # ------------------------------------------------------------ HELPERS --
    def _overall_progress(self) -> float:
        if not self.phases:
            return 0.0
        percents = [p.as_percent() for p in self.phases.values()]
        return sum(percents) / len(percents)

    @staticmethod
    def _progress_bar(percent: float, width: int = 24) -> str:
        percent = max(0.0, min(percent, 1.0))
        filled = int(percent * width)
        bar = "█" * filled + "░" * (width - filled)
        return f"[white]{bar}[/] {percent*100:5.1f}%"

    @staticmethod
    def _format_ms(ms: int) -> str:
        if ms <= 0:
            return "--"
        seconds = ms / 1000
        if seconds < 60:
            return f"{seconds:.1f}s"
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes}m {seconds:02d}s"

