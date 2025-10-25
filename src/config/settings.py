"""
Application Settings Configuration

Centralized configuration management using Pydantic Settings.
Implements secure environment variable loading with validation.

Security Features:
- No hardcoded fallback values for secrets
- Fail-fast validation on startup
- Minimum length requirements for JWT_SECRET
- Case-sensitive environment variable names
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.

    All security-critical settings (JWT_SECRET, DATABASE_URL) are required
    with no default values. Application will fail on startup if missing.
    """

    # ========================================
    # Required Security Settings (No Defaults)
    # ========================================

    JWT_SECRET: str = Field(
        ...,
        description="JWT signing secret key. Must be at least 32 characters. REQUIRED."
    )

    DATABASE_URL: str = Field(
        ...,
        description="PostgreSQL connection URL. Format: postgresql://user:pass@host:port/db. REQUIRED."
    )

    # ========================================
    # CORS Configuration
    # ========================================

    CORS_ALLOWED_ORIGINS: str = Field(
        default="",
        description="Comma-separated list of allowed CORS origins. Example: http://localhost:3000,https://app.example.com"
    )

    # ========================================
    # Optional Settings (With Defaults)
    # ========================================

    # Redis Configuration
    REDIS_HOST: str = Field(default="localhost", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis password (optional)")

    # JWT Token Expiration
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60,
        description="Access token expiration in minutes"
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=30,
        description="Refresh token expiration in days"
    )

    # JWT Algorithm
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="JWT signing algorithm"
    )

    # Environment
    ENVIRONMENT: str = Field(
        default="development",
        description="Application environment: development, staging, production"
    )

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra environment variables

    def validate_jwt_secret(self) -> str:
        """
        Validate JWT_SECRET meets minimum security requirements.

        Returns:
            Validated JWT_SECRET

        Raises:
            ValueError: If JWT_SECRET is less than 32 characters
        """
        if len(self.JWT_SECRET) < 32:
            raise ValueError(
                f"JWT_SECRET must be at least 32 characters for security. "
                f"Current length: {len(self.JWT_SECRET)}. "
                f"Generate a secure key with: python -c 'import secrets; print(secrets.token_hex(32))'"
            )
        return self.JWT_SECRET

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """
        Validate DATABASE_URL is not empty and has proper format.

        Args:
            v: DATABASE_URL value

        Returns:
            Validated DATABASE_URL

        Raises:
            ValueError: If DATABASE_URL is invalid
        """
        if not v:
            raise ValueError("DATABASE_URL cannot be empty")

        if not v.startswith(("postgresql://", "postgres://")):
            raise ValueError(
                "DATABASE_URL must be a PostgreSQL connection string. "
                "Format: postgresql://user:pass@host:port/db"
            )

        return v

    def get_cors_origins_list(self) -> list[str]:
        """
        Parse CORS_ALLOWED_ORIGINS into a list.

        Returns:
            List of allowed CORS origins (empty list if none configured)
        """
        if not self.CORS_ALLOWED_ORIGINS:
            return []

        return [
            origin.strip()
            for origin in self.CORS_ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]


# Global settings instance (lazy-loaded)
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get global settings instance (singleton).

    Returns:
        Settings instance

    Raises:
        ValidationError: If required environment variables are missing
        SystemExit: If settings validation fails critically
    """
    global _settings

    if _settings is None:
        _settings = Settings()
        # Validate JWT_SECRET on first load
        _settings.validate_jwt_secret()

    return _settings
