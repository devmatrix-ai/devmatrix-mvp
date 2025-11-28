"""
Rich Progress Demo - Interactive E2E Pipeline Console
Shows what an animated progress interface could look like
"""
import asyncio
import time
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.style import Style

console = Console()

# Pipeline phases with estimated steps
PHASES = [
    ("1. Spec Parsing", 3),
    ("2. Business Logic", 5),
    ("3. Normalization", 4),
    ("4. IR Building", 6),
    ("5. Validation", 8),
    ("6. Code Generation", 15),
    ("7. Post-Processing", 5),
    ("8. Deployment", 4),
    ("8.5. Smoke Tests", 10),
    ("9. Quality Gate", 3),
]


def create_status_table(phase_states: dict, current_phase: str, metrics: dict) -> Table:
    """Create a status table showing all phases"""
    table = Table(title="🚀 E2E Pipeline Status", show_header=True, header_style="bold magenta")
    table.add_column("Phase", style="cyan", width=25)
    table.add_column("Status", justify="center", width=12)
    table.add_column("Progress", justify="center", width=15)
    table.add_column("Time", justify="right", width=10)

    status_icons = {
        "pending": "⏳",
        "running": "🔄",
        "completed": "✅",
        "failed": "❌",
    }

    for phase_name, _ in PHASES:
        state = phase_states.get(phase_name, {"status": "pending", "progress": 0, "time": "-"})
        status = state["status"]
        icon = status_icons.get(status, "❓")

        if phase_name == current_phase and status == "running":
            style = Style(bold=True, color="yellow")
            progress_bar = f"[yellow]{'█' * int(state['progress'] / 10)}{'░' * (10 - int(state['progress'] / 10))}[/] {state['progress']}%"
        elif status == "completed":
            style = Style(color="green")
            progress_bar = "[green]██████████[/] 100%"
        elif status == "failed":
            style = Style(color="red")
            progress_bar = f"[red]{'█' * int(state['progress'] / 10)}{'░' * (10 - int(state['progress'] / 10))}[/] {state['progress']}%"
        else:
            style = Style(dim=True)
            progress_bar = "[dim]░░░░░░░░░░[/] 0%"

        table.add_row(
            phase_name,
            f"{icon} {status.upper()}",
            progress_bar,
            state.get("time", "-"),
            style=style
        )

    return table


def create_metrics_panel(metrics: dict) -> Panel:
    """Create a metrics panel"""
    content = Text()
    content.append("📊 Current Metrics\n\n", style="bold")
    content.append(f"  Files Generated: ", style="dim")
    content.append(f"{metrics.get('files', 0)}\n", style="cyan")
    content.append(f"  Lines of Code: ", style="dim")
    content.append(f"{metrics.get('loc', 0):,}\n", style="cyan")
    content.append(f"  LLM Tokens: ", style="dim")
    content.append(f"{metrics.get('tokens', 0):,}\n", style="yellow")
    content.append(f"  Endpoints: ", style="dim")
    content.append(f"{metrics.get('endpoints', 0)}\n", style="green")
    content.append(f"  Tests Passed: ", style="dim")
    content.append(f"{metrics.get('tests_passed', 0)}/{metrics.get('tests_total', 0)}\n", style="green")

    return Panel(content, title="[bold blue]Metrics[/]", border_style="blue")


def create_activity_panel(activities: list) -> Panel:
    """Create an activity log panel"""
    content = Text()
    for activity in activities[-8:]:  # Show last 8 activities
        timestamp, message, style = activity
        content.append(f"[{timestamp}] ", style="dim")
        content.append(f"{message}\n", style=style)

    return Panel(content, title="[bold green]Activity Log[/]", border_style="green")


def create_layout(phase_states: dict, current_phase: str, metrics: dict, activities: list) -> Layout:
    """Create the full layout"""
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3),
    )

    layout["body"].split_row(
        Layout(name="main", ratio=2),
        Layout(name="sidebar", ratio=1),
    )

    layout["sidebar"].split_column(
        Layout(name="metrics"),
        Layout(name="activity"),
    )

    # Header
    header_text = Text()
    header_text.append("🏗️  DevMatrix E2E Pipeline ", style="bold magenta")
    header_text.append("| ", style="dim")
    header_text.append("ecommerce-api-spec-human.md", style="cyan")
    layout["header"].update(Panel(header_text, style="bold"))

    # Main content - phase table
    layout["main"].update(create_status_table(phase_states, current_phase, metrics))

    # Sidebar - metrics and activity
    layout["metrics"].update(create_metrics_panel(metrics))
    layout["activity"].update(create_activity_panel(activities))

    # Footer
    footer_text = Text()
    footer_text.append("Press ", style="dim")
    footer_text.append("Ctrl+C", style="bold red")
    footer_text.append(" to cancel | ", style="dim")
    footer_text.append("Running for: ", style="dim")
    footer_text.append(f"{metrics.get('elapsed', '0:00')}", style="yellow")
    layout["footer"].update(Panel(footer_text, style="dim"))

    return layout


async def simulate_pipeline():
    """Simulate the E2E pipeline with Rich progress"""
    phase_states = {}
    activities = []
    metrics = {
        "files": 0,
        "loc": 0,
        "tokens": 0,
        "endpoints": 0,
        "tests_passed": 0,
        "tests_total": 0,
        "elapsed": "0:00"
    }
    start_time = time.time()

    def add_activity(message: str, style: str = "white"):
        timestamp = time.strftime("%H:%M:%S")
        activities.append((timestamp, message, style))

    add_activity("🚀 Starting E2E Pipeline...", "bold green")
    add_activity("🧹 Clearing caches...", "yellow")

    with Live(create_layout(phase_states, "", metrics, activities), refresh_per_second=4, console=console) as live:
        for phase_name, steps in PHASES:
            # Update elapsed time
            elapsed = int(time.time() - start_time)
            metrics["elapsed"] = f"{elapsed // 60}:{elapsed % 60:02d}"

            # Mark phase as running
            phase_states[phase_name] = {"status": "running", "progress": 0, "time": "-"}
            add_activity(f"▶️  Starting {phase_name}", "cyan")
            live.update(create_layout(phase_states, phase_name, metrics, activities))

            phase_start = time.time()

            # Simulate steps within phase
            for step in range(steps):
                progress = int((step + 1) / steps * 100)
                phase_states[phase_name]["progress"] = progress

                # Update metrics based on phase
                if "Code Generation" in phase_name:
                    metrics["files"] += 2
                    metrics["loc"] += 150
                    metrics["tokens"] += 500
                elif "Smoke Tests" in phase_name:
                    metrics["tests_total"] += 1
                    if step % 3 != 2:  # 66% pass rate simulation
                        metrics["tests_passed"] += 1
                elif "IR Building" in phase_name:
                    metrics["endpoints"] += 3

                elapsed = int(time.time() - start_time)
                metrics["elapsed"] = f"{elapsed // 60}:{elapsed % 60:02d}"

                live.update(create_layout(phase_states, phase_name, metrics, activities))
                await asyncio.sleep(0.15)  # Simulate work

            # Mark phase as completed
            phase_time = f"{time.time() - phase_start:.1f}s"
            phase_states[phase_name] = {"status": "completed", "progress": 100, "time": phase_time}
            add_activity(f"✅ Completed {phase_name} ({phase_time})", "green")
            live.update(create_layout(phase_states, phase_name, metrics, activities))

        # Final summary
        add_activity("🎉 Pipeline completed successfully!", "bold green")
        live.update(create_layout(phase_states, "", metrics, activities))
        await asyncio.sleep(2)

    # Print final summary
    console.print()
    console.print(Panel.fit(
        f"[bold green]✅ E2E Pipeline Completed![/]\n\n"
        f"📁 Files: {metrics['files']} | 📝 LOC: {metrics['loc']:,} | 🎯 Endpoints: {metrics['endpoints']}\n"
        f"🧪 Tests: {metrics['tests_passed']}/{metrics['tests_total']} passed | ⏱️  Total: {metrics['elapsed']}",
        title="Summary",
        border_style="green"
    ))


# Simple progress bar alternative (less fancy but still nice)
async def simple_progress_demo():
    """Simpler progress bar demo"""
    console.print("[bold cyan]🚀 E2E Pipeline - Simple Progress Mode[/]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:

        overall = progress.add_task("[bold]Overall Progress", total=len(PHASES))

        for phase_name, steps in PHASES:
            phase_task = progress.add_task(f"  {phase_name}", total=steps)

            for _ in range(steps):
                await asyncio.sleep(0.1)
                progress.advance(phase_task)

            progress.update(phase_task, description=f"  [green]✓[/] {phase_name}")
            progress.advance(overall)

    console.print("\n[bold green]✅ Pipeline completed![/]")


if __name__ == "__main__":
    import sys

    console.print(Panel.fit(
        "[bold]Rich Progress Demo[/]\n\n"
        "1. [cyan]Full Dashboard[/] - Fancy layout with metrics and activity log\n"
        "2. [cyan]Simple Progress[/] - Clean progress bars only",
        title="Choose Demo Mode"
    ))

    choice = console.input("\nSelect mode [1/2]: ").strip()

    if choice == "2":
        asyncio.run(simple_progress_demo())
    else:
        asyncio.run(simulate_pipeline())
