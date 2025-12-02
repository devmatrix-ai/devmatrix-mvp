"""
Cart Repository

Data access layer for  table.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from uuid import UUID
from typing import Optional, List
from src.models.entities import CartEntity
from src.models.schemas import CartCreate, CartUpdate
import structlog

logger = structlog.get_logger(__name__)


class CartRepository:
    """Data access layer for Cart."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, cart_data: CartCreate) -> CartEntity:
        """
        Create new cart.

        Args:
            cart_data: Cart creation data

        Returns:
            Created cart entity
        """
        cart = CartEntity(**cart_data.model_dump())
        self.db.add(cart)
        await self.db.flush()
        await self.db.refresh(cart)

        logger.info("cart_created", cart_id=str(cart.id))
        return cart

    async def get(self, cart_id: UUID) -> Optional[CartEntity]:
        """
        Get cart by ID.

        Args:
            cart_id: Cart UUID

        Returns:
            Cart entity or None if not found
        """
        result = await self.db.execute(
            select(CartEntity).where(CartEntity.id == cart_id)
        )
        return result.scalar_one_or_none()

    async def list(self, skip: int = 0, limit: int = 100) -> List[CartEntity]:
        """
        List  with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of cart entities
        """
        result = await self.db.execute(
            select(CartEntity).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def count(self) -> int:
        """
        Count total .

        Returns:
            Total count of 
        """
        result = await self.db.execute(
            select(CartEntity)
        )
        return len(result.scalars().all())

    async def update(
        self, cart_id: UUID, cart_data: CartUpdate
    ) -> Optional[CartEntity]:
        """
        Update cart.

        Args:
            cart_id: Cart UUID
            cart_data: Update data

        Returns:
            Updated cart entity or None if not found
        """
        # Get existing cart
        cart = await self.get(cart_id)
        if not cart:
            return None

        # Update only provided fields
        update_data = cart_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(cart, key, value)

        await self.db.flush()
        await self.db.refresh(cart)

        logger.info("cart_updated", cart_id=str(cart_id))
        return cart

    async def delete(self, cart_id: UUID) -> bool:
        """
        Delete cart.

        Args:
            cart_id: Cart UUID

        Returns:
            True if deleted, False if not found
        """
        result = await self.db.execute(
            delete(CartEntity).where(CartEntity.id == cart_id)
        )

        deleted = result.rowcount > 0
        if deleted:
            logger.info("cart_deleted", cart_id=str(cart_id))

        return deleted