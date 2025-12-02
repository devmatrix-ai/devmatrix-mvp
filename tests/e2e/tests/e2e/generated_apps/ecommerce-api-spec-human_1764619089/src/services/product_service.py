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
        # Bug #142 Fix: Pass Pydantic model directly - repository handles model_dump()
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
        # Bug #142 Fix: Pass Pydantic model directly - repository handles model_dump()
        db_obj = await self.repo.update(id, data)
        if db_obj:
            return ProductResponse.model_validate(db_obj)
        return None

    async def delete(self, id: UUID) -> bool:
        """Delete product."""
        return await self.repo.delete(id)

    async def activate(self, id: UUID) -> Optional[ProductResponse]:
        """
        Activate product by setting is_active to True.

        Bug #80a Fix: Custom operation method for activate endpoint.
        """
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        db_obj.is_active = True
        await self.db.flush()
        await self.db.refresh(db_obj)

        logger.info(f"Product activated: product_id=<built-in function id>")
        return ProductResponse.model_validate(db_obj)

    async def deactivate(self, id: UUID) -> Optional[ProductResponse]:
        """
        Deactivate product by setting is_active to False.

        Bug #80a Fix: Custom operation method for deactivate endpoint.
        """
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        db_obj.is_active = False
        await self.db.flush()
        await self.db.refresh(db_obj)

        logger.info(f"Product deactivated: product_id=<built-in function id>")
        return ProductResponse.model_validate(db_obj)

    async def list_actives(self, id: UUID) -> Optional[ProductResponse]:
        """
        F2: List Active Products operation for Product.

        Generated from IR BehaviorModel flow. Bug #143 Fix.
        """
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        # TODO: Implement actual list_actives logic from IR steps
        # For now, log and return the entity
        logger.info(f"Product list_actives: id={str(id)}")
        await self.db.refresh(db_obj)
        return ProductResponse.model_validate(db_obj)

    async def view_details(self, id: UUID) -> Optional[ProductResponse]:
        """
        F3: View Product Details operation for Product.

        Generated from IR BehaviorModel flow. Bug #143 Fix.
        """
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        # TODO: Implement actual view_details logic from IR steps
        # For now, log and return the entity
        logger.info(f"Product view_details: id={str(id)}")
        await self.db.refresh(db_obj)
        return ProductResponse.model_validate(db_obj)

    async def add_item_to_cart(self, id: UUID, data: dict) -> Optional[ProductResponse]:
        """
        F9: Add Item to Cart operation for Product.

        Generated from IR BehaviorModel flow. Bug #143 Fix.
        """
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        # TODO: Implement actual add_item_to_cart logic from IR steps
        # For now, log and return the entity
        logger.info(f"Product add_item_to_cart: id={str(id)}, data={data}")
        await self.db.refresh(db_obj)
        return ProductResponse.model_validate(db_obj)

    async def update_item_quantity(self, id: UUID, data: dict) -> Optional[ProductResponse]:
        """
        F11: Update Item Quantity operation for Product.

        Generated from IR BehaviorModel flow. Bug #143 Fix.
        """
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        # TODO: Implement actual update_item_quantity logic from IR steps
        # For now, log and return the entity
        logger.info(f"Product update_item_quantity: id={str(id)}, data={data}")
        await self.db.refresh(db_obj)
        return ProductResponse.model_validate(db_obj)

    async def checkout(self, id: UUID) -> Optional[ProductResponse]:
        """
        F13: Checkout (Create Order) operation for Product.

        Generated from IR BehaviorModel flow. Bug #143 Fix.
        """
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        # TODO: Implement actual checkout logic from IR steps
        # For now, log and return the entity
        logger.info(f"Product checkout: id={str(id)}")
        await self.db.refresh(db_obj)
        return ProductResponse.model_validate(db_obj)

    async def cancel_order(self, id: UUID) -> Optional[ProductResponse]:
        """
        F15: Cancel Order operation for Product.

        Generated from IR BehaviorModel flow. Bug #143 Fix.
        """
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        # TODO: Implement actual cancel_order logic from IR steps
        # For now, log and return the entity
        logger.info(f"Product cancel_order: id={str(id)}")
        await self.db.refresh(db_obj)
        return ProductResponse.model_validate(db_obj)