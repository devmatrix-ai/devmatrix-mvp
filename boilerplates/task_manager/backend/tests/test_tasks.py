"""Tests for task management endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.schemas.task import TaskCreate
from src.services.task_service import TaskService

client = TestClient(app)


def test_create_task(test_user_token, test_user, organization_id):
    """Test creating a task."""
    response = client.post(
        "/api/v1/tasks",
        json={
            "name": "New Task",
            "description": "A new task to test",
            "status": "todo",
            "priority": "high",
            "organization_id": organization_id,
            "user_id": test_user.id,
        },
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Task"
    assert data["status"] == "todo"
    assert data["priority"] == "high"


def test_list_tasks(test_task, test_user_token, test_user):
    """Test listing tasks."""
    response = client.get(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1


def test_get_task(test_task, test_user_token, test_user):
    """Test getting a specific task."""
    response = client.get(
        f"/api/v1/tasks/{test_task.id}",
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_task.id
    assert data["name"] == test_task.name


def test_get_nonexistent_task(test_user_token):
    """Test getting a non-existent task."""
    response = client.get(
        "/api/v1/tasks/nonexistent",
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 404


def test_update_task(test_task, test_user_token, test_user):
    """Test updating a task."""
    response = client.put(
        f"/api/v1/tasks/{test_task.id}",
        json={"name": "Updated Task", "priority": "critical"},
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Task"
    assert data["priority"] == "critical"


def test_delete_task(test_task, test_user_token):
    """Test deleting a task."""
    response = client.delete(
        f"/api/v1/tasks/{test_task.id}",
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 204

    # Verify task is soft deleted
    response = client.get(
        f"/api/v1/tasks/{test_task.id}",
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 404


def test_update_task_status(test_task, test_user_token):
    """Test updating task status."""
    response = client.patch(
        f"/api/v1/tasks/{test_task.id}/status",
        json={"status": "in_progress"},
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "in_progress"


def test_bulk_update_status(test_task, test_user_token, test_user, organization_id, db_session):
    """Test bulk updating task statuses."""
    # Create another task
    task_service = TaskService()
    from src.schemas.task import TaskCreate

    task_data = TaskCreate(
        name="Another Task",
        status="todo",
        priority="low",
        user_id=test_user.id,
        organization_id=organization_id,
    )
    another_task = task_service.create_task(db_session, obj_in=task_data)

    response = client.post(
        "/api/v1/tasks/bulk/status",
        json={
            "task_ids": [test_task.id, another_task.id],
            "status": "done",
        },
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["updated"] == 2


def test_search_tasks_by_status(test_task, test_user_token):
    """Test searching tasks by status."""
    response = client.get(
        "/api/v1/tasks?status=todo",
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert all(item["status"] == "todo" for item in data["items"])


def test_search_tasks_by_priority(test_task, test_user_token):
    """Test searching tasks by priority."""
    response = client.get(
        "/api/v1/tasks?priority=medium",
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 200


def test_list_tasks_pagination(test_user_token):
    """Test task pagination."""
    response = client.get(
        "/api/v1/tasks?skip=0&limit=10",
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data
