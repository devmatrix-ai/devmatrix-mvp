"""Task model for task management."""

from sqlalchemy import Column, String, Text, DateTime, Index, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import TimestampedBase


class Task(TimestampedBase):
    """Task entity with status tracking and assignment."""

    __tablename__ = "tasks"

    # Required fields
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="todo", index=True)  # todo, in_progress, done
    priority = Column(String(50), nullable=False, default="medium", index=True)  # low, medium, high, critical

    # Relationships
    project_id = Column(String(36), nullable=True, index=True)
    user_id = Column(String(36), nullable=False, index=True)  # Created by
    assigned_to = Column(String(36), nullable=True, index=True)  # Assigned to user

    # Dates and metadata
    due_date = Column(DateTime, nullable=True, index=True)
    parent_id = Column(String(36), nullable=True, index=True)  # For subtasks

    # Tags for filtering
    tags = Column(String(255), nullable=True)  # Comma-separated tags

    __table_args__ = (
        Index("idx_org_user", "organization_id", "user_id"),
        Index("idx_org_status", "organization_id", "status"),
        Index("idx_org_project", "organization_id", "project_id"),
        Index("idx_org_assigned", "organization_id", "assigned_to"),
        Index("idx_created_desc", "created_at"),
    )
