"""
Tests for Password Reset Service

Focused tests for password reset functionality.
Task Group 2.2 - Phase 6: Authentication & Multi-tenancy
"""

import uuid
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from src.services.password_reset_service import PasswordResetService
from src.models.user import User
from src.config.database import get_db_context


@pytest.fixture
def password_reset_service():
    """Create PasswordResetService instance"""
    return PasswordResetService()


@pytest.fixture
def test_user(request):
    """Create a test user for password reset tests"""
    # Generate unique username for each test
    test_id = str(uuid.uuid4())[:8]
    username = f"testuser_{test_id}"
    email = f"test_{test_id}@example.com"

    with get_db_context() as db:
        user = User(
            email=email,
            username=username,
            password_hash="old_hashed_password",
            is_active=True,
            is_verified=True
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


class TestPasswordResetService:
    """Test suite for PasswordResetService"""

    @patch('src.services.password_reset_service.PasswordResetService.send_password_reset_email')
    def test_request_password_reset_generates_token(self, mock_send_email, password_reset_service, test_user):
        """Test reset token generation and storage"""
        mock_send_email.return_value = True

        # Request password reset
        token = password_reset_service.request_password_reset(test_user.email)

        # Verify token is a UUID
        assert isinstance(token, uuid.UUID)

        # Verify token is stored in database with expiry
        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == test_user.user_id).first()
            assert user.password_reset_token == token
            assert user.password_reset_expires is not None
            assert isinstance(user.password_reset_expires, datetime)

            # Verify expiry is approximately 1 hour from now
            expiry_diff = user.password_reset_expires - datetime.utcnow()
            assert 55 <= expiry_diff.total_seconds() / 60 <= 65  # Between 55 and 65 minutes

        # Verify email was sent
        mock_send_email.assert_called_once_with(test_user.email, token)

    def test_validate_reset_token_success(self, password_reset_service, test_user):
        """Test token validation with valid non-expired token"""
        # Set valid token
        token = uuid.uuid4()
        future_expiry = datetime.utcnow() + timedelta(minutes=30)

        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == test_user.user_id).first()
            user.password_reset_token = token
            user.password_reset_expires = future_expiry
            db.commit()

        # Validate token
        is_valid = password_reset_service.validate_reset_token(token)

        assert is_valid is True

    def test_validate_reset_token_invalid(self, password_reset_service):
        """Test token validation with non-existent token"""
        invalid_token = uuid.uuid4()

        is_valid = password_reset_service.validate_reset_token(invalid_token)

        assert is_valid is False

    def test_validate_reset_token_expired(self, password_reset_service, test_user):
        """Test token validation with expired token (> 1 hour)"""
        # Set expired token (2 hours ago)
        token = uuid.uuid4()
        past_expiry = datetime.utcnow() - timedelta(hours=1)

        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == test_user.user_id).first()
            user.password_reset_token = token
            user.password_reset_expires = past_expiry
            db.commit()

        # Validate token
        is_valid = password_reset_service.validate_reset_token(token)

        assert is_valid is False

    def test_reset_password_success(self, password_reset_service, test_user):
        """Test password reset with valid token"""
        # Set valid reset token
        token = uuid.uuid4()
        future_expiry = datetime.utcnow() + timedelta(minutes=30)

        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == test_user.user_id).first()
            user.password_reset_token = token
            user.password_reset_expires = future_expiry
            old_password_hash = user.password_hash
            db.commit()

        new_password = "newSecurePassword123"

        # Reset password
        success = password_reset_service.reset_password(token, new_password)

        assert success is True

        # Verify password was changed and token cleared
        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == test_user.user_id).first()

            # Password hash should be different
            assert user.password_hash != old_password_hash

            # Token and expiry should be cleared
            assert user.password_reset_token is None
            assert user.password_reset_expires is None

            # Verify new password works (hash verification)
            from src.services.auth_service import AuthService
            assert AuthService.verify_password(new_password, user.password_hash) is True

    def test_reset_password_invalid_token(self, password_reset_service):
        """Test password reset with invalid token fails"""
        invalid_token = uuid.uuid4()
        new_password = "newSecurePassword123"

        success = password_reset_service.reset_password(invalid_token, new_password)

        assert success is False

    def test_token_invalidation_after_use(self, password_reset_service, test_user):
        """Test token is invalidated after single use"""
        # Set valid reset token
        token = uuid.uuid4()
        future_expiry = datetime.utcnow() + timedelta(minutes=30)

        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == test_user.user_id).first()
            user.password_reset_token = token
            user.password_reset_expires = future_expiry
            db.commit()

        # First reset should succeed
        success1 = password_reset_service.reset_password(token, "newPassword1")
        assert success1 is True

        # Second reset with same token should fail (token invalidated)
        success2 = password_reset_service.reset_password(token, "newPassword2")
        assert success2 is False

    @patch('src.services.password_reset_service.PasswordResetService.send_password_reset_email')
    def test_request_password_reset_nonexistent_email(self, mock_send_email, password_reset_service):
        """Test password reset request for non-existent email (should not reveal)"""
        mock_send_email.return_value = True

        # Request reset for non-existent email
        # Should return None but not raise error (security: don't reveal if email exists)
        token = password_reset_service.request_password_reset("nonexistent@example.com")

        # Should return None for non-existent email
        assert token is None

        # Should NOT send email
        mock_send_email.assert_not_called()
