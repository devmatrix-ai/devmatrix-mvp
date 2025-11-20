# Specification: DevMatrix Production-Ready Code Generation

**Version**: 1.0
**Date**: 2025-11-20
**Status**: Draft → Ready for Implementation
**Priority**: P0 (Critical for Production Readiness)

---

## Executive Summary

### Goal

Transform DevMatrix from **"MVP Generator"** (25% production readiness) to **"Production App Generator"** (95% production readiness) by enhancing code generation templates and pipeline to output production-ready applications with complete test coverage, observability, database persistence, security hardening, and Docker infrastructure.

### Current State Analysis

**Achievements** (Milestone 4):
- ✅ 100% Semantic Compliance (simple_task_api, ecommerce_api)
- ✅ Functional code generation (CRUD operations working)
- ✅ FastAPI best practices (HTTP status codes, Pydantic validation)
- ✅ Pipeline Precision: 73-79% (varies by spec complexity)

**Critical Gaps** (QA/CTO Evaluation Results):
- ❌ 0% test coverage (no pytest, no fixtures, no tests)
- ❌ 0% observability (no logging, health checks, metrics)
- ❌ In-memory dict storage (no database, no persistence)
- ❌ Monolithic architecture (233 LOC in single main.py)
- ❌ Security score: 3/10 OWASP (no rate limiting, no auth, XSS vulnerable)
- ❌ No Docker infrastructure
- ❌ 3 critical bugs (type coercion, naive datetimes, XSS)

### Solution Overview

Implement 10 enhancement areas across code generation pipeline:

1. **Test Suite Generation** (pytest, 80%+ coverage, fixtures, factories)
2. **Observability Infrastructure** (structlog, health checks, Prometheus metrics)
3. **Database Integration** (SQLAlchemy async, Alembic migrations)
4. **Configuration Management** (pydantic-settings, .env, multi-environment)
5. **Modular Architecture** (models/repos/services/routes separation)
6. **Security Hardening** (sanitization, rate limiting, CORS, security headers)
7. **Bug Fixes** (strict mode, timezone-aware datetimes, validation)
8. **Production Best Practices** (lockfile, pre-commit, API versioning, pagination)
9. **Docker Infrastructure** (multi-stage Dockerfile, docker-compose with full stack)
10. **Testing Infrastructure** (docker-compose.test.yml, CI/CD templates)

### Expected Impact

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Semantic Compliance | 100% | 100% | 0% (maintain) |
| Production Readiness | 25% | 95% | +70% |
| Test Coverage | 0% | 80%+ | +80% |
| Observability | 0% | 100% | +100% |
| Security (OWASP) | 3/10 | 8/10 | +5 areas |
| Docker Support | 0% | 100% | +100% |
| Time to Production | 80-120h | 0h | 100% reduction |

### Timeline & Effort

- **Total Effort**: ~90 hours (~11.5 days @ 8h/day)
- **Phases**: 3 priority waves (P0/P1/P2)
- **Breakeven**: 1 app generated (saves 80-120h of manual work)
- **ROI for 10 apps**: 9-13x return on investment

---

## Problem Statement

### The Gap: MVP vs. Production

DevMatrix successfully generates **semantically correct code** (100% compliance) that:
- ✅ Implements all required entities and endpoints
- ✅ Uses FastAPI best practices (HTTP codes, Pydantic, OpenAPI)
- ✅ Passes functional testing (CRUD operations work)

However, the generated code is **not production-ready**:
- ❌ Zero tests → Can't validate changes safely
- ❌ No observability → Can't debug production issues
- ❌ In-memory storage → Loses all data on restart
- ❌ Monolithic structure → Hard to maintain and test
- ❌ Security vulnerabilities → XSS, no rate limiting, no auth
- ❌ No deployment infrastructure → Can't deploy to production

### Real-World Example: simple_task_api

Generated app ([main.py:233 LOC](tests/e2e/generated_apps/simple_task_api_1763638943/main.py)):

```python
# ❌ ISSUE 1: Global mutable state (not production-safe)
tasks_db: Dict[UUID, Task] = {}  # In-memory, not thread-safe, no persistence

# ❌ ISSUE 2: Naive datetime (timezone bugs)
created_at: datetime = Field(default_factory=datetime.utcnow)  # Should use timezone.utc

# ❌ ISSUE 3: Type coercion enabled (security risk)
class Task(BaseModel):  # Missing ConfigDict(strict=True)
    completed: bool  # Accepts "yes" → false (silently coerces)

# ❌ ISSUE 4: XSS vulnerability
description: str = Field(..., max_length=500)  # No HTML sanitization

# ❌ ISSUE 5: Monolithic structure
# All models, routes, storage in one 233-line file
```

**Production Readiness Assessment**: 25%
- Would need 80-120 hours of manual work to make production-ready
- Missing: tests, logging, database, config, architecture, security, Docker

### Business Impact

**Without This Spec**:
- Every generated app needs 80-120h of manual production-hardening
- Can't deploy generated code safely to production
- DevMatrix limited to prototypes/MVPs only

**With This Spec**:
- Generated apps are immediately production-ready
- Zero manual work needed for deployment
- DevMatrix competitive with production-focused AI code generators
- **ROI**: 9-13x return after 10 apps generated

---

## Technical Requirements

### 1. Test Suite Generation (MUST HAVE)

**Goal**: Generate comprehensive pytest test suite with 80%+ coverage

#### 1.1 pytest Configuration

**Files to Generate**:
- `pytest.ini` - pytest configuration
- `tests/conftest.py` - shared fixtures
- `tests/factories.py` - test data factories
- `.coveragerc` - coverage configuration

**pytest.ini Template**:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --verbose
    --cov=src
    --cov-report=term-missing
    --cov-report=html
    --cov-fail-under=80
asyncio_mode = auto
```

#### 1.2 Test Fixtures (conftest.py)

**Required Fixtures**:
```python
@pytest.fixture
async def db_session():
    """Async database session for testing"""
    async with async_session_maker() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client(db_session):
    """FastAPI TestClient with database"""
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.fixture
def sample_task_data():
    """Sample task data for testing"""
    return {
        "title": "Test Task",
        "description": "Test description",
        "completed": False
    }
```

#### 1.3 Test Data Factories (factories.py)

**Factory Pattern** (using factory_boy or similar):
```python
class TaskFactory:
    """Factory for creating test tasks"""

    @staticmethod
    def create(**kwargs):
        defaults = {
            "id": uuid4(),
            "title": "Test Task",
            "description": "Test description",
            "completed": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        defaults.update(kwargs)
        return Task(**defaults)

    @staticmethod
    def create_batch(n: int, **kwargs):
        return [TaskFactory.create(**kwargs) for _ in range(n)]
```

#### 1.4 Unit Tests

**tests/unit/test_models.py** - Test Pydantic schemas:
```python
def test_task_create_validation():
    """Test TaskCreate validation"""
    # Valid data
    task = TaskCreate(title="Test", description="Desc")
    assert task.title == "Test"

    # Invalid - missing required field
    with pytest.raises(ValidationError):
        TaskCreate(description="Desc")  # Missing title

    # Invalid - type coercion should fail (strict mode)
    with pytest.raises(ValidationError):
        TaskCreate(title="Test", completed="yes")  # Should reject string

def test_task_update_partial():
    """Test partial updates"""
    update = TaskUpdate(title="Updated")
    assert update.title == "Updated"
    assert update.description is None  # Optional fields
```

**tests/unit/test_repositories.py** - Test data access layer:
```python
@pytest.mark.asyncio
async def test_create_task(db_session):
    """Test task creation in repository"""
    repo = TaskRepository(db_session)
    task_data = TaskFactory.create()

    created = await repo.create(task_data)

    assert created.id is not None
    assert created.title == task_data.title
    assert created.created_at is not None

@pytest.mark.asyncio
async def test_get_task_not_found(db_session):
    """Test get non-existent task"""
    repo = TaskRepository(db_session)
    result = await repo.get(uuid4())
    assert result is None
```

**tests/unit/test_services.py** - Test business logic:
```python
@pytest.mark.asyncio
async def test_create_task_service(mocker):
    """Test task service creation"""
    mock_repo = mocker.Mock()
    mock_repo.create.return_value = TaskFactory.create()

    service = TaskService(mock_repo)
    result = await service.create_task(TaskCreate(title="Test"))

    assert result.title == "Test"
    mock_repo.create.assert_called_once()
```

#### 1.5 Integration Tests

**tests/integration/test_api.py** - Test complete API workflows:
```python
@pytest.mark.asyncio
async def test_create_task_endpoint(client):
    """Test POST /api/v1/tasks"""
    response = await client.post(
        "/api/v1/tasks",
        json={"title": "Test Task", "description": "Test"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Task"
    assert "id" in data
    assert "created_at" in data

@pytest.mark.asyncio
async def test_get_tasks_pagination(client):
    """Test GET /api/v1/tasks with pagination"""
    # Create 15 tasks
    for i in range(15):
        await client.post("/api/v1/tasks", json={"title": f"Task {i}"})

    # Get page 1 (10 items)
    response = await client.get("/api/v1/tasks?page=1&size=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 10
    assert data["total"] == 15
    assert data["page"] == 1

@pytest.mark.asyncio
async def test_update_task_not_found(client):
    """Test PUT /api/v1/tasks/{id} with non-existent ID"""
    response = await client.put(
        f"/api/v1/tasks/{uuid4()}",
        json={"title": "Updated"}
    )
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_validation_error_response(client):
    """Test validation error returns proper format"""
    response = await client.post(
        "/api/v1/tasks",
        json={"description": "Missing title"}  # Title required
    )

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any("title" in str(err) for err in data["detail"])
```

#### 1.6 Coverage Requirements

**Minimum Coverage Targets**:
- Overall: 80%+
- Models/schemas: 90%+
- Repositories: 85%+
- Services: 80%+
- API routes: 75%+
- Core utilities: 70%+

**Coverage Report** (generated automatically):
```bash
# Terminal output
tests/unit/test_models.py ........... 95% coverage
tests/unit/test_repositories.py ..... 87% coverage
tests/unit/test_services.py ......... 82% coverage
tests/integration/test_api.py ....... 78% coverage

TOTAL COVERAGE: 83%  ✅ PASS (≥80%)
```

---

### 2. Observability Infrastructure (MUST HAVE)

**Goal**: Full production observability with structured logging, health checks, and metrics

#### 2.1 Structured Logging (structlog)

**File**: `src/core/logging.py`

**Configuration**:
```python
import structlog
from structlog.contextvars import merge_contextvars

def setup_logging(log_level: str = "INFO"):
    """Configure structured logging with context"""

    structlog.configure(
        processors=[
            merge_contextvars,  # Add context vars (request_id, user_id)
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
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        level=log_level,
    )
```

**Usage in Code**:
```python
logger = structlog.get_logger(__name__)

# Add request context
structlog.contextvars.bind_contextvars(
    request_id=str(uuid4()),
    user_id=current_user.id,
    endpoint=request.url.path
)

# Log with context
logger.info("task_created", task_id=task.id, title=task.title)
# Output: {"event": "task_created", "task_id": "...", "title": "...",
#          "request_id": "...", "timestamp": "2025-11-20T10:30:00Z"}
```

#### 2.2 Request ID Tracking

**Middleware**: `src/core/middleware.py`

```python
from starlette.middleware.base import BaseHTTPMiddleware
import structlog
from uuid import uuid4

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to all requests"""

    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))

        # Bind to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path
        )

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response
```

#### 2.3 Health Check Endpoints

**File**: `src/api/routes/health.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db
import structlog

router = APIRouter(prefix="/health", tags=["health"])
logger = structlog.get_logger(__name__)

@router.get("/health")
async def health_check():
    """Basic health check - always returns OK"""
    return {"status": "ok", "service": "task-api"}

@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness check - verifies dependencies"""
    try:
        # Check database connection
        await db.execute("SELECT 1")

        return {
            "status": "ready",
            "checks": {
                "database": "ok"
            }
        }
    except Exception as e:
        logger.error("readiness_check_failed", error=str(e))
        return {
            "status": "not_ready",
            "checks": {
                "database": "failed"
            }
        }, 503
```

#### 2.4 Metrics Endpoint (Prometheus)

**File**: `src/api/routes/metrics.py`

```python
from fastapi import APIRouter
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

router = APIRouter(prefix="/metrics", tags=["metrics"])

# Metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"]
)

tasks_created_total = Counter(
    "tasks_created_total",
    "Total tasks created"
)

tasks_deleted_total = Counter(
    "tasks_deleted_total",
    "Total tasks deleted"
)

@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

**Metrics Middleware**:
```python
from starlette.middleware.base import BaseHTTPMiddleware
import time

class MetricsMiddleware(BaseHTTPMiddleware):
    """Track request metrics"""

    async def dispatch(self, request, call_next):
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time

        # Record metrics
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()

        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)

        return response
```

#### 2.5 Error Tracking

**Exception Handler**:
```python
from fastapi import Request, status
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger(__name__)

async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with logging"""

    logger.error(
        "unhandled_exception",
        exception_type=type(exc).__name__,
        exception_message=str(exc),
        path=request.url.path,
        method=request.method,
        exc_info=True
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "request_id": request.headers.get("X-Request-ID")
        }
    )
```

---

### 3. Database Integration (MUST HAVE)

**Goal**: Replace in-memory dict with SQLAlchemy async + Alembic migrations

#### 3.1 Database Configuration

**File**: `src/core/config.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # Application
    app_name: str = "Task API"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://user:pass@localhost/tasks"
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # Logging
    log_level: str = "INFO"

    # Security
    cors_origins: list[str] = ["http://localhost:3000"]
    rate_limit: str = "100/minute"

@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
```

**File**: `src/core/database.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from src.core.config import get_settings

settings = get_settings()

# Async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True  # Verify connections
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base for models
Base = declarative_base()

async def get_db() -> AsyncSession:
    """FastAPI dependency for database sessions"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

#### 3.2 SQLAlchemy Models

**File**: `src/models/entities.py`

```python
from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid
from src.core.database import Base

class TaskEntity(Base):
    """SQLAlchemy model for tasks table"""

    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    completed = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self):
        return f"<Task {self.id}: {self.title}>"
```

#### 3.3 Alembic Migrations

**Setup**:
```bash
# Initialize Alembic
alembic init alembic

# Configure alembic.ini
# sqlalchemy.url = postgresql+asyncpg://user:pass@localhost/tasks

# Configure env.py to use async
```

**File**: `alembic/env.py` (configure for async):
```python
from sqlalchemy.ext.asyncio import create_async_engine
from src.core.config import get_settings
from src.core.database import Base
from src.models.entities import *  # Import all models

config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = Base.metadata

# ... async migration logic
```

**Initial Migration**:
```bash
# Generate initial migration
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```

**Migration File** (auto-generated):
```python
def upgrade():
    op.create_table(
        'tasks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('completed', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )

    # Indexes
    op.create_index('ix_tasks_title', 'tasks', ['title'])
    op.create_index('ix_tasks_completed', 'tasks', ['completed'])

def downgrade():
    op.drop_table('tasks')
```

#### 3.4 Repository Pattern

**File**: `src/repositories/task_repository.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from uuid import UUID
from typing import Optional, List
from src.models.entities import TaskEntity
from src.models.schemas import TaskCreate, TaskUpdate
import structlog

logger = structlog.get_logger(__name__)

class TaskRepository:
    """Data access layer for tasks"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, task_data: TaskCreate) -> TaskEntity:
        """Create new task"""
        task = TaskEntity(**task_data.model_dump())
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)

        logger.info("task_created", task_id=str(task.id))
        return task

    async def get(self, task_id: UUID) -> Optional[TaskEntity]:
        """Get task by ID"""
        result = await self.db.execute(
            select(TaskEntity).where(TaskEntity.id == task_id)
        )
        return result.scalar_one_or_none()

    async def list(self, skip: int = 0, limit: int = 100) -> List[TaskEntity]:
        """List tasks with pagination"""
        result = await self.db.execute(
            select(TaskEntity).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def update(self, task_id: UUID, task_data: TaskUpdate) -> Optional[TaskEntity]:
        """Update task"""
        # Get existing
        task = await self.get(task_id)
        if not task:
            return None

        # Update only provided fields
        update_data = task_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(task, key, value)

        await self.db.flush()
        await self.db.refresh(task)

        logger.info("task_updated", task_id=str(task_id))
        return task

    async def delete(self, task_id: UUID) -> bool:
        """Delete task"""
        result = await self.db.execute(
            delete(TaskEntity).where(TaskEntity.id == task_id)
        )

        deleted = result.rowcount > 0
        if deleted:
            logger.info("task_deleted", task_id=str(task_id))

        return deleted
```

---

### 4. Configuration Management (MUST HAVE)

**Goal**: Type-safe configuration with .env support and multi-environment settings

#### 4.1 Settings Structure

Already covered in section 3.1 (`src/core/config.py` with pydantic-settings)

#### 4.2 Environment Files

**.env.example**:
```bash
# Application
APP_NAME=Task API
APP_VERSION=1.0.0
DEBUG=false

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/tasks
DB_ECHO=false
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10

# Logging
LOG_LEVEL=INFO

# Security
CORS_ORIGINS=["http://localhost:3000"]
RATE_LIMIT=100/minute

# Redis (optional)
REDIS_URL=redis://localhost:6379/0
```

**.env** (gitignored):
```bash
# Copy from .env.example and customize
DATABASE_URL=postgresql+asyncpg://user:secret@localhost:5432/tasks_dev
DEBUG=true
LOG_LEVEL=DEBUG
```

#### 4.3 Multi-Environment Support

**Development** (`.env`):
```bash
DEBUG=true
LOG_LEVEL=DEBUG
DB_ECHO=true
```

**Staging** (`.env.staging`):
```bash
DEBUG=false
LOG_LEVEL=INFO
DATABASE_URL=postgresql+asyncpg://user:pass@staging-db:5432/tasks
```

**Production** (environment variables):
```bash
export DEBUG=false
export LOG_LEVEL=WARNING
export DATABASE_URL=postgresql+asyncpg://user:pass@prod-db:5432/tasks
export CORS_ORIGINS='["https://app.example.com"]'
```

---

### 5. Modular Architecture (MUST HAVE)

**Goal**: Separate models, repositories, services, and routes for maintainability

#### 5.1 Directory Structure

```
src/
├── __init__.py
├── main.py                    # FastAPI app setup
├── core/                      # Core infrastructure
│   ├── __init__.py
│   ├── config.py              # Settings
│   ├── database.py            # Database setup
│   ├── logging.py             # Logging config
│   ├── security.py            # Security utilities
│   └── middleware.py          # Custom middleware
├── models/                    # Data models
│   ├── __init__.py
│   ├── schemas.py             # Pydantic request/response
│   └── entities.py            # SQLAlchemy ORM
├── repositories/              # Data access layer
│   ├── __init__.py
│   └── task_repository.py     # Task repository
├── services/                  # Business logic
│   ├── __init__.py
│   └── task_service.py        # Task service
└── api/                       # API layer
    ├── __init__.py
    ├── dependencies.py        # FastAPI dependencies
    └── routes/                # Route handlers
        ├── __init__.py
        ├── health.py          # Health checks
        └── tasks.py           # Task endpoints
```

#### 5.2 Pydantic Schemas

**File**: `src/models/schemas.py`

```python
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional

class TaskBase(BaseModel):
    """Base task schema"""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    completed: bool = Field(default=False)

class TaskCreate(TaskBase):
    """Schema for creating tasks"""
    model_config = ConfigDict(strict=True)  # Enable strict validation

class TaskUpdate(BaseModel):
    """Schema for updating tasks (all fields optional)"""
    model_config = ConfigDict(strict=True)

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    completed: Optional[bool] = None

class Task(TaskBase):
    """Schema for task response"""
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)  # Allow ORM models

class TaskList(BaseModel):
    """Paginated task list response"""
    items: list[Task]
    total: int
    page: int
    size: int
    pages: int
```

#### 5.3 Service Layer

**File**: `src/services/task_service.py`

```python
from uuid import UUID
from typing import Optional, List
from src.repositories.task_repository import TaskRepository
from src.models.schemas import TaskCreate, TaskUpdate, Task
from src.models.entities import TaskEntity
import structlog

logger = structlog.get_logger(__name__)

class TaskService:
    """Business logic for tasks"""

    def __init__(self, repository: TaskRepository):
        self.repo = repository

    async def create_task(self, task_data: TaskCreate) -> Task:
        """Create new task with business validation"""
        # Business logic here (e.g., sanitize HTML)
        task_entity = await self.repo.create(task_data)
        return Task.model_validate(task_entity)

    async def get_task(self, task_id: UUID) -> Optional[Task]:
        """Get task by ID"""
        task_entity = await self.repo.get(task_id)
        if not task_entity:
            return None
        return Task.model_validate(task_entity)

    async def list_tasks(self, page: int = 1, size: int = 10) -> dict:
        """List tasks with pagination"""
        skip = (page - 1) * size

        tasks = await self.repo.list(skip=skip, limit=size)
        total = len(tasks)  # TODO: Add count query

        return {
            "items": [Task.model_validate(t) for t in tasks],
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size
        }

    async def update_task(self, task_id: UUID, task_data: TaskUpdate) -> Optional[Task]:
        """Update task"""
        task_entity = await self.repo.update(task_id, task_data)
        if not task_entity:
            return None
        return Task.model_validate(task_entity)

    async def delete_task(self, task_id: UUID) -> bool:
        """Delete task"""
        return await self.repo.delete(task_id)
```

#### 5.4 API Dependencies

**File**: `src/api/dependencies.py`

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db
from src.repositories.task_repository import TaskRepository
from src.services.task_service import TaskService

def get_task_repository(db: AsyncSession = Depends(get_db)) -> TaskRepository:
    """Get task repository dependency"""
    return TaskRepository(db)

def get_task_service(
    repository: TaskRepository = Depends(get_task_repository)
) -> TaskService:
    """Get task service dependency"""
    return TaskService(repository)
```

#### 5.5 API Routes

**File**: `src/api/routes/tasks.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from src.services.task_service import TaskService
from src.api.dependencies import get_task_service
from src.models.schemas import Task, TaskCreate, TaskUpdate, TaskList
import structlog

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])
logger = structlog.get_logger(__name__)

@router.post("/", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    service: TaskService = Depends(get_task_service)
):
    """Create new task"""
    return await service.create_task(task_data)

@router.get("/", response_model=TaskList)
async def list_tasks(
    page: int = 1,
    size: int = 10,
    service: TaskService = Depends(get_task_service)
):
    """List tasks with pagination"""
    return await service.list_tasks(page, size)

@router.get("/{task_id}", response_model=Task)
async def get_task(
    task_id: UUID,
    service: TaskService = Depends(get_task_service)
):
    """Get task by ID"""
    task = await service.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    return task

@router.put("/{task_id}", response_model=Task)
async def update_task(
    task_id: UUID,
    task_data: TaskUpdate,
    service: TaskService = Depends(get_task_service)
):
    """Update task"""
    task = await service.update_task(task_id, task_data)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    return task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    service: TaskService = Depends(get_task_service)
):
    """Delete task"""
    deleted = await service.delete_task(task_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
```

#### 5.6 Main Application Setup

**File**: `src/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import get_settings
from src.core.logging import setup_logging
from src.core.middleware import RequestIDMiddleware, MetricsMiddleware
from src.api.routes import tasks, health, metrics
import structlog

settings = get_settings()
setup_logging(settings.log_level)
logger = structlog.get_logger(__name__)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug
)

# Middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Routes
app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(tasks.router)

@app.on_event("startup")
async def startup():
    logger.info("application_starting", version=settings.app_version)

@app.on_event("shutdown")
async def shutdown():
    logger.info("application_shutdown")
```

---

### 6. Security Hardening (SHOULD HAVE)

**Goal**: Address OWASP Top 10 vulnerabilities and production security requirements

#### 6.1 Pydantic Strict Mode

Enable strict type validation to prevent type coercion:

```python
class TaskCreate(BaseModel):
    model_config = ConfigDict(strict=True)  # ✅ Reject "yes" for bool

    completed: bool  # Only accepts true/false, not "yes"/"1"/etc.
```

#### 6.2 HTML Sanitization

**File**: `src/core/security.py`

```python
import bleach

ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'a']
ALLOWED_ATTRS = {'a': ['href', 'title']}

def sanitize_html(text: str) -> str:
    """Sanitize HTML to prevent XSS"""
    return bleach.clean(
        text,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        strip=True
    )
```

**Usage in Service**:
```python
async def create_task(self, task_data: TaskCreate) -> Task:
    # Sanitize HTML
    if task_data.description:
        task_data.description = sanitize_html(task_data.description)

    task_entity = await self.repo.create(task_data)
    return Task.model_validate(task_entity)
```

#### 6.3 Rate Limiting

**Install**: `slowapi`

**File**: `src/core/middleware.py`

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# In main.py
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply to routes
@router.post("/")
@limiter.limit("10/minute")  # Max 10 requests per minute
async def create_task(...):
    ...
```

#### 6.4 Security Headers

**Middleware**:
```python
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response
```

#### 6.5 CORS Configuration

Already covered in main.py with proper CORS middleware setup.

#### 6.6 SQL Injection Prevention

✅ **Already handled** by SQLAlchemy ORM (parameterized queries).

**DON'T**:
```python
# ❌ VULNERABLE
query = f"SELECT * FROM tasks WHERE id = '{task_id}'"
```

**DO**:
```python
# ✅ SAFE (parameterized)
await db.execute(select(TaskEntity).where(TaskEntity.id == task_id))
```

---

### 7. Bug Fixes (SHOULD HAVE)

#### 7.1 Timezone-Aware Datetimes

**Before** (❌ Bug):
```python
created_at: datetime = Field(default_factory=datetime.utcnow)  # Naive datetime
```

**After** (✅ Fixed):
```python
from datetime import datetime, timezone

created_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc)  # Timezone-aware
)
```

**SQLAlchemy**:
```python
from sqlalchemy import Column, DateTime

created_at = Column(
    DateTime(timezone=True),  # ✅ Enforce timezone
    default=lambda: datetime.now(timezone.utc)
)
```

#### 7.2 Strict Type Validation

Already covered in 6.1 (Pydantic strict mode).

#### 7.3 Error Message Consistency

**Standard Error Format**:
```python
from fastapi import HTTPException, status

# Consistent error responses
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={
        "error": "resource_not_found",
        "message": f"Task {task_id} not found",
        "resource": "task",
        "resource_id": str(task_id)
    }
)
```

---

### 8. Production Best Practices (SHOULD HAVE)

#### 8.1 Dependency Lockfile

**pyproject.toml** (Poetry):
```toml
[tool.poetry]
name = "task-api"
version = "1.0.0"

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.0"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
sqlalchemy = {extras = ["asyncio"], version = "^2.0.0"}
asyncpg = "^0.29.0"
pydantic-settings = "^2.0.0"
structlog = "^23.2.0"
bleach = "^6.1.0"
slowapi = "^0.1.9"
prometheus-client = "^0.19.0"
alembic = "^1.12.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
pytest-cov = "^4.1.0"
httpx = "^0.25.0"
pre-commit = "^3.5.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

**Generate lock**:
```bash
poetry lock
# Creates poetry.lock with exact versions
```

#### 8.2 Pre-commit Hooks

**.pre-commit-config.yaml**:
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: [--max-line-length=100]
```

#### 8.3 .gitignore

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/
*.egg-info/
dist/
build/

# Testing
.pytest_cache/
.coverage
htmlcov/
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo

# Environment
.env
.env.local
.env.*.local

# Database
*.db
*.sqlite3

# Docker
docker-compose.override.yml

# OS
.DS_Store
Thumbs.db
```

#### 8.4 README.md

```markdown
# Task API

Production-ready FastAPI application with complete test coverage, observability, and Docker support.

## Features

- ✅ 80%+ test coverage
- ✅ Structured logging (structlog)
- ✅ Health checks and metrics
- ✅ PostgreSQL with async SQLAlchemy
- ✅ Alembic migrations
- ✅ Docker infrastructure
- ✅ Security hardening
- ✅ Rate limiting

## Quick Start

### Local Development

```bash
# Install dependencies
poetry install

# Setup database
docker-compose up -d postgres
alembic upgrade head

# Run application
poetry run uvicorn src.main:app --reload

# Run tests
poetry run pytest

# Check coverage
poetry run pytest --cov
```

### Docker

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Run migrations
docker-compose exec app alembic upgrade head

# Run tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health: http://localhost:8000/health/health
- Metrics: http://localhost:8000/metrics/metrics

## Environment Variables

See `.env.example` for all configuration options.

## Testing

```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Integration tests only
pytest tests/integration/

# Unit tests only
pytest tests/unit/
```

## Deployment

See `docker/` directory for production deployment configurations.
```

#### 8.5 API Versioning

Already implemented in routes: `prefix="/api/v1/tasks"`

#### 8.6 Pagination

Already implemented in `list_tasks` with `page` and `size` parameters.

---

### 9. Docker Infrastructure (MUST HAVE)

**Goal**: Complete containerization with full stack (app + database + monitoring)

#### 9.1 Multi-Stage Dockerfile

**File**: `docker/Dockerfile`

```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install poetry
RUN pip install poetry==1.7.0

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies (no dev)
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health/health')"

# Run migrations and start app
CMD alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port 8000
```

#### 9.2 Docker Compose (Development)

**File**: `docker/docker-compose.yml`

```yaml
version: '3.8'

services:
  # Application
  app:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://taskuser:taskpass@postgres:5432/tasks
      - REDIS_URL=redis://redis:6379/0
      - LOG_LEVEL=INFO
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - ../src:/app/src  # Hot reload for development
    networks:
      - app-network
    restart: unless-stopped

  # PostgreSQL Database
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: tasks
      POSTGRES_USER: taskuser
      POSTGRES_PASSWORD: taskpass
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U taskuser -d tasks"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - app-network
    restart: unless-stopped

  # Redis Cache
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - app-network
    restart: unless-stopped

  # Prometheus Metrics
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - app-network
    restart: unless-stopped

  # Grafana Dashboards
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
    depends_on:
      - prometheus
    networks:
      - app-network
    restart: unless-stopped

volumes:
  postgres-data:
  redis-data:
  prometheus-data:
  grafana-data:

networks:
  app-network:
    driver: bridge
```

#### 9.3 Prometheus Configuration

**File**: `docker/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'task-api'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics/metrics'
```

#### 9.4 Makefile (Development Commands)

**File**: `Makefile`

```makefile
.PHONY: help install dev test coverage docker-up docker-down migrate lint format

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	poetry install

dev: ## Run development server
	poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

test: ## Run tests
	poetry run pytest

coverage: ## Run tests with coverage
	poetry run pytest --cov=src --cov-report=term-missing --cov-report=html

docker-up: ## Start Docker services
	docker-compose -f docker/docker-compose.yml up -d

docker-down: ## Stop Docker services
	docker-compose -f docker/docker-compose.yml down

docker-logs: ## View Docker logs
	docker-compose -f docker/docker-compose.yml logs -f

migrate: ## Run database migrations
	poetry run alembic upgrade head

migrate-create: ## Create new migration
	poetry run alembic revision --autogenerate -m "$(name)"

lint: ## Run linting
	poetry run flake8 src tests
	poetry run mypy src

format: ## Format code
	poetry run black src tests
	poetry run isort src tests

clean: ## Clean cache and build files
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov dist build *.egg-info
```

---

### 10. Testing Infrastructure (MUST HAVE)

**Goal**: Isolated test environment with automated CI/CD pipeline

#### 10.1 Docker Compose Test Environment

**File**: `docker/docker-compose.test.yml`

```yaml
version: '3.8'

services:
  # Test Database (isolated)
  postgres-test:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: tasks_test
      POSTGRES_USER: testuser
      POSTGRES_PASSWORD: testpass
    tmpfs:
      - /var/lib/postgresql/data  # In-memory for speed
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U testuser -d tasks_test"]
      interval: 5s
      timeout: 3s
      retries: 3

  # Test Runner
  test:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    environment:
      - DATABASE_URL=postgresql+asyncpg://testuser:testpass@postgres-test:5432/tasks_test
      - LOG_LEVEL=WARNING
    depends_on:
      postgres-test:
        condition: service_healthy
    command: |
      sh -c "
        alembic upgrade head &&
        pytest --cov=src --cov-report=term-missing --cov-report=xml --cov-fail-under=80
      "
    volumes:
      - ../src:/app/src
      - ../tests:/app/tests
      - test-reports:/app/htmlcov
    networks:
      - test-network

volumes:
  test-reports:

networks:
  test-network:
    driver: bridge
```

**Usage**:
```bash
# Run tests in isolated environment
docker-compose -f docker/docker-compose.test.yml up --abort-on-container-exit

# View coverage report
open htmlcov/index.html
```

#### 10.2 GitHub Actions CI/CD Pipeline

**File**: `.github/workflows/ci.yml`

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: tasks_test
          POSTGRES_USER: testuser
          POSTGRES_PASSWORD: testpass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Poetry
        run: |
          curl -sSL https://install.python-poetry.org | python3 -
          echo "$HOME/.local/bin" >> $GITHUB_PATH

      - name: Install dependencies
        run: poetry install

      - name: Run linting
        run: |
          poetry run flake8 src tests
          poetry run black --check src tests
          poetry run isort --check src tests

      - name: Run migrations
        env:
          DATABASE_URL: postgresql+asyncpg://testuser:testpass@localhost:5432/tasks_test
        run: poetry run alembic upgrade head

      - name: Run tests with coverage
        env:
          DATABASE_URL: postgresql+asyncpg://testuser:testpass@localhost:5432/tasks_test
        run: |
          poetry run pytest --cov=src --cov-report=xml --cov-report=term-missing --cov-fail-under=80

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: true

  build:
    runs-on: ubuntu-latest
    needs: test

    steps:
      - uses: actions/checkout@v3

      - name: Build Docker image
        run: docker build -f docker/Dockerfile -t task-api:${{ github.sha }} .

      - name: Run Docker container
        run: |
          docker-compose -f docker/docker-compose.yml up -d
          sleep 10

      - name: Health check
        run: |
          curl --fail http://localhost:8000/health/health || exit 1

      - name: Cleanup
        run: docker-compose -f docker/docker-compose.yml down
```

#### 10.3 Coverage Reporting

**File**: `.coveragerc`

```ini
[run]
source = src
omit =
    */tests/*
    */migrations/*
    */__pycache__/*
    */venv/*

[report]
precision = 2
show_missing = True
skip_covered = False

[html]
directory = htmlcov
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (P0) - 40 hours

**Week 1: Foundation**

1. **Database & Configuration** (10h)
   - [ ] Setup SQLAlchemy async engine
   - [ ] Create Base and session management
   - [ ] Implement pydantic-settings configuration
   - [ ] Create .env.example template
   - [ ] Setup Alembic migrations
   - [ ] Create initial migration for each entity

2. **Modular Architecture** (15h)
   - [ ] Create directory structure (core/models/repositories/services/api)
   - [ ] Split schemas (models/schemas.py) and entities (models/entities.py)
   - [ ] Implement repository pattern for each entity
   - [ ] Implement service layer with business logic
   - [ ] Setup FastAPI dependencies for DI
   - [ ] Refactor routes to use services

3. **Observability** (15h)
   - [ ] Configure structlog
   - [ ] Implement RequestIDMiddleware
   - [ ] Create health check endpoints
   - [ ] Implement Prometheus metrics
   - [ ] Add MetricsMiddleware
   - [ ] Setup global exception handler with logging

### Phase 2: Testing & Security (P1) - 30 hours

**Week 2: Quality & Safety**

4. **Test Suite** (20h)
   - [ ] Setup pytest configuration
   - [ ] Create conftest.py with fixtures
   - [ ] Implement test factories
   - [ ] Write unit tests (models, repositories, services)
   - [ ] Write integration tests (API endpoints)
   - [ ] Configure coverage reporting
   - [ ] Achieve 80%+ coverage

5. **Security Hardening** (10h)
   - [ ] Enable Pydantic strict mode
   - [ ] Implement HTML sanitization
   - [ ] Add rate limiting (slowapi)
   - [ ] Configure CORS properly
   - [ ] Add security headers middleware
   - [ ] Fix timezone-aware datetimes
   - [ ] Implement consistent error responses

### Phase 3: Docker & CI/CD (P2) - 20 hours

**Week 3: Infrastructure**

6. **Docker Infrastructure** (15h)
   - [ ] Create multi-stage Dockerfile
   - [ ] Setup docker-compose.yml (app + postgres + redis)
   - [ ] Add Prometheus configuration
   - [ ] Add Grafana dashboards
   - [ ] Create docker-compose.test.yml
   - [ ] Add health checks to containers

7. **CI/CD & Documentation** (5h)
   - [ ] Create GitHub Actions workflow
   - [ ] Setup pre-commit hooks
   - [ ] Add .gitignore
   - [ ] Create comprehensive README.md
   - [ ] Create Makefile with common commands
   - [ ] Document deployment procedures

### Total Timeline

- **Total Effort**: 90 hours (~11.5 days @ 8h/day)
- **Phases**: 3 sequential waves (P0 → P1 → P2)
- **Dependencies**: P1 requires P0 (tests need database), P2 requires P1 (Docker needs tests)

---

## Code Generation Pipeline Changes

### Production Pattern Library (Leverages Existing PatternBank)

**Current** (Milestone 4):
```python
# Single code generation generates monolithic main.py
# No reusable patterns stored
```

**Proposed** - **Leverage Existing PatternBank Infrastructure**:

DevMatrix ALREADY has a powerful pattern system (`PatternBank` + Qdrant + Neo4j). Instead of creating Jinja2 templates (duplicate functionality), we'll create **production-ready golden patterns** stored in PatternBank.

**Existing PatternBank Infrastructure** (`src/cognitive/patterns/pattern_bank.py`):
```python
@dataclass
class StoredPattern:
    pattern_id: str
    signature: SemanticTaskSignature
    code: str
    success_rate: float
    similarity_score: float
    usage_count: int
    created_at: datetime
    domain: str  # "auth", "crud", "api", "validation", etc.

class PatternBank:
    """
    Pattern Bank with Qdrant vector database integration.

    Features:
    - Pattern storage with ≥95% success rate threshold
    - Semantic similarity search (Sentence Transformers embeddings)
    - Hybrid search (vector + metadata filtering)
    - Auto-classification (PatternClassifier with domain/security/performance)
    - Usage tracking and auto-evolution
    """

    def store_pattern(
        self, signature: SemanticTaskSignature, code: str, success_rate: float
    ) -> str:
        """Store pattern with auto-classification"""

    def search_patterns(
        self,
        signature: SemanticTaskSignature,
        top_k: int = 5,
        similarity_threshold: float = 0.85
    ) -> List[StoredPattern]:
        """Semantic similarity search"""

    def hybrid_search(
        self,
        signature: SemanticTaskSignature,
        domain: Optional[str] = None,
        top_k: int = 5
    ) -> List[StoredPattern]:
        """Hybrid search: 70% vector similarity + 30% metadata"""
```

**Pattern Categories for Production-Ready Apps**:
```python
PRODUCTION_PATTERN_CATEGORIES = {
    # Core Infrastructure
    'core_config': {
        'patterns': ['pydantic_settings_config', 'environment_management', 'feature_flags'],
        'success_threshold': 0.98,
        'domain': 'configuration'
    },
    'database_async': {
        'patterns': ['sqlalchemy_async_engine', 'connection_pooling', 'alembic_setup'],
        'success_threshold': 0.98,
        'domain': 'data_access'
    },
    'observability': {
        'patterns': ['structlog_setup', 'health_checks', 'prometheus_metrics', 'request_id_middleware'],
        'success_threshold': 0.95,
        'domain': 'infrastructure'
    },

    # Data Layer
    'models_pydantic': {
        'patterns': ['strict_mode_schemas', 'validation_patterns', 'timezone_aware_datetimes'],
        'success_threshold': 0.95,
        'domain': 'data_modeling'
    },
    'models_sqlalchemy': {
        'patterns': ['async_declarative_base', 'entity_relationships', 'database_indexes'],
        'success_threshold': 0.95,
        'domain': 'data_modeling'
    },
    'repository_pattern': {
        'patterns': ['generic_repository', 'async_crud_operations', 'transaction_management'],
        'success_threshold': 0.95,
        'domain': 'data_access'
    },

    # Service Layer
    'business_logic': {
        'patterns': ['service_layer_pattern', 'dependency_injection', 'error_handling'],
        'success_threshold': 0.90,
        'domain': 'business_logic'
    },

    # API Layer
    'api_routes': {
        'patterns': ['fastapi_crud_endpoints', 'pagination', 'api_versioning'],
        'success_threshold': 0.95,
        'domain': 'api'
    },

    # Security
    'security_hardening': {
        'patterns': ['html_sanitization', 'rate_limiting', 'security_headers', 'cors_config'],
        'success_threshold': 0.98,
        'domain': 'security'
    },

    # Testing
    'test_infrastructure': {
        'patterns': ['pytest_config', 'async_fixtures', 'test_factories', 'integration_tests'],
        'success_threshold': 0.95,
        'domain': 'testing'
    },

    # Docker & Infrastructure
    'docker_infrastructure': {
        'patterns': ['multistage_dockerfile', 'docker_compose_full_stack', 'health_checks'],
        'success_threshold': 0.95,
        'domain': 'infrastructure'
    },

    # Configuration Files
    'project_config': {
        'patterns': ['pyproject_toml', 'env_example', 'gitignore', 'makefile', 'pre_commit'],
        'success_threshold': 0.90,
        'domain': 'configuration'
    }
}
```

### Pattern Metadata Enhancement

**Add Production Readiness Score** to PatternBank metadata:

```python
# Extend PatternBank._store_in_qdrant() metadata:
metadata = {
    "pattern_id": pattern_id,
    "purpose": signature.purpose,
    "intent": signature.intent,
    "domain": signature.domain,
    "category": classification_result.category,
    "code": code,
    "success_rate": success_rate,

    # NEW: Production readiness metadata
    "production_ready": True,  # Flag for production patterns
    "production_readiness_score": 0.95,  # Calculated from quality metrics
    "test_coverage": 0.85,  # From execution metrics
    "security_level": "high",  # From PatternClassifier
    "performance_tier": "medium",  # From PatternClassifier
    "observability_complete": True,  # Has logging/metrics
    "docker_ready": True,  # Has Docker support

    "usage_count": 0,
    "created_at": datetime.utcnow().isoformat(),
    "semantic_hash": semantic_hash,
}
```

### Pattern Composition System

**File**: `src/services/code_generation_service.py`

**New Pattern-Based Methods**:
```python
class CodeGenerationService:
    def __init__(self):
        self.pattern_bank = PatternBank()
        self.pattern_bank.connect()

    async def generate_production_app(self, spec: SpecRequirements) -> GeneratedApp:
        """
        Generate complete production-ready application using pattern composition.

        Uses existing PatternBank infrastructure instead of Jinja2 templates.
        """

        # 1. Retrieve production-ready patterns by category
        patterns = await self._retrieve_production_patterns(spec)

        # 2. Compose patterns into modular architecture
        generated_files = await self._compose_patterns(patterns, spec)

        # 3. Validate completeness
        validation_result = await self._validate_production_readiness(generated_files)

        return GeneratedApp(
            files=generated_files,
            validation=validation_result,
            production_ready=validation_result.production_score >= 0.95
        )

    async def _retrieve_production_patterns(
        self, spec: SpecRequirements
    ) -> Dict[str, List[StoredPattern]]:
        """
        Retrieve production-ready patterns for all categories.

        Uses PatternBank.hybrid_search() with production_ready filter.
        """
        patterns = {}

        for category, config in PRODUCTION_PATTERN_CATEGORIES.items():
            # Create query signature for category
            query_sig = SemanticTaskSignature(
                purpose=f"production ready {category} implementation",
                intent="implement",
                inputs={},
                outputs={},
                domain=config['domain']
            )

            # Hybrid search with production_ready filter
            # NOTE: Need to extend PatternBank.hybrid_search() to support metadata filters
            category_patterns = self.pattern_bank.hybrid_search(
                signature=query_sig,
                domain=config['domain'],
                top_k=3
            )

            # Filter by production readiness threshold
            patterns[category] = [
                p for p in category_patterns
                if p.success_rate >= config['success_threshold']
                # TODO: Add production_ready metadata filter
            ]

        return patterns

    async def _compose_patterns(
        self,
        patterns: Dict[str, List[StoredPattern]],
        spec: SpecRequirements
    ) -> Dict[str, str]:
        """
        Compose patterns into complete modular application.

        Pattern composition rules:
        1. Core infrastructure patterns are applied first (config, database, logging)
        2. Data layer patterns (models, repositories)
        3. Service layer patterns
        4. API layer patterns (routes)
        5. Security patterns (middleware)
        6. Testing patterns
        7. Docker and config files
        """
        files = {}

        # 1. Core infrastructure
        if 'core_config' in patterns:
            files['src/core/config.py'] = self._adapt_pattern(
                patterns['core_config'][0].code,
                spec
            )

        if 'database_async' in patterns:
            files['src/core/database.py'] = self._adapt_pattern(
                patterns['database_async'][0].code,
                spec
            )

        if 'observability' in patterns:
            files['src/core/logging.py'] = self._adapt_pattern(
                patterns['observability'][0].code,  # structlog_setup
                spec
            )
            files['src/api/routes/health.py'] = self._adapt_pattern(
                patterns['observability'][1].code,  # health_checks
                spec
            )

        # 2. Data layer (per entity)
        for entity in spec.entities:
            # Pydantic schemas
            if 'models_pydantic' in patterns:
                files[f'src/models/schemas.py'] = self._generate_entity_schemas(
                    patterns['models_pydantic'], entity
                )

            # SQLAlchemy models
            if 'models_sqlalchemy' in patterns:
                files[f'src/models/entities.py'] = self._generate_entity_models(
                    patterns['models_sqlalchemy'], entity
                )

            # Repositories
            if 'repository_pattern' in patterns:
                files[f'src/repositories/{entity.snake_name}_repository.py'] = (
                    self._generate_repository(patterns['repository_pattern'], entity)
                )

        # 3. Service layer (per entity)
        if 'business_logic' in patterns:
            for entity in spec.entities:
                files[f'src/services/{entity.snake_name}_service.py'] = (
                    self._generate_service(patterns['business_logic'], entity)
                )

        # 4. API routes (per entity)
        if 'api_routes' in patterns:
            for entity in spec.entities:
                files[f'src/api/routes/{entity.snake_name}.py'] = (
                    self._generate_routes(patterns['api_routes'], entity)
                )

        # 5. Security
        if 'security_hardening' in patterns:
            files['src/core/security.py'] = self._compose_security_patterns(
                patterns['security_hardening']
            )

        # 6. Testing
        if 'test_infrastructure' in patterns:
            files['tests/conftest.py'] = patterns['test_infrastructure'][0].code  # pytest_config
            files['tests/factories.py'] = patterns['test_infrastructure'][1].code  # test_factories

            for entity in spec.entities:
                files[f'tests/integration/test_{entity.snake_name}_api.py'] = (
                    self._generate_integration_tests(patterns['test_infrastructure'], entity)
                )

        # 7. Docker & Infrastructure
        if 'docker_infrastructure' in patterns:
            files['docker/Dockerfile'] = patterns['docker_infrastructure'][0].code
            files['docker/docker-compose.yml'] = patterns['docker_infrastructure'][1].code

        # 8. Config files
        if 'project_config' in patterns:
            files['pyproject.toml'] = patterns['project_config'][0].code
            files['.env.example'] = patterns['project_config'][1].code
            files['.gitignore'] = patterns['project_config'][2].code
            files['Makefile'] = patterns['project_config'][3].code

        return files

    def _adapt_pattern(self, pattern_code: str, spec: SpecRequirements) -> str:
        """
        Adapt pattern code to spec requirements.

        Replace placeholder variables with actual spec values:
        - {APP_NAME} → spec.app_name
        - {DATABASE_URL} → spec.database_url
        - {ENTITY_NAME} → entity.name
        """
        adapted = pattern_code
        adapted = adapted.replace("{APP_NAME}", spec.app_name)
        adapted = adapted.replace("{DATABASE_URL}", spec.config.get("database_url", ""))
        # ... additional adaptations
        return adapted
```

---

## Success Criteria

### Functional Requirements

✅ **Generated App Must**:
1. Have 80%+ test coverage (pytest)
2. Include structured logging (structlog)
3. Provide health and metrics endpoints
4. Use SQLAlchemy async with Alembic migrations
5. Have modular architecture (models/repos/services/routes)
6. Include security hardening (sanitization, rate limiting, strict mode)
7. Provide complete Docker setup (docker-compose with full stack)
8. Include CI/CD pipeline template
9. Have comprehensive README and documentation
10. Be immediately deployable to production

### Quality Metrics

| Metric | Target | Validation Method |
|--------|--------|-------------------|
| Test Coverage | ≥80% | pytest --cov |
| Semantic Compliance | 100% | E2E compliance validator |
| Production Readiness | ≥95% | QA/CTO checklist |
| Security Score (OWASP) | ≥8/10 | Security audit |
| Docker Health Checks | 100% | docker-compose ps |
| Documentation Completeness | 100% | README checklist |

### Performance Targets

- Code generation time: <3 minutes (maintain current speed)
- Docker build time: <5 minutes
- Test execution time: <2 minutes
- Application startup time: <10 seconds

---

## Risk Assessment

### High Risk

1. **Template Complexity Explosion**
   - Risk: Too many templates hard to maintain
   - Mitigation: Use inheritance and composition in Jinja2 templates

2. **Breaking Changes to Existing Pipeline**
   - Risk: New templates break current code generation
   - Mitigation: Feature flag for "production mode", keep legacy path

3. **Performance Degradation**
   - Risk: Generating more files slows down pipeline
   - Mitigation: Parallel file generation, optimize template rendering

### Medium Risk

4. **Test Generation Accuracy**
   - Risk: Generated tests don't cover edge cases
   - Mitigation: Test template validation, E2E test of generated tests

5. **Docker Configuration Complexity**
   - Risk: docker-compose too complex for users
   - Mitigation: Comprehensive README, Makefile shortcuts

### Low Risk

6. **Documentation Drift**
   - Risk: Generated README doesn't match code
   - Mitigation: README template synced with code templates

---

## Rollout Strategy

### Phase 0: Preparation (1 week)

- Set up development environment
- Create feature branch: `feature/production-ready-generation`
- Design template architecture
- Create sample generated app manually (validation)

### Phase 1: Core Implementation (2 weeks)

- Implement all templates
- Modify code generation service
- Add template rendering logic
- Create integration tests for generator

### Phase 2: Testing & Validation (1 week)

- Generate simple_task_api with new system
- Generate ecommerce_api with new system
- Run QA/CTO evaluation on generated apps
- Verify 95% production readiness target

### Phase 3: Rollout (1 week)

- Merge to develop branch
- Run full E2E test suite
- Update documentation
- Deploy to production

---

## Appendix: QA/CTO Evaluation Checklist

### Production Readiness Assessment

**Score**: X / 20 points (X% production-ready)

#### Testing (4 points)
- [ ] +1: pytest configuration exists
- [ ] +1: Test coverage ≥80%
- [ ] +1: Unit tests for models, repos, services
- [ ] +1: Integration tests for API endpoints

#### Observability (4 points)
- [ ] +1: Structured logging (structlog) configured
- [ ] +1: Health check endpoint (/health)
- [ ] +1: Readiness check endpoint (/ready)
- [ ] +1: Metrics endpoint (/metrics) - Prometheus

#### Architecture (4 points)
- [ ] +1: Modular structure (models/repos/services/routes)
- [ ] +1: SQLAlchemy async with real database
- [ ] +1: Alembic migrations setup
- [ ] +1: Repository pattern implemented

#### Configuration (2 points)
- [ ] +1: pydantic-settings configuration
- [ ] +1: .env support with .env.example

#### Security (3 points)
- [ ] +1: Pydantic strict mode enabled
- [ ] +1: HTML sanitization / XSS prevention
- [ ] +1: Rate limiting implemented

#### Infrastructure (3 points)
- [ ] +1: Dockerfile exists and builds
- [ ] +1: docker-compose.yml with full stack
- [ ] +1: CI/CD pipeline template

**Rating Scale**:
- 0-10 points (0-50%): MVP/Prototype only
- 11-15 points (55-75%): Needs work for production
- 16-18 points (80-90%): Production-ready with minor gaps
- 19-20 points (95-100%): Fully production-ready

---

## Conclusion

This specification transforms DevMatrix from an MVP generator to a **Production App Generator** by:

1. ✅ Adding comprehensive test suite (80%+ coverage)
2. ✅ Implementing full observability (logging, health checks, metrics)
3. ✅ Replacing in-memory storage with SQLAlchemy + Alembic
4. ✅ Creating modular architecture (models/repos/services/routes)
5. ✅ Hardening security (OWASP 8/10)
6. ✅ Providing complete Docker infrastructure
7. ✅ Including CI/CD pipeline templates
8. ✅ Fixing critical bugs (type coercion, timezones, XSS)

**Expected Outcome**: Generated applications are **immediately production-ready** with zero manual work needed for deployment, achieving **95% production readiness** vs. current 25%.

**Business Impact**: Save 80-120 hours per generated application, with **9-13x ROI** after 10 apps.
