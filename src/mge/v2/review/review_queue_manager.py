"""
ReviewQueueManager - Manage human review queue for low-confidence atoms

Handles queue operations for bottom 15-20% confidence atoms:
- CRUD operations for review items
- Intelligent prioritization (critical atoms first)
- SLA tracking (<24h target)
- Statistics and correction rate monitoring (>80% target)

Target: Bottom 15-20% of atoms enter queue (baja + some media)
SLA: <24h review time
Correction Rate Target: >80% (proportion of reviews that improve code)
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.atomic_unit import AtomicUnit
from src.mge.v2.review.confidence_scorer import ConfidenceScore, ConfidenceLevel

logger = logging.getLogger(__name__)


class ReviewPriority(str, Enum):
    """Review priority levels"""
    CRITICAL = "critical"  # Blocks execution, requires immediate review
    HIGH = "high"          # Important atom, review within 12h
    MEDIUM = "medium"      # Standard review, 24h SLA
    LOW = "low"            # Optional review, 48h SLA


class ReviewStatus(str, Enum):
    """Review item status"""
    PENDING = "pending"      # Awaiting review
    IN_REVIEW = "in_review"  # Currently being reviewed
    APPROVED = "approved"    # Approved by reviewer
    REJECTED = "rejected"    # Rejected, needs rework
    COMPLETED = "completed"  # Review cycle complete


@dataclass
class ReviewItem:
    """Review queue item with metadata"""

    atom_id: UUID
    masterplan_id: UUID
    confidence_score: ConfidenceScore
    priority: ReviewPriority
    status: ReviewStatus
    created_at: datetime
    assigned_to: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    sla_deadline: Optional[datetime] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage/serialization"""
        return {
            "atom_id": str(self.atom_id),
            "masterplan_id": str(self.masterplan_id),
            "confidence_score": self.confidence_score.to_dict(),
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "assigned_to": self.assigned_to,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "sla_deadline": self.sla_deadline.isoformat() if self.sla_deadline else None,
            "notes": self.notes
        }

    def is_sla_violated(self) -> bool:
        """Check if SLA deadline has passed"""
        if not self.sla_deadline:
            return False
        return datetime.utcnow() > self.sla_deadline

    def time_in_queue(self) -> timedelta:
        """Calculate time spent in queue"""
        return datetime.utcnow() - self.created_at


@dataclass
class QueueStatistics:
    """Review queue statistics"""

    total_items: int
    pending_count: int
    in_review_count: int
    approved_count: int
    rejected_count: int
    completed_count: int

    avg_review_time_hours: float
    sla_violation_rate: float
    correction_rate: float

    by_priority: Dict[str, int]
    by_confidence_level: Dict[str, int]


class ReviewQueueManager:
    """
    Manage review queue for low-confidence atoms

    Features:
    - Bottom 15-20% selection based on confidence scores
    - Intelligent prioritization (critical atoms first)
    - CRUD operations for review items
    - SLA tracking and violation detection
    - Statistics and metrics

    Example:
        queue_manager = ReviewQueueManager(db_session)

        # Add atom to queue
        review_item = queue_manager.add_to_queue(
            atom=atom,
            confidence_score=score,
            priority=ReviewPriority.HIGH
        )

        # Get pending reviews
        pending = queue_manager.get_pending_reviews(limit=10)

        # Update review status
        queue_manager.update_status(atom_id, ReviewStatus.APPROVED)

        # Get statistics
        stats = queue_manager.get_statistics(masterplan_id)
    """

    def __init__(self, db: Session):
        """
        Initialize ReviewQueueManager

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

        # In-memory queue (should be replaced with database table)
        # TODO: Create review_queue table in database schema
        self._queue: Dict[UUID, ReviewItem] = {}

        # SLA targets by priority (in hours)
        self.sla_targets = {
            ReviewPriority.CRITICAL: 4,   # 4 hours
            ReviewPriority.HIGH: 12,      # 12 hours
            ReviewPriority.MEDIUM: 24,    # 24 hours
            ReviewPriority.LOW: 48        # 48 hours
        }

    def add_to_queue(
        self,
        atom: AtomicUnit,
        confidence_score: ConfidenceScore,
        priority: Optional[ReviewPriority] = None
    ) -> ReviewItem:
        """
        Add atom to review queue

        Args:
            atom: AtomicUnit instance
            confidence_score: Calculated confidence score
            priority: Review priority (auto-calculated if None)

        Returns:
            ReviewItem added to queue
        """
        # Auto-calculate priority if not provided
        if priority is None:
            priority = self._calculate_priority(confidence_score, atom)

        # Calculate SLA deadline
        sla_hours = self.sla_targets[priority]
        sla_deadline = datetime.utcnow() + timedelta(hours=sla_hours)

        # Create review item
        review_item = ReviewItem(
            atom_id=atom.id,
            masterplan_id=atom.masterplan_id,
            confidence_score=confidence_score,
            priority=priority,
            status=ReviewStatus.PENDING,
            created_at=datetime.utcnow(),
            sla_deadline=sla_deadline
        )

        # Add to queue
        self._queue[atom.id] = review_item

        logger.info(
            f"Added atom {atom.id} to review queue: "
            f"score={confidence_score.total_score:.2f}, "
            f"level={confidence_score.level.value}, "
            f"priority={priority.value}, "
            f"sla_deadline={sla_deadline.isoformat()}"
        )

        return review_item

    def _calculate_priority(
        self,
        confidence_score: ConfidenceScore,
        atom: AtomicUnit
    ) -> ReviewPriority:
        """
        Calculate review priority based on confidence score and atom metadata

        Priority Logic:
        - CRITICAL: baja confidence (<60) AND (high complexity OR critical phase)
        - HIGH: baja confidence (<60) OR (media confidence + critical factors)
        - MEDIUM: media confidence (60-74)
        - LOW: alta confidence (75-89) in review queue (edge cases)

        Args:
            confidence_score: Calculated confidence score
            atom: AtomicUnit instance

        Returns:
            ReviewPriority level
        """
        score = confidence_score.total_score
        level = confidence_score.level

        # CRITICAL: Very low confidence + critical factors
        if level == ConfidenceLevel.BAJA:
            # Check if atom is in critical phase or has high complexity
            is_critical_phase = atom.phase_number <= 2  # Early phases more critical
            has_high_complexity = (
                confidence_score.complexity_metrics.get("cyclomatic_complexity", 0) > 20
            )

            if is_critical_phase or has_high_complexity:
                return ReviewPriority.CRITICAL

            # Otherwise HIGH priority for baja confidence
            return ReviewPriority.HIGH

        # HIGH: Media confidence with critical factors
        if level == ConfidenceLevel.MEDIA:
            has_high_retry = confidence_score.retry_metrics.get("retry_count", 0) >= 3
            validation_failed = confidence_score.validation_score < 75

            if has_high_retry or validation_failed:
                return ReviewPriority.HIGH

            # Otherwise MEDIUM priority for media confidence
            return ReviewPriority.MEDIUM

        # LOW: Alta confidence in review queue (should be rare)
        return ReviewPriority.LOW

    def get_pending_reviews(
        self,
        masterplan_id: Optional[UUID] = None,
        priority: Optional[ReviewPriority] = None,
        limit: int = 100
    ) -> List[ReviewItem]:
        """
        Get pending review items with optional filters

        Args:
            masterplan_id: Filter by masterplan (optional)
            priority: Filter by priority (optional)
            limit: Maximum number of items to return

        Returns:
            List of pending ReviewItems, sorted by priority and SLA deadline
        """
        # Filter pending items
        pending = [
            item for item in self._queue.values()
            if item.status == ReviewStatus.PENDING
        ]

        # Apply filters
        if masterplan_id:
            pending = [item for item in pending if item.masterplan_id == masterplan_id]

        if priority:
            pending = [item for item in pending if item.priority == priority]

        # Sort by priority (critical first) and SLA deadline (soonest first)
        priority_order = {
            ReviewPriority.CRITICAL: 0,
            ReviewPriority.HIGH: 1,
            ReviewPriority.MEDIUM: 2,
            ReviewPriority.LOW: 3
        }

        pending.sort(
            key=lambda x: (
                priority_order[x.priority],
                x.sla_deadline if x.sla_deadline else datetime.max
            )
        )

        return pending[:limit]

    def get_review_item(self, atom_id: UUID) -> Optional[ReviewItem]:
        """
        Get review item by atom ID

        Args:
            atom_id: Atom UUID

        Returns:
            ReviewItem or None if not found
        """
        return self._queue.get(atom_id)

    def update_status(
        self,
        atom_id: UUID,
        status: ReviewStatus,
        assigned_to: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[ReviewItem]:
        """
        Update review item status

        Args:
            atom_id: Atom UUID
            status: New review status
            assigned_to: Reviewer username (optional)
            notes: Review notes (optional)

        Returns:
            Updated ReviewItem or None if not found
        """
        item = self._queue.get(atom_id)
        if not item:
            logger.warning(f"Review item not found: {atom_id}")
            return None

        # Update status
        old_status = item.status
        item.status = status

        # Update assigned_to if provided
        if assigned_to:
            item.assigned_to = assigned_to

        # Update notes if provided
        if notes:
            item.notes = notes

        # Set reviewed_at timestamp for completed statuses
        if status in [ReviewStatus.APPROVED, ReviewStatus.REJECTED, ReviewStatus.COMPLETED]:
            item.reviewed_at = datetime.utcnow()

        logger.info(
            f"Review item {atom_id} status updated: "
            f"{old_status.value} → {status.value}"
        )

        return item

    def remove_from_queue(self, atom_id: UUID) -> bool:
        """
        Remove item from review queue

        Args:
            atom_id: Atom UUID

        Returns:
            True if removed, False if not found
        """
        if atom_id in self._queue:
            del self._queue[atom_id]
            logger.info(f"Removed atom {atom_id} from review queue")
            return True

        logger.warning(f"Cannot remove - atom {atom_id} not in queue")
        return False

    def get_sla_violations(
        self,
        masterplan_id: Optional[UUID] = None
    ) -> List[ReviewItem]:
        """
        Get items that have violated SLA deadline

        Args:
            masterplan_id: Filter by masterplan (optional)

        Returns:
            List of ReviewItems with violated SLAs
        """
        items = self._queue.values()

        if masterplan_id:
            items = [item for item in items if item.masterplan_id == masterplan_id]

        violations = [item for item in items if item.is_sla_violated()]

        logger.info(f"Found {len(violations)} SLA violations")

        return violations

    def get_statistics(
        self,
        masterplan_id: Optional[UUID] = None
    ) -> QueueStatistics:
        """
        Get queue statistics

        Args:
            masterplan_id: Filter by masterplan (optional)

        Returns:
            QueueStatistics with metrics
        """
        items = list(self._queue.values())

        if masterplan_id:
            items = [item for item in items if item.masterplan_id == masterplan_id]

        # Count by status
        total = len(items)
        pending = len([i for i in items if i.status == ReviewStatus.PENDING])
        in_review = len([i for i in items if i.status == ReviewStatus.IN_REVIEW])
        approved = len([i for i in items if i.status == ReviewStatus.APPROVED])
        rejected = len([i for i in items if i.status == ReviewStatus.REJECTED])
        completed = len([i for i in items if i.status == ReviewStatus.COMPLETED])

        # Calculate average review time
        reviewed_items = [
            i for i in items
            if i.reviewed_at and i.status in [ReviewStatus.APPROVED, ReviewStatus.REJECTED, ReviewStatus.COMPLETED]
        ]

        if reviewed_items:
            avg_review_time_seconds = sum(
                (i.reviewed_at - i.created_at).total_seconds()
                for i in reviewed_items
            ) / len(reviewed_items)
            avg_review_time_hours = avg_review_time_seconds / 3600
        else:
            avg_review_time_hours = 0.0

        # Calculate SLA violation rate
        if items:
            violations = len([i for i in items if i.is_sla_violated()])
            sla_violation_rate = violations / total
        else:
            sla_violation_rate = 0.0

        # Calculate correction rate (rejected / total reviewed)
        total_reviewed = approved + rejected
        correction_rate = rejected / total_reviewed if total_reviewed > 0 else 0.0

        # Count by priority
        by_priority = {
            ReviewPriority.CRITICAL.value: len([i for i in items if i.priority == ReviewPriority.CRITICAL]),
            ReviewPriority.HIGH.value: len([i for i in items if i.priority == ReviewPriority.HIGH]),
            ReviewPriority.MEDIUM.value: len([i for i in items if i.priority == ReviewPriority.MEDIUM]),
            ReviewPriority.LOW.value: len([i for i in items if i.priority == ReviewPriority.LOW])
        }

        # Count by confidence level
        by_confidence_level = {
            ConfidenceLevel.BAJA.value: len([
                i for i in items if i.confidence_score.level == ConfidenceLevel.BAJA
            ]),
            ConfidenceLevel.MEDIA.value: len([
                i for i in items if i.confidence_score.level == ConfidenceLevel.MEDIA
            ]),
            ConfidenceLevel.ALTA.value: len([
                i for i in items if i.confidence_score.level == ConfidenceLevel.ALTA
            ]),
            ConfidenceLevel.MUY_ALTA.value: len([
                i for i in items if i.confidence_score.level == ConfidenceLevel.MUY_ALTA
            ])
        }

        return QueueStatistics(
            total_items=total,
            pending_count=pending,
            in_review_count=in_review,
            approved_count=approved,
            rejected_count=rejected,
            completed_count=completed,
            avg_review_time_hours=avg_review_time_hours,
            sla_violation_rate=sla_violation_rate,
            correction_rate=correction_rate,
            by_priority=by_priority,
            by_confidence_level=by_confidence_level
        )

    def should_add_to_queue(
        self,
        confidence_score: ConfidenceScore,
        masterplan_atom_count: int,
        current_queue_size: int
    ) -> bool:
        """
        Determine if atom should be added to review queue

        Target: Bottom 15-20% of atoms in queue

        Logic:
        1. Always add baja confidence (<60)
        2. Add media confidence (60-74) if queue < 20% of total atoms
        3. Never add alta (75-89) or muy_alta (≥90)

        Args:
            confidence_score: Calculated confidence score
            masterplan_atom_count: Total atoms in masterplan
            current_queue_size: Current queue size for masterplan

        Returns:
            True if should add to queue
        """
        level = confidence_score.level

        # Always add baja confidence
        if level == ConfidenceLevel.BAJA:
            return True

        # Add media confidence only if within 20% target
        if level == ConfidenceLevel.MEDIA:
            target_queue_size = masterplan_atom_count * 0.20
            return current_queue_size < target_queue_size

        # Never add alta or muy_alta
        return False
