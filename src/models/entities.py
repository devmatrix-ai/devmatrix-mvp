"""
Production-ready SQLAlchemy entities with async support.

Features:
- UUID primary keys
- Timezone-aware DateTime columns
- Proper indexes for performance
- __repr__ methods for debugging
- created_at/updated_at timestamps
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, Index
from sqlalchemy.dialects.postgresql import UUID

from src.core.database import Base


class TaskEntity(Base):
    """
    SQLAlchemy model for tasks table.

    Production-ready features:
    - UUID primary key for better distribution
    - Timezone-aware timestamps
    - Indexes on frequently queried fields (title, completed)
    - Automatic timestamp management
    """

    __tablename__ = "tasks"

    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique task identifier (UUID)"
    )

    # Business fields
    title = Column(
        String(200),
        nullable=False,
        index=True,
        comment="Task title (max 200 chars)"
    )
    description = Column(
        Text,
        nullable=True,
        comment="Detailed task description"
    )
    completed = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Task completion status"
    )
    priority = Column(
        Integer,
        nullable=True,
        default=0,
        comment="Task priority (0=low, 1=medium, 2=high)"
    )

    # Timestamps (timezone-aware)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Timestamp when task was created (UTC)"
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Timestamp when task was last updated (UTC)"
    )

    # Indexes for performance
    __table_args__ = (
        Index('ix_tasks_completed_created', 'completed', 'created_at'),
        Index('ix_tasks_priority_completed', 'priority', 'completed'),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<TaskEntity {self.id}: {self.title} (completed={self.completed})>"


class ProductEntity(Base):
    """
    SQLAlchemy model for products table (example e-commerce entity).

    Demonstrates production-ready entity with:
    - Decimal pricing (stored as integers to avoid floating point issues)
    - Stock tracking
    - SKU indexing
    - Soft delete capability
    """

    __tablename__ = "products"

    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique product identifier (UUID)"
    )

    # Business fields
    sku = Column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="Stock Keeping Unit (unique product code)"
    )
    name = Column(
        String(200),
        nullable=False,
        index=True,
        comment="Product name"
    )
    description = Column(
        Text,
        nullable=True,
        comment="Product description"
    )
    price_cents = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Price in cents (avoid floating point issues)"
    )
    stock_quantity = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Current stock quantity"
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Product active status (soft delete)"
    )

    # Timestamps (timezone-aware)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Timestamp when product was created (UTC)"
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Timestamp when product was last updated (UTC)"
    )

    # Indexes for performance
    __table_args__ = (
        Index('ix_products_active_stock', 'is_active', 'stock_quantity'),
        Index('ix_products_name_active', 'name', 'is_active'),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<ProductEntity {self.id}: {self.name} (${self.price_cents/100:.2f}, stock={self.stock_quantity})>"

    @property
    def price_dollars(self) -> float:
        """Convert price from cents to dollars."""
        return self.price_cents / 100.0

    @price_dollars.setter
    def price_dollars(self, value: float) -> None:
        """Set price in dollars (converted to cents)."""
        self.price_cents = int(value * 100)
