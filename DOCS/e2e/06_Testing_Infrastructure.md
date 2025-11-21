# Infraestructura de Testing

## 📋 Índice

1. [Overview](#overview)
2. [Test Architecture](#test-architecture)
3. [Unit Tests](#unit-tests)
4. [Integration Tests](#integration-tests)
5. [Test Fixtures](#test-fixtures)
6. [Coverage](#coverage)
7. [CI/CD Integration](#cicd-integration)

---

## Overview

Las apps generadas incluyen **testing completo** con:

- ✅ **pytest** como framework principal
- ✅ **Unit tests** (models, services, repositories)
- ✅ **Integration tests** (endpoints E2E)
- ✅ **Fixtures** reutilizables (database, test data)
- ✅ **Factories** para generar datos (Factory pattern)
- ✅ **Coverage** 80%+ garantizado
- ✅ **Async support** con pytest-asyncio

```mermaid
graph TB
    subgraph "🧪 Test Suite"
        direction TB

        subgraph "Unit Tests"
            UT1[test_models.py<br/>Pydantic validation]
            UT2[test_repositories.py<br/>Database operations]
            UT3[test_services.py<br/>Business logic]
        end

        subgraph "Integration Tests"
            IT1[test_api.py<br/>Full endpoint flows]
            IT2[test_observability.py<br/>Metrics & health]
        end

        subgraph "Test Infrastructure"
            CONF[conftest.py<br/>Fixtures & config]
            FACT[factories.py<br/>Test data generation]
        end
    end

    subgraph "🔧 Test Tools"
        PYTEST[pytest<br/>Test runner]
        ASYNCIO[pytest-asyncio<br/>Async support]
        COV[pytest-cov<br/>Coverage reporting]
    end

    subgraph "💾 Test Database"
        TESTDB[(PostgreSQL Test DB<br/>Isolated from production)]
    end

    CONF --> UT1
    CONF --> UT2
    CONF --> UT3
    CONF --> IT1
    CONF --> IT2

    FACT --> UT2
    FACT --> UT3
    FACT --> IT1

    UT2 --> TESTDB
    IT1 --> TESTDB

    PYTEST --> UT1
    PYTEST --> UT2
    PYTEST --> UT3
    PYTEST --> IT1
    PYTEST --> IT2

    style PYTEST fill:#3498DB,stroke:#2874A6,color:#FFFFFF,stroke-width:3px
    style TESTDB fill:#336791,stroke:#2C5B7A,color:#FFFFFF,stroke-width:2px
    style UT1 fill:#9B59B6,stroke:#7D3C92,color:#FFFFFF,stroke-width:2px
    style UT2 fill:#9B59B6,stroke:#7D3C92,color:#FFFFFF,stroke-width:2px
    style UT3 fill:#9B59B6,stroke:#7D3C92,color:#FFFFFF,stroke-width:2px
    style IT1 fill:#E74C3C,stroke:#C0392B,color:#FFFFFF,stroke-width:2px
    style IT2 fill:#E74C3C,stroke:#C0392B,color:#FFFFFF,stroke-width:2px
```

---

## Test Architecture

### Directory Structure

```
tests/
├── __init__.py
├── conftest.py                 # pytest configuration & fixtures
├── factories.py                # Test data factories
├── test_observability.py       # Metrics & health checks
│
├── unit/                       # Unit tests (fast, isolated)
│   ├── __init__.py
│   ├── test_models.py          # Pydantic schema validation
│   ├── test_repositories.py    # Repository layer tests
│   └── test_services.py        # Service layer business logic
│
└── integration/                # Integration tests (slower, E2E)
    ├── __init__.py
    └── test_api.py             # Full API endpoint tests
```

### Test Pyramid

```mermaid
graph TB
    subgraph "🔺 Test Pyramid"
        direction TB

        E2E[Integration Tests<br/>Full API flows<br/>~10 tests<br/>Slow]
        INT[Service Tests<br/>Business logic<br/>~20 tests<br/>Medium]
        UNIT[Unit Tests<br/>Models, Schemas<br/>~15 tests<br/>Fast]

        UNIT --> INT
        INT --> E2E
    end

    subgraph "⚡ Execution Speed"
        FAST[Unit: ~0.5s]
        MED[Integration: ~2s]
        SLOW[E2E: ~5s]

        FAST --> MED
        MED --> SLOW
    end

    style UNIT fill:#27AE60,stroke:#1E8449,color:#FFFFFF,stroke-width:3px
    style INT fill:#F39C12,stroke:#D68910,color:#FFFFFF,stroke-width:2px
    style E2E fill:#E74C3C,stroke:#C0392B,color:#FFFFFF,stroke-width:2px
```

---

## Unit Tests

### Test Models (Pydantic Schemas)

**Archivo:** `tests/unit/test_models.py`

```python
import pytest
from decimal import Decimal
from pydantic import ValidationError
from src.models.schemas import ProductCreate, ProductUpdate

def test_product_create_valid():
    """✅ Valid product creation data passes validation"""
    data = ProductCreate(
        name="Laptop",
        description="Gaming laptop",
        price=Decimal("999.99"),
        stock=10,
        is_active=True
    )
    assert data.name == "Laptop"
    assert data.price == Decimal("999.99")

def test_product_create_invalid_price():
    """❌ Price must be > 0"""
    with pytest.raises(ValidationError) as exc_info:
        ProductCreate(
            name="Laptop",
            price=Decimal("0"),  # Invalid: price <= 0
            stock=10
        )
    assert "greater than 0" in str(exc_info.value)

def test_product_create_invalid_stock():
    """❌ Stock must be >= 0"""
    with pytest.raises(ValidationError):
        ProductCreate(
            name="Laptop",
            price=Decimal("999"),
            stock=-5  # Invalid: negative stock
        )

def test_product_update_partial():
    """✅ Partial updates are allowed"""
    data = ProductUpdate(price=Decimal("1299.99"))
    assert data.price == Decimal("1299.99")
    assert data.name is None  # Other fields optional
```

### Test Repositories

**Archivo:** `tests/unit/test_repositories.py`

```python
import pytest
from decimal import Decimal
from src.repositories.product_repository import ProductRepository
from src.models.entities import Product

@pytest.mark.asyncio
async def test_create_product(db_session, product_factory):
    """✅ Repository creates product in database"""
    repo = ProductRepository(db_session)

    product = await repo.create(
        name="Laptop",
        price=Decimal("999.99"),
        stock=10
    )

    assert product.id is not None
    assert product.name == "Laptop"
    assert product.price == Decimal("999.99")

@pytest.mark.asyncio
async def test_get_product_by_id(db_session, product_factory):
    """✅ Repository finds product by ID"""
    repo = ProductRepository(db_session)

    # Create test product
    created = await product_factory(name="Test Product")

    # Retrieve by ID
    found = await repo.get(created.id)

    assert found is not None
    assert found.id == created.id
    assert found.name == "Test Product"

@pytest.mark.asyncio
async def test_list_active_products(db_session, product_factory):
    """✅ Repository lists only active products"""
    repo = ProductRepository(db_session)

    # Create 2 active, 1 inactive
    await product_factory(name="Active 1", is_active=True)
    await product_factory(name="Active 2", is_active=True)
    await product_factory(name="Inactive", is_active=False)

    # List active only
    products = await repo.list_active(page=1, page_size=10)

    assert len(products) == 2
    assert all(p.is_active for p in products)

@pytest.mark.asyncio
async def test_update_stock(db_session, product_factory):
    """✅ Repository updates product stock"""
    repo = ProductRepository(db_session)

    product = await product_factory(stock=10)

    # Update stock
    updated = await repo.update_stock(product.id, new_stock=5)

    assert updated.stock == 5
```

### Test Services (Business Logic)

**Archivo:** `tests/unit/test_services.py`

```python
import pytest
from decimal import Decimal
from src.services.product_service import ProductService
from src.models.schemas import ProductCreate

@pytest.mark.asyncio
async def test_create_product_valid(db_session):
    """✅ Service creates product with valid data"""
    service = ProductService(db_session)

    product_data = ProductCreate(
        name="Laptop",
        price=Decimal("999.99"),
        stock=10
    )

    product = await service.create(product_data)

    assert product.id is not None
    assert product.name == "Laptop"
    assert product.price == Decimal("999.99")

@pytest.mark.asyncio
async def test_create_product_invalid_price(db_session):
    """❌ Service rejects price <= 0"""
    service = ProductService(db_session)

    product_data = ProductCreate(
        name="Laptop",
        price=Decimal("0"),  # Invalid
        stock=10
    )

    with pytest.raises(ValueError, match="Price must be greater than 0"):
        await service.create(product_data)

@pytest.mark.asyncio
async def test_checkout_cart_insufficient_stock(
    db_session,
    cart_factory,
    product_factory
):
    """❌ Checkout fails with insufficient stock"""
    service = OrderService(db_session)

    # Product with only 5 in stock
    product = await product_factory(stock=5)

    # Cart wants 10 units
    cart = await cart_factory(
        items=[{"product_id": product.id, "quantity": 10}]
    )

    with pytest.raises(InsufficientStockError):
        await service.checkout_cart(cart.id)
```

---

## Integration Tests

### Full API Endpoint Tests

**Archivo:** `tests/integration/test_api.py`

```python
import pytest
from decimal import Decimal
from httpx import AsyncClient
from src.main import app

@pytest.mark.asyncio
async def test_create_product(async_client: AsyncClient):
    """✅ POST /api/v1/products creates product"""
    response = await async_client.post(
        "/api/v1/products",
        json={
            "name": "Laptop",
            "description": "Gaming laptop",
            "price": "999.99",
            "stock": 10,
            "is_active": True
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Laptop"
    assert data["price"] == "999.99"
    assert "id" in data

@pytest.mark.asyncio
async def test_list_products_with_pagination(async_client, product_factory):
    """✅ GET /api/v1/products supports pagination"""
    # Create 15 products
    for i in range(15):
        await product_factory(name=f"Product {i}")

    # Get page 1
    response = await async_client.get(
        "/api/v1/products?page=1&page_size=10"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 10
    assert data["total"] == 15
    assert data["page"] == 1

@pytest.mark.asyncio
async def test_full_checkout_flow(async_client, product_factory):
    """✅ Full E2E: Create customer → cart → add items → checkout"""

    # 1. Create customer
    customer_resp = await async_client.post(
        "/api/v1/customers",
        json={"email": "test@example.com", "full_name": "Test User"}
    )
    assert customer_resp.status_code == 201
    customer = customer_resp.json()

    # 2. Create product
    product = await product_factory(
        name="Laptop",
        price=Decimal("999.99"),
        stock=10
    )

    # 3. Create cart
    cart_resp = await async_client.post(
        f"/api/v1/cart/create?customer_id={customer['id']}"
    )
    assert cart_resp.status_code == 201
    cart = cart_resp.json()

    # 4. Add item to cart
    add_resp = await async_client.post(
        "/api/v1/cart/add",
        json={
            "cart_id": cart["id"],
            "product_id": str(product.id),
            "quantity": 2
        }
    )
    assert add_resp.status_code == 200

    # 5. Checkout
    checkout_resp = await async_client.post(
        f"/api/v1/cart/checkout?cart_id={cart['id']}"
    )
    assert checkout_resp.status_code == 201
    order = checkout_resp.json()

    # Verify order
    assert order["status"] == "PENDING_PAYMENT"
    assert order["payment_status"] == "PENDING"
    assert len(order["items"]) == 1
    assert float(order["total_amount"]) == 1999.98  # 2 * 999.99

@pytest.mark.asyncio
async def test_checkout_insufficient_stock(async_client, product_factory):
    """❌ Checkout fails when stock insufficient"""
    # Product with only 5 units
    product = await product_factory(stock=5)

    # ... create customer and cart ...

    # Try to add 10 units
    add_resp = await async_client.post(
        "/api/v1/cart/add",
        json={
            "cart_id": cart["id"],
            "product_id": str(product.id),
            "quantity": 10
        }
    )

    assert add_resp.status_code == 400
    assert "insufficient stock" in add_resp.json()["detail"].lower()
```

### Observability Tests

**Archivo:** `tests/test_observability.py`

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    """✅ /health/health returns 200"""
    response = await async_client.get("/health/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data

@pytest.mark.asyncio
async def test_readiness_endpoint(async_client: AsyncClient):
    """✅ /health/ready checks database"""
    response = await async_client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"

@pytest.mark.asyncio
async def test_metrics_endpoint(async_client: AsyncClient):
    """✅ /metrics/metrics returns Prometheus format"""
    # Make some requests first
    await async_client.get("/health/health")

    response = await async_client.get("/metrics/metrics")

    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds" in response.text

@pytest.mark.asyncio
async def test_request_id_header(async_client: AsyncClient):
    """✅ Response includes X-Request-ID header"""
    response = await async_client.get("/health/health")

    assert "X-Request-ID" in response.headers
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 36  # UUID format
```

---

## Test Fixtures

### Database Fixtures

**Archivo:** `tests/conftest.py`

```python
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient
from src.main import app
from src.models.entities import Base

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://devmatrix:devmatrix@localhost:5432/test_db"

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

@pytest.fixture
async def db_session(test_engine):
    """Create clean database session for each test"""
    AsyncSessionLocal = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()  # Rollback after test

@pytest.fixture
async def async_client(db_session):
    """HTTP client for API testing"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

### Factory Fixtures

**Archivo:** `tests/factories.py`

```python
from decimal import Decimal
from uuid import uuid4
from src.models.entities import Product, Customer

class ProductFactory:
    def __init__(self, db_session):
        self.db_session = db_session

    async def __call__(
        self,
        name="Test Product",
        price=Decimal("99.99"),
        stock=10,
        is_active=True
    ):
        product = Product(
            id=uuid4(),
            name=name,
            price=price,
            stock=stock,
            is_active=is_active
        )
        self.db_session.add(product)
        await self.db_session.commit()
        await self.db_session.refresh(product)
        return product

class CustomerFactory:
    def __init__(self, db_session):
        self.db_session = db_session

    async def __call__(
        self,
        email=None,
        full_name="Test Customer"
    ):
        if email is None:
            email = f"test_{uuid4().hex[:8]}@example.com"

        customer = Customer(
            id=uuid4(),
            email=email,
            full_name=full_name
        )
        self.db_session.add(customer)
        await self.db_session.commit()
        await self.db_session.refresh(customer)
        return customer

@pytest.fixture
def product_factory(db_session):
    return ProductFactory(db_session)

@pytest.fixture
def customer_factory(db_session):
    return CustomerFactory(db_session)
```

---

## Coverage

### Running Coverage

```bash
# Run tests with coverage
pytest --cov=src --cov-report=html --cov-report=term

# Output:
# ---------- coverage: platform linux, python 3.11 -----------
# Name                              Stmts   Miss  Cover
# -----------------------------------------------------
# src/models/entities.py              45      2    96%
# src/models/schemas.py               38      1    97%
# src/repositories/product_repo.py    52      4    92%
# src/services/product_service.py     65      8    88%
# src/api/routes/product.py           42      5    88%
# -----------------------------------------------------
# TOTAL                              242     20    92%
```

### Coverage Report

```mermaid
graph LR
    subgraph "📊 Coverage by Layer"
        MOD[Models<br/>96%<br/>45/47 lines]
        REPO[Repositories<br/>92%<br/>48/52 lines]
        SVC[Services<br/>88%<br/>57/65 lines]
        ROUTE[Routes<br/>88%<br/>37/42 lines]
    end

    subgraph "🎯 Coverage Target"
        TARGET[Overall<br/>92%<br/>Target: 80%+<br/>✅ PASSED]
    end

    MOD --> TARGET
    REPO --> TARGET
    SVC --> TARGET
    ROUTE --> TARGET

    style TARGET fill:#27AE60,stroke:#1E8449,color:#FFFFFF,stroke-width:3px
    style MOD fill:#3498DB,stroke:#2874A6,color:#FFFFFF,stroke-width:2px
    style REPO fill:#9B59B6,stroke:#7D3C92,color:#FFFFFF,stroke-width:2px
    style SVC fill:#E67E22,stroke:#CA6F1E,color:#FFFFFF,stroke-width:2px
    style ROUTE fill:#E74C3C,stroke:#C0392B,color:#FFFFFF,stroke-width:2px
```

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: devmatrix
          POSTGRES_PASSWORD: devmatrix
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run tests
        env:
          DATABASE_URL: postgresql+asyncpg://devmatrix:devmatrix@localhost:5432/test_db
        run: |
          pytest --cov=src --cov-report=xml --cov-report=term

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: true
```

### Test Execution Flow

```mermaid
graph TB
    START[Git Push] --> GH[GitHub Actions]

    GH --> SETUP[Setup Environment<br/>Python 3.11]
    SETUP --> PG[Start PostgreSQL<br/>Test Database]

    PG --> INSTALL[Install Dependencies<br/>pip install -r requirements.txt]
    INSTALL --> MIGRATE[Run Migrations<br/>alembic upgrade head]

    MIGRATE --> TEST[Run Tests<br/>pytest --cov]

    TEST --> |Failed| FAIL[❌ Build Failed<br/>Notify developers]
    TEST --> |Passed| COV{Coverage >= 80%?}

    COV --> |No| FAIL
    COV --> |Yes| SUCCESS[✅ Build Passed<br/>Upload coverage]

    SUCCESS --> CODECOV[Upload to Codecov<br/>Badge updated]

    style START fill:#4A90E2,stroke:#2E5C8A,color:#FFFFFF,stroke-width:2px
    style SUCCESS fill:#27AE60,stroke:#1E8449,color:#FFFFFF,stroke-width:3px
    style FAIL fill:#E74C3C,stroke:#C0392B,color:#FFFFFF,stroke-width:3px
    style TEST fill:#9B59B6,stroke:#7D3C92,color:#FFFFFF,stroke-width:2px
```

---

## Resumen de Testing

| Aspecto | Implementado | Details |
|---------|--------------|---------|
| **Framework** | ✅ pytest | Con async support |
| **Unit Tests** | ✅ 15 tests | Models, repos, services |
| **Integration Tests** | ✅ 10 tests | Full API flows |
| **Test Database** | ✅ PostgreSQL | Isolated test DB |
| **Fixtures** | ✅ conftest.py | DB session, HTTP client |
| **Factories** | ✅ factories.py | Product, Customer, Cart |
| **Coverage** | ✅ 92% | Target: 80%+ |
| **CI/CD** | ✅ GitHub Actions | Auto-test on push |

---

**Continuar leyendo:**
- [07_Ecommerce_Case_Study.md](07_Ecommerce_Case_Study.md) - Caso de estudio completo

---

**Versión**: 1.0.0
**Última actualización**: 2025-11-21
