"""
Unit tests for SharedScratchpad
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from src.state.shared_scratchpad import (
    SharedScratchpad,
    Artifact,
    ArtifactType
)


class TestArtifact:
    """Test suite for Artifact class."""

    def test_artifact_creation(self):
        """Test creating an artifact."""
        artifact = Artifact(
            artifact_type=ArtifactType.CODE,
            content="def hello(): pass",
            created_by="test_agent",
            task_id="task_1",
            metadata={"language": "python"}
        )

        assert artifact.type == "code"
        assert artifact.content == "def hello(): pass"
        assert artifact.created_by == "test_agent"
        assert artifact.task_id == "task_1"
        assert artifact.metadata["language"] == "python"
        assert artifact.id is not None
        assert artifact.created_at is not None

    def test_artifact_to_dict(self):
        """Test converting artifact to dictionary."""
        artifact = Artifact(
            artifact_type=ArtifactType.TEST,
            content="test content",
            created_by="agent",
            task_id="task_1"
        )

        artifact_dict = artifact.to_dict()

        assert artifact_dict["type"] == "test"
        assert artifact_dict["content"] == "test content"
        assert artifact_dict["created_by"] == "agent"
        assert artifact_dict["task_id"] == "task_1"
        assert "id" in artifact_dict
        assert "created_at" in artifact_dict

    def test_artifact_from_dict(self):
        """Test creating artifact from dictionary."""
        data = {
            "id": "test123",
            "type": "code",
            "content": "content",
            "metadata": {"key": "value"},
            "created_by": "agent",
            "created_at": "2024-01-01T00:00:00",
            "task_id": "task_1"
        }

        artifact = Artifact.from_dict(data)

        assert artifact.id == "test123"
        assert artifact.type == "code"
        assert artifact.content == "content"
        assert artifact.metadata["key"] == "value"
        assert artifact.created_by == "agent"
        assert artifact.task_id == "task_1"

    def test_artifact_unique_ids(self):
        """Test that artifacts get unique IDs."""
        artifact1 = Artifact(
            artifact_type=ArtifactType.CODE,
            content="content1",
            created_by="agent1",
            task_id="task_1"
        )

        artifact2 = Artifact(
            artifact_type=ArtifactType.CODE,
            content="content2",
            created_by="agent2",
            task_id="task_1"
        )

        assert artifact1.id != artifact2.id


class TestSharedScratchpad:
    """Test suite for SharedScratchpad."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis manager."""
        with patch('src.state.shared_scratchpad.RedisManager') as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def scratchpad(self, mock_redis):
        """Create scratchpad with mocked Redis."""
        return SharedScratchpad(workspace_id="test-workspace", redis_manager=mock_redis)

    def test_init(self, scratchpad):
        """Test scratchpad initialization."""
        assert scratchpad.workspace_id == "test-workspace"
        assert scratchpad.ttl == 7200
        assert scratchpad.artifact_prefix == "scratchpad:test-workspace:artifact"
        assert scratchpad.task_prefix == "scratchpad:test-workspace:task"
        assert scratchpad.context_prefix == "scratchpad:test-workspace:context"

    def test_write_artifact(self, scratchpad, mock_redis):
        """Test writing artifact."""
        artifact = Artifact(
            artifact_type=ArtifactType.CODE,
            content="def test(): pass",
            created_by="agent1",
            task_id="task_1"
        )

        mock_redis.client.setex.return_value = True
        mock_redis.client.sadd.return_value = 1
        mock_redis.client.expire.return_value = True

        result = scratchpad.write_artifact(artifact)

        assert result is True
        assert mock_redis.client.setex.called
        assert mock_redis.client.sadd.called

    def test_read_artifact(self, scratchpad, mock_redis):
        """Test reading artifact by ID."""
        artifact_data = {
            "id": "test123",
            "type": "code",
            "content": "content",
            "metadata": {},
            "created_by": "agent",
            "created_at": "2024-01-01T00:00:00",
            "task_id": "task_1"
        }

        import json
        mock_redis.client.get.return_value = json.dumps(artifact_data)

        artifact = scratchpad.read_artifact("test123")

        assert artifact is not None
        assert artifact.id == "test123"
        assert artifact.type == "code"
        assert artifact.content == "content"

    def test_read_artifact_not_found(self, scratchpad, mock_redis):
        """Test reading nonexistent artifact."""
        mock_redis.client.get.return_value = None

        artifact = scratchpad.read_artifact("nonexistent")

        assert artifact is None

    def test_read_artifacts_by_task(self, scratchpad, mock_redis):
        """Test reading artifacts filtered by task ID."""
        artifact_ids = {"art1", "art2"}
        mock_redis.client.smembers.return_value = artifact_ids

        artifact1_data = {
            "id": "art1",
            "type": "code",
            "content": "content1",
            "metadata": {},
            "created_by": "agent1",
            "created_at": "2024-01-01T00:00:00",
            "task_id": "task_1"
        }

        artifact2_data = {
            "id": "art2",
            "type": "test",
            "content": "content2",
            "metadata": {},
            "created_by": "agent2",
            "created_at": "2024-01-01T00:01:00",
            "task_id": "task_1"
        }

        import json

        def mock_get(key):
            if "art1" in key:
                return json.dumps(artifact1_data)
            elif "art2" in key:
                return json.dumps(artifact2_data)
            return None

        mock_redis.client.get.side_effect = mock_get

        artifacts = scratchpad.read_artifacts(task_id="task_1")

        assert len(artifacts) == 2
        # Should be sorted by created_at (newest first)
        assert artifacts[0].id == "art2"
        assert artifacts[1].id == "art1"

    def test_read_artifacts_with_type_filter(self, scratchpad, mock_redis):
        """Test reading artifacts filtered by type."""
        artifact_ids = {"art1", "art2"}
        mock_redis.client.smembers.return_value = artifact_ids

        artifact1_data = {
            "id": "art1",
            "type": "code",
            "content": "content1",
            "metadata": {},
            "created_by": "agent1",
            "created_at": "2024-01-01T00:00:00",
            "task_id": "task_1"
        }

        artifact2_data = {
            "id": "art2",
            "type": "test",
            "content": "content2",
            "metadata": {},
            "created_by": "agent2",
            "created_at": "2024-01-01T00:01:00",
            "task_id": "task_1"
        }

        import json

        def mock_get(key):
            if "art1" in key:
                return json.dumps(artifact1_data)
            elif "art2" in key:
                return json.dumps(artifact2_data)
            return None

        mock_redis.client.get.side_effect = mock_get

        artifacts = scratchpad.read_artifacts(artifact_type=ArtifactType.CODE)

        assert len(artifacts) == 1
        assert artifacts[0].type == "code"

    def test_delete_artifact(self, scratchpad, mock_redis):
        """Test deleting artifact."""
        artifact_data = {
            "id": "test123",
            "type": "code",
            "content": "content",
            "metadata": {},
            "created_by": "agent",
            "created_at": "2024-01-01T00:00:00",
            "task_id": "task_1"
        }

        import json
        mock_redis.client.get.return_value = json.dumps(artifact_data)
        mock_redis.client.delete.return_value = 1

        result = scratchpad.delete_artifact("test123")

        assert result is True
        assert mock_redis.client.delete.called
        assert mock_redis.client.srem.called

    def test_set_and_get_context(self, scratchpad, mock_redis):
        """Test setting and getting context."""
        mock_redis.client.setex.return_value = True

        context_value = {"theme": "dark", "language": "en"}
        result = scratchpad.set_context("user_prefs", context_value)

        assert result is True

        import json
        mock_redis.client.get.return_value = json.dumps(context_value)

        retrieved = scratchpad.get_context("user_prefs")

        assert retrieved == context_value

    def test_get_context_with_default(self, scratchpad, mock_redis):
        """Test getting context with default value."""
        mock_redis.client.get.return_value = None

        default = {"default": "value"}
        retrieved = scratchpad.get_context("nonexistent", default=default)

        assert retrieved == default

    def test_delete_context(self, scratchpad, mock_redis):
        """Test deleting context."""
        mock_redis.client.delete.return_value = 1

        result = scratchpad.delete_context("test_key")

        assert result is True
        assert mock_redis.client.delete.called

    def test_mark_task_started(self, scratchpad, mock_redis):
        """Test marking task as started."""
        mock_redis.client.setex.return_value = True

        result = scratchpad.mark_task_started("task_1", "agent1")

        assert result is True
        assert mock_redis.client.setex.called

    def test_mark_task_completed(self, scratchpad, mock_redis):
        """Test marking task as completed."""
        mock_redis.client.setex.return_value = True

        result = scratchpad.mark_task_completed("task_1", "agent1")

        assert result is True
        assert mock_redis.client.setex.called

    def test_mark_task_failed(self, scratchpad, mock_redis):
        """Test marking task as failed."""
        mock_redis.client.setex.return_value = True

        result = scratchpad.mark_task_failed("task_1", "agent1", "Error message")

        assert result is True
        assert mock_redis.client.setex.called

    def test_get_task_status(self, scratchpad, mock_redis):
        """Test getting task status."""
        status_data = {
            "status": "in_progress",
            "agent": "agent1",
            "started_at": "2024-01-01T00:00:00"
        }

        import json
        mock_redis.client.get.return_value = json.dumps(status_data)

        status = scratchpad.get_task_status("task_1")

        assert status is not None
        assert status["status"] == "in_progress"
        assert status["agent"] == "agent1"

    def test_get_task_status_not_found(self, scratchpad, mock_redis):
        """Test getting status for nonexistent task."""
        mock_redis.client.get.return_value = None

        status = scratchpad.get_task_status("nonexistent")

        assert status is None

    def test_clear(self, scratchpad, mock_redis):
        """Test clearing all scratchpad data."""
        mock_redis.client.scan_iter.return_value = iter(["key1", "key2", "key3"])
        mock_redis.client.delete.return_value = 3

        result = scratchpad.clear()

        assert result is True
        assert mock_redis.client.delete.called

    def test_get_stats(self, scratchpad, mock_redis):
        """Test getting scratchpad statistics."""
        mock_redis.client.smembers.return_value = {"art1", "art2", "art3"}

        artifact_data_1 = {
            "id": "art1",
            "type": "code",
            "content": "content1",
            "metadata": {},
            "created_by": "agent1",
            "created_at": "2024-01-01T00:00:00",
            "task_id": "task_1"
        }

        artifact_data_2 = {
            "id": "art2",
            "type": "code",
            "content": "content2",
            "metadata": {},
            "created_by": "agent2",
            "created_at": "2024-01-01T00:01:00",
            "task_id": "task_2"
        }

        artifact_data_3 = {
            "id": "art3",
            "type": "test",
            "content": "content3",
            "metadata": {},
            "created_by": "agent3",
            "created_at": "2024-01-01T00:02:00",
            "task_id": "task_3"
        }

        import json

        def mock_get(key):
            if "art1" in key:
                return json.dumps(artifact_data_1)
            elif "art2" in key:
                return json.dumps(artifact_data_2)
            elif "art3" in key:
                return json.dumps(artifact_data_3)
            return None

        mock_redis.client.get.side_effect = mock_get

        stats = scratchpad.get_stats()

        assert stats["workspace_id"] == "test-workspace"
        assert stats["total_artifacts"] == 3
        assert stats["artifacts_by_type"]["code"] == 2
        assert stats["artifacts_by_type"]["test"] == 1
        assert stats["ttl"] == 7200

    def test_custom_ttl(self):
        """Test creating scratchpad with custom TTL."""
        with patch('src.state.shared_scratchpad.RedisManager') as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance

            scratchpad = SharedScratchpad(
                workspace_id="test",
                redis_manager=mock_instance,
                ttl=3600
            )

            assert scratchpad.ttl == 3600

    def test_artifact_type_enum(self):
        """Test ArtifactType enum values."""
        assert ArtifactType.CODE.value == "code"
        assert ArtifactType.TEST.value == "test"
        assert ArtifactType.DOCUMENTATION.value == "documentation"
        assert ArtifactType.ANALYSIS.value == "analysis"
        assert ArtifactType.PLAN.value == "plan"
        assert ArtifactType.RESULT.value == "result"
        assert ArtifactType.ERROR.value == "error"
        assert ArtifactType.CONTEXT.value == "context"
