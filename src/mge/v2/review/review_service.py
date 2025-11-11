"""
ReviewService - Orchestrate human review workflows

Coordinates review operations for low-confidence atoms:
- Approve: Accept code and continue execution
- Reject: Reject code with feedback, mark for correction
- Edit: Apply manual code changes
- Regenerate: Retry generation with reviewer feedback

Integrates:
- ConfidenceScorer: Recalculate confidence after changes
- ReviewQueueManager: Queue management operations
- AIAssistant: Fix suggestions for rejected atoms
- Execution pipeline: Regenerate atom code
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.atomic_unit import AtomicUnit
from src.mge.v2.review.confidence_scorer import ConfidenceScorer, ConfidenceScore
from src.mge.v2.review.review_queue_manager import (
    ReviewQueueManager,
    ReviewItem,
    ReviewStatus
)
from src.mge.v2.review.ai_assistant import AIAssistant, CodeIssue, FixSuggestion

logger = logging.getLogger(__name__)


@dataclass
class ReviewDecision:
    """Review decision with metadata"""

    atom_id: UUID
    decision: str  # "approve", "reject", "edit", "regenerate"
    reviewer: str
    feedback: Optional[str] = None
    code_changes: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            "atom_id": str(self.atom_id),
            "decision": self.decision,
            "reviewer": self.reviewer,
            "feedback": self.feedback,
            "code_changes": self.code_changes,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ReviewResult:
    """Result of review workflow"""

    success: bool
    message: str
    updated_atom: Optional[AtomicUnit] = None
    new_confidence_score: Optional[ConfidenceScore] = None
    ai_suggestions: Optional[List[FixSuggestion]] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for API response"""
        return {
            "success": self.success,
            "message": self.message,
            "updated_atom_id": str(self.updated_atom.id) if self.updated_atom else None,
            "new_confidence_score": self.new_confidence_score.to_dict() if self.new_confidence_score else None,
            "ai_suggestions": [s.to_dict() for s in self.ai_suggestions] if self.ai_suggestions else []
        }


class ReviewService:
    """
    Orchestrate human review workflows

    Provides complete review cycle management with 4 primary workflows:
    1. Approve - Accept code and continue
    2. Reject - Reject with feedback and AI suggestions
    3. Edit - Apply manual code changes
    4. Regenerate - Retry generation with feedback

    Example:
        service = ReviewService(db_session)

        # Approve atom
        result = await service.approve(atom_id, reviewer="alice")

        # Reject with feedback
        result = await service.reject(
            atom_id,
            reviewer="bob",
            feedback="Logic error in validation"
        )

        # Edit code manually
        result = await service.edit(
            atom_id,
            reviewer="alice",
            new_code="fixed implementation"
        )

        # Regenerate with feedback
        result = await service.regenerate(
            atom_id,
            reviewer="bob",
            feedback="Add error handling"
        )
    """

    def __init__(self, db: Session):
        """
        Initialize ReviewService

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.queue_manager = ReviewQueueManager(db)
        self.confidence_scorer = ConfidenceScorer()
        self.ai_assistant = AIAssistant()

    async def approve(
        self,
        atom_id: UUID,
        reviewer: str,
        notes: Optional[str] = None
    ) -> ReviewResult:
        """
        Approve atom - accept code and continue execution

        Workflow:
        1. Update review status to APPROVED
        2. Remove from review queue
        3. Mark atom as approved in database
        4. Continue execution pipeline

        Args:
            atom_id: Atom UUID
            reviewer: Reviewer username
            notes: Optional approval notes

        Returns:
            ReviewResult with success status
        """
        try:
            # Get atom from database
            atom = self.db.query(AtomicUnit).filter(AtomicUnit.atom_id == atom_id).first()
            if not atom:
                return ReviewResult(
                    success=False,
                    message=f"Atom {atom_id} not found"
                )

            # Update review queue status
            review_item = self.queue_manager.update_status(
                atom_id=atom_id,
                status=ReviewStatus.APPROVED,
                assigned_to=reviewer,
                notes=notes
            )

            if not review_item:
                return ReviewResult(
                    success=False,
                    message=f"Review item {atom_id} not found in queue"
                )

            # Mark atom as approved
            atom.review_status = "approved"
            atom.reviewed_by = reviewer
            atom.reviewed_at = datetime.utcnow()

            self.db.commit()

            # Remove from queue (review complete)
            self.queue_manager.remove_from_queue(atom_id)

            logger.info(
                f"Atom {atom_id} approved by {reviewer}"
            )

            return ReviewResult(
                success=True,
                message=f"Atom {atom_id} approved successfully",
                updated_atom=atom
            )

        except Exception as e:
            logger.error(f"Error approving atom {atom_id}: {e}")
            self.db.rollback()
            return ReviewResult(
                success=False,
                message=f"Error approving atom: {str(e)}"
            )

    async def reject(
        self,
        atom_id: UUID,
        reviewer: str,
        feedback: str,
        provide_suggestions: bool = True
    ) -> ReviewResult:
        """
        Reject atom - mark for correction with feedback and AI suggestions

        Workflow:
        1. Update review status to REJECTED
        2. Store rejection feedback
        3. Generate AI fix suggestions
        4. Keep in queue for re-review after correction

        Args:
            atom_id: Atom UUID
            reviewer: Reviewer username
            feedback: Rejection reason and feedback
            provide_suggestions: Generate AI fix suggestions (default: True)

        Returns:
            ReviewResult with AI suggestions
        """
        try:
            # Get atom from database
            atom = self.db.query(AtomicUnit).filter(AtomicUnit.atom_id == atom_id).first()
            if not atom:
                return ReviewResult(
                    success=False,
                    message=f"Atom {atom_id} not found"
                )

            # Update review queue status
            review_item = self.queue_manager.update_status(
                atom_id=atom_id,
                status=ReviewStatus.REJECTED,
                assigned_to=reviewer,
                notes=feedback
            )

            if not review_item:
                return ReviewResult(
                    success=False,
                    message=f"Review item {atom_id} not found in queue"
                )

            # Mark atom as rejected
            atom.review_status = "rejected"
            atom.reviewed_by = reviewer
            atom.reviewed_at = datetime.utcnow()
            atom.review_feedback = feedback

            self.db.commit()

            # Generate AI suggestions if requested
            ai_suggestions = []
            if provide_suggestions and atom.code:
                # Analyze code and generate suggestions
                validation_results = self._get_validation_results(atom)
                issues = self.ai_assistant.analyze_validation_errors(
                    validation_results=validation_results,
                    code=atom.code
                )

                for issue in issues:
                    suggestion = self.ai_assistant.suggest_fix(issue, atom.code)
                    ai_suggestions.append(suggestion)

            logger.info(
                f"Atom {atom_id} rejected by {reviewer}: {feedback}"
            )

            return ReviewResult(
                success=True,
                message=f"Atom {atom_id} rejected - {len(ai_suggestions)} AI suggestions provided",
                updated_atom=atom,
                ai_suggestions=ai_suggestions
            )

        except Exception as e:
            logger.error(f"Error rejecting atom {atom_id}: {e}")
            self.db.rollback()
            return ReviewResult(
                success=False,
                message=f"Error rejecting atom: {str(e)}"
            )

    async def edit(
        self,
        atom_id: UUID,
        reviewer: str,
        new_code: str,
        edit_notes: Optional[str] = None
    ) -> ReviewResult:
        """
        Edit atom - apply manual code changes

        Workflow:
        1. Update atom code with manual changes
        2. Re-run validation on new code
        3. Recalculate confidence score
        4. Update review status based on new confidence

        Args:
            atom_id: Atom UUID
            reviewer: Reviewer username
            new_code: Manually edited code
            edit_notes: Optional notes about changes

        Returns:
            ReviewResult with new confidence score
        """
        try:
            # Get atom from database
            atom = self.db.query(AtomicUnit).filter(AtomicUnit.atom_id == atom_id).first()
            if not atom:
                return ReviewResult(
                    success=False,
                    message=f"Atom {atom_id} not found"
                )

            # Store original code for rollback if needed
            original_code = atom.code

            # Update code
            atom.code = new_code
            atom.edited_by = reviewer
            atom.edited_at = datetime.utcnow()
            atom.edit_notes = edit_notes

            # Re-run validation (simplified - should call actual validation service)
            validation_results = self._validate_code(new_code)

            # Recalculate confidence score
            new_confidence = self.confidence_scorer.calculate_score(
                atom_id=atom_id,
                validation_results=validation_results,
                retry_count=atom.retry_count,
                complexity_metrics=self._get_complexity_metrics(new_code),
                test_results=None  # Tests not re-run yet
            )

            # Update review status based on new confidence
            if self.confidence_scorer.should_enter_review_queue(new_confidence):
                # Still needs review
                review_status = ReviewStatus.IN_REVIEW
            else:
                # High enough confidence to approve
                review_status = ReviewStatus.APPROVED
                atom.review_status = "approved"
                self.queue_manager.remove_from_queue(atom_id)

            self.queue_manager.update_status(
                atom_id=atom_id,
                status=review_status,
                assigned_to=reviewer,
                notes=edit_notes
            )

            self.db.commit()

            logger.info(
                f"Atom {atom_id} edited by {reviewer} - "
                f"new confidence: {new_confidence.total_score:.2f}"
            )

            return ReviewResult(
                success=True,
                message=f"Atom {atom_id} edited successfully - "
                        f"new confidence: {new_confidence.total_score:.2f} ({new_confidence.level.value})",
                updated_atom=atom,
                new_confidence_score=new_confidence
            )

        except Exception as e:
            logger.error(f"Error editing atom {atom_id}: {e}")
            self.db.rollback()
            return ReviewResult(
                success=False,
                message=f"Error editing atom: {str(e)}"
            )

    async def regenerate(
        self,
        atom_id: UUID,
        reviewer: str,
        feedback: str,
        max_retries: int = 3
    ) -> ReviewResult:
        """
        Regenerate atom - retry code generation with reviewer feedback

        Workflow:
        1. Add reviewer feedback to generation context
        2. Increment retry counter
        3. Trigger atom regeneration with enhanced prompt
        4. Re-run validation and recalculate confidence
        5. Update review queue status

        Args:
            atom_id: Atom UUID
            reviewer: Reviewer username
            feedback: Feedback to guide regeneration
            max_retries: Maximum regeneration attempts

        Returns:
            ReviewResult with regenerated code and confidence
        """
        try:
            # Get atom from database
            atom = self.db.query(AtomicUnit).filter(AtomicUnit.atom_id == atom_id).first()
            if not atom:
                return ReviewResult(
                    success=False,
                    message=f"Atom {atom_id} not found"
                )

            # Check retry limit
            if atom.retry_count >= max_retries:
                return ReviewResult(
                    success=False,
                    message=f"Maximum retries ({max_retries}) exceeded"
                )

            # Store feedback for regeneration context
            atom.review_feedback = feedback
            atom.retry_count += 1

            # Generate AI suggestions to enhance regeneration prompt
            validation_results = self._get_validation_results(atom)
            issues = self.ai_assistant.analyze_validation_errors(
                validation_results=validation_results,
                code=atom.code or ""
            )

            ai_suggestions = [
                self.ai_assistant.suggest_fix(issue, atom.code or "")
                for issue in issues
            ]

            # Build enhanced prompt with feedback and suggestions
            enhanced_prompt = self._build_regeneration_prompt(
                atom=atom,
                feedback=feedback,
                ai_suggestions=ai_suggestions
            )

            # Trigger regeneration (simplified - should call actual execution service)
            # For now, just mark for regeneration
            atom.status = "pending_regeneration"
            atom.regeneration_prompt = enhanced_prompt
            atom.regenerated_by = reviewer
            atom.regenerated_at = datetime.utcnow()

            # Update review queue
            self.queue_manager.update_status(
                atom_id=atom_id,
                status=ReviewStatus.IN_REVIEW,
                assigned_to=reviewer,
                notes=f"Regeneration requested (retry #{atom.retry_count}): {feedback}"
            )

            self.db.commit()

            logger.info(
                f"Atom {atom_id} marked for regeneration by {reviewer} "
                f"(retry #{atom.retry_count})"
            )

            return ReviewResult(
                success=True,
                message=f"Atom {atom_id} queued for regeneration (retry #{atom.retry_count})",
                updated_atom=atom,
                ai_suggestions=ai_suggestions
            )

        except Exception as e:
            logger.error(f"Error regenerating atom {atom_id}: {e}")
            self.db.rollback()
            return ReviewResult(
                success=False,
                message=f"Error regenerating atom: {str(e)}"
            )

    def _get_validation_results(self, atom: AtomicUnit) -> Dict:
        """
        Get validation results for atom

        Simplified stub - should integrate with actual validation service

        Args:
            atom: AtomicUnit instance

        Returns:
            Validation results dictionary
        """
        # Stub implementation
        return {
            "l1_syntax": {"error": None} if atom.validation_l1 else {"error": "Syntax error"},
            "l2_imports": {"error": None} if atom.validation_l2 else {"error": "Import error"},
            "l3_types": {"errors": []} if atom.validation_l3 else {"errors": [{"message": "Type error", "line": 1}]},
            "l4_complexity": {"cyclomatic_complexity": 10, "cognitive_complexity": 15}
        }

    def _validate_code(self, code: str) -> Dict:
        """
        Validate code

        Simplified stub - should call actual validation service

        Args:
            code: Source code to validate

        Returns:
            Validation results dictionary
        """
        # Stub implementation - always pass for now
        return {
            "l1_syntax": {"error": None},
            "l2_imports": {"error": None},
            "l3_types": {"errors": []},
            "l4_complexity": {"cyclomatic_complexity": 10, "cognitive_complexity": 15}
        }

    def _get_complexity_metrics(self, code: str) -> Dict:
        """
        Calculate complexity metrics

        Simplified stub - should call actual complexity analyzer

        Args:
            code: Source code

        Returns:
            Complexity metrics dictionary
        """
        # Stub implementation
        return {
            "cyclomatic_complexity": 10,
            "cognitive_complexity": 15,
            "lines_of_code": len(code.split("\n"))
        }

    def _build_regeneration_prompt(
        self,
        atom: AtomicUnit,
        feedback: str,
        ai_suggestions: List[FixSuggestion]
    ) -> str:
        """
        Build enhanced prompt for regeneration

        Args:
            atom: AtomicUnit instance
            feedback: Reviewer feedback
            ai_suggestions: AI fix suggestions

        Returns:
            Enhanced regeneration prompt
        """
        prompt_parts = [
            f"# Atom Regeneration Request",
            f"",
            f"## Original Task",
            f"{atom.description}",
            f"",
            f"## Reviewer Feedback",
            f"{feedback}",
            f"",
            f"## Issues Detected",
        ]

        for i, suggestion in enumerate(ai_suggestions, 1):
            prompt_parts.extend([
                f"### Issue {i}",
                f"**Fix**: {suggestion.primary_fix}",
                f"**Explanation**: {suggestion.explanation}",
                f"**Alternatives**:",
            ])
            for alt in suggestion.alternatives:
                prompt_parts.append(f"  - {alt}")
            prompt_parts.append("")

        prompt_parts.extend([
            f"## Requirements",
            f"- Address all feedback points",
            f"- Apply suggested fixes where applicable",
            f"- Ensure code passes validation (L1-L4)",
            f"- Maintain code quality and readability",
        ])

        return "\n".join(prompt_parts)
