"""
Production-ready configuration management using pydantic-settings.

Supports:
- Type-safe configuration with validation
- Environment variable loading from .env files
- Multi-environment support (development, staging, production)
- Cached settings for performance
"""

from functools import lru_cache
from typing import List

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="DevMatrix API", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    environment: str = Field(default="development", description="Environment (development, staging, production)")
    debug: bool = Field(default=False, description="Debug mode")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/devmatrix",
        description="Async PostgreSQL connection URL (postgresql+asyncpg://...)",
    )
    db_echo: bool = Field(default=False, description="Echo SQL queries (for debugging)")
    db_pool_size: int = Field(default=5, ge=1, le=50, description="Connection pool size")
    db_max_overflow: int = Field(default=10, ge=0, le=100, description="Max overflow connections")
    db_pool_timeout: int = Field(default=30, ge=5, le=300, description="Pool timeout in seconds")
    db_pool_recycle: int = Field(default=3600, ge=300, description="Pool recycle time in seconds")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    log_json: bool = Field(default=True, description="Output logs in JSON format")

    # Security
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins",
    )
    rate_limit: str = Field(default="100/minute", description="Rate limit (requests/time)")
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for signing (MUST change in production)",
    )

    # Redis (optional)
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")

    @validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the allowed values."""
        allowed_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in allowed_levels:
            raise ValueError(f"log_level must be one of {allowed_levels}, got {v}")
        return v_upper

    @validator("environment")
    def validate_environment(cls, v: str) -> str:
        """Validate environment is one of the allowed values."""
        allowed_envs = {"development", "staging", "production"}
        v_lower = v.lower()
        if v_lower not in allowed_envs:
            raise ValueError(f"environment must be one of {allowed_envs}, got {v}")
        return v_lower

    @validator("database_url")
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL uses asyncpg driver."""
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError(
                f"database_url must use asyncpg driver (postgresql+asyncpg://...), got {v[:20]}..."
            )
        return v


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure settings are loaded only once per process.
    This improves performance and ensures consistent configuration.

    Returns:
        Settings: Cached application settings
    """
    return Settings()
