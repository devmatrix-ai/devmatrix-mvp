"""Advanced logging viewer for DevMatrix Console."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from src.observability import get_logger

logger = get_logger(__name__)


class LogLevel(str, Enum):
    """Log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


@dataclass
class LogEntry:
    """Single log entry."""

    timestamp: str
    level: LogLevel
    source: str
    message: str
    details: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        return f"[{self.timestamp}] {self.level}: {self.message}"


class LogViewer:
    """Advanced logging viewer with filtering and search."""

    # Color mapping for log levels
    LEVEL_COLORS = {
        LogLevel.DEBUG: "dim",
        LogLevel.INFO: "cyan",
        LogLevel.WARN: "yellow",
        LogLevel.ERROR: "red",
    }

    def __init__(self, console: Optional[Console] = None, max_entries: int = 10000):
        """Initialize log viewer.

        Args:
            console: Rich Console instance
            max_entries: Maximum log entries to keep
        """
        self.console = console or Console()
        self.max_entries = max_entries
        self.logs: List[LogEntry] = []
        logger.info(f"LogViewer initialized (max_entries={max_entries})")

    def add_log(
        self,
        level: LogLevel,
        message: str,
        source: str = "console",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add log entry.

        Args:
            level: Log level
            message: Log message
            source: Source component
            details: Optional details
        """
        timestamp = datetime.now().isoformat()
        entry = LogEntry(timestamp=timestamp, level=level, source=source, message=message, details=details)

        self.logs.append(entry)

        # Keep size bounded
        if len(self.logs) > self.max_entries:
            self.logs = self.logs[-self.max_entries :]

        logger.debug(f"Log added: {level} - {message[:50]}")

    def filter_logs(
        self,
        level: Optional[LogLevel] = None,
        source: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 100,
    ) -> List[LogEntry]:
        """Filter logs with multiple criteria.

        Args:
            level: Filter by level (optional)
            source: Filter by source (optional)
            query: Search message text (optional)
            limit: Max results to return

        Returns:
            List of matching log entries
        """
        results = self.logs

        # Filter by level
        if level:
            results = [l for l in results if l.level == level]

        # Filter by source
        if source:
            results = [l for l in results if source.lower() in l.source.lower()]

        # Search by query
        if query:
            query_lower = query.lower()
            results = [l for l in results if query_lower in l.message.lower()]

        # Return most recent, limited
        return list(reversed(results))[:limit]

    def render_table(
        self,
        level: Optional[LogLevel] = None,
        source: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 50,
    ) -> Table:
        """Render logs as table.

        Args:
            level: Filter by level
            source: Filter by source
            query: Search query
            limit: Max entries

        Returns:
            Rich Table with logs
        """
        logs = self.filter_logs(level, source, query, limit)

        table = Table(title="Execution Logs", show_header=True, header_style="bold")
        table.add_column("Time", style="dim", width=12)
        table.add_column("Level", style="cyan", width=8)
        table.add_column("Source", style="magenta", width=15)
        table.add_column("Message", style="white")

        for log in logs:
            color = self.LEVEL_COLORS.get(log.level, "white")
            time_str = log.timestamp.split("T")[1][:8]  # HH:MM:SS

            # Truncate message
            msg = log.message[:60] + ("..." if len(log.message) > 60 else "")

            table.add_row(time_str, f"[{color}]{log.level.value}[/{color}]", log.source, msg)

        return table

    def render_detailed(self, entry: LogEntry) -> Panel:
        """Render detailed view of single log entry.

        Args:
            entry: Log entry to display

        Returns:
            Rich Panel with details
        """
        color = self.LEVEL_COLORS.get(entry.level, "white")
        header = f"[{color}]{entry.level.value}[/{color}] {entry.source} @ {entry.timestamp}"

        content = f"\n{entry.message}\n"

        if entry.details:
            content += "\nDetails:\n"
            for key, value in entry.details.items():
                content += f"  {key}: {value}\n"

        return Panel(content, title=header, border_style=color)

    def get_stats(self) -> Dict[str, Any]:
        """Get log statistics.

        Returns:
            Stats dictionary
        """
        level_counts = {}
        source_counts = {}

        for log in self.logs:
            level_counts[log.level.value] = level_counts.get(log.level.value, 0) + 1
            source_counts[log.source] = source_counts.get(log.source, 0) + 1

        return {
            "total_logs": len(self.logs),
            "by_level": level_counts,
            "by_source": source_counts,
            "oldest": self.logs[0].timestamp if self.logs else None,
            "newest": self.logs[-1].timestamp if self.logs else None,
        }

    def get_summary(self) -> str:
        """Get human-readable summary.

        Returns:
            Summary string
        """
        stats = self.get_stats()
        total = stats["total_logs"]

        errors = stats["by_level"].get("ERROR", 0)
        warnings = stats["by_level"].get("WARN", 0)

        summary = f"{total} logs"
        if errors:
            summary += f" | {errors} errors"
        if warnings:
            summary += f" | {warnings} warnings"

        return summary

    def export_logs(self) -> List[Dict[str, Any]]:
        """Export logs for saving.

        Returns:
            List of log dictionaries
        """
        return [
            {
                "timestamp": log.timestamp,
                "level": log.level.value,
                "source": log.source,
                "message": log.message,
                "details": log.details,
            }
            for log in self.logs
        ]

    def clear(self) -> None:
        """Clear all logs."""
        self.logs = []
        logger.info("Logs cleared")

    def get_error_logs(self) -> List[LogEntry]:
        """Get all error logs.

        Returns:
            List of error entries
        """
        return [log for log in self.logs if log.level == LogLevel.ERROR]

    def get_warnings(self) -> List[LogEntry]:
        """Get all warning logs.

        Returns:
            List of warning entries
        """
        return [log for log in self.logs if log.level == LogLevel.WARN]
