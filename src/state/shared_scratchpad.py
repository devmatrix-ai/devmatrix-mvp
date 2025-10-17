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
from src.observability import get_logger


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
        Initialize shared scratchpad with fallback support.

        Args:
            workspace_id: Unique workspace identifier
            redis_manager: Redis manager instance (creates new if not provided)
            ttl: Time-to-live for scratchpad data in seconds
        """
        self.workspace_id = workspace_id
        self.redis = redis_manager or RedisManager()
        self.ttl = ttl
        self.logger = get_logger("shared_scratchpad")

        # Key prefixes
        self.artifact_prefix = f"scratchpad:{workspace_id}:artifact"
        self.task_prefix = f"scratchpad:{workspace_id}:task"
        self.context_prefix = f"scratchpad:{workspace_id}:context"
        self.index_key = f"scratchpad:{workspace_id}:index"

        # Fallback in-memory storage (when Redis unavailable)
        self._fallback_artifacts = {}
        self._fallback_task_artifacts = {}  # task_id -> set of artifact_ids
        self._fallback_context = {}
        self._fallback_task_status = {}

    def _has_redis(self) -> bool:
        """Check if Redis is available."""
        return self.redis.connected and self.redis.client is not None

    def write_artifact(self, artifact: Artifact) -> bool:
        """
        Write artifact to scratchpad with fallback support.

        Args:
            artifact: Artifact to write

        Returns:
            True if successful, False otherwise
        """
        key = f"{self.artifact_prefix}:{artifact.id}"

        # Try Redis first
        if self._has_redis():
            try:
                artifact_json = json.dumps(artifact.to_dict())
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
                self.logger.error("Failed to write artifact to Redis",
                                artifact_id=artifact.id,
                                task_id=artifact.task_id,
                                error=str(e))
                # Fall through to fallback

        # Use fallback storage
        self._fallback_artifacts[artifact.id] = artifact

        # Update task index in fallback
        if artifact.task_id not in self._fallback_task_artifacts:
            self._fallback_task_artifacts[artifact.task_id] = set()
        self._fallback_task_artifacts[artifact.task_id].add(artifact.id)

        self.logger.debug("Wrote artifact to fallback storage",
                        artifact_id=artifact.id,
                        task_id=artifact.task_id)
        return True

    def read_artifact(self, artifact_id: str) -> Optional[Artifact]:
        """
        Read artifact by ID with fallback support.

        Args:
            artifact_id: Artifact identifier

        Returns:
            Artifact if found, None otherwise
        """
        key = f"{self.artifact_prefix}:{artifact_id}"

        # Try Redis first
        if self._has_redis():
            try:
                artifact_json = self.redis.client.get(key)
                if artifact_json is not None:
                    artifact_dict = json.loads(artifact_json)
                    return Artifact.from_dict(artifact_dict)
            except Exception as e:
                self.logger.error("Failed to read artifact from Redis",
                                artifact_id=artifact_id,
                                error=str(e))

        # Check fallback storage
        return self._fallback_artifacts.get(artifact_id)

    def read_artifacts(
        self,
        task_id: Optional[str] = None,
        artifact_type: Optional[ArtifactType] = None,
        created_by: Optional[str] = None
    ) -> List[Artifact]:
        """
        Read artifacts with optional filters and fallback support.

        Args:
            task_id: Filter by task ID
            artifact_type: Filter by artifact type
            created_by: Filter by creator agent

        Returns:
            List of matching artifacts
        """
        artifacts = []

        # Try Redis first
        if self._has_redis():
            try:
                # Get artifact IDs
                if task_id:
                    task_artifacts_key = f"{self.task_prefix}:{task_id}:artifacts"
                    artifact_ids = self.redis.client.smembers(task_artifacts_key)
                else:
                    artifact_ids = self.redis.client.smembers(self.index_key)

                # Read artifacts
                for artifact_id in artifact_ids:
                    artifact = self.read_artifact(artifact_id)
                    if artifact:
                        artifacts.append(artifact)

            except Exception as e:
                self.logger.error("Failed to read artifacts from Redis",
                                task_id=task_id,
                                error=str(e))
                # Fall through to fallback

        # If Redis failed or unavailable, use fallback
        if not artifacts:
            if task_id and task_id in self._fallback_task_artifacts:
                artifact_ids = self._fallback_task_artifacts[task_id]
                artifacts = [self._fallback_artifacts[aid] for aid in artifact_ids
                           if aid in self._fallback_artifacts]
            else:
                artifacts = list(self._fallback_artifacts.values())

        # Apply filters
        if artifact_type:
            artifacts = [a for a in artifacts if a.type == artifact_type.value]
        if created_by:
            artifacts = [a for a in artifacts if a.created_by == created_by]

        # Sort by creation time
        artifacts.sort(key=lambda a: a.created_at, reverse=True)
        return artifacts

    def delete_artifact(self, artifact_id: str) -> bool:
        """
        Delete artifact from scratchpad with fallback support.

        Args:
            artifact_id: Artifact identifier

        Returns:
            True if deleted, False otherwise
        """
        key = f"{self.artifact_prefix}:{artifact_id}"
        deleted = False

        # Get artifact to find task_id
        artifact = self.read_artifact(artifact_id)

        # Try Redis first
        if self._has_redis() and artifact:
            try:
                # Remove from task index
                task_artifacts_key = f"{self.task_prefix}:{artifact.task_id}:artifacts"
                self.redis.client.srem(task_artifacts_key, artifact_id)

                # Remove from global index
                self.redis.client.srem(self.index_key, artifact_id)

                # Delete artifact
                deleted = self.redis.client.delete(key) > 0
            except Exception as e:
                self.logger.error("Failed to delete artifact from Redis",
                                artifact_id=artifact_id,
                                error=str(e))

        # Delete from fallback storage
        if artifact_id in self._fallback_artifacts:
            artifact = self._fallback_artifacts[artifact_id]
            del self._fallback_artifacts[artifact_id]

            # Remove from task index
            if artifact.task_id in self._fallback_task_artifacts:
                self._fallback_task_artifacts[artifact.task_id].discard(artifact_id)

            deleted = True

        return deleted

    def set_context(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set context value for agent coordination with fallback support.

        Args:
            key: Context key
            value: Context value (will be JSON serialized)
            ttl: Optional TTL override

        Returns:
            True if successful, False otherwise
        """
        context_key = f"{self.context_prefix}:{key}"
        ttl = ttl or self.ttl

        # Try Redis first
        if self._has_redis():
            try:
                value_json = json.dumps(value)
                self.redis.client.setex(context_key, ttl, value_json)
                return True
            except Exception as e:
                self.logger.error("Failed to set context in Redis",
                                key=key,
                                error=str(e))
                # Fall through to fallback

        # Use fallback storage
        self._fallback_context[key] = value
        self.logger.debug("Set context in fallback storage", key=key)
        return True

    def get_context(self, key: str, default: Any = None) -> Any:
        """
        Get context value with fallback support.

        Args:
            key: Context key
            default: Default value if not found

        Returns:
            Context value or default
        """
        context_key = f"{self.context_prefix}:{key}"

        # Try Redis first
        if self._has_redis():
            try:
                value_json = self.redis.client.get(context_key)
                if value_json is not None:
                    return json.loads(value_json)
            except Exception as e:
                self.logger.warning("Failed to get context from Redis",
                                  key=key,
                                  error=str(e))

        # Check fallback storage
        return self._fallback_context.get(key, default)

    def delete_context(self, key: str) -> bool:
        """
        Delete context value with fallback support.

        Args:
            key: Context key

        Returns:
            True if deleted, False otherwise
        """
        context_key = f"{self.context_prefix}:{key}"
        deleted = False

        # Try Redis first
        if self._has_redis():
            try:
                deleted = self.redis.client.delete(context_key) > 0
            except Exception as e:
                self.logger.error("Failed to delete context from Redis",
                                key=key,
                                error=str(e))

        # Delete from fallback storage
        if key in self._fallback_context:
            del self._fallback_context[key]
            deleted = True

        return deleted

    def mark_task_started(self, task_id: str, agent_name: str) -> bool:
        """
        Mark task as started by an agent with fallback support.

        Args:
            task_id: Task identifier
            agent_name: Agent starting the task

        Returns:
            True if successful, False otherwise
        """
        key = f"{self.task_prefix}:{task_id}:status"
        status = {
            "status": "in_progress",
            "agent": agent_name,
            "started_at": datetime.utcnow().isoformat()
        }

        # Try Redis first
        if self._has_redis():
            try:
                status_json = json.dumps(status)
                self.redis.client.setex(key, self.ttl, status_json)
                return True
            except Exception as e:
                self.logger.error("Failed to mark task started in Redis",
                                task_id=task_id,
                                agent=agent_name,
                                error=str(e))

        # Use fallback storage
        self._fallback_task_status[task_id] = status
        return True

    def mark_task_completed(self, task_id: str, agent_name: str) -> bool:
        """
        Mark task as completed with fallback support.

        Args:
            task_id: Task identifier
            agent_name: Agent completing the task

        Returns:
            True if successful, False otherwise
        """
        key = f"{self.task_prefix}:{task_id}:status"
        status = {
            "status": "completed",
            "agent": agent_name,
            "completed_at": datetime.utcnow().isoformat()
        }

        # Try Redis first
        if self._has_redis():
            try:
                status_json = json.dumps(status)
                self.redis.client.setex(key, self.ttl, status_json)
                return True
            except Exception as e:
                self.logger.error("Failed to mark task completed in Redis",
                                task_id=task_id,
                                agent=agent_name,
                                error=str(e))

        # Use fallback storage
        self._fallback_task_status[task_id] = status
        return True

    def mark_task_failed(self, task_id: str, agent_name: str, error: str) -> bool:
        """
        Mark task as failed with fallback support.

        Args:
            task_id: Task identifier
            agent_name: Agent that failed
            error: Error message

        Returns:
            True if successful, False otherwise
        """
        key = f"{self.task_prefix}:{task_id}:status"
        status = {
            "status": "failed",
            "agent": agent_name,
            "error": error,
            "failed_at": datetime.utcnow().isoformat()
        }

        # Try Redis first
        if self._has_redis():
            try:
                status_json = json.dumps(status)
                self.redis.client.setex(key, self.ttl, status_json)
                return True
            except Exception as e:
                self.logger.error("Failed to mark task failed in Redis",
                                task_id=task_id,
                                agent=agent_name,
                                error=str(e))

        # Use fallback storage
        self._fallback_task_status[task_id] = status
        return True

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task status with fallback support.

        Args:
            task_id: Task identifier

        Returns:
            Status dictionary if found, None otherwise
        """
        key = f"{self.task_prefix}:{task_id}:status"

        # Try Redis first
        if self._has_redis():
            try:
                status_json = self.redis.client.get(key)
                if status_json is not None:
                    return json.loads(status_json)
            except Exception as e:
                self.logger.warning("Failed to get task status from Redis",
                                  task_id=task_id,
                                  error=str(e))

        # Check fallback storage
        return self._fallback_task_status.get(task_id)

    def clear(self) -> bool:
        """
        Clear all scratchpad data for this workspace with fallback support.

        Returns:
            True if successful, False otherwise
        """
        # Try Redis first
        if self._has_redis():
            try:
                # Get all keys for this workspace
                pattern = f"scratchpad:{self.workspace_id}:*"
                keys = list(self.redis.client.scan_iter(match=pattern))

                if keys:
                    self.redis.client.delete(*keys)
            except Exception as e:
                self.logger.error("Failed to clear scratchpad from Redis",
                                workspace_id=self.workspace_id,
                                error=str(e))

        # Clear fallback storage
        self._fallback_artifacts.clear()
        self._fallback_task_artifacts.clear()
        self._fallback_context.clear()
        self._fallback_task_status.clear()

        return True

    def get_stats(self) -> Dict[str, Any]:
        """
        Get scratchpad statistics with fallback support.

        Returns:
            Dictionary with stats
        """
        total_artifacts = 0
        type_counts = {}

        # Try Redis first
        if self._has_redis():
            try:
                total_artifacts = len(self.redis.client.smembers(self.index_key))
            except Exception as e:
                self.logger.warning("Failed to get stats from Redis",
                                  workspace_id=self.workspace_id,
                                  error=str(e))

        # If Redis failed or no artifacts, check fallback
        if total_artifacts == 0:
            total_artifacts = len(self._fallback_artifacts)

        # Count by type from all artifacts
        artifacts = self.read_artifacts()
        for artifact in artifacts:
            type_counts[artifact.type] = type_counts.get(artifact.type, 0) + 1

        return {
            "workspace_id": self.workspace_id,
            "total_artifacts": total_artifacts,
            "artifacts_by_type": type_counts,
            "ttl": self.ttl,
            "mode": "redis" if self._has_redis() else "fallback"
        }
