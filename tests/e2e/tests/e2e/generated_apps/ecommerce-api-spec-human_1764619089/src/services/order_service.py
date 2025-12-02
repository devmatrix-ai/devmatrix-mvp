"""
FastAPI Service for Order

Business logic and data access patterns.
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging

from src.models.schemas import OrderCreate, OrderUpdate, OrderResponse, OrderList
from src.repositories.order_repository import OrderRepository
from src.models.entities import OrderEntity

logger = logging.getLogger(__name__)


class OrderService:
    """Business logic for Order."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = OrderRepository(db)

    async def create(self, data: OrderCreate) -> OrderResponse:
        """Create a new order."""
        # Bug #142 Fix: Pass Pydantic model directly - repository handles model_dump()
        db_obj = await self.repo.create(data)
        return OrderResponse.model_validate(db_obj)

    async def get(self, id: UUID) -> Optional[OrderResponse]:
        """Get order by ID."""
        db_obj = await self.repo.get(id)
        if db_obj:
            return OrderResponse.model_validate(db_obj)
        return None

    async def get_by_id(self, id: UUID) -> Optional[OrderResponse]:
        """Alias for get() to satisfy routes expecting get_by_id."""
        return await self.get(id)

    async def list(self, page: int = 1, size: int = 10) -> OrderList:
        """List orders with pagination."""
        skip = (page - 1) * size

        items = await self.repo.list(skip=skip, limit=size)
        total = await self.repo.count()

        return OrderList(
            items=[OrderResponse.model_validate(t) for t in items],
            total=total,
            page=page,
            size=size,
        )

    async def update(self, id: UUID, data: OrderUpdate) -> Optional[OrderResponse]:
        """Update order."""
        # Bug #142 Fix: Pass Pydantic model directly - repository handles model_dump()
        db_obj = await self.repo.update(id, data)
        if db_obj:
            return OrderResponse.model_validate(db_obj)
        return None

    async def delete(self, id: UUID) -> bool:
        """Delete order."""
        return await self.repo.delete(id)

    async def clear_items(self, id: UUID) -> Optional[OrderResponse]:
        """
        Clear all items/children from this order.

        Used for entities that have child relationships (e.g., Cart → CartItems).
        Returns the updated entity after clearing items.

        Bug #105 Fix: Uses direct SQLAlchemy delete instead of non-existent repo method.
        Bug #140 Fix: Only generated for entities with verified child relationships.
        """
        # Get the entity first
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        # Bug #105 Fix: Clear items directly using SQLAlchemy delete
        from sqlalchemy import delete
        from src.models.entities import OrderItemEntity
        await self.db.execute(
            delete(OrderItemEntity).where(OrderItemEntity.order_id == id)
        )
        await self.db.flush()

        # Return the updated entity
        refreshed = await self.repo.get(id)
        return OrderResponse.model_validate(refreshed) if refreshed else None

    async def checkout(self, id: UUID) -> Optional[OrderResponse]:
        """
        F13: Checkout (Create Order) operation for Order.

        Generated from IR BehaviorModel flow. Bug #143 Fix.
        """
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        # TODO: Implement actual checkout logic from IR steps
        # For now, log and return the entity
        logger.info(f"Order checkout: id={str(id)}")
        await self.db.refresh(db_obj)
        return OrderResponse.model_validate(db_obj)

    async def pay(self, id: UUID) -> Optional[OrderResponse]:
        """
        F14: Pay Order (Simulated) operation for Order.

        Generated from IR BehaviorModel flow. Bug #143 Fix.
        """
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        # TODO: Implement actual pay logic from IR steps
        # For now, log and return the entity
        logger.info(f"Order pay: id={str(id)}")
        await self.db.refresh(db_obj)
        return OrderResponse.model_validate(db_obj)

    async def cancel(self, id: UUID) -> Optional[OrderResponse]:
        """
        F15: Cancel Order operation for Order.

        Generated from IR BehaviorModel flow. Bug #143 Fix.
        """
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        # TODO: Implement actual cancel logic from IR steps
        # For now, log and return the entity
        logger.info(f"Order cancel: id={str(id)}")
        await self.db.refresh(db_obj)
        return OrderResponse.model_validate(db_obj)

    async def list_customers(self, id: UUID) -> Optional[OrderResponse]:
        """
        F16: List Customer Orders operation for Order.

        Generated from IR BehaviorModel flow. Bug #143 Fix.
        """
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        # TODO: Implement actual list_customers logic from IR steps
        # For now, log and return the entity
        logger.info(f"Order list_customers: id={str(id)}")
        await self.db.refresh(db_obj)
        return OrderResponse.model_validate(db_obj)

    async def view_details(self, id: UUID) -> Optional[OrderResponse]:
        """
        F17: View Order Details operation for Order.

        Generated from IR BehaviorModel flow. Bug #143 Fix.
        """
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        # TODO: Implement actual view_details logic from IR steps
        # For now, log and return the entity
        logger.info(f"Order view_details: id={str(id)}")
        await self.db.refresh(db_obj)
        return OrderResponse.model_validate(db_obj)