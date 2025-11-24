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
        db_obj = await self.repo.update(id, data)
        if db_obj:
            return CartResponse.model_validate(db_obj)
        return None

    async def delete(self, id: UUID) -> bool:
        """Delete cart."""
        return await self.repo.delete(id)