# Tasks: DevMatrix Production-Ready Code Generation

**Specification**: [spec.md](spec.md)
**Status**: Ready for Implementation
**Total Effort**: 90 hours (~11.5 days @ 8h/day)

---

## Task Organization

### Priority Levels

- **P0 (Critical)**: Blockers for production readiness
- **P1 (High)**: Major quality/security issues
- **P2 (Medium)**: Infrastructure and tooling

### Phases

1. **Phase 1: Core Infrastructure (P0)** - 40 hours - Week 1
2. **Phase 2: Testing & Security (P1)** - 30 hours - Week 2
3. **Phase 3: Docker & CI/CD (P2)** - 20 hours - Week 3

---

## Phase 1: Core Infrastructure (P0) - 40 hours

### Task Group 1: Database & Configuration (10 hours)

#### Task 1.1: Setup SQLAlchemy Async Engine (2h)

**Priority**: P0
**Component**: Core Infrastructure
**Dependencies**: None

**Requirements**:
- Create `src/core/database.py`
- Configure async engine with asyncpg driver
- Implement connection pooling (pool_size, max_overflow)
- Add pool_pre_ping for connection health checks
- Create AsyncSession factory (async_sessionmaker)
- Implement Base for declarative models

**Deliverables**:
- [ ] `src/core/database.py` created
- [ ] Async engine configured with settings
- [ ] Connection pooling setup (5 connections, 10 overflow)
- [ ] Session factory implemented
- [ ] `get_db()` dependency for FastAPI

**Validation**:
```python
# Test connection
async with async_session_maker() as session:
    await session.execute("SELECT 1")
```

---

#### Task 1.2: Implement pydantic-settings Configuration (2h)

**Priority**: P0
**Component**: Core Infrastructure
**Dependencies**: None

**Requirements**:
- Create `src/core/config.py`
- Define Settings class with pydantic-settings
- Support .env file loading
- Include all configuration categories:
  - Application (app_name, version, debug)
  - Database (url, pool settings)
  - Logging (log_level)
  - Security (cors_origins, rate_limit)
- Implement cached settings with `@lru_cache`

**Deliverables**:
- [ ] `src/core/config.py` created
- [ ] Settings class with all fields
- [ ] .env.example template created
- [ ] get_settings() cached function

**Validation**:
```python
settings = get_settings()
assert settings.database_url.startswith("postgresql+asyncpg://")
assert settings.log_level in ["DEBUG", "INFO", "WARNING", "ERROR"]
```

---

#### Task 1.3: Setup Alembic Migrations (3h)

**Priority**: P0
**Component**: Database
**Dependencies**: Task 1.1 (SQLAlchemy setup)

**Requirements**:
- Initialize Alembic in project root
- Configure `alembic.ini` with database URL from settings
- Setup `alembic/env.py` for async migrations
- Import Base metadata for auto-generation
- Configure target_metadata

**Deliverables**:
- [ ] `alembic/` directory created
- [ ] `alembic.ini` configured
- [ ] `alembic/env.py` setup for async
- [ ] Alembic can connect to database

**Commands**:
```bash
alembic init alembic
alembic revision --autogenerate -m "Test"
alembic upgrade head
```

---

#### Task 1.4: Create Initial Migrations for Entities (3h)

**Priority**: P0
**Component**: Database
**Dependencies**: Task 1.3 (Alembic setup)

**Requirements**:
- Define SQLAlchemy models for all entities (TaskEntity, etc.)
- Use proper column types (UUID, String, Text, Boolean, DateTime)
- Add timezone-aware DateTime columns
- Create indexes on commonly queried fields
- Generate initial migration
- Apply migration to create tables

**Deliverables**:
- [ ] SQLAlchemy models defined in `src/models/entities.py`
- [ ] Timezone-aware created_at/updated_at columns
- [ ] Indexes on title, completed, etc.
- [ ] Initial migration created
- [ ] Migration applied successfully

**Validation**:
```bash
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
# Check tables exist
psql -c "\dt"
```

---

### Task Group 2: Modular Architecture (15 hours)

#### Task 2.1: Create Directory Structure (1h)

**Priority**: P0
**Component**: Architecture
**Dependencies**: None

**Requirements**:
- Create `src/core/` directory
- Create `src/models/` directory
- Create `src/repositories/` directory
- Create `src/services/` directory
- Create `src/api/routes/` directory
- Add `__init__.py` to all directories

**Deliverables**:
- [ ] All directories created
- [ ] `__init__.py` in each directory
- [ ] Project follows modular structure

**Structure**:
```
src/
├── core/
├── models/
├── repositories/
├── services/
└── api/
    └── routes/
```

---

#### Task 2.2: Split Pydantic Schemas (2h)

**Priority**: P0
**Component**: Models
**Dependencies**: Task 2.1 (directory structure)

**Requirements**:
- Create `src/models/schemas.py`
- Define Pydantic schemas for all entities:
  - Base schema (common fields)
  - Create schema (input for POST)
  - Update schema (input for PUT/PATCH)
  - Response schema (output)
- Enable strict mode with ConfigDict(strict=True)
- Add field validators and constraints
- Support Optional fields for updates

**Deliverables**:
- [ ] `src/models/schemas.py` created
- [ ] Schemas for each entity (Task, Product, etc.)
- [ ] Strict mode enabled
- [ ] Field validation with min_length, max_length, gt, ge
- [ ] Update schemas support partial updates

**Example**:
```python
class TaskCreate(BaseModel):
    model_config = ConfigDict(strict=True)
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    completed: bool = Field(default=False)
```

---

#### Task 2.3: Define SQLAlchemy Entities (2h)

**Priority**: P0
**Component**: Models
**Dependencies**: Task 1.1 (database setup), Task 2.1 (structure)

**Requirements**:
- Create `src/models/entities.py`
- Define SQLAlchemy models for all entities
- Use UUID primary keys
- Add timezone-aware DateTime columns
- Create indexes on frequently queried fields
- Add __repr__ methods for debugging

**Deliverables**:
- [ ] `src/models/entities.py` created
- [ ] SQLAlchemy models for each entity
- [ ] UUID(as_uuid=True) primary keys
- [ ] DateTime(timezone=True) for timestamps
- [ ] Indexes on title, completed, is_active, etc.

**Example**:
```python
class TaskEntity(Base):
    __tablename__ = "tasks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
```

---

#### Task 2.4: Implement Repository Pattern (4h)

**Priority**: P0
**Component**: Repositories
**Dependencies**: Task 2.2 (schemas), Task 2.3 (entities)

**Requirements**:
- Create repository class for each entity (e.g., `TaskRepository`)
- Implement CRUD operations:
  - `create(data: CreateSchema) -> Entity`
  - `get(id: UUID) -> Optional[Entity]`
  - `list(skip: int, limit: int) -> List[Entity]`
  - `update(id: UUID, data: UpdateSchema) -> Optional[Entity]`
  - `delete(id: UUID) -> bool`
- Use async/await for all database operations
- Add structured logging for operations
- Handle transactions properly

**Deliverables**:
- [ ] Repository class per entity in `src/repositories/`
- [ ] All CRUD methods implemented
- [ ] Async/await used consistently
- [ ] Logging for create/update/delete operations
- [ ] Proper error handling

**Example**:
```python
class TaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, task_data: TaskCreate) -> TaskEntity:
        task = TaskEntity(**task_data.model_dump())
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)
        logger.info("task_created", task_id=str(task.id))
        return task
```

---

#### Task 2.5: Implement Service Layer (3h)

**Priority**: P0
**Component**: Services
**Dependencies**: Task 2.4 (repositories)

**Requirements**:
- Create service class for each entity (e.g., `TaskService`)
- Implement business logic layer
- Convert between entities and schemas
- Add business validations (e.g., HTML sanitization)
- Use repository for data access
- Return Pydantic schemas (not entities)

**Deliverables**:
- [ ] Service class per entity in `src/services/`
- [ ] Business logic methods
- [ ] Entity → Schema conversion
- [ ] Business validations
- [ ] Uses repository pattern

**Example**:
```python
class TaskService:
    def __init__(self, repository: TaskRepository):
        self.repo = repository

    async def create_task(self, task_data: TaskCreate) -> Task:
        # Business logic (e.g., sanitize HTML)
        task_entity = await self.repo.create(task_data)
        return Task.model_validate(task_entity)
```

---

#### Task 2.6: Setup FastAPI Dependencies (1h)

**Priority**: P0
**Component**: API
**Dependencies**: Task 2.4 (repositories), Task 2.5 (services)

**Requirements**:
- Create `src/api/dependencies.py`
- Implement dependency for database session (get_db)
- Implement dependency for repositories
- Implement dependency for services
- Use FastAPI Depends for dependency injection

**Deliverables**:
- [ ] `src/api/dependencies.py` created
- [ ] get_db() dependency
- [ ] get_X_repository() dependencies
- [ ] get_X_service() dependencies
- [ ] Proper dependency chain

**Example**:
```python
def get_task_repository(db: AsyncSession = Depends(get_db)) -> TaskRepository:
    return TaskRepository(db)

def get_task_service(repo: TaskRepository = Depends(get_task_repository)) -> TaskService:
    return TaskService(repo)
```

---

#### Task 2.7: Refactor Routes to Use Services (2h)

**Priority**: P0
**Component**: API
**Dependencies**: Task 2.6 (dependencies)

**Requirements**:
- Create route files per entity in `src/api/routes/`
- Use APIRouter with prefix and tags
- Inject services via Depends
- Implement all CRUD endpoints
- Use proper HTTP status codes
- Add error handling (404, 422)
- Return Pydantic schemas

**Deliverables**:
- [ ] Route file per entity (e.g., `tasks.py`)
- [ ] All CRUD endpoints implemented
- [ ] Services injected via Depends
- [ ] HTTP status codes (201, 200, 204, 404)
- [ ] HTTPException for errors

**Example**:
```python
router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

@router.post("/", response_model=Task, status_code=201)
async def create_task(data: TaskCreate, service: TaskService = Depends(get_task_service)):
    return await service.create_task(data)
```

---

### Task Group 3: Observability Infrastructure (15 hours)

#### Task 3.1: Configure structlog (2h)

**Priority**: P0
**Component**: Core Infrastructure
**Dependencies**: None

**Requirements**:
- Create `src/core/logging.py`
- Configure structlog with:
  - JSON renderer for structured logs
  - Timestamp processor (ISO format)
  - Log level processor
  - Exception info processor
  - Context variables (request_id, user_id)
- Setup logging levels from config

**Deliverables**:
- [ ] `src/core/logging.py` created
- [ ] structlog configured with processors
- [ ] JSON output format
- [ ] Context variables support
- [ ] setup_logging() function

**Example**:
```python
structlog.configure(
    processors=[
        merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    ...
)
```

---

#### Task 3.2: Implement RequestIDMiddleware (2h)

**Priority**: P0
**Component**: Middleware
**Dependencies**: Task 3.1 (structlog)

**Requirements**:
- Create `src/core/middleware.py`
- Implement RequestIDMiddleware
- Generate UUID for each request
- Support X-Request-ID header (if provided)
- Bind request_id to structlog context
- Add request_id to response headers

**Deliverables**:
- [ ] RequestIDMiddleware class created
- [ ] UUID generation per request
- [ ] X-Request-ID header support
- [ ] Binds to structlog context
- [ ] Returns request_id in response

**Example**:
```python
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

---

#### Task 3.3: Create Health Check Endpoints (2h)

**Priority**: P0
**Component**: API
**Dependencies**: Task 1.1 (database)

**Requirements**:
- Create `src/api/routes/health.py`
- Implement `/health/health` endpoint (basic check)
- Implement `/health/ready` endpoint (dependency check)
- Check database connection in readiness
- Return proper status codes (200, 503)
- Add structured logging

**Deliverables**:
- [ ] `src/api/routes/health.py` created
- [ ] /health/health endpoint (always returns 200)
- [ ] /health/ready endpoint (checks database)
- [ ] Proper error handling (503 if not ready)
- [ ] Structured logging for failures

**Example**:
```python
@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "task-api"}

@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute("SELECT 1")
        return {"status": "ready", "checks": {"database": "ok"}}
    except Exception as e:
        logger.error("readiness_check_failed", error=str(e))
        raise HTTPException(503, {"status": "not_ready"})
```

---

#### Task 3.4: Implement Prometheus Metrics (4h)

**Priority**: P0
**Component**: Metrics
**Dependencies**: None

**Requirements**:
- Create `src/api/routes/metrics.py`
- Setup Prometheus client
- Define metrics:
  - http_requests_total (Counter)
  - http_request_duration_seconds (Histogram)
  - business metrics (tasks_created_total, etc.)
- Create `/metrics/metrics` endpoint
- Implement MetricsMiddleware to track requests

**Deliverables**:
- [ ] `src/api/routes/metrics.py` created
- [ ] Prometheus metrics defined
- [ ] /metrics/metrics endpoint
- [ ] MetricsMiddleware tracks all requests
- [ ] Business metrics for key operations

**Example**:
```python
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

@router.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

---

#### Task 3.5: Add MetricsMiddleware (2h)

**Priority**: P0
**Component**: Middleware
**Dependencies**: Task 3.4 (metrics setup)

**Requirements**:
- Add MetricsMiddleware to `src/core/middleware.py`
- Track request duration
- Record metrics for each request
- Label by method, endpoint, status code
- Handle exceptions gracefully

**Deliverables**:
- [ ] MetricsMiddleware class created
- [ ] Tracks request duration
- [ ] Records http_requests_total
- [ ] Records http_request_duration_seconds
- [ ] Labels include method, endpoint, status

---

#### Task 3.6: Setup Global Exception Handler (2h)

**Priority**: P0
**Component**: Error Handling
**Dependencies**: Task 3.1 (structlog)

**Requirements**:
- Create global exception handler
- Log all unhandled exceptions with structlog
- Return standardized error response
- Include request_id in error response
- Return 500 status code
- Add exc_info=True for stack traces

**Deliverables**:
- [ ] Global exception handler function
- [ ] Registered with FastAPI app
- [ ] Logs exceptions with full context
- [ ] Returns standard error format
- [ ] Includes request_id

**Example**:
```python
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "unhandled_exception",
        exception_type=type(exc).__name__,
        exception_message=str(exc),
        path=request.url.path,
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "request_id": request.headers.get("X-Request-ID")}
    )
```

---

#### Task 3.7: Update Main Application Setup (1h)

**Priority**: P0
**Component**: Main App
**Dependencies**: All Phase 1 tasks

**Requirements**:
- Update `src/main.py`
- Initialize structlog on startup
- Add all middleware (RequestID, Metrics, Security, CORS)
- Register all routers (health, metrics, tasks, etc.)
- Add startup/shutdown event handlers
- Configure exception handlers

**Deliverables**:
- [ ] main.py updated with all components
- [ ] Middleware registered in correct order
- [ ] All routes included
- [ ] Startup/shutdown events
- [ ] Exception handlers registered

**Example**:
```python
setup_logging(settings.log_level)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(MetricsMiddleware)
app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(tasks.router)
```

---

## Phase 2: Testing & Security (P1) - 30 hours

### Task Group 4: Test Suite Generation (20 hours)

#### Task 4.1: Setup pytest Configuration (2h)

**Priority**: P1
**Component**: Testing
**Dependencies**: Phase 1 complete

**Requirements**:
- Create `pytest.ini`
- Configure test paths, patterns
- Setup asyncio mode
- Configure coverage options (--cov, --cov-report)
- Set coverage minimum threshold (80%)
- Create `.coveragerc`

**Deliverables**:
- [ ] pytest.ini created
- [ ] Test paths configured (tests/)
- [ ] asyncio_mode = auto
- [ ] Coverage options set
- [ ] Coverage threshold 80%
- [ ] .coveragerc with source/omit rules

**Example**:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = --verbose --cov=src --cov-report=term-missing --cov-fail-under=80
asyncio_mode = auto
```

---

#### Task 4.2: Create conftest.py with Fixtures (3h)

**Priority**: P1
**Component**: Testing
**Dependencies**: Task 4.1 (pytest config)

**Requirements**:
- Create `tests/conftest.py`
- Implement db_session fixture (async)
- Implement client fixture (AsyncClient)
- Override get_db dependency for testing
- Setup test database connection
- Add session cleanup (rollback)

**Deliverables**:
- [ ] tests/conftest.py created
- [ ] db_session fixture (yields AsyncSession)
- [ ] client fixture (yields AsyncClient)
- [ ] Dependency override for get_db
- [ ] Session rollback after each test

**Example**:
```python
@pytest.fixture
async def db_session():
    async with async_session_maker() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

---

#### Task 4.3: Implement Test Data Factories (2h)

**Priority**: P1
**Component**: Testing
**Dependencies**: Task 4.1

**Requirements**:
- Create `tests/factories.py`
- Implement factory for each entity
- Support kwargs override
- Implement create() static method
- Implement create_batch() for multiple instances
- Use realistic default values

**Deliverables**:
- [ ] tests/factories.py created
- [ ] Factory class per entity
- [ ] create(**kwargs) method
- [ ] create_batch(n, **kwargs) method
- [ ] Realistic defaults

**Example**:
```python
class TaskFactory:
    @staticmethod
    def create(**kwargs):
        defaults = {
            "id": uuid4(),
            "title": "Test Task",
            "description": "Test description",
            "completed": False,
            "created_at": datetime.now(timezone.utc)
        }
        defaults.update(kwargs)
        return Task(**defaults)

    @staticmethod
    def create_batch(n: int, **kwargs):
        return [TaskFactory.create(**kwargs) for _ in range(n)]
```

---

#### Task 4.4: Write Model Unit Tests (3h)

**Priority**: P1
**Component**: Testing
**Dependencies**: Task 4.3 (factories)

**Requirements**:
- Create `tests/unit/test_models.py`
- Test Pydantic validation for Create schemas
- Test required fields raise ValidationError
- Test field constraints (min_length, max_length, gt, ge)
- Test strict mode (type coercion rejected)
- Test Update schemas with optional fields
- Test model_validate for ORM conversion

**Deliverables**:
- [ ] tests/unit/test_models.py created
- [ ] Tests for each entity schema
- [ ] Validation error tests
- [ ] Field constraint tests
- [ ] Strict mode tests (reject "yes" for bool)
- [ ] Update schema optional field tests

**Coverage Target**: 90%+ for models/schemas.py

---

#### Task 4.5: Write Repository Unit Tests (4h)

**Priority**: P1
**Component**: Testing
**Dependencies**: Task 4.2 (conftest), Task 4.3 (factories)

**Requirements**:
- Create `tests/unit/test_repositories.py`
- Test create() method
- Test get() method (found and not found)
- Test list() method with pagination
- Test update() method
- Test delete() method
- Use db_session fixture
- Use factories for test data

**Deliverables**:
- [ ] tests/unit/test_repositories.py created
- [ ] Tests for each repository class
- [ ] All CRUD methods tested
- [ ] Not found scenarios tested
- [ ] Uses db_session fixture
- [ ] Uses factories

**Coverage Target**: 85%+ for repositories/

---

#### Task 4.6: Write Service Unit Tests (4h)

**Priority**: P1
**Component**: Testing
**Dependencies**: Task 4.5

**Requirements**:
- Create `tests/unit/test_services.py`
- Test service methods with mocked repositories
- Use pytest-mock or unittest.mock
- Test business logic (e.g., HTML sanitization)
- Test entity → schema conversion
- Test error handling

**Deliverables**:
- [ ] tests/unit/test_services.py created
- [ ] Tests for each service class
- [ ] Mocked repository dependencies
- [ ] Business logic tests
- [ ] Conversion tests
- [ ] Error scenario tests

**Coverage Target**: 80%+ for services/

---

#### Task 4.7: Write API Integration Tests (6h)

**Priority**: P1
**Component**: Testing
**Dependencies**: Task 4.2 (client fixture)

**Requirements**:
- Create `tests/integration/test_api.py`
- Test all CRUD endpoints
- Test success scenarios (201, 200, 204)
- Test error scenarios (404, 422)
- Test pagination
- Test validation errors
- Use client fixture
- Test complete workflows (create → get → update → delete)

**Deliverables**:
- [ ] tests/integration/test_api.py created
- [ ] Tests for all endpoints
- [ ] Success path tests
- [ ] Error path tests (404, 422)
- [ ] Pagination tests
- [ ] Validation error tests
- [ ] End-to-end workflow tests

**Coverage Target**: 75%+ for api/routes/

---

### Task Group 5: Security Hardening (10 hours)

#### Task 5.1: Enable Pydantic Strict Mode (1h)

**Priority**: P1
**Component**: Security
**Dependencies**: Task 2.2 (schemas)

**Requirements**:
- Add `ConfigDict(strict=True)` to all Create schemas
- Add `ConfigDict(strict=True)` to all Update schemas
- Test that type coercion is rejected

**Deliverables**:
- [ ] Strict mode enabled on all schemas
- [ ] Tests verify type coercion rejected
- [ ] No breaking changes to valid data

**Validation**:
```python
# Should raise ValidationError
with pytest.raises(ValidationError):
    TaskCreate(title="Test", completed="yes")  # String for bool
```

---

#### Task 5.2: Implement HTML Sanitization (2h)

**Priority**: P1
**Component**: Security
**Dependencies**: Task 2.5 (services)

**Requirements**:
- Create `src/core/security.py`
- Implement sanitize_html() using bleach
- Define allowed tags and attributes
- Apply sanitization in service layer
- Add tests for XSS prevention

**Deliverables**:
- [ ] src/core/security.py created
- [ ] sanitize_html() function
- [ ] Applied in service create/update methods
- [ ] Tests verify XSS prevention

**Example**:
```python
import bleach

def sanitize_html(text: str) -> str:
    return bleach.clean(text, tags=['p', 'br', 'strong'], strip=True)
```

---

#### Task 5.3: Add Rate Limiting (2h)

**Priority**: P1
**Component**: Security
**Dependencies**: Task 2.7 (routes)

**Requirements**:
- Install slowapi
- Create limiter instance
- Add rate limit decorator to routes
- Configure rate limits per endpoint
- Add exception handler for rate limit exceeded
- Test rate limiting

**Deliverables**:
- [ ] slowapi installed
- [ ] Limiter configured
- [ ] Rate limits on POST/PUT/DELETE endpoints
- [ ] Exception handler for 429
- [ ] Tests verify rate limiting

**Example**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/")
@limiter.limit("10/minute")
async def create_task(...):
    ...
```

---

#### Task 5.4: Configure CORS Properly (1h)

**Priority**: P1
**Component**: Security
**Dependencies**: Task 3.7 (main app)

**Requirements**:
- Configure CORSMiddleware in main.py
- Use cors_origins from settings
- Set proper allow_credentials, allow_methods, allow_headers
- Add to middleware stack

**Deliverables**:
- [ ] CORSMiddleware configured
- [ ] Uses settings.cors_origins
- [ ] Proper configuration for credentials/methods/headers

**Example**:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

---

#### Task 5.5: Add Security Headers Middleware (2h)

**Priority**: P1
**Component**: Security
**Dependencies**: Task 3.2 (middleware)

**Requirements**:
- Create SecurityHeadersMiddleware
- Add security headers:
  - X-Content-Type-Options: nosniff
  - X-Frame-Options: DENY
  - X-XSS-Protection: 1; mode=block
  - Strict-Transport-Security
  - Content-Security-Policy
- Register in middleware stack

**Deliverables**:
- [ ] SecurityHeadersMiddleware class
- [ ] All security headers added
- [ ] Registered in app
- [ ] Tests verify headers present

---

#### Task 5.6: Fix Timezone-Aware Datetimes (1h)

**Priority**: P1
**Component**: Bug Fix
**Dependencies**: Task 2.3 (entities)

**Requirements**:
- Update all DateTime columns to use DateTime(timezone=True)
- Use datetime.now(timezone.utc) instead of datetime.utcnow()
- Update default factories
- Create migration if needed

**Deliverables**:
- [ ] All DateTime columns timezone-aware
- [ ] datetime.now(timezone.utc) used
- [ ] Migration created and applied
- [ ] Tests verify timezone info present

---

#### Task 5.7: Implement Consistent Error Responses (1h)

**Priority**: P1
**Component**: Error Handling
**Dependencies**: Task 2.7 (routes)

**Requirements**:
- Define standard error response format
- Update all HTTPException raises
- Include error code, message, resource info
- Include request_id in errors

**Deliverables**:
- [ ] Standard error format defined
- [ ] All routes use consistent format
- [ ] Tests verify error structure

**Example**:
```python
raise HTTPException(
    status_code=404,
    detail={
        "error": "resource_not_found",
        "message": f"Task {task_id} not found",
        "resource": "task",
        "resource_id": str(task_id)
    }
)
```

---

## Phase 3: Docker & CI/CD (P2) - 20 hours

### Task Group 6: Docker Infrastructure (15 hours)

#### Task 6.1: Create Multi-Stage Dockerfile (3h)

**Priority**: P2
**Component**: Docker
**Dependencies**: Phase 1 & 2 complete

**Requirements**:
- Create `docker/Dockerfile`
- Implement builder stage (install dependencies)
- Implement runtime stage (copy only needed files)
- Use poetry for dependency management
- Create non-root user
- Add health check
- Add CMD for migrations + app startup

**Deliverables**:
- [ ] docker/Dockerfile created
- [ ] Multi-stage build (builder + runtime)
- [ ] Non-root user (appuser)
- [ ] Health check defined
- [ ] CMD runs migrations then uvicorn

---

#### Task 6.2: Create docker-compose.yml (4h)

**Priority**: P2
**Component**: Docker
**Dependencies**: Task 6.1 (Dockerfile)

**Requirements**:
- Create `docker/docker-compose.yml`
- Define services:
  - app (FastAPI)
  - postgres (PostgreSQL 16)
  - redis (Redis 7)
  - prometheus (Prometheus)
  - grafana (Grafana)
- Configure networking
- Add volumes for persistence
- Add health checks
- Set depends_on with conditions

**Deliverables**:
- [ ] docker/docker-compose.yml created
- [ ] All 5 services defined
- [ ] Networking configured (app-network)
- [ ] Volumes for data persistence
- [ ] Health checks for postgres
- [ ] Proper service dependencies

---

#### Task 6.3: Configure Prometheus (2h)

**Priority**: P2
**Component**: Monitoring
**Dependencies**: Task 6.2 (docker-compose)

**Requirements**:
- Create `docker/prometheus.yml`
- Configure scrape for app service
- Set metrics path to `/metrics/metrics`
- Add to docker-compose volumes

**Deliverables**:
- [ ] docker/prometheus.yml created
- [ ] Scrape config for task-api
- [ ] Mounted in prometheus container

---

#### Task 6.4: Setup Grafana Dashboards (3h)

**Priority**: P2
**Component**: Monitoring
**Dependencies**: Task 6.3 (Prometheus)

**Requirements**:
- Create `docker/grafana/dashboards/` directory
- Create dashboard JSON for:
  - HTTP request rates
  - Request duration
  - Error rates
  - Business metrics (tasks created/deleted)
- Create `docker/grafana/datasources/` for Prometheus
- Configure provisioning in docker-compose

**Deliverables**:
- [ ] Grafana dashboard JSON created
- [ ] Datasource configuration
- [ ] Volumes mounted in docker-compose
- [ ] Dashboard displays app metrics

---

#### Task 6.5: Create docker-compose.test.yml (2h)

**Priority**: P2
**Component**: Testing
**Dependencies**: Task 4.7 (tests complete)

**Requirements**:
- Create `docker/docker-compose.test.yml`
- Define postgres-test service (tmpfs for speed)
- Define test service (runs pytest)
- Configure test database URL
- Set command to run migrations + tests
- Mount test reports volume

**Deliverables**:
- [ ] docker/docker-compose.test.yml created
- [ ] Isolated test database
- [ ] Test runner service
- [ ] Migrations run before tests
- [ ] Coverage reports saved to volume

---

#### Task 6.6: Test Docker Setup (1h)

**Priority**: P2
**Component**: Validation
**Dependencies**: All Task Group 6 tasks

**Requirements**:
- Build Docker image successfully
- Start all services with docker-compose up
- Verify all containers healthy
- Test health endpoint
- Test metrics endpoint
- Access Grafana dashboard
- Run tests with docker-compose.test.yml

**Deliverables**:
- [ ] Docker image builds without errors
- [ ] All services start and stay healthy
- [ ] Health checks pass
- [ ] Metrics accessible
- [ ] Grafana accessible on :3000
- [ ] Tests run successfully in Docker

**Commands**:
```bash
docker-compose -f docker/docker-compose.yml build
docker-compose -f docker/docker-compose.yml up -d
docker-compose -f docker/docker-compose.yml ps
curl http://localhost:8000/health/health
docker-compose -f docker/docker-compose.test.yml up --abort-on-container-exit
```

---

### Task Group 7: CI/CD & Documentation (5 hours)

#### Task 7.1: Create GitHub Actions Workflow (2h)

**Priority**: P2
**Component**: CI/CD
**Dependencies**: Task 6.5 (test setup)

**Requirements**:
- Create `.github/workflows/ci.yml`
- Define test job with postgres service
- Run linting (flake8, black, isort)
- Run migrations
- Run tests with coverage
- Upload coverage to Codecov
- Define build job (builds Docker image)
- Run health check on built image

**Deliverables**:
- [ ] .github/workflows/ci.yml created
- [ ] Test job configured
- [ ] Build job configured
- [ ] Coverage upload to Codecov
- [ ] Health check verification

---

#### Task 7.2: Setup Pre-commit Hooks (1h)

**Priority**: P2
**Component**: Development
**Dependencies**: None

**Requirements**:
- Create `.pre-commit-config.yaml`
- Configure hooks:
  - trailing-whitespace
  - end-of-file-fixer
  - check-yaml
  - black (code formatting)
  - isort (import sorting)
  - flake8 (linting)
- Add to pyproject.toml dev dependencies

**Deliverables**:
- [ ] .pre-commit-config.yaml created
- [ ] All hooks configured
- [ ] pre-commit in dev dependencies

---

#### Task 7.3: Create .gitignore (15min)

**Priority**: P2
**Component**: Git
**Dependencies**: None

**Requirements**:
- Create comprehensive .gitignore
- Include Python patterns (__pycache__, *.pyc, venv)
- Include testing patterns (.pytest_cache, .coverage)
- Include environment patterns (.env)
- Include IDE patterns (.vscode, .idea)

**Deliverables**:
- [ ] .gitignore created
- [ ] Covers Python, testing, env, IDE

---

#### Task 7.4: Create Comprehensive README.md (1h)

**Priority**: P2
**Component**: Documentation
**Dependencies**: All tasks complete

**Requirements**:
- Create README.md with sections:
  - Features list
  - Quick start (local & Docker)
  - API documentation links
  - Environment variables
  - Testing instructions
  - Deployment notes
- Include code examples
- Add badges (coverage, build status)

**Deliverables**:
- [ ] README.md created
- [ ] All sections complete
- [ ] Code examples included
- [ ] Clear instructions

---

#### Task 7.5: Create Makefile (45min)

**Priority**: P2
**Component**: Development
**Dependencies**: None

**Requirements**:
- Create Makefile with common commands:
  - help (list commands)
  - install (install dependencies)
  - dev (run dev server)
  - test (run tests)
  - coverage (tests with coverage)
  - docker-up/docker-down
  - migrate/migrate-create
  - lint/format
  - clean
- Add help text for each command

**Deliverables**:
- [ ] Makefile created
- [ ] All common commands included
- [ ] Help text for each command

**Example**:
```makefile
.PHONY: help install dev test coverage docker-up docker-down

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST)

dev: ## Run development server
	poetry run uvicorn src.main:app --reload
```

---

## Template Generation Tasks

These tasks modify the DevMatrix code generation pipeline to use the new templates.

### Task Group 8: Template System (20 hours - Separate from Phase 1-3)

#### Task 8.1: Create Template Directory Structure (1h)

**Priority**: P0
**Component**: Code Generation
**Dependencies**: None

**Requirements**:
- Create `templates/production/` directory
- Create subdirectories for each component
- Create README explaining template organization

**Deliverables**:
- [ ] templates/production/ directory
- [ ] Subdirectories (core, models, repositories, services, api, tests, docker, configs)
- [ ] Template README.md

---

#### Task 8.2: Create Core Templates (3h)

**Priority**: P0
**Component**: Templates
**Dependencies**: Task 8.1

**Requirements**:
- Create Jinja2 templates:
  - `core/config.py.j2`
  - `core/database.py.j2`
  - `core/logging.py.j2`
  - `core/security.py.j2`
  - `core/middleware.py.j2`
- Support variable substitution (app_name, settings fields)
- Add comments explaining generated code

**Deliverables**:
- [ ] 5 core templates created
- [ ] Variable substitution working
- [ ] Comments in templates

---

#### Task 8.3: Create Model Templates (2h)

**Priority**: P0
**Component**: Templates
**Dependencies**: Task 8.1

**Requirements**:
- Create `models/schemas.py.j2` (per-entity)
- Create `models/entities.py.j2` (per-entity)
- Support field iteration
- Generate validation constraints from spec
- Support optional fields for updates

**Deliverables**:
- [ ] schemas.py.j2 template
- [ ] entities.py.j2 template
- [ ] Field iteration working
- [ ] Constraints generated

---

#### Task 8.4: Create Repository Templates (2h)

**Priority**: P0
**Component**: Templates
**Dependencies**: Task 8.1

**Requirements**:
- Create `repositories/repository.py.j2` (per-entity)
- Generate CRUD methods
- Support async/await
- Add logging statements

**Deliverables**:
- [ ] repository.py.j2 template
- [ ] All CRUD methods generated
- [ ] Async syntax
- [ ] Logging included

---

#### Task 8.5: Create Service Templates (2h)

**Priority**: P0
**Component**: Templates
**Dependencies**: Task 8.1

**Requirements**:
- Create `services/service.py.j2` (per-entity)
- Generate business logic layer
- Include HTML sanitization
- Support pagination

**Deliverables**:
- [ ] service.py.j2 template
- [ ] Business logic methods
- [ ] Sanitization included
- [ ] Pagination support

---

#### Task 8.6: Create API Templates (2h)

**Priority**: P0
**Component**: Templates
**Dependencies**: Task 8.1

**Requirements**:
- Create `api/dependencies.py.j2`
- Create `api/routes.py.j2` (per-entity)
- Generate all CRUD endpoints from spec
- Include error handling
- Support pagination parameters

**Deliverables**:
- [ ] dependencies.py.j2 template
- [ ] routes.py.j2 template
- [ ] All endpoints generated
- [ ] Error handling included

---

#### Task 8.7: Create Test Templates (4h)

**Priority**: P1
**Component**: Templates
**Dependencies**: Task 8.1

**Requirements**:
- Create `tests/pytest.ini.j2`
- Create `tests/conftest.py.j2`
- Create `tests/factories.py.j2` (per-entity)
- Create `tests/test_models.py.j2` (per-entity)
- Create `tests/test_repositories.py.j2` (per-entity)
- Create `tests/test_services.py.j2` (per-entity)
- Create `tests/test_api.py.j2` (per-entity)
- Generate tests based on spec

**Deliverables**:
- [ ] 7 test templates created
- [ ] Tests generated per entity
- [ ] Coverage for all scenarios

---

#### Task 8.8: Create Docker Templates (2h)

**Priority**: P2
**Component**: Templates
**Dependencies**: Task 8.1

**Requirements**:
- Create `docker/Dockerfile.j2`
- Create `docker/docker-compose.yml.j2`
- Create `docker/docker-compose.test.yml.j2`
- Create `docker/prometheus.yml.j2`
- Support variable substitution (app_name, ports)

**Deliverables**:
- [ ] 4 Docker templates created
- [ ] Variables substituted
- [ ] Services configured

---

#### Task 8.9: Create Config Templates (1h)

**Priority**: P2
**Component**: Templates
**Dependencies**: Task 8.1

**Requirements**:
- Create `.env.example.j2`
- Create `.gitignore.j2`
- Create `pyproject.toml.j2`
- Create `alembic.ini.j2`
- Create `Makefile.j2`
- Create `README.md.j2`

**Deliverables**:
- [ ] 6 config templates created
- [ ] Variables substituted

---

#### Task 8.10: Modify Code Generation Service (3h)

**Priority**: P0
**Component**: Code Generation
**Dependencies**: All Task Group 8 tasks

**Requirements**:
- Update `src/services/code_generation_service.py`
- Add method: `generate_modular_app(spec) -> GeneratedApp`
- Implement directory structure creation
- Implement template rendering for each file
- Support per-entity file generation
- Add feature flag for "production mode"

**Deliverables**:
- [ ] generate_modular_app() method implemented
- [ ] Directory creation working
- [ ] All templates rendered
- [ ] Feature flag for production/legacy mode

---

## Validation & Testing

### Final Validation Checklist

After all tasks complete, validate the generated application:

#### Functional Validation

- [ ] Generate simple_task_api with new system
- [ ] Generate ecommerce_api with new system
- [ ] All files created in correct structure
- [ ] Application starts without errors
- [ ] All endpoints respond correctly
- [ ] Health checks return 200
- [ ] Metrics endpoint accessible

#### Test Validation

- [ ] pytest runs successfully
- [ ] All tests pass
- [ ] Coverage ≥80%
- [ ] No test failures

#### Docker Validation

- [ ] Docker image builds
- [ ] docker-compose up succeeds
- [ ] All containers healthy
- [ ] Application accessible
- [ ] Database connected
- [ ] Prometheus scraping metrics
- [ ] Grafana dashboards loading

#### Security Validation

- [ ] Pydantic strict mode working (rejects type coercion)
- [ ] HTML sanitization working
- [ ] Rate limiting enforced
- [ ] Security headers present
- [ ] CORS configured

#### QA/CTO Checklist

Run full evaluation using [spec.md Appendix: QA/CTO Evaluation Checklist](spec.md#appendix-qacto-evaluation-checklist)

**Target Score**: 19-20 / 20 points (95-100% production-ready)

---

## Progress Tracking

### Phase 1: Core Infrastructure ⏳

- [ ] Task Group 1: Database & Configuration (0/4 tasks)
- [ ] Task Group 2: Modular Architecture (0/7 tasks)
- [ ] Task Group 3: Observability Infrastructure (0/7 tasks)

**Progress**: 0/18 tasks (0%)

### Phase 2: Testing & Security ⏳

- [ ] Task Group 4: Test Suite Generation (0/7 tasks)
- [ ] Task Group 5: Security Hardening (0/7 tasks)

**Progress**: 0/14 tasks (0%)

### Phase 3: Docker & CI/CD ⏳

- [ ] Task Group 6: Docker Infrastructure (0/6 tasks)
- [ ] Task Group 7: CI/CD & Documentation (0/5 tasks)

**Progress**: 0/11 tasks (0%)

### Template System ⏳

- [ ] Task Group 8: Template Generation (0/10 tasks)

**Progress**: 0/10 tasks (0%)

---

## Overall Progress

**Total Tasks**: 53
**Completed**: 0
**In Progress**: 0
**Blocked**: 0
**Not Started**: 53

**Completion**: 0%

---

## Dependencies Graph

```
Phase 1 (P0) - Core Infrastructure
├── Task Group 1: Database & Config
│   └── Task Group 2: Modular Architecture
│       └── Task Group 3: Observability
│
Phase 2 (P1) - Testing & Security
├── Depends on: Phase 1 complete
├── Task Group 4: Test Suite
└── Task Group 5: Security Hardening
│
Phase 3 (P2) - Docker & CI/CD
├── Depends on: Phase 1 & 2 complete
├── Task Group 6: Docker Infrastructure
└── Task Group 7: CI/CD & Documentation

Template System (Parallel)
└── Task Group 8: Template Generation
    ├── Can start in parallel with Phase 1
    └── Required before production deployment
```

---

## Timeline Summary

| Phase | Effort | Duration | Dependency |
|-------|--------|----------|------------|
| Phase 1: Core Infrastructure | 40h | 5 days @ 8h/day | None |
| Phase 2: Testing & Security | 30h | 4 days @ 8h/day | Phase 1 |
| Phase 3: Docker & CI/CD | 20h | 2.5 days @ 8h/day | Phase 1 & 2 |
| Template System | 20h | 2.5 days @ 8h/day | Can be parallel |

**Total Sequential**: 90 hours (11.25 days @ 8h/day)
**With Parallelization**: 70 hours (8.75 days @ 8h/day) if Template System done in parallel

---

## Risk Mitigation

### High-Risk Tasks

1. **Task 8.10: Modify Code Generation Service** (3h)
   - Risk: Breaking existing pipeline
   - Mitigation: Feature flag for legacy/production mode, comprehensive testing

2. **Task 4.7: API Integration Tests** (6h)
   - Risk: Tests too brittle, fail on small changes
   - Mitigation: Focus on behavior not implementation, use factories

3. **Task 6.2: Docker Compose Setup** (4h)
   - Risk: Complex service dependencies
   - Mitigation: Incremental testing (add one service at a time)

### Blocked Tasks

Monitor for:
- Database connection issues (Phase 1)
- Test environment setup problems (Phase 2)
- Docker networking issues (Phase 3)

---

## Success Metrics

### Code Quality

- [ ] Pylint score ≥8.0
- [ ] No critical security issues (bandit scan)
- [ ] All type hints present (mypy passing)

### Performance

- [ ] Code generation time <3 minutes
- [ ] Docker build time <5 minutes
- [ ] Test execution time <2 minutes
- [ ] Application startup <10 seconds

### Production Readiness

- [ ] QA/CTO score ≥19/20 (95%+)
- [ ] All validation checklists passing
- [ ] Zero critical bugs
- [ ] Documentation complete

---

## Next Steps

1. Review this task list with team
2. Assign tasks to developers
3. Create feature branch: `feature/production-ready-generation`
4. Begin Phase 1: Task 1.1 (Setup SQLAlchemy Async Engine)
5. Track progress using GitHub Projects or similar
6. Daily standups to report blockers
7. Weekly demos of completed phases

---

**Document Version**: 1.0
**Last Updated**: 2025-11-20
**Next Review**: After Phase 1 completion
