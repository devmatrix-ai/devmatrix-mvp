"""
FastAPI Routes for Customer

Spec-compliant endpoints with:
- Repository pattern integration
- Service layer architecture
- Proper error handling
- Pydantic validation
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.schemas import CustomerCreate, CustomerUpdate, CustomerResponse
from src.services.customer_service import CustomerService

router = APIRouter(
    prefix="/customers",
    tags=["customers"],
)


@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def register_customer(
    customer_data: CustomerCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register customer
    """
    service = CustomerService(db)
    customer = await service.create(customer_data)
    return customer


@router.get("/{id}", response_model=CustomerResponse)
async def get_customer_by_id(
    id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get customer by id
    """
    service = CustomerService(db)
    customer = await service.get_by_id(id)

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with id {id} not found"
        )

    return customer


@router.get("/{id}/orders", response_model=CustomerResponse)
async def list_customer_orders(
    id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    List customer orders
    """
    service = CustomerService(db)
    customer = await service.get_by_id(id)

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with id {id} not found"
        )

    return customer