"""
Unit tests for MultiAgentWorkflow
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.workflows.multi_agent_workflow import MultiAgentWorkflow, MultiAgentState


class TestMultiAgentWorkflow:
    """Test suite for MultiAgentWorkflow."""

    @pytest.fixture
    def mock_components(self):
        """Create all mocked components."""
        with patch('src.workflows.multi_agent_workflow.OrchestratorAgent') as mock_orch, \
             patch('src.workflows.multi_agent_workflow.AgentRegistry') as mock_reg, \
             patch('src.workflows.multi_agent_workflow.SharedScratchpad') as mock_scratch, \
             patch('src.workflows.multi_agent_workflow.ParallelExecutor') as mock_exec, \
             patch('src.workflows.multi_agent_workflow.ImplementationAgent') as mock_impl, \
             patch('src.workflows.multi_agent_workflow.TestingAgent') as mock_test, \
             patch('src.workflows.multi_agent_workflow.DocumentationAgent') as mock_doc:

            yield {
                'orchestrator': mock_orch,
                'registry': mock_reg,
                'scratchpad': mock_scratch,
                'executor': mock_exec,
                'implementation': mock_impl,
                'testing': mock_test,
                'documentation': mock_doc
            }

    @pytest.fixture
    def workflow(self, mock_components):
        """Create workflow with mocked components."""
        return MultiAgentWorkflow(workspace_id="test-workspace")

    def test_init(self, workflow):
        """Test workflow initialization."""
        assert workflow.workspace_id == "test-workspace"
        assert workflow.max_workers == 4
        assert workflow.orchestrator is not None
        assert workflow.registry is not None
        assert workflow.scratchpad is not None
        assert workflow.executor is not None
        assert workflow.graph is not None

    def test_init_with_custom_params(self, mock_components):
        """Test initialization with custom parameters."""
        workflow = MultiAgentWorkflow(
            workspace_id="custom-ws",
            max_workers=8,
            redis_host="redis.example.com",
            redis_port=6380
        )

        assert workflow.workspace_id == "custom-ws"
        assert workflow.max_workers == 8

    def test_register_agents(self, workflow, mock_components):
        """Test agent registration during initialization."""
        # Registry's register_agent should be called for each agent type
        registry_instance = workflow.registry

        # Check that register_agent was called (3 agents: Implementation, Testing, Documentation)
        assert registry_instance.register_agent.call_count == 3

    def test_plan_node_success(self, workflow):
        """Test successful planning node execution."""
        # Mock orchestrator response
        workflow.orchestrator.orchestrate.return_value = {
            "success": True,
            "plan": {
                "tasks": [
                    {"id": "task_1", "description": "Write code", "task_type": "implementation"},
                    {"id": "task_2", "description": "Write tests", "task_type": "testing"}
                ]
            },
            "dependency_graph": {"task_1": [], "task_2": ["task_1"]}
        }

        # Create initial state
        state = MultiAgentState(
            project_request="Build calculator",
            workspace_id="test-ws",
            tasks=[],
            dependency_graph={},
            scratchpad=workflow.scratchpad,
            registry=workflow.registry,
            executor=workflow.executor,
            completed_tasks=[],
            failed_tasks=[],
            execution_stats={},
            messages=[],
            status="initialized",
            error=""
        )

        # Execute plan node
        result = workflow._plan_node(state)

        assert result["status"] == "planning"
        assert len(result["tasks"]) == 2
        assert result["tasks"][0]["id"] == "task_1"
        assert "Planning" in result["messages"][0]

    def test_plan_node_failure(self, workflow):
        """Test planning node with orchestrator failure."""
        # Mock orchestrator failure
        workflow.orchestrator.orchestrate.return_value = {
            "success": False,
            "error": "Failed to decompose project"
        }

        state = MultiAgentState(
            project_request="Build calculator",
            workspace_id="test-ws",
            tasks=[],
            dependency_graph={},
            scratchpad=workflow.scratchpad,
            registry=workflow.registry,
            executor=workflow.executor,
            completed_tasks=[],
            failed_tasks=[],
            execution_stats={},
            messages=[],
            status="initialized",
            error=""
        )

        result = workflow._plan_node(state)

        assert result["status"] == "failed"
        assert "Planning failed" in result["error"]

    def test_plan_node_exception(self, workflow):
        """Test planning node with exception."""
        # Mock orchestrator to raise exception
        workflow.orchestrator.orchestrate.side_effect = RuntimeError("Orchestrator error")

        state = MultiAgentState(
            project_request="Build calculator",
            workspace_id="test-ws",
            tasks=[],
            dependency_graph={},
            scratchpad=workflow.scratchpad,
            registry=workflow.registry,
            executor=workflow.executor,
            completed_tasks=[],
            failed_tasks=[],
            execution_stats={},
            messages=[],
            status="initialized",
            error=""
        )

        result = workflow._plan_node(state)

        assert result["status"] == "failed"
        assert "Planning exception" in result["error"]

    def test_execute_node_success(self, workflow):
        """Test successful execution node."""
        # Mock registry to return agents
        workflow.registry.find_agent_for_task.return_value = {
            "success": True,
            "agent_name": "ImplementationAgent"
        }

        mock_agent = Mock()
        mock_agent.execute.return_value = {
            "success": True,
            "output": "Code generated",
            "error": None
        }
        workflow.registry.get_agent_instance.return_value = mock_agent

        # Mock executor
        workflow.executor.execute_tasks.return_value = {
            "results": {"task_1": {"success": True}},
            "completed_tasks": ["task_1"],
            "failed_tasks": [],
            "stats": {
                "successful": 1,
                "failed": 0,
                "skipped": 0,
                "parallel_time_saved": 0.5
            }
        }

        state = MultiAgentState(
            project_request="Build calculator",
            workspace_id="test-ws",
            tasks=[{"id": "task_1", "description": "Write code", "task_type": "implementation"}],
            dependency_graph={"task_1": []},
            scratchpad=workflow.scratchpad,
            registry=workflow.registry,
            executor=workflow.executor,
            completed_tasks=[],
            failed_tasks=[],
            execution_stats={},
            messages=[],
            status="planning",
            error=""
        )

        result = workflow._execute_node(state)

        assert result["status"] == "completed"
        assert "task_1" in result["completed_tasks"]
        assert len(result["failed_tasks"]) == 0
        assert "Executing" in result["messages"][0]

    def test_execute_node_with_failures(self, workflow):
        """Test execution node with some task failures."""
        # Mock registry
        workflow.registry.find_agent_for_task.return_value = {
            "success": True,
            "agent_name": "TestingAgent"
        }

        mock_agent = Mock()
        mock_agent.execute.return_value = {
            "success": False,
            "output": None,
            "error": "Tests failed"
        }
        workflow.registry.get_agent_instance.return_value = mock_agent

        # Mock executor with failures
        workflow.executor.execute_tasks.return_value = {
            "results": {"task_1": {"success": False}},
            "completed_tasks": [],
            "failed_tasks": ["task_1"],
            "stats": {
                "successful": 0,
                "failed": 1,
                "skipped": 0,
                "parallel_time_saved": 0.0
            }
        }

        state = MultiAgentState(
            project_request="Build calculator",
            workspace_id="test-ws",
            tasks=[{"id": "task_1", "description": "Write tests", "task_type": "testing"}],
            dependency_graph={"task_1": []},
            scratchpad=workflow.scratchpad,
            registry=workflow.registry,
            executor=workflow.executor,
            completed_tasks=[],
            failed_tasks=[],
            execution_stats={},
            messages=[],
            status="planning",
            error=""
        )

        result = workflow._execute_node(state)

        assert result["status"] == "completed_with_errors"
        assert "task_1" in result["failed_tasks"]

    def test_execute_node_no_agent_found(self, workflow):
        """Test execution when no appropriate agent is found."""
        # Mock registry to return no agent
        workflow.registry.find_agent_for_task.return_value = {
            "success": False,
            "error": "No matching agent"
        }

        # Mock executor
        workflow.executor.execute_tasks.return_value = {
            "results": {"task_1": {"success": False, "error": "No agent found"}},
            "completed_tasks": [],
            "failed_tasks": ["task_1"],
            "stats": {
                "successful": 0,
                "failed": 1,
                "skipped": 0,
                "parallel_time_saved": 0.0
            }
        }

        state = MultiAgentState(
            project_request="Build calculator",
            workspace_id="test-ws",
            tasks=[{"id": "task_1", "description": "Unknown task", "task_type": "unknown"}],
            dependency_graph={"task_1": []},
            scratchpad=workflow.scratchpad,
            registry=workflow.registry,
            executor=workflow.executor,
            completed_tasks=[],
            failed_tasks=[],
            execution_stats={},
            messages=[],
            status="planning",
            error=""
        )

        result = workflow._execute_node(state)

        assert result["status"] == "completed_with_errors"

    def test_execute_node_exception(self, workflow):
        """Test execution node with exception."""
        # Mock executor to raise exception
        workflow.executor.execute_tasks.side_effect = RuntimeError("Execution error")

        state = MultiAgentState(
            project_request="Build calculator",
            workspace_id="test-ws",
            tasks=[{"id": "task_1", "description": "Write code", "task_type": "implementation"}],
            dependency_graph={"task_1": []},
            scratchpad=workflow.scratchpad,
            registry=workflow.registry,
            executor=workflow.executor,
            completed_tasks=[],
            failed_tasks=[],
            execution_stats={},
            messages=[],
            status="planning",
            error=""
        )

        result = workflow._execute_node(state)

        assert result["status"] == "failed"
        assert "Execution exception" in result["error"]

    def test_finalize_node_success(self, workflow):
        """Test successful finalize node."""
        # Mock scratchpad
        workflow.scratchpad.read_artifacts.return_value = [
            {"id": "artifact_1", "type": "CODE"},
            {"id": "artifact_2", "type": "TEST"}
        ]

        state = MultiAgentState(
            project_request="Build calculator",
            workspace_id="test-ws",
            tasks=[],
            dependency_graph={},
            scratchpad=workflow.scratchpad,
            registry=workflow.registry,
            executor=workflow.executor,
            completed_tasks=["task_1"],
            failed_tasks=[],
            execution_stats={"successful": 1},
            messages=[],
            status="completed",
            error=""
        )

        result = workflow._finalize_node(state)

        assert "Finalizing" in result["messages"][0]
        assert "2 artifacts" in result["messages"][1]

    def test_finalize_node_exception(self, workflow):
        """Test finalize node with exception."""
        # Mock scratchpad to raise exception
        workflow.scratchpad.read_artifacts.side_effect = RuntimeError("Scratchpad error")

        state = MultiAgentState(
            project_request="Build calculator",
            workspace_id="test-ws",
            tasks=[],
            dependency_graph={},
            scratchpad=workflow.scratchpad,
            registry=workflow.registry,
            executor=workflow.executor,
            completed_tasks=["task_1"],
            failed_tasks=[],
            execution_stats={"successful": 1},
            messages=[],
            status="completed",
            error=""
        )

        result = workflow._finalize_node(state)

        # Should handle exception gracefully with warning
        assert any("warning" in msg.lower() for msg in result["messages"])

    def test_run_end_to_end_success(self, workflow):
        """Test complete workflow run with success."""
        # Mock orchestrator
        workflow.orchestrator.orchestrate.return_value = {
            "success": True,
            "plan": {
                "tasks": [{"id": "task_1", "description": "Write code", "task_type": "implementation"}]
            },
            "dependency_graph": {"task_1": []}
        }

        # Mock registry
        workflow.registry.find_agent_for_task.return_value = {
            "success": True,
            "agent_name": "ImplementationAgent"
        }

        mock_agent = Mock()
        mock_agent.execute.return_value = {"success": True, "output": "Code"}
        workflow.registry.get_agent_instance.return_value = mock_agent

        # Mock executor
        workflow.executor.execute_tasks.return_value = {
            "results": {"task_1": {"success": True}},
            "completed_tasks": ["task_1"],
            "failed_tasks": [],
            "stats": {"successful": 1, "failed": 0, "skipped": 0, "parallel_time_saved": 0.0}
        }

        # Mock scratchpad
        workflow.scratchpad.read_artifacts.return_value = [{"id": "artifact_1"}]

        # Run workflow
        result = workflow.run("Build a calculator")

        assert result["success"] is True
        assert result["status"] in ["completed", "completed_with_errors"]
        assert len(result["completed_tasks"]) > 0
        assert "messages" in result

    def test_run_end_to_end_failure(self, workflow):
        """Test complete workflow run with failure."""
        # Mock orchestrator failure
        workflow.orchestrator.orchestrate.return_value = {
            "success": False,
            "error": "Planning failed"
        }

        result = workflow.run("Build a calculator")

        assert result["success"] is False
        assert result["status"] == "failed"
        assert "error" in result

    def test_get_workflow_visualization(self, workflow):
        """Test workflow visualization."""
        viz = workflow.get_workflow_visualization()

        assert isinstance(viz, str)
        # Should contain workflow steps
        assert "plan" in viz.lower() or "execute" in viz.lower() or "finalize" in viz.lower()

    def test_repr(self, workflow):
        """Test string representation."""
        repr_str = repr(workflow)

        assert "MultiAgentWorkflow" in repr_str
        assert "workspace_id=test-workspace" in repr_str
        assert "max_workers=4" in repr_str

    def test_postgres_tracking(self, mock_components):
        """Test workflow with PostgreSQL tracking enabled."""
        with patch('src.workflows.multi_agent_workflow.PostgresManager') as mock_pg:
            workflow = MultiAgentWorkflow(
                workspace_id="test-ws",
                postgres_config={"dbname": "test", "user": "test", "password": "test"}
            )

            assert workflow.postgres is not None
            mock_pg.assert_called_once()

    def test_agent_executor_function(self, workflow):
        """Test the agent executor function used in execute node."""
        # This tests the inner function created in _execute_node
        # We'll test it through the execute_node path

        workflow.registry.find_agent_for_task.return_value = {
            "success": True,
            "agent_name": "DocumentationAgent"
        }

        mock_agent = Mock()
        mock_agent.execute.return_value = {
            "success": True,
            "output": "Documentation generated"
        }
        workflow.registry.get_agent_instance.return_value = mock_agent

        # We need to actually call the executor, not mock its return value
        # Store the original execute_tasks to capture the executor function
        original_execute_tasks = workflow.executor.execute_tasks
        captured_executor_func = None

        def capture_executor_func(tasks, executor_func, context):
            nonlocal captured_executor_func
            captured_executor_func = executor_func
            # Call the executor function for each task
            results = {}
            for task in tasks:
                results[task["id"]] = executor_func(task, context)
            return {
                "results": results,
                "completed_tasks": [task["id"] for task in tasks],
                "failed_tasks": [],
                "stats": {"successful": 1, "failed": 0, "skipped": 0, "parallel_time_saved": 0.0}
            }

        workflow.executor.execute_tasks = capture_executor_func

        state = MultiAgentState(
            project_request="Document code",
            workspace_id="test-ws",
            tasks=[{"id": "task_1", "description": "Generate docs", "task_type": "documentation"}],
            dependency_graph={"task_1": []},
            scratchpad=workflow.scratchpad,
            registry=workflow.registry,
            executor=workflow.executor,
            completed_tasks=[],
            failed_tasks=[],
            execution_stats={},
            messages=[],
            status="planning",
            error=""
        )

        result = workflow._execute_node(state)

        # Verify agent was called correctly
        assert mock_agent.execute.called
        assert result["status"] == "completed"

    def test_workflow_with_multiple_tasks(self, workflow):
        """Test workflow with multiple interdependent tasks."""
        # Mock orchestrator with multiple tasks
        workflow.orchestrator.orchestrate.return_value = {
            "success": True,
            "plan": {
                "tasks": [
                    {"id": "task_1", "description": "Write code", "task_type": "implementation"},
                    {"id": "task_2", "description": "Write tests", "task_type": "testing", "dependencies": ["task_1"]},
                    {"id": "task_3", "description": "Write docs", "task_type": "documentation", "dependencies": ["task_1"]}
                ]
            },
            "dependency_graph": {
                "task_1": [],
                "task_2": ["task_1"],
                "task_3": ["task_1"]
            }
        }

        # Mock registry and agents
        workflow.registry.find_agent_for_task.return_value = {"success": True, "agent_name": "TestAgent"}
        mock_agent = Mock()
        mock_agent.execute.return_value = {"success": True, "output": "Done"}
        workflow.registry.get_agent_instance.return_value = mock_agent

        # Mock executor
        workflow.executor.execute_tasks.return_value = {
            "results": {
                "task_1": {"success": True},
                "task_2": {"success": True},
                "task_3": {"success": True}
            },
            "completed_tasks": ["task_1", "task_2", "task_3"],
            "failed_tasks": [],
            "stats": {
                "successful": 3,
                "failed": 0,
                "skipped": 0,
                "parallel_time_saved": 1.5
            }
        }

        # Mock scratchpad
        workflow.scratchpad.read_artifacts.return_value = [
            {"id": "art_1"}, {"id": "art_2"}, {"id": "art_3"}
        ]

        result = workflow.run("Build calculator with tests and docs")

        assert result["success"] is True
        assert len(result["completed_tasks"]) == 3
        assert result["execution_stats"]["successful"] == 3
