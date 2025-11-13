"""Task service for task management."""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional, Tuple
from datetime import datetime

from src.models.task import Task
from src.schemas.task import TaskCreate, TaskUpdate
from .base_crud import BaseCRUDService


class TaskService(BaseCRUDService[Task, TaskCreate, TaskUpdate]):
    """Service for task operations."""

    def __init__(self):
        super().__init__(Task)

    def create_task(self, db: Session, *, obj_in: TaskCreate) -> Task:
        """Create a new task."""
        task_data = obj_in.dict(exclude_unset=True)
        task = Task(**task_data)
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def get_tasks_by_project(
        self,
        db: Session,
        *,
        organization_id: str,
        project_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Task], int]:
        """Get all tasks in a project."""
        query = db.query(Task).filter(
            and_(
                Task.organization_id == organization_id,
                Task.project_id == project_id,
                Task.is_deleted == False,
            )
        )
        total = query.count()
        tasks = query.offset(skip).limit(limit).all()
        return tasks, total

    def get_tasks_by_assignee(
        self,
        db: Session,
        *,
        organization_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Task], int]:
        """Get all tasks assigned to a user."""
        query = db.query(Task).filter(
            and_(
                Task.organization_id == organization_id,
                Task.assigned_to == user_id,
                Task.is_deleted == False,
            )
        )
        total = query.count()
        tasks = query.offset(skip).limit(limit).all()
        return tasks, total

    def get_tasks_by_status(
        self,
        db: Session,
        *,
        organization_id: str,
        status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Task], int]:
        """Get all tasks with a specific status."""
        query = db.query(Task).filter(
            and_(
                Task.organization_id == organization_id,
                Task.status == status,
                Task.is_deleted == False,
            )
        )
        total = query.count()
        tasks = query.offset(skip).limit(limit).all()
        return tasks, total

    def update_task_status(
        self,
        db: Session,
        *,
        task_id: str,
        organization_id: str,
        status: str,
    ) -> Optional[Task]:
        """Update task status."""
        task = self.read(db, id=task_id, organization_id=organization_id)
        if not task:
            return None

        task.status = status
        task.updated_at = datetime.utcnow()
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def bulk_update_status(
        self,
        db: Session,
        *,
        organization_id: str,
        task_ids: List[str],
        status: str,
    ) -> int:
        """Bulk update task status."""
        count = db.query(Task).filter(
            and_(
                Task.organization_id == organization_id,
                Task.id.in_(task_ids),
                Task.is_deleted == False,
            )
        ).update(
            {Task.status: status, Task.updated_at: datetime.utcnow()},
            synchronize_session=False,
        )
        db.commit()
        return count

    def get_overdue_tasks(
        self,
        db: Session,
        *,
        organization_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Task], int]:
        """Get tasks that are overdue."""
        query = db.query(Task).filter(
            and_(
                Task.organization_id == organization_id,
                Task.due_date < datetime.utcnow(),
                Task.status != "done",
                Task.is_deleted == False,
            )
        )
        total = query.count()
        tasks = query.offset(skip).limit(limit).all()
        return tasks, total
