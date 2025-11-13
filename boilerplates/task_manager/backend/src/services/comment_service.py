"""Comment service for entity discussions."""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional, Tuple

from src.models.comment import Comment
from src.schemas.comment import CommentCreate, CommentCreate as CommentUpdate
from .base_crud import BaseCRUDService


class CommentService(BaseCRUDService[Comment, CommentCreate, CommentUpdate]):
    """Service for comment operations."""

    def __init__(self):
        super().__init__(Comment)

    def get_entity_comments(
        self,
        db: Session,
        *,
        organization_id: str,
        entity_type: str,
        entity_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Comment], int]:
        """Get all comments for an entity."""
        query = db.query(Comment).filter(
            and_(
                Comment.organization_id == organization_id,
                Comment.entity_type == entity_type,
                Comment.entity_id == entity_id,
                Comment.is_deleted == False,
            )
        ).order_by(Comment.created_at.asc())

        total = query.count()
        comments = query.offset(skip).limit(limit).all()
        return comments, total

    def get_threaded_comments(
        self,
        db: Session,
        *,
        organization_id: str,
        entity_type: str,
        entity_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Comment], int]:
        """Get threaded comments (root comments only)."""
        query = db.query(Comment).filter(
            and_(
                Comment.organization_id == organization_id,
                Comment.entity_type == entity_type,
                Comment.entity_id == entity_id,
                Comment.parent_comment_id.is_(None),
                Comment.is_deleted == False,
            )
        ).order_by(Comment.created_at.asc())

        total = query.count()
        comments = query.offset(skip).limit(limit).all()
        return comments, total
