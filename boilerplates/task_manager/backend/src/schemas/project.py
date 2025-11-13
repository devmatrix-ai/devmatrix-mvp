"""Project schemas for project management."""

from pydantic import BaseModel, Field
from typing import Optional
from .base import TimestampedSchema


class ProjectCreate(BaseModel):
    """Schema for creating a project."""

    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    color: Optional[str] = Field(None, regex="^#[0-9A-Fa-f]{6}$", description="Hex color")
    organization_id: str = Field(..., description="Organization ID")
    owner_id: str = Field(..., description="Owner user ID")


class ProjectRead(TimestampedSchema):
    """Schema for reading project data."""

    name: str
    description: Optional[str]
    owner_id: str
    status: str
    color: Optional[str]


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""

    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    color: Optional[str] = Field(None, regex="^#[0-9A-Fa-f]{6}$")
    status: Optional[str] = None
