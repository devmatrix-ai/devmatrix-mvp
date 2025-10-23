"""
Unit tests for User model extensions (email verification and password reset).

Tests focus on:
- Email verification token generation and validation
- Password reset token creation and expiry
- User ID UUID constraints

As per Task 1.1.1: Write 2-5 focused tests (not exhaustive)
"""

import uuid
from datetime import datetime, timedelta
import pytest
from sqlalchemy.exc import IntegrityError

from src.models.user import User


class TestUserEmailVerification:
    """Test email verification functionality"""

    def test_user_has_verification_fields(self):
        """Test that User model has email verification fields"""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
            is_verified=False,
            verification_token=uuid.uuid4(),
            verification_token_created_at=datetime.utcnow()
        )

        assert hasattr(user, 'is_verified')
        assert hasattr(user, 'verification_token')
        assert hasattr(user, 'verification_token_created_at')
        assert user.is_verified is False
        assert isinstance(user.verification_token, uuid.UUID)
        assert isinstance(user.verification_token_created_at, datetime)

    def test_verification_token_can_be_null(self):
        """Test that verification token fields can be null"""
        user = User(
            email="test2@example.com",
            username="testuser2",
            password_hash="hashed_password",
            is_verified=True,
            verification_token=None,
            verification_token_created_at=None
        )

        assert user.verification_token is None
        assert user.verification_token_created_at is None


class TestUserPasswordReset:
    """Test password reset functionality"""

    def test_user_has_password_reset_fields(self):
        """Test that User model has password reset fields"""
        user = User(
            email="reset@example.com",
            username="resetuser",
            password_hash="hashed_password",
            password_reset_token=uuid.uuid4(),
            password_reset_expires=datetime.utcnow() + timedelta(hours=1)
        )

        assert hasattr(user, 'password_reset_token')
        assert hasattr(user, 'password_reset_expires')
        assert isinstance(user.password_reset_token, uuid.UUID)
        assert isinstance(user.password_reset_expires, datetime)

    def test_password_reset_token_expiry_validation(self):
        """Test password reset token expiry logic"""
        now = datetime.utcnow()
        user = User(
            email="expire@example.com",
            username="expireuser",
            password_hash="hashed_password",
            password_reset_token=uuid.uuid4(),
            password_reset_expires=now + timedelta(hours=1)
        )

        # Token should not be expired
        assert user.password_reset_expires > now

        # Simulate expired token
        user.password_reset_expires = now - timedelta(hours=1)
        assert user.password_reset_expires < now


class TestUserIDConstraints:
    """Test user_id UUID constraints"""

    def test_user_id_is_uuid(self, db_session):
        """Test that user_id is a UUID"""
        user = User(
            email="uuid@example.com",
            username="uuiduser",
            password_hash="hashed_password"
        )
        db_session.add(user)
        db_session.commit()

        assert isinstance(user.user_id, uuid.UUID)
        assert user.user_id is not None

    def test_user_email_unique_constraint(self, db_session):
        """Test that email must be unique"""
        user1 = User(
            email="duplicate@example.com",
            username="user1",
            password_hash="hashed_password"
        )
        db_session.add(user1)
        db_session.commit()

        # Try to create user with duplicate email
        user2 = User(
            email="duplicate@example.com",
            username="user2",
            password_hash="hashed_password"
        )
        db_session.add(user2)

        with pytest.raises(IntegrityError):
            db_session.commit()
