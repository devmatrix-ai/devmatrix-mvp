"""
Integration Tests for Authentication API

Tests the full authentication flow including:
- Registration
- Login
- Token refresh
- Email verification
- Password reset
- User info
"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.config.database import get_db_context
from src.models.user import User


@pytest.fixture
def client():
    """Create test client"""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def test_user_data():
    """Test user data"""
    return {
        "email": f"test_{uuid4()}@example.com",
        "username": f"testuser_{uuid4().hex[:8]}",
        "password": "SecurePassword123!"
    }


class TestAuthenticationAPI:
    """Integration tests for authentication API endpoints"""

    # ========================================================================
    # Registration Tests
    # ========================================================================

    def test_register_success(self, client, test_user_data):
        """Test successful user registration"""
        response = client.post(
            "/api/v1/auth/register",
            json=test_user_data
        )

        assert response.status_code == 201
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 3600
        assert "user" in data

        user = data["user"]
        assert user["email"] == test_user_data["email"]
        assert user["username"] == test_user_data["username"]
        assert user["is_active"] is True
        assert "password" not in user  # Password should not be returned

    def test_register_duplicate_email(self, client, test_user_data):
        """Test registration with duplicate email"""
        # Register first user
        client.post("/api/v1/auth/register", json=test_user_data)

        # Try to register again with same email
        response = client.post(
            "/api/v1/auth/register",
            json={
                **test_user_data,
                "username": "different_username"
            }
        )

        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_register_duplicate_username(self, client, test_user_data):
        """Test registration with duplicate username"""
        # Register first user
        client.post("/api/v1/auth/register", json=test_user_data)

        # Try to register again with same username
        response = client.post(
            "/api/v1/auth/register",
            json={
                **test_user_data,
                "email": f"different_{test_user_data['email']}"
            }
        )

        assert response.status_code == 400
        assert "Username already taken" in response.json()["detail"]

    def test_register_invalid_email(self, client, test_user_data):
        """Test registration with invalid email"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                **test_user_data,
                "email": "not-an-email"
            }
        )

        assert response.status_code == 422  # Validation error

    def test_register_weak_password(self, client, test_user_data):
        """Test registration with weak password"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                **test_user_data,
                "password": "short"  # Too short
            }
        )

        assert response.status_code == 422  # Validation error

    def test_register_invalid_username(self, client, test_user_data):
        """Test registration with invalid username"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                **test_user_data,
                "username": "ab"  # Too short
            }
        )

        assert response.status_code == 422  # Validation error

    # ========================================================================
    # Login Tests
    # ========================================================================

    def test_login_success(self, client, test_user_data):
        """Test successful login"""
        # Register user first
        client.post("/api/v1/auth/register", json=test_user_data)

        # Login
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user_data["email"],
                "password": test_user_data["password"]
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data

    def test_login_invalid_email(self, client):
        """Test login with non-existent email"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "anypassword"
            }
        )

        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_invalid_password(self, client, test_user_data):
        """Test login with incorrect password"""
        # Register user
        client.post("/api/v1/auth/register", json=test_user_data)

        # Try login with wrong password
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user_data["email"],
                "password": "WrongPassword123!"
            }
        )

        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    # ========================================================================
    # Token Refresh Tests
    # ========================================================================

    def test_refresh_token_success(self, client, test_user_data):
        """Test successful token refresh"""
        # Register and login
        client.post("/api/v1/auth/register", json=test_user_data)
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user_data["email"],
                "password": test_user_data["password"]
            }
        )

        refresh_token = login_response.json()["refresh_token"]

        # Refresh token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_with_invalid_token(self, client):
        """Test token refresh with invalid token"""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"}
        )

        assert response.status_code == 401

    # ========================================================================
    # Get Current User Tests
    # ========================================================================

    def test_get_current_user_success(self, client, test_user_data):
        """Test getting current user info"""
        # Register user
        register_response = client.post(
            "/api/v1/auth/register",
            json=test_user_data
        )

        access_token = register_response.json()["access_token"]

        # Get user info
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["email"] == test_user_data["email"]
        assert data["username"] == test_user_data["username"]
        assert data["is_active"] is True

    def test_get_current_user_no_token(self, client):
        """Test getting current user without token"""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 403  # Forbidden (no token)

    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )

        assert response.status_code == 401

    # ========================================================================
    # Logout Tests
    # ========================================================================

    def test_logout_success(self, client, test_user_data):
        """Test successful logout"""
        # Register user
        register_response = client.post(
            "/api/v1/auth/register",
            json=test_user_data
        )

        access_token = register_response.json()["access_token"]

        # Logout
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        assert "Successfully logged out" in response.json()["message"]

    # ========================================================================
    # Email Verification Tests
    # ========================================================================

    def test_email_verification_flow(self, client, test_user_data):
        """Test email verification flow"""
        from src.services.email_verification_service import EmailVerificationService
        from src.config.database import get_db_context

        # Register user
        register_response = client.post(
            "/api/v1/auth/register",
            json=test_user_data
        )

        user_id = register_response.json()["user"]["user_id"]

        # Mark user as unverified and generate token
        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == user_id).first()
            user.is_verified = False
            db.commit()

        service = EmailVerificationService()
        token = service.generate_verification_token(user_id)

        # Verify email
        response = client.post(
            "/api/v1/auth/verify-email",
            json={"token": str(token)}
        )

        assert response.status_code == 200
        assert "Email verified successfully" in response.json()["message"]

        # Check user is now verified
        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == user_id).first()
            assert user.is_verified is True

    def test_verify_invalid_token(self, client):
        """Test email verification with invalid token"""
        response = client.post(
            "/api/v1/auth/verify-email",
            json={"token": str(uuid4())}
        )

        assert response.status_code == 400

    # ========================================================================
    # Password Reset Tests
    # ========================================================================

    def test_forgot_password(self, client, test_user_data):
        """Test forgot password request"""
        # Register user
        client.post("/api/v1/auth/register", json=test_user_data)

        # Request password reset
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": test_user_data["email"]}
        )

        assert response.status_code == 200
        assert "password reset link" in response.json()["message"].lower()

    def test_forgot_password_nonexistent_email(self, client):
        """Test forgot password with non-existent email (should still return 200)"""
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"}
        )

        # Should return 200 to prevent email enumeration
        assert response.status_code == 200

    def test_reset_password_flow(self, client, test_user_data):
        """Test password reset flow"""
        from src.services.password_reset_service import PasswordResetService

        # Register user
        client.post("/api/v1/auth/register", json=test_user_data)

        # Generate reset token
        service = PasswordResetService()
        token = service.request_password_reset(test_user_data["email"])

        # Reset password
        new_password = "NewSecurePassword456!"
        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": str(token),
                "new_password": new_password
            }
        )

        assert response.status_code == 200
        assert "Password has been reset successfully" in response.json()["message"]

        # Verify can login with new password
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user_data["email"],
                "password": new_password
            }
        )

        assert login_response.status_code == 200

        # Verify cannot login with old password
        old_login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user_data["email"],
                "password": test_user_data["password"]
            }
        )

        assert old_login_response.status_code == 401

    def test_reset_password_invalid_token(self, client):
        """Test password reset with invalid token"""
        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": str(uuid4()),
                "new_password": "NewPassword123!"
            }
        )

        assert response.status_code == 400

    # ========================================================================
    # Health Check Tests
    # ========================================================================

    def test_auth_health(self, client):
        """Test authentication health check"""
        response = client.get("/api/v1/auth/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["service"] == "authentication"
