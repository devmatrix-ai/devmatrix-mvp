"""
Test Data Factories

Factory classes for creating test data with realistic defaults.
"""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from typing import Dict, Any, List

from src.models.schemas import ProductCreate, CustomerCreate, CartCreate, CartItemCreate, OrderCreate, OrderItemCreate


class ProductFactory:
    """Factory for creating Product test data."""

    @staticmethod
    def create(**kwargs: Any) -> ProductCreate:
        """
        Create ProductCreate schema with realistic defaults.

        Args:
            **kwargs: Override default values

        Returns:
            ProductCreate schema
        """
        defaults: Dict[str, Any] = {
            "name": f"name_{uuid4().hex[:8]}",
            "description": f"description_{uuid4().hex[:8]}",
            "price": Decimal("99.99"),
            "stock": 0,
            "is_active": True,
        }
        defaults.update(kwargs)
        return ProductCreate(**defaults)

    @staticmethod
    def create_batch(n: int, **kwargs: Any) -> List[ProductCreate]:
        """
        Create multiple ProductCreate schemas.

        Args:
            n: Number of instances to create
            **kwargs: Override default values for all instances

        Returns:
            List of ProductCreate schemas
        """
        return [ProductFactory.create(**kwargs) for _ in range(n)]


class CustomerFactory:
    """Factory for creating Customer test data."""

    @staticmethod
    def create(**kwargs: Any) -> CustomerCreate:
        """
        Create CustomerCreate schema with realistic defaults.

        Args:
            **kwargs: Override default values

        Returns:
            CustomerCreate schema
        """
        defaults: Dict[str, Any] = {
            "email": f"email_{uuid4().hex[:8]}",
            "full_name": f"full_name_{uuid4().hex[:8]}",
            "registration_date": datetime.now(timezone.utc),
        }
        defaults.update(kwargs)
        return CustomerCreate(**defaults)

    @staticmethod
    def create_batch(n: int, **kwargs: Any) -> List[CustomerCreate]:
        """
        Create multiple CustomerCreate schemas.

        Args:
            n: Number of instances to create
            **kwargs: Override default values for all instances

        Returns:
            List of CustomerCreate schemas
        """
        return [CustomerFactory.create(**kwargs) for _ in range(n)]


class CartFactory:
    """Factory for creating Cart test data."""

    @staticmethod
    def create(**kwargs: Any) -> CartCreate:
        """
        Create CartCreate schema with realistic defaults.

        Args:
            **kwargs: Override default values

        Returns:
            CartCreate schema
        """
        defaults: Dict[str, Any] = {
            "customer_id": uuid4(),
            "status": f"status_{uuid4().hex[:8]}",
        }
        defaults.update(kwargs)
        return CartCreate(**defaults)

    @staticmethod
    def create_batch(n: int, **kwargs: Any) -> List[CartCreate]:
        """
        Create multiple CartCreate schemas.

        Args:
            n: Number of instances to create
            **kwargs: Override default values for all instances

        Returns:
            List of CartCreate schemas
        """
        return [CartFactory.create(**kwargs) for _ in range(n)]


class CartItemFactory:
    """Factory for creating CartItem test data."""

    @staticmethod
    def create(**kwargs: Any) -> CartItemCreate:
        """
        Create CartItemCreate schema with realistic defaults.

        Args:
            **kwargs: Override default values

        Returns:
            CartItemCreate schema
        """
        defaults: Dict[str, Any] = {
            "cart_id": uuid4(),
            "product_id": uuid4(),
            "quantity": 0,
            "unit_price": Decimal("99.99"),
        }
        defaults.update(kwargs)
        return CartItemCreate(**defaults)

    @staticmethod
    def create_batch(n: int, **kwargs: Any) -> List[CartItemCreate]:
        """
        Create multiple CartItemCreate schemas.

        Args:
            n: Number of instances to create
            **kwargs: Override default values for all instances

        Returns:
            List of CartItemCreate schemas
        """
        return [CartItemFactory.create(**kwargs) for _ in range(n)]


class OrderFactory:
    """Factory for creating Order test data."""

    @staticmethod
    def create(**kwargs: Any) -> OrderCreate:
        """
        Create OrderCreate schema with realistic defaults.

        Args:
            **kwargs: Override default values

        Returns:
            OrderCreate schema
        """
        defaults: Dict[str, Any] = {
            "customer_id": uuid4(),
            "order_status": f"order_status_{uuid4().hex[:8]}",
            "payment_status": f"payment_status_{uuid4().hex[:8]}",
            "total_amount": Decimal("99.99"),
            "creation_date": datetime.now(timezone.utc),
        }
        defaults.update(kwargs)
        return OrderCreate(**defaults)

    @staticmethod
    def create_batch(n: int, **kwargs: Any) -> List[OrderCreate]:
        """
        Create multiple OrderCreate schemas.

        Args:
            n: Number of instances to create
            **kwargs: Override default values for all instances

        Returns:
            List of OrderCreate schemas
        """
        return [OrderFactory.create(**kwargs) for _ in range(n)]


class OrderItemFactory:
    """Factory for creating OrderItem test data."""

    @staticmethod
    def create(**kwargs: Any) -> OrderItemCreate:
        """
        Create OrderItemCreate schema with realistic defaults.

        Args:
            **kwargs: Override default values

        Returns:
            OrderItemCreate schema
        """
        defaults: Dict[str, Any] = {
            "order_id": uuid4(),
            "product_id": uuid4(),
            "quantity": 0,
            "unit_price": Decimal("99.99"),
        }
        defaults.update(kwargs)
        return OrderItemCreate(**defaults)

    @staticmethod
    def create_batch(n: int, **kwargs: Any) -> List[OrderItemCreate]:
        """
        Create multiple OrderItemCreate schemas.

        Args:
            n: Number of instances to create
            **kwargs: Override default values for all instances

        Returns:
            List of OrderItemCreate schemas
        """
        return [OrderItemFactory.create(**kwargs) for _ in range(n)]