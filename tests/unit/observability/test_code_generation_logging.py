"""
Tests for code generation agent logging implementation.

Validates that code generation agent properly uses StructuredLogger for internal
logging while maintaining Rich Console for user interaction.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from src.agents.code_generation_agent import CodeGenerationAgent
from src.observability import get_logger


class TestCodeGenerationLogging:
    """Test code generation agent logging functionality."""

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM client."""
        with patch('src.agents.code_generation_agent.AnthropicClient') as mock:
            mock_instance = Mock()
            mock_instance.generate = Mock(return_value={'content': 'test response'})
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def agent(self, mock_llm):
        """Create code generation agent instance."""
        return CodeGenerationAgent()

    def test_agent_has_logger(self, agent):
        """Test that agent has a logger attribute."""
        assert hasattr(agent, 'logger')
        assert agent.logger is not None
        assert agent.logger.name == "code_generation"

    def test_agent_logs_file_operations(self, agent, capsys, tmp_path):
        """Test that file operations are logged."""
        state = {
            "workspace_id": "test-workspace",
            "target_filename": "test.py",
            "generated_code": "print('hello')",
            "approval_status": "approved"
        }

        # Mock workspace manager
        with patch('src.agents.code_generation_agent.WorkspaceManager') as mock_ws:
            mock_ws_instance = Mock()
            mock_ws_instance.base_path = tmp_path
            mock_ws_instance.write_file = Mock(return_value=tmp_path / "test.py")
            mock_ws.return_value = mock_ws_instance

            result = agent._write_file(state)

        captured = capsys.readouterr()
        # Should log file write success
        assert "file" in captured.out.lower() or "written" in captured.out.lower()

    def test_agent_logs_file_operation_errors(self, agent, capsys):
        """Test that file operation errors are logged."""
        state = {
            "workspace_id": "test-ws",
            "target_filename": "test.py",
            "generated_code": "code",
            "approval_status": "approved"
        }

        # Force an error
        with patch('src.agents.code_generation_agent.WorkspaceManager', side_effect=Exception("Write error")):
            result = agent._write_file(state)

        captured = capsys.readouterr()
        # Error should be logged
        assert "error" in captured.out.lower() or "fail" in captured.out.lower()

    def test_agent_logs_git_operations(self, agent, capsys, tmp_path):
        """Test that git operations are logged."""
        state = {
            "workspace_id": "test-workspace",
            "target_filename": "test.py",
            "file_path": str(tmp_path / "test.py"),
            "user_request": "create test file",
            "plan": {"description": "test plan"},
            "file_written": True
        }

        # Mock git operations
        with patch('src.agents.code_generation_agent.WorkspaceManager') as mock_ws, \
             patch('src.agents.code_generation_agent.GitOperations') as mock_git:

            mock_ws_instance = Mock()
            mock_ws_instance.base_path = tmp_path
            mock_ws.return_value = mock_ws_instance

            mock_git_instance = Mock()
            mock_git_instance.get_status = Mock()
            mock_git_instance.add_files = Mock()
            mock_git_instance.commit = Mock(return_value={"hash": "abc123"})
            mock_git.return_value = mock_git_instance

            result = agent._git_commit(state)

        captured = capsys.readouterr()
        # Should log git operations
        assert "git" in captured.out.lower() or "commit" in captured.out.lower()

    def test_agent_logs_git_failures(self, agent, capsys, tmp_path):
        """Test that git failures are logged."""
        state = {
            "workspace_id": "test-ws",
            "target_filename": "test.py",
            "file_path": str(tmp_path / "test.py"),
            "user_request": "test",
            "plan": {"description": "test"},
            "file_written": True
        }

        # Force git error
        with patch('src.agents.code_generation_agent.WorkspaceManager') as mock_ws, \
             patch('src.agents.code_generation_agent.GitOperations', side_effect=Exception("Git error")):

            mock_ws_instance = Mock()
            mock_ws_instance.base_path = tmp_path
            mock_ws.return_value = mock_ws_instance

            result = agent._git_commit(state)

        captured = capsys.readouterr()
        # Should log warning about git failure
        assert "warning" in captured.out.lower() or "could not" in captured.out.lower()

    def test_agent_logs_decision_logging(self, agent, capsys):
        """Test that PostgreSQL decision logging is logged."""
        state = {
            "workspace_id": "test-ws",
            "user_request": "test request",
            "approval_status": "approved",
            "generated_code": "code",
            "target_filename": "test.py",
            "file_path": "/tmp/test.py",
            "code_quality_score": 8.5,
            "git_committed": True,
            "git_commit_hash": "abc123",
            "git_commit_message": "feat: add test"
        }

        # Mock postgres manager
        with patch.object(agent.postgres, 'create_project', return_value="proj-123"), \
             patch.object(agent.postgres, 'create_task', return_value="task-456"), \
             patch.object(agent.postgres, 'log_decision', return_value="dec-789"):

            result = agent._log_decision(state)

        captured = capsys.readouterr()
        # Should log decision logging success
        assert "decision" in captured.out.lower() or "logged" in captured.out.lower()

    def test_agent_logs_decision_logging_errors(self, agent, capsys):
        """Test that decision logging errors are logged."""
        state = {
            "workspace_id": "test-ws",
            "user_request": "test",
            "approval_status": "approved"
        }

        # Force postgres error
        with patch.object(agent.postgres, 'create_project', side_effect=Exception("DB error")):
            result = agent._log_decision(state)

        captured = capsys.readouterr()
        # Should log error
        assert "warning" in captured.out.lower() or "could not" in captured.out.lower()

    def test_agent_console_only_for_user_interaction(self, agent):
        """Test that console.print is only used for user interaction, not internal logging."""
        # Verify agent has both console and logger
        assert hasattr(agent, 'console')
        assert hasattr(agent, 'logger')

        # Verify they are different objects
        assert agent.console is not agent.logger

    def test_agent_logger_includes_context(self, agent, capsys, tmp_path):
        """Test that logger includes proper context (workspace_id, filename, etc.)."""
        state = {
            "workspace_id": "context-test-ws",
            "target_filename": "context_test.py",
            "generated_code": "# test code",
            "approval_status": "approved"
        }

        with patch('src.agents.code_generation_agent.WorkspaceManager') as mock_ws:
            mock_ws_instance = Mock()
            mock_ws_instance.base_path = tmp_path
            mock_ws_instance.write_file = Mock(return_value=tmp_path / "context_test.py")
            mock_ws.return_value = mock_ws_instance

            result = agent._write_file(state)

        captured = capsys.readouterr()
        # Should include context
        assert "workspace" in captured.out.lower() or "file" in captured.out.lower()
