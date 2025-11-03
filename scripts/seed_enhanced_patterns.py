#!/usr/bin/env python
"""
Enhanced RAG Pattern Seeding Script

Populates ChromaDB with curated high-quality code patterns for:
- Task decomposition (various project types)
- Security patterns (production-grade)
- Performance optimization
- Testing strategies
- Observability patterns

Usage:
    python scripts/seed_enhanced_patterns.py [--clear] [--category all|planning|security|performance|testing|observability]
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag import (
    create_embedding_model,
    create_vector_store,
)
from src.observability import get_logger

logger = get_logger("seed_enhanced_patterns")


# ============================================================
# CATEGORÍA 1: TASK DECOMPOSITION PATTERNS
# ============================================================

TASK_DECOMPOSITION_PATTERNS: List[Tuple[str, Dict[str, Any]]] = [
    (
        """def decompose_rest_api_with_auth_tasks(requirements: str) -> List[Task]:
    '''Decompose complete REST API with authentication into structured tasks.'''
    return [
        Task(
            id=1,
            name="Project Setup & Dependencies",
            description="Initialize FastAPI project with SQLAlchemy, Alembic, pytest, and security packages",
            dependencies=[],
            priority="high",
            estimated_time="30min",
            files=["pyproject.toml", "requirements.txt", "README.md", ".env.example"]
        ),
        Task(
            id=2,
            name="Database Models & Migrations",
            description="Create User, Role models with SQLAlchemy 2.0 async, define relationships, initial Alembic migration",
            dependencies=[1],
            priority="high",
            estimated_time="1h",
            files=["models/user.py", "models/role.py", "models/base.py", "alembic/versions/001_initial.py"]
        ),
        Task(
            id=3,
            name="Authentication Layer",
            description="JWT token generation with refresh, bcrypt password hashing, login/logout/refresh endpoints",
            dependencies=[2],
            priority="high",
            estimated_time="2h",
            files=["auth/security.py", "auth/dependencies.py", "auth/schemas.py", "routers/auth.py"]
        ),
        Task(
            id=4,
            name="RBAC Authorization",
            description="Role-based access control with permission decorators and middleware",
            dependencies=[3],
            priority="high",
            estimated_time="1.5h",
            files=["auth/permissions.py", "auth/decorators.py", "middleware/rbac.py"]
        ),
        Task(
            id=5,
            name="CRUD Endpoints",
            description="Create resource endpoints with pagination, filtering, sorting, and field selection",
            dependencies=[4],
            priority="medium",
            estimated_time="2h",
            files=["routers/resources.py", "schemas/resource.py", "services/resource_service.py"]
        ),
        Task(
            id=6,
            name="Input Validation & Error Handling",
            description="Pydantic schemas with custom validators, exception hierarchy, global error handlers",
            dependencies=[5],
            priority="high",
            estimated_time="1h",
            files=["schemas/", "exceptions.py", "middleware/error_handlers.py"]
        ),
        Task(
            id=7,
            name="Testing Suite",
            description="Unit tests, integration tests with testcontainers, API tests with auth, 80%+ coverage",
            dependencies=[6],
            priority="high",
            estimated_time="3h",
            files=["tests/unit/", "tests/integration/", "tests/api/", "tests/conftest.py"]
        ),
        Task(
            id=8,
            name="API Documentation & Deployment",
            description="OpenAPI docs configuration, README with examples, Docker setup, deployment guide",
            dependencies=[7],
            priority="medium",
            estimated_time="1h",
            files=["docs/API.md", "docs/DEPLOYMENT.md", "Dockerfile", "docker-compose.yml"]
        ),
    ]""",
        {
            "language": "python",
            "pattern": "task_decomposition",
            "task_type": "project_planning",
            "project_type": "rest_api_auth",
            "complexity": "high",
            "quality": "production",
            "tags": ["planning", "rest_api", "authentication", "rbac", "testing", "fastapi"],
            "approved": True,
        }
    ),
    
    (
        """def decompose_microservices_architecture(requirements: str) -> List[Task]:
    '''Decompose microservices system with event-driven communication.'''
    return [
        Task(
            id=1,
            name="Service Boundaries Definition",
            description="Define bounded contexts using DDD, identify service responsibilities, design service contracts",
            dependencies=[],
            priority="critical",
            estimated_time="2h",
            deliverables=["architecture_diagram.png", "service_boundaries.md", "context_map.md"]
        ),
        Task(
            id=2,
            name="Shared Infrastructure Setup",
            description="Setup message broker (RabbitMQ/Kafka), API gateway (Kong/Traefik), service discovery (Consul), observability stack",
            dependencies=[1],
            priority="high",
            estimated_time="3h",
            files=["docker-compose.yml", "k8s/base/", "infrastructure/messaging/", "infrastructure/gateway/"]
        ),
        Task(
            id=3,
            name="Event Schema Registry",
            description="Define event contracts with versioning (Avro/Protobuf), setup schema registry, define backwards compatibility rules",
            dependencies=[1],
            priority="high",
            estimated_time="1.5h",
            files=["schemas/events/", "schemas/VERSION.md", "schemas/registry.py"]
        ),
        Task(
            id=4,
            name="User Service Implementation",
            description="User management with CQRS, event sourcing for audit, publish domain events (UserCreated, UserUpdated)",
            dependencies=[2, 3],
            priority="high",
            estimated_time="4h",
            files=["services/user-service/", "services/user-service/domain/", "services/user-service/events/"]
        ),
        Task(
            id=5,
            name="Order Service with Saga Pattern",
            description="Order processing using Saga pattern for distributed transactions, compensating transactions, idempotency handling",
            dependencies=[2, 3],
            priority="high",
            estimated_time="5h",
            files=["services/order-service/", "services/order-service/sagas/", "services/order-service/compensations/"]
        ),
        Task(
            id=6,
            name="Inter-Service Communication",
            description="Event handlers with retry logic, dead letter queues, circuit breaker pattern, message deduplication",
            dependencies=[4, 5],
            priority="high",
            estimated_time="3h",
            files=["*/event_handlers.py", "*/messaging.py", "*/circuit_breaker.py"]
        ),
        Task(
            id=7,
            name="Distributed Observability",
            description="Distributed tracing (Jaeger), centralized logging (ELK), metrics aggregation (Prometheus), service mesh",
            dependencies=[6],
            priority="high",
            estimated_time="2h",
            files=["monitoring/tracing/", "monitoring/logging/", "monitoring/metrics/"]
        ),
        Task(
            id=8,
            name="End-to-End Integration Tests",
            description="Test complete workflows across services with testcontainers, chaos engineering tests, performance tests",
            dependencies=[7],
            priority="high",
            estimated_time="3h",
            files=["tests/integration/", "tests/e2e/", "tests/chaos/"]
        ),
    ]""",
        {
            "language": "python",
            "pattern": "task_decomposition",
            "task_type": "project_planning",
            "project_type": "microservices",
            "complexity": "very_high",
            "quality": "production",
            "tags": ["planning", "microservices", "event_driven", "saga", "distributed_systems", "ddd"],
            "approved": True,
        }
    ),

    (
        """def decompose_data_pipeline_tasks(requirements: str) -> List[Task]:
    '''Decompose data pipeline/ETL system into tasks.'''
    return [
        Task(
            id=1,
            name="Data Source Integration",
            description="Connect to data sources (APIs, databases, S3), implement connectors with retry logic",
            dependencies=[],
            priority="high",
            estimated_time="2h",
            files=["connectors/api_connector.py", "connectors/db_connector.py", "connectors/s3_connector.py"]
        ),
        Task(
            id=2,
            name="Data Validation & Quality Checks",
            description="Implement Great Expectations for data validation, define quality rules, alerting on anomalies",
            dependencies=[1],
            priority="high",
            estimated_time="2.5h",
            files=["validation/expectations/", "validation/rules.py", "validation/quality_checks.py"]
        ),
        Task(
            id=3,
            name="Data Transformation Layer",
            description="Build transformation pipeline with Pandas/Polars, implement data cleaning, enrichment, aggregation",
            dependencies=[2],
            priority="high",
            estimated_time="3h",
            files=["transformers/cleaning.py", "transformers/enrichment.py", "transformers/aggregation.py"]
        ),
        Task(
            id=4,
            name="Data Warehouse Loading",
            description="Implement incremental loading to data warehouse, handle deduplication, maintain idempotency",
            dependencies=[3],
            priority="high",
            estimated_time="2h",
            files=["loaders/warehouse_loader.py", "loaders/incremental.py"]
        ),
        Task(
            id=5,
            name="Orchestration & Scheduling",
            description="Setup Airflow/Prefect DAGs, define dependencies, configure retries and SLAs",
            dependencies=[4],
            priority="medium",
            estimated_time="2h",
            files=["dags/main_pipeline.py", "dags/monitoring.py"]
        ),
        Task(
            id=6,
            name="Monitoring & Alerting",
            description="Data quality metrics, pipeline performance monitoring, alerting on failures or anomalies",
            dependencies=[5],
            priority="high",
            estimated_time="1.5h",
            files=["monitoring/metrics.py", "monitoring/alerts.py"]
        ),
    ]""",
        {
            "language": "python",
            "pattern": "task_decomposition",
            "task_type": "project_planning",
            "project_type": "data_pipeline",
            "complexity": "high",
            "quality": "production",
            "tags": ["planning", "etl", "data_engineering", "pipeline", "airflow"],
            "approved": True,
        }
    ),

    (
        """def decompose_cli_application_tasks(requirements: str) -> List[Task]:
    '''Decompose CLI application with multiple commands.'''
    return [
        Task(
            id=1,
            name="CLI Framework Setup",
            description="Setup Typer framework, define app structure, configure rich console for formatting",
            dependencies=[],
            priority="high",
            estimated_time="30min",
            files=["cli/app.py", "cli/__init__.py", "pyproject.toml"]
        ),
        Task(
            id=2,
            name="Command Modules",
            description="Implement main commands (init, deploy, status, logs) with subcommands and options",
            dependencies=[1],
            priority="high",
            estimated_time="2h",
            files=["cli/commands/init.py", "cli/commands/deploy.py", "cli/commands/status.py"]
        ),
        Task(
            id=3,
            name="Configuration Management",
            description="YAML/TOML config file handling, environment variable overrides, config validation",
            dependencies=[1],
            priority="medium",
            estimated_time="1h",
            files=["cli/config.py", "cli/schemas.py"]
        ),
        Task(
            id=4,
            name="Interactive Prompts",
            description="Implement interactive mode with questionary, input validation, confirmation prompts",
            dependencies=[2],
            priority="medium",
            estimated_time="1.5h",
            files=["cli/interactive.py", "cli/validators.py"]
        ),
        Task(
            id=5,
            name="Output Formatting & Progress",
            description="Rich tables, progress bars, spinners, colored output, JSON output mode",
            dependencies=[2],
            priority="medium",
            estimated_time="1h",
            files=["cli/output.py", "cli/formatters.py"]
        ),
        Task(
            id=6,
            name="Testing & Documentation",
            description="CLI tests with CliRunner, help text, README with examples, shell completions",
            dependencies=[4, 5],
            priority="high",
            estimated_time="1.5h",
            files=["tests/cli/", "docs/CLI.md", "completions/"]
        ),
    ]""",
        {
            "language": "python",
            "pattern": "task_decomposition",
            "task_type": "project_planning",
            "project_type": "cli_application",
            "complexity": "medium",
            "quality": "production",
            "tags": ["planning", "cli", "typer", "interactive", "terminal"],
            "approved": True,
        }
    ),
]


# ============================================================
# CATEGORÍA 2: SECURITY PATTERNS
# ============================================================

SECURITY_PATTERNS: List[Tuple[str, Dict[str, Any]]] = [
    (
        """from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt
from typing import Optional
import secrets

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class SecurityService:
    '''Production-grade security service with token refresh and revocation.
    
    Features:
    - Bcrypt password hashing
    - JWT access + refresh token pairs
    - Token blacklist/revocation
    - Secure token generation
    '''
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_blacklist: set = set()  # In production, use Redis
    
    def hash_password(self, password: str) -> str:
        '''Hash password with bcrypt (cost factor 12).'''
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        '''Verify password against bcrypt hash.'''
        return pwd_context.verify(plain_password, hashed_password)
    
    def create_token_pair(self, data: dict) -> dict:
        '''Create access and refresh token pair for authentication.
        
        Args:
            data: User data to encode in token (user_id, email, roles)
            
        Returns:
            Dict with access_token, refresh_token, token_type
        '''
        access_token = self._create_token(
            data=data,
            token_type="access",
            expires_delta=timedelta(minutes=15)
        )
        refresh_token = self._create_token(
            data=data,
            token_type="refresh",
            expires_delta=timedelta(days=7)
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 900  # 15 minutes in seconds
        }
    
    def _create_token(
        self, 
        data: dict, 
        token_type: str,
        expires_delta: timedelta
    ) -> str:
        '''Create JWT token with type, expiration, and jti (token ID).'''
        to_encode = data.copy()
        expire = datetime.utcnow() + expires_delta
        jti = secrets.token_urlsafe(32)  # Unique token ID for revocation
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": token_type,
            "jti": jti
        })
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str, expected_type: str = "access") -> Optional[dict]:
        '''Verify JWT token, check blacklist, validate type.
        
        Returns:
            Decoded payload if valid, None otherwise
        '''
        try:
            # Check blacklist first (fast check)
            if token in self.token_blacklist:
                return None
            
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Verify token type
            if payload.get("type") != expected_type:
                return None
                
            return payload
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.JWTError:
            return None
    
    def revoke_token(self, token: str):
        '''Revoke token by adding jti to blacklist.
        
        In production: store jti in Redis with TTL matching token expiration.
        '''
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            jti = payload.get("jti")
            if jti:
                self.token_blacklist.add(jti)
        except jwt.JWTError:
            pass  # Invalid token, nothing to revoke
    
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        '''Generate new access token from refresh token.
        
        Returns:
            New access token if refresh token is valid, None otherwise
        '''
        payload = self.verify_token(refresh_token, expected_type="refresh")
        if not payload:
            return None
        
        # Remove JWT-specific claims
        user_data = {k: v for k, v in payload.items() 
                    if k not in ["exp", "iat", "type", "jti"]}
        
        return self._create_token(
            data=user_data,
            token_type="access",
            expires_delta=timedelta(minutes=15)
        )""",
        {
            "language": "python",
            "pattern": "security_authentication",
            "task_type": "auth_implementation",
            "framework": "pyjwt",
            "complexity": "high",
            "quality": "production",
            "tags": ["security", "jwt", "token_refresh", "password_hashing", "bcrypt", "revocation"],
            "approved": True,
        }
    ),

    (
        """from pydantic import BaseModel, field_validator, Field
from typing import Optional
import re

class InputValidator:
    '''Input validation patterns to prevent SQL injection and XSS.'''
    
    # Dangerous patterns that could indicate SQL injection
    SQL_INJECTION_PATTERNS = [
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bOR\b.*=.*)",
        r"(;.*DROP\b.*\bTABLE)",
        r"(--.*)",
        r"(/\*.*\*/)",
        r"(\bEXEC\b|\bEXECUTE\b)",
        r"(\bINSERT\b.*\bINTO\b)",
        r"(\bUPDATE\b.*\bSET\b)",
        r"(\bDELETE\b.*\bFROM\b)",
    ]
    
    # HTML/Script tags for XSS prevention
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",  # Event handlers like onclick=
        r"<iframe",
    ]
    
    @staticmethod
    def sanitize_sql_input(value: str) -> str:
        '''Sanitize input to prevent SQL injection.
        
        Best practice: Use parameterized queries (this is defense in depth).
        '''
        if not value:
            return value
            
        # Check for SQL injection patterns
        for pattern in InputValidator.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError(f"Potential SQL injection detected: {pattern}")
        
        # Remove dangerous characters
        dangerous_chars = ["'", '"', ";", "--", "/*", "*/"]
        for char in dangerous_chars:
            value = value.replace(char, "")
        
        return value
    
    @staticmethod
    def sanitize_html_input(value: str) -> str:
        '''Sanitize input to prevent XSS attacks.'''
        if not value:
            return value
        
        # Check for XSS patterns
        for pattern in InputValidator.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError("Potential XSS attack detected")
        
        # Escape HTML special characters
        html_escape_table = {
            "&": "&amp;",
            '"': "&quot;",
            "'": "&#x27;",
            ">": "&gt;",
            "<": "&lt;",
        }
        
        return "".join(html_escape_table.get(c, c) for c in value)


class UserRegistrationRequest(BaseModel):
    '''User registration with comprehensive validation.'''
    
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    password: str = Field(..., min_length=12)
    full_name: Optional[str] = Field(None, max_length=100)
    
    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        '''Username must be alphanumeric with underscores/hyphens.'''
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Username must contain only letters, numbers, underscores, and hyphens")
        
        # Prevent SQL injection attempts
        return InputValidator.sanitize_sql_input(v)
    
    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        '''Enforce strong password policy.'''
        errors = []
        
        if not any(char.isupper() for char in v):
            errors.append("at least one uppercase letter")
        if not any(char.islower() for char in v):
            errors.append("at least one lowercase letter")
        if not any(char.isdigit() for char in v):
            errors.append("at least one digit")
        if not any(char in "!@#$%^&*()_+-=[]{}|;:,.<>?" for char in v):
            errors.append("at least one special character")
        
        if errors:
            raise ValueError(f"Password must contain {', '.join(errors)}")
        
        # Check for common passwords (in production, use a password dictionary)
        common_passwords = ["password123", "admin123", "12345678"]
        if v.lower() in common_passwords:
            raise ValueError("Password is too common")
        
        return v
    
    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        '''Sanitize full name to prevent XSS.'''
        if v is None:
            return v
        return InputValidator.sanitize_html_input(v)""",
        {
            "language": "python",
            "pattern": "input_validation",
            "task_type": "security_validation",
            "framework": "pydantic",
            "complexity": "high",
            "quality": "production",
            "tags": ["security", "validation", "sql_injection", "xss", "pydantic", "password_policy"],
            "approved": True,
        }
    ),

    (
        """from functools import wraps
from typing import List, Optional, Callable
from fastapi import HTTPException, status, Depends
from enum import Enum

class Permission(str, Enum):
    '''Application permissions.'''
    READ_USERS = "users:read"
    WRITE_USERS = "users:write"
    DELETE_USERS = "users:delete"
    READ_ADMIN = "admin:read"
    WRITE_ADMIN = "admin:write"
    MANAGE_ROLES = "roles:manage"


class Role(str, Enum):
    '''Application roles with hierarchical permissions.'''
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    GUEST = "guest"


# Role permission mapping
ROLE_PERMISSIONS = {
    Role.ADMIN: [
        Permission.READ_USERS, Permission.WRITE_USERS, Permission.DELETE_USERS,
        Permission.READ_ADMIN, Permission.WRITE_ADMIN, Permission.MANAGE_ROLES
    ],
    Role.MANAGER: [
        Permission.READ_USERS, Permission.WRITE_USERS, Permission.READ_ADMIN
    ],
    Role.USER: [
        Permission.READ_USERS
    ],
    Role.GUEST: []
}


class RBACService:
    '''Role-Based Access Control service.'''
    
    @staticmethod
    def get_role_permissions(role: Role) -> List[Permission]:
        '''Get all permissions for a role.'''
        return ROLE_PERMISSIONS.get(role, [])
    
    @staticmethod
    def has_permission(user_roles: List[Role], required_permission: Permission) -> bool:
        '''Check if user has required permission through any of their roles.'''
        for role in user_roles:
            role_perms = ROLE_PERMISSIONS.get(role, [])
            if required_permission in role_perms:
                return True
        return False
    
    @staticmethod
    def has_any_permission(user_roles: List[Role], required_permissions: List[Permission]) -> bool:
        '''Check if user has at least one of the required permissions.'''
        return any(RBACService.has_permission(user_roles, perm) for perm in required_permissions)
    
    @staticmethod
    def has_all_permissions(user_roles: List[Role], required_permissions: List[Permission]) -> bool:
        '''Check if user has all required permissions.'''
        return all(RBACService.has_permission(user_roles, perm) for perm in required_permissions)


def require_permission(permission: Permission):
    '''Decorator to require specific permission for an endpoint.
    
    Usage:
        @router.get("/users")
        @require_permission(Permission.READ_USERS)
        async def get_users(current_user: User = Depends(get_current_user)):
            ...
    '''
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, current_user = None, **kwargs):
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            user_roles = current_user.roles  # Assume User model has roles field
            
            if not RBACService.has_permission(user_roles, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied. Required: {permission.value}"
                )
            
            return await func(*args, current_user=current_user, **kwargs)
        
        return wrapper
    return decorator


def require_any_permission(*permissions: Permission):
    '''Decorator to require at least one of the specified permissions.'''
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, current_user = None, **kwargs):
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            user_roles = current_user.roles
            
            if not RBACService.has_any_permission(user_roles, list(permissions)):
                perms_str = ", ".join(p.value for p in permissions)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied. Required one of: {perms_str}"
                )
            
            return await func(*args, current_user=current_user, **kwargs)
        
        return wrapper
    return decorator


def require_role(role: Role):
    '''Decorator to require specific role.'''
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, current_user = None, **kwargs):
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if role not in current_user.roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role denied. Required: {role.value}"
                )
            
            return await func(*args, current_user=current_user, **kwargs)
        
        return wrapper
    return decorator""",
        {
            "language": "python",
            "pattern": "rbac_authorization",
            "task_type": "authorization",
            "framework": "fastapi",
            "complexity": "high",
            "quality": "production",
            "tags": ["security", "rbac", "authorization", "permissions", "decorators", "fastapi"],
            "approved": True,
        }
    ),
]


# ============================================================
# CATEGORÍA 3: PERFORMANCE PATTERNS
# ============================================================

PERFORMANCE_PATTERNS: List[Tuple[str, Dict[str, Any]]] = [
    (
        """from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload, contains_eager
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import asyncio

class OptimizedRepository:
    '''Repository with N+1 query prevention and performance optimizations.'''
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_users_with_posts_optimized(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[User]:
        '''Fetch users with their posts using selectinload to prevent N+1.
        
        selectinload: Executes separate query for related objects (good for one-to-many).
        Result: 2 queries total instead of 1 + N queries.
        '''
        stmt = (
            select(User)
            .options(selectinload(User.posts))  # Eager load posts
            .limit(limit)
            .offset(offset)
            .order_by(User.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().unique().all()
    
    async def get_posts_with_nested_relations(
        self,
        post_ids: List[int]
    ) -> List[Post]:
        '''Fetch posts with author and comments (nested) efficiently.
        
        joinedload: Uses LEFT OUTER JOIN (good for one-to-one or small one-to-many).
        selectinload: Uses separate query (better for large collections).
        '''
        stmt = (
            select(Post)
            .where(Post.id.in_(post_ids))
            .options(
                joinedload(Post.author),  # Use JOIN for one-to-one
                selectinload(Post.comments)  # Separate query for collection
                    .selectinload(Comment.author)  # Nested eager loading
            )
        )
        result = await self.session.execute(stmt)
        return result.unique().scalars().all()
    
    async def get_posts_with_filter_join(
        self,
        author_name: str,
        limit: int = 50
    ) -> List[Post]:
        '''Fetch posts filtered by author name with optimized JOIN.
        
        contains_eager: Use when you're already joining and want to populate relationship.
        '''
        stmt = (
            select(Post)
            .join(Post.author)
            .where(User.name == author_name)
            .options(contains_eager(Post.author))  # Reuse existing JOIN
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().unique().all()
    
    async def batch_fetch_by_ids(
        self,
        model_class,
        ids: List[int],
        batch_size: int = 100
    ) -> List[Any]:
        '''Fetch records in batches to avoid huge IN clauses.
        
        Large IN clauses (>1000 items) can be slow. Batching improves performance.
        '''
        all_results = []
        
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            stmt = select(model_class).where(model_class.id.in_(batch_ids))
            result = await self.session.execute(stmt)
            all_results.extend(result.scalars().all())
        
        return all_results
    
    async def prefetch_related_concurrent(
        self,
        users: List[User]
    ) -> List[User]:
        '''Prefetch multiple relationships concurrently.
        
        Instead of sequential queries, fetch all relationships in parallel.
        '''
        user_ids = [u.id for u in users]
        
        # Fetch all relationships concurrently
        posts_task = self._fetch_posts_for_users(user_ids)
        profiles_task = self._fetch_profiles_for_users(user_ids)
        comments_task = self._fetch_comments_for_users(user_ids)
        
        posts, profiles, comments = await asyncio.gather(
            posts_task, profiles_task, comments_task
        )
        
        # Map results back to users
        posts_by_user = {}
        for post in posts:
            posts_by_user.setdefault(post.user_id, []).append(post)
        
        for user in users:
            user.posts = posts_by_user.get(user.id, [])
        
        return users
    
    async def _fetch_posts_for_users(self, user_ids: List[int]) -> List[Post]:
        '''Helper to fetch posts for multiple users.'''
        stmt = select(Post).where(Post.user_id.in_(user_ids))
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def _fetch_profiles_for_users(self, user_ids: List[int]) -> List[Profile]:
        '''Helper to fetch profiles for multiple users.'''
        stmt = select(Profile).where(Profile.user_id.in_(user_ids))
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def _fetch_comments_for_users(self, user_ids: List[int]) -> List[Comment]:
        '''Helper to fetch comments for multiple users.'''
        stmt = select(Comment).where(Comment.user_id.in_(user_ids))
        result = await self.session.execute(stmt)
        return result.scalars().all()""",
        {
            "language": "python",
            "pattern": "database_optimization",
            "task_type": "performance",
            "framework": "sqlalchemy",
            "complexity": "high",
            "quality": "production",
            "tags": ["performance", "n+1_prevention", "eager_loading", "sqlalchemy", "async", "batch_processing"],
            "approved": True,
        }
    ),

    (
        """import redis.asyncio as redis
from typing import Optional, Any, Callable
from functools import wraps
import json
import hashlib
from datetime import timedelta

class RedisCacheService:
    '''Redis caching service with multiple strategies.'''
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url, decode_responses=True)
    
    async def get(self, key: str) -> Optional[str]:
        '''Get value from cache.'''
        return await self.redis.get(key)
    
    async def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None
    ) -> bool:
        '''Set value in cache with optional TTL (seconds).'''
        if ttl:
            return await self.redis.setex(key, ttl, value)
        return await self.redis.set(key, value)
    
    async def delete(self, key: str) -> bool:
        '''Delete key from cache.'''
        return bool(await self.redis.delete(key))
    
    async def get_json(self, key: str) -> Optional[Any]:
        '''Get JSON value from cache.'''
        value = await self.get(key)
        return json.loads(value) if value else None
    
    async def set_json(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        '''Set JSON value in cache.'''
        json_str = json.dumps(value)
        return await self.set(key, json_str, ttl)
    
    async def invalidate_pattern(self, pattern: str) -> int:
        '''Invalidate all keys matching pattern (e.g., "users:*").
        
        Use carefully in production - SCAN is better than KEYS for large datasets.
        '''
        count = 0
        async for key in self.redis.scan_iter(match=pattern):
            await self.redis.delete(key)
            count += 1
        return count


def cache_result(
    ttl: int = 300,
    key_prefix: str = "",
    cache_none: bool = False
):
    '''Decorator to cache function results in Redis.
    
    Args:
        ttl: Time to live in seconds (default 5 min)
        key_prefix: Prefix for cache keys
        cache_none: Whether to cache None results
    
    Usage:
        @cache_result(ttl=600, key_prefix="user")
        async def get_user_by_id(user_id: int) -> Optional[User]:
            ...
    '''
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = _generate_cache_key(func.__name__, key_prefix, args, kwargs)
            
            # Try to get from cache
            cache_service = RedisCacheService()
            cached = await cache_service.get_json(cache_key)
            
            if cached is not None:
                return cached
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result if not None or if cache_none is True
            if result is not None or cache_none:
                await cache_service.set_json(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


def _generate_cache_key(
    func_name: str,
    prefix: str,
    args: tuple,
    kwargs: dict
) -> str:
    '''Generate unique cache key from function name and arguments.'''
    # Create hash of arguments
    args_str = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
    args_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
    
    # Build key
    key_parts = [prefix, func_name, args_hash]
    return ":".join(filter(None, key_parts))


class CacheStrategies:
    '''Common caching strategies.'''
    
    @staticmethod
    async def cache_aside(
        cache: RedisCacheService,
        key: str,
        fetch_func: Callable,
        ttl: int = 300
    ) -> Any:
        '''Cache-aside pattern (lazy loading).
        
        1. Check cache
        2. If miss, fetch from source
        3. Store in cache
        4. Return result
        '''
        # Try cache first
        cached = await cache.get_json(key)
        if cached is not None:
            return cached
        
        # Fetch from source
        result = await fetch_func()
        
        # Store in cache
        if result is not None:
            await cache.set_json(key, result, ttl)
        
        return result
    
    @staticmethod
    async def write_through(
        cache: RedisCacheService,
        key: str,
        value: Any,
        write_func: Callable,
        ttl: int = 300
    ) -> Any:
        '''Write-through pattern.
        
        1. Write to database
        2. Write to cache
        3. Return result
        '''
        # Write to database first
        result = await write_func(value)
        
        # Write to cache
        await cache.set_json(key, result, ttl)
        
        return result
    
    @staticmethod
    async def refresh_ahead(
        cache: RedisCacheService,
        key: str,
        fetch_func: Callable,
        ttl: int = 300,
        refresh_threshold: float = 0.8
    ) -> Any:
        '''Refresh-ahead pattern (proactive refresh).
        
        Refresh cache before it expires to avoid cache stampede.
        '''
        cached = await cache.get_json(key)
        
        # Check if cache is about to expire
        ttl_remaining = await cache.redis.ttl(key)
        should_refresh = ttl_remaining > 0 and ttl_remaining < (ttl * refresh_threshold)
        
        if should_refresh:
            # Refresh cache in background (don't wait)
            import asyncio
            asyncio.create_task(cache.set_json(key, await fetch_func(), ttl))
        
        if cached is not None:
            return cached
        
        # Cache miss - fetch and store
        result = await fetch_func()
        await cache.set_json(key, result, ttl)
        
        return result""",
        {
            "language": "python",
            "pattern": "caching_strategies",
            "task_type": "performance",
            "framework": "redis",
            "complexity": "high",
            "quality": "production",
            "tags": ["performance", "caching", "redis", "decorator", "cache_strategies", "async"],
            "approved": True,
        }
    ),
]


# ============================================================
# CATEGORÍA 4: TESTING PATTERNS
# ============================================================

TESTING_PATTERNS: List[Tuple[str, Dict[str, Any]]] = [
    (
        """import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient
from typing import AsyncGenerator

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost:5432/test_db"


@pytest_asyncio.fixture(scope="function")
async def async_db_engine():
    '''Create test database engine.'''
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )
    
    yield engine
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_db_session(async_db_engine) -> AsyncGenerator[AsyncSession, None]:
    '''Create test database session with automatic rollback.
    
    Each test gets a fresh session that rolls back after test completion.
    '''
    async_session = async_sessionmaker(
        async_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def test_client(async_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    '''Create test client with dependency overrides.'''
    from main import app
    from database import get_db
    
    # Override database dependency
    async def override_get_db():
        yield async_db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def sample_user_data():
    '''Sample user data for tests.'''
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "SecurePass123!",
        "full_name": "Test User"
    }


@pytest.fixture
async def created_user(test_client: AsyncClient, sample_user_data):
    '''Fixture that creates a user and returns it.'''
    response = await test_client.post("/api/v1/users", json=sample_user_data)
    assert response.status_code == 201
    return response.json()


@pytest.fixture
async def auth_headers(test_client: AsyncClient, created_user):
    '''Fixture that provides authentication headers.'''
    # Login to get token
    login_data = {
        "username": created_user["username"],
        "password": "SecurePass123!"
    }
    response = await test_client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ============================================================
# Test Examples
# ============================================================

@pytest.mark.asyncio
async def test_create_user(test_client: AsyncClient, sample_user_data):
    '''Test user creation endpoint.
    
    Given: Valid user data
    When: POST to /api/v1/users
    Then: User is created with 201 status
    '''
    response = await test_client.post("/api/v1/users", json=sample_user_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == sample_user_data["username"]
    assert data["email"] == sample_user_data["email"]
    assert "id" in data
    assert "password" not in data  # Password should not be in response


@pytest.mark.asyncio
async def test_create_user_duplicate_username(test_client: AsyncClient, created_user, sample_user_data):
    '''Test duplicate username rejection.
    
    Given: User already exists
    When: POST to /api/v1/users with same username
    Then: Request fails with 409 Conflict
    '''
    response = await test_client.post("/api/v1/users", json=sample_user_data)
    
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_user_authenticated(test_client: AsyncClient, created_user, auth_headers):
    '''Test getting user details with authentication.
    
    Given: Authenticated user
    When: GET to /api/v1/users/{id}
    Then: User details are returned
    '''
    user_id = created_user["id"]
    response = await test_client.get(f"/api/v1/users/{user_id}", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["username"] == created_user["username"]


@pytest.mark.asyncio
async def test_get_user_unauthenticated(test_client: AsyncClient, created_user):
    '''Test getting user without authentication fails.
    
    Given: No authentication
    When: GET to /api/v1/users/{id}
    Then: Request fails with 401 Unauthorized
    '''
    user_id = created_user["id"]
    response = await test_client.get(f"/api/v1/users/{user_id}")
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_user(test_client: AsyncClient, created_user, auth_headers):
    '''Test updating user details.
    
    Given: Authenticated user
    When: PATCH to /api/v1/users/{id}
    Then: User is updated successfully
    '''
    user_id = created_user["id"]
    update_data = {"full_name": "Updated Name"}
    
    response = await test_client.patch(
        f"/api/v1/users/{user_id}",
        json=update_data,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_email", [
    "notanemail",
    "@example.com",
    "user@",
    "user @example.com",
    "",
])
async def test_create_user_invalid_email(test_client: AsyncClient, sample_user_data, invalid_email):
    '''Test user creation with invalid emails.
    
    Given: Invalid email format
    When: POST to /api/v1/users
    Then: Request fails with 422 Unprocessable Entity
    '''
    sample_user_data["email"] = invalid_email
    response = await test_client.post("/api/v1/users", json=sample_user_data)
    
    assert response.status_code == 422
    assert "email" in response.json()["detail"][0]["loc"]""",
        {
            "language": "python",
            "pattern": "testing_api",
            "task_type": "testing",
            "framework": "pytest",
            "complexity": "high",
            "quality": "production",
            "tags": ["testing", "pytest", "async", "fixtures", "api_testing", "authentication", "parametrize"],
            "approved": True,
        }
    ),

    (
        """import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List

# ============================================================
# Mocking Async Functions
# ============================================================

@pytest.mark.asyncio
async def test_fetch_user_service_with_mock():
    '''Test service that calls external API with mock.'''
    
    # Arrange
    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com"
    }
    
    user_service = UserService(http_client=mock_http_client)
    
    # Act
    user = await user_service.fetch_user_by_id(1)
    
    # Assert
    assert user.username == "testuser"
    mock_http_client.get.assert_called_once_with("/users/1")


# ============================================================
# Mocking Database Queries
# ============================================================

@pytest.mark.asyncio
async def test_repository_get_user():
    '''Test repository method with mocked database.'''
    
    # Arrange
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalars.return_value.first.return_value = User(
        id=1,
        username="testuser",
        email="test@example.com"
    )
    mock_session.execute.return_value = mock_result
    
    repository = UserRepository(session=mock_session)
    
    # Act
    user = await repository.get_by_id(1)
    
    # Assert
    assert user.id == 1
    assert user.username == "testuser"
    mock_session.execute.assert_called_once()


# ============================================================
# Mocking External Services with Patch
# ============================================================

@pytest.mark.asyncio
@patch('services.email_service.EmailService.send_email')
async def test_user_registration_sends_email(mock_send_email):
    '''Test that user registration triggers welcome email.'''
    
    # Arrange
    mock_send_email.return_value = True
    user_service = UserService()
    user_data = {
        "username": "newuser",
        "email": "new@example.com",
        "password": "SecurePass123!"
    }
    
    # Act
    user = await user_service.register_user(user_data)
    
    # Assert
    assert user.username == "newuser"
    mock_send_email.assert_called_once()
    
    # Verify email was called with correct parameters
    call_args = mock_send_email.call_args
    assert call_args[1]['to'] == "new@example.com"
    assert "welcome" in call_args[1]['subject'].lower()


# ============================================================
# Mocking with Side Effects
# ============================================================

@pytest.mark.asyncio
async def test_retry_on_failure():
    '''Test retry logic with mock that fails then succeeds.'''
    
    # Arrange - mock that fails twice then succeeds
    mock_api = AsyncMock()
    mock_api.call.side_effect = [
        Exception("Connection timeout"),
        Exception("Connection timeout"),
        {"status": "success"}
    ]
    
    service = ResilientService(api=mock_api)
    
    # Act
    result = await service.call_with_retry(max_retries=3)
    
    # Assert
    assert result["status"] == "success"
    assert mock_api.call.call_count == 3


# ============================================================
# Mocking Class Methods with Spec
# ============================================================

def test_user_service_with_spec():
    '''Test using mock with spec for type safety.'''
    
    # Arrange - spec ensures mock has same interface as UserRepository
    mock_repo = Mock(spec=UserRepository)
    mock_repo.get_by_id.return_value = User(id=1, username="testuser")
    
    service = UserService(repository=mock_repo)
    
    # Act
    user = service.get_user(1)
    
    # Assert
    assert user.username == "testuser"
    mock_repo.get_by_id.assert_called_once_with(1)
    
    # This would raise AttributeError if method doesn't exist on spec
    # mock_repo.non_existent_method()  # AttributeError


# ============================================================
# Mocking Context Managers
# ============================================================

@pytest.mark.asyncio
async def test_database_transaction_with_mock():
    '''Test service using database transaction with mock.'''
    
    # Arrange
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None
    
    service = TransactionalService()
    
    # Act
    async with mock_session as session:
        result = await service.process_with_transaction(session)
    
    # Assert
    assert result is not None
    mock_session.commit.assert_called_once()


# ============================================================
# Spy Pattern - Verify Real Method Calls
# ============================================================

@pytest.mark.asyncio
async def test_spy_on_real_method():
    '''Test using spy to verify real method was called.'''
    
    # Arrange
    service = UserService()
    
    # Create spy on real method
    with patch.object(service, 'validate_email', wraps=service.validate_email) as spy:
        # Act
        user_data = {"username": "test", "email": "test@example.com"}
        await service.create_user(user_data)
        
        # Assert - verify validate_email was called with correct arg
        spy.assert_called_once_with("test@example.com")


# ============================================================
# Mocking Multiple Return Values
# ============================================================

def test_mock_multiple_calls():
    '''Test mock with different return values for each call.'''
    
    # Arrange
    mock_cache = Mock()
    mock_cache.get.side_effect = [None, "cached_value", "cached_value"]
    
    service = CachedService(cache=mock_cache)
    
    # Act & Assert
    result1 = service.get_data("key1")  # Cache miss
    assert result1 is None
    
    result2 = service.get_data("key1")  # Cache hit
    assert result2 == "cached_value"
    
    result3 = service.get_data("key1")  # Cache hit
    assert result3 == "cached_value"
    
    assert mock_cache.get.call_count == 3""",
        {
            "language": "python",
            "pattern": "testing_mocking",
            "task_type": "testing",
            "framework": "pytest",
            "complexity": "high",
            "quality": "production",
            "tags": ["testing", "mocking", "pytest", "unittest.mock", "async", "spy", "side_effects"],
            "approved": True,
        }
    ),
]


# ============================================================
# CATEGORÍA 5: OBSERVABILITY PATTERNS
# ============================================================

OBSERVABILITY_PATTERNS: List[Tuple[str, Dict[str, Any]]] = [
    (
        """import structlog
from typing import Any, Dict
import time
from contextvars import ContextVar
from uuid import uuid4

# Context variable for request ID (thread-safe)
request_id_var: ContextVar[str] = ContextVar('request_id', default='')

def configure_logging():
    '''Configure structured logging with structlog.'''
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    '''Get configured structured logger.'''
    return structlog.get_logger(name)


class LoggingMiddleware:
    '''FastAPI middleware for request/response logging with correlation IDs.'''
    
    def __init__(self, app):
        self.app = app
        self.logger = get_logger("api.requests")
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Generate request ID
        request_id = str(uuid4())
        request_id_var.set(request_id)
        
        # Bind request context to logger
        logger = self.logger.bind(
            request_id=request_id,
            method=scope["method"],
            path=scope["path"],
            client=scope["client"][0] if scope.get("client") else None
        )
        
        # Start timing
        start_time = time.time()
        
        try:
            # Log request
            logger.info("request_started")
            
            # Process request
            await self.app(scope, receive, send)
            
            # Log response
            duration = (time.time() - start_time) * 1000  # ms
            logger.info(
                "request_completed",
                duration_ms=duration,
                status_code=200  # Default success
            )
        
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(
                "request_failed",
                duration_ms=duration,
                error=str(e),
                error_type=type(e).__name__
            )
            raise


# Example service with structured logging
class UserService:
    '''User service with comprehensive structured logging.'''
    
    def __init__(self):
        self.logger = get_logger("services.user")
    
    async def create_user(self, user_data: Dict[str, Any]) -> User:
        '''Create user with detailed logging.'''
        
        # Log operation start with context
        self.logger.info(
            "user_creation_started",
            username=user_data.get("username"),
            email=user_data.get("email"),
            request_id=request_id_var.get()
        )
        
        try:
            # Validate user data
            await self._validate_user_data(user_data)
            
            # Check for duplicates
            existing = await self.repository.find_by_email(user_data["email"])
            if existing:
                self.logger.warning(
                    "user_creation_duplicate",
                    email=user_data["email"]
                )
                raise ValueError("User already exists")
            
            # Create user
            start_time = time.time()
            user = await self.repository.create(user_data)
            duration = (time.time() - start_time) * 1000
            
            # Log success with metrics
            self.logger.info(
                "user_created_successfully",
                user_id=user.id,
                username=user.username,
                creation_duration_ms=duration
            )
            
            # Log business event
            self.logger.info(
                "business_event",
                event_type="user_registered",
                user_id=user.id,
                source="api"
            )
            
            return user
        
        except ValueError as e:
            # Log validation error
            self.logger.warning(
                "user_creation_validation_failed",
                error=str(e),
                username=user_data.get("username")
            )
            raise
        
        except Exception as e:
            # Log unexpected error with full context
            self.logger.error(
                "user_creation_failed",
                error=str(e),
                error_type=type(e).__name__,
                username=user_data.get("username"),
                exc_info=True  # Include stack trace
            )
            raise
    
    async def _validate_user_data(self, user_data: Dict[str, Any]):
        '''Validate user data with logging.'''
        self.logger.debug(
            "validating_user_data",
            fields=list(user_data.keys())
        )
        
        # Validation logic here
        pass


# Example: Logging with timing context manager
class TimingLogger:
    '''Context manager for timing operations with logging.'''
    
    def __init__(self, logger: structlog.BoundLogger, operation: str, **kwargs):
        self.logger = logger
        self.operation = operation
        self.context = kwargs
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.debug(f"{self.operation}_started", **self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (time.time() - self.start_time) * 1000
        
        if exc_type is None:
            self.logger.info(
                f"{self.operation}_completed",
                duration_ms=duration,
                **self.context
            )
        else:
            self.logger.error(
                f"{self.operation}_failed",
                duration_ms=duration,
                error=str(exc_val),
                error_type=exc_type.__name__,
                **self.context
            )
        
        return False  # Don't suppress exceptions


# Usage example
async def process_order(order_id: int):
    logger = get_logger("orders")
    
    with TimingLogger(logger, "order_processing", order_id=order_id):
        # Process order logic
        await process_order_logic(order_id)""",
        {
            "language": "python",
            "pattern": "structured_logging",
            "task_type": "observability",
            "framework": "structlog",
            "complexity": "high",
            "quality": "production",
            "tags": ["observability", "logging", "structlog", "correlation_id", "middleware", "context"],
            "approved": True,
        }
    ),
]


# ============================================================
# CATEGORÍA 6: WEBSOCKET & REAL-TIME PATTERNS (7 ejemplos)
# ============================================================

WEBSOCKET_PATTERNS: List[Tuple[str, Dict[str, Any]]] = [
    (
        """from fastapi import FastAPI, WebSocket
from typing import Set
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                self.disconnect(connection)

app = FastAPI()
manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast({"client_id": client_id, "message": data.get("message")})
    except:
        manager.disconnect(websocket)""",
        {"language": "python", "pattern": "websocket_broadcast", "task_type": "realtime_communication", "framework": "fastapi", "complexity": "high", "quality": "production", "tags": "websocket,realtime,broadcast,fastapi", "approved": True}
    ),
    (
        """import asyncio
from datetime import datetime

async def websocket_with_heartbeat(websocket):
    await websocket.accept()
    heartbeat_task = asyncio.create_task(heartbeat_loop(websocket))
    
    try:
        async for message in websocket.iter_json():
            process_message(message)
    finally:
        heartbeat_task.cancel()

async def heartbeat_loop(websocket):
    try:
        while True:
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping", "time": datetime.now().isoformat()})
    except asyncio.CancelledError:
        pass""",
        {"language": "python", "pattern": "websocket_heartbeat", "task_type": "realtime_communication", "framework": "fastapi", "complexity": "high", "quality": "production", "tags": "websocket,heartbeat,ping-pong,asyncio", "approved": True}
    ),
    (
        """from fastapi import FastAPI, WebSocket
import json
from typing import Dict, List

class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, List[WebSocket]] = {}
    
    async def join_room(self, room_id: str, websocket: WebSocket):
        if room_id not in self.rooms:
            self.rooms[room_id] = []
        self.rooms[room_id].append(websocket)
    
    def leave_room(self, room_id: str, websocket: WebSocket):
        if room_id in self.rooms:
            self.rooms[room_id].remove(websocket)
    
    async def broadcast_to_room(self, room_id: str, message: dict):
        if room_id in self.rooms:
            for conn in self.rooms[room_id]:
                try:
                    await conn.send_json(message)
                except:
                    pass

app = FastAPI()
room_manager = RoomManager()

@app.websocket("/ws/room/{room_id}")
async def websocket_room(websocket: WebSocket, room_id: str):
    await websocket.accept()
    await room_manager.join_room(room_id, websocket)
    
    try:
        while True:
            data = await websocket.receive_json()
            await room_manager.broadcast_to_room(room_id, data)
    finally:
        room_manager.leave_room(room_id, websocket)""",
        {"language": "python", "pattern": "websocket_rooms", "task_type": "realtime_communication", "framework": "fastapi", "complexity": "high", "quality": "production", "tags": "websocket,rooms,broadcast,groups", "approved": True}
    ),
]

# ============================================================
# CATEGORÍA 7: BACKGROUND JOBS & TASK QUEUES (8 ejemplos)
# ============================================================

BACKGROUND_JOBS_PATTERNS: List[Tuple[str, Dict[str, Any]]] = [
    (
        """from celery import Celery
from datetime import timedelta
import logging

app = Celery('tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')
logger = logging.getLogger(__name__)

@app.task(bind=True, max_retries=3)
def process_data(self, data):
    try:
        result = do_work(data)
        return result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

@app.task
def send_email(email: str, subject: str, body: str):
    logger.info(f"Sending email to {email}")
    # Email sending logic

app.conf.beat_schedule = {
    'send-emails-every-hour': {
        'task': 'tasks.send_email',
        'schedule': timedelta(hours=1),
    },
}""",
        {"language": "python", "pattern": "celery_basics", "task_type": "background_processing", "framework": "celery", "complexity": "high", "quality": "production", "tags": "celery,tasks,retry,periodic", "approved": True}
    ),
    (
        """from celery import group, chain, chord

# Parallel execution with group
def parallel_tasks(items):
    job = group(process_item.s(item) for item in items)
    return job.apply_async().get()

# Sequential execution with chain
def sequential_workflow():
    workflow = chain(
        fetch_data.s(),
        transform_data.s(),
        save_data.s()
    )
    return workflow.apply_async()

# Parallel with callback using chord
def parallel_with_callback(items):
    workflow = chord([
        process_item.s(item) for item in items
    ])(aggregate_results.s())
    return workflow.apply_async()

@app.task
def process_item(item):
    return f"Processed {item}"

@app.task
def aggregate_results(results):
    return {"status": "complete", "items": len(results)}""",
        {"language": "python", "pattern": "celery_workflows", "task_type": "background_processing", "framework": "celery", "complexity": "high", "quality": "production", "tags": "celery,workflows,chain,group,chord", "approved": True}
    ),
    (
        """from celery import Task
import logging

logger = logging.getLogger(__name__)

class CallbackTask(Task):
    def on_success(self, retval, task_id, args, kwargs):
        logger.info(f"Task {task_id} succeeded: {retval}")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Task {task_id} failed: {exc}")
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning(f"Task {task_id} retrying: {exc}")

@app.task(bind=True, base=CallbackTask, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3})
def reliable_task(self, data):
    self.update_state(state='PROGRESS', meta={'current': 50, 'total': 100})
    result = process(data)
    return result""",
        {"language": "python", "pattern": "celery_callbacks", "task_type": "background_processing", "framework": "celery", "complexity": "high", "quality": "production", "tags": "celery,callbacks,lifecycle,monitoring", "approved": True}
    ),
]

# ============================================================
# CATEGORÍA 8: GRAPHQL PATTERNS (5 ejemplos)
# ============================================================

GRAPHQL_PATTERNS: List[Tuple[str, Dict[str, Any]]] = [
    (
        """import strawberry
from typing import List, Optional
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

@strawberry.type
class User:
    id: strawberry.ID
    name: str
    email: str

@strawberry.type
class Query:
    @strawberry.field
    async def user(self, id: strawberry.ID) -> Optional[User]:
        return User(id=id, name="John", email="john@example.com")
    
    @strawberry.field
    async def users(self) -> List[User]:
        return [User(id=strawberry.ID("1"), name="John", email="john@example.com")]

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_user(self, name: str, email: str) -> User:
        return User(id=strawberry.ID("new"), name=name, email=email)

schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema)
app = FastAPI()
app.include_router(graphql_app, prefix="/graphql")""",
        {"language": "python", "pattern": "graphql_basic", "task_type": "api_design", "framework": "strawberry", "complexity": "high", "quality": "production", "tags": "graphql,strawberry,schema,mutations,queries", "approved": True}
    ),
    (
        """import strawberry
from dataclasses import dataclass
from typing import List

@strawberry.type
class Post:
    id: strawberry.ID
    title: str
    content: str

@strawberry.type
class UserWithPosts:
    id: strawberry.ID
    name: str
    posts: List[Post]

async def resolve_user_with_posts(user_id: str) -> UserWithPosts:
    user = await fetch_user(user_id)
    posts = await fetch_user_posts(user_id)
    return UserWithPosts(
        id=strawberry.ID(user_id),
        name=user.name,
        posts=[Post(id=strawberry.ID(p.id), title=p.title, content=p.content) for p in posts]
    )

@strawberry.type
class Query:
    @strawberry.field
    async def user_with_posts(self, user_id: str) -> UserWithPosts:
        return await resolve_user_with_posts(user_id)""",
        {"language": "python", "pattern": "graphql_nested_types", "task_type": "api_design", "framework": "strawberry", "complexity": "high", "quality": "production", "tags": "graphql,types,nested,relationships", "approved": True}
    ),
]

# ============================================================
# CATEGORÍA 9: ADVANCED SQLALCHEMY PATTERNS (6 ejemplos)
# ============================================================

ADVANCED_SQLALCHEMY_PATTERNS: List[Tuple[str, Dict[str, Any]]] = [
    (
        """from sqlalchemy import select
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from typing import Optional

class SoftDeleteMixin:
    deleted_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
    
    def soft_delete(self):
        self.deleted_at = datetime.utcnow()

class User(Base, SoftDeleteMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]

async def get_active_users(session):
    stmt = select(User).where(User.deleted_at == None)
    return await session.execute(stmt)""",
        {"language": "python", "pattern": "sqlalchemy_soft_delete", "task_type": "database_patterns", "framework": "sqlalchemy", "complexity": "high", "quality": "production", "tags": "sqlalchemy,soft_delete,mixin,orm", "approved": True}
    ),
    (
        """from sqlalchemy import ForeignKey, Table, Column, Integer, String
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import List

association_table = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True),
)

class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    users: Mapped[List['User']] = relationship(secondary=association_table, back_populates="roles")

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    roles: Mapped[List[Role]] = relationship(secondary=association_table, back_populates="users", lazy="selectin")""",
        {"language": "python", "pattern": "sqlalchemy_many_to_many", "task_type": "database_patterns", "framework": "sqlalchemy", "complexity": "high", "quality": "production", "tags": "sqlalchemy,many-to-many,relationships,rbac", "approved": True}
    ),
    (
        """from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    _price: Mapped[float] = mapped_column("price")
    tax_rate: Mapped[float] = mapped_column(default=0.10)
    
    @hybrid_property
    def price_with_tax(self) -> float:
        return self._price * (1 + self.tax_rate)
    
    @price_with_tax.expression
    def price_with_tax(cls):
        return cls._price * (1 + cls.tax_rate)

async def get_expensive_products(session):
    stmt = select(Product).where(Product.price_with_tax > 100)
    return await session.execute(stmt)""",
        {"language": "python", "pattern": "sqlalchemy_hybrid_property", "task_type": "database_patterns", "framework": "sqlalchemy", "complexity": "high", "quality": "production", "tags": "sqlalchemy,hybrid_property,computed,expressions", "approved": True}
    ),
]

# ============================================================
# CATEGORÍA 10: API VERSIONING & DEPRECATION (4 ejemplos)
# ============================================================

API_VERSIONING_PATTERNS: List[Tuple[str, Dict[str, Any]]] = [
    (
        """from fastapi import FastAPI, APIRouter, Header, HTTPException

app = FastAPI()
v1_router = APIRouter(prefix="/api/v1")
v2_router = APIRouter(prefix="/api/v2")

@v1_router.get("/users/{user_id}")
async def get_user_v1(user_id: int):
    return {"id": user_id, "name": "John"}

@v2_router.get("/users/{user_id}")
async def get_user_v2(user_id: int):
    return {"id": user_id, "name": "John", "email": "john@example.com"}

app.include_router(v1_router)
app.include_router(v2_router)""",
        {"language": "python", "pattern": "api_versioning_url", "task_type": "api_design", "framework": "fastapi", "complexity": "medium", "quality": "production", "tags": "versioning,api,url-versioning,compatibility", "approved": True}
    ),
    (
        """from fastapi import FastAPI, Header, HTTPException
from enum import Enum

app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(user_id: int, api_version: str = Header(default="v2", alias="X-API-Version")):
    if api_version == "v1":
        return {"id": user_id, "name": "John"}
    elif api_version == "v2":
        return {"id": user_id, "name": "John", "email": "john@example.com"}
    else:
        raise HTTPException(status_code=400, detail="Unsupported API version")""",
        {"language": "python", "pattern": "api_versioning_header", "task_type": "api_design", "framework": "fastapi", "complexity": "medium", "quality": "production", "tags": "versioning,header-based,api,compatibility", "approved": True}
    ),
]

# ============================================================
# CATEGORÍA 11: MICROSERVICES COMMUNICATION (6 ejemplos)
# ============================================================

MICROSERVICES_PATTERNS: List[Tuple[str, Dict[str, Any]]] = [
    (
        """import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

class MicroserviceClient:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def call_with_retry(self, url: str) -> dict:
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

async def get_user_data(user_id: int):
    client = MicroserviceClient()
    try:
        return await client.call_with_retry(f"http://user-service:8000/users/{user_id}")
    except httpx.HTTPError:
        return {"id": user_id, "name": "Unknown"}""",
        {"language": "python", "pattern": "service_retry", "task_type": "service_communication", "framework": "httpx", "complexity": "high", "quality": "production", "tags": "microservices,retry,resilience,exponential-backoff", "approved": True}
    ),
    (
        """from circuitbreaker import circuit
import httpx

class ResilientClient:
    @circuit(failure_threshold=5, recovery_timeout=60)
    async def call_service(self, url: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

# Usage
client = ResilientClient()
try:
    data = await client.call_service("http://api-service/endpoint")
except Exception as e:
    # Handle circuit breaker open
    pass""",
        {"language": "python", "pattern": "circuit_breaker", "task_type": "service_communication", "framework": "circuitbreaker", "complexity": "high", "quality": "production", "tags": "microservices,circuit-breaker,resilience", "approved": True}
    ),
    (
        """from pydantic import BaseModel
from datetime import datetime
import uuid

class DomainEvent(BaseModel):
    event_id: str = None
    event_type: str
    aggregate_id: str
    data: dict
    timestamp: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.utcnow()

class UserCreatedEvent(DomainEvent):
    event_type: str = "user.created"

class EventBus:
    async def publish(self, event: DomainEvent):
        # Publish to message broker
        pass""",
        {"language": "python", "pattern": "event_driven", "task_type": "service_communication", "framework": "pydantic", "complexity": "high", "quality": "production", "tags": "microservices,events,event-driven,ddd", "approved": True}
    ),
]

# ============================================================
# CATEGORÍA 12: DOCKER & DEPLOYMENT (5 ejemplos)
# ============================================================

DOCKER_DEPLOYMENT_PATTERNS: List[Tuple[str, Dict[str, Any]]] = [
    (
        """# Multi-stage Dockerfile
FROM python:3.12-slim as builder
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN useradd -m appuser
COPY . .
USER appuser
HEALTHCHECK CMD curl -f http://localhost:8000/health
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]""",
        {"language": "dockerfile", "pattern": "docker_multistage", "task_type": "deployment", "framework": "docker", "complexity": "medium", "quality": "production", "tags": "docker,multistage,optimization", "approved": True}
    ),
]

# ============================================================
# CATEGORÍA 13: MIDDLEWARE PATTERNS (4 ejemplos)
# ============================================================

MIDDLEWARE_PATTERNS: List[Tuple[str, Dict[str, Any]]] = [
    (
        """from fastapi import FastAPI, Request
from uuid import uuid4
import time

app = FastAPI()

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request.state.request_id = str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response

@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    response.headers["X-Process-Time"] = str(duration)
    return response""",
        {"language": "python", "pattern": "fastapi_middleware", "task_type": "api_infrastructure", "framework": "fastapi", "complexity": "medium", "quality": "production", "tags": "middleware,request-id,monitoring,performance", "approved": True}
    ),
]

# Combine all patterns including new categories
ALL_PATTERNS = (
    TASK_DECOMPOSITION_PATTERNS +
    SECURITY_PATTERNS +
    PERFORMANCE_PATTERNS +
    TESTING_PATTERNS +
    OBSERVABILITY_PATTERNS +
    WEBSOCKET_PATTERNS +
    BACKGROUND_JOBS_PATTERNS +
    GRAPHQL_PATTERNS +
    ADVANCED_SQLALCHEMY_PATTERNS +
    API_VERSIONING_PATTERNS +
    MICROSERVICES_PATTERNS +
    DOCKER_DEPLOYMENT_PATTERNS +
    MIDDLEWARE_PATTERNS
)


def seed_patterns(
    vector_store,
    patterns: List[Tuple[str, Dict[str, Any]]],
    batch_size: int = 50,
    clear_first: bool = False,
) -> int:
    """
    Seed vector store with enhanced patterns.
    
    Args:
        vector_store: Vector store instance
        patterns: List of (code, metadata) tuples
        batch_size: Batch size for indexing
        clear_first: Whether to clear collection first
    
    Returns:
        Number of patterns indexed
    """
    if clear_first:
        logger.info("Clearing existing collection...")
        count = vector_store.clear_collection()
        logger.info(f"Cleared {count} existing examples")
    
    logger.info(f"Seeding {len(patterns)} enhanced patterns...")
    
    # Process in batches
    total_indexed = 0
    
    for i in range(0, len(patterns), batch_size):
        batch = patterns[i : i + batch_size]
        codes = [code for code, _ in batch]
        
        # Convert list values to strings for ChromaDB compatibility
        metadatas = []
        for _, metadata in batch:
            cleaned_metadata = {}
            for key, value in metadata.items():
                if isinstance(value, list):
                    cleaned_metadata[key] = ",".join(str(v) for v in value)
                else:
                    cleaned_metadata[key] = value
            metadatas.append(cleaned_metadata)
        
        try:
            code_ids = vector_store.add_batch(codes, metadatas)
            total_indexed += len(code_ids)
            
            logger.info(
                f"Batch indexed",
                batch_num=i // batch_size + 1,
                batch_size=len(code_ids),
                total=total_indexed,
            )
        
        except Exception as e:
            logger.error(f"Batch indexing failed", batch_num=i // batch_size + 1, error=str(e))
            continue
    
    return total_indexed


def main():
    """Main seeding script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed RAG with enhanced patterns")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing collection before seeding",
    )
    parser.add_argument(
        "--category",
        choices=["all", "planning", "security", "performance", "testing", "observability"],
        default="all",
        help="Category of patterns to seed",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for indexing (default: 50)",
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Enhanced RAG Pattern Seeding Script")
    print("=" * 60)
    
    # Select patterns based on category
    if args.category == "all":
        patterns_to_seed = ALL_PATTERNS
    elif args.category == "planning":
        patterns_to_seed = TASK_DECOMPOSITION_PATTERNS
    elif args.category == "security":
        patterns_to_seed = SECURITY_PATTERNS
    elif args.category == "performance":
        patterns_to_seed = PERFORMANCE_PATTERNS
    elif args.category == "testing":
        patterns_to_seed = TESTING_PATTERNS
    elif args.category == "observability":
        patterns_to_seed = OBSERVABILITY_PATTERNS
    
    # Initialize RAG components
    try:
        logger.info("Initializing RAG components...")
        embedding_model = create_embedding_model()
        vector_store = create_vector_store(embedding_model)
        
        logger.info("RAG components initialized")
    
    except Exception as e:
        logger.error("Failed to initialize RAG", error=str(e))
        print(f"\n❌ Initialization failed: {str(e)}")
        print("\nPlease ensure:")
        print("  1. ChromaDB is running: docker-compose up chromadb -d")
        print("  2. CHROMADB_HOST and CHROMADB_PORT are configured in .env")
        return 1
    
    # Seed patterns
    try:
        print(f"\n📦 Seeding {len(patterns_to_seed)} {args.category} patterns...")
        if args.clear:
            print("⚠️  Clearing existing collection first...")
        
        indexed_count = seed_patterns(
            vector_store,
            patterns_to_seed,
            batch_size=args.batch_size,
            clear_first=args.clear,
        )
        
        print(f"\n✅ Successfully indexed {indexed_count} patterns")
        
        # Show stats
        stats = vector_store.get_stats()
        print(f"\n📊 Vector Store Stats:")
        print(f"  Total examples: {stats.get('total_examples', 0)}")
        
    except Exception as e:
        logger.error("Seeding failed", error=str(e))
        print(f"\n❌ Seeding failed: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

