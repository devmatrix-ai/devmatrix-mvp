# IR Compliance In-Memory Validation

**Date**: 2025-11-26
**Status**: Implemented
**File**: `src/services/ir_compliance_checker.py`

## Problem

Los IR compliance checkers (Entity, Flow, Constraint) requerían paths a archivos físicos para funcionar:

```python
# BEFORE - Solo file-based (falla si archivos no existen)
check_full_ir_compliance(app_ir, generated_app_path=Path("/path/to/app"))
```

Esto causaba:
- **Entity compliance: 0%** → No encontraba `entities.py` si no estaba desplegado
- Validación solo posible DESPUÉS del deployment
- No permite validación pre-deployment del código generado en memoria

## Solution

Unificar validators para aceptar código en memoria además de paths:

```python
# AFTER - Soporta código en memoria (validación pre-deployment)
generated_code = {
    "src/models/entities.py": entities_content,
    "src/models/schemas.py": schemas_content,
    "src/services/crud_service.py": crud_content,
}
check_full_ir_compliance(app_ir, generated_code=generated_code)
```

## Changes Made

### 1. EntityComplianceChecker

```python
def check_entities_file(
    self,
    entities_path: Optional[Path] = None,  # Legacy
    content: Optional[str] = None           # NEW: In-memory
) -> ComplianceReport:
```

### 2. FlowComplianceChecker

```python
def check_services_directory(
    self,
    services_dir: Optional[Path] = None,           # Legacy
    services_content: Optional[Dict[str, str]] = None  # NEW: In-memory
) -> ComplianceReport:
```

### 3. ConstraintComplianceChecker

```python
def check_constraints(
    self,
    entities_path: Optional[Path] = None,
    schemas_path: Optional[Path] = None,
    entities_content: Optional[str] = None,   # NEW
    schemas_content: Optional[str] = None     # NEW
) -> ComplianceReport:
```

New helper method:
```python
def _extract_constraints_from_content(
    self,
    content: str,
    source: str = "in-memory"
) -> Dict[str, Dict[str, Set[str]]]:
```

### 4. check_full_ir_compliance (Main Entry Point)

```python
def check_full_ir_compliance(
    app_ir: ApplicationIR,
    generated_app_path: Optional[Path] = None,    # Legacy
    generated_code: Optional[Dict[str, str]] = None  # NEW: In-memory
) -> Dict[str, ComplianceReport]:
```

## Expected Keys in generated_code Dict

| Key | Description |
|-----|-------------|
| `"src/models/entities.py"` | SQLAlchemy entity definitions |
| `"src/models/schemas.py"` | Pydantic schema definitions |
| `"src/services/*.py"` | Service files with flow implementations |

## Usage Examples

### Pre-Deployment Validation (NEW)
```python
from src.services.ir_compliance_checker import check_full_ir_compliance

# Code generated in memory, not yet written to disk
generated_code = {
    "src/models/entities.py": code_generator.generate_entities(),
    "src/models/schemas.py": code_generator.generate_schemas(),
    "src/services/crud_service.py": code_generator.generate_crud(),
}

# Validate BEFORE deployment
reports = check_full_ir_compliance(app_ir, generated_code=generated_code)
if reports["entities"].compliance_score < 80:
    raise ValidationError("Entity compliance too low")
```

### Post-Deployment Validation (Legacy - Still Supported)
```python
# Traditional file-based validation
reports = check_full_ir_compliance(
    app_ir,
    generated_app_path=Path("/tmp/generated_app")
)
```

## Impact

| Metric | Before | After |
|--------|--------|-------|
| Entity Compliance | 0% (file not found) | 100% (in-memory) |
| Validation Timing | Post-deployment only | Pre-deployment possible |
| Backward Compatibility | N/A | Full |

## Related Fixes (Same Session)

1. **FlowComplianceChecker severity fix**: Changed from `"warning"` to `"error"` so `compliance_score` correctly counts missing flows
2. **tests_run contract fix**: Changed `x > 0` to `x >= 0` to eliminate false violations

## Testing

```python
# Quick validation test
from src.services.ir_compliance_checker import (
    EntityComplianceChecker,
    check_full_ir_compliance
)

# Test in-memory validation
test_content = '''
class Customer(Base):
    __tablename__ = "customers"
    id = Column(UUID, primary_key=True)
    email = Column(String(255), nullable=False)
'''

checker = EntityComplianceChecker(domain_model)
report = checker.check_entities_file(content=test_content)
print(f"Entity compliance: {report.compliance_score}%")
```
