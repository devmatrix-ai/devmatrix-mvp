"""
User Model for Authentication

Implements user authentication with password hashing and JWT support.
Extended with email verification and password reset functionality.
Phase 2 extensions: Authentication hardening (lockout, legacy password tracking, 2FA/MFA).
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Optional
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Index, Text, JSON
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

    Phase 2 Authentication Hardening Fields:
        password_last_changed: Timestamp when password was last changed
        legacy_password: Flag indicating password predates new complexity policy
        failed_login_attempts: Counter for consecutive failed login attempts
        locked_until: Timestamp when account lockout expires (NULL = not locked)
        last_failed_login: Timestamp of most recent failed login attempt

    Phase 2 2FA/MFA Fields (Task Group 9):
        totp_secret: Encrypted TOTP secret for 2FA (NULL if 2FA not enabled)
        totp_enabled: Flag indicating if user has 2FA enabled (default FALSE)
        totp_backup_codes: JSON array of hashed backup codes (NULL if 2FA not enabled)
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

    # Phase 2: Authentication hardening fields (Task Group 1)
    password_last_changed = Column(DateTime, nullable=True)
    # Note: Migration sets server_default='true' for existing users (grandfathered)
    # Python default is False for new users (meets new policy by default)
    legacy_password = Column(Boolean, nullable=False, default=False, server_default='false')
    failed_login_attempts = Column(Integer, nullable=False, default=0, server_default='0')
    locked_until = Column(DateTime, nullable=True)
    last_failed_login = Column(DateTime, nullable=True)

    # Phase 2: 2FA/MFA fields (Task Group 9)
    totp_secret = Column(Text, nullable=True)  # Encrypted TOTP secret
    totp_enabled = Column(Boolean, nullable=False, default=False, server_default='false')
    totp_backup_codes = Column(JSON, nullable=True)  # Array of hashed backup codes (JSON for SQLite, becomes JSONB in PostgreSQL)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    # Indexes for token lookups (Task 1.1.3)
    # Phase 2 indexes for authentication hardening (Task Group 1)
    # Phase 2 indexes for 2FA (Task Group 9)
    __table_args__ = (
        Index('idx_verification_token', 'verification_token'),
        Index('idx_password_reset_token', 'password_reset_token'),
        Index('idx_users_locked_until', 'locked_until'),
        Index('idx_users_legacy_password', 'legacy_password'),
        Index('idx_users_totp_enabled', 'totp_enabled'),
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

    # Phase 2: Helper methods for authentication hardening

    def is_locked(self) -> bool:
        """
        Check if account is currently locked.

        Returns:
            bool: True if account is locked and lockout has not expired, False otherwise
        """
        if self.locked_until is None:
            return False

        return datetime.utcnow() < self.locked_until

    def is_legacy_password(self) -> bool:
        """
        Check if user has a legacy password (predates new complexity policy).

        Returns:
            bool: True if password is legacy, False if meets current policy
        """
        return self.legacy_password is True

    def lockout_remaining_time(self) -> Optional[timedelta]:
        """
        Calculate remaining time until account lockout expires.

        Returns:
            timedelta: Time remaining until unlock, or None if not locked/already expired
        """
        if self.locked_until is None:
            return None

        now = datetime.utcnow()
        if now >= self.locked_until:
            # Lockout has expired
            return None

        return self.locked_until - now

    # Phase 2: Helper methods for 2FA/MFA (Task Group 9)

    def has_2fa_enabled(self) -> bool:
        """
        Check if user has 2FA/MFA enabled.

        Returns:
            bool: True if user has 2FA enabled, False otherwise
        """
        return self.totp_enabled is True and self.totp_secret is not None
    def has_unused_backup_codes(self) -> bool:
        """
        Check if user has unused backup codes available.

        Returns:
            bool: True if user has at least one unused backup code, False otherwise
        """
        return self.totp_backup_codes is not None and len(self.totp_backup_codes) > 0
