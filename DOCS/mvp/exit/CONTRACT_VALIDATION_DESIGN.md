# Contract Validation System - Redesign

**Status:** ✅ IMPLEMENTED
**Date:** 2025-12-01
**Related:** Bug #172 - Contracts too lax

## Implementation Summary

| File | Changes |
|------|---------|
| `tests/e2e/precision_metrics.py` | 3-tier ContractValidator, `validate_smoke_test_against_ir()` |
| `tests/e2e/real_e2e_full_pipeline.py` | IR-centric validation in `_process_smoke_result()`, tier report |

---

## 🎯 Single Source of Truth: ApplicationIR

**PRINCIPIO FUNDAMENTAL:** El `ApplicationIR` es la ÚNICA fuente de verdad.

```
Spec (input) → ApplicationIR (truth) → Generated Code (output)
                     ↓
              Contract Validation
```

Todos los contratos validan **contra el IR**, no contra:
- ❌ Métricas calculadas internamente
- ❌ Ground truth hardcodeado
- ❌ Conteos de archivos generados
- ❌ Datos derivados de otras fuentes

### IR Components (fuente de verdad)

| Component | Qué contiene | Contratos que validan |
|-----------|--------------|----------------------|
| `DomainModelIR.entities` | Entidades del dominio | entity_count, relationships |
| `APIModelIR.endpoints` | Endpoints a generar | endpoint_count, methods, paths |
| `BehaviorModelIR.flows` | Flujos de negocio | flow_count, validations |
| `RequirementsIR` | Requirements clasificados | requirement_count, domains |

### Ejemplo de Validación IR-Centric

```python
# ✅ CORRECTO: Validar contra IR
expected_endpoints = len(application_ir.api_model.endpoints)
generated_endpoints = count_endpoints_in_code(generated_code)
coverage = generated_endpoints / expected_endpoints

# ❌ INCORRECTO: Validar contra conteo interno
expected = self.precision.dag_nodes_expected  # ¿De dónde viene?
```

---

## Problem Statement

Los contratos actuales solo validan **existencia** y **tipos**, no **calidad**:

```python
# Ejemplo actual - DEMASIADO LAX
"constraints": {
    "complexity": lambda x: 0.0 <= x <= 1.0,  # Acepta 0.0!
    "requirements": lambda x: len(x) > 0       # Solo pide ≥1
}
```

**Resultado:** Un spec con complexity=0.0 y 1 requirement PASA validación.

---

## Proposed Solution: 3-Tier Contracts

### Tier 1: STRUCTURAL (Hard Fail)
- Campos requeridos existen
- Tipos correctos
- Invariantes básicos (DAG es acíclico, counts ≥ 0)

**Si falla:** Pipeline ABORT inmediato.

### Tier 2: SEMANTIC (Warnings)
- Valores tienen sentido lógico
- Complexity > 0 para specs reales
- Requirements tienen dominio clasificado

**Si falla:** Warning en log, pipeline continúa.

### Tier 3: QUALITY (Gating)
- Métricas de calidad sobre thresholds
- Smoke test pass rate ≥ 70%
- Pattern matching precision ≥ 50%

**Si falla:** Pipeline completa pero status = "failed".

---

## Contract Definitions by Phase

### Phase 1: Spec Ingestion

| Check | Tier | Condition | Action |
|-------|------|-----------|--------|
| spec_content exists | STRUCTURAL | `len(x) > 0` | ABORT |
| requirements exists | STRUCTURAL | `isinstance(x, list)` | ABORT |
| complexity in range | STRUCTURAL | `0.0 <= x <= 1.0` | ABORT |
| complexity > 0 | SEMANTIC | `x > 0.0` | WARN |
| requirements ≥ 3 | SEMANTIC | `len(x) >= 3` | WARN |
| requirements have domains | QUALITY | `any(r.domain for r)` | GATE |

### Phase 2: Requirements Analysis

| Check | Tier | Condition | Action |
|-------|------|-----------|--------|
| functional_reqs exists | STRUCTURAL | `isinstance(x, list)` | ABORT |
| has functional reqs | SEMANTIC | `len(x) >= 1` | WARN |
| patterns matched | QUALITY | `x >= 1` | GATE |

### Phase 3: Planning (DAG)

| Check | Tier | Condition | Action |
|-------|------|-----------|--------|
| node_count > 0 | STRUCTURAL | `x > 0` | ABORT |
| is_acyclic = True | STRUCTURAL | `x == True` | ABORT |
| waves ≥ 1 | SEMANTIC | `x >= 1` | WARN |
| edge/node ratio | QUALITY | `edges/nodes >= 0.5` | GATE |

### Phase 4: Atomization

| Check | Tier | Condition | Action |
|-------|------|-----------|--------|
| unit_count > 0 | STRUCTURAL | `x > 0` | ABORT |
| avg_complexity in range | STRUCTURAL | `0.0 <= x <= 1.0` | ABORT |
| units have IDs | SEMANTIC | `all(u.id for u)` | WARN |

### Phase 5: DAG Construction

| Check | Tier | Condition | Action |
|-------|------|-----------|--------|
| wave_count > 0 | STRUCTURAL | `x > 0` | ABORT |
| nodes exist | SEMANTIC | `len(nodes) > 0` | WARN |

### Phase 6: Wave Execution

| Check | Tier | Condition | Action |
|-------|------|-----------|--------|
| atoms_executed > 0 | STRUCTURAL | `x > 0` | ABORT |
| success_rate ≥ 50% | QUALITY | `succeeded/executed >= 0.5` | GATE |
| success_rate ≥ 80% | QUALITY | `succeeded/executed >= 0.8` | EXCELLENT |

### Phase 7+: Smoke Test (THE KEY CONTRACT)

| Check | Tier | Condition | Action |
|-------|------|-----------|--------|
| total_scenarios > 0 | STRUCTURAL | `x > 0` | ABORT |
| pass_rate in range | STRUCTURAL | `0.0 <= x <= 1.0` | ABORT |
| passed + failed = total | SEMANTIC | `p + f == t` | WARN |
| pass_rate ≥ 70% | QUALITY | `x >= 0.70` | GATE |
| pass_rate ≥ 95% | QUALITY | `x >= 0.95` | EXCELLENT |

---

## Quality Thresholds

```python
QUALITY_THRESHOLDS = {
    # Minimums (below = FAIL)
    "min_requirements": 3,
    "min_functional_reqs": 1,
    "min_success_rate": 0.50,
    "min_smoke_pass_rate": 0.70,
    
    # Targets (below = WARNING)
    "target_success_rate": 0.80,
    "target_smoke_pass_rate": 0.95,
    
    # Excellence (above = EXCELLENT badge)
    "excellent_smoke_pass_rate": 0.95,
    "excellent_success_rate": 0.95,
}
```

---

## Validation Modes

### 1. STRICT Mode (CI/CD, Production)
- STRUCTURAL failures → ABORT
- SEMANTIC failures → WARNING + continue
- QUALITY failures → status = "failed"

### 2. LENIENT Mode (Development)
- STRUCTURAL failures → ABORT
- SEMANTIC failures → log only
- QUALITY failures → log only, status = "completed_with_warnings"

### 3. RESEARCH Mode (Experimentation)
- STRUCTURAL failures → log + continue
- SEMANTIC failures → ignore
- QUALITY failures → ignore

---

## Implementation Plan

### Step 1: Update ContractValidator class
```python
@dataclass
class ContractValidator:
    mode: str = "STRICT"  # STRICT | LENIENT | RESEARCH
    violations: List[Dict] = field(default_factory=list)
    warnings: List[Dict] = field(default_factory=list)
    
    def validate_phase_output(self, phase: str, output: Dict) -> ValidationResult:
        result = ValidationResult(phase=phase)
        
        # Check STRUCTURAL
        for check in contract["structural"]:
            if not check(output):
                result.structural_failures.append(...)
                if self.mode != "RESEARCH":
                    result.should_abort = True
        
        # Check SEMANTIC
        for check in contract["semantic"]:
            if not check(output):
                result.semantic_warnings.append(...)
        
        # Check QUALITY
        for check in contract["quality"]:
            if not check(output):
                result.quality_failures.append(...)
                if self.mode == "STRICT":
                    result.status = "failed"
        
        return result
```

### Step 2: Add Smoke Test Contract
```python
SMOKE_TEST_CONTRACT = {
    "structural": {
        "total_scenarios": lambda x: x > 0,
        "pass_rate": lambda x: 0.0 <= x <= 1.0,
    },
    "semantic": {
        "consistency": lambda o: o["passed"] + o["failed"] == o["total_scenarios"],
    },
    "quality": {
        "pass_rate": lambda x: x >= 0.70,
    },
    "excellent": {
        "pass_rate": lambda x: x >= 0.95,
    }
}
```

### Step 3: Update Report Output
```
✅ CONTRACT VALIDATION
------------------------------------------------------------------------------------------
  Phase: spec_ingestion
    ✅ STRUCTURAL: All checks passed
    ⚠️  SEMANTIC: complexity=0.0 (expected > 0)
    ✅ QUALITY: requirements have domains
    
  Phase: smoke_test
    ✅ STRUCTURAL: 76 scenarios
    ✅ SEMANTIC: 53 + 23 = 76 ✓
    ❌ QUALITY: pass_rate=69.7% (minimum: 70%)
    
  Overall: ⚠️ 1 quality gate failed
```

---

## Migration Path

1. **Phase 1:** Add `warnings` list to ContractValidator (non-breaking)
2. **Phase 2:** Add SMOKE_TEST_CONTRACT (new contract)
3. **Phase 3:** Split existing constraints into structural/semantic/quality
4. **Phase 4:** Add `mode` parameter for STRICT/LENIENT/RESEARCH
5. **Phase 5:** Update `_print_report()` to show tiered results

---

## Success Metrics

| Metric | Before | After |
|--------|--------|-------|
| False positives (pass when should fail) | HIGH | LOW |
| False negatives (fail when should pass) | LOW | LOW |
| Actionable feedback | NO | YES |
| Clear thresholds | NO | YES |

---

## Files to Modify

| File | Changes |
|------|---------|
| `tests/e2e/precision_metrics.py` | ContractValidator redesign |
| `tests/e2e/real_e2e_full_pipeline.py` | Use new validation, update report |
| `DOCS/mvp/exit/RUNTIME_TUNING_PLAN.md` | Reference this doc |

---

## IR-Centric Contract Examples

### Smoke Test Contract (validates against IR)

```python
def validate_smoke_tests(self, ir: ApplicationIR, results: SmokeTestResults) -> ValidationResult:
    """
    Validates smoke test results against IR (the source of truth).
    """
    # IR defines what SHOULD exist
    expected_endpoints = set()
    for endpoint in ir.api_model.endpoints:
        expected_endpoints.add(f"{endpoint.method} {endpoint.path}")

    # Results show what WAS tested
    tested_endpoints = set(r.endpoint for r in results.scenarios)

    # STRUCTURAL: All IR endpoints should be tested
    missing = expected_endpoints - tested_endpoints
    if missing:
        return ValidationResult(
            tier="STRUCTURAL",
            passed=False,
            message=f"Missing tests for {len(missing)} IR endpoints: {missing}"
        )

    # QUALITY: Pass rate threshold
    pass_rate = results.passed / results.total if results.total > 0 else 0
    if pass_rate < 0.70:
        return ValidationResult(
            tier="QUALITY",
            passed=False,
            message=f"Pass rate {pass_rate:.1%} < 70% threshold"
        )

    return ValidationResult(tier="QUALITY", passed=True)
```

### Endpoint Coverage Contract (IR as truth)

```python
def validate_endpoint_coverage(self, ir: ApplicationIR, generated_code: dict) -> ValidationResult:
    """
    Validates that generated code covers all IR endpoints.
    """
    # IR is truth
    ir_endpoints = {f"{e.method} {e.path}" for e in ir.api_model.endpoints}

    # Generated code is what we validate
    code_endpoints = extract_endpoints_from_code(generated_code)

    # Calculate coverage against IR (not against itself!)
    covered = ir_endpoints & code_endpoints
    coverage = len(covered) / len(ir_endpoints) if ir_endpoints else 1.0

    return ValidationResult(
        tier="QUALITY",
        passed=coverage >= 0.95,
        coverage=coverage,
        missing=ir_endpoints - code_endpoints
    )
```

---

## Open Questions

1. **Should QUALITY failures block deployment?**
   - Current thinking: Yes in STRICT mode, No in LENIENT

2. **How to handle smoke test pass_rate edge cases?**
   - 0 scenarios → STRUCTURAL fail
   - 1-10 scenarios → Warning (too few for confidence)
   - 70-94% → QUALITY warning
   - 95%+ → EXCELLENT

3. **Should we track contract violations over time?**
   - Could help identify systemic issues
   - Neo4j storage for trend analysis

