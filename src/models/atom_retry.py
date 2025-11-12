"""
Atom Retry History Database Model

SQLAlchemy ORM model for MGE V2 retry tracking with feedback.

AtomRetryHistory: Tracks retry attempts with error analysis and prompt variations

Schema design based on MGE V2 specification.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from src.config.database import Base


class AtomRetryHistory(Base):
    """
    Atom Retry History - Retry tracking with feedback

    MGE V2 retry strategy (Deterministic mode):
    - All attempts: temperature=0.0 (deterministic)
    - Error feedback added progressively
    - Detailed error analysis on later attempts

    Stores:
    - Temperature adjustments
    - Modified prompts with error feedback
    - Parsed error information
    - Success/failure outcomes
    - Token usage and cost tracking

    Target: 99% success after 3 attempts
    """
    __tablename__ = "atom_retry_history"

    # Primary Key
    retry_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    atom_id = Column(UUID(as_uuid=True), ForeignKey("atomic_units.atom_id", ondelete="CASCADE"), nullable=False)

    # Retry Info
    attempt_number = Column(Integer, nullable=False, index=True)  # 1, 2, 3

    # LLM Configuration
    temperature = Column(Float, nullable=False)  # 0.7 → 0.5 → 0.3
    prompt_variation = Column(Text, nullable=True)  # Modified prompt with error feedback

    # Error Analysis
    error_analysis = Column(JSONB, nullable=True)  # Parsed error info:
    # {
    #   "error_type": "syntax_error|type_error|logic_error|runtime_error",
    #   "error_location": {"line": 10, "column": 5},
    #   "suggested_fixes": ["fix1", "fix2"],
    #   "context": {...}
    # }

    # Results
    success = Column(Boolean, nullable=False, index=True)
    execution_result = Column(Text, nullable=True)  # Output if successful
    error_message = Column(Text, nullable=True)  # Error if failed

    # Cost Tracking
    tokens_used = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    atom = relationship("AtomicUnit", back_populates="retry_history")

    # Indexes
    __table_args__ = (
        Index("idx_retry_atom", "atom_id"),
        Index("idx_retry_attempt", "attempt_number"),
        Index("idx_retry_success", "success"),
        Index("idx_retry_created", "created_at"),
        Index("idx_retry_atom_attempt", "atom_id", "attempt_number"),  # Composite for ordering
    )

    def __repr__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return f"<AtomRetryHistory(atom_id={self.atom_id}, attempt={self.attempt_number}, temp={self.temperature}, status={status})>"

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses"""
        return {
            "retry_id": str(self.retry_id),
            "atom_id": str(self.atom_id),
            "attempt_number": self.attempt_number,
            "temperature": self.temperature,
            "success": self.success,
            "error_message": self.error_message if not self.success else None,
            "error_analysis": self.error_analysis,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
