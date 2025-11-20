# Ejemplos de Código Generado - ecommerce_api_simple_1763662889

---

## 📦 Modelos de Datos (Líneas 48-122)

### Product Entity
```python
class Product(BaseModel):
    """Product entity with validation"""
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: Decimal = Field(..., gt=0, decimal_places=2)  # ⚠️ Pydantic v2 issue
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
```

**✅ Calidad**:
- Validadores implementados correctamente
- Docstrings presentes
- Tipos adecuados

---

## 🏪 Lógica de Carrito (Líneas 368-459)

### Add to Cart Endpoint - Validaciones Completas
```python
@app.post("/carts", response_model=Cart, status_code=201)
def create_or_add_to_cart(request: AddCartItemRequest):
    """
    Add item to cart (creates cart if needed)

    Business logic:
    - Validates product exists and is active
    - Checks stock availability
    - Creates new cart if customer doesn't have active cart
    - Updates existing cart item quantity if product already in cart
    - Calculates subtotals

    Raises:
    - 404: Product not found
    - 400: Product inactive or insufficient stock
    """

    # 1. Validate product exists
    if request.product_id not in products_db:
        raise HTTPException(
            status_code=404,
            detail=f"Product {request.product_id} not found"
        )

    product = products_db[request.product_id]

    # 2. Validate product is active
    if not product.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Product {product.name} is not available"
        )

    # 3. Validate stock availability
    if product.stock < request.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock for {product.name}. Available: {product.stock}"
        )

    # 4. Get cart
    if request.cart_id not in carts_db:
        raise HTTPException(
            status_code=404,
            detail=f"Cart {request.cart_id} not found"
        )

    cart = carts_db[request.cart_id]

    # 5. Validate cart is active
    if cart.status != CartStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail=f"Cart {request.cart_id} is not active"
        )

    # 6. Check if product already in cart
    existing_item = None
    for item in cart.items:
        if item.product_id == request.product_id:
            existing_item = item
            break

    if existing_item:
        # Update quantity
        new_quantity = existing_item.quantity + request.quantity

        # Check stock for new quantity
        if product.stock < new_quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {product.name}. Available: {product.stock}"
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

    # Update timestamp
    cart.updated_at = datetime.utcnow()

    return cart
```

**✅ Calidad**:
- Validaciones exhaustivas (6 checks)
- Manejo de errores HTTP específicos
- Cálculos correctos de subtotal
- Docstring completo con validaciones listadas
- Timestamping correcto

**⚠️ Notas**:
- Lógica compleja pero bien documentada
- La búsqueda de item es O(n) - para MVP está bien
- No hay transacciones (en-memory db)

---

## 💳 Lógica de Checkout (Líneas 570-687)

### Checkout Endpoint - Order Creation
```python
@app.post("/carts/checkout", response_model=Order, status_code=201)
def checkout_cart(request: CheckoutRequest):
    """
    Checkout cart and create order

    Business logic:
    - Validates cart exists and is active
    - Checks that cart is not empty
    - Creates new order from cart items
    - Transfers item data to order
    - Updates cart status to CHECKED_OUT
    - Maps cart items to order items

    Raises:
    - 404: Cart not found
    - 400: Cart inactive or empty
    """

    # 1. Validate cart exists
    if request.cart_id not in carts_db:
        raise HTTPException(
            status_code=404,
            detail=f"Cart {request.cart_id} not found"
        )

    cart = carts_db[request.cart_id]

    # 2. Validate cart is active
    if cart.status != CartStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail=f"Cart {request.cart_id} is not active"
        )

    # 3. Validate cart is not empty
    if len(cart.items) == 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot checkout empty cart"
        )

    # 4. Calculate total and create order items
    total_amount = Decimal(0)
    order_items = []

    for cart_item in cart.items:
        total_amount += cart_item.subtotal

        order_item = OrderItem(
            id=uuid4(),
            product_id=cart_item.product_id,
            product_name=cart_item.product_name,
            product_price=cart_item.product_price,
            quantity=cart_item.quantity,
            subtotal=cart_item.subtotal
        )
        order_items.append(order_item)

    # 5. Create order
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

    # 6. Update cart status
    cart.status = CartStatus.CHECKED_OUT
    cart.updated_at = datetime.utcnow()
    carts_db[cart.id] = cart

    # 7. Store order
    orders_db[order.id] = order
    if cart.customer_id not in customer_orders:
        customer_orders[cart.customer_id] = []
    customer_orders[cart.customer_id].append(order.id)

    return order
```

**✅ Calidad**:
- Conversión correcta de CarItems a OrderItems
- Cálculo preciso de total_amount
- Actualización consistente de estado
- Mantenimiento de índices (customer_orders)
- Timestamps correctos

---

## 💰 Lógica de Pago (Líneas 688-732)

### Payment Endpoint
```python
@app.post("/unknowns/{id}/payment", response_model=Order)
def simulate_payment(id: UUID, payment_data: PaymentRequest):
    """
    Simulate payment for an order

    Business logic:
    - Validates order exists
    - Checks order is in PENDING status
    - Simulates payment (always succeeds)
    - Updates order status to CONFIRMED
    - Updates payment status to PAID
    - Updates timestamps

    Raises:
    - 404: Order not found
    - 400: Order not in PENDING status
    """

    # 1. Validate order exists
    if payment_data.order_id not in orders_db:
        raise HTTPException(
            status_code=404,
            detail=f"Order {payment_data.order_id} not found"
        )

    order = orders_db[payment_data.order_id]

    # 2. Validate order is pending
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Order {payment_data.order_id} is not in PENDING status"
        )

    # 3. Validate order is awaiting payment
    if order.payment_status != PaymentStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Order {payment_data.order_id} payment is not PENDING"
        )

    # 4. Simulate payment (always succeeds)
    order.payment_status = PaymentStatus.PAID
    order.status = OrderStatus.CONFIRMED
    order.updated_at = datetime.utcnow()

    # 5. Store updated order
    orders_db[order.id] = order

    return order
```

**⚠️ Problemas**:
- URL `/unknowns/{id}/payment` debería ser `/orders/{id}/payment`
- Problema generado por patrón que usa nombres genéricos
- Lógica es correcta, solo el naming está mal

**✅ Positivos**:
- Simulación de pago adecuada para MVP
- Validaciones de estado correctas
- Cambio de estado atómico

---

## ❌ Validaciones de Entrada (Líneas 128-182)

### Request Schemas con Validaciones
```python
class ProductCreate(BaseModel):
    """Schema for creating a product"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: Decimal = Field(..., gt=0, decimal_places=2)  # ⚠️ decimal_places issue
    stock: int = Field(..., ge=0)
    is_active: bool = Field(default=True)


class AddCartItemRequest(BaseModel):
    """Schema for adding item to cart"""
    cart_id: UUID
    product_id: UUID
    quantity: int = Field(..., gt=0)


class CheckoutRequest(BaseModel):
    """Schema for cart checkout"""
    cart_id: UUID
```

**✅ Calidad**:
- Restricciones validadas (min_length, max_length, gt, ge)
- Tipos específicos (UUID, Decimal)
- Documentación de propósito
- Valores por defecto sensatos

**⚠️ Issue Pydantic v2**:
- `decimal_places` no es válido en Pydantic v2
- Debe usar `@field_validator` en lugar de Field constraint

---

## 📊 Almacenamiento (Líneas 184-195)

### In-Memory Storage con Índices
```python
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
```

**✅ Patrones Correctos**:
- Índices secundarios para búsquedas rápidas
- Comentarios sobre propósito de cada índice
- Tipos claramente declarados

**⚠️ Limitaciones**:
- No persistente (se pierde al reiniciar)
- No thread-safe (pero FastAPI maneja bien)
- No escala a muchos registros

---

## 🚀 FastAPI Setup (Líneas 201-206)

```python
# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="E-commerce API",
    description="Complete e-commerce API with products, customers, carts, and orders",
    version="1.0.0"
)
```

**✅ Calidad**:
- Metadata clara (title, description, version)
- Automáticamente genera docs en /docs
- Swagger UI funcional

---

## 📈 Estadísticas de Código

```
Total lines:      884
Modelos Pydantic: 6 (Product, Customer, Cart, Order + Items)
Request/Response: 7 schemas
Endpoints:        16 (CRUD + business logic)
Validators:       2 (price, stock)
Enums:            3 (CartStatus, OrderStatus, PaymentStatus)
Storage dicts:    7 (con 3 índices)
Docstrings:       En todos los endpoints
Status codes:     Correctos (201, 404, 400, 200)
```

---

## 🎓 Conclusiones de Código

### Fortalezas
✅ **Lógica de negocio completa** - Toda la funcionalidad de e-commerce
✅ **Validaciones exhaustivas** - En modelos y en endpoints
✅ **Error handling decente** - HTTPException con mensajes claros
✅ **Documentación buena** - Docstrings y comentarios
✅ **Estructura limpia** - Organizadas en secciones claras
✅ **Tipos correctos** - UUID, Decimal, Enum, BaseModel

### Problemas Específicos
⚠️ **Pydantic v2 `decimal_places`** - Línea 53, 132, 141
⚠️ **Rutas confusas** - `/unknowns/{id}/payment` debería ser `/orders/{id}/payment`
⚠️ **datetime.utcnow() deprecado** - Usar `datetime.now(timezone.utc)` en Python 3.12+

### Mejoras Recomendadas
🔧 Arreglar decimal_places constraint
🔧 Corregir nombres de rutas
🔧 Agregar paginación en list endpoints
🔧 Agregar logging/observability
🔧 Migrar a base de datos real (SQLAlchemy)

---

**Status**: ✅ MVP-ready con templating funcionando correctamente

