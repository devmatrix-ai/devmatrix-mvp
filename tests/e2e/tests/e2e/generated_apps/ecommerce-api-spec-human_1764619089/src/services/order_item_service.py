"""
FastAPI Service for OrderItem

Business logic and data access patterns.
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging

from src.models.schemas import OrderItemCreate, OrderItemUpdate, OrderItemResponse, OrderItemList
from src.repositories.order_item_repository import OrderItemRepository
from src.models.entities import OrderItemEntity

logger = logging.getLogger(__name__)


class OrderItemService:
    """Business logic for OrderItem."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = OrderItemRepository(db)

    async def create(self, data: OrderItemCreate) -> OrderItemResponse:
        """Create a new orderitem."""
        # Bug #142 Fix: Pass Pydantic model directly - repository handles model_dump()
        db_obj = await self.repo.create(data)
        return OrderItemResponse.model_validate(db_obj)

    async def get(self, id: UUID) -> Optional[OrderItemResponse]:
        """Get orderitem by ID."""
        db_obj = await self.repo.get(id)
        if db_obj:
            return OrderItemResponse.model_validate(db_obj)
        return None

    async def get_by_id(self, id: UUID) -> Optional[OrderItemResponse]:
        """Alias for get() to satisfy routes expecting get_by_id."""
        return await self.get(id)

    async def list(self, page: int = 1, size: int = 10) -> OrderItemList:
        """List order_items with pagination."""
        skip = (page - 1) * size

        items = await self.repo.list(skip=skip, limit=size)
        total = await self.repo.count()

        return OrderItemList(
            items=[OrderItemResponse.model_validate(t) for t in items],
            total=total,
            page=page,
            size=size,
        )

    async def update(self, id: UUID, data: OrderItemUpdate) -> Optional[OrderItemResponse]:
        """Update orderitem."""
        # Bug #142 Fix: Pass Pydantic model directly - repository handles model_dump()
        db_obj = await self.repo.update(id, data)
        if db_obj:
            return OrderItemResponse.model_validate(db_obj)
        return None

    async def delete(self, id: UUID) -> bool:
        """Delete orderitem."""
        return await self.repo.delete(id)

    async def checkout(self, id: UUID) -> Optional[OrderItemResponse]:
        """
        F13: Checkout (Create Order) operation for OrderItem.

        Generated from IR BehaviorModel flow. Bug #143 Fix.
        """
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        # TODO: Implement actual checkout logic from IR steps
        # For now, log and return the entity
        logger.info(f"OrderItem checkout: id={str(id)}")
        await self.db.refresh(db_obj)
        return OrderItemResponse.model_validate(db_obj)