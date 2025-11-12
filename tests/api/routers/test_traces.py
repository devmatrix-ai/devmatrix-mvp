"""
Tests for Traces API endpoints.

Complete test coverage for E2E tracing REST API.
"""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from src.api.main import app
from src.mge.v2.tracing import get_trace_collector, AtomTrace
from src.mge.v2.validation.atomic_validator import AtomicValidationResult


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_traces():
    """Clear traces before and after each test."""
    collector = get_trace_collector()
    collector.clear_traces()
    yield
    collector.clear_traces()


@pytest.fixture
def sample_trace():
    """Create a sample trace for testing."""
    collector = get_trace_collector()
    atom_id = uuid4()
    masterplan_id = uuid4()

    trace = collector.start_trace(
        atom_id=atom_id,
        masterplan_id=masterplan_id,
        wave_id=1,
        atom_name="test_atom",
        context_data={"key": "value"},
        dependencies=[]
    )

    # Add some data to the trace
    collector.record_retry_attempt(
        atom_id=atom_id,
        attempt=1,
        temperature=0.7,
        success=True,
        duration_ms=1000.0
    )

    validation_result = AtomicValidationResult(
        passed=True,
        issues=[],
        metrics={
            "l1_syntax": {"passed": True},
            "l2_imports": {"passed": True},
            "l3_types": {"passed": True},
            "l4_complexity": {"passed": True}
        }
    )

    collector.record_validation(
        atom_id=atom_id,
        validation_result=validation_result,
        duration_ms=500.0
    )

    collector.record_cost(
        atom_id=atom_id,
        llm_api_cost_usd=0.05,
        prompt_tokens=1000,
        completion_tokens=500
    )

    collector.complete_trace(
        atom_id=atom_id,
        success=True,
        code="def test(): pass"
    )

    return {
        "trace": trace,
        "atom_id": atom_id,
        "masterplan_id": masterplan_id
    }


class TestGetTraceById:
    """Test GET /api/v2/traces/{trace_id} endpoint."""

    def test_get_existing_trace(self, client, sample_trace):
        """Test getting trace by ID."""
        trace_id = sample_trace["trace"].trace_id

        response = client.get(f"/api/v2/traces/{trace_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["trace_id"] == str(trace_id)
        assert data["atom_name"] == "test_atom"
        assert data["final_status"] == "success"

    def test_get_nonexistent_trace(self, client):
        """Test getting trace that doesn't exist."""
        fake_trace_id = uuid4()

        response = client.get(f"/api/v2/traces/{fake_trace_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestGetTraceByAtom:
    """Test GET /api/v2/traces/atom/{atom_id} endpoint."""

    def test_get_trace_by_atom_id(self, client, sample_trace):
        """Test getting trace by atom ID."""
        atom_id = sample_trace["atom_id"]

        response = client.get(f"/api/v2/traces/atom/{atom_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["atom_id"] == str(atom_id)
        assert data["atom_name"] == "test_atom"

    def test_get_trace_by_nonexistent_atom(self, client):
        """Test getting trace for atom that doesn't exist."""
        fake_atom_id = uuid4()

        response = client.get(f"/api/v2/traces/atom/{fake_atom_id}")

        assert response.status_code == 404
        assert "no trace found" in response.json()["detail"].lower()


class TestGetMasterplanTraces:
    """Test GET /api/v2/traces/masterplan/{masterplan_id} endpoint."""

    def test_get_masterplan_traces(self, client, sample_trace):
        """Test getting all traces for masterplan."""
        masterplan_id = sample_trace["masterplan_id"]

        response = client.get(f"/api/v2/traces/masterplan/{masterplan_id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["masterplan_id"] == str(masterplan_id)

    def test_get_masterplan_traces_with_limit(self, client):
        """Test getting traces with limit parameter."""
        collector = get_trace_collector()
        masterplan_id = uuid4()

        # Create 3 traces
        for i in range(3):
            atom_id = uuid4()
            trace = collector.start_trace(
                atom_id=atom_id,
                masterplan_id=masterplan_id,
                wave_id=1,
                atom_name=f"atom_{i}"
            )
            collector.complete_trace(atom_id, True, "code")

        response = client.get(f"/api/v2/traces/masterplan/{masterplan_id}?limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_get_masterplan_traces_with_status_filter(self, client):
        """Test getting traces filtered by status."""
        collector = get_trace_collector()
        masterplan_id = uuid4()

        # Create 2 successful traces
        for i in range(2):
            atom_id = uuid4()
            collector.start_trace(atom_id, masterplan_id, 1, f"success_{i}")
            collector.complete_trace(atom_id, True, "code")

        # Create 1 failed trace
        failed_atom = uuid4()
        collector.start_trace(failed_atom, masterplan_id, 1, "failed")
        collector.complete_trace(failed_atom, False, error="Error")

        # Filter by success
        response = client.get(f"/api/v2/traces/masterplan/{masterplan_id}?status=success")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(t["final_status"] == "success" for t in data)

        # Filter by failed
        response = client.get(f"/api/v2/traces/masterplan/{masterplan_id}?status=failed")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["final_status"] == "failed"

    def test_get_masterplan_traces_empty(self, client):
        """Test getting traces for masterplan with no traces."""
        empty_masterplan_id = uuid4()

        response = client.get(f"/api/v2/traces/masterplan/{empty_masterplan_id}")

        assert response.status_code == 200
        data = response.json()
        assert data == []


class TestGetCorrelations:
    """Test GET /api/v2/traces/masterplan/{masterplan_id}/correlations endpoint."""

    def test_get_correlations(self, client, sample_trace):
        """Test getting correlation data."""
        masterplan_id = sample_trace["masterplan_id"]

        response = client.get(f"/api/v2/traces/masterplan/{masterplan_id}/correlations")

        assert response.status_code == 200
        data = response.json()
        assert data["masterplan_id"] == str(masterplan_id)
        assert data["total_atoms"] == 1
        assert "avg_retries_success" in data
        assert "avg_retries_failed" in data

    def test_get_correlations_empty_masterplan(self, client):
        """Test getting correlations for masterplan with no traces."""
        empty_masterplan_id = uuid4()

        response = client.get(f"/api/v2/traces/masterplan/{empty_masterplan_id}/correlations")

        assert response.status_code == 200
        data = response.json()
        assert data["total_atoms"] == 0
        assert data["avg_retries_success"] == 0.0


class TestGetMasterplanSummary:
    """Test GET /api/v2/traces/masterplan/{masterplan_id}/summary endpoint."""

    def test_get_summary_with_traces(self, client, sample_trace):
        """Test getting summary statistics."""
        masterplan_id = sample_trace["masterplan_id"]

        response = client.get(f"/api/v2/traces/masterplan/{masterplan_id}/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["masterplan_id"] == str(masterplan_id)
        assert data["total_atoms"] == 1
        assert data["success_count"] == 1
        assert data["failed_count"] == 0
        assert data["success_rate"] == 100.0
        assert data["avg_duration_ms"] > 0
        assert data["avg_cost_usd"] == 0.05
        assert data["total_cost_usd"] == 0.05

    def test_get_summary_empty_masterplan(self, client):
        """Test getting summary for masterplan with no traces."""
        empty_masterplan_id = uuid4()

        response = client.get(f"/api/v2/traces/masterplan/{empty_masterplan_id}/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_atoms"] == 0
        assert data["success_count"] == 0
        assert data["success_rate"] == 0.0
        assert data["avg_duration_ms"] == 0.0
        assert data["avg_cost_usd"] == 0.0


class TestClearMasterplanTraces:
    """Test DELETE /api/v2/traces/masterplan/{masterplan_id} endpoint."""

    def test_clear_masterplan_traces(self, client, sample_trace):
        """Test clearing traces for specific masterplan."""
        masterplan_id = sample_trace["masterplan_id"]

        # Verify trace exists
        response = client.get(f"/api/v2/traces/masterplan/{masterplan_id}")
        assert len(response.json()) == 1

        # Clear traces
        response = client.delete(f"/api/v2/traces/masterplan/{masterplan_id}")

        assert response.status_code == 200
        assert "cleared" in response.json()["message"].lower()

        # Verify traces are gone
        response = client.get(f"/api/v2/traces/masterplan/{masterplan_id}")
        assert len(response.json()) == 0

    def test_clear_nonexistent_masterplan(self, client):
        """Test clearing traces for masterplan that doesn't exist."""
        fake_masterplan_id = uuid4()

        response = client.delete(f"/api/v2/traces/masterplan/{fake_masterplan_id}")

        assert response.status_code == 200


class TestClearAllTraces:
    """Test DELETE /api/v2/traces/all endpoint."""

    def test_clear_all_traces(self, client):
        """Test clearing all traces."""
        collector = get_trace_collector()

        # Create traces for 2 different masterplans
        masterplan1 = uuid4()
        masterplan2 = uuid4()

        atom1 = uuid4()
        collector.start_trace(atom1, masterplan1, 1, "atom1")
        collector.complete_trace(atom1, True, "code")

        atom2 = uuid4()
        collector.start_trace(atom2, masterplan2, 1, "atom2")
        collector.complete_trace(atom2, True, "code")

        # Verify both exist
        assert len(collector.get_masterplan_traces(masterplan1)) == 1
        assert len(collector.get_masterplan_traces(masterplan2)) == 1

        # Clear all
        response = client.delete("/api/v2/traces/all")

        assert response.status_code == 200
        assert "cleared all" in response.json()["message"].lower()

        # Verify all are gone
        assert len(collector.get_masterplan_traces(masterplan1)) == 0
        assert len(collector.get_masterplan_traces(masterplan2)) == 0


class TestIntegration:
    """Integration tests for complete trace workflows."""

    def test_complete_workflow(self, client):
        """Test complete trace lifecycle through API."""
        collector = get_trace_collector()
        masterplan_id = uuid4()
        atom_id = uuid4()

        # Create trace
        trace = collector.start_trace(
            atom_id=atom_id,
            masterplan_id=masterplan_id,
            wave_id=1,
            atom_name="integration_test"
        )

        # Get by trace ID
        response = client.get(f"/api/v2/traces/{trace.trace_id}")
        assert response.status_code == 200

        # Get by atom ID
        response = client.get(f"/api/v2/traces/atom/{atom_id}")
        assert response.status_code == 200

        # Get masterplan traces
        response = client.get(f"/api/v2/traces/masterplan/{masterplan_id}")
        assert response.status_code == 200
        assert len(response.json()) == 1

        # Get correlations
        response = client.get(f"/api/v2/traces/masterplan/{masterplan_id}/correlations")
        assert response.status_code == 200

        # Get summary
        response = client.get(f"/api/v2/traces/masterplan/{masterplan_id}/summary")
        assert response.status_code == 200

        # Clear masterplan
        response = client.delete(f"/api/v2/traces/masterplan/{masterplan_id}")
        assert response.status_code == 200

        # Verify cleared
        response = client.get(f"/api/v2/traces/masterplan/{masterplan_id}")
        assert len(response.json()) == 0
