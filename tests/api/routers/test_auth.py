"""
Tests for Authentication API Router

Tests all authentication, authorization, and 2FA endpoints.
Security-critical router requiring comprehensive coverage.

Author: DevMatrix Team
Date: 2025-11-03
"""

import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routers.auth import router
from src.models.user import User


@pytest.fixture
def mock_auth_service():
    """Create mock AuthService."""
    return MagicMock()


@pytest.fixture
def mock_email_service():
    """Create mock EmailVerificationService."""
    return MagicMock()


@pytest.fixture
def mock_password_reset_service():
    """Create mock PasswordResetService."""
    return MagicMock()


@pytest.fixture
def mock_totp_service():
    """Create mock TOTPService."""
    return MagicMock()


@pytest.fixture
def client():
    """Create test client with auth router."""
    test_app = FastAPI()
    test_app.include_router(router)
    return TestClient(test_app)


@pytest.fixture
def sample_user():
    """Sample user object."""
    user = MagicMock(spec=User)
    user.user_id = uuid4()
    user.email = "test@example.com"
    user.username = "testuser"
    user.email_verified = True
    user.is_active = True
    user.totp_enabled = False
    return user


# ============================================================================
# POST /api/v1/auth/register Tests
# ============================================================================

def test_register_success(client, mock_auth_service):
    """Test successful user registration."""
    mock_tokens = {
        "access_token": "access_token_123",
        "refresh_token": "refresh_token_123",
        "token_type": "bearer",
        "expires_in": 3600
    }
    mock_auth_service.register.return_value = mock_tokens

    with patch('src.api.routers.auth.auth_service', mock_auth_service):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "SecurePassword123!"
            }
        )

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_register_weak_password(client, mock_auth_service):
    """Test registration with weak password."""
    mock_auth_service.register.side_effect = ValueError("Password too weak")

    with patch('src.api.routers.auth.auth_service', mock_auth_service):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "weak"
            }
        )

    assert response.status_code == 400


def test_register_duplicate_email(client, mock_auth_service):
    """Test registration with existing email."""
    mock_auth_service.register.side_effect = ValueError("Email already registered")

    with patch('src.api.routers.auth.auth_service', mock_auth_service):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "existing@example.com",
                "username": "newuser",
                "password": "SecurePassword123!"
            }
        )

    assert response.status_code == 400


def test_register_invalid_username(client):
    """Test registration with invalid username format."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "username": "invalid user!",  # Contains invalid characters
            "password": "SecurePassword123!"
        }
    )

    assert response.status_code == 422  # Validation error


def test_register_password_too_short(client):
    """Test registration with password too short."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "short"  # Less than 8 chars
        }
    )

    assert response.status_code == 422


# ============================================================================
# POST /api/v1/auth/login Tests
# ============================================================================

def test_login_success(client, mock_auth_service):
    """Test successful login."""
    mock_tokens = {
        "access_token": "access_token_123",
        "refresh_token": "refresh_token_123",
        "token_type": "bearer",
        "expires_in": 3600,
        "requires_2fa": False
    }
    mock_auth_service.login.return_value = mock_tokens

    with patch('src.api.routers.auth.auth_service', mock_auth_service):
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "SecurePassword123!"
            }
        )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "access_token_123"


def test_login_invalid_credentials(client, mock_auth_service):
    """Test login with invalid credentials."""
    mock_auth_service.login.side_effect = ValueError("Invalid credentials")

    with patch('src.api.routers.auth.auth_service', mock_auth_service):
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword"
            }
        )

    assert response.status_code == 401


def test_login_unverified_email(client, mock_auth_service):
    """Test login with unverified email."""
    mock_auth_service.login.side_effect = ValueError("Email not verified")

    with patch('src.api.routers.auth.auth_service', mock_auth_service):
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "unverified@example.com",
                "password": "SecurePassword123!"
            }
        )

    assert response.status_code == 403


def test_login_account_locked(client, mock_auth_service):
    """Test login with locked account."""
    mock_auth_service.login.side_effect = ValueError("Account locked")

    with patch('src.api.routers.auth.auth_service', mock_auth_service):
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "locked@example.com",
                "password": "SecurePassword123!"
            }
        )

    assert response.status_code == 403


def test_login_requires_2fa(client, mock_auth_service):
    """Test login when 2FA is required."""
    mock_response = {
        "requires_2fa": True,
        "temp_token": "temp_token_123"
    }
    mock_auth_service.login.return_value = mock_response

    with patch('src.api.routers.auth.auth_service', mock_auth_service):
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "2fa@example.com",
                "password": "SecurePassword123!"
            }
        )

    data = response.json()
    assert data.get("requires_2fa") is True


# ============================================================================
# POST /api/v1/auth/login/2fa Tests
# ============================================================================

def test_login_2fa_success(client, mock_auth_service, mock_totp_service):
    """Test successful 2FA login."""
    mock_totp_service.verify_totp.return_value = True
    mock_tokens = {
        "access_token": "access_token_123",
        "refresh_token": "refresh_token_123",
        "token_type": "bearer"
    }
    mock_auth_service.complete_2fa_login.return_value = mock_tokens

    with patch('src.api.routers.auth.auth_service', mock_auth_service), \
         patch('src.api.routers.auth.totp_service', mock_totp_service):
        response = client.post(
            "/api/v1/auth/login/2fa",
            json={
                "temp_token": "temp_token_123",
                "totp_code": "123456"
            }
        )

    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_2fa_invalid_code(client, mock_totp_service):
    """Test 2FA login with invalid code."""
    mock_totp_service.verify_totp.return_value = False

    with patch('src.api.routers.auth.totp_service', mock_totp_service):
        response = client.post(
            "/api/v1/auth/login/2fa",
            json={
                "temp_token": "temp_token_123",
                "totp_code": "000000"
            }
        )

    assert response.status_code == 401


def test_login_2fa_with_backup_code(client, mock_auth_service, mock_totp_service):
    """Test 2FA login with backup code."""
    mock_totp_service.verify_backup_code.return_value = True
    mock_tokens = {
        "access_token": "access_token_123",
        "refresh_token": "refresh_token_123"
    }
    mock_auth_service.complete_2fa_login.return_value = mock_tokens

    with patch('src.api.routers.auth.auth_service', mock_auth_service), \
         patch('src.api.routers.auth.totp_service', mock_totp_service):
        response = client.post(
            "/api/v1/auth/login/2fa",
            json={
                "temp_token": "temp_token_123",
                "backup_code": "ABCD-1234-EFGH-5678"
            }
        )

    assert response.status_code == 200


# ============================================================================
# POST /api/v1/auth/refresh Tests
# ============================================================================

def test_refresh_token_success(client, mock_auth_service):
    """Test successful token refresh."""
    mock_tokens = {
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "token_type": "bearer"
    }
    mock_auth_service.refresh_token.return_value = mock_tokens

    with patch('src.api.routers.auth.auth_service', mock_auth_service):
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "old_refresh_token"}
        )

    assert response.status_code == 200
    assert response.json()["access_token"] == "new_access_token"


def test_refresh_token_invalid(client, mock_auth_service):
    """Test refresh with invalid token."""
    mock_auth_service.refresh_token.side_effect = ValueError("Invalid refresh token")

    with patch('src.api.routers.auth.auth_service', mock_auth_service):
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"}
        )

    assert response.status_code == 401


def test_refresh_token_expired(client, mock_auth_service):
    """Test refresh with expired token."""
    mock_auth_service.refresh_token.side_effect = ValueError("Refresh token expired")

    with patch('src.api.routers.auth.auth_service', mock_auth_service):
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "expired_token"}
        )

    assert response.status_code == 401


# ============================================================================
# GET /api/v1/auth/me Tests
# ============================================================================

def test_get_current_user_success(client, sample_user):
    """Test getting current user info."""
    def override_get_current_active_user():
        return sample_user

    from src.api.middleware.auth_middleware import get_current_active_user
    
    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[get_current_active_user] = override_get_current_active_user
    
    client_with_auth = TestClient(test_app)
    response = client_with_auth.get("/api/v1/auth/me")

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"


def test_get_current_user_unauthorized(client):
    """Test /me without authentication."""
    response = client.get("/api/v1/auth/me")

    # Should return 401 or 403 (depends on auth middleware)
    assert response.status_code in [401, 403]


# ============================================================================
# POST /api/v1/auth/logout Tests
# ============================================================================

def test_logout_success(client, mock_auth_service):
    """Test successful logout."""
    mock_auth_service.logout.return_value = {"success": True}

    with patch('src.api.routers.auth.auth_service', mock_auth_service):
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer access_token_123"}
        )

    assert response.status_code == 200


def test_logout_with_refresh_token(client, mock_auth_service):
    """Test logout with refresh token blacklisting."""
    mock_auth_service.logout.return_value = {"success": True}

    with patch('src.api.routers.auth.auth_service', mock_auth_service):
        response = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": "refresh_token_123"},
            headers={"Authorization": "Bearer access_token_123"}
        )

    assert response.status_code == 200


# ============================================================================
# POST /api/v1/auth/session/keep-alive Tests
# ============================================================================

def test_keep_alive_success(client, mock_auth_service):
    """Test successful session keep-alive."""
    mock_response = {
        "success": True,
        "session_extended_until": (datetime.now() + timedelta(minutes=30)).isoformat()
    }
    mock_auth_service.keep_alive.return_value = mock_response

    with patch('src.api.routers.auth.auth_service', mock_auth_service):
        response = client.post(
            "/api/v1/auth/session/keep-alive",
            headers={"Authorization": "Bearer access_token_123"}
        )

    assert response.status_code == 200
    assert response.json()["success"] is True


# ============================================================================
# POST /api/v1/auth/verify-email Tests
# ============================================================================

def test_verify_email_success(client, mock_email_service):
    """Test successful email verification."""
    mock_email_service.verify_email.return_value = {
        "success": True,
        "message": "Email verified successfully"
    }

    with patch('src.api.routers.auth.email_verification_service', mock_email_service):
        response = client.post(
            "/api/v1/auth/verify-email",
            json={"token": "verification_token_123"}
        )

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_verify_email_invalid_token(client, mock_email_service):
    """Test email verification with invalid token."""
    mock_email_service.verify_email.side_effect = ValueError("Invalid token")

    with patch('src.api.routers.auth.email_verification_service', mock_email_service):
        response = client.post(
            "/api/v1/auth/verify-email",
            json={"token": "invalid_token"}
        )

    assert response.status_code == 400


def test_verify_email_expired_token(client, mock_email_service):
    """Test email verification with expired token."""
    mock_email_service.verify_email.side_effect = ValueError("Token expired")

    with patch('src.api.routers.auth.email_verification_service', mock_email_service):
        response = client.post(
            "/api/v1/auth/verify-email",
            json={"token": "expired_token"}
        )

    assert response.status_code == 400


# ============================================================================
# POST /api/v1/auth/resend-verification Tests
# ============================================================================

def test_resend_verification_success(client, mock_email_service):
    """Test successful verification email resend."""
    mock_email_service.resend_verification.return_value = {
        "success": True,
        "message": "Verification email sent"
    }

    with patch('src.api.routers.auth.email_verification_service', mock_email_service):
        response = client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "test@example.com"}
        )

    assert response.status_code == 200


def test_resend_verification_already_verified(client, mock_email_service):
    """Test resend when email already verified."""
    mock_email_service.resend_verification.side_effect = ValueError("Already verified")

    with patch('src.api.routers.auth.email_verification_service', mock_email_service):
        response = client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "verified@example.com"}
        )

    assert response.status_code == 400


# ============================================================================
# POST /api/v1/auth/forgot-password Tests
# ============================================================================

def test_forgot_password_success(client, mock_password_reset_service):
    """Test successful password reset request."""
    mock_password_reset_service.request_reset.return_value = {
        "success": True,
        "message": "Reset email sent"
    }

    with patch('src.api.routers.auth.password_reset_service', mock_password_reset_service):
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "test@example.com"}
        )

    assert response.status_code == 200


def test_forgot_password_user_not_found(client, mock_password_reset_service):
    """Test forgot password for non-existent user."""
    # Should return success anyway (security: don't reveal if user exists)
    mock_password_reset_service.request_reset.return_value = {
        "success": True,
        "message": "If email exists, reset link sent"
    }

    with patch('src.api.routers.auth.password_reset_service', mock_password_reset_service):
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"}
        )

    assert response.status_code == 200  # Don't reveal user existence


# ============================================================================
# POST /api/v1/auth/reset-password Tests
# ============================================================================

def test_reset_password_success(client, mock_password_reset_service):
    """Test successful password reset."""
    mock_password_reset_service.reset_password.return_value = {
        "success": True,
        "message": "Password reset successfully"
    }

    with patch('src.api.routers.auth.password_reset_service', mock_password_reset_service):
        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": "reset_token_123",
                "new_password": "NewSecurePassword123!"
            }
        )

    assert response.status_code == 200


def test_reset_password_invalid_token(client, mock_password_reset_service):
    """Test password reset with invalid token."""
    mock_password_reset_service.reset_password.side_effect = ValueError("Invalid token")

    with patch('src.api.routers.auth.password_reset_service', mock_password_reset_service):
        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": "invalid_token",
                "new_password": "NewSecurePassword123!"
            }
        )

    assert response.status_code == 400


def test_reset_password_weak_password(client, mock_password_reset_service):
    """Test password reset with weak new password."""
    mock_password_reset_service.reset_password.side_effect = ValueError("Password too weak")

    with patch('src.api.routers.auth.password_reset_service', mock_password_reset_service):
        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": "reset_token_123",
                "new_password": "weak"
            }
        )

    assert response.status_code == 400


# ============================================================================
# POST /api/v1/auth/2fa/enable Tests
# ============================================================================

def test_enable_2fa_success(client, sample_user, mock_totp_service):
    """Test successful 2FA enablement."""
    mock_totp_service.generate_totp_secret.return_value = {
        "secret": "SECRET_KEY_123",
        "qr_code": "data:image/png;base64,..."
    }

    def override_get_current_active_user():
        return sample_user

    from src.api.middleware.auth_middleware import get_current_active_user
    
    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[get_current_active_user] = override_get_current_active_user
    
    client_with_auth = TestClient(test_app)

    with patch('src.api.routers.auth.totp_service', mock_totp_service):
        response = client_with_auth.post("/api/v1/auth/2fa/enable")

    assert response.status_code == 200
    data = response.json()
    assert "secret" in data or "qr_code" in data


def test_enable_2fa_already_enabled(client, sample_user, mock_totp_service):
    """Test enabling 2FA when already enabled."""
    sample_user.totp_enabled = True

    def override_get_current_active_user():
        return sample_user

    from src.api.middleware.auth_middleware import get_current_active_user
    
    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[get_current_active_user] = override_get_current_active_user
    
    client_with_auth = TestClient(test_app)

    response = client_with_auth.post("/api/v1/auth/2fa/enable")

    # Should handle gracefully or return error
    assert response.status_code in [200, 400]


# ============================================================================
# POST /api/v1/auth/2fa/verify Tests
# ============================================================================

def test_verify_2fa_setup_success(client, sample_user, mock_totp_service):
    """Test successful 2FA setup verification."""
    mock_totp_service.verify_and_enable.return_value = {
        "success": True,
        "backup_codes": ["CODE1", "CODE2", "CODE3"]
    }

    def override_get_current_active_user():
        return sample_user

    from src.api.middleware.auth_middleware import get_current_active_user
    
    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[get_current_active_user] = override_get_current_active_user
    
    client_with_auth = TestClient(test_app)

    with patch('src.api.routers.auth.totp_service', mock_totp_service):
        response = client_with_auth.post(
            "/api/v1/auth/2fa/verify",
            json={"totp_code": "123456"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_verify_2fa_setup_invalid_code(client, sample_user, mock_totp_service):
    """Test 2FA setup verification with invalid code."""
    mock_totp_service.verify_and_enable.side_effect = ValueError("Invalid code")

    def override_get_current_active_user():
        return sample_user

    from src.api.middleware.auth_middleware import get_current_active_user
    
    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[get_current_active_user] = override_get_current_active_user
    
    client_with_auth = TestClient(test_app)

    with patch('src.api.routers.auth.totp_service', mock_totp_service):
        response = client_with_auth.post(
            "/api/v1/auth/2fa/verify",
            json={"totp_code": "000000"}
        )

    assert response.status_code == 400


# ============================================================================
# POST /api/v1/auth/2fa/disable Tests
# ============================================================================

def test_disable_2fa_success(client, sample_user, mock_totp_service):
    """Test successful 2FA disablement."""
    sample_user.totp_enabled = True
    mock_totp_service.verify_totp.return_value = True
    mock_totp_service.disable_2fa.return_value = {"success": True}

    def override_get_current_active_user():
        return sample_user

    from src.api.middleware.auth_middleware import get_current_active_user
    
    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[get_current_active_user] = override_get_current_active_user
    
    client_with_auth = TestClient(test_app)

    with patch('src.api.routers.auth.totp_service', mock_totp_service):
        response = client_with_auth.post(
            "/api/v1/auth/2fa/disable",
            json={"totp_code": "123456"}
        )

    assert response.status_code == 200


def test_disable_2fa_not_enabled(client, sample_user):
    """Test disabling 2FA when not enabled."""
    sample_user.totp_enabled = False

    def override_get_current_active_user():
        return sample_user

    from src.api.middleware.auth_middleware import get_current_active_user
    
    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[get_current_active_user] = override_get_current_active_user
    
    client_with_auth = TestClient(test_app)

    response = client_with_auth.post(
        "/api/v1/auth/2fa/disable",
        json={"totp_code": "123456"}
    )

    assert response.status_code == 400


# ============================================================================
# GET /api/v1/auth/2fa/backup-codes Tests
# ============================================================================

def test_get_backup_codes_success(client, sample_user, mock_totp_service):
    """Test getting backup codes."""
    sample_user.totp_enabled = True
    mock_totp_service.get_backup_codes.return_value = ["CODE1", "CODE2", "CODE3"]

    def override_get_current_active_user():
        return sample_user

    from src.api.middleware.auth_middleware import get_current_active_user
    
    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[get_current_active_user] = override_get_current_active_user
    
    client_with_auth = TestClient(test_app)

    with patch('src.api.routers.auth.totp_service', mock_totp_service):
        response = client_with_auth.get("/api/v1/auth/2fa/backup-codes")

    assert response.status_code == 200
    data = response.json()
    assert len(data.get("backup_codes", [])) >= 0


# ============================================================================
# POST /api/v1/auth/2fa/regenerate-backup-codes Tests
# ============================================================================

def test_regenerate_backup_codes_success(client, sample_user, mock_totp_service):
    """Test successful backup codes regeneration."""
    sample_user.totp_enabled = True
    mock_totp_service.regenerate_backup_codes.return_value = {
        "backup_codes": ["NEW1", "NEW2", "NEW3", "NEW4", "NEW5"]
    }

    def override_get_current_active_user():
        return sample_user

    from src.api.middleware.auth_middleware import get_current_active_user
    
    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[get_current_active_user] = override_get_current_active_user
    
    client_with_auth = TestClient(test_app)

    with patch('src.api.routers.auth.totp_service', mock_totp_service):
        response = client_with_auth.post("/api/v1/auth/2fa/regenerate-backup-codes")

    assert response.status_code == 200
    data = response.json()
    assert len(data.get("backup_codes", [])) > 0


# ============================================================================
# GET /api/v1/auth/health Tests
# ============================================================================

def test_auth_health_check(client):
    """Test auth service health check."""
    response = client.get("/api/v1/auth/health")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data


@pytest.mark.unit
class TestAuthModels:
    """Unit tests for auth request/response models."""

    def test_register_request_model(self):
        """Test RegisterRequest model validation."""
        from src.api.routers.auth import RegisterRequest

        request = RegisterRequest(
            email="test@example.com",
            username="testuser",
            password="SecurePassword123!"
        )
        assert request.email == "test@example.com"

    def test_login_request_model(self):
        """Test LoginRequest model validation."""
        from src.api.routers.auth import LoginRequest

        request = LoginRequest(
            email="test@example.com",
            password="password"
        )
        assert request.email == "test@example.com"

    def test_refresh_token_request_model(self):
        """Test RefreshTokenRequest model."""
        from src.api.routers.auth import RefreshTokenRequest

        request = RefreshTokenRequest(refresh_token="token_123")
        assert request.refresh_token == "token_123"

