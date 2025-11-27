# E2E Pipeline Phases - Complete Reference

**Date**: Nov 26, 2025
**Status**: PRODUCTION
**File**: `tests/e2e/real_e2e_full_pipeline.py`

---

## Overview

El E2E pipeline orquesta la generación completa de aplicaciones desde specs hasta código validado. Todas las fases corren desde un único archivo: `tests/e2e/real_e2e_full_pipeline.py`.

### Quick Start

```bash
# Full E2E test with stratified architecture
PYTHONPATH=/home/kwar/code/agentic-ai \
EXECUTION_MODE=hybrid \
QA_LEVEL=fast \
QUALITY_GATE_ENV=dev \
timeout 9000 python tests/e2e/real_e2e_full_pipeline.py tests/e2e/test_specs/ecommerce-api-spec-human.md | tee /tmp/e2e_test.log
```

**Usage**: `python tests/e2e/real_e2e_full_pipeline.py <spec_file_path>`

**Environment Variables**:

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `EXECUTION_MODE` | safe, hybrid, research | hybrid | Controls LLM usage |
| `QA_LEVEL` | fast, heavy | fast | Validation depth |
| `QUALITY_GATE_ENV` | dev, staging, production | dev | Policy strictness |

---

## Phase Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         E2E PIPELINE PHASES                          │
├─────────────────────────────────────────────────────────────────────┤
│  Phase 1: Spec Ingestion                                            │
│  ├─ SpecParser → SpecRequirements (legacy)                          │
│  └─ SpecToApplicationIR → ApplicationIR (IR-centric) ✨              │
├─────────────────────────────────────────────────────────────────────┤
│  Phase 2: DAG Generation                                            │
│  └─ Multi-Pass Planner con ApplicationIR                            │
├─────────────────────────────────────────────────────────────────────┤
│  Phase 3: Multi-Pass Planning                                       │
│  └─ DAG ground truth desde IR                                       │
├─────────────────────────────────────────────────────────────────────┤
│  Phase 4: Code Generation Setup                                     │
│  └─ Preparación de generadores                                      │
├─────────────────────────────────────────────────────────────────────┤
│  Phase 5: Entity/Schema Generation                                  │
│  └─ SQLAlchemy entities + Pydantic schemas                          │
├─────────────────────────────────────────────────────────────────────┤
│  Phase 6: Full Code Generation                                      │
│  └─ generate_from_application_ir() - IR-driven generation           │
├─────────────────────────────────────────────────────────────────────┤
│  Phase 6.5: IR-based Test Generation ✨                             │
│  ├─ TestGeneratorFromIR (ValidationModelIR → pytest)                │
│  ├─ IntegrationTestGeneratorFromIR (BehaviorModelIR → integration)  │
│  └─ APIContractValidatorFromIR (APIModelIR → contract tests)        │
├─────────────────────────────────────────────────────────────────────┤
│  Phase 6.6: IR-based Service Generation ✨ NEW                      │
│  ├─ ServiceGeneratorFromIR (BehaviorModelIR → service methods)      │
│  ├─ BusinessFlowService (cross-entity flows)                        │
│  └─ get_flow_coverage_report() (coverage tracking)                  │
├─────────────────────────────────────────────────────────────────────┤
│  Phase 7: Code Repair                                               │
│  └─ CodeRepairAgent - fixing syntax/import errors                   │
├─────────────────────────────────────────────────────────────────────┤
│  Phase 8: Test Execution                                            │
│  └─ pytest execution + coverage                                     │
├─────────────────────────────────────────────────────────────────────┤
│  Phase 9: Validation                                                │
│  ├─ Semantic validation                                             │
│  ├─ Compliance checking                                             │
│  └─ IR-based Compliance Check ✨ NEW                                │
│      ├─ EntityComplianceChecker (DomainModelIR validation)          │
│      ├─ FlowComplianceChecker (BehaviorModelIR validation)          │
│      └─ ConstraintComplianceChecker (ValidationModelIR validation)  │
├─────────────────────────────────────────────────────────────────────┤
│  Phase 10: Metrics & Reporting                                      │
│  └─ Final metrics collection + summary                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## New Services (Phase 6.5 & Phase 9)

### IR Test Generator (`src/services/ir_test_generator.py`)

Genera tests automáticamente desde los modelos IR:

```python
from src.services.ir_test_generator import (
    generate_all_tests_from_ir,
    TestGeneratorFromIR,
    IntegrationTestGeneratorFromIR,
    APIContractValidatorFromIR
)

# Uso simple - genera todos los tests
generated_files = generate_all_tests_from_ir(application_ir, output_dir)

# Uso específico
test_gen = TestGeneratorFromIR(validation_model)
pytest_code = test_gen.generate_tests()

integration_gen = IntegrationTestGeneratorFromIR(behavior_model)
integration_tests = integration_gen.generate_tests()

contract_gen = APIContractValidatorFromIR(api_model)
contract_tests = contract_gen.generate_contract_tests()
```

**Tipos de tests generados:**

| Validation Type | Test Generated |
|-----------------|----------------|
| PRESENCE | `test_{entity}_{attr}_required()` |
| FORMAT | `test_{entity}_{attr}_format()` |
| RANGE | `test_{entity}_{attr}_range()` |
| UNIQUENESS | `test_{entity}_{attr}_unique()` |
| RELATIONSHIP | `test_{entity}_{attr}_relationship()` |
| STATUS_TRANSITION | `test_{entity}_{attr}_transitions()` |

---

### IR Compliance Checker (`src/services/ir_compliance_checker.py`)

Valida que el código generado cumpla con los modelos IR:

```python
from src.services.ir_compliance_checker import (
    check_full_ir_compliance,
    EntityComplianceChecker,
    FlowComplianceChecker,
    ConstraintComplianceChecker
)

# Uso simple - check completo
reports = check_full_ir_compliance(application_ir, generated_app_path)
# Returns: {"entity": ComplianceReport, "flow": ComplianceReport, "constraint": ComplianceReport}

# Uso específico
entity_checker = EntityComplianceChecker(domain_model)
report = entity_checker.check_entities_file(entities_path)

flow_checker = FlowComplianceChecker(behavior_model)
report = flow_checker.check_services_directory(services_dir)

constraint_checker = ConstraintComplianceChecker(validation_model)
report = constraint_checker.check_constraints(entities_path, schemas_path)
```

**ComplianceReport:**

```python
@dataclass
class ComplianceReport:
    total_expected: int      # Elementos esperados del IR
    total_found: int         # Elementos encontrados en código
    issues: List[Issue]      # Problemas detectados
    coverage: float          # % de cobertura

    @property
    def is_compliant(self) -> bool

    @property
    def compliance_score(self) -> float  # 0-100%
```

---

## Integration in E2E Pipeline

### Imports (línea ~85)

```python
# IR-based Test Generation and Compliance Checking
try:
    from src.services.ir_test_generator import (
        generate_all_tests_from_ir,
        TestGeneratorFromIR,
        IntegrationTestGeneratorFromIR,
        APIContractValidatorFromIR
    )
    from src.services.ir_compliance_checker import (
        check_full_ir_compliance,
        EntityComplianceChecker,
        FlowComplianceChecker,
        ConstraintComplianceChecker
    )
    IR_SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: IR services not available: {e}")
    IR_SERVICES_AVAILABLE = False
```

### Phase 6.5: Test Generation (línea ~2024)

```python
# Phase 6.5: Generate IR-based tests if available
if IR_SERVICES_AVAILABLE and self.application_ir and self.output_path:
    try:
        print("\n  🧪 Phase 6.5: IR-based Test Generation")
        tests_output_dir = self.output_path / "tests" / "generated"
        generated_test_files = generate_all_tests_from_ir(
            self.application_ir,
            tests_output_dir
        )
        if generated_test_files:
            print(f"    ✅ Generated {len(generated_test_files)} test files:")
            for test_type, path in generated_test_files.items():
                print(f"       - {test_type}: {path.name}")
    except Exception as e:
        print(f"    ⚠️  IR test generation failed (non-blocking): {e}")
```

### Phase 9: IR Compliance Check (línea ~3225)

```python
# IR-based Compliance Check
ir_compliance_reports = {}
if IR_SERVICES_AVAILABLE and self.application_ir and self.output_path:
    try:
        print("\n  🔬 Running IR-based Compliance Check...")
        ir_compliance_reports = check_full_ir_compliance(
            self.application_ir,
            self.output_path
        )
        for checker_type, report in ir_compliance_reports.items():
            status = "✅" if report.is_compliant else "⚠️"
            print(f"    {status} {checker_type.capitalize()}: "
                  f"{report.compliance_score:.1f}% "
                  f"({report.total_found}/{report.total_expected})")
            if report.issues:
                errors = [i for i in report.issues if i.severity == "error"]
                if errors:
                    print(f"       Errors: {len(errors)}")
    except Exception as e:
        print(f"    ⚠️  IR compliance check failed (non-blocking): {e}")
```

---

## Output Directory Structure

```
generated_app/
├── src/
│   ├── models/
│   │   ├── entities.py      ← Validated by EntityComplianceChecker
│   │   └── schemas.py       ← Validated by ConstraintComplianceChecker
│   ├── services/            ← Validated by FlowComplianceChecker
│   ├── routes/
│   └── repositories/
├── tests/
│   ├── generated/           ← NEW: IR-generated tests
│   │   ├── test_validation_rules.py
│   │   ├── test_integration_flows.py
│   │   └── test_api_contracts.py
│   └── unit/
└── alembic/
```

---

## Error Handling

Todas las integraciones son **non-blocking**:

- Si IR extraction falla → continúa con SpecRequirements
- Si test generation falla → continúa sin tests generados
- Si compliance check falla → reporta warning, continúa

Esto garantiza backward compatibility y robustez.

---

## Stratified Architecture Integration

El pipeline E2E integra la arquitectura estratificada (4 strata: TEMPLATE → AST → LLM → QA):

### Components Initialized

| Component | Purpose |
|-----------|---------|
| ExecutionModeManager | Controls SAFE/HYBRID/RESEARCH modes |
| ManifestBuilder | Tracks what generated each file |
| MetricsCollector | Time, errors, tokens by stratum |
| QualityGate | Policy enforcement by environment |
| GoldenAppRunner | Regression validation vs baselines |
| SkeletonGenerator | Generates structure with LLM slots |
| PatternPromoter | Formal criteria for stratum graduation |
| BasicValidationPipeline | py_compile + regression patterns |

### Output Artifacts

After E2E run, the generated app contains:

```text
generated_app/
├── src/
├── tests/
├── generation_manifest.json   ← File provenance tracking
├── stratum_metrics.json       ← Performance by stratum
├── quality_gate.json          ← Policy compliance result
└── golden_app_comparison.json ← Baseline comparison
```

See [E2E_STRATIFIED_INTEGRATION_SUMMARY.md](E2E_STRATIFIED_INTEGRATION_SUMMARY.md) for full details.

---

## Related Documentation

- [E2E_STRATIFIED_INTEGRATION_SUMMARY.md](E2E_STRATIFIED_INTEGRATION_SUMMARY.md) - **Stratified architecture quick reference**
- [STRATIFIED_ENHANCEMENTS_PLAN.md](STRATIFIED_ENHANCEMENTS_PLAN.md) - Full implementation details
- [E2E_IR_CENTRIC_INTEGRATION.md](E2E_IR_CENTRIC_INTEGRATION.md) - IR architecture overview
- [SEMANTIC_VALIDATION_ARCHITECTURE.md](SEMANTIC_VALIDATION_ARCHITECTURE.md) - Validation system
- [PHASE_2_UNIFIED_CONSTRAINT_EXTRACTOR.md](PHASE_2_UNIFIED_CONSTRAINT_EXTRACTOR.md) - Constraint extraction
- [phases.md](phases.md) - Phase execution order

---

## Files Modified/Created

| File | Description |
|------|-------------|
| `src/services/ir_test_generator.py` | NEW: Test generation from IR models |
| `src/services/ir_compliance_checker.py` | NEW: Compliance validation against IR |
| `tests/e2e/real_e2e_full_pipeline.py` | MODIFIED: Phase 6.5 + Phase 9 IR integration |

---

## Metrics

**Expected compliance targets:**
- Entity compliance: ≥95%
- Flow compliance: ≥80%
- Constraint compliance: ≥90%

**Test generation coverage:**
- Validation rules → pytest tests: 100%
- Behavior flows → integration tests: 100%
- API endpoints → contract tests: 100%
