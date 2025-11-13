"""User service for authentication and authorization."""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional
import bcrypt
import os
from datetime import datetime, timedelta
import jwt

from src.models.user import User
from src.schemas.user import UserCreate, UserUpdate


class UserService:
    """Service for user operations."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a password against hash."""
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

    @staticmethod
    def create_user(db: Session, *, obj_in: UserCreate) -> User:
        """Create a new user."""
        user = User(
            email=obj_in.email,
            username=obj_in.username,
            password_hash=UserService.hash_password(obj_in.password),
            full_name=obj_in.full_name,
            organization_id=obj_in.organization_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_user_by_email(db: Session, *, email: str, organization_id: str) -> Optional[User]:
        """Get user by email."""
        return db.query(User).filter(
            and_(
                User.email == email,
                User.organization_id == organization_id,
            )
        ).first()

    @staticmethod
    def get_user_by_username(db: Session, *, username: str, organization_id: str) -> Optional[User]:
        """Get user by username."""
        return db.query(User).filter(
            and_(
                User.username == username,
                User.organization_id == organization_id,
            )
        ).first()

    @staticmethod
    def get_user(db: Session, *, user_id: str, organization_id: str) -> Optional[User]:
        """Get user by ID."""
        return db.query(User).filter(
            and_(
                User.id == user_id,
                User.organization_id == organization_id,
                User.is_active == True,
                User.is_deleted == False,
            )
        ).first()

    @staticmethod
    def authenticate_user(db: Session, *, email: str, password: str, organization_id: str) -> Optional[User]:
        """Authenticate user by email and password."""
        user = UserService.get_user_by_email(db, email=email, organization_id=organization_id)
        if not user or not UserService.verify_password(password, user.password_hash):
            return None
        return user

    @staticmethod
    def create_access_token(user_id: str, organization_id: str, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        if expires_delta is None:
            expires_delta = timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30)))

        expire = datetime.utcnow() + expires_delta
        to_encode = {
            "sub": user_id,
            "org": organization_id,
            "exp": expire,
            "type": "access",
        }

        encoded_jwt = jwt.encode(
            to_encode,
            os.getenv("SECRET_KEY"),
            algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        )
        return encoded_jwt

    @staticmethod
    def create_refresh_token(user_id: str, organization_id: str) -> str:
        """Create JWT refresh token."""
        expires_delta = timedelta(days=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7)))
        expire = datetime.utcnow() + expires_delta
        to_encode = {
            "sub": user_id,
            "org": organization_id,
            "exp": expire,
            "type": "refresh",
        }

        encoded_jwt = jwt.encode(
            to_encode,
            os.getenv("SECRET_KEY"),
            algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        )
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(
                token,
                os.getenv("SECRET_KEY"),
                algorithms=[os.getenv("JWT_ALGORITHM", "HS256")],
            )
            return payload
        except jwt.InvalidTokenError:
            return None

    @staticmethod
    def update_user(
        db: Session,
        *,
        user_id: str,
        organization_id: str,
        obj_in: UserUpdate,
    ) -> Optional[User]:
        """Update user."""
        user = UserService.get_user(db, user_id=user_id, organization_id=organization_id)
        if not user:
            return None

        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        user.updated_at = datetime.utcnow()
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
