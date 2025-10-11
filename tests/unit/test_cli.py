"""
Unit tests for CLI commands.
"""

import pytest
from click.testing import CliRunner
from pathlib import Path
from src.cli.main import cli
from src.tools.workspace_manager import WorkspaceManager


class TestCLI:
    """Test CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_cli_help(self, runner):
        """Test main CLI help."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Devmatrix" in result.output
        assert "workspace" in result.output
        assert "files" in result.output
        assert "git" in result.output

    def test_cli_version(self, runner):
        """Test version command."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_info_command(self, runner):
        """Test info command."""
        result = runner.invoke(cli, ["info"])
        assert result.exit_code == 0
        assert "Devmatrix" in result.output
        assert "Python" in result.output
        assert "WorkspaceManager" in result.output

    def test_init_command(self, runner, tmp_path):
        """Test project initialization."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init", "test_project"])
            assert result.exit_code == 0
            assert "Project created" in result.output

            # Verify project structure
            project_path = Path("test_project")
            assert project_path.exists()
            assert (project_path / "src").exists()
            assert (project_path / "tests").exists()
            assert (project_path / "docs").exists()
            assert (project_path / "README.md").exists()
            assert (project_path / ".gitignore").exists()

    def test_init_command_existing_project(self, runner, tmp_path):
        """Test init fails for existing project."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create project first time
            runner.invoke(cli, ["init", "test_project"])

            # Try to create again
            result = runner.invoke(cli, ["init", "test_project"])
            assert result.exit_code == 1
            assert "already exists" in result.output

    def test_workspace_create(self, runner):
        """Test workspace creation."""
        result = runner.invoke(cli, ["workspace", "create"])
        assert result.exit_code == 0
        assert "Workspace Created" in result.output
        assert "/tmp/devmatrix-workspace-" in result.output

        # Extract workspace ID from output
        lines = result.output.split("\n")
        workspace_id = None
        for line in lines:
            if "ID:" in line:
                workspace_id = line.split("ID:")[1].strip()
                break

        # Cleanup
        if workspace_id:
            ws = WorkspaceManager(workspace_id=workspace_id, auto_cleanup=False)
            ws.cleanup()

    def test_workspace_create_with_custom_id(self, runner):
        """Test workspace creation with custom ID."""
        result = runner.invoke(cli, ["workspace", "create", "--id", "test_workspace"])
        assert result.exit_code == 0
        assert "test_workspace" in result.output

        # Cleanup
        ws = WorkspaceManager(workspace_id="test_workspace", auto_cleanup=False)
        ws.cleanup()

    def test_workspace_list_empty(self, runner):
        """Test listing workspaces when none exist."""
        # Clean all first
        runner.invoke(cli, ["workspace", "clean", "--all"])

        result = runner.invoke(cli, ["workspace", "list"])
        assert result.exit_code == 0
        assert "No active workspaces" in result.output

    def test_workspace_list_with_workspaces(self, runner):
        """Test listing active workspaces."""
        # Create a workspace
        runner.invoke(cli, ["workspace", "create", "--id", "test_list"])

        result = runner.invoke(cli, ["workspace", "list"])
        assert result.exit_code == 0
        assert "test_list" in result.output

        # Cleanup
        ws = WorkspaceManager(workspace_id="test_list", auto_cleanup=False)
        ws.cleanup()

    def test_workspace_clean_specific(self, runner):
        """Test cleaning specific workspace."""
        # Create workspace
        runner.invoke(cli, ["workspace", "create", "--id", "test_clean"])

        # Clean it
        result = runner.invoke(cli, ["workspace", "clean", "--id", "test_clean"])
        assert result.exit_code == 0
        assert "Cleaned workspace" in result.output

    def test_workspace_clean_all(self, runner):
        """Test cleaning all workspaces."""
        # Create multiple workspaces
        runner.invoke(cli, ["workspace", "create", "--id", "test_clean1"])
        runner.invoke(cli, ["workspace", "create", "--id", "test_clean2"])

        # Clean all
        result = runner.invoke(cli, ["workspace", "clean", "--all"])
        assert result.exit_code == 0
        assert "Cleaned" in result.output

    def test_workspace_clean_no_args(self, runner):
        """Test clean without arguments fails."""
        result = runner.invoke(cli, ["workspace", "clean"])
        assert result.exit_code == 1
        assert "--all or --id" in result.output

    def test_files_list_nonexistent_workspace(self, runner):
        """Test listing files in nonexistent workspace."""
        result = runner.invoke(cli, ["files", "list", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_files_list(self, runner):
        """Test listing files in workspace."""
        # Create workspace with files
        ws = WorkspaceManager(workspace_id="test_files", auto_cleanup=False)
        ws.create()
        ws.write_file("test1.txt", "content1")
        ws.write_file("test2.py", "print('hello')")

        result = runner.invoke(cli, ["files", "list", "test_files"])
        assert result.exit_code == 0
        assert "test1.txt" in result.output
        assert "test2.py" in result.output

        # Cleanup
        ws.cleanup()

    def test_files_list_with_pattern(self, runner):
        """Test listing files with glob pattern."""
        # Create workspace with files
        ws = WorkspaceManager(workspace_id="test_pattern", auto_cleanup=False)
        ws.create()
        ws.write_file("test.py", "content")
        ws.write_file("test.txt", "content")

        result = runner.invoke(cli, ["files", "list", "test_pattern", "--pattern", "*.py"])
        assert result.exit_code == 0
        assert "test.py" in result.output
        assert "test.txt" not in result.output

        # Cleanup
        ws.cleanup()

    def test_files_list_empty(self, runner):
        """Test listing files in empty workspace."""
        # Create empty workspace
        ws = WorkspaceManager(workspace_id="test_empty", auto_cleanup=False)
        ws.create()

        result = runner.invoke(cli, ["files", "list", "test_empty"])
        assert result.exit_code == 0
        assert "No files found" in result.output

        # Cleanup
        ws.cleanup()

    def test_files_read(self, runner):
        """Test reading file from workspace."""
        # Create workspace with file
        ws = WorkspaceManager(workspace_id="test_read", auto_cleanup=False)
        ws.create()
        ws.write_file("test.txt", "Hello, World!")

        result = runner.invoke(cli, ["files", "read", "test_read", "test.txt"])
        assert result.exit_code == 0
        assert "Hello, World!" in result.output

        # Cleanup
        ws.cleanup()

    def test_files_read_with_syntax(self, runner):
        """Test reading file with syntax highlighting."""
        # Create workspace with Python file
        ws = WorkspaceManager(workspace_id="test_syntax", auto_cleanup=False)
        ws.create()
        ws.write_file("test.py", "def hello():\n    print('hello')")

        result = runner.invoke(cli, ["files", "read", "test_syntax", "test.py", "--syntax", "python"])
        assert result.exit_code == 0
        assert "hello" in result.output

        # Cleanup
        ws.cleanup()

    def test_files_read_nonexistent(self, runner):
        """Test reading nonexistent file."""
        ws = WorkspaceManager(workspace_id="test_nofile", auto_cleanup=False)
        ws.create()

        result = runner.invoke(cli, ["files", "read", "test_nofile", "nonexistent.txt"])
        assert result.exit_code == 1
        assert "not found" in result.output

        # Cleanup
        ws.cleanup()

    def test_git_status_not_a_repo(self, runner, tmp_path):
        """Test git status on non-git directory."""
        result = runner.invoke(cli, ["git", "status", "--repo", str(tmp_path)])
        assert result.exit_code == 1
        assert "Not a git repository" in result.output

    def test_git_status_current_repo(self, runner):
        """Test git status on current repository."""
        result = runner.invoke(cli, ["git", "status"])
        assert result.exit_code == 0
        assert "Branch" in result.output
        assert "Status" in result.output

    def test_workspace_help(self, runner):
        """Test workspace help command."""
        result = runner.invoke(cli, ["workspace", "--help"])
        assert result.exit_code == 0
        assert "Manage temporary workspaces" in result.output

    def test_files_help(self, runner):
        """Test files help command."""
        result = runner.invoke(cli, ["files", "--help"])
        assert result.exit_code == 0
        assert "File operations" in result.output

    def test_git_help(self, runner):
        """Test git help command."""
        result = runner.invoke(cli, ["git", "--help"])
        assert result.exit_code == 0
        assert "Git operations" in result.output

    def test_plan_command_without_api_key(self, runner, monkeypatch):
        """Test plan command fails without API key."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        result = runner.invoke(cli, ["plan", "Create a REST API"])
        assert result.exit_code == 1
        assert "ANTHROPIC_API_KEY" in result.output

    def test_plan_command_with_mocked_agent(self, runner, monkeypatch):
        """Test plan command with mocked planning agent."""
        from unittest.mock import Mock, patch

        # Mock the planning agent
        mock_agent = Mock()
        mock_agent.plan.return_value = {
            "plan": {
                "summary": "REST API development",
                "requirements": ["Authentication", "Database"],
                "tasks": [
                    {
                        "id": 1,
                        "title": "Setup project",
                        "description": "Initialize structure",
                        "dependencies": [],
                        "estimated_time": "2 hours",
                        "complexity": "low"
                    }
                ],
                "risks": ["Security vulnerabilities"],
                "next_steps": "Setup development environment"
            },
            "tasks": [],
            "messages": []
        }
        mock_agent.format_plan.return_value = "📋 Summary: REST API development\n\n✅ Requirements:\n  • Authentication\n  • Database"

        with patch('src.agents.planning_agent.PlanningAgent') as mock_class:
            mock_class.return_value = mock_agent

            result = runner.invoke(cli, ["plan", "Create a REST API"])
            assert result.exit_code == 0
            assert "Planning:" in result.output
            assert "REST API" in result.output

            # Verify agent was called
            mock_agent.plan.assert_called_once()
            mock_agent.format_plan.assert_called_once()

    def test_plan_command_with_context(self, runner, monkeypatch):
        """Test plan command with JSON context."""
        from unittest.mock import Mock, patch

        mock_agent = Mock()
        mock_agent.plan.return_value = {
            "plan": {"summary": "API with FastAPI"},
            "tasks": [],
            "messages": []
        }
        mock_agent.format_plan.return_value = "Plan summary"

        with patch('src.agents.planning_agent.PlanningAgent') as mock_class:
            mock_class.return_value = mock_agent

            result = runner.invoke(
                cli,
                ["plan", "Create API", "--context", '{"framework": "FastAPI"}']
            )
            assert result.exit_code == 0

            # Verify context was passed
            call_args = mock_agent.plan.call_args
            assert call_args[0][0] == "Create API"
            assert call_args[0][1] == {"framework": "FastAPI"}

    def test_plan_command_with_invalid_json_context(self, runner, monkeypatch):
        """Test plan command handles invalid JSON context gracefully."""
        from unittest.mock import Mock, patch

        mock_agent = Mock()
        mock_agent.plan.return_value = {
            "plan": {"summary": "API development"},
            "tasks": [],
            "messages": []
        }
        mock_agent.format_plan.return_value = "Plan"

        with patch('src.agents.planning_agent.PlanningAgent') as mock_class:
            mock_class.return_value = mock_agent

            result = runner.invoke(
                cli,
                ["plan", "Create API", "--context", "not valid json"]
            )
            assert result.exit_code == 0
            assert "Invalid JSON context" in result.output or "Plan" in result.output

            # Context should be empty dict
            call_args = mock_agent.plan.call_args
            assert call_args[0][1] == {}

    def test_plan_command_with_save(self, runner, tmp_path, monkeypatch):
        """Test plan command saves plan to file."""
        from unittest.mock import Mock, patch

        mock_agent = Mock()
        plan_data = {
            "plan": {
                "summary": "REST API",
                "tasks": [{"id": 1, "title": "Setup"}],
                "risks": []
            },
            "tasks": [],
            "messages": []
        }
        mock_agent.plan.return_value = plan_data
        mock_agent.format_plan.return_value = "Plan summary"

        with patch('src.agents.planning_agent.PlanningAgent') as mock_class:
            mock_class.return_value = mock_agent

            with runner.isolated_filesystem(temp_dir=tmp_path):
                result = runner.invoke(
                    cli,
                    ["plan", "Create API", "--save"]
                )
                assert result.exit_code == 0
                assert "Plan saved" in result.output

                # Verify file was created
                plans_dir = Path("plans")
                assert plans_dir.exists()
                plan_files = list(plans_dir.glob("plan_*.json"))
                assert len(plan_files) == 1

                # Verify content
                import json
                with open(plan_files[0]) as f:
                    saved_plan = json.load(f)
                assert saved_plan == plan_data

    def test_plan_command_agent_error(self, runner):
        """Test plan command handles agent errors gracefully."""
        from unittest.mock import Mock, patch

        with patch('src.agents.planning_agent.PlanningAgent') as mock_class:
            mock_class.side_effect = Exception("Agent initialization failed")

            result = runner.invoke(cli, ["plan", "Create API"])
            assert result.exit_code == 1
            assert "Error:" in result.output

    def test_plan_help(self, runner):
        """Test plan help command."""
        result = runner.invoke(cli, ["plan", "--help"])
        assert result.exit_code == 0
        assert "Create a development plan" in result.output
        assert "--context" in result.output
        assert "--save" in result.output
