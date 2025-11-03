"""
Tests for Review API Router

Tests human review workflow endpoints.

Author: DevMatrix Team
Date: 2025-11-03
"""

import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routers.review import router


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return MagicMock()


@pytest.fixture
def client(mock_db):
    """Create test client with review router."""
    from src.config.database import get_db

    test_app = FastAPI()
    test_app.include_router(router)

    # Override get_db dependency
    test_app.dependency_overrides[get_db] = lambda: mock_db

    return TestClient(test_app)


@pytest.fixture
def sample_review_id():
    """Sample review ID."""
    return str(uuid4())


@pytest.fixture
def sample_atom_id():
    """Sample atom ID."""
    return str(uuid4())


@pytest.fixture
def sample_masterplan_id():
    """Sample masterplan ID."""
    return str(uuid4())


@pytest.fixture
def mock_review_service():
    """Create mock ReviewService."""
    return MagicMock()


# ============================================================================
# GET /api/v2/review/queue Tests
# ============================================================================

def test_get_review_queue_success(client, mock_review_service):
    """Test successful review queue retrieval."""
    mock_items = [
        {
            "review_id": str(uuid4()),
            "atom_id": str(uuid4()),
            "status": "pending",
            "priority": "high",
            "assigned_to": None
        },
        {
            "review_id": str(uuid4()),
            "atom_id": str(uuid4()),
            "status": "in_review",
            "priority": "medium",
            "assigned_to": "user123"
        }
    ]
    mock_review_service.get_review_queue.return_value = mock_items

    with patch('src.api.routers.review.ReviewService', return_value=mock_review_service):
        response = client.get("/api/v2/review/queue")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_get_review_queue_with_status_filter(client, mock_review_service):
    """Test review queue filtered by status."""
    mock_review_service.get_review_queue.return_value = []

    with patch('src.api.routers.review.ReviewService', return_value=mock_review_service):
        response = client.get("/api/v2/review/queue?status=pending")

    assert response.status_code == 200


def test_get_review_queue_with_assigned_filter(client, mock_review_service):
    """Test review queue filtered by assigned user."""
    mock_review_service.get_review_queue.return_value = []

    with patch('src.api.routers.review.ReviewService', return_value=mock_review_service):
        response = client.get("/api/v2/review/queue?assigned_to=user123")

    assert response.status_code == 200


def test_get_review_queue_with_limit(client, mock_review_service):
    """Test review queue with custom limit."""
    mock_review_service.get_review_queue.return_value = []

    with patch('src.api.routers.review.ReviewService', return_value=mock_review_service):
        response = client.get("/api/v2/review/queue?limit=10")

    assert response.status_code == 200


def test_get_review_queue_empty(client, mock_review_service):
    """Test review queue when no items pending."""
    mock_review_service.get_review_queue.return_value = []

    with patch('src.api.routers.review.ReviewService', return_value=mock_review_service):
        response = client.get("/api/v2/review/queue")

    assert response.status_code == 200
    assert response.json() == []


# ============================================================================
# GET /api/v2/review/{review_id} Tests
# ============================================================================

def test_get_review_detail_success(client, sample_review_id, mock_review_service):
    """Test successful review detail retrieval."""
    mock_review = {
        "review_id": sample_review_id,
        "atom_id": str(uuid4()),
        "status": "pending",
        "atom_code": "def test(): pass",
        "feedback_history": []
    }
    mock_review_service.get_review.return_value = mock_review

    with patch('src.api.routers.review.ReviewService', return_value=mock_review_service):
        response = client.get(f"/api/v2/review/{sample_review_id}")

    assert response.status_code == 200
    data = response.json()
    assert data['review_id'] == sample_review_id


def test_get_review_detail_not_found(client, mock_review_service):
    """Test getting non-existent review."""
    review_id = str(uuid4())
    mock_review_service.get_review.side_effect = ValueError("Review not found")

    with patch('src.api.routers.review.ReviewService', return_value=mock_review_service):
        response = client.get(f"/api/v2/review/{review_id}")

    assert response.status_code == 404


# ============================================================================
# POST /api/v2/review/approve Tests
# ============================================================================

def test_approve_review_success(client, sample_review_id, mock_review_service):
    """Test successful review approval."""
    mock_result = {
        "success": True,
        "review_id": sample_review_id,
        "status": "approved",
        "message": "Review approved successfully"
    }
    mock_review_service.approve.return_value = mock_result

    with patch('src.api.routers.review.ReviewService', return_value=mock_review_service):
        response = client.post(
            "/api/v2/review/approve",
            json={
                "reviewer_id": "user123",
                "feedback": "Looks good!"
            },
            params={"review_id": sample_review_id}
        )

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == "approved"


def test_approve_review_with_feedback(client, sample_review_id, mock_review_service):
    """Test approval with detailed feedback."""
    mock_review_service.approve.return_value = {
        "success": True,
        "review_id": sample_review_id,
        "status": "approved"
    }

    with patch('src.api.routers.review.ReviewService', return_value=mock_review_service):
        response = client.post(
            "/api/v2/review/approve",
            json={
                "reviewer_id": "user123",
                "feedback": "Well implemented, good test coverage."
            },
            params={"review_id": sample_review_id}
        )

    assert response.status_code == 200


def test_approve_review_not_found(client, mock_review_service):
    """Test approving non-existent review."""
    review_id = str(uuid4())
    mock_review_service.approve.side_effect = ValueError("Review not found")

    with patch('src.api.routers.review.ReviewService', return_value=mock_review_service):
        response = client.post(
            "/api/v2/review/approve",
            json={"reviewer_id": "user123"},
            params={"review_id": review_id}
        )

    assert response.status_code == 404


# ============================================================================
# POST /api/v2/review/reject Tests
# ============================================================================

def test_reject_review_success(client, sample_review_id, mock_review_service):
    """Test successful review rejection."""
    mock_result = {
        "success": True,
        "review_id": sample_review_id,
        "status": "rejected",
        "message": "Review rejected"
    }
    mock_review_service.reject.return_value = mock_result

    with patch('src.api.routers.review.ReviewService', return_value=mock_review_service):
        response = client.post(
            "/api/v2/review/reject",
            json={
                "reviewer_id": "user123",
                "feedback": "Needs improvement in error handling"
            },
            params={"review_id": sample_review_id}
        )

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == "rejected"


def test_reject_review_without_feedback(client, sample_review_id):
    """Test rejection requires feedback."""
    response = client.post(
        "/api/v2/review/reject",
        json={"reviewer_id": "user123"},
        params={"review_id": sample_review_id}
    )

    assert response.status_code == 422  # Validation error


# ============================================================================
# POST /api/v2/review/edit Tests
# ============================================================================

def test_edit_review_success(client, sample_review_id, mock_review_service):
    """Test successful review edit."""
    mock_result = {
        "success": True,
        "review_id": sample_review_id,
        "status": "edited",
        "new_code": "def test():\n    return True"
    }
    mock_review_service.edit.return_value = mock_result

    with patch('src.api.routers.review.ReviewService', return_value=mock_review_service):
        response = client.post(
            "/api/v2/review/edit",
            json={
                "reviewer_id": "user123",
                "new_code": "def test():\n    return True",
                "feedback": "Fixed implementation"
            },
            params={"review_id": sample_review_id}
        )

    assert response.status_code == 200


def test_edit_review_empty_code(client, sample_review_id):
    """Test edit with empty code."""
    response = client.post(
        "/api/v2/review/edit",
        json={
            "reviewer_id": "user123",
            "new_code": ""
        },
        params={"review_id": sample_review_id}
    )

    assert response.status_code == 422


# ============================================================================
# POST /api/v2/review/regenerate Tests
# ============================================================================

def test_regenerate_review_success(client, sample_review_id, mock_review_service):
    """Test successful review regeneration request."""
    mock_result = {
        "success": True,
        "review_id": sample_review_id,
        "status": "regenerating",
        "message": "Regeneration queued"
    }
    mock_review_service.regenerate.return_value = mock_result

    with patch('src.api.routers.review.ReviewService', return_value=mock_review_service):
        response = client.post(
            "/api/v2/review/regenerate",
            json={
                "reviewer_id": "user123",
                "feedback": "Please use async pattern instead"
            },
            params={"review_id": sample_review_id}
        )

    assert response.status_code == 200


def test_regenerate_review_without_feedback(client, sample_review_id):
    """Test regeneration requires feedback."""
    response = client.post(
        "/api/v2/review/regenerate",
        json={"reviewer_id": "user123"},
        params={"review_id": sample_review_id}
    )

    assert response.status_code == 422


# ============================================================================
# POST /api/v2/review/assign Tests
# ============================================================================

def test_assign_review_success(client, sample_review_id, mock_review_service):
    """Test successful review assignment."""
    mock_result = {
        "success": True,
        "review_id": sample_review_id,
        "assigned_to": "user456"
    }
    mock_review_service.assign.return_value = mock_result

    with patch('src.api.routers.review.ReviewService', return_value=mock_review_service):
        response = client.post(
            "/api/v2/review/assign",
            json={"user_id": "user456"},
            params={"review_id": sample_review_id}
        )

    assert response.status_code == 200


def test_assign_review_to_invalid_user(client, sample_review_id, mock_review_service):
    """Test assignment to non-existent user."""
    mock_review_service.assign.side_effect = ValueError("User not found")

    with patch('src.api.routers.review.ReviewService', return_value=mock_review_service):
        response = client.post(
            "/api/v2/review/assign",
            json={"user_id": "nonexistent"},
            params={"review_id": sample_review_id}
        )

    assert response.status_code == 400


# ============================================================================
# GET /api/v2/review/statistics/{masterplan_id} Tests
# ============================================================================

def test_get_review_statistics_success(client, sample_masterplan_id, mock_review_service):
    """Test successful statistics retrieval."""
    mock_stats = {
        "masterplan_id": sample_masterplan_id,
        "total_reviews": 50,
        "approved": 35,
        "rejected": 5,
        "pending": 10,
        "approval_rate": 0.70,
        "avg_review_time_minutes": 15
    }
    mock_review_service.get_statistics.return_value = mock_stats

    with patch('src.api.routers.review.ReviewService', return_value=mock_review_service):
        response = client.get(f"/api/v2/review/statistics/{sample_masterplan_id}")

    assert response.status_code == 200
    data = response.json()
    assert data['total_reviews'] == 50
    assert data['approval_rate'] == 0.70


def test_get_review_statistics_no_reviews(client, sample_masterplan_id, mock_review_service):
    """Test statistics when no reviews exist."""
    mock_stats = {
        "masterplan_id": sample_masterplan_id,
        "total_reviews": 0,
        "approved": 0,
        "rejected": 0,
        "pending": 0,
        "approval_rate": 0.0
    }
    mock_review_service.get_statistics.return_value = mock_stats

    with patch('src.api.routers.review.ReviewService', return_value=mock_review_service):
        response = client.get(f"/api/v2/review/statistics/{sample_masterplan_id}")

    data = response.json()
    assert data['total_reviews'] == 0


# ============================================================================
# POST /api/v2/review/create/{atom_id} Tests
# ============================================================================

def test_create_review_success(client, sample_atom_id, mock_review_service):
    """Test successful review creation."""
    mock_review = {
        "review_id": str(uuid4()),
        "atom_id": sample_atom_id,
        "status": "pending",
        "created_at": "2025-11-03T10:00:00"
    }
    mock_review_service.create_review.return_value = mock_review

    with patch('src.api.routers.review.ReviewService', return_value=mock_review_service):
        response = client.post(f"/api/v2/review/create/{sample_atom_id}")

    assert response.status_code == 201
    data = response.json()
    assert data['atom_id'] == sample_atom_id


def test_create_review_atom_not_found(client, mock_review_service):
    """Test review creation for non-existent atom."""
    atom_id = str(uuid4())
    mock_review_service.create_review.side_effect = ValueError("Atom not found")

    with patch('src.api.routers.review.ReviewService', return_value=mock_review_service):
        response = client.post(f"/api/v2/review/create/{atom_id}")

    assert response.status_code == 404


def test_create_review_already_exists(client, sample_atom_id, mock_review_service):
    """Test review creation when review already exists."""
    mock_review_service.create_review.side_effect = ValueError("Review already exists")

    with patch('src.api.routers.review.ReviewService', return_value=mock_review_service):
        response = client.post(f"/api/v2/review/create/{sample_atom_id}")

    assert response.status_code == 400


# ============================================================================
# POST /api/v2/review/bulk-create/{masterplan_id} Tests
# ============================================================================

def test_bulk_create_reviews_success(client, sample_masterplan_id, mock_review_service):
    """Test successful bulk review creation."""
    mock_result = {
        "masterplan_id": sample_masterplan_id,
        "total_created": 50,
        "review_ids": [str(uuid4()) for _ in range(50)]
    }
    mock_review_service.bulk_create_reviews.return_value = mock_result

    with patch('src.api.routers.review.ReviewService', return_value=mock_review_service):
        response = client.post(f"/api/v2/review/bulk-create/{sample_masterplan_id}")

    assert response.status_code == 201
    data = response.json()
    assert data['total_created'] == 50


def test_bulk_create_reviews_no_atoms(client, sample_masterplan_id, mock_review_service):
    """Test bulk creation when no atoms need review."""
    mock_result = {
        "masterplan_id": sample_masterplan_id,
        "total_created": 0,
        "review_ids": []
    }
    mock_review_service.bulk_create_reviews.return_value = mock_result

    with patch('src.api.routers.review.ReviewService', return_value=mock_review_service):
        response = client.post(f"/api/v2/review/bulk-create/{sample_masterplan_id}")

    data = response.json()
    assert data['total_created'] == 0


def test_bulk_create_reviews_masterplan_not_found(client, mock_review_service):
    """Test bulk creation for non-existent masterplan."""
    masterplan_id = str(uuid4())
    mock_review_service.bulk_create_reviews.side_effect = ValueError("MasterPlan not found")

    with patch('src.api.routers.review.ReviewService', return_value=mock_review_service):
        response = client.post(f"/api/v2/review/bulk-create/{masterplan_id}")

    assert response.status_code == 404


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_review_service_error(client, sample_review_id, mock_review_service):
    """Test handling of review service errors."""
    mock_review_service.get_review.side_effect = Exception("Service error")

    with patch('src.api.routers.review.ReviewService', return_value=mock_review_service):
        response = client.get(f"/api/v2/review/{sample_review_id}")

    assert response.status_code == 500


@pytest.mark.unit
class TestReviewModels:
    """Unit tests for review request/response models."""

    def test_approve_request_model(self):
        """Test ApproveRequest model."""
        from src.api.routers.review import ApproveRequest

        request = ApproveRequest(
            reviewer_id="user123",
            feedback="Looks good"
        )
        assert request.reviewer_id == "user123"

    def test_reject_request_model(self):
        """Test RejectRequest model requires feedback."""
        from src.api.routers.review import RejectRequest

        request = RejectRequest(
            reviewer_id="user123",
            feedback="Needs work"
        )
        assert request.feedback == "Needs work"

    def test_edit_request_model(self):
        """Test EditRequest model."""
        from src.api.routers.review import EditRequest

        request = EditRequest(
            reviewer_id="user123",
            new_code="def test(): pass"
        )
        assert request.new_code == "def test(): pass"

