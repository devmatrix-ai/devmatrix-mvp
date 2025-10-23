"""
User Model for Authentication

Implements user authentication with password hashing and JWT support.
Extended with email verification and password reset functionality.
"""

import uuid
from datetime import datetime
from typing import Any, Optional
from sqlalchemy import Column, String, DateTime, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID

from src.config.database import Base


class User(Base):
    """
    User model for authentication and authorization.

    Fields:
        user_id: UUID primary key
        email: Unique email address
        username: Unique username
        password_hash: Bcrypt hashed password
        is_active: Account status
        is_superuser: Admin privileges flag
        is_verified: Email verification status (default True)
        verification_token: UUID token for email verification (nullable)
        verification_token_created_at: Timestamp for verification token creation (nullable)
        password_reset_token: UUID token for password reset (nullable)
        password_reset_expires: Expiry timestamp for password reset token (nullable)
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        last_login_at: Last login timestamp
    """

    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    # Email verification fields (Task 1.1.2)
    is_verified = Column(Boolean, default=True, nullable=False)
    verification_token = Column(UUID(as_uuid=True), nullable=True)
    verification_token_created_at = Column(DateTime, nullable=True)

    # Password reset fields (Task 1.1.3)
    password_reset_token = Column(UUID(as_uuid=True), nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    # Indexes for token lookups (Task 1.1.3)
    __table_args__ = (
        Index('idx_verification_token', 'verification_token'),
        Index('idx_password_reset_token', 'password_reset_token'),
    )

    def __repr__(self) -> str:
        return f"<User(user_id={self.user_id}, email={self.email}, username={self.username})>"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (excluding password_hash and sensitive tokens)"""
        return {
            "user_id": str(self.user_id),
            "email": self.email,
            "username": self.username,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None
        }
