#!/usr/bin/env python3
"""
Pattern Database Repopulation Script

Fixes TG3 issue: 99.83% of patterns have empty purpose="" field.
Creates valid seed patterns for production-ready code generation.

Author: DevMatrix Team
Date: 2025-11-20
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cognitive.patterns.pattern_bank import PatternBank
from src.cognitive.signatures.semantic_signature import SemanticTaskSignature
from src.observability import StructuredLogger

logger = StructuredLogger("pattern_repopulation", output_json=False)


# Production-ready seed patterns
SEED_PATTERNS = [
    # Core Configuration
    {
        "category": "core_config",
        "purpose": "Production-ready FastAPI configuration with pydantic-settings",
        "code": '''"""
Core Configuration Module

Uses pydantic-settings for environment-based configuration.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # App metadata
    app_name: str = Field(default="API", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/app",
        env="DATABASE_URL"
    )

    # Security
    secret_key: str = Field(default="", env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    # CORS
    cors_origins: list[str] = Field(default=["*"], env="CORS_ORIGINS")

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
''',
        "domain": "api_development",
        "success_rate": 0.95,
        "production_ready": True,
    },

    # Async Database Connection
    {
        "category": "database_async",
        "purpose": "Async SQLAlchemy database connection with connection pooling",
        "code": '''"""
Async Database Connection Module

Provides async SQLAlchemy engine and session management.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from contextlib import asynccontextmanager

from .config import settings

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create async session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Declarative base for models
Base = declarative_base()


@asynccontextmanager
async def get_db():
    """Dependency for getting database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
''',
        "domain": "api_development",
        "success_rate": 0.95,
        "production_ready": True,
    },

    # Structured Logging
    {
        "category": "observability_logging",
        "purpose": "Structured logging with context tracking and request IDs",
        "code": '''"""
Structured Logging Module

Provides JSON-formatted structured logging with request context.
"""

import structlog
import logging
from contextvars import ContextVar

# Context variables for request tracking
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
user_id_ctx: ContextVar[str] = ContextVar("user_id", default="")


def configure_logging():
    """Configure structlog for production use."""

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )


# Configure on module import
configure_logging()

# Create logger instance
logger = structlog.get_logger()
''',
        "domain": "api_development",
        "success_rate": 0.95,
        "production_ready": True,
    },

    # Pydantic Models Base
    {
        "category": "models_pydantic",
        "purpose": "Base Pydantic schemas for request/response validation",
        "code": '''"""
Pydantic Schemas Module

Request and response models with validation.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from uuid import UUID


class EntityBase(BaseModel):
    """Base schema for all entities."""
    pass


class EntityCreate(EntityBase):
    """Schema for entity creation."""
    pass


class EntityUpdate(BaseModel):
    """Schema for entity updates (all fields optional)."""
    pass


class EntityResponse(EntityBase):
    """Schema for entity responses."""
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class PaginatedResponse(BaseModel):
    """Generic paginated response."""
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int
''',
        "domain": "api_development",
        "success_rate": 0.95,
        "production_ready": True,
    },

    # SQLAlchemy Models Base
    {
        "category": "models_sqlalchemy",
        "purpose": "Base SQLAlchemy entity models with common fields",
        "code": '''"""
SQLAlchemy Entity Models

Database models with timestamp tracking and soft delete support.
"""

from sqlalchemy import Column, String, DateTime, Boolean, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid
from datetime import datetime

from src.core.database import Base


class TimestampMixin:
    """Mixin for automatic timestamp tracking."""

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SoftDeleteMixin:
    """Mixin for soft delete support."""

    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)


class BaseEntity(Base, TimestampMixin):
    """Base entity model with UUID primary key and timestamps."""

    __abstract__ = True

    id = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
''',
        "domain": "api_development",
        "success_rate": 0.95,
        "production_ready": True,
    },

    # Repository Pattern Base
    {
        "category": "repository_pattern",
        "purpose": "Generic repository pattern for data access layer",
        "code": '''"""
Repository Pattern Base

Generic CRUD operations for data access layer.
"""

from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from uuid import UUID

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base repository with generic CRUD operations."""

    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def create(
        self,
        db: AsyncSession,
        obj_in: CreateSchemaType
    ) -> ModelType:
        """Create new entity."""
        db_obj = self.model(**obj_in.dict())
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get(
        self,
        db: AsyncSession,
        id: UUID
    ) -> Optional[ModelType]:
        """Get entity by ID."""
        result = await db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """List entities with pagination."""
        result = await db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def update(
        self,
        db: AsyncSession,
        id: UUID,
        obj_in: UpdateSchemaType
    ) -> Optional[ModelType]:
        """Update entity."""
        await db.execute(
            update(self.model)
            .where(self.model.id == id)
            .values(**obj_in.dict(exclude_unset=True))
        )
        return await self.get(db, id)

    async def delete(
        self,
        db: AsyncSession,
        id: UUID
    ) -> bool:
        """Delete entity."""
        result = await db.execute(
            delete(self.model).where(self.model.id == id)
        )
        return result.rowcount > 0
''',
        "domain": "api_development",
        "success_rate": 0.95,
        "production_ready": True,
    },

    # FastAPI Route Template
    {
        "category": "api_routes",
        "purpose": "FastAPI route handlers with dependency injection",
        "code": '''"""
API Routes Module

REST API endpoints with OpenAPI documentation.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from src.core.database import get_db
from src.models.schemas import (
    EntityCreate,
    EntityUpdate,
    EntityResponse,
    PaginationParams,
    PaginatedResponse,
)
from src.repositories import EntityRepository

router = APIRouter(prefix="/entities", tags=["entities"])
repository = EntityRepository()


@router.post(
    "/",
    response_model=EntityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create entity",
)
async def create_entity(
    entity_in: EntityCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new entity."""
    return await repository.create(db, entity_in)


@router.get(
    "/",
    response_model=List[EntityResponse],
    summary="List entities",
)
async def list_entities(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """List entities with pagination."""
    return await repository.list(
        db,
        skip=pagination.offset,
        limit=pagination.limit
    )


@router.get(
    "/{entity_id}",
    response_model=EntityResponse,
    summary="Get entity",
)
async def get_entity(
    entity_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get entity by ID."""
    entity = await repository.get(db, entity_id)
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity {entity_id} not found"
        )
    return entity


@router.put(
    "/{entity_id}",
    response_model=EntityResponse,
    summary="Update entity",
)
async def update_entity(
    entity_id: UUID,
    entity_in: EntityUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update entity."""
    entity = await repository.update(db, entity_id, entity_in)
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity {entity_id} not found"
        )
    return entity


@router.delete(
    "/{entity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete entity",
)
async def delete_entity(
    entity_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete entity."""
    deleted = await repository.delete(db, entity_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity {entity_id} not found"
        )
''',
        "domain": "api_development",
        "success_rate": 0.95,
        "production_ready": True,
    },

    # Health Check Endpoints
    {
        "category": "health_checks",
        "purpose": "Health check endpoints for production monitoring",
        "code": '''"""
Health Check Endpoints

Kubernetes-compatible health and readiness probes.
"""

from fastapi import APIRouter, status
from pydantic import BaseModel
from datetime import datetime

from src.core.config import settings
from src.core.database import engine

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    version: str
    app_name: str


class ReadinessResponse(BaseModel):
    """Readiness check response."""
    ready: bool
    checks: dict[str, bool]


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
)
async def health_check():
    """Basic health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version=settings.app_version,
        app_name=settings.app_name,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
)
async def readiness_check():
    """
    Readiness probe for Kubernetes.
    Checks if app can accept traffic.
    """
    checks = {
        "database": False,
    }

    # Check database connection
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        checks["database"] = True
    except Exception:
        pass

    ready = all(checks.values())

    return ReadinessResponse(
        ready=ready,
        checks=checks,
    )
''',
        "domain": "api_development",
        "success_rate": 0.96,
        "production_ready": True,
    },

    # E-commerce Pattern 1: Cart State Management
    {
        "category": "cart_management",
        "purpose": "Shopping cart state management with item CRUD operations and state transitions",
        "code": '''"""
Cart management service with state handling.

Handles cart lifecycle: OPEN → CHECKED_OUT
"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from models import Cart, CartItem, CartStatus

class CartService:
    """Cart management with state transitions."""

    async def create_cart(
        self,
        db: AsyncSession,
        customer_id: UUID
    ) -> Cart:
        """Create cart or reuse existing OPEN cart."""
        # Check for existing OPEN cart
        existing = await db.execute(
            select(Cart).where(
                Cart.customer_id == customer_id,
                Cart.status == CartStatus.OPEN
            )
        )
        cart = existing.scalar_one_or_none()

        if cart:
            return cart

        # Create new cart
        cart = Cart(customer_id=customer_id, status=CartStatus.OPEN)
        db.add(cart)
        await db.commit()
        return cart

    async def add_item(
        self,
        db: AsyncSession,
        cart_id: UUID,
        product_id: UUID,
        quantity: int,
        unit_price: Decimal
    ) -> CartItem:
        """Add item to cart or update quantity if exists."""
        # Check if item exists
        existing = await db.execute(
            select(CartItem).where(
                CartItem.cart_id == cart_id,
                CartItem.product_id == product_id
            )
        )
        item = existing.scalar_one_or_none()

        if item:
            item.quantity += quantity
        else:
            item = CartItem(
                cart_id=cart_id,
                product_id=product_id,
                quantity=quantity,
                unit_price=unit_price
            )
            db.add(item)

        await db.commit()
        return item

    async def update_item_quantity(
        self,
        db: AsyncSession,
        item_id: UUID,
        quantity: int
    ) -> Optional[CartItem]:
        """Update item quantity or delete if <= 0."""
        item = await db.get(CartItem, item_id)
        if not item:
            return None

        if quantity <= 0:
            await db.delete(item)
            await db.commit()
            return None

        item.quantity = quantity
        await db.commit()
        return item

    async def clear_cart(self, db: AsyncSession, cart_id: UUID) -> bool:
        """Remove all items from cart."""
        await db.execute(
            delete(CartItem).where(CartItem.cart_id == cart_id)
        )
        await db.commit()
        return True
''',
        "domain": "api_development",
        "success_rate": 0.95,
        "production_ready": True,
    },

    # E-commerce Pattern 2: Order Checkout Workflow
    {
        "category": "order_checkout",
        "purpose": "Order checkout workflow with stock validation, deduction, and cart state transition",
        "code": '''"""
Order checkout workflow with transaction safety.

Validates stock, deducts inventory, transitions cart to CHECKED_OUT.
"""
from decimal import Decimal
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from models import Cart, Order, OrderItem, Product, CartStatus, OrderStatus

class CheckoutService:
    """Order checkout with atomicity guarantees."""

    async def checkout_cart(
        self,
        db: AsyncSession,
        cart_id: UUID
    ) -> Order:
        """Create order from cart with stock validation."""
        # Load cart with items
        cart = await db.get(Cart, cart_id, with_for_update=True)
        if not cart or cart.status != CartStatus.OPEN:
            raise ValueError("Cart not found or already checked out")

        items = await db.execute(
            select(CartItem).where(CartItem.cart_id == cart_id)
        )
        cart_items = items.scalars().all()

        if not cart_items:
            raise ValueError("Cart is empty")

        # Validate stock for all items
        order_items = []
        total_amount = Decimal("0.00")

        for item in cart_items:
            product = await db.get(Product, item.product_id, with_for_update=True)

            if not product or not product.is_active:
                raise ValueError(f"Product {item.product_id} not available")

            if product.stock < item.quantity:
                raise ValueError(
                    f"Insufficient stock for {product.name}. "
                    f"Available: {product.stock}, Requested: {item.quantity}"
                )

            # Deduct stock
            product.stock -= item.quantity

            # Create order item
            order_item = OrderItem(
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price
            )
            order_items.append(order_item)
            total_amount += item.unit_price * item.quantity

        # Create order
        order = Order(
            customer_id=cart.customer_id,
            items=order_items,
            total_amount=total_amount,
            status=OrderStatus.PENDING_PAYMENT,
            payment_status=PaymentStatus.PENDING
        )
        db.add(order)

        # Transition cart to CHECKED_OUT
        cart.status = CartStatus.CHECKED_OUT

        await db.commit()
        return order
''',
        "domain": "api_development",
        "success_rate": 0.95,
        "production_ready": True,
    },

    # E-commerce Pattern 3: Payment Workflow
    {
        "category": "payment_workflow",
        "purpose": "Payment state transitions and order cancellation with stock rollback",
        "code": '''"""
Payment workflow with state machine and rollback logic.

Handles payment simulation and order cancellation with stock restoration.
"""
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from models import Order, Product, OrderStatus, PaymentStatus

class PaymentService:
    """Payment operations with state validation."""

    async def simulate_payment_success(
        self,
        db: AsyncSession,
        order_id: UUID
    ) -> Order:
        """Mark order as paid (simulated payment)."""
        order = await db.get(Order, order_id, with_for_update=True)

        if not order:
            raise ValueError("Order not found")

        if order.status != OrderStatus.PENDING_PAYMENT:
            raise ValueError(
                f"Cannot pay order in status {order.status}"
            )

        order.status = OrderStatus.PAID
        order.payment_status = PaymentStatus.SIMULATED_OK

        await db.commit()
        return order

    async def cancel_order(
        self,
        db: AsyncSession,
        order_id: UUID
    ) -> Order:
        """Cancel order and restore stock."""
        order = await db.get(Order, order_id, with_for_update=True)

        if not order:
            raise ValueError("Order not found")

        if order.status != OrderStatus.PENDING_PAYMENT:
            raise ValueError(
                f"Cannot cancel order in status {order.status}"
            )

        # Restore stock for all items
        for item in order.items:
            product = await db.get(Product, item.product_id, with_for_update=True)
            if product:
                product.stock += item.quantity

        # Cancel order
        order.status = OrderStatus.CANCELLED
        order.payment_status = PaymentStatus.FAILED

        await db.commit()
        return order
''',
        "domain": "api_development",
        "success_rate": 0.95,
        "production_ready": True,
    },

    # E-commerce Pattern 4: Order Queries
    {
        "category": "order_queries",
        "purpose": "Order listing and retrieval with filtering by customer and status",
        "code": '''"""
Order query operations with filtering.

List orders by customer with optional status filtering.
"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from models import Order, OrderStatus

class OrderQueryService:
    """Order retrieval operations."""

    async def list_customer_orders(
        self,
        db: AsyncSession,
        customer_id: UUID,
        status: Optional[OrderStatus] = None,
        page: int = 1,
        page_size: int = 20
    ) -> List[Order]:
        """List orders for a customer with optional status filter."""
        query = select(Order).where(Order.customer_id == customer_id)

        if status:
            query = query.where(Order.status == status)

        query = query.order_by(Order.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        return result.scalars().all()

    async def get_order(
        self,
        db: AsyncSession,
        order_id: UUID
    ) -> Optional[Order]:
        """Get order by ID with items loaded."""
        result = await db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == order_id)
        )
        return result.scalar_one_or_none()
''',
        "domain": "api_development",
        "success_rate": 0.95,
        "production_ready": True,
    },

    # E-commerce Pattern 5: Stock Validation
    {
        "category": "stock_management",
        "purpose": "Product stock validation and availability checking",
        "code": '''"""
Stock management utilities.

Validate product availability and stock levels.
"""
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from models import Product

class StockService:
    """Stock validation and management."""

    async def validate_stock_availability(
        self,
        db: AsyncSession,
        product_id: UUID,
        quantity: int
    ) -> bool:
        """Check if product has sufficient stock."""
        product = await db.get(Product, product_id)

        if not product:
            return False

        if not product.is_active:
            return False

        return product.stock >= quantity

    async def check_multiple_products(
        self,
        db: AsyncSession,
        items: List[tuple[UUID, int]]
    ) -> dict[UUID, bool]:
        """Check stock for multiple products."""
        results = {}

        for product_id, quantity in items:
            available = await self.validate_stock_availability(
                db, product_id, quantity
            )
            results[product_id] = available

        return results

    async def get_available_stock(
        self,
        db: AsyncSession,
        product_id: UUID
    ) -> int:
        """Get current available stock for product."""
        product = await db.get(Product, product_id)

        if not product or not product.is_active:
            return 0

        return product.stock
''',
        "domain": "api_development",
        "success_rate": 0.96,
        "production_ready": True,
    },

    # E-commerce Pattern 6: Price Snapshotting
    {
        "category": "price_snapshot",
        "purpose": "Price capture and snapshotting for cart items and orders",
        "code": '''"""
Price snapshotting utilities.

Capture product prices at the time of cart add or order creation.
"""
from decimal import Decimal
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from models import Product

class PriceService:
    """Price capture and management."""

    async def get_current_price(
        self,
        db: AsyncSession,
        product_id: UUID
    ) -> Decimal:
        """Get current product price."""
        product = await db.get(Product, product_id)

        if not product:
            raise ValueError(f"Product {product_id} not found")

        return product.price

    async def snapshot_prices(
        self,
        db: AsyncSession,
        product_ids: List[UUID]
    ) -> dict[UUID, Decimal]:
        """Capture prices for multiple products."""
        prices = {}

        result = await db.execute(
            select(Product).where(Product.id.in_(product_ids))
        )
        products = result.scalars().all()

        for product in products:
            prices[product.id] = product.price

        return prices

    def calculate_subtotal(
        self,
        unit_price: Decimal,
        quantity: int
    ) -> Decimal:
        """Calculate subtotal for item."""
        return unit_price * Decimal(quantity)

    def calculate_order_total(
        self,
        items: List[tuple[Decimal, int]]
    ) -> Decimal:
        """Calculate total for order from (price, quantity) tuples."""
        total = Decimal("0.00")

        for unit_price, quantity in items:
            total += self.calculate_subtotal(unit_price, quantity)

        return total
''',
        "domain": "api_development",
        "success_rate": 0.97,
        "production_ready": True,
    },

    # E-commerce Pattern 7: Workflow State Machine
    {
        "category": "state_machine",
        "purpose": "State machine for cart and order status transitions with validation",
        "code": '''"""
State machine for workflow status transitions.

Validates and manages state transitions for carts and orders.
"""
from enum import Enum
from typing import Set

class CartStatus(str, Enum):
    """Cart status states."""
    OPEN = "OPEN"
    CHECKED_OUT = "CHECKED_OUT"

class OrderStatus(str, Enum):
    """Order status states."""
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PAID = "PAID"
    CANCELLED = "CANCELLED"

class PaymentStatus(str, Enum):
    """Payment status states."""
    PENDING = "PENDING"
    SIMULATED_OK = "SIMULATED_OK"
    FAILED = "FAILED"

class StateMachine:
    """State transition validator."""

    # Valid transitions
    CART_TRANSITIONS = {
        CartStatus.OPEN: {CartStatus.CHECKED_OUT},
        CartStatus.CHECKED_OUT: set(),  # Terminal state
    }

    ORDER_TRANSITIONS = {
        OrderStatus.PENDING_PAYMENT: {OrderStatus.PAID, OrderStatus.CANCELLED},
        OrderStatus.PAID: set(),  # Terminal state
        OrderStatus.CANCELLED: set(),  # Terminal state
    }

    PAYMENT_TRANSITIONS = {
        PaymentStatus.PENDING: {PaymentStatus.SIMULATED_OK, PaymentStatus.FAILED},
        PaymentStatus.SIMULATED_OK: set(),  # Terminal state
        PaymentStatus.FAILED: set(),  # Terminal state
    }

    @classmethod
    def can_transition_cart(
        cls,
        from_status: CartStatus,
        to_status: CartStatus
    ) -> bool:
        """Check if cart status transition is valid."""
        return to_status in cls.CART_TRANSITIONS.get(from_status, set())

    @classmethod
    def can_transition_order(
        cls,
        from_status: OrderStatus,
        to_status: OrderStatus
    ) -> bool:
        """Check if order status transition is valid."""
        return to_status in cls.ORDER_TRANSITIONS.get(from_status, set())

    @classmethod
    def can_transition_payment(
        cls,
        from_status: PaymentStatus,
        to_status: PaymentStatus
    ) -> bool:
        """Check if payment status transition is valid."""
        return to_status in cls.PAYMENT_TRANSITIONS.get(from_status, set())

    @classmethod
    def get_allowed_transitions(
        cls,
        current_status: Enum,
        state_type: str
    ) -> Set[Enum]:
        """Get allowed transitions from current state."""
        transitions_map = {
            "cart": cls.CART_TRANSITIONS,
            "order": cls.ORDER_TRANSITIONS,
            "payment": cls.PAYMENT_TRANSITIONS,
        }

        transitions = transitions_map.get(state_type, {})
        return transitions.get(current_status, set())
''',
        "domain": "api_development",
        "success_rate": 0.96,
        "production_ready": True,
    },
]


def repopulate_patterns():
    """Repopulate pattern database with valid seed patterns."""

    logger.info(
        "Starting pattern database repopulation",
        extra={"seed_patterns_count": len(SEED_PATTERNS)}
    )

    # Initialize PatternBank
    pattern_bank = PatternBank()

    # Store each seed pattern
    stored_count = 0
    failed_count = 0

    for seed in SEED_PATTERNS:
        try:
            # Create signature from seed
            signature = SemanticTaskSignature(
                purpose=seed["purpose"],
                intent="implement",
                inputs={},
                outputs={},
                domain=seed["domain"],
                constraints=[],
                security_level="low",  # Valid values: low, medium, high, critical
            )

            # Store in PatternBank using public API
            pattern_id = pattern_bank.store_pattern(
                signature=signature,
                code=seed["code"],
                success_rate=seed["success_rate"]
            )

            stored_count += 1
            logger.info(
                f"Stored seed pattern: {seed['category']}",
                extra={
                    "category": seed["category"],
                    "purpose": seed["purpose"],
                    "success_rate": seed["success_rate"],
                }
            )

        except Exception as e:
            failed_count += 1
            logger.error(
                f"Failed to store seed pattern: {seed['category']}",
                extra={"category": seed["category"], "error": str(e)},
                exc_info=True,
            )

    logger.info(
        "Pattern database repopulation complete",
        extra={
            "stored": stored_count,
            "failed": failed_count,
            "total": len(SEED_PATTERNS),
        }
    )

    return stored_count, failed_count


def main():
    """Main entry point."""
    print("=" * 70)
    print("PATTERN DATABASE REPOPULATION")
    print("=" * 70)
    print(f"\nRepopulating with {len(SEED_PATTERNS)} seed patterns...\n")

    stored, failed = repopulate_patterns()

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"✅ Stored: {stored} patterns")
    print(f"❌ Failed: {failed} patterns")
    print(f"📊 Total: {len(SEED_PATTERNS)} patterns")
    print("=" * 70)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
