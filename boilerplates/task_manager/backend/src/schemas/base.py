"""Base schemas for common response patterns."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Generic, TypeVar, List

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    class Config:
        from_attributes = True


class TimestampedSchema(BaseSchema):
    """Schema with timestamp fields."""

    id: str = Field(..., description="Unique identifier")
    organization_id: str = Field(..., description="Organization ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_deleted: bool = Field(default=False, description="Soft delete flag")


class PaginatedResponse(BaseSchema, Generic[T]):
    """Generic paginated response."""

    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    total_pages: int = Field(..., description="Total number of pages")

    class Config:
        arbitrary_types_allowed = True
