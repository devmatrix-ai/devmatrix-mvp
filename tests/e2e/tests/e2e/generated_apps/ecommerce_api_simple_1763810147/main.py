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

def calculate_cart_total(items: List[Dict]) -> Decimal:
    """Calculate total amount for cart items"""
    return sum(Decimal(str(item["subtotal"])) for item in items)


def calculate_item_subtotal(price: Decimal, quantity: int) -> Decimal:
    """Calculate subtotal for a cart/order item"""
    return Decimal(str(price)) * Decimal(str(quantity))


def check_stock_availability(product_id: UUID, quantity: int) -> bool:
    """Check if product has sufficient stock"""
    if product_id not in products_db:
        return False
    product = products_db[product_id]
    return product["stock"] >= quantity


def reduce_product_stock(product_id: UUID, quantity: int):
    """Reduce product stock after order"""
    if product_id in products_db:
        products_db[product_id]["stock"] -= quantity


def restore_product_stock(product_id: UUID, quantity: int):
    """Restore product stock after order cancellation"""
    if product_id in products_db:
        products_db[product_id]["stock"] += quantity


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
async def create_product(product: ProductCreate):
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
async def list_products():
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
async def get_product(id: UUID):
    """
    Get product details by ID
    
    - **id**: Product UUID
    """
    if id not in products_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {id} not found"
        )
    return Product(**products_db[id])


@app.put("/products/{id}", response_model=Product)
async def update_product(id: UUID, product_update: ProductUpdate):
    """
    Update product details
    
    - **id**: Product UUID
    - All fields are optional, only provided fields will be updated
    """
    if id not in products_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {id} not found"
        )
    
    product_data = products_db[id]
    update_data = product_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        product_data[field] = value
    
    products_db[id] = product_data
    return Product(**product_data)


@app.delete("/products/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_product(id: UUID):
    """
    Deactivate a product (soft delete)
    
    - **id**: Product UUID
    Sets is_active to false instead of deleting
    """
    if id not in products_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {id} not found"
        )
    
    products_db[id]["is_active"] = False
    return None


# ============================================================================
# CUSTOMER ENDPOINTS
# ============================================================================

@app.post("/customers", response_model=Customer, status_code=status.HTTP_201_CREATED)
async def register_customer(customer: CustomerCreate):
    """
    Register a new customer
    
    - **email**: Customer email (must be unique and valid format)
    - **full_name**: Customer full name
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
async def get_customer(id: UUID):
    """
    Get customer details by ID
    
    - **id**: Customer UUID
    """
    if id not in customers_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with id {id} not found"
        )
    return Customer(**customers_db[id])


# ============================================================================
# CART ENDPOINTS
# ============================================================================

@app.post("/carts", response_model=Cart, status_code=status.HTTP_201_CREATED)
async def create_cart(cart_create: CartCreate):
    """
    Create a new shopping cart for a customer
    
    - **customer_id**: Customer UUID
    """
    # Verify customer exists
    if cart_create.customer_id not in customers_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with id {cart_create.customer_id} not found"
        )
    
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
async def add_item_to_cart(id: UUID, item: CartItemCreate):
    """
    Add an item to the cart
    
    - **id**: Cart UUID
    - **product_id**: Product UUID to add
    - **quantity**: Quantity to add (must be greater than 0)
    """
    # Verify cart exists and is active
    if id not in carts_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart with id {id} not found"
        )
    
    cart_data = carts_db[id]
    
    if cart_data["status"] != CartStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot modify cart with status {cart_data['status']}"
        )
    
    # Verify product exists and is active
    if item.product_id not in products_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {item.product_id} not found"
        )
    
    product = products_db[item.product_id]
    
    if not product.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product {item.product_id} is not active"
        )
    
    # Check stock availability
    if not check_stock_availability(item.product_id, item.quantity):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock for product {item.product_id}. Available: {product['stock']}"
        )
    
    # Check if item already exists in cart
    existing_item = None
    for cart_item in cart_data["items"]:
        if cart_item["product_id"] == item.product_id:
            existing_item = cart_item
            break
    
    if existing_item:
        # Update quantity of existing item
        new_quantity = existing_item["quantity"] + item.quantity
        
        # Check stock for new total quantity
        if not check_stock_availability(item.product_id, new_quantity):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for product {item.product_id}. Available: {product['stock']}"
            )
        
        existing_item["quantity"] = new_quantity
        existing_item["subtotal"] = calculate_item_subtotal(
            Decimal(str(product["price"])),
            new_quantity
        )
    else:
        # Add new item to cart
        cart_item_data = {
            "id": uuid4(),
            "product_id": item.product_id,
            "product_name": product["name"],
            "product_price": Decimal(str(product["price"])),
            "quantity": item.quantity,
            "subtotal": calculate_item_subtotal(
                Decimal(str(product["price"])),
                item.quantity
            )
        }
        cart_data["items"].append(cart_item_data)
    
    # Recalculate cart total
    cart_data["total_amount"] = calculate_cart_total(cart_data["items"])
    
    carts_db[id] = cart_data
    return Cart(**cart_data)


@app.get("/carts/{id}", response_model=Cart)
async def get_cart(id: UUID):
    """
    View current cart details
    
    - **id**: Cart UUID
    """
    if id not in carts_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart with id {id} not found"
        )
    return Cart(**carts_db[id])


@app.put("/carts/{id}/items/{item_id}", response_model=Cart)
async def update_cart_item(id: UUID, item_id: UUID, item_update: CartItemUpdate):
    """
    Update quantity of an item in the cart
    
    - **id**: Cart UUID
    - **item_id**: Cart item UUID
    - **quantity**: New quantity (must be greater than 0)
    """
    # Verify cart exists and is active
    if id not in carts_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart with id {id} not found"
        )
    
    cart_data = carts_db[id]
    
    if cart_data["status"] != CartStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot modify cart with status {cart_data['status']}"
        )
    
    # Find the item in cart
    cart_item = None
    for item in cart_data["items"]:
        if item["id"] == item_id:
            cart_item = item
            break
    
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found in cart"
        )
    
    # Check stock availability for new quantity
    if not check_stock_availability(cart_item["product_id"], item_update.quantity):
        product = products_db[cart_item["product_id"]]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock for product {cart_item['product_id']}. Available: {product['stock']}"
        )
    
    # Update item quantity and subtotal
    cart_item["quantity"] = item_update.quantity
    cart_item["subtotal"] = calculate_item_subtotal(
        cart_item["product_price"],
        item_update.quantity
    )
    
    # Recalculate cart total
    cart_data["total_amount"] = calculate_cart_total(cart_data["items"])
    
    carts_db[id] = cart_data
    return Cart(**cart_data)


@app.delete("/carts/{id}/items", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(id: UUID):
    """
    Clear all items from the cart
    
    - **id**: Cart UUID
    """
    if id not in carts_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart with id {id} not found"
        )
    
    cart_data = carts_db[id]
    
    if cart_data["status"] != CartStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot modify cart with status {cart_data['status']}"
        )
    
    cart_data["items"] = []
    cart_data["total_amount"] = Decimal("0.00")
    
    carts_db[id] = cart_data
    return None


@app.post("/carts/{id}/checkout", response_model=Order, status_code=status.HTTP_201_CREATED)
async def checkout_cart(id: UUID):
    """
    Checkout cart and create an order
    
    - **id**: Cart UUID
    Validates stock, creates order, reduces product stock, and marks cart as checked out
    """
    # Verify cart exists and is active
    if id not in carts_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart with id {id} not found"
        )
    
    cart_data = carts_db[id]
    
    if cart_data["status"] != CartStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot checkout cart with status {cart_data['status']}"
        )
    
    if not cart_data["items"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot checkout empty cart"
        )
    
    # Verify all items still have sufficient stock
    for cart_item in cart_data["items"]:
        if not check_stock_availability(cart_item["product_id"], cart_item["quantity"]):
            product = products_db[cart_item["product_id"]]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for product {cart_item['product_name']}. Available: {product['stock']}"
            )
    
    # Create order
    order_id = uuid4()
    order_items = []
    
    for cart_item in cart_data["items"]:
        order_item = {
            "id": uuid4(),
            "product_id": cart_item["product_id"],
            "product_name": cart_item["product_name"],
            "quantity": cart_item["quantity"],
            "unit_price": cart_item["product_price"],
            "subtotal": cart_item["subtotal"]
        }
        order_items.append(order_item)
        
        # Reduce product stock
        reduce_product_stock(cart_item["product_id"], cart_item["quantity"])
    
    order_data = {
        "id": order_id,
        "customer_id": cart_data["customer_id"],
        "items": order_items,
        "total_amount": cart_data["total_amount"],
        "status": OrderStatus.PENDING,
        "payment_status": PaymentStatus.PENDING,
        "created_at": datetime.utcnow()
    }
    
    orders_db[order_id] = order_data
    
    # Mark cart as checked out
    cart_data["status"] = CartStatus.CHECKED_OUT
    carts_db[id] = cart_data
    
    return Order(**order_data)


# ============================================================================
# ORDER ENDPOINTS
# ============================================================================

@app.post("/orders/{id}/payment", response_model=Order)
async def process_payment(id: UUID):
    """
    Simulate successful payment for an order
    
    - **id**: Order UUID
    Updates payment status to completed and order status to confirmed
    """
    if id not in orders_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id {id} not found"
        )
    
    order_data = orders_db[id]
    
    if order_data["payment_status"] == PaymentStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment already completed for this order"
        )
    
    if order_data["status"] == OrderStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot process payment for cancelled order"
        )
    
    order_data["payment_status"] = PaymentStatus.COMPLETED
    order_data["status"] = OrderStatus.CONFIRMED
    
    orders_db[id] = order_data
    return Order(**order_data)


@app.post("/orders/{id}/cancel", response_model=Order)
async def cancel_order(id: UUID):
    """
    Cancel an order
    
    - **id**: Order UUID
    Restores product stock and updates order status to cancelled
    Only pending/confirmed orders can be cancelled
    """
    if id not in orders_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id {id} not found"
        )
    
    order_data = orders_db[id]
    
    # Check if order can be cancelled
    if order_data["status"] in [OrderStatus.CANCELLED, OrderStatus.SHIPPED, OrderStatus.DELIVERED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel order with status {order_data['status']}"
        )
    
    # Restore product stock
    for order_item in order_data["items"]:
        restore_product_stock(order_item["product_id"], order_item["quantity"])
    
    # Update order status
    order_data["status"] = OrderStatus.CANCELLED
    
    # Handle payment refund if payment was completed
    if order_data["payment_status"] == PaymentStatus.COMPLETED:
        order_data["payment_status"] = PaymentStatus.REFUNDED
    
    orders_db[id] = order_data
    return Order(**order_data)


@app.get("/customers/{id}/orders", response_model=List[Order])
async def list_customer_orders(id: UUID):
    """
    List all orders for a customer
    
    - **id**: Customer UUID
    """
    if id not in customers_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with id {id} not found"
        )
    
    customer_orders = [
        Order(**order)
        for order in orders_db.values()
        if order["customer_id"] == id
    ]
    
    # Sort by created_at descending (newest first)
    customer_orders.sort(key=lambda x: x.created_at, reverse=True)
    
    return customer_orders


@app.get("/orders/{id}", response_model=Order)
async def get_order(id: UUID):
    """
    Get order details by ID
    
    - **id**: Order UUID
    """
    if id not in orders_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id {id} not found"
        )
    return Order(**orders_db[id])


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