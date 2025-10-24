"""
Review API Router - Human review endpoints

Provides REST API for human review workflow.

Author: DevMatrix Team
Date: 2025-10-24
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from src.config.database import get_db
from src.services.review_service import ReviewService
from src.models import AtomicUnit


router = APIRouter(
    prefix="/api/v2/review",
    tags=["Review - Human Review System"]
)


# ============================================================================
# Request/Response Models
# ============================================================================

class ReviewQueueFilter(BaseModel):
    """Filter parameters for review queue"""
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    limit: Optional[int] = 50


class ApproveRequest(BaseModel):
    """Approve atom request"""
    reviewer_id: str
    feedback: Optional[str] = None


class RejectRequest(BaseModel):
    """Reject atom request"""
    reviewer_id: str
    feedback: str


class EditRequest(BaseModel):
    """Edit atom request"""
    reviewer_id: str
    new_code: str
    feedback: Optional[str] = None


class RegenerateRequest(BaseModel):
    """Regenerate atom request"""
    reviewer_id: str
    feedback: str


class AssignRequest(BaseModel):
    """Assign review request"""
    user_id: str


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/queue")
async def get_review_queue(
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get review queue with filters.

    Query Parameters:
    - status: Filter by status (pending, in_review, approved, rejected)
    - assigned_to: Filter by assigned user ID
    - limit: Maximum results (default: 50)

    Returns:
    - List of review items with atom details and AI analysis
    """
    try:
        service = ReviewService(db)
        queue = service.get_review_queue(status, assigned_to, limit)

        return {
            "success": True,
            "total": len(queue),
            "queue": queue
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{review_id}")
async def get_review(
    review_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed review information.

    Path Parameters:
    - review_id: Review ID

    Returns:
    - Review details with atom and AI analysis
    """
    try:
        service = ReviewService(db)

        # Get queue with single item
        queue = service.get_review_queue(limit=1)

        # Find matching review
        review = next((r for r in queue if r["review_id"] == review_id), None)

        if not review:
            raise HTTPException(status_code=404, detail="Review not found")

        return {
            "success": True,
            "review": review
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve")
async def approve_atom(
    request: ApproveRequest,
    review_id: str,
    db: Session = Depends(get_db)
):
    """
    Approve an atom.

    Request Body:
    - reviewer_id: User ID approving
    - feedback: Optional approval feedback

    Returns:
    - Success confirmation
    """
    try:
        service = ReviewService(db)
        result = service.approve_atom(
            review_id=review_id,
            reviewer_id=request.reviewer_id,
            feedback=request.feedback
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reject")
async def reject_atom(
    request: RejectRequest,
    review_id: str,
    db: Session = Depends(get_db)
):
    """
    Reject an atom with feedback.

    Request Body:
    - reviewer_id: User ID rejecting
    - feedback: Required rejection feedback

    Returns:
    - Success confirmation with rejection details
    """
    try:
        service = ReviewService(db)
        result = service.reject_atom(
            review_id=review_id,
            reviewer_id=request.reviewer_id,
            feedback=request.feedback
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/edit")
async def edit_atom(
    request: EditRequest,
    review_id: str,
    db: Session = Depends(get_db)
):
    """
    Manually edit atom code.

    Request Body:
    - reviewer_id: User ID editing
    - new_code: New code content
    - feedback: Optional edit notes

    Returns:
    - Success confirmation with code diff
    """
    try:
        service = ReviewService(db)
        result = service.edit_atom(
            review_id=review_id,
            reviewer_id=request.reviewer_id,
            new_code=request.new_code,
            feedback=request.feedback
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/regenerate")
async def regenerate_atom(
    request: RegenerateRequest,
    review_id: str,
    db: Session = Depends(get_db)
):
    """
    Request atom regeneration with feedback.

    Request Body:
    - reviewer_id: User ID requesting regeneration
    - feedback: Regeneration instructions

    Returns:
    - Success confirmation
    """
    try:
        service = ReviewService(db)
        result = service.regenerate_atom(
            review_id=review_id,
            reviewer_id=request.reviewer_id,
            feedback=request.feedback
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assign")
async def assign_review(
    request: AssignRequest,
    review_id: str,
    db: Session = Depends(get_db)
):
    """
    Assign a review to a user.

    Request Body:
    - user_id: User ID to assign

    Returns:
    - Updated review record
    """
    try:
        service = ReviewService(db)
        review = service.assign_review(
            review_id=review_id,
            user_id=request.user_id
        )

        return {
            "success": True,
            "review_id": review.review_id,
            "assigned_to": review.assigned_to,
            "status": review.status,
            "message": f"Review assigned to user {request.user_id}"
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/{masterplan_id}")
async def get_review_statistics(
    masterplan_id: str,
    db: Session = Depends(get_db)
):
    """
    Get review statistics for a masterplan.

    Path Parameters:
    - masterplan_id: MasterPlan ID (or "all" for global stats)

    Returns:
    - Review statistics including approval/rejection rates
    """
    try:
        service = ReviewService(db)

        if masterplan_id == "all":
            stats = service.get_review_statistics()
        else:
            stats = service.get_review_statistics(masterplan_id)

        return {
            "success": True,
            "statistics": stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create/{atom_id}")
async def create_review(
    atom_id: str,
    auto_add_suggestions: bool = True,
    db: Session = Depends(get_db)
):
    """
    Create a review entry for an atom.

    Path Parameters:
    - atom_id: Atom ID to review

    Query Parameters:
    - auto_add_suggestions: Auto-generate AI suggestions (default: true)

    Returns:
    - Created review record
    """
    try:
        service = ReviewService(db)
        review = service.create_review(
            atom_id=atom_id,
            auto_add_suggestions=auto_add_suggestions
        )

        return {
            "success": True,
            "review_id": review.review_id,
            "atom_id": review.atom_id,
            "confidence_score": review.confidence_score,
            "priority": review.priority,
            "status": review.status,
            "ai_suggestions": review.ai_suggestions,
            "message": "Review created successfully"
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk-create/{masterplan_id}")
async def bulk_create_reviews(
    masterplan_id: str,
    percentage: float = 0.20,
    db: Session = Depends(get_db)
):
    """
    Bulk create reviews for bottom N% of atoms.

    Path Parameters:
    - masterplan_id: MasterPlan ID

    Query Parameters:
    - percentage: Percentage of atoms to review (default: 0.20 = 20%)

    Returns:
    - Created review records
    """
    try:
        service = ReviewService(db)

        # Use queue manager to select bottom N%
        reviews = service.queue_manager.select_for_review(
            masterplan_id=masterplan_id,
            percentage=percentage
        )

        # Add AI suggestions for each
        for review in reviews:
            if not review.ai_suggestions:
                atom = db.query(AtomicUnit).filter(
                    AtomicUnit.atom_id == review.atom_id
                ).first()

                if atom:
                    analysis = service.ai_assistant.analyze_atom_for_review(atom)
                    review.ai_suggestions = analysis

        db.commit()

        return {
            "success": True,
            "total_created": len(reviews),
            "percentage": percentage,
            "masterplan_id": masterplan_id,
            "reviews": [
                {
                    "review_id": r.review_id,
                    "atom_id": r.atom_id,
                    "confidence_score": r.confidence_score,
                    "priority": r.priority
                }
                for r in reviews
            ],
            "message": f"Created {len(reviews)} review entries (bottom {percentage*100}%)"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
