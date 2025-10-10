"""
Integration tests for StatefulWorkflow.
"""

import pytest
from src.workflows.stateful_workflow import StatefulWorkflow


class TestStatefulWorkflow:
    """Test StatefulWorkflow integration."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup workflow for each test."""
        self.workflow = StatefulWorkflow()
        yield
        # Cleanup
        self.workflow.close()

    def test_workflow_initialization(self):
        """Test workflow initializes correctly."""
        assert self.workflow.redis is not None
        assert self.workflow.postgres is not None

    def test_run_workflow_end_to_end(self):
        """Test complete workflow execution."""
        # Run workflow
        final_state, project_id, task_id = self.workflow.run_workflow(
            user_request="Integration test workflow",
            project_name="Integration Test",
            project_description="Testing end-to-end workflow"
        )

        # Verify final state
        assert final_state is not None
        assert final_state["user_request"] == "Integration test workflow"
        assert final_state["current_task"] == "stateful_agent_complete"
        assert final_state["agent_name"] == "stateful_agent"
        assert len(final_state["messages"]) == 1
        assert final_state["generated_code"] != ""

        # Verify project_id and task_id
        assert project_id is not None
        assert task_id is not None

    def test_redis_state_persistence(self):
        """Test that workflow state is saved to Redis."""
        # Run workflow
        final_state, project_id, task_id = self.workflow.run_workflow(
            user_request="Redis persistence test",
            project_name="Redis Test"
        )

        workflow_id = final_state["workflow_id"]

        # Retrieve state from Redis
        redis_state = self.workflow.get_workflow_state_from_redis(workflow_id)
        assert redis_state is not None
        assert redis_state["user_request"] == "Redis persistence test"
        assert redis_state["workflow_id"] == workflow_id

    def test_postgres_task_persistence(self):
        """Test that task is saved to PostgreSQL."""
        # Run workflow
        final_state, project_id, task_id = self.workflow.run_workflow(
            user_request="PostgreSQL persistence test",
            project_name="PostgreSQL Test"
        )

        # Retrieve task from PostgreSQL
        task = self.workflow.get_task_from_postgres(task_id)
        assert task is not None
        assert str(task["id"]) == str(task_id)  # Compare as strings
        assert task["status"] == "completed"
        assert task["agent_name"] == "stateful_agent"
        assert task["task_type"] == "greeting"
        assert task["completed_at"] is not None

    def test_cost_tracking_integration(self):
        """Test cost tracking integration."""
        # Run workflow
        final_state, project_id, task_id = self.workflow.run_workflow(
            user_request="Cost tracking test",
            project_name="Cost Test"
        )

        # Track cost
        cost_id = self.workflow.track_llm_cost(
            task_id=task_id,
            model_name="claude-sonnet-4.5",
            input_tokens=150,
            output_tokens=75,
            cost_usd=0.003
        )
        assert cost_id is not None

        # Verify cost was tracked
        project_costs = self.workflow.postgres.get_project_costs(project_id)
        assert project_costs is not None
        assert float(project_costs["total_cost"]) == 0.003
        assert project_costs["total_input_tokens"] == 150
        assert project_costs["total_output_tokens"] == 75
        assert project_costs["api_calls"] == 1

    def test_multiple_workflow_executions(self):
        """Test running multiple workflows in sequence."""
        results = []

        for i in range(3):
            final_state, project_id, task_id = self.workflow.run_workflow(
                user_request=f"Multiple workflow test {i}",
                project_name=f"Multi Test {i}"
            )
            results.append((final_state, project_id, task_id))

        # Verify all workflows completed
        assert len(results) == 3
        for final_state, project_id, task_id in results:
            assert final_state["current_task"] == "stateful_agent_complete"
            assert project_id is not None
            assert task_id is not None

    def test_workflow_state_contains_all_fields(self):
        """Test that workflow state contains all required fields."""
        final_state, project_id, task_id = self.workflow.run_workflow(
            user_request="Complete state test",
            project_name="State Test"
        )

        # Verify all required fields are present
        required_fields = [
            "user_request",
            "messages",
            "current_task",
            "generated_code",
            "workflow_id",
            "project_id",
            "agent_name",
            "error",
            "retry_count",
            "task_id"
        ]

        for field in required_fields:
            assert field in final_state, f"Missing field: {field}"

    def test_project_tasks_retrieval(self):
        """Test retrieving all tasks for a project."""
        # Run workflow
        final_state, project_id, task_id = self.workflow.run_workflow(
            user_request="Task retrieval test",
            project_name="Task Retrieval Test"
        )

        # Get all tasks for the project
        tasks = self.workflow.postgres.get_project_tasks(project_id)
        assert len(tasks) >= 1
        assert any(str(task["id"]) == str(task_id) for task in tasks)  # Compare as strings

    def test_workflow_with_long_request(self):
        """Test workflow with very long user request."""
        long_request = "A" * 1000  # 1000 character request

        final_state, project_id, task_id = self.workflow.run_workflow(
            user_request=long_request,
            project_name="Long Request Test"
        )

        assert final_state["user_request"] == long_request
        assert len(final_state["user_request"]) == 1000

    def test_workflow_with_special_characters(self):
        """Test workflow with special characters in request."""
        special_request = "Test with 特殊字符 émojis 🚀 and symbols @#$%"

        final_state, project_id, task_id = self.workflow.run_workflow(
            user_request=special_request,
            project_name="Special Chars Test"
        )

        assert final_state["user_request"] == special_request

    def test_redis_and_postgres_sync(self):
        """Test that Redis and PostgreSQL stay in sync."""
        final_state, project_id, task_id = self.workflow.run_workflow(
            user_request="Sync test",
            project_name="Sync Test"
        )

        workflow_id = final_state["workflow_id"]

        # Get state from both sources
        redis_state = self.workflow.get_workflow_state_from_redis(workflow_id)
        postgres_task = self.workflow.get_task_from_postgres(task_id)

        # Verify sync
        assert redis_state["user_request"] == "Sync test"
        assert postgres_task["status"] == "completed"
        # task_id gets updated after workflow completes, verify from final_state
        assert str(final_state["task_id"]) == str(postgres_task["id"])

    def test_multiple_cost_entries_same_task(self):
        """Test tracking multiple costs for same task."""
        final_state, project_id, task_id = self.workflow.run_workflow(
            user_request="Multiple costs test",
            project_name="Multi Cost Test"
        )

        # Track multiple costs
        cost_ids = []
        for i in range(3):
            cost_id = self.workflow.track_llm_cost(
                task_id=task_id,
                model_name=f"model-{i}",
                input_tokens=100 * (i + 1),
                output_tokens=50 * (i + 1),
                cost_usd=0.01 * (i + 1)
            )
            cost_ids.append(cost_id)

        # Verify all tracked
        assert len(cost_ids) == 3

        # Verify aggregation
        project_costs = self.workflow.postgres.get_project_costs(project_id)
        assert project_costs["api_calls"] == 3
        assert float(project_costs["total_cost"]) == 0.06  # 0.01 + 0.02 + 0.03

    def test_workflow_error_state_persistence(self):
        """Test that workflow state with errors persists correctly."""
        # Create a state with error manually
        from uuid import uuid4

        workflow_id = str(uuid4())
        error_state = {
            "user_request": "Error test",
            "messages": [],
            "current_task": "failed",
            "generated_code": "",
            "workflow_id": workflow_id,
            "project_id": str(uuid4()),
            "agent_name": "test_agent",
            "error": "Simulated error",
            "retry_count": 2,
            "task_id": ""
        }

        # Save to Redis
        self.workflow.redis.save_workflow_state(workflow_id, error_state)

        # Retrieve and verify
        retrieved = self.workflow.get_workflow_state_from_redis(workflow_id)
        assert retrieved["error"] == "Simulated error"
        assert retrieved["retry_count"] == 2
        assert retrieved["current_task"] == "failed"
