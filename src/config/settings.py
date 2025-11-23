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

    # ========================================
    # Phase 2: Password Policy Settings
    # ========================================

    PASSWORD_MIN_LENGTH: int = Field(
        default=12,
        description="Minimum password length (NIST compliant)"
    )

    PASSWORD_MAX_LENGTH: int = Field(
        default=128,
        description="Maximum password length (NIST compliant)"
    )

    PASSWORD_MIN_ENTROPY: int = Field(
        default=3,
        description="Minimum zxcvbn entropy score (0-4, where 3=good, 4=strong)"
    )

    # ========================================
    # Phase 2: Account Lockout Settings
    # ========================================

    ACCOUNT_LOCKOUT_THRESHOLD: int = Field(
        default=5,
        description="Number of failed login attempts before account lockout"
    )

    ACCOUNT_LOCKOUT_WINDOW_MINUTES: int = Field(
        default=15,
        description="Time window (in minutes) for counting failed login attempts"
    )

    ACCOUNT_LOCKOUT_DURATIONS: str = Field(
        default="15,30,60,120,240",
        description="Comma-separated lockout durations in minutes (exponential backoff)"
    )

    # ========================================
    # Phase 2: Session Timeout Settings
    # ========================================

    SESSION_IDLE_TIMEOUT_MINUTES: int = Field(
        default=30,
        description="Session idle timeout in minutes (default: 30 minutes)"
    )

    SESSION_ABSOLUTE_TIMEOUT_HOURS: int = Field(
        default=12,
        description="Session absolute timeout in hours (default: 12 hours)"
    )

    # ========================================
    # Phase 2: IP-Based Access Controls
    # ========================================

    ADMIN_IP_WHITELIST: str = Field(
        default="",
        description="Comma-separated list of IPs and CIDR ranges allowed to access admin endpoints. "
                    "Example: 192.168.1.0/24,10.0.0.5,203.0.113.0/25. "
                    "Empty string allows all IPs (IP restriction disabled)."
    )

    # ========================================
    # Phase 2: 2FA/MFA Settings (Task Group 9)
    # ========================================

    TOTP_ISSUER_NAME: str = Field(
        default="DevMatrix",
        description="TOTP issuer name displayed in authenticator apps (e.g., Google Authenticator)"
    )

    TOTP_DIGITS: int = Field(
        default=6,
        description="Number of digits in TOTP code (default: 6)"
    )

    TOTP_INTERVAL: int = Field(
        default=30,
        description="TOTP time window in seconds (default: 30)"
    )

    ENFORCE_2FA: bool = Field(
        default=False,
        description="Globally enforce 2FA for all users (default: False, optional enforcement)"
    )

    TOTP_ENCRYPTION_KEY: Optional[str] = Field(
        default=None,
        description="Fernet encryption key for TOTP secrets (base64-encoded 32-byte key). "
                    "Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
    )

    # ========================================
    # Phase 2: Enhanced Audit Logging (Task Group 12)
    # ========================================

    AUDIT_READ_OPERATIONS: bool = Field(
        default=True,
        description="Enable logging of read operations (GET requests) to audit_logs table. "
                    "Set to False to disable read operation logging (write operations still logged)."
    )

    AUDIT_EXCLUDED_PATHS: str = Field(
        default="/health,/metrics,/auth/session/keep-alive",
        description="Comma-separated list of paths to exclude from read operation logging. "
                    "Example: /health,/metrics,/static/*,/auth/session/keep-alive"
    )

    # ========================================
    # Phase 2: Security Monitoring (Task Group 13)
    # ========================================

    SECURITY_MONITORING_INTERVAL_MINUTES: int = Field(
        default=5,
        description="Interval (in minutes) for running security event detection batch job"
    )

    GEOIP2_DATABASE_PATH: Optional[str] = Field(
        default=None,
        description="Path to GeoIP2 database file for geo-location detection (optional). "
                    "Example: /path/to/GeoLite2-Country.mmdb. "
                    "If not provided, geo-location detection will use country data from audit log metadata."
    )

    # ========================================
    # Phase 2: Alert System (Task Group 14)
    # ========================================

    SLACK_WEBHOOK_URL: Optional[str] = Field(
        default=None,
        description="Slack webhook URL for alert notifications (optional). "
                    "Example: https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX. "
                    "If not provided, Slack alerts will be disabled."
    )

    PAGERDUTY_API_KEY: Optional[str] = Field(
        default=None,
        description="PagerDuty Events API v2 routing key for critical alerts (optional). "
                    "Example: R0XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX. "
                    "If not provided, PagerDuty alerts will be disabled."
    )

    ALERT_THROTTLE_HOURS: int = Field(
        default=1,
        description="Hours to throttle duplicate alerts (max 1 alert per event type per user per hour)"
    )

    # ========================================
    # Phase 2: Log Retention & Management (Task Group 15)
    # ========================================

    AWS_S3_BUCKET: Optional[str] = Field(
        default=None,
        description="S3 bucket name for log archival (optional). "
                    "Example: devmatrix-logs-prod. "
                    "If not provided, log archival to S3 will be disabled."
    )

    AWS_ACCESS_KEY_ID: Optional[str] = Field(
        default=None,
        description="AWS access key ID for S3 operations (optional). "
                    "If not provided, will use IAM role credentials."
    )

    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(
        default=None,
        description="AWS secret access key for S3 operations (optional). "
                    "If not provided, will use IAM role credentials."
    )

    AUDIT_LOG_RETENTION_DAYS: int = Field(
        default=90,
        description="Number of days to retain audit logs in PostgreSQL (hot storage) before archival to S3"
    )

    SECURITY_EVENT_RETENTION_DAYS: int = Field(
        default=90,
        description="Number of days to retain security events in PostgreSQL (hot storage) before archival to S3"
    )

    ALERT_HISTORY_RETENTION_DAYS: int = Field(
        default=365,
        description="Number of days to retain alert history in PostgreSQL before purging (1 year)"
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
        Automatically converts legacy sync drivers to async (asyncpg).

        Args:
            v: DATABASE_URL value

        Returns:
            Validated DATABASE_URL with async driver

        Raises:
            ValueError: If DATABASE_URL is invalid
        """
        if not v:
            raise ValueError("DATABASE_URL cannot be empty")

        # Auto-convert legacy sync drivers to async (asyncpg)
        if "+psycopg2" in v or "+psycopg" in v or (v.startswith("postgresql://") and "+psycopg" not in v and "+asyncpg" not in v):
            # Convert: postgresql+psycopg2:// → postgresql+asyncpg://
            # Convert: postgresql+psycopg:// → postgresql+asyncpg://
            # Convert: postgresql:// → postgresql+asyncpg://
            v = v.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
            v = v.replace("postgresql+psycopg://", "postgresql+asyncpg://")
            if v.startswith("postgresql://") and "+asyncpg" not in v:
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)

        if not v.startswith(("postgresql://", "postgresql+asyncpg://", "postgres://")):
            raise ValueError(
                "DATABASE_URL must be a PostgreSQL connection string with async driver. "
                "Format: postgresql+asyncpg://user:pass@host:port/db"
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
