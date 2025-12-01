"""
Dashboard State - Dataclass holding all dashboard state.

Reference: DOCS/mvp/exit/anti/PRO_DASHBOARD_IMPLEMENTATION_PLAN.md Task 1
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class PhaseStatus(Enum):
    """Status of a pipeline phase."""
    PENDING = "pending"      # ⏳ Not started
    RUNNING = "running"      # ◐ Animated spinner
    COMPLETED = "completed"  # ✓ Green check
    FAILED = "failed"        # ✗ Red X
    SKIPPED = "skipped"      # ⊘ Grey


class LogLevel(Enum):
    """Log message level."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class LogEntry:
    """A single log entry."""
    timestamp: datetime
    message: str
    level: LogLevel = LogLevel.INFO
    
    @property
    def icon(self) -> str:
        """Get icon for log level."""
        icons = {
            LogLevel.INFO: " ",
            LogLevel.SUCCESS: "✓",
            LogLevel.WARNING: "⚠",
            LogLevel.ERROR: "✗",
        }
        return icons.get(self.level, " ")
    
    @property
    def color(self) -> str:
        """Get Rich color for log level."""
        colors = {
            LogLevel.INFO: "white",
            LogLevel.SUCCESS: "green",
            LogLevel.WARNING: "yellow",
            LogLevel.ERROR: "red",
        }
        return colors.get(self.level, "white")


@dataclass
class PhaseState:
    """State of a single phase."""
    name: str
    status: PhaseStatus = PhaseStatus.PENDING
    current_step: int = 0
    total_steps: int = 1
    message: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: Optional[str] = None
    
    @property
    def progress(self) -> float:
        """Progress as 0.0 to 1.0."""
        if self.total_steps == 0:
            return 0.0
        return min(1.0, self.current_step / self.total_steps)
    
    @property
    def elapsed_seconds(self) -> float:
        """Elapsed time in seconds."""
        if not self.start_time:
            return 0.0
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()


@dataclass 
class MetricsState:
    """Current metrics for dashboard cards."""
    # Tests
    tests_passed: int = 0
    tests_total: int = 0
    
    # Compliance
    compliance_percent: float = 0.0
    
    # LLM
    llm_cost: float = 0.0
    llm_tokens: int = 0
    
    # Repair Loop
    repair_iteration: int = 0
    repair_max: int = 3
    repair_status: str = "skip"  # skip, running, completed, failed


@dataclass
class DashboardState:
    """Complete dashboard state."""
    # Pipeline info
    pipeline_name: str = "DevMatrix Pipeline"
    start_time: datetime = field(default_factory=datetime.now)
    
    # Phases
    phases: List[PhaseState] = field(default_factory=list)
    current_phase_index: int = -1
    total_phases: int = 13
    
    # Metrics
    metrics: MetricsState = field(default_factory=MetricsState)
    
    # Logs (last N entries)
    logs: List[LogEntry] = field(default_factory=list)
    max_logs: int = 5
    
    # Final status
    final_status: Optional[str] = None  # SUCCESS, FAILED, None if running
    
    @property
    def current_phase(self) -> Optional[PhaseState]:
        """Get current running phase."""
        if 0 <= self.current_phase_index < len(self.phases):
            return self.phases[self.current_phase_index]
        return None
    
    @property
    def completed_phases(self) -> int:
        """Count of completed phases."""
        return sum(1 for p in self.phases if p.status == PhaseStatus.COMPLETED)
    
    @property
    def overall_progress(self) -> float:
        """Overall pipeline progress 0.0 to 1.0."""
        if self.total_phases == 0:
            return 0.0
        completed = self.completed_phases
        current_progress = 0.0
        if self.current_phase:
            current_progress = self.current_phase.progress
        return (completed + current_progress) / self.total_phases
    
    @property
    def total_elapsed_seconds(self) -> float:
        """Total elapsed time."""
        return (datetime.now() - self.start_time).total_seconds()
    
    def add_log(self, message: str, level: LogLevel = LogLevel.INFO):
        """Add a log entry, keeping only last max_logs."""
        entry = LogEntry(timestamp=datetime.now(), message=message, level=level)
        self.logs.append(entry)
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]

