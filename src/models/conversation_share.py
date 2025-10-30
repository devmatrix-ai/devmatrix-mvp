"""
ConversationShare Model

Stores user-to-user conversation sharing permissions.
Phase 2 - Task Group 8: Granular Permission System

Permission Levels:
- view: Read-only access
- comment: Read + write messages
- edit: Full access except delete/re-share
"""

import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, ForeignKey, Index, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.config.database import Base


class PermissionLevel(str, Enum):
    """Permission levels for conversation sharing."""
    VIEW = "view"
    COMMENT = "comment"
    EDIT = "edit"


class ConversationShare(Base):
    """
    ConversationShare model for user-to-user conversation sharing.

    Fields:
        share_id: UUID primary key
        conversation_id: UUID foreign key to conversations table
        shared_by: UUID foreign key to users table (nullable for deleted users)
        shared_with: UUID foreign key to users table
        permission_level: Permission level (view/comment/edit)
        shared_at: Share creation timestamp

    Constraints:
        - CHECK: permission_level IN ('view', 'comment', 'edit')
        - UNIQUE: (conversation_id, shared_with) - cannot share same conversation twice

    Indexes:
        - Index on conversation_id for fast conversation-based queries
        - Index on shared_with for fast user-based queries
    """

    __tablename__ = "conversation_shares"

    share_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.conversation_id", ondelete="CASCADE"),
        nullable=False
    )
    shared_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True
    )
    shared_with = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    permission_level = Column(String(20), nullable=False)

    # Timestamp
    shared_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Constraints
    __table_args__ = (
        Index('idx_conversation_shares_conversation_id', 'conversation_id'),
        Index('idx_conversation_shares_shared_with', 'shared_with'),
        CheckConstraint(
            "permission_level IN ('view', 'comment', 'edit')",
            name='ck_conversation_shares_permission_level'
        ),
        UniqueConstraint(
            'conversation_id', 'shared_with',
            name='uq_conversation_shares_conversation_user'
        ),
    )

    # Relationships (optional, for convenience)
    # conversation = relationship("Conversation", backref="shares")
    # shared_by_user = relationship("User", foreign_keys=[shared_by])
    # shared_with_user = relationship("User", foreign_keys=[shared_with])

    def __repr__(self):
        return (
            f"<ConversationShare(share_id={self.share_id}, "
            f"conversation_id={self.conversation_id}, "
            f"shared_with={self.shared_with}, "
            f"permission_level='{self.permission_level}')>"
        )

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "share_id": str(self.share_id),
            "conversation_id": str(self.conversation_id),
            "shared_by": str(self.shared_by) if self.shared_by else None,
            "shared_with": str(self.shared_with),
            "permission_level": self.permission_level,
            "shared_at": self.shared_at.isoformat() if self.shared_at else None,
        }

    @staticmethod
    def validate_permission_level(level: str) -> bool:
        """Validate permission level string."""
        try:
            PermissionLevel(level)
            return True
        except ValueError:
            return False
