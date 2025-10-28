"""
Unit Tests for Approval Workflow Endpoints - GROUP 2

Tests for:
- POST /api/v1/masterplans/{id}/approve endpoint
- POST /api/v1/masterplans/{id}/reject endpoint
- Status validation and transitions
"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.app import create_app
from src.models.masterplan import (
    MasterPlan,
    MasterPlanPhase,
    MasterPlanStatus,
    PhaseType,
    DiscoveryDocument,
)


@pytest.fixture
def test_client():
    """Create test client for API testing."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def draft_masterplan(db_session: Session):
    """Create a draft masterplan for testing approval workflow."""
    # Create discovery document
    discovery = DiscoveryDocument(
        discovery_id=uuid4(),
        session_id="test-session",
        user_id="test-user",
        user_request="Create approval test API",
        domain="Test",
        bounded_contexts=[],
        aggregates=[],
        value_objects=[],
        domain_events=[],
        services=[],
    )
    db_session.add(discovery)
    db_session.flush()

    # Create masterplan with DRAFT status
    masterplan = MasterPlan(
        masterplan_id=uuid4(),
        discovery_id=discovery.discovery_id,
        session_id="test-session",
        user_id="test-user",
        project_name="Approval Test Project",
        description="Test masterplan for approval workflow",
        status=MasterPlanStatus.DRAFT,
        tech_stack={"backend": "FastAPI", "frontend": "React"},
    )
    db_session.add(masterplan)

    # Add a phase for completeness
    phase = MasterPlanPhase(
        phase_id=uuid4(),
        masterplan_id=masterplan.masterplan_id,
        phase_type=PhaseType.SETUP,
        phase_number=1,
        name="Setup Phase",
    )
    db_session.add(phase)
    db_session.commit()

    return masterplan


class TestApproveMasterplanEndpoint:
    """Test approve endpoint updates status to 'approved'."""

    def test_approve_draft_masterplan_success(self, test_client, draft_masterplan, db_session):
        """Test that approving a draft masterplan changes status to approved."""
        masterplan_id = str(draft_masterplan.masterplan_id)

        # Call approve endpoint
        response = test_client.post(f"/api/v1/masterplans/{masterplan_id}/approve")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["masterplan_id"] == masterplan_id

        # Verify database update
        db_session.refresh(draft_masterplan)
        assert draft_masterplan.status == MasterPlanStatus.APPROVED

    def test_approve_nonexistent_masterplan_returns_404(self, test_client):
        """Test that approving non-existent masterplan returns 404."""
        fake_id = str(uuid4())
        response = test_client.post(f"/api/v1/masterplans/{fake_id}/approve")
        assert response.status_code == 404

    def test_approve_already_approved_masterplan_returns_400(self, test_client, draft_masterplan, db_session):
        """Test that approving already approved masterplan returns 400."""
        # First approve
        masterplan_id = str(draft_masterplan.masterplan_id)
        test_client.post(f"/api/v1/masterplans/{masterplan_id}/approve")

        # Try to approve again
        response = test_client.post(f"/api/v1/masterplans/{masterplan_id}/approve")
        assert response.status_code == 400


class TestRejectMasterplanEndpoint:
    """Test reject endpoint updates status to 'rejected'."""

    def test_reject_draft_masterplan_success(self, test_client, draft_masterplan, db_session):
        """Test that rejecting a draft masterplan changes status to rejected."""
        masterplan_id = str(draft_masterplan.masterplan_id)

        # Call reject endpoint
        response = test_client.post(f"/api/v1/masterplans/{masterplan_id}/reject")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
        assert data["masterplan_id"] == masterplan_id

        # Verify database update
        db_session.refresh(draft_masterplan)
        assert draft_masterplan.status == MasterPlanStatus.REJECTED

    def test_reject_with_reason(self, test_client, draft_masterplan, db_session):
        """Test reject endpoint accepts optional rejection reason."""
        masterplan_id = str(draft_masterplan.masterplan_id)
        rejection_reason = "Tasks are too complex, needs simplification"

        # Call reject endpoint with reason
        response = test_client.post(
            f"/api/v1/masterplans/{masterplan_id}/reject",
            json={"rejection_reason": rejection_reason}
        )

        # Verify response
        assert response.status_code == 200

    def test_reject_nonexistent_masterplan_returns_404(self, test_client):
        """Test that rejecting non-existent masterplan returns 404."""
        fake_id = str(uuid4())
        response = test_client.post(f"/api/v1/masterplans/{fake_id}/reject")
        assert response.status_code == 404


class TestApprovalValidation:
    """Test status validation for approval endpoints."""

    def test_cannot_approve_rejected_masterplan(self, test_client, draft_masterplan, db_session):
        """Test that approved endpoint validates status is 'draft'."""
        masterplan_id = str(draft_masterplan.masterplan_id)

        # First reject
        test_client.post(f"/api/v1/masterplans/{masterplan_id}/reject")

        # Try to approve rejected masterplan
        response = test_client.post(f"/api/v1/masterplans/{masterplan_id}/approve")
        assert response.status_code == 400

    def test_invalid_masterplan_id_format_returns_400(self, test_client):
        """Test that invalid UUID format returns 400."""
        response = test_client.post("/api/v1/masterplans/invalid-uuid/approve")
        assert response.status_code == 400
