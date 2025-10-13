"""
Unit tests for OrchestratorAgent
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.agents.orchestrator_agent import OrchestratorAgent, Task
from src.agents.agent_registry import AgentRegistry, AgentCapability, TaskType


class TestOrchestratorAgent:
    """Test suite for OrchestratorAgent."""

    @pytest.fixture
    def agent(self):
        """Create OrchestratorAgent with mocked dependencies."""
        with patch('src.agents.orchestrator_agent.AnthropicClient') as mock_class:
            with patch('src.agents.orchestrator_agent.PostgresManager'):
                mock_client = Mock()
                mock_class.return_value = mock_client
                agent = OrchestratorAgent()
                agent.llm = mock_client
                yield agent

    def test_init(self, agent):
        """Test agent initialization."""
        assert agent.llm is not None
        assert agent.console is not None
        assert agent.graph is not None

    def test_analyze_project_simple(self, agent):
        """Test project analysis for simple function."""
        agent.llm.generate.return_value = {
            'content': """Project Type: simple function
Complexity: 0.2
Components: fibonacci calculator
Languages: Python""",
            'model': 'claude',
            'usage': {'input_tokens': 100, 'output_tokens': 50},
            'stop_reason': 'end_turn'
        }

        state = {
            "user_request": "Create a fibonacci function",
            "context": {},
            "messages": [],
            "project_type": "",
            "complexity": 0.0,
            "tasks": [],
            "dependency_graph": {},
            "completed_tasks": [],
            "failed_tasks": [],
            "workspace_id": "test",
            "project_structure": {},
            "success": False,
            "error_message": ""
        }

        result = agent._analyze_project(state)

        assert result["project_type"] == "simple function"
        assert result["complexity"] == 0.2
        assert len(result["messages"]) == 1

    def test_analyze_project_complex(self, agent):
        """Test project analysis for complex API."""
        agent.llm.generate.return_value = {
            'content': """Project Type: REST API
Complexity: 0.8
Components: User management, Authentication, Database
Languages: Python, FastAPI""",
            'model': 'claude',
            'usage': {'input_tokens': 100, 'output_tokens': 50},
            'stop_reason': 'end_turn'
        }

        state = {
            "user_request": "Create REST API for user management",
            "context": {},
            "messages": [],
            "project_type": "",
            "complexity": 0.0,
            "tasks": [],
            "dependency_graph": {},
            "completed_tasks": [],
            "failed_tasks": [],
            "workspace_id": "test",
            "project_structure": {},
            "success": False,
            "error_message": ""
        }

        result = agent._analyze_project(state)

        assert "api" in result["project_type"].lower()
        assert result["complexity"] == 0.8

    def test_decompose_tasks_simple(self, agent):
        """Test task decomposition for simple project."""
        agent.llm.generate.return_value = {
            'content': """```json
[
  {
    "id": "task_1",
    "description": "Create fibonacci function",
    "task_type": "implementation",
    "dependencies": [],
    "files": ["fibonacci.py"]
  },
  {
    "id": "task_2",
    "description": "Create tests for fibonacci function",
    "task_type": "testing",
    "dependencies": ["task_1"],
    "files": ["test_fibonacci.py"]
  }
]
```""",
            'model': 'claude',
            'usage': {'input_tokens': 150, 'output_tokens': 100},
            'stop_reason': 'end_turn'
        }

        state = {
            "user_request": "Create fibonacci function",
            "context": {},
            "messages": [],
            "project_type": "simple function",
            "complexity": 0.2,
            "tasks": [],
            "dependency_graph": {},
            "completed_tasks": [],
            "failed_tasks": [],
            "workspace_id": "test",
            "project_structure": {},
            "success": False,
            "error_message": ""
        }

        result = agent._decompose_tasks(state)

        assert len(result["tasks"]) == 2
        assert result["tasks"][0]["id"] == "task_1"
        assert result["tasks"][0]["task_type"] == "implementation"
        assert result["tasks"][1]["dependencies"] == ["task_1"]

    def test_decompose_tasks_complex(self, agent):
        """Test task decomposition for complex project."""
        agent.llm.generate.return_value = {
            'content': """```json
[
  {
    "id": "task_1",
    "description": "Create User model",
    "task_type": "implementation",
    "dependencies": [],
    "files": ["models/user.py"]
  },
  {
    "id": "task_2",
    "description": "Create API routes",
    "task_type": "implementation",
    "dependencies": ["task_1"],
    "files": ["routes/users.py"]
  },
  {
    "id": "task_3",
    "description": "Create tests for User model",
    "task_type": "testing",
    "dependencies": ["task_1"],
    "files": ["tests/test_user.py"]
  },
  {
    "id": "task_4",
    "description": "Create API documentation",
    "task_type": "documentation",
    "dependencies": ["task_1", "task_2"],
    "files": ["README.md"]
  }
]
```""",
            'model': 'claude',
            'usage': {'input_tokens': 200, 'output_tokens': 150},
            'stop_reason': 'end_turn'
        }

        state = {
            "user_request": "Create REST API for user management",
            "context": {},
            "messages": [],
            "project_type": "REST API",
            "complexity": 0.8,
            "tasks": [],
            "dependency_graph": {},
            "completed_tasks": [],
            "failed_tasks": [],
            "workspace_id": "test",
            "project_structure": {},
            "success": False,
            "error_message": ""
        }

        result = agent._decompose_tasks(state)

        assert len(result["tasks"]) == 4
        assert result["tasks"][0]["task_type"] == "implementation"
        assert result["tasks"][2]["task_type"] == "testing"
        assert result["tasks"][3]["task_type"] == "documentation"

    def test_decompose_tasks_json_fallback(self, agent):
        """Test task decomposition with invalid JSON (should fallback)."""
        agent.llm.generate.return_value = {
            'content': "This is not valid JSON",
            'model': 'claude',
            'usage': {'input_tokens': 100, 'output_tokens': 50},
            'stop_reason': 'end_turn'
        }

        state = {
            "user_request": "Create function",
            "context": {},
            "messages": [],
            "project_type": "simple function",
            "complexity": 0.2,
            "tasks": [],
            "dependency_graph": {},
            "completed_tasks": [],
            "failed_tasks": [],
            "workspace_id": "test",
            "project_structure": {},
            "success": False,
            "error_message": ""
        }

        result = agent._decompose_tasks(state)

        # Should fallback to single task
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["id"] == "task_1"
        assert result["tasks"][0]["task_type"] == "implementation"

    def test_build_dependency_graph(self, agent):
        """Test building dependency graph from tasks."""
        tasks = [
            Task(
                id="task_1",
                description="Create model",
                task_type="implementation",
                dependencies=[],
                assigned_agent="",
                status="pending",
                output={}
            ),
            Task(
                id="task_2",
                description="Create tests",
                task_type="testing",
                dependencies=["task_1"],
                assigned_agent="",
                status="pending",
                output={}
            ),
            Task(
                id="task_3",
                description="Create docs",
                task_type="documentation",
                dependencies=["task_1", "task_2"],
                assigned_agent="",
                status="pending",
                output={}
            )
        ]

        state = {
            "user_request": "Create module",
            "context": {},
            "messages": [],
            "project_type": "module",
            "complexity": 0.5,
            "tasks": tasks,
            "dependency_graph": {},
            "completed_tasks": [],
            "failed_tasks": [],
            "workspace_id": "test",
            "project_structure": {},
            "success": False,
            "error_message": ""
        }

        result = agent._build_dependency_graph(state)

        assert result["dependency_graph"]["task_1"] == []
        assert result["dependency_graph"]["task_2"] == ["task_1"]
        assert result["dependency_graph"]["task_3"] == ["task_1", "task_2"]

    def test_orchestrate_integration(self, agent):
        """Test complete orchestration workflow."""
        # Mock LLM responses for full workflow
        agent.llm.generate.side_effect = [
            # analyze_project
            {
                'content': """Project Type: simple module
Complexity: 0.4
Components: calculator
Languages: Python""",
                'model': 'claude',
                'usage': {'input_tokens': 100, 'output_tokens': 50},
                'stop_reason': 'end_turn'
            },
            # decompose_tasks
            {
                'content': """```json
[
  {
    "id": "task_1",
    "description": "Create calculator functions",
    "task_type": "implementation",
    "dependencies": [],
    "files": ["calculator.py"]
  },
  {
    "id": "task_2",
    "description": "Create tests",
    "task_type": "testing",
    "dependencies": ["task_1"],
    "files": ["test_calculator.py"]
  }
]
```""",
                'model': 'claude',
                'usage': {'input_tokens': 150, 'output_tokens': 100},
                'stop_reason': 'end_turn'
            }
        ]

        result = agent.orchestrate(
            user_request="Create a calculator module",
            workspace_id="test-calc"
        )

        assert result["success"] is True
        assert result["workspace_id"] == "test-calc"
        assert result["project_type"] == "simple module"
        assert result["complexity"] == 0.4
        assert len(result["tasks"]) == 2
        assert len(result["dependency_graph"]) == 2

    def test_orchestrate_auto_workspace_id(self, agent):
        """Test orchestration with auto-generated workspace ID."""
        agent.llm.generate.side_effect = [
            {
                'content': """Project Type: function
Complexity: 0.2
Components: simple function
Languages: Python""",
                'model': 'claude',
                'usage': {'input_tokens': 100, 'output_tokens': 50},
                'stop_reason': 'end_turn'
            },
            {
                'content': """```json
[
  {
    "id": "task_1",
    "description": "Create function",
    "task_type": "implementation",
    "dependencies": [],
    "files": ["main.py"]
  }
]
```""",
                'model': 'claude',
                'usage': {'input_tokens': 150, 'output_tokens': 100},
                'stop_reason': 'end_turn'
            }
        ]

        result = agent.orchestrate(user_request="Create hello world")

        assert "orchestrated-" in result["workspace_id"]
        assert result["success"] is True

    def test_display_plan(self, agent):
        """Test displaying execution plan."""
        tasks = [
            Task(
                id="task_1",
                description="Create model",
                task_type="implementation",
                dependencies=[],
                assigned_agent="",
                status="pending",
                output={}
            ),
            Task(
                id="task_2",
                description="Create tests",
                task_type="testing",
                dependencies=["task_1"],
                assigned_agent="",
                status="pending",
                output={}
            )
        ]

        state = {
            "user_request": "Create module",
            "context": {},
            "messages": [],
            "project_type": "module",
            "complexity": 0.5,
            "tasks": tasks,
            "dependency_graph": {"task_1": [], "task_2": ["task_1"]},
            "completed_tasks": [],
            "failed_tasks": [],
            "workspace_id": "test",
            "project_structure": {},
            "success": False,
            "error_message": ""
        }

        # Should not raise exception
        result = agent._display_plan(state)
        assert result is not None

    def test_finalize(self, agent):
        """Test finalization step."""
        state = {
            "user_request": "Create module",
            "context": {},
            "messages": [],
            "project_type": "module",
            "complexity": 0.5,
            "tasks": [],
            "dependency_graph": {},
            "completed_tasks": [],
            "failed_tasks": [],
            "workspace_id": "test",
            "project_structure": {},
            "success": False,
            "error_message": ""
        }

        result = agent._finalize(state)

        assert result["success"] is True
        assert result["completed_tasks"] == []
        assert result["failed_tasks"] == []

    def test_assign_agents_with_registry(self):
        """Test agent assignment with populated registry."""
        # Create mock agent class
        class MockAgent:
            def execute(self, task, context):
                return {"success": True}
            def get_capabilities(self):
                return {AgentCapability.CODE_GENERATION}
            def get_name(self):
                return "mock_agent"

        # Create registry and register mock agent
        registry = AgentRegistry()
        registry.register(
            name="code_agent",
            agent_class=MockAgent,
            capabilities={AgentCapability.CODE_GENERATION, AgentCapability.API_DESIGN},
            priority=10
        )
        registry.register(
            name="test_agent",
            agent_class=MockAgent,
            capabilities={AgentCapability.UNIT_TESTING},
            priority=8
        )

        # Create orchestrator with custom registry
        with patch('src.agents.orchestrator_agent.AnthropicClient'):
            with patch('src.agents.orchestrator_agent.PostgresManager'):
                orchestrator = OrchestratorAgent(agent_registry=registry)

        # Create state with tasks
        tasks = [
            Task(
                id="task_1",
                description="Create model",
                task_type="implementation",
                dependencies=[],
                assigned_agent="",
                status="pending",
                output={}
            ),
            Task(
                id="task_2",
                description="Create tests",
                task_type="testing",
                dependencies=["task_1"],
                assigned_agent="",
                status="pending",
                output={}
            )
        ]

        state = {
            "user_request": "Create module",
            "context": {},
            "messages": [],
            "project_type": "module",
            "complexity": 0.5,
            "tasks": tasks,
            "dependency_graph": {"task_1": [], "task_2": ["task_1"]},
            "completed_tasks": [],
            "failed_tasks": [],
            "workspace_id": "test",
            "project_structure": {},
            "success": False,
            "error_message": ""
        }

        result = orchestrator._assign_agents(state)

        # Verify agents were assigned
        assert result["tasks"][0]["assigned_agent"] == "code_agent"
        assert result["tasks"][1]["assigned_agent"] == "test_agent"

    def test_assign_agents_no_agent_available(self):
        """Test agent assignment when no agent available."""
        # Create empty registry
        registry = AgentRegistry()

        # Create orchestrator with empty registry
        with patch('src.agents.orchestrator_agent.AnthropicClient'):
            with patch('src.agents.orchestrator_agent.PostgresManager'):
                orchestrator = OrchestratorAgent(agent_registry=registry)

        # Create state with task
        tasks = [
            Task(
                id="task_1",
                description="Create model",
                task_type="implementation",
                dependencies=[],
                assigned_agent="",
                status="pending",
                output={}
            )
        ]

        state = {
            "user_request": "Create module",
            "context": {},
            "messages": [],
            "project_type": "module",
            "complexity": 0.5,
            "tasks": tasks,
            "dependency_graph": {"task_1": []},
            "completed_tasks": [],
            "failed_tasks": [],
            "workspace_id": "test",
            "project_structure": {},
            "success": False,
            "error_message": ""
        }

        result = orchestrator._assign_agents(state)

        # Verify task marked as unassigned
        assert result["tasks"][0]["assigned_agent"] == "unassigned"
