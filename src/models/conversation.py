"""
Conversation Model

Stores user chat conversations for multi-tenancy support.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.config.database import Base


class Conversation(Base):
    """
    Conversation model for user chat history.

    Fields:
        conversation_id: UUID primary key
        user_id: UUID foreign key to users table
        title: Conversation title (max 300 chars)
        created_at: Conversation creation timestamp
        updated_at: Last update timestamp

    Indexes:
        - Index on user_id for fast user-based queries
        - Index on created_at for chronological sorting
    """

    __tablename__ = "conversations"

    conversation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    title = Column(String(300), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indexes for performance
    __table_args__ = (
        Index('idx_conversations_user_id', 'user_id'),
        Index('idx_conversations_created_at', 'created_at'),
    )

    # Relationship to User and Messages (optional, for convenience)
    # user = relationship("User", backref="conversations")
    # messages = relationship("Message", backref="conversation", cascade="all, delete-orphan")

    def __repr__(self):
        return (
            f"<Conversation(conversation_id={self.conversation_id}, "
            f"user_id={self.user_id}, title='{self.title}')>"
        )

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "conversation_id": str(self.conversation_id),
            "user_id": str(self.user_id),
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
