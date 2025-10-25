"""
Unit Tests: Authentication Security Layer

Tests for JWT token blacklist, logout functionality, and jti claims.
Part of Phase 1 Critical Security Vulnerabilities - Group 3.

Test Coverage:
- jti claim in access tokens
- jti claim in refresh tokens
- Logout adds access token to blacklist
- Logout adds refresh token to blacklist
- Blacklisted access token rejected with 401
- Blacklisted refresh token rejected with 401
- Blacklist TTL matches token expiration
- Token reuse after logout fails
"""

import pytest
import uuid
import os
import jwt
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

# Set test environment variables before any imports
os.environ.setdefault('JWT_SECRET', 'test_secret_key_that_is_32_chars_min_for_validation_testing')
os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost:5432/test')
os.environ.setdefault('CORS_ALLOWED_ORIGINS', 'http://localhost:3000')


class TestJtiClaims:
    """Tests for jti claim in JWT tokens."""

    def test_jti_claim_included_in_access_tokens(self):
        """Test jti claim is included in access tokens."""
        from src.services.auth_service import AuthService
        from src.config.settings import get_settings

        settings = get_settings()
        auth_service = AuthService()

        # Create access token
        user_id = uuid.uuid4()
        token = auth_service.create_access_token(
            user_id=user_id,
            email="test@example.com",
            username="testuser"
        )

        # Decode token
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

        # Verify jti exists and is valid UUID
        assert "jti" in payload, "jti claim should be present in access token"
        assert payload.get("type") == "access", "Token type should be 'access'"

        # Verify jti is valid UUID
        try:
            uuid.UUID(payload["jti"])
        except ValueError:
            pytest.fail("jti is not a valid UUID")

    def test_jti_claim_included_in_refresh_tokens(self):
        """Test jti claim is included in refresh tokens."""
        from src.services.auth_service import AuthService
        from src.config.settings import get_settings

        settings = get_settings()
        auth_service = AuthService()

        # Create refresh token
        user_id = uuid.uuid4()
        token = auth_service.create_refresh_token(user_id=user_id)

        # Decode token
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

        # Verify jti exists and is valid UUID
        assert "jti" in payload, "jti claim should be present in refresh token"
        assert payload.get("type") == "refresh", "Token type should be 'refresh'"

        # Verify jti is valid UUID
        try:
            uuid.UUID(payload["jti"])
        except ValueError:
            pytest.fail("jti is not a valid UUID")


class TestTokenBlacklist:
    """Tests for token blacklist functionality."""

    def test_check_token_blacklist_raises_401_for_blacklisted_token(self):
        """Test blacklisted tokens are rejected with 401."""
        from src.services.auth_service import AuthService, get_redis_client

        # Mock Redis client
        mock_redis_manager = MagicMock()
        mock_redis_manager.connected = True
        mock_redis_manager.client = MagicMock()
        mock_redis_manager.client.get.return_value = "1"  # Token is blacklisted

        with patch('src.services.auth_service.get_redis_client', return_value=mock_redis_manager):
            auth_service = AuthService()

            # Create a token payload with jti
            payload = {
                "sub": str(uuid.uuid4()),
                "jti": str(uuid.uuid4()),
                "type": "access",
                "exp": datetime.utcnow() + timedelta(hours=1)
            }

            # Should raise HTTPException(401)
            with pytest.raises(HTTPException) as exc_info:
                auth_service.check_token_blacklist(payload)

            assert exc_info.value.status_code == 401
            assert "revoked" in exc_info.value.detail.lower()

    def test_check_token_blacklist_allows_non_blacklisted_token(self):
        """Test non-blacklisted tokens are allowed."""
        from src.services.auth_service import AuthService

        # Mock Redis client
        mock_redis_manager = MagicMock()
        mock_redis_manager.connected = True
        mock_redis_manager.client = MagicMock()
        mock_redis_manager.client.get.return_value = None  # Token is NOT blacklisted

        with patch('src.services.auth_service.get_redis_client', return_value=mock_redis_manager):
            auth_service = AuthService()

            # Create a token payload with jti
            payload = {
                "sub": str(uuid.uuid4()),
                "jti": str(uuid.uuid4()),
                "type": "access",
                "exp": datetime.utcnow() + timedelta(hours=1)
            }

            # Should not raise exception
            result = auth_service.check_token_blacklist(payload)
            assert result == payload


class TestLogoutEndpoint:
    """Tests for logout endpoint."""

    def test_logout_adds_access_token_to_blacklist(self):
        """Test logout adds access token to blacklist."""
        from src.services.auth_service import AuthService

        # Mock Redis client
        mock_redis_manager = MagicMock()
        mock_redis_manager.connected = True
        mock_redis_manager.client = MagicMock()

        with patch('src.services.auth_service.get_redis_client', return_value=mock_redis_manager):
            auth_service = AuthService()

            # Create access token with jti
            user_id = uuid.uuid4()
            access_token = auth_service.create_access_token(
                user_id=user_id,
                email="test@example.com",
                username="testuser"
            )

            # Blacklist the token
            auth_service.blacklist_token(access_token, token_type="access")

            # Verify setex called with correct parameters
            assert mock_redis_manager.client.setex.called
            call_args = mock_redis_manager.client.setex.call_args[0]

            # Verify key format: blacklist:access:{jti}
            assert call_args[0].startswith("blacklist:access:")
            # Verify TTL matches access token expiration (3600 seconds)
            assert call_args[1] == 3600
            # Verify value is "1"
            assert call_args[2] == "1"

    def test_logout_adds_refresh_token_to_blacklist(self):
        """Test logout adds refresh token to blacklist."""
        from src.services.auth_service import AuthService

        # Mock Redis client
        mock_redis_manager = MagicMock()
        mock_redis_manager.connected = True
        mock_redis_manager.client = MagicMock()

        with patch('src.services.auth_service.get_redis_client', return_value=mock_redis_manager):
            auth_service = AuthService()

            # Create refresh token with jti
            user_id = uuid.uuid4()
            refresh_token = auth_service.create_refresh_token(user_id=user_id)

            # Blacklist the token
            auth_service.blacklist_token(refresh_token, token_type="refresh")

            # Verify setex called with correct parameters
            assert mock_redis_manager.client.setex.called
            call_args = mock_redis_manager.client.setex.call_args[0]

            # Verify key format: blacklist:refresh:{jti}
            assert call_args[0].startswith("blacklist:refresh:")
            # Verify TTL matches refresh token expiration (30 days = 2592000 seconds)
            assert call_args[1] == 2592000
            # Verify value is "1"
            assert call_args[2] == "1"

    def test_blacklist_ttl_matches_token_expiration(self):
        """Test blacklist TTL matches token expiration times."""
        from src.services.auth_service import AuthService
        from src.config.settings import get_settings

        settings = get_settings()

        # Mock Redis client
        mock_redis_manager = MagicMock()
        mock_redis_manager.connected = True
        mock_redis_manager.client = MagicMock()

        with patch('src.services.auth_service.get_redis_client', return_value=mock_redis_manager):
            auth_service = AuthService()

            # Create access token
            user_id = uuid.uuid4()
            access_token = auth_service.create_access_token(
                user_id=user_id,
                email="test@example.com",
                username="testuser"
            )

            # Blacklist access token
            auth_service.blacklist_token(access_token, token_type="access")

            # Verify TTL matches access token expiration
            call_args = mock_redis_manager.client.setex.call_args[0]
            expected_ttl = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
            assert call_args[1] == expected_ttl

            # Reset mock
            mock_redis_manager.client.reset_mock()

            # Create refresh token
            refresh_token = auth_service.create_refresh_token(user_id=user_id)

            # Blacklist refresh token
            auth_service.blacklist_token(refresh_token, token_type="refresh")

            # Verify TTL matches refresh token expiration
            call_args = mock_redis_manager.client.setex.call_args[0]
            expected_ttl = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
            assert call_args[1] == expected_ttl


class TestTokenReuseAfterLogout:
    """Tests for token reuse prevention after logout."""

    def test_token_reuse_after_logout_fails(self):
        """Test token cannot be reused after logout."""
        from src.services.auth_service import AuthService
        from src.config.settings import get_settings

        settings = get_settings()

        # Mock Redis client - return None first (not blacklisted), then "1" (blacklisted)
        mock_redis_manager = MagicMock()
        mock_redis_manager.connected = True
        mock_redis_manager.client = MagicMock()

        with patch('src.services.auth_service.get_redis_client', return_value=mock_redis_manager):
            auth_service = AuthService()

            # Create access token
            user_id = uuid.uuid4()
            access_token = auth_service.create_access_token(
                user_id=user_id,
                email="test@example.com",
                username="testuser"
            )

            # Decode token to get payload
            payload = jwt.decode(access_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

            # First verification should pass (not blacklisted)
            mock_redis_manager.client.get.return_value = None
            result = auth_service.check_token_blacklist(payload)
            assert result == payload

            # Blacklist the token (simulate logout)
            auth_service.blacklist_token(access_token, token_type="access")
            assert mock_redis_manager.client.setex.called

            # Second verification should fail (now blacklisted)
            mock_redis_manager.client.get.return_value = "1"
            with pytest.raises(HTTPException) as exc_info:
                auth_service.check_token_blacklist(payload)

            assert exc_info.value.status_code == 401
