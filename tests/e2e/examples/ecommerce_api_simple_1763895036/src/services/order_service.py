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
        db_obj = await self.repo.update(id, data)
        if db_obj:
            return OrderResponse.model_validate(db_obj)
        return None

    async def delete(self, id: UUID) -> bool:
        """Delete order."""
        return await self.repo.delete(id)