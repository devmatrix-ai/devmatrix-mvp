"""Project management routes."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from src.db import get_db
from src.models.user import User
from src.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from src.schemas.base import PaginatedResponse
from src.services.project_service import ProjectService
from src.services.task_service import TaskService
from src.services.activity_service import ActivityService
from src.security import get_current_user
from src.security.permissions import check_organization_access

router = APIRouter()
project_service = ProjectService()
task_service = TaskService()
activity_service = ActivityService()


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    project_in: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new project."""
    check_organization_access(current_user, project_in.organization_id)

    project = project_service.create(db, obj_in=project_in, organization_id=project_in.organization_id)

    activity_service.log_activity(
        db,
        organization_id=project_in.organization_id,
        user_id=current_user.id,
        entity_type="project",
        entity_id=project.id,
        action="created",
        after_state={"name": project.name},
    )

    return project


@router.get("", response_model=PaginatedResponse[ProjectRead])
def list_projects(
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List projects."""
    projects, total = project_service.read_all(
        db,
        organization_id=current_user.organization_id,
        skip=skip,
        limit=limit,
    )

    return {
        "items": projects,
        "total": total,
        "page": skip // limit + 1,
        "page_size": limit,
        "total_pages": (total + limit - 1) // limit,
    }


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific project."""
    project = project_service.read(db, id=project_id, organization_id=current_user.organization_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: str,
    project_in: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a project."""
    project = project_service.read(db, id=project_id, organization_id=current_user.organization_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    updated_project = project_service.update(
        db,
        id=project_id,
        organization_id=current_user.organization_id,
        obj_in=project_in,
    )

    activity_service.log_activity(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        entity_type="project",
        entity_id=project_id,
        action="updated",
    )

    return updated_project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a project."""
    result = project_service.delete(db, id=project_id, organization_id=current_user.organization_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    activity_service.log_activity(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        entity_type="project",
        entity_id=project_id,
        action="deleted",
    )


@router.get("/{project_id}/tasks", response_model=PaginatedResponse)
def get_project_tasks(
    project_id: str,
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get all tasks in a project."""
    project = project_service.read(db, id=project_id, organization_id=current_user.organization_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    tasks, total = task_service.get_tasks_by_project(
        db,
        organization_id=current_user.organization_id,
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
