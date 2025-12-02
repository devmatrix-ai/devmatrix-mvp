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
    model_config = ConfigDict(json_encoders={UUID: str}, from_attributes=True)


class CartItemBase(BaseSchema):
    """Base schema for cartitem."""
    cart_id: UUID = Field(...)
    product_id: UUID = Field(...)
    quantity: int = Field(..., gt=0, ge=1)
    unit_price: float = Field(..., gt=0, ge=0.01)


class CartItemCreate(BaseSchema):
    """Schema for creating cartitem."""
    product_id: UUID
    quantity: int = Field(..., gt=0, ge=1)


class CartItemUpdate(BaseSchema):
    """Schema for updating cartitem."""
    cart_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    quantity: Optional[int] = Field(None, gt=0, ge=1)
    unit_price: Optional[float] = Field(None, gt=0, ge=0.01)


class CartItemResponse(CartItemBase):
    """Response schema for cartitem."""
    cart_id: UUID
    product_id: UUID
    quantity: int = Field(..., gt=0, ge=1)
    unit_price: float = Field(..., gt=0, ge=0.01)
    id: UUID = Field(...)


class CartItemList(BaseSchema):
    """List response with pagination."""
    items: List[CartItemResponse]
    total: int
    page: int


class OrderItemBase(BaseSchema):
    """Base schema for orderitem."""
    order_id: UUID = Field(...)
    product_id: UUID = Field(...)
    quantity: int = Field(..., gt=0, ge=1)
    unit_price: float = Field(..., gt=0, ge=0.01)


class OrderItemCreate(BaseSchema):
    """Schema for creating orderitem."""
    product_id: UUID
    quantity: int = Field(..., gt=0, ge=1)


class OrderItemUpdate(BaseSchema):
    """Schema for updating orderitem."""
    order_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    quantity: Optional[int] = Field(None, gt=0, ge=1)
    unit_price: Optional[float] = Field(None, gt=0, ge=0.01)


class OrderItemResponse(OrderItemBase):
    """Response schema for orderitem."""
    order_id: UUID
    product_id: UUID
    quantity: int = Field(..., gt=0, ge=1)
    unit_price: float = Field(..., gt=0, ge=0.01)
    id: UUID = Field(...)


class OrderItemList(BaseSchema):
    """List response with pagination."""
    items: List[OrderItemResponse]
    total: int
    page: int


class ProductBase(BaseSchema):
    """Base schema for product."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=255)
    price: float = Field(..., gt=0, ge=0.01)
    stock: int = Field(..., ge=0, gt=0)
    is_active: bool = Field(...)


class ProductCreate(BaseSchema):
    """Schema for creating product."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=255)
    price: float = Field(..., gt=0, ge=0.01)
    stock: int = Field(..., ge=0)
    is_active: bool = True


class ProductUpdate(BaseSchema):
    """Schema for updating product."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=255)
    price: Optional[float] = Field(None, gt=0, ge=0.01)
    stock: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ProductResponse(ProductBase):
    """Response schema for product."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=255)
    price: float = Field(..., gt=0, ge=0.01)
    stock: int = Field(..., ge=0)
    is_active: bool = True
    id: UUID = Field(...)


class ProductList(BaseSchema):
    """List response with pagination."""
    items: List[ProductResponse]
    total: int
    page: int


class CustomerBase(BaseSchema):
    """Base schema for customer."""
    email: str = Field(..., pattern=
        '^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$')
    full_name: str = Field(..., min_length=1, max_length=255)
    registration_date: datetime = Field(..., default_factory=datetime.now)


class CustomerCreate(BaseSchema):
    """Schema for creating customer."""
    email: str = Field(..., pattern='^[^@]+@[^@]+\\.[^@]+$')
    full_name: str = Field(..., min_length=1, max_length=255)
    registration_date: datetime = Field(default_factory=datetime.now)


class CustomerUpdate(BaseSchema):
    """Schema for updating customer."""
    email: Optional[str] = Field(None, pattern='^[^@]+@[^@]+\\.[^@]+$')
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    registration_date: Optional[datetime] = Field(None)


class CustomerResponse(CustomerBase):
    """Response schema for customer."""
    email: str = Field(..., pattern='^[^@]+@[^@]+\\.[^@]+$')
    full_name: str = Field(..., min_length=1, max_length=255)
    registration_date: datetime = Field(default_factory=datetime.now)
    id: UUID = Field(...)


class CustomerList(BaseSchema):
    """List response with pagination."""
    items: List[CustomerResponse]
    total: int
    page: int


class CartBase(BaseSchema):
    """Base schema for cart."""
    customer_id: UUID = Field(...)
    status: Literal['open', 'checked_out'] = Field(..., min_length=1,
        max_length=255)


class CartCreate(BaseSchema):
    """Schema for creating cart."""
    customer_id: UUID
    status: str = Field('OPEN', min_length=1, max_length=255)


class CartUpdate(BaseSchema):
    """Schema for updating cart."""
    customer_id: Optional[UUID] = None
    status: Optional[str] = Field(None, min_length=1, max_length=255)


class CartResponse(CartBase):
    """Response schema for cart."""
    customer_id: UUID
    status: str = Field('OPEN', min_length=1, max_length=255)
    id: UUID = Field(...)


class CartList(BaseSchema):
    """List response with pagination."""
    items: List[CartResponse]
    total: int
    page: int


class OrderBase(BaseSchema):
    """Base schema for order."""
    customer_id: UUID = Field(...)
    order_status: Literal['pending_payment', 'paid', 'cancelled'] = Field(...,
        min_length=1, max_length=255)
    payment_status: Literal['pending', 'simulated_ok', 'failed'] = Field(...,
        min_length=1, max_length=255)
    total_amount: float = Field(..., ge=0, gt=0)
    items: List[OrderItemResponse] = []


class OrderCreate(BaseSchema):
    """Schema for creating order."""
    customer_id: UUID
    order_status: str = Field('PENDING_PAYMENT', min_length=1, max_length=255)
    payment_status: str = Field('PENDING', min_length=1, max_length=255)
    total_amount: float = Field(..., ge=0)
    items: List[OrderItemResponse] = []


class OrderUpdate(BaseSchema):
    """Schema for updating order."""
    customer_id: Optional[UUID] = None
    order_status: Optional[str] = Field(None, min_length=1, max_length=255)
    payment_status: Optional[str] = Field(None, min_length=1, max_length=255)
    total_amount: Optional[float] = Field(None, ge=0)
    items: Optional[List[OrderItemResponse]] = None


class OrderResponse(OrderBase):
    """Response schema for order."""
    customer_id: UUID
    order_status: str = Field('PENDING_PAYMENT', min_length=1, max_length=255)
    payment_status: str = Field('PENDING', min_length=1, max_length=255)
    total_amount: float = Field(..., ge=0)
    items: List[OrderItemResponse] = []
    id: UUID = Field(...)
    created_at: datetime = Field(...)
    created_at: datetime


class OrderList(BaseSchema):
    """List response with pagination."""
    items: List[OrderResponse]
    total: int
    page: int
