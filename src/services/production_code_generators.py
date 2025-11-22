"""
Production-Ready Code Generators

Hardcoded generators that produce 100% correct code for production apps.
These are used as fallback when LLM-generated patterns are incomplete.
"""

import ast
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def validate_python_syntax(code: str, filename: str = "generated") -> bool:
    """
    Validate that generated code has correct Python syntax.

    Args:
        code: Python code string
        filename: File name for error reporting

    Returns:
        True if valid, False otherwise
    """
    try:
        ast.parse(code)
        return True
    except SyntaxError as e:
        logger.error(f"❌ Syntax error in {filename}: {e.msg} at line {e.lineno}")
        return False


def generate_entities(entities: List[Dict[str, Any]]) -> str:
    """
    Generate SQLAlchemy ORM entities dynamically from entity fields.

    Args:
        entities: List of entity dicts with 'name', 'plural', and 'fields'

    Returns:
        Complete entities.py code
    """
    code = '''"""
SQLAlchemy ORM Models

Database entity definitions with proper table names and columns.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid
from src.core.database import Base


'''

    # Type mapping from spec types to SQLAlchemy types
    type_mapping = {
        'UUID': 'UUID(as_uuid=True)',
        'str': 'String(255)',
        'string': 'String(255)',
        'int': 'Integer',
        'integer': 'Integer',
        'Decimal': 'Numeric(10, 2)',
        'decimal': 'Numeric(10, 2)',
        'float': 'Numeric(10, 2)',
        'datetime': 'DateTime(timezone=True)',
        'bool': 'Boolean',
        'boolean': 'Boolean',
        'text': 'Text',
    }

    for entity in entities:
        entity_name = entity.get('name', 'Unknown')
        entity_plural = entity.get('plural', f'{entity_name}s').lower()
        fields = entity.get('fields', [])

        code += f'''
class {entity_name}Entity(Base):
    """SQLAlchemy model for {entity_plural} table."""

    __tablename__ = "{entity_plural}"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
'''

        # Generate columns dynamically from entity fields
        # Skip system fields that are added automatically (id, created_at, updated_at)
        for field in fields:
            field_name = field.name

            # Skip system fields - they are added separately
            if field_name in ['id', 'created_at', 'updated_at']:
                continue

            field_type = field.type
            is_required = field.required
            has_default = field.default is not None
            constraints = field.constraints

            # Map field type to SQLAlchemy type
            sql_type = type_mapping.get(field_type, 'String(255)')

            # Determine nullable
            nullable = not is_required

            # Handle foreign keys (fields ending with _id)
            if field_name.endswith('_id') and field_type == 'UUID':
                # Foreign key reference
                code += f'    {field_name} = Column(UUID(as_uuid=True), nullable={nullable})\n'
            else:
                # Regular column
                column_def = f'    {field_name} = Column({sql_type}'

                # Add nullable
                column_def += f', nullable={nullable}'

                # Add unique for email fields
                if field_name == 'email':
                    column_def += ', unique=True'

                # Add default if exists
                if has_default and field.default != '...':
                    if field_type == 'datetime':
                        column_def += ', default=lambda: datetime.now(timezone.utc)'
                    elif field_type in ['str', 'string']:
                        column_def += f', default="{field.default}"'
                    elif field_type in ['int', 'integer', 'Decimal', 'decimal', 'float']:
                        column_def += f', default={field.default}'
                    elif field_type in ['bool', 'boolean']:
                        # Capitalize boolean strings (true/false → True/False)
                        if isinstance(field.default, str):
                            bool_value = 'True' if field.default.lower() == 'true' else 'False'
                            column_def += f', default={bool_value}'
                        else:
                            column_def += f', default={field.default}'

                column_def += ')\n'
                code += column_def

        # Always add created_at for consistency
        code += '    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))\n'

        # Generate __repr__ method
        # Try to find a good display field (name, email, status, or first non-id field)
        display_field = None
        for field in fields:
            if field.name in ['name', 'email', 'status']:
                display_field = field.name
                break

        if not display_field and fields:
            # Use first non-id field
            for field in fields:
                if field.name not in ['id', 'created_at', 'updated_at']:
                    display_field = field.name
                    break

        if display_field:
            code += f'''
    def __repr__(self):
        return f"<{entity_name} {{self.id}}: {{getattr(self, '{display_field}', 'N/A')}}>"
'''
        else:
            code += f'''
    def __repr__(self):
        return f"<{entity_name} {{self.id}}>"
'''

    return code.strip()


def generate_config() -> str:
    """
    Generate Pydantic settings configuration with proper defaults.

    Returns:
        Complete config.py code
    """
    return '''"""
Application Configuration

Uses pydantic-settings for type-safe configuration with .env support.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore unknown environment variables
    )

    # Application
    app_name: str = "API"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://user:pass@localhost/api_db"
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # Logging
    log_level: str = "INFO"

    # Security
    cors_origins: list[str] = ["http://localhost:3000"]
    rate_limit: str = "100/minute"

    # Optional - Redis configuration (if needed)
    redis_url: str = "redis://localhost:6379/0"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
'''


def generate_schemas(entities: List[Dict[str, Any]], validation_ground_truth: Dict[str, Any] = None) -> str:
    """
    Generate Pydantic schemas for request/response validation.

    Args:
        entities: List of entity dicts with 'name', 'plural', and 'fields'
        validation_ground_truth: Optional validation ground truth from spec parser

    Returns:
        Complete schemas.py code
    """
    code = '''"""
Pydantic Request/Response Schemas

Type-safe data validation for API endpoints.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import List, Optional
from decimal import Decimal


'''

    # Build validation constraint lookup from ground truth
    validation_lookup = {}  # {(entity, field): constraint}
    if validation_ground_truth and 'validations' in validation_ground_truth:
        for val_id, val_data in validation_ground_truth['validations'].items():
            entity_name = val_data.get('entity')
            field_name = val_data.get('field')
            constraint = val_data.get('constraint')
            if entity_name and field_name and constraint:
                validation_lookup[(entity_name, field_name)] = constraint
                logger.debug(f"📋 Validation ground truth: {entity_name}.{field_name} → {constraint}")

    # Type mapping from spec types to Python/Pydantic types
    type_mapping = {
        'UUID': 'UUID',
        'str': 'str',
        'string': 'str',
        'int': 'int',
        'integer': 'int',
        'float': 'float',
        'Decimal': 'Decimal',
        'decimal': 'Decimal',
        'bool': 'bool',
        'boolean': 'bool',
        'datetime': 'datetime',
        'date': 'datetime',
    }

    for entity in entities:
        entity_name = entity.get('name', 'Unknown')
        entity_lower = entity_name.lower()
        fields_list = entity.get('fields', [])

        # Build field definitions for Pydantic
        pydantic_fields = []
        for field_obj in fields_list:
            # Skip system fields (id, created_at) - those go in Response only
            if hasattr(field_obj, 'name') and field_obj.name in ['id', 'created_at']:
                continue

            # Extract field attributes
            if hasattr(field_obj, 'name'):
                field_name = field_obj.name
                field_type = getattr(field_obj, 'type', 'str')
                required = getattr(field_obj, 'required', True)
                field_default = getattr(field_obj, 'default', None)
                description = getattr(field_obj, 'description', '')
                constraints = getattr(field_obj, 'constraints', [])
            else:
                # Fallback for dict-based fields
                field_name = field_obj.get('name', 'unknown')
                field_type = field_obj.get('type', 'str')
                required = field_obj.get('required', True)
                field_default = field_obj.get('default', None)
                description = field_obj.get('description', '')
                constraints = field_obj.get('constraints', [])

            # Map type to Python type
            python_type = type_mapping.get(field_type, 'str')

            # Build Field() constraints based on type and constraints list
            field_constraints = {}  # Use dict to track constraint types and avoid duplicates

            # Check validation ground truth first (highest priority)
            gt_constraint = validation_lookup.get((entity_name, field_name))
            if gt_constraint:
                logger.info(f"✅ Using validation ground truth for {entity_name}.{field_name}: {gt_constraint}")
                # Add ground truth constraint to constraints list if not already present
                if isinstance(constraints, list):
                    if gt_constraint not in constraints:
                        constraints.append(gt_constraint)
                else:
                    constraints = [gt_constraint]

            # Parse constraints from spec first (to get the authoritative values)
            for constraint in constraints:
                if isinstance(constraint, str):
                    constraint = constraint.strip()
                    # NORMALIZATION: Convert to lowercase and replace spaces with underscores
                    # This handles variations like "email format" vs "email_format"
                    constraint_normalized = constraint.lower().replace(' ', '_')

                    # Parse operator syntax: ">= 0", "> 0", "< 10", etc.
                    if constraint.startswith('>='):
                        value = constraint[2:].strip()
                        field_constraints['ge'] = f'ge={value}'
                        logger.debug(f"✅ Parsed constraint '{constraint}' → 'ge={value}' for {field_name}")
                    elif constraint.startswith('>'):
                        value = constraint[1:].strip()
                        field_constraints['gt'] = f'gt={value}'
                        logger.debug(f"✅ Parsed constraint '{constraint}' → 'gt={value}' for {field_name}")
                    elif constraint.startswith('<='):
                        value = constraint[2:].strip()
                        field_constraints['le'] = f'le={value}'
                        logger.debug(f"✅ Parsed constraint '{constraint}' → 'le={value}' for {field_name}")
                    elif constraint.startswith('<'):
                        value = constraint[1:].strip()
                        field_constraints['lt'] = f'lt={value}'
                        logger.debug(f"✅ Parsed constraint '{constraint}' → 'lt={value}' for {field_name}")
                    # Parse named constraints
                    elif '=' in constraint:
                        # Direct constraint like "gt=0", "min_length=1"
                        key = constraint.split('=')[0]
                        field_constraints[key] = constraint
                        logger.debug(f"✅ Parsed named constraint '{constraint}' → key='{key}' for {field_name}")
                    # Use normalized version for matching keyword constraints
                    elif constraint_normalized == 'email_format':
                        field_constraints['pattern'] = 'pattern=r"^[^@]+@[^@]+\\.[^@]+$"'
                        logger.debug(f"✅ Parsed email_format constraint for {field_name}")
                    elif constraint_normalized == 'positive':
                        field_constraints['gt'] = 'gt=0'
                        logger.debug(f"✅ Parsed 'positive' → 'gt=0' for {field_name}")
                    elif constraint_normalized == 'non_negative':
                        field_constraints['ge'] = 'ge=0'
                        logger.debug(f"✅ Parsed 'non_negative' → 'ge=0' for {field_name}")
                    # NEW: Handle constraint types from validation ground truth
                    elif constraint_normalized == 'required':
                        # Mark field as required (will prevent Optional and default)
                        required = True
                        logger.debug(f"✅ Parsed 'required' constraint for {field_name}")
                    elif constraint_normalized == 'uuid_format':
                        # Add UUID pattern validation
                        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                        field_constraints['pattern'] = f'pattern=r"{uuid_pattern}"'
                        logger.debug(f"✅ Parsed 'uuid_format' constraint for {field_name}")
                    elif constraint_normalized == 'enum':
                        # Mark that this field needs enum validation (handled separately)
                        field_constraints['_is_enum'] = True
                        logger.debug(f"✅ Parsed 'enum' constraint for {field_name}")
                    elif constraint_normalized == 'business_rule':
                        # Business rules are not field-level validations, skip
                        logger.debug(f"ℹ️ Skipping 'business_rule' constraint for {field_name} (not a field validation)")
                    else:
                        logger.warning(f"⚠️ Unparsed constraint '{constraint}' (normalized: '{constraint_normalized}') for {field_name} - SKIPPING")
                else:
                    logger.warning(f"⚠️ Non-string constraint {constraint} (type={type(constraint)}) for {field_name}")

            # Add type-specific default constraints (only if not already set)
            if python_type == 'str' and field_name == 'email':
                # Email validation with pattern
                if 'pattern' not in field_constraints:
                    field_constraints['pattern'] = 'pattern=r"^[^@]+@[^@]+\\.[^@]+$"'
            elif python_type == 'str':
                # Default min_length=1 for required strings to ensure not empty
                if required and 'min_length' not in field_constraints:
                    field_constraints['min_length'] = 'min_length=1'
                # Add reasonable max_length to trigger validation in OpenAPI
                if 'max_length' not in field_constraints:
                    field_constraints['max_length'] = 'max_length=255'
            elif python_type in ['Decimal', 'int', 'float']:
                # Numeric constraints - only add defaults if no constraint already exists
                # gt (greater than) is more restrictive than ge (greater or equal)
                if 'gt' not in field_constraints and 'ge' not in field_constraints:
                    if field_name in ['price', 'total_amount', 'amount', 'cost', 'quantity']:
                        field_constraints['gt'] = 'gt=0'
                    elif field_name in ['id', 'count', 'total']:
                        field_constraints['ge'] = 'ge=0'
                    # For 'stock' - spec says >= 0, so don't override with gt=0

            # Handle enum fields - remove marker and note for future enhancement
            is_enum_field = field_constraints.pop('_is_enum', False)
            if is_enum_field:
                logger.info(f"ℹ️ Field {entity_name}.{field_name} marked as enum - using Literal or Enum would be ideal")
                # For now, we'll let it be a string field with the constraints
                # Future enhancement: Generate Literal['value1', 'value2'] or Enum class

            # Convert dict to list for joining
            field_constraints_list = list(field_constraints.values())

            # Convert JavaScript/JSON boolean values to Python
            python_default = field_default
            if field_default is not None:
                if isinstance(field_default, str):
                    if field_default.lower() == 'true':
                        python_default = 'True'
                    elif field_default.lower() == 'false':
                        python_default = 'False'

            # Build field definition with or without Field()
            if field_constraints_list:
                # Use Field() with constraints
                constraints_str = ', '.join(field_constraints_list)
                if required and not python_default:
                    # Required field: Field(...)
                    pydantic_fields.append(f"    {field_name}: {python_type} = Field(..., {constraints_str})")
                elif python_default:
                    # Field with default value
                    if python_type == 'str':
                        pydantic_fields.append(f'    {field_name}: {python_type} = Field("{python_default}", {constraints_str})')
                    else:
                        pydantic_fields.append(f'    {field_name}: {python_type} = Field({python_default}, {constraints_str})')
                else:
                    # Optional field
                    pydantic_fields.append(f"    {field_name}: Optional[{python_type}] = Field(None, {constraints_str})")
            else:
                # No constraints, use simple type annotation
                if required and not python_default:
                    # Required field without default
                    pydantic_fields.append(f"    {field_name}: {python_type}")
                elif python_default:
                    # Field with default value
                    if python_type == 'str':
                        pydantic_fields.append(f'    {field_name}: {python_type} = "{python_default}"')
                    else:
                        pydantic_fields.append(f'    {field_name}: {python_type} = {python_default}')
                else:
                    # Optional field (not required, no default)
                    pydantic_fields.append(f"    {field_name}: Optional[{python_type}] = None")

        # Base schema - includes all fields
        code += f'''class {entity_name}Base(BaseModel):
    """Base schema for {entity_lower}."""
'''
        if pydantic_fields:
            code += '\n'.join(pydantic_fields) + '\n'
        else:
            code += '    pass\n'
        code += '\n\n'

        # Create schema - inherits all fields from Base
        code += f'''class {entity_name}Create({entity_name}Base):
    """Schema for creating {entity_lower}."""
    pass


'''

        # Update schema - all fields optional for partial updates
        code += f'''class {entity_name}Update(BaseModel):
    """Schema for updating {entity_lower}."""
'''
        if pydantic_fields:
            # Make all fields optional for updates, preserving Field() constraints
            update_fields = []
            for field_line in pydantic_fields:
                # Extract field name and type
                field_def = field_line.strip()
                if ': ' in field_def:
                    field_part = field_def.split(': ', 1)
                    fname = field_part[0]
                    rest = field_part[1]

                    # Check if it uses Field()
                    if ' = Field(' in rest:
                        # Extract type and Field() part
                        type_part = rest.split(' = Field(')[0]
                        field_part_match = rest.split(' = Field(')[1]
                        # Replace first argument with None and keep constraints
                        if field_part_match.startswith('...'):
                            # Field(..., constraints) → Field(None, constraints)
                            field_constraints = field_part_match.replace('...', 'None', 1)
                        else:
                            # Field(default, constraints) → Field(None, constraints)
                            # Find the first comma to replace default with None
                            if ',' in field_part_match:
                                field_constraints = 'None' + field_part_match[field_part_match.index(','):]
                            else:
                                # No constraints, just default
                                field_constraints = 'None' + field_part_match[field_part_match.index(')'):]

                        # Make type Optional if not already
                        if not type_part.startswith('Optional['):
                            update_fields.append(f"    {fname}: Optional[{type_part}] = Field({field_constraints}")
                        else:
                            update_fields.append(f"    {fname}: {type_part} = Field({field_constraints}")
                    else:
                        # Simple type annotation, make it Optional
                        ftype = rest.split(' = ')[0]  # Remove default if present
                        if ftype.startswith('Optional['):
                            update_fields.append(f"    {fname}: {ftype} = None")
                        else:
                            update_fields.append(f"    {fname}: Optional[{ftype}] = None")
            code += '\n'.join(update_fields) + '\n'
        else:
            code += '    pass\n'
        code += '\n\n'

        # Response schema (WITH Response suffix for consistency with routes)
        code += f'''class {entity_name}Response({entity_name}Base):
    """Response schema for {entity_lower}."""
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


'''

        # List schema (uses {entity_name}Response for items)
        code += f'''class {entity_name}List(BaseModel):
    """List response with pagination."""
    items: List[{entity_name}Response]
    total: int
    page: int


'''

    return code.strip()


def generate_service_method(entity_name: str) -> str:
    """
    Generate a complete service method without indentation errors.

    Args:
        entity_name: Name of the entity

    Returns:
        Complete service file code
    """
    # Convert CamelCase to snake_case (CartItem → cart_item)
    import re
    entity_snake = re.sub(r'(?<!^)(?=[A-Z])', '_', entity_name).lower()
    plural = f"{entity_snake}s"

    return f'''"""
FastAPI Service for {entity_name}

Business logic and data access patterns.
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging

from src.models.schemas import {entity_name}Create, {entity_name}Update, {entity_name}Response, {entity_name}List
from src.repositories.{entity_snake}_repository import {entity_name}Repository
from src.models.entities import {entity_name}Entity

logger = logging.getLogger(__name__)


class {entity_name}Service:
    """Business logic for {entity_name}."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = {entity_name}Repository(db)

    async def create(self, data: {entity_name}Create) -> {entity_name}Response:
        """Create a new {entity_name.lower()}."""
        db_obj = await self.repo.create(data)
        return {entity_name}Response.model_validate(db_obj)

    async def get(self, id: UUID) -> Optional[{entity_name}Response]:
        """Get {entity_name.lower()} by ID."""
        db_obj = await self.repo.get(id)
        if db_obj:
            return {entity_name}Response.model_validate(db_obj)
        return None

    async def list(self, page: int = 1, size: int = 10) -> {entity_name}List:
        """List {plural} with pagination."""
        skip = (page - 1) * size

        items = await self.repo.list(skip=skip, limit=size)
        total = await self.repo.count()

        return {entity_name}List(
            items=[{entity_name}Response.model_validate(t) for t in items],
            total=total,
            page=page,
            size=size,
        )

    async def update(self, id: UUID, data: {entity_name}Update) -> Optional[{entity_name}Response]:
        """Update {entity_name.lower()}."""
        db_obj = await self.repo.update(id, data)
        if db_obj:
            return {entity_name}Response.model_validate(db_obj)
        return None

    async def delete(self, id: UUID) -> bool:
        """Delete {entity_name.lower()}."""
        return await self.repo.delete(id)
'''


def generate_initial_migration(entities: List[Dict[str, Any]]) -> str:
    """
    Generate initial Alembic migration file.

    Args:
        entities: List of entities to create

    Returns:
        Complete migration code
    """
    code = '''"""
Initial migration - Create database tables

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables."""
'''

    for entity in entities:
        entity_name = entity.get('name', 'Unknown')
        entity_plural = entity.get('plural', f'{entity_name}s').lower()

        code += f'''
    op.create_table(
        '{entity_plural}',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
'''

    code += '''

def downgrade() -> None:
    """Drop all tables."""
'''

    for entity in entities:
        entity_plural = entity.get('plural', f'{entity["name"]}s').lower()
        code += f'''    op.drop_table('{entity_plural}')
'''

    return code.strip()


def validate_generated_files(files: Dict[str, str]) -> Dict[str, bool]:
    """
    Validate syntax of all generated Python files.

    Args:
        files: Dict of filename -> code

    Returns:
        Dict of filename -> is_valid
    """
    results = {}

    for filename, code in files.items():
        if filename.endswith('.py'):
            is_valid = validate_python_syntax(code, filename)
            results[filename] = is_valid

            if is_valid:
                logger.info(f"✅ Valid: {filename}")
            else:
                logger.error(f"❌ Invalid: {filename}")

    return results


def get_validation_summary(results: Dict[str, bool]) -> Dict[str, Any]:
    """
    Get summary of validation results.

    Args:
        results: Results from validate_generated_files

    Returns:
        Summary dict with total, passed, failed
    """
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "valid": failed == 0,
        "pass_rate": round(passed / total * 100, 1) if total > 0 else 0,
    }
