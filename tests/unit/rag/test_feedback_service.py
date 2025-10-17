"""
Unit tests for FeedbackService (continuous learning).

Tests cover:
- Initialization and configuration
- Recording feedback (approved, rejected, modified, used)
- Auto-indexing approved examples
- Metrics tracking
- Feedback history management
- Enable/disable functionality
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from src.rag.feedback_service import (
    FeedbackService,
    FeedbackType,
    FeedbackEntry,
    FeedbackMetrics,
    create_feedback_service,
)
from src.rag.vector_store import VectorStore


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store."""
    store = Mock(spec=VectorStore)
    store.add_example.return_value = "example_id_123"
    store.get_stats.return_value = {
        "total_examples": 10,
        "collection_name": "test_collection"
    }
    return store


@pytest.fixture
def feedback_service(mock_vector_store):
    """Create feedback service with mock vector store."""
    return FeedbackService(vector_store=mock_vector_store, enabled=True)


class TestFeedbackServiceInitialization:
    """Test FeedbackService initialization."""

    def test_init_enabled(self, mock_vector_store):
        """Test initialization with feedback enabled."""
        service = FeedbackService(
            vector_store=mock_vector_store,
            enabled=True
        )

        assert service.enabled is True
        assert service.vector_store == mock_vector_store
        assert isinstance(service.metrics, FeedbackMetrics)
        assert service.feedback_history == []

    def test_init_disabled(self, mock_vector_store):
        """Test initialization with feedback disabled."""
        service = FeedbackService(
            vector_store=mock_vector_store,
            enabled=False
        )

        assert service.enabled is False


class TestRecordFeedback:
    """Test recording feedback."""

    def test_record_feedback_basic(self, feedback_service, mock_vector_store):
        """Test basic feedback recording."""
        feedback_id = feedback_service.record_feedback(
            code="def test(): pass",
            feedback_type=FeedbackType.APPROVED,
            metadata={"language": "python"}
        )

        assert feedback_id is not None
        assert len(feedback_service.feedback_history) == 1
        assert feedback_service.metrics.total_feedback == 1
        assert feedback_service.metrics.approved_count == 1

    def test_record_feedback_with_context(self, feedback_service):
        """Test feedback recording with full context."""
        feedback_id = feedback_service.record_feedback(
            code="def hello(): return 'world'",
            feedback_type=FeedbackType.APPROVED,
            metadata={"language": "python"},
            user_id="user123",
            task_description="Create greeting function",
            original_query="greeting function",
            retrieval_id="ret123"
        )

        entry = feedback_service.feedback_history[0]
        assert entry.id == feedback_id
        assert entry.user_id == "user123"
        assert entry.task_description == "Create greeting function"
        assert entry.original_query == "greeting function"
        assert entry.retrieval_id == "ret123"

    def test_record_feedback_empty_code(self, feedback_service):
        """Test recording feedback with empty code raises error."""
        with pytest.raises(ValueError) as exc_info:
            feedback_service.record_feedback(
                code="",
                feedback_type=FeedbackType.APPROVED
            )

        assert "empty" in str(exc_info.value).lower()

    def test_record_feedback_updates_timestamp(self, feedback_service):
        """Test that feedback includes timestamp."""
        feedback_service.record_feedback(
            code="test code",
            feedback_type=FeedbackType.APPROVED
        )

        entry = feedback_service.feedback_history[0]
        assert entry.timestamp is not None
        # Should be valid ISO format
        datetime.fromisoformat(entry.timestamp)


class TestRecordApproval:
    """Test convenience method for recording approvals."""

    def test_record_approval_basic(self, feedback_service, mock_vector_store):
        """Test recording code approval."""
        feedback_id = feedback_service.record_approval(
            code="def approved(): pass",
            metadata={"language": "python"}
        )

        assert feedback_id is not None
        assert feedback_service.metrics.approved_count == 1

        entry = feedback_service.feedback_history[0]
        assert entry.feedback_type == FeedbackType.APPROVED
        assert entry.metadata["approved"] is True
        assert entry.metadata["feedback_source"] == "manual_approval"

    def test_record_approval_indexes_to_vector_store(
        self, feedback_service, mock_vector_store
    ):
        """Test that approved code is auto-indexed."""
        feedback_service.record_approval(
            code="def approved(): pass",
            metadata={"language": "python"}
        )

        # Should have called add_example on vector store
        mock_vector_store.add_example.assert_called_once()

        # Check indexed count
        assert feedback_service.metrics.indexed_count == 1


class TestRecordRejection:
    """Test convenience method for recording rejections."""

    def test_record_rejection_basic(self, feedback_service, mock_vector_store):
        """Test recording code rejection."""
        feedback_id = feedback_service.record_rejection(
            code="def rejected(): pass",
            reason="Incorrect implementation",
            metadata={"language": "python"}
        )

        assert feedback_id is not None
        assert feedback_service.metrics.rejected_count == 1

        entry = feedback_service.feedback_history[0]
        assert entry.feedback_type == FeedbackType.REJECTED
        assert entry.metadata["approved"] is False
        assert entry.metadata["feedback_source"] == "manual_rejection"
        assert entry.metadata["rejection_reason"] == "Incorrect implementation"

    def test_record_rejection_not_indexed(
        self, feedback_service, mock_vector_store
    ):
        """Test that rejected code is not indexed."""
        feedback_service.record_rejection(
            code="def rejected(): pass"
        )

        # Should NOT have called add_example
        mock_vector_store.add_example.assert_not_called()
        assert feedback_service.metrics.indexed_count == 0


class TestRecordUsage:
    """Test recording usage of retrieved examples."""

    def test_record_usage_helpful(self, feedback_service):
        """Test recording helpful usage."""
        result_id = feedback_service.record_usage(
            retrieval_id="ret123",
            was_helpful=True,
            metadata={"context": "authentication"}
        )

        assert result_id == "ret123"
        assert feedback_service.metrics.used_count == 1

    def test_record_usage_not_helpful(self, feedback_service):
        """Test recording not helpful usage."""
        result_id = feedback_service.record_usage(
            retrieval_id="ret123",
            was_helpful=False
        )

        assert result_id == "ret123"
        assert feedback_service.metrics.used_count == 1


class TestAutoIndexing:
    """Test auto-indexing functionality."""

    def test_auto_index_approved_when_enabled(
        self, mock_vector_store
    ):
        """Test approved examples are auto-indexed when enabled."""
        service = FeedbackService(
            vector_store=mock_vector_store,
            enabled=True
        )

        service.record_approval(code="def test(): pass")

        mock_vector_store.add_example.assert_called_once()

    def test_no_auto_index_when_disabled(
        self, mock_vector_store
    ):
        """Test approved examples are not indexed when disabled."""
        service = FeedbackService(
            vector_store=mock_vector_store,
            enabled=False
        )

        service.record_approval(code="def test(): pass")

        # Should not index when disabled
        mock_vector_store.add_example.assert_not_called()

    def test_auto_index_can_be_overridden(
        self, feedback_service, mock_vector_store
    ):
        """Test auto-index can be disabled per-call."""
        feedback_service.record_feedback(
            code="def test(): pass",
            feedback_type=FeedbackType.APPROVED,
            auto_index=False
        )

        # Should not index even though feedback is approved
        mock_vector_store.add_example.assert_not_called()

    def test_auto_index_includes_feedback_metadata(
        self, feedback_service, mock_vector_store
    ):
        """Test indexed examples include feedback metadata."""
        feedback_service.record_approval(
            code="def test(): pass",
            metadata={"language": "python"},
            user_id="user123"
        )

        # Check metadata passed to add_example
        call_args = mock_vector_store.add_example.call_args
        indexed_metadata = call_args.kwargs["metadata"]

        assert indexed_metadata["approved"] is True
        assert indexed_metadata["approved_by"] == "user123"
        assert "feedback_id" in indexed_metadata
        assert "feedback_indexed_at" in indexed_metadata


class TestMetrics:
    """Test metrics tracking."""

    def test_metrics_track_feedback_types(self, feedback_service):
        """Test metrics track different feedback types."""
        feedback_service.record_approval(code="code1")
        feedback_service.record_approval(code="code2")
        feedback_service.record_rejection(code="code3")
        feedback_service.record_feedback(
            code="code4",
            feedback_type=FeedbackType.MODIFIED
        )

        metrics = feedback_service.metrics

        assert metrics.total_feedback == 4
        assert metrics.approved_count == 2
        assert metrics.rejected_count == 1
        assert metrics.modified_count == 1

    def test_metrics_approval_rate(self, feedback_service):
        """Test approval rate calculation."""
        # Record 3 approvals, 1 rejection = 75% approval rate
        feedback_service.record_approval(code="code1")
        feedback_service.record_approval(code="code2")
        feedback_service.record_approval(code="code3")
        feedback_service.record_rejection(code="code4")

        assert feedback_service.metrics.approval_rate == 75.0

    def test_metrics_approval_rate_zero_feedback(self, feedback_service):
        """Test approval rate with no feedback."""
        assert feedback_service.metrics.approval_rate == 0.0

    def test_get_metrics(self, feedback_service):
        """Test getting metrics dictionary."""
        feedback_service.record_approval(code="code1")
        feedback_service.record_rejection(code="code2")

        metrics_dict = feedback_service.get_metrics()

        assert metrics_dict["total_feedback"] == 2
        assert metrics_dict["approved_count"] == 1
        assert metrics_dict["rejected_count"] == 1
        assert "approval_rate" in metrics_dict

    def test_metrics_track_indexed_count(self, feedback_service):
        """Test metrics track successfully indexed examples."""
        feedback_service.record_approval(code="code1")
        feedback_service.record_approval(code="code2")

        assert feedback_service.metrics.indexed_count == 2


class TestFeedbackHistory:
    """Test feedback history management."""

    def test_get_feedback_history(self, feedback_service):
        """Test retrieving feedback history."""
        feedback_service.record_approval(code="code1")
        feedback_service.record_rejection(code="code2")

        history = feedback_service.get_feedback_history()

        assert len(history) == 2
        assert all(isinstance(entry, dict) for entry in history)

    def test_get_feedback_history_with_limit(self, feedback_service):
        """Test retrieving limited feedback history."""
        for i in range(10):
            feedback_service.record_approval(code=f"code{i}")

        history = feedback_service.get_feedback_history(limit=5)

        assert len(history) == 5

    def test_get_feedback_history_filtered_by_type(self, feedback_service):
        """Test retrieving history filtered by type."""
        feedback_service.record_approval(code="code1")
        feedback_service.record_approval(code="code2")
        feedback_service.record_rejection(code="code3")

        approved_history = feedback_service.get_feedback_history(
            feedback_type=FeedbackType.APPROVED
        )

        assert len(approved_history) == 2
        assert all(
            entry["feedback_type"] == "approved"
            for entry in approved_history
        )

    def test_get_recent_approvals(self, feedback_service):
        """Test getting recent approvals."""
        feedback_service.record_approval(code="code1")
        feedback_service.record_rejection(code="code2")
        feedback_service.record_approval(code="code3")

        recent = feedback_service.get_recent_approvals(limit=10)

        assert len(recent) == 2
        assert all(
            entry["feedback_type"] == "approved"
            for entry in recent
        )

    def test_clear_history(self, feedback_service):
        """Test clearing feedback history."""
        feedback_service.record_approval(code="code1")
        feedback_service.record_approval(code="code2")

        cleared = feedback_service.clear_history()

        assert cleared == 2
        assert len(feedback_service.feedback_history) == 0


class TestEnableDisable:
    """Test enable/disable functionality."""

    def test_enable(self, mock_vector_store):
        """Test enabling feedback loop."""
        service = FeedbackService(
            vector_store=mock_vector_store,
            enabled=False
        )

        service.enable()

        assert service.enabled is True

    def test_disable(self, feedback_service):
        """Test disabling feedback loop."""
        feedback_service.disable()

        assert feedback_service.enabled is False

    def test_disabled_service_doesnt_index(self, mock_vector_store):
        """Test disabled service doesn't auto-index."""
        service = FeedbackService(
            vector_store=mock_vector_store,
            enabled=False
        )

        service.record_approval(code="def test(): pass")

        # Should record feedback but not index
        assert len(service.feedback_history) == 1
        mock_vector_store.add_example.assert_not_called()


class TestResetMetrics:
    """Test metrics reset functionality."""

    def test_reset_metrics(self, feedback_service):
        """Test resetting metrics."""
        feedback_service.record_approval(code="code1")
        feedback_service.record_rejection(code="code2")

        feedback_service.reset_metrics()

        assert feedback_service.metrics.total_feedback == 0
        assert feedback_service.metrics.approved_count == 0
        assert feedback_service.metrics.rejected_count == 0


class TestGetStats:
    """Test comprehensive statistics."""

    def test_get_stats(self, feedback_service):
        """Test getting comprehensive statistics."""
        feedback_service.record_approval(code="code1")

        stats = feedback_service.get_stats()

        assert stats["enabled"] is True
        assert "metrics" in stats
        assert "history_size" in stats
        assert "vector_store_stats" in stats
        assert stats["history_size"] == 1


class TestFeedbackEntry:
    """Test FeedbackEntry dataclass."""

    def test_feedback_entry_creation(self):
        """Test creating feedback entry."""
        entry = FeedbackEntry(
            id="test_id",
            code="test code",
            feedback_type=FeedbackType.APPROVED,
            metadata={"key": "value"},
            timestamp="2024-01-01T00:00:00"
        )

        assert entry.id == "test_id"
        assert entry.code == "test code"
        assert entry.feedback_type == FeedbackType.APPROVED

    def test_feedback_entry_to_dict(self):
        """Test converting feedback entry to dict."""
        entry = FeedbackEntry(
            id="test_id",
            code="test code",
            feedback_type=FeedbackType.APPROVED,
            metadata={},
            timestamp="2024-01-01T00:00:00",
            user_id="user123"
        )

        entry_dict = entry.to_dict()

        assert entry_dict["id"] == "test_id"
        assert entry_dict["feedback_type"] == "approved"
        assert entry_dict["user_id"] == "user123"


class TestFeedbackMetrics:
    """Test FeedbackMetrics dataclass."""

    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = FeedbackMetrics()

        assert metrics.total_feedback == 0
        assert metrics.approved_count == 0
        assert metrics.approval_rate == 0.0

    def test_metrics_to_dict(self):
        """Test converting metrics to dict."""
        metrics = FeedbackMetrics(
            total_feedback=10,
            approved_count=7,
            rejected_count=3
        )

        metrics_dict = metrics.to_dict()

        assert metrics_dict["total_feedback"] == 10
        assert metrics_dict["approved_count"] == 7
        assert metrics_dict["approval_rate"] == 70.0


class TestFactoryFunction:
    """Test factory function."""

    def test_create_feedback_service(self, mock_vector_store):
        """Test factory function creates FeedbackService."""
        service = create_feedback_service(
            vector_store=mock_vector_store,
            enabled=True
        )

        assert isinstance(service, FeedbackService)
        assert service.enabled is True
        assert service.vector_store == mock_vector_store


class TestErrorHandling:
    """Test error handling."""

    def test_indexing_error_handled_gracefully(
        self, feedback_service, mock_vector_store
    ):
        """Test that indexing errors don't crash the service."""
        mock_vector_store.add_example.side_effect = Exception("Index error")

        # Should not raise, just log error
        feedback_id = feedback_service.record_approval(code="def test(): pass")

        # Feedback should still be recorded
        assert feedback_id is not None
        assert len(feedback_service.feedback_history) == 1
        # But not counted as indexed
        assert feedback_service.metrics.indexed_count == 0
