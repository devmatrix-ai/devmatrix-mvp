"""
Devmatrix CLI

Main command-line interface using Rich for beautiful terminal output.
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from pathlib import Path
import sys

from src.tools.workspace_manager import WorkspaceManager
from src.tools.file_operations import FileOperations
from src.tools.git_operations import GitOperations

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="devmatrix")
def cli():
    """
    🤖 Devmatrix - AI-Powered Development Assistant

    A command-line tool for managing AI agent workspaces and operations.
    """
    pass


@cli.command()
@click.argument("project_name")
@click.option("--path", default=".", help="Project path (default: current directory)")
def init(project_name: str, path: str):
    """
    Initialize a new Devmatrix project.

    Creates project structure and configuration files.
    """
    console.print(f"\n[bold cyan]Initializing project:[/bold cyan] {project_name}")

    project_path = Path(path).resolve() / project_name

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Creating project structure...", total=None)

        try:
            # Create project directory
            project_path.mkdir(parents=True, exist_ok=False)

            # Create subdirectories
            (project_path / "src").mkdir()
            (project_path / "tests").mkdir()
            (project_path / "docs").mkdir()

            # Create README
            readme_content = f"""# {project_name}

Devmatrix AI Agent Project

## Setup

```bash
devmatrix workspace create
```

## Usage

TODO: Add usage instructions
"""
            (project_path / "README.md").write_text(readme_content)

            # Create .gitignore
            gitignore_content = """.env
*.pyc
__pycache__/
.pytest_cache/
.coverage
htmlcov/
dist/
build/
*.egg-info/
"""
            (project_path / ".gitignore").write_text(gitignore_content)

            progress.update(task, completed=True)

            console.print(f"\n[bold green]✓[/bold green] Project created at: {project_path}")
            console.print("\n[dim]Next steps:[/dim]")
            console.print(f"  cd {project_name}")
            console.print("  devmatrix workspace create")

        except FileExistsError:
            console.print(f"\n[bold red]✗[/bold red] Project already exists at: {project_path}", style="red")
            sys.exit(1)
        except Exception as e:
            console.print(f"\n[bold red]✗[/bold red] Error: {e}", style="red")
            sys.exit(1)


@cli.group()
def workspace():
    """Manage temporary workspaces for agent operations."""
    pass


@workspace.command("create")
@click.option("--id", "workspace_id", help="Custom workspace ID")
def workspace_create(workspace_id: str):
    """Create a new temporary workspace."""
    try:
        ws = WorkspaceManager(workspace_id=workspace_id, auto_cleanup=False)
        ws.create()

        panel = Panel(
            f"[bold green]Workspace Created[/bold green]\n\n"
            f"ID: [cyan]{ws.workspace_id}[/cyan]\n"
            f"Path: [cyan]{ws.base_path}[/cyan]",
            title="✓ Success",
            border_style="green"
        )
        console.print(panel)

    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}", style="red")
        sys.exit(1)


@workspace.command("list")
def workspace_list():
    """List all active workspaces."""
    import os

    workspaces = []
    tmp_dir = Path("/tmp")

    for item in tmp_dir.glob("devmatrix-workspace-*"):
        if item.is_dir():
            workspace_id = item.name.replace("devmatrix-workspace-", "")
            size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
            workspaces.append({
                "id": workspace_id,
                "path": str(item),
                "size": f"{size / 1024:.2f} KB"
            })

    if not workspaces:
        console.print("[yellow]No active workspaces found[/yellow]")
        return

    table = Table(title="Active Workspaces", show_header=True, header_style="bold cyan")
    table.add_column("ID", style="cyan")
    table.add_column("Path", style="dim")
    table.add_column("Size", justify="right")

    for ws in workspaces:
        table.add_row(ws["id"], ws["path"], ws["size"])

    console.print(table)


@workspace.command("clean")
@click.option("--all", is_flag=True, help="Clean all workspaces")
@click.option("--id", "workspace_id", help="Specific workspace ID to clean")
def workspace_clean(all: bool, workspace_id: str):
    """Clean up temporary workspaces."""
    if not all and not workspace_id:
        console.print("[red]Specify --all or --id <workspace_id>[/red]")
        sys.exit(1)

    tmp_dir = Path("/tmp")

    if all:
        workspaces = list(tmp_dir.glob("devmatrix-workspace-*"))
        if not workspaces:
            console.print("[yellow]No workspaces to clean[/yellow]")
            return

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Cleaning {len(workspaces)} workspaces...", total=len(workspaces))

            for ws_path in workspaces:
                ws_id = ws_path.name.replace("devmatrix-workspace-", "")
                ws = WorkspaceManager(workspace_id=ws_id, auto_cleanup=False)
                ws.cleanup()
                progress.advance(task)

        console.print(f"[green]✓ Cleaned {len(workspaces)} workspaces[/green]")

    elif workspace_id:
        ws = WorkspaceManager(workspace_id=workspace_id, auto_cleanup=False)
        if ws.base_path.exists():
            ws.cleanup()
            console.print(f"[green]✓ Cleaned workspace: {workspace_id}[/green]")
        else:
            console.print(f"[yellow]Workspace not found: {workspace_id}[/yellow]")


@cli.group()
def files():
    """File operations within workspaces."""
    pass


@files.command("list")
@click.argument("workspace_id")
@click.option("--pattern", default="*", help="Glob pattern (default: *)")
def files_list(workspace_id: str, pattern: str):
    """List files in a workspace."""
    try:
        ws = WorkspaceManager(workspace_id=workspace_id, auto_cleanup=False)

        if not ws.base_path.exists():
            console.print(f"[red]Workspace not found: {workspace_id}[/red]")
            sys.exit(1)

        file_ops = FileOperations(str(ws.base_path))
        files = file_ops.list_files("", pattern, recursive=True)

        if not files:
            console.print(f"[yellow]No files found matching '{pattern}'[/yellow]")
            return

        table = Table(title=f"Files in {workspace_id}", show_header=True, header_style="bold cyan")
        table.add_column("File", style="cyan")
        table.add_column("Size", justify="right")

        for file_path in files:
            info = file_ops.get_file_info(file_path)
            table.add_row(file_path, f"{info['size']} bytes")

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@files.command("read")
@click.argument("workspace_id")
@click.argument("file_path")
@click.option("--syntax", help="Syntax highlighting (python, javascript, etc.)")
def files_read(workspace_id: str, file_path: str, syntax: str):
    """Read and display a file from workspace."""
    try:
        ws = WorkspaceManager(workspace_id=workspace_id, auto_cleanup=False)

        if not ws.base_path.exists():
            console.print(f"[red]Workspace not found: {workspace_id}[/red]")
            sys.exit(1)

        file_ops = FileOperations(str(ws.base_path))
        content = file_ops.read_file(file_path)

        if syntax:
            syntax_obj = Syntax(content, syntax, theme="monokai", line_numbers=True)
            console.print(syntax_obj)
        else:
            console.print(Panel(content, title=file_path, border_style="cyan"))

    except FileNotFoundError:
        console.print(f"[red]File not found: {file_path}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.group()
def git():
    """Git operations and status."""
    pass


@git.command("status")
@click.option("--repo", default=".", help="Repository path (default: current directory)")
def git_status(repo: str):
    """Show git repository status with Rich formatting."""
    try:
        git_ops = GitOperations(repo)
        status = git_ops.get_status()

        # Create status panel
        status_text = f"[bold]Branch:[/bold] {status.branch}\n"
        status_text += f"[bold]Status:[/bold] {'[green]Clean[/green]' if status.is_clean else '[yellow]Modified[/yellow]'}\n"

        if status.ahead > 0 or status.behind > 0:
            status_text += f"[bold]Sync:[/bold] "
            if status.ahead > 0:
                status_text += f"[green]↑{status.ahead}[/green] "
            if status.behind > 0:
                status_text += f"[red]↓{status.behind}[/red]"
            status_text += "\n"

        panel = Panel(status_text, title="Git Status", border_style="cyan")
        console.print(panel)

        # Show changes if any
        if not status.is_clean:
            if status.staged_files:
                table = Table(title="Staged Changes", show_header=False, border_style="green")
                for file in status.staged_files:
                    table.add_row("[green]+[/green]", file)
                console.print(table)

            if status.modified_files:
                table = Table(title="Modified Files", show_header=False, border_style="yellow")
                for file in status.modified_files:
                    table.add_row("[yellow]M[/yellow]", file)
                console.print(table)

            if status.untracked_files:
                table = Table(title="Untracked Files", show_header=False, border_style="red")
                for file in status.untracked_files:
                    table.add_row("[red]?[/red]", file)
                console.print(table)

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("request")
@click.option("--context", help="Additional context as JSON string")
@click.option("--save", is_flag=True, help="Save plan to file")
def plan(request: str, context: str, save: bool):
    """
    Create a development plan from a request.

    Uses AI to break down your request into actionable tasks.
    """
    try:
        from src.agents.planning_agent import PlanningAgent
        import json

        console.print(f"\n[bold cyan]Planning:[/bold cyan] {request}\n")

        # Parse context if provided
        context_dict = {}
        if context:
            try:
                context_dict = json.loads(context)
            except json.JSONDecodeError:
                console.print("[yellow]Warning: Invalid JSON context, ignoring[/yellow]")

        # Create planning agent
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Analyzing request...", total=None)

            agent = PlanningAgent()
            result = agent.plan(request, context_dict)

            progress.update(task, description="Plan generated!")

        # Display plan
        formatted_plan = agent.format_plan(result)
        panel = Panel(formatted_plan, title="Development Plan", border_style="green")
        console.print(panel)

        # Save if requested
        if save:
            import json
            from datetime import datetime
            from pathlib import Path

            plans_dir = Path("plans")
            plans_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"plan_{timestamp}.json"

            with open(plans_dir / filename, "w") as f:
                json.dump(result, f, indent=2)

            console.print(f"\n[green]✓ Plan saved to: {plans_dir / filename}[/green]")

    except ValueError as e:
        console.print(f"[red]Configuration Error: {e}[/red]")
        console.print("\n[yellow]Make sure to set ANTHROPIC_API_KEY in .env file[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@cli.command()
@click.argument("request")
@click.option("--workspace", "-w", help="Workspace ID (auto-generated if not provided)")
@click.option("--context", help="Additional context as JSON string")
@click.option("--git/--no-git", default=True, help="Enable/disable auto-commit to Git (default: enabled)")
def generate(request: str, workspace: str, context: str, git: bool):
    """
    Generate Python code with AI assistance and human approval.

    Uses CodeGenerationAgent to create code based on your request,
    with interactive approval gates for quality control and optional Git integration.

    Example:
        devmatrix generate "Create a function to calculate fibonacci numbers"
        devmatrix generate "Add authentication module" --no-git
    """
    try:
        from src.agents.code_generation_agent import CodeGenerationAgent
        import json

        console.print(f"\n[bold cyan]Code Generation:[/bold cyan] {request}\n")

        # Parse context if provided
        context_dict = {}
        if context:
            try:
                context_dict = json.loads(context)
            except json.JSONDecodeError:
                console.print("[yellow]Warning: Invalid JSON context, ignoring[/yellow]")

        # Create agent
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Initializing agent...", total=None)

            agent = CodeGenerationAgent()

            progress.update(task, description="Generating code...")

            # Generate code (includes interactive approval and optional git commit)
            result = agent.generate(
                user_request=request,
                workspace_id=workspace,
                context=context_dict,
                git_enabled=git
            )

            progress.update(task, description="Complete!")

        # Display results
        if result["approval_status"] == "approved":
            # Build success message
            success_msg = (
                f"[bold green]✓ Code Generated and Approved[/bold green]\n\n"
                f"File: [cyan]{result['file_path']}[/cyan]\n"
                f"Workspace: [cyan]{result['workspace_id']}[/cyan]\n"
                f"Quality Score: [{'green' if result['quality_score'] >= 8 else 'yellow'}]{result['quality_score']}/10[/]\n"
            )

            # Add git info if committed
            if result.get("git_committed", False):
                success_msg += (
                    f"\n[bold green]✓ Git Commit:[/bold green]\n"
                    f"  Hash: [cyan]{result['git_commit_hash']}[/cyan]\n"
                    f"  Message: [dim]{result['git_commit_message']}[/dim]\n"
                )

            success_msg += (
                f"\n[dim]Next steps:[/dim]\n"
                f"  • Review the generated file\n"
                f"  • Run tests if needed\n"
            )

            if result.get("git_committed", False):
                success_msg += f"  • Push with: cd {result['workspace_id']} && git push"
            else:
                success_msg += f"  • Commit with: devmatrix git status"

            panel = Panel(
                success_msg,
                title="✓ Success",
                border_style="green"
            )
            console.print(panel)

        elif result["approval_status"] == "rejected":
            console.print(Panel(
                "[bold red]Code generation rejected[/bold red]\n\n"
                "No files were written.",
                title="✗ Rejected",
                border_style="red"
            ))

        else:
            console.print(Panel(
                f"[bold yellow]Status: {result['approval_status']}[/bold yellow]",
                title="ℹ Info",
                border_style="yellow"
            ))

    except ValueError as e:
        console.print(f"[red]Configuration Error: {e}[/red]")
        console.print("\n[yellow]Make sure to set ANTHROPIC_API_KEY in .env file[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@cli.command()
def info():
    """Show Devmatrix system information."""
    from datetime import datetime

    info_text = f"""[bold cyan]Devmatrix v0.1.0[/bold cyan]

[bold]Status:[/bold] Active
[bold]Python:[/bold] {sys.version.split()[0]}
[bold]Time:[/bold] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

[bold]Components:[/bold]
  • WorkspaceManager: Temporary workspace isolation
  • FileOperations: Safe file manipulation
  • GitOperations: Version control integration
  • PlanningAgent: AI-powered task planning
  • Rich CLI: Beautiful terminal interface

[dim]Use --help with any command for more information[/dim]
"""

    panel = Panel(info_text, title="🤖 Devmatrix Info", border_style="cyan")
    console.print(panel)


if __name__ == "__main__":
    cli()
