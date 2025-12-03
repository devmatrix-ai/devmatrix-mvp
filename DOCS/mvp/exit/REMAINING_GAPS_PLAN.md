# Remaining Gaps Plan - Post 100% Pass Rate

**Status**: ALL 3 GAPS IMPLEMENTED ✅
**Date**: 2025-12-03
**Context**: Smoke tests passing, all 3 gaps now implemented

---

## 📊 Current State

```
Pass Rate:    100.0% ✅
Semantic:     100.0% ✅
IR Relaxed:   85.3%  ✅
IR Strict:    90.8%  ✅
Errors:       0      ✅
```

### What Works
- Schema constraints (gt, ge, patterns, unique) → 99%+ compliance
- IR-Centric Auto-Seed → All preconditions satisfied
- Smoke tests → All endpoints respond correctly

### What's Missing
1. **SERVICE Repair Agent** → Business logic constraints not auto-repaired
2. **Idempotency in CodeRepair** → Same fixes applied twice
3. **Separated Metrics** → Schema vs Business Logic not distinguished

---

## 🔧 Gap 1: SERVICE Repair Agent

### Problem
```
Constraint not auto-repairable: status_transition
Constraint not auto-repairable: custom  
Constraint not auto-repairable: stock_constraint
```

CodeRepair detects these but marks them "not auto-repairable" because no SERVICE repair exists.

### Solution

#### Phase 1: Constraint → Guard Template Mapping

| Constraint Type | Guard Template | Location |
|-----------------|----------------|----------|
| `status_transition` | `if entity.status != '{expected}': raise HTTPException(422, "Invalid status")` | Service method pre-guard |
| `stock_constraint` | `if product.stock < quantity: raise HTTPException(422, "Insufficient stock")` | Service method pre-guard |
| `workflow_constraint` | `if not {precondition}: raise HTTPException(422, "Workflow precondition failed")` | Service method pre-guard |
| `custom` | Mark as `MANUAL` | N/A (human review) |

#### Phase 2: Implementation

```python
# src/cognitive/repair/service_repair_agent.py

class ServiceRepairAgent:
    """Repairs business logic constraints by injecting guards into services."""
    
    GUARD_TEMPLATES = {
        'status_transition': '''
        # Guard: {constraint_name}
        if {entity}.status != "{expected_status}":
            raise HTTPException(
                status_code=422,
                detail=f"Cannot {operation}: {entity_name} status is {{{entity}.status}}, expected {expected_status}"
            )
        ''',
        'stock_constraint': '''
        # Guard: {constraint_name}
        if {product}.stock < {quantity}:
            raise HTTPException(
                status_code=422,
                detail=f"Insufficient stock: {{{product}.stock}} available, {{{quantity}}} requested"
            )
        ''',
    }
    
    def repair(self, constraint: ValidationFailure, service_code: str) -> str:
        """Inject guard into service method."""
        template = self.GUARD_TEMPLATES.get(constraint.constraint_type)
        if not template:
            return None  # Mark as MANUAL
        
        guard = template.format(**constraint.context)
        return self._inject_guard(service_code, constraint.method_name, guard)
```

#### Phase 3: Integration with SmokeRepairOrchestrator

```python
# In smoke_repair_orchestrator.py

async def _route_to_repair_agent(self, failure: ValidationFailure):
    if failure.constraint_type in ('status_transition', 'stock_constraint', 'workflow_constraint'):
        # Route to SERVICE repair
        return await self.service_repair_agent.repair(failure, self.service_files)
    elif failure.constraint_type == 'custom':
        # Mark as MANUAL - cannot auto-repair
        return RepairResult(success=False, reason="MANUAL_REVIEW_REQUIRED")
    else:
        # Route to existing schema repair
        return await self.code_repair_agent.repair(failure)
```

### Files to Modify
- `src/cognitive/repair/service_repair_agent.py` (NEW)
- `src/validation/smoke_repair_orchestrator.py` (integration)
- `src/cognitive/ir/behavior_model.py` (constraint context extraction)

### Effort: Medium (4-6 hours)

---

## 🔧 Gap 2: Idempotency in CodeRepair

### Problem
```
Iteration 1: Applied 258 fixes → 99.9%
Iteration 2: Applied 258 fixes → 99.9% (SAME FIXES!)
```

### Solution

#### AST Normalization Before/After

```python
# src/validation/code_repair_agent.py

def _is_fix_already_applied(self, file_content: str, fix: CodeFix) -> bool:
    """Check if fix is already present in code."""
    ast_before = self._normalize_ast(file_content)
    ast_after = self._normalize_ast(self._apply_fix(file_content, fix))
    return ast_before == ast_after

def _normalize_ast(self, code: str) -> str:
    """Normalize AST to canonical form for comparison."""
    import ast
    tree = ast.parse(code)
    return ast.dump(tree, annotate_fields=False)
```

#### Fix Fingerprinting

```python
def _get_fix_fingerprint(self, fix: CodeFix) -> str:
    """Generate unique fingerprint for a fix."""
    return hashlib.md5(f"{fix.file}:{fix.line}:{fix.type}:{fix.value}".encode()).hexdigest()

def repair_with_idempotency(self, failures: List[ValidationFailure]) -> RepairResult:
    applied_fingerprints = set()
    
    for failure in failures:
        fix = self._generate_fix(failure)
        fingerprint = self._get_fix_fingerprint(fix)
        
        if fingerprint in applied_fingerprints:
            continue  # Skip duplicate
        if self._is_fix_already_applied(self.files[fix.file], fix):
            continue  # Already in code
            
        self._apply_fix(fix)
        applied_fingerprints.add(fingerprint)
```

### Files to Modify
- `src/validation/code_repair_agent.py`

### Effort: Low (2-3 hours)

---

## 🔧 Gap 3: Separated Metrics

### Problem
Current metrics mix schema and business logic compliance:
```
IR Compliance: 85.3%  ← What's schema? What's business logic?
```

### Solution

```python
# src/validation/compliance_validator.py

class ComplianceMetrics:
    schema_compliance: float      # gt, ge, patterns, unique, etc.
    business_logic_compliance: float  # status_transition, stock, workflow
    manual_review_count: int      # custom constraints marked MANUAL
    
    def to_report(self) -> dict:
        return {
            "schema_constraints": {
                "compliance": f"{self.schema_compliance:.1%}",
                "status": "✅" if self.schema_compliance >= 0.95 else "⚠️"
            },
            "business_logic_constraints": {
                "compliance": f"{self.business_logic_compliance:.1%}",
                "auto_repaired": self.auto_repaired_count,
                "manual_required": self.manual_review_count,
                "status": "✅" if self.manual_review_count == 0 else "👁️ REVIEW"
            }
        }
```

### Output Example
```
📊 Compliance Report
├── Schema Constraints:        99.2% ✅
├── Business Logic Constraints: 87.5% ✅
│   ├── Auto-repaired:         14
│   └── Manual required:       2 👁️
└── Overall:                   93.4%
```

### Files to Modify
- `src/validation/compliance_validator.py`
- `src/validation/smoke_runner_v2.py` (report output)

### Effort: Low (1-2 hours)

---

## 📋 Implementation Order

| Priority | Gap | Effort | Impact |
|----------|-----|--------|--------|
| 1 | SERVICE Repair Agent | Medium | High - enables auto-repair of business logic |
| 2 | Idempotency | Low | Medium - reduces noise, improves efficiency |
| 3 | Separated Metrics | Low | Low - visibility only |

### Total Effort: ~8-11 hours

---

## ✅ Success Criteria

1. **SERVICE Repair Agent**
   - [ ] status_transition constraints auto-repaired
   - [ ] stock_constraint constraints auto-repaired
   - [ ] custom constraints marked as MANUAL (not failed)

2. **Idempotency**
   - [ ] Iteration 2 applies 0 fixes if Iteration 1 succeeded
   - [ ] No duplicate fingerprints in fix log

3. **Separated Metrics**
   - [ ] Report shows schema vs business logic separately
   - [ ] MANUAL items clearly marked for human review

