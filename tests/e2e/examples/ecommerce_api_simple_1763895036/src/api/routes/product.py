"""
FastAPI Routes for Product

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
from src.models.schemas import ProductCreate, ProductUpdate, ProductResponse
from src.services.product_service import ProductService

router = APIRouter(
    prefix="/products",
    tags=["products"],
)


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create product
    """
    service = ProductService(db)
    product = await service.create(product_data)
    return product


@router.get("/", response_model=List[ProductResponse])
async def list_active_products(
    db: AsyncSession = Depends(get_db)
):
    """
    List active products
    """
    service = ProductService(db)
    products = await service.get_all(skip=0, limit=100)
    return products


@router.get("/{id}", response_model=ProductResponse)
async def get_product_detail(
    id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get product detail
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
async def update_product(
    id: str,
    product_data: ProductCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update product
    """
    service = ProductService(db)
    product = await service.update(id, product_data)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {id} not found"
        )

    return product


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_product(
    id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Deactivate product
    """
    service = ProductService(db)
    success = await service.delete(id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {id} not found"
        )

    return None