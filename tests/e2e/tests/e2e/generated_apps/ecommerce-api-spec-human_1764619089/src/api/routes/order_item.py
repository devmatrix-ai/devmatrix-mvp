"""
FastAPI Routes for OrderItem

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
from src.models.schemas import OrderItemCreate, OrderItemUpdate, OrderItemResponse
from src.services.order_item_service import OrderItemService

router = APIRouter(
    prefix="/order_items",
    tags=["order_items"],
)