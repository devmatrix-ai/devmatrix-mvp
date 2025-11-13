"""Comment model for entity collaboration."""

from sqlalchemy import Column, String, Text, Index
from .base import TimestampedBase


class Comment(TimestampedBase):
    """Comment entity for discussions on tasks and projects."""

    __tablename__ = "comments"

    user_id = Column(String(36), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)  # task, project
    entity_id = Column(String(36), nullable=False, index=True)
    content = Column(Text, nullable=False)
    parent_comment_id = Column(String(36), nullable=True, index=True)  # For threaded comments

    __table_args__ = (
        Index("idx_entity", "organization_id", "entity_type", "entity_id"),
        Index("idx_user", "organization_id", "user_id"),
    )
