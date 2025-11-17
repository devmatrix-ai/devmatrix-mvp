"""Beautiful masterplan visualization with Rich and ASCII art."""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.progress import Progress, BarColumn, TextColumn
from rich.box import ROUNDED
from rich import print as rprint


@dataclass
class Phase:
    """Represents a pipeline phase."""

    number: int
    name: str
    task_count: int
    completed: int = 0
    emoji: str = "⏳"


@dataclass
class Task:
    """Represents a task in the masterplan."""

    id: str
    name: str
    phase: int
    phase_name: str
    status: str  # pending, in_progress, completed, failed
    estimated_duration_ms: int = 0
    dependencies: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

    @property
    def status_emoji(self) -> str:
        """Get emoji for task status."""
        emojis = {
            "pending": "⏳",
            "in_progress": "🔄",
            "completed": "✅",
            "failed": "❌",
        }
        return emojis.get(self.status, "❓")


@dataclass
class MasterPlan:
    """Represents a complete masterplan."""

    execution_id: str
    total_tasks: int
    phases: List[Phase]
    tasks: List[Task]
    created_at: str = ""
    estimated_total_duration_ms: float = 0
    total_tokens_estimated: int = 0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class PlanVisualizer:
    """Visualizes masterplans with Rich formatting."""

    # Motivational messages for different completion percentages
    MOTIVATIONAL_MESSAGES = {
        0: "🚀 Let's build something amazing!",
        25: "💪 You're on fire!",
        50: "🎯 Halfway there! Keep going!",
        75: "⚡ Almost done! The finish line is near!",
        100: "🏆 LEGENDARY! You've completed it all!",
    }

    # Funny phase-specific messages
    PHASE_MESSAGES = {
        0: "🔍 Discovery: Poking around to understand what's needed",
        1: "📊 Analysis: Making sense of all those notes",
        2: "📝 Planning: Drawing boxes and arrows (the fun part)",
        3: "⚙️  Execution: The actual hard work begins",
        4: "🧪 Validation: Please tell me it works...",
    }

    def __init__(self, console: Optional[Console] = None):
        """Initialize visualizer."""
        self.console = console or Console()

    def motivational_message(self, completion_percent: int) -> str:
        """Get motivational message based on completion."""
        if completion_percent >= 100:
            return self.MOTIVATIONAL_MESSAGES[100]
        elif completion_percent >= 75:
            return self.MOTIVATIONAL_MESSAGES[75]
        elif completion_percent >= 50:
            return self.MOTIVATIONAL_MESSAGES[50]
        elif completion_percent >= 25:
            return self.MOTIVATIONAL_MESSAGES[25]
        else:
            return self.MOTIVATIONAL_MESSAGES[0]

    def phase_message(self, phase_number: int) -> str:
        """Get funny message for phase."""
        return self.PHASE_MESSAGES.get(phase_number, "🔧 Working hard...")

    def show_masterplan_overview(self, plan: MasterPlan) -> None:
        """Show high-level overview of masterplan."""
        completion = (sum(p.completed for p in plan.phases) / plan.total_tasks) * 100

        # Header
        header = f"[bold cyan]📋 MASTERPLAN: {plan.execution_id}[/bold cyan]"
        self.console.print(header)
        self.console.print()

        # Quick stats
        stats_table = Table(title="Quick Stats", box=ROUNDED, show_header=False)
        stats_table.add_row("📌 Total Tasks", f"[cyan]{plan.total_tasks}[/cyan]")
        stats_table.add_row("⏱️  Est. Duration", f"[yellow]{plan.estimated_total_duration_ms/1000:.1f}s[/yellow]")
        stats_table.add_row(
            "🔌 Est. Tokens", f"[magenta]{plan.total_tokens_estimated:,}[/magenta]"
        )
        stats_table.add_row(
            "📈 Progress", f"[green]{completion:.1f}%[/green]"
        )
        self.console.print(stats_table)
        self.console.print()

        # Overall progress bar
        self._print_progress_bar(completion, 50)
        self.console.print()

        # Motivational message
        msg = self.motivational_message(int(completion))
        self.console.print(f"[bold yellow]{msg}[/bold yellow]")
        self.console.print()

    def show_phases_timeline(self, plan: MasterPlan) -> None:
        """Show timeline of phases with progress."""
        self.console.print("[bold cyan]═══ 📊 PHASES TIMELINE ═══[/bold cyan]")
        self.console.print()

        for phase in plan.phases:
            completion = (phase.completed / phase.task_count * 100) if phase.task_count > 0 else 0

            # Phase header
            phase_emoji = "✅" if completion == 100 else "🔄" if completion > 0 else "⏳"
            phase_line = (
                f"{phase_emoji} [bold]{phase.name:<12}[/bold] "
                f"({phase.completed}/{phase.task_count} tasks)"
            )
            self.console.print(phase_line)

            # Progress bar
            self._print_progress_bar(completion, 40, show_percent=True)

            # Funny message
            if completion == 0:
                self.console.print(f"   {self.phase_message(phase.number)}", style="dim")

            self.console.print()

    def show_tasks_table(self, plan: MasterPlan, max_rows: int = 20) -> None:
        """Show tasks in a formatted table."""
        self.console.print("[bold cyan]═══ 📋 TASKS ═══[/bold cyan]")
        self.console.print()

        # Group by phase
        tasks_by_phase = {}
        for task in plan.tasks:
            if task.phase not in tasks_by_phase:
                tasks_by_phase[task.phase] = []
            tasks_by_phase[task.phase].append(task)

        # Show table for each phase
        for phase_num in sorted(tasks_by_phase.keys()):
            tasks = tasks_by_phase[phase_num]
            phase = next((p for p in plan.phases if p.number == phase_num), None)
            if not phase:
                continue

            # Phase header
            self.console.print(f"[bold magenta]▶ {phase.name}[/bold magenta]")

            # Task table
            table = Table(
                title=f"{len(tasks)} tasks",
                box=ROUNDED,
                show_header=True,
                header_style="bold cyan",
            )
            table.add_column("Status", width=6)
            table.add_column("Task", width=40)
            table.add_column("Duration", width=10, justify="right")
            table.add_column("Deps", width=6, justify="center")

            for task in tasks[:max_rows]:
                deps_count = len(task.dependencies) if task.dependencies else 0
                deps_str = f"[dim]{deps_count}[/dim]" if deps_count > 0 else "—"
                duration_str = f"{task.estimated_duration_ms/1000:.1f}s" if task.estimated_duration_ms else "—"

                table.add_row(
                    task.status_emoji,
                    f"[white]{task.name}[/white]",
                    f"[yellow]{duration_str}[/yellow]",
                    deps_str,
                )

            self.console.print(table)
            self.console.print()

    def show_dependencies_graph(self, plan: MasterPlan, max_depth: int = 3) -> None:
        """Show dependency graph as ASCII tree."""
        self.console.print("[bold cyan]═══ 🔗 DEPENDENCY GRAPH ═══[/bold cyan]")
        self.console.print()

        # Find root tasks (no dependencies)
        root_tasks = [t for t in plan.tasks if not t.dependencies or len(t.dependencies) == 0]

        if not root_tasks:
            self.console.print("[dim]No root tasks found (all have dependencies)[/dim]")
            return

        # Build tree
        tree = Tree("[bold]Entry Points[/bold]", guide_style="dim")

        for task in root_tasks[:5]:  # Show first 5 root tasks
            self._add_to_tree(tree, task, plan.tasks, depth=0, max_depth=max_depth)

        self.console.print(tree)
        self.console.print()

    def _add_to_tree(
        self,
        tree: Tree,
        task: Task,
        all_tasks: List[Task],
        depth: int = 0,
        max_depth: int = 3,
    ) -> None:
        """Recursively add tasks to dependency tree."""
        if depth > max_depth:
            return

        # Find dependent tasks
        dependent_tasks = [
            t for t in all_tasks
            if t.dependencies and task.id in t.dependencies
        ]

        # Add current task
        task_line = f"{task.status_emoji} {task.name} [{task.phase_name}]"
        if not dependent_tasks:
            tree.label = task_line
            return

        # Add dependents
        subtree = tree.add(task_line)
        for dep_task in dependent_tasks[:3]:  # Limit dependents shown
            self._add_to_tree(subtree, dep_task, all_tasks, depth + 1, max_depth)

    def show_statistics(self, plan: MasterPlan) -> None:
        """Show detailed statistics about the masterplan."""
        self.console.print("[bold cyan]═══ 📊 STATISTICS ═══[/bold cyan]")
        self.console.print()

        # Calculate stats
        total_completed = sum(p.completed for p in plan.phases)
        total_in_progress = sum(1 for t in plan.tasks if t.status == "in_progress")
        total_failed = sum(1 for t in plan.tasks if t.status == "failed")
        avg_duration = (
            sum(t.estimated_duration_ms for t in plan.tasks) / len(plan.tasks)
            if plan.tasks
            else 0
        )

        # Stats table
        table = Table(box=ROUNDED, show_header=False)
        table.add_row("[yellow]Completed[/yellow]", f"[green]{total_completed}/{plan.total_tasks}[/green]")
        table.add_row("[cyan]In Progress[/cyan]", f"[blue]{total_in_progress}[/blue]")
        table.add_row("[red]Failed[/red]", f"[bright_red]{total_failed}[/bright_red]")
        table.add_row(
            "[magenta]Avg Duration[/magenta]",
            f"[yellow]{avg_duration/1000:.2f}s[/yellow]",
        )
        table.add_row(
            "[magenta]Total Est. Tokens[/magenta]",
            f"[cyan]{plan.total_tokens_estimated:,}[/cyan]",
        )

        # Task distribution by phase
        table.add_row("", "")  # Spacer
        for phase in plan.phases:
            pct = (phase.completed / phase.task_count * 100) if phase.task_count > 0 else 0
            table.add_row(
                f"[magenta]{phase.name}[/magenta]",
                f"{pct:.0f}% ({phase.completed}/{phase.task_count})",
            )

        self.console.print(table)
        self.console.print()

    def show_full_plan(self, plan: MasterPlan) -> None:
        """Show complete masterplan with all visualizations."""
        # Clear and show everything
        self.console.clear()

        # Header with fancy border
        header_text = f"🎯 MASTERPLAN: {plan.execution_id}"
        self.console.print(
            Panel(
                f"[bold cyan]{header_text}[/bold cyan]",
                border_style="cyan",
                expand=False,
            )
        )
        self.console.print()

        # Show all sections
        self.show_masterplan_overview(plan)
        self.show_phases_timeline(plan)
        self.show_statistics(plan)
        self.show_tasks_table(plan, max_rows=15)

    def _print_progress_bar(
        self,
        completion: float,
        width: int = 50,
        show_percent: bool = False,
    ) -> None:
        """Print a styled progress bar."""
        filled = int(width * completion / 100)
        bar = "█" * filled + "░" * (width - filled)
        percent_str = f" {completion:.1f}%" if show_percent else ""
        self.console.print(f"   [green]{bar}[/green]{percent_str}")


# Helper function for easy usage
def visualize_plan(plan: MasterPlan, view: str = "overview") -> None:
    """Convenience function to visualize a plan.

    Args:
        plan: MasterPlan object to visualize
        view: Type of visualization ('overview', 'timeline', 'tasks', 'stats', 'dependencies', 'full')
    """
    visualizer = PlanVisualizer()

    views = {
        "overview": visualizer.show_masterplan_overview,
        "timeline": visualizer.show_phases_timeline,
        "tasks": visualizer.show_tasks_table,
        "stats": visualizer.show_statistics,
        "dependencies": visualizer.show_dependencies_graph,
        "full": visualizer.show_full_plan,
    }

    view_func = views.get(view, visualizer.show_masterplan_overview)
    view_func(plan)
