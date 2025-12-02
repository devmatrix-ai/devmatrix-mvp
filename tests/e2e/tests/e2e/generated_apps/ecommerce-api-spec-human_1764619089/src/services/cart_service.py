"""
FastAPI Service for Cart

Business logic and data access patterns.
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging

from src.models.schemas import CartCreate, CartUpdate, CartResponse, CartList
from src.repositories.cart_repository import CartRepository
from src.models.entities import CartEntity

logger = logging.getLogger(__name__)


class CartService:
    """Business logic for Cart."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CartRepository(db)

    async def create(self, data: CartCreate) -> CartResponse:
        """Create a new cart."""
        # Bug #142 Fix: Pass Pydantic model directly - repository handles model_dump()
        db_obj = await self.repo.create(data)
        return CartResponse.model_validate(db_obj)

    async def get(self, id: UUID) -> Optional[CartResponse]:
        """Get cart by ID."""
        db_obj = await self.repo.get(id)
        if db_obj:
            return CartResponse.model_validate(db_obj)
        return None

    async def get_by_id(self, id: UUID) -> Optional[CartResponse]:
        """Alias for get() to satisfy routes expecting get_by_id."""
        return await self.get(id)

    async def list(self, page: int = 1, size: int = 10) -> CartList:
        """List carts with pagination."""
        skip = (page - 1) * size

        items = await self.repo.list(skip=skip, limit=size)
        total = await self.repo.count()

        return CartList(
            items=[CartResponse.model_validate(t) for t in items],
            total=total,
            page=page,
            size=size,
        )

    async def update(self, id: UUID, data: CartUpdate) -> Optional[CartResponse]:
        """Update cart."""
        # Bug #142 Fix: Pass Pydantic model directly - repository handles model_dump()
        db_obj = await self.repo.update(id, data)
        if db_obj:
            return CartResponse.model_validate(db_obj)
        return None

    async def delete(self, id: UUID) -> bool:
        """Delete cart."""
        return await self.repo.delete(id)

    async def clear_items(self, id: UUID) -> Optional[CartResponse]:
        """
        Clear all items/children from this cart.

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
        from src.models.entities import CartItemEntity
        await self.db.execute(
            delete(CartItemEntity).where(CartItemEntity.cart_id == id)
        )
        await self.db.flush()

        # Return the updated entity
        refreshed = await self.repo.get(id)
        return CartResponse.model_validate(refreshed) if refreshed else None

    async def add_item(self, id: UUID, data: dict) -> Optional[CartResponse]:
        """
        F9: Add Item to Cart operation for Cart.

        Generated from IR BehaviorModel flow. Bug #143 Fix.
        """
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        # TODO: Implement actual add_item logic from IR steps
        # For now, log and return the entity
        logger.info(f"Cart add_item: id={str(id)}, data={data}")
        await self.db.refresh(db_obj)
        return CartResponse.model_validate(db_obj)

    async def view_current(self, id: UUID) -> Optional[CartResponse]:
        """
        F10: View Current Cart operation for Cart.

        Generated from IR BehaviorModel flow. Bug #143 Fix.
        """
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        # TODO: Implement actual view_current logic from IR steps
        # For now, log and return the entity
        logger.info(f"Cart view_current: id={str(id)}")
        await self.db.refresh(db_obj)
        return CartResponse.model_validate(db_obj)

    async def update_item_quantity(self, id: UUID, data: dict) -> Optional[CartResponse]:
        """
        F11: Update Item Quantity operation for Cart.

        Generated from IR BehaviorModel flow. Bug #143 Fix.
        """
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        # TODO: Implement actual update_item_quantity logic from IR steps
        # For now, log and return the entity
        logger.info(f"Cart update_item_quantity: id={str(id)}, data={data}")
        await self.db.refresh(db_obj)
        return CartResponse.model_validate(db_obj)

    async def empty(self, id: UUID) -> Optional[CartResponse]:
        """
        F12: Empty Cart operation for Cart.

        Generated from IR BehaviorModel flow. Bug #143 Fix.
        """
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        # TODO: Implement actual empty logic from IR steps
        # For now, log and return the entity
        logger.info(f"Cart empty: id={str(id)}")
        await self.db.refresh(db_obj)
        return CartResponse.model_validate(db_obj)

    async def checkout(self, id: UUID) -> Optional[CartResponse]:
        """
        F13: Checkout (Create Order) operation for Cart.

        Generated from IR BehaviorModel flow. Bug #143 Fix.
        """
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        # TODO: Implement actual checkout logic from IR steps
        # For now, log and return the entity
        logger.info(f"Cart checkout: id={str(id)}")
        await self.db.refresh(db_obj)
        return CartResponse.model_validate(db_obj)