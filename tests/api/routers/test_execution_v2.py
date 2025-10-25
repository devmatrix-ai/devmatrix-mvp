"""
Tests for Execution V2 API Router

Tests all REST endpoints for wave-based parallel execution with intelligent retry.

Author: DevMatrix Team
Date: 2025-10-25
"""

import pytest
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from fastapi import FastAPI, status as http_status
from fastapi.testclient import TestClient

from src.api.routers.execution_v2 import router
from src.mge.v2.services.execution_service_v2 import (
    ExecutionState,
    ExecutionStatus,
)
from src.mge.v2.execution.wave_executor import ExecutionResult


@pytest.fixture
def client():
    """Create test client with execution_v2 router."""
    test_app = FastAPI()
    test_app.include_router(router)
    return TestClient(test_app)


@pytest.fixture
def mock_execution_service():
    """Create mock ExecutionServiceV2."""
    service = MagicMock()
    service.start_execution = AsyncMock()
    service.get_execution_state = MagicMock()
    service.get_execution_metrics = MagicMock()
    service.get_wave_status = MagicMock()
    service.get_atom_status = MagicMock()
    service.pause_execution = AsyncMock()
    service.resume_execution = AsyncMock()
    service.list_executions = MagicMock(return_value=[])
    return service


@pytest.fixture
def sample_execution_id():
    """Sample execution UUID."""
    return uuid4()


@pytest.fixture
def sample_masterplan_id():
    """Sample masterplan UUID."""
    return uuid4()


@pytest.fixture
def sample_execution_state(sample_execution_id, sample_masterplan_id):
    """Sample ExecutionState."""
    return ExecutionState(
        execution_id=sample_execution_id,
        masterplan_id=sample_masterplan_id,
        status=ExecutionStatus.RUNNING,
        current_wave=1,
        total_waves=3,
        atoms_completed=5,
        atoms_total=10,
        atoms_succeeded=5,
        atoms_failed=0,
        total_cost_usd=1.50,
        total_time_seconds=30.5,
        started_at=datetime.utcnow()
    )


# ============================================================================
# POST /api/v2/execution/start
# ============================================================================

@patch("src.api.routers.execution_v2.get_execution_service")
def test_start_execution_success(
    mock_get_service,
    client,
    mock_execution_service,
    sample_execution_id,
    sample_masterplan_id,
    sample_execution_state
):
    """Test starting execution successfully."""
    # Setup
    mock_get_service.return_value = mock_execution_service
    mock_execution_service.start_execution.return_value = sample_execution_id
    mock_execution_service.get_execution_state.return_value = sample_execution_state

    # Execute
    response = client.post(
        "/api/v2/execution/start",
        json={
            "masterplan_id": str(sample_masterplan_id),
            "execution_plan": [{"level": 0, "atom_ids": ["a1", "a2"]}],
            "atoms": {"a1": {}, "a2": {}}
        }
    )

    # Verify
    assert response.status_code == http_status.HTTP_202_ACCEPTED
    data = response.json()
    assert data["execution_id"] == str(sample_execution_id)
    assert data["masterplan_id"] == str(sample_masterplan_id)
    assert data["status"] == "running"
    assert data["total_waves"] == 3
    assert data["atoms_total"] == 10
    assert "Execution started" in data["message"]


@patch("src.api.routers.execution_v2.get_execution_service")
def test_start_execution_invalid_masterplan_id(
    mock_get_service,
    client,
    mock_execution_service
):
    """Test starting execution with invalid masterplan_id."""
    # Setup
    mock_get_service.return_value = mock_execution_service

    # Execute
    response = client.post(
        "/api/v2/execution/start",
        json={
            "masterplan_id": "invalid-uuid",
            "execution_plan": [],
            "atoms": {}
        }
    )

    # Verify
    assert response.status_code == http_status.HTTP_400_BAD_REQUEST
    assert "Invalid request" in response.json()["detail"]


@patch("src.api.routers.execution_v2.get_execution_service")
def test_start_execution_service_error(
    mock_get_service,
    client,
    mock_execution_service,
    sample_masterplan_id
):
    """Test starting execution with service error."""
    # Setup
    mock_get_service.return_value = mock_execution_service
    mock_execution_service.start_execution.side_effect = Exception("Service error")

    # Execute
    response = client.post(
        "/api/v2/execution/start",
        json={
            "masterplan_id": str(sample_masterplan_id),
            "execution_plan": [],
            "atoms": {}
        }
    )

    # Verify
    assert response.status_code == http_status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Failed to start execution" in response.json()["detail"]


# ============================================================================
# GET /api/v2/execution/{execution_id}
# ============================================================================

@patch("src.api.routers.execution_v2.get_execution_service")
def test_get_execution_status_success(
    mock_get_service,
    client,
    mock_execution_service,
    sample_execution_id,
    sample_execution_state
):
    """Test getting execution status successfully."""
    # Setup
    mock_get_service.return_value = mock_execution_service
    mock_execution_service.get_execution_state.return_value = sample_execution_state

    # Execute
    response = client.get(f"/api/v2/execution/{sample_execution_id}")

    # Verify
    assert response.status_code == http_status.HTTP_200_OK
    data = response.json()
    assert data["execution_id"] == str(sample_execution_id)
    assert data["status"] == "running"
    assert data["current_wave"] == 1
    assert data["total_waves"] == 3
    assert data["atoms_completed"] == 5
    assert data["atoms_total"] == 10


@patch("src.api.routers.execution_v2.get_execution_service")
def test_get_execution_status_not_found(
    mock_get_service,
    client,
    mock_execution_service,
    sample_execution_id
):
    """Test getting execution status when not found."""
    # Setup
    mock_get_service.return_value = mock_execution_service
    mock_execution_service.get_execution_state.return_value = None

    # Execute
    response = client.get(f"/api/v2/execution/{sample_execution_id}")

    # Verify
    assert response.status_code == http_status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]


@patch("src.api.routers.execution_v2.get_execution_service")
def test_get_execution_status_invalid_id(
    mock_get_service,
    client,
    mock_execution_service
):
    """Test getting execution status with invalid ID."""
    # Setup
    mock_get_service.return_value = mock_execution_service

    # Execute
    response = client.get("/api/v2/execution/invalid-uuid")

    # Verify
    assert response.status_code == http_status.HTTP_400_BAD_REQUEST
    assert "Invalid execution_id" in response.json()["detail"]


# ============================================================================
# GET /api/v2/execution/{execution_id}/progress
# ============================================================================

@patch("src.api.routers.execution_v2.get_execution_service")
def test_get_execution_progress_success(
    mock_get_service,
    client,
    mock_execution_service,
    sample_execution_id,
    sample_masterplan_id
):
    """Test getting execution progress successfully."""
    # Setup
    mock_get_service.return_value = mock_execution_service
    mock_execution_service.get_execution_metrics.return_value = {
        "execution_id": str(sample_execution_id),
        "masterplan_id": str(sample_masterplan_id),
        "status": "running",
        "completion_percent": 50.0,
        "precision_percent": 100.0,
        "current_wave": 1,
        "total_waves": 3,
        "atoms_completed": 5,
        "atoms_total": 10,
        "atoms_succeeded": 5,
        "atoms_failed": 0
    }

    # Execute
    response = client.get(f"/api/v2/execution/{sample_execution_id}/progress")

    # Verify
    assert response.status_code == http_status.HTTP_200_OK
    data = response.json()
    assert data["execution_id"] == str(sample_execution_id)
    assert data["completion_percent"] == 50.0
    assert data["precision_percent"] == 100.0


@patch("src.api.routers.execution_v2.get_execution_service")
def test_get_execution_progress_not_found(
    mock_get_service,
    client,
    mock_execution_service,
    sample_execution_id
):
    """Test getting execution progress when not found."""
    # Setup
    mock_get_service.return_value = mock_execution_service
    mock_execution_service.get_execution_metrics.return_value = None

    # Execute
    response = client.get(f"/api/v2/execution/{sample_execution_id}/progress")

    # Verify
    assert response.status_code == http_status.HTTP_404_NOT_FOUND


# ============================================================================
# GET /api/v2/execution/{execution_id}/waves/{wave_id}
# ============================================================================

@patch("src.api.routers.execution_v2.get_execution_service")
def test_get_wave_status_success(
    mock_get_service,
    client,
    mock_execution_service,
    sample_execution_id
):
    """Test getting wave status successfully."""
    # Setup
    mock_get_service.return_value = mock_execution_service
    mock_execution_service.get_wave_status.return_value = {
        "wave_id": 1,
        "execution_id": str(sample_execution_id),
        "status": "completed",
        "current": False
    }

    # Execute
    response = client.get(f"/api/v2/execution/{sample_execution_id}/waves/1")

    # Verify
    assert response.status_code == http_status.HTTP_200_OK
    data = response.json()
    assert data["wave_id"] == 1
    assert data["status"] == "completed"
    assert data["current"] is False


@patch("src.api.routers.execution_v2.get_execution_service")
def test_get_wave_status_not_found(
    mock_get_service,
    client,
    mock_execution_service,
    sample_execution_id
):
    """Test getting wave status when not found."""
    # Setup
    mock_get_service.return_value = mock_execution_service
    mock_execution_service.get_wave_status.return_value = None

    # Execute
    response = client.get(f"/api/v2/execution/{sample_execution_id}/waves/1")

    # Verify
    assert response.status_code == http_status.HTTP_404_NOT_FOUND


# ============================================================================
# GET /api/v2/execution/{execution_id}/atoms/{atom_id}
# ============================================================================

@patch("src.api.routers.execution_v2.get_execution_service")
def test_get_atom_status_success(
    mock_get_service,
    client,
    mock_execution_service,
    sample_execution_id
):
    """Test getting atom status successfully."""
    # Setup
    atom_id = uuid4()
    mock_get_service.return_value = mock_execution_service
    mock_execution_service.get_atom_status.return_value = ExecutionResult(
        atom_id=atom_id,
        success=True,
        code="def test(): pass",
        attempts=1,
        error_message=None,
        execution_time_seconds=1.5,
        validation_result=None
    )

    # Execute
    response = client.get(
        f"/api/v2/execution/{sample_execution_id}/atoms/{atom_id}"
    )

    # Verify
    assert response.status_code == http_status.HTTP_200_OK
    data = response.json()
    assert data["atom_id"] == str(atom_id)
    assert data["success"] is True
    assert data["attempts"] == 1
    assert data["time_seconds"] == 1.5


@patch("src.api.routers.execution_v2.get_execution_service")
def test_get_atom_status_not_found(
    mock_get_service,
    client,
    mock_execution_service,
    sample_execution_id
):
    """Test getting atom status when not found."""
    # Setup
    atom_id = uuid4()
    mock_get_service.return_value = mock_execution_service
    mock_execution_service.get_atom_status.return_value = None

    # Execute
    response = client.get(
        f"/api/v2/execution/{sample_execution_id}/atoms/{atom_id}"
    )

    # Verify
    assert response.status_code == http_status.HTTP_404_NOT_FOUND


# ============================================================================
# POST /api/v2/execution/{execution_id}/pause
# ============================================================================

@patch("src.api.routers.execution_v2.get_execution_service")
def test_pause_execution_success(
    mock_get_service,
    client,
    mock_execution_service,
    sample_execution_id
):
    """Test pausing execution successfully."""
    # Setup
    mock_get_service.return_value = mock_execution_service
    mock_execution_service.pause_execution.return_value = True

    # Execute
    response = client.post(f"/api/v2/execution/{sample_execution_id}/pause")

    # Verify
    assert response.status_code == http_status.HTTP_200_OK
    data = response.json()
    assert data["execution_id"] == str(sample_execution_id)
    assert data["status"] == "paused"
    assert "successfully" in data["message"]


@patch("src.api.routers.execution_v2.get_execution_service")
def test_pause_execution_not_found(
    mock_get_service,
    client,
    mock_execution_service,
    sample_execution_id
):
    """Test pausing execution when not found."""
    # Setup
    mock_get_service.return_value = mock_execution_service
    mock_execution_service.pause_execution.return_value = False
    mock_execution_service.get_execution_state.return_value = None

    # Execute
    response = client.post(f"/api/v2/execution/{sample_execution_id}/pause")

    # Verify
    assert response.status_code == http_status.HTTP_404_NOT_FOUND


@patch("src.api.routers.execution_v2.get_execution_service")
def test_pause_execution_invalid_state(
    mock_get_service,
    client,
    mock_execution_service,
    sample_execution_id,
    sample_execution_state
):
    """Test pausing execution in invalid state."""
    # Setup
    sample_execution_state.status = ExecutionStatus.COMPLETED
    mock_get_service.return_value = mock_execution_service
    mock_execution_service.pause_execution.return_value = False
    mock_execution_service.get_execution_state.return_value = sample_execution_state

    # Execute
    response = client.post(f"/api/v2/execution/{sample_execution_id}/pause")

    # Verify
    assert response.status_code == http_status.HTTP_400_BAD_REQUEST
    assert "Cannot pause" in response.json()["detail"]


# ============================================================================
# POST /api/v2/execution/{execution_id}/resume
# ============================================================================

@patch("src.api.routers.execution_v2.get_execution_service")
def test_resume_execution_success(
    mock_get_service,
    client,
    mock_execution_service,
    sample_execution_id
):
    """Test resuming execution successfully."""
    # Setup
    mock_get_service.return_value = mock_execution_service
    mock_execution_service.resume_execution.return_value = True

    # Execute
    response = client.post(f"/api/v2/execution/{sample_execution_id}/resume")

    # Verify
    assert response.status_code == http_status.HTTP_200_OK
    data = response.json()
    assert data["execution_id"] == str(sample_execution_id)
    assert data["status"] == "running"
    assert "successfully" in data["message"]


@patch("src.api.routers.execution_v2.get_execution_service")
def test_resume_execution_not_found(
    mock_get_service,
    client,
    mock_execution_service,
    sample_execution_id
):
    """Test resuming execution when not found."""
    # Setup
    mock_get_service.return_value = mock_execution_service
    mock_execution_service.resume_execution.return_value = False
    mock_execution_service.get_execution_state.return_value = None

    # Execute
    response = client.post(f"/api/v2/execution/{sample_execution_id}/resume")

    # Verify
    assert response.status_code == http_status.HTTP_404_NOT_FOUND


# ============================================================================
# GET /api/v2/execution/{execution_id}/metrics
# ============================================================================

@patch("src.api.routers.execution_v2.get_execution_service")
def test_get_execution_metrics_success(
    mock_get_service,
    client,
    mock_execution_service,
    sample_execution_id,
    sample_masterplan_id
):
    """Test getting execution metrics successfully."""
    # Setup
    mock_get_service.return_value = mock_execution_service
    mock_execution_service.get_execution_metrics.return_value = {
        "execution_id": str(sample_execution_id),
        "masterplan_id": str(sample_masterplan_id),
        "precision_percent": 100.0,
        "atoms_total": 10,
        "atoms_succeeded": 10,
        "atoms_failed": 0,
        "atoms_completed": 10,
        "completion_percent": 100.0,
        "current_wave": 3,
        "total_waves": 3,
        "total_cost_usd": 2.50,
        "total_time_seconds": 45.2,
        "status": "completed",
        "started_at": "2025-01-24T10:00:00",
        "completed_at": "2025-01-24T10:01:00"
    }

    # Execute
    response = client.get(f"/api/v2/execution/{sample_execution_id}/metrics")

    # Verify
    assert response.status_code == http_status.HTTP_200_OK
    data = response.json()
    assert data["execution_id"] == str(sample_execution_id)
    assert data["precision_percent"] == 100.0
    assert data["completion_percent"] == 100.0
    assert data["total_cost_usd"] == 2.50


@patch("src.api.routers.execution_v2.get_execution_service")
def test_get_execution_metrics_not_found(
    mock_get_service,
    client,
    mock_execution_service,
    sample_execution_id
):
    """Test getting execution metrics when not found."""
    # Setup
    mock_get_service.return_value = mock_execution_service
    mock_execution_service.get_execution_metrics.return_value = None

    # Execute
    response = client.get(f"/api/v2/execution/{sample_execution_id}/metrics")

    # Verify
    assert response.status_code == http_status.HTTP_404_NOT_FOUND


# ============================================================================
# GET /api/v2/execution/health
# ============================================================================

@patch("src.api.routers.execution_v2.get_execution_service")
def test_execution_v2_health(
    mock_get_service,
    client,
    mock_execution_service
):
    """Test execution v2 health check."""
    # Setup
    mock_get_service.return_value = mock_execution_service
    mock_execution_service.list_executions.return_value = [MagicMock(), MagicMock()]

    # Execute
    response = client.get("/api/v2/execution/health")

    # Verify
    assert response.status_code == http_status.HTTP_200_OK
    data = response.json()
    assert data["service"] == "execution_v2"
    assert data["status"] == "healthy"
    assert data["version"] == "2.0.0"
    assert data["active_executions"] == 2
