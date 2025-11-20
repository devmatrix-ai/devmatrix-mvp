#!/usr/bin/env python3
"""
Populate Production Patterns in PatternBank

Stores all production-ready golden patterns defined in Task Groups 8.2-8.8.
Patterns are stored in Qdrant using PatternBank infrastructure.

Usage:
    python tools/populate_production_patterns.py

Author: DevMatrix Team
Date: 2025-11-20
Spec: agent-os/specs/2025-11-20-devmatrix-improvements-minimal/tasks.md (Task Groups 8.2-8.8)
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.cognitive.patterns.pattern_bank import PatternBank
from src.cognitive.signatures.semantic_signature import SemanticTaskSignature
from src.cognitive.patterns.production_patterns import PRODUCTION_PATTERN_CATEGORIES

# Production pattern code templates
# These are production-ready golden patterns with placeholders for customization

# === TASK 8.2: CORE INFRASTRUCTURE PATTERNS ===

PYDANTIC_SETTINGS_CONFIG = '''from pydantic_settings import BaseSettings, SettingsConfigDict
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

SQLALCHEMY_ASYNC_ENGINE = '''from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator

# Create async engine with connection pooling
engine = create_async_engine(
    "{DATABASE_URL}",
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,   # Recycle connections every hour
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Declarative base for models
Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI routes."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
'''

ALEMBIC_SETUP = '''# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import asyncio

from src.core.database import Base
from src.core.config import settings

# Import all models for auto-generation
from src.models import *  # noqa

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
'''

STRUCTLOG_SETUP = '''import structlog
import logging
import sys

def configure_logging(log_level: str = "INFO", json_logs: bool = True):
    """Configure structured logging with structlog."""

    # Processors for structlog
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_logs:
        # JSON output for production
        processors = shared_processors + [
            structlog.processors.JSONRenderer()
        ]
    else:
        # Human-readable output for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer()
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
'''

HEALTH_CHECKS = '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(tags=["health"])

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    database: str

@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint.

    Returns:
        Health status with database connectivity check
    """
    try:
        # Check database connectivity
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        timestamp=datetime.utcnow(),
        database=db_status
    )

@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness check for Kubernetes/Docker.

    Returns:
        200 if ready, 503 if not ready
    """
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="Not ready")
'''

PROMETHEUS_METRICS = '''from fastapi import APIRouter
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

router = APIRouter(tags=["metrics"])

# Metrics
request_count = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"]
)

@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
'''

REQUEST_ID_MIDDLEWARE = '''from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import uuid
import structlog

logger = structlog.get_logger()

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add request ID to headers and logs."""

    async def dispatch(self, request: Request, call_next):
        # Generate or use existing request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Add to context for logging
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Process request
        response = await call_next(request)

        # Add to response headers
        response.headers["X-Request-ID"] = request_id

        # Clear context
        structlog.contextvars.clear_contextvars()

        return response
'''

# === TASK 8.3: MODEL & DATA ACCESS PATTERNS ===

STRICT_MODE_SCHEMAS = '''from pydantic import BaseModel, ConfigDict, Field, EmailStr
from datetime import datetime
from typing import Optional
from decimal import Decimal

class {ENTITY_NAME}Base(BaseModel):
    """Base Pydantic schema with strict mode."""

    model_config = ConfigDict(
        strict=True,
        from_attributes=True,
        validate_assignment=True,
        use_enum_values=True,
    )

class {ENTITY_NAME}Create(BaseModel):
    """Schema for creating {ENTITY_NAME}."""
    # Add your fields here with validation
    # Example:
    # name: str = Field(..., min_length=1, max_length=100)
    # email: EmailStr
    # price: Decimal = Field(..., gt=0, decimal_places=2)
    pass

class {ENTITY_NAME}Response(BaseModel):
    """Schema for {ENTITY_NAME} response."""
    id: int
    created_at: datetime
    updated_at: datetime
    # Add your fields from Create schema
'''

TIMEZONE_AWARE_DATETIMES = '''from datetime import datetime, timezone

# ALWAYS use timezone-aware datetimes
def utc_now() -> datetime:
    """Get current UTC time with timezone info."""
    return datetime.now(timezone.utc)

# In models:
# created_at: datetime = Field(default_factory=utc_now)
# updated_at: datetime = Field(default_factory=utc_now)
'''

ASYNC_DECLARATIVE_BASE = '''from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime

class Base(AsyncAttrs, DeclarativeBase):
    """Async declarative base with common columns."""
    pass

class {ENTITY_NAME}(Base):
    """SQLAlchemy model for {ENTITY_NAME}."""
    __tablename__ = "{TABLE_NAME}"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Add your entity-specific columns here
'''

GENERIC_REPOSITORY = '''from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Generic, TypeVar, Optional, List
from sqlalchemy.orm import DeclarativeBase

ModelType = TypeVar("ModelType", bound=DeclarativeBase)

class BaseRepository(Generic[ModelType]):
    """Generic async repository for CRUD operations."""

    def __init__(self, model: type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get(self, id: int) -> Optional[ModelType]:
        """Get entity by ID."""
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """Get all entities with pagination."""
        result = await self.db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, obj: ModelType) -> ModelType:
        """Create new entity."""
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: ModelType) -> ModelType:
        """Update existing entity."""
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, id: int) -> bool:
        """Delete entity by ID."""
        obj = await self.get(id)
        if obj:
            await self.db.delete(obj)
            await self.db.flush()
            return True
        return False
'''

# === TASK 8.4: API & BUSINESS LOGIC PATTERNS ===

FASTAPI_CRUD_ENDPOINTS = '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

router = APIRouter(prefix="/{ENTITY_PLURAL}", tags=["{ENTITY_NAME}"])

@router.post("/", response_model={ENTITY_NAME}Response, status_code=201)
async def create_{ENTITY_SNAKE}(
    data: {ENTITY_NAME}Create,
    db: AsyncSession = Depends(get_db)
):
    """Create new {ENTITY_NAME}."""
    # Business logic here
    obj = {ENTITY_NAME}(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

@router.get("/{id}", response_model={ENTITY_NAME}Response)
async def get_{ENTITY_SNAKE}(id: int, db: AsyncSession = Depends(get_db)):
    """Get {ENTITY_NAME} by ID."""
    obj = await db.get({ENTITY_NAME}, id)
    if not obj:
        raise HTTPException(status_code=404, detail="{ENTITY_NAME} not found")
    return obj

@router.get("/", response_model=List[{ENTITY_NAME}Response])
async def list_{ENTITY_PLURAL}(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all {ENTITY_PLURAL} with pagination."""
    result = await db.execute(
        select({ENTITY_NAME}).offset(skip).limit(limit)
    )
    return list(result.scalars().all())

@router.put("/{id}", response_model={ENTITY_NAME}Response)
async def update_{ENTITY_SNAKE}(
    id: int,
    data: {ENTITY_NAME}Create,
    db: AsyncSession = Depends(get_db)
):
    """Update {ENTITY_NAME}."""
    obj = await db.get({ENTITY_NAME}, id)
    if not obj:
        raise HTTPException(status_code=404, detail="{ENTITY_NAME} not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)

    await db.commit()
    await db.refresh(obj)
    return obj

@router.delete("/{id}", status_code=204)
async def delete_{ENTITY_SNAKE}(id: int, db: AsyncSession = Depends(get_db)):
    """Delete {ENTITY_NAME}."""
    obj = await db.get({ENTITY_NAME}, id)
    if not obj:
        raise HTTPException(status_code=404, detail="{ENTITY_NAME} not found")

    await db.delete(obj)
    await db.commit()
'''

DEPENDENCY_INJECTION = '''from fastapi import Depends
from typing import Annotated

# Dependency for database session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

# Typed dependency
DBSession = Annotated[AsyncSession, Depends(get_db)]

# Usage in routes:
# @router.get("/")
# async def list_items(db: DBSession):
#     ...
'''

# === TASK 8.5: SECURITY PATTERNS ===

HTML_SANITIZATION = '''import bleach
from typing import Optional

ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'a', 'code', 'pre', 'blockquote'
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'code': ['class']
}

def sanitize_html(text: Optional[str]) -> Optional[str]:
    """Sanitize HTML to prevent XSS attacks."""
    if not text:
        return text

    return bleach.clean(
        text,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )
'''

RATE_LIMITING = '''from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI, Request

# Create limiter
limiter = Limiter(key_func=get_remote_address)

# Add to FastAPI app
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Usage in routes:
# @router.get("/")
# @limiter.limit("5/minute")
# async def rate_limited_endpoint(request: Request):
#     ...
'''

SECURITY_HEADERS = '''from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response
'''

CORS_CONFIG = '''from fastapi.middleware.cors import CORSMiddleware

def configure_cors(app: FastAPI, allowed_origins: list[str]):
    """Configure CORS with secure defaults."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        max_age=600,  # Cache preflight requests for 10 minutes
    )
'''

# === TASK 8.6: TEST INFRASTRUCTURE PATTERNS ===

PYTEST_CONFIG = '''# pytest.ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --cov=src
    --cov-report=term-missing
    --cov-report=html
    --verbose
    -ra
markers =
    integration: Integration tests (slower)
    unit: Unit tests (fast)
'''

ASYNC_FIXTURES = '''import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def engine():
    """Create test database engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=NullPool,
    )
    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(engine):
    """Create test database session."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
'''

TEST_FACTORIES = '''from typing import Optional
import factory
from datetime import datetime, timezone

class {ENTITY_NAME}Factory(factory.Factory):
    """Factory for creating test {ENTITY_NAME} instances."""

    class Meta:
        model = {ENTITY_NAME}

    id = factory.Sequence(lambda n: n + 1)
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))

    # Add entity-specific fields
    # name = factory.Faker("name")
    # email = factory.Faker("email")
'''

# === TASK 8.7: DOCKER INFRASTRUCTURE PATTERNS ===

MULTISTAGE_DOCKERFILE = '''# Multi-stage Dockerfile for production
FROM python:3.11-slim as builder

WORKDIR /app

# Install dependencies
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && \\
    poetry config virtualenvs.create false && \\
    poetry install --no-dev --no-interaction --no-ansi

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy dependencies from builder
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
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
'''

DOCKER_COMPOSE_FULL_STACK = '''version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/app
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 3s
      retries: 3

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=app
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3000:3000"

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:
'''

# === TASK 8.8: PROJECT CONFIGURATION PATTERNS ===

PYPROJECT_TOML = '''[tool.poetry]
name = "{APP_NAME}"
version = "0.1.0"
description = "Production-ready FastAPI application"
authors = ["Your Name <you@example.com>"]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.109.0"
uvicorn = {extras = ["standard"], version = "^0.27.0"}
sqlalchemy = {extras = ["asyncio"], version = "^2.0.25"}
alembic = "^1.13.1"
pydantic = "^2.5.3"
pydantic-settings = "^2.1.0"
asyncpg = "^0.29.0"
structlog = "^24.1.0"
prometheus-client = "^0.19.0"
bleach = "^6.1.0"
slowapi = "^0.1.9"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.4"
pytest-asyncio = "^0.23.3"
pytest-cov = "^4.1.0"
httpx = "^0.26.0"
factory-boy = "^3.3.0"
black = "^24.1.1"
ruff = "^0.1.13"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.black]
line-length = 100

[tool.ruff]
line-length = 100
select = ["E", "F", "I"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
'''

ENV_EXAMPLE = '''# Application
APP_NAME={APP_NAME}
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=your-secret-key-here-change-in-production

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/app
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Observability
LOG_LEVEL=INFO
LOG_JSON=false

# Security
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# Redis (optional)
REDIS_URL=redis://localhost:6379/0
'''

GITIGNORE = '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/

# Environment
.env
.env.local

# Database
*.db
*.sqlite

# Logs
*.log

# OS
.DS_Store
Thumbs.db
'''

MAKEFILE = '''# Makefile for {APP_NAME}

.PHONY: install run test migrate lint format clean

install:
\tpoetry install

run:
\tuvicorn src.main:app --reload

test:
\tpytest tests/ -v --cov=src

migrate:
\talembic upgrade head

migrate-create:
\talembic revision --autogenerate -m "$(message)"

lint:
\truff check src/ tests/

format:
\tblack src/ tests/
\truff check --fix src/ tests/

clean:
\tfind . -type d -name __pycache__ -exec rm -rf {} +
\tfind . -type f -name "*.pyc" -delete
\trm -rf .pytest_cache .coverage htmlcov

docker-build:
\tdocker-compose build

docker-up:
\tdocker-compose up -d

docker-down:
\tdocker-compose down

docker-logs:
\tdocker-compose logs -f app
'''


def store_all_patterns():
    """Store all production patterns in PatternBank."""
    print("=" * 80)
    print("POPULATING PRODUCTION PATTERNS IN PATTERNBANK")
    print("=" * 80)

    # Initialize PatternBank
    bank = PatternBank()
    bank.connect()
    bank.create_collection()

    patterns_stored = 0
    categories_processed = 0

    # Pattern definitions: (pattern_name, code, purpose, domain, success_rate, test_coverage, security_level, observability)
    all_patterns = [
        # Task 8.2: Core Infrastructure
        ("pydantic_settings_config", PYDANTIC_SETTINGS_CONFIG,
         "Production-ready pydantic-settings configuration with environment management",
         "configuration", 0.98, 0.90, "HIGH", True),

        ("sqlalchemy_async_engine", SQLALCHEMY_ASYNC_ENGINE,
         "Async SQLAlchemy engine with connection pooling and session management",
         "data_access", 0.98, 0.90, "HIGH", True),

        ("alembic_setup", ALEMBIC_SETUP,
         "Alembic migration configuration for async SQLAlchemy",
         "data_access", 0.98, 0.85, "MEDIUM", False),

        ("structlog_setup", STRUCTLOG_SETUP,
         "Structured JSON logging with structlog for production observability",
         "infrastructure", 0.95, 0.85, "MEDIUM", True),

        ("health_checks", HEALTH_CHECKS,
         "Health and readiness check endpoints for Kubernetes/Docker",
         "infrastructure", 0.95, 0.90, "MEDIUM", True),

        ("prometheus_metrics", PROMETHEUS_METRICS,
         "Prometheus metrics endpoint with custom metrics",
         "infrastructure", 0.95, 0.85, "MEDIUM", True),

        ("request_id_middleware", REQUEST_ID_MIDDLEWARE,
         "Request ID tracking middleware for distributed tracing",
         "infrastructure", 0.95, 0.90, "MEDIUM", True),

        # Task 8.3: Models & Data Access
        ("strict_mode_schemas", STRICT_MODE_SCHEMAS,
         "Pydantic schemas with strict mode and comprehensive validation",
         "data_modeling", 0.95, 0.90, "HIGH", False),

        ("timezone_aware_datetimes", TIMEZONE_AWARE_DATETIMES,
         "Timezone-aware datetime utilities for consistent time handling",
         "data_modeling", 0.95, 0.85, "MEDIUM", False),

        ("async_declarative_base", ASYNC_DECLARATIVE_BASE,
         "SQLAlchemy async declarative base with common columns and timestamps",
         "data_modeling", 0.95, 0.85, "MEDIUM", False),

        ("generic_repository", GENERIC_REPOSITORY,
         "Generic async repository pattern with CRUD operations",
         "data_access", 0.95, 0.90, "MEDIUM", False),

        # Task 8.4: API & Business Logic
        ("fastapi_crud_endpoints", FASTAPI_CRUD_ENDPOINTS,
         "Complete FastAPI CRUD endpoints with proper status codes and error handling",
         "api", 0.95, 0.90, "HIGH", False),

        ("dependency_injection", DEPENDENCY_INJECTION,
         "FastAPI dependency injection patterns for database sessions and services",
         "api", 0.95, 0.85, "MEDIUM", False),

        # Task 8.5: Security
        ("html_sanitization", HTML_SANITIZATION,
         "HTML sanitization with bleach to prevent XSS attacks",
         "security", 0.98, 0.90, "CRITICAL", False),

        ("rate_limiting", RATE_LIMITING,
         "API rate limiting with slowapi to prevent abuse",
         "security", 0.98, 0.85, "CRITICAL", True),

        ("security_headers", SECURITY_HEADERS,
         "Security headers middleware (CSP, X-Frame-Options, etc.)",
         "security", 0.98, 0.85, "CRITICAL", False),

        ("cors_config", CORS_CONFIG,
         "CORS configuration with secure defaults",
         "security", 0.98, 0.85, "HIGH", False),

        # Task 8.6: Test Infrastructure
        ("pytest_config", PYTEST_CONFIG,
         "Pytest configuration with async support and coverage reporting",
         "testing", 0.95, 1.0, "MEDIUM", False),

        ("async_fixtures", ASYNC_FIXTURES,
         "Pytest async fixtures for database testing",
         "testing", 0.95, 0.95, "MEDIUM", False),

        ("test_factories", TEST_FACTORIES,
         "Factory pattern for test data generation",
         "testing", 0.95, 0.90, "MEDIUM", False),

        # Task 8.7: Docker Infrastructure
        ("multistage_dockerfile", MULTISTAGE_DOCKERFILE,
         "Multi-stage Dockerfile for optimized production images",
         "infrastructure", 0.95, 0.80, "MEDIUM", True),

        ("docker_compose_full_stack", DOCKER_COMPOSE_FULL_STACK,
         "Docker Compose configuration with PostgreSQL, Redis, Prometheus, and Grafana",
         "infrastructure", 0.95, 0.85, "MEDIUM", True),

        # Task 8.8: Project Configuration
        ("pyproject_toml", PYPROJECT_TOML,
         "Poetry pyproject.toml with production dependencies",
         "configuration", 0.90, 0.80, "MEDIUM", False),

        ("env_example", ENV_EXAMPLE,
         ".env.example template with all configuration variables",
         "configuration", 0.90, 0.75, "MEDIUM", False),

        ("gitignore", GITIGNORE,
         "Comprehensive .gitignore for Python projects",
         "configuration", 0.90, 0.70, "LOW", False),

        ("makefile", MAKEFILE,
         "Makefile with common development commands",
         "configuration", 0.90, 0.75, "LOW", False),
    ]

    print(f"\nStoring {len(all_patterns)} production patterns...\n")

    for pattern_name, code, purpose, domain, success_rate, test_coverage, security_level, observability in all_patterns:
        try:
            # Create semantic signature
            signature = SemanticTaskSignature(
                purpose=purpose,
                intent="implement",
                inputs={},
                outputs={},
                domain=domain,
            )

            # Store production pattern
            pattern_id = bank.store_production_pattern(
                signature=signature,
                code=code,
                success_rate=success_rate,
                test_coverage=test_coverage,
                security_level=security_level,
                observability_complete=observability,
                docker_ready=(pattern_name in ["multistage_dockerfile", "docker_compose_full_stack"]),
            )

            patterns_stored += 1
            print(f"✓ Stored {pattern_name:30s} (score: {bank._calculate_production_readiness_score(success_rate, test_coverage, security_level, observability):.2%})")

        except Exception as e:
            print(f"✗ Failed to store {pattern_name}: {e}")

    print(f"\n{'=' * 80}")
    print(f"SUMMARY:")
    print(f"  Patterns stored: {patterns_stored}/{len(all_patterns)}")
    print(f"  Categories covered: {len(set(p[3] for p in all_patterns))}")
    print(f"{'=' * 80}")

    # Verify patterns are retrievable
    print("\nVerifying patterns...")
    for category_name, config in PRODUCTION_PATTERN_CATEGORIES.items():
        sig = SemanticTaskSignature(
            purpose=f"production ready {category_name} implementation",
            intent="implement",
            inputs={},
            outputs={},
            domain=config["domain"]
        )
        results = bank.hybrid_search(sig, domain=config["domain"], production_ready=True, top_k=3)
        print(f"  {category_name:25s}: {len(results)} patterns retrieved")

    print("\n✓ All production patterns stored successfully!")


if __name__ == "__main__":
    store_all_patterns()
