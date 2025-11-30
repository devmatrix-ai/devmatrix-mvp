"""
Product Repository

Data access layer for  table.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from uuid import UUID
from typing import Optional, List
from src.models.entities import ProductEntity
from src.models.schemas import ProductCreate, ProductUpdate
import structlog

logger = structlog.get_logger(__name__)


class ProductRepository:
    """Data access layer for Product."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, product_data: ProductCreate) -> ProductEntity:
        """
        Create new product.

        Args:
            product_data: Product creation data

        Returns:
            Created product entity
        """
        product = ProductEntity(**product_data.model_dump())
        self.db.add(product)
        await self.db.flush()
        await self.db.refresh(product)

        logger.info("product_created", product_id=str(product.id))
        return product

    async def get(self, product_id: UUID) -> Optional[ProductEntity]:
        """
        Get product by ID.

        Args:
            product_id: Product UUID

        Returns:
            Product entity or None if not found
        """
        result = await self.db.execute(
            select(ProductEntity).where(ProductEntity.id == product_id)
        )
        return result.scalar_one_or_none()

    async def list(self, skip: int = 0, limit: int = 100) -> List[ProductEntity]:
        """
        List  with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of product entities
        """
        result = await self.db.execute(
            select(ProductEntity).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def count(self) -> int:
        """
        Count total .

        Returns:
            Total count of 
        """
        result = await self.db.execute(
            select(ProductEntity)
        )
        return len(result.scalars().all())

    async def update(
        self, product_id: UUID, product_data: ProductUpdate
    ) -> Optional[ProductEntity]:
        """
        Update product.

        Args:
            product_id: Product UUID
            product_data: Update data

        Returns:
            Updated product entity or None if not found
        """
        # Get existing product
        product = await self.get(product_id)
        if not product:
            return None

        # Update only provided fields
        update_data = product_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(product, key, value)

        await self.db.flush()
        await self.db.refresh(product)

        logger.info("product_updated", product_id=str(product_id))
        return product

    async def delete(self, product_id: UUID) -> bool:
        """
        Delete product.

        Args:
            product_id: Product UUID

        Returns:
            True if deleted, False if not found
        """
        result = await self.db.execute(
            delete(ProductEntity).where(ProductEntity.id == product_id)
        )

        deleted = result.rowcount > 0
        if deleted:
            logger.info("product_deleted", product_id=str(product_id))

        return deleted