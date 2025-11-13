"""Base model with common fields for all entities."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base
from uuid import uuid4

Base = declarative_base()


class TimestampedBase(Base):
    """Base class for all models with timestamps and soft delete."""

    __abstract__ = True

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id = Column(String(36), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.id}>"
