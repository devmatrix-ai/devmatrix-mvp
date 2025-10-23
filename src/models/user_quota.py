"""
UserQuota Model

Stores per-user quota limits for LLM tokens, masterplans, storage, and API calls.
"""

import uuid
from sqlalchemy import Column, Integer, BigInteger, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.config.database import Base


class UserQuota(Base):
    """
    UserQuota model for per-user quota limits.

    Fields:
        quota_id: UUID primary key
        user_id: UUID foreign key to users table (unique - one quota per user)
        llm_tokens_monthly_limit: Monthly LLM token limit (nullable = unlimited)
        masterplans_limit: Maximum masterplans allowed (nullable = unlimited)
        storage_bytes_limit: Maximum workspace storage in bytes (nullable = unlimited)
        api_calls_per_minute: API rate limit per minute (default 30)
    """

    __tablename__ = "user_quotas"

    quota_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )

    # Quota limits (nullable = unlimited)
    llm_tokens_monthly_limit = Column(Integer, nullable=True)
    masterplans_limit = Column(Integer, nullable=True)
    storage_bytes_limit = Column(BigInteger, nullable=True)
    api_calls_per_minute = Column(Integer, default=30, nullable=False)

    # Relationship to User (optional, for convenience)
    # user = relationship("User", backref="quota")

    def __repr__(self):
        return (
            f"<UserQuota(quota_id={self.quota_id}, user_id={self.user_id}, "
            f"tokens={self.llm_tokens_monthly_limit}, "
            f"masterplans={self.masterplans_limit}, "
            f"storage={self.storage_bytes_limit})>"
        )

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "quota_id": str(self.quota_id),
            "user_id": str(self.user_id),
            "llm_tokens_monthly_limit": self.llm_tokens_monthly_limit,
            "masterplans_limit": self.masterplans_limit,
            "storage_bytes_limit": self.storage_bytes_limit,
            "api_calls_per_minute": self.api_calls_per_minute,
        }
