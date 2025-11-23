# Component: CodeGenerationService

**Module**: `src/services/code_generation_service.py`
**Phase**: 6 (Code Generation)
**Status**: ✅ Core Required Component

---

## Purpose

CodeGenerationService generates production-ready Python code from atomic units using Claude API. It's the code generation engine of the pipeline.

## Role in Pipeline

```
Input: ExecutionDAG from Phase 5
    ↓
[CodeGenerationService.generate_from_requirements()]
    ├─ Uses: PatternBank for code patterns
    ├─ Uses: ApplicationIRNormalizer for templates
    └─ May use: ErrorPatternStore for known fixes
    ↓
Output: GeneratedCode (40-60 files)
    ↓
Consumed by: Phase 6.5 (Code Repair) or Phase 7 (Validation)
```

## Critical Transitive Dependencies

**IMPORTANT**: This component has critical transitive dependencies:

```python
CodeGenerationService.__init__():
    Line 48: from src.services.application_ir_normalizer import ApplicationIRNormalizer
    Line 40: from src.cognitive.patterns.pattern_bank import PatternBank
    Line 41: from src.cognitive.services.neo4j_ir_repository import Neo4jIRRepository

    # ApplicationIRNormalizer is REQUIRED for template rendering
    # PatternBank is optional (graceful degradation)
    # Neo4j is optional (graceful degradation)
```

**Pipeline Impact**: If ApplicationIRNormalizer unavailable → CODE GENERATION FAILS (fatal)

## Key Methods

### Main Method: `generate_from_requirements(spec_requirements) → GeneratedCode`

**Purpose**: Generate Python code for all atomic units

**Input**:
- `spec_requirements`: Requirements from Phase 1
- `allow_syntax_errors`: If True, allows imperfect code (fixed in Phase 6.5)

**Output**:
```python
class GeneratedCode:
    file_structure: Dict[str, str]      # {filepath: code_content}
    files: List[str]                    # File paths
    total_lines: int                    # Total LOC
    by_type: Dict[str, int]            # LOC by type
    syntax_errors: int                 # Error count
```

**Usage in Pipeline** (Phase 6, line 1482):
```python
generated_code = await code_generator.generate_from_requirements(
    spec_requirements,
    allow_syntax_errors=True
)
```

## Code Generation Process

```
For each wave in ExecutionDAG.waves (parallel within wave):
    │
    ├─ For each atomic unit in wave:
    │   ├─ Generate function/method/class
    │   ├─ Add error handling (try/except)
    │   ├─ Add type hints
    │   ├─ Add docstrings
    │   └─ Combine with other atoms
    │
    ├─ Wave-level code artifact
    │
    └─ Add to output files

Output: Complete project structure
├── src/
│   ├── models/
│   ├── api/routes/
│   ├── api/schemas/
│   ├── validations/
│   ├── main.py
│   ├── database.py
│   └── config.py
├── tests/
├── migrations/
├── requirements.txt
├── Dockerfile
└── README.md
```

## Output File Structure

### Generated Files (46-57 total)

```
Models (10-15 files):
  - src/models/entity1.py
  - src/models/entity2.py
  - src/models/__init__.py

API Routes (5-8 files):
  - src/api/routes/entity1.py
  - src/api/routes/entity2.py
  - src/api/__init__.py

Schemas (5-10 files):
  - src/api/schemas/entity1.py
  - src/api/schemas/entity2.py

Tests (10-15 files):
  - tests/test_models.py
  - tests/test_entity1.py
  - tests/conftest.py

Config & Setup (8-12 files):
  - src/main.py
  - src/config.py
  - src/database.py
  - requirements.txt
  - Dockerfile
  - docker-compose.yml
  - README.md
  - .env.example
```

## Code Quality Standards

Generated code includes:
- ✅ Type hints (mypy compatible)
- ✅ Docstrings (Google style)
- ✅ Error handling (try/except)
- ✅ Input validation (Pydantic)
- ✅ Proper imports
- ✅ PEP 8 compliance
- ✅ Security best practices

## Metrics Collected

In Phase 6 (line 1700+):
```python
metrics: {
    "files_generated": int,         # Total files
    "total_lines": int,             # Total LOC
    "by_type": {
        "models": int,
        "routes": int,
        "schemas": int,
        "tests": int,
        "config": int
    },
    "generation_time": float,       # Seconds
    "syntax_errors": int,           # Error count
    "syntax_error_rate": float      # Percentage
}

# Example:
{
    "files_generated": 52,
    "total_lines": 3847,
    "by_type": {
        "models": 486,
        "routes": 892,
        "schemas": 384,
        "tests": 986,
        "config": 378
    },
    "generation_time": 19.3,
    "syntax_errors": 12,
    "syntax_error_rate": 0.3
}
```

## Pattern Integration

**PatternBank Usage**: Provides code templates for common patterns
- FastAPI_CRUD_Template
- SQLAlchemy_ORM_Model
- Pydantic_Schema
- CustomValidation_Rule

If PatternBank unavailable: Falls back to base code generation (lower quality)

## Transitive Dependencies

### ApplicationIRNormalizer (CRITICAL)
**Status**: Required
```python
from src.services.application_ir_normalizer import ApplicationIRNormalizer
# Line 48 in code_generation_service.py
# Purpose: Normalize requirements to intermediate representation for templating
# Impact: Code generation fails if unavailable (fatal)
```

### PatternBank (Optional)
**Status**: Graceful degradation
```python
try:
    from src.cognitive.patterns.pattern_bank import PatternBank
except ImportError:
    PatternBank = None  # Continue without patterns (lower quality)
```

### Neo4j (Optional)
**Status**: Graceful degradation
```python
try:
    from src.cognitive.services.neo4j_ir_repository import Neo4jIRRepository
except ImportError:
    Neo4jIRRepository = None  # Continue without Neo4j storage
```

## Error Handling

### Syntax Errors
Generated with `allow_syntax_errors=True`:
```python
# Let repair phase (6.5) fix these
def func(x  # Missing colon - fixed in repair phase
    pass
```

### Generation Failure
```python
ValueError: Code generation from requirements failed: {error}
# Check logs, verify spec, retry
```

## Usage Example

```python
from src.services.code_generation_service import CodeGenerationService

# Initialize service
service = CodeGenerationService(db=None)

# Generate code from requirements
result = await service.generate_from_requirements(
    spec_requirements=spec_requirements,
    allow_syntax_errors=True
)

# Access generated code
print(f"Files generated: {len(result.files)}")
print(f"Total LOC: {result.total_lines}")

# Access individual files
for filename, content in result.file_structure.items():
    print(f"\n{filename}:")
    print(content[:500] + "...")  # First 500 chars
```

## Performance Characteristics

- **Time**: 10-20 seconds per wave (LLM dependent)
- **Memory**: ~200-500 MB
- **API Calls**: 5-50 Claude API calls
- **Cost**: $1-5 per project
- **Throughput**: 100-500 LOC per second (generation)

## Success Criteria

✅ All atomic units generate code
✅ 40-60 files created
✅ Total LOC ≥ 1000 (typical 2000-5000)
✅ All entities and endpoints implemented
✅ Type hints present
✅ Docstrings present
✅ Error handling included
✅ Code is valid Python (or has minor syntax errors for repair phase)

## Typical Output

```
Phase 6: Code Generation
  Files generated: 52
  Total lines of code: 3,847
  Syntax errors: 12 (0.3%)

Generation time: 19.3 seconds
  - Wave 1: 3.2s (models)
  - Wave 2: 4.1s (schemas)
  - Wave 3: 5.8s (routes)
  - Wave 4: 6.2s (tests)

Code distribution:
  - Models: 486 LOC (13%)
  - Routes: 892 LOC (23%)
  - Schemas: 384 LOC (10%)
  - Tests: 986 LOC (26%)
  - Config: 378 LOC (9%)
  - Other: 378 LOC (9%)

API calls: 23
Average tokens: ~2000 per call
Total tokens: 46,000
Cost: $2.30
```

## Known Limitations

- ⚠️ Generated code may have syntax errors (Phase 6.5 fixes)
- ⚠️ Logic may be incomplete (Phase 7 validates)
- ⚠️ Some patterns may not be familiar to Claude
- ⚠️ Generation time varies with spec complexity

## Next Phase

Output (GeneratedCode) feeds to:
- **Phase 6.5 (Code Repair)**: Fix syntax errors and test failures
- **Phase 7 (Validation)**: Validate against specification

---

**Last Updated**: 2025-11-23
**Source**: tests/e2e/real_e2e_full_pipeline.py:1405-1912
**Status**: Verified ✅
**Critical Dependency**: ApplicationIRNormalizer (REQUIRED)
