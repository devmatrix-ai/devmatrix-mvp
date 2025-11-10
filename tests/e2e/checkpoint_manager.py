"""
Checkpoint Manager for E2E Test Recovery

Manages test state persistence and recovery for long-running E2E tests.
"""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class PhaseStatus(str, Enum):
    """Status of each pipeline phase."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PhaseCheckpoint:
    """Checkpoint data for a single phase."""
    phase_name: str
    status: PhaseStatus
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    error: Optional[str] = None
    retry_count: int = 0
    # Phase-specific data
    discovery_id: Optional[str] = None
    masterplan_id: Optional[str] = None
    conversation_id: Optional[str] = None
    generated_tasks_count: Optional[int] = None
    generated_code_count: Optional[int] = None
    atoms_count: Optional[int] = None
    waves_count: Optional[int] = None
    files_written_count: Optional[int] = None
    total_cost_usd: Optional[float] = None


@dataclass
class TestCheckpoint:
    """Complete test execution checkpoint."""
    test_name: str
    test_id: str
    started_at: str
    last_updated_at: str
    total_duration_seconds: float
    current_phase: str
    phases: Dict[str, PhaseCheckpoint]
    user_request: str
    total_retries: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "test_name": self.test_name,
            "test_id": self.test_id,
            "started_at": self.started_at,
            "last_updated_at": self.last_updated_at,
            "total_duration_seconds": self.total_duration_seconds,
            "current_phase": self.current_phase,
            "phases": {
                name: asdict(phase) for name, phase in self.phases.items()
            },
            "user_request": self.user_request,
            "total_retries": self.total_retries
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestCheckpoint":
        """Load from dictionary."""
        phases = {
            name: PhaseCheckpoint(**phase_data)
            for name, phase_data in data["phases"].items()
        }
        return cls(
            test_name=data["test_name"],
            test_id=data["test_id"],
            started_at=data["started_at"],
            last_updated_at=data["last_updated_at"],
            total_duration_seconds=data["total_duration_seconds"],
            current_phase=data["current_phase"],
            phases=phases,
            user_request=data["user_request"],
            total_retries=data.get("total_retries", 0)
        )


class CheckpointManager:
    """Manages test checkpoint persistence and recovery."""

    def __init__(self, checkpoint_dir: Path = None):
        """Initialize checkpoint manager.

        Args:
            checkpoint_dir: Directory to store checkpoint files
        """
        if checkpoint_dir is None:
            checkpoint_dir = Path(__file__).parent / "checkpoints"

        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.current_checkpoint: Optional[TestCheckpoint] = None

    def get_checkpoint_path(self, test_id: str) -> Path:
        """Get checkpoint file path for test ID."""
        return self.checkpoint_dir / f"checkpoint_{test_id}.json"

    def checkpoint_exists(self, test_id: str) -> bool:
        """Check if checkpoint exists for test ID."""
        return self.get_checkpoint_path(test_id).exists()

    def create_checkpoint(
        self,
        test_name: str,
        test_id: str,
        user_request: str,
        phases: list[str]
    ) -> TestCheckpoint:
        """Create new test checkpoint.

        Args:
            test_name: Name of the test
            test_id: Unique test identifier
            user_request: User request being tested
            phases: List of phase names in order

        Returns:
            Created checkpoint
        """
        now = datetime.utcnow().isoformat()

        phase_checkpoints = {
            phase: PhaseCheckpoint(
                phase_name=phase,
                status=PhaseStatus.PENDING
            )
            for phase in phases
        }

        checkpoint = TestCheckpoint(
            test_name=test_name,
            test_id=test_id,
            started_at=now,
            last_updated_at=now,
            total_duration_seconds=0.0,
            current_phase=phases[0] if phases else "",
            phases=phase_checkpoints,
            user_request=user_request,
            total_retries=0
        )

        self.current_checkpoint = checkpoint
        self.save_checkpoint(checkpoint)
        return checkpoint

    def load_checkpoint(self, test_id: str) -> Optional[TestCheckpoint]:
        """Load existing checkpoint.

        Args:
            test_id: Test identifier

        Returns:
            Loaded checkpoint or None if not found
        """
        checkpoint_path = self.get_checkpoint_path(test_id)

        if not checkpoint_path.exists():
            return None

        try:
            with open(checkpoint_path, 'r') as f:
                data = json.load(f)

            checkpoint = TestCheckpoint.from_dict(data)
            self.current_checkpoint = checkpoint
            return checkpoint

        except Exception as e:
            print(f"⚠️ Failed to load checkpoint: {e}")
            return None

    def save_checkpoint(self, checkpoint: TestCheckpoint):
        """Persist checkpoint to disk.

        Args:
            checkpoint: Checkpoint to save
        """
        checkpoint_path = self.get_checkpoint_path(checkpoint.test_id)

        try:
            with open(checkpoint_path, 'w') as f:
                json.dump(checkpoint.to_dict(), f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save checkpoint: {e}")

    def start_phase(self, checkpoint: TestCheckpoint, phase_name: str):
        """Mark phase as started.

        Args:
            checkpoint: Test checkpoint
            phase_name: Name of phase starting
        """
        if phase_name not in checkpoint.phases:
            raise ValueError(f"Unknown phase: {phase_name}")

        phase = checkpoint.phases[phase_name]
        phase.status = PhaseStatus.IN_PROGRESS
        phase.started_at = datetime.utcnow().isoformat()
        phase.retry_count += 1

        checkpoint.current_phase = phase_name
        checkpoint.last_updated_at = datetime.utcnow().isoformat()

        self.save_checkpoint(checkpoint)

    def complete_phase(
        self,
        checkpoint: TestCheckpoint,
        phase_name: str,
        **phase_data
    ):
        """Mark phase as completed with results.

        Args:
            checkpoint: Test checkpoint
            phase_name: Name of completed phase
            **phase_data: Phase-specific result data
        """
        if phase_name not in checkpoint.phases:
            raise ValueError(f"Unknown phase: {phase_name}")

        phase = checkpoint.phases[phase_name]
        phase.status = PhaseStatus.COMPLETED
        phase.completed_at = datetime.utcnow().isoformat()

        # Calculate duration
        if phase.started_at:
            started = datetime.fromisoformat(phase.started_at)
            completed = datetime.fromisoformat(phase.completed_at)
            phase.duration_seconds = (completed - started).total_seconds()

        # Update phase-specific data
        for key, value in phase_data.items():
            if hasattr(phase, key):
                setattr(phase, key, value)

        # Update checkpoint timing
        checkpoint.last_updated_at = datetime.utcnow().isoformat()
        started = datetime.fromisoformat(checkpoint.started_at)
        now = datetime.utcnow()
        checkpoint.total_duration_seconds = (now - started).total_seconds()

        self.save_checkpoint(checkpoint)

    def fail_phase(
        self,
        checkpoint: TestCheckpoint,
        phase_name: str,
        error: str
    ):
        """Mark phase as failed.

        Args:
            checkpoint: Test checkpoint
            phase_name: Name of failed phase
            error: Error message
        """
        if phase_name not in checkpoint.phases:
            raise ValueError(f"Unknown phase: {phase_name}")

        phase = checkpoint.phases[phase_name]
        phase.status = PhaseStatus.FAILED
        phase.completed_at = datetime.utcnow().isoformat()
        phase.error = error

        # Calculate duration
        if phase.started_at:
            started = datetime.fromisoformat(phase.started_at)
            completed = datetime.fromisoformat(phase.completed_at)
            phase.duration_seconds = (completed - started).total_seconds()

        checkpoint.last_updated_at = datetime.utcnow().isoformat()
        checkpoint.total_retries += 1

        self.save_checkpoint(checkpoint)

    def skip_phase(self, checkpoint: TestCheckpoint, phase_name: str):
        """Mark phase as skipped (already completed in previous run).

        Args:
            checkpoint: Test checkpoint
            phase_name: Name of phase to skip
        """
        if phase_name not in checkpoint.phases:
            raise ValueError(f"Unknown phase: {phase_name}")

        phase = checkpoint.phases[phase_name]

        # If already completed, mark as skipped for this run
        if phase.status == PhaseStatus.COMPLETED:
            phase.status = PhaseStatus.SKIPPED
            checkpoint.last_updated_at = datetime.utcnow().isoformat()
            self.save_checkpoint(checkpoint)

    def get_resume_phase(self, checkpoint: TestCheckpoint) -> Optional[str]:
        """Get next phase to execute for recovery.

        Args:
            checkpoint: Test checkpoint

        Returns:
            Phase name to resume from, or None if all complete
        """
        phase_order = list(checkpoint.phases.keys())

        for phase_name in phase_order:
            phase = checkpoint.phases[phase_name]

            # Resume from first non-completed phase
            if phase.status in [PhaseStatus.PENDING, PhaseStatus.FAILED]:
                return phase_name

        # All phases completed
        return None

    def cleanup_checkpoint(self, test_id: str):
        """Remove checkpoint file after successful completion.

        Args:
            test_id: Test identifier
        """
        checkpoint_path = self.get_checkpoint_path(test_id)

        if checkpoint_path.exists():
            try:
                checkpoint_path.unlink()
            except Exception as e:
                print(f"⚠️ Failed to cleanup checkpoint: {e}")

    def print_checkpoint_status(self, checkpoint: TestCheckpoint):
        """Print checkpoint status summary.

        Args:
            checkpoint: Test checkpoint
        """
        print(f"\n{'='*60}")
        print(f"📋 Checkpoint Status: {checkpoint.test_name}")
        print(f"🆔 Test ID: {checkpoint.test_id}")
        print(f"⏱️  Started: {checkpoint.started_at}")
        print(f"⏱️  Duration: {checkpoint.total_duration_seconds:.1f}s")
        print(f"🔄 Total Retries: {checkpoint.total_retries}")
        print(f"{'='*60}\n")

        for phase_name, phase in checkpoint.phases.items():
            status_icon = {
                PhaseStatus.PENDING: "⏳",
                PhaseStatus.IN_PROGRESS: "🔄",
                PhaseStatus.COMPLETED: "✅",
                PhaseStatus.FAILED: "❌",
                PhaseStatus.SKIPPED: "⏭️"
            }.get(phase.status, "❓")

            duration = f"{phase.duration_seconds:.1f}s" if phase.duration_seconds else "N/A"
            retry_info = f"(retry {phase.retry_count})" if phase.retry_count > 1 else ""

            print(f"{status_icon} {phase_name}: {phase.status.value} {retry_info} - {duration}")

            if phase.error:
                print(f"   ⚠️ Error: {phase.error[:100]}")

        print(f"\n{'='*60}\n")
