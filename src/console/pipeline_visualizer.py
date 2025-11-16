"""Terminal UI components for pipeline visualization."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from rich.console import Console
from rich.tree import Tree
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, DownloadColumn
from rich.table import Table
from rich.status import Status
from rich.text import Text
from src.observability import get_logger

logger = get_logger(__name__)


@dataclass
class TaskNode:
    """Represents a task in the pipeline tree."""

    id: str
    name: str
    status: str  # pending, running, completed, failed, skipped
    progress: int = 0  # 0-100
    duration_ms: float = 0.0
    error: Optional[str] = None
    children: List["TaskNode"] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "progress": self.progress,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "children": [child.to_dict() for child in self.children],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskNode":
        """Create from dictionary."""
        children = [cls.from_dict(child) for child in data.get("children", [])]
        return cls(
            id=data["id"],
            name=data["name"],
            status=data["status"],
            progress=data.get("progress", 0),
            duration_ms=data.get("duration_ms", 0.0),
            error=data.get("error"),
            children=children,
        )


class PipelineVisualizer:
    """Renders pipeline execution tree and status in terminal."""

    # Status symbols and colors
    STATUS_SYMBOLS = {
        "pending": "⏳",
        "running": "🔄",
        "completed": "✅",
        "failed": "❌",
        "skipped": "⊘",
        "warning": "⚠️",
    }

    STATUS_COLORS = {
        "pending": "yellow",
        "running": "blue",
        "completed": "green",
        "failed": "red",
        "skipped": "dim",
        "warning": "yellow",
    }

    def __init__(self, console: Optional[Console] = None):
        """Initialize visualizer.

        Args:
            console: Rich Console instance. Defaults to creating new one.
        """
        self.console = console or Console()
        self.root_task: Optional[TaskNode] = None
        self.collapsed_nodes: set[str] = set()
        logger.info("PipelineVisualizer initialized")

    def set_pipeline(self, root: TaskNode) -> None:
        """Set root task node.

        Args:
            root: Root TaskNode
        """
        self.root_task = root

    def toggle_collapse(self, task_id: str) -> None:
        """Toggle collapse state of a task.

        Args:
            task_id: Task ID
        """
        if task_id in self.collapsed_nodes:
            self.collapsed_nodes.remove(task_id)
        else:
            self.collapsed_nodes.add(task_id)

    def render_tree(self) -> Tree:
        """Render pipeline as Rich Tree.

        Returns:
            Rich Tree object
        """
        if not self.root_task:
            return Tree("📦 Pipeline [dim](empty)[/dim]")

        tree = Tree(self._format_node(self.root_task))
        self._render_tree_recursive(self.root_task, tree)
        return tree

    def _render_tree_recursive(self, node: TaskNode, tree: Tree) -> None:
        """Recursively render tree nodes.

        Args:
            node: Current node
            tree: Rich Tree to add to
        """
        if node.id in self.collapsed_nodes or not node.children:
            return

        for child in node.children:
            child_label = self._format_node(child)
            child_tree = tree.add(child_label)
            self._render_tree_recursive(child, child_tree)

    def _format_node(self, node: TaskNode) -> str:
        """Format node for display.

        Args:
            node: TaskNode to format

        Returns:
            Formatted string with symbol, name, progress
        """
        symbol = self.STATUS_SYMBOLS.get(node.status, "❓")
        color = self.STATUS_COLORS.get(node.status, "white")

        # Build progress indicator
        progress_str = ""
        if node.status == "running" and node.progress > 0:
            progress_str = f" [{progress_str}{node.progress}%]"
        elif node.status == "completed":
            progress_str = f" ({node.duration_ms:.1f}ms)"

        # Build error indicator
        error_str = ""
        if node.error:
            error_str = f" [red]({node.error[:30]}...)[/red]"

        return f"[{color}]{symbol}[/{color}] {node.name}{progress_str}{error_str}"

    def render_status_panel(
        self, total: int, completed: int, failed: int, current: Optional[str] = None
    ) -> Panel:
        """Render status summary panel.

        Args:
            total: Total tasks
            completed: Completed tasks
            failed: Failed tasks
            current: Currently running task name

        Returns:
            Rich Panel with status info
        """
        status_text = f"✅ {completed} | ❌ {failed} | ⏳ {total - completed - failed}"

        content = f"""
[bold]Pipeline Status[/bold]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{status_text}

[dim]Progress:[/dim] {completed}/{total} tasks
"""

        if current:
            content += f"\n[bold blue]Currently:[/bold blue] {current}"

        return Panel(content, border_style="blue", expand=False)

    def render_artifacts_panel(self, artifacts: List[Dict[str, Any]]) -> Panel:
        """Render created artifacts panel.

        Args:
            artifacts: List of artifact info dicts

        Returns:
            Rich Panel with artifact info
        """
        if not artifacts:
            content = "[dim]No artifacts created yet[/dim]"
        else:
            table = Table(title="Created Artifacts", show_header=True, header_style="bold cyan")
            table.add_column("Type", style="cyan")
            table.add_column("Path", style="green")
            table.add_column("Size", style="magenta")

            for artifact in artifacts[:10]:  # Show first 10
                table.add_row(
                    artifact.get("type", "file"),
                    artifact.get("path", "unknown"),
                    artifact.get("size", "?"),
                )

            content = table

        return Panel(content, border_style="green", expand=False)

    def render_tokens_panel(self, used: int, budget: Optional[int] = None) -> Panel:
        """Render token usage panel.

        Args:
            used: Tokens used
            budget: Token budget (optional)

        Returns:
            Rich Panel with token info
        """
        if budget:
            percent = (used / budget) * 100
            color = "green" if percent < 75 else "yellow" if percent < 90 else "red"
            content = f"[{color}]{percent:.0f}%[/{color}] ({used:,} / {budget:,})"
        else:
            content = f"{used:,} tokens"

        return Panel(content, title="Token Usage", border_style="magenta", expand=False)

    def render_logs_table(self, logs: List[Dict[str, str]]) -> Table:
        """Render logs as table.

        Args:
            logs: List of log entries with level, message, timestamp

        Returns:
            Rich Table with logs
        """
        table = Table(title="Recent Logs", show_header=True, header_style="bold")
        table.add_column("Time", style="dim")
        table.add_column("Level", style="cyan")
        table.add_column("Message")

        for log in logs[-20:]:  # Show last 20
            level = log.get("level", "INFO")
            level_color = {
                "ERROR": "red",
                "WARN": "yellow",
                "INFO": "cyan",
                "DEBUG": "dim",
            }.get(level, "white")

            table.add_row(
                log.get("timestamp", "")[-8:],  # Show HH:MM:SS
                f"[{level_color}]{level}[/{level_color}]",
                log.get("message", "")[:60],
            )

        return table

    def render_fullscreen(
        self,
        total: int,
        completed: int,
        failed: int,
        current: Optional[str] = None,
        artifacts: Optional[List[Dict[str, Any]]] = None,
        token_usage: int = 0,
        token_budget: Optional[int] = None,
    ) -> None:
        """Render complete fullscreen pipeline view.

        Args:
            total: Total tasks
            completed: Completed tasks
            failed: Failed tasks
            current: Currently running task
            artifacts: Created artifacts
            token_usage: Tokens used
            token_budget: Token budget
        """
        self.console.clear()

        # Title
        title = Text("🚀 DevMatrix Pipeline", style="bold cyan")
        self.console.print(title)

        # Pipeline tree
        if self.root_task:
            tree = self.render_tree()
            self.console.print(tree)
        else:
            self.console.print("[dim]No pipeline data[/dim]")

        # Status panels in a row
        self.console.print()
        status_panel = self.render_status_panel(total, completed, failed, current)
        token_panel = self.render_tokens_panel(token_usage, token_budget)
        self.console.print(status_panel)
        self.console.print(token_panel)

        # Artifacts
        if artifacts:
            self.console.print()
            artifacts_panel = self.render_artifacts_panel(artifacts)
            self.console.print(artifacts_panel)
