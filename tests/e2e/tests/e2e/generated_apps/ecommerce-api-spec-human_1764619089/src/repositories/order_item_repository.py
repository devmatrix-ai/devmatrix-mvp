"""
OrderItem Repository

Data access layer for  table.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from uuid import UUID
from typing import Optional, List
from src.models.entities import OrderItemEntity
from src.models.schemas import OrderItemCreate, OrderItemUpdate
import structlog

logger = structlog.get_logger(__name__)


class OrderItemRepository:
    """Data access layer for OrderItem."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, orderitem_data: OrderItemCreate) -> OrderItemEntity:
        """
        Create new orderitem.

        Args:
            orderitem_data: OrderItem creation data

        Returns:
            Created orderitem entity
        """
        orderitem = OrderItemEntity(**orderitem_data.model_dump())
        self.db.add(orderitem)
        await self.db.flush()
        await self.db.refresh(orderitem)

        logger.info("orderitem_created", orderitem_id=str(orderitem.id))
        return orderitem

    async def get(self, orderitem_id: UUID) -> Optional[OrderItemEntity]:
        """
        Get orderitem by ID.

        Args:
            orderitem_id: OrderItem UUID

        Returns:
            OrderItem entity or None if not found
        """
        result = await self.db.execute(
            select(OrderItemEntity).where(OrderItemEntity.id == orderitem_id)
        )
        return result.scalar_one_or_none()

    async def list(self, skip: int = 0, limit: int = 100) -> List[OrderItemEntity]:
        """
        List  with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of orderitem entities
        """
        result = await self.db.execute(
            select(OrderItemEntity).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def count(self) -> int:
        """
        Count total .

        Returns:
            Total count of 
        """
        result = await self.db.execute(
            select(OrderItemEntity)
        )
        return len(result.scalars().all())

    async def update(
        self, orderitem_id: UUID, orderitem_data: OrderItemUpdate
    ) -> Optional[OrderItemEntity]:
        """
        Update orderitem.

        Args:
            orderitem_id: OrderItem UUID
            orderitem_data: Update data

        Returns:
            Updated orderitem entity or None if not found
        """
        # Get existing orderitem
        orderitem = await self.get(orderitem_id)
        if not orderitem:
            return None

        # Update only provided fields
        update_data = orderitem_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(orderitem, key, value)

        await self.db.flush()
        await self.db.refresh(orderitem)

        logger.info("orderitem_updated", orderitem_id=str(orderitem_id))
        return orderitem

    async def delete(self, orderitem_id: UUID) -> bool:
        """
        Delete orderitem.

        Args:
            orderitem_id: OrderItem UUID

        Returns:
            True if deleted, False if not found
        """
        result = await self.db.execute(
            delete(OrderItemEntity).where(OrderItemEntity.id == orderitem_id)
        )

        deleted = result.rowcount > 0
        if deleted:
            logger.info("orderitem_deleted", orderitem_id=str(orderitem_id))

        return deleted