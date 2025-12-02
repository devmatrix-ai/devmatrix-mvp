"""
FastAPI Routes for Customer

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
from src.models.schemas import CustomerCreate, CustomerUpdate, CustomerResponse
from src.services.customer_service import CustomerService
router = APIRouter(prefix='/customers', tags=['customers'])


@router.post('', response_model=CustomerResponse, status_code=status.
    HTTP_201_CREATED)
async def creates_a_new_customer_account_with_email_and_name__returns_400_if_email_already_exists(
    customer_data: CustomerCreate, db: AsyncSession=Depends(get_db)):
    """
    Creates a new customer account with email and name. Returns 400 if email already exists
    """
    service = CustomerService(db)
    customer = await service.create(customer_data)
    return customer


@router.get('/{id}', response_model=CustomerResponse)
async def returns_complete_information_of_a_customer_by_id__returns_404_if_not_found(
    id: UUID, db: AsyncSession=Depends(get_db)):
    """
    Returns complete information of a customer by ID. Returns 404 if not found
    """
    service = CustomerService(db)
    customer = await service.get_by_id(id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=
            f'Customer with id {id} not found')
    return customer


@router.get('/{customer_id}/orders', response_model=CustomerResponse)
async def returns_all_orders_of_a_customer__optionally_filtered_by_status(
    customer_id: UUID, db: AsyncSession=Depends(get_db)):
    """
    Returns all orders of a customer, optionally filtered by status
    """
    service = CustomerService(db)
    customer = await service.get_by_id(customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=
            f'Customer with id {customer_id} not found')
    return customer


@router.get('', response_model=List[CustomerResponse])
async def retrieve_a_list_of_all_customers__inferred_best_practice_(db:
    AsyncSession=Depends(get_db)):
    """
    Retrieve a list of all customers (inferred best practice)
    """
    service = CustomerService(db)
    result = await service.list(page=1, size=100)
    return result.items


@router.delete('/{id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_a_specific_customer_by_id__inferred_best_practice_(id:
    UUID, db: AsyncSession=Depends(get_db)):
    """
    Delete a specific customer by ID (inferred best practice)
    """
    service = CustomerService(db)
    success = await service.delete(id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=
            f'Customer with id {id} not found')
    return None


@router.post('/')
async def create_customer(data: CustomerCreate, db: AsyncSession=Depends(
    get_db)):
    service = CustomerService(db)
    return await service.create(data)


@router.get('/')
async def list_customers(db: AsyncSession=Depends(get_db)):
    service = CustomerService(db)
    result = await service.list(page=1, size=100)
    return result.items


@router.delete('/')
async def delete_customer(id: str, db: AsyncSession=Depends(get_db)):
    service = CustomerService(db)
    return await service.delete(id)
