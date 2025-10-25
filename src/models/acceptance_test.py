"""
Acceptance test models for MGE V2

Auto-generated tests from masterplan requirements with must/should classification
"""
from sqlalchemy import Column, String, Integer, Text, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from src.config.database import Base


class AcceptanceTest(Base):
    """
    Generated acceptance test from masterplan requirement

    Tests are auto-generated from masterplan markdown:
    ## Requirements
    ### MUST
    - User authentication must use JWT tokens
    ### SHOULD
    - UI should be responsive on mobile
    """
    __tablename__ = "acceptance_tests"

    # Primary key
    test_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    masterplan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("masterplans.masterplan_id", ondelete="CASCADE"),
        nullable=False
    )

    # Requirement data
    requirement_text = Column(Text, nullable=False, comment="Original requirement from masterplan")
    requirement_priority = Column(
        String(10),
        nullable=False,
        comment="must or should classification"
    )

    # Test code
    test_code = Column(Text, nullable=False, comment="Generated test code (pytest/jest/vitest)")
    test_language = Column(
        String(20),
        nullable=False,
        comment="pytest, jest, or vitest"
    )
    test_framework_version = Column(String(20))

    # Configuration
    timeout_seconds = Column(Integer, default=30, comment="Test execution timeout")

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    masterplan = relationship("Masterplan", back_populates="acceptance_tests")
    results = relationship(
        "AcceptanceTestResult",
        back_populates="test",
        cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "requirement_priority IN ('must', 'should')",
            name="valid_priority"
        ),
        CheckConstraint(
            "test_language IN ('pytest', 'jest', 'vitest')",
            name="valid_language"
        ),
        Index("idx_acceptance_tests_masterplan", "masterplan_id"),
        Index("idx_acceptance_tests_priority", "masterplan_id", "requirement_priority"),
    )

    def __repr__(self):
        return (
            f"<AcceptanceTest("
            f"test_id={self.test_id}, "
            f"priority={self.requirement_priority}, "
            f"language={self.test_language}"
            f")>"
        )


class AcceptanceTestResult(Base):
    """
    Execution result for an acceptance test

    Stores pass/fail status, execution time, error messages
    """
    __tablename__ = "acceptance_test_results"

    # Primary key
    result_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    test_id = Column(
        UUID(as_uuid=True),
        ForeignKey("acceptance_tests.test_id", ondelete="CASCADE"),
        nullable=False
    )
    wave_id = Column(
        UUID(as_uuid=True),
        ForeignKey("execution_waves.wave_id"),
        nullable=True
    )

    # Execution metadata
    execution_time = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False)

    # Result data
    status = Column(
        String(20),
        nullable=False,
        comment="pass, fail, timeout, or error"
    )
    error_message = Column(Text, comment="Error message if failed")
    execution_duration_ms = Column(Integer, comment="Actual execution time in milliseconds")

    # Output
    stdout = Column(Text, comment="Test stdout")
    stderr = Column(Text, comment="Test stderr")

    # Relationships
    test = relationship("AcceptanceTest", back_populates="results")
    wave = relationship("ExecutionWave", back_populates="acceptance_test_results")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pass', 'fail', 'timeout', 'error')",
            name="valid_status"
        ),
        Index("idx_test_results_test", "test_id"),
        Index("idx_test_results_wave", "wave_id"),
        Index("idx_test_results_status", "test_id", "status"),
    )

    def __repr__(self):
        return (
            f"<AcceptanceTestResult("
            f"result_id={self.result_id}, "
            f"status={self.status}, "
            f"duration={self.execution_duration_ms}ms"
            f")>"
        )
