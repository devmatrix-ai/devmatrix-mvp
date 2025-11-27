"""
AST Generators - Pure Deterministic IR→Code Functions

Phase 0.5.3: Extract LLM-free code generation logic into pure functions.

These functions are:
- DETERMINISTIC: Same IR input → Same code output
- LLM-FREE: No LLM calls, no randomness
- TESTABLE: Each function can be unit tested independently
- COMPOSABLE: Can be combined to build complete files

Stratum: AST (deterministic transforms from ApplicationIR)
"""

import logging
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# TYPE MAPPINGS (Single Source of Truth)
# =============================================================================

SQL_TYPE_MAP: Dict[str, str] = {
    # UUID types
    "uuid": "UUID(as_uuid=True)",
    "UUID": "UUID(as_uuid=True)",

    # String types
    "str": "String(255)",
    "string": "String(255)",
    "text": "Text",
    "email": "String(255)",

    # Numeric types
    "int": "Integer",
    "integer": "Integer",
    "float": "Numeric(10, 2)",
    "decimal": "Numeric(10, 2)",
    "Decimal": "Numeric(10, 2)",

    # Boolean
    "bool": "Boolean",
    "boolean": "Boolean",

    # Date/Time
    "datetime": "DateTime(timezone=True)",
    "date": "DateTime(timezone=True)",
    "timestamp": "DateTime(timezone=True)",
}

PYDANTIC_TYPE_MAP: Dict[str, str] = {
    # UUID types
    "uuid": "UUID",
    "UUID": "UUID",

    # String types
    "str": "str",
    "string": "str",
    "text": "str",
    "email": "EmailStr",

    # Numeric types
    "int": "int",
    "integer": "int",
    "float": "Decimal",
    "decimal": "Decimal",
    "Decimal": "Decimal",

    # Boolean
    "bool": "bool",
    "boolean": "bool",

    # Date/Time
    "datetime": "datetime",
    "date": "datetime",
    "timestamp": "datetime",
}


class SchemaType(str, Enum):
    """Pydantic schema types for different operations."""
    CREATE = "create"
    UPDATE = "update"
    READ = "read"


# =============================================================================
# MIGRATION GENERATORS (Alembic)
# =============================================================================

def generate_migration_column(
    field_name: str,
    field_type: str,
    is_nullable: bool = True,
    is_unique: bool = False,
    default_value: Optional[Any] = None,
    is_primary_key: bool = False,
    is_server_default: bool = False,
) -> str:
    """
    Generate SQLAlchemy column definition for Alembic migration.

    DETERMINISTIC: IR.Attribute → sa.Column() string

    Args:
        field_name: Name of the column
        field_type: Type string (e.g., 'str', 'int', 'UUID')
        is_nullable: Whether column allows NULL
        is_unique: Whether column has unique constraint
        default_value: Default value (if any)
        is_primary_key: Whether column is primary key
        is_server_default: Whether default should use sa.text() for server-side

    Returns:
        Complete sa.Column() definition string
    """
    # Map type to SQLAlchemy type
    sql_type = SQL_TYPE_MAP.get(field_type, "String(255)")

    # Build column definition parts
    parts = [f"sa.Column('{field_name}', sa.{sql_type}"]

    # Add nullable
    if not is_nullable:
        parts.append("nullable=False")
    else:
        parts.append("nullable=True")

    # Add unique
    if is_unique:
        parts.append("unique=True")

    # Add primary key
    if is_primary_key:
        parts.append("primary_key=True")

    # Add default value
    if default_value is not None:
        if is_server_default:
            # Server-side default (SQL functions like NOW())
            # Use sa.text() for SQL expressions
            if _is_sql_function(default_value):
                parts.append(f"server_default=sa.text('{default_value}')")
            else:
                # Literal value - quote strings
                if isinstance(default_value, str):
                    parts.append(f"server_default='{default_value}'")
                else:
                    parts.append(f"server_default='{default_value}'")
        else:
            # Python-side default
            if isinstance(default_value, str):
                parts.append(f"default='{default_value}'")
            elif isinstance(default_value, bool):
                parts.append(f"default={default_value}")
            else:
                parts.append(f"default={default_value}")

    # Join parts
    column_def = ", ".join(parts) + ")"
    return column_def


def generate_migration_upgrade(
    table_name: str,
    columns: List[Dict[str, Any]],
) -> str:
    """
    Generate complete Alembic upgrade() function body.

    DETERMINISTIC: Table name + columns → Complete upgrade code

    Args:
        table_name: Name of the table
        columns: List of column definitions

    Returns:
        Complete upgrade() function body
    """
    lines = [f"    op.create_table('{table_name}',"]

    for col in columns:
        col_def = generate_migration_column(
            field_name=col.get("name"),
            field_type=col.get("type", "str"),
            is_nullable=col.get("nullable", True),
            is_unique=col.get("unique", False),
            default_value=col.get("default"),
            is_primary_key=col.get("primary_key", False),
            is_server_default=col.get("server_default", False),
        )
        lines.append(f"        {col_def},")

    lines.append("    )")
    return "\n".join(lines)


def generate_migration_downgrade(table_name: str) -> str:
    """
    Generate complete Alembic downgrade() function body.

    Args:
        table_name: Name of the table to drop

    Returns:
        Complete downgrade() function body
    """
    return f"    op.drop_table('{table_name}')"


def _is_sql_function(value: Any) -> bool:
    """Check if value looks like a SQL function (e.g., NOW(), UUID())."""
    if not isinstance(value, str):
        return False
    sql_functions = ["NOW()", "CURRENT_TIMESTAMP", "UUID()", "GEN_RANDOM_UUID()"]
    return value.upper() in sql_functions


# =============================================================================
# PYDANTIC SCHEMA GENERATORS
# =============================================================================

def generate_pydantic_field(
    field_name: str,
    field_type: str,
    schema_type: SchemaType,
    is_required: bool = True,
    default_value: Optional[Any] = None,
    description: Optional[str] = None,
    is_computed: bool = False,
    is_immutable: bool = False,
) -> Optional[str]:
    """
    Generate Pydantic field definition for a schema.

    DETERMINISTIC: IR.Attribute + schema_type → Pydantic field string

    Rules:
    - CREATE schema: Exclude id, created_at, updated_at (server-generated)
    - UPDATE schema: All fields optional, exclude immutable fields
    - READ schema: Include all fields

    Args:
        field_name: Name of the field
        field_type: Type string (e.g., 'str', 'int', 'UUID')
        schema_type: CREATE, UPDATE, or READ
        is_required: Whether field is required
        default_value: Default value (if any)
        description: Field description
        is_computed: Whether field is computed (server-side)
        is_immutable: Whether field cannot be updated

    Returns:
        Field definition string, or None if field should be excluded
    """
    # Determine if field should be excluded
    if _should_exclude_field(field_name, schema_type, is_computed, is_immutable):
        return None

    # Map type to Pydantic type
    pydantic_type = PYDANTIC_TYPE_MAP.get(field_type, "str")

    # Build field definition
    if schema_type == SchemaType.UPDATE:
        # UPDATE: All fields are optional
        type_annotation = f"Optional[{pydantic_type}]"
        default_part = " = None"
    elif schema_type == SchemaType.CREATE:
        # CREATE: Required fields don't have defaults
        if is_required and default_value is None:
            type_annotation = pydantic_type
            default_part = ""
        else:
            type_annotation = f"Optional[{pydantic_type}]"
            if default_value is not None:
                default_part = f" = {_format_default(default_value, field_type)}"
            else:
                default_part = " = None"
    else:
        # READ: All fields included
        type_annotation = pydantic_type
        default_part = ""

    # Add Field() with description if provided
    if description:
        return f"    {field_name}: {type_annotation} = Field({_format_default(default_value, field_type) if default_value else 'None' if 'Optional' in type_annotation else '...'}, description=\"{description}\")"
    else:
        return f"    {field_name}: {type_annotation}{default_part}"


def generate_pydantic_schema(
    entity_name: str,
    fields: List[Dict[str, Any]],
    schema_type: SchemaType,
    enforcement_rules: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate complete Pydantic schema class.

    DETERMINISTIC: Entity + fields + schema_type → Complete schema class

    Args:
        entity_name: Name of the entity (e.g., 'Product')
        fields: List of field definitions
        schema_type: CREATE, UPDATE, or READ
        enforcement_rules: Optional enforcement rules for immutable/computed fields

    Returns:
        Complete schema class definition
    """
    schema_suffix = {
        SchemaType.CREATE: "Create",
        SchemaType.UPDATE: "Update",
        SchemaType.READ: "Read",
    }

    class_name = f"{entity_name}{schema_suffix[schema_type]}"

    lines = [f"class {class_name}(BaseModel):"]
    lines.append(f'    """{schema_type.value.title()} schema for {entity_name}."""')

    # Generate fields
    field_lines = []
    for field in fields:
        field_name = field.get("name")

        # Get enforcement info
        is_computed = False
        is_immutable = False
        if enforcement_rules and field_name in enforcement_rules:
            rule = enforcement_rules[field_name]
            is_computed = rule.get("enforcement_type") == "computed_field"
            is_immutable = rule.get("enforcement_type") == "immutable"

        field_def = generate_pydantic_field(
            field_name=field_name,
            field_type=field.get("type", "str"),
            schema_type=schema_type,
            is_required=field.get("required", True),
            default_value=field.get("default"),
            description=field.get("description"),
            is_computed=is_computed,
            is_immutable=is_immutable,
        )

        if field_def:
            field_lines.append(field_def)

    if field_lines:
        lines.extend(field_lines)
    else:
        lines.append("    pass")

    return "\n".join(lines)


def _should_exclude_field(
    field_name: str,
    schema_type: SchemaType,
    is_computed: bool,
    is_immutable: bool,
) -> bool:
    """Determine if a field should be excluded from schema."""
    # System fields always excluded from CREATE
    system_fields = {"id", "created_at", "updated_at"}

    if schema_type == SchemaType.CREATE:
        if field_name in system_fields:
            return True
        if is_computed:
            return True

    if schema_type == SchemaType.UPDATE:
        if field_name in system_fields:
            return True
        if is_immutable:
            return True
        if is_computed:
            return True

    return False


def _format_default(value: Any, field_type: str) -> str:
    """Format default value for Pydantic field."""
    if value is None:
        return "None"
    if field_type in ("str", "string", "text", "email"):
        return f'"{value}"'
    if field_type in ("bool", "boolean"):
        return str(value).capitalize()
    return str(value)


# =============================================================================
# REPOSITORY GENERATORS
# =============================================================================

def generate_repository_method(
    entity_name: str,
    method_type: str,
) -> str:
    """
    Generate repository method for an entity.

    DETERMINISTIC: Entity + method_type → Repository method string

    Args:
        entity_name: Name of the entity (e.g., 'Product')
        method_type: One of 'list', 'get', 'create', 'update', 'delete'

    Returns:
        Complete method definition string
    """
    entity_lower = entity_name.lower()
    entity_class = f"{entity_name}Entity"

    methods = {
        "list": _generate_list_method(entity_name, entity_class),
        "get": _generate_get_method(entity_name, entity_class),
        "create": _generate_create_method(entity_name, entity_class),
        "update": _generate_update_method(entity_name, entity_class),
        "delete": _generate_delete_method(entity_name, entity_class),
    }

    return methods.get(method_type, "")


def generate_repository_class(
    entity_name: str,
    include_methods: Optional[List[str]] = None,
) -> str:
    """
    Generate complete repository class for an entity.

    DETERMINISTIC: Entity → Complete repository class

    Args:
        entity_name: Name of the entity (e.g., 'Product')
        include_methods: List of methods to include (default: all CRUD)

    Returns:
        Complete repository class definition
    """
    if include_methods is None:
        include_methods = ["list", "get", "create", "update", "delete"]

    entity_lower = entity_name.lower()
    entity_class = f"{entity_name}Entity"

    lines = [
        f"class {entity_name}Repository:",
        f'    """Repository for {entity_name} entity."""',
        "",
        "    def __init__(self, session: AsyncSession):",
        "        self.session = session",
        "",
    ]

    for method_type in include_methods:
        method_code = generate_repository_method(entity_name, method_type)
        if method_code:
            lines.append(method_code)
            lines.append("")

    return "\n".join(lines)


def _generate_list_method(entity_name: str, entity_class: str) -> str:
    """Generate list method."""
    return f'''    async def list_{entity_name.lower()}s(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[{entity_class}]:
        """List all {entity_name.lower()}s with pagination."""
        query = select({entity_class}).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()'''


def _generate_get_method(entity_name: str, entity_class: str) -> str:
    """Generate get method."""
    return f'''    async def get_{entity_name.lower()}(
        self,
        {entity_name.lower()}_id: UUID,
    ) -> Optional[{entity_class}]:
        """Get {entity_name.lower()} by ID."""
        query = select({entity_class}).where({entity_class}.id == {entity_name.lower()}_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()'''


def _generate_create_method(entity_name: str, entity_class: str) -> str:
    """Generate create method."""
    return f'''    async def create_{entity_name.lower()}(
        self,
        data: {entity_name}Create,
    ) -> {entity_class}:
        """Create new {entity_name.lower()}."""
        db_obj = {entity_class}(**data.model_dump())
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj'''


def _generate_update_method(entity_name: str, entity_class: str) -> str:
    """Generate update method."""
    return f'''    async def update_{entity_name.lower()}(
        self,
        {entity_name.lower()}_id: UUID,
        data: {entity_name}Update,
    ) -> Optional[{entity_class}]:
        """Update existing {entity_name.lower()}."""
        db_obj = await self.get_{entity_name.lower()}({entity_name.lower()}_id)
        if not db_obj:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj'''


def _generate_delete_method(entity_name: str, entity_class: str) -> str:
    """Generate delete method."""
    return f'''    async def delete_{entity_name.lower()}(
        self,
        {entity_name.lower()}_id: UUID,
    ) -> bool:
        """Delete {entity_name.lower()} by ID."""
        db_obj = await self.get_{entity_name.lower()}({entity_name.lower()}_id)
        if not db_obj:
            return False
        await self.session.delete(db_obj)
        await self.session.commit()
        return True'''


# =============================================================================
# ROUTE GENERATORS (CRUD Endpoints)
# =============================================================================

def generate_crud_route(
    entity_name: str,
    method: str,
    path: str,
) -> str:
    """
    Generate CRUD route handler.

    DETERMINISTIC: Entity + HTTP method + path → Route handler

    Args:
        entity_name: Name of the entity (e.g., 'Product')
        method: HTTP method ('GET', 'POST', 'PUT', 'DELETE')
        path: Route path (e.g., '/', '/{id}')

    Returns:
        Complete route handler definition
    """
    entity_lower = entity_name.lower()
    entity_plural = f"{entity_lower}s"

    if method == "GET" and path == "/":
        return _generate_list_route(entity_name, entity_plural)
    elif method == "GET" and "{id}" in path:
        return _generate_get_route(entity_name, entity_plural)
    elif method == "POST" and path == "/":
        return _generate_create_route(entity_name, entity_plural)
    elif method == "PUT" and "{id}" in path:
        return _generate_update_route(entity_name, entity_plural)
    elif method == "DELETE" and "{id}" in path:
        return _generate_delete_route(entity_name, entity_plural)

    return ""


def _generate_list_route(entity_name: str, entity_plural: str) -> str:
    """Generate list route handler."""
    return f'''@router.get("/", response_model=List[{entity_name}Read])
async def list_{entity_plural}(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """List all {entity_plural}."""
    repo = {entity_name}Repository(db)
    return await repo.list_{entity_plural}(skip=skip, limit=limit)'''


def _generate_get_route(entity_name: str, entity_plural: str) -> str:
    """Generate get route handler."""
    entity_lower = entity_name.lower()
    return f'''@router.get("/{{id}}", response_model={entity_name}Read)
async def get_{entity_lower}(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get {entity_lower} by ID."""
    repo = {entity_name}Repository(db)
    obj = await repo.get_{entity_lower}(id)
    if not obj:
        raise HTTPException(status_code=404, detail="{entity_name} not found")
    return obj'''


def _generate_create_route(entity_name: str, entity_plural: str) -> str:
    """Generate create route handler."""
    entity_lower = entity_name.lower()
    return f'''@router.post("/", response_model={entity_name}Read, status_code=201)
async def create_{entity_lower}(
    data: {entity_name}Create,
    db: AsyncSession = Depends(get_db),
):
    """Create new {entity_lower}."""
    repo = {entity_name}Repository(db)
    return await repo.create_{entity_lower}(data)'''


def _generate_update_route(entity_name: str, entity_plural: str) -> str:
    """Generate update route handler."""
    entity_lower = entity_name.lower()
    return f'''@router.put("/{{id}}", response_model={entity_name}Read)
async def update_{entity_lower}(
    id: UUID,
    data: {entity_name}Update,
    db: AsyncSession = Depends(get_db),
):
    """Update {entity_lower}."""
    repo = {entity_name}Repository(db)
    obj = await repo.update_{entity_lower}(id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="{entity_name} not found")
    return obj'''


def _generate_delete_route(entity_name: str, entity_plural: str) -> str:
    """Generate delete route handler."""
    entity_lower = entity_name.lower()
    return f'''@router.delete("/{{id}}", status_code=204)
async def delete_{entity_lower}(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete {entity_lower}."""
    repo = {entity_name}Repository(db)
    if not await repo.delete_{entity_lower}(id):
        raise HTTPException(status_code=404, detail="{entity_name} not found")'''


# =============================================================================
# UTILITY: IR TO CODE CONVERSION
# =============================================================================

def ir_attribute_to_sql_column(
    attr_name: str,
    attr_type: str,
    is_nullable: bool,
    is_unique: bool,
    default: Optional[Any],
) -> str:
    """
    Convert IR Attribute to SQLAlchemy Column definition.

    This is the SINGLE FUNCTION that should be used for entity generation.

    Args:
        attr_name: Attribute name
        attr_type: IR type string
        is_nullable: Whether nullable
        is_unique: Whether unique
        default: Default value

    Returns:
        SQLAlchemy Column definition string
    """
    sql_type = SQL_TYPE_MAP.get(attr_type.lower(), "String(255)")

    parts = [f"Column({sql_type}"]

    if not is_nullable:
        parts.append("nullable=False")

    if is_unique:
        parts.append("unique=True")

    if default is not None:
        if isinstance(default, str):
            parts.append(f'default="{default}"')
        else:
            parts.append(f"default={default}")

    return ", ".join(parts) + ")"


def ir_attribute_to_pydantic_field(
    attr_name: str,
    attr_type: str,
    is_required: bool,
    default: Optional[Any],
    schema_type: SchemaType,
) -> Optional[str]:
    """
    Convert IR Attribute to Pydantic field definition.

    This is the SINGLE FUNCTION for schema field generation.

    Args:
        attr_name: Attribute name
        attr_type: IR type string
        is_required: Whether required
        default: Default value
        schema_type: CREATE, UPDATE, or READ

    Returns:
        Pydantic field definition or None if excluded
    """
    return generate_pydantic_field(
        field_name=attr_name,
        field_type=attr_type,
        schema_type=schema_type,
        is_required=is_required,
        default_value=default,
    )
