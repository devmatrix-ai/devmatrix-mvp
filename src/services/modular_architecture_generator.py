"""
Modular Architecture Generator

Generates production-ready modular FastAPI architecture with:
- models/ (schemas.py, entities.py)
- repositories/ (repository pattern)
- services/ (business logic)
- api/routes/ (endpoints)
- core/ (config, database, dependencies)

Author: System Architect (Task Group 2: Modular Architecture)
Date: 2025-11-20
"""

from typing import Dict, List
from dataclasses import dataclass


@dataclass
class EntitySpec:
    """Entity specification extracted from requirements"""
    name: str
    fields: List[Dict]
    description: str = ""


class ModularArchitectureGenerator:
    """
    Generates modular FastAPI architecture from spec requirements.

    Implements Task Group 2: Modular Architecture (15 hours)
    - Task 2.1: Directory structure
    - Task 2.2: Pydantic schemas
    - Task 2.3: SQLAlchemy entities
    - Task 2.4: Repository pattern
    - Task 2.5: Service layer
    - Task 2.6: FastAPI dependencies
    - Task 2.7: Route handlers
    """

    def generate_modular_app(self, spec_requirements) -> Dict[str, str]:
        """
        Generate complete modular application structure.

        Args:
            spec_requirements: SpecRequirements object from parser

        Returns:
            Dict[file_path, file_content] for all generated files
        """
        files = {}

        # 1. Core infrastructure
        files["src/core/__init__.py"] = ""
        files["src/core/config.py"] = self._generate_config()
        files["src/core/database.py"] = self._generate_database()

        # 2. Models (schemas + entities)
        files["src/models/__init__.py"] = ""
        files["src/models/schemas.py"] = self._generate_schemas(spec_requirements)
        files["src/models/entities.py"] = self._generate_entities(spec_requirements)

        # 3. Repositories (data access)
        files["src/repositories/__init__.py"] = ""
        for entity in spec_requirements.entities:
            repo_file = f"src/repositories/{entity.snake_name}_repository.py"
            files[repo_file] = self._generate_repository(entity)

        # 4. Services (business logic)
        files["src/services/__init__.py"] = ""
        for entity in spec_requirements.entities:
            service_file = f"src/services/{entity.snake_name}_service.py"
            files[service_file] = self._generate_service(entity)

        # 5. API routes
        files["src/api/__init__.py"] = ""
        files["src/api/dependencies.py"] = self._generate_dependencies(spec_requirements)
        files["src/api/routes/__init__.py"] = ""
        for entity in spec_requirements.entities:
            route_file = f"src/api/routes/{entity.snake_name}.py"
            files[route_file] = self._generate_routes(entity, spec_requirements)

        # 6. Main application
        files["src/main.py"] = self._generate_main(spec_requirements)

        # 7. Configuration files
        files["requirements.txt"] = self._generate_requirements()
        files[".env.example"] = self._generate_env_example()
        files["README.md"] = self._generate_readme(spec_requirements)

        return files

    def _generate_config(self) -> str:
        """Generate src/core/config.py (Task 1.2)"""
        return '''"""
Application Configuration
Type-safe settings with pydantic-settings
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # Application
    app_name: str = "FastAPI Application"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://user:pass@localhost/db"
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # Logging
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
'''

    def _generate_database(self) -> str:
        """Generate src/core/database.py (Task 1.1)"""
        return '''"""
Database Configuration
Async SQLAlchemy setup with connection pooling
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from src.core.config import get_settings

settings = get_settings()

# Async engine with connection pooling
engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base for ORM models
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
'''

    def _generate_schemas(self, spec_requirements) -> str:
        """Generate src/models/schemas.py (Task 2.2)"""
        code_parts = [
            '"""',
            'Pydantic Schemas',
            'Request/Response models with validation',
            '"""',
            '',
            'from pydantic import BaseModel, Field, ConfigDict',
            'from uuid import UUID',
            'from datetime import datetime',
            'from typing import Optional, Literal',
            'from decimal import Decimal',
            '',
        ]

        for entity in spec_requirements.entities:
            # Base schema
            code_parts.append(f'class {entity.name}Base(BaseModel):')
            code_parts.append('    """Base schema with common fields"""')
            for field in entity.fields:
                if field.name not in ['id', 'created_at', 'updated_at']:
                    field_def = self._generate_pydantic_field(field)
                    code_parts.append(f'    {field_def}')
            code_parts.append('')

            # Create schema
            code_parts.append(f'class {entity.name}Create({entity.name}Base):')
            code_parts.append('    """Schema for creating entities"""')
            code_parts.append('    model_config = ConfigDict(strict=True)')
            code_parts.append('')

            # Update schema
            code_parts.append(f'class {entity.name}Update(BaseModel):')
            code_parts.append('    """Schema for updating entities (all fields optional)"""')
            code_parts.append('    model_config = ConfigDict(strict=True)')
            for field in entity.fields:
                if field.name not in ['id', 'created_at', 'updated_at']:
                    field_type = self._map_field_type(field.type)
                    # For enums in update schema
                    if hasattr(field, 'enum_values') and field.enum_values:
                        enum_str = ', '.join(f"'{v}'" for v in field.enum_values)
                        field_type = f"Literal[{enum_str}]"
                    code_parts.append(f'    {field.name}: Optional[{field_type}] = None')
            code_parts.append('')

            # Response schema
            code_parts.append(f'class {entity.name}({entity.name}Base):')
            code_parts.append('    """Schema for responses"""')
            code_parts.append('    id: UUID')
            code_parts.append('    created_at: datetime')
            code_parts.append('    updated_at: datetime')
            code_parts.append('    model_config = ConfigDict(from_attributes=True)')
            code_parts.append('')

        return '\n'.join(code_parts)
    
    def _generate_pydantic_field(self, field) -> str:
        """Generate Pydantic field with Field() and all validations"""
        field_type = self._map_field_type(field.type)
        
        # Handle enums
        if hasattr(field, 'enum_values') and field.enum_values:
            enum_str = ', '.join(f"'{v}'" for v in field.enum_values)
            field_type = f"Literal[{enum_str}]"
        
        # Handle Optional
        if not field.required:
            field_type = f"Optional[{field_type}]"
        
        # Build Field() arguments
        field_args = []
        
        # Required or default
        if field.required:
            field_args.append("...")
        elif field.default:
            # For enums and booleans, use the value directly
            if hasattr(field, 'enum_values') and field.enum_values:
                field_args.append(f"'{field.default}'")
            elif field.type.lower() == 'boolean':
                field_args.append(str(field.default))
            else:
                field_args.append(f"'{field.default}'")
        
        # Add constraints from field.constraints list
        for constraint in field.constraints:
            # constraint format: "gt=0", "min_length=1", "email_format"
            if '=' in constraint:
                field_args.append(constraint)
            elif constraint == 'email_format':
                # Add email pattern
                field_args.append("pattern=r'^[^@]+@[^@]+\\.[^@]+$'")
            elif constraint == 'uuid_format':
                # UUID pattern
                field_args.append("pattern='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'")
        
        # Add length constraints if present
        if hasattr(field, 'min_length') and field.min_length is not None:
            field_args.append(f"min_length={field.min_length}")
        if hasattr(field, 'max_length') and field.max_length is not None:
            field_args.append(f"max_length={field.max_length}")
        
        # Add pattern if present
        if hasattr(field, 'pattern') and field.pattern:
            field_args.append(f"pattern=r'{field.pattern}'")
        
        # Add description for metadata
        if field.description:
            # Escape quotes in description
            desc = field.description.replace("'", "\\'")
            field_args.append(f"description='{desc}'")
        elif hasattr(field, 'metadata') and field.metadata:
            # Generate description from metadata
            if 'read-only' in field.metadata or field.metadata.get('read-only'):
                field_args.append("description='Read-only field (auto-generated)'")
            elif 'auto-calculated' in field.metadata:
                pattern = field.metadata.get('auto-calculated', 'auto-calculated')
                field_args.append(f"description='Auto-calculated: {pattern}'")
            elif 'snapshot_at_add_time' in field.metadata:
                field_args.append("description='Snapshot at add time'")
            elif 'snapshot_at_order_time' in field.metadata:
                field_args.append("description='Snapshot at order time'")
            elif 'immutable' in field.metadata:
                field_args.append("description='Immutable after creation'")
        
        # Build final field definition
        if field_args:
            field_call = f"Field({', '.join(field_args)})"
            return f"{field.name}: {field_type} = {field_call}"
        else:
            # No Field() needed if no constraints
            if field.default:
                return f"{field.name}: {field_type} = {field.default}"
            else:
                return f"{field.name}: {field_type}"


    def _generate_entities(self, spec_requirements) -> str:
        """Generate src/models/entities.py (Task 2.3)"""
        code_parts = [
            '"""',
            'SQLAlchemy Entities',
            'Database models with relationships',
            '"""',
            '',
            'from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, Float, ForeignKey, Enum',
            'from sqlalchemy.dialects.postgresql import UUID',
            'from sqlalchemy.orm import relationship',
            'from datetime import datetime, timezone',
            'from decimal import Decimal',
            'import uuid',
            'from src.core.database import Base',
            '',
        ]

        for entity in spec_requirements.entities:
            code_parts.append(f'class {entity.name}Entity(Base):')
            code_parts.append(f'    """SQLAlchemy model for {entity.snake_name} table"""')
            code_parts.append(f'    __tablename__ = "{entity.snake_name}"')
            code_parts.append('')
            code_parts.append('    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)')

            for field in entity.fields:
                if field.name not in ['id', 'created_at', 'updated_at']:
                    col_def = self._generate_sqlalchemy_column(field, entity.name)
                    code_parts.append(f'    {col_def}')

            code_parts.append('    created_at = Column(')
            code_parts.append('        DateTime(timezone=True),')
            code_parts.append('        nullable=False,')
            code_parts.append('        default=lambda: datetime.now(timezone.utc)')
            code_parts.append('    )')
            code_parts.append('    updated_at = Column(')
            code_parts.append('        DateTime(timezone=True),')
            code_parts.append('        nullable=False,')
            code_parts.append('        default=lambda: datetime.now(timezone.utc),')
            code_parts.append('        onupdate=lambda: datetime.now(timezone.utc)')
            code_parts.append('    )')
            code_parts.append('')
            code_parts.append(f'    def __repr__(self):')
            code_parts.append(f'        return f"<{entity.name} {{self.id}}>"')
            code_parts.append('')

        return '\n'.join(code_parts)
    
    def _generate_sqlalchemy_column(self, field, entity_name: str) -> str:
        """Generate SQLAlchemy Column with all constraints and metadata"""
        col_type = self._map_sqlalchemy_type(field.type)
        col_parts = []
        
        # Handle foreign keys
        if hasattr(field, 'foreign_key') and field.foreign_key:
            # Extract table name from foreign_key (e.g., "Customer.id" -> "customers")
            target_entity = field.foreign_key.split('.')[0]
            table_name = self._entity_to_table_name(target_entity)
            col_parts.append(f"ForeignKey('{table_name}.id')")
        
        # Column type
        col_parts.append(col_type)
        
        # Nullable
        nullable = not field.required
        col_parts.append(f"nullable={nullable}")
        
        # Unique
        if field.unique:
            col_parts.append("unique=True")
        
        # Index
        if field.unique or field.name in ['title', 'name', 'email']:
            col_parts.append("index=True")
        
        # Default value from field.default
        if field.default is not None and not hasattr(field, 'metadata'):
            # Simple defaults handling
            if field.type.lower() == 'boolean':
                col_parts.append(f"default={field.default}")
            elif hasattr(field, 'enum_values') and field.enum_values:
                col_parts.append(f"default='{field.default}'")
            else:
                col_parts.append(f"default='{field.default}'")
        
        # Process constraints and metadata for validation flags
        info_dict = {}
        # Constraints list
        for constraint in getattr(field, 'constraints', []):
            if constraint in {'read-only', 'read_only'}:
                info_dict['read_only'] = True
            elif constraint in {'auto-calculated', 'auto_calculated'}:
                info_dict['auto_calculated'] = True
            elif constraint == 'snapshot_at_add_time':
                info_dict['snapshot_at_add_time'] = True
            elif constraint == 'snapshot_at_order_time':
                info_dict['snapshot_at_order_time'] = True
            elif constraint == 'immutable':
                info_dict['immutable'] = True
            # Default handling
            elif constraint == 'default_true':
                col_parts.append('default=True')
            elif constraint == 'default_false':
                col_parts.append('default=False')
            elif constraint.startswith('default_'):
                val = constraint.split('default_', 1)[1]
                col_parts.append(f"default='{val}'")
        # Description / metadata fields
        if field.description:
            desc = field.description.lower()
            if 'read-only' in desc:
                info_dict['read_only'] = True
            if 'auto-calculated' in desc:
                info_dict['auto_calculated'] = True
            if 'snapshot' in desc:
                if 'add time' in desc:
                    info_dict['snapshot_at_add_time'] = True
                elif 'order time' in desc:
                    info_dict['snapshot_at_order_time'] = True
            if 'immutable' in desc:
                info_dict['immutable'] = True
        elif hasattr(field, 'metadata') and field.metadata:
            for key, value in field.metadata.items():
                if key == 'read-only':
                    info_dict['read_only'] = True
                elif key == 'auto-calculated':
                    info_dict['auto_calculated'] = True
                elif key == 'snapshot_at_add_time':
                    info_dict['snapshot_at_add_time'] = True
                elif key == 'snapshot_at_order_time':
                    info_dict['snapshot_at_order_time'] = True
                elif key == 'immutable':
                    info_dict['immutable'] = True
                elif key == 'default' and field.default is None:
                    if field.type.lower() == 'boolean':
                        col_parts.append(f"default={value}")
                    else:
                        col_parts.append(f"default='{value}'")
                elif key == 'description':
                    info_dict['description'] = value
        # Append info dict if any flags set
        if info_dict:
            col_parts.append(f"info={info_dict}")
        # Build column definition
        column_call = f"Column({', '.join(col_parts)})"
        return f"{field.name} = {column_call}"
    
    def _entity_to_table_name(self, entity_name: str) -> str:
        """Convert entity name to table name (snake_case plural)"""
        # Simple conversion: CamelCase -> snake_case
        import re
        snake = re.sub('([A-Z]+)([A-Z][a-z])', r'\1_\2', entity_name)
        snake = re.sub('([a-z\d])([A-Z])', r'\1_\2', snake)
        snake = snake.lower()
        
        # Simple pluralization
        if snake.endswith('y'):
            return snake[:-1] + 'ies'
        elif snake.endswith('s'):
            return snake + 'es'
        else:
            return snake + 's'


    def _generate_repository(self, entity) -> str:
        """Generate repository for entity (Task 2.4)"""
        entity_name = entity.name
        entity_snake = entity.snake_name

        return f'''"""
{entity_name} Repository
Data access layer for {entity_snake} operations
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import Optional, List
from src.models.entities import {entity_name}Entity
from src.models.schemas import {entity_name}Create, {entity_name}Update


class {entity_name}Repository:
    """Data access layer for {entity_snake}"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: {entity_name}Create) -> {entity_name}Entity:
        """Create new {entity_snake}"""
        entity = {entity_name}Entity(**data.model_dump())
        self.db.add(entity)
        await self.db.flush()
        await self.db.refresh(entity)
        return entity

    async def get(self, id: UUID) -> Optional[{entity_name}Entity]:
        """Get {entity_snake} by ID"""
        result = await self.db.execute(
            select({entity_name}Entity).where({entity_name}Entity.id == id)
        )
        return result.scalar_one_or_none()

    async def list(self, skip: int = 0, limit: int = 100) -> List[{entity_name}Entity]:
        """List {entity_snake} with pagination"""
        result = await self.db.execute(
            select({entity_name}Entity).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def update(self, id: UUID, data: {entity_name}Update) -> Optional[{entity_name}Entity]:
        """Update {entity_snake}"""
        entity = await self.get(id)
        if not entity:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(entity, key, value)

        await self.db.flush()
        await self.db.refresh(entity)
        return entity

    async def delete(self, id: UUID) -> bool:
        """Delete {entity_snake}"""
        entity = await self.get(id)
        if not entity:
            return False

        await self.db.delete(entity)
        return True
'''

    def _generate_service(self, entity) -> str:
        """Generate service for entity (Task 2.5)"""
        entity_name = entity.name
        entity_snake = entity.snake_name

        return f'''"""
{entity_name} Service
Business logic for {entity_snake} operations
"""

from uuid import UUID
from typing import Optional, List
from src.repositories.{entity_snake}_repository import {entity_name}Repository
from src.models.schemas import {entity_name}Create, {entity_name}Update, {entity_name}
from src.models.entities import {entity_name}Entity


class {entity_name}Service:
    """Business logic for {entity_snake}"""

    def __init__(self, repository: {entity_name}Repository):
        self.repo = repository

    async def create(self, data: {entity_name}Create) -> {entity_name}:
        """Create new {entity_snake} with business validation"""
        entity = await self.repo.create(data)
        return {entity_name}.model_validate(entity)

    async def get(self, id: UUID) -> Optional[{entity_name}]:
        """Get {entity_snake} by ID"""
        entity = await self.repo.get(id)
        if not entity:
            return None
        return {entity_name}.model_validate(entity)

    async def list(self, page: int = 1, size: int = 10) -> dict:
        """List {entity_snake} with pagination"""
        skip = (page - 1) * size
        entities = await self.repo.list(skip=skip, limit=size)

        return {{
            "items": [{entity_name}.model_validate(e) for e in entities],
            "total": len(entities),
            "page": page,
            "size": size
        }}

    async def update(self, id: UUID, data: {entity_name}Update) -> Optional[{entity_name}]:
        """Update {entity_snake}"""
        entity = await self.repo.update(id, data)
        if not entity:
            return None
        return {entity_name}.model_validate(entity)

    async def delete(self, id: UUID) -> bool:
        """Delete {entity_snake}"""
        return await self.repo.delete(id)
'''

    def _generate_dependencies(self, spec_requirements) -> str:
        """Generate src/api/dependencies.py (Task 2.6)"""
        code_parts = [
            '"""',
            'FastAPI Dependencies',
            'Dependency injection for repositories and services',
            '"""',
            '',
            'from fastapi import Depends',
            'from sqlalchemy.ext.asyncio import AsyncSession',
            'from src.core.database import get_db',
        ]

        # Import repositories
        for entity in spec_requirements.entities:
            code_parts.append(
                f'from src.repositories.{entity.snake_name}_repository import {entity.name}Repository'
            )

        # Import services
        for entity in spec_requirements.entities:
            code_parts.append(
                f'from src.services.{entity.snake_name}_service import {entity.name}Service'
            )

        code_parts.append('')

        # Repository dependencies
        for entity in spec_requirements.entities:
            code_parts.append(f'def get_{entity.snake_name}_repository(db: AsyncSession = Depends(get_db)) -> {entity.name}Repository:')
            code_parts.append(f'    """Get {entity.snake_name} repository dependency"""')
            code_parts.append(f'    return {entity.name}Repository(db)')
            code_parts.append('')

        # Service dependencies
        for entity in spec_requirements.entities:
            code_parts.append(f'def get_{entity.snake_name}_service(')
            code_parts.append(f'    repository: {entity.name}Repository = Depends(get_{entity.snake_name}_repository)')
            code_parts.append(f') -> {entity.name}Service:')
            code_parts.append(f'    """Get {entity.snake_name} service dependency"""')
            code_parts.append(f'    return {entity.name}Service(repository)')
            code_parts.append('')

        return '\n'.join(code_parts)

    def _generate_routes(self, entity, spec_requirements) -> str:
        """Generate routes for entity (Task 2.7)"""
        entity_name = entity.name
        entity_snake = entity.snake_name

        # Find endpoints for this entity
        entity_endpoints = [ep for ep in spec_requirements.endpoints if ep.entity == entity_name]

        code_parts = [
            f'"""',
            f'{entity_name} Routes',
            f'API endpoints for {entity_snake} operations',
            f'"""',
            '',
            'from fastapi import APIRouter, Depends, HTTPException, status',
            'from uuid import UUID',
            f'from src.services.{entity_snake}_service import {entity_name}Service',
            f'from src.api.dependencies import get_{entity_snake}_service',
            f'from src.models.schemas import {entity_name}, {entity_name}Create, {entity_name}Update',
            '',
            f'router = APIRouter(prefix="/api/v1/{entity_snake}", tags=["{entity_snake}"])',
            '',
        ]

        # Generate endpoints based on spec
        for endpoint in entity_endpoints:
            if endpoint.operation == 'create':
                code_parts.extend([
                    '@router.post("/", response_model=' + entity_name + ', status_code=status.HTTP_201_CREATED)',
                    f'async def create_{entity_snake}(',
                    f'    data: {entity_name}Create,',
                    f'    service: {entity_name}Service = Depends(get_{entity_snake}_service)',
                    f'):',
                    f'    """Create new {entity_snake}"""',
                    '    return await service.create(data)',
                    '',
                ])

            elif endpoint.operation == 'read':
                code_parts.extend([
                    '@router.get("/{id}", response_model=' + entity_name + ')',
                    f'async def get_{entity_snake}(',
                    '    id: UUID,',
                    f'    service: {entity_name}Service = Depends(get_{entity_snake}_service)',
                    f'):',
                    f'    """Get {entity_snake} by ID"""',
                    '    result = await service.get(id)',
                    '    if not result:',
                    f'        raise HTTPException(status_code=404, detail="{entity_name} not found")',
                    '    return result',
                    '',
                ])

            elif endpoint.operation == 'list':
                code_parts.extend([
                    '@router.get("/", response_model=dict)',
                    f'async def list_{entity_snake}(',
                    '    page: int = 1,',
                    '    size: int = 10,',
                    f'    service: {entity_name}Service = Depends(get_{entity_snake}_service)',
                    f'):',
                    f'    """List {entity_snake} with pagination"""',
                    '    return await service.list(page, size)',
                    '',
                ])

            elif endpoint.operation == 'update':
                code_parts.extend([
                    '@router.put("/{id}", response_model=' + entity_name + ')',
                    f'async def update_{entity_snake}(',
                    '    id: UUID,',
                    f'    data: {entity_name}Update,',
                    f'    service: {entity_name}Service = Depends(get_{entity_snake}_service)',
                    f'):',
                    f'    """Update {entity_snake}"""',
                    '    result = await service.update(id, data)',
                    '    if not result:',
                    f'        raise HTTPException(status_code=404, detail="{entity_name} not found")',
                    '    return result',
                    '',
                ])

            elif endpoint.operation == 'delete':
                code_parts.extend([
                    '@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)',
                    f'async def delete_{entity_snake}(',
                    '    id: UUID,',
                    f'    service: {entity_name}Service = Depends(get_{entity_snake}_service)',
                    f'):',
                    f'    """Delete {entity_snake}"""',
                    '    deleted = await service.delete(id)',
                    '    if not deleted:',
                    f'        raise HTTPException(status_code=404, detail="{entity_name} not found")',
                    '',
                ])

        return '\n'.join(code_parts)

    def _generate_main(self, spec_requirements) -> str:
        """Generate src/main.py"""
        code_parts = [
            '"""',
            'FastAPI Application',
            'Main application setup with all routers',
            '"""',
            '',
            'from fastapi import FastAPI',
            'from src.core.config import get_settings',
        ]

        # Import routers
        for entity in spec_requirements.entities:
            code_parts.append(f'from src.api.routes import {entity.snake_name}')

        code_parts.extend([
            '',
            'settings = get_settings()',
            '',
            'app = FastAPI(',
            '    title=settings.app_name,',
            '    version=settings.app_version,',
            '    debug=settings.debug',
            ')',
            '',
        ])

        # Include routers
        for entity in spec_requirements.entities:
            code_parts.append(f'app.include_router({entity.snake_name}.router)')

        code_parts.extend([
            '',
            '@app.get("/")',
            'async def root():',
            '    return {"message": "FastAPI Application", "version": settings.app_version}',
        ])

        return '\n'.join(code_parts)

    def _generate_requirements(self) -> str:
        """Generate requirements.txt"""
        return '''fastapi==0.104.0
uvicorn[standard]==0.24.0
sqlalchemy[asyncio]==2.0.23
asyncpg==0.29.0
pydantic-settings==2.0.3
python-dotenv==1.0.0
alembic==1.12.1
'''

    def _generate_env_example(self) -> str:
        """Generate .env.example"""
        return '''# Application
APP_NAME=FastAPI Application
DEBUG=false

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/db

# Logging
LOG_LEVEL=INFO
'''

    def _generate_readme(self, spec_requirements) -> str:
        """Generate README.md"""
        app_name = spec_requirements.metadata.get('spec_name', 'FastAPI Application')

        return f'''# {app_name}

Production-ready FastAPI application with modular architecture.

## Features

- Modular architecture (models/repositories/services/routes)
- Async SQLAlchemy with PostgreSQL
- Pydantic validation with strict mode
- FastAPI dependency injection
- Proper separation of concerns

## Project Structure

```
src/
├── core/           # Configuration and database
├── models/         # Pydantic schemas and SQLAlchemy entities
├── repositories/   # Data access layer
├── services/       # Business logic
└── api/
    └── routes/     # API endpoints
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Setup database
alembic upgrade head

# Run application
uvicorn src.main:app --reload
```

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
'''

    def _map_field_type(self, type_str: str) -> str:
        """Map spec field type to Python type"""
        type_map = {
            'string': 'str',
            'str': 'str',
            'integer': 'int',
            'int': 'int',
            'boolean': 'bool',
            'bool': 'bool',
            'float': 'float',
            'decimal': 'Decimal',
            'datetime': 'datetime',
            'date': 'datetime',
            'uuid': 'UUID',
            'UUID': 'UUID',
            'email': 'EmailStr',
            'text': 'str'
        }
        # Normalize input and look up in map - ensure return values are always correct case
        normalized = type_str.lower().strip() if isinstance(type_str, str) else 'str'
        result = type_map.get(normalized, 'str')
        return result

    def _map_sqlalchemy_type(self, type_str: str) -> str:
        """Map spec field type to SQLAlchemy column type"""
        type_map = {
            'string': 'String(200)',
            'text': 'Text',
            'integer': 'Integer',
            'boolean': 'Boolean',
            'float': 'Float',
            'decimal': 'Numeric(10, 2)',
            'datetime': 'DateTime(timezone=True)',
            'uuid': 'UUID(as_uuid=True)',
            'email': 'String(255)'
        }
        return type_map.get(type_str.lower(), 'String(200)')
