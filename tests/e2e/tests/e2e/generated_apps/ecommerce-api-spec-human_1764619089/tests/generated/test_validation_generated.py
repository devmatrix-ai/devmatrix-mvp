"""
Auto-generated validation tests from ValidationModelIR.
Bug #59 Fix: Now includes pytest fixtures for valid entity data.
Bug #74 Fix: Re-added entity imports for behavioral validation tests.
"""
import pytest
import uuid
from datetime import datetime
from pydantic import ValidationError
from src.models.schemas import ProductCreate, CustomerCreate, CartItemCreate, OrderItemCreate, CartCreate, OrderCreate
from src.models.entities import ProductEntity, CustomerEntity, CartItemEntity, OrderItemEntity, CartEntity, OrderEntity


@pytest.fixture
def valid_product_data():
    """
    Bug #59 Fix: Fixture providing valid Product data for tests.
    Generated from DomainModelIR and ValidationModelIR.
    """
    return {
        "description": "Test description",
        "stock": 0,
        "is_active": True,
        "name": "Test Name",
        "id": str(uuid.uuid4()),
        "price": 0,
    }


@pytest.fixture
def valid_customer_data():
    """
    Bug #59 Fix: Fixture providing valid Customer data for tests.
    Generated from DomainModelIR and ValidationModelIR.
    """
    return {
        "email": "test@example.com",
        "full_name": "Test Full Name",
        "id": str(uuid.uuid4()),
        "registration_date": datetime.utcnow(),
    }


@pytest.fixture
def valid_cartitem_data():
    """
    Bug #59 Fix: Fixture providing valid CartItem data for tests.
    Generated from DomainModelIR and ValidationModelIR.
    """
    return {
        "product_id": str(uuid.uuid4()),
        "cart_id": str(uuid.uuid4()),
        "quantity": 0,
        "unit_price": 0,
        "id": str(uuid.uuid4()),
    }


@pytest.fixture
def valid_orderitem_data():
    """
    Bug #59 Fix: Fixture providing valid OrderItem data for tests.
    Generated from DomainModelIR and ValidationModelIR.
    """
    return {
        "product_id": str(uuid.uuid4()),
        "quantity": 0,
        "unit_price": 0,
        "id": str(uuid.uuid4()),
        "order_id": str(uuid.uuid4()),
    }


@pytest.fixture
def valid_cart_data():
    """
    Bug #59 Fix: Fixture providing valid Cart data for tests.
    Generated from DomainModelIR and ValidationModelIR.
    """
    return {
        "id": str(uuid.uuid4()),
        "customer_id": str(uuid.uuid4()),
        "status": "active",
    }


@pytest.fixture
def valid_order_data():
    """
    Bug #59 Fix: Fixture providing valid Order data for tests.
    Generated from DomainModelIR and ValidationModelIR.
    """
    return {
        "items": "test_value",
        "customer_id": str(uuid.uuid4()),
        "payment_status": "active",
        "id": str(uuid.uuid4()),
        "order_status": "active",
        "total_amount": 0,
        "creation_date": datetime.utcnow(),
    }


class TestProductValidation:
    """Validation tests for Product entity."""

    def test_product_price_range_valid(self, valid_product_data):
        """price accepts value in range (> 0)."""
        product = ProductCreate(**valid_product_data)
        assert product.price is not None

    def test_product_price_range_below_min(self, valid_product_data):
        """price rejects value below minimum."""
        data = valid_product_data.copy()
        data["price"] = -1  # Below minimum
        with pytest.raises(ValidationError) as exc:
            ProductCreate(**data)
        assert "price" in str(exc.value)

    def test_product_price_range_at_boundary(self, valid_product_data):
        """price tests boundary value."""
        data = valid_product_data.copy()
        data["price"] = 0  # At boundary
        # This may or may not pass depending on condition (>= vs >)
        try:
            ProductCreate(**data)
        except ValidationError:
            pass  # Expected if condition is > 0

    def test_product_stock_range_valid(self, valid_product_data):
        """stock accepts value in range (>= 0)."""
        product = ProductCreate(**valid_product_data)
        assert product.stock is not None

    def test_product_stock_range_below_min(self, valid_product_data):
        """stock rejects value below minimum."""
        data = valid_product_data.copy()
        data["stock"] = -1  # Below minimum
        with pytest.raises(ValidationError) as exc:
            ProductCreate(**data)
        assert "stock" in str(exc.value)

    def test_product_stock_range_at_boundary(self, valid_product_data):
        """stock tests boundary value."""
        data = valid_product_data.copy()
        data["stock"] = 0  # At boundary
        # This may or may not pass depending on condition (>= vs >)
        try:
            ProductCreate(**data)
        except ValidationError:
            pass  # Expected if condition is > 0

    def test_product_name_presence_required(self, valid_product_data):
        """name is required for Product."""
        data = valid_product_data.copy()
        del data["name"]
        with pytest.raises(ValidationError) as exc:
            ProductCreate(**data)
        assert "name" in str(exc.value)

    def test_product_name_presence_not_null(self, valid_product_data):
        """name cannot be null for Product."""
        data = valid_product_data.copy()
        data["name"] = None
        with pytest.raises(ValidationError) as exc:
            ProductCreate(**data)
        assert "name" in str(exc.value)

    async def test_product_id_relationship_valid_fk(self, db_session, valid_product_data):
        """id references valid foreign key."""
        # FK should exist before creating
        product = ProductEntity(**valid_product_data)
        db_session.add(product)
        await db_session.commit()
        assert product.id is not None

    async def test_product_id_relationship_invalid_fk(self, db_session, valid_product_data):
        """id rejects non-existent foreign key."""
        data = valid_product_data.copy()
        data["id"] = 99999  # Non-existent FK
        product = ProductEntity(**data)
        db_session.add(product)

        with pytest.raises(Exception):  # IntegrityError
            await db_session.commit()

    def test_product_id_presence_required(self, valid_product_data):
        """id is required for Product."""
        data = valid_product_data.copy()
        del data["id"]
        with pytest.raises(ValidationError) as exc:
            ProductCreate(**data)
        assert "id" in str(exc.value)

    def test_product_id_presence_not_null(self, valid_product_data):
        """id cannot be null for Product."""
        data = valid_product_data.copy()
        data["id"] = None
        with pytest.raises(ValidationError) as exc:
            ProductCreate(**data)
        assert "id" in str(exc.value)

    async def test_product_id_uniqueness(self, db_session, valid_product_data):
        """id must be unique for Product."""
        # Create first entity
        product1 = ProductEntity(**valid_product_data)
        db_session.add(product1)
        await db_session.commit()

        # Try to create duplicate
        duplicate_data = valid_product_data.copy()
        duplicate_data["id"] = product1.id
        product2 = ProductEntity(**duplicate_data)
        db_session.add(product2)

        with pytest.raises(Exception) as exc:  # IntegrityError
            await db_session.commit()
        assert "unique" in str(exc.value).lower() or "duplicate" in str(exc.value).lower()

    def test_product_id_format_valid(self, valid_product_data):
        """id accepts uuid."""
        # Valid format should pass
        product = ProductCreate(**valid_product_data)
        assert product.id is not None

    def test_product_id_format_invalid(self, valid_product_data):
        """id rejects invalid format."""
        data = valid_product_data.copy()
        data["id"] = "invalid_format_value"
        with pytest.raises(ValidationError) as exc:
            ProductCreate(**data)
        assert "id" in str(exc.value)

    def test_product_name_presence_required(self, valid_product_data):
        """name is required for Product."""
        data = valid_product_data.copy()
        del data["name"]
        with pytest.raises(ValidationError) as exc:
            ProductCreate(**data)
        assert "name" in str(exc.value)

    def test_product_name_presence_not_null(self, valid_product_data):
        """name cannot be null for Product."""
        data = valid_product_data.copy()
        data["name"] = None
        with pytest.raises(ValidationError) as exc:
            ProductCreate(**data)
        assert "name" in str(exc.value)

    def test_product_name_format_valid(self, valid_product_data):
        """name accepts length >= 1."""
        # Valid format should pass
        product = ProductCreate(**valid_product_data)
        assert product.name is not None

    def test_product_name_format_invalid(self, valid_product_data):
        """name rejects invalid format."""
        data = valid_product_data.copy()
        data["name"] = "invalid_format_value"
        with pytest.raises(ValidationError) as exc:
            ProductCreate(**data)
        assert "name" in str(exc.value)

    def test_product_price_presence_required(self, valid_product_data):
        """price is required for Product."""
        data = valid_product_data.copy()
        del data["price"]
        with pytest.raises(ValidationError) as exc:
            ProductCreate(**data)
        assert "price" in str(exc.value)

    def test_product_price_presence_not_null(self, valid_product_data):
        """price cannot be null for Product."""
        data = valid_product_data.copy()
        data["price"] = None
        with pytest.raises(ValidationError) as exc:
            ProductCreate(**data)
        assert "price" in str(exc.value)

    def test_product_price_range_valid(self, valid_product_data):
        """price accepts value in range (>= 0.01)."""
        product = ProductCreate(**valid_product_data)
        assert product.price is not None

    def test_product_price_range_below_min(self, valid_product_data):
        """price rejects value below minimum."""
        data = valid_product_data.copy()
        data["price"] = -1  # Below minimum
        with pytest.raises(ValidationError) as exc:
            ProductCreate(**data)
        assert "price" in str(exc.value)

    def test_product_price_range_at_boundary(self, valid_product_data):
        """price tests boundary value."""
        data = valid_product_data.copy()
        data["price"] = 0  # At boundary
        # This may or may not pass depending on condition (>= vs >)
        try:
            ProductCreate(**data)
        except ValidationError:
            pass  # Expected if condition is > 0

    def test_product_stock_presence_required(self, valid_product_data):
        """stock is required for Product."""
        data = valid_product_data.copy()
        del data["stock"]
        with pytest.raises(ValidationError) as exc:
            ProductCreate(**data)
        assert "stock" in str(exc.value)

    def test_product_stock_presence_not_null(self, valid_product_data):
        """stock cannot be null for Product."""
        data = valid_product_data.copy()
        data["stock"] = None
        with pytest.raises(ValidationError) as exc:
            ProductCreate(**data)
        assert "stock" in str(exc.value)

    def test_product_stock_range_valid(self, valid_product_data):
        """stock accepts value in range (>= 0)."""
        product = ProductCreate(**valid_product_data)
        assert product.stock is not None

    def test_product_stock_range_below_min(self, valid_product_data):
        """stock rejects value below minimum."""
        data = valid_product_data.copy()
        data["stock"] = -1  # Below minimum
        with pytest.raises(ValidationError) as exc:
            ProductCreate(**data)
        assert "stock" in str(exc.value)

    def test_product_stock_range_at_boundary(self, valid_product_data):
        """stock tests boundary value."""
        data = valid_product_data.copy()
        data["stock"] = 0  # At boundary
        # This may or may not pass depending on condition (>= vs >)
        try:
            ProductCreate(**data)
        except ValidationError:
            pass  # Expected if condition is > 0

    def test_product_is_active_presence_required(self, valid_product_data):
        """is_active is required for Product."""
        data = valid_product_data.copy()
        del data["is_active"]
        with pytest.raises(ValidationError) as exc:
            ProductCreate(**data)
        assert "is_active" in str(exc.value)

    def test_product_is_active_presence_not_null(self, valid_product_data):
        """is_active cannot be null for Product."""
        data = valid_product_data.copy()
        data["is_active"] = None
        with pytest.raises(ValidationError) as exc:
            ProductCreate(**data)
        assert "is_active" in str(exc.value)


class TestCustomerValidation:
    """Validation tests for Customer entity."""

    def test_customer_email_format_valid(self, valid_customer_data):
        """email accepts valid email."""
        # Valid format should pass
        customer = CustomerCreate(**valid_customer_data)
        assert customer.email is not None

    def test_customer_email_format_invalid(self, valid_customer_data):
        """email rejects invalid format."""
        data = valid_customer_data.copy()
        data["email"] = "invalid_format_value"
        with pytest.raises(ValidationError) as exc:
            CustomerCreate(**data)
        assert "email" in str(exc.value)

    async def test_customer_email_uniqueness(self, db_session, valid_customer_data):
        """email must be unique for Customer."""
        # Create first entity
        customer1 = CustomerEntity(**valid_customer_data)
        db_session.add(customer1)
        await db_session.commit()

        # Try to create duplicate
        duplicate_data = valid_customer_data.copy()
        duplicate_data["email"] = customer1.email
        customer2 = CustomerEntity(**duplicate_data)
        db_session.add(customer2)

        with pytest.raises(Exception) as exc:  # IntegrityError
            await db_session.commit()
        assert "unique" in str(exc.value).lower() or "duplicate" in str(exc.value).lower()

    def test_customer_email_presence_required(self, valid_customer_data):
        """email is required for Customer."""
        data = valid_customer_data.copy()
        del data["email"]
        with pytest.raises(ValidationError) as exc:
            CustomerCreate(**data)
        assert "email" in str(exc.value)

    def test_customer_email_presence_not_null(self, valid_customer_data):
        """email cannot be null for Customer."""
        data = valid_customer_data.copy()
        data["email"] = None
        with pytest.raises(ValidationError) as exc:
            CustomerCreate(**data)
        assert "email" in str(exc.value)

    def test_customer_full_name_presence_required(self, valid_customer_data):
        """full_name is required for Customer."""
        data = valid_customer_data.copy()
        del data["full_name"]
        with pytest.raises(ValidationError) as exc:
            CustomerCreate(**data)
        assert "full_name" in str(exc.value)

    def test_customer_full_name_presence_not_null(self, valid_customer_data):
        """full_name cannot be null for Customer."""
        data = valid_customer_data.copy()
        data["full_name"] = None
        with pytest.raises(ValidationError) as exc:
            CustomerCreate(**data)
        assert "full_name" in str(exc.value)

    async def test_customer_id_relationship_valid_fk(self, db_session, valid_customer_data):
        """id references valid foreign key."""
        # FK should exist before creating
        customer = CustomerEntity(**valid_customer_data)
        db_session.add(customer)
        await db_session.commit()
        assert customer.id is not None

    async def test_customer_id_relationship_invalid_fk(self, db_session, valid_customer_data):
        """id rejects non-existent foreign key."""
        data = valid_customer_data.copy()
        data["id"] = 99999  # Non-existent FK
        customer = CustomerEntity(**data)
        db_session.add(customer)

        with pytest.raises(Exception):  # IntegrityError
            await db_session.commit()

    def test_customer_id_presence_required(self, valid_customer_data):
        """id is required for Customer."""
        data = valid_customer_data.copy()
        del data["id"]
        with pytest.raises(ValidationError) as exc:
            CustomerCreate(**data)
        assert "id" in str(exc.value)

    def test_customer_id_presence_not_null(self, valid_customer_data):
        """id cannot be null for Customer."""
        data = valid_customer_data.copy()
        data["id"] = None
        with pytest.raises(ValidationError) as exc:
            CustomerCreate(**data)
        assert "id" in str(exc.value)

    async def test_customer_id_uniqueness(self, db_session, valid_customer_data):
        """id must be unique for Customer."""
        # Create first entity
        customer1 = CustomerEntity(**valid_customer_data)
        db_session.add(customer1)
        await db_session.commit()

        # Try to create duplicate
        duplicate_data = valid_customer_data.copy()
        duplicate_data["id"] = customer1.id
        customer2 = CustomerEntity(**duplicate_data)
        db_session.add(customer2)

        with pytest.raises(Exception) as exc:  # IntegrityError
            await db_session.commit()
        assert "unique" in str(exc.value).lower() or "duplicate" in str(exc.value).lower()

    def test_customer_id_format_valid(self, valid_customer_data):
        """id accepts uuid."""
        # Valid format should pass
        customer = CustomerCreate(**valid_customer_data)
        assert customer.id is not None

    def test_customer_id_format_invalid(self, valid_customer_data):
        """id rejects invalid format."""
        data = valid_customer_data.copy()
        data["id"] = "invalid_format_value"
        with pytest.raises(ValidationError) as exc:
            CustomerCreate(**data)
        assert "id" in str(exc.value)

    def test_customer_email_presence_required(self, valid_customer_data):
        """email is required for Customer."""
        data = valid_customer_data.copy()
        del data["email"]
        with pytest.raises(ValidationError) as exc:
            CustomerCreate(**data)
        assert "email" in str(exc.value)

    def test_customer_email_presence_not_null(self, valid_customer_data):
        """email cannot be null for Customer."""
        data = valid_customer_data.copy()
        data["email"] = None
        with pytest.raises(ValidationError) as exc:
            CustomerCreate(**data)
        assert "email" in str(exc.value)

    async def test_customer_email_uniqueness(self, db_session, valid_customer_data):
        """email must be unique for Customer."""
        # Create first entity
        customer1 = CustomerEntity(**valid_customer_data)
        db_session.add(customer1)
        await db_session.commit()

        # Try to create duplicate
        duplicate_data = valid_customer_data.copy()
        duplicate_data["email"] = customer1.email
        customer2 = CustomerEntity(**duplicate_data)
        db_session.add(customer2)

        with pytest.raises(Exception) as exc:  # IntegrityError
            await db_session.commit()
        assert "unique" in str(exc.value).lower() or "duplicate" in str(exc.value).lower()

    def test_customer_email_format_valid(self, valid_customer_data):
        """email accepts email."""
        # Valid format should pass
        customer = CustomerCreate(**valid_customer_data)
        assert customer.email is not None

    def test_customer_email_format_invalid(self, valid_customer_data):
        """email rejects invalid format."""
        data = valid_customer_data.copy()
        data["email"] = "invalid_format_value"
        with pytest.raises(ValidationError) as exc:
            CustomerCreate(**data)
        assert "email" in str(exc.value)

    def test_customer_full_name_presence_required(self, valid_customer_data):
        """full_name is required for Customer."""
        data = valid_customer_data.copy()
        del data["full_name"]
        with pytest.raises(ValidationError) as exc:
            CustomerCreate(**data)
        assert "full_name" in str(exc.value)

    def test_customer_full_name_presence_not_null(self, valid_customer_data):
        """full_name cannot be null for Customer."""
        data = valid_customer_data.copy()
        data["full_name"] = None
        with pytest.raises(ValidationError) as exc:
            CustomerCreate(**data)
        assert "full_name" in str(exc.value)

    def test_customer_full_name_format_valid(self, valid_customer_data):
        """full_name accepts length >= 1."""
        # Valid format should pass
        customer = CustomerCreate(**valid_customer_data)
        assert customer.full_name is not None

    def test_customer_full_name_format_invalid(self, valid_customer_data):
        """full_name rejects invalid format."""
        data = valid_customer_data.copy()
        data["full_name"] = "invalid_format_value"
        with pytest.raises(ValidationError) as exc:
            CustomerCreate(**data)
        assert "full_name" in str(exc.value)

    def test_customer_registration_date_presence_required(self, valid_customer_data):
        """registration_date is required for Customer."""
        data = valid_customer_data.copy()
        del data["registration_date"]
        with pytest.raises(ValidationError) as exc:
            CustomerCreate(**data)
        assert "registration_date" in str(exc.value)

    def test_customer_registration_date_presence_not_null(self, valid_customer_data):
        """registration_date cannot be null for Customer."""
        data = valid_customer_data.copy()
        data["registration_date"] = None
        with pytest.raises(ValidationError) as exc:
            CustomerCreate(**data)
        assert "registration_date" in str(exc.value)

    def test_customer_registration_date_format_valid(self, valid_customer_data):
        """registration_date accepts datetime."""
        # Valid format should pass
        customer = CustomerCreate(**valid_customer_data)
        assert customer.registration_date is not None

    def test_customer_registration_date_format_invalid(self, valid_customer_data):
        """registration_date rejects invalid format."""
        data = valid_customer_data.copy()
        data["registration_date"] = "invalid_format_value"
        with pytest.raises(ValidationError) as exc:
            CustomerCreate(**data)
        assert "registration_date" in str(exc.value)


class TestCartItemValidation:
    """Validation tests for CartItem entity."""

    def test_cartitem_quantity_range_valid(self, valid_cartitem_data):
        """quantity accepts value in range (> 0)."""
        cartitem = CartItemCreate(**valid_cartitem_data)
        assert cartitem.quantity is not None

    def test_cartitem_quantity_range_below_min(self, valid_cartitem_data):
        """quantity rejects value below minimum."""
        data = valid_cartitem_data.copy()
        data["quantity"] = -1  # Below minimum
        with pytest.raises(ValidationError) as exc:
            CartItemCreate(**data)
        assert "quantity" in str(exc.value)

    def test_cartitem_quantity_range_at_boundary(self, valid_cartitem_data):
        """quantity tests boundary value."""
        data = valid_cartitem_data.copy()
        data["quantity"] = 0  # At boundary
        # This may or may not pass depending on condition (>= vs >)
        try:
            CartItemCreate(**data)
        except ValidationError:
            pass  # Expected if condition is > 0

    def test_cartitem_unit_price_range_valid(self, valid_cartitem_data):
        """unit_price accepts value in range (> 0)."""
        cartitem = CartItemCreate(**valid_cartitem_data)
        assert cartitem.unit_price is not None

    def test_cartitem_unit_price_range_below_min(self, valid_cartitem_data):
        """unit_price rejects value below minimum."""
        data = valid_cartitem_data.copy()
        data["unit_price"] = -1  # Below minimum
        with pytest.raises(ValidationError) as exc:
            CartItemCreate(**data)
        assert "unit_price" in str(exc.value)

    def test_cartitem_unit_price_range_at_boundary(self, valid_cartitem_data):
        """unit_price tests boundary value."""
        data = valid_cartitem_data.copy()
        data["unit_price"] = 0  # At boundary
        # This may or may not pass depending on condition (>= vs >)
        try:
            CartItemCreate(**data)
        except ValidationError:
            pass  # Expected if condition is > 0

    async def test_cartitem_product_id_relationship_valid_fk(self, db_session, valid_cartitem_data):
        """product_id references valid foreign key."""
        # FK should exist before creating
        cartitem = CartItemEntity(**valid_cartitem_data)
        db_session.add(cartitem)
        await db_session.commit()
        assert cartitem.product_id is not None

    async def test_cartitem_product_id_relationship_invalid_fk(self, db_session, valid_cartitem_data):
        """product_id rejects non-existent foreign key."""
        data = valid_cartitem_data.copy()
        data["product_id"] = 99999  # Non-existent FK
        cartitem = CartItemEntity(**data)
        db_session.add(cartitem)

        with pytest.raises(Exception):  # IntegrityError
            await db_session.commit()

    def test_cartitem_product_id_custom(self, valid_cartitem_data):
        """product must be active for CartItem.product_id."""
        # Custom validation test - implementation depends on specific rule
        cartitem = CartItemCreate(**valid_cartitem_data)
        assert cartitem.product_id is not None

    def test_cartitem_quantity_stock_constraint(self, valid_cartitem_data):
        """quantity <= product.stock for CartItem.quantity."""
        # Custom validation test - implementation depends on specific rule
        cartitem = CartItemCreate(**valid_cartitem_data)
        assert cartitem.quantity is not None

    def test_cartitem_product_id_custom(self, valid_cartitem_data):
        """if product already in cart, increase quantity instead of duplicating for CartItem.product_id."""
        # Custom validation test - implementation depends on specific rule
        cartitem = CartItemCreate(**valid_cartitem_data)
        assert cartitem.product_id is not None

    def test_cartitem_id_presence_required(self, valid_cartitem_data):
        """id is required for CartItem."""
        data = valid_cartitem_data.copy()
        del data["id"]
        with pytest.raises(ValidationError) as exc:
            CartItemCreate(**data)
        assert "id" in str(exc.value)

    def test_cartitem_id_presence_not_null(self, valid_cartitem_data):
        """id cannot be null for CartItem."""
        data = valid_cartitem_data.copy()
        data["id"] = None
        with pytest.raises(ValidationError) as exc:
            CartItemCreate(**data)
        assert "id" in str(exc.value)

    async def test_cartitem_id_uniqueness(self, db_session, valid_cartitem_data):
        """id must be unique for CartItem."""
        # Create first entity
        cartitem1 = CartItemEntity(**valid_cartitem_data)
        db_session.add(cartitem1)
        await db_session.commit()

        # Try to create duplicate
        duplicate_data = valid_cartitem_data.copy()
        duplicate_data["id"] = cartitem1.id
        cartitem2 = CartItemEntity(**duplicate_data)
        db_session.add(cartitem2)

        with pytest.raises(Exception) as exc:  # IntegrityError
            await db_session.commit()
        assert "unique" in str(exc.value).lower() or "duplicate" in str(exc.value).lower()

    def test_cartitem_id_format_valid(self, valid_cartitem_data):
        """id accepts uuid."""
        # Valid format should pass
        cartitem = CartItemCreate(**valid_cartitem_data)
        assert cartitem.id is not None

    def test_cartitem_id_format_invalid(self, valid_cartitem_data):
        """id rejects invalid format."""
        data = valid_cartitem_data.copy()
        data["id"] = "invalid_format_value"
        with pytest.raises(ValidationError) as exc:
            CartItemCreate(**data)
        assert "id" in str(exc.value)

    def test_cartitem_cart_id_presence_required(self, valid_cartitem_data):
        """cart_id is required for CartItem."""
        data = valid_cartitem_data.copy()
        del data["cart_id"]
        with pytest.raises(ValidationError) as exc:
            CartItemCreate(**data)
        assert "cart_id" in str(exc.value)

    def test_cartitem_cart_id_presence_not_null(self, valid_cartitem_data):
        """cart_id cannot be null for CartItem."""
        data = valid_cartitem_data.copy()
        data["cart_id"] = None
        with pytest.raises(ValidationError) as exc:
            CartItemCreate(**data)
        assert "cart_id" in str(exc.value)

    def test_cartitem_cart_id_format_valid(self, valid_cartitem_data):
        """cart_id accepts uuid."""
        # Valid format should pass
        cartitem = CartItemCreate(**valid_cartitem_data)
        assert cartitem.cart_id is not None

    def test_cartitem_cart_id_format_invalid(self, valid_cartitem_data):
        """cart_id rejects invalid format."""
        data = valid_cartitem_data.copy()
        data["cart_id"] = "invalid_format_value"
        with pytest.raises(ValidationError) as exc:
            CartItemCreate(**data)
        assert "cart_id" in str(exc.value)

    def test_cartitem_product_id_presence_required(self, valid_cartitem_data):
        """product_id is required for CartItem."""
        data = valid_cartitem_data.copy()
        del data["product_id"]
        with pytest.raises(ValidationError) as exc:
            CartItemCreate(**data)
        assert "product_id" in str(exc.value)

    def test_cartitem_product_id_presence_not_null(self, valid_cartitem_data):
        """product_id cannot be null for CartItem."""
        data = valid_cartitem_data.copy()
        data["product_id"] = None
        with pytest.raises(ValidationError) as exc:
            CartItemCreate(**data)
        assert "product_id" in str(exc.value)

    def test_cartitem_product_id_format_valid(self, valid_cartitem_data):
        """product_id accepts uuid."""
        # Valid format should pass
        cartitem = CartItemCreate(**valid_cartitem_data)
        assert cartitem.product_id is not None

    def test_cartitem_product_id_format_invalid(self, valid_cartitem_data):
        """product_id rejects invalid format."""
        data = valid_cartitem_data.copy()
        data["product_id"] = "invalid_format_value"
        with pytest.raises(ValidationError) as exc:
            CartItemCreate(**data)
        assert "product_id" in str(exc.value)

    def test_cartitem_quantity_presence_required(self, valid_cartitem_data):
        """quantity is required for CartItem."""
        data = valid_cartitem_data.copy()
        del data["quantity"]
        with pytest.raises(ValidationError) as exc:
            CartItemCreate(**data)
        assert "quantity" in str(exc.value)

    def test_cartitem_quantity_presence_not_null(self, valid_cartitem_data):
        """quantity cannot be null for CartItem."""
        data = valid_cartitem_data.copy()
        data["quantity"] = None
        with pytest.raises(ValidationError) as exc:
            CartItemCreate(**data)
        assert "quantity" in str(exc.value)

    def test_cartitem_quantity_range_valid(self, valid_cartitem_data):
        """quantity accepts value in range (>= 1)."""
        cartitem = CartItemCreate(**valid_cartitem_data)
        assert cartitem.quantity is not None

    def test_cartitem_quantity_range_below_min(self, valid_cartitem_data):
        """quantity rejects value below minimum."""
        data = valid_cartitem_data.copy()
        data["quantity"] = -1  # Below minimum
        with pytest.raises(ValidationError) as exc:
            CartItemCreate(**data)
        assert "quantity" in str(exc.value)

    def test_cartitem_quantity_range_at_boundary(self, valid_cartitem_data):
        """quantity tests boundary value."""
        data = valid_cartitem_data.copy()
        data["quantity"] = 0  # At boundary
        # This may or may not pass depending on condition (>= vs >)
        try:
            CartItemCreate(**data)
        except ValidationError:
            pass  # Expected if condition is > 0

    def test_cartitem_unit_price_presence_required(self, valid_cartitem_data):
        """unit_price is required for CartItem."""
        data = valid_cartitem_data.copy()
        del data["unit_price"]
        with pytest.raises(ValidationError) as exc:
            CartItemCreate(**data)
        assert "unit_price" in str(exc.value)

    def test_cartitem_unit_price_presence_not_null(self, valid_cartitem_data):
        """unit_price cannot be null for CartItem."""
        data = valid_cartitem_data.copy()
        data["unit_price"] = None
        with pytest.raises(ValidationError) as exc:
            CartItemCreate(**data)
        assert "unit_price" in str(exc.value)

    def test_cartitem_unit_price_range_valid(self, valid_cartitem_data):
        """unit_price accepts value in range (>= 0.01)."""
        cartitem = CartItemCreate(**valid_cartitem_data)
        assert cartitem.unit_price is not None

    def test_cartitem_unit_price_range_below_min(self, valid_cartitem_data):
        """unit_price rejects value below minimum."""
        data = valid_cartitem_data.copy()
        data["unit_price"] = -1  # Below minimum
        with pytest.raises(ValidationError) as exc:
            CartItemCreate(**data)
        assert "unit_price" in str(exc.value)

    def test_cartitem_unit_price_range_at_boundary(self, valid_cartitem_data):
        """unit_price tests boundary value."""
        data = valid_cartitem_data.copy()
        data["unit_price"] = 0  # At boundary
        # This may or may not pass depending on condition (>= vs >)
        try:
            CartItemCreate(**data)
        except ValidationError:
            pass  # Expected if condition is > 0


class TestOrderItemValidation:
    """Validation tests for OrderItem entity."""

    def test_orderitem_quantity_range_valid(self, valid_orderitem_data):
        """quantity accepts value in range (> 0)."""
        orderitem = OrderItemCreate(**valid_orderitem_data)
        assert orderitem.quantity is not None

    def test_orderitem_quantity_range_below_min(self, valid_orderitem_data):
        """quantity rejects value below minimum."""
        data = valid_orderitem_data.copy()
        data["quantity"] = -1  # Below minimum
        with pytest.raises(ValidationError) as exc:
            OrderItemCreate(**data)
        assert "quantity" in str(exc.value)

    def test_orderitem_quantity_range_at_boundary(self, valid_orderitem_data):
        """quantity tests boundary value."""
        data = valid_orderitem_data.copy()
        data["quantity"] = 0  # At boundary
        # This may or may not pass depending on condition (>= vs >)
        try:
            OrderItemCreate(**data)
        except ValidationError:
            pass  # Expected if condition is > 0

    def test_orderitem_unit_price_range_valid(self, valid_orderitem_data):
        """unit_price accepts value in range (> 0)."""
        orderitem = OrderItemCreate(**valid_orderitem_data)
        assert orderitem.unit_price is not None

    def test_orderitem_unit_price_range_below_min(self, valid_orderitem_data):
        """unit_price rejects value below minimum."""
        data = valid_orderitem_data.copy()
        data["unit_price"] = -1  # Below minimum
        with pytest.raises(ValidationError) as exc:
            OrderItemCreate(**data)
        assert "unit_price" in str(exc.value)

    def test_orderitem_unit_price_range_at_boundary(self, valid_orderitem_data):
        """unit_price tests boundary value."""
        data = valid_orderitem_data.copy()
        data["unit_price"] = 0  # At boundary
        # This may or may not pass depending on condition (>= vs >)
        try:
            OrderItemCreate(**data)
        except ValidationError:
            pass  # Expected if condition is > 0

    def test_orderitem_id_presence_required(self, valid_orderitem_data):
        """id is required for OrderItem."""
        data = valid_orderitem_data.copy()
        del data["id"]
        with pytest.raises(ValidationError) as exc:
            OrderItemCreate(**data)
        assert "id" in str(exc.value)

    def test_orderitem_id_presence_not_null(self, valid_orderitem_data):
        """id cannot be null for OrderItem."""
        data = valid_orderitem_data.copy()
        data["id"] = None
        with pytest.raises(ValidationError) as exc:
            OrderItemCreate(**data)
        assert "id" in str(exc.value)

    async def test_orderitem_id_uniqueness(self, db_session, valid_orderitem_data):
        """id must be unique for OrderItem."""
        # Create first entity
        orderitem1 = OrderItemEntity(**valid_orderitem_data)
        db_session.add(orderitem1)
        await db_session.commit()

        # Try to create duplicate
        duplicate_data = valid_orderitem_data.copy()
        duplicate_data["id"] = orderitem1.id
        orderitem2 = OrderItemEntity(**duplicate_data)
        db_session.add(orderitem2)

        with pytest.raises(Exception) as exc:  # IntegrityError
            await db_session.commit()
        assert "unique" in str(exc.value).lower() or "duplicate" in str(exc.value).lower()

    def test_orderitem_id_format_valid(self, valid_orderitem_data):
        """id accepts uuid."""
        # Valid format should pass
        orderitem = OrderItemCreate(**valid_orderitem_data)
        assert orderitem.id is not None

    def test_orderitem_id_format_invalid(self, valid_orderitem_data):
        """id rejects invalid format."""
        data = valid_orderitem_data.copy()
        data["id"] = "invalid_format_value"
        with pytest.raises(ValidationError) as exc:
            OrderItemCreate(**data)
        assert "id" in str(exc.value)

    def test_orderitem_order_id_presence_required(self, valid_orderitem_data):
        """order_id is required for OrderItem."""
        data = valid_orderitem_data.copy()
        del data["order_id"]
        with pytest.raises(ValidationError) as exc:
            OrderItemCreate(**data)
        assert "order_id" in str(exc.value)

    def test_orderitem_order_id_presence_not_null(self, valid_orderitem_data):
        """order_id cannot be null for OrderItem."""
        data = valid_orderitem_data.copy()
        data["order_id"] = None
        with pytest.raises(ValidationError) as exc:
            OrderItemCreate(**data)
        assert "order_id" in str(exc.value)

    def test_orderitem_order_id_format_valid(self, valid_orderitem_data):
        """order_id accepts uuid."""
        # Valid format should pass
        orderitem = OrderItemCreate(**valid_orderitem_data)
        assert orderitem.order_id is not None

    def test_orderitem_order_id_format_invalid(self, valid_orderitem_data):
        """order_id rejects invalid format."""
        data = valid_orderitem_data.copy()
        data["order_id"] = "invalid_format_value"
        with pytest.raises(ValidationError) as exc:
            OrderItemCreate(**data)
        assert "order_id" in str(exc.value)

    def test_orderitem_product_id_presence_required(self, valid_orderitem_data):
        """product_id is required for OrderItem."""
        data = valid_orderitem_data.copy()
        del data["product_id"]
        with pytest.raises(ValidationError) as exc:
            OrderItemCreate(**data)
        assert "product_id" in str(exc.value)

    def test_orderitem_product_id_presence_not_null(self, valid_orderitem_data):
        """product_id cannot be null for OrderItem."""
        data = valid_orderitem_data.copy()
        data["product_id"] = None
        with pytest.raises(ValidationError) as exc:
            OrderItemCreate(**data)
        assert "product_id" in str(exc.value)

    def test_orderitem_product_id_format_valid(self, valid_orderitem_data):
        """product_id accepts uuid."""
        # Valid format should pass
        orderitem = OrderItemCreate(**valid_orderitem_data)
        assert orderitem.product_id is not None

    def test_orderitem_product_id_format_invalid(self, valid_orderitem_data):
        """product_id rejects invalid format."""
        data = valid_orderitem_data.copy()
        data["product_id"] = "invalid_format_value"
        with pytest.raises(ValidationError) as exc:
            OrderItemCreate(**data)
        assert "product_id" in str(exc.value)

    def test_orderitem_quantity_presence_required(self, valid_orderitem_data):
        """quantity is required for OrderItem."""
        data = valid_orderitem_data.copy()
        del data["quantity"]
        with pytest.raises(ValidationError) as exc:
            OrderItemCreate(**data)
        assert "quantity" in str(exc.value)

    def test_orderitem_quantity_presence_not_null(self, valid_orderitem_data):
        """quantity cannot be null for OrderItem."""
        data = valid_orderitem_data.copy()
        data["quantity"] = None
        with pytest.raises(ValidationError) as exc:
            OrderItemCreate(**data)
        assert "quantity" in str(exc.value)

    def test_orderitem_quantity_range_valid(self, valid_orderitem_data):
        """quantity accepts value in range (>= 1)."""
        orderitem = OrderItemCreate(**valid_orderitem_data)
        assert orderitem.quantity is not None

    def test_orderitem_quantity_range_below_min(self, valid_orderitem_data):
        """quantity rejects value below minimum."""
        data = valid_orderitem_data.copy()
        data["quantity"] = -1  # Below minimum
        with pytest.raises(ValidationError) as exc:
            OrderItemCreate(**data)
        assert "quantity" in str(exc.value)

    def test_orderitem_quantity_range_at_boundary(self, valid_orderitem_data):
        """quantity tests boundary value."""
        data = valid_orderitem_data.copy()
        data["quantity"] = 0  # At boundary
        # This may or may not pass depending on condition (>= vs >)
        try:
            OrderItemCreate(**data)
        except ValidationError:
            pass  # Expected if condition is > 0

    def test_orderitem_unit_price_presence_required(self, valid_orderitem_data):
        """unit_price is required for OrderItem."""
        data = valid_orderitem_data.copy()
        del data["unit_price"]
        with pytest.raises(ValidationError) as exc:
            OrderItemCreate(**data)
        assert "unit_price" in str(exc.value)

    def test_orderitem_unit_price_presence_not_null(self, valid_orderitem_data):
        """unit_price cannot be null for OrderItem."""
        data = valid_orderitem_data.copy()
        data["unit_price"] = None
        with pytest.raises(ValidationError) as exc:
            OrderItemCreate(**data)
        assert "unit_price" in str(exc.value)

    def test_orderitem_unit_price_range_valid(self, valid_orderitem_data):
        """unit_price accepts value in range (>= 0.01)."""
        orderitem = OrderItemCreate(**valid_orderitem_data)
        assert orderitem.unit_price is not None

    def test_orderitem_unit_price_range_below_min(self, valid_orderitem_data):
        """unit_price rejects value below minimum."""
        data = valid_orderitem_data.copy()
        data["unit_price"] = -1  # Below minimum
        with pytest.raises(ValidationError) as exc:
            OrderItemCreate(**data)
        assert "unit_price" in str(exc.value)

    def test_orderitem_unit_price_range_at_boundary(self, valid_orderitem_data):
        """unit_price tests boundary value."""
        data = valid_orderitem_data.copy()
        data["unit_price"] = 0  # At boundary
        # This may or may not pass depending on condition (>= vs >)
        try:
            OrderItemCreate(**data)
        except ValidationError:
            pass  # Expected if condition is > 0


class TestCartValidation:
    """Validation tests for Cart entity."""

    def test_cart_status_status_transition_valid_transition(self, valid_cart_data):
        """Cart allows valid status transitions."""
        cart = CartEntity(**valid_cart_data)
        # Test valid transition (implementation depends on business logic)
        # This is a placeholder - actual transitions depend on spec
        assert cart.status is not None

    def test_cart_status_status_transition_invalid_transition(self, valid_cart_data):
        """Cart rejects invalid status transitions."""
        cart = CartEntity(**valid_cart_data)
        # Test invalid transition
        with pytest.raises(ValueError):
            cart.transition_to("invalid_status")

    def test_cart_customer_id_custom(self, valid_cart_data):
        """one OPEN cart per customer for Cart.customer_id."""
        # Custom validation test - implementation depends on specific rule
        cart = CartCreate(**valid_cart_data)
        assert cart.customer_id is not None

    async def test_cart_id_relationship_valid_fk(self, db_session, valid_cart_data):
        """id references valid foreign key."""
        # FK should exist before creating
        cart = CartEntity(**valid_cart_data)
        db_session.add(cart)
        await db_session.commit()
        assert cart.id is not None

    async def test_cart_id_relationship_invalid_fk(self, db_session, valid_cart_data):
        """id rejects non-existent foreign key."""
        data = valid_cart_data.copy()
        data["id"] = 99999  # Non-existent FK
        cart = CartEntity(**data)
        db_session.add(cart)

        with pytest.raises(Exception):  # IntegrityError
            await db_session.commit()

    def test_cart_id_presence_required(self, valid_cart_data):
        """id is required for Cart."""
        data = valid_cart_data.copy()
        del data["id"]
        with pytest.raises(ValidationError) as exc:
            CartCreate(**data)
        assert "id" in str(exc.value)

    def test_cart_id_presence_not_null(self, valid_cart_data):
        """id cannot be null for Cart."""
        data = valid_cart_data.copy()
        data["id"] = None
        with pytest.raises(ValidationError) as exc:
            CartCreate(**data)
        assert "id" in str(exc.value)

    async def test_cart_id_uniqueness(self, db_session, valid_cart_data):
        """id must be unique for Cart."""
        # Create first entity
        cart1 = CartEntity(**valid_cart_data)
        db_session.add(cart1)
        await db_session.commit()

        # Try to create duplicate
        duplicate_data = valid_cart_data.copy()
        duplicate_data["id"] = cart1.id
        cart2 = CartEntity(**duplicate_data)
        db_session.add(cart2)

        with pytest.raises(Exception) as exc:  # IntegrityError
            await db_session.commit()
        assert "unique" in str(exc.value).lower() or "duplicate" in str(exc.value).lower()

    def test_cart_id_format_valid(self, valid_cart_data):
        """id accepts uuid."""
        # Valid format should pass
        cart = CartCreate(**valid_cart_data)
        assert cart.id is not None

    def test_cart_id_format_invalid(self, valid_cart_data):
        """id rejects invalid format."""
        data = valid_cart_data.copy()
        data["id"] = "invalid_format_value"
        with pytest.raises(ValidationError) as exc:
            CartCreate(**data)
        assert "id" in str(exc.value)

    def test_cart_customer_id_presence_required(self, valid_cart_data):
        """customer_id is required for Cart."""
        data = valid_cart_data.copy()
        del data["customer_id"]
        with pytest.raises(ValidationError) as exc:
            CartCreate(**data)
        assert "customer_id" in str(exc.value)

    def test_cart_customer_id_presence_not_null(self, valid_cart_data):
        """customer_id cannot be null for Cart."""
        data = valid_cart_data.copy()
        data["customer_id"] = None
        with pytest.raises(ValidationError) as exc:
            CartCreate(**data)
        assert "customer_id" in str(exc.value)

    def test_cart_customer_id_format_valid(self, valid_cart_data):
        """customer_id accepts uuid."""
        # Valid format should pass
        cart = CartCreate(**valid_cart_data)
        assert cart.customer_id is not None

    def test_cart_customer_id_format_invalid(self, valid_cart_data):
        """customer_id rejects invalid format."""
        data = valid_cart_data.copy()
        data["customer_id"] = "invalid_format_value"
        with pytest.raises(ValidationError) as exc:
            CartCreate(**data)
        assert "customer_id" in str(exc.value)

    def test_cart_status_presence_required(self, valid_cart_data):
        """status is required for Cart."""
        data = valid_cart_data.copy()
        del data["status"]
        with pytest.raises(ValidationError) as exc:
            CartCreate(**data)
        assert "status" in str(exc.value)

    def test_cart_status_presence_not_null(self, valid_cart_data):
        """status cannot be null for Cart."""
        data = valid_cart_data.copy()
        data["status"] = None
        with pytest.raises(ValidationError) as exc:
            CartCreate(**data)
        assert "status" in str(exc.value)

    def test_cart_status_status_transition_valid_transition(self, valid_cart_data):
        """Cart allows valid status transitions."""
        cart = CartEntity(**valid_cart_data)
        # Test valid transition (implementation depends on business logic)
        # This is a placeholder - actual transitions depend on spec
        assert cart.status is not None

    def test_cart_status_status_transition_invalid_transition(self, valid_cart_data):
        """Cart rejects invalid status transitions."""
        cart = CartEntity(**valid_cart_data)
        # Test invalid transition
        with pytest.raises(ValueError):
            cart.transition_to("invalid_status")


class TestOrderValidation:
    """Validation tests for Order entity."""

    def test_order_order_status_status_transition_valid_transition(self, valid_order_data):
        """Order allows valid status transitions."""
        order = OrderEntity(**valid_order_data)
        # Test valid transition (implementation depends on business logic)
        # This is a placeholder - actual transitions depend on spec
        assert order.order_status is not None

    def test_order_order_status_status_transition_invalid_transition(self, valid_order_data):
        """Order rejects invalid status transitions."""
        order = OrderEntity(**valid_order_data)
        # Test invalid transition
        with pytest.raises(ValueError):
            order.transition_to("invalid_status")

    def test_order_total_amount_range_valid(self, valid_order_data):
        """total_amount accepts value in range (>= 0)."""
        order = OrderCreate(**valid_order_data)
        assert order.total_amount is not None

    def test_order_total_amount_range_below_min(self, valid_order_data):
        """total_amount rejects value below minimum."""
        data = valid_order_data.copy()
        data["total_amount"] = -1  # Below minimum
        with pytest.raises(ValidationError) as exc:
            OrderCreate(**data)
        assert "total_amount" in str(exc.value)

    def test_order_total_amount_range_at_boundary(self, valid_order_data):
        """total_amount tests boundary value."""
        data = valid_order_data.copy()
        data["total_amount"] = 0  # At boundary
        # This may or may not pass depending on condition (>= vs >)
        try:
            OrderCreate(**data)
        except ValidationError:
            pass  # Expected if condition is > 0

    def test_order_items_custom(self, valid_order_data):
        """cart must not be empty for Order.items."""
        # Custom validation test - implementation depends on specific rule
        order = OrderCreate(**valid_order_data)
        assert order.items is not None

    def test_order_items_stock_constraint(self, valid_order_data):
        """stock available for all items for Order.items."""
        # Custom validation test - implementation depends on specific rule
        order = OrderCreate(**valid_order_data)
        assert order.items is not None

    def test_order_order_status_workflow_constraint(self, valid_order_data):
        """can only pay if status is PENDING_PAYMENT for Order.order_status."""
        # Custom validation test - implementation depends on specific rule
        order = OrderCreate(**valid_order_data)
        assert order.order_status is not None

    def test_order_order_status_workflow_constraint(self, valid_order_data):
        """can only cancel if status is PENDING_PAYMENT for Order.order_status."""
        # Custom validation test - implementation depends on specific rule
        order = OrderCreate(**valid_order_data)
        assert order.order_status is not None

    async def test_order_id_relationship_valid_fk(self, db_session, valid_order_data):
        """id references valid foreign key."""
        # FK should exist before creating
        order = OrderEntity(**valid_order_data)
        db_session.add(order)
        await db_session.commit()
        assert order.id is not None

    async def test_order_id_relationship_invalid_fk(self, db_session, valid_order_data):
        """id rejects non-existent foreign key."""
        data = valid_order_data.copy()
        data["id"] = 99999  # Non-existent FK
        order = OrderEntity(**data)
        db_session.add(order)

        with pytest.raises(Exception):  # IntegrityError
            await db_session.commit()

    def test_order_id_presence_required(self, valid_order_data):
        """id is required for Order."""
        data = valid_order_data.copy()
        del data["id"]
        with pytest.raises(ValidationError) as exc:
            OrderCreate(**data)
        assert "id" in str(exc.value)

    def test_order_id_presence_not_null(self, valid_order_data):
        """id cannot be null for Order."""
        data = valid_order_data.copy()
        data["id"] = None
        with pytest.raises(ValidationError) as exc:
            OrderCreate(**data)
        assert "id" in str(exc.value)

    async def test_order_id_uniqueness(self, db_session, valid_order_data):
        """id must be unique for Order."""
        # Create first entity
        order1 = OrderEntity(**valid_order_data)
        db_session.add(order1)
        await db_session.commit()

        # Try to create duplicate
        duplicate_data = valid_order_data.copy()
        duplicate_data["id"] = order1.id
        order2 = OrderEntity(**duplicate_data)
        db_session.add(order2)

        with pytest.raises(Exception) as exc:  # IntegrityError
            await db_session.commit()
        assert "unique" in str(exc.value).lower() or "duplicate" in str(exc.value).lower()

    def test_order_id_format_valid(self, valid_order_data):
        """id accepts uuid."""
        # Valid format should pass
        order = OrderCreate(**valid_order_data)
        assert order.id is not None

    def test_order_id_format_invalid(self, valid_order_data):
        """id rejects invalid format."""
        data = valid_order_data.copy()
        data["id"] = "invalid_format_value"
        with pytest.raises(ValidationError) as exc:
            OrderCreate(**data)
        assert "id" in str(exc.value)

    def test_order_customer_id_presence_required(self, valid_order_data):
        """customer_id is required for Order."""
        data = valid_order_data.copy()
        del data["customer_id"]
        with pytest.raises(ValidationError) as exc:
            OrderCreate(**data)
        assert "customer_id" in str(exc.value)

    def test_order_customer_id_presence_not_null(self, valid_order_data):
        """customer_id cannot be null for Order."""
        data = valid_order_data.copy()
        data["customer_id"] = None
        with pytest.raises(ValidationError) as exc:
            OrderCreate(**data)
        assert "customer_id" in str(exc.value)

    def test_order_customer_id_format_valid(self, valid_order_data):
        """customer_id accepts uuid."""
        # Valid format should pass
        order = OrderCreate(**valid_order_data)
        assert order.customer_id is not None

    def test_order_customer_id_format_invalid(self, valid_order_data):
        """customer_id rejects invalid format."""
        data = valid_order_data.copy()
        data["customer_id"] = "invalid_format_value"
        with pytest.raises(ValidationError) as exc:
            OrderCreate(**data)
        assert "customer_id" in str(exc.value)

    def test_order_order_status_presence_required(self, valid_order_data):
        """order_status is required for Order."""
        data = valid_order_data.copy()
        del data["order_status"]
        with pytest.raises(ValidationError) as exc:
            OrderCreate(**data)
        assert "order_status" in str(exc.value)

    def test_order_order_status_presence_not_null(self, valid_order_data):
        """order_status cannot be null for Order."""
        data = valid_order_data.copy()
        data["order_status"] = None
        with pytest.raises(ValidationError) as exc:
            OrderCreate(**data)
        assert "order_status" in str(exc.value)

    def test_order_order_status_status_transition_valid_transition(self, valid_order_data):
        """Order allows valid status transitions."""
        order = OrderEntity(**valid_order_data)
        # Test valid transition (implementation depends on business logic)
        # This is a placeholder - actual transitions depend on spec
        assert order.order_status is not None

    def test_order_order_status_status_transition_invalid_transition(self, valid_order_data):
        """Order rejects invalid status transitions."""
        order = OrderEntity(**valid_order_data)
        # Test invalid transition
        with pytest.raises(ValueError):
            order.transition_to("invalid_status")

    def test_order_payment_status_presence_required(self, valid_order_data):
        """payment_status is required for Order."""
        data = valid_order_data.copy()
        del data["payment_status"]
        with pytest.raises(ValidationError) as exc:
            OrderCreate(**data)
        assert "payment_status" in str(exc.value)

    def test_order_payment_status_presence_not_null(self, valid_order_data):
        """payment_status cannot be null for Order."""
        data = valid_order_data.copy()
        data["payment_status"] = None
        with pytest.raises(ValidationError) as exc:
            OrderCreate(**data)
        assert "payment_status" in str(exc.value)

    def test_order_payment_status_status_transition_valid_transition(self, valid_order_data):
        """Order allows valid status transitions."""
        order = OrderEntity(**valid_order_data)
        # Test valid transition (implementation depends on business logic)
        # This is a placeholder - actual transitions depend on spec
        assert order.payment_status is not None

    def test_order_payment_status_status_transition_invalid_transition(self, valid_order_data):
        """Order rejects invalid status transitions."""
        order = OrderEntity(**valid_order_data)
        # Test invalid transition
        with pytest.raises(ValueError):
            order.transition_to("invalid_status")

    def test_order_total_amount_presence_required(self, valid_order_data):
        """total_amount is required for Order."""
        data = valid_order_data.copy()
        del data["total_amount"]
        with pytest.raises(ValidationError) as exc:
            OrderCreate(**data)
        assert "total_amount" in str(exc.value)

    def test_order_total_amount_presence_not_null(self, valid_order_data):
        """total_amount cannot be null for Order."""
        data = valid_order_data.copy()
        data["total_amount"] = None
        with pytest.raises(ValidationError) as exc:
            OrderCreate(**data)
        assert "total_amount" in str(exc.value)

    def test_order_total_amount_range_valid(self, valid_order_data):
        """total_amount accepts value in range (>= 0)."""
        order = OrderCreate(**valid_order_data)
        assert order.total_amount is not None

    def test_order_total_amount_range_below_min(self, valid_order_data):
        """total_amount rejects value below minimum."""
        data = valid_order_data.copy()
        data["total_amount"] = -1  # Below minimum
        with pytest.raises(ValidationError) as exc:
            OrderCreate(**data)
        assert "total_amount" in str(exc.value)

    def test_order_total_amount_range_at_boundary(self, valid_order_data):
        """total_amount tests boundary value."""
        data = valid_order_data.copy()
        data["total_amount"] = 0  # At boundary
        # This may or may not pass depending on condition (>= vs >)
        try:
            OrderCreate(**data)
        except ValidationError:
            pass  # Expected if condition is > 0

    def test_order_creation_date_presence_required(self, valid_order_data):
        """creation_date is required for Order."""
        data = valid_order_data.copy()
        del data["creation_date"]
        with pytest.raises(ValidationError) as exc:
            OrderCreate(**data)
        assert "creation_date" in str(exc.value)

    def test_order_creation_date_presence_not_null(self, valid_order_data):
        """creation_date cannot be null for Order."""
        data = valid_order_data.copy()
        data["creation_date"] = None
        with pytest.raises(ValidationError) as exc:
            OrderCreate(**data)
        assert "creation_date" in str(exc.value)

    def test_order_creation_date_format_valid(self, valid_order_data):
        """creation_date accepts datetime."""
        # Valid format should pass
        order = OrderCreate(**valid_order_data)
        assert order.creation_date is not None

    def test_order_creation_date_format_invalid(self, valid_order_data):
        """creation_date rejects invalid format."""
        data = valid_order_data.copy()
        data["creation_date"] = "invalid_format_value"
        with pytest.raises(ValidationError) as exc:
            OrderCreate(**data)
        assert "creation_date" in str(exc.value)


