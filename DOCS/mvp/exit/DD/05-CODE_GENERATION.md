# Code Generation Pipeline

**Version**: 2.0
**Date**: November 2025
**Status**: Production

---

## Overview

DevMatrix generates production-ready code through a **stratified pipeline** that minimizes LLM usage by preferring deterministic generation (templates and AST) where possible.

---

## Generation Flow

```
ApplicationIR
      │
      v
┌─────────────────────────────────┐
│   StratifiedRouter              │
│   ├─ complexity == "template"   │──> TemplateGenerator
│   ├─ complexity == "ast"        │──> ASTGenerator
│   └─ complexity == "llm"        │──> LLMGenerator
└─────────────────────────────────┘
      │
      v
┌─────────────────────────────────┐
│   QA Validation                 │
│   ├─ py_compile                 │
│   ├─ AST parse                  │
│   ├─ Regression check           │
│   └─ IR compliance              │
└─────────────────────────────────┘
      │
      v
Generated Application
```

---

## Main Entry Point

**File**: `src/services/code_generation_service.py`

```python
async def generate_from_application_ir(
    self,
    app_ir: ApplicationIR,
    output_path: Path
) -> Dict[str, str]:
    """
    Generate complete application from ApplicationIR.

    Args:
        app_ir: The ApplicationIR containing all specifications
        output_path: Where to write generated files

    Returns:
        Dict mapping file paths to generated content
    """
    files_dict = {}

    # Phase 1: Generate entities from DomainModelIR
    entities_code = self._generate_entities_from_ir(app_ir.domain_model)
    files_dict["src/models/entities.py"] = entities_code

    # Phase 2: Generate schemas from APIModelIR
    schemas_code = self._generate_schemas_from_ir(app_ir.api_model)
    files_dict["src/models/schemas.py"] = schemas_code

    # Phase 3: Generate repositories
    repos_code = self._generate_repositories_from_ir(app_ir.domain_model)
    files_dict["src/repositories/"] = repos_code

    # Phase 4: Generate routes from APIModelIR
    routes_code = self._generate_routes_from_ir(app_ir.api_model)
    files_dict["src/routes/"] = routes_code

    # Phase 5: Generate services from BehaviorModelIR
    services_code = self._generate_services_from_ir(app_ir.behavior_model)
    files_dict["src/services/"] = services_code

    # Phase 6: Generate migrations
    migrations = self._generate_migrations_from_ir(app_ir.domain_model)
    files_dict["alembic/versions/"] = migrations

    # Phase 7: Generate infrastructure (TEMPLATE stratum)
    infra = self._generate_infrastructure()
    files_dict.update(infra)

    return files_dict
```

---

## AST Generators

**File**: `src/services/ast_generators.py`

### Entity Generation

```python
def generate_entity_class(entity: Entity) -> str:
    """Generate SQLAlchemy model from DomainModelIR entity."""
    imports = ["from sqlalchemy import Column, String, Integer, DateTime, ForeignKey"]
    lines = []

    lines.append(f"class {entity.name}(Base):")
    lines.append(f'    __tablename__ = "{entity.name.lower()}s"')
    lines.append("")

    for attr in entity.attributes:
        column_def = _generate_column(attr)
        lines.append(f"    {attr.name} = {column_def}")

    return "\n".join(imports + [""] + lines)

def _generate_column(attr: Attribute) -> str:
    """Generate SQLAlchemy Column definition."""
    type_mapping = {
        "str": "String(255)",
        "int": "Integer",
        "float": "Numeric(10, 2)",
        "bool": "Boolean",
        "datetime": "DateTime(timezone=True)",
        "uuid": "UUID(as_uuid=True)",
        "decimal": "Numeric(10, 2)"
    }

    col_type = type_mapping.get(attr.type, "String(255)")
    parts = [f"Column({col_type}"]

    if attr.name == "id":
        parts.append("primary_key=True")
    if not attr.nullable:
        parts.append("nullable=False")
    if attr.default is not None:
        parts.append(f"default={repr(attr.default)}")

    return ", ".join(parts) + ")"
```

### Schema Generation

```python
def generate_pydantic_schemas(entity: Entity) -> Dict[str, str]:
    """Generate Pydantic schemas (*Base, *Create, *Update, *Read)."""
    schemas = {}

    # Base schema (shared fields)
    base_fields = [f for f in entity.attributes if not f.auto_generated]
    schemas[f"{entity.name}Base"] = _generate_schema_class(
        f"{entity.name}Base",
        base_fields,
        all_optional=False
    )

    # Create schema (required fields)
    schemas[f"{entity.name}Create"] = _generate_schema_class(
        f"{entity.name}Create",
        base_fields,
        all_optional=False,
        parent=f"{entity.name}Base"
    )

    # Update schema (all optional for partial updates)
    schemas[f"{entity.name}Update"] = _generate_schema_class(
        f"{entity.name}Update",
        base_fields,
        all_optional=True
    )

    # Read schema (includes auto-generated fields)
    schemas[f"{entity.name}Read"] = _generate_schema_class(
        f"{entity.name}Read",
        entity.attributes,
        all_optional=False,
        parent=f"{entity.name}Base"
    )

    return schemas
```

---

## Template Generator

**File**: `src/services/template_generator.py`

Templates are pre-tested, immutable code patterns:

```python
TEMPLATE_CATEGORIES = [
    "infrastructure/docker",
    "infrastructure/observability",
    "core/config",
    "core/database",
    "models/base",
    "repository/generic",
    "routes/health",
    "project/structure"
]

PROTECTED_PATHS = [
    "docker-compose.yml",
    "Dockerfile",
    "prometheus.yml",
    "src/core/config.py",
    "src/core/database.py",
    "src/models/base.py",
    "src/routes/health.py"
]

def generate_from_template(template_name: str, context: dict) -> str:
    """Load and render a template with context."""
    template_path = TEMPLATE_DIR / f"{template_name}.jinja2"
    template = env.get_template(str(template_path))
    return template.render(**context)
```

---

## LLM Generator

**File**: `src/services/llm_generator.py`

LLM is used only for complex business logic:

```python
LLM_ALLOWED_SLOTS = [
    "services/*_flow_methods.py",
    "services/*_business_rules.py",
    "routes/*_custom_endpoints.py",
    "repair_patches/*.py"
]

async def generate_with_llm(
    slot: str,
    ir_context: ApplicationIR,
    existing_code: Optional[str] = None
) -> str:
    """Generate code using LLM within allowed slots."""
    assert slot in LLM_ALLOWED_SLOTS, f"LLM cannot write to {slot}"

    prompt = f"""
    Generate ONLY the business logic for: {slot}

    IR Context:
    - Entities: {ir_context.domain_model.entities}
    - Flows: {ir_context.behavior_model.flows}
    - Invariants: {ir_context.behavior_model.invariants}

    Constraints:
    - Do NOT modify infrastructure, models, or CRUD
    - Work within the existing structure
    - Follow existing patterns
    """

    response = await llm_client.generate(prompt, model="claude-haiku-4-5-20251001")
    return response.content
```

---

## Bug Fixes Applied

### Bug #1: requirements.txt Not Generated

**Root Cause**: `generate_from_application_ir()` was missing call to `_generate_with_llm_fallback()`

**Fix**: Added call after `_compose_patterns()`:
```python
llm_generated = await self._generate_with_llm_fallback(
    files_dict,
    spec_requirements=None,
    application_ir=app_ir
)
files_dict.update(llm_generated)
```

### Bug #2: Route<->Service Method Mismatch

**Root Cause**: Route called `service.get_all()` but Service template uses `service.list()`

**Fix**: Updated route generator:
```python
# Before:
body += f'''    {entity_plural} = await service.get_all(skip=0, limit=100)'''
# After:
body += f'''    result = await service.list(page=1, size=100)
return result.items'''
```

### Bug #3: PUT Using Wrong Schema

**Root Cause**: PUT used `*Create` schema instead of `*Update`

**Fix**:
```python
if method == 'post':
    params.append(f'{entity_snake}_data: {entity.name}Create')
elif method == 'put':
    params.append(f'{entity_snake}_data: {entity.name}Update')
```

### Bug #4: Missing Custom Operations

**Root Cause**: Only 5 CRUD operations handled; `deactivate`, `clear` ignored

**Fix**: Added handlers for custom operations in `ModularArchitectureGenerator`

### Bug #5: Dead Code (pass only)

**Root Cause**: `CodeRepairAgent` generated placeholder endpoints with only `pass`

**Fix**: Generate real code or raise `NotImplementedError` with clear message

### Bug #6: REG-010 False Positives

**Root Cause**: Regex `\.\.\.` caught valid Pydantic `Field(...)`

**Fix**: Updated pattern to exclude Field context:
```python
"pattern": r"(?<![Ff]ield\()\.\.\.(?!\s*,|\s*\))|(?<!\w)Ellipsis(?!\w)"
```

### Bug #7: IR Compliance Always 0%

**Root Cause**: Looking at wrong attribute (`self.precision.ir_compliance_relaxed`)

**Fix**: Use correct source `self.ir_compliance_metrics.relaxed_overall`

---

## Hardcoding Elimination

**Status**: COMPLETED

All e-commerce-specific hardcoding has been removed:

| Before | After |
|--------|-------|
| Constraint detection by field name | Constraint detection from IR |
| Type detection by field name pattern | Type detection from IR type |
| Entity-specific logic by entity name | Entity-specific logic from field presence |

**Impact**: Pipeline generates correct code for ANY domain spec, not just e-commerce.

---

## Output Structure

```
generated_app/
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── dependencies.py
│   ├── models/
│   │   ├── base.py
│   │   ├── entities.py
│   │   └── schemas.py
│   ├── repositories/
│   │   └── {entity}_repository.py
│   ├── services/
│   │   └── {entity}_service.py
│   └── routes/
│       ├── health.py
│       └── {entity}_router.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── generated/
├── alembic/
│   ├── env.py
│   └── versions/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── pyproject.toml
├── generation_manifest.json
├── stratum_metrics.json
└── quality_gate.json
```

---

## Related Documentation

- [02-ARCHITECTURE.md](02-ARCHITECTURE.md) - Stratified architecture
- [04-IR_SYSTEM.md](04-IR_SYSTEM.md) - ApplicationIR
- [06-VALIDATION.md](06-VALIDATION.md) - Validation system

---

*DevMatrix - Code Generation Pipeline*
