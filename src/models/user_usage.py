"""
UserUsage Model

Tracks per-user monthly usage metrics for LLM tokens, masterplans, storage, and API calls.
"""

import uuid
from datetime import date
from sqlalchemy import Column, String, Integer, BigInteger, Date, ForeignKey, Index, UniqueConstraint, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.config.database import Base


class UserUsage(Base):
    """
    UserUsage model for tracking monthly usage metrics.

    Fields:
        usage_id: UUID primary key
        user_id: UUID foreign key to users table
        month: Date (first day of month, e.g., 2025-10-01)
        llm_tokens_used: Total LLM tokens consumed this month (default 0)
        llm_cost_usd: Total LLM cost in USD this month
        masterplans_created: Count of masterplans created this month
        storage_bytes: Current workspace storage size in bytes
        api_calls: Total API calls made this month

    Constraints:
        - Unique constraint on (user_id, month) - one record per user per month
        - Compound index on (user_id, month) for fast lookups
    """

    __tablename__ = "user_usage"

    usage_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    month = Column(String(7), nullable=False)  # Format: YYYY-MM

    # Usage metrics (mapped to actual DB column names)
    llm_tokens_used = Column('total_tokens_used', BigInteger, default=0, nullable=False)
    llm_cost_usd = Column('total_cost_usd', Numeric(10, 4), default=0.0, nullable=False)
    masterplans_created = Column('masterplans_count', Integer, default=0, nullable=False)
    storage_bytes = Column('storage_used_mb', Numeric(10, 2), default=0, nullable=False)
    api_calls = Column('api_calls_count', Integer, default=0, nullable=False)

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('user_id', 'month', name='uq_user_usage_user_month'),
        Index('idx_user_usage_user_month', 'user_id', 'month'),
    )

    # Relationship to User (optional, for convenience)
    # user = relationship("User", backref="usage_records")

    def __repr__(self):
        return (
            f"<UserUsage(usage_id={self.usage_id}, user_id={self.user_id}, "
            f"month={self.month}, tokens={self.llm_tokens_used}, "
            f"cost=${self.llm_cost_usd})>"
        )

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "usage_id": str(self.usage_id),
            "user_id": str(self.user_id),
            "month": self.month.isoformat() if self.month else None,
            "llm_tokens_used": self.llm_tokens_used,
            "llm_cost_usd": float(self.llm_cost_usd) if self.llm_cost_usd else 0.0,
            "masterplans_created": self.masterplans_created,
            "storage_bytes": self.storage_bytes,
            "api_calls": self.api_calls,
        }
