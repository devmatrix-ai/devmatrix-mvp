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
        db_obj = await self.repo.update(id, data)
        if db_obj:
            return CustomerResponse.model_validate(db_obj)
        return None

    async def delete(self, id: UUID) -> bool:
        """Delete customer."""
        return await self.repo.delete(id)