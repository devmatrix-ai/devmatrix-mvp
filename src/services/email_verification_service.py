"""
Email Verification Service

Handles email verification token generation, validation, and email sending.
Task Group 2.1 - Phase 6: Authentication & Multi-tenancy
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import UUID

from src.models.user import User
from src.config.database import get_db_context
from src.services.email_service import EmailService
from src.observability import get_logger

logger = get_logger("email_verification_service")


class EmailVerificationService:
    """
    Service for managing email verification workflow.

    Usage:
        service = EmailVerificationService()

        # Generate and send verification token
        token = service.generate_verification_token(user_id)
        service.send_verification_email(user_email, token)

        # Verify email with token
        success, user_id = service.verify_email(token)

        # Resend verification
        new_token = service.resend_verification(user_id)
    """

    def __init__(self):
        """Initialize email verification service with email sender."""
        self.email_service = EmailService()

    def generate_verification_token(self, user_id: UUID) -> UUID:
        """
        Generate a new verification token for user.

        Creates a UUID token and stores it in the database with timestamp.

        Args:
            user_id: User UUID

        Returns:
            Generated UUID token

        Raises:
            ValueError: If user not found
        """
        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == user_id).first()

            if not user:
                logger.warning(f"Cannot generate token: User not found ({user_id})")
                raise ValueError("User not found")

            # Generate new UUID token
            token = uuid.uuid4()

            # Store token and timestamp
            user.verification_token = token
            user.verification_token_created_at = datetime.utcnow()

            db.commit()
            db.refresh(user)

            logger.info(f"Verification token generated for user {user_id}")
            return token

    def verify_email(self, token: UUID) -> Tuple[bool, Optional[UUID]]:
        """
        Verify email using verification token.

        Validates token exists, is not expired, and marks user as verified.

        Args:
            token: Verification token UUID

        Returns:
            Tuple of (success: bool, user_id: Optional[UUID])
            - (True, user_id) if verification successful
            - (False, None) if verification failed
        """
        with get_db_context() as db:
            # Find user by verification token
            user = db.query(User).filter(User.verification_token == token).first()

            if not user:
                logger.warning(f"Verification failed: Invalid token")
                return (False, None)

            # Check if token is expired (24 hours)
            if self.is_token_expired(user.verification_token_created_at, hours=24):
                logger.warning(f"Verification failed: Token expired for user {user.user_id}")
                return (False, None)

            # Store user_id before clearing token
            user_id = user.user_id

            # Mark user as verified and clear token
            user.is_verified = True
            user.verification_token = None
            user.verification_token_created_at = None

            db.commit()

            logger.info(f"Email verified successfully for user {user_id}")
            return (True, user_id)

    def is_token_expired(self, created_at: datetime, hours: int = 24) -> bool:
        """
        Check if verification token is expired.

        Args:
            created_at: Token creation timestamp
            hours: Expiry time in hours (default: 24)

        Returns:
            True if token is expired, False otherwise
        """
        if not created_at:
            return True

        expiry_time = created_at + timedelta(hours=hours)
        is_expired = datetime.utcnow() > expiry_time

        return is_expired

    def resend_verification(self, user_id: UUID) -> UUID:
        """
        Resend verification email with new token.

        Generates new token, invalidates old one, and sends email.

        Args:
            user_id: User UUID

        Returns:
            New verification token UUID

        Raises:
            ValueError: If user already verified or not found
        """
        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == user_id).first()

            if not user:
                logger.warning(f"Resend failed: User not found ({user_id})")
                raise ValueError("User not found")

            # Check if already verified
            if user.is_verified:
                logger.warning(f"Resend failed: User already verified ({user_id})")
                raise ValueError("User already verified")

            # Generate new token (this also invalidates the old one)
            new_token = self.generate_verification_token(user_id)

            # Send verification email with username
            self.send_verification_email(user.email, new_token, user.username)

            logger.info(f"Verification email resent for user {user_id}")
            return new_token

    def send_verification_email(self, user_email: str, token: UUID, username: str = "User") -> bool:
        """
        Send verification email to user.

        Task Group 3.1: Implemented with real email sending.

        Args:
            user_email: User's email address
            token: Verification token UUID
            username: User's username (for personalization)

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            return self.email_service.send_verification_email(
                to_email=user_email,
                username=username,
                token=token
            )
        except Exception as e:
            logger.error(f"Failed to send verification email to {user_email}: {str(e)}")
            return False
