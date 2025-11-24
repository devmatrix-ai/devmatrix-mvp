"""
Complete E-commerce API with Products, Customers, Carts, and Orders
FastAPI application implementing full shopping cart and order management system
"""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List, Dict
from decimal import Decimal
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum


# ============================================================================
# ENUMS
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
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    """Payment status enumeration"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

# Product Models
class ProductBase(BaseModel):
    """Base product model with common fields"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: Decimal = Field(..., gt=0, decimal_places=2)
    stock: int = Field(..., ge=0)
    is_active: bool = Field(default=True)


class ProductCreate(ProductBase):
    """Model for creating a new product"""
    pass


class ProductUpdate(BaseModel):
    """Model for updating a product (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    stock: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class Product(ProductBase):
    """Complete product model with ID"""
    id: UUID

    class Config:
        from_attributes = True


# Customer Models
class CustomerBase(BaseModel):
    """Base customer model"""
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=200)


class CustomerCreate(CustomerBase):
    """Model for creating a new customer"""
    pass


class Customer(CustomerBase):
    """Complete customer model with ID and timestamp"""
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# Cart Item Models
class CartItemBase(BaseModel):
    """Base cart item model"""
    product_id: UUID
    quantity: int = Field(..., gt=0)


class CartItemCreate(CartItemBase):
    """Model for adding item to cart"""
    pass


class CartItemUpdate(BaseModel):
    """Model for updating cart item quantity"""
    quantity: int = Field(..., gt=0)


class CartItem(CartItemBase):
    """Complete cart item with product details"""
    id: UUID
    product_name: str
    product_price: Decimal
    subtotal: Decimal

    class Config:
        from_attributes = True


# Cart Models
class CartCreate(BaseModel):
    """Model for creating a new cart"""
    customer_id: UUID


class Cart(BaseModel):
    """Complete cart model"""
    id: UUID
    customer_id: UUID
    items: List[CartItem]
    status: CartStatus
    total_amount: Decimal

    class Config:
        from_attributes = True


# Order Models
class OrderItem(BaseModel):
    """Order item model"""
    id: UUID
    product_id: UUID
    product_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

    class Config:
        from_attributes = True


class Order(BaseModel):
    """Complete order model"""
    id: UUID
    customer_id: UUID
    items: List[OrderItem]
    total_amount: Decimal
    status: OrderStatus
    payment_status: PaymentStatus
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# IN-MEMORY STORAGE
# ============================================================================

products_db: Dict[UUID, Dict] = {}
customers_db: Dict[UUID, Dict] = {}
carts_db: Dict[UUID, Dict] = {}
orders_db: Dict[UUID, Dict] = {}
customer_emails: Dict[str, UUID] = {}  # Track unique emails


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_cart_total(cart_data: Dict) -> Decimal:
    """Calculate total amount for cart"""
    total = Decimal("0.00")
    for item in cart_data["items"]:
        total += item["subtotal"]
    return total


def calculate_order_total(order_data: Dict) -> Decimal:
    """Calculate total amount for order"""
    total = Decimal("0.00")
    for item in order_data["items"]:
        total += item["subtotal"]
    return total


def get_product_or_404(product_id: UUID) -> Dict:
    """Get product by ID or raise 404"""
    product = products_db.get(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found"
        )
    return product


def get_customer_or_404(customer_id: UUID) -> Dict:
    """Get customer by ID or raise 404"""
    customer = customers_db.get(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with id {customer_id} not found"
        )
    return customer


def get_cart_or_404(cart_id: UUID) -> Dict:
    """Get cart by ID or raise 404"""
    cart = carts_db.get(cart_id)
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart with id {cart_id} not found"
        )
    return cart


def get_order_or_404(order_id: UUID) -> Dict:
    """Get order by ID or raise 404"""
    order = orders_db.get(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id {order_id} not found"
        )
    return order


def find_cart_item(cart_data: Dict, item_id: UUID) -> Optional[Dict]:
    """Find cart item by ID"""
    for item in cart_data["items"]:
        if item["id"] == item_id:
            return item
    return None


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="E-commerce API",
    description="Complete shopping cart and order management system",
    version="1.0.0"
)


# ============================================================================
# PRODUCT ENDPOINTS
# ============================================================================

@app.post("/products", response_model=Product, status_code=status.HTTP_201_CREATED)
def create_product(product: ProductCreate):
    """
    Create a new product
    
    - **name**: Product name (required)
    - **description**: Product description (optional)
    - **price**: Product price, must be greater than 0
    - **stock**: Available stock, must be non-negative
    - **is_active**: Whether product is active (default: true)
    """
    product_id = uuid4()
    product_data = {
        "id": product_id,
        **product.model_dump()
    }
    products_db[product_id] = product_data
    return Product(**product_data)


@app.get("/products", response_model=List[Product])
def list_products():
    """
    List all active products
    
    Returns only products where is_active=true
    """
    active_products = [
        Product(**product)
        for product in products_db.values()
        if product.get("is_active", True)
    ]
    return active_products


@app.get("/products/{id}", response_model=Product)
def get_product(id: UUID):
    """
    Get product details by ID
    
    Returns complete product information including inactive products
    """
    product = get_product_or_404(id)
    return Product(**product)


@app.put("/products/{id}", response_model=Product)
def update_product(id: UUID, product_update: ProductUpdate):
    """
    Update product information
    
    All fields are optional. Only provided fields will be updated.
    """
    product = get_product_or_404(id)
    
    update_data = product_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        product[field] = value
    
    products_db[id] = product
    return Product(**product)


@app.delete("/products/{id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_product(id: UUID):
    """
    Deactivate a product (soft delete)
    
    Sets is_active=false instead of removing from database
    """
    product = get_product_or_404(id)
    product["is_active"] = False
    products_db[id] = product
    return None


# ============================================================================
# CUSTOMER ENDPOINTS
# ============================================================================

@app.post("/customers", response_model=Customer, status_code=status.HTTP_201_CREATED)
def register_customer(customer: CustomerCreate):
    """
    Register a new customer
    
    - **email**: Valid email address (must be unique)
    - **full_name**: Customer's full name
    """
    # Check for duplicate email
    if customer.email in customer_emails:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Customer with email {customer.email} already exists"
        )
    
    customer_id = uuid4()
    customer_data = {
        "id": customer_id,
        "email": customer.email,
        "full_name": customer.full_name,
        "created_at": datetime.utcnow()
    }
    
    customers_db[customer_id] = customer_data
    customer_emails[customer.email] = customer_id
    
    return Customer(**customer_data)


@app.get("/customers/{id}", response_model=Customer)
def get_customer(id: UUID):
    """
    Get customer details by ID
    """
    customer = get_customer_or_404(id)
    return Customer(**customer)


# ============================================================================
# CART ENDPOINTS
# ============================================================================

@app.post("/carts", response_model=Cart, status_code=status.HTTP_201_CREATED)
def create_cart(cart_create: CartCreate):
    """
    Create a new shopping cart for a customer
    
    - **customer_id**: ID of the customer
    """
    # Verify customer exists
    get_customer_or_404(cart_create.customer_id)
    
    cart_id = uuid4()
    cart_data = {
        "id": cart_id,
        "customer_id": cart_create.customer_id,
        "items": [],
        "status": CartStatus.ACTIVE,
        "total_amount": Decimal("0.00")
    }
    
    carts_db[cart_id] = cart_data
    return Cart(**cart_data)


@app.post("/carts/{id}/items", response_model=Cart)
def add_item_to_cart(id: UUID, item: CartItemCreate):
    """
    Add an item to the cart
    
    - **product_id**: ID of the product to add
    - **quantity**: Quantity to add (must be greater than 0)
    
    Validates:
    - Product exists and is active
    - Sufficient stock available
    - Updates or creates cart item
    """
    cart = get_cart_or_404(id)
    
    # Verify cart is active
    if cart["status"] != CartStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify cart that is not active"
        )
    
    # Get and validate product
    product = get_product_or_404(item.product_id)
    
    if not product.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product is not active"
        )
    
    # Check stock availability
    if product["stock"] < item.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock. Available: {product['stock']}, Requested: {item.quantity}"
        )
    
    # Check if item already exists in cart
    existing_item = None
    for cart_item in cart["items"]:
        if cart_item["product_id"] == item.product_id:
            existing_item = cart_item
            break
    
    if existing_item:
        # Update existing item
        new_quantity = existing_item["quantity"] + item.quantity
        
        # Check stock for new total quantity
        if product["stock"] < new_quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock. Available: {product['stock']}, Requested total: {new_quantity}"
            )
        
        existing_item["quantity"] = new_quantity
        existing_item["subtotal"] = Decimal(str(product["price"])) * new_quantity
    else:
        # Add new item
        cart_item_data = {
            "id": uuid4(),
            "product_id": item.product_id,
            "product_name": product["name"],
            "product_price": Decimal(str(product["price"])),
            "quantity": item.quantity,
            "subtotal": Decimal(str(product["price"])) * item.quantity
        }
        cart["items"].append(cart_item_data)
    
    # Recalculate total
    cart["total_amount"] = calculate_cart_total(cart)
    
    carts_db[id] = cart
    return Cart(**cart)


@app.get("/carts/{id}", response_model=Cart)
def get_cart(id: UUID):
    """
    View current cart with all items
    """
    cart = get_cart_or_404(id)
    return Cart(**cart)


@app.put("/carts/{id}/items/{item_id}", response_model=Cart)
def update_cart_item(id: UUID, item_id: UUID, item_update: CartItemUpdate):
    """
    Update quantity of a specific cart item
    
    - **quantity**: New quantity (must be greater than 0)
    
    Validates stock availability for new quantity
    """
    cart = get_cart_or_404(id)
    
    # Verify cart is active
    if cart["status"] != CartStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify cart that is not active"
        )
    
    # Find cart item
    cart_item = find_cart_item(cart, item_id)
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart item with id {item_id} not found"
        )
    
    # Get product and check stock
    product = get_product_or_404(cart_item["product_id"])
    
    if product["stock"] < item_update.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock. Available: {product['stock']}, Requested: {item_update.quantity}"
        )
    
    # Update item
    cart_item["quantity"] = item_update.quantity
    cart_item["subtotal"] = Decimal(str(product["price"])) * item_update.quantity
    
    # Recalculate total
    cart["total_amount"] = calculate_cart_total(cart)
    
    carts_db[id] = cart
    return Cart(**cart)


@app.delete("/carts/{id}/items", status_code=status.HTTP_204_NO_CONTENT)
def clear_cart(id: UUID):
    """
    Remove all items from cart
    """
    cart = get_cart_or_404(id)
    
    # Verify cart is active
    if cart["status"] != CartStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify cart that is not active"
        )
    
    cart["items"] = []
    cart["total_amount"] = Decimal("0.00")
    
    carts_db[id] = cart
    return None


@app.post("/carts/{id}/checkout", response_model=Order)
def checkout_cart(id: UUID):
    """
    Checkout cart and create an order
    
    Process:
    1. Validates cart is active and has items
    2. Checks stock availability for all items
    3. Reduces product stock
    4. Creates order with PENDING status
    5. Marks cart as CHECKED_OUT
    """
    cart = get_cart_or_404(id)
    
    # Verify cart is active
    if cart["status"] != CartStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is not active"
        )
    
    # Verify cart has items
    if not cart["items"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot checkout empty cart"
        )
    
    # Verify customer exists
    get_customer_or_404(cart["customer_id"])
    
    # Validate stock for all items
    for cart_item in cart["items"]:
        product = get_product_or_404(cart_item["product_id"])
        
        if not product.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product {product['name']} is no longer active"
            )
        
        if product["stock"] < cart_item["quantity"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for {product['name']}. Available: {product['stock']}, Required: {cart_item['quantity']}"
            )
    
    # Create order
    order_id = uuid4()
    order_items = []
    
    for cart_item in cart["items"]:
        product = products_db[cart_item["product_id"]]
        
        # Reduce stock
        product["stock"] -= cart_item["quantity"]
        products_db[cart_item["product_id"]] = product
        
        # Create order item
        order_item = {
            "id": uuid4(),
            "product_id": cart_item["product_id"],
            "product_name": cart_item["product_name"],
            "quantity": cart_item["quantity"],
            "unit_price": cart_item["product_price"],
            "subtotal": cart_item["subtotal"]
        }
        order_items.append(order_item)
    
    order_data = {
        "id": order_id,
        "customer_id": cart["customer_id"],
        "items": order_items,
        "total_amount": cart["total_amount"],
        "status": OrderStatus.PENDING,
        "payment_status": PaymentStatus.PENDING,
        "created_at": datetime.utcnow()
    }
    
    orders_db[order_id] = order_data
    
    # Update cart status
    cart["status"] = CartStatus.CHECKED_OUT
    carts_db[id] = cart
    
    return Order(**order_data)


# ============================================================================
# ORDER ENDPOINTS
# ============================================================================

@app.post("/orders/{id}/payment", response_model=Order)
def process_payment(id: UUID):
    """
    Simulate successful payment for an order
    
    Updates:
    - payment_status to COMPLETED
    - order status to CONFIRMED
    """
    order = get_order_or_404(id)
    
    # Verify order is in correct state
    if order["payment_status"] != PaymentStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot process payment. Current payment status: {order['payment_status']}"
        )
    
    if order["status"] == OrderStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot process payment for cancelled order"
        )
    
    # Update payment and order status
    order["payment_status"] = PaymentStatus.COMPLETED
    order["status"] = OrderStatus.CONFIRMED
    
    orders_db[id] = order
    return Order(**order)


@app.post("/orders/{id}/cancel", response_model=Order)
def cancel_order(id: UUID):
    """
    Cancel an order
    
    Process:
    1. Validates order can be cancelled (not already cancelled or delivered)
    2. Restores product stock
    3. Updates order status to CANCELLED
    4. If payment was completed, marks for refund
    """
    order = get_order_or_404(id)
    
    # Verify order can be cancelled
    if order["status"] == OrderStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is already cancelled"
        )
    
    if order["status"] == OrderStatus.DELIVERED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel delivered order"
        )
    
    # Restore stock for all items
    for order_item in order["items"]:
        product = products_db.get(order_item["product_id"])
        if product:  # Product might have been deleted
            product["stock"] += order_item["quantity"]
            products_db[order_item["product_id"]] = product
    
    # Update order status
    order["status"] = OrderStatus.CANCELLED
    
    # Handle payment refund if payment was completed
    if order["payment_status"] == PaymentStatus.COMPLETED:
        order["payment_status"] = PaymentStatus.REFUNDED
    
    orders_db[id] = order
    return Order(**order)


@app.get("/customers/{id}/orders", response_model=List[Order])
def list_customer_orders(id: UUID):
    """
    List all orders for a specific customer
    
    Returns orders sorted by creation date (newest first)
    """
    # Verify customer exists
    get_customer_or_404(id)
    
    customer_orders = [
        Order(**order)
        for order in orders_db.values()
        if order["customer_id"] == id
    ]
    
    # Sort by created_at descending
    customer_orders.sort(key=lambda x: x.created_at, reverse=True)
    
    return customer_orders


@app.get("/orders/{id}", response_model=Order)
def get_order(id: UUID):
    """
    Get order details by ID
    """
    order = get_order_or_404(id)
    return Order(**order)


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/")
def root():
    """
    API root endpoint with basic information
    """
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
def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "stats": {
            "products": len(products_db),
            "customers": len(customers_db),
            "carts": len(carts_db),
            "orders": len(orders_db)
        }
    }