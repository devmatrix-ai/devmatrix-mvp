"""Project model for task grouping."""

from sqlalchemy import Column, String, Text, Index
from .base import TimestampedBase


class Project(TimestampedBase):
    """Project entity for grouping related tasks."""

    __tablename__ = "projects"

    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    owner_id = Column(String(36), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="active", index=True)  # active, archived, completed
    color = Column(String(7), nullable=True)  # Hex color for UI

    __table_args__ = (
        Index("idx_org_owner", "organization_id", "owner_id"),
        Index("idx_org_status", "organization_id", "status"),
    )
