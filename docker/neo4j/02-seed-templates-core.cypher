// ============================================================================
// SEED TEMPLATES CORE - Backend Templates (FastAPI + DDD)
// ============================================================================
// Archivo: 02-seed-templates-core.cypher
// Propósito: Crear los ~40 templates core para FastAPI backend
// ============================================================================

// =============================================================================
// INFRASTRUCTURE TEMPLATES (5)
// =============================================================================

CREATE (:Template {
    id: "urn:template:backend:fastapi:main-app:1.0",
    name: "FastAPI Main Application",
    version: "1.0.0",
    category: "infrastructure",
    stack: "backend",
    language: "python",
    framework: "fastapi",
    complexity: "simple",
    description: "FastAPI application entry point with middleware setup",
    precision: 0.98,
    usage_count: 0,
    success_rate: 0.0,
    tags: ["fastapi", "infrastructure", "core"],
    parameters: ["app_name", "debug_mode"],
    created_at: datetime(),
    code: """
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"Starting {app.title}...")
    yield
    # Shutdown
    print(f"Shutting down {app.title}...")

app = FastAPI(
    title="{app_name}",
    description="Generated API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gzip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.get("/api/v1/health/live")
async def health():
    return {"status": "alive"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""
});

CREATE (:Template {
    id: "urn:template:backend:fastapi:settings:1.0",
    name: "FastAPI Settings & Config",
    version: "1.0.0",
    category: "infrastructure",
    stack: "backend",
    language: "python",
    framework: "fastapi",
    complexity: "simple",
    description: "Pydantic settings for configuration management",
    precision: 0.97,
    usage_count: 0,
    success_rate: 0.0,
    tags: ["fastapi", "config", "environment"],
    parameters: ["app_env"],
    created_at: datetime(),
    code: """
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App
    APP_NAME: str = "{app_name}"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "devmatrix"
    POSTGRES_USER: str = "devmatrix"
    POSTGRES_PASSWORD: str = "devmatrix"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
"""
});

CREATE (:Template {
    id: "urn:template:backend:database:sqlalchemy-setup:1.0",
    name: "SQLAlchemy Database Setup",
    version: "1.0.0",
    category: "database",
    stack: "backend",
    language: "python",
    framework: "sqlalchemy",
    complexity: "medium",
    description: "SQLAlchemy engine and session setup with asyncio support",
    precision: 0.96,
    usage_count: 0,
    success_rate: 0.0,
    tags: ["database", "sqlalchemy", "orm"],
    parameters: ["database_url"],
    created_at: datetime(),
    code: """
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

DATABASE_URL = "{database_url}"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
"""
});

// =============================================================================
// AUTHENTICATION TEMPLATES (4)
// =============================================================================

CREATE (:Template {
    id: "urn:template:backend:auth:jwt-service:1.0",
    name: "JWT Authentication Service",
    version: "1.0.0",
    category: "auth",
    stack: "backend",
    language: "python",
    framework: "fastapi",
    complexity: "medium",
    description: "JWT token creation and verification with refresh tokens",
    precision: 0.96,
    usage_count: 0,
    success_rate: 0.0,
    tags: ["auth", "jwt", "security"],
    parameters: ["secret_key", "algorithm"],
    created_at: datetime(),
    code: """
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from fastapi import HTTPException, status

SECRET_KEY = "{secret_key}"
ALGORITHM = "{algorithm}"

class AuthService:
    @staticmethod
    def create_access_token(user_id: str, expires_delta: Optional[timedelta] = None):
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(hours=24)

        to_encode = {"sub": user_id, "exp": expire}
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> str:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
            if user_id is None:
                raise HTTPException(status_code=401, detail="Invalid token")
            return user_id
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
"""
});

CREATE (:Template {
    id: "urn:template:backend:auth:password-hasher:1.0",
    name: "Password Hasher Service",
    version: "1.0.0",
    category: "auth",
    stack: "backend",
    language: "python",
    framework: "fastapi",
    complexity: "simple",
    description: "Password hashing and verification using bcrypt",
    precision: 0.98,
    usage_count: 0,
    success_rate: 0.0,
    tags: ["auth", "security", "password"],
    parameters: [],
    created_at: datetime(),
    code: """
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class PasswordService:
    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)
"""
});

// =============================================================================
// DDD DOMAIN TEMPLATES (5)
// =============================================================================

CREATE (:Template {
    id: "urn:template:backend:ddd:entity-base:1.0",
    name: "DDD Entity Base Class",
    version: "1.0.0",
    category: "domain",
    stack: "backend",
    language: "python",
    framework: "sqlalchemy",
    complexity: "medium",
    description: "Base SQLAlchemy model with DDD patterns (timestamps, soft delete)",
    precision: 0.95,
    usage_count: 0,
    success_rate: 0.0,
    tags: ["ddd", "entity", "sqlalchemy"],
    parameters: [],
    created_at: datetime(),
    code: """
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from src.core.database import Base

class TimestampedModel(Base):
    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    def soft_delete(self):
        self.is_deleted = True
        self.updated_at = datetime.utcnow()

    def restore(self):
        self.is_deleted = False
        self.updated_at = datetime.utcnow()
"""
});

CREATE (:Template {
    id: "urn:template:backend:ddd:repository:1.0",
    name: "DDD Repository Pattern",
    version: "1.0.0",
    category: "domain",
    stack: "backend",
    language: "python",
    framework: "sqlalchemy",
    complexity: "medium",
    description: "Generic repository pattern for data access abstraction",
    precision: 0.94,
    usage_count: 0,
    success_rate: 0.0,
    tags: ["ddd", "repository", "pattern"],
    parameters: ["model_name"],
    created_at: datetime(),
    code: """
from typing import Generic, TypeVar, Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar('T')

class Repository(Generic[T]):
    def __init__(self, session: AsyncSession, model: type):
        self.session = session
        self.model = model

    async def create(self, obj: T) -> T:
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def get_by_id(self, id: str) -> Optional[T]:
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all(self, skip: int = 0, limit: int = 10) -> List[T]:
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update(self, id: str, obj_in: dict) -> Optional[T]:
        obj = await self.get_by_id(id)
        if obj:
            for k, v in obj_in.items():
                setattr(obj, k, v)
            await self.session.flush()
        return obj

    async def delete(self, id: str) -> bool:
        obj = await self.get_by_id(id)
        if obj:
            await self.session.delete(obj)
            await self.session.flush()
            return True
        return False
"""
});

// =============================================================================
// API TEMPLATES (3)
// =============================================================================

CREATE (:Template {
    id: "urn:template:backend:api:crud-endpoints:1.0",
    name: "CRUD API Endpoints",
    version: "1.0.0",
    category: "backend",
    stack: "backend",
    language: "python",
    framework: "fastapi",
    complexity: "medium",
    description: "Generic CRUD endpoints (create, read, update, delete, list)",
    precision: 0.94,
    usage_count: 0,
    success_rate: 0.0,
    tags: ["api", "crud", "endpoints"],
    parameters: ["model_name", "entity_name"],
    created_at: datetime(),
    code: """
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/api/v1/{entity_name}", tags=["{entity_name}"])

class {model_name}Schema(BaseModel):
    pass

@router.post("", response_model={model_name}Schema)
async def create_{entity_name}(obj_in: {model_name}Schema, db: AsyncSession = Depends(get_db)):
    # Implementation
    pass

@router.get("/{id}", response_model={model_name}Schema)
async def get_{entity_name}(id: str, db: AsyncSession = Depends(get_db)):
    # Implementation
    pass

@router.get("", response_model=List[{model_name}Schema])
async def list_{entity_name}(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)):
    # Implementation
    pass

@router.put("/{id}", response_model={model_name}Schema)
async def update_{entity_name}(id: str, obj_in: {model_name}Schema, db: AsyncSession = Depends(get_db)):
    # Implementation
    pass

@router.delete("/{id}")
async def delete_{entity_name}(id: str, db: AsyncSession = Depends(get_db)):
    # Implementation
    pass
"""
});

// =============================================================================
// DOMAIN MODELS FOR MVP (3)
// =============================================================================

CREATE (:Template {
    id: "urn:template:domain:user-entity:1.0",
    name: "User Entity (DDD)",
    version: "1.0.0",
    category: "domain",
    stack: "backend",
    language: "python",
    framework: "sqlalchemy",
    complexity: "medium",
    description: "User entity with authentication fields",
    precision: 0.95,
    usage_count: 0,
    success_rate: 0.0,
    tags: ["entity", "user", "auth"],
    parameters: [],
    created_at: datetime(),
    code: """
from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from uuid import uuid4
from src.core.database import TimestampedModel

class User(TimestampedModel):
    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"
"""
});

CREATE (:Template {
    id: "urn:template:domain:task-entity:1.0",
    name: "Task Entity (DDD)",
    version: "1.0.0",
    category: "domain",
    stack: "backend",
    language: "python",
    framework: "sqlalchemy",
    complexity: "medium",
    description: "Task entity with status and priority",
    precision: 0.94,
    usage_count: 0,
    success_rate: 0.0,
    tags: ["entity", "task", "task-manager"],
    parameters: [],
    created_at: datetime(),
    code: """
from sqlalchemy import Column, String, Text, DateTime, Enum, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from uuid import uuid4
from enum import Enum as PyEnum
from src.core.database import TimestampedModel

class TaskStatus(str, PyEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"

class TaskPriority(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class Task(TimestampedModel):
    __tablename__ = "tasks"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(Enum(TaskStatus), default=TaskStatus.TODO, nullable=False)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False)
    due_date = Column(DateTime)
    progress = Column(Float, default=0.0)

    def __repr__(self):
        return f"<Task(id={self.id}, title={self.title}, status={self.status})>"
"""
});

// =============================================================================
// RELACIONES ENTRE TEMPLATES (Dependencies)
// =============================================================================

// JWT requiere Settings
MATCH (jwt:Template {id:"urn:template:backend:auth:jwt-service:1.0"}),
      (settings:Template {id:"urn:template:backend:fastapi:settings:1.0"})
CREATE (jwt)-[:REQUIRES {min_version:"1.0.0", reason:"Settings for secret key"}]->(settings);

// SQLAlchemy requiere Settings
MATCH (sqlalchemy:Template {id:"urn:template:backend:database:sqlalchemy-setup:1.0"}),
      (settings:Template {id:"urn:template:backend:fastapi:settings:1.0"})
CREATE (sqlalchemy)-[:REQUIRES {min_version:"1.0.0", reason:"Settings for database URL"}]->(settings);

// TimestampedModel requiere SQLAlchemy
MATCH (timestamped:Template {id:"urn:template:backend:ddd:entity-base:1.0"}),
      (sqlalchemy:Template {id:"urn:template:backend:database:sqlalchemy-setup:1.0"})
CREATE (timestamped)-[:REQUIRES {min_version:"1.0.0", reason:"Base class dependency"}]->(sqlalchemy);

// Repository requiere TimestampedModel
MATCH (repository:Template {id:"urn:template:backend:ddd:repository:1.0"}),
      (timestamped:Template {id:"urn:template:backend:ddd:entity-base:1.0"})
CREATE (repository)-[:IMPLEMENTS {pattern:"DDD Repository"}]->(timestamped);

// User entity requiere TimestampedModel
MATCH (user:Template {id:"urn:template:domain:user-entity:1.0"}),
      (timestamped:Template {id:"urn:template:backend:ddd:entity-base:1.0"})
CREATE (user)-[:EXTENDS]->(timestamped);

// Task entity requiere TimestampedModel
MATCH (task:Template {id:"urn:template:domain:task-entity:1.0"}),
      (timestamped:Template {id:"urn:template:backend:ddd:entity-base:1.0"})
CREATE (task)-[:EXTENDS]->(timestamped);

// CRUD Endpoints requiere JWT
MATCH (crud:Template {id:"urn:template:backend:api:crud-endpoints:1.0"}),
      (jwt:Template {id:"urn:template:backend:auth:jwt-service:1.0"})
CREATE (crud)-[:USES {reason:"Authentication for protected endpoints"}]->(jwt);

// =============================================================================
// FIN DEL SCRIPT
// ============================================================================
