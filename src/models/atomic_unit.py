"""
AtomicUnit Database Model

SQLAlchemy ORM model for MGE V2 atomic execution units.

An AtomicUnit represents a ~10 LOC executable code block with:
- Complete context for execution
- Atomicity validation (complexity, independence, testability)
- Dependency tracking
- Execution state and retry history
- Confidence scoring for human review

Schema design based on MGE V2 specification.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, List
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, Enum, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
import enum

from src.config.database import Base


# Enums
class AtomStatus(str, enum.Enum):
    """Atomic unit execution status"""
    PENDING = "pending"        # Not yet ready to execute
    READY = "ready"            # All dependencies met
    RUNNING = "running"        # Currently executing
    COMPLETED = "completed"    # Successfully completed
    FAILED = "failed"          # Failed after all retries
    BLOCKED = "blocked"        # Dependencies failed
    SKIPPED = "skipped"        # Skipped by user or system


class AtomicUnit(Base):
    """
    Atomic Unit - 10 LOC execution unit

    Core execution unit in MGE V2:
    - Atomicity: Single responsibility, <15 LOC, complexity <3.0
    - Context completeness: All imports, types, pre/postconditions
    - Dependency-aware: Part of execution graph
    - Retryable: 3 attempts with temperature adjustment
    - Reviewable: Confidence scoring for human review
    """
    __tablename__ = "atomic_units"

    # Primary Key
    atom_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    masterplan_id = Column(UUID(as_uuid=True), ForeignKey("masterplans.masterplan_id", ondelete="CASCADE"), nullable=False)
    task_id = Column(UUID(as_uuid=True), ForeignKey("masterplan_tasks.task_id", ondelete="SET NULL"), nullable=True)  # For migration

    # Atom Info
    atom_number = Column(Integer, nullable=False)  # Sequential within masterplan (1-800)
    name = Column(String(1000), nullable=False)  # Long descriptive names for atoms
    description = Column(Text, nullable=False)

    # Code
    code_to_generate = Column(Text, nullable=False)  # Implementation code
    file_path = Column(String(500), nullable=True)  # Target file
    line_start = Column(Integer, nullable=True)  # Start line in file
    line_end = Column(Integer, nullable=True)  # End line in file
    language = Column(String(50), nullable=False)  # python, typescript, javascript
    loc = Column(Integer, nullable=False)  # Lines of code (target: ~10)
    complexity = Column(Float, nullable=False)  # Cyclomatic complexity (target: <3.0)

    # Context for Execution (JSONB for performance)
    imports = Column(JSONB, nullable=True)  # {module: [items]} e.g., {"typing": ["List", "Optional"]}
    type_schema = Column(JSONB, nullable=True)  # Type definitions needed
    preconditions = Column(JSONB, nullable=True)  # Required state before execution
    postconditions = Column(JSONB, nullable=True)  # Expected state after execution
    test_cases = Column(JSONB, nullable=True)  # Generated test cases
    context_completeness = Column(Float, nullable=True)  # Quality score 0.0-1.0 (target: ≥0.95)

    # Atomicity Validation
    atomicity_score = Column(Float, nullable=True)  # Overall atomicity 0.0-1.0
    atomicity_violations = Column(JSONB, nullable=True)  # List of violations with details
    is_atomic = Column(Boolean, nullable=False, default=True)

    # Execution State
    status = Column(Enum(AtomStatus), nullable=False, default=AtomStatus.PENDING, index=True)
    wave_number = Column(Integer, nullable=True, index=True)  # Execution wave (1-10)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)  # V2: 3 retries
    execution_result = Column(Text, nullable=True)  # Execution output
    error_message = Column(Text, nullable=True)  # Last error

    # Confidence and Review
    confidence_score = Column(Float, nullable=True, index=True)  # 0.0-1.0 (low=review)
    needs_review = Column(Boolean, nullable=False, default=False, index=True)  # Flagged for human review
    review_priority = Column(Integer, nullable=True)  # 1=critical, 5=low

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    masterplan = relationship("MasterPlan", foreign_keys=[masterplan_id])
    task = relationship("MasterPlanTask", foreign_keys=[task_id])

    # Dependencies (many-to-many via atom_dependencies table)
    dependencies_from = relationship(
        "AtomDependency",
        foreign_keys="AtomDependency.from_atom_id",
        back_populates="from_atom",
        cascade="all, delete-orphan"
    )
    dependencies_to = relationship(
        "AtomDependency",
        foreign_keys="AtomDependency.to_atom_id",
        back_populates="to_atom",
        cascade="all, delete-orphan"
    )

    # Validation results (one-to-many)
    validation_results = relationship(
        "ValidationResult",
        back_populates="atom",
        cascade="all, delete-orphan"
    )

    # Retry history (one-to-many)
    retry_history = relationship(
        "AtomRetryHistory",
        back_populates="atom",
        cascade="all, delete-orphan",
        order_by="AtomRetryHistory.attempt_number"
    )

    # Human review (one-to-one)
    review = relationship(
        "HumanReviewQueue",
        back_populates="atom",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_atomic_units_masterplan", "masterplan_id"),
        Index("idx_atomic_units_task", "task_id"),
        Index("idx_atomic_units_status", "status"),
        Index("idx_atomic_units_wave", "wave_number"),
        Index("idx_atomic_units_review", "needs_review"),
        Index("idx_atomic_units_confidence", "confidence_score"),
        Index("idx_atomic_units_number", "masterplan_id", "atom_number"),  # Composite for ordering
    )

    def __repr__(self) -> str:
        return f"<AtomicUnit(atom_id={self.atom_id}, name='{self.name}', status={self.status}, wave={self.wave_number})>"

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses"""
        return {
            "atom_id": str(self.atom_id),
            "atom_number": self.atom_number,
            "name": self.name,
            "description": self.description,
            "code": self.code_to_generate,
            "file_path": self.file_path,
            "language": self.language,
            "loc": self.loc,
            "complexity": self.complexity,
            "status": self.status.value,
            "wave_number": self.wave_number,
            "attempts": self.attempts,
            "confidence_score": self.confidence_score,
            "needs_review": self.needs_review,
            "atomicity_score": self.atomicity_score,
            "is_atomic": self.is_atomic,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
