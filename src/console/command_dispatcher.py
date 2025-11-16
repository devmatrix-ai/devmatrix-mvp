"""Command routing and execution dispatcher for console."""

from typing import Dict, Callable, Any, Optional
from dataclasses import dataclass
from src.observability import get_logger
from src.console.spec_questioner import SpecificationBuilder, SpecificationGap

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
        self.spec_builder: Optional[SpecificationBuilder] = None
        self.current_questions: Optional[list[SpecificationGap]] = None
        self._register_builtin_commands()
        logger.info("CommandDispatcher initialized")

    def _register_builtin_commands(self) -> None:
        """Register built-in commands."""
        # Core workflow
        self.register("help", self._cmd_help, "Show help information")
        self.register("spec", self._cmd_spec, "Generate specification from request")
        self.register("plan", self._cmd_plan, "Plan, show, or manage masterplan")
        self.register("execute", self._cmd_execute, "Execute the masterplan")
        self.register("validate", self._cmd_validate, "Validate execution results")

        # Utilities
        self.register("test", self._cmd_test, "Run tests")
        self.register("show", self._cmd_show, "Show pipeline, logs, artifacts, or plan")
        self.register("logs", self._cmd_logs, "Display execution logs")
        self.register("cancel", self._cmd_cancel, "Cancel current execution")
        self.register("retry", self._cmd_retry, "Retry failed task")
        self.register("session", self._cmd_session, "Manage sessions")
        self.register("config", self._cmd_config, "Manage configuration")

        # Exit
        self.register("exit", self._cmd_exit, "Exit the console")
        self.register("quit", self._cmd_exit, "Exit the console")

        # Aliases
        self.aliases["q"] = "exit"
        self.aliases["h"] = "help"
        self.aliases["?"] = "help"
        self.aliases["p"] = "plan"
        self.aliases["s"] = "show"

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

    def _cmd_spec(self, args: list[str], options: Dict[str, Any]) -> CommandResult:
        """Generate specification from user request with intelligent questioning.

        Usage:
          /spec <description>          - Start specification gathering
          /spec answer <answer>        - Provide answer to current question
          /spec show                   - Show current specification summary
          /spec ready                  - Mark specification as ready for masterplan

        This command uses intelligent questioning to ensure specification completeness.
        """
        if not args:
            return CommandResult(
                success=False, output="", error="Usage: /spec <description|answer|show|ready>"
            )

        action = args[0].lower()

        # Initialize new specification gathering
        if action not in ["answer", "show", "ready"] or not self.spec_builder:
            # Starting new spec gathering
            if action in ["answer", "show", "ready"] and not self.spec_builder:
                return CommandResult(
                    success=False, output="", error="No specification in progress. Start with /spec <description>"
                )

            # Start specification gathering
            description = " ".join(args)
            self.spec_builder = SpecificationBuilder()
            spec, questions = self.spec_builder.start_from_requirement(description)
            self.current_questions = questions

            # Format output
            output = f"🔍 Analyzing requirement:\n"
            output += f"{description}\n\n"

            # Detect app type
            output += f"📱 Detected app type: **{spec.app_type.value.replace('_', ' ').title()}**\n\n"

            # Ask clarifying questions
            output += "Para generar un masterplan más preciso, tengo algunas preguntas:\n\n"
            output += self.spec_builder.questioner.format_questions_for_claude(questions, num_questions=3)

            return CommandResult(
                success=True,
                output=output,
                data={
                    "action": "init",
                    "app_type": spec.app_type.value,
                    "pending_questions": len(questions)
                }
            )

        # Handle "answer" action
        elif action == "answer":
            if len(args) < 2:
                return CommandResult(
                    success=False, output="", error="Usage: /spec answer <your_answer>"
                )

            answer = " ".join(args[1:])
            if not self.current_questions:
                return CommandResult(
                    success=False, output="", error="No pending questions"
                )

            # Process answer
            gap = self.current_questions[0]
            is_complete, next_questions = self.spec_builder.add_answer(gap, answer)
            self.current_questions = next_questions if next_questions else []

            # Format output
            output = f"✅ Recorded: {answer}\n\n"

            if is_complete:
                output += "🎉 Specification is now complete!\n\n"
                output += "You can now:\n"
                output += "  /spec show    - Review the complete specification\n"
                output += "  /spec ready   - Generate the masterplan\n"
                return CommandResult(
                    success=True,
                    output=output,
                    data={"action": "answer", "is_complete": True}
                )
            else:
                if self.current_questions:
                    output += "Next question:\n\n"
                    output += self.spec_builder.questioner.format_questions_for_claude(
                        self.current_questions,
                        num_questions=1
                    )
                return CommandResult(
                    success=True,
                    output=output,
                    data={"action": "answer", "is_complete": False, "pending_questions": len(self.current_questions)}
                )

        # Handle "show" action
        elif action == "show":
            if not self.spec_builder:
                return CommandResult(
                    success=False, output="", error="No specification in progress"
                )

            summary = self.spec_builder.format_spec_summary()
            return CommandResult(success=True, output=summary, data={"action": "show"})

        # Handle "ready" action
        elif action == "ready":
            if not self.spec_builder:
                return CommandResult(
                    success=False, output="", error="No specification in progress"
                )

            spec = self.spec_builder.get_final_specification()
            is_valid, missing, completeness = self.spec_builder.questioner.validate_specification(spec)

            if not is_valid:
                output = f"⚠️  Specification is {completeness*100:.0f}% complete.\n\n"
                output += "Missing critical information:\n"
                for category in missing:
                    output += f"  - {category}\n"
                output += "\nPlease answer more questions before proceeding."
                return CommandResult(success=False, output=output, error="Incomplete specification")

            output = f"✅ Specification ready for masterplan generation!\n\n"
            output += f"Completeness: {completeness*100:.0f}%\n\n"
            output += "Next step: /plan generate\n"

            return CommandResult(
                success=True,
                output=output,
                data={"action": "ready", "spec_data": spec.__dict__}
            )

    def _cmd_plan(self, args: list[str], options: Dict[str, Any]) -> CommandResult:
        """Plan, show, or manage masterplan.

        Subcommands:
          /plan show [--view overview|timeline|tasks|stats|dependencies|full]
          /plan generate <description>
          /plan review
        """
        if not args:
            return CommandResult(
                success=False,
                output="",
                error="Usage: /plan <show|generate|review> [options]",
            )

        action = args[0]
        valid_actions = ["show", "generate", "review"]

        if action not in valid_actions:
            return CommandResult(
                success=False,
                output="",
                error=f"Invalid plan action. Choose: {', '.join(valid_actions)}",
            )

        if action == "show":
            view = options.get("view", "overview")
            output = f"📋 Showing masterplan ({view} view)...\n"
            return CommandResult(success=True, output=output, data={"action": "show", "view": view})

        elif action == "generate":
            if len(args) < 2:
                return CommandResult(
                    success=False, output="", error="Usage: /plan generate <description>"
                )
            description = " ".join(args[1:])
            output = f"📝 Generating masterplan from specification...\n"
            output += f"📌 Description: {description}\n"
            output += f"⏳ Creating 120 tasks across 5 phases...\n"
            return CommandResult(success=True, output=output, data={"action": "generate", "description": description})

        elif action == "review":
            output = "👀 Reviewing masterplan before execution...\n"
            output += "📊 Checking dependencies, estimates, and feasibility...\n"
            return CommandResult(success=True, output=output, data={"action": "review"})

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

    def _cmd_execute(self, args: list[str], options: Dict[str, Any]) -> CommandResult:
        """Execute the masterplan.

        Options:
          --parallel: Use parallel execution
          --max-workers: Number of parallel workers
          --dry-run: Show what would be executed without running
        """
        parallel = options.get("parallel", True)
        max_workers = options.get("max-workers", "4")
        dry_run = options.get("dry-run", False)

        output = "🚀 Executing masterplan...\n"
        if dry_run:
            output += "🔍 Dry-run mode: No changes will be made\n"
        output += f"⚙️  Parallel execution: {'Yes' if parallel else 'No'}\n"
        output += f"👷 Max workers: {max_workers}\n"
        output += f"⏳ Starting execution waves...\n"

        return CommandResult(success=True, output=output, data={"parallel": parallel, "max_workers": max_workers, "dry_run": dry_run})

    def _cmd_validate(self, args: list[str], options: Dict[str, Any]) -> CommandResult:
        """Validate execution results.

        Options:
          --strict: Strict validation mode
          --check <type>: Check specific aspect (syntax, tests, coverage, etc)
        """
        strict = options.get("strict", False)
        check_type = options.get("check", "all")

        output = "✅ Validating execution results...\n"
        if strict:
            output += "🔒 Strict validation mode enabled\n"
        output += f"🔍 Checking: {check_type}\n"
        output += f"📊 Generating validation report...\n"

        return CommandResult(success=True, output=output, data={"strict": strict, "check_type": check_type})

    def _cmd_exit(self, args: list[str], options: Dict[str, Any]) -> CommandResult:
        """Exit console."""
        output = "Exiting DevMatrix console...\n"
        return CommandResult(success=True, output=output, data={"should_exit": True})
