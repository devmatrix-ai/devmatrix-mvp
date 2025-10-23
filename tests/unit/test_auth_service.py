"""
Unit Tests for AuthService

Tests authentication service functionality including:
- User registration
- Login
- Token generation and validation
- Password hashing
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.services.auth_service import AuthService
from src.models.user import User
from src.config.database import get_db_context


class TestAuthService:
    """Test suite for AuthService"""

    @pytest.fixture
    def auth_service(self):
        """Create AuthService instance"""
        return AuthService()

    @pytest.fixture
    def test_user_data(self):
        """Test user data"""
        return {
            "email": f"test_{uuid4()}@example.com",
            "username": f"testuser_{uuid4().hex[:8]}",
            "password": "SecurePassword123!"
        }

    # ========================================================================
    # Password Hashing Tests
    # ========================================================================

    def test_hash_password(self, auth_service):
        """Test password hashing"""
        password = "my_secure_password"
        hashed = auth_service.hash_password(password)

        assert hashed is not None
        assert hashed != password
        assert isinstance(hashed, str)
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_password_correct(self, auth_service):
        """Test password verification with correct password"""
        password = "my_secure_password"
        hashed = auth_service.hash_password(password)

        assert auth_service.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self, auth_service):
        """Test password verification with incorrect password"""
        password = "my_secure_password"
        wrong_password = "wrong_password"
        hashed = auth_service.hash_password(password)

        assert auth_service.verify_password(wrong_password, hashed) is False

    # ========================================================================
    # User Registration Tests
    # ========================================================================

    def test_register_user_success(self, auth_service, test_user_data):
        """Test successful user registration"""
        user = auth_service.register_user(
            email=test_user_data["email"],
            username=test_user_data["username"],
            password=test_user_data["password"]
        )

        assert user is not None
        assert user.email == test_user_data["email"]
        assert user.username == test_user_data["username"]
        assert user.is_active is True
        assert user.is_superuser is False
        assert user.is_verified is True  # Default
        assert user.password_hash != test_user_data["password"]

        # Verify password hash works
        assert auth_service.verify_password(
            test_user_data["password"],
            user.password_hash
        ) is True

    def test_register_user_duplicate_email(self, auth_service, test_user_data):
        """Test registration with duplicate email"""
        # Register first user
        auth_service.register_user(
            email=test_user_data["email"],
            username=test_user_data["username"],
            password=test_user_data["password"]
        )

        # Try to register with same email
        with pytest.raises(ValueError, match="Email already registered"):
            auth_service.register_user(
                email=test_user_data["email"],
                username=f"different_{test_user_data['username']}",
                password=test_user_data["password"]
            )

    def test_register_user_duplicate_username(self, auth_service, test_user_data):
        """Test registration with duplicate username"""
        # Register first user
        auth_service.register_user(
            email=test_user_data["email"],
            username=test_user_data["username"],
            password=test_user_data["password"]
        )

        # Try to register with same username
        with pytest.raises(ValueError, match="Username already taken"):
            auth_service.register_user(
                email=f"different_{test_user_data['email']}",
                username=test_user_data["username"],
                password=test_user_data["password"]
            )

    # ========================================================================
    # Token Generation Tests
    # ========================================================================

    def test_create_access_token(self, auth_service):
        """Test access token creation"""
        user_id = uuid4()
        email = "test@example.com"
        username = "testuser"

        token = auth_service.create_access_token(user_id, email, username)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self, auth_service):
        """Test refresh token creation"""
        user_id = uuid4()

        token = auth_service.create_refresh_token(user_id)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_access_token(self, auth_service):
        """Test access token verification"""
        user_id = uuid4()
        email = "test@example.com"
        username = "testuser"

        token = auth_service.create_access_token(user_id, email, username)
        payload = auth_service.verify_access_token(token)

        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["email"] == email
        assert payload["username"] == username
        assert payload["type"] == "access"

    def test_verify_invalid_token(self, auth_service):
        """Test verification of invalid token"""
        invalid_token = "invalid.token.here"

        payload = auth_service.verify_access_token(invalid_token)

        assert payload is None

    def test_verify_expired_token(self, auth_service):
        """Test verification of expired token"""
        # Create token with very short expiry
        import jwt
        from src.services.auth_service import JWT_SECRET_KEY, JWT_ALGORITHM

        user_id = uuid4()
        expire = datetime.utcnow() - timedelta(seconds=1)  # Already expired

        payload = {
            "sub": str(user_id),
            "email": "test@example.com",
            "username": "testuser",
            "type": "access",
            "exp": expire,
            "iat": datetime.utcnow()
        }

        expired_token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        result = auth_service.verify_access_token(expired_token)

        assert result is None

    # ========================================================================
    # Login Tests
    # ========================================================================

    def test_login_success(self, auth_service, test_user_data):
        """Test successful login"""
        # Register user
        user = auth_service.register_user(
            email=test_user_data["email"],
            username=test_user_data["username"],
            password=test_user_data["password"]
        )

        # Login
        tokens = auth_service.login(
            email=test_user_data["email"],
            password=test_user_data["password"]
        )

        assert tokens is not None
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "token_type" in tokens
        assert tokens["token_type"] == "bearer"
        assert "expires_in" in tokens
        assert "user" in tokens

        # Verify tokens are valid
        access_payload = auth_service.verify_access_token(tokens["access_token"])
        assert access_payload["sub"] == str(user.user_id)

        refresh_payload = auth_service.verify_refresh_token(tokens["refresh_token"])
        assert refresh_payload["sub"] == str(user.user_id)

    def test_login_invalid_email(self, auth_service):
        """Test login with non-existent email"""
        with pytest.raises(ValueError, match="Invalid email or password"):
            auth_service.login(
                email="nonexistent@example.com",
                password="anypassword"
            )

    def test_login_invalid_password(self, auth_service, test_user_data):
        """Test login with incorrect password"""
        # Register user
        auth_service.register_user(
            email=test_user_data["email"],
            username=test_user_data["username"],
            password=test_user_data["password"]
        )

        # Try login with wrong password
        with pytest.raises(ValueError, match="Invalid email or password"):
            auth_service.login(
                email=test_user_data["email"],
                password="WrongPassword123!"
            )

    def test_login_inactive_user(self, auth_service, test_user_data):
        """Test login with inactive account"""
        # Register user
        user = auth_service.register_user(
            email=test_user_data["email"],
            username=test_user_data["username"],
            password=test_user_data["password"]
        )

        # Deactivate user
        with get_db_context() as db:
            db_user = db.query(User).filter(User.user_id == user.user_id).first()
            db_user.is_active = False
            db.commit()

        # Try login
        with pytest.raises(ValueError, match="Account is inactive"):
            auth_service.login(
                email=test_user_data["email"],
                password=test_user_data["password"]
            )

    # ========================================================================
    # Token Refresh Tests
    # ========================================================================

    def test_refresh_access_token_success(self, auth_service, test_user_data):
        """Test successful token refresh"""
        # Register and login
        auth_service.register_user(
            email=test_user_data["email"],
            username=test_user_data["username"],
            password=test_user_data["password"]
        )

        login_tokens = auth_service.login(
            email=test_user_data["email"],
            password=test_user_data["password"]
        )

        # Refresh token
        new_tokens = auth_service.refresh_access_token(login_tokens["refresh_token"])

        assert new_tokens is not None
        assert "access_token" in new_tokens
        assert "token_type" in new_tokens
        assert new_tokens["token_type"] == "bearer"

        # Verify new access token is valid
        payload = auth_service.verify_access_token(new_tokens["access_token"])
        assert payload is not None

    def test_refresh_with_invalid_token(self, auth_service):
        """Test token refresh with invalid token"""
        with pytest.raises(ValueError, match="Invalid or expired refresh token"):
            auth_service.refresh_access_token("invalid.token.here")

    def test_refresh_with_access_token(self, auth_service, test_user_data):
        """Test token refresh with access token (should fail)"""
        # Register and login
        user = auth_service.register_user(
            email=test_user_data["email"],
            username=test_user_data["username"],
            password=test_user_data["password"]
        )

        # Create access token
        access_token = auth_service.create_access_token(
            user.user_id,
            user.email,
            user.username
        )

        # Try to use access token for refresh (should fail)
        with pytest.raises(ValueError, match="Invalid or expired refresh token"):
            auth_service.refresh_access_token(access_token)

    # ========================================================================
    # Get Current User Tests
    # ========================================================================

    def test_get_current_user_success(self, auth_service, test_user_data):
        """Test getting current user from valid token"""
        # Register user
        user = auth_service.register_user(
            email=test_user_data["email"],
            username=test_user_data["username"],
            password=test_user_data["password"]
        )

        # Create access token
        token = auth_service.create_access_token(
            user.user_id,
            user.email,
            user.username
        )

        # Get current user
        current_user = auth_service.get_current_user(token)

        assert current_user is not None
        assert current_user.user_id == user.user_id
        assert current_user.email == user.email
        assert current_user.username == user.username

    def test_get_current_user_invalid_token(self, auth_service):
        """Test getting current user with invalid token"""
        current_user = auth_service.get_current_user("invalid.token.here")

        assert current_user is None

    def test_get_current_user_nonexistent_user(self, auth_service):
        """Test getting current user for deleted user"""
        # Create token for non-existent user
        fake_user_id = uuid4()
        token = auth_service.create_access_token(
            fake_user_id,
            "fake@example.com",
            "fakeuser"
        )

        # Try to get user
        current_user = auth_service.get_current_user(token)

        assert current_user is None
