"""
MasterPlan Database Models

SQLAlchemy ORM models for the MasterPlan MVP system.

Schema design based on MASTERPLAN_DESIGN.md:
- DiscoveryDocument: DDD discovery results
- MasterPlan: Main plan with metadata and stack
- MasterPlanPhase: Execution phases (Setup, Core, Polish)
- MasterPlanMilestone: Milestones within phases
- MasterPlanTask: Atomic tasks with dependencies
- MasterPlanSubtask: Sub-tasks for complex tasks
- MasterPlanVersion: Version tracking
- MasterPlanHistory: Execution history
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, List, Any
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime, JSON, ForeignKey, Enum, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from src.config.database import Base


# Enums
class MasterPlanStatus(str, enum.Enum):
    """MasterPlan execution status"""
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(str, enum.Enum):
    """Task execution status"""
    PENDING = "pending"
    READY = "ready"  # All dependencies met
    IN_PROGRESS = "in_progress"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"  # Dependencies failed


class TaskComplexity(str, enum.Enum):
    """Task complexity for LLM model selection"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PhaseType(str, enum.Enum):
    """MasterPlan phase types"""
    SETUP = "setup"
    CORE = "core"
    POLISH = "polish"


# Models
class DiscoveryDocument(Base):
    """
    DDD Discovery Document

    Stores discovery phase results:
    - Domain identification
    - Bounded contexts
    - Aggregates and entities
    - Value objects
    - Domain events
    - Services
    """
    __tablename__ = "discovery_documents"

    # Primary Key
    discovery_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Metadata
    session_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    user_request = Column(Text, nullable=False)  # Original user request

    # Discovery Results (JSON)
    domain = Column(String(200), nullable=False)
    bounded_contexts = Column(JSON, nullable=False)  # List of bounded contexts
    aggregates = Column(JSON, nullable=False)  # List of aggregates with entities
    value_objects = Column(JSON, nullable=False)  # List of value objects
    domain_events = Column(JSON, nullable=False)  # List of domain events
    services = Column(JSON, nullable=False)  # List of domain/application services

    # Additional Context
    assumptions = Column(JSON)  # Assumptions made during discovery
    clarifications_needed = Column(JSON)  # Questions for user
    risk_factors = Column(JSON)  # Identified risks

    # LLM Metadata
    llm_model = Column(String(100))  # Model used for discovery
    llm_cost_usd = Column(Float)  # Discovery cost

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    masterplans = relationship("MasterPlan", back_populates="discovery", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_discovery_session", "session_id"),
        Index("idx_discovery_user", "user_id"),
        Index("idx_discovery_created", "created_at"),
    )


class MasterPlan(Base):
    """
    MasterPlan - Main plan document

    Stores the complete MasterPlan with metadata, tech stack, and execution state.
    """
    __tablename__ = "masterplans"

    # Primary Key
    masterplan_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    discovery_id = Column(UUID(as_uuid=True), ForeignKey("discovery_documents.discovery_id"), nullable=False)

    # Metadata
    session_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    project_name = Column(String(200), nullable=False)
    description = Column(Text)

    # Status
    status = Column(Enum(MasterPlanStatus), default=MasterPlanStatus.DRAFT, nullable=False, index=True)

    # Tech Stack (JSON)
    tech_stack = Column(JSON, nullable=False)  # {backend, frontend, database, etc.}
    architecture_style = Column(String(100))  # e.g., "microservices", "monolithic"

    # Execution Metrics
    total_phases = Column(Integer, default=3)  # Setup, Core, Polish
    total_milestones = Column(Integer, default=0)
    total_tasks = Column(Integer, default=0)
    total_subtasks = Column(Integer, default=0)

    # Progress Tracking
    completed_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)
    skipped_tasks = Column(Integer, default=0)
    progress_percent = Column(Float, default=0.0)

    # Cost & Performance
    estimated_cost_usd = Column(Float)  # Estimated LLM cost
    actual_cost_usd = Column(Float, default=0.0)  # Actual LLM cost
    estimated_duration_minutes = Column(Integer)  # Estimated execution time
    actual_duration_minutes = Column(Integer)  # Actual execution time

    # LLM Generation Metadata
    llm_model = Column(String(100))  # Model used for generation
    generation_cost_usd = Column(Float)  # Cost to generate plan
    generation_tokens = Column(Integer)  # Tokens used

    # Workspace Path - Added for execution tracking
    workspace_path = Column(String(500), nullable=True)  # Absolute path to workspace directory

    # Version Control
    version = Column(Integer, default=1)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Relationships
    discovery = relationship("DiscoveryDocument", back_populates="masterplans")
    phases = relationship("MasterPlanPhase", back_populates="masterplan", cascade="all, delete-orphan")
    versions = relationship("MasterPlanVersion", back_populates="masterplan", foreign_keys="MasterPlanVersion.masterplan_id")
    history = relationship("MasterPlanHistory", back_populates="masterplan", cascade="all, delete-orphan")
    acceptance_tests = relationship("AcceptanceTest", back_populates="masterplan", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_masterplan_session", "session_id"),
        Index("idx_masterplan_user", "user_id"),
        Index("idx_masterplan_status", "status"),
        Index("idx_masterplan_created", "created_at"),
    )


class MasterPlanPhase(Base):
    """
    MasterPlan Phase (Setup, Core, Polish)

    Execution phases for organizing tasks.
    """
    __tablename__ = "masterplan_phases"

    # Primary Key
    phase_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    masterplan_id = Column(UUID(as_uuid=True), ForeignKey("masterplans.masterplan_id"), nullable=False)

    # Phase Info
    phase_type = Column(Enum(PhaseType), nullable=False)
    phase_number = Column(Integer, nullable=False)  # 1, 2, 3
    name = Column(String(200), nullable=False)
    description = Column(Text)

    # Progress
    total_milestones = Column(Integer, default=0)
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    progress_percent = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Relationships
    masterplan = relationship("MasterPlan", back_populates="phases")
    milestones = relationship("MasterPlanMilestone", back_populates="phase", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_phase_masterplan", "masterplan_id"),
        Index("idx_phase_number", "masterplan_id", "phase_number"),
    )


class MasterPlanMilestone(Base):
    """
    Milestone within a Phase

    Groups related tasks into logical milestones.
    """
    __tablename__ = "masterplan_milestones"

    # Primary Key
    milestone_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    phase_id = Column(UUID(as_uuid=True), ForeignKey("masterplan_phases.phase_id"), nullable=False)

    # Milestone Info
    milestone_number = Column(Integer, nullable=False)  # e.g., 1, 2, 3
    name = Column(String(200), nullable=False)
    description = Column(Text)

    # Dependencies
    depends_on_milestones = Column(JSON)  # List of milestone_ids

    # Progress
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    progress_percent = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Relationships
    phase = relationship("MasterPlanPhase", back_populates="milestones")
    tasks = relationship("MasterPlanTask", back_populates="milestone", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_milestone_phase", "phase_id"),
        Index("idx_milestone_number", "phase_id", "milestone_number"),
    )


class MasterPlanTask(Base):
    """
    Atomic Task - Main execution unit

    Each task is:
    - Atomic (single responsibility)
    - Executable by LLM
    - Validated automatically
    - Tracked for dependencies
    """
    __tablename__ = "masterplan_tasks"

    # Primary Key
    task_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    masterplan_id = Column(UUID(as_uuid=True), ForeignKey("masterplans.masterplan_id"), nullable=False, index=True)
    phase_id = Column(UUID(as_uuid=True), ForeignKey("masterplan_phases.phase_id"), nullable=True, index=True)
    milestone_id = Column(UUID(as_uuid=True), ForeignKey("masterplan_milestones.milestone_id"), nullable=False)

    # Task Info
    task_number = Column(Integer, nullable=False)  # Global task number (1-50)
    name = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)

    # Task Classification
    complexity = Column(Enum(TaskComplexity), default=TaskComplexity.MEDIUM, nullable=False)
    task_type = Column(String(100))  # e.g., "model_creation", "api_endpoint", "validation"

    # Dependencies
    depends_on_tasks = Column(JSON)  # List of task_ids
    blocks_tasks = Column(JSON)  # List of task_ids that depend on this

    # Execution State
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)

    # Files to Create/Modify
    target_files = Column(JSON)  # List of file paths
    modified_files = Column(JSON)  # Actual files modified

    # LLM Execution
    llm_model = Column(String(100))  # Model used for execution
    llm_prompt = Column(Text)  # Prompt sent to LLM
    llm_response = Column(Text)  # LLM response
    llm_cost_usd = Column(Float)  # Task execution cost
    llm_tokens_input = Column(Integer)
    llm_tokens_output = Column(Integer)
    llm_cached_tokens = Column(Integer)  # Prompt caching savings

    # Validation
    validation_passed = Column(Boolean)
    validation_errors = Column(JSON)  # List of validation errors
    validation_logs = Column(Text)  # Validation output

    # Retry Logic
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=1)  # MVP: 1 retry max
    last_error = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    failed_at = Column(DateTime)

    # Relationships
    milestone = relationship("MasterPlanMilestone", back_populates="tasks")
    subtasks = relationship("MasterPlanSubtask", back_populates="task", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_task_milestone", "milestone_id"),
        Index("idx_task_status", "status"),
        Index("idx_task_number", "milestone_id", "task_number"),
    )


class MasterPlanSubtask(Base):
    """
    Sub-task for Complex Tasks

    Some tasks need breakdown into smaller steps.
    """
    __tablename__ = "masterplan_subtasks"

    # Primary Key
    subtask_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    task_id = Column(UUID(as_uuid=True), ForeignKey("masterplan_tasks.task_id"), nullable=False)

    # Subtask Info
    subtask_number = Column(Integer, nullable=False)
    name = Column(String(300), nullable=False)
    description = Column(Text)

    # Execution
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    completed = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    # Relationships
    task = relationship("MasterPlanTask", back_populates="subtasks")

    # Indexes
    __table_args__ = (
        Index("idx_subtask_task", "task_id"),
    )


class MasterPlanVersion(Base):
    """
    MasterPlan Version Tracking

    Stores historical versions of MasterPlans for rollback/comparison.
    """
    __tablename__ = "masterplan_versions"

    # Primary Key
    version_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    masterplan_id = Column(UUID(as_uuid=True), ForeignKey("masterplans.masterplan_id"), nullable=False)

    # Version Info
    version_number = Column(Integer, nullable=False)
    change_description = Column(Text)

    # Snapshot (JSON)
    snapshot = Column(JSON, nullable=False)  # Complete plan state

    # Metadata
    created_by = Column(String(100))  # "system" or user_id
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    masterplan = relationship("MasterPlan", back_populates="versions", foreign_keys=[masterplan_id])

    # Indexes
    __table_args__ = (
        Index("idx_version_masterplan", "masterplan_id"),
        Index("idx_version_number", "masterplan_id", "version_number"),
    )


class MasterPlanHistory(Base):
    """
    MasterPlan Execution History

    Audit trail of all actions taken during execution.
    """
    __tablename__ = "masterplan_history"

    # Primary Key
    history_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    masterplan_id = Column(UUID(as_uuid=True), ForeignKey("masterplans.masterplan_id"), nullable=False)
    task_id = Column(UUID(as_uuid=True), ForeignKey("masterplan_tasks.task_id"), nullable=True)

    # Event Info
    event_type = Column(String(100), nullable=False)  # "task_started", "task_completed", etc.
    event_data = Column(JSON)  # Additional event data

    # Actor
    actor = Column(String(100))  # "system", "user", "llm"

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    masterplan = relationship("MasterPlan", back_populates="history")

    # Indexes
    __table_args__ = (
        Index("idx_history_masterplan", "masterplan_id"),
        Index("idx_history_task", "task_id"),
        Index("idx_history_created", "created_at"),
    )
