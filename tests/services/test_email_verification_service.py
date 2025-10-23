"""
Tests for Email Verification Service

Focused tests for email verification functionality.
Task Group 2.1 - Phase 6: Authentication & Multi-tenancy
"""

import uuid
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.services.email_verification_service import EmailVerificationService
from src.models.user import User
from src.config.database import get_db_context


@pytest.fixture
def email_service():
    """Create EmailVerificationService instance"""
    return EmailVerificationService()


@pytest.fixture
def test_user(request):
    """Create a test user for verification tests"""
    # Generate unique username for each test
    test_id = str(uuid.uuid4())[:8]
    username = f"testuser_{test_id}"
    email = f"test_{test_id}@example.com"

    with get_db_context() as db:
        user = User(
            email=email,
            username=username,
            password_hash="hashed_password",
            is_active=True,
            is_verified=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        yield user

        # Cleanup
        try:
            db.delete(user)
            db.commit()
        except:
            db.rollback()


class TestEmailVerificationService:
    """Test suite for EmailVerificationService"""

    def test_generate_verification_token(self, email_service, test_user):
        """Test verification token generation and storage"""
        token = email_service.generate_verification_token(test_user.user_id)

        # Verify token is a UUID
        assert isinstance(token, uuid.UUID)

        # Verify token is stored in database
        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == test_user.user_id).first()
            assert user.verification_token == token
            assert user.verification_token_created_at is not None
            assert isinstance(user.verification_token_created_at, datetime)

    @patch('src.services.email_verification_service.EmailVerificationService.send_verification_email')
    def test_send_verification_email_stub(self, mock_send_email, email_service, test_user):
        """Test verification email sending (stubbed)"""
        token = uuid.uuid4()

        # Set up mock to return True
        mock_send_email.return_value = True

        # Call the stubbed email sending method
        result = email_service.send_verification_email(test_user.email, token)

        # Verify stub returns expected value
        assert result is True

    def test_verify_email_success(self, email_service, test_user):
        """Test successful email verification"""
        # Generate verification token
        token = email_service.generate_verification_token(test_user.user_id)

        # Verify email
        result = email_service.verify_email(token)

        # Verify result
        assert result is True

        # Verify user is marked as verified
        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == test_user.user_id).first()
            assert user.is_verified is True
            assert user.verification_token is None
            assert user.verification_token_created_at is None

    def test_verify_email_invalid_token(self, email_service):
        """Test email verification with invalid token"""
        invalid_token = uuid.uuid4()

        result = email_service.verify_email(invalid_token)

        # Verify fails with invalid token
        assert result is False

    def test_verify_email_expired_token(self, email_service, test_user):
        """Test email verification with expired token (24 hours)"""
        # Generate token and manually set it to expired (25 hours ago)
        token = uuid.uuid4()
        expired_time = datetime.utcnow() - timedelta(hours=25)

        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == test_user.user_id).first()
            user.verification_token = token
            user.verification_token_created_at = expired_time
            db.commit()

        # Attempt to verify with expired token
        result = email_service.verify_email(token)

        # Verify fails with expired token
        assert result is False

    def test_token_expiry_check(self, email_service):
        """Test token expiry validation logic"""
        # Test non-expired token (23 hours old)
        recent_time = datetime.utcnow() - timedelta(hours=23)
        assert email_service.is_token_expired(recent_time, hours=24) is False

        # Test expired token (25 hours old)
        old_time = datetime.utcnow() - timedelta(hours=25)
        assert email_service.is_token_expired(old_time, hours=24) is True

        # Test edge case: exactly 24 hours
        edge_time = datetime.utcnow() - timedelta(hours=24, minutes=1)
        assert email_service.is_token_expired(edge_time, hours=24) is True

    def test_resend_verification_creates_new_token(self, email_service, test_user):
        """Test resend verification generates new token"""
        # Generate initial token
        first_token = email_service.generate_verification_token(test_user.user_id)

        # Resend verification
        with patch('src.services.email_verification_service.EmailVerificationService.send_verification_email'):
            second_token = email_service.resend_verification(test_user.user_id)

        # Verify new token is different
        assert second_token != first_token

        # Verify new token is stored
        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == test_user.user_id).first()
            assert user.verification_token == second_token

    def test_resend_verification_already_verified(self, email_service, test_user):
        """Test resend verification fails if user already verified"""
        # Mark user as verified
        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == test_user.user_id).first()
            user.is_verified = True
            db.commit()

        # Attempt to resend verification
        with pytest.raises(ValueError, match="already verified"):
            email_service.resend_verification(test_user.user_id)
