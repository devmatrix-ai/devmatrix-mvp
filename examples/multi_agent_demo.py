"""
Multi-Agent Workflow Demo

Demonstrates complete multi-agent system with:
- Orchestrator decomposing projects into tasks
- Specialized agents (Implementation, Testing, Documentation)
- Parallel task execution
- Inter-agent communication via SharedScratchpad
- LangGraph workflow orchestration

Example usage:
    python examples/multi_agent_demo.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.workflows.multi_agent_workflow import MultiAgentWorkflow
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn


console = Console()


def print_header():
    """Print demo header."""
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]Multi-Agent System Demo[/bold cyan]\n"
        "[dim]Orchestrator + Specialized Agents + Parallel Execution[/dim]",
        border_style="cyan"
    ))
    console.print("\n")


def print_project_request(request: str):
    """Print project request."""
    console.print(Panel(
        f"[bold]Project Request:[/bold]\n{request}",
        title="📋 Input",
        border_style="blue"
    ))
    console.print("\n")


def print_workflow_steps():
    """Print workflow steps."""
    tree = Tree("🔄 [bold]Workflow Steps[/bold]")

    plan_branch = tree.add("1️⃣ [cyan]Planning Phase[/cyan]")
    plan_branch.add("• OrchestratorAgent decomposes project into tasks")
    plan_branch.add("• Identifies dependencies between tasks")
    plan_branch.add("• Creates execution plan")

    execute_branch = tree.add("2️⃣ [green]Execution Phase[/green]")
    execute_branch.add("• AgentRegistry routes tasks to specialized agents")
    execute_branch.add("• ParallelExecutor runs independent tasks concurrently")
    execute_branch.add("• Agents communicate via SharedScratchpad")
    execute_branch.add("• Error propagation for dependent tasks")

    finalize_branch = tree.add("3️⃣ [yellow]Finalization Phase[/yellow]")
    finalize_branch.add("• Collect all artifacts from scratchpad")
    finalize_branch.add("• Aggregate results and statistics")
    finalize_branch.add("• Prepare final output")

    console.print(Panel(tree, border_style="dim"))
    console.print("\n")


def print_results(result: dict):
    """Print workflow results."""
    console.print(Panel.fit(
        f"[bold]Status:[/bold] {result['status']}\n"
        f"[bold]Success:[/bold] {result['success']}",
        title="✅ Workflow Complete",
        border_style="green" if result['success'] else "red"
    ))
    console.print("\n")

    # Print tasks summary
    if result['tasks']:
        table = Table(title="📋 Tasks Summary", show_header=True)
        table.add_column("Task ID", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Type", style="magenta")
        table.add_column("Status", style="green")

        completed = set(result['completed_tasks'])
        failed = set(result['failed_tasks'])

        for task in result['tasks']:
            task_id = task['id']
            status = "✅ Completed" if task_id in completed else "❌ Failed" if task_id in failed else "⏳ Pending"
            table.add_row(
                task_id,
                task['description'][:50] + "..." if len(task['description']) > 50 else task['description'],
                task.get('task_type', 'unknown'),
                status
            )

        console.print(table)
        console.print("\n")

    # Print execution stats
    if result['execution_stats']:
        stats = result['execution_stats']
        stats_table = Table(title="📊 Execution Statistics", show_header=True)
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="yellow")

        stats_table.add_row("Total Tasks", str(stats.get('total_tasks', 0)))
        stats_table.add_row("Successful", str(stats.get('successful', 0)))
        stats_table.add_row("Failed", str(stats.get('failed', 0)))
        stats_table.add_row("Skipped", str(stats.get('skipped', 0)))
        stats_table.add_row("Total Time", f"{stats.get('total_time', 0):.2f}s")

        if stats.get('parallel_time_saved', 0) > 0:
            stats_table.add_row(
                "Parallel Time Saved",
                f"[green]{stats['parallel_time_saved']:.2f}s[/green]"
            )

        console.print(stats_table)
        console.print("\n")

    # Print messages
    if result['messages']:
        console.print("[bold]Workflow Messages:[/bold]")
        for msg in result['messages']:
            console.print(f"  {msg}")
        console.print("\n")


def run_calculator_demo():
    """Run calculator project demo."""
    console.rule("[bold cyan]Demo 1: Calculator with Tests and Docs[/bold cyan]")
    console.print("\n")

    project_request = """
    Build a Python calculator module with the following features:
    1. A Calculator class with basic operations (add, subtract, multiply, divide)
    2. Comprehensive pytest test suite with fixtures and edge cases
    3. Complete documentation with docstrings and README
    """

    print_project_request(project_request)
    print_workflow_steps()

    # Create workflow
    console.print("[dim]Initializing multi-agent workflow...[/dim]")
    workflow = MultiAgentWorkflow(workspace_id="calculator-demo")

    # Run workflow with progress indicator
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Running multi-agent workflow...", total=None)
        result = workflow.run(project_request)
        progress.update(task, completed=True)

    console.print("\n")
    print_results(result)


def run_api_demo():
    """Run REST API project demo."""
    console.rule("[bold cyan]Demo 2: REST API with Authentication[/bold cyan]")
    console.print("\n")

    project_request = """
    Create a simple REST API with user authentication:
    1. User registration and login endpoints
    2. JWT token-based authentication
    3. Unit tests for all endpoints
    4. API documentation with usage examples
    """

    print_project_request(project_request)

    # Create workflow
    workflow = MultiAgentWorkflow(workspace_id="api-demo")

    # Run workflow
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Running multi-agent workflow...", total=None)
        result = workflow.run(project_request)
        progress.update(task, completed=True)

    console.print("\n")
    print_results(result)


def run_simple_demo():
    """Run simple function demo."""
    console.rule("[bold cyan]Demo 3: Simple Utility Function[/bold cyan]")
    console.print("\n")

    project_request = """
    Create a utility function to calculate Fibonacci numbers:
    1. Implement efficient fibonacci function with memoization
    2. Write pytest tests including edge cases
    3. Add comprehensive docstrings
    """

    print_project_request(project_request)

    # Create workflow
    workflow = MultiAgentWorkflow(workspace_id="fibonacci-demo")

    # Run workflow
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Running multi-agent workflow...", total=None)
        result = workflow.run(project_request)
        progress.update(task, completed=True)

    console.print("\n")
    print_results(result)


def print_system_architecture():
    """Print system architecture overview."""
    console.rule("[bold cyan]System Architecture[/bold cyan]")
    console.print("\n")

    tree = Tree("🏗️ [bold]Multi-Agent System Components[/bold]")

    # Orchestration Layer
    orch_branch = tree.add("🎯 [cyan]Orchestration Layer[/cyan]")
    orch_branch.add("• MultiAgentWorkflow (LangGraph StateGraph)")
    orch_branch.add("• OrchestratorAgent (Task decomposition)")
    orch_branch.add("• AgentRegistry (Capability-based routing)")

    # Execution Layer
    exec_branch = tree.add("⚙️ [green]Execution Layer[/green]")
    exec_branch.add("• ParallelExecutor (ThreadPoolExecutor)")
    exec_branch.add("• Dependency resolution (Topological sort)")
    exec_branch.add("• Error propagation")

    # Agent Layer
    agent_branch = tree.add("🤖 [magenta]Specialized Agents[/magenta]")
    agent_branch.add("• ImplementationAgent (CODE_GENERATION)")
    agent_branch.add("• TestingAgent (UNIT_TESTING)")
    agent_branch.add("• DocumentationAgent (API_DOCUMENTATION)")

    # Communication Layer
    comm_branch = tree.add("💬 [yellow]Communication Layer[/yellow]")
    comm_branch.add("• SharedScratchpad (Redis-backed)")
    comm_branch.add("• Artifact system (8 types)")
    comm_branch.add("• Task status tracking")

    # State Layer
    state_branch = tree.add("💾 [blue]State Layer[/blue]")
    state_branch.add("• RedisManager (Workflow state)")
    state_branch.add("• PostgresManager (Task history)")
    state_branch.add("• WorkspaceManager (File operations)")

    console.print(Panel(tree, border_style="dim"))
    console.print("\n")


def main():
    """Run multi-agent demo."""
    print_header()
    print_system_architecture()

    # Run demos
    try:
        run_calculator_demo()

        console.print("\n")
        if console.input("[bold]Run API demo? (y/n): [/bold]").lower() == 'y':
            run_api_demo()

        console.print("\n")
        if console.input("[bold]Run simple demo? (y/n): [/bold]").lower() == 'y':
            run_simple_demo()

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Demo interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n\n[red]Error: {str(e)}[/red]")
        import traceback
        console.print(traceback.format_exc())

    console.print("\n")
    console.print(Panel.fit(
        "[bold green]Demo Complete![/bold green]\n"
        "[dim]Check workspace directories for generated files[/dim]",
        border_style="green"
    ))


if __name__ == "__main__":
    main()
