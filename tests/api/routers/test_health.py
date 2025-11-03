"""
Tests for Health Check API Router

Tests all health check endpoints for proper system monitoring.

Author: DevMatrix Team
Date: 2025-11-03
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routers.health import router


@pytest.fixture
def client():
    """Create test client with health router."""
    test_app = FastAPI()
    test_app.include_router(router)
    return TestClient(test_app)


@pytest.fixture
def mock_health_check():
    """Create mock health check service."""
    return MagicMock()


# ============================================================================
# GET /health Tests
# ============================================================================

def test_health_check_all_healthy(client, mock_health_check):
    """Test health check when all components are healthy."""
    mock_health_check.check_all.return_value = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": {"status": "healthy", "latency_ms": 5},
            "redis": {"status": "healthy", "latency_ms": 2},
            "anthropic_api": {"status": "healthy", "latency_ms": 150}
        }
    }

    with patch('src.api.routers.health.health_check', mock_health_check):
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "components" in data
    assert len(data["components"]) == 3
    assert data["components"]["database"]["status"] == "healthy"


def test_health_check_degraded(client, mock_health_check):
    """Test health check when some components are degraded."""
    mock_health_check.check_all.return_value = {
        "status": "degraded",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": {"status": "healthy", "latency_ms": 5},
            "redis": {"status": "degraded", "latency_ms": 500},
            "anthropic_api": {"status": "healthy", "latency_ms": 150}
        }
    }

    with patch('src.api.routers.health.health_check', mock_health_check):
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["components"]["redis"]["status"] == "degraded"


def test_health_check_unhealthy(client, mock_health_check):
    """Test health check when components are unhealthy."""
    mock_health_check.check_all.return_value = {
        "status": "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": {"status": "unhealthy", "error": "Connection failed"},
            "redis": {"status": "healthy", "latency_ms": 2},
            "anthropic_api": {"status": "healthy", "latency_ms": 150}
        }
    }

    with patch('src.api.routers.health.health_check', mock_health_check):
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unhealthy"
    assert "error" in data["components"]["database"]


# ============================================================================
# GET /health/live Tests (Liveness Probe)
# ============================================================================

def test_liveness_probe_always_returns_alive(client):
    """Test liveness probe always returns alive."""
    response = client.get("/health/live")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"


def test_liveness_probe_fast_response(client):
    """Test liveness probe responds quickly (< 100ms)."""
    import time
    start = time.time()
    response = client.get("/health/live")
    duration = (time.time() - start) * 1000  # Convert to milliseconds

    assert response.status_code == 200
    assert duration < 100  # Should respond in less than 100ms


# ============================================================================
# GET /health/ready Tests (Readiness Probe)
# ============================================================================

def test_readiness_probe_when_healthy(client, mock_health_check):
    """Test readiness probe returns ready when system is healthy."""
    mock_health_check.check_all.return_value = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": {"status": "healthy"},
            "redis": {"status": "healthy"}
        }
    }

    with patch('src.api.routers.health.health_check', mock_health_check):
        response = client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"


def test_readiness_probe_when_unhealthy(client, mock_health_check):
    """Test readiness probe returns not ready when system is unhealthy."""
    mock_health_check.check_all.return_value = {
        "status": "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": {"status": "unhealthy", "error": "Connection failed"}
        }
    }

    with patch('src.api.routers.health.health_check', mock_health_check):
        response = client.get("/health/ready")

    assert response.status_code == 503  # Service Unavailable
    data = response.json()
    assert data["status"] == "not_ready"
    assert "reason" in data


def test_readiness_probe_when_degraded(client, mock_health_check):
    """Test readiness probe returns not ready when system is degraded."""
    mock_health_check.check_all.return_value = {
        "status": "degraded",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "redis": {"status": "degraded"}
        }
    }

    with patch('src.api.routers.health.health_check', mock_health_check):
        response = client.get("/health/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

def test_health_check_with_empty_components(client, mock_health_check):
    """Test health check with no components."""
    mock_health_check.check_all.return_value = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {}
    }

    with patch('src.api.routers.health.health_check', mock_health_check):
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["components"] == {}


def test_health_check_with_many_components(client, mock_health_check):
    """Test health check with many components."""
    components = {
        f"component_{i}": {"status": "healthy", "latency_ms": i}
        for i in range(20)
    }

    mock_health_check.check_all.return_value = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": components
    }

    with patch('src.api.routers.health.health_check', mock_health_check):
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert len(data["components"]) == 20


@pytest.mark.unit
class TestHealthRouterUnit:
    """Unit tests for health router."""

    def test_health_check_response_model(self, client):
        """Test health response follows expected schema."""
        from src.api.routers.health import HealthResponse

        # Verify HealthResponse model exists and has correct fields
        assert hasattr(HealthResponse, '__fields__')
        fields = HealthResponse.__fields__
        assert 'status' in fields
        assert 'timestamp' in fields
        assert 'components' in fields

    def test_liveness_simple_response(self, client):
        """Test liveness returns simple dict response."""
        response = client.get("/health/live")
        data = response.json()

        # Should be simple dict with only status
        assert isinstance(data, dict)
        assert 'status' in data
        assert data['status'] == 'alive'

    def test_readiness_conditional_status_code(self, client, mock_health_check):
        """Test readiness uses correct HTTP status codes."""
        # Test healthy -> 200
        mock_health_check.check_all.return_value = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {}
        }

        with patch('src.api.routers.health.health_check', mock_health_check):
            response = client.get("/health/ready")
        assert response.status_code == 200

        # Test any other status -> 503
        for status_val in ["unhealthy", "degraded", "unknown"]:
            mock_health_check.check_all.return_value = {
                "status": status_val,
                "timestamp": datetime.now().isoformat(),
                "components": {}
            }

            with patch('src.api.routers.health.health_check', mock_health_check):
                response = client.get("/health/ready")
            assert response.status_code == 503

