"""
Unit tests for TestingAgent
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.agents.testing_agent import TestingAgent
from src.agents.agent_registry import AgentCapability
from src.state.shared_scratchpad import Artifact, ArtifactType


class TestTestingAgent:
    """Test suite for TestingAgent."""

    @pytest.fixture
    def agent(self):
        """Create agent with mocked LLM."""
        with patch('src.agents.testing_agent.AnthropicClient') as mock_llm_class:
            mock_llm = Mock()
            mock_llm_class.return_value = mock_llm
            agent = TestingAgent()
            agent.llm = mock_llm
            yield agent

    @pytest.fixture
    def mock_scratchpad(self):
        """Create mock scratchpad."""
        return Mock()

    def test_init(self, agent):
        """Test agent initialization."""
        assert agent.name == "TestingAgent"
        assert agent.llm is not None

    def test_get_capabilities(self, agent):
        """Test getting agent capabilities."""
        capabilities = agent.get_capabilities()

        assert AgentCapability.UNIT_TESTING in capabilities
        assert AgentCapability.INTEGRATION_TESTING in capabilities
        assert AgentCapability.E2E_TESTING in capabilities
        assert len(capabilities) == 3

    def test_get_name(self, agent):
        """Test getting agent name."""
        assert agent.get_name() == "TestingAgent"

    def test_execute_simple_task(self, agent, mock_scratchpad):
        """Test executing a simple testing task."""
        # Setup
        mock_scratchpad.read_artifacts.return_value = [
            Artifact(
                artifact_type=ArtifactType.CODE,
                content="def add(a, b):\n    return a + b",
                created_by="ImplementationAgent",
                task_id="task_0"
            )
        ]

        agent.llm.generate.return_value = {
            'content': '```python\nimport pytest\n\ndef test_add():\n    assert add(1, 2) == 3\n```',
            'model': 'claude',
            'usage': {'input_tokens': 100, 'output_tokens': 50},
            'stop_reason': 'end_turn'
        }

        task = {
            "id": "task_1",
            "description": "Create tests for add function",
            "task_type": "testing",
            "dependencies": ["task_0"],
            "files": ["tests/test_math.py"]
        }

        context = {
            "workspace_id": "test-workspace",
            "scratchpad": mock_scratchpad,
            "run_tests": False  # Don't run tests in this test
        }

        with patch('src.agents.testing_agent.WorkspaceManager') as mock_ws_class:
            mock_ws = Mock()
            mock_ws.base_path.exists.return_value = True
            mock_ws.write_file.return_value = Path("/workspace/tests/test_math.py")
            mock_ws.create_dir.return_value = None
            mock_ws_class.return_value = mock_ws

            # Execute
            result = agent.execute(task, context)

        # Assertions
        assert result["success"] is True
        assert "import pytest" in result["output"]
        assert "test_add" in result["output"]
        assert len(result["artifacts"]) > 0
        assert result["error"] is None

        # Verify scratchpad interactions
        mock_scratchpad.mark_task_started.assert_called_once_with("task_1", "TestingAgent")
        mock_scratchpad.write_artifact.assert_called_once()
        mock_scratchpad.mark_task_completed.assert_called_once_with("task_1", "TestingAgent")

    def test_execute_with_test_execution(self, agent, mock_scratchpad):
        """Test executing task with test execution enabled."""
        # Setup dependency artifacts
        mock_scratchpad.read_artifacts.return_value = [
            Artifact(
                artifact_type=ArtifactType.CODE,
                content="def multiply(a, b):\n    return a * b",
                created_by="ImplementationAgent",
                task_id="task_0"
            )
        ]

        agent.llm.generate.return_value = {
            'content': '```python\nimport pytest\n\ndef test_multiply():\n    assert multiply(2, 3) == 6\n```',
            'model': 'claude',
            'usage': {'input_tokens': 100, 'output_tokens': 50},
            'stop_reason': 'end_turn'
        }

        task = {
            "id": "task_1",
            "description": "Create tests for multiply function",
            "task_type": "testing",
            "dependencies": ["task_0"],
            "files": ["tests/test_multiply.py"]
        }

        context = {
            "workspace_id": "test-workspace",
            "scratchpad": mock_scratchpad,
            "run_tests": True
        }

        with patch('src.agents.testing_agent.WorkspaceManager') as mock_ws_class, \
             patch('src.agents.testing_agent.subprocess.run') as mock_run:

            mock_ws = Mock()
            mock_ws.base_path.exists.return_value = True
            mock_ws.base_path = Path("/workspace")
            mock_ws.write_file.return_value = Path("/workspace/tests/test_multiply.py")
            mock_ws.create_dir.return_value = None
            mock_ws_class.return_value = mock_ws

            # Mock pytest execution
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "test_multiply.py::test_multiply PASSED\n1 passed in 0.01s"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            # Execute
            result = agent.execute(task, context)

        # Assertions
        assert result["success"] is True
        assert result["test_results"] is not None
        assert result["test_results"]["passed"] is True
        assert result["test_results"]["num_tests"] == 1
        assert len(result["artifacts"]) == 2  # Test artifact + result artifact

    def test_execute_without_scratchpad(self, agent):
        """Test executing task without scratchpad fails when no code available."""
        task = {
            "id": "task_1",
            "description": "Create a test",
            "task_type": "testing",
            "dependencies": [],
            "files": ["tests/test_example.py"]
        }

        context = {
            "workspace_id": "test-workspace",
            "run_tests": False
            # No scratchpad - can't read dependencies
        }

        # Execute
        result = agent.execute(task, context)

        # Assertions - should fail because no code to test
        assert result["success"] is False
        assert "No code found to test" in result["error"]
        assert result["artifacts"] == []

    def test_execute_with_nested_file_path(self, agent, mock_scratchpad):
        """Test executing task with nested file paths."""
        mock_scratchpad.read_artifacts.return_value = [
            Artifact(
                artifact_type=ArtifactType.CODE,
                content="class Calculator:\n    pass",
                created_by="ImplementationAgent",
                task_id="task_0"
            )
        ]

        agent.llm.generate.return_value = {
            'content': '```python\nimport pytest\nfrom calculator import Calculator\n\ndef test_calculator():\n    calc = Calculator()\n    assert calc is not None\n```',
            'model': 'claude',
            'usage': {'input_tokens': 100, 'output_tokens': 50},
            'stop_reason': 'end_turn'
        }

        task = {
            "id": "task_1",
            "description": "Create tests for Calculator",
            "task_type": "testing",
            "dependencies": ["task_0"],
            "files": ["tests/unit/test_calculator.py"]
        }

        context = {
            "workspace_id": "test-workspace",
            "scratchpad": mock_scratchpad,
            "run_tests": False
        }

        with patch('src.agents.testing_agent.WorkspaceManager') as mock_ws_class:
            mock_ws = Mock()
            mock_ws.base_path.exists.return_value = True
            mock_ws.create_dir.return_value = None
            mock_ws.write_file.return_value = Path("/workspace/tests/unit/test_calculator.py")
            mock_ws_class.return_value = mock_ws

            # Execute
            result = agent.execute(task, context)

        # Assertions
        assert result["success"] is True
        mock_ws.create_dir.assert_called_once_with("tests/unit")
        mock_ws.write_file.assert_called_once()

    def test_execute_error_handling(self, agent, mock_scratchpad):
        """Test error handling during execution."""
        mock_scratchpad.read_artifacts.return_value = []
        agent.llm.generate.side_effect = Exception("LLM error")

        task = {
            "id": "task_1",
            "description": "Create tests",
            "task_type": "testing",
            "dependencies": ["task_0"],
            "files": ["tests/test_error.py"]
        }

        context = {
            "workspace_id": "test-workspace",
            "scratchpad": mock_scratchpad
        }

        # Execute
        result = agent.execute(task, context)

        # Assertions
        assert result["success"] is False
        assert "No code found to test" in result["error"]
        assert result["output"] is None
        mock_scratchpad.mark_task_failed.assert_called_once()

    def test_generate_tests_extracts_from_markdown(self, agent):
        """Test test code extraction from markdown blocks."""
        agent.llm.generate.return_value = {
            'content': 'Here are the tests:\n```python\nimport pytest\n\ndef test_foo():\n    assert True\n```\nDone!',
            'model': 'claude',
            'usage': {'input_tokens': 100, 'output_tokens': 50},
            'stop_reason': 'end_turn'
        }

        test_code = agent._generate_tests("Test task", "def foo(): pass", ["test.py"])

        assert test_code == "import pytest\n\ndef test_foo():\n    assert True"
        assert "Here are the tests:" not in test_code
        assert "```" not in test_code

    def test_generate_tests_no_markdown(self, agent):
        """Test test generation when no markdown blocks present."""
        raw_code = "import pytest\n\ndef test_bar():\n    assert False"
        agent.llm.generate.return_value = {
            'content': raw_code,
            'model': 'claude',
            'usage': {'input_tokens': 100, 'output_tokens': 50},
            'stop_reason': 'end_turn'
        }

        test_code = agent._generate_tests("Test task", "def bar(): pass", ["test.py"])

        assert test_code == raw_code

    def test_read_code_from_dependencies_empty(self, agent):
        """Test reading code from dependencies when empty."""
        mock_scratchpad = Mock()

        result = agent._read_code_from_dependencies([], mock_scratchpad)

        assert result == ""
        mock_scratchpad.read_artifacts.assert_not_called()

    def test_read_code_from_dependencies_code(self, agent):
        """Test reading code artifacts from dependencies."""
        mock_scratchpad = Mock()

        artifact = Artifact(
            artifact_type=ArtifactType.CODE,
            content="def helper():\n    pass",
            created_by="ImplementationAgent",
            task_id="task_0"
        )

        mock_scratchpad.read_artifacts.return_value = [artifact]

        result = agent._read_code_from_dependencies(["task_0"], mock_scratchpad)

        assert "def helper()" in result
        mock_scratchpad.read_artifacts.assert_called_once()

    def test_run_tests_success(self, agent):
        """Test running tests with successful execution."""
        with patch('src.agents.testing_agent.WorkspaceManager') as mock_ws_class, \
             patch('src.agents.testing_agent.subprocess.run') as mock_run:

            mock_ws = Mock()
            mock_ws.base_path = Path("/workspace")
            mock_ws_class.return_value = mock_ws

            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "test_example.py::test_one PASSED\ntest_example.py::test_two PASSED\n2 passed in 0.05s"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            result = agent._run_tests("test-workspace", ["test_example.py"])

        assert result["passed"] is True
        assert result["exit_code"] == 0
        assert result["num_tests"] == 2

    def test_run_tests_failure(self, agent):
        """Test running tests with failures."""
        with patch('src.agents.testing_agent.WorkspaceManager') as mock_ws_class, \
             patch('src.agents.testing_agent.subprocess.run') as mock_run:

            mock_ws = Mock()
            mock_ws.base_path = Path("/workspace")
            mock_ws_class.return_value = mock_ws

            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = "test_example.py::test_one FAILED\n1 failed in 0.03s"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            result = agent._run_tests("test-workspace", ["test_example.py"])

        assert result["passed"] is False
        assert result["exit_code"] == 1
        assert result["num_tests"] == 1

    def test_run_tests_timeout(self, agent):
        """Test running tests with timeout."""
        with patch('src.agents.testing_agent.WorkspaceManager') as mock_ws_class, \
             patch('src.agents.testing_agent.subprocess.run') as mock_run:

            mock_ws = Mock()
            mock_ws.base_path = Path("/workspace")
            mock_ws_class.return_value = mock_ws

            import subprocess
            mock_run.side_effect = subprocess.TimeoutExpired("pytest", 30)

            result = agent._run_tests("test-workspace", ["test_example.py"])

        assert result["passed"] is False
        assert result["exit_code"] == -1
        assert "timed out" in result["output"]
        assert result["num_tests"] == 0

    def test_parse_test_count(self, agent):
        """Test parsing test count from pytest output."""
        output1 = "test_example.py::test_one PASSED\ntest_example.py::test_two PASSED\n2 passed in 0.05s"
        assert agent._parse_test_count(output1) == 2

        output2 = "test_example.py::test_one FAILED\n1 failed, 2 passed in 0.08s"
        assert agent._parse_test_count(output2) == 3

        output3 = "5 passed in 0.10s"
        assert agent._parse_test_count(output3) == 5

        output4 = "No tests collected"
        assert agent._parse_test_count(output4) == 0

    def test_repr(self, agent):
        """Test string representation."""
        repr_str = repr(agent)

        assert "TestingAgent" in repr_str
        assert "name=" in repr_str
