"""
E2E Tracing Models for MGE V2

Captures complete atom execution flow: context → L1-L4 → acceptance → retries → cost/time
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum
from pydantic import BaseModel, Field


class TraceEventType(str, Enum):
    """Types of trace events in atom execution flow."""
    ATOM_STARTED = "atom_started"
    CONTEXT_LOADED = "context_loaded"
    VALIDATION_L1_STARTED = "validation_l1_started"
    VALIDATION_L1_COMPLETED = "validation_l1_completed"
    VALIDATION_L2_STARTED = "validation_l2_started"
    VALIDATION_L2_COMPLETED = "validation_l2_completed"
    VALIDATION_L3_STARTED = "validation_l3_started"
    VALIDATION_L3_COMPLETED = "validation_l3_completed"
    VALIDATION_L4_STARTED = "validation_l4_started"
    VALIDATION_L4_COMPLETED = "validation_l4_completed"
    CODE_GENERATION_STARTED = "code_generation_started"
    CODE_GENERATION_COMPLETED = "code_generation_completed"
    RETRY_ATTEMPT = "retry_attempt"
    ACCEPTANCE_TESTS_STARTED = "acceptance_tests_started"
    ACCEPTANCE_TESTS_COMPLETED = "acceptance_tests_completed"
    ATOM_COMPLETED = "atom_completed"
    ATOM_FAILED = "atom_failed"


class TraceEvent(BaseModel):
    """Single event in atom execution trace."""
    event_id: UUID = Field(default_factory=uuid4)
    event_type: TraceEventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: Optional[float] = None
    error: Optional[str] = None


class ValidationTrace(BaseModel):
    """Trace of validation phases (L1-L4)."""
    l1_syntax: Optional[TraceEvent] = None
    l2_imports: Optional[TraceEvent] = None
    l3_types: Optional[TraceEvent] = None
    l4_complexity: Optional[TraceEvent] = None
    total_duration_ms: float = 0.0
    passed: bool = False
    issues_count: int = 0


class RetryTrace(BaseModel):
    """Trace of retry attempts."""
    attempt_number: int
    temperature: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    success: bool
    duration_ms: float
    error_feedback: Optional[List[str]] = None


class AcceptanceTestTrace(BaseModel):
    """Trace of acceptance test execution."""
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    must_pass_rate: float = 0.0
    should_pass_rate: float = 0.0
    duration_ms: float = 0.0
    timestamp: Optional[datetime] = None


class CostMetrics(BaseModel):
    """Cost tracking metrics."""
    llm_api_cost_usd: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cache_hit: bool = False


class TimeMetrics(BaseModel):
    """Time tracking metrics."""
    total_duration_ms: float = 0.0
    validation_duration_ms: float = 0.0
    generation_duration_ms: float = 0.0
    acceptance_duration_ms: float = 0.0
    retry_overhead_ms: float = 0.0


class AtomTrace(BaseModel):
    """
    Complete E2E trace for a single atomic unit execution.

    Captures full flow: context → L1-L4 → acceptance → retries → cost/time
    """
    trace_id: UUID = Field(default_factory=uuid4)
    atom_id: UUID
    masterplan_id: UUID
    wave_id: int
    atom_name: str

    # Context
    context_data: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)

    # Validation trace (L1-L4)
    validation: ValidationTrace = Field(default_factory=ValidationTrace)

    # Retry trace
    retries: List[RetryTrace] = Field(default_factory=list)
    total_attempts: int = 0

    # Acceptance tests trace
    acceptance_tests: Optional[AcceptanceTestTrace] = None

    # Cost & Time metrics
    cost: CostMetrics = Field(default_factory=CostMetrics)
    time: TimeMetrics = Field(default_factory=TimeMetrics)

    # Events log
    events: List[TraceEvent] = Field(default_factory=list)

    # Status
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    final_status: Optional[str] = None  # "success", "failed", "error"

    # Result
    code_generated: Optional[str] = None
    final_validation_passed: bool = False

    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat() if v else None
        }

    def add_event(
        self,
        event_type: TraceEventType,
        data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
        error: Optional[str] = None
    ) -> TraceEvent:
        """Add event to trace."""
        event = TraceEvent(
            event_type=event_type,
            data=data or {},
            duration_ms=duration_ms,
            error=error
        )
        self.events.append(event)
        return event

    def record_retry(
        self,
        attempt: int,
        temperature: float,
        success: bool,
        duration_ms: float,
        error_feedback: Optional[List[str]] = None
    ):
        """Record retry attempt."""
        retry = RetryTrace(
            attempt_number=attempt,
            temperature=temperature,
            success=success,
            duration_ms=duration_ms,
            error_feedback=error_feedback
        )
        self.retries.append(retry)
        self.total_attempts = len(self.retries)

    def complete(self, status: str, code: Optional[str] = None):
        """Mark trace as completed."""
        self.completed_at = datetime.utcnow()
        self.final_status = status
        self.code_generated = code

        # Calculate total time
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            self.time.total_duration_ms = delta.total_seconds() * 1000


class TraceCorrelation(BaseModel):
    """Correlation data for dashboard visualizations."""
    masterplan_id: UUID
    total_atoms: int

    # Correlation: retries vs success
    avg_retries_success: float
    avg_retries_failed: float

    # Correlation: validation issues vs success
    avg_l1_issues_success: float
    avg_l1_issues_failed: float

    # Correlation: complexity vs time
    complexity_time_data: List[Dict[str, Any]] = Field(default_factory=list)

    # Correlation: cost vs success
    cost_success_correlation: float = 0.0

    # Correlation: acceptance pass rate vs final success
    acceptance_success_correlation: float = 0.0

    class Config:
        json_encoders = {
            UUID: str
        }
