"""Tests for project management endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_create_project(test_user_token, test_user, organization_id):
    """Test creating a project."""
    response = client.post(
        "/api/v1/projects",
        json={
            "name": "New Project",
            "description": "A new project",
            "owner_id": test_user.id,
            "organization_id": organization_id,
        },
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Project"
    assert data["owner_id"] == test_user.id


def test_list_projects(test_project, test_user_token):
    """Test listing projects."""
    response = client.get(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1


def test_get_project(test_project, test_user_token):
    """Test getting a specific project."""
    response = client.get(
        f"/api/v1/projects/{test_project.id}",
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_project.id
    assert data["name"] == test_project.name


def test_get_nonexistent_project(test_user_token):
    """Test getting a non-existent project."""
    response = client.get(
        "/api/v1/projects/nonexistent",
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 404


def test_update_project(test_project, test_user_token):
    """Test updating a project."""
    response = client.put(
        f"/api/v1/projects/{test_project.id}",
        json={"name": "Updated Project", "description": "Updated description"},
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Project"
    assert data["description"] == "Updated description"


def test_delete_project(test_project, test_user_token):
    """Test deleting a project."""
    response = client.delete(
        f"/api/v1/projects/{test_project.id}",
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 204

    # Verify project is soft deleted
    response = client.get(
        f"/api/v1/projects/{test_project.id}",
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 404


def test_get_project_tasks(test_project, test_task, test_user_token):
    """Test getting tasks in a project."""
    response = client.get(
        f"/api/v1/projects/{test_project.id}/tasks",
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1
    assert any(item["id"] == test_task.id for item in data["items"])


def test_list_projects_pagination(test_user_token):
    """Test project pagination."""
    response = client.get(
        "/api/v1/projects?skip=0&limit=10",
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data
