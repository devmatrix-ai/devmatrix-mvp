"""
Customer Repository

Data access layer for  table.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from uuid import UUID
from typing import Optional, List
from src.models.entities import CustomerEntity
from src.models.schemas import CustomerCreate, CustomerUpdate
import structlog

logger = structlog.get_logger(__name__)


class CustomerRepository:
    """Data access layer for Customer."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, customer_data: CustomerCreate) -> CustomerEntity:
        """
        Create new customer.

        Args:
            customer_data: Customer creation data

        Returns:
            Created customer entity
        """
        customer = CustomerEntity(**customer_data.model_dump())
        self.db.add(customer)
        await self.db.flush()
        await self.db.refresh(customer)

        logger.info("customer_created", customer_id=str(customer.id))
        return customer

    async def get(self, customer_id: UUID) -> Optional[CustomerEntity]:
        """
        Get customer by ID.

        Args:
            customer_id: Customer UUID

        Returns:
            Customer entity or None if not found
        """
        result = await self.db.execute(
            select(CustomerEntity).where(CustomerEntity.id == customer_id)
        )
        return result.scalar_one_or_none()

    async def list(self, skip: int = 0, limit: int = 100) -> List[CustomerEntity]:
        """
        List  with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of customer entities
        """
        result = await self.db.execute(
            select(CustomerEntity).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def count(self) -> int:
        """
        Count total .

        Returns:
            Total count of 
        """
        result = await self.db.execute(
            select(CustomerEntity)
        )
        return len(result.scalars().all())

    async def update(
        self, customer_id: UUID, customer_data: CustomerUpdate
    ) -> Optional[CustomerEntity]:
        """
        Update customer.

        Args:
            customer_id: Customer UUID
            customer_data: Update data

        Returns:
            Updated customer entity or None if not found
        """
        # Get existing customer
        customer = await self.get(customer_id)
        if not customer:
            return None

        # Update only provided fields
        update_data = customer_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(customer, key, value)

        await self.db.flush()
        await self.db.refresh(customer)

        logger.info("customer_updated", customer_id=str(customer_id))
        return customer

    async def delete(self, customer_id: UUID) -> bool:
        """
        Delete customer.

        Args:
            customer_id: Customer UUID

        Returns:
            True if deleted, False if not found
        """
        result = await self.db.execute(
            delete(CustomerEntity).where(CustomerEntity.id == customer_id)
        )

        deleted = result.rowcount > 0
        if deleted:
            logger.info("customer_deleted", customer_id=str(customer_id))

        return deleted