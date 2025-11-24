"""
FastAPI Routes for Cart

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
from src.models.schemas import CartCreate, CartUpdate, CartResponse
from src.services.cart_service import CartService

router = APIRouter(
    prefix="/carts",
    tags=["carts"],
)


@router.post("/", response_model=CartResponse, status_code=status.HTTP_201_CREATED)
async def create_cart_for_customer(
    cart_data: CartCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create cart for customer
    """
    service = CartService(db)
    cart = await service.create(cart_data)
    return cart


@router.post("/{id}/items", response_model=CartResponse, status_code=status.HTTP_201_CREATED)
async def add_item_to_cart(
    id: str,
    cart_data: CartCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Add item to cart
    """
    service = CartService(db)
    cart = await service.create(cart_data)
    return cart


@router.get("/{id}", response_model=CartResponse)
async def view_current_cart(
    id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    View current cart
    """
    service = CartService(db)
    cart = await service.get_by_id(id)

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart with id {id} not found"
        )

    return cart


@router.put("/{id}/items/{item_id}", response_model=CartResponse)
async def update_item_quantity(
    id: str,
    item_id: str,
    cart_data: CartCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update item quantity
    """
    service = CartService(db)
    cart = await service.update(id, cart_data)

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart with id {id} not found"
        )

    return cart


@router.delete("/{id}/items", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(
    id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Clear cart
    """
    service = CartService(db)
    success = await service.delete(id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart with id {id} not found"
        )

    return None


@router.post("/{id}/checkout", response_model=CartResponse, status_code=status.HTTP_201_CREATED)
async def checkout_cart(
    id: str,
    cart_data: CartCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Checkout cart
    """
    service = CartService(db)
    cart = await service.create(cart_data)
    return cart