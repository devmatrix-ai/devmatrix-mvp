"""
Authentication Service

Handles user authentication, JWT token generation/validation, and password hashing.
"""

import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

from src.models.user import User
from src.config.database import get_db_context
from src.observability import get_logger

logger = get_logger("auth_service")

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production-IMPORTANT")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))  # 1 hour
JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "30"))  # 30 days


class AuthService:
    """
    Authentication service for user management and JWT tokens.

    Usage:
        auth = AuthService()

        # Register new user
        user = auth.register_user(email="user@example.com", username="john", password="secret123")

        # Login
        tokens = auth.login(email="user@example.com", password="secret123")

        # Verify token
        user_id = auth.verify_access_token(tokens["access_token"])

        # Refresh token
        new_tokens = auth.refresh_access_token(tokens["refresh_token"])
    """

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify password against hash.

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password from database

        Returns:
            True if password matches, False otherwise
        """
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )

    @staticmethod
    def create_access_token(user_id: UUID, email: str, username: str) -> str:
        """
        Create JWT access token.

        Args:
            user_id: User UUID
            email: User email
            username: Username

        Returns:
            JWT access token string
        """
        expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

        payload = {
            "sub": str(user_id),  # Subject (user_id)
            "email": email,
            "username": username,
            "type": "access",
            "exp": expire,
            "iat": datetime.utcnow()
        }

        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        logger.debug(f"Created access token for user {user_id}")
        return token

    @staticmethod
    def create_refresh_token(user_id: UUID) -> str:
        """
        Create JWT refresh token.

        Args:
            user_id: User UUID

        Returns:
            JWT refresh token string
        """
        expire = datetime.utcnow() + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)

        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "exp": expire,
            "iat": datetime.utcnow()
        }

        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        logger.debug(f"Created refresh token for user {user_id}")
        return token

    @staticmethod
    def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode JWT access token.

        Args:
            token: JWT access token

        Returns:
            Decoded payload dict or None if invalid
        """
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

            # Verify token type
            if payload.get("type") != "access":
                logger.warning("Invalid token type (expected access)")
                return None

            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Access token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid access token: {str(e)}")
            return None

    @staticmethod
    def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode JWT refresh token.

        Args:
            token: JWT refresh token

        Returns:
            Decoded payload dict or None if invalid
        """
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

            # Verify token type
            if payload.get("type") != "refresh":
                logger.warning("Invalid token type (expected refresh)")
                return None

            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Refresh token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid refresh token: {str(e)}")
            return None

    def register_user(self, email: str, username: str, password: str) -> User:
        """
        Register new user.

        Args:
            email: User email
            username: Username
            password: Plain text password

        Returns:
            Created User object

        Raises:
            ValueError: If email or username already exists
        """
        with get_db_context() as db:
            # Check if email already exists
            existing_user = db.query(User).filter(User.email == email).first()
            if existing_user:
                logger.warning(f"Registration failed: Email {email} already exists")
                raise ValueError("Email already registered")

            # Check if username already exists
            existing_username = db.query(User).filter(User.username == username).first()
            if existing_username:
                logger.warning(f"Registration failed: Username {username} already exists")
                raise ValueError("Username already taken")

            # Hash password
            password_hash = self.hash_password(password)

            # Create user
            user = User(
                email=email,
                username=username,
                password_hash=password_hash,
                is_active=True,
                is_superuser=False
            )

            db.add(user)
            db.commit()
            db.refresh(user)

            logger.info(f"User registered successfully: {user.user_id} ({email})")
            return user

    def login(self, email: str, password: str) -> Dict[str, str]:
        """
        Authenticate user and generate tokens.

        Args:
            email: User email
            password: Plain text password

        Returns:
            Dict with access_token and refresh_token

        Raises:
            ValueError: If authentication fails
        """
        with get_db_context() as db:
            # Find user by email
            user = db.query(User).filter(User.email == email).first()

            if not user:
                logger.warning(f"Login failed: User not found ({email})")
                raise ValueError("Invalid email or password")

            # Verify password
            if not self.verify_password(password, user.password_hash):
                logger.warning(f"Login failed: Invalid password for {email}")
                raise ValueError("Invalid email or password")

            # Check if account is active
            if not user.is_active:
                logger.warning(f"Login failed: Account inactive ({email})")
                raise ValueError("Account is inactive")

            # Update last login
            user.last_login_at = datetime.utcnow()
            db.commit()

            # Generate tokens
            access_token = self.create_access_token(
                user_id=user.user_id,
                email=user.email,
                username=user.username
            )
            refresh_token = self.create_refresh_token(user_id=user.user_id)

            logger.info(f"User logged in successfully: {user.user_id} ({email})")

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # seconds
                "user": user.to_dict()
            }

    def refresh_access_token(self, refresh_token: str) -> Dict[str, str]:
        """
        Generate new access token from refresh token.

        Args:
            refresh_token: JWT refresh token

        Returns:
            Dict with new access_token

        Raises:
            ValueError: If refresh token is invalid
        """
        # Verify refresh token
        payload = self.verify_refresh_token(refresh_token)
        if not payload:
            raise ValueError("Invalid or expired refresh token")

        user_id = UUID(payload["sub"])

        # Get user from database
        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == user_id).first()

            if not user:
                logger.warning(f"Refresh token failed: User not found ({user_id})")
                raise ValueError("User not found")

            if not user.is_active:
                logger.warning(f"Refresh token failed: Account inactive ({user_id})")
                raise ValueError("Account is inactive")

            # Generate new access token
            access_token = self.create_access_token(
                user_id=user.user_id,
                email=user.email,
                username=user.username
            )

            logger.info(f"Access token refreshed for user {user_id}")

            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds
            }

    def get_current_user(self, token: str) -> Optional[User]:
        """
        Get current user from access token.

        Args:
            token: JWT access token

        Returns:
            User object or None if invalid
        """
        payload = self.verify_access_token(token)
        if not payload:
            return None

        user_id = UUID(payload["sub"])

        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == user_id).first()
            return user
