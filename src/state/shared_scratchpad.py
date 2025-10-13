"""
Shared Scratchpad

Inter-agent communication system using Redis as shared memory.
Allows agents to read/write artifacts, share context, and coordinate execution.
"""

import json
import hashlib
from typing import Any, Optional, List, Dict
from datetime import datetime
from enum import Enum

from src.state.redis_manager import RedisManager


class ArtifactType(Enum):
    """Types of artifacts that can be shared."""
    CODE = "code"
    TEST = "test"
    DOCUMENTATION = "documentation"
    ANALYSIS = "analysis"
    PLAN = "plan"
    RESULT = "result"
    ERROR = "error"
    CONTEXT = "context"


class Artifact:
    """
    Represents a shared artifact between agents.

    Attributes:
        id: Unique artifact identifier
        type: Type of artifact
        content: Artifact content
        metadata: Additional metadata
        created_by: Agent that created this artifact
        created_at: Creation timestamp
        task_id: Associated task ID
    """

    def __init__(
        self,
        artifact_type: ArtifactType,
        content: Any,
        created_by: str,
        task_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize artifact."""
        self.id = self._generate_id(artifact_type, task_id, created_by)
        self.type = artifact_type.value
        self.content = content
        self.metadata = metadata or {}
        self.created_by = created_by
        self.created_at = datetime.utcnow().isoformat()
        self.task_id = task_id

    def _generate_id(self, artifact_type: ArtifactType, task_id: str, created_by: str) -> str:
        """Generate unique artifact ID."""
        timestamp = datetime.utcnow().isoformat()
        hash_input = f"{artifact_type.value}:{task_id}:{created_by}:{timestamp}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Convert artifact to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "metadata": self.metadata,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "task_id": self.task_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Artifact':
        """Create artifact from dictionary."""
        artifact = cls.__new__(cls)
        artifact.id = data["id"]
        artifact.type = data["type"]
        artifact.content = data["content"]
        artifact.metadata = data.get("metadata", {})
        artifact.created_by = data["created_by"]
        artifact.created_at = data["created_at"]
        artifact.task_id = data["task_id"]
        return artifact


class SharedScratchpad:
    """
    Shared memory system for inter-agent communication.

    Provides:
    - Artifact storage and retrieval
    - Task context management
    - Agent coordination primitives
    - Dependency tracking

    Usage:
        scratchpad = SharedScratchpad(workspace_id="my-project")

        # Write artifact
        artifact = Artifact(
            artifact_type=ArtifactType.CODE,
            content="def hello(): ...",
            created_by="code_agent",
            task_id="task_1"
        )
        scratchpad.write_artifact(artifact)

        # Read artifacts
        artifacts = scratchpad.read_artifacts(task_id="task_1")

        # Share context
        scratchpad.set_context("user_preferences", {"theme": "dark"})
        context = scratchpad.get_context("user_preferences")
    """

    def __init__(
        self,
        workspace_id: str,
        redis_manager: Optional[RedisManager] = None,
        ttl: int = 7200  # 2 hours default
    ):
        """
        Initialize shared scratchpad.

        Args:
            workspace_id: Unique workspace identifier
            redis_manager: Redis manager instance (creates new if not provided)
            ttl: Time-to-live for scratchpad data in seconds
        """
        self.workspace_id = workspace_id
        self.redis = redis_manager or RedisManager()
        self.ttl = ttl

        # Key prefixes
        self.artifact_prefix = f"scratchpad:{workspace_id}:artifact"
        self.task_prefix = f"scratchpad:{workspace_id}:task"
        self.context_prefix = f"scratchpad:{workspace_id}:context"
        self.index_key = f"scratchpad:{workspace_id}:index"

    def write_artifact(self, artifact: Artifact) -> bool:
        """
        Write artifact to scratchpad.

        Args:
            artifact: Artifact to write

        Returns:
            True if successful, False otherwise
        """
        key = f"{self.artifact_prefix}:{artifact.id}"

        try:
            # Serialize artifact
            artifact_json = json.dumps(artifact.to_dict())

            # Store artifact
            self.redis.client.setex(key, self.ttl, artifact_json)

            # Update task index
            task_artifacts_key = f"{self.task_prefix}:{artifact.task_id}:artifacts"
            self.redis.client.sadd(task_artifacts_key, artifact.id)
            self.redis.client.expire(task_artifacts_key, self.ttl)

            # Update global index
            self.redis.client.sadd(self.index_key, artifact.id)
            self.redis.client.expire(self.index_key, self.ttl)

            return True

        except Exception as e:
            print(f"Error writing artifact: {e}")
            return False

    def read_artifact(self, artifact_id: str) -> Optional[Artifact]:
        """
        Read artifact by ID.

        Args:
            artifact_id: Artifact identifier

        Returns:
            Artifact if found, None otherwise
        """
        key = f"{self.artifact_prefix}:{artifact_id}"

        try:
            artifact_json = self.redis.client.get(key)

            if artifact_json is None:
                return None

            artifact_dict = json.loads(artifact_json)
            return Artifact.from_dict(artifact_dict)

        except Exception as e:
            print(f"Error reading artifact: {e}")
            return None

    def read_artifacts(
        self,
        task_id: Optional[str] = None,
        artifact_type: Optional[ArtifactType] = None,
        created_by: Optional[str] = None
    ) -> List[Artifact]:
        """
        Read artifacts with optional filters.

        Args:
            task_id: Filter by task ID
            artifact_type: Filter by artifact type
            created_by: Filter by creator agent

        Returns:
            List of matching artifacts
        """
        try:
            # Get artifact IDs
            if task_id:
                task_artifacts_key = f"{self.task_prefix}:{task_id}:artifacts"
                artifact_ids = self.redis.client.smembers(task_artifacts_key)
            else:
                artifact_ids = self.redis.client.smembers(self.index_key)

            # Read and filter artifacts
            artifacts = []
            for artifact_id in artifact_ids:
                artifact = self.read_artifact(artifact_id)

                if artifact is None:
                    continue

                # Apply filters
                if artifact_type and artifact.type != artifact_type.value:
                    continue

                if created_by and artifact.created_by != created_by:
                    continue

                artifacts.append(artifact)

            # Sort by creation time (newest first)
            artifacts.sort(key=lambda a: a.created_at, reverse=True)

            return artifacts

        except Exception as e:
            print(f"Error reading artifacts: {e}")
            return []

    def delete_artifact(self, artifact_id: str) -> bool:
        """
        Delete artifact from scratchpad.

        Args:
            artifact_id: Artifact identifier

        Returns:
            True if deleted, False otherwise
        """
        key = f"{self.artifact_prefix}:{artifact_id}"

        try:
            # Get artifact to find task_id
            artifact = self.read_artifact(artifact_id)

            if artifact:
                # Remove from task index
                task_artifacts_key = f"{self.task_prefix}:{artifact.task_id}:artifacts"
                self.redis.client.srem(task_artifacts_key, artifact_id)

            # Remove from global index
            self.redis.client.srem(self.index_key, artifact_id)

            # Delete artifact
            deleted = self.redis.client.delete(key)
            return deleted > 0

        except Exception as e:
            print(f"Error deleting artifact: {e}")
            return False

    def set_context(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set context value for agent coordination.

        Args:
            key: Context key
            value: Context value (will be JSON serialized)
            ttl: Optional TTL override

        Returns:
            True if successful, False otherwise
        """
        context_key = f"{self.context_prefix}:{key}"
        ttl = ttl or self.ttl

        try:
            value_json = json.dumps(value)
            self.redis.client.setex(context_key, ttl, value_json)
            return True

        except Exception as e:
            print(f"Error setting context: {e}")
            return False

    def get_context(self, key: str, default: Any = None) -> Any:
        """
        Get context value.

        Args:
            key: Context key
            default: Default value if not found

        Returns:
            Context value or default
        """
        context_key = f"{self.context_prefix}:{key}"

        try:
            value_json = self.redis.client.get(context_key)

            if value_json is None:
                return default

            return json.loads(value_json)

        except Exception as e:
            print(f"Error getting context: {e}")
            return default

    def delete_context(self, key: str) -> bool:
        """
        Delete context value.

        Args:
            key: Context key

        Returns:
            True if deleted, False otherwise
        """
        context_key = f"{self.context_prefix}:{key}"

        try:
            deleted = self.redis.client.delete(context_key)
            return deleted > 0

        except Exception as e:
            print(f"Error deleting context: {e}")
            return False

    def mark_task_started(self, task_id: str, agent_name: str) -> bool:
        """
        Mark task as started by an agent.

        Args:
            task_id: Task identifier
            agent_name: Agent starting the task

        Returns:
            True if successful, False otherwise
        """
        key = f"{self.task_prefix}:{task_id}:status"

        try:
            status = {
                "status": "in_progress",
                "agent": agent_name,
                "started_at": datetime.utcnow().isoformat()
            }

            status_json = json.dumps(status)
            self.redis.client.setex(key, self.ttl, status_json)
            return True

        except Exception as e:
            print(f"Error marking task started: {e}")
            return False

    def mark_task_completed(self, task_id: str, agent_name: str) -> bool:
        """
        Mark task as completed.

        Args:
            task_id: Task identifier
            agent_name: Agent completing the task

        Returns:
            True if successful, False otherwise
        """
        key = f"{self.task_prefix}:{task_id}:status"

        try:
            status = {
                "status": "completed",
                "agent": agent_name,
                "completed_at": datetime.utcnow().isoformat()
            }

            status_json = json.dumps(status)
            self.redis.client.setex(key, self.ttl, status_json)
            return True

        except Exception as e:
            print(f"Error marking task completed: {e}")
            return False

    def mark_task_failed(self, task_id: str, agent_name: str, error: str) -> bool:
        """
        Mark task as failed.

        Args:
            task_id: Task identifier
            agent_name: Agent that failed
            error: Error message

        Returns:
            True if successful, False otherwise
        """
        key = f"{self.task_prefix}:{task_id}:status"

        try:
            status = {
                "status": "failed",
                "agent": agent_name,
                "error": error,
                "failed_at": datetime.utcnow().isoformat()
            }

            status_json = json.dumps(status)
            self.redis.client.setex(key, self.ttl, status_json)
            return True

        except Exception as e:
            print(f"Error marking task failed: {e}")
            return False

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task status.

        Args:
            task_id: Task identifier

        Returns:
            Status dictionary if found, None otherwise
        """
        key = f"{self.task_prefix}:{task_id}:status"

        try:
            status_json = self.redis.client.get(key)

            if status_json is None:
                return None

            return json.loads(status_json)

        except Exception as e:
            print(f"Error getting task status: {e}")
            return None

    def clear(self) -> bool:
        """
        Clear all scratchpad data for this workspace.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get all keys for this workspace
            pattern = f"scratchpad:{self.workspace_id}:*"
            keys = list(self.redis.client.scan_iter(match=pattern))

            if keys:
                self.redis.client.delete(*keys)

            return True

        except Exception as e:
            print(f"Error clearing scratchpad: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get scratchpad statistics.

        Returns:
            Dictionary with stats
        """
        try:
            total_artifacts = len(self.redis.client.smembers(self.index_key))

            # Count by type
            artifacts = self.read_artifacts()
            type_counts = {}
            for artifact in artifacts:
                type_counts[artifact.type] = type_counts.get(artifact.type, 0) + 1

            return {
                "workspace_id": self.workspace_id,
                "total_artifacts": total_artifacts,
                "artifacts_by_type": type_counts,
                "ttl": self.ttl
            }

        except Exception as e:
            return {"error": str(e)}
