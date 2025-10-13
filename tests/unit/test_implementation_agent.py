"""
Unit tests for ImplementationAgent
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.agents.implementation_agent import ImplementationAgent
from src.agents.agent_registry import AgentCapability
from src.state.shared_scratchpad import Artifact, ArtifactType


class TestImplementationAgent:
    """Test suite for ImplementationAgent."""

    @pytest.fixture
    def agent(self):
        """Create agent with mocked LLM."""
        with patch('src.agents.implementation_agent.AnthropicClient') as mock_llm_class:
            mock_llm = Mock()
            mock_llm_class.return_value = mock_llm
            agent = ImplementationAgent()
            agent.llm = mock_llm
            yield agent

    @pytest.fixture
    def mock_scratchpad(self):
        """Create mock scratchpad."""
        return Mock()

    @pytest.fixture
    def mock_workspace(self):
        """Create mock workspace manager."""
        mock_ws = Mock()
        mock_ws.base_path = Mock()
        mock_ws.base_path.exists.return_value = True
        mock_ws.write_file.return_value = Path("/workspace/test.py")
        return mock_ws

    def test_init(self, agent):
        """Test agent initialization."""
        assert agent.name == "ImplementationAgent"
        assert agent.llm is not None

    def test_get_capabilities(self, agent):
        """Test getting agent capabilities."""
        capabilities = agent.get_capabilities()

        assert AgentCapability.CODE_GENERATION in capabilities
        assert AgentCapability.API_DESIGN in capabilities
        assert AgentCapability.REFACTORING in capabilities
        assert len(capabilities) == 3

    def test_get_name(self, agent):
        """Test getting agent name."""
        assert agent.get_name() == "ImplementationAgent"

    def test_execute_simple_task(self, agent, mock_scratchpad):
        """Test executing a simple implementation task."""
        # Setup
        agent.llm.generate.return_value = {
            'content': '```python\ndef hello():\n    return "Hello, World!"\n```',
            'model': 'claude',
            'usage': {'input_tokens': 100, 'output_tokens': 50},
            'stop_reason': 'end_turn'
        }

        task = {
            "id": "task_1",
            "description": "Create a hello world function",
            "task_type": "implementation",
            "dependencies": [],
            "files": ["hello.py"]
        }

        context = {
            "workspace_id": "test-workspace",
            "scratchpad": mock_scratchpad
        }

        with patch('src.agents.implementation_agent.WorkspaceManager') as mock_ws_class:
            mock_ws = Mock()
            mock_ws.base_path.exists.return_value = True
            mock_ws.write_file.return_value = Path("/workspace/hello.py")
            mock_ws_class.return_value = mock_ws

            # Execute
            result = agent.execute(task, context)

        # Assertions
        assert result["success"] is True
        assert result["output"] == 'def hello():\n    return "Hello, World!"'
        assert len(result["artifacts"]) > 0
        assert result["error"] is None

        # Verify scratchpad interactions
        mock_scratchpad.mark_task_started.assert_called_once_with("task_1", "ImplementationAgent")
        mock_scratchpad.write_artifact.assert_called_once()
        mock_scratchpad.mark_task_completed.assert_called_once_with("task_1", "ImplementationAgent")

    def test_execute_with_dependencies(self, agent, mock_scratchpad):
        """Test executing task with dependencies."""
        # Setup dependency artifacts
        dep_artifact = Artifact(
            artifact_type=ArtifactType.CODE,
            content="class User:\n    pass",
            created_by="other_agent",
            task_id="task_0"
        )

        mock_scratchpad.read_artifacts.return_value = [dep_artifact]

        agent.llm.generate.return_value = {
            'content': '```python\ndef create_user():\n    return User()\n```',
            'model': 'claude',
            'usage': {'input_tokens': 100, 'output_tokens': 50},
            'stop_reason': 'end_turn'
        }

        task = {
            "id": "task_1",
            "description": "Create a function to instantiate User",
            "task_type": "implementation",
            "dependencies": ["task_0"],
            "files": ["services/user.py"]
        }

        context = {
            "workspace_id": "test-workspace",
            "scratchpad": mock_scratchpad
        }

        with patch('src.agents.implementation_agent.WorkspaceManager') as mock_ws_class:
            mock_ws = Mock()
            mock_ws.base_path.exists.return_value = True
            mock_ws.write_file.return_value = Path("/workspace/services/user.py")
            mock_ws.create_dir.return_value = None
            mock_ws_class.return_value = mock_ws

            # Execute
            result = agent.execute(task, context)

        # Assertions
        assert result["success"] is True
        assert "create_user" in result["output"]
        mock_scratchpad.read_artifacts.assert_called_once_with(task_id="task_0")

    def test_execute_without_scratchpad(self, agent):
        """Test executing task without scratchpad."""
        agent.llm.generate.return_value = {
            'content': '```python\ndef test():\n    pass\n```',
            'model': 'claude',
            'usage': {'input_tokens': 100, 'output_tokens': 50},
            'stop_reason': 'end_turn'
        }

        task = {
            "id": "task_1",
            "description": "Create a test function",
            "task_type": "implementation",
            "dependencies": [],
            "files": ["test.py"]
        }

        context = {
            "workspace_id": "test-workspace"
            # No scratchpad
        }

        with patch('src.agents.implementation_agent.WorkspaceManager') as mock_ws_class:
            mock_ws = Mock()
            mock_ws.base_path.exists.return_value = True
            mock_ws.write_file.return_value = Path("/workspace/test.py")
            mock_ws_class.return_value = mock_ws

            # Execute
            result = agent.execute(task, context)

        # Assertions
        assert result["success"] is True
        assert result["artifacts"] == []  # No artifacts without scratchpad

    def test_execute_with_nested_file_path(self, agent, mock_scratchpad):
        """Test executing task with nested file paths."""
        agent.llm.generate.return_value = {
            'content': '```python\nclass Model:\n    pass\n```',
            'model': 'claude',
            'usage': {'input_tokens': 100, 'output_tokens': 50},
            'stop_reason': 'end_turn'
        }

        task = {
            "id": "task_1",
            "description": "Create a model",
            "task_type": "implementation",
            "dependencies": [],
            "files": ["models/base/model.py"]
        }

        context = {
            "workspace_id": "test-workspace",
            "scratchpad": mock_scratchpad
        }

        with patch('src.agents.implementation_agent.WorkspaceManager') as mock_ws_class:
            mock_ws = Mock()
            mock_ws.base_path.exists.return_value = True
            mock_ws.create_dir.return_value = None
            mock_ws.write_file.return_value = Path("/workspace/models/base/model.py")
            mock_ws_class.return_value = mock_ws

            # Execute
            result = agent.execute(task, context)

        # Assertions
        assert result["success"] is True
        mock_ws.create_dir.assert_called_once_with("models/base")
        mock_ws.write_file.assert_called_once()

    def test_execute_multiple_files(self, agent, mock_scratchpad):
        """Test executing task that generates multiple files."""
        agent.llm.generate.return_value = {
            'content': '```python\nclass User:\n    pass\n```',
            'model': 'claude',
            'usage': {'input_tokens': 100, 'output_tokens': 50},
            'stop_reason': 'end_turn'
        }

        task = {
            "id": "task_1",
            "description": "Create User model",
            "task_type": "implementation",
            "dependencies": [],
            "files": ["models/user.py", "models/__init__.py"]
        }

        context = {
            "workspace_id": "test-workspace",
            "scratchpad": mock_scratchpad
        }

        with patch('src.agents.implementation_agent.WorkspaceManager') as mock_ws_class:
            mock_ws = Mock()
            mock_ws.base_path.exists.return_value = True
            mock_ws.create_dir.return_value = None

            def mock_write_file(filename, content):
                return Path(f"/workspace/{filename}")

            mock_ws.write_file.side_effect = mock_write_file
            mock_ws_class.return_value = mock_ws

            # Execute
            result = agent.execute(task, context)

        # Assertions
        assert result["success"] is True
        assert len(result["file_paths"]) == 2
        assert mock_ws.write_file.call_count == 2

    def test_execute_workspace_creation(self, agent, mock_scratchpad):
        """Test executing task when workspace doesn't exist."""
        agent.llm.generate.return_value = {
            'content': '```python\ndef test():\n    pass\n```',
            'model': 'claude',
            'usage': {'input_tokens': 100, 'output_tokens': 50},
            'stop_reason': 'end_turn'
        }

        task = {
            "id": "task_1",
            "description": "Create test function",
            "task_type": "implementation",
            "dependencies": [],
            "files": ["test.py"]
        }

        context = {
            "workspace_id": "new-workspace",
            "scratchpad": mock_scratchpad
        }

        with patch('src.agents.implementation_agent.WorkspaceManager') as mock_ws_class:
            mock_ws = Mock()
            mock_ws.base_path.exists.return_value = False
            mock_ws.create.return_value = None
            mock_ws.write_file.return_value = Path("/workspace/test.py")
            mock_ws_class.return_value = mock_ws

            # Execute
            result = agent.execute(task, context)

        # Assertions
        assert result["success"] is True
        mock_ws.create.assert_called_once()

    def test_execute_error_handling(self, agent, mock_scratchpad):
        """Test error handling during execution."""
        agent.llm.generate.side_effect = Exception("LLM error")

        task = {
            "id": "task_1",
            "description": "Create function",
            "task_type": "implementation",
            "dependencies": [],
            "files": ["test.py"]
        }

        context = {
            "workspace_id": "test-workspace",
            "scratchpad": mock_scratchpad
        }

        # Execute
        result = agent.execute(task, context)

        # Assertions
        assert result["success"] is False
        assert result["error"] == "LLM error"
        assert result["output"] is None
        mock_scratchpad.mark_task_failed.assert_called_once_with(
            "task_1",
            "ImplementationAgent",
            "LLM error"
        )

    def test_generate_code_extracts_from_markdown(self, agent):
        """Test code extraction from markdown blocks."""
        agent.llm.generate.return_value = {
            'content': 'Here is the code:\n```python\ndef foo():\n    pass\n```\nDone!',
            'model': 'claude',
            'usage': {'input_tokens': 100, 'output_tokens': 50},
            'stop_reason': 'end_turn'
        }

        code = agent._generate_code("Test task", ["test.py"], "")

        assert code == "def foo():\n    pass"
        assert "Here is the code:" not in code
        assert "```" not in code

    def test_generate_code_no_markdown(self, agent):
        """Test code generation when no markdown blocks present."""
        raw_code = "def bar():\n    return 42"
        agent.llm.generate.return_value = {
            'content': raw_code,
            'model': 'claude',
            'usage': {'input_tokens': 100, 'output_tokens': 50},
            'stop_reason': 'end_turn'
        }

        code = agent._generate_code("Test task", ["test.py"], "")

        assert code == raw_code

    def test_read_dependency_artifacts_empty(self, agent):
        """Test reading dependency artifacts when empty."""
        mock_scratchpad = Mock()

        result = agent._read_dependency_artifacts([], mock_scratchpad)

        assert result == ""
        mock_scratchpad.read_artifacts.assert_not_called()

    def test_read_dependency_artifacts_code(self, agent):
        """Test reading code artifacts from dependencies."""
        mock_scratchpad = Mock()

        artifact = Artifact(
            artifact_type=ArtifactType.CODE,
            content="def helper():\n    pass",
            created_by="other_agent",
            task_id="task_0"
        )

        mock_scratchpad.read_artifacts.return_value = [artifact]

        result = agent._read_dependency_artifacts(["task_0"], mock_scratchpad)

        assert "task_0" in result
        assert "def helper()" in result
        assert "```python" in result

    def test_repr(self, agent):
        """Test string representation."""
        repr_str = repr(agent)

        assert "ImplementationAgent" in repr_str
        assert "name=" in repr_str
