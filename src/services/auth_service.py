"""
Authentication Service

Handles user authentication, JWT token generation/validation, and password hashing.
Part of Phase 1 Critical Security Vulnerabilities - Exception handling updated.
"""

import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from src.models.user import User
from src.config.database import get_db_context
from src.config.settings import get_settings
from src.observability import get_logger

logger = get_logger("auth_service")

# Load settings from environment (no hardcoded fallbacks)
settings = get_settings()


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
        try:
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            return hashed.decode('utf-8')
        except Exception as e:
            logger.error(f"Password hashing failed: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Password hashing failed")

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
        try:
            return bcrypt.checkpw(
                plain_password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Password verification failed: {str(e)}", exc_info=True)
            return False

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
        try:
            expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

            payload = {
                "sub": str(user_id),  # Subject (user_id)
                "email": email,
                "username": username,
                "type": "access",
                "exp": expire,
                "iat": datetime.utcnow()
            }

            token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
            logger.debug(f"Created access token for user {user_id}")
            return token

        except Exception as e:
            logger.error(f"Access token creation failed: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Token generation failed")

    @staticmethod
    def create_refresh_token(user_id: UUID) -> str:
        """
        Create JWT refresh token.

        Args:
            user_id: User UUID

        Returns:
            JWT refresh token string
        """
        try:
            expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

            payload = {
                "sub": str(user_id),
                "type": "refresh",
                "exp": expire,
                "iat": datetime.utcnow()
            }

            token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
            logger.debug(f"Created refresh token for user {user_id}")
            return token

        except Exception as e:
            logger.error(f"Refresh token creation failed: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Token generation failed")

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
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

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
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}", exc_info=True)
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
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

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
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}", exc_info=True)
            return None

    def register_user(self, email: str, username: str, password: str, correlation_id: Optional[str] = None) -> User:
        """
        Register new user.

        Args:
            email: User email
            username: Username
            password: Plain text password
            correlation_id: Optional correlation ID for request tracing

        Returns:
            Created User object

        Raises:
            ValueError: If email or username already exists
            HTTPException: On database errors
        """
        try:
            with get_db_context() as db:
                # Check if email already exists
                existing_user = db.query(User).filter(User.email == email).first()
                if existing_user:
                    logger.warning(
                        f"Registration failed: Email {email} already exists",
                        extra={"correlation_id": correlation_id}
                    )
                    raise ValueError("Email already registered")

                # Check if username already exists
                existing_username = db.query(User).filter(User.username == username).first()
                if existing_username:
                    logger.warning(
                        f"Registration failed: Username {username} already exists",
                        extra={"correlation_id": correlation_id}
                    )
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

                logger.info(
                    f"User registered successfully: {user.user_id} ({email})",
                    extra={"correlation_id": correlation_id}
                )
                return user

        except ValueError:
            # Re-raise validation errors
            raise
        except SQLAlchemyError as e:
            logger.error(
                f"Database error during user registration: {str(e)}",
                exc_info=True,
                extra={"correlation_id": correlation_id}
            )
            raise HTTPException(status_code=500, detail="Database error occurred")
        except HTTPException:
            # Re-raise HTTPException unchanged
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error during user registration: {str(e)}",
                exc_info=True,
                extra={"correlation_id": correlation_id}
            )
            raise HTTPException(status_code=500, detail="Internal server error")

    def login(self, email: str, password: str, correlation_id: Optional[str] = None) -> Dict[str, str]:
        """
        Authenticate user and generate tokens.

        Args:
            email: User email
            password: Plain text password
            correlation_id: Optional correlation ID for request tracing

        Returns:
            Dict with access_token and refresh_token

        Raises:
            ValueError: If authentication fails
            HTTPException: On database errors
        """
        try:
            with get_db_context() as db:
                # Find user by email
                user = db.query(User).filter(User.email == email).first()

                if not user:
                    logger.warning(
                        f"Login failed: User not found ({email})",
                        extra={"correlation_id": correlation_id}
                    )
                    raise ValueError("Invalid email or password")

                # Verify password
                if not self.verify_password(password, user.password_hash):
                    logger.warning(
                        f"Login failed: Invalid password for {email}",
                        extra={"correlation_id": correlation_id}
                    )
                    raise ValueError("Invalid email or password")

                # Check if account is active
                if not user.is_active:
                    logger.warning(
                        f"Login failed: Account inactive ({email})",
                        extra={"correlation_id": correlation_id}
                    )
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

                logger.info(
                    f"User logged in successfully: {user.user_id} ({email})",
                    extra={"correlation_id": correlation_id}
                )

                return {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "bearer",
                    "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # seconds
                    "user": user.to_dict()
                }

        except ValueError:
            # Re-raise validation errors
            raise
        except SQLAlchemyError as e:
            logger.error(
                f"Database error during login: {str(e)}",
                exc_info=True,
                extra={"correlation_id": correlation_id}
            )
            raise HTTPException(status_code=500, detail="Database error occurred")
        except HTTPException:
            # Re-raise HTTPException unchanged
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error during login: {str(e)}",
                exc_info=True,
                extra={"correlation_id": correlation_id}
            )
            raise HTTPException(status_code=500, detail="Internal server error")

    def refresh_access_token(self, refresh_token: str, correlation_id: Optional[str] = None) -> Dict[str, str]:
        """
        Generate new access token from refresh token.

        Args:
            refresh_token: JWT refresh token
            correlation_id: Optional correlation ID for request tracing

        Returns:
            Dict with new access_token

        Raises:
            ValueError: If refresh token is invalid
            HTTPException: On database errors
        """
        try:
            # Verify refresh token
            payload = self.verify_refresh_token(refresh_token)
            if not payload:
                raise ValueError("Invalid or expired refresh token")

            user_id = UUID(payload["sub"])

            # Get user from database
            with get_db_context() as db:
                user = db.query(User).filter(User.user_id == user_id).first()

                if not user:
                    logger.warning(
                        f"Refresh token failed: User not found ({user_id})",
                        extra={"correlation_id": correlation_id}
                    )
                    raise ValueError("User not found")

                if not user.is_active:
                    logger.warning(
                        f"Refresh token failed: Account inactive ({user_id})",
                        extra={"correlation_id": correlation_id}
                    )
                    raise ValueError("Account is inactive")

                # Generate new access token
                access_token = self.create_access_token(
                    user_id=user.user_id,
                    email=user.email,
                    username=user.username
                )

                logger.info(
                    f"Access token refreshed for user {user_id}",
                    extra={"correlation_id": correlation_id}
                )

                return {
                    "access_token": access_token,
                    "token_type": "bearer",
                    "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds
                }

        except ValueError:
            # Re-raise validation errors
            raise
        except SQLAlchemyError as e:
            logger.error(
                f"Database error during token refresh: {str(e)}",
                exc_info=True,
                extra={"correlation_id": correlation_id}
            )
            raise HTTPException(status_code=500, detail="Database error occurred")
        except HTTPException:
            # Re-raise HTTPException unchanged
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error during token refresh: {str(e)}",
                exc_info=True,
                extra={"correlation_id": correlation_id}
            )
            raise HTTPException(status_code=500, detail="Internal server error")

    def get_current_user(self, token: str, correlation_id: Optional[str] = None) -> Optional[User]:
        """
        Get current user from access token.

        Args:
            token: JWT access token
            correlation_id: Optional correlation ID for request tracing

        Returns:
            User object or None if invalid
        """
        try:
            payload = self.verify_access_token(token)
            if not payload:
                return None

            user_id = UUID(payload["sub"])

            with get_db_context() as db:
                user = db.query(User).filter(User.user_id == user_id).first()
                return user

        except SQLAlchemyError as e:
            logger.error(
                f"Database error while fetching current user: {str(e)}",
                exc_info=True,
                extra={"correlation_id": correlation_id}
            )
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error while fetching current user: {str(e)}",
                exc_info=True,
                extra={"correlation_id": correlation_id}
            )
            return None
