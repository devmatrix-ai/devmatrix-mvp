"""
ReviewQueueManager - Manage human review queue

Handles review queue operations:
- Adding atoms to review queue
- Prioritizing by confidence score
- Selecting bottom 15-20% for review
- Assigning reviewers
- Tracking review status

Author: DevMatrix Team
Date: 2025-10-24
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..models import HumanReviewQueue, AtomicUnit
from .confidence_scorer import ConfidenceScorer


class ReviewQueueManager:
    """
    Manage the human review queue for low-confidence atoms.

    Features:
    - Automatic prioritization by confidence score
    - Bottom 15-20% selection for review
    - Reviewer assignment
    - Status tracking (pending, in_review, approved, rejected)
    """

    def __init__(self, db: Session):
        self.db = db
        self.scorer = ConfidenceScorer(db)

        # Default percentage of atoms to review
        self.DEFAULT_REVIEW_PERCENTAGE = 0.20  # 20%

    def add_to_queue(
        self,
        atom_id: str,
        confidence_score: float,
        priority: Optional[int] = None
    ) -> HumanReviewQueue:
        """
        Add an atom to the review queue.

        Args:
            atom_id: Atom ID to add to queue
            confidence_score: Confidence score (0.0-1.0)
            priority: Optional manual priority (higher = more important)

        Returns:
            Created HumanReviewQueue record
        """
        # Check if already in queue
        existing = self.db.query(HumanReviewQueue).filter(
            HumanReviewQueue.atom_id == atom_id
        ).first()

        if existing:
            # Update confidence and priority if needed
            existing.confidence_score = confidence_score
            if priority is not None:
                existing.priority = priority
            self.db.commit()
            return existing

        # Calculate priority if not provided
        if priority is None:
            priority = self._calculate_priority(confidence_score)

        # Create new queue entry
        review = HumanReviewQueue(
            atom_id=atom_id,
            confidence_score=confidence_score,
            priority=priority,
            status="pending",
            assigned_to=None,
            ai_suggestions=None,
            reviewer_feedback=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        self.db.add(review)
        self.db.commit()

        return review

    def get_queue(
        self,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[HumanReviewQueue]:
        """
        Get review queue with optional filters.

        Args:
            status: Filter by status (pending, in_review, approved, rejected)
            assigned_to: Filter by assigned user ID
            limit: Maximum number of results

        Returns:
            List of HumanReviewQueue records sorted by priority (highest first)
        """
        query = self.db.query(HumanReviewQueue)

        if status:
            query = query.filter(HumanReviewQueue.status == status)

        if assigned_to:
            query = query.filter(HumanReviewQueue.assigned_to == assigned_to)

        # Sort by priority (highest first), then confidence (lowest first)
        query = query.order_by(
            desc(HumanReviewQueue.priority),
            HumanReviewQueue.confidence_score.asc()
        )

        if limit:
            query = query.limit(limit)

        return query.all()

    def prioritize_queue(self) -> int:
        """
        Recalculate priorities for all pending queue items.

        Uses confidence scores to assign priorities.

        Returns:
            Number of items reprioritized
        """
        pending = self.db.query(HumanReviewQueue).filter(
            HumanReviewQueue.status == "pending"
        ).all()

        count = 0
        for review in pending:
            new_priority = self._calculate_priority(review.confidence_score)
            if review.priority != new_priority:
                review.priority = new_priority
                review.updated_at = datetime.utcnow()
                count += 1

        self.db.commit()
        return count

    def select_for_review(
        self,
        masterplan_id: str,
        percentage: float = 0.20
    ) -> List[HumanReviewQueue]:
        """
        Select bottom N% of atoms for review based on confidence.

        Args:
            masterplan_id: MasterPlan ID
            percentage: Percentage of atoms to select (0.0-1.0, default: 0.20)

        Returns:
            List of HumanReviewQueue records for selected atoms
        """
        # Get all atoms for masterplan
        atoms = self.db.query(AtomicUnit).filter(
            AtomicUnit.masterplan_id == masterplan_id
        ).all()

        total_atoms = len(atoms)
        review_count = int(total_atoms * percentage)

        # Calculate confidence scores
        atom_scores = []
        for atom in atoms:
            try:
                score = self.scorer.calculate_confidence(atom.atom_id)
                atom_scores.append((atom, score))
            except Exception as e:
                print(f"Error scoring atom {atom.atom_id}: {e}")
                continue

        # Sort by confidence (lowest first)
        atom_scores.sort(key=lambda x: x[1].overall_score)

        # Select bottom N%
        selected = atom_scores[:review_count]

        # Add to queue
        queue_items = []
        for atom, score in selected:
            review = self.add_to_queue(
                atom_id=atom.atom_id,
                confidence_score=score.overall_score
            )
            queue_items.append(review)

        return queue_items

    def assign_reviewer(
        self,
        review_id: str,
        user_id: str
    ) -> HumanReviewQueue:
        """
        Assign a reviewer to a queue item.

        Args:
            review_id: Review queue ID
            user_id: User ID to assign

        Returns:
            Updated HumanReviewQueue record
        """
        review = self.db.query(HumanReviewQueue).filter(
            HumanReviewQueue.review_id == review_id
        ).first()

        if not review:
            raise ValueError(f"Review {review_id} not found")

        review.assigned_to = user_id
        review.status = "in_review"
        review.updated_at = datetime.utcnow()

        self.db.commit()

        return review

    def update_review_status(
        self,
        review_id: str,
        status: str,
        feedback: Optional[str] = None
    ) -> HumanReviewQueue:
        """
        Update review status.

        Args:
            review_id: Review queue ID
            status: New status (pending, in_review, approved, rejected)
            feedback: Optional reviewer feedback

        Returns:
            Updated HumanReviewQueue record
        """
        review = self.db.query(HumanReviewQueue).filter(
            HumanReviewQueue.review_id == review_id
        ).first()

        if not review:
            raise ValueError(f"Review {review_id} not found")

        review.status = status
        review.updated_at = datetime.utcnow()

        if feedback:
            review.reviewer_feedback = feedback

        self.db.commit()

        return review

    def remove_from_queue(self, review_id: str) -> bool:
        """
        Remove an item from the review queue.

        Args:
            review_id: Review queue ID to remove

        Returns:
            True if removed, False if not found
        """
        review = self.db.query(HumanReviewQueue).filter(
            HumanReviewQueue.review_id == review_id
        ).first()

        if not review:
            return False

        self.db.delete(review)
        self.db.commit()

        return True

    def get_review_statistics(self, masterplan_id: Optional[str] = None) -> dict:
        """
        Get review queue statistics.

        Args:
            masterplan_id: Optional masterplan ID filter

        Returns:
            Dictionary with queue statistics
        """
        query = self.db.query(HumanReviewQueue)

        if masterplan_id:
            # Join with AtomicUnit to filter by masterplan
            query = query.join(AtomicUnit).filter(
                AtomicUnit.masterplan_id == masterplan_id
            )

        all_reviews = query.all()

        stats = {
            "total": len(all_reviews),
            "pending": sum(1 for r in all_reviews if r.status == "pending"),
            "in_review": sum(1 for r in all_reviews if r.status == "in_review"),
            "approved": sum(1 for r in all_reviews if r.status == "approved"),
            "rejected": sum(1 for r in all_reviews if r.status == "rejected"),
            "avg_confidence": (
                sum(r.confidence_score for r in all_reviews) / len(all_reviews)
                if all_reviews else 0.0
            ),
            "min_confidence": (
                min(r.confidence_score for r in all_reviews)
                if all_reviews else 0.0
            ),
            "max_confidence": (
                max(r.confidence_score for r in all_reviews)
                if all_reviews else 0.0
            )
        }

        return stats

    def _calculate_priority(self, confidence_score: float) -> int:
        """
        Calculate priority from confidence score.

        Priority levels:
        - Critical (<0.50): 100
        - Low (0.50-0.69): 75
        - Medium (0.70-0.84): 50
        - High (≥0.85): 25

        Args:
            confidence_score: Confidence score (0.0-1.0)

        Returns:
            Priority value (higher = more important)
        """
        if confidence_score < 0.50:
            return 100  # Critical - highest priority
        elif confidence_score < 0.70:
            return 75  # Low confidence
        elif confidence_score < 0.85:
            return 50  # Medium confidence
        else:
            return 25  # High confidence - lowest priority

    def get_next_for_review(self, user_id: Optional[str] = None) -> Optional[HumanReviewQueue]:
        """
        Get the next pending item for review.

        Args:
            user_id: Optional user ID to auto-assign

        Returns:
            Next HumanReviewQueue item or None if queue is empty
        """
        review = self.db.query(HumanReviewQueue).filter(
            HumanReviewQueue.status == "pending"
        ).order_by(
            desc(HumanReviewQueue.priority),
            HumanReviewQueue.confidence_score.asc()
        ).first()

        if review and user_id:
            # Auto-assign to user
            review.assigned_to = user_id
            review.status = "in_review"
            review.updated_at = datetime.utcnow()
            self.db.commit()

        return review
