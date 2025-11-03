"""
Tests for Validation API Router (MGE V2)

Tests hierarchical validation endpoints for atoms, tasks, milestones, and masterplans.

Author: DevMatrix Team
Date: 2025-11-03
"""

import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routers.validation import router


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return MagicMock()


@pytest.fixture
def client(mock_db):
    """Create test client with validation router."""
    from src.config.database import get_db

    test_app = FastAPI()
    test_app.include_router(router)

    # Override get_db dependency
    test_app.dependency_overrides[get_db] = lambda: mock_db

    return TestClient(test_app)


@pytest.fixture
def sample_atom_id():
    """Sample atom UUID."""
    return str(uuid4())


@pytest.fixture
def sample_task_id():
    """Sample task UUID."""
    return str(uuid4())


@pytest.fixture
def sample_milestone_id():
    """Sample milestone UUID."""
    return str(uuid4())


@pytest.fixture
def sample_masterplan_id():
    """Sample masterplan UUID."""
    return str(uuid4())


@pytest.fixture
def mock_validation_service():
    """Create mock ValidationService."""
    return MagicMock()


# ============================================================================
# POST /api/v2/validation/atom/{atom_id} Tests
# ============================================================================

def test_validate_atom_success(client, sample_atom_id, mock_validation_service):
    """Test successful atom validation."""
    mock_result = {
        "atom_id": sample_atom_id,
        "is_valid": True,
        "validation_score": 0.95,
        "issues": [],
        "metrics": {"complexity": 2, "lines_of_code": 15}
    }
    mock_validation_service.validate_atom.return_value = mock_result

    with patch('src.api.routers.validation.ValidationService', return_value=mock_validation_service):
        response = client.post(f"/api/v2/validation/atom/{sample_atom_id}")

    assert response.status_code == 200
    data = response.json()
    assert data['atom_id'] == sample_atom_id
    assert data['is_valid'] is True
    assert 'validation_score' in data


def test_validate_atom_with_issues(client, sample_atom_id, mock_validation_service):
    """Test atom validation with validation issues."""
    mock_result = {
        "atom_id": sample_atom_id,
        "is_valid": False,
        "validation_score": 0.60,
        "issues": [
            {"type": "syntax", "message": "Missing semicolon", "severity": "error"},
            {"type": "atomicity", "message": "Too complex", "severity": "warning"}
        ],
        "metrics": {}
    }
    mock_validation_service.validate_atom.return_value = mock_result

    with patch('src.api.routers.validation.ValidationService', return_value=mock_validation_service):
        response = client.post(f"/api/v2/validation/atom/{sample_atom_id}")

    data = response.json()
    assert data['is_valid'] is False
    assert len(data['issues']) == 2


def test_validate_atom_not_found(client, mock_validation_service):
    """Test validating non-existent atom."""
    atom_id = str(uuid4())
    mock_validation_service.validate_atom.side_effect = ValueError("Atom not found")

    with patch('src.api.routers.validation.ValidationService', return_value=mock_validation_service):
        response = client.post(f"/api/v2/validation/atom/{atom_id}")

    assert response.status_code == 404


def test_validate_atom_invalid_uuid(client):
    """Test atom validation with invalid UUID."""
    response = client.post("/api/v2/validation/atom/invalid-uuid")

    assert response.status_code == 400


# ============================================================================
# POST /api/v2/validation/task/{task_id} Tests
# ============================================================================

def test_validate_task_success(client, sample_task_id, mock_validation_service):
    """Test successful task validation."""
    mock_result = {
        "task_id": sample_task_id,
        "is_valid": True,
        "validation_score": 0.90,
        "atom_validations": [
            {"atom_id": str(uuid4()), "is_valid": True}
        ],
        "dependency_issues": [],
        "issues": []
    }
    mock_validation_service.validate_task.return_value = mock_result

    with patch('src.api.routers.validation.ValidationService', return_value=mock_validation_service):
        response = client.post(f"/api/v2/validation/task/{sample_task_id}")

    assert response.status_code == 200
    data = response.json()
    assert data['task_id'] == sample_task_id
    assert data['is_valid'] is True


def test_validate_task_with_dependency_issues(client, sample_task_id, mock_validation_service):
    """Test task validation with dependency issues."""
    mock_result = {
        "task_id": sample_task_id,
        "is_valid": False,
        "validation_score": 0.50,
        "atom_validations": [],
        "dependency_issues": [
            {"type": "circular", "message": "Circular dependency detected"}
        ],
        "issues": []
    }
    mock_validation_service.validate_task.return_value = mock_result

    with patch('src.api.routers.validation.ValidationService', return_value=mock_validation_service):
        response = client.post(f"/api/v2/validation/task/{sample_task_id}")

    data = response.json()
    assert data['is_valid'] is False
    assert len(data['dependency_issues']) == 1


def test_validate_task_not_found(client, mock_validation_service):
    """Test validating non-existent task."""
    task_id = str(uuid4())
    mock_validation_service.validate_task.side_effect = ValueError("Task not found")

    with patch('src.api.routers.validation.ValidationService', return_value=mock_validation_service):
        response = client.post(f"/api/v2/validation/task/{task_id}")

    assert response.status_code == 404


# ============================================================================
# POST /api/v2/validation/milestone/{milestone_id} Tests
# ============================================================================

def test_validate_milestone_success(client, sample_milestone_id, mock_validation_service):
    """Test successful milestone validation."""
    mock_result = {
        "milestone_id": sample_milestone_id,
        "is_valid": True,
        "validation_score": 0.92,
        "task_validations": [
            {"task_id": str(uuid4()), "is_valid": True}
        ],
        "issues": []
    }
    mock_validation_service.validate_milestone.return_value = mock_result

    with patch('src.api.routers.validation.ValidationService', return_value=mock_validation_service):
        response = client.post(f"/api/v2/validation/milestone/{sample_milestone_id}")

    assert response.status_code == 200
    data = response.json()
    assert data['milestone_id'] == sample_milestone_id
    assert data['is_valid'] is True


def test_validate_milestone_with_failed_tasks(client, sample_milestone_id, mock_validation_service):
    """Test milestone validation with failed tasks."""
    mock_result = {
        "milestone_id": sample_milestone_id,
        "is_valid": False,
        "validation_score": 0.65,
        "task_validations": [
            {"task_id": str(uuid4()), "is_valid": True},
            {"task_id": str(uuid4()), "is_valid": False, "issues": ["Syntax error"]}
        ],
        "issues": ["Not all tasks are valid"]
    }
    mock_validation_service.validate_milestone.return_value = mock_result

    with patch('src.api.routers.validation.ValidationService', return_value=mock_validation_service):
        response = client.post(f"/api/v2/validation/milestone/{sample_milestone_id}")

    data = response.json()
    assert data['is_valid'] is False
    assert len(data['task_validations']) == 2


# ============================================================================
# POST /api/v2/validation/masterplan/{masterplan_id} Tests
# ============================================================================

def test_validate_masterplan_success(client, sample_masterplan_id, mock_validation_service):
    """Test successful masterplan validation."""
    mock_result = {
        "masterplan_id": sample_masterplan_id,
        "is_valid": True,
        "validation_score": 0.95,
        "milestone_validations": [
            {"milestone_id": str(uuid4()), "is_valid": True}
        ],
        "overall_health": "excellent",
        "issues": []
    }
    mock_validation_service.validate_masterplan.return_value = mock_result

    with patch('src.api.routers.validation.ValidationService', return_value=mock_validation_service):
        response = client.post(f"/api/v2/validation/masterplan/{sample_masterplan_id}")

    assert response.status_code == 200
    data = response.json()
    assert data['masterplan_id'] == sample_masterplan_id
    assert data['is_valid'] is True
    assert data['overall_health'] == "excellent"


def test_validate_masterplan_with_issues(client, sample_masterplan_id, mock_validation_service):
    """Test masterplan validation with issues."""
    mock_result = {
        "masterplan_id": sample_masterplan_id,
        "is_valid": False,
        "validation_score": 0.55,
        "milestone_validations": [],
        "overall_health": "poor",
        "issues": ["Multiple milestones failed validation"]
    }
    mock_validation_service.validate_masterplan.return_value = mock_result

    with patch('src.api.routers.validation.ValidationService', return_value=mock_validation_service):
        response = client.post(f"/api/v2/validation/masterplan/{sample_masterplan_id}")

    data = response.json()
    assert data['is_valid'] is False
    assert data['overall_health'] == "poor"


# ============================================================================
# POST /api/v2/validation/hierarchical/{masterplan_id} Tests
# ============================================================================

def test_hierarchical_validation_success(client, sample_masterplan_id, mock_validation_service):
    """Test successful hierarchical validation."""
    mock_result = {
        "masterplan_id": sample_masterplan_id,
        "is_valid": True,
        "hierarchical_score": 0.93,
        "level_results": {
            "atomic": {"valid": 50, "invalid": 0},
            "task": {"valid": 12, "invalid": 0},
            "milestone": {"valid": 4, "invalid": 0},
            "masterplan": {"valid": True}
        },
        "issues": []
    }
    mock_validation_service.validate_hierarchical.return_value = mock_result

    with patch('src.api.routers.validation.ValidationService', return_value=mock_validation_service):
        response = client.post(f"/api/v2/validation/hierarchical/{sample_masterplan_id}")

    assert response.status_code == 200
    data = response.json()
    assert data['is_valid'] is True
    assert 'level_results' in data


def test_hierarchical_validation_with_levels(client, sample_masterplan_id, mock_validation_service):
    """Test hierarchical validation with specific levels."""
    mock_result = {
        "masterplan_id": sample_masterplan_id,
        "is_valid": True,
        "hierarchical_score": 0.90,
        "level_results": {
            "atomic": {"valid": 50, "invalid": 0},
            "task": {"valid": 12, "invalid": 0}
        },
        "issues": []
    }
    mock_validation_service.validate_hierarchical.return_value = mock_result

    with patch('src.api.routers.validation.ValidationService', return_value=mock_validation_service):
        response = client.post(
            f"/api/v2/validation/hierarchical/{sample_masterplan_id}",
            json={"levels": ["atomic", "task"]}
        )

    assert response.status_code == 200


def test_hierarchical_validation_cascading_failures(client, sample_masterplan_id, mock_validation_service):
    """Test hierarchical validation with cascading failures."""
    mock_result = {
        "masterplan_id": sample_masterplan_id,
        "is_valid": False,
        "hierarchical_score": 0.45,
        "level_results": {
            "atomic": {"valid": 45, "invalid": 5},
            "task": {"valid": 10, "invalid": 2},
            "milestone": {"valid": 3, "invalid": 1},
            "masterplan": {"valid": False}
        },
        "issues": ["Cascading validation failures detected"]
    }
    mock_validation_service.validate_hierarchical.return_value = mock_result

    with patch('src.api.routers.validation.ValidationService', return_value=mock_validation_service):
        response = client.post(f"/api/v2/validation/hierarchical/{sample_masterplan_id}")

    data = response.json()
    assert data['is_valid'] is False
    assert data['hierarchical_score'] < 0.5


# ============================================================================
# POST /api/v2/validation/batch/atoms Tests
# ============================================================================

def test_batch_validate_atoms_success(client, mock_validation_service):
    """Test successful batch atom validation."""
    atom_ids = [str(uuid4()), str(uuid4()), str(uuid4())]
    mock_result = {
        "total": 3,
        "valid": 3,
        "invalid": 0,
        "results": [
            {"atom_id": atom_ids[0], "is_valid": True},
            {"atom_id": atom_ids[1], "is_valid": True},
            {"atom_id": atom_ids[2], "is_valid": True}
        ]
    }
    mock_validation_service.batch_validate_atoms.return_value = mock_result

    with patch('src.api.routers.validation.ValidationService', return_value=mock_validation_service):
        response = client.post(
            "/api/v2/validation/batch/atoms",
            json={"atom_ids": atom_ids}
        )

    assert response.status_code == 200
    data = response.json()
    assert data['total'] == 3
    assert data['valid'] == 3


def test_batch_validate_atoms_mixed_results(client, mock_validation_service):
    """Test batch validation with mixed valid/invalid atoms."""
    atom_ids = [str(uuid4()), str(uuid4()), str(uuid4())]
    mock_result = {
        "total": 3,
        "valid": 2,
        "invalid": 1,
        "results": [
            {"atom_id": atom_ids[0], "is_valid": True},
            {"atom_id": atom_ids[1], "is_valid": False, "issues": ["Syntax error"]},
            {"atom_id": atom_ids[2], "is_valid": True}
        ]
    }
    mock_validation_service.batch_validate_atoms.return_value = mock_result

    with patch('src.api.routers.validation.ValidationService', return_value=mock_validation_service):
        response = client.post(
            "/api/v2/validation/batch/atoms",
            json={"atom_ids": atom_ids}
        )

    data = response.json()
    assert data['valid'] == 2
    assert data['invalid'] == 1


def test_batch_validate_atoms_empty_list(client):
    """Test batch validation with empty atom list."""
    response = client.post(
        "/api/v2/validation/batch/atoms",
        json={"atom_ids": []}
    )

    assert response.status_code == 422  # Validation error


def test_batch_validate_atoms_large_batch(client, mock_validation_service):
    """Test batch validation with large number of atoms."""
    atom_ids = [str(uuid4()) for _ in range(100)]
    mock_result = {
        "total": 100,
        "valid": 95,
        "invalid": 5,
        "results": [{"atom_id": aid, "is_valid": True} for aid in atom_ids]
    }
    mock_validation_service.batch_validate_atoms.return_value = mock_result

    with patch('src.api.routers.validation.ValidationService', return_value=mock_validation_service):
        response = client.post(
            "/api/v2/validation/batch/atoms",
            json={"atom_ids": atom_ids}
        )

    assert response.status_code == 200
    data = response.json()
    assert data['total'] == 100


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_validation_service_error(client, sample_atom_id, mock_validation_service):
    """Test handling of validation service errors."""
    mock_validation_service.validate_atom.side_effect = Exception("Service error")

    with patch('src.api.routers.validation.ValidationService', return_value=mock_validation_service):
        response = client.post(f"/api/v2/validation/atom/{sample_atom_id}")

    assert response.status_code == 500


def test_validation_database_error(client, sample_atom_id, mock_db):
    """Test handling of database errors."""
    mock_db.query.side_effect = Exception("Database connection failed")

    response = client.post(f"/api/v2/validation/atom/{sample_atom_id}")

    # Should handle gracefully
    assert response.status_code in [500, 503]


@pytest.mark.unit
class TestValidationModels:
    """Unit tests for validation request/response models."""

    def test_batch_validate_atoms_request(self):
        """Test BatchValidateAtomsRequest model."""
        from src.api.routers.validation import BatchValidateAtomsRequest

        request = BatchValidateAtomsRequest(atom_ids=["id1", "id2", "id3"])
        assert len(request.atom_ids) == 3

    def test_hierarchical_validation_request(self):
        """Test HierarchicalValidationRequest model."""
        from src.api.routers.validation import HierarchicalValidationRequest

        # With levels
        request1 = HierarchicalValidationRequest(levels=["atomic", "task"])
        assert len(request1.levels) == 2

        # Without levels (all levels)
        request2 = HierarchicalValidationRequest()
        assert request2.levels is None

