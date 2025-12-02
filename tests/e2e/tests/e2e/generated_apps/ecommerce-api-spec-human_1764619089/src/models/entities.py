"""
SQLAlchemy ORM Models

Database entity definitions with proper table names and columns.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid
from src.core.database import Base


class ProductEntity(Base):
    """SQLAlchemy model for products table."""
    __tablename__ = 'products'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        unique=True)
    cart_items = relationship('CartItemEntity', lazy='selectin',
        back_populates='product')
    order_items = relationship('OrderItemEntity', lazy='selectin',
        back_populates='product')
    name = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    stock = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda : datetime.
        now(timezone.utc))

    def __repr__(self):
        return f"<Product {self.id}: {getattr(self, 'name', 'N/A')}>"


class CustomerEntity(Base):
    """SQLAlchemy model for customers table."""
    __tablename__ = 'customers'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        unique=True)
    carts = relationship('CartEntity', lazy='selectin', back_populates=
        'customer')
    orders = relationship('OrderEntity', lazy='selectin', back_populates=
        'customer')
    email = Column(String(255), nullable=False, unique=True)
    full_name = Column(String(255), nullable=False)
    registration_date = Column(DateTime(timezone=True), nullable=False,
        default=lambda : datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda : datetime.
        now(timezone.utc))

    def __repr__(self):
        return f"<Customer {self.id}: {getattr(self, 'email', 'N/A')}>"


class CartEntity(Base):
    """SQLAlchemy model for carts table."""
    __tablename__ = 'carts'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        unique=True)
    customer = relationship('CustomerEntity', lazy='select', back_populates
        ='carts')
    items = relationship('CartItemEntity', lazy='selectin', back_populates=
        'cart')
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.id'),
        nullable=False)
    status = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda : datetime.
        now(timezone.utc))

    def __repr__(self):
        return f"<Cart {self.id}: {getattr(self, 'customer_id', 'N/A')}>"


class CartItemEntity(Base):
    """SQLAlchemy model for cartitems table."""
    __tablename__ = 'cartitems'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        unique=True)
    cart = relationship('CartEntity', lazy='select', back_populates='items')
    product = relationship('ProductEntity', lazy='select', back_populates=
        'cart_items')
    cart_id = Column(UUID(as_uuid=True), ForeignKey('carts.id'), nullable=False
        )
    product_id = Column(UUID(as_uuid=True), ForeignKey('products.id'),
        nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda : datetime.
        now(timezone.utc))

    def __repr__(self):
        return f"<CartItem {self.id}: {getattr(self, 'cart_id', 'N/A')}>"


class OrderEntity(Base):
    """SQLAlchemy model for orders table."""
    __tablename__ = 'orders'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        unique=True)
    customer = relationship('CustomerEntity', lazy='select', back_populates
        ='orders')
    items = relationship('OrderItemEntity', lazy='selectin', back_populates
        ='order')
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.id'),
        nullable=False)
    order_status = Column(String(255), nullable=False)
    payment_status = Column(String(255), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda : datetime.
        now(timezone.utc))

    def __repr__(self):
        return f"<Order {self.id}: {getattr(self, 'customer_id', 'N/A')}>"


class OrderItemEntity(Base):
    """SQLAlchemy model for orderitems table."""
    __tablename__ = 'orderitems'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        unique=True)
    order = relationship('OrderEntity', lazy='select', back_populates='items')
    product = relationship('ProductEntity', lazy='select', back_populates=
        'order_items')
    order_id = Column(UUID(as_uuid=True), ForeignKey('orders.id'), nullable
        =False)
    product_id = Column(UUID(as_uuid=True), ForeignKey('products.id'),
        nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda : datetime.
        now(timezone.utc))

    def __repr__(self):
        return f"<OrderItem {self.id}: {getattr(self, 'order_id', 'N/A')}>"
