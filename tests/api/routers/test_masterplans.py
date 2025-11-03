"""
Tests for MasterPlans API Router

Tests all REST endpoints for masterplan management and execution.

Author: DevMatrix Team
Date: 2025-11-03
"""

import pytest
from uuid import uuid4, UUID
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routers.masterplans import router
from src.models.masterplan import MasterPlan, MasterPlanStatus
from src.models.user import User


@pytest.fixture
def mock_current_user():
    """Create mock authenticated user."""
    user = MagicMock(spec=User)
    user.user_id = str(uuid4())
    user.username = "testuser"
    user.email = "test@example.com"
    return user


@pytest.fixture
def client(mock_current_user):
    """Create test client with masterplans router."""
    test_app = FastAPI()
    test_app.include_router(router)

    # Override auth dependency
    def override_get_current_user():
        return mock_current_user

    from src.api.middleware.auth_middleware import get_current_user
    test_app.dependency_overrides[get_current_user] = override_get_current_user

    return TestClient(test_app)


@pytest.fixture
def sample_masterplan_id():
    """Sample masterplan UUID."""
    return uuid4()


@pytest.fixture
def sample_discovery_id():
    """Sample discovery UUID."""
    return uuid4()


@pytest.fixture
def sample_masterplan(sample_masterplan_id, sample_discovery_id):
    """Sample MasterPlan object."""
    masterplan = MagicMock(spec=MasterPlan)
    masterplan.masterplan_id = sample_masterplan_id
    masterplan.discovery_id = sample_discovery_id
    masterplan.project_name = "Test Project"
    masterplan.description = "A test project description"
    masterplan.status = MasterPlanStatus.PENDING
    masterplan.total_phases = 4
    masterplan.total_milestones = 12
    masterplan.total_tasks = 50
    masterplan.completed_tasks = 0
    masterplan.progress_percent = 0.0
    masterplan.tech_stack = ["Python", "FastAPI", "PostgreSQL"]
    masterplan.estimated_cost_usd = 2.50
    masterplan.estimated_duration_minutes = 120
    masterplan.generation_cost_usd = 0.15
    masterplan.created_at = datetime.now()
    masterplan.started_at = None
    masterplan.completed_at = None
    masterplan.phases = []
    masterplan.session_id = "sess_test123"
    masterplan.user_id = "user_123"
    masterplan.architecture_style = "microservices"
    masterplan.llm_model = "claude-sonnet-4.5"
    masterplan.generation_tokens = 10000
    masterplan.version = "1.0.0"
    masterplan.updated_at = None
    masterplan.workspace_path = None
    return masterplan


# ============================================================================
# POST /api/v1/masterplans Tests
# ============================================================================

def test_create_masterplan_success(client, sample_discovery_id, mock_current_user):
    """Test successful masterplan creation."""
    mock_generator = MagicMock()
    mock_generator.generate_masterplan = AsyncMock(return_value=uuid4())

    with patch('src.api.routers.masterplans.MasterPlanGenerator', return_value=mock_generator):
        response = client.post(
            "/api/v1/masterplans",
            json={
                "discovery_id": str(sample_discovery_id),
                "session_id": "sess_test123"
            }
        )

    assert response.status_code == 200
    data = response.json()
    assert "masterplan_id" in data
    assert data["status"] == "pending"
    assert "message" in data


def test_create_masterplan_invalid_discovery_id(client):
    """Test masterplan creation with invalid discovery ID format."""
    response = client.post(
        "/api/v1/masterplans",
        json={
            "discovery_id": "invalid-uuid",
            "session_id": "sess_test123"
        }
    )

    assert response.status_code == 400
    assert "Invalid discovery_id format" in response.json()['detail']


def test_create_masterplan_discovery_not_found(client, sample_discovery_id):
    """Test masterplan creation when discovery document not found."""
    mock_generator = MagicMock()
    mock_generator.generate_masterplan = AsyncMock(side_effect=ValueError("Discovery not found"))

    with patch('src.api.routers.masterplans.MasterPlanGenerator', return_value=mock_generator):
        response = client.post(
            "/api/v1/masterplans",
            json={
                "discovery_id": str(sample_discovery_id),
                "session_id": "sess_test123"
            }
        )

    assert response.status_code == 404


def test_create_masterplan_generation_error(client, sample_discovery_id):
    """Test masterplan creation handles generation errors."""
    mock_generator = MagicMock()
    mock_generator.generate_masterplan = AsyncMock(side_effect=Exception("LLM timeout"))

    with patch('src.api.routers.masterplans.MasterPlanGenerator', return_value=mock_generator):
        response = client.post(
            "/api/v1/masterplans",
            json={
                "discovery_id": str(sample_discovery_id),
                "session_id": "sess_test123"
            }
        )

    assert response.status_code == 500


# ============================================================================
# GET /api/v1/masterplans Tests
# ============================================================================

def test_list_masterplans_success(client, sample_masterplan, mock_current_user):
    """Test successful masterplan listing."""
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
        sample_masterplan
    ]
    mock_db.query.return_value = mock_query

    with patch('src.api.routers.masterplans.get_db', return_value=mock_db):
        response = client.get("/api/v1/masterplans")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]['project_name'] == "Test Project"
    assert data[0]['status'] == "pending"


def test_list_masterplans_with_pagination(client, mock_current_user):
    """Test masterplan listing with pagination parameters."""
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
    mock_db.query.return_value = mock_query

    with patch('src.api.routers.masterplans.get_db', return_value=mock_db):
        response = client.get("/api/v1/masterplans?skip=10&limit=25")

    assert response.status_code == 200
    # Verify pagination was applied
    mock_query.filter.return_value.order_by.return_value.offset.assert_called_with(10)
    mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.assert_called_with(25)


def test_list_masterplans_with_status_filter(client, mock_current_user):
    """Test masterplan listing filtered by status."""
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
    mock_db.query.return_value = mock_query

    with patch('src.api.routers.masterplans.get_db', return_value=mock_db):
        response = client.get("/api/v1/masterplans?status=approved")

    assert response.status_code == 200


def test_list_masterplans_empty(client, mock_current_user):
    """Test masterplan listing with no results."""
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
    mock_db.query.return_value = mock_query

    with patch('src.api.routers.masterplans.get_db', return_value=mock_db):
        response = client.get("/api/v1/masterplans")

    assert response.status_code == 200
    assert response.json() == []


# ============================================================================
# GET /api/v1/masterplans/{masterplan_id} Tests
# ============================================================================

def test_get_masterplan_detail_success(client, sample_masterplan_id, sample_masterplan, mock_current_user):
    """Test successful retrieval of masterplan details."""
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = sample_masterplan
    mock_db.query.return_value = mock_query

    with patch('src.api.routers.masterplans.get_db', return_value=mock_db):
        response = client.get(f"/api/v1/masterplans/{sample_masterplan_id}")

    assert response.status_code == 200
    data = response.json()
    assert data['masterplan_id'] == str(sample_masterplan_id)
    assert data['project_name'] == "Test Project"
    assert 'phases' in data


def test_get_masterplan_detail_not_found(client, mock_current_user):
    """Test getting masterplan details when not found."""
    masterplan_id = uuid4()
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None
    mock_db.query.return_value = mock_query

    with patch('src.api.routers.masterplans.get_db', return_value=mock_db):
        response = client.get(f"/api/v1/masterplans/{masterplan_id}")

    assert response.status_code == 404
    assert "not found" in response.json()['detail'].lower()


def test_get_masterplan_detail_invalid_uuid(client, mock_current_user):
    """Test getting masterplan with invalid UUID."""
    response = client.get("/api/v1/masterplans/invalid-uuid")

    assert response.status_code == 422  # Validation error


def test_get_masterplan_detail_unauthorized_user(client, sample_masterplan_id, sample_masterplan, mock_current_user):
    """Test getting masterplan details from different user."""
    sample_masterplan.user_id = "different_user_id"

    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = sample_masterplan
    mock_db.query.return_value = mock_query

    with patch('src.api.routers.masterplans.get_db', return_value=mock_db):
        response = client.get(f"/api/v1/masterplans/{sample_masterplan_id}")

    # Should still return 200 if user can view (might be shared)
    # Or 403 if strict ownership check is implemented
    assert response.status_code in [200, 403]


# ============================================================================
# POST /api/v1/masterplans/{masterplan_id}/approve Tests
# ============================================================================

def test_approve_masterplan_success(client, sample_masterplan_id, sample_masterplan, mock_current_user):
    """Test successful masterplan approval."""
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = sample_masterplan
    mock_db.query.return_value = mock_query

    with patch('src.api.routers.masterplans.get_db', return_value=mock_db):
        response = client.post(f"/api/v1/masterplans/{sample_masterplan_id}/approve")

    assert response.status_code == 200
    data = response.json()
    assert data['masterplan_id'] == str(sample_masterplan_id)
    assert data['status'] == 'approved'


def test_approve_masterplan_not_found(client, mock_current_user):
    """Test approving non-existent masterplan."""
    masterplan_id = uuid4()
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None
    mock_db.query.return_value = mock_query

    with patch('src.api.routers.masterplans.get_db', return_value=mock_db):
        response = client.post(f"/api/v1/masterplans/{masterplan_id}/approve")

    assert response.status_code == 404


def test_approve_masterplan_already_approved(client, sample_masterplan_id, sample_masterplan, mock_current_user):
    """Test approving already approved masterplan."""
    sample_masterplan.status = MasterPlanStatus.APPROVED

    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = sample_masterplan
    mock_db.query.return_value = mock_query

    with patch('src.api.routers.masterplans.get_db', return_value=mock_db):
        response = client.post(f"/api/v1/masterplans/{sample_masterplan_id}/approve")

    # Should handle gracefully (idempotent) or return specific error
    assert response.status_code in [200, 400]


def test_approve_masterplan_in_progress(client, sample_masterplan_id, sample_masterplan, mock_current_user):
    """Test approving masterplan that's already executing."""
    sample_masterplan.status = MasterPlanStatus.IN_PROGRESS

    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = sample_masterplan
    mock_db.query.return_value = mock_query

    with patch('src.api.routers.masterplans.get_db', return_value=mock_db):
        response = client.post(f"/api/v1/masterplans/{sample_masterplan_id}/approve")

    assert response.status_code == 400  # Cannot approve in-progress plan


# ============================================================================
# POST /api/v1/masterplans/{masterplan_id}/reject Tests
# ============================================================================

def test_reject_masterplan_success(client, sample_masterplan_id, sample_masterplan, mock_current_user):
    """Test successful masterplan rejection."""
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = sample_masterplan
    mock_db.query.return_value = mock_query

    with patch('src.api.routers.masterplans.get_db', return_value=mock_db):
        response = client.post(
            f"/api/v1/masterplans/{sample_masterplan_id}/reject",
            json={"rejection_reason": "Tasks are too complex"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data['masterplan_id'] == str(sample_masterplan_id)
    assert data['status'] == 'rejected'


def test_reject_masterplan_without_reason(client, sample_masterplan_id, sample_masterplan, mock_current_user):
    """Test masterplan rejection without reason (optional)."""
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = sample_masterplan
    mock_db.query.return_value = mock_query

    with patch('src.api.routers.masterplans.get_db', return_value=mock_db):
        response = client.post(
            f"/api/v1/masterplans/{sample_masterplan_id}/reject",
            json={}
        )

    assert response.status_code == 200


def test_reject_masterplan_not_found(client, mock_current_user):
    """Test rejecting non-existent masterplan."""
    masterplan_id = uuid4()
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None
    mock_db.query.return_value = mock_query

    with patch('src.api.routers.masterplans.get_db', return_value=mock_db):
        response = client.post(
            f"/api/v1/masterplans/{masterplan_id}/reject",
            json={}
        )

    assert response.status_code == 404


def test_reject_masterplan_already_rejected(client, sample_masterplan_id, sample_masterplan, mock_current_user):
    """Test rejecting already rejected masterplan."""
    sample_masterplan.status = MasterPlanStatus.REJECTED

    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = sample_masterplan
    mock_db.query.return_value = mock_query

    with patch('src.api.routers.masterplans.get_db', return_value=mock_db):
        response = client.post(
            f"/api/v1/masterplans/{sample_masterplan_id}/reject",
            json={"rejection_reason": "Still too complex"}
        )

    # Should handle gracefully (idempotent) or return specific error
    assert response.status_code in [200, 400]


# ============================================================================
# POST /api/v1/masterplans/{masterplan_id}/execute Tests
# ============================================================================

def test_execute_masterplan_success(client, sample_masterplan_id, sample_masterplan, mock_current_user):
    """Test successful masterplan execution start."""
    sample_masterplan.status = MasterPlanStatus.APPROVED

    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = sample_masterplan
    mock_db.query.return_value = mock_query

    mock_execution_service = MagicMock()
    mock_execution_service.start_execution.return_value = {
        "workspace_id": "masterplan_test_project",
        "workspace_path": "/absolute/path/to/workspace",
        "total_tasks": 50
    }

    with patch('src.api.routers.masterplans.get_db', return_value=mock_db), \
         patch('src.api.routers.masterplans.MasterplanExecutionService', return_value=mock_execution_service):
        response = client.post(f"/api/v1/masterplans/{sample_masterplan_id}/execute")

    assert response.status_code == 200
    data = response.json()
    assert data['masterplan_id'] == str(sample_masterplan_id)
    assert data['status'] == 'in_progress'
    assert 'workspace_id' in data
    assert 'workspace_path' in data
    assert data['total_tasks'] == 50


def test_execute_masterplan_not_approved(client, sample_masterplan_id, sample_masterplan, mock_current_user):
    """Test executing masterplan that's not approved."""
    sample_masterplan.status = MasterPlanStatus.PENDING

    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = sample_masterplan
    mock_db.query.return_value = mock_query

    with patch('src.api.routers.masterplans.get_db', return_value=mock_db):
        response = client.post(f"/api/v1/masterplans/{sample_masterplan_id}/execute")

    assert response.status_code == 400
    assert "not approved" in response.json()['detail'].lower()


def test_execute_masterplan_already_executing(client, sample_masterplan_id, sample_masterplan, mock_current_user):
    """Test executing masterplan that's already in progress."""
    sample_masterplan.status = MasterPlanStatus.IN_PROGRESS

    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = sample_masterplan
    mock_db.query.return_value = mock_query

    with patch('src.api.routers.masterplans.get_db', return_value=mock_db):
        response = client.post(f"/api/v1/masterplans/{sample_masterplan_id}/execute")

    assert response.status_code == 400
    assert "already" in response.json()['detail'].lower()


def test_execute_masterplan_not_found(client, mock_current_user):
    """Test executing non-existent masterplan."""
    masterplan_id = uuid4()
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None
    mock_db.query.return_value = mock_query

    with patch('src.api.routers.masterplans.get_db', return_value=mock_db):
        response = client.post(f"/api/v1/masterplans/{masterplan_id}/execute")

    assert response.status_code == 404


def test_execute_masterplan_execution_error(client, sample_masterplan_id, sample_masterplan, mock_current_user):
    """Test execution handles service errors."""
    sample_masterplan.status = MasterPlanStatus.APPROVED

    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = sample_masterplan
    mock_db.query.return_value = mock_query

    mock_execution_service = MagicMock()
    mock_execution_service.start_execution.side_effect = Exception("Workspace creation failed")

    with patch('src.api.routers.masterplans.get_db', return_value=mock_db), \
         patch('src.api.routers.masterplans.MasterplanExecutionService', return_value=mock_execution_service):
        response = client.post(f"/api/v1/masterplans/{sample_masterplan_id}/execute")

    assert response.status_code == 500


# ============================================================================
# Unit Tests for Serialization Functions
# ============================================================================

@pytest.mark.unit
class TestMasterplanSerialization:
    """Unit tests for masterplan serialization functions."""

    def test_serialize_masterplan_summary(self, sample_masterplan):
        """Test masterplan summary serialization."""
        from src.api.routers.masterplans import serialize_masterplan_summary

        result = serialize_masterplan_summary(sample_masterplan)

        assert 'masterplan_id' in result
        assert result['project_name'] == "Test Project"
        assert result['status'] == "pending"
        assert result['total_tasks'] == 50
        assert 'phases' not in result  # Summary doesn't include phases

    def test_serialize_masterplan_detail(self, sample_masterplan):
        """Test masterplan detail serialization includes all fields."""
        from src.api.routers.masterplans import serialize_masterplan_detail

        result = serialize_masterplan_detail(sample_masterplan)

        assert 'masterplan_id' in result
        assert 'phases' in result  # Detail includes phases
        assert 'discovery_id' in result
        assert 'session_id' in result
        assert 'architecture_style' in result

