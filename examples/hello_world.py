#!/usr/bin/env python3
"""
LangGraph Hello World Example

This script demonstrates the minimal LangGraph workflow in Devmatrix.

Usage:
    python examples/hello_world.py
    python examples/hello_world.py "Create a Python function to calculate fibonacci"
"""

import sys
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.workflows.hello_workflow import run_hello_workflow
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax


def main():
    """Run the hello world workflow example."""
    console = Console()

    # Get user request from command line or use default
    if len(sys.argv) > 1:
        user_request = " ".join(sys.argv[1:])
    else:
        user_request = "Create a hello world function"

    console.print("\n[bold blue]╔══════════════════════════════════════╗[/bold blue]")
    console.print("[bold blue]║   Devmatrix - LangGraph Hello World  ║[/bold blue]")
    console.print("[bold blue]╚══════════════════════════════════════╝[/bold blue]\n")

    # Display user request
    console.print(
        Panel(
            user_request,
            title="[bold cyan]User Request[/bold cyan]",
            border_style="cyan",
        )
    )

    # Run the workflow
    console.print("\n[yellow]⚡ Executing workflow...[/yellow]\n")

    try:
        final_state = run_hello_workflow(user_request, workflow_id="example-001")

        # Display results
        console.print("[bold green]✓ Workflow completed successfully![/bold green]\n")

        # Show workflow metadata
        console.print(
            Panel(
                f"[cyan]Workflow ID:[/cyan] {final_state['workflow_id']}\n"
                f"[cyan]Agent Name:[/cyan] {final_state['agent_name']}\n"
                f"[cyan]Current Task:[/cyan] {final_state['current_task']}\n"
                f"[cyan]Messages:[/cyan] {len(final_state['messages'])} message(s)",
                title="[bold magenta]Workflow Metadata[/bold magenta]",
                border_style="magenta",
            )
        )

        # Show messages
        if final_state["messages"]:
            console.print("\n[bold yellow]📝 Agent Messages:[/bold yellow]")
            for idx, msg in enumerate(final_state["messages"], 1):
                console.print(
                    Panel(
                        msg["content"],
                        title=f"[bold]Message {idx} - {msg['role'].upper()}[/bold]",
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

    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        import traceback

        console.print(f"\n[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)

    console.print("\n[bold blue]✨ Example completed![/bold blue]\n")


if __name__ == "__main__":
    main()
