# Phase 6: Code Generation

**Purpose**: Generate production-ready Python code from atomic units

**Status**: ✅ Optional (Graceful degradation if unavailable - but requires real code)

---

## Overview

Phase 6 is the core code generation phase. It calls Claude API to generate real, production-quality code for each atomic unit. Code is generated in dependency order (wave by wave) to enable parallelization.

## Input

- **Source**: ExecutionDAG from Phase 5
- **Contains**: Atomic units organized into execution waves

## Processing

```python
async def _phase_6_code_generation(self):
    # 1. Validate prerequisites
    if not code_generator:
        raise ValueError("CodeGenerationService not initialized")
    if not spec_requirements:
        raise ValueError("SpecRequirements not available")

    # 2. For each wave in execution order
    for wave_num, wave_atoms in enumerate(dag.waves):
        # 3. Generate code for each atom in parallel
        generated_code = await code_generator.generate_from_requirements(
            spec_requirements,
            allow_syntax_errors=True  # Let repair loop fix issues
        )

    # 4. Parse generated code into file structure
    generated_files = parse_code_to_files(generated_code)
```

## Output

### Generated Code

```python
class GeneratedCode:
    file_structure: Dict[str, str]  # {filepath: code_content}
    files: List[str]                # ["models/user.py", "api/routes.py", ...]
    total_lines: int                # Total LOC generated
    by_type: Dict[str, int]         # {type: LOC}
```

### File Structure Generated

```
project/
├── src/
│   ├── models/
│   │   ├── user.py          # SQLAlchemy models
│   │   ├── task.py
│   │   └── __init__.py
│   ├── api/
│   │   ├── routes/
│   │   │   ├── users.py     # FastAPI endpoints
│   │   │   ├── tasks.py
│   │   │   └── __init__.py
│   │   ├── schemas/
│   │   │   ├── user.py      # Pydantic request/response
│   │   │   ├── task.py
│   │   │   └── __init__.py
│   │   └── __init__.py
│   ├── validations/
│   │   ├── user.py          # Business logic validation
│   │   ├── task.py
│   │   └── __init__.py
│   ├── config.py            # Configuration
│   ├── main.py              # FastAPI app entry
│   └── database.py          # Database setup
├── tests/
│   ├── test_models.py       # Unit tests
│   ├── test_users.py        # API endpoint tests
│   ├── test_tasks.py
│   └── conftest.py
├── migrations/
│   ├── alembic.ini
│   └── versions/            # Alembic migration files
├── docs/
│   ├── API.md               # Generated API documentation
│   ├── ENTITIES.md
│   └── ARCHITECTURE.md
├── requirements.txt         # Python dependencies
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Service Dependencies

### Required
- **CodeGenerationService** (`src/services/code_generation_service.py`)
  - Claude API integration
  - Code generation from requirements
  - Multi-format support (Python, SQL, etc.)
  - Error handling and retries

### Optional
- **PatternBank** (`src/cognitive/patterns/pattern_bank.py`)
  - Provide pattern templates
  - Improve code consistency
  - Reduce generation time

## Code Generation Flow

```
ExecutionDAG with Waves
    ↓
    For Wave 1, 2, 3, ... N:
        └─ For each atomic unit in wave:
            ├─ Generate function/method/class
            ├─ Include error handling
            ├─ Add type hints
            ├─ Add docstrings
            └─ Combine with other atoms
                ↓
            Wave-level code artifact
                ↓
    Combine all waves
        ↓
    Parse into file structure
        ↓
    Generated Project Files
```

## Generation Strategy

### By Wave

```
Wave 1 generation (parallel, 10-20 seconds):
  - User model
  - Task model
  - Database schema
  ├─ All can run simultaneously
  └─ No dependencies

Wave 2 generation (parallel, 15-25 seconds):
  - User endpoints
  - Task endpoints
  - Auth middleware
  ├─ Depends on Wave 1 models
  └─ All can run simultaneously

Wave 3+: Progressive composition
```

### By File Type

| Type | Generated | Example |
|------|-----------|---------|
| **Models** | SQLAlchemy ORM | User, Task, Organization |
| **Schemas** | Pydantic | UserCreate, UserResponse |
| **Routes** | FastAPI endpoints | GET /api/users, POST /api/tasks |
| **Validations** | Business logic | Email validation, status checks |
| **Tests** | Pytest | test_user_creation, test_auth |
| **Migrations** | Alembic | 001_create_users_table.py |
| **Config** | Settings | Database URL, API keys |
| **Docs** | Markdown | API documentation, guides |

## Code Quality Standards

Generated code includes:
- ✅ Type hints (mypy compatible)
- ✅ Docstrings (Google style)
- ✅ Error handling (try/except)
- ✅ Input validation (Pydantic)
- ✅ Proper imports
- ✅ Following PEP 8 style
- ✅ Security best practices

## Metrics Collected

- Total files generated
- Total lines of code
- Generation time per wave
- Generation time per file type
- LOC distribution by type
- Syntax errors (if any)
- Syntax error rate

## Performance Characteristics

- **Time**: 10-20 seconds per wave (LLM dependent)
- **Memory**: ~200-500 MB
- **API Calls**: 5-50 Claude API calls
- **Cost**: $1-5 per project (LLM dependent)

## Error Handling

### Syntax Errors
- Generated with `allow_syntax_errors=True`
- Intentionally allows imperfect code
- Phase 6.5 (Code Repair) fixes syntax issues
- Tests validate after repair

### Generation Failure
```python
ValueError: Code generation from requirements failed: {error}
```
**Resolution**: Check logs, verify spec format, retry

## Data Flow

```
ExecutionDAG + SpecRequirements
    ↓
    └─ CodeGenerationService.generate_from_requirements()
        ├─ Call Claude API with spec + context
        ├─ Generate code for all atoms
        ├─ Allow syntax errors (for repair later)
        └─ Return code string
            ↓
        Generated Code String
            ↓
        Parse into file structure
            ↓
        Generated Project Files
            ├─ models/user.py
            ├── api/routes/users.py
            ├── tests/test_users.py
            └─ ... 40-60 files total
                ↓
                Feeds to Phase 6.5 (Code Repair)
```

## Integration Points

- **Phase 5**: Receives DAG with execution waves
- **Phase 6.5**: Sends generated code for repair
- **Phase 7**: Sends code for validation
- **Metrics**: LOC, files, generation time, cost

## Success Criteria

✅ All atomic units generate code
✅ 40-60 files created
✅ Total LOC ≥ 1,000 (typical 2,000-5,000)
✅ All required entities and endpoints implemented
✅ Type hints present
✅ Docstrings present
✅ Error handling included

## Typical Code Generation Output

```
Code Generation Summary:
  Files Generated: 52
  Total Lines of Code: 3,847
  Syntax Errors: 12 (0.3%)

Generation Time:
  - Wave 1: 3.2s
  - Wave 2: 4.1s
  - Wave 3: 5.8s
  - Wave 4: 6.2s
  Total: 19.3 seconds

Code Distribution:
  - Models/ORM: 486 LOC (13%)
  - API Routes: 892 LOC (23%)
  - Schemas: 384 LOC (10%)
  - Validations: 721 LOC (19%)
  - Tests: 986 LOC (26%)
  - Config/Other: 378 LOC (9%)

File Types:
  - Python files: 42
  - Migration files: 3
  - Config files: 4
  - Markdown docs: 3

API Calls:
  - Claude API calls: 23
  - Average tokens per call: ~2,000
  - Total tokens: 46,000
  - Cost: $2.30
```

## Known Limitations

- ⚠️ Generated code may have syntax errors (fixed in Phase 6.5)
- ⚠️ Logic may be incomplete (validated in Phase 7)
- ⚠️ Some patterns may not be familiar to Claude
- ⚠️ Generation time varies with spec complexity

## Fallback Behavior

If CodeGenerationService unavailable:
1. Use hardcoded template (REMOVED - no fallback)
2. Or raise error
3. Pipeline cannot continue without real code generation

## Parallelization Opportunity

```
Sequential:
  Phase 6 Wave 1 → Phase 6 Wave 2 → Phase 6 Wave 3 → ...
  Total: 20 seconds

Parallel (with API limits):
  Wave 1: 5 atoms simultaneously = 3.2s
  Wave 2: 5 atoms simultaneously = 4.1s
  Wave 3: 5 atoms simultaneously = 5.8s
  Total: 13.1s (37% faster)
```

## Next Phase

Output feeds to **Phase 6.5: Code Repair** which:
- Runs tests on generated code
- Detects failing tests
- Repairs broken code
- Re-validates

---

**Last Updated**: 2025-11-23
**Source**: tests/e2e/real_e2e_full_pipeline.py:1405-1912
**Status**: Verified ✅
