"""
Tests for Workflows API Router

Tests CRUD operations for workflow definitions.

Author: DevMatrix Team
Date: 2025-11-03
"""

import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routers.workflows import router


@pytest.fixture
def client():
    """Create test client with workflows router."""
    test_app = FastAPI()
    test_app.include_router(router)
    return TestClient(test_app)


@pytest.fixture
def sample_workflow_id():
    """Sample workflow ID."""
    return f"wf_{uuid4()}"


@pytest.fixture
def sample_task_definition():
    """Sample task definition."""
    return {
        "task_id": "task_1",
        "agent_type": "implementation",
        "prompt": "Implement user authentication",
        "dependencies": [],
        "max_retries": 3,
        "timeout": 300
    }


@pytest.fixture
def sample_workflow_data(sample_task_definition):
    """Sample workflow creation data."""
    return {
        "name": "Test Workflow",
        "description": "A test workflow",
        "tasks": [sample_task_definition],
        "metadata": {"project": "test"}
    }


@pytest.fixture
def sample_workflow(sample_workflow_id, sample_workflow_data):
    """Sample workflow object."""
    return {
        "workflow_id": sample_workflow_id,
        "name": sample_workflow_data["name"],
        "description": sample_workflow_data["description"],
        "tasks": sample_workflow_data["tasks"],
        "metadata": sample_workflow_data["metadata"],
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }


# ============================================================================
# POST /workflows Tests
# ============================================================================

def test_create_workflow_success(client, sample_workflow_data):
    """Test successful workflow creation."""
    with patch('src.api.routers.workflows.workflows_db', {}):
        response = client.post(
            "/workflows",
            json=sample_workflow_data
        )

    assert response.status_code == 201
    data = response.json()
    assert 'workflow_id' in data
    assert data['name'] == sample_workflow_data['name']
    assert len(data['tasks']) == 1


def test_create_workflow_minimal(client):
    """Test workflow creation with minimal data."""
    minimal_workflow = {
        "name": "Minimal Workflow",
        "tasks": [
            {
                "task_id": "task_1",
                "agent_type": "planning",
                "prompt": "Create a plan"
            }
        ]
    }

    with patch('src.api.routers.workflows.workflows_db', {}):
        response = client.post("/workflows", json=minimal_workflow)

    assert response.status_code == 201
    data = response.json()
    assert data['description'] is None
    assert data['metadata'] == {}


def test_create_workflow_multiple_tasks(client):
    """Test workflow creation with multiple tasks."""
    workflow = {
        "name": "Multi-Task Workflow",
        "tasks": [
            {
                "task_id": "task_1",
                "agent_type": "planning",
                "prompt": "Plan",
                "dependencies": []
            },
            {
                "task_id": "task_2",
                "agent_type": "implementation",
                "prompt": "Implement",
                "dependencies": ["task_1"]
            },
            {
                "task_id": "task_3",
                "agent_type": "testing",
                "prompt": "Test",
                "dependencies": ["task_2"]
            }
        ]
    }

    with patch('src.api.routers.workflows.workflows_db', {}):
        response = client.post("/workflows", json=workflow)

    assert response.status_code == 201
    data = response.json()
    assert len(data['tasks']) == 3
    assert data['tasks'][1]['dependencies'] == ["task_1"]


def test_create_workflow_invalid_name_empty(client):
    """Test workflow creation with empty name."""
    workflow = {
        "name": "",
        "tasks": [
            {
                "task_id": "task_1",
                "agent_type": "planning",
                "prompt": "Plan"
            }
        ]
    }

    response = client.post("/workflows", json=workflow)
    assert response.status_code == 422  # Validation error


def test_create_workflow_invalid_name_too_long(client):
    """Test workflow creation with name exceeding max length."""
    workflow = {
        "name": "A" * 101,  # Max is 100
        "tasks": [
            {
                "task_id": "task_1",
                "agent_type": "planning",
                "prompt": "Plan"
            }
        ]
    }

    response = client.post("/workflows", json=workflow)
    assert response.status_code == 422


def test_create_workflow_no_tasks(client):
    """Test workflow creation without tasks."""
    workflow = {
        "name": "No Tasks Workflow",
        "tasks": []
    }

    response = client.post("/workflows", json=workflow)
    assert response.status_code == 422  # min_items=1 validation


def test_create_workflow_invalid_timeout(client):
    """Test workflow creation with invalid timeout."""
    workflow = {
        "name": "Invalid Timeout",
        "tasks": [
            {
                "task_id": "task_1",
                "agent_type": "planning",
                "prompt": "Plan",
                "timeout": 10000  # Exceeds MAX_TIMEOUT
            }
        ]
    }

    response = client.post("/workflows", json=workflow)
    assert response.status_code == 422


def test_create_workflow_invalid_max_retries(client):
    """Test workflow creation with invalid max_retries."""
    workflow = {
        "name": "Invalid Retries",
        "tasks": [
            {
                "task_id": "task_1",
                "agent_type": "planning",
                "prompt": "Plan",
                "max_retries": 20  # Max is 10
            }
        ]
    }

    response = client.post("/workflows", json=workflow)
    assert response.status_code == 422


# ============================================================================
# GET /workflows Tests
# ============================================================================

def test_list_workflows_success(client, sample_workflow):
    """Test successful workflow listing."""
    mock_db = {sample_workflow['workflow_id']: sample_workflow}

    with patch('src.api.routers.workflows.workflows_db', mock_db):
        response = client.get("/workflows")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]['workflow_id'] == sample_workflow['workflow_id']


def test_list_workflows_empty(client):
    """Test workflow listing with no workflows."""
    with patch('src.api.routers.workflows.workflows_db', {}):
        response = client.get("/workflows")

    assert response.status_code == 200
    assert response.json() == []


def test_list_workflows_multiple(client):
    """Test workflow listing with multiple workflows."""
    workflows = {}
    for i in range(5):
        wf_id = f"wf_{i}"
        workflows[wf_id] = {
            "workflow_id": wf_id,
            "name": f"Workflow {i}",
            "description": f"Description {i}",
            "tasks": [],
            "metadata": {},
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

    with patch('src.api.routers.workflows.workflows_db', workflows):
        response = client.get("/workflows")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5


# ============================================================================
# GET /workflows/{workflow_id} Tests
# ============================================================================

def test_get_workflow_success(client, sample_workflow):
    """Test successful workflow retrieval."""
    wf_id = sample_workflow['workflow_id']
    mock_db = {wf_id: sample_workflow}

    with patch('src.api.routers.workflows.workflows_db', mock_db):
        response = client.get(f"/workflows/{wf_id}")

    assert response.status_code == 200
    data = response.json()
    assert data['workflow_id'] == wf_id
    assert data['name'] == sample_workflow['name']


def test_get_workflow_not_found(client):
    """Test getting non-existent workflow."""
    wf_id = "wf_nonexistent"

    with patch('src.api.routers.workflows.workflows_db', {}):
        response = client.get(f"/workflows/{wf_id}")

    assert response.status_code == 404
    assert "not found" in response.json()['detail'].lower()


def test_get_workflow_with_tasks(client, sample_workflow):
    """Test workflow retrieval includes tasks."""
    wf_id = sample_workflow['workflow_id']
    sample_workflow['tasks'] = [
        {
            "task_id": "task_1",
            "agent_type": "planning",
            "prompt": "Plan",
            "dependencies": [],
            "max_retries": 3,
            "timeout": 300
        },
        {
            "task_id": "task_2",
            "agent_type": "implementation",
            "prompt": "Implement",
            "dependencies": ["task_1"],
            "max_retries": 3,
            "timeout": 600
        }
    ]

    mock_db = {wf_id: sample_workflow}

    with patch('src.api.routers.workflows.workflows_db', mock_db):
        response = client.get(f"/workflows/{wf_id}")

    data = response.json()
    assert len(data['tasks']) == 2
    assert data['tasks'][0]['task_id'] == "task_1"
    assert data['tasks'][1]['dependencies'] == ["task_1"]


# ============================================================================
# PUT /workflows/{workflow_id} Tests
# ============================================================================

def test_update_workflow_name(client, sample_workflow):
    """Test workflow name update."""
    wf_id = sample_workflow['workflow_id']
    mock_db = {wf_id: sample_workflow}

    with patch('src.api.routers.workflows.workflows_db', mock_db):
        response = client.put(
            f"/workflows/{wf_id}",
            json={"name": "Updated Workflow Name"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data['name'] == "Updated Workflow Name"


def test_update_workflow_description(client, sample_workflow):
    """Test workflow description update."""
    wf_id = sample_workflow['workflow_id']
    mock_db = {wf_id: sample_workflow}

    with patch('src.api.routers.workflows.workflows_db', mock_db):
        response = client.put(
            f"/workflows/{wf_id}",
            json={"description": "New description"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data['description'] == "New description"


def test_update_workflow_tasks(client, sample_workflow):
    """Test workflow tasks update."""
    wf_id = sample_workflow['workflow_id']
    mock_db = {wf_id: sample_workflow}

    new_tasks = [
        {
            "task_id": "new_task_1",
            "agent_type": "documentation",
            "prompt": "Document the code",
            "dependencies": []
        }
    ]

    with patch('src.api.routers.workflows.workflows_db', mock_db):
        response = client.put(
            f"/workflows/{wf_id}",
            json={"tasks": new_tasks}
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data['tasks']) == 1
    assert data['tasks'][0]['agent_type'] == "documentation"


def test_update_workflow_metadata(client, sample_workflow):
    """Test workflow metadata update."""
    wf_id = sample_workflow['workflow_id']
    mock_db = {wf_id: sample_workflow}

    with patch('src.api.routers.workflows.workflows_db', mock_db):
        response = client.put(
            f"/workflows/{wf_id}",
            json={"metadata": {"version": "2.0", "author": "test"}}
        )

    assert response.status_code == 200
    data = response.json()
    assert data['metadata']['version'] == "2.0"


def test_update_workflow_multiple_fields(client, sample_workflow):
    """Test updating multiple workflow fields."""
    wf_id = sample_workflow['workflow_id']
    mock_db = {wf_id: sample_workflow}

    with patch('src.api.routers.workflows.workflows_db', mock_db):
        response = client.put(
            f"/workflows/{wf_id}",
            json={
                "name": "New Name",
                "description": "New Description",
                "metadata": {"updated": True}
            }
        )

    assert response.status_code == 200
    data = response.json()
    assert data['name'] == "New Name"
    assert data['description'] == "New Description"
    assert data['metadata']['updated'] is True


def test_update_workflow_not_found(client):
    """Test updating non-existent workflow."""
    wf_id = "wf_nonexistent"

    with patch('src.api.routers.workflows.workflows_db', {}):
        response = client.put(
            f"/workflows/{wf_id}",
            json={"name": "Updated"}
        )

    assert response.status_code == 404


def test_update_workflow_empty_update(client, sample_workflow):
    """Test updating workflow with no changes."""
    wf_id = sample_workflow['workflow_id']
    mock_db = {wf_id: sample_workflow}

    with patch('src.api.routers.workflows.workflows_db', mock_db):
        response = client.put(f"/workflows/{wf_id}", json={})

    assert response.status_code == 400
    assert "No fields to update" in response.json()['detail']


# ============================================================================
# DELETE /workflows/{workflow_id} Tests
# ============================================================================

def test_delete_workflow_success(client, sample_workflow):
    """Test successful workflow deletion."""
    wf_id = sample_workflow['workflow_id']
    mock_db = {wf_id: sample_workflow}

    with patch('src.api.routers.workflows.workflows_db', mock_db):
        response = client.delete(f"/workflows/{wf_id}")

    assert response.status_code == 204


def test_delete_workflow_not_found(client):
    """Test deleting non-existent workflow."""
    wf_id = "wf_nonexistent"

    with patch('src.api.routers.workflows.workflows_db', {}):
        response = client.delete(f"/workflows/{wf_id}")

    assert response.status_code == 404


def test_delete_workflow_idempotent(client, sample_workflow):
    """Test workflow deletion is not idempotent (second delete fails)."""
    wf_id = sample_workflow['workflow_id']
    mock_db = {wf_id: sample_workflow}

    with patch('src.api.routers.workflows.workflows_db', mock_db):
        # First delete succeeds
        response1 = client.delete(f"/workflows/{wf_id}")
        assert response1.status_code == 204

        # Second delete fails (workflow already removed from DB)
        response2 = client.delete(f"/workflows/{wf_id}")
        assert response2.status_code == 404


# ============================================================================
# Unit Tests for Models
# ============================================================================

@pytest.mark.unit
class TestWorkflowsModels:
    """Unit tests for workflows models."""

    def test_task_definition_model(self):
        """Test TaskDefinition model."""
        from src.api.routers.workflows import TaskDefinition

        task = TaskDefinition(
            task_id="task_1",
            agent_type="planning",
            prompt="Create a plan",
            dependencies=["task_0"],
            max_retries=5,
            timeout=600
        )

        assert task.task_id == "task_1"
        assert task.agent_type == "planning"
        assert task.dependencies == ["task_0"]

    def test_task_definition_defaults(self):
        """Test TaskDefinition default values."""
        from src.api.routers.workflows import TaskDefinition

        task = TaskDefinition(
            task_id="task_1",
            agent_type="planning",
            prompt="Plan"
        )

        assert task.dependencies == []
        assert task.max_retries > 0
        assert task.timeout > 0

    def test_workflow_create_model(self):
        """Test WorkflowCreate model."""
        from src.api.routers.workflows import WorkflowCreate, TaskDefinition

        workflow = WorkflowCreate(
            name="Test Workflow",
            description="A test",
            tasks=[
                TaskDefinition(
                    task_id="task_1",
                    agent_type="planning",
                    prompt="Plan"
                )
            ],
            metadata={"key": "value"}
        )

        assert workflow.name == "Test Workflow"
        assert len(workflow.tasks) == 1

    def test_workflow_update_model(self):
        """Test WorkflowUpdate model with optional fields."""
        from src.api.routers.workflows import WorkflowUpdate

        # All fields optional
        update = WorkflowUpdate()
        assert update.name is None
        assert update.description is None
        assert update.tasks is None

        # With some fields
        update2 = WorkflowUpdate(name="New Name")
        assert update2.name == "New Name"
        assert update2.description is None

