"""Activity log schemas for audit trails."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any


class ActivityLogRead(BaseModel):
    """Schema for reading activity log data."""

    id: str = Field(..., description="Activity log ID")
    organization_id: str = Field(..., description="Organization ID")
    user_id: str = Field(..., description="User who performed action")
    entity_type: str = Field(..., description="Type of entity affected")
    entity_id: str = Field(..., description="ID of entity affected")
    action: str = Field(..., description="Action performed")
    before_state: Optional[Dict[str, Any]] = Field(None, description="State before change")
    after_state: Optional[Dict[str, Any]] = Field(None, description="State after change")
    created_at: datetime = Field(..., description="Timestamp of action")

    class Config:
        from_attributes = True
