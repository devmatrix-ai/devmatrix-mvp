"""
Authentication Service

Handles user authentication, JWT token generation/validation, and password hashing.
Part of Phase 1 Critical Security Vulnerabilities - Group 3: Authentication Security Layer.

Changes:
- Added jti (JWT ID) to all tokens for blacklist tracking
- Implemented token blacklist functionality using Redis
- Added check_token_blacklist function
- Added blacklist_token function for logout
"""

import bcrypt
import jwt
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from redis.exceptions import RedisError

from src.models.user import User
from src.config.database import get_db_context
from src.config.settings import get_settings
from src.state.redis_manager import RedisManager
from src.observability import get_logger

logger = get_logger("auth_service")

# Load settings from environment (no hardcoded fallbacks)
settings = get_settings()

# Global Redis manager instance for token blacklist
_redis_manager: Optional[RedisManager] = None


def get_redis_client() -> RedisManager:
    """
    Get Redis client for token blacklist.

    Returns:
        RedisManager instance
    """
    global _redis_manager

    if _redis_manager is None:
        _redis_manager = RedisManager(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0,
            enable_fallback=True
        )

    return _redis_manager


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

        # Logout (blacklist tokens)
        auth.blacklist_token(access_token, token_type="access")
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
        Create JWT access token with jti claim.

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
                "jti": str(uuid.uuid4()),  # JWT ID for blacklist tracking
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
        Create JWT refresh token with jti claim.

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
                "jti": str(uuid.uuid4()),  # JWT ID for blacklist tracking
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
    def check_token_blacklist(payload: Dict[str, Any], correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Check if token is blacklisted in Redis.

        Args:
            payload: Decoded JWT payload
            correlation_id: Optional correlation ID for request tracing

        Returns:
            Payload if token is not blacklisted

        Raises:
            HTTPException: 401 if token is blacklisted or missing jti
        """
        try:
            # Extract jti and type from payload
            jti = payload.get("jti")
            token_type = payload.get("type")

            if not jti:
                logger.warning(
                    "Token missing jti claim",
                    extra={"correlation_id": correlation_id}
                )
                raise HTTPException(
                    status_code=401,
                    detail="Token has been revoked"
                )

            if not token_type:
                logger.warning(
                    "Token missing type claim",
                    extra={"correlation_id": correlation_id}
                )
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token format"
                )

            # Check Redis for blacklist
            redis_client = get_redis_client()
            blacklist_key = f"blacklist:{token_type}:{jti}"

            # Use the Redis client directly
            is_blacklisted = redis_client.client.get(blacklist_key) if redis_client.connected else None

            if is_blacklisted:
                logger.warning(
                    f"Blacklisted token access attempt: {token_type} token {jti}",
                    extra={"correlation_id": correlation_id}
                )
                raise HTTPException(
                    status_code=401,
                    detail="Token has been revoked"
                )

            return payload

        except HTTPException:
            # Re-raise HTTPException unchanged
            raise
        except RedisError as e:
            logger.error(
                f"Redis error during blacklist check: {str(e)}",
                exc_info=True,
                extra={"correlation_id": correlation_id}
            )
            # Fail open: allow token if Redis is down (logged for security review)
            logger.warning(
                "Allowing token due to Redis unavailability - SECURITY REVIEW NEEDED",
                extra={"correlation_id": correlation_id}
            )
            return payload
        except Exception as e:
            logger.error(
                f"Unexpected error during blacklist check: {str(e)}",
                exc_info=True,
                extra={"correlation_id": correlation_id}
            )
            raise HTTPException(status_code=500, detail="Internal server error")

    @staticmethod
    def blacklist_token(token: str, token_type: str, correlation_id: Optional[str] = None) -> bool:
        """
        Add token to blacklist in Redis.

        Args:
            token: JWT token string
            token_type: Token type ("access" or "refresh")
            correlation_id: Optional correlation ID for request tracing

        Returns:
            True if successfully blacklisted, False otherwise
        """
        try:
            # Decode token to get jti
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            jti = payload.get("jti")

            if not jti:
                logger.warning(
                    "Cannot blacklist token without jti",
                    extra={"correlation_id": correlation_id}
                )
                return False

            # Calculate TTL based on token type
            if token_type == "access":
                ttl = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
            elif token_type == "refresh":
                ttl = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # Convert to seconds
            else:
                logger.warning(
                    f"Unknown token type: {token_type}",
                    extra={"correlation_id": correlation_id}
                )
                return False

            # Add to Redis blacklist
            redis_client = get_redis_client()
            blacklist_key = f"blacklist:{token_type}:{jti}"

            # Use Redis client directly
            if redis_client.connected:
                redis_client.client.setex(blacklist_key, ttl, "1")
                logger.info(
                    f"Token blacklisted: {token_type} token {jti} (TTL: {ttl}s)",
                    extra={"correlation_id": correlation_id}
                )
                return True
            else:
                logger.warning(
                    "Redis unavailable - token not blacklisted",
                    extra={"correlation_id": correlation_id}
                )
                return False

        except jwt.InvalidTokenError as e:
            logger.warning(
                f"Cannot blacklist invalid token: {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            return False
        except RedisError as e:
            logger.error(
                f"Redis error during token blacklist: {str(e)}",
                exc_info=True,
                extra={"correlation_id": correlation_id}
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error during token blacklist: {str(e)}",
                exc_info=True,
                extra={"correlation_id": correlation_id}
            )
            return False

    @staticmethod
    def verify_access_token(token: str, correlation_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Verify and decode JWT access token.

        Args:
            token: JWT access token
            correlation_id: Optional correlation ID for request tracing

        Returns:
            Decoded payload dict or None if invalid
        """
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

            # Verify token type
            if payload.get("type") != "access":
                logger.warning(
                    "Invalid token type (expected access)",
                    extra={"correlation_id": correlation_id}
                )
                return None

            # Check blacklist before returning payload
            AuthService.check_token_blacklist(payload, correlation_id)

            return payload

        except HTTPException:
            # Token is blacklisted
            return None
        except jwt.ExpiredSignatureError:
            logger.warning(
                "Access token expired",
                extra={"correlation_id": correlation_id}
            )
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(
                f"Invalid access token: {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            return None
        except Exception as e:
            logger.error(
                f"Token verification failed: {str(e)}",
                exc_info=True,
                extra={"correlation_id": correlation_id}
            )
            return None

    @staticmethod
    def verify_refresh_token(token: str, correlation_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Verify and decode JWT refresh token.

        Args:
            token: JWT refresh token
            correlation_id: Optional correlation ID for request tracing

        Returns:
            Decoded payload dict or None if invalid
        """
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

            # Verify token type
            if payload.get("type") != "refresh":
                logger.warning(
                    "Invalid token type (expected refresh)",
                    extra={"correlation_id": correlation_id}
                )
                return None

            # Check blacklist before returning payload
            AuthService.check_token_blacklist(payload, correlation_id)

            return payload

        except HTTPException:
            # Token is blacklisted
            return None
        except jwt.ExpiredSignatureError:
            logger.warning(
                "Refresh token expired",
                extra={"correlation_id": correlation_id}
            )
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(
                f"Invalid refresh token: {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            return None
        except Exception as e:
            logger.error(
                f"Token verification failed: {str(e)}",
                exc_info=True,
                extra={"correlation_id": correlation_id}
            )
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
            payload = self.verify_refresh_token(refresh_token, correlation_id)
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
            payload = self.verify_access_token(token, correlation_id)
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
