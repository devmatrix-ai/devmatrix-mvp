"""
Tests for Metrics API Router

Tests Prometheus metrics export and cache statistics endpoints.

Author: DevMatrix Team
Date: 2025-11-03
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routers.metrics import router


@pytest.fixture
def client():
    """Create test client with metrics router."""
    test_app = FastAPI()
    test_app.include_router(router)
    return TestClient(test_app)


@pytest.fixture
def mock_metrics_collector():
    """Create mock metrics collector."""
    collector = MagicMock()
    collector.export_prometheus.return_value = """# HELP workflows_total Total workflows
# TYPE workflows_total gauge
workflows_total 42
# HELP executions_total Total executions
# TYPE executions_total gauge
executions_total 150
"""
    return collector


@pytest.fixture
def mock_workflows_db():
    """Create mock workflows database."""
    return {
        "wf1": {"id": "wf1", "name": "Test Workflow 1"},
        "wf2": {"id": "wf2", "name": "Test Workflow 2"},
    }


@pytest.fixture
def mock_executions_db():
    """Create mock executions database."""
    from src.api.routers.executions import ExecutionStatus

    now = datetime.now()
    return {
        "ex1": {
            "id": "ex1",
            "status": ExecutionStatus.COMPLETED,
            "started_at": now - timedelta(minutes=5),
            "completed_at": now,
        },
        "ex2": {
            "id": "ex2",
            "status": ExecutionStatus.RUNNING,
            "started_at": now - timedelta(minutes=2),
            "completed_at": None,
        },
        "ex3": {
            "id": "ex3",
            "status": ExecutionStatus.COMPLETED,
            "started_at": now - timedelta(minutes=10),
            "completed_at": now - timedelta(minutes=5),
        },
    }


# ============================================================================
# GET /metrics Tests (Prometheus Export)
# ============================================================================

def test_get_prometheus_metrics_success(client, mock_metrics_collector, mock_workflows_db, mock_executions_db):
    """Test successful Prometheus metrics export."""
    with patch('src.api.routers.metrics.metrics_collector', mock_metrics_collector), \
         patch('src.api.routers.metrics.workflows_db', mock_workflows_db), \
         patch('src.api.routers.metrics.executions_db', mock_executions_db):

        response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers['content-type'] == "text/plain; version=0.0.4; charset=utf-8"
    assert "workflows_total" in response.text
    assert "executions_total" in response.text


def test_get_prometheus_metrics_format(client, mock_metrics_collector):
    """Test Prometheus metrics follow correct format."""
    with patch('src.api.routers.metrics.metrics_collector', mock_metrics_collector), \
         patch('src.api.routers.metrics.workflows_db', {}), \
         patch('src.api.routers.metrics.executions_db', {}):

        response = client.get("/metrics")

    # Should contain Prometheus format markers
    assert "# HELP" in response.text or "# TYPE" in response.text


def test_get_prometheus_metrics_empty_data(client, mock_metrics_collector):
    """Test Prometheus metrics with no workflows/executions."""
    with patch('src.api.routers.metrics.metrics_collector', mock_metrics_collector), \
         patch('src.api.routers.metrics.workflows_db', {}), \
         patch('src.api.routers.metrics.executions_db', {}):

        response = client.get("/metrics")

    assert response.status_code == 200
    mock_metrics_collector.set_gauge.assert_any_call("workflows_total", 0)
    mock_metrics_collector.set_gauge.assert_any_call("executions_total", 0)


# ============================================================================
# GET /metrics/summary Tests
# ============================================================================

def test_get_metrics_summary_success(client, mock_workflows_db, mock_executions_db):
    """Test successful metrics summary retrieval."""
    with patch('src.api.routers.metrics.workflows_db', mock_workflows_db), \
         patch('src.api.routers.metrics.executions_db', mock_executions_db):

        response = client.get("/metrics/summary")

    assert response.status_code == 200
    data = response.json()
    assert data['total_workflows'] == 2
    assert data['total_executions'] == 3
    assert 'executions_by_status' in data
    assert 'avg_execution_time_seconds' in data


def test_get_metrics_summary_execution_time_calculation(client, mock_executions_db):
    """Test execution time average calculation."""
    with patch('src.api.routers.metrics.workflows_db', {}), \
         patch('src.api.routers.metrics.executions_db', mock_executions_db):

        response = client.get("/metrics/summary")

    data = response.json()
    # Should calculate average of completed executions
    # ex1: 5 minutes = 300 seconds
    # ex3: 5 minutes = 300 seconds
    # Average: 300 seconds
    assert data['avg_execution_time_seconds'] > 0
    assert data['avg_execution_time_seconds'] <= 600  # Max 10 minutes


def test_get_metrics_summary_status_counts(client, mock_executions_db):
    """Test execution status counting."""
    with patch('src.api.routers.metrics.workflows_db', {}), \
         patch('src.api.routers.metrics.executions_db', mock_executions_db):

        response = client.get("/metrics/summary")

    data = response.json()
    status_counts = data['executions_by_status']
    assert 'completed' in status_counts or 'running' in status_counts


def test_get_metrics_summary_empty(client):
    """Test metrics summary with no data."""
    with patch('src.api.routers.metrics.workflows_db', {}), \
         patch('src.api.routers.metrics.executions_db', {}):

        response = client.get("/metrics/summary")

    assert response.status_code == 200
    data = response.json()
    assert data['total_workflows'] == 0
    assert data['total_executions'] == 0
    assert data['avg_execution_time_seconds'] == 0.0


def test_get_metrics_summary_no_completed_executions(client):
    """Test metrics summary when no executions are completed."""
    from src.api.routers.executions import ExecutionStatus

    mock_execs = {
        "ex1": {
            "id": "ex1",
            "status": ExecutionStatus.RUNNING,
            "started_at": datetime.now(),
            "completed_at": None,
        },
    }

    with patch('src.api.routers.metrics.workflows_db', {}), \
         patch('src.api.routers.metrics.executions_db', mock_execs):

        response = client.get("/metrics/summary")

    data = response.json()
    assert data['avg_execution_time_seconds'] == 0.0


# ============================================================================
# GET /metrics/cache/statistics Tests
# ============================================================================

def test_get_cache_statistics_success(client):
    """Test successful cache statistics retrieval."""
    mock_stats = {
        "hit_rate": 0.85,
        "total_hits": 850,
        "total_misses": 150,
        "total_writes": 200,
        "total_invalidations": 10,
        "total_errors": 2,
    }

    with patch('src.api.routers.metrics.get_cache_statistics', return_value=mock_stats):
        response = client.get("/metrics/cache/statistics")

    assert response.status_code == 200
    data = response.json()
    assert 'llm_cache' in data
    assert 'rag_cache' in data
    assert 'rag_similarity_cache' in data
    assert 'combined_hit_rate' in data


def test_get_cache_statistics_combined_hit_rate(client):
    """Test combined hit rate calculation."""
    mock_llm_stats = {
        "hit_rate": 0.90,
        "total_hits": 900,
        "total_misses": 100,
        "total_writes": 100,
        "total_invalidations": 5,
        "total_errors": 1,
    }

    mock_rag_stats = {
        "hit_rate": 0.80,
        "total_hits": 400,
        "total_misses": 100,
        "total_writes": 50,
        "total_invalidations": 2,
        "total_errors": 0,
    }

    mock_rag_sim_stats = {
        "hit_rate": 0.75,
        "total_hits": 300,
        "total_misses": 100,
        "total_writes": 50,
        "total_invalidations": 1,
        "total_errors": 0,
    }

    def get_stats_side_effect(layer):
        if layer == "llm":
            return mock_llm_stats
        elif layer == "rag":
            return mock_rag_stats
        elif layer == "rag_similarity":
            return mock_rag_sim_stats

    with patch('src.api.routers.metrics.get_cache_statistics', side_effect=get_stats_side_effect):
        response = client.get("/metrics/cache/statistics")

    data = response.json()
    # Combined: (900 + 400 + 300) / (900 + 400 + 300 + 100 + 100 + 100) = 1600 / 1900 ≈ 0.84
    assert 0.80 <= data['combined_hit_rate'] <= 0.90


def test_get_cache_statistics_zero_hits_misses(client):
    """Test cache statistics with zero hits and misses."""
    mock_stats = {
        "hit_rate": 0.0,
        "total_hits": 0,
        "total_misses": 0,
        "total_writes": 0,
        "total_invalidations": 0,
        "total_errors": 0,
    }

    with patch('src.api.routers.metrics.get_cache_statistics', return_value=mock_stats):
        response = client.get("/metrics/cache/statistics")

    data = response.json()
    assert data['combined_hit_rate'] == 0.0  # Should handle division by zero


# ============================================================================
# GET /metrics/cache/statistics/{cache_layer} Tests
# ============================================================================

def test_get_cache_layer_statistics_llm(client):
    """Test cache statistics for LLM layer."""
    mock_stats = {
        "hit_rate": 0.90,
        "total_hits": 900,
        "total_misses": 100,
        "total_writes": 100,
        "total_invalidations": 5,
        "total_errors": 1,
    }

    with patch('src.api.routers.metrics.get_cache_statistics', return_value=mock_stats):
        response = client.get("/metrics/cache/statistics/llm")

    assert response.status_code == 200
    data = response.json()
    assert data['cache_layer'] == 'llm'
    assert data['hit_rate'] == 0.90
    assert data['total_hits'] == 900


def test_get_cache_layer_statistics_rag(client):
    """Test cache statistics for RAG layer."""
    mock_stats = {
        "hit_rate": 0.80,
        "total_hits": 400,
        "total_misses": 100,
        "total_writes": 50,
        "total_invalidations": 2,
        "total_errors": 0,
    }

    with patch('src.api.routers.metrics.get_cache_statistics', return_value=mock_stats):
        response = client.get("/metrics/cache/statistics/rag")

    assert response.status_code == 200
    data = response.json()
    assert data['cache_layer'] == 'rag'
    assert data['hit_rate'] == 0.80


def test_get_cache_layer_statistics_rag_similarity(client):
    """Test cache statistics for RAG similarity layer."""
    mock_stats = {
        "hit_rate": 0.75,
        "total_hits": 300,
        "total_misses": 100,
        "total_writes": 50,
        "total_invalidations": 1,
        "total_errors": 0,
    }

    with patch('src.api.routers.metrics.get_cache_statistics', return_value=mock_stats):
        response = client.get("/metrics/cache/statistics/rag_similarity")

    assert response.status_code == 200
    data = response.json()
    assert data['cache_layer'] == 'rag_similarity'
    assert data['hit_rate'] == 0.75


def test_get_cache_layer_statistics_invalid_layer(client):
    """Test cache statistics with invalid layer name."""
    response = client.get("/metrics/cache/statistics/invalid_layer")

    assert response.status_code == 400
    assert "Invalid cache_layer" in response.json()['detail']


def test_get_cache_layer_statistics_all_layers(client):
    """Test that all valid layer names work."""
    mock_stats = {
        "hit_rate": 0.85,
        "total_hits": 100,
        "total_misses": 20,
        "total_writes": 30,
        "total_invalidations": 5,
        "total_errors": 1,
    }

    valid_layers = ["llm", "rag", "rag_similarity"]

    with patch('src.api.routers.metrics.get_cache_statistics', return_value=mock_stats):
        for layer in valid_layers:
            response = client.get(f"/metrics/cache/statistics/{layer}")
            assert response.status_code == 200
            data = response.json()
            assert data['cache_layer'] == layer


# ============================================================================
# Unit Tests for Response Models
# ============================================================================

@pytest.mark.unit
class TestMetricsModels:
    """Unit tests for metrics response models."""

    def test_metrics_summary_model(self):
        """Test MetricsSummary model validation."""
        from src.api.routers.metrics import MetricsSummary

        summary = MetricsSummary(
            total_workflows=10,
            total_executions=50,
            executions_by_status={"completed": 30, "running": 20},
            avg_execution_time_seconds=125.5
        )

        assert summary.total_workflows == 10
        assert summary.total_executions == 50
        assert summary.avg_execution_time_seconds == 125.5

    def test_cache_statistics_model(self):
        """Test CacheStatistics model validation."""
        from src.api.routers.metrics import CacheStatistics

        stats = CacheStatistics(
            cache_layer="llm",
            hit_rate=0.85,
            total_hits=850,
            total_misses=150,
            total_writes=200,
            total_invalidations=10,
            total_errors=2
        )

        assert stats.cache_layer == "llm"
        assert stats.hit_rate == 0.85
        assert stats.total_hits == 850

    def test_combined_cache_statistics_model(self):
        """Test CombinedCacheStatistics model validation."""
        from src.api.routers.metrics import CombinedCacheStatistics, CacheStatistics

        llm_stats = CacheStatistics(
            cache_layer="llm",
            hit_rate=0.9,
            total_hits=900,
            total_misses=100,
            total_writes=100,
            total_invalidations=5,
            total_errors=1
        )

        rag_stats = CacheStatistics(
            cache_layer="rag",
            hit_rate=0.8,
            total_hits=400,
            total_misses=100,
            total_writes=50,
            total_invalidations=2,
            total_errors=0
        )

        rag_sim_stats = CacheStatistics(
            cache_layer="rag_similarity",
            hit_rate=0.75,
            total_hits=300,
            total_misses=100,
            total_writes=50,
            total_invalidations=1,
            total_errors=0
        )

        combined = CombinedCacheStatistics(
            llm_cache=llm_stats,
            rag_cache=rag_stats,
            rag_similarity_cache=rag_sim_stats,
            combined_hit_rate=0.84
        )

        assert combined.llm_cache.hit_rate == 0.9
        assert combined.rag_cache.hit_rate == 0.8
        assert combined.combined_hit_rate == 0.84

