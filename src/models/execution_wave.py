"""
Execution Wave Database Model

SQLAlchemy ORM model for MGE V2 wave-based parallel execution.

ExecutionWave: Groups atoms that can execute in parallel

Schema design based on MGE V2 specification.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, List
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, ForeignKey, Enum, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import enum

from src.config.database import Base


# Enums
class WaveStatus(str, enum.Enum):
    """Execution wave status"""
    PENDING = "pending"        # Not yet started
    RUNNING = "running"        # Currently executing
    COMPLETED = "completed"    # All atoms completed successfully
    FAILED = "failed"          # Some atoms failed critically
    PARTIAL = "partial"        # Some atoms completed, some failed


class ExecutionWave(Base):
    """
    Execution Wave - Parallel execution group

    Groups atoms that can execute concurrently:
    - No dependencies between atoms in same wave
    - All wave N atoms execute before wave N+1
    - Enables 100+ atom parallelization

    Wave generation from topological sort:
    - Wave 1: Atoms with no dependencies
    - Wave 2: Atoms depending only on Wave 1
    - Wave 3: Atoms depending on Waves 1-2
    - ...
    """
    __tablename__ = "execution_waves"

    # Primary Key
    wave_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    graph_id = Column(UUID(as_uuid=True), ForeignKey("dependency_graphs.graph_id", ondelete="CASCADE"), nullable=False)

    # Wave Info
    wave_number = Column(Integer, nullable=False, index=True)  # 1, 2, 3, ...
    atom_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False)  # Atoms in this wave

    # Progress Tracking
    total_atoms = Column(Integer, nullable=False)
    completed_atoms = Column(Integer, nullable=False, default=0)
    failed_atoms = Column(Integer, nullable=False, default=0)

    # Status
    status = Column(Enum(WaveStatus), nullable=False, default=WaveStatus.PENDING, index=True)

    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)  # Wave execution time

    # Relationships
    graph = relationship("DependencyGraph", back_populates="waves")
    acceptance_test_results = relationship("AcceptanceTestResult", back_populates="wave", cascade="all, delete-orphan")

    # Indexes and Constraints
    __table_args__ = (
        Index("idx_waves_graph", "graph_id"),
        Index("idx_waves_number", "wave_number"),
        Index("idx_waves_status", "status"),
        Index("idx_waves_graph_number", "graph_id", "wave_number"),  # Composite for ordering
        UniqueConstraint("graph_id", "wave_number", name="uq_wave_number"),  # One wave per number per graph
    )

    def __repr__(self) -> str:
        return f"<ExecutionWave(wave_id={self.wave_id}, wave_number={self.wave_number}, atoms={self.total_atoms}, status={self.status})>"

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses"""
        return {
            "wave_id": str(self.wave_id),
            "graph_id": str(self.graph_id),
            "wave_number": self.wave_number,
            "atom_ids": [str(aid) for aid in self.atom_ids] if self.atom_ids else [],
            "total_atoms": self.total_atoms,
            "completed_atoms": self.completed_atoms,
            "failed_atoms": self.failed_atoms,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
        }

    @property
    def progress_percent(self) -> float:
        """Calculate wave progress percentage"""
        if self.total_atoms == 0:
            return 0.0
        return (self.completed_atoms / self.total_atoms) * 100.0

    @property
    def failure_rate(self) -> float:
        """Calculate wave failure rate"""
        if self.total_atoms == 0:
            return 0.0
        return (self.failed_atoms / self.total_atoms) * 100.0
