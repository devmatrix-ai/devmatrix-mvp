"""Activity log model for audit trails."""

from sqlalchemy import Column, String, Text, DateTime, Index
from datetime import datetime
from .base import Base


class ActivityLog(Base):
    """Activity log for tracking changes to entities."""

    __tablename__ = "activity_logs"

    id = Column(String(36), primary_key=True)
    organization_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)  # task, project, etc.
    entity_id = Column(String(36), nullable=False, index=True)
    action = Column(String(50), nullable=False)  # created, updated, deleted, status_changed
    before_state = Column(Text, nullable=True)  # JSON string
    after_state = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_entity", "organization_id", "entity_type", "entity_id"),
        Index("idx_user", "organization_id", "user_id"),
        Index("idx_created", "created_at"),
    )
