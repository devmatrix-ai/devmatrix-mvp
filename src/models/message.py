"""
Message Model

Stores individual messages within conversations.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.config.database import Base


class Message(Base):
    """
    Message model for conversation chat messages.

    Fields:
        message_id: UUID primary key
        conversation_id: UUID foreign key to conversations table
        role: Message role (user/assistant/system, max 20 chars)
        content: Message content (Text for large messages)
        created_at: Message creation timestamp

    Indexes:
        - Index on conversation_id for fast conversation-based queries
    """

    __tablename__ = "messages"

    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.conversation_id", ondelete="CASCADE"),
        nullable=False
    )
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Index for performance
    __table_args__ = (
        Index('idx_messages_conversation_id', 'conversation_id'),
    )

    # Relationship to Conversation (optional, for convenience)
    # conversation = relationship("Conversation", backref="messages")

    def __repr__(self):
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return (
            f"<Message(message_id={self.message_id}, "
            f"conversation_id={self.conversation_id}, "
            f"role='{self.role}', content='{content_preview}')>"
        )

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "message_id": str(self.message_id),
            "conversation_id": str(self.conversation_id),
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
