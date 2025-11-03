"""
Tests for Dependency API Router (MGE V2)

Tests dependency graph building and query endpoints.

Author: DevMatrix Team
Date: 2025-11-03
"""

import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routers.dependency import router


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return MagicMock()


@pytest.fixture
def client(mock_db):
    """Create test client with dependency router."""
    from src.config.database import get_db

    test_app = FastAPI()
    test_app.include_router(router)

    # Override get_db dependency
    test_app.dependency_overrides[get_db] = lambda: mock_db

    return TestClient(test_app)


@pytest.fixture
def sample_masterplan_id():
    """Sample masterplan UUID."""
    return str(uuid4())


@pytest.fixture
def sample_atom_id():
    """Sample atom UUID."""
    return str(uuid4())


@pytest.fixture
def mock_dependency_service():
    """Create mock DependencyService."""
    return MagicMock()


# ============================================================================
# POST /api/v2/dependency/build Tests
# ============================================================================

def test_build_graph_success(client, sample_masterplan_id, mock_dependency_service):
    """Test successful dependency graph building."""
    mock_result = {
        "success": True,
        "masterplan_id": sample_masterplan_id,
        "total_atoms": 50,
        "graph_stats": {
            "nodes": 50,
            "edges": 75,
            "density": 0.03,
            "has_cycles": False
        },
        "execution_plan": {
            "total_waves": 8,
            "max_parallelism": 12,
            "estimated_duration_minutes": 45
        },
        "waves": [
            {"wave_number": 1, "atom_count": 5, "dependencies_resolved": True},
            {"wave_number": 2, "atom_count": 8, "dependencies_resolved": True}
        ]
    }
    mock_dependency_service.build_graph.return_value = mock_result

    with patch('src.api.routers.dependency.DependencyService', return_value=mock_dependency_service):
        response = client.post(
            "/api/v2/dependency/build",
            json={"masterplan_id": sample_masterplan_id}
        )

    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert data['total_atoms'] == 50
    assert 'graph_stats' in data
    assert 'execution_plan' in data


def test_build_graph_with_cycles(client, sample_masterplan_id, mock_dependency_service):
    """Test graph building with circular dependencies."""
    mock_result = {
        "success": True,
        "masterplan_id": sample_masterplan_id,
        "total_atoms": 30,
        "graph_stats": {
            "nodes": 30,
            "edges": 45,
            "density": 0.05,
            "has_cycles": True,
            "cycles": [
                {"nodes": ["atom_1", "atom_2", "atom_3"], "severity": "warning"}
            ]
        },
        "execution_plan": {},
        "waves": []
    }
    mock_dependency_service.build_graph.return_value = mock_result

    with patch('src.api.routers.dependency.DependencyService', return_value=mock_dependency_service):
        response = client.post(
            "/api/v2/dependency/build",
            json={"masterplan_id": sample_masterplan_id}
        )

    data = response.json()
    assert data['graph_stats']['has_cycles'] is True


def test_build_graph_masterplan_not_found(client, mock_dependency_service):
    """Test graph building with non-existent masterplan."""
    masterplan_id = str(uuid4())
    mock_dependency_service.build_graph.side_effect = ValueError("MasterPlan not found")

    with patch('src.api.routers.dependency.DependencyService', return_value=mock_dependency_service):
        response = client.post(
            "/api/v2/dependency/build",
            json={"masterplan_id": masterplan_id}
        )

    assert response.status_code == 404


def test_build_graph_invalid_uuid(client):
    """Test graph building with invalid UUID format."""
    response = client.post(
        "/api/v2/dependency/build",
        json={"masterplan_id": "invalid-uuid"}
    )

    assert response.status_code == 400


def test_build_graph_no_atoms(client, sample_masterplan_id, mock_dependency_service):
    """Test graph building for masterplan with no atoms."""
    mock_result = {
        "success": True,
        "masterplan_id": sample_masterplan_id,
        "total_atoms": 0,
        "graph_stats": {
            "nodes": 0,
            "edges": 0,
            "density": 0,
            "has_cycles": False
        },
        "execution_plan": {},
        "waves": []
    }
    mock_dependency_service.build_graph.return_value = mock_result

    with patch('src.api.routers.dependency.DependencyService', return_value=mock_dependency_service):
        response = client.post(
            "/api/v2/dependency/build",
            json={"masterplan_id": sample_masterplan_id}
        )

    data = response.json()
    assert data['total_atoms'] == 0


# ============================================================================
# GET /api/v2/dependency/graph/{masterplan_id} Tests
# ============================================================================

def test_get_graph_success(client, sample_masterplan_id, mock_dependency_service):
    """Test successful dependency graph retrieval."""
    mock_result = {
        "graph_id": str(uuid4()),
        "masterplan_id": sample_masterplan_id,
        "total_atoms": 50,
        "total_dependencies": 75,
        "has_cycles": False,
        "max_parallelism": 12,
        "waves": [
            {"wave_number": 1, "atoms": ["atom1", "atom2"]},
            {"wave_number": 2, "atoms": ["atom3", "atom4", "atom5"]}
        ]
    }
    mock_dependency_service.get_graph.return_value = mock_result

    with patch('src.api.routers.dependency.DependencyService', return_value=mock_dependency_service):
        response = client.get(f"/api/v2/dependency/graph/{sample_masterplan_id}")

    assert response.status_code == 200
    data = response.json()
    assert data['masterplan_id'] == sample_masterplan_id
    assert data['total_atoms'] == 50
    assert data['max_parallelism'] == 12


def test_get_graph_not_found(client, mock_dependency_service):
    """Test getting graph for non-existent masterplan."""
    masterplan_id = str(uuid4())
    mock_dependency_service.get_graph.side_effect = ValueError("Graph not found")

    with patch('src.api.routers.dependency.DependencyService', return_value=mock_dependency_service):
        response = client.get(f"/api/v2/dependency/graph/{masterplan_id}")

    assert response.status_code == 404


def test_get_graph_with_complex_dependencies(client, sample_masterplan_id, mock_dependency_service):
    """Test getting graph with complex dependency structure."""
    mock_result = {
        "graph_id": str(uuid4()),
        "masterplan_id": sample_masterplan_id,
        "total_atoms": 100,
        "total_dependencies": 250,
        "has_cycles": False,
        "max_parallelism": 25,
        "waves": [
            {"wave_number": i, "atoms": [f"atom_{j}" for j in range(5)]}
            for i in range(1, 11)
        ]
    }
    mock_dependency_service.get_graph.return_value = mock_result

    with patch('src.api.routers.dependency.DependencyService', return_value=mock_dependency_service):
        response = client.get(f"/api/v2/dependency/graph/{sample_masterplan_id}")

    data = response.json()
    assert data['total_atoms'] == 100
    assert data['total_dependencies'] == 250
    assert len(data['waves']) == 10


# ============================================================================
# GET /api/v2/dependency/waves/{masterplan_id} Tests
# ============================================================================

def test_get_waves_success(client, sample_masterplan_id, mock_dependency_service):
    """Test successful wave retrieval."""
    mock_result = [
        {
            "wave_number": 1,
            "atom_count": 5,
            "atom_ids": [str(uuid4()) for _ in range(5)],
            "estimated_duration_minutes": 5
        },
        {
            "wave_number": 2,
            "atom_count": 8,
            "atom_ids": [str(uuid4()) for _ in range(8)],
            "estimated_duration_minutes": 8
        }
    ]
    mock_dependency_service.get_waves.return_value = mock_result

    with patch('src.api.routers.dependency.DependencyService', return_value=mock_dependency_service):
        response = client.get(f"/api/v2/dependency/waves/{sample_masterplan_id}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]['wave_number'] == 1
    assert data[0]['atom_count'] == 5


def test_get_waves_empty(client, sample_masterplan_id, mock_dependency_service):
    """Test wave retrieval for masterplan with no waves."""
    mock_dependency_service.get_waves.return_value = []

    with patch('src.api.routers.dependency.DependencyService', return_value=mock_dependency_service):
        response = client.get(f"/api/v2/dependency/waves/{sample_masterplan_id}")

    assert response.status_code == 200
    assert response.json() == []


def test_get_waves_single_wave(client, sample_masterplan_id, mock_dependency_service):
    """Test waves with all atoms in single wave (no dependencies)."""
    mock_result = [
        {
            "wave_number": 1,
            "atom_count": 50,
            "atom_ids": [str(uuid4()) for _ in range(50)],
            "estimated_duration_minutes": 50
        }
    ]
    mock_dependency_service.get_waves.return_value = mock_result

    with patch('src.api.routers.dependency.DependencyService', return_value=mock_dependency_service):
        response = client.get(f"/api/v2/dependency/waves/{sample_masterplan_id}")

    data = response.json()
    assert len(data) == 1
    assert data[0]['atom_count'] == 50


def test_get_waves_many_waves(client, sample_masterplan_id, mock_dependency_service):
    """Test waves with deep dependency chain."""
    mock_result = [
        {
            "wave_number": i,
            "atom_count": 3,
            "atom_ids": [str(uuid4()) for _ in range(3)],
            "estimated_duration_minutes": 3
        }
        for i in range(1, 21)  # 20 waves
    ]
    mock_dependency_service.get_waves.return_value = mock_result

    with patch('src.api.routers.dependency.DependencyService', return_value=mock_dependency_service):
        response = client.get(f"/api/v2/dependency/waves/{sample_masterplan_id}")

    data = response.json()
    assert len(data) == 20


# ============================================================================
# GET /api/v2/dependency/atom/{atom_id} Tests
# ============================================================================

def test_get_atom_dependencies_success(client, sample_atom_id, mock_dependency_service):
    """Test successful atom dependencies retrieval."""
    mock_result = {
        "atom_id": sample_atom_id,
        "depends_on": [str(uuid4()), str(uuid4())],
        "required_by": [str(uuid4()), str(uuid4()), str(uuid4())],
        "wave_number": 3,
        "can_execute_after_wave": 2
    }
    mock_dependency_service.get_atom_dependencies.return_value = mock_result

    with patch('src.api.routers.dependency.DependencyService', return_value=mock_dependency_service):
        response = client.get(f"/api/v2/dependency/atom/{sample_atom_id}")

    assert response.status_code == 200
    data = response.json()
    assert data['atom_id'] == sample_atom_id
    assert len(data['depends_on']) == 2
    assert len(data['required_by']) == 3


def test_get_atom_dependencies_no_dependencies(client, sample_atom_id, mock_dependency_service):
    """Test atom with no dependencies (can execute in wave 1)."""
    mock_result = {
        "atom_id": sample_atom_id,
        "depends_on": [],
        "required_by": [str(uuid4()) for _ in range(5)],
        "wave_number": 1,
        "can_execute_after_wave": 0
    }
    mock_dependency_service.get_atom_dependencies.return_value = mock_result

    with patch('src.api.routers.dependency.DependencyService', return_value=mock_dependency_service):
        response = client.get(f"/api/v2/dependency/atom/{sample_atom_id}")

    data = response.json()
    assert len(data['depends_on']) == 0
    assert data['wave_number'] == 1


def test_get_atom_dependencies_isolated_atom(client, sample_atom_id, mock_dependency_service):
    """Test atom with no dependencies or dependents."""
    mock_result = {
        "atom_id": sample_atom_id,
        "depends_on": [],
        "required_by": [],
        "wave_number": 1,
        "can_execute_after_wave": 0
    }
    mock_dependency_service.get_atom_dependencies.return_value = mock_result

    with patch('src.api.routers.dependency.DependencyService', return_value=mock_dependency_service):
        response = client.get(f"/api/v2/dependency/atom/{sample_atom_id}")

    data = response.json()
    assert len(data['depends_on']) == 0
    assert len(data['required_by']) == 0


def test_get_atom_dependencies_not_found(client, mock_dependency_service):
    """Test getting dependencies for non-existent atom."""
    atom_id = str(uuid4())
    mock_dependency_service.get_atom_dependencies.side_effect = ValueError("Atom not found")

    with patch('src.api.routers.dependency.DependencyService', return_value=mock_dependency_service):
        response = client.get(f"/api/v2/dependency/atom/{atom_id}")

    assert response.status_code == 404


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_dependency_service_error(client, sample_masterplan_id, mock_dependency_service):
    """Test handling of dependency service errors."""
    mock_dependency_service.build_graph.side_effect = Exception("Graph building failed")

    with patch('src.api.routers.dependency.DependencyService', return_value=mock_dependency_service):
        response = client.post(
            "/api/v2/dependency/build",
            json={"masterplan_id": sample_masterplan_id}
        )

    assert response.status_code == 500


def test_database_connection_error(client, sample_masterplan_id, mock_db):
    """Test handling of database connection errors."""
    mock_db.query.side_effect = Exception("Database unavailable")

    response = client.post(
        "/api/v2/dependency/build",
        json={"masterplan_id": sample_masterplan_id}
    )

    assert response.status_code in [500, 503]


@pytest.mark.unit
class TestDependencyModels:
    """Unit tests for dependency request/response models."""

    def test_build_graph_request(self):
        """Test BuildGraphRequest model."""
        from src.api.routers.dependency import BuildGraphRequest

        request = BuildGraphRequest(masterplan_id=str(uuid4()))
        assert request.masterplan_id is not None

    def test_build_graph_response(self):
        """Test BuildGraphResponse model."""
        from src.api.routers.dependency import BuildGraphResponse

        response = BuildGraphResponse(
            success=True,
            masterplan_id=str(uuid4()),
            total_atoms=50,
            graph_stats={"nodes": 50, "edges": 75},
            execution_plan={"waves": 8},
            waves=[]
        )
        assert response.success is True
        assert response.total_atoms == 50

    def test_wave_response(self):
        """Test WaveResponse model."""
        from src.api.routers.dependency import WaveResponse

        wave = WaveResponse(
            wave_number=1,
            atom_count=5,
            atom_ids=[str(uuid4()) for _ in range(5)],
            estimated_duration_minutes=5
        )
        assert wave.wave_number == 1
        assert len(wave.atom_ids) == 5

