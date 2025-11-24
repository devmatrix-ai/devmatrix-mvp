"""
Pydantic Request/Response Schemas

Type-safe data validation for API endpoints.
"""
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import List, Optional, Literal
from decimal import Decimal


class BaseSchema(BaseModel):
    """Base schema with UUID-friendly JSON encoding."""

    model_config = ConfigDict(
        json_encoders={UUID: str},
        from_attributes=True,
    )


class CartItem(BaseModel):
    """Item within a cart."""
    product_id: UUID = Field(..., pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., gt=0)


class OrderItem(BaseModel):
    """Item within an order."""
    product_id: UUID = Field(..., pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., gt=0)


class CartItemBase(BaseSchema):
    """Base schema for cartitem."""
    product_id: UUID = Field(..., pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., gt=0)


class CartItemCreate(CartItemBase):
    """Schema for creating cartitem."""
    pass


class CartItemUpdate(BaseSchema):
    """Schema for updating cartitem."""
    product_id: Optional[UUID] = Field(None, pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    quantity: Optional[int] = Field(None, gt=0)
    unit_price: Optional[Decimal] = Field(None, gt=0)


class CartItemResponse(CartItemBase):
    """Response schema for cartitem."""
    product_id: UUID = Field(..., pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., gt=0)
    id: UUID
    created_at: datetime

class CartItemList(BaseSchema):
    """List response with pagination."""
    items: List[CartItemResponse]
    total: int
    page: int


class OrderItemBase(BaseSchema):
    """Base schema for orderitem."""
    product_id: UUID = Field(..., pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., gt=0)


class OrderItemCreate(OrderItemBase):
    """Schema for creating orderitem."""
    pass


class OrderItemUpdate(BaseSchema):
    """Schema for updating orderitem."""
    product_id: Optional[UUID] = Field(None, pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    quantity: Optional[int] = Field(None, gt=0)
    unit_price: Optional[Decimal] = Field(None, gt=0)


class OrderItemResponse(OrderItemBase):
    """Response schema for orderitem."""
    product_id: UUID = Field(..., pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., gt=0)
    id: UUID
    created_at: datetime

class OrderItemList(BaseSchema):
    """List response with pagination."""
    items: List[OrderItemResponse]
    total: int
    page: int


class ProductBase(BaseSchema):
    """Base schema for product."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    price: Decimal = Field(..., gt=0)
    stock: int = Field(..., ge=0)
    is_active: bool


class ProductCreate(ProductBase):
    """Schema for creating product."""
    pass


class ProductUpdate(BaseSchema):
    """Schema for updating product."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    price: Optional[Decimal] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ProductResponse(ProductBase):
    """Response schema for product."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    price: Decimal = Field(..., gt=0)
    stock: int = Field(..., ge=0)
    is_active: bool
    id: UUID = Field(..., pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

class ProductList(BaseSchema):
    """List response with pagination."""
    items: List[ProductResponse]
    total: int
    page: int


class CustomerBase(BaseSchema):
    """Base schema for customer."""
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$", max_length=255)
    full_name: str = Field(..., min_length=1, max_length=255)


class CustomerCreate(CustomerBase):
    """Schema for creating customer."""
    pass


class CustomerUpdate(BaseSchema):
    """Schema for updating customer."""
    email: Optional[str] = Field(None, pattern=r"^[^@]+@[^@]+\.[^@]+$", max_length=255)
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)


class CustomerResponse(CustomerBase):
    """Response schema for customer."""
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$", max_length=255)
    full_name: str = Field(..., min_length=1, max_length=255)
    id: UUID = Field(..., pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    created_at: datetime

class CustomerList(BaseSchema):
    """List response with pagination."""
    items: List[CustomerResponse]
    total: int
    page: int


class CartBase(BaseSchema):
    """Base schema for cart."""
    customer_id: UUID = Field(..., pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    items: List[CartItem]
    status: Literal["OPEN", "CHECKED_OUT"] = Field(..., min_length=1, max_length=255)


class CartCreate(CartBase):
    """Schema for creating cart."""
    pass


class CartUpdate(BaseSchema):
    """Schema for updating cart."""
    customer_id: Optional[UUID] = Field(None, pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    items: Optional[List[CartItem]] = None
    status: Optional[Literal["OPEN", "CHECKED_OUT"]] = Field(None, min_length=1, max_length=255)


class CartResponse(CartBase):
    """Response schema for cart."""
    customer_id: UUID = Field(..., pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    items: List[CartItem]
    status: Literal["OPEN", "CHECKED_OUT"] = Field(..., min_length=1, max_length=255)
    id: UUID = Field(..., pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

class CartList(BaseSchema):
    """List response with pagination."""
    items: List[CartResponse]
    total: int
    page: int


class OrderBase(BaseSchema):
    """Base schema for order."""
    customer_id: UUID = Field(..., pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    items: List[OrderItem]
    total_amount: Decimal = Field(..., ge=0)
    status: Literal["PENDING_PAYMENT", "PAID", "CANCELLED"] = Field(..., min_length=1, max_length=255)
    payment_status: Literal["PENDING", "SIMULATED_OK", "FAILED"] = Field(..., min_length=1, max_length=255)


class OrderCreate(OrderBase):
    """Schema for creating order."""
    pass


class OrderUpdate(BaseSchema):
    """Schema for updating order."""
    customer_id: Optional[UUID] = Field(None, pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    items: Optional[List[OrderItem]] = None
    total_amount: Optional[Decimal] = Field(None, ge=0)
    status: Optional[Literal["PENDING_PAYMENT", "PAID", "CANCELLED"]] = Field(None, min_length=1, max_length=255)
    payment_status: Optional[Literal["PENDING", "SIMULATED_OK", "FAILED"]] = Field(None, min_length=1, max_length=255)


class OrderResponse(OrderBase):
    """Response schema for order."""
    customer_id: UUID = Field(..., pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    items: List[OrderItem]
    total_amount: Decimal = Field(..., ge=0)
    status: Literal["PENDING_PAYMENT", "PAID", "CANCELLED"] = Field(..., min_length=1, max_length=255)
    payment_status: Literal["PENDING", "SIMULATED_OK", "FAILED"] = Field(..., min_length=1, max_length=255)
    id: UUID = Field(..., pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    created_at: datetime

class OrderList(BaseSchema):
    """List response with pagination."""
    items: List[OrderResponse]
    total: int
    page: int