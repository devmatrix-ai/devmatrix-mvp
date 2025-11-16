"""Command autocomplete and history for DevMatrix Console."""

from typing import List, Optional, Tuple
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from src.observability import get_logger

logger = get_logger(__name__)


@dataclass
class HistoryEntry:
    """Command history entry."""

    command: str
    timestamp: str
    status: str  # success, error, warning
    output_preview: str = ""


class CommandHistory:
    """Manages command history with search capabilities."""

    def __init__(self, max_size: int = 1000):
        """Initialize history.

        Args:
            max_size: Maximum number of entries to keep
        """
        self.history: deque = deque(maxlen=max_size)
        self.search_index: dict = {}
        logger.info(f"CommandHistory initialized (max_size={max_size})")

    def add(self, command: str, status: str = "success", output: str = "") -> None:
        """Add command to history.

        Args:
            command: Command executed
            status: Execution status
            output: Output preview (first 100 chars)
        """
        entry = HistoryEntry(
            command=command,
            timestamp=datetime.now().isoformat(),
            status=status,
            output_preview=output[:100] if output else "",
        )

        self.history.append(entry)

        # Update search index
        self._update_search_index(command)

        logger.debug(f"Command added to history: {command[:50]}")

    def search(self, query: str) -> List[HistoryEntry]:
        """Search command history.

        Args:
            query: Search query (partial command match)

        Returns:
            List of matching entries
        """
        query_lower = query.lower()
        matches = [
            entry for entry in self.history if query_lower in entry.command.lower()
        ]
        return list(reversed(matches))

    def get_recent(self, n: int = 10) -> List[HistoryEntry]:
        """Get recent commands.

        Args:
            n: Number of recent entries

        Returns:
            List of recent entries
        """
        return list(reversed(list(self.history)[-n:]))

    def _update_search_index(self, command: str) -> None:
        """Update search index for command.

        Args:
            command: Command to index
        """
        words = command.split()
        for word in words:
            word_lower = word.lower()
            if word_lower not in self.search_index:
                self.search_index[word_lower] = 0
            self.search_index[word_lower] += 1

    def get_suggestions(self, prefix: str) -> List[str]:
        """Get command suggestions for prefix.

        Args:
            prefix: Prefix to complete

        Returns:
            List of suggested commands
        """
        prefix_lower = prefix.lower()
        matching = [
            entry.command
            for entry in self.history
            if entry.command.lower().startswith(prefix_lower)
        ]
        # Remove duplicates, keep order
        seen = set()
        unique = []
        for cmd in reversed(matching):
            if cmd not in seen:
                seen.add(cmd)
                unique.append(cmd)
        return list(reversed(unique))[:10]  # Return top 10


class CommandAutocomplete:
    """Provides intelligent command completion."""

    def __init__(self, dispatcher, history: Optional[CommandHistory] = None):
        """Initialize autocomplete.

        Args:
            dispatcher: CommandDispatcher instance
            history: Optional CommandHistory instance
        """
        self.dispatcher = dispatcher
        self.history = history or CommandHistory()
        self.command_options = self._build_option_map()
        logger.info("CommandAutocomplete initialized")

    def _build_option_map(self) -> dict:
        """Build map of commands and their options.

        Returns:
            Dictionary of command options
        """
        return {
            "run": {
                "flags": ["--focus", "--depth", "--time-limit"],
                "focus_values": ["general", "security", "performance", "accessibility"],
                "depth_values": ["light", "standard", "deep"],
            },
            "plan": {
                "flags": ["--scope"],
                "scope_values": ["feature", "architecture", "security", "performance"],
            },
            "test": {
                "flags": ["--filter", "--coverage", "--limit"],
            },
            "show": {
                "flags": [],
                "subcommands": ["pipeline", "logs", "artifacts"],
            },
            "logs": {
                "flags": ["--filter", "--limit", "--level"],
                "level_values": ["debug", "info", "warn", "error"],
            },
            "session": {
                "flags": [],
                "subcommands": ["save", "load", "list"],
            },
            "config": {
                "flags": [],
                "subcommands": ["get", "set", "show"],
            },
        }

    def complete(self, partial_input: str) -> Tuple[List[str], str]:
        """Complete partial command input.

        Args:
            partial_input: Partial command/option input

        Returns:
            Tuple of (suggestions, common_prefix)
        """
        partial = partial_input.strip()

        # Empty input - suggest commands
        if not partial:
            commands = list(self.dispatcher.list_commands().keys())
            return commands, ""

        parts = partial.split()

        # Completing command name
        if len(parts) == 1 and not partial.endswith(" "):
            cmd_prefix = parts[0].lstrip("/")
            matches = [
                cmd for cmd in self.dispatcher.list_commands().keys()
                if cmd.startswith(cmd_prefix)
            ]
            return matches, cmd_prefix

        # Completing after command
        if len(parts) >= 1:
            cmd = parts[0].lstrip("/")
            if cmd not in self.command_options:
                # Try history
                return self.history.get_suggestions(partial), ""

            # Suggest flags
            options = self.command_options[cmd]
            current_word = parts[-1] if not partial.endswith(" ") else ""

            # If current word starts with --, suggest flags
            if current_word.startswith("--"):
                flags = options.get("flags", [])
                matching = [f for f in flags if f.startswith(current_word)]
                return matching, current_word

            # Suggest subcommands
            if len(parts) == 2 and "subcommands" in options:
                subcommands = options["subcommands"]
                prefix = current_word
                matching = [s for s in subcommands if s.startswith(prefix)]
                return matching, prefix

            # Try history for arguments
            return self.history.get_suggestions(partial), ""

        return [], ""

    def get_help_for_command(self, command: str) -> Optional[str]:
        """Get help/options for command.

        Args:
            command: Command name

        Returns:
            Help string or None
        """
        if command not in self.command_options:
            return None

        options = self.command_options[command]
        help_text = f"\n{command} options:\n"

        if flags := options.get("flags"):
            help_text += f"  Flags: {', '.join(flags)}\n"

        if subcommands := options.get("subcommands"):
            help_text += f"  Subcommands: {', '.join(subcommands)}\n"

        if focus_values := options.get("focus_values"):
            help_text += f"  Focus: {', '.join(focus_values)}\n"

        if depth_values := options.get("depth_values"):
            help_text += f"  Depth: {', '.join(depth_values)}\n"

        return help_text.strip()

    def add_to_history(self, command: str, status: str = "success", output: str = "") -> None:
        """Add command to history.

        Args:
            command: Command executed
            status: Execution status
            output: Command output
        """
        self.history.add(command, status, output)

    def get_recent_history(self, n: int = 10) -> List[str]:
        """Get recent command history.

        Args:
            n: Number of recent commands

        Returns:
            List of recent commands
        """
        return [entry.command for entry in self.history.get_recent(n)]

    def export_history(self) -> List[dict]:
        """Export history for session saving.

        Returns:
            List of history entries as dictionaries
        """
        return [
            {
                "command": entry.command,
                "timestamp": entry.timestamp,
                "status": entry.status,
                "output_preview": entry.output_preview,
            }
            for entry in self.history.history
        ]
