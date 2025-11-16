"""Live artifact preview and display for created files."""

from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.table import Table
from src.observability import get_logger

logger = get_logger(__name__)


@dataclass
class Artifact:
    """Represents a created artifact (file)."""

    path: str
    file_type: str  # file, directory, image, code
    size: int  # bytes
    timestamp: str
    language: Optional[str] = None  # For code files
    preview: Optional[str] = None  # First N lines
    status: str = "created"  # created, modified, deleted


class ArtifactPreviewer:
    """Manages artifact preview and display."""

    # Language detection by extension
    LANGUAGE_MAP = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".cs": "csharp",
        ".rb": "ruby",
        ".php": "php",
        ".sql": "sql",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".json": "json",
        ".xml": "xml",
        ".html": "html",
        ".css": "css",
        ".scss": "scss",
        ".md": "markdown",
        ".txt": "text",
    }

    def __init__(self, console: Optional[Console] = None, max_preview_lines: int = 20):
        """Initialize previewer.

        Args:
            console: Rich Console instance
            max_preview_lines: Max lines to show in preview
        """
        self.console = console or Console()
        self.max_preview_lines = max_preview_lines
        self.artifacts: Dict[str, Artifact] = {}
        logger.info(f"ArtifactPreviewer initialized (max preview: {max_preview_lines} lines)")

    def add_artifact(
        self,
        path: str,
        file_type: str = "file",
        size: int = 0,
        timestamp: str = "",
        preview: Optional[str] = None,
    ) -> None:
        """Add artifact to tracking.

        Args:
            path: File path
            file_type: Type of artifact
            size: File size in bytes
            timestamp: Creation timestamp
            preview: Preview content (first N lines)
        """
        # Detect language for code files
        language = None
        if file_type == "file":
            ext = Path(path).suffix.lower()
            language = self.LANGUAGE_MAP.get(ext)

        artifact = Artifact(
            path=path,
            file_type=file_type,
            size=size,
            timestamp=timestamp,
            language=language,
            preview=preview,
        )

        self.artifacts[path] = artifact
        logger.debug(f"Artifact added: {path} ({file_type}, {size} bytes)")

    def render_artifact_table(self, limit: int = 20) -> Table:
        """Render artifacts as table.

        Args:
            limit: Max artifacts to show

        Returns:
            Rich Table with artifact info
        """
        table = Table(title="Created Artifacts", show_header=True, header_style="bold cyan")
        table.add_column("Status", style="green")
        table.add_column("Type", style="magenta")
        table.add_column("Path", style="cyan")
        table.add_column("Size", style="yellow")

        for artifact in list(self.artifacts.values())[:limit]:
            status_symbol = {
                "created": "✨",
                "modified": "📝",
                "deleted": "🗑️",
            }.get(artifact.status, "❓")

            table.add_row(
                status_symbol,
                artifact.file_type,
                artifact.path,
                self._format_size(artifact.size),
            )

        return table

    def render_artifact_preview(self, path: str) -> Optional[Panel]:
        """Render preview of specific artifact.

        Args:
            path: Artifact path

        Returns:
            Rich Panel with preview or None if not found
        """
        artifact = self.artifacts.get(path)
        if not artifact:
            return None

        if not artifact.preview:
            return Panel(
                "[dim]No preview available[/dim]",
                title=f"Preview: {path}",
                border_style="cyan",
            )

        # For code, use syntax highlighting
        if artifact.language:
            content = Syntax(
                artifact.preview,
                artifact.language,
                theme="monokai",
                line_numbers=True,
                word_wrap=True,
            )
        else:
            content = artifact.preview

        return Panel(
            content,
            title=f"Preview: {path}",
            border_style="cyan",
            expand=False,
        )

    def render_all_previews(self) -> None:
        """Display previews of all artifacts."""
        if not self.artifacts:
            self.console.print("[dim]No artifacts to preview[/dim]")
            return

        for path, artifact in self.artifacts.items():
            panel = self.render_artifact_preview(path)
            if panel:
                self.console.print(panel)

    def get_stats(self) -> Dict[str, Any]:
        """Get artifact statistics.

        Returns:
            Stats dictionary
        """
        total_size = sum(a.size for a in self.artifacts.values())
        by_type = {}
        for artifact in self.artifacts.values():
            if artifact.file_type not in by_type:
                by_type[artifact.file_type] = 0
            by_type[artifact.file_type] += 1

        return {
            "total_count": len(self.artifacts),
            "total_size": total_size,
            "by_type": by_type,
            "artifacts": [
                {"path": a.path, "type": a.file_type, "size": a.size} for a in self.artifacts.values()
            ],
        }

    def get_summary(self) -> str:
        """Get human-readable summary.

        Returns:
            Formatted summary string
        """
        count = len(self.artifacts)
        total_size = sum(a.size for a in self.artifacts.values())
        return f"{count} artifacts created ({self._format_size(total_size)})"

    @staticmethod
    def _format_size(size: int) -> str:
        """Format byte size to human readable.

        Args:
            size: Size in bytes

        Returns:
            Formatted string
        """
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"

    def export_artifacts(self) -> List[Dict[str, Any]]:
        """Export artifacts for session saving.

        Returns:
            List of artifact dictionaries
        """
        return [
            {
                "path": a.path,
                "type": a.file_type,
                "size": a.size,
                "timestamp": a.timestamp,
                "language": a.language,
                "status": a.status,
            }
            for a in self.artifacts.values()
        ]
