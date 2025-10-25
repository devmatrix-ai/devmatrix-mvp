"""
Unit tests for configuration settings validation.

Tests configuration validation for Phase 1 Critical Security Vulnerabilities.
"""

import pytest
import os
from pydantic import ValidationError


def test_jwt_secret_missing():
    """Test application fails when JWT_SECRET is missing."""
    # Clear JWT_SECRET from environment
    old_value = os.environ.pop("JWT_SECRET", None)

    try:
        from src.config.settings import Settings

        # Should raise validation error when JWT_SECRET is missing
        with pytest.raises(ValidationError) as exc_info:
            Settings()

        # Verify the error is for JWT_SECRET field
        assert "JWT_SECRET" in str(exc_info.value)
    finally:
        # Restore original value
        if old_value is not None:
            os.environ["JWT_SECRET"] = old_value


def test_jwt_secret_minimum_length():
    """Test application fails when JWT_SECRET is less than 32 characters."""
    # Set a short JWT_SECRET
    os.environ["JWT_SECRET"] = "too_short"
    os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost:5432/db"

    try:
        from src.config.settings import Settings

        settings = Settings()

        # Should raise ValueError when validating JWT_SECRET
        with pytest.raises(ValueError) as exc_info:
            settings.validate_jwt_secret()

        assert "at least 32 characters" in str(exc_info.value)
    finally:
        # Clean up
        os.environ.pop("JWT_SECRET", None)
        os.environ.pop("DATABASE_URL", None)


def test_database_url_missing():
    """Test application fails when DATABASE_URL is missing."""
    # Clear DATABASE_URL from environment
    old_value = os.environ.pop("DATABASE_URL", None)

    # Also clear legacy postgres variables
    old_host = os.environ.pop("POSTGRES_HOST", None)
    old_port = os.environ.pop("POSTGRES_PORT", None)
    old_db = os.environ.pop("POSTGRES_DB", None)
    old_user = os.environ.pop("POSTGRES_USER", None)
    old_password = os.environ.pop("POSTGRES_PASSWORD", None)

    try:
        from src.config.settings import Settings

        # Should raise validation error when DATABASE_URL is missing
        with pytest.raises(ValidationError) as exc_info:
            Settings()

        # Verify the error is for DATABASE_URL field
        assert "DATABASE_URL" in str(exc_info.value)
    finally:
        # Restore original values
        if old_value is not None:
            os.environ["DATABASE_URL"] = old_value
        if old_host is not None:
            os.environ["POSTGRES_HOST"] = old_host
        if old_port is not None:
            os.environ["POSTGRES_PORT"] = old_port
        if old_db is not None:
            os.environ["POSTGRES_DB"] = old_db
        if old_user is not None:
            os.environ["POSTGRES_USER"] = old_user
        if old_password is not None:
            os.environ["POSTGRES_PASSWORD"] = old_password


def test_cors_allowed_origins_parses_comma_separated():
    """Test CORS_ALLOWED_ORIGINS parses comma-separated list correctly."""
    # Set JWT_SECRET and DATABASE_URL so validation passes
    os.environ["JWT_SECRET"] = "a" * 32
    os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost:5432/db"
    os.environ["CORS_ALLOWED_ORIGINS"] = "http://localhost:3000,http://localhost:5173, https://app.example.com"

    try:
        from src.config.settings import Settings

        settings = Settings()

        # Parse origins
        origins = [o.strip() for o in settings.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]

        # Verify parsing
        assert len(origins) == 3
        assert "http://localhost:3000" in origins
        assert "http://localhost:5173" in origins
        assert "https://app.example.com" in origins
        # Verify no leading/trailing spaces
        assert all(o == o.strip() for o in origins)
    finally:
        # Clean up
        os.environ.pop("JWT_SECRET", None)
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("CORS_ALLOWED_ORIGINS", None)


def test_configuration_loads_successfully_with_all_required_variables():
    """Test configuration loads successfully when all required variables are set."""
    # Set all required environment variables
    os.environ["JWT_SECRET"] = "a" * 32
    os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost:5432/db"
    os.environ["CORS_ALLOWED_ORIGINS"] = "http://localhost:5173"

    try:
        from src.config.settings import Settings

        # Should not raise any exception
        settings = Settings()

        # Verify settings loaded correctly
        assert settings.JWT_SECRET == "a" * 32
        assert settings.DATABASE_URL == "postgresql://user:pass@localhost:5432/db"
        assert settings.CORS_ALLOWED_ORIGINS == "http://localhost:5173"

        # Verify JWT_SECRET validation passes
        validated_secret = settings.validate_jwt_secret()
        assert validated_secret == "a" * 32
    finally:
        # Clean up
        os.environ.pop("JWT_SECRET", None)
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("CORS_ALLOWED_ORIGINS", None)


def test_environment_variable_validation_on_startup():
    """Test environment variables are validated on startup."""
    # Set valid environment variables
    os.environ["JWT_SECRET"] = "b" * 32
    os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost:5432/test"

    try:
        from src.config.settings import Settings

        settings = Settings()

        # Verify case sensitivity
        assert hasattr(settings, "JWT_SECRET")
        assert hasattr(settings, "DATABASE_URL")

        # Verify no default fallback values
        assert settings.JWT_SECRET != "your-secret-key-change-in-production-IMPORTANT"
        assert settings.JWT_SECRET == "b" * 32
    finally:
        # Clean up
        os.environ.pop("JWT_SECRET", None)
        os.environ.pop("DATABASE_URL", None)


def test_jwt_secret_exactly_32_characters():
    """Test JWT_SECRET validation passes with exactly 32 characters."""
    os.environ["JWT_SECRET"] = "a" * 32
    os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost:5432/db"

    try:
        from src.config.settings import Settings

        settings = Settings()

        # Should not raise exception with exactly 32 characters
        validated = settings.validate_jwt_secret()
        assert validated == "a" * 32
    finally:
        # Clean up
        os.environ.pop("JWT_SECRET", None)
        os.environ.pop("DATABASE_URL", None)


def test_jwt_secret_more_than_32_characters():
    """Test JWT_SECRET validation passes with more than 32 characters."""
    os.environ["JWT_SECRET"] = "a" * 64
    os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost:5432/db"

    try:
        from src.config.settings import Settings

        settings = Settings()

        # Should not raise exception with more than 32 characters
        validated = settings.validate_jwt_secret()
        assert validated == "a" * 64
    finally:
        # Clean up
        os.environ.pop("JWT_SECRET", None)
        os.environ.pop("DATABASE_URL", None)
