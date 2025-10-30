"""
Audit Log Model

Tracks authentication, authorization, and modification events for security and compliance.
Group 4: Authorization & Access Control Layer
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, DateTime, ForeignKey, Index, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSON

from src.config.database import Base


class AuditLog(Base):
    """
    Audit log model for security event tracking.

    Logs:
    - Authentication events (login, logout, login_failed, token_refresh)
    - Authorization failures (access denied to resources)
    - Modification events (create, update, delete operations)
    - Read operations (conversation.read, message.read, user.read) - Phase 2

    Fields:
        id: UUID primary key
        timestamp: Event timestamp (UTC)
        user_id: UUID foreign key to users table (nullable for anonymous events)
        action: Event action (e.g., "auth.login", "conversation.read", "conversation.update_denied")
        resource_type: Type of resource accessed (e.g., "conversation", "message")
        resource_id: UUID of the resource accessed
        result: Event result ("success" or "denied")
        ip_address: Client IP address
        user_agent: Client user agent string
        event_metadata: Additional event metadata (JSON, column name 'metadata')
            Note: Uses JSON (not JSONB) for SQLite test compatibility
                  PostgreSQL migrations still use JSONB for optimal performance
    """

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True  # Nullable for anonymous access attempts
    )
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    result = Column(
        String(20),
        CheckConstraint("result IN ('success', 'denied')"),
        nullable=False
    )
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    # Use JSON (not JSONB) for SQLite test compatibility
    # PostgreSQL migrations still use JSONB for optimal performance
    event_metadata = Column("metadata", JSON, nullable=True, default={})

    # Indexes for performance
    __table_args__ = (
        Index('ix_audit_logs_timestamp', 'timestamp'),
        Index('ix_audit_logs_user_id', 'user_id'),
        Index('ix_audit_logs_resource', 'resource_type', 'resource_id'),
        Index('ix_audit_logs_action', 'action'),
    )

    def __repr__(self):
        return (
            f"<AuditLog(id={self.id}, timestamp={self.timestamp}, "
            f"user_id={self.user_id}, action='{self.action}', result='{self.result}')>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user_id": str(self.user_id) if self.user_id else None,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": str(self.resource_id) if self.resource_id else None,
            "result": self.result,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "metadata": self.event_metadata or {}
        }
