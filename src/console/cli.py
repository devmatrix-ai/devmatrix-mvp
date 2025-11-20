"""Main CLI entry point for DevMatrix Console Tool."""

import asyncio
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
import click

from src.console.config import load_config, Config
from src.console.session_manager import SessionManager, PipelineState
from src.console.websocket_client import WebSocketClient
from src.console.pipeline_visualizer import PipelineVisualizer, TaskNode
from src.console.command_dispatcher import CommandDispatcher
from src.console.token_tracker import TokenTracker
from src.console.artifact_previewer import ArtifactPreviewer
from src.console.autocomplete import CommandAutocomplete
from src.console.log_viewer import LogViewer, LogLevel
from src.console.live_dashboard import LiveDashboard
from src.cli.approval_manager import ApprovalManager
from src.observability import setup_logging, get_logger

logger = get_logger(__name__)


class DevMatrixConsole:
    """Main console application."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize console application.

        Args:
            config: Configuration object. Loads from files if not provided.
        """
        self.config = config or load_config()
        self.console = Console()
        self.session_manager = SessionManager()
        self.visualizer = PipelineVisualizer(self.console)
        self.dispatcher = CommandDispatcher()
        self.websocket: Optional[WebSocketClient] = None
        self.running = True
        self.session_id: Optional[str] = None

        # Phase 2 features
        self.token_tracker = TokenTracker(
            default_model=self.config.default_model,
            budget=self.config.token_budget if self.config.enable_token_tracking else None,
            cost_limit=self.config.cost_limit if self.config.enable_cost_tracking else None,
        )
        self.artifact_previewer = ArtifactPreviewer(self.console)
        self.log_viewer = LogViewer(self.console)
        self.autocomplete = CommandAutocomplete(self.dispatcher)

        # Phase 2: Approval system
        self.approval_manager = ApprovalManager(
            auto_approve=False,  # Default to interactive
            console=self.console  # Share Rich console
        )

        # Phase 3: Live Dashboard
        self.live_dashboard: Optional[LiveDashboard] = None
        self.live_context: Optional[Live] = None

        logger.info(f"DevMatrixConsole initialized (theme={self.config.theme})")
        logger.info("Approval workflow enabled")
        logger.info("E2E integration enabled with all event handlers")

    def setup(self) -> None:
        """Setup console application."""
        # Setup logging
        setup_logging(
            environment="console",
            log_level=self.config.verbosity.upper(),
            json_format=False,
        )

        # Create or load session
        self._init_session()

        # Show welcome
        self._show_welcome()

    def _init_session(self) -> None:
        """Initialize session."""
        if self.config.session_auto_load:
            # Try to load previous session
            recent_sessions = self.session_manager.list_sessions(limit=1)
            if recent_sessions:
                prev_session_id = recent_sessions[0]["id"]
                try:
                    self.session_manager.load_session(prev_session_id)
                    self.session_id = prev_session_id
                    self.console.print(
                        f"[cyan]Loaded previous session: {prev_session_id}[/cyan]"
                    )
                    return
                except Exception as e:
                    logger.warning(f"Failed to load previous session: {e}")

        # Create new session
        project_path = str(Path.cwd())
        self.session_id = self.session_manager.create_session(project_path)
        self.console.print(f"[cyan]Created new session: {self.session_id}[/cyan]")

    def _show_welcome(self) -> None:
        """Display welcome message."""
        title = Text("🚀 DevMatrix Console Tool", style="bold cyan")
        welcome_text = f"""
[cyan]Welcome to DevMatrix Console[/cyan]

Type [bold]/help[/bold] for available commands
Type [bold]/run <task>[/bold] to execute tasks
Type [bold]/exit[/bold] to quit

Session: {self.session_id}
Theme: {self.config.theme}
Verbosity: {self.config.verbosity}
"""
        panel = Panel(welcome_text, border_style="cyan", title=title)
        self.console.print(panel)

    async def run_async(self) -> None:
        """Run console application asynchronously."""
        try:
            await self._connect_websocket()
            await self._repl_loop()
        except Exception as e:
            logger.error(f"Console error: {e}")
            self.console.print(f"[red]Error: {e}[/red]")
        finally:
            await self._cleanup()

    def run(self) -> None:
        """Run console application (blocking)."""
        try:
            asyncio.run(self.run_async())
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Interrupted by user[/yellow]")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            sys.exit(1)

    async def _connect_websocket(self) -> None:
        """Connect to WebSocket server with full event subscriptions (Phase 5)."""
        try:
            self.websocket = WebSocketClient(self.config.websocket_url, self.session_id)

            # Subscribe to ALL events (Phase 5: E2E Integration)
            self.websocket.subscribe("pipeline_update", self._on_pipeline_update)
            self.websocket.subscribe("phase_started", self._on_phase_started)
            self.websocket.subscribe("phase_completed", self._on_phase_completed)
            self.websocket.subscribe("approval_request", self._on_approval_request)
            self.websocket.subscribe("snapshot_created", self._on_snapshot_created)
            self.websocket.subscribe("context_update", self._on_context_update)
            self.websocket.subscribe("artifact_created", self._on_artifact_created)
            self.websocket.subscribe("test_result", self._on_test_result)
            self.websocket.subscribe("error", self._on_error)

            if self.websocket.connect(timeout=self.config.timeout):
                self.console.print("[green]✅ Connected to backend (E2E mode)[/green]")
                logger.info("WebSocket connected with full E2E event subscriptions")
            else:
                self.console.print(
                    "[yellow]Warning: Could not connect to backend. Offline mode.[/yellow]"
                )
                logger.warning("WebSocket connection failed - using offline mode")
        except Exception as e:
            logger.warning(f"WebSocket connection failed: {e}")

    async def _repl_loop(self) -> None:
        """Main REPL loop."""
        while self.running:
            try:
                # Read command
                prompt = Prompt.get("[cyan]devmatrix[/cyan]", console=self.console)

                if not prompt.strip():
                    continue

                # Execute command
                result = self.dispatcher.execute(prompt)

                # Display output
                if result.success:
                    if result.output:
                        self.console.print(result.output)
                else:
                    if result.error:
                        self.console.print(f"[red]Error: {result.error}[/red]")

                # Check for special actions
                if result.data:
                    if result.data.get("should_exit"):
                        self.running = False
                        break

                    # Handle execute command with dashboard
                    if result.data.get("action") == "execute":
                        auto_approve = result.data.get("auto_approve", False)
                        use_dashboard = result.data.get("use_dashboard", True)

                        if use_dashboard:
                            # Get spec from previous /spec command or prompt
                            spec = result.data.get("spec", "Pipeline Execution")
                            await self._execute_with_dashboard(spec, auto_approve)
                        else:
                            # Use basic visualization
                            self.console.print("[yellow]Executing without dashboard (basic mode)[/yellow]")

                    # Save command to session
                    if self.session_manager.current_session_id:
                        self.session_manager.save_command(
                            command=prompt,
                            args={},
                            output=result.output,
                            status="success" if result.success else "error",
                            duration_ms=0.0,
                        )

            except Exception as e:
                logger.error(f"REPL error: {e}")
                self.console.print(f"[red]Error: {e}[/red]")

    async def _execute_with_dashboard(self, spec: str, auto_approve: bool = False):
        """Execute pipeline with live dashboard.

        Args:
            spec: Specification to execute
            auto_approve: Auto-approve all changes
        """
        # Create dashboard
        self.live_dashboard = LiveDashboard(
            console=self.console,
            spec_name=spec[:50] + "..." if len(spec) > 50 else spec
        )

        # Start live rendering
        with Live(self.live_dashboard.update(), console=self.console, refresh_per_second=4) as live:
            self.live_context = live

            try:
                # Execute pipeline via WebSocket
                execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                # Send execution request
                if self.websocket:
                    self.websocket.send_command(
                        "execute_pipeline",
                        {
                            "spec": spec,
                            "execution_id": execution_id,
                            "auto_approve": auto_approve
                        }
                    )
                else:
                    # Simulate execution for demo/offline mode
                    await self._simulate_pipeline_execution()

                # Wait for completion (updates handled by callbacks)
                while self.live_dashboard.status == "running":
                    await asyncio.sleep(0.1)
                    live.update(self.live_dashboard.update())

                # Final update
                live.update(self.live_dashboard.update())

            except Exception as e:
                logger.error(f"Dashboard execution error: {e}")
                self.live_dashboard.set_status("failed")
                self.live_dashboard.add_log(f"Error: {e}", level="error")
                live.update(self.live_dashboard.update())
            finally:
                self.live_context = None

        # Show completion message
        if self.live_dashboard.status == "completed":
            self.console.print("\n[green]✅ Pipeline execution completed successfully![/green]")
        else:
            self.console.print("\n[red]❌ Pipeline execution failed![/red]")

    async def _simulate_pipeline_execution(self):
        """Simulate pipeline execution for demo/offline mode."""
        logger.info("Simulating pipeline execution (offline mode)")

        phases = [
            (1, "Spec Ingestion", 4),
            (2, "Requirements Analysis", 5),
            (3, "Multi-Pass Planning", 5),
            (4, "Atomization", 5),
            (5, "DAG Construction", 5),
            (6, "Code Generation", 5),
            (7, "Semantic Validation", 5),
        ]

        for phase_num, phase_name, total_steps in phases:
            # Start phase
            self.live_dashboard.update_phase(phase_num, 0, "running")
            self.live_dashboard.set_current_task(f"Starting {phase_name}...")
            self.live_dashboard.add_log(f"Started: {phase_name}", level="info")

            # Simulate progress
            for step in range(1, total_steps + 1):
                await asyncio.sleep(0.5)  # Simulate work
                self.live_dashboard.update_phase(phase_num, step, "running")
                self.live_dashboard.set_current_task(f"{phase_name}: step {step}/{total_steps}")

                # Update metrics
                self.live_dashboard.update_metrics(
                    files_processed=phase_num * step,
                    atoms_created=phase_num * step * 3,
                    validations=phase_num * step * 2,
                )

            # Complete phase
            self.live_dashboard.update_phase(phase_num, total_steps, "completed")
            self.live_dashboard.add_log(f"Completed: {phase_name}", level="success")

        # Mark as completed
        self.live_dashboard.set_status("completed")
        self.live_dashboard.set_current_task("All phases completed!")

    async def _cleanup(self) -> None:
        """Cleanup on exit."""
        if self.websocket:
            self.websocket.disconnect()

        # Save session
        if self.session_manager.current_session_id:
            logger.info("Saving session...")
            # Session data is auto-saved, but we can add final cleanup here

        self.console.print("[cyan]Goodbye![/cyan]")
        logger.info("Console shutdown")

    # =========================================================================
    # Phase 5: E2E Integration - WebSocket Event Callbacks
    # =========================================================================

    def _on_pipeline_update(self, update) -> None:
        """Handle pipeline update.

        Updates:
        - Pipeline phase progress
        - Current task description
        - Performance metrics
        """
        data = update.data

        # Update dashboard if active
        if self.live_dashboard:
            # Update phase progress
            if "phase" in data:
                phase_num = data["phase"]
                progress = data.get("progress", 0)
                total = data.get("total", 0)
                status = data.get("phase_status", "running")

                self.live_dashboard.update_phase(
                    phase_num=phase_num,
                    progress=progress,
                    status=status
                )
                self.live_dashboard.phases[phase_num]["total"] = total

            # Update current task
            if "current_task" in data:
                self.live_dashboard.set_current_task(data["current_task"])

            # Update metrics
            if "metrics" in data:
                self.live_dashboard.update_metrics(**data["metrics"])

            # Add log
            if "message" in data:
                level = data.get("level", "info")
                self.live_dashboard.add_log(data["message"], level)
        else:
            # Fallback: basic visualization
            self.visualizer.render_fullscreen(
                total=data.get("total_tasks", 0),
                completed=data.get("completed_tasks", 0),
                failed=data.get("failed_tasks", 0),
                current=data.get("current_task"),
            )

    def _on_phase_started(self, update) -> None:
        """Handle phase started event (Phase 5)."""
        data = update.data
        phase_num = data.get("phase")
        phase_name = data.get("name", f"Phase {phase_num}")

        logger.info(f"Phase {phase_num} started: {phase_name}")

        if self.live_dashboard:
            self.live_dashboard.update_phase(phase_num, progress=0, status="running")
            self.live_dashboard.add_log(f"Started: {phase_name}", level="info")
            self.live_dashboard.set_current_task(f"Starting {phase_name}...")

    def _on_phase_completed(self, update) -> None:
        """Handle phase completed event (Phase 5)."""
        data = update.data
        phase_num = data.get("phase")
        phase_name = data.get("name", f"Phase {phase_num}")
        success = data.get("success", True)

        logger.info(f"Phase {phase_num} completed: {phase_name} (success={success})")

        if self.live_dashboard:
            total = self.live_dashboard.phases[phase_num]["total"]
            status = "completed" if success else "failed"
            self.live_dashboard.update_phase(phase_num, progress=total, status=status)

            level = "success" if success else "error"
            self.live_dashboard.add_log(f"Completed: {phase_name}", level=level)

    def _on_snapshot_created(self, update) -> None:
        """Handle snapshot created event (Phase 5)."""
        data = update.data
        snapshot_id = data.get("snapshot_id", "unknown")
        snapshot_name = data.get("name", "")

        display_name = f"{snapshot_name} ({snapshot_id})" if snapshot_name else snapshot_id
        logger.info(f"Snapshot created: {display_name}")

        self.console.print(f"[green]📸 Snapshot created: {display_name}[/green]")

        if self.live_dashboard:
            self.live_dashboard.add_log(f"Snapshot: {snapshot_id}", level="info")

    def _on_context_update(self, update) -> None:
        """Handle context usage update (Phase 5)."""
        data = update.data
        usage_pct = data.get("usage_percentage", 0)
        total_tokens = data.get("total_tokens", 0)

        logger.debug(f"Context update: {usage_pct:.1f}% ({total_tokens} tokens)")

        # Context tracker in live_dashboard is automatically updated
        # No explicit action needed - dashboard renders it on next update

    def _on_error(self, update) -> None:
        """Handle error."""
        error_msg = update.data.get('message')
        logger.error(f"Pipeline error: {error_msg}")
        self.console.print(f"[red]Error: {error_msg}[/red]")

        if self.live_dashboard:
            self.live_dashboard.add_log(error_msg, level="error")
            self.live_dashboard.update_metrics(errors=self.live_dashboard.metrics["errors"] + 1)

    def _on_artifact_created(self, update) -> None:
        """Handle artifact creation."""
        artifact = update.data
        artifact_path = artifact.get('path')
        logger.info(f"Artifact created: {artifact_path}")
        self.console.print(f"[green]✓[/green] Created: {artifact_path}")

        if self.live_dashboard:
            self.live_dashboard.add_log(f"Created: {artifact_path}", level="success")

    def _on_test_result(self, update) -> None:
        """Handle test result."""
        result = update.data
        test_name = result.get('test_name')
        passed = result.get('passed')
        status_symbol = "✅" if passed else "❌"
        logger.info(f"Test result: {test_name} - {'passed' if passed else 'failed'}")
        self.console.print(f"{status_symbol} {test_name}")

        if self.live_dashboard:
            level = "success" if passed else "error"
            self.live_dashboard.add_log(f"Test: {test_name}", level=level)
            if not passed:
                self.live_dashboard.update_metrics(errors=self.live_dashboard.metrics["errors"] + 1)

    def _on_approval_request(self, update) -> None:
        """Handle approval request from pipeline (Phase 2 + Phase 5).

        This callback is triggered when the pipeline needs approval for file operations.

        Args:
            update: WebSocket update with approval request data
                {
                    "type": "approval_request",
                    "data": {
                        "batch_id": "batch_123",
                        "operations": [
                            {"file": "src/foo.py", "operation": "create", "preview": "..."},
                            {"file": "src/bar.py", "operation": "modify", "diff": "..."}
                        ]
                    }
                }
        """
        data = update.data
        batch_id = data["batch_id"]
        operations = data["operations"]

        logger.info(f"Approval request received: batch={batch_id}, operations={len(operations)}")

        # Display operations for review
        self.console.print("\n[yellow]⚠️  Approval Required[/yellow]\n")
        self.console.print(f"Batch ID: {batch_id}")
        self.console.print(f"Operations: {len(operations)} file changes\n")

        # Show each operation with preview/diff
        for i, op in enumerate(operations, 1):
            file_path = op["file"]
            operation_type = op["operation"]

            self.console.print(f"[cyan]{i}. {operation_type.upper()}[/cyan] {file_path}")

            # Show preview for creates
            if operation_type == "create" and "preview" in op:
                preview = op["preview"]
                preview_text = preview[:500] + "..." if len(preview) > 500 else preview
                self.console.print(Panel(preview_text, title="Preview (first 500 chars)"))

            # Show diff for modifications
            if operation_type == "modify" and "diff" in op:
                diff = op["diff"]
                diff_text = diff[:500] + "..." if len(diff) > 500 else diff
                self.console.print(Panel(diff_text, title="Diff (first 500 chars)"))

            self.console.print()

        # Prompt for approval
        approved = Confirm.ask(
            "[yellow]Approve these operations?[/yellow]",
            default=True
        )

        # Send approval response via WebSocket
        if self.websocket:
            self.websocket.send_command(
                "approval_response",
                {
                    "batch_id": batch_id,
                    "approved": approved,
                    "timestamp": datetime.now().isoformat()
                }
            )

        # Display result
        if approved:
            self.console.print("[green]✅ Operations approved[/green]\n")
            logger.info(f"Approval granted for batch {batch_id}")
        else:
            self.console.print("[red]❌ Operations rejected[/red]\n")
            logger.info(f"Approval rejected for batch {batch_id}")

        # Update dashboard
        if self.live_dashboard:
            status_msg = "approved" if approved else "rejected"
            self.live_dashboard.add_log(f"Approval {status_msg}: {len(operations)} ops", level="info")


@click.command()
@click.option("--theme", default="auto", help="UI theme (auto, dark, light, high-contrast)")
@click.option("--verbosity", default="info", help="Log verbosity (debug, info, warn, error)")
@click.option("--session", default=None, help="Load specific session ID")
@click.option("--offline", is_flag=True, help="Run in offline mode (no WebSocket)")
def main(theme: str, verbosity: str, session: Optional[str], offline: bool) -> None:
    """DevMatrix Console Tool - Interactive pipeline execution interface."""
    # Load config
    config = load_config()

    # Override with CLI flags
    if theme != "auto":
        config.theme = theme
    if verbosity != "info":
        config.verbosity = verbosity

    # Initialize console
    console_app = DevMatrixConsole(config)
    console_app.setup()

    # Run
    console_app.run()


if __name__ == "__main__":
    main()
