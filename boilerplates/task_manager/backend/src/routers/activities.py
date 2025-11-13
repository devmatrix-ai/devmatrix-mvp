"""Activity log routes for audit trails."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from src.db import get_db
from src.models.user import User
from src.schemas.activity import ActivityLogRead
from src.schemas.base import PaginatedResponse
from src.services.activity_service import ActivityService
from src.security import get_current_user

router = APIRouter()
activity_service = ActivityService()


@router.get("/entity/{entity_type}/{entity_id}", response_model=PaginatedResponse[ActivityLogRead])
def get_entity_activity(
    entity_type: str,
    entity_id: str,
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get activity log for an entity."""
    activities, total = activity_service.get_entity_activity(
        db,
        organization_id=current_user.organization_id,
        entity_type=entity_type,
        entity_id=entity_id,
        skip=skip,
        limit=limit,
    )

    return {
        "items": activities,
        "total": total,
        "page": skip // limit + 1,
        "page_size": limit,
        "total_pages": (total + limit - 1) // limit,
    }


@router.get("/user/{user_id}", response_model=PaginatedResponse[ActivityLogRead])
def get_user_activity(
    user_id: str,
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get activity log for a user."""
    if user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user's activity",
        )

    activities, total = activity_service.get_user_activity(
        db,
        organization_id=current_user.organization_id,
        user_id=user_id,
        skip=skip,
        limit=limit,
    )

    return {
        "items": activities,
        "total": total,
        "page": skip // limit + 1,
        "page_size": limit,
        "total_pages": (total + limit - 1) // limit,
    }
