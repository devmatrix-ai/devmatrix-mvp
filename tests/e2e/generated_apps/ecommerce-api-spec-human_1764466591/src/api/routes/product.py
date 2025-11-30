"""
FastAPI Routes for Product

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
from src.models.schemas import ProductCreate, ProductUpdate, ProductResponse
from src.services.product_service import ProductService

router = APIRouter(
    prefix="/products",
    tags=["products"],
)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def creates_a_new_product_with_name__description__price__stock_and_status(
    product_data: ProductCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Creates a new product with name, description, price, stock and status
    """
    service = ProductService(db)
    product = await service.create(product_data)
    return product


@router.get("", response_model=List[ProductResponse])
async def returns_a_paginated_list_of_all_active_products__is_active___true_(
    db: AsyncSession = Depends(get_db)
):
    """
    Returns a paginated list of all active products (is_active = true)
    """
    service = ProductService(db)
    result = await service.list(page=1, size=100)
    return result.items


@router.get("/{id}", response_model=ProductResponse)
async def returns_all_information_of_a_specific_product_by_id__returns_404_if_not_found(
    id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns all information of a specific product by ID. Returns 404 if not found
    """
    service = ProductService(db)
    product = await service.get_by_id(id)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {id} not found"
        )

    return product


@router.put("/{id}", response_model=ProductResponse)
async def updates_name__description__price__stock_or_status_of_an_existing_product(
    id: UUID,
    product_data: ProductUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Updates name, description, price, stock or status of an existing product
    """
    service = ProductService(db)
    product = await service.update(id, product_data)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {id} not found"
        )

    return product


@router.post("/{id}/deactivate", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def marks_a_product_as_inactive__is_active___false___product_is_not_deleted__just_hidden(
    id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Marks a product as inactive (is_active = false). Product is not deleted, just hidden
    """
    service = ProductService(db)
    product = await service.deactivate(id)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {id} not found"
        )

    return product


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_a_specific_product_by_id__inferred_best_practice_(
    id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a specific product by ID (inferred best practice)
    """
    service = ProductService(db)
    success = await service.delete(id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {id} not found"
        )

    return None


@router.patch("/{id}/deactivate", response_model=ProductResponse)
async def custom_operation__f5__deactivate_product__inferred_from_flow_(
    id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Custom operation: f5: deactivate product (inferred from flow)
    """
    service = ProductService(db)
    product = await service.deactivate(id)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {id} not found"
        )

    return product


@router.patch("/{id}/activate", response_model=ProductResponse)
async def custom_operation__f5__deactivate_product__inferred_from_flow_(
    id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Custom operation: f5: deactivate product (inferred from flow)
    """
    service = ProductService(db)
    product = await service.activate(id)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {id} not found"
        )

    return product