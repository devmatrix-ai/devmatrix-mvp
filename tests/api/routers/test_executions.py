"""
Tests for Executions API Router

Tests workflow execution management endpoints.

Author: DevMatrix Team
Date: 2025-11-03
"""

import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routers.executions import router, ExecutionStatus


@pytest.fixture
def client():
    """Create test client with executions router."""
    test_app = FastAPI()
    test_app.include_router(router)
    return TestClient(test_app)


@pytest.fixture
def sample_execution_id():
    """Sample execution ID."""
    return f"exec_{uuid4()}"


@pytest.fixture
def sample_workflow_id():
    """Sample workflow ID."""
    return f"wf_{uuid4()}"


@pytest.fixture
def sample_execution(sample_execution_id, sample_workflow_id):
    """Sample execution data."""
    return {
        "execution_id": sample_execution_id,
        "workflow_id": sample_workflow_id,
        "status": ExecutionStatus.PENDING,
        "input_data": {"user_request": "Test request"},
        "priority": 5,
        "task_statuses": [],
        "started_at": None,
        "completed_at": None,
        "error": None,
        "result": None,
        "created_at": datetime.now(),
        "tasks": []
    }


# ============================================================================
# POST /executions Tests
# ============================================================================

def test_create_execution_success(client, sample_workflow_id):
    """Test successful execution creation."""
    with patch('src.api.routers.executions.workflows_db', {sample_workflow_id: {"id": sample_workflow_id}}):
        response = client.post(
            "/executions",
            json={
                "workflow_id": sample_workflow_id,
                "input_data": {"user_request": "Test"},
                "priority": 7
            }
        )

    assert response.status_code == 201
    data = response.json()
    assert 'execution_id' in data
    assert data['workflow_id'] == sample_workflow_id
    assert data['status'] == 'pending'
    assert data['priority'] == 7


def test_create_execution_default_priority(client, sample_workflow_id):
    """Test execution creation with default priority."""
    with patch('src.api.routers.executions.workflows_db', {sample_workflow_id: {"id": sample_workflow_id}}):
        response = client.post(
            "/executions",
            json={
                "workflow_id": sample_workflow_id,
                "input_data": {}
            }
        )

    assert response.status_code == 201
    data = response.json()
    assert data['priority'] == 5  # Default priority


def test_create_execution_workflow_not_found(client):
    """Test execution creation with non-existent workflow."""
    workflow_id = f"wf_{uuid4()}"

    with patch('src.api.routers.executions.workflows_db', {}):
        response = client.post(
            "/executions",
            json={
                "workflow_id": workflow_id,
                "input_data": {}
            }
        )

    assert response.status_code == 404
    assert "Workflow not found" in response.json()['detail']


def test_create_execution_invalid_priority(client, sample_workflow_id):
    """Test execution creation with invalid priority."""
    with patch('src.api.routers.executions.workflows_db', {sample_workflow_id: {"id": sample_workflow_id}}):
        # Priority > 10
        response = client.post(
            "/executions",
            json={
                "workflow_id": sample_workflow_id,
                "input_data": {},
                "priority": 15
            }
        )

    assert response.status_code == 422  # Validation error


def test_create_execution_empty_input_data(client, sample_workflow_id):
    """Test execution creation with empty input data."""
    with patch('src.api.routers.executions.workflows_db', {sample_workflow_id: {"id": sample_workflow_id}}):
        response = client.post(
            "/executions",
            json={
                "workflow_id": sample_workflow_id
            }
        )

    assert response.status_code == 201
    data = response.json()
    assert data['input_data'] == {}


# ============================================================================
# GET /executions Tests
# ============================================================================

def test_list_executions_success(client, sample_execution):
    """Test successful execution listing."""
    mock_db = {sample_execution['execution_id']: sample_execution}

    with patch('src.api.routers.executions.executions_db', mock_db):
        response = client.get("/executions")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]['execution_id'] == sample_execution['execution_id']


def test_list_executions_with_status_filter(client, sample_execution):
    """Test execution listing filtered by status."""
    completed_exec = sample_execution.copy()
    completed_exec['execution_id'] = "exec_2"
    completed_exec['status'] = ExecutionStatus.COMPLETED

    pending_exec = sample_execution.copy()
    pending_exec['execution_id'] = "exec_3"
    pending_exec['status'] = ExecutionStatus.PENDING

    mock_db = {
        "exec_2": completed_exec,
        "exec_3": pending_exec
    }

    with patch('src.api.routers.executions.executions_db', mock_db):
        response = client.get("/executions?status=completed")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]['status'] == 'completed'


def test_list_executions_with_workflow_filter(client, sample_execution):
    """Test execution listing filtered by workflow_id."""
    workflow_1 = "wf_1"
    workflow_2 = "wf_2"

    exec_1 = sample_execution.copy()
    exec_1['execution_id'] = "exec_1"
    exec_1['workflow_id'] = workflow_1

    exec_2 = sample_execution.copy()
    exec_2['execution_id'] = "exec_2"
    exec_2['workflow_id'] = workflow_2

    mock_db = {
        "exec_1": exec_1,
        "exec_2": exec_2
    }

    with patch('src.api.routers.executions.executions_db', mock_db):
        response = client.get(f"/executions?workflow_id={workflow_1}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]['workflow_id'] == workflow_1


def test_list_executions_empty(client):
    """Test execution listing with no executions."""
    with patch('src.api.routers.executions.executions_db', {}):
        response = client.get("/executions")

    assert response.status_code == 200
    assert response.json() == []


def test_list_executions_with_pagination(client):
    """Test execution listing with pagination parameters."""
    # Create 20 executions
    mock_db = {}
    for i in range(20):
        exec_data = {
            "execution_id": f"exec_{i}",
            "workflow_id": "wf_1",
            "status": ExecutionStatus.COMPLETED,
            "created_at": datetime.now()
        }
        mock_db[f"exec_{i}"] = exec_data

    with patch('src.api.routers.executions.executions_db', mock_db):
        response = client.get("/executions?skip=5&limit=10")

    assert response.status_code == 200
    data = response.json()
    # Should return at most 10 items, skipping first 5
    assert len(data) <= 10


# ============================================================================
# GET /executions/{execution_id} Tests
# ============================================================================

def test_get_execution_detail_success(client, sample_execution):
    """Test successful execution detail retrieval."""
    exec_id = sample_execution['execution_id']
    mock_db = {exec_id: sample_execution}

    with patch('src.api.routers.executions.executions_db', mock_db):
        response = client.get(f"/executions/{exec_id}")

    assert response.status_code == 200
    data = response.json()
    assert data['execution_id'] == exec_id
    assert 'task_statuses' in data


def test_get_execution_detail_not_found(client):
    """Test getting non-existent execution."""
    exec_id = "exec_nonexistent"

    with patch('src.api.routers.executions.executions_db', {}):
        response = client.get(f"/executions/{exec_id}")

    assert response.status_code == 404
    assert "Execution not found" in response.json()['detail']


def test_get_execution_detail_completed(client, sample_execution):
    """Test getting completed execution with results."""
    sample_execution['status'] = ExecutionStatus.COMPLETED
    sample_execution['result'] = {"output": "Success"}
    sample_execution['completed_at'] = datetime.now()

    exec_id = sample_execution['execution_id']
    mock_db = {exec_id: sample_execution}

    with patch('src.api.routers.executions.executions_db', mock_db):
        response = client.get(f"/executions/{exec_id}")

    data = response.json()
    assert data['status'] == 'completed'
    assert data['result'] is not None


def test_get_execution_detail_failed(client, sample_execution):
    """Test getting failed execution with error."""
    sample_execution['status'] = ExecutionStatus.FAILED
    sample_execution['error'] = "Task execution failed"

    exec_id = sample_execution['execution_id']
    mock_db = {exec_id: sample_execution}

    with patch('src.api.routers.executions.executions_db', mock_db):
        response = client.get(f"/executions/{exec_id}")

    data = response.json()
    assert data['status'] == 'failed'
    assert data['error'] == "Task execution failed"


# ============================================================================
# POST /executions/{execution_id}/cancel Tests
# ============================================================================

def test_cancel_execution_success(client, sample_execution):
    """Test successful execution cancellation."""
    sample_execution['status'] = ExecutionStatus.RUNNING

    exec_id = sample_execution['execution_id']
    mock_db = {exec_id: sample_execution}

    with patch('src.api.routers.executions.executions_db', mock_db):
        response = client.post(f"/executions/{exec_id}/cancel")

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'cancelled'


def test_cancel_execution_not_found(client):
    """Test cancelling non-existent execution."""
    exec_id = "exec_nonexistent"

    with patch('src.api.routers.executions.executions_db', {}):
        response = client.post(f"/executions/{exec_id}/cancel")

    assert response.status_code == 404


def test_cancel_execution_already_completed(client, sample_execution):
    """Test cancelling already completed execution."""
    sample_execution['status'] = ExecutionStatus.COMPLETED

    exec_id = sample_execution['execution_id']
    mock_db = {exec_id: sample_execution}

    with patch('src.api.routers.executions.executions_db', mock_db):
        response = client.post(f"/executions/{exec_id}/cancel")

    assert response.status_code == 400
    assert "Cannot cancel" in response.json()['detail']


def test_cancel_execution_already_cancelled(client, sample_execution):
    """Test cancelling already cancelled execution."""
    sample_execution['status'] = ExecutionStatus.CANCELLED

    exec_id = sample_execution['execution_id']
    mock_db = {exec_id: sample_execution}

    with patch('src.api.routers.executions.executions_db', mock_db):
        response = client.post(f"/executions/{exec_id}/cancel")

    # Should be idempotent or return 400
    assert response.status_code in [200, 400]


def test_cancel_execution_pending(client, sample_execution):
    """Test cancelling pending execution."""
    sample_execution['status'] = ExecutionStatus.PENDING

    exec_id = sample_execution['execution_id']
    mock_db = {exec_id: sample_execution}

    with patch('src.api.routers.executions.executions_db', mock_db):
        response = client.post(f"/executions/{exec_id}/cancel")

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'cancelled'


# ============================================================================
# DELETE /executions/{execution_id} Tests
# ============================================================================

def test_delete_execution_success(client, sample_execution):
    """Test successful execution deletion."""
    sample_execution['status'] = ExecutionStatus.COMPLETED

    exec_id = sample_execution['execution_id']
    mock_db = {exec_id: sample_execution}

    with patch('src.api.routers.executions.executions_db', mock_db):
        response = client.delete(f"/executions/{exec_id}")

    assert response.status_code == 204


def test_delete_execution_not_found(client):
    """Test deleting non-existent execution."""
    exec_id = "exec_nonexistent"

    with patch('src.api.routers.executions.executions_db', {}):
        response = client.delete(f"/executions/{exec_id}")

    assert response.status_code == 404


def test_delete_execution_running(client, sample_execution):
    """Test deleting running execution."""
    sample_execution['status'] = ExecutionStatus.RUNNING

    exec_id = sample_execution['execution_id']
    mock_db = {exec_id: sample_execution}

    with patch('src.api.routers.executions.executions_db', mock_db):
        response = client.delete(f"/executions/{exec_id}")

    assert response.status_code == 400
    assert "Cannot delete" in response.json()['detail']


def test_delete_execution_failed(client, sample_execution):
    """Test deleting failed execution."""
    sample_execution['status'] = ExecutionStatus.FAILED

    exec_id = sample_execution['execution_id']
    mock_db = {exec_id: sample_execution}

    with patch('src.api.routers.executions.executions_db', mock_db):
        response = client.delete(f"/executions/{exec_id}")

    assert response.status_code == 204


def test_delete_execution_cancelled(client, sample_execution):
    """Test deleting cancelled execution."""
    sample_execution['status'] = ExecutionStatus.CANCELLED

    exec_id = sample_execution['execution_id']
    mock_db = {exec_id: sample_execution}

    with patch('src.api.routers.executions.executions_db', mock_db):
        response = client.delete(f"/executions/{exec_id}")

    assert response.status_code == 204


# ============================================================================
# Unit Tests for Models
# ============================================================================

@pytest.mark.unit
class TestExecutionsModels:
    """Unit tests for executions models."""

    def test_execution_status_enum(self):
        """Test ExecutionStatus enum values."""
        assert ExecutionStatus.PENDING.value == "pending"
        assert ExecutionStatus.RUNNING.value == "running"
        assert ExecutionStatus.COMPLETED.value == "completed"
        assert ExecutionStatus.FAILED.value == "failed"
        assert ExecutionStatus.CANCELLED.value == "cancelled"

    def test_execution_create_model(self):
        """Test ExecutionCreate model validation."""
        from src.api.routers.executions import ExecutionCreate

        request = ExecutionCreate(
            workflow_id="wf_123",
            input_data={"key": "value"},
            priority=7
        )

        assert request.workflow_id == "wf_123"
        assert request.priority == 7

    def test_execution_create_default_values(self):
        """Test ExecutionCreate model defaults."""
        from src.api.routers.executions import ExecutionCreate

        request = ExecutionCreate(workflow_id="wf_123")

        assert request.input_data == {}
        assert request.priority == 5

    def test_task_status_model(self):
        """Test TaskStatus model."""
        from src.api.routers.executions import TaskStatus

        task = TaskStatus(
            task_id="task_1",
            status=ExecutionStatus.COMPLETED,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            result={"output": "Success"}
        )

        assert task.task_id == "task_1"
        assert task.status == ExecutionStatus.COMPLETED
        assert task.result is not None

    def test_execution_response_model(self):
        """Test ExecutionResponse model."""
        from src.api.routers.executions import ExecutionResponse

        response = ExecutionResponse(
            execution_id="exec_123",
            workflow_id="wf_123",
            status=ExecutionStatus.RUNNING,
            input_data={"key": "value"},
            priority=5,
            task_statuses=[],
            started_at=datetime.now(),
            completed_at=None,
            error=None,
            result=None,
            created_at=datetime.now()
        )

        assert response.execution_id == "exec_123"
        assert response.status == ExecutionStatus.RUNNING

