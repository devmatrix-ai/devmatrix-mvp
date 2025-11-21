# Arquitectura de Aplicaciones Generadas

## 📋 Índice

1. [Overview](#overview)
2. [Estructura de Directorios](#estructura-de-directorios)
3. [Arquitectura en Capas](#arquitectura-en-capas)
4. [Componentes Core](#componentes-core)
5. [Data Flow](#data-flow)
6. [Deployment](#deployment)

---

## Overview

Las aplicaciones generadas por DevMatrix siguen una **arquitectura modular production-ready** basada en:

- ✅ **Clean Architecture** (routes → services → repositories → entities)
- ✅ **Dependency Injection** con FastAPI
- ✅ **Async/Await** end-to-end
- ✅ **Type Safety** con Pydantic v2
- ✅ **Database Migrations** con Alembic
- ✅ **Full Observability** (logs, metrics, health checks)
- ✅ **Docker Support** con docker-compose completo

---

## Estructura de Directorios

```
ecommerce_api_simple_1763747745/
│
├── 📁 src/                              # Application source code
│   ├── 📁 api/                          # API Layer
│   │   ├── 📁 routes/                   # FastAPI endpoints
│   │   │   ├── health.py                # Health checks (/health, /ready)
│   │   │   ├── metrics.py               # Prometheus metrics (/metrics)
│   │   │   ├── product.py               # Product management (CRUD)
│   │   │   ├── customer.py              # Customer registration
│   │   │   ├── cart.py                  # Shopping cart operations
│   │   │   └── order.py                 # Order processing & payment
│   │   ├── dependencies.py              # Dependency injection
│   │   └── middleware.py                # Custom middleware
│   │
│   ├── 📁 core/                         # Core Infrastructure
│   │   ├── config.py                    # Pydantic settings (.env)
│   │   ├── database.py                  # SQLAlchemy async setup
│   │   ├── logging.py                   # structlog configuration
│   │   ├── middleware.py                # Request ID, Metrics, Security
│   │   ├── security.py                  # Sanitization, rate limiting
│   │   └── exception_handlers.py        # Global error handling
│   │
│   ├── 📁 models/                       # Data Models
│   │   ├── entities.py                  # SQLAlchemy ORM models
│   │   └── schemas.py                   # Pydantic request/response schemas
│   │
│   ├── 📁 repositories/                 # Data Access Layer
│   │   ├── product_repository.py        # Product database operations
│   │   ├── customer_repository.py       # Customer database operations
│   │   ├── cart_repository.py           # Cart database operations
│   │   └── order_repository.py          # Order database operations
│   │
│   ├── 📁 services/                     # Business Logic Layer
│   │   ├── product_service.py           # Product business rules
│   │   ├── customer_service.py          # Customer business rules
│   │   ├── cart_service.py              # Cart business rules
│   │   └── order_service.py             # Order & payment business rules
│   │
│   └── main.py                          # FastAPI application entry point
│
├── 📁 tests/                            # Test Suite
│   ├── conftest.py                      # pytest configuration & fixtures
│   ├── factories.py                     # Test data factories
│   ├── test_observability.py            # Metrics & health checks tests
│   ├── 📁 unit/                         # Unit Tests
│   │   ├── test_models.py               # Pydantic schema validation
│   │   ├── test_repositories.py         # Repository layer tests
│   │   └── test_services.py             # Service layer business logic
│   └── 📁 integration/                  # Integration Tests
│       └── test_api.py                  # Full API endpoint tests
│
├── 📁 alembic/                          # Database Migrations
│   ├── env.py                           # Alembic environment config
│   ├── alembic.ini                      # Alembic settings
│   └── versions/                        # Migration files
│       └── 001_initial.py               # Initial schema
│
├── 📁 docker/                           # Docker Configuration
│   ├── Dockerfile                       # Multi-stage app image
│   ├── docker-compose.yml               # Full stack (app + postgres + monitoring)
│   ├── docker-compose.test.yml          # Test environment
│   ├── prometheus.yml                   # Prometheus config
│   └── grafana/                         # Grafana dashboards
│       ├── dashboards/
│       └── datasources/
│
├── .env.example                         # Environment variables template
├── requirements.txt                     # Python dependencies
├── pytest.ini                           # pytest configuration
├── Makefile                             # Common commands (test, run, migrate)
└── README.md                            # Project documentation
```

---

## Arquitectura en Capas

```mermaid
graph TB
    subgraph "🔷 Client Layer"
        CLIENT[HTTP Client<br/>Browser, Mobile, API Consumer]
    end

    subgraph "🔶 API Layer - FastAPI"
        direction TB

        MW1[RequestIDMiddleware<br/>Genera UUID por request]
        MW2[MetricsMiddleware<br/>Prometheus counters/histograms]
        MW3[SecurityHeadersMiddleware<br/>X-Frame-Options, CSP]

        subgraph "Routes (Endpoints)"
            HEALTH[/health/health<br/>/health/ready]
            METRICS[/metrics/metrics<br/>Prometheus format]
            PRODUCT[/api/v1/products<br/>CRUD operations]
            CUSTOMER[/api/v1/customers<br/>Registration]
            CART[/api/v1/cart<br/>Cart management]
            ORDER[/api/v1/orders<br/>Checkout & payment]
        end
    end

    subgraph "🟡 Business Logic Layer"
        direction LR

        subgraph "Services"
            PS[ProductService<br/>Validation, business rules]
            CS[CustomerService<br/>Email uniqueness]
            CAS[CartService<br/>Cart state management]
            OS[OrderService<br/>Checkout, stock deduction]
        end
    end

    subgraph "🟢 Data Access Layer"
        direction LR

        subgraph "Repositories"
            PR[ProductRepository<br/>CRUD + stock updates]
            CR[CustomerRepository<br/>Find by email]
            CAR[CartRepository<br/>Active cart queries]
            OR[OrderRepository<br/>Order persistence]
        end
    end

    subgraph "🔵 Data Layer"
        direction TB

        subgraph "Models"
            ENT[SQLAlchemy Entities<br/>Product, Customer, Cart, Order]
            SCH[Pydantic Schemas<br/>Request/Response validation]
        end

        PG[(PostgreSQL<br/>Async Database)]
    end

    subgraph "📊 Infrastructure"
        LOG[structlog<br/>Structured logging]
        PROM[Prometheus<br/>Metrics collection]
    end

    CLIENT --> MW1
    MW1 --> MW2
    MW2 --> MW3

    MW3 --> HEALTH
    MW3 --> METRICS
    MW3 --> PRODUCT
    MW3 --> CUSTOMER
    MW3 --> CART
    MW3 --> ORDER

    PRODUCT --> PS
    CUSTOMER --> CS
    CART --> CAS
    ORDER --> OS

    PS --> PR
    CS --> CR
    CAS --> CAR
    OS --> OR

    PR --> ENT
    CR --> ENT
    CAR --> ENT
    OR --> ENT

    ENT --> PG

    PS --> SCH
    CS --> SCH
    CAS --> SCH
    OS --> SCH

    MW1 --> LOG
    MW2 --> PROM

    style CLIENT fill:#4A90E2,stroke:#2E5C8A,color:#FFFFFF,stroke-width:3px
    style PG fill:#336791,stroke:#2C5B7A,color:#FFFFFF,stroke-width:3px
    style MW1 fill:#E74C3C,stroke:#C0392B,color:#FFFFFF,stroke-width:2px
    style MW2 fill:#E74C3C,stroke:#C0392B,color:#FFFFFF,stroke-width:2px
    style MW3 fill:#E74C3C,stroke:#C0392B,color:#FFFFFF,stroke-width:2px
    style PS fill:#9B59B6,stroke:#7D3C92,color:#FFFFFF,stroke-width:2px
    style PR fill:#3498DB,stroke:#2874A6,color:#FFFFFF,stroke-width:2px
    style ENT fill:#27AE60,stroke:#1E8449,color:#FFFFFF,stroke-width:2px
```

---

## Componentes Core

### 1. Configuration Management

**Archivo:** `src/core/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Application
    app_name: str = "API"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://user:pass@localhost/db"
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # Logging
    log_level: str = "INFO"

    # Security
    cors_origins: list[str] = ["http://localhost:3000"]
    rate_limit: str = "100/minute"

    class Config:
        env_file = ".env"
```

**Features:**
- ✅ Type-safe con Pydantic
- ✅ Auto-load de `.env`
- ✅ Validación en startup
- ✅ Cached con `@lru_cache`

### 2. Database Setup

**Archivo:** `src/core/database.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    echo=settings.db_echo
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

**Features:**
- ✅ Async SQLAlchemy
- ✅ Connection pooling
- ✅ Dependency injection ready

### 3. Logging Setup

**Archivo:** `src/core/logging.py`

```python
import structlog

def setup_logging(log_level: str = "INFO"):
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True
    )
```

**Features:**
- ✅ Structured JSON logs
- ✅ Request ID tracking
- ✅ Context propagation
- ✅ ISO timestamps

### 4. Middleware Stack

**Archivo:** `src/core/middleware.py`

```python
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid4())
        request.state.request_id = request_id

        # Add to structlog context
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time
        REQUEST_DURATION.labels(
            method=request.method,
            path=request.url.path,
            status=response.status_code
        ).observe(duration)

        REQUEST_COUNT.labels(
            method=request.method,
            path=request.url.path,
            status=response.status_code
        ).inc()

        return response
```

**Middlewares:**
1. **RequestIDMiddleware**: UUID por request
2. **MetricsMiddleware**: Prometheus metrics
3. **SecurityHeadersMiddleware**: Security headers
4. **CORSMiddleware**: CORS configuration

---

## Data Flow

### Request Flow Completo

```mermaid
sequenceDiagram
    participant C as Client
    participant MW as Middleware Stack
    participant R as Route Handler
    participant S as Service Layer
    participant REPO as Repository Layer
    participant DB as PostgreSQL
    participant LOG as structlog
    participant PROM as Prometheus

    C->>MW: POST /api/v1/products
    MW->>MW: Generate Request ID
    MW->>LOG: Log request started
    MW->>R: Forward request

    R->>R: Validate ProductCreate schema
    R->>S: product_service.create(data)

    S->>S: Business validation (price > 0)
    S->>REPO: repository.create(product)

    REPO->>DB: INSERT INTO products
    DB-->>REPO: Product entity
    REPO-->>S: Product entity

    S->>S: Map to ProductResponse
    S-->>R: ProductResponse

    R-->>MW: Response 201 Created
    MW->>PROM: Record metrics (duration, status)
    MW->>LOG: Log request completed
    MW-->>C: JSON response + X-Request-ID

    style C fill:#4A90E2,stroke:#2E5C8A,color:#FFFFFF,stroke-width:2px
    style DB fill:#336791,stroke:#2C5B7A,color:#FFFFFF,stroke-width:2px
    style MW fill:#E74C3C,stroke:#C0392B,color:#FFFFFF,stroke-width:2px
    style S fill:#9B59B6,stroke:#7D3C92,color:#FFFFFF,stroke-width:2px
```

### Checkout Flow (Complejo)

```mermaid
graph TB
    START[POST /cart/checkout<br/>customer_id] --> VALIDATE[Validate Cart Exists<br/>CartService.get_active_cart]

    VALIDATE --> |Not Found| ERR1[Return 404<br/>No active cart]
    VALIDATE --> |Found| CHECK_ITEMS[Check Cart Has Items<br/>cart.items.length > 0]

    CHECK_ITEMS --> |Empty| ERR2[Return 400<br/>Cart is empty]
    CHECK_ITEMS --> |Has Items| VALIDATE_STOCK[Validate Stock<br/>For each cart item]

    VALIDATE_STOCK --> |Insufficient| ERR3[Return 400<br/>Insufficient stock]
    VALIDATE_STOCK --> |OK| START_TX[BEGIN Transaction]

    START_TX --> CREATE_ORDER[Create Order<br/>status=PENDING_PAYMENT]
    CREATE_ORDER --> COPY_ITEMS[Copy Cart Items<br/>to Order Items]
    COPY_ITEMS --> CALC_TOTAL[Calculate Total Amount<br/>sum(unit_price * quantity)]
    CALC_TOTAL --> DEDUCT_STOCK[Deduct Stock<br/>product.stock -= quantity]
    DEDUCT_STOCK --> UPDATE_CART[Update Cart Status<br/>status=CHECKED_OUT]
    UPDATE_CART --> COMMIT_TX[COMMIT Transaction]

    COMMIT_TX --> SUCCESS[Return 201<br/>OrderResponse]

    ERR1 --> ROLLBACK[ROLLBACK]
    ERR2 --> ROLLBACK
    ERR3 --> ROLLBACK
    DEDUCT_STOCK --> |Error| ROLLBACK
    ROLLBACK --> FAIL[Return Error Response]

    style START fill:#4A90E2,stroke:#2E5C8A,color:#FFFFFF,stroke-width:3px
    style SUCCESS fill:#27AE60,stroke:#1E8449,color:#FFFFFF,stroke-width:3px
    style FAIL fill:#E74C3C,stroke:#C0392B,color:#FFFFFF,stroke-width:3px
    style START_TX fill:#F39C12,stroke:#D68910,color:#FFFFFF,stroke-width:2px
    style COMMIT_TX fill:#27AE60,stroke:#1E8449,color:#FFFFFF,stroke-width:2px
    style ROLLBACK fill:#E74C3C,stroke:#C0392B,color:#FFFFFF,stroke-width:2px
```

---

## Deployment

### Docker Compose Stack

```mermaid
graph TB
    subgraph "🐳 Docker Compose Stack"
        direction TB

        subgraph "Application Services"
            APP[FastAPI App<br/>Port 8002<br/>uvicorn]
        end

        subgraph "Database Services"
            PG[PostgreSQL 16<br/>Port 5433<br/>async support]
        end

        subgraph "Monitoring Services"
            PROM[Prometheus<br/>Port 9091<br/>Metrics scraping]
            GRAF[Grafana<br/>Port 3002<br/>Dashboards]
        end

        APP --> |async queries| PG
        PROM --> |scrape /metrics| APP
        GRAF --> |query metrics| PROM
    end

    subgraph "🌐 External Access"
        USER[User Browser] --> |http://localhost:8002| APP
        USER --> |http://localhost:3002| GRAF
        ADMIN[Admin] --> |http://localhost:9091| PROM
    end

    subgraph "💾 Persistent Storage"
        PG_VOL[(postgres-data)]
        PROM_VOL[(prometheus-data)]
        GRAF_VOL[(grafana-data)]

        PG -.->|volume mount| PG_VOL
        PROM -.->|volume mount| PROM_VOL
        GRAF -.->|volume mount| GRAF_VOL
    end

    style APP fill:#3498DB,stroke:#2874A6,color:#FFFFFF,stroke-width:3px
    style PG fill:#336791,stroke:#2C5B7A,color:#FFFFFF,stroke-width:3px
    style PROM fill:#E74C3C,stroke:#C0392B,color:#FFFFFF,stroke-width:3px
    style GRAF fill:#F39C12,stroke:#D68910,color:#FFFFFF,stroke-width:3px
    style USER fill:#27AE60,stroke:#1E8449,color:#FFFFFF,stroke-width:2px
```

### Health Checks

```mermaid
graph LR
    subgraph "Health Endpoints"
        HEALTH[/health/health<br/>Liveness probe]
        READY[/health/ready<br/>Readiness probe]
    end

    subgraph "Checks"
        APP_CHECK[App Running?<br/>FastAPI initialized]
        DB_CHECK[Database Connected?<br/>SELECT 1 query]
    end

    HEALTH --> APP_CHECK
    APP_CHECK --> |✅ 200 OK| LIVE[Healthy]
    APP_CHECK --> |❌ 503| NOT_LIVE[Unhealthy]

    READY --> APP_CHECK
    READY --> DB_CHECK
    APP_CHECK --> |✅| READY_CHECK{All OK?}
    DB_CHECK --> |✅| READY_CHECK
    READY_CHECK --> |Yes| READY_OK[200 Ready]
    READY_CHECK --> |No| NOT_READY[503 Not Ready]

    style HEALTH fill:#27AE60,stroke:#1E8449,color:#FFFFFF,stroke-width:2px
    style READY fill:#3498DB,stroke:#2874A6,color:#FFFFFF,stroke-width:2px
    style LIVE fill:#27AE60,stroke:#1E8449,color:#FFFFFF,stroke-width:2px
    style READY_OK fill:#27AE60,stroke:#1E8449,color:#FFFFFF,stroke-width:2px
    style NOT_LIVE fill:#E74C3C,stroke:#C0392B,color:#FFFFFF,stroke-width:2px
    style NOT_READY fill:#E74C3C,stroke:#C0392B,color:#FFFFFF,stroke-width:2px
```

### Deployment Commands

```bash
# Development
docker-compose -f docker/docker-compose.yml up -d

# Testing
docker-compose -f docker/docker-compose.test.yml up -d
pytest

# Production (future)
docker build -f docker/Dockerfile -t ecommerce-api:1.0.0 .
docker push registry/ecommerce-api:1.0.0
```

---

## Próximos Pasos

**Continuar leyendo:**
- [05_Observability_Stack.md](05_Observability_Stack.md) - Stack completo de observabilidad
- [06_Testing_Infrastructure.md](06_Testing_Infrastructure.md) - Testing completo
- [07_Ecommerce_Case_Study.md](07_Ecommerce_Case_Study.md) - Caso de estudio detallado

---

**Versión**: 1.0.0
**Última actualización**: 2025-11-21
