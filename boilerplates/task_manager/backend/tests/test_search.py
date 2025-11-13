"""Tests for search and filtering functionality."""

import pytest
from sqlalchemy.orm import Session

from src.models.task import Task
from src.schemas.task import TaskCreate
from src.services.task_service import TaskService
from src.services.search_service import SearchService


def test_search_tasks_by_name(db_session, test_user, organization_id):
    """Test searching tasks by name."""
    task_service = TaskService()

    # Create tasks with different names
    task1_data = TaskCreate(
        name="Design Homepage",
        status="todo",
        priority="high",
        user_id=test_user.id,
        organization_id=organization_id,
    )
    task1 = task_service.create_task(db_session, obj_in=task1_data)

    task2_data = TaskCreate(
        name="Implement Authentication",
        status="in_progress",
        priority="medium",
        user_id=test_user.id,
        organization_id=organization_id,
    )
    task2 = task_service.create_task(db_session, obj_in=task2_data)

    # Search for "Design"
    results, total = SearchService.search_tasks(
        db_session,
        organization_id=organization_id,
        query="Design",
    )

    assert total >= 1
    assert any(t.id == task1.id for t in results)


def test_search_tasks_by_description(db_session, test_user, organization_id):
    """Test searching tasks by description."""
    task_service = TaskService()

    task_data = TaskCreate(
        name="Task with Description",
        description="This is a task about database optimization",
        status="todo",
        priority="medium",
        user_id=test_user.id,
        organization_id=organization_id,
    )
    task = task_service.create_task(db_session, obj_in=task_data)

    results, total = SearchService.search_tasks(
        db_session,
        organization_id=organization_id,
        query="database",
    )

    assert total >= 1
    assert any(t.id == task.id for t in results)


def test_filter_by_status(db_session, test_user, organization_id):
    """Test filtering tasks by status."""
    task_service = TaskService()

    # Create tasks with different statuses
    for status in ["todo", "in_progress", "done"]:
        task_data = TaskCreate(
            name=f"Task {status}",
            status=status,
            priority="medium",
            user_id=test_user.id,
            organization_id=organization_id,
        )
        task_service.create_task(db_session, obj_in=task_data)

    # Filter by status
    results, total = SearchService.search_tasks(
        db_session,
        organization_id=organization_id,
        status="done",
    )

    assert total >= 1
    assert all(t.status == "done" for t in results)


def test_filter_by_priority(db_session, test_user, organization_id):
    """Test filtering tasks by priority."""
    task_service = TaskService()

    task_data = TaskCreate(
        name="Critical Task",
        status="todo",
        priority="critical",
        user_id=test_user.id,
        organization_id=organization_id,
    )
    task = task_service.create_task(db_session, obj_in=task_data)

    results, total = SearchService.search_tasks(
        db_session,
        organization_id=organization_id,
        priority="critical",
    )

    assert total >= 1
    assert any(t.id == task.id for t in results)


def test_filter_by_project(db_session, test_task, test_project):
    """Test filtering tasks by project."""
    results, total = SearchService.search_tasks(
        db_session,
        organization_id=test_project.organization_id,
        project_id=test_project.id,
    )

    assert total >= 1
    assert any(t.id == test_task.id for t in results)


def test_search_with_pagination(db_session, test_user, organization_id):
    """Test search results pagination."""
    task_service = TaskService()

    # Create multiple tasks
    for i in range(5):
        task_data = TaskCreate(
            name=f"Task {i}",
            status="todo",
            priority="medium",
            user_id=test_user.id,
            organization_id=organization_id,
        )
        task_service.create_task(db_session, obj_in=task_data)

    # Get first page
    results1, total1 = SearchService.search_tasks(
        db_session,
        organization_id=organization_id,
        skip=0,
        limit=2,
    )

    # Get second page
    results2, total2 = SearchService.search_tasks(
        db_session,
        organization_id=organization_id,
        skip=2,
        limit=2,
    )

    assert len(results1) <= 2
    assert len(results2) <= 2
    assert total1 == total2  # Total should be the same


def test_search_combined_filters(db_session, test_user, organization_id, test_project):
    """Test searching with multiple filters combined."""
    task_service = TaskService()

    task_data = TaskCreate(
        name="Critical Urgent Task",
        status="in_progress",
        priority="high",
        project_id=test_project.id,
        user_id=test_user.id,
        organization_id=organization_id,
    )
    task = task_service.create_task(db_session, obj_in=task_data)

    results, total = SearchService.search_tasks(
        db_session,
        organization_id=organization_id,
        query="Critical",
        status="in_progress",
        priority="high",
        project_id=test_project.id,
    )

    assert total >= 1
    assert any(t.id == task.id for t in results)
