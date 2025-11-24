"""
FastAPI Service for Product

Business logic and data access patterns.
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging

from src.models.schemas import ProductCreate, ProductUpdate, ProductResponse, ProductList
from src.repositories.product_repository import ProductRepository
from src.models.entities import ProductEntity

logger = logging.getLogger(__name__)


class ProductService:
    """Business logic for Product."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ProductRepository(db)

    async def create(self, data: ProductCreate) -> ProductResponse:
        """Create a new product."""
        db_obj = await self.repo.create(data)
        return ProductResponse.model_validate(db_obj)

    async def get(self, id: UUID) -> Optional[ProductResponse]:
        """Get product by ID."""
        db_obj = await self.repo.get(id)
        if db_obj:
            return ProductResponse.model_validate(db_obj)
        return None

    async def get_by_id(self, id: UUID) -> Optional[ProductResponse]:
        """Alias for get() to satisfy routes expecting get_by_id."""
        return await self.get(id)

    async def list(self, page: int = 1, size: int = 10) -> ProductList:
        """List products with pagination."""
        skip = (page - 1) * size

        items = await self.repo.list(skip=skip, limit=size)
        total = await self.repo.count()

        return ProductList(
            items=[ProductResponse.model_validate(t) for t in items],
            total=total,
            page=page,
            size=size,
        )

    async def update(self, id: UUID, data: ProductUpdate) -> Optional[ProductResponse]:
        """Update product."""
        db_obj = await self.repo.update(id, data)
        if db_obj:
            return ProductResponse.model_validate(db_obj)
        return None

    async def delete(self, id: UUID) -> bool:
        """Delete product."""
        return await self.repo.delete(id)