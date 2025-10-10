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
