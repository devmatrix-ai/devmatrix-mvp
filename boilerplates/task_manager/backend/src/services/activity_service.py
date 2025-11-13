"""Activity service for logging entity changes."""

import json
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional, Tuple, Dict, Any

from src.models.activity import ActivityLog


class ActivityService:
    """Service for activity logging and audit trails."""

    @staticmethod
    def log_activity(
        db: Session,
        *,
        organization_id: str,
        user_id: str,
        entity_type: str,
        entity_id: str,
        action: str,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
    ) -> ActivityLog:
        """Log an activity/change."""
        activity = ActivityLog(
            id=str(uuid4()),
            organization_id=organization_id,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            before_state=json.dumps(before_state) if before_state else None,
            after_state=json.dumps(after_state) if after_state else None,
        )
        db.add(activity)
        db.commit()
        db.refresh(activity)
        return activity

    @staticmethod
    def get_entity_activity(
        db: Session,
        *,
        organization_id: str,
        entity_type: str,
        entity_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[ActivityLog], int]:
        """Get activity log for an entity."""
        query = db.query(ActivityLog).filter(
            and_(
                ActivityLog.organization_id == organization_id,
                ActivityLog.entity_type == entity_type,
                ActivityLog.entity_id == entity_id,
            )
        ).order_by(ActivityLog.created_at.desc())

        total = query.count()
        activities = query.offset(skip).limit(limit).all()
        return activities, total

    @staticmethod
    def get_user_activity(
        db: Session,
        *,
        organization_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[ActivityLog], int]:
        """Get activity log for a user."""
        query = db.query(ActivityLog).filter(
            and_(
                ActivityLog.organization_id == organization_id,
                ActivityLog.user_id == user_id,
            )
        ).order_by(ActivityLog.created_at.desc())

        total = query.count()
        activities = query.offset(skip).limit(limit).all()
        return activities, total
