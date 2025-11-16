"""Command routing and execution dispatcher for console."""

from typing import Dict, Callable, Any, Optional
from dataclasses import dataclass
from src.observability import get_logger

logger = get_logger(__name__)


@dataclass
class CommandResult:
    """Result of command execution."""

    success: bool
    output: str
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class CommandDispatcher:
    """Routes and executes console commands."""

    def __init__(self):
        """Initialize dispatcher."""
        self.commands: Dict[str, Callable] = {}
        self.aliases: Dict[str, str] = {}
        self._register_builtin_commands()
        logger.info("CommandDispatcher initialized")

    def _register_builtin_commands(self) -> None:
        """Register built-in commands."""
        self.register("help", self._cmd_help, "Show help information")
        self.register("run", self._cmd_run, "Run a task or feature")
        self.register("plan", self._cmd_plan, "Plan architecture or feature")
        self.register("test", self._cmd_test, "Run tests")
        self.register("show", self._cmd_show, "Show pipeline, logs, or artifacts")
        self.register("logs", self._cmd_logs, "Display execution logs")
        self.register("cancel", self._cmd_cancel, "Cancel current execution")
        self.register("retry", self._cmd_retry, "Retry failed task")
        self.register("session", self._cmd_session, "Manage sessions")
        self.register("config", self._cmd_config, "Manage configuration")
        self.register("exit", self._cmd_exit, "Exit the console")
        self.register("quit", self._cmd_exit, "Exit the console")

        # Aliases
        self.aliases["q"] = "exit"
        self.aliases["h"] = "help"
        self.aliases["?"] = "help"

    def register(self, name: str, handler: Callable, description: str = "") -> None:
        """Register a command.

        Args:
            name: Command name
            handler: Handler function
            description: Command description
        """
        self.commands[name] = {
            "handler": handler,
            "description": description,
        }
        logger.debug(f"Registered command: {name}")

    def parse_command(self, input_str: str) -> tuple[str, list[str], Dict[str, Any]]:
        """Parse command input.

        Args:
            input_str: Raw command input

        Returns:
            Tuple of (command_name, args, options)

        Example:
            "/run --focus security --depth deep feature" ->
            ("run", ["feature"], {"focus": "security", "depth": "deep"})
        """
        parts = input_str.strip().split()
        if not parts:
            return "", [], {}

        # Remove leading / if present
        cmd = parts[0].lstrip("/")

        # Resolve aliases
        cmd = self.aliases.get(cmd, cmd)

        # Extract options (--key value) and arguments
        args = []
        options = {}
        i = 1
        while i < len(parts):
            part = parts[i]
            if part.startswith("--"):
                key = part[2:]
                if i + 1 < len(parts) and not parts[i + 1].startswith("--"):
                    value = parts[i + 1]
                    options[key] = value
                    i += 2
                else:
                    options[key] = True
                    i += 1
            else:
                args.append(part)
                i += 1

        return cmd, args, options

    def execute(self, input_str: str) -> CommandResult:
        """Execute a command.

        Args:
            input_str: Raw command input

        Returns:
            CommandResult with output and status
        """
        try:
            cmd, args, options = self.parse_command(input_str)

            if not cmd:
                return CommandResult(success=False, output="", error="No command provided")

            if cmd not in self.commands:
                return CommandResult(
                    success=False, output="", error=f"Unknown command: {cmd}"
                )

            handler = self.commands[cmd]["handler"]
            result = handler(args, options)

            return result
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return CommandResult(success=False, output="", error=str(e))

    def list_commands(self) -> Dict[str, str]:
        """Get all available commands.

        Returns:
            Dict of command_name -> description
        """
        return {name: info["description"] for name, info in self.commands.items()}

    # Built-in command handlers
    def _cmd_help(self, args: list[str], options: Dict[str, Any]) -> CommandResult:
        """Show help."""
        if args:
            cmd = args[0]
            if cmd in self.commands:
                desc = self.commands[cmd]["description"]
                return CommandResult(success=True, output=f"{cmd}: {desc}")
            else:
                return CommandResult(success=False, output="", error=f"No help for {cmd}")

        commands = self.list_commands()
        output = "Available commands:\n"
        for name, desc in sorted(commands.items()):
            output += f"  {name:12} - {desc}\n"
        return CommandResult(success=True, output=output)

    def _cmd_run(self, args: list[str], options: Dict[str, Any]) -> CommandResult:
        """Execute a task."""
        if not args:
            return CommandResult(
                success=False, output="", error="Usage: /run <task_name> [options]"
            )

        task = " ".join(args)
        focus = options.get("focus", "general")
        depth = options.get("depth", "standard")

        output = f"Running task: {task}\nFocus: {focus}\nDepth: {depth}\n"
        return CommandResult(success=True, output=output, data={"task": task, "focus": focus})

    def _cmd_plan(self, args: list[str], options: Dict[str, Any]) -> CommandResult:
        """Plan architecture or feature."""
        if not args:
            return CommandResult(
                success=False, output="", error="Usage: /plan <feature|architecture|security>"
            )

        plan_type = args[0]
        valid_types = ["feature", "architecture", "security"]

        if plan_type not in valid_types:
            return CommandResult(
                success=False,
                output="",
                error=f"Invalid plan type. Choose: {', '.join(valid_types)}",
            )

        output = f"Planning {plan_type}...\n"
        return CommandResult(success=True, output=output, data={"plan_type": plan_type})

    def _cmd_test(self, args: list[str], options: Dict[str, Any]) -> CommandResult:
        """Run tests."""
        pattern = args[0] if args else "*"
        coverage = options.get("coverage", False)

        output = f"Running tests matching: {pattern}\n"
        if coverage:
            output += "Coverage report enabled\n"
        return CommandResult(success=True, output=output, data={"pattern": pattern})

    def _cmd_show(self, args: list[str], options: Dict[str, Any]) -> CommandResult:
        """Show pipeline, logs, or artifacts."""
        if not args:
            return CommandResult(
                success=False,
                output="",
                error="Usage: /show <pipeline|logs|artifacts>",
            )

        show_type = args[0]
        output = f"Showing {show_type}...\n"
        return CommandResult(success=True, output=output, data={"show_type": show_type})

    def _cmd_logs(self, args: list[str], options: Dict[str, Any]) -> CommandResult:
        """Display logs."""
        filter_str = options.get("filter", "")
        limit = int(options.get("limit", "100"))

        output = f"Showing last {limit} log entries"
        if filter_str:
            output += f" (filter: {filter_str})"
        output += "\n"
        return CommandResult(success=True, output=output)

    def _cmd_cancel(self, args: list[str], options: Dict[str, Any]) -> CommandResult:
        """Cancel execution."""
        output = "Cancelling current execution...\n"
        return CommandResult(success=True, output=output)

    def _cmd_retry(self, args: list[str], options: Dict[str, Any]) -> CommandResult:
        """Retry failed task."""
        output = "Retrying previous failed task...\n"
        return CommandResult(success=True, output=output)

    def _cmd_session(self, args: list[str], options: Dict[str, Any]) -> CommandResult:
        """Manage sessions."""
        if not args:
            return CommandResult(
                success=False,
                output="",
                error="Usage: /session <save|load|list>",
            )

        action = args[0]
        valid_actions = ["save", "load", "list"]

        if action not in valid_actions:
            return CommandResult(
                success=False,
                output="",
                error=f"Invalid action. Choose: {', '.join(valid_actions)}",
            )

        output = f"Session action: {action}\n"
        return CommandResult(success=True, output=output, data={"action": action})

    def _cmd_config(self, args: list[str], options: Dict[str, Any]) -> CommandResult:
        """Manage configuration."""
        if not args:
            return CommandResult(
                success=False,
                output="",
                error="Usage: /config <get|set|show>",
            )

        action = args[0]
        output = f"Config action: {action}\n"
        return CommandResult(success=True, output=output, data={"action": action})

    def _cmd_exit(self, args: list[str], options: Dict[str, Any]) -> CommandResult:
        """Exit console."""
        output = "Exiting DevMatrix console...\n"
        return CommandResult(success=True, output=output, data={"should_exit": True})
