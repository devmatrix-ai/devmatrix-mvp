# Phase 7: Validation

**Purpose**: Validate generated code against original specification

**Status**: ✅ Core (Required)

---

## Overview

Phase 7 validates that all generated code correctly implements the original specification. It checks:
- All entities are generated
- All endpoints are generated
- All validations are implemented
- No requirements are missing

## Input

- **Source**: Generated code from Phase 6 (or Phase 6.5 if repair was done)
- **Contains**: Complete project files (50-60 files)

## Processing

```python
async def _phase_7_validation(self):
    # 1. Initialize validator
    validator = ComplianceValidator()

    # 2. Validate generated code against spec
    result = validator.validate(
        generated_code=generated_code,
        spec_requirements=spec_requirements
    )

    # 3. Check compliance score
    compliance_score = result.compliance_score

    # 4. Log issues if any
    for issue in result.issues:
        logger.warning(issue)
```

## Output

### Validation Result

```python
class ComplianceValidationResult:
    passed: bool                       # Overall validation pass/fail
    compliance_score: float            # 0.0-1.0 compliance percentage
    issues: List[ValidationIssue]      # Issues found
    coverage: Dict[str, float]         # Coverage by requirement type

    # Specific metrics
    entities_coverage: float           # % of entities implemented
    endpoints_coverage: float          # % of endpoints implemented
    validations_coverage: float        # % of validations implemented
    business_logic_coverage: float     # % of logic rules implemented
```

### Issue Types

```python
class ValidationIssue:
    type: str                  # "missing_entity", "incomplete_endpoint", etc.
    severity: str              # "error", "warning"
    description: str           # Human-readable description
    requirement_id: str        # F1, F2, etc.
    required_by: str           # Which spec requirement
```

## Service Dependencies

### Required
- **ComplianceValidator** (`src/validation/compliance_validator.py`)
  - Entity coverage validation
  - Endpoint completeness validation
  - Validation rule coverage
  - Business logic verification
  - Compliance score calculation

### Optional
- None

## Validation Checks

| Check | What | Pass Criteria |
|-------|------|---------------|
| **Entities** | All entities from spec are generated | 100% of entities present |
| **Endpoints** | All endpoints are implemented | All methods, paths, params match |
| **Validations** | All validation rules are enforced | All constraints checked |
| **Business Logic** | All workflows are implemented | Status transitions, rules enforced |
| **Type Safety** | Type hints on all functions | mypy compatible |
| **Tests** | Tests for all features | Coverage > 70% |
| **Errors** | Error handling present | Try/catch, validation errors |
| **Documentation** | Docstrings present | Google style format |

## Compliance Scoring

```python
compliance_score = (
    (entities_implemented / entities_required) * 0.25 +
    (endpoints_implemented / endpoints_required) * 0.35 +
    (validations_implemented / validations_required) * 0.20 +
    (logic_implemented / logic_required) * 0.20
)

# Minimum passing: 0.85 (85%)
if compliance_score >= 0.85:
    validation_passed = True
else:
    validation_passed = False
```

## Metrics Collected

- Overall compliance score
- Coverage by requirement type:
  - Entity coverage
  - Endpoint coverage
  - Validation coverage
  - Business logic coverage
- Issue count by severity:
  - Critical issues
  - Major issues
  - Minor issues
  - Warnings
- Missing items count

## Performance Characteristics

- **Time**: ~2-5 seconds
- **Memory**: ~100-200 MB
- **Computation**: String matching, AST analysis (simple)

## Data Flow

```
Generated Code + OriginalSpec
    ↓
    └─ ComplianceValidator.validate()
        ├─ Extract generated entities
        ├─ Extract generated endpoints
        ├─ Extract validations
        ├─ Compare against spec
        └─ Calculate coverage
            ↓
        ComplianceValidationResult
            ├─ Compliance: 92%
            ├─ Issues: 5
            │   ├─ Missing validation rules: 2
            │   └─ Incomplete endpoint: 3
            └─ Pass/Fail
                ↓
                Feeds to Phase 8 (Deployment)
```

## Typical Validation Output

```
Compliance Validation Report:
  Overall Compliance: 94.1% ✅ (PASSED)

Coverage by Requirement Type:
  - Entity Coverage: 100% (3/3 entities)
    ✓ User
    ✓ Task
    ✓ Category

  - Endpoint Coverage: 97% (34/35 endpoints)
    ✓ GET /api/users
    ✓ POST /api/users
    ✓ GET /api/users/{id}
    ✓ PATCH /api/users/{id}
    ✓ DELETE /api/users/{id}
    ✓ GET /api/tasks
    ✓ POST /api/tasks
    ... (27 more)
    ✗ DELETE /api/tasks/{id} (MISSING)

  - Validation Coverage: 92% (11/12 validations)
    ✓ Email format validation
    ✓ Password strength validation
    ✓ Task title length (1-255 chars)
    ✓ Task status enum validation
    ... (7 more)
    ✗ Unique email constraint (NOT FOUND)

  - Business Logic Coverage: 94% (15/16 logic rules)
    ✓ User creation flow
    ✓ Task status workflow (TODO → IN_PROGRESS → DONE)
    ✓ Permission checks
    ... (12 more)
    ✗ Cascade delete on user deletion (INCOMPLETE)

Issues Found: 4

  MAJOR (3):
    1. Endpoint missing: DELETE /api/tasks/{id}
       - Required by: F7
       - Impact: Task deletion not functional

    2. Validation incomplete: Email unique constraint
       - Required by: F2 (User email)
       - Impact: Duplicate emails may be created

    3. Logic incomplete: Cascade delete
       - Required by: F5 (Relationship)
       - Impact: Orphaned tasks after user deletion

  MINOR (1):
    1. Missing docstring in routes.py:42
       - Required by: Documentation standard
       - Impact: API unclear

Recommendations:
  1. Regenerate DELETE /api/tasks endpoint
  2. Add unique constraint to email field
  3. Add cascade delete to User→Task relationship
  4. Add docstring to route
```

## Validation Levels

```
Level 1: Basic Check (50-60% coverage expected)
  - All entities present
  - All endpoint signatures match
  - Basic validation

Level 2: Full Check (85%+ coverage expected)
  - All entities with proper fields
  - All endpoints with logic
  - All validations implemented
  - Business logic present

Level 3: Complete Check (95%+ coverage expected)
  - Perfect spec match
  - Edge cases handled
  - Comprehensive tests
  - Full documentation
```

## Error Handling

### Validation Failure

```python
ComplianceValidationError: Compliance score too low (78% < 85%)
```
**Resolution**: Review issues, regenerate missing code

### Spec Mismatch

```python
ValueError: Generated code structure doesn't match spec
```
**Resolution**: Check spec format and code generation

## Integration Points

- **Phase 6**: Receives generated code
- **Phase 8**: Determines if deployment should proceed
- **Metrics**: Compliance score, coverage metrics
- **Reporting**: Feeds into final project report

## Success Criteria

✅ Compliance score ≥ 85%
✅ All entities generated and implemented
✅ All endpoints generated and functional
✅ All validations present
✅ All business logic implemented
✅ No critical issues remaining

## Failure Cases

❌ **Critical**: Compliance < 70% - Regenerate code
❌ **Major**: Compliance 70-85% - Fix missing items
⚠️ **Minor**: Compliance 85-95% - May proceed with warnings
✅ **Excellent**: Compliance > 95% - Proceed normally

## Known Limitations

- ⚠️ Validation may miss implicit requirements
- ⚠️ Coverage metrics are approximations
- ⚠️ Cannot validate business logic correctness
- ⚠️ Syntax errors may affect validation

## Next Phase

Output feeds to **Phase 8: Deployment** which:
- Writes validated code to disk
- Creates project structure
- Generates configuration files
- Prepares for execution

---

**Last Updated**: 2025-11-23
**Source**: tests/e2e/real_e2e_full_pipeline.py:2556-2766
**Status**: Verified ✅
