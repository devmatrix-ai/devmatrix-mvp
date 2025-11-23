# Component: SpecParser

**Module**: `src/parsing/spec_parser.py`
**Phase**: 1 (Spec Ingestion)
**Status**: ✅ Core Required Component

---

## Purpose

SpecParser extracts structured requirements from Markdown specification files. It parses raw Markdown text and converts it into a strongly-typed SpecRequirements object with clear categories:
- Requirements (functional & non-functional)
- Entities
- Endpoints
- Business Logic

## Role in Pipeline

```
Input: Markdown spec file
    ↓
[SpecParser.parse()]
    ↓
Output: SpecRequirements object
    ↓
Consumed by: Phase 2 (RequirementsClassifier)
```

## Key Methods

### Main Method: `parse(spec_path: str) → SpecRequirements`

**Purpose**: Parse a Markdown specification file into structured requirements

**Input**:
- `spec_path` (str): Path to `.md` specification file

**Output**:
```python
class SpecRequirements:
    requirements: List[Requirement]      # All extracted requirements
    entities: List[Entity]               # Data models
    endpoints: List[Endpoint]            # API endpoints
    business_logic: List[BusinessLogicRule]  # Workflows and rules
```

**Usage in Pipeline** (Phase 1, line 710-711):
```python
parser = SpecParser()
self.spec_requirements = parser.parse(spec_path)
```

## Specification Format

### Input: Markdown Structure

The component expects Markdown files with clear sections:

```markdown
# Project Name: Task Management API

## Entities

### User
- email (string, required, unique)
- password (string, hashed)
- name (string, 100 chars)

### Task
- title (string, 1-255 chars)
- description (text)
- status (enum: TODO, IN_PROGRESS, DONE)
- owner_id (UUID, foreign key → User)

## Endpoints

### Users
- GET /api/users - List all users
- POST /api/users - Create user (email, password, name)
- GET /api/users/{id} - Get user by ID
- PATCH /api/users/{id} - Update user
- DELETE /api/users/{id} - Delete user

### Tasks
- GET /api/tasks - List tasks (query: owner_id, status)
- POST /api/tasks - Create task (title, description, owner_id)
- GET /api/tasks/{id} - Get task
- PATCH /api/tasks/{id} - Update task (title, description, status)
- DELETE /api/tasks/{id} - Delete task

## Business Logic

- Task status workflow: TODO → IN_PROGRESS → DONE
- Only task owner can modify task
- Deleting user cascades to their tasks
- Task must belong to a valid user
```

### Output: Structured Objects

```python
SpecRequirements {
    requirements: [
        Requirement {
            id: "F1",
            type: "functional",
            description: "User registration with email verification",
            priority: "high"
        },
        Requirement {
            id: "NF1",
            type: "non_functional",
            description: "Response time < 200ms",
            priority: "medium"
        }
    ],

    entities: [
        Entity {
            name: "User",
            fields: {
                "email": FieldDefinition(type="string", required=True, unique=True),
                "password": FieldDefinition(type="string", required=True),
                "name": FieldDefinition(type="string", max_length=100)
            }
        },
        Entity {
            name: "Task",
            fields: {
                "title": FieldDefinition(type="string", min_length=1, max_length=255),
                "status": FieldDefinition(
                    type="enum",
                    values=["TODO", "IN_PROGRESS", "DONE"]
                ),
                "owner_id": FieldDefinition(
                    type="uuid",
                    foreign_key="User.id"
                )
            }
        }
    ],

    endpoints: [
        Endpoint {
            method: "POST",
            path: "/api/users",
            purpose: "Create user",
            required_params: ["email", "password", "name"],
            response_type: "User"
        },
        Endpoint {
            method: "GET",
            path: "/api/tasks",
            purpose: "List tasks",
            query_params: ["owner_id", "status"],
            response_type: "Task[]"
        }
    ],

    business_logic: [
        BusinessLogicRule {
            description: "Task status workflow",
            transitions: {
                "TODO": ["IN_PROGRESS"],
                "IN_PROGRESS": ["DONE"],
                "DONE": []
            }
        },
        BusinessLogicRule {
            description: "Only task owner can modify",
            condition: "current_user_id == task.owner_id",
            applies_to: ["PATCH /api/tasks/{id}", "DELETE /api/tasks/{id}"]
        }
    ]
}
```

## Data Extraction Details

### Entities Extraction
- Looks for "## Entities" section
- Parses entity definitions with fields and constraints
- Extracts field types, validation rules, relationships

### Endpoints Extraction
- Looks for "## Endpoints" section
- Parses HTTP method, path, parameters
- Extracts request/response types
- Identifies required vs optional parameters

### Business Logic Extraction
- Looks for "## Business Logic" section
- Parses workflows, state machines, rules
- Extracts validation constraints
- Identifies access control rules

### Requirements Generation
- Creates one requirement per entity
- Creates one requirement per endpoint
- Creates one requirement per business logic rule
- Tags as "functional" or "non_functional"

## Metrics Collected

In Phase 1 (line 722-729):
```python
metrics_collector.add_checkpoint("spec_ingestion", "CP-1.2: Requirements extracted", {
    "total_requirements": len(self.spec_requirements.requirements),
    "functional_requirements": functional_count,
    "non_functional_requirements": non_functional_count,
    "entities": entity_count,
    "endpoints": endpoint_count,
    "business_logic": business_logic_count
})
```

Example metrics:
```
Total requirements: 25
Functional requirements: 18
Non-functional requirements: 7
Entities: 4
Endpoints: 15
Business logic rules: 8
```

## Integration Points

### Input from
- User-provided Markdown specification file

### Output to
- Phase 2: RequirementsClassifier (receives SpecRequirements)
- Throughout: Metrics collector

### Produces
- `SpecRequirements` object (lines 711-714)
- Metrics checkpoint (lines 722-729)
- Processed requirements list (line 714)

## Error Handling

### File Not Found
```python
if not os.path.exists(spec_path):
    raise FileNotFoundError(f"Spec file not found: {spec_path}")
```

### Invalid Markdown Structure
```python
if not has_entities_section and not has_endpoints_section:
    raise ValueError("Spec must have Entities or Endpoints section")
```

### Missing Required Fields
```python
if not entity.has_primary_key():
    warnings.warn(f"Entity {entity.name} has no primary key")
```

## Usage Example

```python
from src.parsing.spec_parser import SpecParser

# Initialize parser
parser = SpecParser()

# Parse specification
spec = parser.parse("/path/to/spec.md")

# Access structured data
print(f"Total requirements: {len(spec.requirements)}")
print(f"Entities: {[e.name for e in spec.entities]}")
print(f"Endpoints: {[(e.method, e.path) for e in spec.endpoints]}")

# Iterate through requirements
for req in spec.requirements:
    print(f"  {req.id}: {req.description} ({req.type})")
```

## Performance Characteristics

- **Time**: ~100-500ms (depending on spec size)
- **Memory**: ~5-20 MB (spec in memory)
- **I/O**: Single file read from disk
- **Complexity**: O(n) where n = lines in spec file

## Success Criteria

✅ Reads valid Markdown spec file
✅ Extracts all entities and fields
✅ Extracts all endpoints and parameters
✅ Extracts all business logic rules
✅ Creates requirement objects for each item
✅ Builds dependency relationships
✅ Returns valid SpecRequirements object
✅ Metrics collected successfully

## Typical Output

```
Phase 1: Spec Ingestion (Enhanced with SpecParser)
  ✓ Spec content loaded
  ✓ Specification parsed with SpecParser
    - Functional requirements: 18
    - Non-functional requirements: 7
    - Entities: 4 (User, Task, Project, Comment)
    - Endpoints: 15 (5 User, 5 Task, 3 Project, 2 Comment)
    - Business logic rules: 8
  ✓ Context loaded
  ✓ Complexity assessed: 0.65
```

## Known Limitations

- ⚠️ Expects specific Markdown section headers
- ⚠️ Cannot infer types not explicitly specified
- ⚠️ Field descriptions limited to simple formats
- ⚠️ Complex validation rules may not parse correctly

## Next Component

Output (SpecRequirements) feeds to **Phase 2: RequirementsClassifier** which:
- Classifies requirements by domain
- Builds dependency graphs
- Organizes requirements by priority
- Validates semantic correctness

---

**Last Updated**: 2025-11-23
**Source**: tests/e2e/real_e2e_full_pipeline.py:710-714
**Status**: Verified ✅
