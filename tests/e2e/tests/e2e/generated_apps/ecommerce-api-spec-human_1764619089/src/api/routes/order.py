"""
FastAPI Routes for Order

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
from src.models.schemas import OrderCreate, OrderUpdate, OrderResponse, OrderItemCreate, OrderItemUpdate
from src.services.order_service import OrderService
router = APIRouter(prefix='/orders', tags=['orders'])


@router.post('', response_model=OrderResponse, status_code=status.
    HTTP_201_CREATED)
async def customer_finalizes_purchase__validates_cart_not_empty__validates_stock_for_all_items__subtracts_stock__creates_order_with_pending_payment_status__marks_cart_as_checked_out__calculates_total_amount(
    order_data: OrderCreate, db: AsyncSession=Depends(get_db)):
    """
    Customer finalizes purchase. Validates cart not empty, validates stock for all items, subtracts stock, creates order with PENDING_PAYMENT status, marks cart as CHECKED_OUT, calculates total amount
    """
    service = OrderService(db)
    order = await service.create(order_data)
    return order


@router.post('/{id}/pay', response_model=OrderResponse, status_code=status.
    HTTP_201_CREATED)
async def marks_an_order_as_paid__current_status_must_be_pending_payment__changes_to_paid_and_payment_status_to_simulated_ok(
    id: UUID, db: AsyncSession=Depends(get_db)):
    """
    Marks an order as paid. Current status must be PENDING_PAYMENT. Changes to PAID and payment_status to SIMULATED_OK
    """
    service = OrderService(db)
    existing = await service.get(id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=
            f'Order with id {id} not found')
    order = await service.pay(id)
    return order


@router.post('/{id}/cancel', response_model=OrderResponse, status_code=
    status.HTTP_201_CREATED)
async def cancels_an_order_and_returns_stock__current_status_must_be_pending_payment__changes_to_cancelled_and_adds_back_quantity_to_products(
    id: UUID, db: AsyncSession=Depends(get_db)):
    """
    Cancels an order and returns stock. Current status must be PENDING_PAYMENT. Changes to CANCELLED and adds back quantity to products
    """
    service = OrderService(db)
    existing = await service.get(id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=
            f'Order with id {id} not found')
    order = await service.cancel(id)
    return order


@router.get('/{id}', response_model=OrderResponse)
async def returns_all_information_of_an_order_by_id__returns_404_if_not_found(
    id: UUID, db: AsyncSession=Depends(get_db)):
    """
    Returns all information of an order by ID. Returns 404 if not found
    """
    service = OrderService(db)
    order = await service.get_by_id(id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=
            f'Order with id {id} not found')
    return order


@router.get('', response_model=List[OrderResponse])
async def retrieve_a_list_of_all_orders__inferred_best_practice_(db:
    AsyncSession=Depends(get_db)):
    """
    Retrieve a list of all orders (inferred best practice)
    """
    service = OrderService(db)
    result = await service.list(page=1, size=100)
    return result.items


@router.delete('/{id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_a_specific_order_by_id__inferred_best_practice_(id: UUID,
    db: AsyncSession=Depends(get_db)):
    """
    Delete a specific order by ID (inferred best practice)
    """
    service = OrderService(db)
    success = await service.delete(id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=
            f'Order with id {id} not found')
    return None


@router.put('/{id}/items/{product_id}', response_model=OrderResponse)
async def add_update_item_in_order__nested_resource_(id: UUID, product_id:
    UUID, order_item_data: OrderItemUpdate, db: AsyncSession=Depends(get_db)):
    """
    Add/update item in order (nested resource)
    """
    service = OrderService(db)
    existing = await service.get(id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=
            f'Order with id {id} not found')
    order = await service.update(id, order_item_data)
    return order


@router.delete('/{id}/items/{product_id}', status_code=status.
    HTTP_204_NO_CONTENT)
async def remove_item_from_order__nested_resource_(id: UUID, product_id:
    UUID, db: AsyncSession=Depends(get_db)):
    """
    Remove item from order (nested resource)
    """
    service = OrderService(db)
    success = await service.delete(id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=
            f'Order with id {id} not found')
    return None


@router.post('/')
async def create_order(data: OrderCreate, db: AsyncSession=Depends(get_db)):
    service = OrderService(db)
    return await service.create(data)


@router.get('/')
async def list_orders(db: AsyncSession=Depends(get_db)):
    service = OrderService(db)
    result = await service.list(page=1, size=100)
    return result.items


@router.delete('/')
async def delete_order(id: str, db: AsyncSession=Depends(get_db)):
    service = OrderService(db)
    return await service.delete(id)


@router.put('/')
async def update_order(id: str, data: OrderUpdate, db: AsyncSession=Depends
    (get_db)):
    service = OrderService(db)
    existing = await service.get(id)
    if not existing:
        raise HTTPException(status_code=404, detail='Order not found')
    return await service.update(id, data)
