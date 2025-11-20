#!/usr/bin/env python3
"""
Real-time Progress Dashboard for E2E Pipeline Testing
Provides live visualization of pipeline execution with granular metrics
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, List
import websockets
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.align import Align


class PipelineDashboard:
    """Real-time dashboard for pipeline execution monitoring"""

    def __init__(self):
        self.console = Console()
        self.metrics = {}
        self.phase_status = {}
        self.checkpoints = []
        self.errors = []
        self.start_time = None

        # Phase configuration
        self.phases = [
            "spec_ingestion",
            "requirements_analysis",
            "multi_pass_planning",
            "atomization",
            "dag_construction",
            "wave_execution",
            "validation",
            "deployment",
            "health_verification"
        ]

        self.phase_weights = {
            "spec_ingestion": 2,
            "requirements_analysis": 8,
            "multi_pass_planning": 15,
            "atomization": 12,
            "dag_construction": 5,
            "wave_execution": 45,
            "validation": 8,
            "deployment": 5
        }

    def create_header(self) -> Panel:
        """Create dashboard header"""
        header_text = Text()
        header_text.append("🚀 E2E PIPELINE EXECUTION DASHBOARD\n", style="bold cyan")

        if self.start_time:
            elapsed = time.time() - self.start_time
            header_text.append(f"Pipeline ID: {self.metrics.get('pipeline_id', 'N/A')}\n")
            header_text.append(f"Spec: {self.metrics.get('spec_name', 'N/A')}\n")
            header_text.append(f"Elapsed: {self._format_duration(elapsed)}")

        return Panel(Align.center(header_text), border_style="cyan")

    def create_phase_progress(self) -> Panel:
        """Create phase progress display"""
        table = Table(title="Phase Progress", show_header=True)
        table.add_column("Phase", style="cyan", width=20)
        table.add_column("Status", justify="center", width=10)
        table.add_column("Progress", width=30)
        table.add_column("Time", justify="right", width=10)
        table.add_column("Checkpoints", justify="center", width=12)

        overall_progress = 0.0

        for phase in self.phases:
            status = self.phase_status.get(phase, {})
            phase_state = status.get("status", "pending")

            # Status icon
            status_icon = self._get_status_icon(phase_state)

            # Progress bar
            progress = status.get("progress", 0.0)
            progress_bar = self._create_progress_bar(progress)

            # Duration
            duration = status.get("duration_ms", 0)
            time_str = f"{duration}ms" if duration > 0 else "---"

            # Checkpoints
            checkpoints = f"{status.get('checkpoints_completed', 0)}/{status.get('checkpoints_total', 5)}"

            # Add row
            table.add_row(
                phase.replace("_", " ").title(),
                status_icon,
                progress_bar,
                time_str,
                checkpoints
            )

            # Calculate overall progress
            weight = self.phase_weights.get(phase, 5) / 100
            overall_progress += progress * weight

        # Add overall progress row
        table.add_row(
            "[bold]OVERALL[/bold]",
            "🎯",
            self._create_progress_bar(overall_progress),
            f"{overall_progress:.1%}",
            "",
            style="bold yellow"
        )

        return Panel(table, border_style="green")

    def create_metrics_panel(self) -> Panel:
        """Create metrics display panel"""
        metrics_text = Text()

        # E2E Precision Metrics
        metrics_text.append("🎯 E2E Precision\n", style="bold cyan")
        metrics_text.append(f"  Overall Accuracy: {self.metrics.get('overall_accuracy', 0):.1%}\n")
        metrics_text.append(f"  Pipeline Precision: {self.metrics.get('pipeline_precision', 0):.1%}\n")
        metrics_text.append(f"  Pattern F1-Score: {self.metrics.get('pattern_f1', 0):.1%}\n")
        metrics_text.append(f"  Classification Acc: {self.metrics.get('classification_accuracy', 0):.1%}\n\n")

        # Pattern Bank Metrics
        metrics_text.append("📊 Pattern Matching\n", style="bold")
        metrics_text.append(f"  Precision: {self.metrics.get('pattern_precision', 0):.1%}\n")
        metrics_text.append(f"  Recall: {self.metrics.get('pattern_recall', 0):.1%}\n")
        metrics_text.append(f"  F1-Score: {self.metrics.get('pattern_f1', 0):.1%}\n")
        metrics_text.append(f"  Matches: {self.metrics.get('patterns_matched', 0)}\n\n")

        # Quality Metrics
        metrics_text.append("✅ Quality\n", style="bold")
        metrics_text.append(f"  Test Coverage: {self.metrics.get('test_coverage', 0):.1%}\n")
        metrics_text.append(f"  Test Pass Rate: {self.metrics.get('test_pass_rate', 0):.1%}\n")
        metrics_text.append(f"  Code Quality: {self.metrics.get('code_quality_score', 0):.2f}/1.0\n")
        criteria_met = self.metrics.get('acceptance_criteria_met', 0)
        criteria_total = self.metrics.get('acceptance_criteria_total', 0)
        metrics_text.append(f"  Acceptance: {criteria_met}/{criteria_total}\n\n")

        # Contract Validation
        contract_violations = self.metrics.get('contract_violations', 0)
        if contract_violations > 0:
            metrics_text.append("⚠️ Contracts\n", style="bold yellow")
            metrics_text.append(f"  Violations: {contract_violations}\n\n", style="yellow")
        else:
            metrics_text.append("✅ Contracts: Valid\n\n", style="green")

        # Performance Metrics
        metrics_text.append("⚡ Performance\n", style="bold")
        metrics_text.append(f"  Peak Memory: {self.metrics.get('peak_memory_mb', 0):.1f} MB\n")
        metrics_text.append(f"  Neo4j Avg: {self.metrics.get('neo4j_avg_query_ms', 0):.1f}ms\n")
        metrics_text.append(f"  Qdrant Avg: {self.metrics.get('qdrant_avg_query_ms', 0):.1f}ms\n\n")

        # Reliability
        metrics_text.append("🔧 Reliability\n", style="bold")
        metrics_text.append(f"  Success Rate: {self.metrics.get('execution_success_rate', 0):.1%}\n")
        metrics_text.append(f"  Recovery Rate: {self.metrics.get('recovery_success_rate', 0):.1%}\n")
        metrics_text.append(f"  Critical Errors: {self.metrics.get('critical_errors', 0)}\n")

        return Panel(metrics_text, title="Real-time Metrics", border_style="yellow")

    def create_checkpoint_log(self) -> Panel:
        """Create checkpoint activity log"""
        log_text = Text()

        # Show last 10 checkpoints
        recent_checkpoints = self.checkpoints[-10:] if self.checkpoints else []

        for checkpoint in recent_checkpoints:
            timestamp = checkpoint.get("timestamp", "")
            name = checkpoint.get("name", "")
            phase = checkpoint.get("phase", "")

            # Format: [HH:MM:SS] Phase: Checkpoint Name ✓
            time_str = datetime.fromisoformat(timestamp).strftime("%H:%M:%S") if timestamp else "??:??:??"
            log_text.append(f"[{time_str}] ", style="dim")
            log_text.append(f"{phase}: ", style="cyan")
            log_text.append(f"{name} ✓\n", style="green")

        if not recent_checkpoints:
            log_text.append("Waiting for checkpoints...", style="dim")

        return Panel(log_text, title="Checkpoint Activity", border_style="blue")

    def create_error_panel(self) -> Panel:
        """Create error display panel"""
        error_text = Text()

        if self.errors:
            recent_errors = self.errors[-5:]  # Show last 5 errors
            for error in recent_errors:
                phase = error.get("phase", "unknown")
                message = error.get("message", "No details")
                critical = error.get("critical", False)

                style = "bold red" if critical else "yellow"
                icon = "🔴" if critical else "⚠️"

                error_text.append(f"{icon} [{phase}] {message}\n", style=style)
        else:
            error_text.append("✨ No errors detected", style="green")

        return Panel(error_text, title="Error Log", border_style="red")

    def create_wave_execution_detail(self) -> Panel:
        """Create detailed wave execution display"""
        wave_text = Text()

        wave_data = self.metrics.get("wave_execution", {})
        if wave_data:
            wave_text.append("🌊 Wave Execution Details\n\n", style="bold")

            waves = wave_data.get("waves", [])
            for i, wave in enumerate(waves):
                atoms = wave.get("atoms", 0)
                succeeded = wave.get("succeeded", 0)
                failed = wave.get("failed", 0)
                duration = wave.get("duration_ms", 0)

                # Wave header
                wave_text.append(f"Wave {i}: ", style="cyan bold")
                wave_text.append(f"{atoms} atoms ")

                # Success/failure counts
                if succeeded > 0:
                    wave_text.append(f"✓{succeeded} ", style="green")
                if failed > 0:
                    wave_text.append(f"✗{failed} ", style="red")

                # Duration
                wave_text.append(f"({duration}ms)\n", style="dim")

                # Progress bar for wave
                if atoms > 0:
                    progress = succeeded / atoms
                    bar = self._create_mini_progress_bar(progress, width=20)
                    wave_text.append(f"  {bar}\n")
        else:
            wave_text.append("Waiting for wave execution...", style="dim")

        return Panel(wave_text, title="Wave Execution", border_style="cyan")

    def _get_status_icon(self, status: str) -> str:
        """Get icon for status"""
        icons = {
            "pending": "⏳",
            "in_progress": "🔄",
            "completed": "✅",
            "failed": "❌",
            "retrying": "🔁"
        }
        return icons.get(status, "❓")

    def _create_progress_bar(self, progress: float, width: int = 30) -> str:
        """Create text-based progress bar"""
        filled = int(progress * width)
        empty = width - filled
        bar = "█" * filled + "░" * empty
        percentage = f"{progress:.1%}"

        if progress >= 1.0:
            return f"[green]{bar}[/green] {percentage}"
        elif progress >= 0.5:
            return f"[yellow]{bar}[/yellow] {percentage}"
        else:
            return f"[red]{bar}[/red] {percentage}"

    def _create_mini_progress_bar(self, progress: float, width: int = 20) -> str:
        """Create mini progress bar"""
        filled = int(progress * width)
        empty = width - filled
        return "▓" * filled + "░" * empty

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"

    def update_metrics(self, event_data: Dict[str, Any]):
        """Update metrics from WebSocket event"""
        event_type = event_data.get("event")

        if event_type == "pipeline_started":
            self.start_time = time.time()
            self.metrics["pipeline_id"] = event_data.get("pipeline_id")
            self.metrics["spec_name"] = event_data.get("spec_name")

        elif event_type == "phase_started":
            phase = event_data.get("phase")
            self.phase_status[phase] = {
                "status": "in_progress",
                "progress": 0.0,
                "checkpoints_completed": 0,
                "checkpoints_total": event_data.get("checkpoints_total", 5)
            }

        elif event_type == "checkpoint_completed":
            phase = event_data.get("phase")
            checkpoint_name = event_data.get("checkpoint")

            self.checkpoints.append({
                "timestamp": datetime.now().isoformat(),
                "phase": phase,
                "name": checkpoint_name
            })

            if phase in self.phase_status:
                status = self.phase_status[phase]
                status["checkpoints_completed"] += 1
                status["progress"] = status["checkpoints_completed"] / status["checkpoints_total"]

            # Update specific metrics
            checkpoint_metrics = event_data.get("metrics", {})
            self.metrics.update(checkpoint_metrics)

        elif event_type == "phase_completed":
            phase = event_data.get("phase")
            if phase in self.phase_status:
                self.phase_status[phase]["status"] = "completed"
                self.phase_status[phase]["progress"] = 1.0
                self.phase_status[phase]["duration_ms"] = event_data.get("duration_ms", 0)

        elif event_type == "error_occurred":
            self.errors.append({
                "phase": event_data.get("phase"),
                "message": event_data.get("error"),
                "critical": event_data.get("critical", False)
            })

            self.metrics["total_errors"] = self.metrics.get("total_errors", 0) + 1
            if event_data.get("critical"):
                self.metrics["critical_errors"] = self.metrics.get("critical_errors", 0) + 1

        elif event_type == "recovery_successful":
            self.metrics["recovered_errors"] = self.metrics.get("recovered_errors", 0) + 1

        elif event_type == "pipeline_completed":
            self.metrics.update(event_data.get("final_metrics", {}))

    def create_layout(self) -> Layout:
        """Create dashboard layout"""
        layout = Layout()

        layout.split_column(
            Layout(self.create_header(), size=6, name="header"),
            Layout(name="body"),
            Layout(self.create_error_panel(), size=8, name="errors")
        )

        layout["body"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1)
        )

        layout["left"].split_column(
            Layout(self.create_phase_progress(), name="phases"),
            Layout(self.create_wave_execution_detail(), size=12, name="waves")
        )

        layout["right"].split_column(
            Layout(self.create_metrics_panel(), name="metrics"),
            Layout(self.create_checkpoint_log(), name="checkpoints")
        )

        return layout

    async def run_dashboard(self, websocket_url: str = "ws://localhost:8000/ws"):
        """Run the dashboard with WebSocket connection"""
        self.console.print("[bold green]Starting Pipeline Dashboard...[/bold green]")

        try:
            # Connect to WebSocket
            async with websockets.connect(websocket_url) as websocket:
                self.console.print(f"[green]Connected to {websocket_url}[/green]")

                with Live(self.create_layout(), refresh_per_second=2, console=self.console) as live:
                    while True:
                        try:
                            # Receive event
                            message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                            event_data = json.loads(message)

                            # Update metrics
                            self.update_metrics(event_data)

                            # Update display
                            live.update(self.create_layout())

                        except asyncio.TimeoutError:
                            # No message, just update display
                            live.update(self.create_layout())

                        except websockets.exceptions.ConnectionClosed:
                            self.console.print("[red]WebSocket connection closed[/red]")
                            break

        except Exception as e:
            self.console.print(f"[red]Dashboard error: {e}[/red]")

    def run_mock_dashboard(self, duration: int = 60):
        """Run dashboard with mock data for testing"""
        self.console.print("[bold yellow]Running Dashboard in Mock Mode[/bold yellow]")

        # Initialize mock pipeline
        self.start_time = time.time()
        self.metrics = {
            "pipeline_id": "pipeline_mock_12345",
            "spec_name": "test_spec.md",
            "patterns_matched": 0,
            "pattern_reuse_rate": 0.0,
            "test_coverage": 0.0,
            "code_quality_score": 0.0
        }

        # Initialize all phases as pending
        for phase in self.phases:
            self.phase_status[phase] = {
                "status": "pending",
                "progress": 0.0,
                "checkpoints_completed": 0,
                "checkpoints_total": 5
            }

        with Live(self.create_layout(), refresh_per_second=2, console=self.console) as live:
            # Simulate pipeline execution
            phase_idx = 0
            checkpoint_counter = 0

            for i in range(duration):
                # Start next phase
                if i % 6 == 0 and phase_idx < len(self.phases):
                    phase = self.phases[phase_idx]
                    self.phase_status[phase]["status"] = "in_progress"

                # Complete checkpoints
                if i % 2 == 0 and phase_idx < len(self.phases):
                    phase = self.phases[phase_idx]
                    status = self.phase_status[phase]

                    if status["checkpoints_completed"] < status["checkpoints_total"]:
                        status["checkpoints_completed"] += 1
                        status["progress"] = status["checkpoints_completed"] / status["checkpoints_total"]

                        self.checkpoints.append({
                            "timestamp": datetime.now().isoformat(),
                            "phase": phase,
                            "name": f"CP-{phase_idx+1}.{status['checkpoints_completed']}"
                        })

                        # Update some metrics
                        self.metrics["patterns_matched"] = min(25, self.metrics["patterns_matched"] + 2)
                        self.metrics["pattern_reuse_rate"] = min(0.65, i * 0.01)
                        self.metrics["test_coverage"] = min(0.85, i * 0.015)
                        self.metrics["code_quality_score"] = min(0.9, 0.5 + i * 0.008)
                        self.metrics["peak_memory_mb"] = 500 + i * 10
                        self.metrics["peak_cpu_percent"] = 30 + (i % 40)

                    # Complete phase
                    if status["checkpoints_completed"] == status["checkpoints_total"]:
                        status["status"] = "completed"
                        status["duration_ms"] = 2000 + phase_idx * 1000
                        phase_idx += 1

                # Simulate occasional errors
                if i % 15 == 0 and i > 0:
                    self.errors.append({
                        "phase": self.phases[min(phase_idx, len(self.phases)-1)],
                        "message": f"Mock error at {i}s",
                        "critical": i % 30 == 0
                    })
                    self.metrics["total_errors"] = len(self.errors)

                # Update display
                live.update(self.create_layout())
                time.sleep(1)

        self.console.print("[bold green]Dashboard simulation complete![/bold green]")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="E2E Pipeline Progress Dashboard")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode for testing")
    parser.add_argument("--duration", type=int, default=60, help="Mock mode duration in seconds")
    parser.add_argument("--ws-url", default="ws://localhost:8000/ws", help="WebSocket URL")

    args = parser.parse_args()

    dashboard = PipelineDashboard()

    if args.mock:
        dashboard.run_mock_dashboard(args.duration)
    else:
        asyncio.run(dashboard.run_dashboard(args.ws_url))


if __name__ == "__main__":
    main()