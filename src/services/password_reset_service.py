"""
Password Reset Service

Handles password reset token generation, validation, and password updates.
Task Group 2.2 - Phase 6: Authentication & Multi-tenancy
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from src.models.user import User
from src.config.database import get_db_context
from src.services.auth_service import AuthService
from src.services.email_service import EmailService
from src.observability import get_logger

logger = get_logger("password_reset_service")


class PasswordResetService:
    """
    Service for managing password reset workflow.

    Usage:
        service = PasswordResetService()

        # Request password reset
        token = service.request_password_reset("user@example.com")

        # Validate reset token
        is_valid = service.validate_reset_token(token)

        # Reset password with token
        success = service.reset_password(token, "new_password")
    """

    def __init__(self):
        """Initialize password reset service with email sender."""
        self.email_service = EmailService()

    def request_password_reset(self, email: str) -> Optional[UUID]:
        """
        Request password reset for user email.

        Generates a reset token with 1-hour expiry and sends reset email.
        Security: Does not reveal whether email exists in database.

        Args:
            email: User email address

        Returns:
            Generated UUID token if user exists, None otherwise
        """
        with get_db_context() as db:
            user = db.query(User).filter(User.email == email).first()

            if not user:
                # Security: Don't reveal if email exists
                logger.info(f"Password reset requested for non-existent email: {email}")
                return None

            # Generate new UUID token
            token = uuid.uuid4()

            # Set expiry to 1 hour from now
            expiry = datetime.utcnow() + timedelta(hours=1)

            # Store token and expiry
            user.password_reset_token = token
            user.password_reset_expires = expiry

            db.commit()
            db.refresh(user)

            # Send password reset email with username
            self.send_password_reset_email(email, user.username, token)

            logger.info(f"Password reset token generated for user {user.user_id}")
            return token

    def validate_reset_token(self, token: UUID) -> bool:
        """
        Validate reset token exists and is not expired.

        Args:
            token: Password reset token UUID

        Returns:
            True if token is valid and not expired, False otherwise
        """
        with get_db_context() as db:
            # Find user by reset token
            user = db.query(User).filter(User.password_reset_token == token).first()

            if not user:
                logger.warning("Token validation failed: Invalid token")
                return False

            # Check if token is expired
            if self.is_token_expired(user.password_reset_expires):
                logger.warning(f"Token validation failed: Expired token for user {user.user_id}")
                return False

            logger.debug(f"Token validated successfully for user {user.user_id}")
            return True

    def is_token_expired(self, expires_at: Optional[datetime]) -> bool:
        """
        Check if reset token is expired.

        Compares expiry timestamp with current time.

        Args:
            expires_at: Token expiry timestamp

        Returns:
            True if token is expired or timestamp is None, False otherwise
        """
        if not expires_at:
            return True

        is_expired = datetime.utcnow() > expires_at

        return is_expired

    def reset_password(self, token: UUID, new_password: str) -> bool:
        """
        Reset password using valid token.

        Validates token, hashes new password, updates user record, and clears token.

        Args:
            token: Password reset token UUID
            new_password: New plain text password

        Returns:
            True if password reset successful, False if token invalid/expired
        """
        # Validate token first
        if not self.validate_reset_token(token):
            logger.warning("Password reset failed: Invalid or expired token")
            return False

        with get_db_context() as db:
            # Find user by token
            user = db.query(User).filter(User.password_reset_token == token).first()

            if not user:
                # Should not happen if validate passed, but safety check
                logger.error("Password reset failed: User not found after validation")
                return False

            # Hash new password using AuthService
            new_password_hash = AuthService.hash_password(new_password)

            # Update password and clear reset token fields
            user.password_hash = new_password_hash
            user.password_reset_token = None
            user.password_reset_expires = None

            db.commit()

            logger.info(f"Password reset successful for user {user.user_id}")
            return True

    def send_password_reset_email(self, user_email: str, username: str, token: UUID) -> bool:
        """
        Send password reset email to user.

        Task Group 3.1: Implemented with real email sending.

        Args:
            user_email: User's email address
            username: User's username (for personalization)
            token: Password reset token UUID

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            return self.email_service.send_password_reset_email(
                to_email=user_email,
                username=username,
                token=token
            )
        except Exception as e:
            logger.error(f"Failed to send password reset email to {user_email}: {str(e)}")
            return False
