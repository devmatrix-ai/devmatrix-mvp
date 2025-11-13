"""Authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.db import get_db
from src.schemas.user import UserCreate, UserLogin, TokenResponse
from src.services.user_service import UserService
from src.security import get_current_user
from src.models.user import User

router = APIRouter()


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    existing_user = UserService.get_user_by_email(
        db, email=user_in.email, organization_id=user_in.organization_id
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    existing_username = UserService.get_user_by_username(
        db, username=user_in.username, organization_id=user_in.organization_id
    )
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    user = UserService.create_user(db, obj_in=user_in)

    access_token = UserService.create_access_token(user.id, user.organization_id)
    refresh_token = UserService.create_refresh_token(user.id, user.organization_id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user,
    }


@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, organization_id: str, db: Session = Depends(get_db)):
    """Login user."""
    user = UserService.authenticate_user(
        db, email=credentials.email, password=credentials.password, organization_id=organization_id
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = UserService.create_access_token(user.id, user.organization_id)
    refresh_token = UserService.create_refresh_token(user.id, user.organization_id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user,
    }


@router.post("/refresh", response_model=TokenResponse)
def refresh(token: str, db: Session = Depends(get_db)):
    """Refresh access token using refresh token."""
    payload = UserService.verify_token(token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    organization_id = payload.get("org")

    user = UserService.get_user(db, user_id=user_id, organization_id=organization_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    access_token = UserService.create_access_token(user.id, user.organization_id)

    return {
        "access_token": access_token,
        "refresh_token": token,
        "token_type": "bearer",
        "user": user,
    }


@router.get("/me")
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user
