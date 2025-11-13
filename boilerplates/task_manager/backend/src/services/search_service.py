"""Search service for filtering and searching entities."""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional, Tuple

from src.models.task import Task


class SearchService:
    """Service for searching and filtering entities."""

    @staticmethod
    def search_tasks(
        db: Session,
        *,
        organization_id: str,
        query: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        project_id: Optional[str] = None,
        assigned_to: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Task], int]:
        """Search and filter tasks."""
        q = db.query(Task).filter(
            and_(
                Task.organization_id == organization_id,
                Task.is_deleted == False,
            )
        )

        if query:
            q = q.filter(
                or_(
                    Task.name.ilike(f"%{query}%"),
                    Task.description.ilike(f"%{query}%"),
                )
            )

        if status:
            q = q.filter(Task.status == status)

        if priority:
            q = q.filter(Task.priority == priority)

        if project_id:
            q = q.filter(Task.project_id == project_id)

        if assigned_to:
            q = q.filter(Task.assigned_to == assigned_to)

        total = q.count()
        tasks = q.offset(skip).limit(limit).all()
        return tasks, total

    @staticmethod
    def search_tasks_by_tags(
        db: Session,
        *,
        organization_id: str,
        tags: List[str],
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Task], int]:
        """Search tasks by tags."""
        q = db.query(Task).filter(
            and_(
                Task.organization_id == organization_id,
                Task.is_deleted == False,
            )
        )

        for tag in tags:
            q = q.filter(Task.tags.ilike(f"%{tag}%"))

        total = q.count()
        tasks = q.offset(skip).limit(limit).all()
        return tasks, total
