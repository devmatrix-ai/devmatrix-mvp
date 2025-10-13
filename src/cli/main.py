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
# Create a workspace for your project
devmatrix workspace create --id {project_name}

# Set your API key
export ANTHROPIC_API_KEY="your-key-here"
```

## Usage

### Planning
Generate a development plan:
```bash
devmatrix plan "Your project description"
```

### Code Generation
Generate code with AI assistance:
```bash
devmatrix generate "Your code request" --workspace {project_name}
```

### Multi-Agent Orchestration
Build complete projects with specialized agents:
```bash
devmatrix orchestrate "Build your project" --workspace {project_name}
```

## Commands

- `devmatrix plan` - Create development plans
- `devmatrix generate` - Generate code with approval gates
- `devmatrix orchestrate` - Multi-agent project execution
- `devmatrix workspace` - Manage workspaces
- `devmatrix files` - File operations
- `devmatrix git` - Git integration
- `devmatrix info` - System information
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
@click.argument("request")
@click.option("--workspace", "-w", help="Workspace ID (auto-generated if not provided)")
@click.option("--max-workers", default=4, help="Maximum concurrent workers (default: 4)")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed execution messages")
def orchestrate(request: str, workspace: str, max_workers: int, verbose: bool):
    """
    Orchestrate multi-agent workflow for complex projects.

    Uses specialized agents (Implementation, Testing, Documentation) to
    build complete projects with parallel task execution.

    Example:
        devmatrix orchestrate "Build a calculator with tests and docs"
        devmatrix orchestrate "Create REST API with authentication" -w my-api-project
    """
    try:
        from src.workflows.multi_agent_workflow import MultiAgentWorkflow
        from rich.tree import Tree
        from rich.table import Table

        console.print(f"\n[bold cyan]Multi-Agent Orchestration:[/bold cyan] {request}\n")

        # Generate workspace ID if not provided
        if not workspace:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            workspace = f"project-{timestamp}"
            console.print(f"[dim]Using auto-generated workspace: {workspace}[/dim]\n")

        # Create workflow
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            init_task = progress.add_task("Initializing multi-agent workflow...", total=None)

            workflow = MultiAgentWorkflow(
                workspace_id=workspace,
                max_workers=max_workers
            )

            progress.update(init_task, description="Running workflow...", completed=True)

            # Run workflow
            exec_task = progress.add_task("Executing multi-agent tasks...", total=None)
            result = workflow.run(request)
            progress.update(exec_task, completed=True)

        console.print("\n")

        # Display results
        if result['success']:
            # Success panel
            status_text = (
                f"[bold green]✓ Workflow Completed Successfully[/bold green]\n\n"
                f"Workspace: [cyan]{workspace}[/cyan]\n"
                f"Status: [green]{result['status']}[/green]\n"
                f"Tasks: {len(result.get('completed_tasks', []))} completed, "
                f"{len(result.get('failed_tasks', []))} failed"
            )

            panel = Panel(status_text, title="✓ Success", border_style="green")
            console.print(panel)

            # Show tasks if verbose
            if verbose and result['tasks']:
                console.print("\n")
                table = Table(title="📋 Task Execution Details", show_header=True)
                table.add_column("Task ID", style="cyan")
                table.add_column("Type", style="magenta")
                table.add_column("Description", style="white")
                table.add_column("Status", style="green")

                completed = set(result['completed_tasks'])
                failed = set(result['failed_tasks'])

                for task in result['tasks']:
                    task_id = task['id']
                    status = "✅" if task_id in completed else "❌" if task_id in failed else "⏳"
                    table.add_row(
                        task_id,
                        task.get('task_type', 'unknown'),
                        task['description'][:60] + "..." if len(task['description']) > 60 else task['description'],
                        status
                    )

                console.print(table)

            # Show execution stats
            if result['execution_stats']:
                console.print("\n")
                stats = result['execution_stats']
                stats_table = Table(title="📊 Execution Statistics", show_header=True)
                stats_table.add_column("Metric", style="cyan")
                stats_table.add_column("Value", style="yellow")

                stats_table.add_row("Total Tasks", str(stats.get('total_tasks', 0)))
                stats_table.add_row("Successful", f"[green]{stats.get('successful', 0)}[/green]")
                stats_table.add_row("Failed", f"[red]{stats.get('failed', 0)}[/red]")
                stats_table.add_row("Skipped", str(stats.get('skipped', 0)))
                stats_table.add_row("Total Time", f"{stats.get('total_time', 0):.2f}s")

                if stats.get('parallel_time_saved', 0) > 0:
                    stats_table.add_row(
                        "Parallel Time Saved",
                        f"[green]⚡ {stats['parallel_time_saved']:.2f}s[/green]"
                    )

                console.print(stats_table)

            # Show messages if verbose
            if verbose and result['messages']:
                console.print("\n[bold]Execution Log:[/bold]")
                for msg in result['messages']:
                    console.print(f"  {msg}")

            # Next steps
            console.print("\n[bold]Next steps:[/bold]")
            console.print(f"  • Check workspace: [cyan]devmatrix files list {workspace}[/cyan]")
            console.print(f"  • Read files: [cyan]devmatrix files read {workspace} <filename>[/cyan]")

        else:
            # Failure panel
            error_text = (
                f"[bold red]✗ Workflow Failed[/bold red]\n\n"
                f"Status: {result['status']}\n"
                f"Error: {result.get('error', 'Unknown error')}"
            )

            panel = Panel(error_text, title="✗ Failed", border_style="red")
            console.print(panel)

            if verbose and result['messages']:
                console.print("\n[bold]Execution Log:[/bold]")
                for msg in result['messages']:
                    console.print(f"  {msg}")

    except ValueError as e:
        console.print(f"[red]Configuration Error: {e}[/red]")
        console.print("\n[yellow]Make sure to set ANTHROPIC_API_KEY in .env file[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@cli.group()
def plugins():
    """Manage plugins (custom agents, tools, workflows)."""
    pass


@plugins.command("list")
@click.option("--type", "-t", "plugin_type", help="Filter by plugin type (agent, tool, workflow, middleware)")
@click.option("--enabled-only", is_flag=True, help="Show only enabled plugins")
def plugins_list(plugin_type: str, enabled_only: bool):
    """List all registered plugins."""
    try:
        from src.plugins.registry import PluginRegistry
        from src.plugins.base import PluginType

        registry = PluginRegistry()

        # Convert string to enum if provided
        type_filter = None
        if plugin_type:
            try:
                type_filter = PluginType(plugin_type.lower())
            except ValueError:
                console.print(f"[red]Invalid plugin type: {plugin_type}[/red]")
                console.print("[yellow]Valid types: agent, tool, workflow, middleware[/yellow]")
                sys.exit(1)

        # Get plugins
        plugin_instances = registry.get_all(plugin_type=type_filter, enabled_only=enabled_only)

        if not plugin_instances:
            console.print("[yellow]No plugins found[/yellow]")
            return

        # Display plugins
        table = Table(title="🔌 Registered Plugins", show_header=True, header_style="bold cyan")
        table.add_column("Name", style="cyan")
        table.add_column("Version", style="dim")
        table.add_column("Type", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Description")

        for plugin in plugin_instances:
            meta = plugin.metadata
            status = "✓ Enabled" if plugin.is_enabled else "✗ Disabled"
            status_style = "green" if plugin.is_enabled else "red"

            table.add_row(
                meta.name,
                meta.version,
                meta.plugin_type.value,
                f"[{status_style}]{status}[/{status_style}]",
                meta.description[:50] + "..." if len(meta.description) > 50 else meta.description
            )

        console.print(table)

        # Show stats
        stats = registry.get_stats()
        stats_text = (
            f"\n[dim]Total: {stats['total']} | "
            f"Enabled: {stats['enabled']} | "
            f"Disabled: {stats['disabled']} | "
            f"Lazy-loaded: {stats['lazy_loaded']}[/dim]"
        )
        console.print(stats_text)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@plugins.command("info")
@click.argument("plugin_name")
def plugins_info(plugin_name: str):
    """Show detailed information about a plugin."""
    try:
        from src.plugins.registry import PluginRegistry

        registry = PluginRegistry()
        plugin = registry.get(plugin_name)

        if not plugin:
            console.print(f"[red]Plugin not found: {plugin_name}[/red]")
            sys.exit(1)

        meta = plugin.metadata

        # Create detailed info panel
        info_text = f"""[bold]Name:[/bold] {meta.name}
[bold]Version:[/bold] {meta.version}
[bold]Author:[/bold] {meta.author}
[bold]Type:[/bold] {meta.plugin_type.value}

[bold]Description:[/bold]
{meta.description}

[bold]Status:[/bold]
  Enabled: {'✓ Yes' if plugin.is_enabled else '✗ No'}
  Initialized: {'✓ Yes' if plugin.is_initialized else '✗ No'}

[bold]Dependencies:[/bold]
{chr(10).join(f'  • {dep}' for dep in meta.dependencies) if meta.dependencies else '  None'}

[bold]Tags:[/bold]
{', '.join(meta.tags) if meta.tags else 'None'}
"""

        panel = Panel(info_text, title=f"🔌 Plugin Info: {meta.name}", border_style="cyan")
        console.print(panel)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@plugins.command("load")
@click.argument("directory")
@click.option("--type", "-t", "plugin_type", help="Load only specific plugin type")
def plugins_load(directory: str, plugin_type: str):
    """Load plugins from a directory."""
    try:
        from src.plugins.registry import PluginRegistry
        from src.plugins.base import PluginType

        # Convert string to enum if provided
        type_filter = None
        if plugin_type:
            try:
                type_filter = PluginType(plugin_type.lower())
            except ValueError:
                console.print(f"[red]Invalid plugin type: {plugin_type}[/red]")
                sys.exit(1)

        plugin_dir = Path(directory).resolve()

        if not plugin_dir.exists():
            console.print(f"[red]Directory not found: {plugin_dir}[/red]")
            sys.exit(1)

        registry = PluginRegistry()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Loading plugins from {directory}...", total=None)

            count = registry.load_from_directory(plugin_dir, plugin_type=type_filter)

            progress.update(task, completed=True)

        console.print(f"\n[green]✓ Loaded {count} plugin(s) from {directory}[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@plugins.command("enable")
@click.argument("plugin_name")
def plugins_enable(plugin_name: str):
    """Enable a plugin."""
    try:
        from src.plugins.registry import PluginRegistry

        registry = PluginRegistry()

        if registry.enable_plugin(plugin_name):
            console.print(f"[green]✓ Plugin enabled: {plugin_name}[/green]")
        else:
            console.print(f"[red]Failed to enable plugin: {plugin_name}[/red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@plugins.command("disable")
@click.argument("plugin_name")
def plugins_disable(plugin_name: str):
    """Disable a plugin."""
    try:
        from src.plugins.registry import PluginRegistry

        registry = PluginRegistry()

        if registry.disable_plugin(plugin_name):
            console.print(f"[yellow]Plugin disabled: {plugin_name}[/yellow]")
        else:
            console.print(f"[red]Failed to disable plugin: {plugin_name}[/red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
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
  • MultiAgentWorkflow: Orchestrated multi-agent execution
  • PluginSystem: Extensible plugin architecture
  • Rich CLI: Beautiful terminal interface

[bold]Specialized Agents:[/bold]
  • ImplementationAgent: Python code generation
  • TestingAgent: pytest test generation and execution
  • DocumentationAgent: Docstring and README generation

[dim]Use --help with any command for more information[/dim]
"""

    panel = Panel(info_text, title="🤖 Devmatrix Info", border_style="cyan")
    console.print(panel)


if __name__ == "__main__":
    cli()
