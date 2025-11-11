"""
Tests for ReviewQueueManager

Verifies queue operations, prioritization, and statistics.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

from src.mge.v2.review.review_queue_manager import (
    ReviewQueueManager,
    ReviewItem,
    ReviewPriority,
    ReviewStatus,
    QueueStatistics
)
from src.mge.v2.review.confidence_scorer import (
    ConfidenceScore,
    ConfidenceLevel
)
from src.models.atomic_unit import AtomicUnit


@pytest.fixture
def db_session():
    """Mock database session"""
    return MagicMock()


@pytest.fixture
def queue_manager(db_session):
    """Create ReviewQueueManager instance"""
    return ReviewQueueManager(db_session)


@pytest.fixture
def mock_atom():
    """Create mock AtomicUnit"""
    atom = MagicMock(spec=AtomicUnit)
    atom.atom_id = uuid4()
    atom.masterplan_id = uuid4()
    atom.phase_number = 3
    return atom


@pytest.fixture
def baja_confidence_score(mock_atom):
    """Low confidence score (baja level)"""
    return ConfidenceScore(
        atom_id=mock_atom.atom_id,
        total_score=45.0,
        level=ConfidenceLevel.BAJA,
        validation_score=25.0,
        retry_score=20.0,
        complexity_score=100.0,
        test_score=50.0,
        validation_metrics={},
        retry_metrics={"retry_count": 4},
        complexity_metrics={"cyclomatic_complexity": 5},
        test_metrics={}
    )


@pytest.fixture
def media_confidence_score(mock_atom):
    """Medium confidence score (media level)"""
    return ConfidenceScore(
        atom_id=mock_atom.atom_id,
        total_score=65.0,
        level=ConfidenceLevel.MEDIA,
        validation_score=50.0,
        retry_score=80.0,
        complexity_score=100.0,
        test_score=50.0,
        validation_metrics={},
        retry_metrics={"retry_count": 1},
        complexity_metrics={"cyclomatic_complexity": 8},
        test_metrics={}
    )


class TestReviewQueueManager:
    """Test ReviewQueueManager functionality"""

    def test_add_to_queue_basic(self, queue_manager, mock_atom, baja_confidence_score):
        """Test adding atom to queue"""
        review_item = queue_manager.add_to_queue(
            atom=mock_atom,
            confidence_score=baja_confidence_score,
            priority=ReviewPriority.HIGH
        )

        assert review_item.atom_id == mock_atom.atom_id
        assert review_item.masterplan_id == mock_atom.masterplan_id
        assert review_item.confidence_score == baja_confidence_score
        assert review_item.priority == ReviewPriority.HIGH
        assert review_item.status == ReviewStatus.PENDING
        assert review_item.sla_deadline is not None

        # Verify in queue
        assert mock_atom.atom_id in queue_manager._queue

    def test_add_to_queue_auto_priority(self, queue_manager, mock_atom, baja_confidence_score):
        """Test auto-calculation of priority"""
        # Baja confidence + early phase (critical) → CRITICAL priority
        mock_atom.phase_number = 1  # Early phase

        review_item = queue_manager.add_to_queue(
            atom=mock_atom,
            confidence_score=baja_confidence_score,
            priority=None  # Auto-calculate
        )

        assert review_item.priority == ReviewPriority.CRITICAL

    def test_calculate_priority_baja_critical(self, queue_manager, mock_atom, baja_confidence_score):
        """Test priority calculation for baja + critical factors"""
        # Baja + early phase → CRITICAL
        mock_atom.phase_number = 1
        priority = queue_manager._calculate_priority(baja_confidence_score, mock_atom)
        assert priority == ReviewPriority.CRITICAL

        # Baja + high complexity → CRITICAL
        mock_atom.phase_number = 5
        baja_confidence_score.complexity_metrics["cyclomatic_complexity"] = 25
        priority = queue_manager._calculate_priority(baja_confidence_score, mock_atom)
        assert priority == ReviewPriority.CRITICAL

    def test_calculate_priority_baja_high(self, queue_manager, mock_atom, baja_confidence_score):
        """Test priority calculation for baja without critical factors"""
        # Baja + later phase + low complexity → HIGH
        mock_atom.phase_number = 5
        baja_confidence_score.complexity_metrics["cyclomatic_complexity"] = 5

        priority = queue_manager._calculate_priority(baja_confidence_score, mock_atom)
        assert priority == ReviewPriority.HIGH

    def test_calculate_priority_media(self, queue_manager, mock_atom, media_confidence_score):
        """Test priority calculation for media confidence"""
        # Media + high retries → HIGH
        media_confidence_score.retry_metrics["retry_count"] = 3
        priority = queue_manager._calculate_priority(media_confidence_score, mock_atom)
        assert priority == ReviewPriority.HIGH

        # Media + low validation → HIGH
        media_confidence_score.retry_metrics["retry_count"] = 0
        media_confidence_score.validation_score = 50.0
        priority = queue_manager._calculate_priority(media_confidence_score, mock_atom)
        assert priority == ReviewPriority.HIGH

        # Media + normal conditions → MEDIUM
        media_confidence_score.validation_score = 80.0
        priority = queue_manager._calculate_priority(media_confidence_score, mock_atom)
        assert priority == ReviewPriority.MEDIUM

    def test_sla_deadline_by_priority(self, queue_manager, mock_atom, baja_confidence_score):
        """Test SLA deadline calculation by priority"""
        # CRITICAL: 4 hours
        review_critical = queue_manager.add_to_queue(
            mock_atom, baja_confidence_score, ReviewPriority.CRITICAL
        )
        expected_deadline_critical = datetime.utcnow() + timedelta(hours=4)
        assert abs((review_critical.sla_deadline - expected_deadline_critical).total_seconds()) < 5

        # HIGH: 12 hours
        mock_atom.atom_id = uuid4()  # New atom
        review_high = queue_manager.add_to_queue(
            mock_atom, baja_confidence_score, ReviewPriority.HIGH
        )
        expected_deadline_high = datetime.utcnow() + timedelta(hours=12)
        assert abs((review_high.sla_deadline - expected_deadline_high).total_seconds()) < 5

        # MEDIUM: 24 hours
        mock_atom.atom_id = uuid4()
        review_medium = queue_manager.add_to_queue(
            mock_atom, baja_confidence_score, ReviewPriority.MEDIUM
        )
        expected_deadline_medium = datetime.utcnow() + timedelta(hours=24)
        assert abs((review_medium.sla_deadline - expected_deadline_medium).total_seconds()) < 5

        # LOW: 48 hours
        mock_atom.atom_id = uuid4()
        review_low = queue_manager.add_to_queue(
            mock_atom, baja_confidence_score, ReviewPriority.LOW
        )
        expected_deadline_low = datetime.utcnow() + timedelta(hours=48)
        assert abs((review_low.sla_deadline - expected_deadline_low).total_seconds()) < 5

    def test_get_pending_reviews_ordering(self, queue_manager, mock_atom, baja_confidence_score):
        """Test pending reviews ordered by priority and SLA"""
        # Add multiple items with different priorities
        atom1 = MagicMock(spec=AtomicUnit)
        atom1.atom_id = uuid4()
        atom1.masterplan_id = mock_atom.masterplan_id
        atom1.phase_number = 3

        atom2 = MagicMock(spec=AtomicUnit)
        atom2.atom_id = uuid4()
        atom2.masterplan_id = mock_atom.masterplan_id
        atom2.phase_number = 3

        atom3 = MagicMock(spec=AtomicUnit)
        atom3.atom_id = uuid4()
        atom3.masterplan_id = mock_atom.masterplan_id
        atom3.phase_number = 3

        # Add: MEDIUM, CRITICAL, HIGH
        queue_manager.add_to_queue(atom1, baja_confidence_score, ReviewPriority.MEDIUM)
        queue_manager.add_to_queue(atom2, baja_confidence_score, ReviewPriority.CRITICAL)
        queue_manager.add_to_queue(atom3, baja_confidence_score, ReviewPriority.HIGH)

        pending = queue_manager.get_pending_reviews()

        # Should be ordered: CRITICAL, HIGH, MEDIUM
        assert len(pending) == 3
        assert pending[0].atom_id == atom2.atom_id  # CRITICAL
        assert pending[1].atom_id == atom3.atom_id  # HIGH
        assert pending[2].atom_id == atom1.atom_id  # MEDIUM

    def test_get_pending_reviews_filters(self, queue_manager, mock_atom, baja_confidence_score):
        """Test pending reviews with filters"""
        masterplan1 = uuid4()
        masterplan2 = uuid4()

        # Add items to different masterplans
        atom1 = MagicMock(spec=AtomicUnit)
        atom1.atom_id = uuid4()
        atom1.masterplan_id = masterplan1
        atom1.phase_number = 3

        atom2 = MagicMock(spec=AtomicUnit)
        atom2.atom_id = uuid4()
        atom2.masterplan_id = masterplan2
        atom2.phase_number = 3

        queue_manager.add_to_queue(atom1, baja_confidence_score, ReviewPriority.HIGH)
        queue_manager.add_to_queue(atom2, baja_confidence_score, ReviewPriority.CRITICAL)

        # Filter by masterplan
        pending_mp1 = queue_manager.get_pending_reviews(masterplan_id=masterplan1)
        assert len(pending_mp1) == 1
        assert pending_mp1[0].masterplan_id == masterplan1

        # Filter by priority
        pending_critical = queue_manager.get_pending_reviews(priority=ReviewPriority.CRITICAL)
        assert len(pending_critical) == 1
        assert pending_critical[0].priority == ReviewPriority.CRITICAL

    def test_update_status(self, queue_manager, mock_atom, baja_confidence_score):
        """Test updating review status"""
        review_item = queue_manager.add_to_queue(
            mock_atom, baja_confidence_score, ReviewPriority.HIGH
        )

        assert review_item.status == ReviewStatus.PENDING
        assert review_item.reviewed_at is None

        # Update to IN_REVIEW
        updated = queue_manager.update_status(
            mock_atom.atom_id,
            ReviewStatus.IN_REVIEW,
            assigned_to="reviewer1"
        )

        assert updated.status == ReviewStatus.IN_REVIEW
        assert updated.assigned_to == "reviewer1"
        assert updated.reviewed_at is None  # Not completed yet

        # Update to APPROVED
        updated = queue_manager.update_status(
            mock_atom.atom_id,
            ReviewStatus.APPROVED,
            notes="Looks good"
        )

        assert updated.status == ReviewStatus.APPROVED
        assert updated.notes == "Looks good"
        assert updated.reviewed_at is not None  # Completion timestamp set

    def test_remove_from_queue(self, queue_manager, mock_atom, baja_confidence_score):
        """Test removing item from queue"""
        queue_manager.add_to_queue(mock_atom, baja_confidence_score, ReviewPriority.HIGH)

        assert mock_atom.atom_id in queue_manager._queue

        # Remove
        removed = queue_manager.remove_from_queue(mock_atom.atom_id)
        assert removed is True
        assert mock_atom.atom_id not in queue_manager._queue

        # Try removing again (should fail)
        removed_again = queue_manager.remove_from_queue(mock_atom.atom_id)
        assert removed_again is False

    def test_get_sla_violations(self, queue_manager, mock_atom, baja_confidence_score):
        """Test SLA violation detection"""
        # Add item with CRITICAL priority (4h SLA)
        review_item = queue_manager.add_to_queue(
            mock_atom, baja_confidence_score, ReviewPriority.CRITICAL
        )

        # No violations initially
        violations = queue_manager.get_sla_violations()
        assert len(violations) == 0

        # Simulate SLA expiration by manipulating deadline
        review_item.sla_deadline = datetime.utcnow() - timedelta(hours=1)

        # Should detect violation
        violations = queue_manager.get_sla_violations()
        assert len(violations) == 1
        assert violations[0].atom_id == mock_atom.atom_id

    def test_get_statistics(self, queue_manager, mock_atom, baja_confidence_score, media_confidence_score):
        """Test queue statistics calculation"""
        masterplan_id = mock_atom.masterplan_id

        # Add multiple items with different statuses
        atom1 = MagicMock(spec=AtomicUnit)
        atom1.atom_id = uuid4()
        atom1.masterplan_id = masterplan_id
        atom1.phase_number = 3

        atom2 = MagicMock(spec=AtomicUnit)
        atom2.atom_id = uuid4()
        atom2.masterplan_id = masterplan_id
        atom2.phase_number = 3

        atom3 = MagicMock(spec=AtomicUnit)
        atom3.atom_id = uuid4()
        atom3.masterplan_id = masterplan_id
        atom3.phase_number = 3

        # Add items
        queue_manager.add_to_queue(atom1, baja_confidence_score, ReviewPriority.CRITICAL)
        queue_manager.add_to_queue(atom2, media_confidence_score, ReviewPriority.MEDIUM)
        queue_manager.add_to_queue(atom3, baja_confidence_score, ReviewPriority.HIGH)

        # Update statuses
        queue_manager.update_status(atom1.atom_id, ReviewStatus.APPROVED)
        queue_manager.update_status(atom2.atom_id, ReviewStatus.REJECTED)

        # Get statistics
        stats = queue_manager.get_statistics(masterplan_id=masterplan_id)

        assert stats.total_items == 3
        assert stats.pending_count == 1  # atom3
        assert stats.approved_count == 1  # atom1
        assert stats.rejected_count == 1  # atom2
        assert stats.correction_rate == pytest.approx(0.5)  # 1 rejected / 2 reviewed

        # Check priority counts
        assert stats.by_priority[ReviewPriority.CRITICAL.value] == 1
        assert stats.by_priority[ReviewPriority.MEDIUM.value] == 1
        assert stats.by_priority[ReviewPriority.HIGH.value] == 1

        # Check confidence level counts
        assert stats.by_confidence_level[ConfidenceLevel.BAJA.value] == 2
        assert stats.by_confidence_level[ConfidenceLevel.MEDIA.value] == 1

    def test_should_add_to_queue_baja(self, queue_manager, baja_confidence_score):
        """Test should_add_to_queue for baja confidence"""
        # Baja always added, regardless of queue size
        should_add = queue_manager.should_add_to_queue(
            confidence_score=baja_confidence_score,
            masterplan_atom_count=100,
            current_queue_size=25  # Already at 25%
        )

        assert should_add is True

    def test_should_add_to_queue_media(self, queue_manager, media_confidence_score):
        """Test should_add_to_queue for media confidence"""
        # Media added if queue < 20% target
        should_add_below = queue_manager.should_add_to_queue(
            confidence_score=media_confidence_score,
            masterplan_atom_count=100,
            current_queue_size=15  # 15% < 20% target
        )
        assert should_add_below is True

        # Media NOT added if queue >= 20% target
        should_add_above = queue_manager.should_add_to_queue(
            confidence_score=media_confidence_score,
            masterplan_atom_count=100,
            current_queue_size=20  # 20% = target
        )
        assert should_add_above is False

    def test_should_add_to_queue_alta(self, queue_manager, mock_atom):
        """Test should_add_to_queue for alta confidence"""
        alta_confidence = ConfidenceScore(
            atom_id=mock_atom.atom_id,
            total_score=85.0,
            level=ConfidenceLevel.ALTA,
            validation_score=100.0,
            retry_score=80.0,
            complexity_score=100.0,
            test_score=50.0,
            validation_metrics={},
            retry_metrics={},
            complexity_metrics={},
            test_metrics={}
        )

        # Alta never added
        should_add = queue_manager.should_add_to_queue(
            confidence_score=alta_confidence,
            masterplan_atom_count=100,
            current_queue_size=5
        )

        assert should_add is False

    def test_review_item_is_sla_violated(self, mock_atom, baja_confidence_score):
        """Test ReviewItem.is_sla_violated()"""
        # Create item with expired SLA
        review_item = ReviewItem(
            atom_id=mock_atom.atom_id,
            masterplan_id=mock_atom.masterplan_id,
            confidence_score=baja_confidence_score,
            priority=ReviewPriority.HIGH,
            status=ReviewStatus.PENDING,
            created_at=datetime.utcnow() - timedelta(hours=25),
            sla_deadline=datetime.utcnow() - timedelta(hours=1)
        )

        assert review_item.is_sla_violated() is True

        # Create item with future SLA
        review_item_ok = ReviewItem(
            atom_id=uuid4(),
            masterplan_id=mock_atom.masterplan_id,
            confidence_score=baja_confidence_score,
            priority=ReviewPriority.HIGH,
            status=ReviewStatus.PENDING,
            created_at=datetime.utcnow(),
            sla_deadline=datetime.utcnow() + timedelta(hours=12)
        )

        assert review_item_ok.is_sla_violated() is False

    def test_review_item_time_in_queue(self, mock_atom, baja_confidence_score):
        """Test ReviewItem.time_in_queue()"""
        created = datetime.utcnow() - timedelta(hours=5)

        review_item = ReviewItem(
            atom_id=mock_atom.atom_id,
            masterplan_id=mock_atom.masterplan_id,
            confidence_score=baja_confidence_score,
            priority=ReviewPriority.HIGH,
            status=ReviewStatus.PENDING,
            created_at=created,
            sla_deadline=datetime.utcnow() + timedelta(hours=7)
        )

        time_in_queue = review_item.time_in_queue()

        # Should be approximately 5 hours
        assert time_in_queue.total_seconds() >= 5 * 3600 - 10  # Allow 10s tolerance
        assert time_in_queue.total_seconds() <= 5 * 3600 + 10

    def test_review_item_to_dict(self, mock_atom, baja_confidence_score):
        """Test ReviewItem serialization"""
        review_item = ReviewItem(
            atom_id=mock_atom.atom_id,
            masterplan_id=mock_atom.masterplan_id,
            confidence_score=baja_confidence_score,
            priority=ReviewPriority.HIGH,
            status=ReviewStatus.PENDING,
            created_at=datetime.utcnow(),
            sla_deadline=datetime.utcnow() + timedelta(hours=12),
            assigned_to="reviewer1",
            notes="Test note"
        )

        item_dict = review_item.to_dict()

        assert "atom_id" in item_dict
        assert "masterplan_id" in item_dict
        assert "confidence_score" in item_dict
        assert "priority" in item_dict
        assert "status" in item_dict
        assert item_dict["priority"] == "high"
        assert item_dict["status"] == "pending"
        assert item_dict["assigned_to"] == "reviewer1"
        assert item_dict["notes"] == "Test note"

    def test_queue_statistics_correction_rate_target(self, queue_manager):
        """Test correction rate calculation and >80% target"""
        masterplan_id = uuid4()

        # Add 10 items and approve 9, reject 1 (10% correction rate)
        for i in range(10):
            atom = MagicMock(spec=AtomicUnit)
            atom.atom_id = uuid4()
            atom.masterplan_id = masterplan_id
            atom.phase_number = 3

            score = ConfidenceScore(
                atom_id=atom.atom_id,
                total_score=45.0,
                level=ConfidenceLevel.BAJA,
                validation_score=25.0,
                retry_score=20.0,
                complexity_score=100.0,
                test_score=50.0,
                validation_metrics={},
                retry_metrics={},
                complexity_metrics={},
                test_metrics={}
            )

            queue_manager.add_to_queue(atom, score, ReviewPriority.HIGH)

            # Approve first 9, reject last 1
            if i < 9:
                queue_manager.update_status(atom.atom_id, ReviewStatus.APPROVED)
            else:
                queue_manager.update_status(atom.atom_id, ReviewStatus.REJECTED)

        stats = queue_manager.get_statistics(masterplan_id=masterplan_id)

        # Correction rate = rejected / (approved + rejected) = 1/10 = 0.1
        assert stats.correction_rate == pytest.approx(0.1)
        assert stats.approved_count == 9
        assert stats.rejected_count == 1
