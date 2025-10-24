"""
Database Models

ORM models for the DevMatrix MVP system.
"""

from .masterplan import (
    # Enums
    MasterPlanStatus,
    TaskStatus,
    TaskComplexity,
    PhaseType,

    # Models
    DiscoveryDocument,
    MasterPlan,
    MasterPlanPhase,
    MasterPlanMilestone,
    MasterPlanTask,
    MasterPlanSubtask,
    MasterPlanVersion,
    MasterPlanHistory,
)

from .user import User
from .user_quota import UserQuota
from .user_usage import UserUsage
from .conversation import Conversation
from .message import Message

# MGE V2 models
from .atomic_unit import AtomicUnit, AtomStatus
from .dependency_graph import DependencyGraph, AtomDependency, DependencyType
from .validation_result import ValidationResult, ValidationLevel
from .execution_wave import ExecutionWave, WaveStatus
from .atom_retry import AtomRetryHistory
from .human_review import HumanReviewQueue, ReviewStatus, ReviewResolution

__all__ = [
    # Enums
    "MasterPlanStatus",
    "TaskStatus",
    "TaskComplexity",
    "PhaseType",

    # Models
    "DiscoveryDocument",
    "MasterPlan",
    "MasterPlanPhase",
    "MasterPlanMilestone",
    "MasterPlanTask",
    "MasterPlanSubtask",
    "MasterPlanVersion",
    "MasterPlanHistory",

    # Authentication & Multi-tenancy Models
    "User",
    "UserQuota",
    "UserUsage",
    "Conversation",
    "Message",

    # MGE V2 models
    "AtomicUnit",
    "DependencyGraph",
    "AtomDependency",
    "ValidationResult",
    "ExecutionWave",
    "AtomRetryHistory",
    "HumanReviewQueue",

    # MGE V2 enums
    "AtomStatus",
    "DependencyType",
    "ValidationLevel",
    "WaveStatus",
    "ReviewStatus",
    "ReviewResolution",
]
