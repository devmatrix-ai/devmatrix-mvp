"""
UserRole Model for RBAC (Role-Based Access Control)

Implements many-to-many relationship between users and roles with audit tracking.
Phase 2 - Task Group 6: Database Schema - RBAC Tables
"""

import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import Column, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.config.database import Base


class UserRole(Base):
    """
    UserRole model for many-to-many user-role assignments.

    Fields:
        user_role_id: UUID primary key
        user_id: UUID foreign key to users table (CASCADE delete)
        role_id: UUID foreign key to roles table (CASCADE delete)
        assigned_by: UUID foreign key to users table (who assigned this role)
        assigned_at: Timestamp when role was assigned

    Constraints:
        - UNIQUE(user_id, role_id): Prevent duplicate role assignments
        - CASCADE delete on user_id: Deleting user removes their role assignments
        - CASCADE delete on role_id: Deleting role removes all user assignments

    Audit Tracking:
        - assigned_by: Tracks which admin assigned the role
        - assigned_at: Tracks when the role was assigned

    Indexes:
        - idx_user_roles_user_id: Fast lookups by user
        - idx_user_roles_role_id: Fast lookups by role
    """

    __tablename__ = "user_roles"

    user_role_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys with CASCADE delete
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("roles.role_id", ondelete="CASCADE"),
        nullable=False
    )

    # Audit tracking: who assigned this role
    assigned_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=True
    )

    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Unique constraint and indexes
    __table_args__ = (
        UniqueConstraint('user_id', 'role_id', name='uq_user_role'),
        Index('idx_user_roles_user_id', 'user_id'),
        Index('idx_user_roles_role_id', 'role_id'),
    )

    # Relationships to User and Role models
    # user = relationship("User", foreign_keys=[user_id], back_populates="user_roles")
    # role = relationship("Role", back_populates="user_roles")
    # assigner = relationship("User", foreign_keys=[assigned_by])

    def __repr__(self) -> str:
        return (
            f"<UserRole(user_role_id={self.user_role_id}, "
            f"user_id={self.user_id}, role_id={self.role_id})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "user_role_id": str(self.user_role_id),
            "user_id": str(self.user_id),
            "role_id": str(self.role_id),
            "assigned_by": str(self.assigned_by) if self.assigned_by else None,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None
        }
