"""
Dashboard Renderer - Generates Rich renderables from DashboardState.

Uses Rich components: Panel, Table, Layout, Progress, Text.
Reference: DOCS/mvp/exit/anti/PRO_DASHBOARD_IMPLEMENTATION_PLAN.md Task 2
"""
from rich.console import Console, Group
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn
from rich.table import Table
from rich.text import Text
from typing import Optional

from src.console.dashboard_state import (
    DashboardState, PhaseState, PhaseStatus, MetricsState, LogLevel
)


# Spinner frames for animated phase
SPINNER_FRAMES = ["◐", "◓", "◑", "◒"]


class DashboardRenderer:
    """Renders DashboardState to Rich components."""
    
    def __init__(self, state: DashboardState):
        self.state = state
        self._spinner_index = 0
        
    def render(self) -> Panel:
        """Render complete dashboard as a Panel."""
        # Build layout with 3 zones
        layout = Layout()
        layout.split_column(
            Layout(name="hero", size=5),
            Layout(name="metrics", size=3),
            Layout(name="logs", size=7),
        )
        
        layout["hero"].update(self._render_hero())
        layout["metrics"].update(self._render_metrics())
        layout["logs"].update(self._render_logs())
        
        return Panel(
            layout,
            title="[bold blue]DevMatrix Pipeline[/]",
            border_style="blue",
        )
    
    def tick(self):
        """Advance spinner animation."""
        self._spinner_index = (self._spinner_index + 1) % len(SPINNER_FRAMES)
    
    def _render_hero(self) -> Panel:
        """Render ZONE 1: Current phase hero."""
        phase = self.state.current_phase
        
        if phase is None:
            if self.state.final_status == "SUCCESS":
                return self._render_hero_success()
            elif self.state.final_status == "FAILED":
                return self._render_hero_failed()
            return Panel("[dim]Waiting to start...[/]", title="Phase")
        
        # Phase status icon
        icon = self._get_phase_icon(phase.status)
        color = self._get_status_color(phase.status)
        
        # Progress bar
        progress_pct = int(phase.progress * 100)
        bar_width = 50
        filled = int(bar_width * phase.progress)
        bar = "█" * filled + "░" * (bar_width - filled)
        
        # Time
        elapsed = f"{phase.elapsed_seconds:.1f}s"
        
        # Phase number
        phase_num = f"Phase {self.state.current_phase_index + 1}/{self.state.total_phases}"
        
        # Build text
        lines = [
            Text.assemble(
                (f"{icon} ", color),
                (phase.name, f"bold {color}"),
                ("  " + " " * (40 - len(phase.name)), ""),
                (phase_num, "dim"),
            ),
            Text.assemble(
                (bar, color),
                (f"  {progress_pct}%  {elapsed}", "dim"),
            ),
            Text(phase.message or "Processing...", style="dim italic"),
        ]
        
        return Panel(Group(*lines), border_style=color)
    
    def _render_hero_success(self) -> Panel:
        """Render success state."""
        elapsed = f"{self.state.total_elapsed_seconds:.1f}s"
        lines = [
            Text("✓ Pipeline Complete", style="bold green"),
            Text("█" * 50 + f"  100%  {elapsed}", style="green"),
            Text(f"All {self.state.total_phases} phases completed successfully", style="dim"),
        ]
        return Panel(Group(*lines), border_style="green", title="[green]SUCCESS[/]")
    
    def _render_hero_failed(self) -> Panel:
        """Render failed state."""
        lines = [
            Text("✗ Pipeline Failed", style="bold red"),
            Text("Check logs for details", style="dim"),
        ]
        return Panel(Group(*lines), border_style="red", title="[red]FAILED[/]")
    
    def _render_metrics(self) -> Table:
        """Render ZONE 2: Metrics cards."""
        m = self.state.metrics
        
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Tests", width=15)
        table.add_column("Compliance", width=15)
        table.add_column("LLM", width=15)
        table.add_column("Repair", width=15)
        
        # Tests card
        tests_color = "green" if m.tests_passed == m.tests_total else "yellow"
        if m.tests_total > 0 and m.tests_passed / m.tests_total < 0.8:
            tests_color = "red"
        tests = f"[{tests_color}]{m.tests_passed}/{m.tests_total}[/]"
        
        # Compliance card  
        comp_color = "green" if m.compliance_percent >= 95 else "yellow" if m.compliance_percent >= 80 else "red"
        comp = f"[{comp_color}]{m.compliance_percent:.1f}%[/]"
        
        # LLM card
        llm = f"${m.llm_cost:.2f}  {m.llm_tokens//1000}K"
        
        # Repair card
        repair = self._render_repair_indicator(m)
        
        table.add_row(
            f"[bold]Tests[/]\n{tests}",
            f"[bold]Compliance[/]\n{comp}",
            f"[bold]LLM[/]\n{llm}",
            f"[bold]Repair[/]\n{repair}",
        )
        
        return table
    
    def _render_repair_indicator(self, m: MetricsState) -> str:
        """Render repair loop indicator ●○○."""
        if m.repair_status == "skip":
            return "[dim]○○○ SKIP[/]"

        dots = ""
        for i in range(m.repair_max):
            if i < m.repair_iteration:
                if m.repair_status == "failed" and i == m.repair_iteration - 1:
                    dots += "[red]●[/]"
                elif m.repair_status == "completed":
                    dots += "[green]●[/]"
                else:
                    dots += "[blue]●[/]"
            else:
                dots += "[dim]○[/]"

        return f"{dots} {m.repair_iteration}/{m.repair_max}"

    def _render_logs(self) -> Panel:
        """Render ZONE 3: Log entries."""
        if not self.state.logs:
            return Panel("[dim]No logs yet...[/]", title="Logs", border_style="dim")

        lines = []
        for entry in reversed(self.state.logs):  # Most recent first
            timestamp = entry.timestamp.strftime("%H:%M:%S")
            icon = entry.icon
            color = entry.color

            line = Text.assemble(
                (timestamp, "dim"),
                " ",
                (icon, color),
                " ",
                (entry.message[:70], color if entry.level != LogLevel.INFO else "white"),
            )
            lines.append(line)

        return Panel(Group(*lines), title="[dim]Logs[/]", border_style="dim")

    def _get_phase_icon(self, status: PhaseStatus) -> str:
        """Get icon for phase status."""
        if status == PhaseStatus.RUNNING:
            return SPINNER_FRAMES[self._spinner_index]
        icons = {
            PhaseStatus.PENDING: "⏳",
            PhaseStatus.COMPLETED: "✓",
            PhaseStatus.FAILED: "✗",
            PhaseStatus.SKIPPED: "⊘",
        }
        return icons.get(status, "?")

    def _get_status_color(self, status: PhaseStatus) -> str:
        """Get Rich color for phase status."""
        colors = {
            PhaseStatus.PENDING: "dim",
            PhaseStatus.RUNNING: "blue",
            PhaseStatus.COMPLETED: "green",
            PhaseStatus.FAILED: "red",
            PhaseStatus.SKIPPED: "dim",
        }
        return colors.get(status, "white")

