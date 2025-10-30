"""
Role Model for RBAC (Role-Based Access Control)

Implements system and custom roles for granular permission control.
Phase 2 - Task Group 6: Database Schema - RBAC Tables
"""

import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import Column, String, DateTime, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.config.database import Base


class Role(Base):
    """
    Role model for RBAC system.

    Fields:
        role_id: UUID primary key
        role_name: Unique role name (e.g., "superadmin", "admin", "user", "viewer")
        description: Human-readable description of the role
        is_system: Flag indicating if role is system-defined (cannot be deleted)
        created_at: Role creation timestamp

    System Roles (is_system=True):
        - superadmin: Full system access, cannot be deleted
        - admin: Manage users, view all conversations, access audit logs
        - user: Full CRUD on own resources, share conversations
        - viewer: Read-only access to shared resources

    Custom Roles (is_system=False):
        - Can be created, updated, and deleted by admins
        - Subject to same permission framework

    Indexes:
        - idx_roles_name: For fast role name lookups
    """

    __tablename__ = "roles"

    role_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_name = Column(String(50), unique=True, nullable=False)
    description = Column(String, nullable=True)
    is_system = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Index for role name lookups
    __table_args__ = (
        Index('idx_roles_name', 'role_name'),
    )

    # Relationship to user_roles (many-to-many through user_roles table)
    # user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Role(role_id={self.role_id}, role_name={self.role_name}, is_system={self.is_system})>"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "role_id": str(self.role_id),
            "role_name": self.role_name,
            "description": self.description,
            "is_system": self.is_system,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
