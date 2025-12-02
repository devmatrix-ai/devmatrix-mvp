"""
CartItem Repository

Data access layer for  table.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from uuid import UUID
from typing import Optional, List
from src.models.entities import CartItemEntity
from src.models.schemas import CartItemCreate, CartItemUpdate
import structlog

logger = structlog.get_logger(__name__)


class CartItemRepository:
    """Data access layer for CartItem."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, cartitem_data: CartItemCreate) -> CartItemEntity:
        """
        Create new cartitem.

        Args:
            cartitem_data: CartItem creation data

        Returns:
            Created cartitem entity
        """
        cartitem = CartItemEntity(**cartitem_data.model_dump())
        self.db.add(cartitem)
        await self.db.flush()
        await self.db.refresh(cartitem)

        logger.info("cartitem_created", cartitem_id=str(cartitem.id))
        return cartitem

    async def get(self, cartitem_id: UUID) -> Optional[CartItemEntity]:
        """
        Get cartitem by ID.

        Args:
            cartitem_id: CartItem UUID

        Returns:
            CartItem entity or None if not found
        """
        result = await self.db.execute(
            select(CartItemEntity).where(CartItemEntity.id == cartitem_id)
        )
        return result.scalar_one_or_none()

    async def list(self, skip: int = 0, limit: int = 100) -> List[CartItemEntity]:
        """
        List  with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of cartitem entities
        """
        result = await self.db.execute(
            select(CartItemEntity).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def count(self) -> int:
        """
        Count total .

        Returns:
            Total count of 
        """
        result = await self.db.execute(
            select(CartItemEntity)
        )
        return len(result.scalars().all())

    async def update(
        self, cartitem_id: UUID, cartitem_data: CartItemUpdate
    ) -> Optional[CartItemEntity]:
        """
        Update cartitem.

        Args:
            cartitem_id: CartItem UUID
            cartitem_data: Update data

        Returns:
            Updated cartitem entity or None if not found
        """
        # Get existing cartitem
        cartitem = await self.get(cartitem_id)
        if not cartitem:
            return None

        # Update only provided fields
        update_data = cartitem_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(cartitem, key, value)

        await self.db.flush()
        await self.db.refresh(cartitem)

        logger.info("cartitem_updated", cartitem_id=str(cartitem_id))
        return cartitem

    async def delete(self, cartitem_id: UUID) -> bool:
        """
        Delete cartitem.

        Args:
            cartitem_id: CartItem UUID

        Returns:
            True if deleted, False if not found
        """
        result = await self.db.execute(
            delete(CartItemEntity).where(CartItemEntity.id == cartitem_id)
        )

        deleted = result.rowcount > 0
        if deleted:
            logger.info("cartitem_deleted", cartitem_id=str(cartitem_id))

        return deleted