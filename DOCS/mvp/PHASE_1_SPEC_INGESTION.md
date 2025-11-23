# Phase 1: Spec Ingestion

**Purpose**: Read and parse Markdown specification into structured requirements

**Status**: ✅ Core (Required)

---

## Overview

Phase 1 reads a Markdown specification file and extracts structured requirements data. It transforms unstructured text into a machine-readable `SpecRequirements` object containing entities, endpoints, validations, and business logic.

## Input

- **Format**: Markdown file (`.md`)
- **Location**: User-provided file path
- **Content Structure**:
  - Entity definitions (fields, types, constraints)
  - Endpoint specifications (method, path, auth)
  - Validation rules (constraints, error messages)
  - Business logic and workflows

## Processing

```python
async def _phase_1_spec_ingestion(self):
    # 1. Read markdown spec file
    spec_path = Path(self.spec_file)
    with open(spec_path, 'r') as f:
        self.spec_content = f.read()

    # 2. Parse with SpecParser
    parser = SpecParser()
    self.spec_requirements = parser.parse(spec_path)

    # 3. Extract structured data
    - self.requirements: List of requirement descriptions (backward compatibility)
    - self.spec_requirements: SpecRequirements object with:
        - entities: List[EntityRequirement]
        - endpoints: List[EndpointRequirement]
        - business_logic: List[BusinessRule]
        - validations: List[Validation]
        - metadata: Dict of spec metadata
```

## Output

### Data Structure: SpecRequirements

```python
class SpecRequirements:
    requirements: List[Requirement]      # All requirements
    entities: List[Entity]               # Data models
    endpoints: List[Endpoint]            # API routes
    business_logic: List[BusinessRule]   # Validation/workflow rules
    validations: List[Validation]        # Constraints
    metadata: Dict[str, Any]             # Spec metadata
```

### Metrics Collected

- Total requirements count
- Functional vs non-functional split
- Entity count
- Endpoint count
- Business logic rule count
- Complexity score (0.0-1.0)

## Service Dependencies

### Required
- **SpecParser** (`src/parsing/spec_parser.py`)
  - Parses Markdown syntax
  - Extracts structured requirements
  - Validates spec format

### Optional
- None

## Contract Validation

Phase 1 output is validated with:
- Total requirements > 0
- At least 1 entity OR 1 endpoint
- Metadata present
- All required fields populated

## Complexity Calculation

```python
base_complexity = min(len(spec_content) / 5000, 1.0)
entity_complexity = min(entity_count / 10, 0.3)
endpoint_complexity = min(endpoint_count / 20, 0.3)
total_complexity = min(base_complexity + entity_complexity + endpoint_complexity, 1.0)
```

Higher complexity triggers:
- More aggressive parallelization in later phases
- Additional validation checkpoints
- More detailed metrics collection

## Data Flow

```
Markdown Spec File
    ↓
    └─ SpecParser.parse()
        ├─ Extract entities
        ├─ Extract endpoints
        ├─ Extract validations
        └─ Extract business logic
            ↓
        SpecRequirements object
            ↓
            Feeds to Phase 2 (Requirements Analysis)
```

## Typical Markdown Spec Format

```markdown
# FastAPI REST API - Task Management

## Entities

**E1. User**
- id: UUID (primary key)
- email: str (unique, not null)
- username: str (unique)
- password_hash: str
- created_at: datetime (default: now)

**E2. Task**
- id: UUID (primary key)
- title: str (1-255 characters)
- status: enum (TODO, IN_PROGRESS, DONE)
- user_id: UUID (foreign key → User)

### Relationships
- User → Task (one-to-many, cascade delete)

## Endpoints

**EP1. Create User**
- Method: POST
- Path: /api/users
- Parameters: email, username, password
- Returns: User object
- Auth: None

**EP2. List Tasks**
- Method: GET
- Path: /api/tasks?user_id=X&status=Y
- Returns: List[Task]
- Auth: Required (JWT)

## Business Logic

**BL1. Task Title Validation**
- Title must be 1-255 characters
- Error if violation: "Invalid title length"

**BL2. Task Status Workflow**
- Can only transition: TODO → IN_PROGRESS → DONE
- Cannot skip or go backwards
```

## Success Criteria

✅ SpecRequirements object created successfully
✅ All entities extracted and parsed
✅ All endpoints extracted with full metadata
✅ Contract validation passed
✅ Complexity score calculated
✅ Metrics collected and logged

## Performance Characteristics

- **Time**: ~0.5-2 seconds (depends on spec size)
- **Memory**: ~5-50 MB (depends on spec complexity)
- **I/O**: Single file read operation

## Error Handling

### Missing or Invalid Spec File
```python
FileNotFoundError: Spec file not found at {path}
```
**Resolution**: Verify file path and permissions

### Invalid Spec Format
```python
ValueError: Spec does not match expected Markdown format
```
**Resolution**: Check spec follows SpecParser syntax requirements

### Missing Required Sections
```python
ValueError: No entities or endpoints found in specification
```
**Resolution**: Ensure spec contains at least E1+ entity OR EP1+ endpoint

## What's Extracted

| Element | Count | Example |
|---------|-------|---------|
| Entities | 2-20 | User, Task, Organization |
| Endpoints | 5-50 | GET /api/users, POST /api/tasks |
| Validations | 3-30 | Email format, range checks |
| Business Logic | 2-20 | Workflow rules, constraints |

## Integration Points

- **Phase 2**: Receives SpecRequirements for classification
- **Phase 6**: Receives spec for code generation templates
- **Phase 7**: Receives spec for compliance validation
- **Metrics**: Used to calculate overall project complexity

## Known Limitations

- ❌ Does not validate Markdown syntax (relies on SpecParser)
- ❌ Does not check for duplicate entity/endpoint names
- ❌ Does not resolve circular dependencies
- ⚠️ Assumes UTF-8 encoding

## Next Phase

Output feeds to **Phase 2: Requirements Analysis** which classifies each requirement by:
- Domain (CRUD, Auth, Payment, etc.)
- Priority (MUST, SHOULD, COULD)
- Complexity (estimated effort)
- Dependencies (on other requirements)

---

**Last Updated**: 2025-11-23
**Source**: tests/e2e/real_e2e_full_pipeline.py:687-776
**Status**: Verified ✅
