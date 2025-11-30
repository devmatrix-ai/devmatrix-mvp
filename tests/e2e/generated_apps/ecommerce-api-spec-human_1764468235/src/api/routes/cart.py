"""
FastAPI Routes for Cart

Spec-compliant endpoints with:
- Repository pattern integration
- Service layer architecture
- Proper error handling
- Pydantic validation
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.schemas import CartCreate, CartUpdate, CartResponse, CartItemCreate, CartItemUpdate
from src.services.cart_service import CartService

router = APIRouter(
    prefix="/carts",
    tags=["carts"],
)


@router.post("", response_model=CartResponse, status_code=status.HTTP_201_CREATED)
async def creates_an_open_cart_for_a_customer__if_an_open_cart_already_exists__it_reuses_it_instead_of_creating_a_new_one(
    cart_data: CartCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Creates an OPEN cart for a customer. If an OPEN cart already exists, it reuses it instead of creating a new one
    """
    service = CartService(db)
    cart = await service.create(cart_data)
    return cart


@router.get("/{id}", response_model=CartResponse)
async def returns_the_customer_s_open_cart_with_all_items_and_subtotals(
    id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the customer's OPEN cart with all items and subtotals
    """
    service = CartService(db)
    cart = await service.get_by_id(id)

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart with id {id} not found"
        )

    return cart


@router.post("/{id}/items", response_model=CartResponse, status_code=status.HTTP_201_CREATED)
async def adds_a_product_with_quantity_to_the_cart__validates_product_is_active__has_sufficient_stock__if_product_already_in_cart__increases_quantity_instead_of_duplicating__captures_current_price_as_unit_price(
    id: UUID,
    cart_item_data: CartItemCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Adds a product with quantity to the cart. Validates product is active, has sufficient stock. If product already in cart, increases quantity instead of duplicating. Captures current price as unit_price
    """
    service = CartService(db)
    cart = await service.add_item(id, cart_item_data.model_dump() if hasattr(cart_item_data, 'model_dump') else cart_item_data)

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart with id {id} not found"
        )

    return cart


@router.put("/{cart_id}/items/{item_id}", response_model=CartResponse)
async def changes_the_quantity_of_a_product_in_the_cart__if_quantity____0__removes_the_item__if_quantity___available_stock__returns_400_error(
    cart_id: UUID,
    item_id: UUID,
    cart_data: CartUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Changes the quantity of a product in the cart. If quantity <= 0, removes the item. If quantity > available stock, returns 400 error
    """
    service = CartService(db)
    cart = await service.update(cart_id, cart_data)

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart with id {cart_id} not found"
        )

    return cart


@router.post("/{id}/clear", response_model=CartResponse, status_code=status.HTTP_201_CREATED)
async def removes_all_items_from_the_open_cart(
    id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Removes all items from the OPEN cart
    """
    service = CartService(db)
    cart = await service.clear_items(id)

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart with id {id} not found"
        )

    return cart


@router.get("", response_model=List[CartResponse])
async def retrieve_a_list_of_all_carts__inferred_best_practice_(
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve a list of all carts (inferred best practice)
    """
    service = CartService(db)
    result = await service.list(page=1, size=100)
    return result.items


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_a_specific_cart_by_id__inferred_best_practice_(
    id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a specific cart by ID (inferred best practice)
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
async def custom_operation__f13__checkout__create_order___inferred_from_flow_(
    id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Custom operation: f13: checkout (create order) (inferred from flow)
    """
    service = CartService(db)
    cart = await service.checkout(id)

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart with id {id} not found"
        )

    return cart


@router.delete("/{id}/items/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item_from_cart__nested_resource_(
    id: UUID,
    product_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Remove item from cart (nested resource)
    """
    service = CartService(db)
    success = await service.delete(id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart with id {id} not found"
        )

    return None