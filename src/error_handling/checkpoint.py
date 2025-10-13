"""
Checkpoint/Restore Mechanism

Provides workflow state checkpointing for recovery from failures.
Enables resuming workflows from last successful checkpoint.
"""

import json
import logging
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class WorkflowCheckpoint:
    """
    Workflow checkpoint data.

    Captures workflow state at a specific point for recovery.
    """

    checkpoint_id: str
    """Unique checkpoint identifier"""

    workflow_id: str
    """Workflow instance identifier"""

    timestamp: datetime
    """When checkpoint was created"""

    state: Dict[str, Any]
    """Workflow state data"""

    completed_tasks: List[str] = field(default_factory=list)
    """List of completed task IDs"""

    pending_tasks: List[str] = field(default_factory=list)
    """List of pending task IDs"""

    failed_tasks: List[str] = field(default_factory=list)
    """List of failed task IDs"""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata"""

    def to_dict(self) -> Dict[str, Any]:
        """Convert checkpoint to dictionary."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowCheckpoint":
        """Create checkpoint from dictionary."""
        data = data.copy()
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class CheckpointManager:
    """
    Manages workflow checkpoints for recovery.

    Provides checkpoint creation, storage, and restoration for
    resilient workflow execution.

    Example:
        >>> manager = CheckpointManager()
        >>> checkpoint = manager.create_checkpoint(
        ...     workflow_id="wf-123",
        ...     state={"current_step": 5},
        ...     completed_tasks=["task1", "task2"]
        ... )
        >>> manager.save_checkpoint(checkpoint)
        >>> restored = manager.load_checkpoint(checkpoint.checkpoint_id)
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        redis_client: Optional[Any] = None,
    ):
        """
        Initialize checkpoint manager.

        Args:
            storage_path: Directory for file-based checkpoints
            redis_client: Redis client for distributed checkpoints
        """
        self.storage_path = storage_path or Path("/tmp/devmatrix-checkpoints")
        self.redis_client = redis_client
        self._checkpoint_ttl = 3600  # 1 hour in Redis

        # Create storage directory
        if storage_path:
            self.storage_path.mkdir(parents=True, exist_ok=True)

    def create_checkpoint(
        self,
        workflow_id: str,
        state: Dict[str, Any],
        completed_tasks: Optional[List[str]] = None,
        pending_tasks: Optional[List[str]] = None,
        failed_tasks: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkflowCheckpoint:
        """
        Create a new checkpoint.

        Args:
            workflow_id: Workflow instance ID
            state: Current workflow state
            completed_tasks: List of completed task IDs
            pending_tasks: List of pending task IDs
            failed_tasks: List of failed task IDs
            metadata: Additional metadata

        Returns:
            Created checkpoint
        """
        checkpoint_id = self._generate_checkpoint_id(workflow_id)

        checkpoint = WorkflowCheckpoint(
            checkpoint_id=checkpoint_id,
            workflow_id=workflow_id,
            timestamp=datetime.now(),
            state=state,
            completed_tasks=completed_tasks or [],
            pending_tasks=pending_tasks or [],
            failed_tasks=failed_tasks or [],
            metadata=metadata or {},
        )

        logger.info(f"Created checkpoint: {checkpoint_id}")
        return checkpoint

    def save_checkpoint(
        self,
        checkpoint: WorkflowCheckpoint,
        use_redis: bool = True,
        use_file: bool = True,
    ) -> bool:
        """
        Save checkpoint to storage.

        Args:
            checkpoint: Checkpoint to save
            use_redis: Save to Redis if available
            use_file: Save to file system

        Returns:
            True if saved successfully
        """
        success = False

        # Save to Redis
        if use_redis and self.redis_client:
            try:
                key = f"checkpoint:{checkpoint.checkpoint_id}"
                data = json.dumps(checkpoint.to_dict())
                self.redis_client.setex(key, self._checkpoint_ttl, data)
                logger.debug(f"Saved checkpoint to Redis: {key}")
                success = True
            except Exception as e:
                logger.error(f"Failed to save checkpoint to Redis: {e}")

        # Save to file
        if use_file:
            try:
                file_path = self._get_checkpoint_path(checkpoint.checkpoint_id)
                with open(file_path, "w") as f:
                    json.dump(checkpoint.to_dict(), f, indent=2)
                logger.debug(f"Saved checkpoint to file: {file_path}")
                success = True
            except Exception as e:
                logger.error(f"Failed to save checkpoint to file: {e}")

        return success

    def load_checkpoint(
        self,
        checkpoint_id: str,
        prefer_redis: bool = True,
    ) -> Optional[WorkflowCheckpoint]:
        """
        Load checkpoint from storage.

        Args:
            checkpoint_id: Checkpoint identifier
            prefer_redis: Try Redis first if available

        Returns:
            Loaded checkpoint or None if not found
        """
        # Try Redis first
        if prefer_redis and self.redis_client:
            try:
                key = f"checkpoint:{checkpoint_id}"
                data = self.redis_client.get(key)
                if data:
                    checkpoint_data = json.loads(data)
                    logger.debug(f"Loaded checkpoint from Redis: {key}")
                    return WorkflowCheckpoint.from_dict(checkpoint_data)
            except Exception as e:
                logger.warning(f"Failed to load from Redis: {e}")

        # Try file system
        try:
            file_path = self._get_checkpoint_path(checkpoint_id)
            if file_path.exists():
                with open(file_path, "r") as f:
                    checkpoint_data = json.load(f)
                logger.debug(f"Loaded checkpoint from file: {file_path}")
                return WorkflowCheckpoint.from_dict(checkpoint_data)
        except Exception as e:
            logger.warning(f"Failed to load from file: {e}")

        logger.error(f"Checkpoint not found: {checkpoint_id}")
        return None

    def list_checkpoints(
        self,
        workflow_id: Optional[str] = None,
    ) -> List[WorkflowCheckpoint]:
        """
        List available checkpoints.

        Args:
            workflow_id: Filter by workflow ID (optional)

        Returns:
            List of checkpoints
        """
        checkpoints = []

        # List from file system
        if self.storage_path.exists():
            for file_path in self.storage_path.glob("checkpoint_*.json"):
                try:
                    with open(file_path, "r") as f:
                        checkpoint_data = json.load(f)
                    checkpoint = WorkflowCheckpoint.from_dict(checkpoint_data)

                    if workflow_id is None or checkpoint.workflow_id == workflow_id:
                        checkpoints.append(checkpoint)
                except Exception as e:
                    logger.warning(f"Failed to load checkpoint {file_path}: {e}")

        # Sort by timestamp (newest first)
        checkpoints.sort(key=lambda c: c.timestamp, reverse=True)
        return checkpoints

    def delete_checkpoint(
        self,
        checkpoint_id: str,
        delete_redis: bool = True,
        delete_file: bool = True,
    ) -> bool:
        """
        Delete checkpoint from storage.

        Args:
            checkpoint_id: Checkpoint identifier
            delete_redis: Delete from Redis
            delete_file: Delete from file system

        Returns:
            True if deleted successfully
        """
        success = False

        # Delete from Redis
        if delete_redis and self.redis_client:
            try:
                key = f"checkpoint:{checkpoint_id}"
                self.redis_client.delete(key)
                logger.debug(f"Deleted checkpoint from Redis: {key}")
                success = True
            except Exception as e:
                logger.error(f"Failed to delete from Redis: {e}")

        # Delete from file
        if delete_file:
            try:
                file_path = self._get_checkpoint_path(checkpoint_id)
                if file_path.exists():
                    file_path.unlink()
                    logger.debug(f"Deleted checkpoint file: {file_path}")
                    success = True
            except Exception as e:
                logger.error(f"Failed to delete file: {e}")

        return success

    def cleanup_old_checkpoints(
        self,
        workflow_id: Optional[str] = None,
        keep_latest: int = 5,
    ):
        """
        Clean up old checkpoints, keeping only the latest N.

        Args:
            workflow_id: Filter by workflow ID (optional)
            keep_latest: Number of latest checkpoints to keep
        """
        checkpoints = self.list_checkpoints(workflow_id)

        if len(checkpoints) <= keep_latest:
            return

        # Delete older checkpoints
        for checkpoint in checkpoints[keep_latest:]:
            self.delete_checkpoint(checkpoint.checkpoint_id)
            logger.info(f"Cleaned up old checkpoint: {checkpoint.checkpoint_id}")

    def restore_workflow_state(
        self,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Restore workflow state from checkpoint.

        Args:
            checkpoint_id: Checkpoint identifier

        Returns:
            Restored state dictionary or None
        """
        checkpoint = self.load_checkpoint(checkpoint_id)
        if checkpoint:
            logger.info(
                f"Restored workflow {checkpoint.workflow_id} state from "
                f"checkpoint {checkpoint_id}"
            )
            return {
                "state": checkpoint.state,
                "completed_tasks": checkpoint.completed_tasks,
                "pending_tasks": checkpoint.pending_tasks,
                "failed_tasks": checkpoint.failed_tasks,
                "metadata": checkpoint.metadata,
            }
        return None

    def _generate_checkpoint_id(self, workflow_id: str) -> str:
        """Generate unique checkpoint ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"checkpoint_{workflow_id}_{timestamp}"

    def _get_checkpoint_path(self, checkpoint_id: str) -> Path:
        """Get file path for checkpoint."""
        return self.storage_path / f"{checkpoint_id}.json"
