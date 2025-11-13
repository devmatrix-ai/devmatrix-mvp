"""Comment management routes."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from src.db import get_db
from src.models.user import User
from src.schemas.comment import CommentCreate, CommentRead
from src.schemas.base import PaginatedResponse
from src.services.comment_service import CommentService
from src.services.activity_service import ActivityService
from src.security import get_current_user
from src.security.permissions import check_organization_access

router = APIRouter()
comment_service = CommentService()
activity_service = ActivityService()


@router.post("", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
def create_comment(
    comment_in: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new comment."""
    check_organization_access(current_user, comment_in.organization_id)

    comment = comment_service.create(db, obj_in=comment_in, organization_id=comment_in.organization_id)

    activity_service.log_activity(
        db,
        organization_id=comment_in.organization_id,
        user_id=current_user.id,
        entity_type=comment_in.entity_type,
        entity_id=comment_in.entity_id,
        action="commented",
        after_state={"content": comment.content[:100]},
    )

    return comment


@router.get("/entity/{entity_type}/{entity_id}", response_model=PaginatedResponse[CommentRead])
def get_entity_comments(
    entity_type: str,
    entity_id: str,
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get all comments for an entity."""
    comments, total = comment_service.get_entity_comments(
        db,
        organization_id=current_user.organization_id,
        entity_type=entity_type,
        entity_id=entity_id,
        skip=skip,
        limit=limit,
    )

    return {
        "items": comments,
        "total": total,
        "page": skip // limit + 1,
        "page_size": limit,
        "total_pages": (total + limit - 1) // limit,
    }


@router.get("/{comment_id}", response_model=CommentRead)
def get_comment(
    comment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific comment."""
    comment = comment_service.read(db, id=comment_id, organization_id=current_user.organization_id)
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    return comment


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    comment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a comment."""
    comment = comment_service.read(db, id=comment_id, organization_id=current_user.organization_id)
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    if comment.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this comment",
        )

    result = comment_service.delete(db, id=comment_id, organization_id=current_user.organization_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
