"""
Unit tests for PostgresManager.
"""

import pytest
from uuid import uuid4
from src.state.postgres_manager import PostgresManager


class TestPostgresManager:
    """Test PostgresManager functionality."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup Postgres manager for each test."""
        self.postgres = PostgresManager()
        yield
        # Cleanup after each test
        self.postgres.close()

    def test_connection(self):
        """Test PostgreSQL connection."""
        # If we get here without exception, connection works
        assert self.postgres.conn is not None
        assert self.postgres.conn.closed == 0

    def test_create_and_get_project(self):
        """Test creating and retrieving a project."""
        # Create project
        project_id = self.postgres.create_project(
            name="Test Project",
            description="A test project for unit testing"
        )
        assert project_id is not None

        # Retrieve project
        project = self.postgres.get_project(project_id)
        assert project is not None
        assert project["name"] == "Test Project"
        assert project["description"] == "A test project for unit testing"
        assert project["status"] == "in_progress"

    def test_get_nonexistent_project(self):
        """Test retrieving non-existent project."""
        nonexistent_id = uuid4()
        project = self.postgres.get_project(nonexistent_id)
        assert project is None

    def test_create_and_get_task(self, sample_task_input):
        """Test creating and retrieving a task."""
        # Create project first
        project_id = self.postgres.create_project(name="Task Test Project")

        # Create task
        task_id = self.postgres.create_task(
            project_id=project_id,
            agent_name="test_agent",
            task_type="testing",
            input_data=sample_task_input
        )
        assert task_id is not None

        # Retrieve task
        task = self.postgres.get_task(task_id)
        assert task is not None
        assert task["agent_name"] == "test_agent"
        assert task["task_type"] == "testing"
        assert task["status"] == "pending"
        assert task["project_id"] == project_id

    def test_update_task_status(self, sample_task_input, sample_task_output):
        """Test updating task status."""
        # Create project and task
        project_id = self.postgres.create_project(name="Status Update Test")
        task_id = self.postgres.create_task(
            project_id=project_id,
            agent_name="test_agent",
            task_type="testing",
            input_data=sample_task_input
        )

        # Update to in_progress
        updated = self.postgres.update_task_status(
            task_id=task_id,
            status="in_progress"
        )
        assert updated is True

        task = self.postgres.get_task(task_id)
        assert task["status"] == "in_progress"

        # Update to completed with output
        updated = self.postgres.update_task_status(
            task_id=task_id,
            status="completed",
            output_data=sample_task_output
        )
        assert updated is True

        task = self.postgres.get_task(task_id)
        assert task["status"] == "completed"
        assert task["completed_at"] is not None

    def test_get_project_tasks(self, sample_task_input):
        """Test retrieving all tasks for a project."""
        # Create project
        project_id = self.postgres.create_project(name="Multiple Tasks Test")

        # Create multiple tasks
        task_ids = []
        for i in range(3):
            task_id = self.postgres.create_task(
                project_id=project_id,
                agent_name=f"agent_{i}",
                task_type="testing",
                input_data=sample_task_input
            )
            task_ids.append(task_id)

        # Retrieve all tasks
        tasks = self.postgres.get_project_tasks(project_id)
        assert len(tasks) == 3
        assert all(task["project_id"] == project_id for task in tasks)

    def test_track_cost(self):
        """Test tracking LLM cost."""
        # Create project and task
        project_id = self.postgres.create_project(name="Cost Tracking Test")
        task_id = self.postgres.create_task(
            project_id=project_id,
            agent_name="test_agent",
            task_type="testing"
        )

        # Track cost
        cost_id = self.postgres.track_cost(
            task_id=task_id,
            model_name="claude-sonnet-4.5",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.002
        )
        assert cost_id is not None

    def test_get_project_costs(self):
        """Test getting project cost summary."""
        # Create project and task
        project_id = self.postgres.create_project(name="Cost Summary Test")
        task_id = self.postgres.create_task(
            project_id=project_id,
            agent_name="test_agent",
            task_type="testing"
        )

        # Track multiple costs
        self.postgres.track_cost(
            task_id=task_id,
            model_name="claude-sonnet-4.5",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.002
        )
        self.postgres.track_cost(
            task_id=task_id,
            model_name="claude-sonnet-4.5",
            input_tokens=200,
            output_tokens=100,
            cost_usd=0.004
        )

        # Get cost summary
        costs = self.postgres.get_project_costs(project_id)
        assert costs is not None
        assert float(costs["total_cost"]) == 0.006
        assert costs["total_input_tokens"] == 300
        assert costs["total_output_tokens"] == 150
        assert costs["api_calls"] == 2

    def test_get_monthly_costs(self):
        """Test getting monthly cost summary."""
        from datetime import datetime

        # Create project and task
        project_id = self.postgres.create_project(name="Monthly Cost Test")
        task_id = self.postgres.create_task(
            project_id=project_id,
            agent_name="test_agent",
            task_type="testing"
        )

        # Track cost
        self.postgres.track_cost(
            task_id=task_id,
            model_name="claude-sonnet-4.5",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.002
        )

        # Get monthly costs for current month
        now = datetime.now()
        monthly_costs = self.postgres.get_monthly_costs(year=now.year, month=now.month)

        assert monthly_costs is not None
        assert monthly_costs["year"] == now.year
        assert monthly_costs["month"] == now.month
        assert monthly_costs["total_cost_usd"] >= 0.002
        assert monthly_costs["total_api_calls"] >= 1

    def test_log_decision(self):
        """Test logging agent decision."""
        # Create project and task
        project_id = self.postgres.create_project(name="Decision Test")
        task_id = self.postgres.create_task(
            project_id=project_id,
            agent_name="test_agent",
            task_type="testing"
        )

        # Log decision
        decision_id = self.postgres.log_decision(
            task_id=task_id,
            decision_type="implementation_approach",
            reasoning="Chose approach B for best balance of performance and maintainability",
            approved=True,
            metadata={"options": ["A", "B", "C"], "selected": "B"}
        )
        assert decision_id is not None

    def test_update_task_status_with_error(self, sample_task_input):
        """Test updating task status to failed with error message."""
        # Create project and task
        project_id = self.postgres.create_project(name="Error Test")
        task_id = self.postgres.create_task(
            project_id=project_id,
            agent_name="test_agent",
            task_type="testing",
            input_data=sample_task_input
        )

        # Update to failed with error
        updated = self.postgres.update_task_status(
            task_id=task_id,
            status="failed",
            error="Test error occurred"
        )
        assert updated is True

        task = self.postgres.get_task(task_id)
        assert task["status"] == "failed"
        assert task["completed_at"] is not None

    def test_create_task_without_input_data(self):
        """Test creating task without input data."""
        project_id = self.postgres.create_project(name="No Input Test")

        task_id = self.postgres.create_task(
            project_id=project_id,
            agent_name="test_agent",
            task_type="testing",
            input_data=None  # No input data
        )
        assert task_id is not None

        task = self.postgres.get_task(task_id)
        assert task is not None
        assert task["input"] == ""

    def test_get_project_tasks_empty(self):
        """Test getting tasks for project with no tasks."""
        project_id = self.postgres.create_project(name="Empty Tasks Test")

        tasks = self.postgres.get_project_tasks(project_id)
        assert tasks is not None
        assert len(tasks) == 0

    def test_get_project_costs_no_costs(self):
        """Test getting costs for project with no cost entries."""
        project_id = self.postgres.create_project(name="No Costs Test")

        costs = self.postgres.get_project_costs(project_id)
        # Should return empty dict or dict with None values
        assert costs is not None

    def test_track_cost_zero_tokens(self):
        """Test tracking cost with zero tokens."""
        project_id = self.postgres.create_project(name="Zero Tokens Test")
        task_id = self.postgres.create_task(
            project_id=project_id,
            agent_name="test_agent",
            task_type="testing"
        )

        cost_id = self.postgres.track_cost(
            task_id=task_id,
            model_name="test-model",
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0
        )
        assert cost_id is not None

    def test_track_cost_large_numbers(self):
        """Test tracking cost with large token counts."""
        project_id = self.postgres.create_project(name="Large Tokens Test")
        task_id = self.postgres.create_task(
            project_id=project_id,
            agent_name="test_agent",
            task_type="testing"
        )

        cost_id = self.postgres.track_cost(
            task_id=task_id,
            model_name="test-model",
            input_tokens=1000000,
            output_tokens=500000,
            cost_usd=150.50
        )
        assert cost_id is not None

        # Verify retrieval
        costs = self.postgres.get_project_costs(project_id)
        assert float(costs["total_cost"]) == 150.50
        assert costs["total_input_tokens"] == 1000000
        assert costs["total_output_tokens"] == 500000

    def test_create_project_with_empty_description(self):
        """Test creating project with empty description."""
        project_id = self.postgres.create_project(name="Empty Desc", description="")
        assert project_id is not None

        project = self.postgres.get_project(project_id)
        assert project["description"] == ""

    def test_create_project_with_long_name(self):
        """Test creating project with long name."""
        long_name = "A" * 255  # Max VARCHAR(255)
        project_id = self.postgres.create_project(name=long_name)
        assert project_id is not None

        project = self.postgres.get_project(project_id)
        assert project["name"] == long_name

    def test_multiple_tasks_same_project(self):
        """Test creating multiple tasks for same project."""
        project_id = self.postgres.create_project(name="Multi Task Project")

        task_ids = []
        for i in range(5):
            task_id = self.postgres.create_task(
                project_id=project_id,
                agent_name=f"agent_{i}",
                task_type="testing",
                input_data={"iteration": i}
            )
            task_ids.append(task_id)

        # Verify all tasks exist
        tasks = self.postgres.get_project_tasks(project_id)
        assert len(tasks) == 5

        # Verify they're ordered by created_at DESC
        for i in range(len(tasks) - 1):
            assert tasks[i]["created_at"] >= tasks[i + 1]["created_at"]

    def test_task_status_transitions(self):
        """Test all valid task status transitions."""
        project_id = self.postgres.create_project(name="Status Transition Test")
        task_id = self.postgres.create_task(
            project_id=project_id,
            agent_name="test_agent",
            task_type="testing"
        )

        # pending → in_progress
        self.postgres.update_task_status(task_id, "in_progress")
        task = self.postgres.get_task(task_id)
        assert task["status"] == "in_progress"

        # in_progress → completed
        self.postgres.update_task_status(task_id, "completed")
        task = self.postgres.get_task(task_id)
        assert task["status"] == "completed"
        assert task["completed_at"] is not None

    def test_task_cancelled_status(self):
        """Test task can be cancelled."""
        project_id = self.postgres.create_project(name="Cancel Test")
        task_id = self.postgres.create_task(
            project_id=project_id,
            agent_name="test_agent",
            task_type="testing"
        )

        self.postgres.update_task_status(task_id, "cancelled")
        task = self.postgres.get_task(task_id)
        assert task["status"] == "cancelled"

    def test_log_decision_without_approval(self):
        """Test logging decision without approval status."""
        project_id = self.postgres.create_project(name="Decision No Approval")
        task_id = self.postgres.create_task(
            project_id=project_id,
            agent_name="test_agent",
            task_type="testing"
        )

        decision_id = self.postgres.log_decision(
            task_id=task_id,
            decision_type="automatic_decision",
            reasoning="Automatically selected based on heuristics",
            approved=None,  # No approval needed
            metadata={}
        )
        assert decision_id is not None

    def test_log_decision_rejected(self):
        """Test logging rejected decision."""
        project_id = self.postgres.create_project(name="Decision Rejected")
        task_id = self.postgres.create_task(
            project_id=project_id,
            agent_name="test_agent",
            task_type="testing"
        )

        decision_id = self.postgres.log_decision(
            task_id=task_id,
            decision_type="user_intervention",
            reasoning="User rejected proposed approach",
            approved=False,
            metadata={"user_feedback": "Need different approach"}
        )
        assert decision_id is not None

    def test_get_monthly_costs_no_data(self):
        """Test getting monthly costs when no data exists for that month."""
        from datetime import datetime
        future_year = datetime.now().year + 1
        future_month = 12

        monthly_costs = self.postgres.get_monthly_costs(year=future_year, month=future_month)
        assert monthly_costs is not None
        assert monthly_costs["year"] == future_year
        assert monthly_costs["month"] == future_month
        assert monthly_costs["total_cost_usd"] == 0.0
        assert monthly_costs["total_api_calls"] == 0
