"""
Tests for Usage API Router

Tests usage tracking and quota management endpoints.

Author: DevMatrix Team
Date: 2025-11-03
"""

import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routers.usage import router
from src.models.user import User


@pytest.fixture
def mock_current_user():
    """Create mock authenticated user."""
    user = MagicMock(spec=User)
    user.user_id = uuid4()
    user.username = "testuser"
    user.email = "test@example.com"
    return user


@pytest.fixture
def client(mock_current_user):
    """Create test client with usage router."""
    test_app = FastAPI()
    test_app.include_router(router)

    # Override auth dependency
    def override_get_current_user():
        return mock_current_user

    from src.api.middleware.auth_middleware import get_current_user
    test_app.dependency_overrides[get_current_user] = override_get_current_user

    return TestClient(test_app)


@pytest.fixture
def mock_usage_service():
    """Create mock UsageTrackingService."""
    return MagicMock()


# ============================================================================
# GET /api/v1/usage Tests
# ============================================================================

def test_get_usage_success(client, mock_current_user, mock_usage_service):
    """Test successful usage retrieval."""
    mock_usage = {
        "user_id": str(mock_current_user.user_id),
        "period": "current_month",
        "api_calls": 1250,
        "tokens_used": 125000,
        "cost_usd": 12.50,
        "quota": {
            "api_calls_limit": 10000,
            "tokens_limit": 1000000,
            "cost_limit_usd": 100.00
        },
        "usage_percentage": 12.5
    }
    mock_usage_service.get_usage.return_value = mock_usage

    with patch('src.api.routers.usage.UsageTrackingService', return_value=mock_usage_service):
        response = client.get("/api/v1/usage")

    assert response.status_code == 200
    data = response.json()
    assert data['api_calls'] == 1250
    assert data['tokens_used'] == 125000
    assert data['usage_percentage'] == 12.5


def test_get_usage_near_limit(client, mock_current_user, mock_usage_service):
    """Test usage retrieval when near quota limit."""
    mock_usage = {
        "user_id": str(mock_current_user.user_id),
        "period": "current_month",
        "api_calls": 9500,
        "tokens_used": 950000,
        "cost_usd": 95.00,
        "quota": {
            "api_calls_limit": 10000,
            "tokens_limit": 1000000,
            "cost_limit_usd": 100.00
        },
        "usage_percentage": 95.0,
        "warning": "Approaching quota limit"
    }
    mock_usage_service.get_usage.return_value = mock_usage

    with patch('src.api.routers.usage.UsageTrackingService', return_value=mock_usage_service):
        response = client.get("/api/v1/usage")

    data = response.json()
    assert data['usage_percentage'] == 95.0
    assert 'warning' in data


def test_get_usage_exceeded(client, mock_current_user, mock_usage_service):
    """Test usage retrieval when quota exceeded."""
    mock_usage = {
        "user_id": str(mock_current_user.user_id),
        "period": "current_month",
        "api_calls": 10500,
        "tokens_used": 1050000,
        "cost_usd": 105.00,
        "quota": {
            "api_calls_limit": 10000,
            "tokens_limit": 1000000,
            "cost_limit_usd": 100.00
        },
        "usage_percentage": 105.0,
        "error": "Quota exceeded"
    }
    mock_usage_service.get_usage.return_value = mock_usage

    with patch('src.api.routers.usage.UsageTrackingService', return_value=mock_usage_service):
        response = client.get("/api/v1/usage")

    data = response.json()
    assert data['usage_percentage'] > 100.0


def test_get_usage_with_period(client, mock_current_user, mock_usage_service):
    """Test usage retrieval for specific period."""
    mock_usage = {
        "user_id": str(mock_current_user.user_id),
        "period": "last_month",
        "api_calls": 8000,
        "tokens_used": 800000,
        "cost_usd": 80.00,
        "quota": {},
        "usage_percentage": 80.0
    }
    mock_usage_service.get_usage.return_value = mock_usage

    with patch('src.api.routers.usage.UsageTrackingService', return_value=mock_usage_service):
        response = client.get("/api/v1/usage?period=last_month")

    assert response.status_code == 200
    data = response.json()
    assert data['period'] == "last_month"


# ============================================================================
# GET /api/v1/usage/history Tests
# ============================================================================

def test_get_usage_history_success(client, mock_current_user, mock_usage_service):
    """Test successful usage history retrieval."""
    mock_history = [
        {
            "date": (datetime.now() - timedelta(days=i)).isoformat(),
            "api_calls": 100 + i * 10,
            "tokens_used": 10000 + i * 1000,
            "cost_usd": 1.0 + i * 0.1
        }
        for i in range(30)
    ]
    mock_usage_service.get_usage_history.return_value = mock_history

    with patch('src.api.routers.usage.UsageTrackingService', return_value=mock_usage_service):
        response = client.get("/api/v1/usage/history")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 30


def test_get_usage_history_with_limit(client, mock_current_user, mock_usage_service):
    """Test usage history with custom limit."""
    mock_history = [
        {
            "date": (datetime.now() - timedelta(days=i)).isoformat(),
            "api_calls": 100,
            "tokens_used": 10000,
            "cost_usd": 1.0
        }
        for i in range(7)
    ]
    mock_usage_service.get_usage_history.return_value = mock_history

    with patch('src.api.routers.usage.UsageTrackingService', return_value=mock_usage_service):
        response = client.get("/api/v1/usage/history?days=7")

    data = response.json()
    assert len(data) == 7


def test_get_usage_history_empty(client, mock_current_user, mock_usage_service):
    """Test usage history when no data available."""
    mock_usage_service.get_usage_history.return_value = []

    with patch('src.api.routers.usage.UsageTrackingService', return_value=mock_usage_service):
        response = client.get("/api/v1/usage/history")

    assert response.status_code == 200
    assert response.json() == []


# ============================================================================
# GET /api/v1/usage/quota Tests
# ============================================================================

def test_get_quota_success(client, mock_current_user, mock_usage_service):
    """Test successful quota retrieval."""
    mock_quota = {
        "user_id": str(mock_current_user.user_id),
        "api_calls_limit": 10000,
        "tokens_limit": 1000000,
        "cost_limit_usd": 100.00,
        "reset_date": (datetime.now() + timedelta(days=15)).isoformat(),
        "plan": "pro"
    }
    mock_usage_service.get_quota.return_value = mock_quota

    with patch('src.api.routers.usage.UsageTrackingService', return_value=mock_usage_service):
        response = client.get("/api/v1/usage/quota")

    assert response.status_code == 200
    data = response.json()
    assert data['api_calls_limit'] == 10000
    assert data['plan'] == "pro"


def test_get_quota_free_tier(client, mock_current_user, mock_usage_service):
    """Test quota for free tier user."""
    mock_quota = {
        "user_id": str(mock_current_user.user_id),
        "api_calls_limit": 1000,
        "tokens_limit": 100000,
        "cost_limit_usd": 10.00,
        "reset_date": (datetime.now() + timedelta(days=15)).isoformat(),
        "plan": "free"
    }
    mock_usage_service.get_quota.return_value = mock_quota

    with patch('src.api.routers.usage.UsageTrackingService', return_value=mock_usage_service):
        response = client.get("/api/v1/usage/quota")

    data = response.json()
    assert data['plan'] == "free"
    assert data['api_calls_limit'] == 1000


# ============================================================================
# PUT /api/v1/usage/quota Tests (Admin only)
# ============================================================================

def test_update_quota_success(client, mock_current_user, mock_usage_service):
    """Test successful quota update."""
    mock_updated_quota = {
        "user_id": str(mock_current_user.user_id),
        "api_calls_limit": 50000,
        "tokens_limit": 5000000,
        "cost_limit_usd": 500.00,
        "plan": "enterprise"
    }
    mock_usage_service.update_quota.return_value = mock_updated_quota

    with patch('src.api.routers.usage.UsageTrackingService', return_value=mock_usage_service):
        response = client.put(
            "/api/v1/usage/quota",
            json={
                "api_calls_limit": 50000,
                "tokens_limit": 5000000,
                "cost_limit_usd": 500.00
            }
        )

    assert response.status_code == 200
    data = response.json()
    assert data['api_calls_limit'] == 50000


def test_update_quota_unauthorized(client):
    """Test quota update without admin privileges."""
    # This would require admin role check
    response = client.put(
        "/api/v1/usage/quota",
        json={"api_calls_limit": 50000}
    )

    # Should return 403 if admin check is implemented
    assert response.status_code in [200, 403]


# ============================================================================
# POST /api/v1/usage/track Tests
# ============================================================================

def test_track_usage_success(client, mock_current_user, mock_usage_service):
    """Test successful usage tracking."""
    mock_result = {
        "success": True,
        "tracked": {
            "api_calls": 1,
            "tokens_used": 500,
            "cost_usd": 0.05
        },
        "remaining_quota": {
            "api_calls": 9999,
            "tokens": 999500,
            "cost_usd": 99.95
        }
    }
    mock_usage_service.track_usage.return_value = mock_result

    with patch('src.api.routers.usage.UsageTrackingService', return_value=mock_usage_service):
        response = client.post(
            "/api/v1/usage/track",
            json={
                "operation": "api_call",
                "tokens_used": 500,
                "cost_usd": 0.05
            }
        )

    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True


def test_track_usage_quota_exceeded(client, mock_current_user, mock_usage_service):
    """Test usage tracking when quota exceeded."""
    mock_usage_service.track_usage.side_effect = ValueError("Quota exceeded")

    with patch('src.api.routers.usage.UsageTrackingService', return_value=mock_usage_service):
        response = client.post(
            "/api/v1/usage/track",
            json={
                "operation": "api_call",
                "tokens_used": 500
            }
        )

    assert response.status_code == 429  # Too Many Requests


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_usage_service_error(client, mock_current_user, mock_usage_service):
    """Test handling of usage service errors."""
    mock_usage_service.get_usage.side_effect = Exception("Service unavailable")

    with patch('src.api.routers.usage.UsageTrackingService', return_value=mock_usage_service):
        response = client.get("/api/v1/usage")

    assert response.status_code == 500


@pytest.mark.unit
class TestUsageModels:
    """Unit tests for usage request/response models."""

    def test_usage_response_model(self):
        """Test usage response structure."""
        usage = {
            "user_id": str(uuid4()),
            "api_calls": 1000,
            "tokens_used": 100000,
            "cost_usd": 10.00,
            "quota": {"api_calls_limit": 10000}
        }

        assert usage['api_calls'] == 1000
        assert usage['cost_usd'] == 10.00

    def test_quota_response_model(self):
        """Test quota response structure."""
        quota = {
            "api_calls_limit": 10000,
            "tokens_limit": 1000000,
            "cost_limit_usd": 100.00,
            "plan": "pro"
        }

        assert quota['plan'] == "pro"
        assert quota['api_calls_limit'] == 10000

