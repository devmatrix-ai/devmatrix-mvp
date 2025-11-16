"""Main CLI entry point for DevMatrix Console Tool."""

import asyncio
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text
import click

from src.console.config import load_config, Config
from src.console.session_manager import SessionManager, PipelineState
from src.console.websocket_client import WebSocketClient
from src.console.pipeline_visualizer import PipelineVisualizer, TaskNode
from src.console.command_dispatcher import CommandDispatcher
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

        logger.info(f"DevMatrixConsole initialized (theme={self.config.theme})")

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
        """Connect to WebSocket server."""
        try:
            self.websocket = WebSocketClient(self.config.websocket_url, self.session_id)

            # Subscribe to updates
            self.websocket.subscribe("pipeline_update", self._on_pipeline_update)
            self.websocket.subscribe("error", self._on_error)
            self.websocket.subscribe("artifact_created", self._on_artifact_created)
            self.websocket.subscribe("test_result", self._on_test_result)

            if self.websocket.connect(timeout=self.config.timeout):
                self.console.print("[green]Connected to backend[/green]")
                logger.info("WebSocket connected")
            else:
                self.console.print(
                    "[yellow]Warning: Could not connect to backend. Offline mode.[/yellow]"
                )
                logger.warning("WebSocket connection failed")
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

    # Callback handlers for WebSocket events
    def _on_pipeline_update(self, update) -> None:
        """Handle pipeline update."""
        data = update.data
        self.visualizer.render_fullscreen(
            total=data.get("total_tasks", 0),
            completed=data.get("completed_tasks", 0),
            failed=data.get("failed_tasks", 0),
            current=data.get("current_task"),
        )

    def _on_error(self, update) -> None:
        """Handle error."""
        self.console.print(f"[red]Error: {update.data.get('message')}[/red]")

    def _on_artifact_created(self, update) -> None:
        """Handle artifact creation."""
        artifact = update.data
        self.console.print(f"[green]✓[/green] Created: {artifact.get('path')}")

    def _on_test_result(self, update) -> None:
        """Handle test result."""
        result = update.data
        status_symbol = "✅" if result.get("passed") else "❌"
        self.console.print(f"{status_symbol} {result.get('test_name')}")


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
