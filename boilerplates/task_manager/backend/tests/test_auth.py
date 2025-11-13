"""Tests for authentication endpoints."""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from src.main import app
from src.services.user_service import UserService


client = TestClient(app)


def test_signup(db_session):
    """Test user signup."""
    organization_id = str(uuid4())
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "Password123!",
            "full_name": "New User",
            "organization_id": organization_id,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "newuser@example.com"


def test_signup_duplicate_email(test_user, db_session):
    """Test signup with duplicate email."""
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": test_user.email,
            "username": "anotheruser",
            "password": "Password123!",
            "full_name": "Another User",
            "organization_id": test_user.organization_id,
        },
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_signup_duplicate_username(test_user, db_session):
    """Test signup with duplicate username."""
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "different@example.com",
            "username": test_user.username,
            "password": "Password123!",
            "full_name": "Different User",
            "organization_id": test_user.organization_id,
        },
    )
    assert response.status_code == 400
    assert "already taken" in response.json()["detail"]


def test_login_success(test_user, db_session):
    """Test successful login."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "TestPassword123!",
        },
        params={"organization_id": test_user.organization_id},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == test_user.email


def test_login_invalid_email(test_user):
    """Test login with invalid email."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "Password123!",
        },
        params={"organization_id": test_user.organization_id},
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_login_invalid_password(test_user):
    """Test login with invalid password."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "WrongPassword123!",
        },
        params={"organization_id": test_user.organization_id},
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_refresh_token(test_user_token, test_user):
    """Test refresh token."""
    refresh_token = UserService.create_refresh_token(test_user.id, test_user.organization_id)
    response = client.post(
        "/api/v1/auth/refresh",
        json={"token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_refresh_token_invalid(test_user):
    """Test refresh with invalid token."""
    response = client.post(
        "/api/v1/auth/refresh",
        json={"token": "invalid_token"},
    )
    assert response.status_code == 401
    assert "Invalid refresh token" in response.json()["detail"]


def test_get_current_user(test_user_token, test_user):
    """Test getting current user info."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["username"] == test_user.username
