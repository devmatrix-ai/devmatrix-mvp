"""
FastAPI Service for Customer

Business logic and data access patterns.
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging

from src.models.schemas import CustomerCreate, CustomerUpdate, CustomerResponse, CustomerList
from src.repositories.customer_repository import CustomerRepository
from src.models.entities import CustomerEntity

logger = logging.getLogger(__name__)


class CustomerService:
    """Business logic for Customer."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CustomerRepository(db)

    async def create(self, data: CustomerCreate) -> CustomerResponse:
        """Create a new customer."""
        # Bug #142 Fix: Pass Pydantic model directly - repository handles model_dump()
        db_obj = await self.repo.create(data)
        return CustomerResponse.model_validate(db_obj)

    async def get(self, id: UUID) -> Optional[CustomerResponse]:
        """Get customer by ID."""
        db_obj = await self.repo.get(id)
        if db_obj:
            return CustomerResponse.model_validate(db_obj)
        return None

    async def get_by_id(self, id: UUID) -> Optional[CustomerResponse]:
        """Alias for get() to satisfy routes expecting get_by_id."""
        return await self.get(id)

    async def list(self, page: int = 1, size: int = 10) -> CustomerList:
        """List customers with pagination."""
        skip = (page - 1) * size

        items = await self.repo.list(skip=skip, limit=size)
        total = await self.repo.count()

        return CustomerList(
            items=[CustomerResponse.model_validate(t) for t in items],
            total=total,
            page=page,
            size=size,
        )

    async def update(self, id: UUID, data: CustomerUpdate) -> Optional[CustomerResponse]:
        """Update customer."""
        # Bug #142 Fix: Pass Pydantic model directly - repository handles model_dump()
        db_obj = await self.repo.update(id, data)
        if db_obj:
            return CustomerResponse.model_validate(db_obj)
        return None

    async def delete(self, id: UUID) -> bool:
        """Delete customer."""
        return await self.repo.delete(id)

    async def register(self, id: UUID) -> Optional[CustomerResponse]:
        """
        F6: Register Customer operation for Customer.

        Generated from IR BehaviorModel flow. Bug #143 Fix.
        """
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        # TODO: Implement actual register logic from IR steps
        # For now, log and return the entity
        logger.info(f"Customer register: id={str(id)}")
        await self.db.refresh(db_obj)
        return CustomerResponse.model_validate(db_obj)

    async def view_details(self, id: UUID) -> Optional[CustomerResponse]:
        """
        F7: View Customer Details operation for Customer.

        Generated from IR BehaviorModel flow. Bug #143 Fix.
        """
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        # TODO: Implement actual view_details logic from IR steps
        # For now, log and return the entity
        logger.info(f"Customer view_details: id={str(id)}")
        await self.db.refresh(db_obj)
        return CustomerResponse.model_validate(db_obj)

    async def create_cart(self, id: UUID) -> Optional[CustomerResponse]:
        """
        F8: Create Cart operation for Customer.

        Generated from IR BehaviorModel flow. Bug #143 Fix.
        """
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        # TODO: Implement actual create_cart logic from IR steps
        # For now, log and return the entity
        logger.info(f"Customer create_cart: id={str(id)}")
        await self.db.refresh(db_obj)
        return CustomerResponse.model_validate(db_obj)

    async def list_orders(self, id: UUID) -> Optional[CustomerResponse]:
        """
        F16: List Customer Orders operation for Customer.

        Generated from IR BehaviorModel flow. Bug #143 Fix.
        """
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        # TODO: Implement actual list_orders logic from IR steps
        # For now, log and return the entity
        logger.info(f"Customer list_orders: id={str(id)}")
        await self.db.refresh(db_obj)
        return CustomerResponse.model_validate(db_obj)