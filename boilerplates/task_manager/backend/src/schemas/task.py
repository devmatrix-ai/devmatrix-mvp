"""Task schemas for task management."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from .base import TimestampedSchema


class TaskCreate(BaseModel):
    """Schema for creating a task."""

    name: str = Field(..., min_length=1, max_length=255, description="Task name")
    description: Optional[str] = Field(None, description="Task description")
    project_id: Optional[str] = Field(None, description="Project ID")
    assigned_to: Optional[str] = Field(None, description="User ID to assign task to")
    priority: str = Field(default="medium", description="Priority level")
    due_date: Optional[datetime] = Field(None, description="Due date")
    tags: Optional[str] = Field(None, description="Comma-separated tags")
    organization_id: str = Field(..., description="Organization ID")
    user_id: str = Field(..., description="Created by user ID")


class TaskRead(TimestampedSchema):
    """Schema for reading task data."""

    name: str
    description: Optional[str]
    status: str
    priority: str
    project_id: Optional[str]
    user_id: str
    assigned_to: Optional[str]
    due_date: Optional[datetime]
    tags: Optional[str]
    parent_id: Optional[str]


class TaskUpdate(BaseModel):
    """Schema for updating a task."""

    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None
    tags: Optional[str] = None
    project_id: Optional[str] = None


class TaskStatusChange(BaseModel):
    """Schema for changing task status."""

    status: str = Field(..., description="New status")


class BulkTaskStatusChange(BaseModel):
    """Schema for bulk status change."""

    task_ids: List[str] = Field(..., description="List of task IDs")
    status: str = Field(..., description="New status for all tasks")
