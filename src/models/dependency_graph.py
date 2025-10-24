"""
Dependency Graph Database Models

SQLAlchemy ORM models for MGE V2 dependency graph and edges.

DependencyGraph: Stores NetworkX graph metadata
AtomDependency: Individual dependency edges between atoms

Schema design based on MGE V2 specification.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, List
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, Enum, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
import enum

from src.config.database import Base


# Enums
class DependencyType(str, enum.Enum):
    """Type of dependency between atoms"""
    IMPORT = "import"            # Import dependency (module import)
    DATA_FLOW = "data_flow"      # Data flow dependency (variable usage)
    FUNCTION_CALL = "function_call"  # Function call dependency
    TYPE = "type"                # Type dependency (class/interface usage)
    TEMPORAL = "temporal"        # Temporal dependency (must execute in order)


class DependencyGraph(Base):
    """
    Dependency Graph - NetworkX graph metadata

    Stores the complete dependency graph for a masterplan:
    - Graph structure (NetworkX DiGraph as JSON)
    - Topological sort for execution order
    - Wave groupings for parallel execution
    - Cycle detection results
    """
    __tablename__ = "dependency_graphs"

    # Primary Key
    graph_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    masterplan_id = Column(UUID(as_uuid=True), ForeignKey("masterplans.masterplan_id", ondelete="CASCADE"), nullable=False)

    # Graph Data (stored as NetworkX JSON)
    graph_data = Column(JSONB, nullable=False)  # Complete NetworkX graph

    # Graph Statistics
    total_atoms = Column(Integer, nullable=False)
    total_edges = Column(Integer, nullable=False)
    total_waves = Column(Integer, nullable=False)  # Number of execution waves
    max_parallelism = Column(Integer, nullable=False)  # Max atoms that can run in parallel

    # Cycle Detection
    has_cycles = Column(Boolean, nullable=False, default=False)

    # Execution Order (topological sort)
    topological_order = Column(ARRAY(UUID(as_uuid=True)), nullable=True)  # Sorted atom IDs

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    masterplan = relationship("MasterPlan", foreign_keys=[masterplan_id])
    dependencies = relationship(
        "AtomDependency",
        back_populates="graph",
        cascade="all, delete-orphan"
    )
    waves = relationship(
        "ExecutionWave",
        back_populates="graph",
        cascade="all, delete-orphan",
        order_by="ExecutionWave.wave_number"
    )

    # Indexes
    __table_args__ = (
        Index("idx_dependency_graphs_masterplan", "masterplan_id"),
        Index("idx_dependency_graphs_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<DependencyGraph(graph_id={self.graph_id}, atoms={self.total_atoms}, waves={self.total_waves}, max_parallel={self.max_parallelism})>"

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses"""
        return {
            "graph_id": str(self.graph_id),
            "masterplan_id": str(self.masterplan_id),
            "total_atoms": self.total_atoms,
            "total_edges": self.total_edges,
            "total_waves": self.total_waves,
            "max_parallelism": self.max_parallelism,
            "has_cycles": self.has_cycles,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AtomDependency(Base):
    """
    Atom Dependency - Edge in dependency graph

    Represents a dependency relationship between two atoms:
    - from_atom depends on to_atom
    - to_atom must execute before from_atom
    - Typed dependencies (import, data flow, function call, etc.)
    """
    __tablename__ = "atom_dependencies"

    # Primary Key
    dependency_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    graph_id = Column(UUID(as_uuid=True), ForeignKey("dependency_graphs.graph_id", ondelete="CASCADE"), nullable=False)
    from_atom_id = Column(UUID(as_uuid=True), ForeignKey("atomic_units.atom_id", ondelete="CASCADE"), nullable=False)  # Dependent
    to_atom_id = Column(UUID(as_uuid=True), ForeignKey("atomic_units.atom_id", ondelete="CASCADE"), nullable=False)  # Dependency

    # Dependency Info
    dependency_type = Column(Enum(DependencyType), nullable=False, index=True)
    strength = Column(Float, nullable=False, default=1.0)  # 0.0-1.0 (weak to strong)
    dep_metadata = Column(JSONB, nullable=True)  # Additional info (e.g., imported symbols, called functions)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    graph = relationship("DependencyGraph", back_populates="dependencies")
    from_atom = relationship(
        "AtomicUnit",
        foreign_keys=[from_atom_id],
        back_populates="dependencies_from"
    )
    to_atom = relationship(
        "AtomicUnit",
        foreign_keys=[to_atom_id],
        back_populates="dependencies_to"
    )

    # Indexes and Constraints
    __table_args__ = (
        Index("idx_dependencies_graph", "graph_id"),
        Index("idx_dependencies_from", "from_atom_id"),
        Index("idx_dependencies_to", "to_atom_id"),
        Index("idx_dependencies_type", "dependency_type"),
        UniqueConstraint("from_atom_id", "to_atom_id", name="uq_atom_dependency"),  # Prevent duplicate edges
    )

    def __repr__(self) -> str:
        return f"<AtomDependency(from={self.from_atom_id}, to={self.to_atom_id}, type={self.dependency_type})>"

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses"""
        return {
            "dependency_id": str(self.dependency_id),
            "from_atom_id": str(self.from_atom_id),
            "to_atom_id": str(self.to_atom_id),
            "dependency_type": self.dependency_type.value,
            "strength": self.strength,
            "metadata": self.metadata,
        }
