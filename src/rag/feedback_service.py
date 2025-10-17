"""
Feedback service for RAG system.

This module implements a continuous learning feedback loop where approved code
examples are automatically indexed to improve future retrieval quality.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from src.rag.vector_store import VectorStore
from src.config import RAG_ENABLE_FEEDBACK
from src.observability import get_logger


class FeedbackType(Enum):
    """Feedback type enumeration."""
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    USED = "used"


@dataclass
class FeedbackEntry:
    """
    Single feedback entry.

    Attributes:
        id: Unique feedback ID
        code: Code snippet
        feedback_type: Type of feedback
        metadata: Associated metadata
        timestamp: When feedback was recorded
        user_id: Optional user identifier
        task_description: Optional task context
        original_query: Original retrieval query
        retrieval_id: ID of retrieved example (if applicable)
    """
    id: str
    code: str
    feedback_type: FeedbackType
    metadata: Dict[str, Any]
    timestamp: str
    user_id: Optional[str] = None
    task_description: Optional[str] = None
    original_query: Optional[str] = None
    retrieval_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "code": self.code,
            "feedback_type": self.feedback_type.value,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "task_description": self.task_description,
            "original_query": self.original_query,
            "retrieval_id": self.retrieval_id,
        }


@dataclass
class FeedbackMetrics:
    """
    Feedback metrics tracker.

    Attributes:
        total_feedback: Total feedback count
        approved_count: Number of approved examples
        rejected_count: Number of rejected examples
        modified_count: Number of modified examples
        used_count: Number of used examples
        approval_rate: Percentage of approved examples
        indexed_count: Number of examples indexed to vector store
    """
    total_feedback: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    modified_count: int = 0
    used_count: int = 0
    indexed_count: int = 0

    @property
    def approval_rate(self) -> float:
        """Calculate approval rate."""
        if self.total_feedback == 0:
            return 0.0
        return (self.approved_count / self.total_feedback) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_feedback": self.total_feedback,
            "approved_count": self.approved_count,
            "rejected_count": self.rejected_count,
            "modified_count": self.modified_count,
            "used_count": self.used_count,
            "indexed_count": self.indexed_count,
            "approval_rate": round(self.approval_rate, 2),
        }


class FeedbackService:
    """
    Feedback service for continuous learning.

    Manages feedback loop where approved code is automatically indexed
    to improve future retrieval quality. Tracks metrics and maintains
    feedback history.

    Attributes:
        vector_store: Vector store for indexing approved examples
        enabled: Whether feedback loop is enabled
        logger: Structured logger
        metrics: Feedback metrics tracker
        feedback_history: In-memory feedback history
    """

    def __init__(
        self,
        vector_store: VectorStore,
        enabled: bool = RAG_ENABLE_FEEDBACK,
    ):
        """
        Initialize feedback service.

        Args:
            vector_store: VectorStore instance
            enabled: Whether to enable feedback loop (default: from config)
        """
        self.logger = get_logger("rag.feedback_service")
        self.vector_store = vector_store
        self.enabled = enabled
        self.metrics = FeedbackMetrics()
        self.feedback_history: List[FeedbackEntry] = []

        self.logger.info(
            "FeedbackService initialized",
            enabled=self.enabled
        )

    def record_feedback(
        self,
        code: str,
        feedback_type: FeedbackType,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        task_description: Optional[str] = None,
        original_query: Optional[str] = None,
        retrieval_id: Optional[str] = None,
        auto_index: bool = True,
    ) -> str:
        """
        Record feedback for a code example.

        Args:
            code: Code snippet
            feedback_type: Type of feedback
            metadata: Optional metadata
            user_id: Optional user identifier
            task_description: Optional task context
            original_query: Original retrieval query
            retrieval_id: ID of retrieved example
            auto_index: Whether to auto-index approved examples

        Returns:
            Feedback entry ID

        Raises:
            ValueError: If code is empty
        """
        if not code or not code.strip():
            raise ValueError("Cannot record feedback for empty code")

        try:
            # Create feedback entry
            feedback_id = str(uuid.uuid4())
            entry = FeedbackEntry(
                id=feedback_id,
                code=code,
                feedback_type=feedback_type,
                metadata=metadata or {},
                timestamp=datetime.utcnow().isoformat(),
                user_id=user_id,
                task_description=task_description,
                original_query=original_query,
                retrieval_id=retrieval_id,
            )

            # Store in history
            self.feedback_history.append(entry)

            # Update metrics
            self._update_metrics(feedback_type)

            self.logger.info(
                "Feedback recorded",
                feedback_id=feedback_id,
                feedback_type=feedback_type.value,
                code_length=len(code),
                has_query=original_query is not None
            )

            # Auto-index approved examples if enabled
            if (
                self.enabled
                and auto_index
                and feedback_type == FeedbackType.APPROVED
            ):
                self._index_approved_example(entry)

            return feedback_id

        except Exception as e:
            self.logger.error(
                "Failed to record feedback",
                error=str(e),
                error_type=type(e).__name__,
                feedback_type=feedback_type.value
            )
            raise

    def record_approval(
        self,
        code: str,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Convenience method to record approved code.

        Args:
            code: Approved code snippet
            metadata: Optional metadata
            **kwargs: Additional arguments for record_feedback

        Returns:
            Feedback entry ID
        """
        # Ensure metadata marks this as approved
        if metadata is None:
            metadata = {}
        metadata["approved"] = True
        metadata["feedback_source"] = "manual_approval"

        return self.record_feedback(
            code=code,
            feedback_type=FeedbackType.APPROVED,
            metadata=metadata,
            **kwargs
        )

    def record_rejection(
        self,
        code: str,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Convenience method to record rejected code.

        Args:
            code: Rejected code snippet
            reason: Optional rejection reason
            metadata: Optional metadata
            **kwargs: Additional arguments for record_feedback

        Returns:
            Feedback entry ID
        """
        if metadata is None:
            metadata = {}
        metadata["approved"] = False
        metadata["feedback_source"] = "manual_rejection"
        if reason:
            metadata["rejection_reason"] = reason

        return self.record_feedback(
            code=code,
            feedback_type=FeedbackType.REJECTED,
            metadata=metadata,
            auto_index=False,  # Don't index rejected examples
            **kwargs
        )

    def record_usage(
        self,
        retrieval_id: str,
        was_helpful: bool,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Record that a retrieved example was used.

        Args:
            retrieval_id: ID of the retrieved example
            was_helpful: Whether the example was helpful
            metadata: Optional metadata

        Returns:
            Feedback entry ID or None if example not found
        """
        try:
            # Try to get the example from vector store
            # This is a simplified version - in production you'd query the vector store
            # For now, we'll create a usage feedback without the full code

            if metadata is None:
                metadata = {}

            metadata["was_helpful"] = was_helpful
            metadata["usage_tracked"] = True

            self.logger.info(
                "Usage tracked",
                retrieval_id=retrieval_id,
                was_helpful=was_helpful
            )

            # Update usage count in vector store metadata if possible
            # This would require updating the vector store example
            # For now, we just track in metrics
            self.metrics.used_count += 1
            self.metrics.total_feedback += 1

            return retrieval_id

        except Exception as e:
            self.logger.error(
                "Failed to record usage",
                error=str(e),
                error_type=type(e).__name__,
                retrieval_id=retrieval_id
            )
            return None

    def _index_approved_example(self, entry: FeedbackEntry) -> bool:
        """
        Index an approved example to vector store.

        Args:
            entry: Feedback entry to index

        Returns:
            True if indexed successfully
        """
        try:
            # Prepare metadata for indexing
            index_metadata = entry.metadata.copy()
            index_metadata["feedback_indexed_at"] = entry.timestamp
            index_metadata["feedback_id"] = entry.id
            index_metadata["approved"] = True

            if entry.user_id:
                index_metadata["approved_by"] = entry.user_id
            if entry.task_description:
                index_metadata["task_context"] = entry.task_description

            # Add to vector store
            example_id = self.vector_store.add_example(
                code=entry.code,
                metadata=index_metadata,
                example_id=f"feedback_{entry.id}"
            )

            self.metrics.indexed_count += 1

            self.logger.info(
                "Approved example indexed",
                feedback_id=entry.id,
                example_id=example_id
            )

            return True

        except Exception as e:
            self.logger.error(
                "Failed to index approved example",
                error=str(e),
                error_type=type(e).__name__,
                feedback_id=entry.id
            )
            return False

    def _update_metrics(self, feedback_type: FeedbackType):
        """
        Update feedback metrics.

        Args:
            feedback_type: Type of feedback
        """
        self.metrics.total_feedback += 1

        if feedback_type == FeedbackType.APPROVED:
            self.metrics.approved_count += 1
        elif feedback_type == FeedbackType.REJECTED:
            self.metrics.rejected_count += 1
        elif feedback_type == FeedbackType.MODIFIED:
            self.metrics.modified_count += 1
        elif feedback_type == FeedbackType.USED:
            self.metrics.used_count += 1

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get feedback metrics.

        Returns:
            Dictionary with feedback metrics
        """
        return self.metrics.to_dict()

    def get_feedback_history(
        self,
        limit: Optional[int] = None,
        feedback_type: Optional[FeedbackType] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get feedback history.

        Args:
            limit: Maximum number of entries to return
            feedback_type: Filter by feedback type

        Returns:
            List of feedback entries
        """
        history = self.feedback_history

        # Filter by type if specified
        if feedback_type:
            history = [e for e in history if e.feedback_type == feedback_type]

        # Apply limit
        if limit:
            history = history[-limit:]

        return [entry.to_dict() for entry in history]

    def get_recent_approvals(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent approved examples.

        Args:
            limit: Maximum number of entries

        Returns:
            List of approved examples
        """
        return self.get_feedback_history(
            limit=limit,
            feedback_type=FeedbackType.APPROVED
        )

    def clear_history(self) -> int:
        """
        Clear feedback history.

        Returns:
            Number of entries cleared
        """
        count = len(self.feedback_history)
        self.feedback_history.clear()

        self.logger.info("Feedback history cleared", entries_cleared=count)

        return count

    def reset_metrics(self):
        """Reset feedback metrics."""
        self.metrics = FeedbackMetrics()
        self.logger.info("Feedback metrics reset")

    def enable(self):
        """Enable feedback loop."""
        self.enabled = True
        self.logger.info("Feedback loop enabled")

    def disable(self):
        """Disable feedback loop."""
        self.enabled = False
        self.logger.info("Feedback loop disabled")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics.

        Returns:
            Dictionary with feedback service statistics
        """
        return {
            "enabled": self.enabled,
            "metrics": self.metrics.to_dict(),
            "history_size": len(self.feedback_history),
            "vector_store_stats": self.vector_store.get_stats(),
        }


def create_feedback_service(
    vector_store: VectorStore,
    enabled: bool = RAG_ENABLE_FEEDBACK,
) -> FeedbackService:
    """
    Factory function to create a feedback service instance.

    Args:
        vector_store: VectorStore instance
        enabled: Whether to enable feedback loop

    Returns:
        Initialized FeedbackService instance
    """
    return FeedbackService(
        vector_store=vector_store,
        enabled=enabled,
    )
