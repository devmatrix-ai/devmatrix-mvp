"""
FastAPI Service for CartItem

Business logic and data access patterns.
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging

from src.models.schemas import CartItemCreate, CartItemUpdate, CartItemResponse, CartItemList
from src.repositories.cart_item_repository import CartItemRepository
from src.models.entities import CartItemEntity

logger = logging.getLogger(__name__)


class CartItemService:
    """Business logic for CartItem."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CartItemRepository(db)

    async def create(self, data: CartItemCreate) -> CartItemResponse:
        """Create a new cartitem."""
        # Bug #142 Fix: Pass Pydantic model directly - repository handles model_dump()
        db_obj = await self.repo.create(data)
        return CartItemResponse.model_validate(db_obj)

    async def get(self, id: UUID) -> Optional[CartItemResponse]:
        """Get cartitem by ID."""
        db_obj = await self.repo.get(id)
        if db_obj:
            return CartItemResponse.model_validate(db_obj)
        return None

    async def get_by_id(self, id: UUID) -> Optional[CartItemResponse]:
        """Alias for get() to satisfy routes expecting get_by_id."""
        return await self.get(id)

    async def list(self, page: int = 1, size: int = 10) -> CartItemList:
        """List cart_items with pagination."""
        skip = (page - 1) * size

        items = await self.repo.list(skip=skip, limit=size)
        total = await self.repo.count()

        return CartItemList(
            items=[CartItemResponse.model_validate(t) for t in items],
            total=total,
            page=page,
            size=size,
        )

    async def update(self, id: UUID, data: CartItemUpdate) -> Optional[CartItemResponse]:
        """Update cartitem."""
        # Bug #142 Fix: Pass Pydantic model directly - repository handles model_dump()
        db_obj = await self.repo.update(id, data)
        if db_obj:
            return CartItemResponse.model_validate(db_obj)
        return None

    async def delete(self, id: UUID) -> bool:
        """Delete cartitem."""
        return await self.repo.delete(id)