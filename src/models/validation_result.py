"""
Validation Result Database Model

SQLAlchemy ORM model for MGE V2 hierarchical validation results.

ValidationResult: Stores results from 4-level validation:
- Level 1 (Atomic): Syntax, types, unit tests
- Level 2 (Module): Integration tests, API consistency
- Level 3 (Component): E2E tests, architecture validation
- Level 4 (System): System tests, acceptance criteria

Schema design based on MGE V2 specification.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, Enum, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum

from src.config.database import Base


# Enums
class ValidationLevel(str, enum.Enum):
    """Hierarchical validation levels"""
    ATOMIC = "atomic"          # Level 1: Unit-level validation
    MODULE = "module"          # Level 2: Module-level integration
    COMPONENT = "component"    # Level 3: Component-level E2E
    SYSTEM = "system"          # Level 4: System-level acceptance


class ValidationResult(Base):
    """
    Validation Result - 4-level hierarchical validation

    Stores validation results at different levels:

    Level 1 (Atomic): 99% error detection
    - Syntax validation (AST parsing)
    - Type checking (mypy)
    - Unit test generation and execution

    Level 2 (Module): 95% integration validation
    - Module integration tests
    - API consistency checks
    - Cohesion analysis

    Level 3 (Component): 90% E2E validation
    - Component E2E tests
    - Architecture validation
    - Performance benchmarking

    Level 4 (System): 85% system validation
    - Full system tests
    - Acceptance criteria validation
    - Production readiness checks
    """
    __tablename__ = "validation_results"

    # Primary Key
    validation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    atom_id = Column(UUID(as_uuid=True), ForeignKey("atomic_units.atom_id", ondelete="CASCADE"), nullable=False)

    # Validation Info
    validation_level = Column(Enum(ValidationLevel), nullable=False, index=True)
    level_number = Column(Integer, nullable=False)  # 1, 2, 3, 4

    # Results
    passed = Column(Boolean, nullable=False, index=True)
    test_type = Column(String(100), nullable=False)  # syntax|types|unit|integration|e2e|acceptance
    test_output = Column(Text, nullable=True)
    error_details = Column(JSONB, nullable=True)  # Structured error information

    # Performance
    execution_time_ms = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    atom = relationship("AtomicUnit", back_populates="validation_results")

    # Indexes
    __table_args__ = (
        Index("idx_validation_atom", "atom_id"),
        Index("idx_validation_level", "validation_level"),
        Index("idx_validation_passed", "passed"),
        Index("idx_validation_created", "created_at"),
        Index("idx_validation_atom_level", "atom_id", "validation_level"),  # Composite for queries
    )

    def __repr__(self) -> str:
        status = "PASSED" if self.passed else "FAILED"
        return f"<ValidationResult(atom_id={self.atom_id}, level={self.validation_level}, type={self.test_type}, status={status})>"

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses"""
        return {
            "validation_id": str(self.validation_id),
            "atom_id": str(self.atom_id),
            "validation_level": self.validation_level.value,
            "level_number": self.level_number,
            "passed": self.passed,
            "test_type": self.test_type,
            "test_output": self.test_output,
            "error_details": self.error_details,
            "execution_time_ms": self.execution_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
