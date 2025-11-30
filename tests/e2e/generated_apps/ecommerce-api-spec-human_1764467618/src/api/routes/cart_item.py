"""
FastAPI Routes for CartItem

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
from src.models.schemas import CartItemCreate, CartItemUpdate, CartItemResponse
from src.services.cart_item_service import CartItemService

router = APIRouter(
    prefix="/cart_items",
    tags=["cart_items"],
)