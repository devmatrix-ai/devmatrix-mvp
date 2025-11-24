"""
Complete E-commerce API with Products, Customers, Carts, and Orders
FastAPI implementation with full CRUD operations and business logic
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field, field_validator


# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class CartStatus(str, Enum):
    """Cart status enumeration"""
    ACTIVE = "active"
    CHECKED_OUT = "checked_out"
    ABANDONED = "abandoned"


class OrderStatus(str, Enum):
    """Order status enumeration"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    """Payment status enumeration"""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


# ============================================================================
# PYDANTIC MODELS - ENTITIES
# ============================================================================

class Product(BaseModel):
    """Product entity with validation"""
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: Decimal = Field(..., gt=0, decimal_places=2)
    stock: int = Field(..., ge=0)
    is_active: bool = Field(default=True)

    @field_validator('price')
    @classmethod
    def validate_price(cls, v):
        """Validate price is greater than 0"""
        if v <= 0:
            raise ValueError('Price must be greater than 0')
        return v

    @field_validator('stock')
    @classmethod
    def validate_stock(cls, v):
        """Validate stock is non-negative"""
        if v < 0:
            raise ValueError('Stock must be non-negative')
        return v


class Customer(BaseModel):
    """Customer entity with email validation"""
    id: UUID = Field(default_factory=uuid4)
    email: EmailStr = Field(...)
    full_name: str = Field(..., min_length=1, max_length=200)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CartItem(BaseModel):
    """Cart item with product reference and quantity"""
    id: UUID = Field(default_factory=uuid4)
    product_id: UUID
    product_name: str
    product_price: Decimal
    quantity: int = Field(..., gt=0)
    subtotal: Decimal = Field(..., ge=0)


class Cart(BaseModel):
    """Shopping cart entity"""
    id: UUID = Field(default_factory=uuid4)
    customer_id: UUID
    items: List[CartItem] = Field(default_factory=list)
    status: CartStatus = Field(default=CartStatus.ACTIVE)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class OrderItem(BaseModel):
    """Order item snapshot"""
    id: UUID = Field(default_factory=uuid4)
    product_id: UUID
    product_name: str
    product_price: Decimal
    quantity: int = Field(..., gt=0)
    subtotal: Decimal = Field(..., ge=0)


class Order(BaseModel):
    """Order entity with payment tracking"""
    id: UUID = Field(default_factory=uuid4)
    customer_id: UUID
    items: List[OrderItem]
    total_amount: Decimal = Field(..., ge=0)
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    payment_status: PaymentStatus = Field(default=PaymentStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class ProductCreate(BaseModel):
    """Schema for creating a product"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: Decimal = Field(..., gt=0, decimal_places=2)
    stock: int = Field(..., ge=0)
    is_active: bool = Field(default=True)


class ProductUpdate(BaseModel):
    """Schema for updating a product"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    stock: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class CustomerCreate(BaseModel):
    """Schema for creating a customer"""
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=200)


class AddCartItemRequest(BaseModel):
    """Schema for adding item to cart"""
    cart_id: UUID
    product_id: UUID
    quantity: int = Field(..., gt=0)


class UpdateCartItemRequest(BaseModel):
    """Schema for updating cart item quantity"""
    quantity: int = Field(..., gt=0)


class CheckoutRequest(BaseModel):
    """Schema for cart checkout"""
    cart_id: UUID


class PaymentRequest(BaseModel):
    """Schema for payment simulation"""
    order_id: UUID


class CancelOrderRequest(BaseModel):
    """Schema for order cancellation"""
    order_id: UUID


class ClearCartRequest(BaseModel):
    """Schema for clearing cart"""
    cart_id: UUID


# ============================================================================
# IN-MEMORY STORAGE
# ============================================================================

products_db: Dict[UUID, Product] = {}
customers_db: Dict[UUID, Customer] = {}
customer_emails: Dict[str, UUID] = {}  # Email uniqueness index
carts_db: Dict[UUID, Cart] = {}
customer_carts: Dict[UUID, UUID] = {}  # Customer to active cart mapping
orders_db: Dict[UUID, Order] = {}
customer_orders: Dict[UUID, List[UUID]] = {}  # Customer to orders mapping


# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="E-commerce API",
    description="Complete e-commerce API with products, customers, carts, and orders",
    version="1.0.0"
)


# ============================================================================
# PRODUCT ENDPOINTS
# ============================================================================

@app.post("/products", response_model=Product, status_code=201)
async def create_product(product_data: ProductCreate):
    """
    Create a new product
    
    Validates:
    - Price must be greater than 0
    - Stock must be non-negative
    """
    product = Product(
        id=uuid4(),
        name=product_data.name,
        description=product_data.description,
        price=product_data.price,
        stock=product_data.stock,
        is_active=product_data.is_active
    )
    
    products_db[product.id] = product
    return product


@app.get("/products", response_model=List[Product])
async def list_products(active_only: bool = Query(True, description="Filter active products only")):
    """
    List all products
    
    By default, returns only active products
    """
    if active_only:
        return [p for p in products_db.values() if p.is_active]
    return list(products_db.values())


@app.get("/products/{id}", response_model=Product)
async def get_product(id: UUID):
    """
    Get product details by ID
    
    Raises:
    - 404: Product not found
    """
    if id not in products_db:
        raise HTTPException(status_code=404, detail=f"Product {id} not found")
    
    return products_db[id]


@app.put("/products/{id}", response_model=Product)
async def update_product(id: UUID, product_data: ProductUpdate):
    """
    Update product details
    
    Validates:
    - Price must be greater than 0 (if provided)
    - Stock must be non-negative (if provided)
    
    Raises:
    - 404: Product not found
    """
    if id not in products_db:
        raise HTTPException(status_code=404, detail=f"Product {id} not found")
    
    product = products_db[id]
    
    update_data = product_data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(product, field, value)
    
    # Re-validate after update
    try:
        Product.model_validate(product.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    products_db[id] = product
    return product


@app.delete("/products/{id}", status_code=200)
async def deactivate_product(id: UUID):
    """
    Deactivate a product (soft delete)
    
    Raises:
    - 404: Product not found
    """
    if id not in products_db:
        raise HTTPException(status_code=404, detail=f"Product {id} not found")
    
    product = products_db[id]
    product.is_active = False
    products_db[id] = product
    
    return {"message": f"Product {id} deactivated successfully"}


# ============================================================================
# CUSTOMER ENDPOINTS
# ============================================================================

@app.post("/customers", response_model=Customer, status_code=201)
async def create_customer(customer_data: CustomerCreate):
    """
    Register a new customer
    
    Validates:
    - Email must be valid format
    - Email must be unique
    
    Raises:
    - 400: Email already registered
    """
    # Check email uniqueness
    if customer_data.email in customer_emails:
        raise HTTPException(
            status_code=400,
            detail=f"Email {customer_data.email} is already registered"
        )
    
    customer = Customer(
        id=uuid4(),
        email=customer_data.email,
        full_name=customer_data.full_name,
        created_at=datetime.utcnow()
    )
    
    customers_db[customer.id] = customer
    customer_emails[customer.email] = customer.id
    customer_orders[customer.id] = []
    
    return customer


@app.get("/customers/{id}", response_model=Customer)
async def get_customer(id: UUID):
    """
    Get customer details by ID
    
    Raises:
    - 404: Customer not found
    """
    if id not in customers_db:
        raise HTTPException(status_code=404, detail=f"Customer {id} not found")
    
    return customers_db[id]


# ============================================================================
# CART ENDPOINTS
# ============================================================================

@app.post("/carts", response_model=Cart, status_code=201)
async def create_or_add_to_cart(request: AddCartItemRequest):
    """
    Add item to cart (creates cart if needed)
    
    Validates:
    - Product exists and is active
    - Sufficient stock available
    - Quantity is positive
    
    Raises:
    - 404: Product or cart not found
    - 400: Product inactive or insufficient stock
    """
    # Validate product exists
    if request.product_id not in products_db:
        raise HTTPException(status_code=404, detail=f"Product {request.product_id} not found")
    
    product = products_db[request.product_id]
    
    # Validate product is active
    if not product.is_active:
        raise HTTPException(status_code=400, detail=f"Product {product.name} is not active")
    
    # Validate sufficient stock
    if product.stock < request.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock for {product.name}. Available: {product.stock}, Requested: {request.quantity}"
        )
    
    # Get or validate cart
    if request.cart_id not in carts_db:
        raise HTTPException(status_code=404, detail=f"Cart {request.cart_id} not found")
    
    cart = carts_db[request.cart_id]
    
    # Validate cart is active
    if cart.status != CartStatus.ACTIVE:
        raise HTTPException(status_code=400, detail=f"Cart {request.cart_id} is not active")
    
    # Check if product already in cart
    existing_item = None
    for item in cart.items:
        if item.product_id == request.product_id:
            existing_item = item
            break
    
    if existing_item:
        # Update quantity
        new_quantity = existing_item.quantity + request.quantity
        
        # Validate total stock
        if product.stock < new_quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {product.name}. Available: {product.stock}, Requested: {new_quantity}"
            )
        
        existing_item.quantity = new_quantity
        existing_item.subtotal = product.price * new_quantity
    else:
        # Add new item
        cart_item = CartItem(
            id=uuid4(),
            product_id=product.id,
            product_name=product.name,
            product_price=product.price,
            quantity=request.quantity,
            subtotal=product.price * request.quantity
        )
        cart.items.append(cart_item)
    
    cart.updated_at = datetime.utcnow()
    carts_db[cart.id] = cart
    
    return cart


@app.get("/carts/{id}", response_model=Cart)
async def get_cart(id: UUID):
    """
    Get cart details by ID
    
    Raises:
    - 404: Cart not found
    """
    if id not in carts_db:
        raise HTTPException(status_code=404, detail=f"Cart {id} not found")
    
    return carts_db[id]


@app.put("/items/{id}", response_model=Cart)
async def update_cart_item(id: UUID, request: UpdateCartItemRequest):
    """
    Update cart item quantity
    
    Validates:
    - Item exists in a cart
    - Sufficient stock available
    - Quantity is positive
    
    Raises:
    - 404: Item not found
    - 400: Insufficient stock
    """
    # Find cart containing this item
    cart = None
    item = None
    
    for c in carts_db.values():
        for i in c.items:
            if i.id == id:
                cart = c
                item = i
                break
        if cart:
            break
    
    if not cart or not item:
        raise HTTPException(status_code=404, detail=f"Cart item {id} not found")
    
    # Validate cart is active
    if cart.status != CartStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Cannot update items in inactive cart")
    
    # Validate product still exists and has stock
    if item.product_id not in products_db:
        raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
    
    product = products_db[item.product_id]
    
    # Validate sufficient stock
    if product.stock < request.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock for {product.name}. Available: {product.stock}, Requested: {request.quantity}"
        )
    
    # Update item
    item.quantity = request.quantity
    item.subtotal = item.product_price * request.quantity
    cart.updated_at = datetime.utcnow()
    
    carts_db[cart.id] = cart
    
    return cart


@app.post("/carts/action", status_code=200)
async def clear_cart(request: ClearCartRequest):
    """
    Clear all items from cart
    
    Raises:
    - 404: Cart not found
    - 400: Cart not active
    """
    if request.cart_id not in carts_db:
        raise HTTPException(status_code=404, detail=f"Cart {request.cart_id} not found")
    
    cart = carts_db[request.cart_id]
    
    if cart.status != CartStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Cannot clear inactive cart")
    
    cart.items = []
    cart.updated_at = datetime.utcnow()
    carts_db[request.cart_id] = cart
    
    return {"message": f"Cart {request.cart_id} cleared successfully"}


@app.post("/carts/checkout", response_model=Order, status_code=201)
async def checkout_cart(request: CheckoutRequest):
    """
    Checkout cart and create order
    
    Validates:
    - Cart exists and is active
    - Cart has items
    - All products still available with sufficient stock
    
    Updates:
    - Product stock levels
    - Cart status to CHECKED_OUT
    
    Raises:
    - 404: Cart not found
    - 400: Cart empty, inactive, or insufficient stock
    """
    if request.cart_id not in carts_db:
        raise HTTPException(status_code=404, detail=f"Cart {request.cart_id} not found")
    
    cart = carts_db[request.cart_id]
    
    # Validate cart is active
    if cart.status != CartStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Cart is not active")
    
    # Validate cart has items
    if not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Validate all products and stock
    for item in cart.items:
        if item.product_id not in products_db:
            raise HTTPException(
                status_code=400,
                detail=f"Product {item.product_id} no longer available"
            )
        
        product = products_db[item.product_id]
        
        if not product.is_active:
            raise HTTPException(
                status_code=400,
                detail=f"Product {product.name} is no longer active"
            )
        
        if product.stock < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {product.name}. Available: {product.stock}, Required: {item.quantity}"
            )
    
    # Create order items
    order_items = []
    total_amount = Decimal("0.00")
    
    for cart_item in cart.items:
        order_item = OrderItem(
            id=uuid4(),
            product_id=cart_item.product_id,
            product_name=cart_item.product_name,
            product_price=cart_item.product_price,
            quantity=cart_item.quantity,
            subtotal=cart_item.subtotal
        )
        order_items.append(order_item)
        total_amount += cart_item.subtotal
    
    # Create order
    order = Order(
        id=uuid4(),
        customer_id=cart.customer_id,
        items=order_items,
        total_amount=total_amount,
        status=OrderStatus.PENDING,
        payment_status=PaymentStatus.PENDING,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Update product stock
    for item in cart.items:
        product = products_db[item.product_id]
        product.stock -= item.quantity
        products_db[item.product_id] = product
    
    # Update cart status
    cart.status = CartStatus.CHECKED_OUT
    cart.updated_at = datetime.utcnow()
    carts_db[cart.id] = cart
    
    # Store order
    orders_db[order.id] = order
    
    # Add to customer orders
    if cart.customer_id not in customer_orders:
        customer_orders[cart.customer_id] = []
    customer_orders[cart.customer_id].append(order.id)
    
    # Remove active cart mapping
    if cart.customer_id in customer_carts and customer_carts[cart.customer_id] == cart.id:
        del customer_carts[cart.customer_id]
    
    return order


# ============================================================================
# ORDER ENDPOINTS
# ============================================================================

@app.post("/unknowns/{id}/payment", response_model=Order)
async def simulate_payment(id: UUID):
    """
    Simulate successful payment for an order
    
    Updates:
    - Payment status to PAID
    - Order status to CONFIRMED
    
    Raises:
    - 404: Order not found
    - 400: Order already paid or cancelled
    """
    if id not in orders_db:
        raise HTTPException(status_code=404, detail=f"Order {id} not found")
    
    order = orders_db[id]
    
    # Validate order can be paid
    if order.payment_status == PaymentStatus.PAID:
        raise HTTPException(status_code=400, detail="Order already paid")
    
    if order.status == OrderStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Cannot pay cancelled order")
    
    # Update payment and order status
    order.payment_status = PaymentStatus.PAID
    order.status = OrderStatus.CONFIRMED
    order.updated_at = datetime.utcnow()
    
    orders_db[id] = order
    
    return order


@app.post("/orders/action", status_code=200)
async def cancel_order(request: CancelOrderRequest):
    """
    Cancel an order
    
    Validates:
    - Order exists
    - Order not already delivered
    
    Updates:
    - Order status to CANCELLED
    - Restores product stock if payment was made
    
    Raises:
    - 404: Order not found
    - 400: Order already delivered or cancelled
    """
    if request.order_id not in orders_db:
        raise HTTPException(status_code=404, detail=f"Order {request.order_id} not found")
    
    order = orders_db[request.order_id]
    
    # Validate order can be cancelled
    if order.status == OrderStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Order already cancelled")
    
    if order.status == OrderStatus.DELIVERED:
        raise HTTPException(status_code=400, detail="Cannot cancel delivered order")
    
    # Restore stock
    for item in order.items:
        if item.product_id in products_db:
            product = products_db[item.product_id]
            product.stock += item.quantity
            products_db[item.product_id] = product
    
    # Update order status
    order.status = OrderStatus.CANCELLED
    order.updated_at = datetime.utcnow()
    
    orders_db[request.order_id] = order
    
    return {"message": f"Order {request.order_id} cancelled successfully"}


@app.get("/customers", response_model=List[Order])
async def list_customer_orders(customer_id: UUID = Query(..., description="Customer ID")):
    """
    List all orders for a customer
    
    Raises:
    - 404: Customer not found
    """
    if customer_id not in customers_db:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    
    if customer_id not in customer_orders:
        return []
    
    order_ids = customer_orders[customer_id]
    return [orders_db[order_id] for order_id in order_ids if order_id in orders_db]


@app.get("/orders/{id}", response_model=Order)
async def get_order(id: UUID):
    """
    Get order details by ID
    
    Raises:
    - 404: Order not found
    """
    if id not in orders_db:
        raise HTTPException(status_code=404, detail=f"Order {id} not found")
    
    return orders_db[id]


# ============================================================================
# HELPER ENDPOINT - Create cart for customer
# ============================================================================

@app.post("/customers/{customer_id}/carts", response_model=Cart, status_code=201)
async def create_cart_for_customer(customer_id: UUID):
    """
    Create a new cart for a customer
    
    Raises:
    - 404: Customer not found
    - 400: Customer already has an active cart
    """
    if customer_id not in customers_db:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    
    # Check if customer already has an active cart
    if customer_id in customer_carts:
        existing_cart_id = customer_carts[customer_id]
        if existing_cart_id in carts_db:
            existing_cart = carts_db[existing_cart_id]
            if existing_cart.status == CartStatus.ACTIVE:
                raise HTTPException(
                    status_code=400,
                    detail=f"Customer already has an active cart: {existing_cart_id}"
                )
    
    # Create new cart
    cart = Cart(
        id=uuid4(),
        customer_id=customer_id,
        items=[],
        status=CartStatus.ACTIVE,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    carts_db[cart.id] = cart
    customer_carts[customer_id] = cart.id
    
    return cart


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/")
async def root():
    """API root endpoint with basic information"""
    return {
        "message": "E-commerce API",
        "version": "1.0.0",
        "endpoints": {
            "products": "/products",
            "customers": "/customers",
            "carts": "/carts",
            "orders": "/orders"
        }
    }


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "products_count": len(products_db),
        "customers_count": len(customers_db),
        "carts_count": len(carts_db),
        "orders_count": len(orders_db)
    }