# Component: ComplianceValidator

**Module**: `src/validation/compliance_validator.py`
**Phase**: 7 (Validation)
**Status**: ✅ Core Required Component

---

## Purpose

ComplianceValidator ensures generated code correctly implements the original specification. It validates that:
- All entities are generated and implemented
- All endpoints are implemented
- All validations are in place
- No requirements are missing
- Business logic is correctly implemented

## Role in Pipeline

```
Input: Generated code + SpecRequirements
    ↓
[ComplianceValidator.validate()]
    ├─ Check entity coverage
    ├─ Check endpoint coverage
    ├─ Check validation coverage
    └─ Check business logic
    ↓
Output: ComplianceValidationResult
    ↓
If passed (≥85%): Continue to Phase 8 (Deployment)
If failed (<85%): Flag for regeneration or repair
```

## Key Methods

### Main Method: `validate(generated_code, spec_requirements) → ComplianceValidationResult`

**Purpose**: Validate generated code against original specification

**Input**:
- `generated_code`: Code files from Phase 6
- `spec_requirements`: Requirements from Phase 1

**Output**:
```python
class ComplianceValidationResult:
    passed: bool                       # Overall pass/fail
    compliance_score: float            # 0.0-1.0 (must be ≥0.85)
    issues: List[ValidationIssue]      # Issues found
    coverage: Dict[str, float]         # Coverage by type

    # Specific metrics
    entities_coverage: float           # % of entities
    endpoints_coverage: float          # % of endpoints
    validations_coverage: float        # % of validations
    business_logic_coverage: float     # % of logic
```

**Usage in Pipeline** (Phase 7, line 2700+):
```python
validation_result = await compliance_validator.validate(
    generated_code=generated_code,
    spec_requirements=spec_requirements
)
```

## Validation Checks

| Check | What | Pass Criteria |
|-------|------|------------------|
| **Entities** | All entities from spec | 100% present |
| **Endpoints** | All endpoints implemented | All methods, paths, params match |
| **Validations** | All validation rules | All constraints checked |
| **Business Logic** | All workflows implemented | Status transitions enforced |
| **Type Safety** | Type hints on functions | mypy compatible |
| **Tests** | Tests for features | Coverage > 70% |
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
# Below 85%: FAILED - needs regeneration
# 85-95%: PASSED with warnings
# 95%+: EXCELLENT
```

## Validation Levels

```
Level 1: Basic Check (50-60% coverage)
  - All entities present
  - All endpoint signatures match
  - Basic validation

Level 2: Full Check (85%+ coverage)
  - All entities with proper fields
  - All endpoints with logic
  - All validations implemented
  - Business logic present

Level 3: Complete Check (95%+ coverage)
  - Perfect spec match
  - Edge cases handled
  - Comprehensive tests
  - Full documentation
```

## Coverage Analysis

### Entity Coverage
```python
required_entities = ["User", "Task", "Project"]
implemented_entities = ["User", "Task"]  # Missing Project
coverage = 2/3 = 66.7% ❌ (below 100%)
```

### Endpoint Coverage
```python
required_endpoints = 15  # From spec
implemented_endpoints = 14  # Generated code
coverage = 14/15 = 93.3% ✅ (high)
missing: ["DELETE /api/tasks/{id}"]
```

### Validation Coverage
```python
required_validations = [
    "email_format",
    "password_strength",
    "task_title_length",
    "status_enum",
    "unique_email"
]
implemented = [
    "email_format", ✅
    "password_strength", ✅
    "task_title_length", ✅
    "status_enum", ✅
    # unique_email missing ❌
]
coverage = 4/5 = 80% ⚠️
```

### Business Logic Coverage
```python
required_logic = [
    "user_creation_flow",
    "task_status_workflow",
    "permission_checks",
    "cascade_delete"
]
implemented = [
    "user_creation_flow", ✅
    "task_status_workflow", ✅
    "permission_checks", ✅
    # cascade_delete incomplete ⚠️
]
coverage = 3/4 = 75% ⚠️
```

## Metrics Collected

In Phase 7:
```python
metrics: {
    "compliance_score": float,         # 0-100%
    "passed": bool,
    "entities_coverage": float,
    "endpoints_coverage": float,
    "validations_coverage": float,
    "business_logic_coverage": float,
    "issues_critical": int,
    "issues_major": int,
    "issues_minor": int,
    "validation_time": float           # Seconds
}

# Example:
{
    "compliance_score": 94.1,
    "passed": true,
    "entities_coverage": 100.0,
    "endpoints_coverage": 97.0,
    "validations_coverage": 92.0,
    "business_logic_coverage": 94.0,
    "issues_critical": 0,
    "issues_major": 1,
    "issues_minor": 2,
    "validation_time": 2.3
}
```

## Typical Validation Output

```
Compliance Validation Report:
  Overall Compliance: 94.1% ✅ (PASSED)

Coverage by Requirement Type:
  - Entity Coverage: 100% (3/3 entities)
  - Endpoint Coverage: 97% (34/35 endpoints)
  - Validation Coverage: 92% (11/12 validations)
  - Business Logic Coverage: 94% (15/16 logic rules)

Issues Found: 4

  MAJOR (3):
    1. Endpoint missing: DELETE /api/tasks/{id}
    2. Validation incomplete: Email unique constraint
    3. Logic incomplete: Cascade delete

  MINOR (1):
    1. Missing docstring in routes.py:42

Recommendations:
  1. Regenerate DELETE /api/tasks endpoint
  2. Add unique constraint to email field
  3. Add cascade delete to User→Task relationship
  4. Add docstring to route
```

## Error Handling

### Validation Failure
```python
if compliance_score < 0.85:
    raise ComplianceValidationError(
        f"Compliance score too low ({compliance_score:.0%} < 85%)"
    )
```

### Spec Mismatch
```python
if generated_structure != expected_structure:
    raise ValueError("Generated code structure doesn't match spec")
```

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

## Usage Example

```python
from src.validation.compliance_validator import ComplianceValidator

# Initialize validator
validator = ComplianceValidator()

# Validate code against spec
result = validator.validate(
    generated_code=generated_code,
    spec_requirements=spec_requirements
)

# Check result
if result.passed:
    print(f"✅ Validation passed: {result.compliance_score:.1%}")
else:
    print(f"❌ Validation failed: {result.compliance_score:.1%}")

# Print issues
for issue in result.issues:
    print(f"  {issue.severity}: {issue.description}")
```

## Performance Characteristics

- **Time**: ~2-5 seconds
- **Memory**: ~100-200 MB
- **Computation**: String matching, AST analysis
- **Complexity**: O(n) where n = requirement count

## Integration Points

### Input from
- Phase 6: CodeGenerationService (GeneratedCode)
- Phase 1: SpecParser (SpecRequirements)

### Output to
- Phase 8: Deployment (if passed)
- Phase 10: Learning (compliance metrics)
- Metrics: Compliance score, coverage metrics

## Known Limitations

- ⚠️ May miss implicit requirements
- ⚠️ Coverage metrics are approximations
- ⚠️ Cannot validate business logic correctness
- ⚠️ Syntax errors may affect validation

## Next Phase

Output (ComplianceValidationResult) feeds to:
- **Phase 8 (Deployment)**: If passed, deploy code to disk
- **Phase 9 (Health Verification)**: If passed, verify health
- **Phase 10 (Learning)**: Record compliance metrics

---

**Last Updated**: 2025-11-23
**Source**: tests/e2e/real_e2e_full_pipeline.py:2556-2766
**Status**: Verified ✅
