"""Comment schemas for collaboration."""

from pydantic import BaseModel, Field
from typing import Optional
from .base import TimestampedSchema


class CommentCreate(BaseModel):
    """Schema for creating a comment."""

    content: str = Field(..., min_length=1, description="Comment content")
    entity_type: str = Field(..., description="Entity type (task, project)")
    entity_id: str = Field(..., description="Entity ID")
    organization_id: str = Field(..., description="Organization ID")
    user_id: str = Field(..., description="Author user ID")
    parent_comment_id: Optional[str] = Field(None, description="Parent comment ID for threading")


class CommentRead(TimestampedSchema):
    """Schema for reading comment data."""

    content: str
    entity_type: str
    entity_id: str
    user_id: str
    parent_comment_id: Optional[str]
