"""
Smoke tests for API - verify basic functionality works.
"""

import pytest


@pytest.mark.asyncio
async def test_root_endpoint(client):
    """Test root endpoint returns API info."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Devmatrix API"
    assert data["status"] == "operational"


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Test health check endpoint."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "components" in data


@pytest.mark.asyncio
async def test_create_and_list_workflow(client):
    """Test creating and listing workflows."""
    # Create workflow
    workflow_data = {
        "name": "Test Workflow",
        "tasks": [
            {
                "task_id": "task1",
                "agent_type": "test",
                "prompt": "test prompt",
            }
        ],
    }

    create_response = await client.post("/api/v1/workflows", json=workflow_data)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "Test Workflow"
    workflow_id = created["workflow_id"]

    # List workflows
    list_response = await client.get("/api/v1/workflows")
    assert list_response.status_code == 200
    workflows = list_response.json()
    assert len(workflows) == 1
    assert workflows[0]["workflow_id"] == workflow_id


@pytest.mark.asyncio
async def test_get_workflow(client):
    """Test getting a specific workflow."""
    # Create workflow
    create_response = await client.post(
        "/api/v1/workflows",
        json={
            "name": "Test",
            "tasks": [{"task_id": "t1", "agent_type": "test", "prompt": "test"}],
        },
    )
    workflow_id = create_response.json()["workflow_id"]

    # Get workflow
    response = await client.get(f"/api/v1/workflows/{workflow_id}")
    assert response.status_code == 200
    assert response.json()["workflow_id"] == workflow_id


@pytest.mark.asyncio
async def test_update_workflow(client):
    """Test updating a workflow."""
    # Create workflow
    create_response = await client.post(
        "/api/v1/workflows",
        json={
            "name": "Original",
            "tasks": [{"task_id": "t1", "agent_type": "test", "prompt": "test"}],
        },
    )
    workflow_id = create_response.json()["workflow_id"]

    # Update workflow
    response = await client.put(
        f"/api/v1/workflows/{workflow_id}",
        json={"name": "Updated"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated"


@pytest.mark.asyncio
async def test_delete_workflow(client):
    """Test deleting a workflow."""
    # Create workflow
    create_response = await client.post(
        "/api/v1/workflows",
        json={
            "name": "Test",
            "tasks": [{"task_id": "t1", "agent_type": "test", "prompt": "test"}],
        },
    )
    workflow_id = create_response.json()["workflow_id"]

    # Delete workflow
    response = await client.delete(f"/api/v1/workflows/{workflow_id}")
    assert response.status_code == 204

    # Verify deleted
    response = await client.get(f"/api/v1/workflows/{workflow_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_execution(client):
    """Test creating an execution."""
    # Create workflow first
    wf_response = await client.post(
        "/api/v1/workflows",
        json={
            "name": "Test",
            "tasks": [{"task_id": "t1", "agent_type": "test", "prompt": "test"}],
        },
    )
    workflow_id = wf_response.json()["workflow_id"]

    # Create execution
    response = await client.post(
        "/api/v1/executions",
        json={
            "workflow_id": workflow_id,
            "input_data": {"key": "value"},
            "priority": 5,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["workflow_id"] == workflow_id
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_list_executions(client):
    """Test listing executions."""
    # Create workflow
    wf_response = await client.post(
        "/api/v1/workflows",
        json={
            "name": "Test",
            "tasks": [{"task_id": "t1", "agent_type": "test", "prompt": "test"}],
        },
    )
    workflow_id = wf_response.json()["workflow_id"]

    # Create execution
    await client.post(
        "/api/v1/executions",
        json={"workflow_id": workflow_id, "input_data": {}, "priority": 5},
    )

    # List executions
    response = await client.get("/api/v1/executions")
    assert response.status_code == 200
    executions = response.json()
    assert len(executions) >= 1


@pytest.mark.asyncio
async def test_metrics_summary(client):
    """Test metrics summary endpoint."""
    response = await client.get("/api/v1/metrics/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_workflows" in data
    assert "total_executions" in data


@pytest.mark.asyncio
async def test_openapi_docs(client):
    """Test OpenAPI documentation endpoint."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert data["info"]["title"] == "Devmatrix API"
