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
- [x] `src/core/database.py` created
- [x] Async engine configured with settings
- [x] Connection pooling setup (5 connections, 10 overflow)
- [x] Session factory implemented
- [x] `get_db()` dependency for FastAPI

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
- [x] `src/core/config.py` created
- [x] Settings class with all fields
- [x] .env.example template created
- [x] get_settings() cached function

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
- [x] `alembic/` directory created
- [x] `alembic.ini` configured
- [x] `alembic/env.py` setup for async
- [x] Alembic can connect to database

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
- [x] SQLAlchemy models defined in `src/models/entities.py`
- [x] Timezone-aware created_at/updated_at columns
- [x] Indexes on title, completed, etc.
- [x] Initial migration created
- [x] Migration applied successfully

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
- [x] All directories created
- [x] `__init__.py` in each directory
- [x] Project follows modular structure

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
- [x] `src/models/schemas.py` created
- [x] Schemas for each entity (Task, Product, etc.)
- [x] Strict mode enabled
- [x] Field validation with min_length, max_length, gt, ge
- [x] Update schemas support partial updates

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
- [x] `src/models/entities.py` created
- [x] SQLAlchemy models for each entity
- [x] UUID(as_uuid=True) primary keys
- [x] DateTime(timezone=True) for timestamps
- [x] Indexes on title, completed, is_active, etc.

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
- [x] Repository class per entity in `src/repositories/`
- [x] All CRUD methods implemented
- [x] Async/await used consistently
- [x] Logging for create/update/delete operations
- [x] Proper error handling

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
- [x] Service class per entity in `src/services/`
- [x] Business logic methods
- [x] Entity → Schema conversion
- [x] Business validations
- [x] Uses repository pattern

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
- [x] `src/api/dependencies.py` created
- [x] get_db() dependency
- [x] get_X_repository() dependencies
- [x] get_X_service() dependencies
- [x] Proper dependency chain

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
- [x] Route file per entity (e.g., `tasks.py`)
- [x] All CRUD endpoints implemented
- [x] Services injected via Depends
- [x] HTTP status codes (201, 200, 204, 404)
- [x] HTTPException for errors

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
- [x] `src/core/logging.py` created
- [x] structlog configured with processors
- [x] JSON output format
- [x] Context variables support
- [x] setup_logging() function

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
- [x] RequestIDMiddleware class created
- [x] UUID generation per request
- [x] X-Request-ID header support
- [x] Binds to structlog context
- [x] Returns request_id in response

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
- [x] `src/api/routes/health.py` created
- [x] /health/health endpoint (always returns 200)
- [x] /health/ready endpoint (checks database)
- [x] Proper error handling (503 if not ready)
- [x] Structured logging for failures

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
- [x] `src/api/routes/metrics.py` created
- [x] Prometheus metrics defined
- [x] /metrics/metrics endpoint
- [x] MetricsMiddleware tracks all requests
- [x] Business metrics for key operations

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
- [x] MetricsMiddleware class created
- [x] Tracks request duration
- [x] Records http_requests_total
- [x] Records http_request_duration_seconds
- [x] Labels include method, endpoint, status

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
- [x] Global exception handler function
- [x] Registered with FastAPI app
- [x] Logs exceptions with full context
- [x] Returns standard error format
- [x] Includes request_id

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
- [x] main.py updated with all components
- [x] Middleware registered in correct order
- [x] All routes included
- [x] Startup/shutdown events
- [x] Exception handlers registered

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
- [x] pytest.ini created
- [x] Test paths configured (tests/)
- [x] asyncio_mode = auto
- [x] Coverage options set
- [x] Coverage threshold 80%
- [x] .coveragerc with source/omit rules

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
- [x] tests/conftest.py created
- [x] db_session fixture (yields AsyncSession)
- [x] client fixture (yields AsyncClient)
- [x] Dependency override for get_db
- [x] Session rollback after each test

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
- [x] tests/factories.py created
- [x] Factory class per entity
- [x] create(**kwargs) method
- [x] create_batch(n, **kwargs) method
- [x] Realistic defaults

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
- [x] tests/unit/test_models.py created
- [x] Tests for each entity schema
- [x] Validation error tests
- [x] Field constraint tests
- [x] Strict mode tests (reject "yes" for bool)
- [x] Update schema optional field tests

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
- [x] tests/unit/test_repositories.py created
- [x] Tests for each repository class
- [x] All CRUD methods tested
- [x] Not found scenarios tested
- [x] Uses db_session fixture
- [x] Uses factories

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
- [x] tests/unit/test_services.py created
- [x] Tests for each service class
- [x] Mocked repository dependencies
- [x] Business logic tests
- [x] Conversion tests
- [x] Error scenario tests

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
- [x] tests/integration/test_api.py created
- [x] Tests for all endpoints
- [x] Success path tests
- [x] Error path tests (404, 422)
- [x] Pagination tests
- [x] Validation error tests
- [x] End-to-end workflow tests

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
- [x] Strict mode enabled on all schemas
- [x] Tests verify type coercion rejected
- [x] No breaking changes to valid data

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
- [x] src/core/security.py created
- [x] sanitize_html() function
- [x] Applied in service create/update methods
- [x] Tests verify XSS prevention

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
- [x] slowapi installed
- [x] Limiter configured
- [x] Rate limits on POST/PUT/DELETE endpoints
- [x] Exception handler for 429
- [x] Tests verify rate limiting

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
- [x] CORSMiddleware configured
- [x] Uses settings.cors_origins
- [x] Proper configuration for credentials/methods/headers

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
- [x] SecurityHeadersMiddleware class
- [x] All security headers added
- [x] Registered in app
- [x] Tests verify headers present

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
- [x] All DateTime columns timezone-aware
- [x] datetime.now(timezone.utc) used
- [x] Migration created and applied
- [x] Tests verify timezone info present

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
- [x] Standard error format defined
- [x] All routes use consistent format
- [x] Tests verify error structure

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
- [x] docker/Dockerfile created
- [x] Multi-stage build (builder + runtime)
- [x] Non-root user (appuser)
- [x] Health check defined
- [x] CMD runs migrations then uvicorn

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
- [x] docker/docker-compose.yml created
- [x] All 5 services defined
- [x] Networking configured (app-network)
- [x] Volumes for data persistence
- [x] Health checks for postgres
- [x] Proper service dependencies

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
- [x] docker/prometheus.yml created
- [x] Scrape config for task-api
- [x] Mounted in prometheus container

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
- [x] Grafana dashboard JSON created
- [x] Datasource configuration
- [x] Volumes mounted in docker-compose
- [x] Dashboard displays app metrics

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
- [x] docker/docker-compose.test.yml created
- [x] Isolated test database
- [x] Test runner service
- [x] Migrations run before tests
- [x] Coverage reports saved to volume

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
- [x] Docker image builds without errors
- [x] All services start and stay healthy
- [x] Health checks pass
- [x] Metrics accessible
- [x] Grafana accessible on :3000
- [x] Tests run successfully in Docker

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
- [x] .github/workflows/ci.yml created
- [x] Test job configured
- [x] Build job configured
- [x] Coverage upload to Codecov
- [x] Health check verification

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
- [x] .pre-commit-config.yaml created
- [x] All hooks configured
- [x] pre-commit in dev dependencies

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
- [x] .gitignore created
- [x] Covers Python, testing, env, IDE

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
- [x] README.md created
- [x] All sections complete
- [x] Code examples included
- [x] Clear instructions

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
- [x] Makefile created
- [x] All common commands included
- [x] Help text for each command

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

### Task Group 8: Production Pattern Library (22 hours - Leverages Existing PatternBank)

**Strategic Change**: Instead of creating Jinja2 templates (duplicate functionality), leverage DevMatrix's existing PatternBank infrastructure (Qdrant + Neo4j + embeddings + auto-classification) to store production-ready golden patterns.

---

#### Task 8.1: Create Production Pattern Categories (2h)

**Priority**: P0
**Component**: Pattern Library
**Dependencies**: None

**Requirements**:
- Define `PRODUCTION_PATTERN_CATEGORIES` configuration in `src/cognitive/patterns/production_patterns.py`
- Create 10 pattern categories:
  - core_config (pydantic-settings, environment management)
  - database_async (SQLAlchemy async, connection pooling, Alembic)
  - observability (structlog, health checks, Prometheus metrics)
  - models_pydantic (strict mode schemas, timezone-aware datetimes)
  - models_sqlalchemy (async declarative base, relationships, indexes)
  - repository_pattern (generic repository, async CRUD, transactions)
  - business_logic (service layer, dependency injection, error handling)
  - api_routes (FastAPI CRUD endpoints, pagination, versioning)
  - security_hardening (HTML sanitization, rate limiting, security headers)
  - test_infrastructure (pytest config, fixtures, factories, integration tests)
  - docker_infrastructure (multistage Dockerfile, docker-compose full stack)
  - project_config (pyproject.toml, .env, .gitignore, Makefile)
- Each category specifies: domain, success_threshold, pattern names

**Deliverables**:
- [x] `src/cognitive/patterns/production_patterns.py` created
- [x] `PRODUCTION_PATTERN_CATEGORIES` dictionary defined (10 categories)
- [x] Category metadata complete (domain, thresholds)

---

#### Task 8.2: Create Core Infrastructure Patterns (4h)

**Priority**: P0
**Component**: Pattern Library
**Dependencies**: Task 8.1

**Requirements**:
- Create production-ready patterns for:
  1. **pydantic_settings_config**: Type-safe config with environment variables
  2. **sqlalchemy_async_engine**: Async engine with connection pooling
  3. **alembic_setup**: Migration configuration
  4. **structlog_setup**: Structured JSON logging with context
  5. **health_checks**: `/health` and `/ready` endpoints
  6. **prometheus_metrics**: `/metrics` endpoint with custom metrics
  7. **request_id_middleware**: Request ID tracking in logs/headers
  8. **metrics_middleware**: Response time and request count tracking
- Store patterns in PatternBank with:
  - `success_rate >= 0.98`
  - `production_ready = True`
  - `test_coverage >= 0.85`
  - Domain classification (configuration, infrastructure, data_access)

**Code**:
```python
# Store pattern in PatternBank
from src.cognitive.patterns.pattern_bank import PatternBank
from src.cognitive.signatures.semantic_signature import SemanticTaskSignature

pattern_bank = PatternBank()
pattern_bank.connect()

# Example: Store pydantic-settings config pattern
signature = SemanticTaskSignature(
    purpose="Production-ready pydantic-settings configuration with environment management",
    intent="implement",
    inputs={},
    outputs={},
    domain="configuration"
)

code = '''
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = "{APP_NAME}"
    environment: str = "development"
    debug: bool = False

    # Database
    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Observability
    log_level: str = "INFO"
    log_json: bool = True

    # Security
    secret_key: str
    allowed_origins: list[str] = ["http://localhost:3000"]

settings = Settings()
'''

pattern_id = pattern_bank.store_pattern(
    signature=signature,
    code=code,
    success_rate=0.98
)
```

**Deliverables**:
- [x] 8 core infrastructure patterns created and stored in PatternBank
- [x] All patterns have success_rate >= 0.98
- [x] Patterns include placeholder substitution ({APP_NAME}, {DATABASE_URL})
- [x] PatternBank metadata includes production_ready=True

---

#### Task 8.3: Create Model & Data Access Patterns (4h)

**Priority**: P0
**Component**: Pattern Library
**Dependencies**: Task 8.1

**Requirements**:
- Create patterns for:
  1. **strict_mode_schemas**: Pydantic schemas with ConfigDict(strict=True)
  2. **timezone_aware_datetimes**: datetime.now(timezone.utc) patterns
  3. **validation_patterns**: Custom validators with clear error messages
  4. **async_declarative_base**: SQLAlchemy async Base configuration
  5. **entity_relationships**: One-to-many, many-to-many patterns
  6. **database_indexes**: Index creation for performance
  7. **generic_repository**: Base repository with CRUD operations
  8. **async_crud_operations**: Async create/read/update/delete methods
  9. **transaction_management**: Context manager for DB transactions
- Store patterns with success_rate >= 0.95
- Domain: data_modeling, data_access

**Deliverables**:
- [x] 9 model & data access patterns created
- [x] All patterns async-compatible
- [x] Patterns follow repository pattern
- [x] Transaction management included

---

#### Task 8.4: Create API & Business Logic Patterns (2h)

**Priority**: P0
**Component**: Pattern Library
**Dependencies**: Task 8.1

**Requirements**:
- Create patterns for:
  1. **service_layer_pattern**: Business logic separation from API
  2. **dependency_injection**: FastAPI Depends() patterns
  3. **error_handling**: Consistent HTTPException responses
  4. **fastapi_crud_endpoints**: Complete CRUD with proper status codes
  5. **pagination**: Offset/limit pagination implementation
  6. **api_versioning**: /api/v1/ routing structure
- Store patterns with success_rate >= 0.95
- Domain: business_logic, api

**Deliverables**:
- [x] 6 API & business logic patterns created
- [x] Dependency injection working
- [x] Error handling consistent
- [x] Pagination implemented

---

#### Task 8.5: Create Security Patterns (2h)

**Priority**: P0
**Component**: Pattern Library
**Dependencies**: Task 8.1

**Requirements**:
- Create patterns for:
  1. **html_sanitization**: bleach library integration
  2. **rate_limiting**: slowapi integration
  3. **security_headers**: CSP, X-Frame-Options, etc.
  4. **cors_config**: Proper CORS configuration
- Store patterns with success_rate >= 0.98 (security critical)
- Domain: security
- Add security_level=CRITICAL metadata

**Deliverables**:
- [x] 4 security hardening patterns created
- [x] All patterns OWASP-compliant
- [x] HTML sanitization working (bleach)
- [x] Rate limiting implemented (slowapi)

---

#### Task 8.6: Create Test Infrastructure Patterns (4h)

**Priority**: P1
**Component**: Pattern Library
**Dependencies**: Task 8.1

**Requirements**:
- Create patterns for:
  1. **pytest_config**: pytest.ini with async support
  2. **async_fixtures**: Database fixtures with async cleanup
  3. **test_factories**: Factory pattern for test data generation
  4. **integration_tests**: FastAPI TestClient patterns
  5. **unit_test_models**: Pydantic model validation tests
  6. **unit_test_repositories**: Repository CRUD tests
  7. **unit_test_services**: Service layer tests with mocking
- Store patterns with success_rate >= 0.95
- Domain: testing
- Include test coverage calculation

**Deliverables**:
- [x] 7 test infrastructure patterns created
- [x] Pytest config with async support
- [x] Test factories implemented
- [x] Integration tests cover all endpoints

---

#### Task 8.7: Create Docker Infrastructure Patterns (2h)

**Priority**: P2
**Component**: Pattern Library
**Dependencies**: Task 8.1

**Requirements**:
- Create patterns for:
  1. **multistage_dockerfile**: Build + runtime stages optimized
  2. **docker_compose_full_stack**: App + PostgreSQL + Redis + Prometheus + Grafana
  3. **docker_compose_test**: Isolated test environment
  4. **health_checks_docker**: Health check configuration in docker-compose
- Store patterns with success_rate >= 0.95
- Domain: infrastructure
- Include volume mounts and networking

**Deliverables**:
- [x] 4 Docker infrastructure patterns created
- [x] Multi-stage Dockerfile optimized
- [x] docker-compose with full stack (5 services)
- [x] Health checks configured

---

#### Task 8.8: Create Project Configuration Patterns (1h)

**Priority**: P2
**Component**: Pattern Library
**Dependencies**: Task 8.1

**Requirements**:
- Create patterns for:
  1. **pyproject_toml**: Poetry config with all dependencies
  2. **env_example**: .env.example template
  3. **gitignore**: Comprehensive .gitignore
  4. **makefile**: Common commands (test, run, migrate)
  5. **pre_commit_config**: Pre-commit hooks (.pre-commit-config.yaml)
  6. **readme_template**: README.md with deployment instructions
- Store patterns with success_rate >= 0.90
- Domain: configuration

**Deliverables**:
- [x] 6 project config patterns created
- [x] All config files production-ready
- [x] Dependencies pinned (poetry.lock)
- [x] Makefile with common commands

---

#### Task 8.9: Extend PatternBank Metadata for Production Readiness (2h)

**Priority**: P0
**Component**: PatternBank
**Dependencies**: None

**Requirements**:
- Modify `src/cognitive/patterns/pattern_bank.py`:
  - Add `production_ready: bool` to metadata
  - Add `production_readiness_score: float` (calculated from quality metrics)
  - Add `test_coverage: float` to metadata
  - Add `observability_complete: bool` to metadata
  - Add `docker_ready: bool` to metadata
- Extend `hybrid_search()` to support `production_ready` filter:
  ```python
  def hybrid_search(
      self,
      signature: SemanticTaskSignature,
      domain: Optional[str] = None,
      production_ready: bool = False,  # NEW
      top_k: int = 5
  ) -> List[StoredPattern]:
  ```
- Calculate production_readiness_score from:
  - success_rate (40%)
  - test_coverage (30%)
  - security_level (20%)
  - observability_complete (10%)

**Deliverables**:
- [x] PatternBank._store_in_qdrant() updated with new metadata fields
- [x] hybrid_search() supports production_ready filter
- [x] production_readiness_score calculation implemented
- [x] All new metadata fields in Qdrant payload

---

#### Task 8.10: Implement Pattern Composition System (3h)

**Priority**: P0
**Component**: Code Generation
**Dependencies**: All Task Group 8 tasks

**Requirements**:
- Update `src/services/code_generation_service.py`:
  - Add method: `generate_production_app(spec) -> GeneratedApp`
  - Implement `_retrieve_production_patterns(spec)`: Retrieve patterns by category
  - Implement `_compose_patterns(patterns, spec)`: Compose patterns into modular app
  - Implement `_adapt_pattern(pattern_code, spec)`: Replace placeholders with spec values
  - Implement `_validate_production_readiness(files)`: Validate completeness
- Pattern composition order:
  1. Core infrastructure (config, database, logging)
  2. Data layer (models, repositories)
  3. Service layer
  4. API layer (routes)
  5. Security patterns
  6. Testing patterns
  7. Docker and config files
- Add feature flag: `PRODUCTION_MODE=True` to enable pattern-based generation

**Code Structure**:
```python
class CodeGenerationService:
    def __init__(self):
        self.pattern_bank = PatternBank()
        self.pattern_bank.connect()

    async def generate_production_app(self, spec: SpecRequirements) -> GeneratedApp:
        # 1. Retrieve patterns
        patterns = await self._retrieve_production_patterns(spec)

        # 2. Compose into modular app
        files = await self._compose_patterns(patterns, spec)

        # 3. Validate
        validation = await self._validate_production_readiness(files)

        return GeneratedApp(files=files, validation=validation)
```

**Deliverables**:
- [x] generate_production_app() method implemented
- [x] Pattern retrieval from PatternBank working
- [x] Pattern composition logic complete
- [x] Placeholder substitution ({APP_NAME}, {ENTITY_NAME}) working
- [x] Feature flag for production/legacy mode
- [x] Production readiness validation (80%+ test coverage, observability, Docker)

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

### Phase 1: Core Infrastructure ✅

- [x] Task Group 1: Database & Configuration (4/4 tasks)
- [x] Task Group 2: Modular Architecture (7/7 tasks)
- [x] Task Group 3: Observability Infrastructure (7/7 tasks)

**Progress**: 18/18 tasks (100%)

### Phase 2: Testing & Security ✅

- [x] Task Group 4: Test Suite Generation (7/7 tasks)
- [x] Task Group 5: Security Hardening (7/7 tasks)

**Progress**: 14/14 tasks (100%)

### Phase 3: Docker & CI/CD ✅

- [x] Task Group 6: Docker Infrastructure (6/6 tasks)
- [x] Task Group 7: CI/CD & Documentation (5/5 tasks)

**Progress**: 11/11 tasks (100%)

### Production Pattern Library ✅

- [x] Task Group 8: Production Pattern Library (10/10 tasks)

**Progress**: 10/10 tasks (100%)

---

## Overall Progress

**Total Tasks**: 53
**Completed**: 53
**In Progress**: 0
**Blocked**: 0
**Not Started**: 0

**Completion**: 100% ✅

**🎉 ALL TASK GROUPS COMPLETE!**

DevMatrix Production-Ready Code Generation implementation is fully complete with:
- ✅ Phase 1: Core Infrastructure (18/18 tasks)
- ✅ Phase 2: Testing & Security (14/14 tasks)
- ✅ Phase 3: Docker & CI/CD (11/11 tasks)
- ✅ Production Pattern Library (10/10 tasks)

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
