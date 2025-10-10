#!/usr/bin/env python3
"""
Stateful Workflow Example

Demonstrates LangGraph workflow with Redis + PostgreSQL state persistence.

Usage:
    python examples/stateful_example.py
    python examples/stateful_example.py "Create a sorting algorithm"
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.workflows.stateful_workflow import StatefulWorkflow
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax


def main():
    """Run stateful workflow example."""
    console = Console()

    # Get user request
    if len(sys.argv) > 1:
        user_request = " ".join(sys.argv[1:])
    else:
        user_request = "Create a hello world function"

    console.print("\n[bold blue]╔════════════════════════════════════════╗[/bold blue]")
    console.print("[bold blue]║   Devmatrix - Stateful Workflow Demo  ║[/bold blue]")
    console.print("[bold blue]╚════════════════════════════════════════╝[/bold blue]\n")

    # Display request
    console.print(
        Panel(
            user_request,
            title="[bold cyan]User Request[/bold cyan]",
            border_style="cyan",
        )
    )

    # Create workflow
    console.print("\n[yellow]⚙️  Initializing stateful workflow...[/yellow]")

    try:
        workflow = StatefulWorkflow()

        console.print("[green]✓ Connected to Redis[/green]")
        console.print("[green]✓ Connected to PostgreSQL[/green]")

        # Run workflow
        console.print("\n[yellow]⚡ Executing workflow with state persistence...[/yellow]\n")

        final_state, project_id, task_id = workflow.run_workflow(
            user_request=user_request,
            project_name="Stateful Demo",
            project_description="Testing Redis + PostgreSQL integration",
        )

        # Display success
        console.print("[bold green]✓ Workflow completed successfully![/bold green]\n")

        # Show workflow metadata
        metadata_table = Table(title="[bold magenta]Workflow Metadata[/bold magenta]")
        metadata_table.add_column("Field", style="cyan")
        metadata_table.add_column("Value", style="yellow")

        metadata_table.add_row("Workflow ID", final_state["workflow_id"])
        metadata_table.add_row("Project ID", str(project_id))
        metadata_table.add_row("Task ID", str(task_id))
        metadata_table.add_row("Agent Name", final_state["agent_name"])
        metadata_table.add_row("Current Task", final_state["current_task"])
        metadata_table.add_row("Messages", str(len(final_state["messages"])))

        console.print(metadata_table)

        # Show messages
        if final_state["messages"]:
            console.print("\n[bold yellow]📝 Agent Messages:[/bold yellow]")
            for idx, msg in enumerate(final_state["messages"], 1):
                console.print(
                    Panel(
                        f"[cyan]Agent:[/cyan] {msg.get('agent', 'unknown')}\n"
                        f"[cyan]Time:[/cyan] {msg.get('timestamp', 'unknown')}\n\n"
                        f"{msg['content']}",
                        title=f"[bold]Message {idx}[/bold]",
                        border_style="yellow",
                    )
                )

        # Show generated code
        if final_state["generated_code"]:
            console.print("\n[bold green]💻 Generated Code:[/bold green]")
            syntax = Syntax(
                final_state["generated_code"],
                "python",
                theme="monokai",
                line_numbers=True,
            )
            console.print(Panel(syntax, border_style="green"))

        # Verify Redis state
        console.print("\n[bold blue]🔍 Verifying State Persistence:[/bold blue]\n")

        redis_state = workflow.get_workflow_state_from_redis(
            final_state["workflow_id"]
        )
        if redis_state:
            console.print("[green]✓ State found in Redis[/green]")
        else:
            console.print("[red]✗ State not found in Redis[/red]")

        # Verify PostgreSQL task
        postgres_task = workflow.get_task_from_postgres(task_id)
        if postgres_task:
            console.print("[green]✓ Task found in PostgreSQL[/green]")

            task_table = Table(title="[bold cyan]PostgreSQL Task Details[/bold cyan]")
            task_table.add_column("Field", style="cyan")
            task_table.add_column("Value", style="yellow")

            task_table.add_row("Task ID", str(postgres_task["id"]))
            task_table.add_row("Status", postgres_task["status"])
            task_table.add_row("Agent Name", postgres_task["agent_name"])
            task_table.add_row("Task Type", postgres_task["task_type"])
            task_table.add_row("Created At", str(postgres_task["created_at"]))
            task_table.add_row("Completed At", str(postgres_task["completed_at"]))

            console.print(f"\n{task_table}")
        else:
            console.print("[red]✗ Task not found in PostgreSQL[/red]")

        # Demo cost tracking
        console.print("\n[bold magenta]💰 Tracking LLM Cost:[/bold magenta]")

        cost_id = workflow.track_llm_cost(
            task_id=task_id,
            model_name="claude-sonnet-4.5",
            input_tokens=150,
            output_tokens=50,
            cost_usd=0.003,
        )

        console.print(f"[green]✓ Cost tracked: {cost_id}[/green]")
        console.print("[dim]  Model: claude-sonnet-4.5[/dim]")
        console.print("[dim]  Tokens: 150 in, 50 out[/dim]")
        console.print("[dim]  Cost: $0.003[/dim]")

        # Get project costs
        project_costs = workflow.postgres.get_project_costs(project_id)
        console.print(
            f"\n[bold]Project Total Cost:[/bold] ${project_costs.get('total_cost', 0):.4f}"
        )

        # Cleanup
        workflow.close()
        console.print("\n[dim]✓ Connections closed[/dim]")

    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        import traceback

        console.print(f"\n[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)

    console.print("\n[bold blue]✨ Example completed![/bold blue]\n")


if __name__ == "__main__":
    main()
