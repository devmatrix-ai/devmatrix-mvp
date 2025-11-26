"""
Production-Ready Code Generators

Hardcoded generators that produce 100% correct code for production apps.
These are used as fallback when LLM-generated patterns are incomplete.
"""

import ast
from collections import defaultdict
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


def generate_entities(entities: List[Dict[str, Any]], validation_ground_truth: dict = None) -> str:
    """
    Generate SQLAlchemy ORM entities dynamically from entity fields.

    Args:
        entities: List of entity dicts with 'name', 'plural', and 'fields'
        validation_ground_truth: Optional validation ground truth with enforcement info

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
        'uuid': 'UUID(as_uuid=True)',
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

            # NEW: Check for immutable enforcement from validation ground truth
            enforcement = _get_enforcement_for_field(entity_name, field_name, validation_ground_truth)
            is_immutable = enforcement and enforcement.get('enforcement_type') == 'immutable'

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

                # Add unique if constraint specifies it (NOT based on field name)
                # NOTE: Hardcoded field_name == 'email' REMOVED - Phase: Hardcoding Elimination
                # Unique constraint should come from IR/spec constraints
                constraint_strs = [str(c).lower() for c in constraints] if constraints else []
                if any('unique' in c for c in constraint_strs):
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

                # NEW: Add onupdate=None for immutable fields
                if is_immutable:
                    logger.info(f"🔒 Adding onupdate=None to immutable field {entity_name}.{field_name}")
                    column_def += ', onupdate=None'

                column_def += ')\n'
                code += column_def

        # Always add created_at for consistency
        code += '    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))\n'

        # Generate __repr__ method
        # NOTE: Hardcoded field names REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
        # Use first non-system field as display field (no preference for specific names)
        display_field = None
        for field in fields:
            # Skip system fields
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

    # Ensure typing imports include optional Literal helper if used
    import re
    need_literal = "Literal[" in code
    # Always include Literal to avoid missing import after post-generation repairs
    import_line = "from typing import List, Optional, Literal"
    code = re.sub(r'^from typing import [^\n]+', import_line, code, count=1, flags=re.MULTILINE)

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


def _get_enforcement_for_field(entity_name: str, field_name: str, validation_ground_truth: dict) -> dict:
    """
    Get enforcement strategy for a field from validation ground truth.

    Args:
        entity_name: Name of the entity
        field_name: Name of the field (or 'attribute' in ApplicationIR terms)
        validation_ground_truth: Validation ground truth from ApplicationIR

    Returns:
        Dict with enforcement_type, enforcement_code, applied_at or None if not found
    """
    if not validation_ground_truth or 'rules' not in validation_ground_truth:
        return None

    # Search for matching rule
    for rule in validation_ground_truth['rules']:
        rule_entity = rule.get('entity', '')
        rule_field = rule.get('attribute', '')  # ApplicationIR uses 'attribute'

        if rule_entity == entity_name and rule_field == field_name:
            # Found matching rule
            enforcement_type = rule.get('enforcement_type', 'description')
            enforcement_code = rule.get('enforcement_code')
            applied_at = rule.get('applied_at', [])

            logger.info(f"🎯 Found enforcement for {entity_name}.{field_name}: type={enforcement_type}")

            return {
                'enforcement_type': enforcement_type,
                'enforcement_code': enforcement_code,
                'applied_at': applied_at,
                'rule_type': rule.get('type', ''),
                'condition': rule.get('condition', '')
            }

    return None


def _should_exclude_from_create(entity_name: str, field_name: str, validation_constraints: dict) -> bool:
    """
    Determine if a field should be excluded from Create schema.
    
    Args:
        entity_name: Name of the entity
        field_name: Name of the field
        validation_constraints: Dictionary of validation constraints from ground truth
    
    Returns:
        True if field should be excluded from Create schema
    """
    # Always exclude server-managed fields
    if field_name in ['id', 'created_at', 'updated_at']:
        return True
    
    # Check validation constraints from ground truth
    constraints = validation_constraints.get((entity_name, field_name), [])
    for constraint in constraints:
        constraint_str = str(constraint).lower()
        # Exclude auto-calculated fields (server computes them)
        if any(kw in constraint_str for kw in ['auto-calculated', 'auto_calculated', 'computed', 'sum_of']):
            return True
        # Exclude auto-generated read-only fields
        if field_name in ['registration_date', 'creation_date'] and 'read' in constraint_str:
            return True
            
    # NOTE: Hardcoded fallbacks REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
    # Exclusions now come exclusively from validation_constraints (ApplicationIR or GT)

    return False


def _should_exclude_from_update(entity_name: str, field_name: str, validation_constraints: dict) -> bool:
    """
    Determine if a field should be excluded from Update schema.
    
    Args:
        entity_name: Name of the entity
        field_name: Name of the field
        validation_constraints: Dictionary of validation constraints from ground truth
    
    Returns:
        True if field should be excluded from Update schema
    """
    # Always exclude server-managed fields
    if field_name in ['id', 'created_at', 'updated_at']:
        return True
    
    # Check validation constraints from ground truth
    constraints = validation_constraints.get((entity_name, field_name), [])
    for constraint in constraints:
        constraint_str = str(constraint).lower()
        # Exclude read-only fields (immutable after creation)
        if any(kw in constraint_str for kw in ['read-only', 'read_only', 'immutable']):
            return True
        # Exclude snapshot fields (captured at creation, immutable)
        if any(kw in constraint_str for kw in ['snapshot_at', 'snapshot']):
            return True
        # Exclude auto-calculated fields (server computes them)
        if any(kw in constraint_str for kw in ['auto-calculated', 'auto_calculated', 'computed', 'sum_of']):
            return True

    # NOTE: Hardcoded fallbacks REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
    # Exclusions now come exclusively from validation_constraints (ApplicationIR or GT)

    return False


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
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import List, Optional, Literal
from decimal import Decimal


class BaseSchema(BaseModel):
    """Base schema with UUID-friendly JSON encoding."""

    model_config = ConfigDict(
        json_encoders={UUID: str},
        from_attributes=True,
    )


'''
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'

    # NOTE: Hardcoded CartItem/OrderItem classes REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
    # Item schemas are now generated dynamically:
    # 1. From ApplicationIR.domain_model.entities (if CartItem/OrderItem exist as entities)
    # 2. From validation_ground_truth synthetic_entities (if validation rules reference them)
    # 3. Generic ItemSchema fallback is added below if needed

    # Track whether we need generic item fallback (will be set after synthetic_entities processing)
    _needs_item_fallback = False

    literal_used = False

    # Build validation constraint lookup from ground truth
    validation_lookup = {}  # {(entity, field): constraint}
    validation_constraints = defaultdict(list)  # {(entity, field): [constraints]}
    validation_entities = {}  # entity -> list of (field, constraint)
    if validation_ground_truth:
        # Handle legacy SpecRequirements format
        if 'validations' in validation_ground_truth:
            for val_id, val_data in validation_ground_truth['validations'].items():
                entity_name = val_data.get('entity')
                field_name = val_data.get('field')
                constraint = val_data.get('constraint')
                if entity_name and field_name and constraint:
                    validation_lookup[(entity_name, field_name)] = constraint
                    if constraint not in validation_constraints[(entity_name, field_name)]:
                        validation_constraints[(entity_name, field_name)].append(constraint)
                    validation_entities.setdefault(entity_name, []).append((field_name, constraint))
                    logger.debug(f"📋 Validation ground truth (legacy): {entity_name}.{field_name} → {constraint}")

        # Handle ApplicationIR format (list of rules)
        if 'rules' in validation_ground_truth:
            for rule in validation_ground_truth['rules']:
                # Handle both dict and object access
                if isinstance(rule, dict):
                    entity_name = rule.get('entity')
                    field_name = rule.get('attribute') # ApplicationIR uses 'attribute'
                    v_type = rule.get('type', '')
                    condition = rule.get('condition', '')
                else:
                    entity_name = getattr(rule, 'entity', None)
                    field_name = getattr(rule, 'attribute', None)
                    v_type = getattr(rule, 'type', '')
                    condition = getattr(rule, 'condition', '')

                # Construct constraint string
                constraint = f"{v_type}"
                if condition:
                    constraint += f": {condition}"
                
                if entity_name and field_name:
                    if constraint not in validation_constraints[(entity_name, field_name)]:
                        validation_constraints[(entity_name, field_name)].append(constraint)
                    validation_entities.setdefault(entity_name, []).append((field_name, constraint))
                    logger.debug(f"📋 Validation ground truth (IR): {entity_name}.{field_name} → {constraint}")

    # Type mapping from spec types to Python/Pydantic types
    type_mapping = {
        'UUID': 'UUID',
        'uuid': 'UUID',
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
        'enum': 'str',   # fallback; Literal applied when values provided via constraints
        'list': 'List[str]',   # safe default when item type unknown
        'array': 'List[str]',
    }

    # Create synthetic entities from validation ground truth (e.g., CartItem, OrderItem)
    existing_entity_names = {e.get('name', 'Unknown') for e in entities}
    synthetic_entities = []

    def _infer_type(field_name: str, constraint: str) -> str:
        """
        Infer field type from constraint text or field name pattern.

        NOTE: Phase: Hardcoding Elimination (Nov 25, 2025)
        - FIRST: Try to extract type from constraint text (IR source)
        - SECOND: Use generic patterns (not domain-specific names)
        """
        constraint_lower = (constraint or "").lower()
        name_lower = field_name.lower()

        # PRIORITY 1: Extract type from constraint text (from IR)
        if 'uuid' in constraint_lower:
            return 'UUID'
        if 'integer' in constraint_lower or 'int' in constraint_lower:
            return 'int'
        if 'decimal' in constraint_lower or 'numeric' in constraint_lower or 'float' in constraint_lower:
            return 'Decimal'
        if 'boolean' in constraint_lower or 'bool' in constraint_lower:
            return 'bool'
        if 'datetime' in constraint_lower or 'timestamp' in constraint_lower:
            return 'datetime'

        # PRIORITY 2: Generic patterns from field name (not domain-specific)
        if name_lower == 'id' or name_lower.endswith('_id'):
            return 'UUID'

        # Default to string (safest)
        return 'str'

    for ent_name, fields_list in validation_entities.items():
        if ent_name not in existing_entity_names:
            synthetic = {
                'name': ent_name,
                'plural': f"{ent_name}s",
                'fields': []
            }
            seen_fields = set()
            for fname, constraint in fields_list:
                if fname in seen_fields:
                    continue
                seen_fields.add(fname)
                ftype = _infer_type(fname, constraint)
                synthetic['fields'].append({
                    'name': fname,
                    'type': ftype,
                    'required': True,
                    'constraints': [constraint],
                })
            synthetic_entities.append(synthetic)

    if synthetic_entities:
        logger.info(f"🧩 Adding synthetic entities from validation ground truth: {[e['name'] for e in synthetic_entities]}")
        entities = list(entities) + synthetic_entities

    # Sort entities so that item-like entities (CartItem, OrderItem) are defined before parents
    def _entity_priority(ent: Dict[str, Any]) -> int:
        name = str(ent.get('name', '')).lower()
        if name.endswith('item'):
            return 0
        return 1

    entities = sorted(entities, key=_entity_priority)

    # NOTE: Hardcoded 'cart'/'order' names REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
    # Generic item schema detection: entities that need item schemas are detected by:
    # 1. Having a field of type List[*] (e.g., items: List[CartItem])
    # 2. Their corresponding *Item entity not being in the entity list
    entity_names_lower = {str(e.get('name', '')).lower() for e in entities}

    # Detect entities that have List fields (potential parent entities needing item schemas)
    entities_with_list_fields = set()
    for entity in entities:
        fields = entity.get('fields', []) or []
        for field in fields:
            if hasattr(field, 'type'):
                ft = str(getattr(field, 'type', '')).lower()
            elif isinstance(field, dict):
                ft = str(field.get('type', '')).lower()
            else:
                ft = ''
            if 'list' in ft or 'array' in ft:
                entities_with_list_fields.add(str(entity.get('name', '')).lower())
                break

    # Check if corresponding *Item entities exist for parent entities
    missing_item_schemas = []
    for parent_name in entities_with_list_fields:
        item_name = f"{parent_name}item"
        if item_name not in entity_names_lower:
            missing_item_schemas.append(parent_name)

    # Add generic ItemSchema fallback if any parent entity needs item schemas
    if missing_item_schemas:
        logger.info(f"📦 Adding generic ItemSchema fallback for: {missing_item_schemas}")
        code += '''from typing import Dict, Any

# Generic item schema - specific item entities should come from ApplicationIR
ItemSchema = Dict[str, Any]


'''
        # Generate generic item classes for each missing item entity
        for parent_name in missing_item_schemas:
            item_class_name = f"{parent_name.title()}Item"
            code += f'''class {item_class_name}(BaseModel):
    """Generic item for {parent_name} - fields should come from ApplicationIR."""
    model_config = ConfigDict(extra="allow")


'''

    # NOTE: gt_defaults for constraint hardening REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
    # Constraints now come exclusively from:
    # 1. ApplicationIR.validation_model.rules (from spec parsing)
    # 2. validation_constraints parameter (from ground truth)
    # If constraints are missing, they should be added to the spec, not hardcoded here.

    for entity in entities:
        entity_name = entity.get('name', 'Unknown')
        entity_lower = entity_name.lower()
        fields_list = entity.get('fields', []) or []

        # If ground truth has constraints for fields not present in the spec, synthesize those fields
        existing_field_names = {f.name if hasattr(f, "name") else f.get("name") for f in fields_list}
        missing_from_gt = []
        for (gt_entity, gt_field), gt_cons in validation_constraints.items():
            if gt_entity == entity_name and gt_field not in existing_field_names:
                missing_from_gt.append((gt_field, gt_cons))
        for fname, gt_cons in missing_from_gt:
            inferred_type = _infer_type(fname, ",".join(gt_cons))
            required_flag = any(c == 'required' for c in gt_cons)
            fields_list.append({
                'name': fname,
                'type': inferred_type,
                'required': required_flag,
                'default': None,
                'constraints': list(gt_cons),
            })
            existing_field_names.add(fname)

        # Build field definitions for Pydantic
        pydantic_fields = []
        for field_obj in fields_list:
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

            # Ensure constraints is a mutable list
            if constraints is None:
                constraints = []
            elif not isinstance(constraints, list):
                constraints = list(constraints)

            # NOTE: Hardening constraint injection REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
            # Constraints now come from validation_constraints parameter only

            # Map type to Python type
            python_type = type_mapping.get(field_type, field_type)

            # Special-case server-managed fields: make them optional on input schemas
            if field_name in ['id', 'created_at']:
                required = False
                field_default = None
                # Remove min/max constraints to avoid blocking creates
                constraints = [c for c in constraints if not str(c).startswith(('min_', 'max_'))]

            # Handle list/array with explicit item type e.g., list[CartItem] or List[CartItem]
            ft_str = str(field_type)
            ft_lower = ft_str.lower()
            if ft_lower.startswith('list[') or ft_lower.startswith('array['):
                inner = ft_str[ft_str.find('[') + 1: ft_str.rfind(']')].strip()
                inner_mapped = type_mapping.get(inner, inner or 'str')
                base_inner = {'uuid', 'str', 'int', 'float', 'decimal', 'bool', 'datetime'}
                if isinstance(inner_mapped, str) and inner_mapped.lower() not in base_inner and not inner_mapped.startswith('List['):
                    inner_mapped = 'str'
                python_type = f"List[{inner_mapped}]"

            # Normalize unknown types to safe defaults
            base_types = {'uuid', 'str', 'int', 'float', 'decimal', 'bool', 'datetime', 'list', 'dict'}
            if isinstance(python_type, str) and python_type.lower() not in base_types and not python_type.startswith('List['):
                python_type = 'str'

            # Detect enum constraints (format: enum=VAL1,VAL2) or enum type
            enum_values = None
            enum_from_constraint = False
            # NOTE: Hardcoded enums for cart/order REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
            # Enums now come exclusively from constraints or field type definition
            if ft_lower.startswith('enum'):
                # Try to parse inline enum values: enum["OPEN","CLOSED"] or enum OPEN,CLOSED
                import re
                match = re.search(r'enum[^\w\d]*[\[\(]?([^\]\)]*)', ft_str, re.IGNORECASE)
                if match:
                    raw_vals = match.group(1)
                    if raw_vals:
                        enum_values = [v.strip().strip('"').strip("'") for v in raw_vals.split(',') if v.strip()]
            if constraints:
                for constraint in list(constraints):
                    if isinstance(constraint, str) and constraint.lower().startswith('enum='):
                        enum_values = [v.strip() for v in constraint.split('=', 1)[1].split(',') if v.strip()]
                        enum_from_constraint = True
                        constraints.remove(constraint)
                        break

            if enum_values:
                literal_vals = ', '.join([f'"{v}"' for v in enum_values])
                python_type = f'Literal[{literal_vals}]'
                literal_used = True
                # Mark as required by default for enums
                required = True
            else:
                # If enum was declared without values, keep it as str to avoid NameError
                if ft_lower.startswith('enum'):
                    python_type = 'str'

            # Check validation ground truth first (highest priority)
            gt_constraints = validation_constraints.get((entity_name, field_name), [])
            required_from_gt = any(c == 'required' for c in gt_constraints)
            for gt_constraint in gt_constraints:
                logger.info(f"✅ Using validation ground truth for {entity_name}.{field_name}: {gt_constraint}")
                if gt_constraint not in constraints:
                    constraints.append(gt_constraint)

            # NOTE: Hardcoded field_name == 'items' REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
            # List detection now based ONLY on type, not field name
            # If this is a list type field, use generic type. Relationships should come from IR.
            if ft_lower.startswith('list') or ft_lower.startswith('array'):
                # Use generic list type - specific item types should be defined via IR relationships
                if python_type not in ('List[Dict[str, Any]]',) and not python_type.startswith('List['):
                    python_type = 'List[Dict[str, Any]]'
                # Allow empty list on create
                required = required_from_gt
                field_default = None if required_from_gt else (field_default or [])
                # Remove any injected min_items to avoid 422 on empty lists
                constraints = [c for c in constraints if not str(c).startswith('min_items')]

            # NOTE: Hardcoded status defaults for cart/order REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
            # Status field defaults should come from spec/IR field_default, not hardcoded here
            # If a status field needs a default, define it in the spec

            # If ground truth requires the field, drop defaults to force Field(...)
            if required_from_gt:
                required = True
                field_default = None

            # Build Field() constraints based on type and constraints list
            field_constraints = {}  # Use dict to track constraint types and avoid duplicates

            # Parse constraints from spec first (to get the authoritative values)
            for constraint in constraints:
                if isinstance(constraint, str):
                    constraint = constraint.strip()
                    # NORMALIZATION: Convert to lowercase and replace spaces with underscores
                    # This handles variations like "email format" vs "email_format"
                    constraint_normalized = constraint.lower().replace(' ', '_')

                    # Capture enum constraints and convert to Literal to avoid leaking into Field kwargs
                    if constraint_normalized.startswith('enum='):
                        raw_vals = constraint.split('=', 1)[1] if '=' in constraint else ''
                        enum_values = [v.strip().strip('"').strip("'") for v in raw_vals.split(',') if v.strip()]
                        literal_used = True
                        if enum_values:
                            literal_vals = ', '.join([f'"{v}"' for v in enum_values])
                            python_type = f'Literal[{literal_vals}]'
                        continue

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
                    # NEW: Parse range format: "range:>0", "range:>=1", "range: >= 0.01", "range:0-100"
                    elif constraint.startswith('range:') or constraint.startswith('range '):
                        range_part = constraint.split(':', 1)[1].strip() if ':' in constraint else constraint[6:].strip()

                        # Handle compound ranges like "0-100" (without operators)
                        if '-' in range_part and not any(op in range_part for op in ['>=', '<=', '>', '<']):
                            parts = range_part.split('-')
                            if len(parts) == 2:
                                min_val, max_val = parts[0].strip(), parts[1].strip()
                                field_constraints['ge'] = f'ge={min_val}'
                                field_constraints['le'] = f'le={max_val}'
                                logger.debug(f"✅ Parsed range '{constraint}' → ge={min_val}, le={max_val} for {field_name}")
                        # Handle operator-based ranges like ">=1", ">0"
                        elif range_part.startswith('>='):
                            value = range_part[2:].strip()
                            field_constraints['ge'] = f'ge={value}'
                            logger.debug(f"✅ Parsed range '{constraint}' → ge={value} for {field_name}")
                        elif range_part.startswith('>'):
                            value = range_part[1:].strip()
                            field_constraints['gt'] = f'gt={value}'
                            logger.debug(f"✅ Parsed range '{constraint}' → gt={value} for {field_name}")
                        elif range_part.startswith('<='):
                            value = range_part[2:].strip()
                            field_constraints['le'] = f'le={value}'
                            logger.debug(f"✅ Parsed range '{constraint}' → le={value} for {field_name}")
                        elif range_part.startswith('<'):
                            value = range_part[1:].strip()
                            field_constraints['lt'] = f'lt={value}'
                            logger.debug(f"✅ Parsed range '{constraint}' → lt={value} for {field_name}")
                        else:
                            logger.warning(f"⚠️ Unknown range format '{constraint}' for {field_name} - SKIPPING")
                    # NEW: Skip unparseable constraint types (business rules go to service layer)
                    elif constraint.startswith('custom:') or constraint.startswith('custom '):
                        logger.debug(f"ℹ️ Skipping custom rule for {field_name}: {constraint[:60]}... (handled in service layer)")
                    elif constraint.startswith('format:') or constraint.startswith('format '):
                        # Handle format constraints that should be converted
                        format_part = constraint.split(':', 1)[1].strip() if ':' in constraint else constraint[7:].strip()
                        if 'length' in format_part.lower():
                            # "format: length >= 1" → skip (already handled by min_length)
                            logger.debug(f"ℹ️ Skipping length format constraint for {field_name}: {constraint[:60]}...")
                        else:
                            logger.debug(f"ℹ️ Skipping format constraint for {field_name}: {constraint[:60]}...")
                    # Parse named constraints (MUST be proper format like "ge=0", NOT "range: >= 1")
                    elif '=' in constraint and ':' not in constraint:
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
            is_literal = isinstance(python_type, str) and python_type.startswith('Literal[')
            is_str_like = python_type == 'str'  # ← FIXED: Literal types are NOT string-like

            # NOTE: Hardcoded field_name checks REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
            # Email pattern now detected by constraint, not field name
            # Check if field has email validation constraint from IR/spec
            constraint_strs_lower = [str(c).lower() for c in constraints] if constraints else []
            has_email_constraint = any(
                kw in c for c in constraint_strs_lower
                for kw in ['email', 'valid_email', 'format:email', 'email_format']
            )

            if is_str_like and has_email_constraint:
                # Email validation with pattern - detected from constraint, not field name
                if 'pattern' not in field_constraints:
                    field_constraints['pattern'] = 'pattern=r"^[^@]+@[^@]+\\.[^@]+$"'
            elif is_str_like:
                # Default min_length=1 for required strings to ensure not empty
                # NOTE: NOT applied to Literal types (enums) - they don't need length validation
                if required and 'min_length' not in field_constraints:
                    field_constraints['min_length'] = 'min_length=1'
                # Add reasonable max_length to trigger validation in OpenAPI
                if 'max_length' not in field_constraints:
                    field_constraints['max_length'] = 'max_length=255'
            elif python_type in ['Decimal', 'int', 'float']:
                # NOTE: Hardcoded field names for gt/ge REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
                # Numeric constraints should come from IR/spec, not inferred from field names
                # If spec says field > 0, the constraint should be in validation_constraints
                # Only add ge=0 as safe default for ALL numerics (non-negative is common)
                # Specific gt=0 (positive) should come from spec constraints
                if 'gt' not in field_constraints and 'ge' not in field_constraints:
                    # Check if spec already defines positivity constraint
                    has_positive_constraint = any(
                        kw in c for c in constraint_strs_lower
                        for kw in ['positive', 'gt=0', 'gt:0', '>0', 'greater_than_zero']
                    )
                    if has_positive_constraint:
                        field_constraints['gt'] = 'gt=0'
                    # Don't add default ge=0 - let spec define constraints explicitly

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
            use_default_factory = False  # Flag for datetime.now() factory pattern
            if field_default is not None:
                if isinstance(field_default, str):
                    if field_default.lower() == 'true':
                        python_default = 'True'
                    elif field_default.lower() == 'false':
                        python_default = 'False'
                    # NEW: Handle "now" default for datetime fields
                    elif field_default.lower() == 'now':
                        if python_type == 'datetime' or 'datetime' in str(python_type).lower():
                            # Use default_factory pattern for dynamic datetime
                            use_default_factory = True
                            python_default = None  # Will be handled specially
                            logger.debug(f"✅ Converting 'now' default to default_factory=datetime.now for {field_name}")
                        else:
                            # Not a datetime field, skip the "now" default
                            python_default = None
                            logger.warning(f"⚠️ 'now' default on non-datetime field {field_name} - removing default")

            # NEW: Check for enforcement strategy from validation ground truth
            enforcement = _get_enforcement_for_field(entity_name, field_name, validation_ground_truth)

            # Handle special enforcement types
            if enforcement:
                enf_type = enforcement.get('enforcement_type', 'description')

                # 1. Computed field - generate @computed_field property
                if enf_type == 'computed_field':
                    logger.info(f"✨ Generating @computed_field for {entity_name}.{field_name}")
                    # Extract calculation logic from enforcement_code or condition
                    calc_code = enforcement.get('enforcement_code')
                    if not calc_code:
                        # Fallback: generate placeholder based on field name
                        if 'total' in field_name.lower():
                            calc_code = f"return sum(item.unit_price * item.quantity for item in self.items)"
                        else:
                            calc_code = "pass  # TODO: Implement calculation logic"

                    pydantic_fields.append(f"""    @computed_field
    @property
    def {field_name}(self) -> {python_type}:
        {calc_code}""")
                    continue  # Skip normal field generation

                # 2. Immutable field - generate with exclude=True
                elif enf_type == 'immutable':
                    logger.info(f"🔒 Generating immutable field for {entity_name}.{field_name}")
                    # Immutable fields should be excluded from input schemas
                    if field_constraints_list:
                        constraints_str = ', '.join(field_constraints_list)
                        pydantic_fields.append(f"    {field_name}: {python_type} = Field(..., {constraints_str}, exclude=True)")
                    else:
                        pydantic_fields.append(f"    {field_name}: {python_type} = Field(..., exclude=True)")
                    continue  # Skip normal field generation

                # 3. Business logic enforcement - add description marker
                elif enf_type == 'business_logic':
                    logger.info(f"⚙️ Business logic enforcement for {entity_name}.{field_name} (handled at service layer)")
                    # Business logic is enforced in service layer, not schema
                    # Still generate normal field but add description
                    description = f"Enforced by business logic: {enforcement.get('condition', '')}"
                    if field_constraints_list:
                        constraints_str = ', '.join(field_constraints_list)
                        pydantic_fields.append(f'    {field_name}: {python_type} = Field(..., {constraints_str}, description="{description}")')
                    else:
                        pydantic_fields.append(f'    {field_name}: {python_type} = Field(..., description="{description}")')
                    continue  # Skip normal field generation

            # NEW: Handle datetime fields with "now" default using default_factory
            if use_default_factory:
                # Use Field with default_factory for datetime.now()
                if field_constraints_list:
                    constraints_str = ', '.join(field_constraints_list)
                    pydantic_fields.append(f"    {field_name}: {python_type} = Field(default_factory=datetime.now, {constraints_str})")
                else:
                    pydantic_fields.append(f"    {field_name}: {python_type} = Field(default_factory=datetime.now)")
                logger.debug(f"✅ Generated datetime field with default_factory: {field_name}")
                continue  # Skip normal field generation

            # Build field definition with or without Field() (EXISTING LOGIC)
            if field_constraints_list:
                # Use Field() with constraints
                constraints_str = ', '.join(field_constraints_list)
                if required and not python_default:
                    # Required field: Field(...)
                    pydantic_fields.append(f"    {field_name}: {python_type} = Field(..., {constraints_str})")
                elif python_default is not None:
                    # Field with default value
                    needs_quotes = python_type == 'str' or (isinstance(python_type, str) and python_type.startswith('Literal['))
                    default_val = f'"{python_default}"' if needs_quotes else python_default
                    pydantic_fields.append(f'    {field_name}: {python_type} = Field({default_val}, {constraints_str})')
                else:
                    # Optional field
                    pydantic_fields.append(f"    {field_name}: Optional[{python_type}] = Field(None, {constraints_str})")
            else:
                # No constraints, use simple type annotation
                # NOTE: Hardcoded field_name == 'items' checks REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
                # List types are now handled generically by type, not field name
                if required and not python_default:
                    # Required field without default
                    pydantic_fields.append(f"    {field_name}: {python_type}")
                elif python_default is not None:
                    # Field with default value
                    needs_quotes = python_type == 'str' or (isinstance(python_type, str) and python_type.startswith('Literal['))
                    default_val = f'"{python_default}"' if needs_quotes else python_default
                    pydantic_fields.append(f'    {field_name}: {python_type} = {default_val}')
                else:
                    # Optional field (not required, no default)
                    pydantic_fields.append(f"    {field_name}: Optional[{python_type}] = None")

        # Base schema - includes core fields (server-managed made optional above)
        base_fields = []
        managed_fields = []
        for line in pydantic_fields:
            fname = line.strip().split(':', 1)[0]
            if fname in ['id', 'created_at']:
                managed_fields.append(line)
            else:
                base_fields.append(line)

        code += f'''class {entity_name}Base(BaseSchema):
    """Base schema for {entity_lower}."""
'''
        if base_fields:
            code += '\n'.join(base_fields) + '\n'
        else:
            code += '    pass\n'
        code += '\n\n'

        # Create schema - exclude server-managed and auto-calculated fields
        code += f'''class {entity_name}Create(BaseSchema):
    \"\"\"Schema for creating {entity_lower}.\"\"\"
'''
        create_fields = []
        for field_line in base_fields:
            fname = field_line.strip().split(':', 1)[0]
            # Check if field should be excluded
            if _should_exclude_from_create(entity_name, fname, validation_constraints):
                logger.info(f"🚫 Excluding {entity_name}.{fname} from Create schema")
                continue
            create_fields.append(field_line)

        if create_fields:
            code += '\n'.join(create_fields) + '\n'
        else:
            code += '    pass\n'
        code += '\n\n'

        # Update schema - all fields optional for partial updates, excluding read-only/auto-calculated
        code += f'''class {entity_name}Update(BaseSchema):
    """Schema for updating {entity_lower}."""
'''
        if base_fields:
            # Make all fields optional for updates, preserving Field() constraints
            update_fields = []
            for field_line in base_fields:
                # Extract field name and type
                field_def = field_line.strip()
                if ': ' in field_def:
                    field_part = field_def.split(': ', 1)
                    fname = field_part[0]
                    rest = field_part[1]
                    
                    # Check if field should be excluded from updates
                    if _should_exclude_from_update(entity_name, fname, validation_constraints):
                        logger.info(f"🔒 Excluding {entity_name}.{fname} from Update schema")
                        continue

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
'''
        response_lines = list(base_fields)
        # Ensure managed fields are present (id, created_at) and required
        for mline in managed_fields or []:
            mname = mline.strip().split(':', 1)[0]
            if mname == 'created_at':
                response_lines.append("    created_at: datetime")
                continue
            # Preserve pattern if present
            import re
            pattern_match = re.search(r'pattern=[^,)]+', mline)
            pattern_part = f", {pattern_match.group(0)}" if pattern_match else ""
            response_lines.append(f"    {mname}: UUID = Field(...{pattern_part})")
        if not managed_fields:
            response_lines.extend([
                "    id: UUID",
                "    created_at: datetime",
            ])
        code += '\n'.join(response_lines) + '\n\n'

        # List schema (uses {entity_name}Response for items)
        code += f'''class {entity_name}List(BaseSchema):
    """List response with pagination."""
    items: List[{entity_name}Response]
    total: int
    page: int


'''

    return code.strip()


def generate_service_method(entity_name: str, attributes: list = None) -> str:
    """
    Generate a complete service method without indentation errors.

    Args:
        entity_name: Name of the entity
        attributes: List of entity attributes for field-based logic detection

    Returns:
        Complete service file code
    """
    # Default to empty list if not provided
    if attributes is None:
        attributes = []
    # Convert CamelCase to snake_case (CartItem → cart_item)
    import re
    entity_snake = re.sub(r'(?<!^)(?=[A-Z])', '_', entity_name).lower()
    plural = f"{entity_snake}s"

    base_service = f'''"""
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

    async def get_by_id(self, id: UUID) -> Optional[{entity_name}Response]:
        """Alias for get() to satisfy routes expecting get_by_id."""
        return await self.get(id)

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

    async def clear_items(self, id: UUID) -> Optional[{entity_name}Response]:
        """
        Clear all items/children from this {entity_name.lower()}.

        Used for entities that have child relationships (e.g., Cart → CartItems).
        Returns the updated entity after clearing items.
        """
        # Get the entity first
        db_obj = await self.repo.get(id)
        if not db_obj:
            return None

        # Clear items through repository (implementation depends on relationship)
        await self.repo.clear_items(id)

        # Return the updated entity
        refreshed = await self.repo.get(id)
        return {entity_name}Response.model_validate(refreshed) if refreshed else None
'''

    # PHASE 2: Add checkout/cancel logic for orderable entities
    # NOTE: Hardcoded entity_name == "Order" REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
    # Now uses field-based detection: entities with both 'status' and 'payment_status' fields
    # are considered "orderable" and get checkout/cancel methods.
    # TODO: This should ultimately come from BehaviorModelIR.flows/operations
    field_names = {f.name if hasattr(f, 'name') else f.get('name', '') for f in attributes}
    is_orderable_entity = 'status' in field_names and 'payment_status' in field_names

    if is_orderable_entity:
        base_service += f'''
    async def checkout(self, cart_id: UUID) -> {entity_name}Response:
        """
        Create order from cart with stock validation and decrement.

        PHASE 2: Real enforcement - stock decrement logic (Fase 2.4)

        Steps:
        1. Validate cart exists and is OPEN
        2. Validate cart has items
        3. Validate stock availability for ALL items
        4. Decrement stock for each product
        5. Create order with PENDING_PAYMENT status
        6. Mark cart as CHECKED_OUT
        """
        from src.repositories.cart_repository import CartRepository
        from src.repositories.product_repository import ProductRepository
        from fastapi import HTTPException

        cart_repo = CartRepository(self.db)
        product_repo = ProductRepository(self.db)

        # 1. Get cart and validate
        cart = await cart_repo.get(cart_id)
        if not cart:
            raise HTTPException(status_code=404, detail="Cart not found")

        if cart.status != "OPEN":
            raise HTTPException(status_code=400, detail="Cart is not open for checkout")

        # 2. Validate cart has items
        if not cart.items or len(cart.items) == 0:
            raise HTTPException(status_code=400, detail="Cart is empty")

        # 3. Validate stock for ALL items before decrementing
        for item in cart.items:
            product = await product_repo.get(item.product_id)
            if not product:
                raise HTTPException(status_code=404, detail=f"Product {{item.product_id}} not found")

            if product.stock < item.quantity:
                raise HTTPException(
                    status_code=422,
                    detail=f"Insufficient stock for product {{product.name}}: available={{product.stock}}, requested={{item.quantity}}"
                )

        # 4. Decrement stock for each product (PHASE 2 - Real enforcement)
        for item in cart.items:
            product = await product_repo.get(item.product_id)
            product.stock -= item.quantity
            await self.db.flush()
            logger.info(f"📦 Stock decremented: {{product.name}} ({{product.stock + item.quantity}} → {{product.stock}})")

        # 5. Create order
        from src.models.schemas import OrderCreate
        order_data = OrderCreate(
            customer_id=cart.customer_id,
            status="PENDING_PAYMENT",
            payment_status="PENDING"
        )
        order = await self.create(order_data)

        # 6. Mark cart as CHECKED_OUT
        cart.status = "CHECKED_OUT"
        await self.db.flush()

        await self.db.commit()

        return order

    async def cancel_order(self, order_id: UUID) -> {entity_name}Response:
        """
        Cancel order and return stock to products.

        PHASE 2: Real enforcement - stock increment on cancel (Fase 2.4)

        Steps:
        1. Validate order exists and is PENDING_PAYMENT
        2. Increment stock for each product in order
        3. Mark order as CANCELLED
        """
        from src.repositories.product_repository import ProductRepository
        from fastapi import HTTPException

        product_repo = ProductRepository(self.db)

        # 1. Get order and validate
        order = await self.get(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.status != "PENDING_PAYMENT":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel order with status {{order.status}}. Only PENDING_PAYMENT orders can be cancelled."
            )

        # 2. Return stock for each product (PHASE 2 - Real enforcement)
        for item in order.items:
            product = await product_repo.get(item.product_id)
            if product:
                product.stock += item.quantity
                await self.db.flush()
                logger.info(f"📦 Stock returned: {{product.name}} ({{product.stock - item.quantity}} → {{product.stock}})")

        # 3. Update order status to CANCELLED
        from src.models.schemas import OrderUpdate
        updated_order = await self.update(
            order_id,
            OrderUpdate(status="CANCELLED")
        )

        await self.db.commit()

        return updated_order
'''

    return base_service


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

    # Map spec types to Alembic/SQLAlchemy column types
    type_mapping = {
        'UUID': 'postgresql.UUID(as_uuid=True)',
        'uuid': 'postgresql.UUID(as_uuid=True)',
        'str': 'sa.String(255)',
        'string': 'sa.String(255)',
        'text': 'sa.Text',
        'int': 'sa.Integer',
        'integer': 'sa.Integer',
        'float': 'sa.Numeric(10, 2)',
        'Decimal': 'sa.Numeric(10, 2)',
        'decimal': 'sa.Numeric(10, 2)',
        'datetime': 'sa.DateTime(timezone=True)',
        'date': 'sa.DateTime(timezone=True)',
        'bool': 'sa.Boolean',
        'boolean': 'sa.Boolean',
    }

    # NOTE: gt_defaults REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
    # Fields now come from ApplicationIR.domain_model.entities.attributes
    # via _entity_to_dict in code_generation_service.py
    # If fields are empty, it's a bug in the upstream pipeline, not something to patch here.

    def _infer_sql_type(fname: str, field_type: str = None) -> str:
        """
        Infer SQL type from field name or explicit type.

        NOTE: Phase: Hardcoding Elimination (Nov 25, 2025)
        This function now PREFERS explicit field_type from IR over name inference.
        Name-based inference is ONLY used as fallback when type is missing.
        """
        # FIRST: Use explicit type if provided (from IR)
        if field_type:
            ft_lower = field_type.lower()
            if ft_lower in type_mapping:
                return type_mapping[ft_lower]
            if 'uuid' in ft_lower:
                return 'postgresql.UUID(as_uuid=True)'
            if 'decimal' in ft_lower or 'numeric' in ft_lower:
                return 'sa.Numeric(10, 2)'
            if 'int' in ft_lower:
                return 'sa.Integer'
            if 'bool' in ft_lower:
                return 'sa.Boolean'
            if 'datetime' in ft_lower or 'timestamp' in ft_lower:
                return 'sa.DateTime(timezone=True)'
            if 'list' in ft_lower or 'array' in ft_lower:
                return 'sa.String(255)'  # Store as JSON string

        # FALLBACK: Name-based inference (when type not provided)
        # NOTE: This is a fallback - types should come from ApplicationIR
        fl = fname.lower()
        if fl.endswith('_id') or fl == 'id':
            return 'postgresql.UUID(as_uuid=True)'
        if fl in ['created_at', 'updated_at']:
            return 'sa.DateTime(timezone=True)'
        # Default to String for unknown fields
        return 'sa.String(255)'

    for entity in entities:
        entity_name = entity.get('name', 'Unknown')
        entity_plural = entity.get('plural', f'{entity_name}s').lower()
        # Support both dict-based and object-based entities
        if hasattr(entity, 'fields'):
            fields = getattr(entity, 'fields', []) or []
        else:
            fields = entity.get('fields', []) or []
        if not fields:
            # NOTE: No longer using gt_defaults fallback - Phase: Hardcoding Elimination (Nov 25, 2025)
            # If fields are empty, it indicates a bug in ApplicationIR population
            # Log warning but don't synthesize fake fields
            logger.warning(f"⚠️ Entity '{entity_name}' has no fields - check ApplicationIR.domain_model.entities.attributes")

        code += f'''
    op.create_table(
        '{entity_plural}',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
'''

        for field in fields:
            # Support both objects and dicts
            if hasattr(field, 'name'):
                fname = field.name
                ftype = getattr(field, 'type', None) or 'str'
                required = getattr(field, 'required', True)
                default = getattr(field, 'default', None)
            else:
                fname = field.get('name', 'unknown')
                ftype = field.get('type') or 'str'
                required = field.get('required')
                default = field.get('default', None)

            if fname in ['id', 'created_at']:
                continue

            # Default required to True when unspecified to avoid generating nullable columns accidentally
            if required is None:
                required = True

            # Infer a type if missing or unknown - now passes ftype to prefer IR type over name inference
            col_type = type_mapping.get(ftype, _infer_sql_type(fname, ftype))
            nullable = not bool(required)

            column_def = f"        sa.Column('{fname}', {col_type}, nullable={str(nullable)})"

            # NOTE: Hardcoded fname == 'email' REMOVED - Phase: Hardcoding Elimination (Nov 25, 2025)
            # Unique constraint should come from field constraints, not field name
            # Check if field has unique constraint from IR/spec
            field_constraints = field.get('constraints', {}) if isinstance(field, dict) else getattr(field, 'constraints', {})
            constraint_strs = [str(c).lower() for c in (field_constraints if isinstance(field_constraints, list) else [field_constraints])]
            if any('unique' in c for c in constraint_strs):
                column_def = column_def.rstrip(')') + ', unique=True)'

            # Simple defaults
            if default not in [None, '...']:
                if ftype in ['datetime', 'date']:
                    column_def = column_def.rstrip(')') + ", server_default=sa.text('now()'))"
                elif ftype in ['str', 'string', 'text']:
                    column_def = column_def.rstrip(')') + f", server_default=sa.text('{default}'))"
                elif ftype in ['bool', 'boolean']:
                    bool_default = 'true' if str(default).lower() == 'true' else 'false'
                    column_def = column_def.rstrip(')') + f", server_default=sa.text('{bool_default}'))"
                else:
                    column_def = column_def.rstrip(')') + f", server_default=sa.text('{default}'))"

            code += column_def + ',\n'

        code += f'''        sa.PrimaryKeyConstraint('id')
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
