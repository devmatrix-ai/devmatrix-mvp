"""
FastAPI Routes for Order

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
from src.models.schemas import OrderCreate, OrderUpdate, OrderResponse
from src.services.order_service import OrderService

router = APIRouter(
    prefix="/orders",
    tags=["orders"],
)


@router.post("/{id}/payment", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def simulate_successful_payment(
    id: str,
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Simulate successful payment
    """
    service = OrderService(db)
    order = await service.create(order_data)
    return order


@router.post("/{id}/cancel", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def cancel_order(
    id: str,
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel order
    """
    service = OrderService(db)
    order = await service.create(order_data)
    return order


@router.get("/{id}", response_model=OrderResponse)
async def get_order_detail(
    id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get order detail
    """
    service = OrderService(db)
    order = await service.get_by_id(id)

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id {id} not found"
        )

    return order