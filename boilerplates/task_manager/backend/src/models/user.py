"""User model for authentication and authorization."""

from sqlalchemy import Column, String, Boolean, Index
from .base import TimestampedBase


class User(TimestampedBase):
    """User entity with authentication credentials."""

    __tablename__ = "users"

    email = Column(String(255), nullable=False, unique=True, index=True)
    username = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    is_superuser = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("idx_org_email", "organization_id", "email"),
        Index("idx_org_active", "organization_id", "is_active"),
    )
