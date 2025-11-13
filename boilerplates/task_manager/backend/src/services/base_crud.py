"""Generic CRUD service for database operations."""

from typing import TypeVar, Generic, List, Optional, Dict, Any, Type
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseCRUDService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Generic CRUD service for all models."""

    def __init__(self, model: Type[ModelType]):
        self.model = model

    def create(self, db: Session, *, obj_in: CreateSchemaType, organization_id: str) -> ModelType:
        """Create a new object."""
        obj_data = obj_in.dict(exclude_unset=True)
        obj_data["organization_id"] = organization_id
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def read(self, db: Session, *, id: str, organization_id: str) -> Optional[ModelType]:
        """Read an object by ID."""
        return db.query(self.model).filter(
            and_(
                self.model.id == id,
                self.model.organization_id == organization_id,
                self.model.is_deleted == False,
            )
        ).first()

    def read_all(
        self,
        db: Session,
        *,
        organization_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[ModelType], int]:
        """Read all objects with pagination."""
        query = db.query(self.model).filter(
            and_(
                self.model.organization_id == organization_id,
                self.model.is_deleted == False,
            )
        )
        total = query.count()
        objects = query.offset(skip).limit(limit).all()
        return objects, total

    def update(
        self,
        db: Session,
        *,
        id: str,
        organization_id: str,
        obj_in: UpdateSchemaType,
    ) -> Optional[ModelType]:
        """Update an object."""
        db_obj = self.read(db, id=id, organization_id=organization_id)
        if not db_obj:
            return None

        obj_data = obj_in.dict(exclude_unset=True)
        for field, value in obj_data.items():
            setattr(db_obj, field, value)

        db_obj.updated_at = datetime.utcnow()
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, *, id: str, organization_id: str) -> bool:
        """Soft delete an object."""
        db_obj = self.read(db, id=id, organization_id=organization_id)
        if not db_obj:
            return False

        db_obj.is_deleted = True
        db_obj.updated_at = datetime.utcnow()
        db.add(db_obj)
        db.commit()
        return True

    def hard_delete(self, db: Session, *, id: str, organization_id: str) -> bool:
        """Hard delete an object (use with caution)."""
        db_obj = db.query(self.model).filter(
            and_(
                self.model.id == id,
                self.model.organization_id == organization_id,
            )
        ).first()

        if not db_obj:
            return False

        db.delete(db_obj)
        db.commit()
        return True

    def filter_by(
        self,
        db: Session,
        *,
        organization_id: str,
        skip: int = 0,
        limit: int = 100,
        **filters: Any,
    ) -> tuple[List[ModelType], int]:
        """Filter objects by attributes."""
        query = db.query(self.model).filter(
            and_(
                self.model.organization_id == organization_id,
                self.model.is_deleted == False,
            )
        )

        for field, value in filters.items():
            if hasattr(self.model, field) and value is not None:
                query = query.filter(getattr(self.model, field) == value)

        total = query.count()
        objects = query.offset(skip).limit(limit).all()
        return objects, total
