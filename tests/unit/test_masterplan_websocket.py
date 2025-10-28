"""
Unit tests for Masterplan WebSocket event broadcasting.

Tests WebSocket event emission during masterplan execution.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, call
from uuid import UUID, uuid4
from datetime import datetime

from src.services.masterplan_execution_service import MasterplanExecutionService
from src.models.masterplan import (
    MasterPlan,
    MasterPlanPhase,
    MasterPlanMilestone,
    MasterPlanTask,
    MasterPlanStatus,
    TaskStatus,
)


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return Mock()


@pytest.fixture
def mock_sio():
    """Mock Socket.IO server."""
    mock = AsyncMock()
    mock.emit = AsyncMock()
    return mock


@pytest.fixture
def execution_service(mock_db_session):
    """Create execution service instance."""
    return MasterplanExecutionService(
        db_session=mock_db_session,
        workspace_base_dir="./test_workspace"
    )


@pytest.fixture
def sample_masterplan():
    """Create sample masterplan with tasks."""
    masterplan_id = uuid4()
    phase_id = uuid4()
    milestone_id = uuid4()
    task1_id = uuid4()
    task2_id = uuid4()

    masterplan = MasterPlan(
        masterplan_id=masterplan_id,
        project_name="Test Project",
        description="Test description",
        status=MasterPlanStatus.APPROVED,
        workspace_path="/test/workspace",
        created_at=datetime.utcnow(),
    )

    phase = MasterPlanPhase(
        phase_id=phase_id,
        masterplan_id=masterplan_id,
        phase_type="core",
        phase_number=1,
        name="Core Phase",
        description="Core phase description",
        created_at=datetime.utcnow(),
    )

    milestone = MasterPlanMilestone(
        milestone_id=milestone_id,
        phase_id=phase_id,
        milestone_number=1,
        name="Test Milestone",
        description="Test milestone description",
        created_at=datetime.utcnow(),
    )

    task1 = MasterPlanTask(
        task_id=task1_id,
        milestone_id=milestone_id,
        task_number=1,
        name="Task 1",
        description="First task",
        target_files=["file1.py"],
        status=TaskStatus.PENDING,
        complexity="medium",
        depends_on_tasks=[],
        max_retries=3,
        retry_count=0,
        created_at=datetime.utcnow(),
    )

    task2 = MasterPlanTask(
        task_id=task2_id,
        milestone_id=milestone_id,
        task_number=2,
        name="Task 2",
        description="Second task",
        target_files=["file2.py"],
        status=TaskStatus.PENDING,
        complexity="high",
        depends_on_tasks=[],
        max_retries=3,
        retry_count=0,
        created_at=datetime.utcnow(),
    )

    # Build relationships
    milestone.tasks = [task1, task2]
    phase.milestones = [milestone]
    masterplan.phases = [phase]

    return masterplan


class TestWebSocketEventEmission:
    """Test WebSocket event emission during masterplan execution."""

    def test_emit_masterplan_execution_start(self, execution_service, sample_masterplan, mock_sio):
        """Test that masterplan_execution_start event is emitted."""
        with patch('src.services.masterplan_execution_service.sio', mock_sio):
            # Call the emit method
            execution_service._emit_websocket_event(
                event_name="masterplan_execution_start",
                masterplan_id=sample_masterplan.masterplan_id,
                data={
                    "masterplan_id": str(sample_masterplan.masterplan_id),
                    "workspace_id": "test-workspace-id",
                    "workspace_path": sample_masterplan.workspace_path,
                    "total_tasks": 2
                }
            )

            # Verify emit was called
            assert mock_sio.emit.call_count == 1

            # Verify event name
            call_args = mock_sio.emit.call_args
            assert call_args[0][0] == "masterplan_execution_start"

            # Verify room
            assert call_args[1]["room"] == f"masterplan_{sample_masterplan.masterplan_id}"

    def test_emit_task_execution_progress(self, execution_service, sample_masterplan, mock_sio):
        """Test that task_execution_progress event is emitted."""
        task = sample_masterplan.phases[0].milestones[0].tasks[0]

        with patch('src.services.masterplan_execution_service.sio', mock_sio):
            # Call the emit method
            execution_service._emit_websocket_event(
                event_name="task_execution_progress",
                masterplan_id=sample_masterplan.masterplan_id,
                data={
                    "masterplan_id": str(sample_masterplan.masterplan_id),
                    "task_id": str(task.task_id),
                    "task_number": task.task_number,
                    "status": "in_progress",
                    "description": task.description,
                    "current_task": 1,
                    "total_tasks": 2
                }
            )

            # Verify emit was called with correct event
            assert mock_sio.emit.call_count == 1
            call_args = mock_sio.emit.call_args
            assert call_args[0][0] == "task_execution_progress"

            # Verify payload structure
            payload = call_args[0][1]
            assert payload["task_id"] == str(task.task_id)
            assert payload["status"] == "in_progress"
            assert payload["current_task"] == 1
            assert payload["total_tasks"] == 2

    def test_emit_task_execution_complete(self, execution_service, sample_masterplan, mock_sio):
        """Test that task_execution_complete event is emitted."""
        task = sample_masterplan.phases[0].milestones[0].tasks[0]

        with patch('src.services.masterplan_execution_service.sio', mock_sio):
            # Call the emit method
            execution_service._emit_websocket_event(
                event_name="task_execution_complete",
                masterplan_id=sample_masterplan.masterplan_id,
                data={
                    "masterplan_id": str(sample_masterplan.masterplan_id),
                    "task_id": str(task.task_id),
                    "status": "completed",
                    "output_files": task.target_files,
                    "completed_tasks": 1,
                    "total_tasks": 2
                }
            )

            # Verify emit was called
            assert mock_sio.emit.call_count == 1
            call_args = mock_sio.emit.call_args
            assert call_args[0][0] == "task_execution_complete"

            # Verify payload contains output files
            payload = call_args[0][1]
            assert payload["status"] == "completed"
            assert payload["output_files"] == ["file1.py"]
            assert payload["completed_tasks"] == 1

    def test_progress_callback_emits_websocket_events(self, execution_service, sample_masterplan, mock_sio, mock_db_session):
        """Test that _progress_callback emits WebSocket events."""
        task = sample_masterplan.phases[0].milestones[0].tasks[0]

        # Setup mock db query
        mock_db_session.commit = Mock()

        with patch('src.services.masterplan_execution_service.sio', mock_sio):
            # Call progress callback
            execution_service._progress_callback(
                masterplan_id=sample_masterplan.masterplan_id,
                task=task,
                status="in_progress",
                current_task=1,
                total_tasks=2
            )

            # Verify WebSocket event was emitted
            assert mock_sio.emit.call_count >= 1

            # Verify database was updated
            assert mock_db_session.commit.called
            assert task.status == TaskStatus.IN_PROGRESS

    def test_websocket_events_use_correct_room(self, execution_service, sample_masterplan, mock_sio):
        """Test that WebSocket events use the correct room format."""
        masterplan_id = sample_masterplan.masterplan_id
        expected_room = f"masterplan_{masterplan_id}"

        with patch('src.services.masterplan_execution_service.sio', mock_sio):
            # Emit different event types
            for event_name in ["masterplan_execution_start", "task_execution_progress", "task_execution_complete"]:
                mock_sio.emit.reset_mock()

                execution_service._emit_websocket_event(
                    event_name=event_name,
                    masterplan_id=masterplan_id,
                    data={"test": "data"}
                )

                # Verify room format
                call_args = mock_sio.emit.call_args
                assert call_args[1]["room"] == expected_room

    def test_websocket_event_payload_structure(self, execution_service, sample_masterplan, mock_sio):
        """Test that WebSocket events have correct payload structure."""
        task = sample_masterplan.phases[0].milestones[0].tasks[0]

        with patch('src.services.masterplan_execution_service.sio', mock_sio):
            # Test masterplan_execution_start payload
            execution_service._emit_websocket_event(
                event_name="masterplan_execution_start",
                masterplan_id=sample_masterplan.masterplan_id,
                data={
                    "masterplan_id": str(sample_masterplan.masterplan_id),
                    "workspace_id": "test-workspace",
                    "workspace_path": "/test/path",
                    "total_tasks": 2
                }
            )

            payload = mock_sio.emit.call_args[0][1]
            assert "masterplan_id" in payload
            assert "workspace_id" in payload
            assert "workspace_path" in payload
            assert "total_tasks" in payload

            # Test task_execution_progress payload
            mock_sio.emit.reset_mock()
            execution_service._emit_websocket_event(
                event_name="task_execution_progress",
                masterplan_id=sample_masterplan.masterplan_id,
                data={
                    "masterplan_id": str(sample_masterplan.masterplan_id),
                    "task_id": str(task.task_id),
                    "task_number": task.task_number,
                    "status": "in_progress",
                    "description": task.description,
                    "current_task": 1,
                    "total_tasks": 2
                }
            )

            payload = mock_sio.emit.call_args[0][1]
            assert "task_id" in payload
            assert "status" in payload
            assert "current_task" in payload
            assert "total_tasks" in payload

    def test_websocket_events_handle_errors_gracefully(self, execution_service, sample_masterplan, mock_sio):
        """Test that WebSocket event emission handles errors gracefully."""
        # Make emit raise an exception
        mock_sio.emit.side_effect = Exception("Connection error")

        with patch('src.services.masterplan_execution_service.sio', mock_sio):
            # Should not raise exception
            try:
                execution_service._emit_websocket_event(
                    event_name="masterplan_execution_start",
                    masterplan_id=sample_masterplan.masterplan_id,
                    data={"test": "data"}
                )
                # If we get here, error was handled gracefully
                assert True
            except Exception:
                # Should not reach here
                assert False, "WebSocket error was not handled gracefully"
