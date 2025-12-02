"""
Order Repository

Data access layer for  table.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from uuid import UUID
from typing import Optional, List
from src.models.entities import OrderEntity
from src.models.schemas import OrderCreate, OrderUpdate
import structlog

logger = structlog.get_logger(__name__)


class OrderRepository:
    """Data access layer for Order."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, order_data: OrderCreate) -> OrderEntity:
        """
        Create new order.

        Args:
            order_data: Order creation data

        Returns:
            Created order entity
        """
        order = OrderEntity(**order_data.model_dump())
        self.db.add(order)
        await self.db.flush()
        await self.db.refresh(order)

        logger.info("order_created", order_id=str(order.id))
        return order

    async def get(self, order_id: UUID) -> Optional[OrderEntity]:
        """
        Get order by ID.

        Args:
            order_id: Order UUID

        Returns:
            Order entity or None if not found
        """
        result = await self.db.execute(
            select(OrderEntity).where(OrderEntity.id == order_id)
        )
        return result.scalar_one_or_none()

    async def list(self, skip: int = 0, limit: int = 100) -> List[OrderEntity]:
        """
        List  with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of order entities
        """
        result = await self.db.execute(
            select(OrderEntity).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def count(self) -> int:
        """
        Count total .

        Returns:
            Total count of 
        """
        result = await self.db.execute(
            select(OrderEntity)
        )
        return len(result.scalars().all())

    async def update(
        self, order_id: UUID, order_data: OrderUpdate
    ) -> Optional[OrderEntity]:
        """
        Update order.

        Args:
            order_id: Order UUID
            order_data: Update data

        Returns:
            Updated order entity or None if not found
        """
        # Get existing order
        order = await self.get(order_id)
        if not order:
            return None

        # Update only provided fields
        update_data = order_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(order, key, value)

        await self.db.flush()
        await self.db.refresh(order)

        logger.info("order_updated", order_id=str(order_id))
        return order

    async def delete(self, order_id: UUID) -> bool:
        """
        Delete order.

        Args:
            order_id: Order UUID

        Returns:
            True if deleted, False if not found
        """
        result = await self.db.execute(
            delete(OrderEntity).where(OrderEntity.id == order_id)
        )

        deleted = result.rowcount > 0
        if deleted:
            logger.info("order_deleted", order_id=str(order_id))

        return deleted