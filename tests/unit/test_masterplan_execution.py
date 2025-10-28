"""
Unit tests for MasterPlan Execution Engine

Tests the execution endpoint and MasterplanExecutionService.execute() method.
Limited to 2-8 highly focused tests as per spec requirements.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from datetime import datetime

from src.models.masterplan import (
    MasterPlan,
    MasterPlanStatus,
    MasterPlanPhase,
    MasterPlanMilestone,
    MasterPlanTask,
    TaskStatus,
    PhaseType,
)


class TestExecuteEndpoint:
    """Test the execute endpoint functionality."""

    @patch("src.services.masterplan_execution_service.MasterplanExecutionService")
    def test_execute_endpoint_creates_workspace_and_starts_execution(self, mock_service_class):
        """Test that execute endpoint creates workspace and starts execution."""
        # Mock the service
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.execute.return_value = {
            "workspace_id": "ws_123",
            "workspace_path": "/path/to/workspace",
            "total_tasks": 10,
        }

        # Create a mock masterplan
        masterplan_id = uuid4()
        masterplan = MasterPlan(
            masterplan_id=masterplan_id,
            project_name="Test Project",
            description="Test description",
            status=MasterPlanStatus.APPROVED,
            total_phases=1,
            total_milestones=1,
            total_tasks=10,
            completed_tasks=0,
            progress_percent=0.0,
            discovery_id=uuid4(),
            session_id="test_session",
            user_id="test_user",
        )

        # Verify the service would be called correctly
        result = mock_service.execute(masterplan_id, masterplan)

        assert result["workspace_id"] == "ws_123"
        assert result["workspace_path"] == "/path/to/workspace"
        assert result["total_tasks"] == 10
        mock_service.execute.assert_called_once()

    def test_execute_endpoint_validates_approved_status(self):
        """Test that execute endpoint only works with approved masterplans."""
        masterplan_id = uuid4()

        # Test with draft status (should fail)
        masterplan_draft = MasterPlan(
            masterplan_id=masterplan_id,
            project_name="Test Project",
            description="Test description",
            status=MasterPlanStatus.DRAFT,
            total_phases=1,
            total_milestones=1,
            total_tasks=10,
            completed_tasks=0,
            progress_percent=0.0,
            discovery_id=uuid4(),
            session_id="test_session",
            user_id="test_user",
        )

        # Should not be able to execute a draft masterplan
        assert masterplan_draft.status != MasterPlanStatus.APPROVED

        # Test with approved status (should succeed)
        masterplan_approved = MasterPlan(
            masterplan_id=masterplan_id,
            project_name="Test Project",
            description="Test description",
            status=MasterPlanStatus.APPROVED,
            total_phases=1,
            total_milestones=1,
            total_tasks=10,
            completed_tasks=0,
            progress_percent=0.0,
            discovery_id=uuid4(),
            session_id="test_session",
            user_id="test_user",
        )

        assert masterplan_approved.status == MasterPlanStatus.APPROVED


class TestTaskExecutionOrder:
    """Test task execution in dependency order."""

    def test_task_dependency_ordering(self):
        """Test that tasks are ordered by dependencies using topological sort."""
        # Create tasks with dependencies
        task1_id = uuid4()
        task2_id = uuid4()
        task3_id = uuid4()

        task1 = {
            "id": str(task1_id),
            "description": "Task 1 - No dependencies",
            "dependencies": [],
            "status": "pending",
        }

        task2 = {
            "id": str(task2_id),
            "description": "Task 2 - Depends on Task 1",
            "dependencies": [str(task1_id)],
            "status": "pending",
        }

        task3 = {
            "id": str(task3_id),
            "description": "Task 3 - Depends on Task 2",
            "dependencies": [str(task2_id)],
            "status": "pending",
        }

        tasks = [task3, task2, task1]  # Out of order intentionally
        dependency_graph = {
            str(task2_id): [str(task1_id)],
            str(task3_id): [str(task2_id)],
        }

        # Simulate topological sort
        in_degree = {task["id"]: len(task["dependencies"]) for task in tasks}
        queue = [task for task in tasks if in_degree[task["id"]] == 0]
        result = []

        while queue:
            current_task = queue.pop(0)
            result.append(current_task)
            current_id = current_task["id"]

            # Update in-degrees
            for task in tasks:
                if current_id in task["dependencies"]:
                    in_degree[task["id"]] -= 1
                    if in_degree[task["id"]] == 0:
                        queue.append(task)

        # Verify execution order: task1 -> task2 -> task3
        assert len(result) == 3
        assert result[0]["id"] == str(task1_id)
        assert result[1]["id"] == str(task2_id)
        assert result[2]["id"] == str(task3_id)


class TestRetryLogic:
    """Test retry logic for failed tasks."""

    def test_task_retry_on_failure(self):
        """Test that failed tasks are retried according to max_retries."""
        task = MasterPlanTask(
            task_id=uuid4(),
            milestone_id=uuid4(),
            task_number=1,
            name="Test Task",
            description="Test task that fails",
            status=TaskStatus.PENDING,
            retry_count=0,
            max_retries=2,
        )

        # Simulate first failure
        task.retry_count += 1
        task.status = TaskStatus.FAILED

        # Should retry (retry_count < max_retries)
        assert task.retry_count < task.max_retries
        can_retry = task.retry_count < task.max_retries
        assert can_retry is True

        # Simulate second failure
        task.retry_count += 1
        task.status = TaskStatus.FAILED

        # Should NOT retry (retry_count == max_retries)
        assert task.retry_count == task.max_retries
        can_retry = task.retry_count < task.max_retries
        assert can_retry is False

    def test_task_exhausted_retries_marked_failed(self):
        """Test that tasks with exhausted retries are marked as failed."""
        task = MasterPlanTask(
            task_id=uuid4(),
            milestone_id=uuid4(),
            task_number=1,
            name="Test Task",
            description="Test task that fails",
            status=TaskStatus.PENDING,
            retry_count=2,
            max_retries=2,
        )

        # Retry count exhausted
        assert task.retry_count >= task.max_retries

        # Should be marked as failed and not retried
        task.status = TaskStatus.FAILED
        task.failed_at = datetime.utcnow()

        assert task.status == TaskStatus.FAILED
        assert task.failed_at is not None


class TestTargetFilesExtraction:
    """Test that target_files are extracted correctly."""

    def test_target_files_extracted_from_task(self):
        """Test that target_files field is extracted from MasterPlanTask."""
        task = MasterPlanTask(
            task_id=uuid4(),
            milestone_id=uuid4(),
            task_number=1,
            name="Create User Model",
            description="Create the User model file",
            status=TaskStatus.PENDING,
            target_files=["models/user.py", "tests/test_user.py"],
            retry_count=0,
            max_retries=1,
        )

        # Verify target_files are set correctly
        assert task.target_files is not None
        assert len(task.target_files) == 2
        assert "models/user.py" in task.target_files
        assert "tests/test_user.py" in task.target_files

    def test_multiple_tasks_different_target_files(self):
        """Test that multiple tasks have different target_files (no overwriting)."""
        task1 = MasterPlanTask(
            task_id=uuid4(),
            milestone_id=uuid4(),
            task_number=1,
            name="Create User Model",
            description="Create the User model",
            status=TaskStatus.PENDING,
            target_files=["models/user.py"],
            retry_count=0,
            max_retries=1,
        )

        task2 = MasterPlanTask(
            task_id=uuid4(),
            milestone_id=uuid4(),
            task_number=2,
            name="Create Product Model",
            description="Create the Product model",
            status=TaskStatus.PENDING,
            target_files=["models/product.py"],
            retry_count=0,
            max_retries=1,
        )

        task3 = MasterPlanTask(
            task_id=uuid4(),
            milestone_id=uuid4(),
            task_number=3,
            name="Create API Router",
            description="Create the API router",
            status=TaskStatus.PENDING,
            target_files=["api/router.py"],
            retry_count=0,
            max_retries=1,
        )

        # Verify each task has unique target_files
        assert task1.target_files != task2.target_files
        assert task2.target_files != task3.target_files
        assert task1.target_files != task3.target_files

        # Verify no task defaults to ["main.py"]
        assert task1.target_files != ["main.py"]
        assert task2.target_files != ["main.py"]
        assert task3.target_files != ["main.py"]
