"""
Tests for Authentication API Endpoints - Email Verification & Password Reset

Task Group 2.3: Authentication API Endpoints
Tests: 2.3.1 - Focused tests for new auth endpoints (2-6 tests)
"""

import uuid
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.models.user import User
from src.services.auth_service import AuthService
from src.services.email_verification_service import EmailVerificationService
from src.services.password_reset_service import PasswordResetService
from src.config.database import get_db_context


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def test_user():
    """Create a test user for authentication tests"""
    auth_service = AuthService()

    # Clean up any existing test user
    with get_db_context() as db:
        existing = db.query(User).filter(User.email == "test@example.com").first()
        if existing:
            db.delete(existing)
            db.commit()

    # Create new test user
    user = auth_service.register_user(
        email="test@example.com",
        username="testuser",
        password="TestPassword123!"
    )

    yield user

    # Cleanup
    with get_db_context() as db:
        user_to_delete = db.query(User).filter(User.user_id == user.user_id).first()
        if user_to_delete:
            db.delete(user_to_delete)
            db.commit()


@pytest.fixture
def unverified_user():
    """Create an unverified test user"""
    auth_service = AuthService()

    # Clean up any existing test user
    with get_db_context() as db:
        existing = db.query(User).filter(User.email == "unverified@example.com").first()
        if existing:
            db.delete(existing)
            db.commit()

    # Create user
    user = auth_service.register_user(
        email="unverified@example.com",
        username="unverifieduser",
        password="TestPassword123!"
    )

    # Mark as unverified
    with get_db_context() as db:
        db_user = db.query(User).filter(User.user_id == user.user_id).first()
        db_user.is_verified = False
        db.commit()
        db.refresh(db_user)
        user = db_user

    yield user

    # Cleanup
    with get_db_context() as db:
        user_to_delete = db.query(User).filter(User.user_id == user.user_id).first()
        if user_to_delete:
            db.delete(user_to_delete)
            db.commit()


class TestVerifyEmailEndpoint:
    """Test POST /api/v1/auth/verify-email endpoint"""

    def test_verify_email_success(self, client, unverified_user):
        """Test successful email verification"""
        # Generate verification token
        verification_service = EmailVerificationService()
        token = verification_service.generate_verification_token(unverified_user.user_id)

        # Verify email via API
        response = client.post(
            "/api/v1/auth/verify-email",
            json={"token": str(token)}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Email verified successfully"
        assert data["user_id"] == str(unverified_user.user_id)

        # Verify user is now verified in database
        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == unverified_user.user_id).first()
            assert user.is_verified is True
            assert user.verification_token is None

    def test_verify_email_invalid_token(self, client):
        """Test email verification with invalid token"""
        fake_token = str(uuid.uuid4())

        response = client.post(
            "/api/v1/auth/verify-email",
            json={"token": fake_token}
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_verify_email_expired_token(self, client, unverified_user):
        """Test email verification with expired token (24+ hours old)"""
        # Generate token and manually set old timestamp
        verification_service = EmailVerificationService()
        token = verification_service.generate_verification_token(unverified_user.user_id)

        # Manually expire the token
        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == unverified_user.user_id).first()
            user.verification_token_created_at = datetime.utcnow() - timedelta(hours=25)
            db.commit()

        # Try to verify
        response = client.post(
            "/api/v1/auth/verify-email",
            json={"token": str(token)}
        )

        assert response.status_code == 400
        data = response.json()
        assert "expired" in data["error"].lower() or "invalid" in data["error"].lower()


class TestResendVerificationEndpoint:
    """Test POST /api/v1/auth/resend-verification endpoint"""

    def test_resend_verification_success(self, client, unverified_user):
        """Test successful resend of verification email"""
        # Login to get auth token
        auth_service = AuthService()
        tokens = auth_service.login("unverified@example.com", "TestPassword123!")

        response = client.post(
            "/api/v1/auth/resend-verification",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_resend_verification_already_verified(self, client, test_user):
        """Test resend verification for already verified user returns error"""
        # Login to get auth token
        auth_service = AuthService()
        tokens = auth_service.login("test@example.com", "TestPassword123!")

        response = client.post(
            "/api/v1/auth/resend-verification",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )

        assert response.status_code == 400
        data = response.json()
        assert "already verified" in data["error"].lower()


class TestForgotPasswordEndpoint:
    """Test POST /api/v1/auth/forgot-password endpoint"""

    def test_forgot_password_success(self, client, test_user):
        """Test forgot password with valid email"""
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "test@example.com"}
        )

        # Always returns 200 for security (don't reveal if email exists)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_forgot_password_nonexistent_email(self, client):
        """Test forgot password with non-existent email (should still return 200)"""
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"}
        )

        # Should return 200 to not reveal email existence
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


class TestResetPasswordEndpoint:
    """Test POST /api/v1/auth/reset-password endpoint"""

    def test_reset_password_success(self, client, test_user):
        """Test successful password reset with valid token"""
        # Request password reset
        password_service = PasswordResetService()
        token = password_service.request_password_reset("test@example.com")

        # Reset password
        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": str(token),
                "new_password": "NewPassword456!"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

        # Verify can login with new password
        auth_service = AuthService()
        tokens = auth_service.login("test@example.com", "NewPassword456!")
        assert tokens["access_token"] is not None

    def test_reset_password_invalid_token(self, client):
        """Test password reset with invalid token"""
        fake_token = str(uuid.uuid4())

        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": fake_token,
                "new_password": "NewPassword456!"
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_reset_password_weak_password(self, client, test_user):
        """Test password reset with weak password (less than 8 chars)"""
        # Request password reset
        password_service = PasswordResetService()
        token = password_service.request_password_reset("test@example.com")

        # Try to reset with weak password
        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": str(token),
                "new_password": "weak"
            }
        )

        # Should fail validation
        assert response.status_code == 422  # Pydantic validation error
