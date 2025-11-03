"""
ReviewService - Human review orchestration

Orchestrates the human review workflow:
- Create review entries
- Manage review queue
- Handle review actions (approve, reject, edit, regenerate)
- Track review history

Author: DevMatrix Team
Date: 2025-10-24
"""

from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from ..models import HumanReviewQueue, AtomicUnit, AtomRetryHistory
from ..review.confidence_scorer import ConfidenceScorer, ConfidenceScore
from ..review.queue_manager import ReviewQueueManager
from ..review.ai_assistant import AIAssistant
from src.observability import get_logger

logger = get_logger("review_service")


class ReviewService:
    """
    Complete human review service orchestration.

    Workflow:
    1. Calculate confidence scores
    2. Add low-confidence atoms to queue
    3. Provide AI assistance for review
    4. Handle review actions (approve/reject/edit/regenerate)
    5. Track review history
    """

    def __init__(self, db: Session):
        self.db = db
        self.scorer = ConfidenceScorer(db)
        self.queue_manager = ReviewQueueManager(db)
        self.ai_assistant = AIAssistant()
        
        # Initialize RAG feedback service for auto-indexing approved atoms
        try:
            from src.rag import create_embedding_model, create_vector_store, create_feedback_service
            embedding_model = create_embedding_model()
            self.vector_store = create_vector_store(embedding_model)
            self.feedback_service = create_feedback_service(self.vector_store)
            logger.info("RAG feedback service initialized in ReviewService")
        except Exception as e:
            logger.warning(f"Failed to initialize RAG feedback service: {e}")
            self.vector_store = None
            self.feedback_service = None

    def create_review(
        self,
        atom_id: str,
        auto_add_suggestions: bool = True
    ) -> HumanReviewQueue:
        """
        Create a review entry for an atom.

        Args:
            atom_id: Atom ID to review
            auto_add_suggestions: Automatically add AI suggestions

        Returns:
            Created HumanReviewQueue record
        """
        # Load atom
        atom = self.db.query(AtomicUnit).filter(
            AtomicUnit.atom_id == atom_id
        ).first()

        if not atom:
            raise ValueError(f"Atom {atom_id} not found")

        # Calculate confidence
        confidence = self.scorer.calculate_confidence(atom_id)

        # Add to queue
        review = self.queue_manager.add_to_queue(
            atom_id=atom_id,
            confidence_score=confidence.overall_score
        )

        # Add AI suggestions if requested
        if auto_add_suggestions:
            analysis = self.ai_assistant.analyze_atom_for_review(atom)
            review.ai_suggestions = analysis
            self.db.commit()

        return review

    def get_review_queue(
        self,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Get review queue with atom details and AI analysis.

        Args:
            status: Filter by status
            assigned_to: Filter by assigned user
            limit: Maximum results

        Returns:
            List of review items with full details
        """
        reviews = self.queue_manager.get_queue(status, assigned_to, limit)

        results = []
        for review in reviews:
            # Load atom
            atom = self.db.query(AtomicUnit).filter(
                AtomicUnit.atom_id == review.atom_id
            ).first()

            if not atom:
                continue

            # Get AI analysis if not cached
            if not review.ai_suggestions:
                analysis = self.ai_assistant.analyze_atom_for_review(atom)
                review.ai_suggestions = analysis
                self.db.commit()
            else:
                analysis = review.ai_suggestions

            results.append({
                "review_id": review.review_id,
                "atom_id": review.atom_id,
                "atom": {
                    "description": atom.description,
                    "code": atom.code_to_generate,
                    "language": atom.language,
                    "file_path": atom.file_path,
                    "complexity": atom.complexity,
                    "status": atom.status,
                },
                "confidence_score": review.confidence_score,
                "priority": review.priority,
                "status": review.status,
                "assigned_to": review.assigned_to,
                "ai_analysis": analysis,
                "reviewer_feedback": review.reviewer_feedback,
                "created_at": review.created_at,
                "updated_at": review.updated_at,
            })

        return results

    def assign_review(
        self,
        review_id: str,
        user_id: str
    ) -> HumanReviewQueue:
        """
        Assign a review to a user.

        Args:
            review_id: Review ID
            user_id: User ID to assign

        Returns:
            Updated HumanReviewQueue record
        """
        return self.queue_manager.assign_reviewer(review_id, user_id)

    def approve_atom(
        self,
        review_id: str,
        reviewer_id: str,
        feedback: Optional[str] = None
    ) -> Dict:
        """
        Approve an atom.

        Args:
            review_id: Review ID
            reviewer_id: User ID approving
            feedback: Optional approval feedback

        Returns:
            Result dictionary
        """
        # Get review
        review = self.db.query(HumanReviewQueue).filter(
            HumanReviewQueue.review_id == review_id
        ).first()

        if not review:
            raise ValueError(f"Review {review_id} not found")

        # Update atom status
        atom = self.db.query(AtomicUnit).filter(
            AtomicUnit.atom_id == review.atom_id
        ).first()

        if atom:
            atom.status = "approved"
            atom.reviewed_by = reviewer_id
            atom.review_timestamp = datetime.utcnow()

        # Update review status
        review.status = "approved"
        review.reviewer_feedback = feedback or "Approved by reviewer"
        review.updated_at = datetime.utcnow()

        self.db.commit()
        
        # Auto-index approved atom code to RAG
        if atom and self.feedback_service:
            try:
                self.feedback_service.record_approval(
                    code=atom.code_to_generate,
                    metadata={
                        "atom_id": str(atom.atom_id),
                        "atom_type": atom.type,
                        "atom_description": atom.description,
                        "atom_language": atom.language,
                        "reviewer_id": reviewer_id,
                        "file_path": atom.file_path,
                        "source": "human_reviewed"
                    },
                    task_description=atom.description,
                    user_id=reviewer_id
                )
                logger.info(f"Approved atom {atom.atom_id} successfully indexed to RAG.")
            except Exception as e:
                logger.warning(f"Failed to index approved atom to RAG: {e}")

        return {
            "success": True,
            "action": "approved",
            "atom_id": review.atom_id,
            "reviewer_id": reviewer_id,
            "message": "Atom approved successfully"
        }

    def reject_atom(
        self,
        review_id: str,
        reviewer_id: str,
        feedback: str
    ) -> Dict:
        """
        Reject an atom with feedback.

        Args:
            review_id: Review ID
            reviewer_id: User ID rejecting
            feedback: Required rejection feedback

        Returns:
            Result dictionary
        """
        if not feedback:
            raise ValueError("Feedback is required for rejection")

        # Get review
        review = self.db.query(HumanReviewQueue).filter(
            HumanReviewQueue.review_id == review_id
        ).first()

        if not review:
            raise ValueError(f"Review {review_id} not found")

        # Update atom status
        atom = self.db.query(AtomicUnit).filter(
            AtomicUnit.atom_id == review.atom_id
        ).first()

        if atom:
            atom.status = "rejected"
            atom.reviewed_by = reviewer_id
            atom.review_timestamp = datetime.utcnow()

        # Update review status
        review.status = "rejected"
        review.reviewer_feedback = feedback
        review.updated_at = datetime.utcnow()

        self.db.commit()

        return {
            "success": True,
            "action": "rejected",
            "atom_id": review.atom_id,
            "reviewer_id": reviewer_id,
            "feedback": feedback,
            "message": "Atom rejected - requires regeneration"
        }

    def edit_atom(
        self,
        review_id: str,
        reviewer_id: str,
        new_code: str,
        feedback: Optional[str] = None
    ) -> Dict:
        """
        Edit atom code manually.

        Args:
            review_id: Review ID
            reviewer_id: User ID editing
            new_code: New code content
            feedback: Optional edit notes

        Returns:
            Result dictionary
        """
        # Get review
        review = self.db.query(HumanReviewQueue).filter(
            HumanReviewQueue.review_id == review_id
        ).first()

        if not review:
            raise ValueError(f"Review {review_id} not found")

        # Get atom
        atom = self.db.query(AtomicUnit).filter(
            AtomicUnit.atom_id == review.atom_id
        ).first()

        if not atom:
            raise ValueError(f"Atom {review.atom_id} not found")

        # Store original code (could be used for history/audit)
        original_code = atom.code_to_generate

        # Update atom with new code
        atom.code_to_generate = new_code
        atom.status = "edited"
        atom.reviewed_by = reviewer_id
        atom.review_timestamp = datetime.utcnow()

        # Update review
        review.status = "approved"  # Edited = approved with changes
        review.reviewer_feedback = feedback or f"Manually edited by {reviewer_id}"
        review.updated_at = datetime.utcnow()

        self.db.commit()

        return {
            "success": True,
            "action": "edited",
            "atom_id": review.atom_id,
            "reviewer_id": reviewer_id,
            "original_code": original_code,
            "new_code": new_code,
            "message": "Atom code updated successfully"
        }

    def regenerate_atom(
        self,
        review_id: str,
        reviewer_id: str,
        feedback: str
    ) -> Dict:
        """
        Request atom regeneration with feedback.

        Args:
            review_id: Review ID
            reviewer_id: User ID requesting regeneration
            feedback: Regeneration instructions

        Returns:
            Result dictionary
        """
        if not feedback:
            raise ValueError("Feedback is required for regeneration")

        # Get review
        review = self.db.query(HumanReviewQueue).filter(
            HumanReviewQueue.review_id == review_id
        ).first()

        if not review:
            raise ValueError(f"Review {review_id} not found")

        # Get atom
        atom = self.db.query(AtomicUnit).filter(
            AtomicUnit.atom_id == review.atom_id
        ).first()

        if not atom:
            raise ValueError(f"Atom {review.atom_id} not found")

        # Mark atom for regeneration
        atom.status = "pending_regeneration"
        atom.reviewed_by = reviewer_id
        atom.review_timestamp = datetime.utcnow()

        # Add to retry history with feedback
        retry = AtomRetryHistory(
            atom_id=atom.atom_id,
            attempt_number=self._get_next_attempt_number(atom.atom_id),
            error_category="human_review",
            error_message="Human reviewer requested regeneration",
            temperature_used=0.7,
            retry_prompt=feedback,
            outcome="pending",
            created_at=datetime.utcnow()
        )
        self.db.add(retry)

        # Update review
        review.status = "regeneration_requested"
        review.reviewer_feedback = feedback
        review.updated_at = datetime.utcnow()

        self.db.commit()

        return {
            "success": True,
            "action": "regeneration_requested",
            "atom_id": review.atom_id,
            "reviewer_id": reviewer_id,
            "feedback": feedback,
            "message": "Atom marked for regeneration with reviewer feedback"
        }

    def get_review_statistics(
        self,
        masterplan_id: Optional[str] = None
    ) -> Dict:
        """
        Get comprehensive review statistics.

        Args:
            masterplan_id: Optional masterplan filter

        Returns:
            Statistics dictionary
        """
        queue_stats = self.queue_manager.get_review_statistics(masterplan_id)

        # Add additional stats
        if masterplan_id:
            total_atoms = self.db.query(AtomicUnit).filter(
                AtomicUnit.masterplan_id == masterplan_id
            ).count()

            review_percentage = (
                (queue_stats["total"] / total_atoms * 100)
                if total_atoms > 0 else 0.0
            )
        else:
            total_atoms = self.db.query(AtomicUnit).count()
            review_percentage = (
                (queue_stats["total"] / total_atoms * 100)
                if total_atoms > 0 else 0.0
            )

        return {
            **queue_stats,
            "total_atoms": total_atoms,
            "review_percentage": review_percentage,
            "approval_rate": (
                (queue_stats["approved"] / queue_stats["total"] * 100)
                if queue_stats["total"] > 0 else 0.0
            ),
            "rejection_rate": (
                (queue_stats["rejected"] / queue_stats["total"] * 100)
                if queue_stats["total"] > 0 else 0.0
            )
        }

    def _get_next_attempt_number(self, atom_id: str) -> int:
        """Get next attempt number for atom retries"""
        max_attempt = self.db.query(AtomRetryHistory).filter(
            AtomRetryHistory.atom_id == atom_id
        ).count()

        return max_attempt + 1
