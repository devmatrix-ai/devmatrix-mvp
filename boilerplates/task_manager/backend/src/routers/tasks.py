"""Task management routes."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from src.db import get_db
from src.models.user import User
from src.models.task import Task
from src.schemas.task import TaskCreate, TaskRead, TaskUpdate, TaskStatusChange, BulkTaskStatusChange
from src.schemas.base import PaginatedResponse
from src.services.task_service import TaskService
from src.services.search_service import SearchService
from src.services.activity_service import ActivityService
from src.security import get_current_user
from src.security.permissions import check_organization_access

router = APIRouter()
task_service = TaskService()
activity_service = ActivityService()


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    task_in: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new task."""
    check_organization_access(current_user, task_in.organization_id)

    task = task_service.create_task(db, obj_in=task_in)

    activity_service.log_activity(
        db,
        organization_id=task_in.organization_id,
        user_id=current_user.id,
        entity_type="task",
        entity_id=task.id,
        action="created",
        after_state={"name": task.name, "status": task.status},
    )

    return task


@router.get("", response_model=PaginatedResponse[TaskRead])
def list_tasks(
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: str = Query(None),
    priority: str = Query(None),
    project_id: str = Query(None),
    db: Session = Depends(get_db),
):
    """List tasks with optional filters."""
    tasks, total = SearchService.search_tasks(
        db,
        organization_id=current_user.organization_id,
        status=status,
        priority=priority,
        project_id=project_id,
        skip=skip,
        limit=limit,
    )

    return {
        "items": tasks,
        "total": total,
        "page": skip // limit + 1,
        "page_size": limit,
        "total_pages": (total + limit - 1) // limit,
    }


@router.get("/{task_id}", response_model=TaskRead)
def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific task."""
    task = task_service.read(db, id=task_id, organization_id=current_user.organization_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: str,
    task_in: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a task."""
    task = task_service.read(db, id=task_id, organization_id=current_user.organization_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    updated_task = task_service.update(
        db,
        id=task_id,
        organization_id=current_user.organization_id,
        obj_in=task_in,
    )

    activity_service.log_activity(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        entity_type="task",
        entity_id=task_id,
        action="updated",
        before_state={"name": task.name},
        after_state={"name": updated_task.name},
    )

    return updated_task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a task."""
    result = task_service.delete(db, id=task_id, organization_id=current_user.organization_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    activity_service.log_activity(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        entity_type="task",
        entity_id=task_id,
        action="deleted",
    )


@router.patch("/{task_id}/status", response_model=TaskRead)
def update_task_status(
    task_id: str,
    status_update: TaskStatusChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update task status."""
    task = task_service.read(db, id=task_id, organization_id=current_user.organization_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    updated_task = task_service.update_task_status(
        db,
        task_id=task_id,
        organization_id=current_user.organization_id,
        status=status_update.status,
    )

    activity_service.log_activity(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        entity_type="task",
        entity_id=task_id,
        action="status_changed",
        before_state={"status": task.status},
        after_state={"status": status_update.status},
    )

    return updated_task


@router.post("/bulk/status", status_code=status.HTTP_200_OK)
def bulk_update_status(
    bulk_update: BulkTaskStatusChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Bulk update task statuses."""
    count = task_service.bulk_update_status(
        db,
        organization_id=current_user.organization_id,
        task_ids=bulk_update.task_ids,
        status=bulk_update.status,
    )

    activity_service.log_activity(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        entity_type="task",
        entity_id="bulk",
        action="bulk_status_change",
        after_state={"count": count, "status": bulk_update.status},
    )

    return {"updated": count}
