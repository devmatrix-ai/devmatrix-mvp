"""User schemas for authentication and user management."""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
from .base import TimestampedSchema


class UserCreate(BaseModel):
    """Schema for user registration."""

    email: EmailStr = Field(..., description="User email")
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    password: str = Field(..., min_length=8, description="User password")
    full_name: Optional[str] = Field(None, max_length=255, description="User full name")
    organization_id: str = Field(..., description="Organization ID")


class UserRead(TimestampedSchema):
    """Schema for reading user data."""

    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    is_superuser: bool


class UserUpdate(BaseModel):
    """Schema for updating user data."""

    full_name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema for token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead
