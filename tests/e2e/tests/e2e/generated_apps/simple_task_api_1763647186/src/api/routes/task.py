"""
FastAPI CRUD Routes for Task

Auto-generated CRUD endpoints with:
- Repository pattern integration
- Service layer architecture
- Proper error handling
- Pydantic validation
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.schemas import TaskCreate, TaskUpdate, TaskResponse
from src.services.task_service import TaskService

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
)


@router.get("/", response_model=List[TaskResponse])
async def get_all_tasks(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get all tasks with pagination."""
    service = TaskService(db)
    tasks = await service.get_all(skip=skip, limit=limit)
    return tasks


@router.get("/{{id}}", response_model=TaskResponse)
async def get_task_by_id(
    id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get task by ID."""
    service = TaskService(db)
    task = await service.get_by_id(id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {{id}} not found"
        )

    return task


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new task."""
    service = TaskService(db)
    task = await service.create(task_data)
    return task


@router.put("/{{id}}", response_model=TaskResponse)
async def update_task(
    id: str,
    task_data: TaskUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing task."""
    service = TaskService(db)
    task = await service.update(id, task_data)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {{id}} not found"
        )

    return task


@router.delete("/{{id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a task by ID."""
    service = TaskService(db)
    success = await service.delete(id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {{id}} not found"
        )

    return None