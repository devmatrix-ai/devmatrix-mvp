# Fases del Pipeline E2E

**Date**: Nov 26, 2025
**Status**: PRODUCTION
**File**: `tests/e2e/real_e2e_full_pipeline.py`

---

## Quick Start

```bash
# Full E2E test with stratified architecture
PYTHONPATH=/home/kwar/code/agentic-ai \
EXECUTION_MODE=hybrid \
QA_LEVEL=fast \
QUALITY_GATE_ENV=dev \
timeout 9000 python tests/e2e/real_e2e_full_pipeline.py tests/e2e/test_specs/ecommerce-api-spec-human.md | tee /tmp/e2e_test.log
```

**Usage**: `python tests/e2e/real_e2e_full_pipeline.py <spec_file_path>`

---

## Orden de Ejecución

| # | Fase | Método | Usa IR? | Descripción |
|---|------|--------|---------|-------------|
| 1 | Spec Ingestion | `_phase_1_spec_ingestion()` | ✅ **EXTRAE** | Parsea spec MD → **genera ApplicationIR** |
| 1.5 | Validation Scaling | `_phase_1_5_validation_scaling()` | ✅ | Extrae validaciones con BusinessLogicExtractor |
| 2 | Requirements Analysis | `_phase_2_requirements_analysis()` | ✅ | `get_dag_ground_truth()` desde ApplicationIR |
| 3 | Multi-Pass Planning | `_phase_3_multi_pass_planning()` | ✅ **MIGRADO** | DAG ground truth ✅, nodos ✅ desde IR (entities, endpoints, flows) |
| 4 | Atomization | `_phase_4_atomization()` | ❌ | Divide en atomic units (planificación legacy) |
| 5 | DAG Construction | `_phase_5_dag_construction()` | ✅ | Valida DAG - hereda nodos IR de Phase 3 |
| 6 | Code Generation | `_phase_6_code_generation()` | ✅ **REQUIERE** | `generate_from_application_ir()` |
| 6.5 | IR Test Generation | `Phase 6.5 block` | ✅ **REQUIERE** | TestGeneratorFromIR (ValidationModelIR → pytest) |
| 6.6 | IR Service Generation | `Phase 6.6 block` | ✅ **REQUIERE** | ServiceGeneratorFromIR (BehaviorModelIR → services) |
| 7 | Code Repair | `_phase_code_repair()` | ✅ **MIGRADO** | Usa ApplicationIR (DomainModelIR, APIModelIR) con fallback legacy |
| 8 | Test Execution | `_phase_test_execution()` | ❌ | pytest execution + coverage |
| 8.5 | Runtime Smoke Test | `_phase_8_5_runtime_smoke_test()` | ✅ | Docker compose + seed_db + HTTP endpoint validation |
| 9 | Validation | `_phase_9_validation()` | ✅ **REQUIERE** | Compliance check contra ApplicationIR |
| 10 | Health Verification | `_phase_10_health_verification()` | ❌ | Verifica app está ready |
| 11 | Learning | `_phase_11_learning()` | ❌ | Registra patrones exitosos |

---

## IR Flow Architecture

```text
Spec (Natural Language)
         │
         ▼
┌─────────────────────────────────────────────────┐
│  Phase 1: SpecToApplicationIR                   │
│  └─ Genera ApplicationIR (ONE-TIME extraction)  │
└─────────────────────────────────────────────────┘
         │
         ▼
    ApplicationIR ─────────────────────────────────┐
         │                                         │
         ├─────────────────┬───────────────┐       │
         │                 │               │       │
         ▼                 ▼               ▼       │
    DomainModelIR    APIModelIR    BehaviorModelIR │
    (entities)       (endpoints)   (flows)         │
         │                 │               │       │
         └────────┬────────┘               │       │
                  │                        │       │
                  ▼                        ▼       │
         ┌────────────────────────────────────┐    │
         │  Phase 6: Code Generation          │    │
         │  generate_from_application_ir()    │◄───┘
         └────────────────────────────────────┘
                  │
         ┌───────┴───────┐
         ▼               ▼
   Phase 6.5         Phase 6.6
   Test Gen          Service Gen
         │               │
         └───────┬───────┘
                 ▼
         Generated Code
                 │
                 ▼
         ┌────────────────────────────────────┐
         │  Phase 7: Code Repair (usa IR) ✅  │
         │  Phase 8: Test Execution           │
         │  Phase 8.5: Runtime Smoke Test ✅  │
         └────────────────────────────────────┘
                 │
                 ▼
         ┌────────────────────────────────────┐
         │  Phase 9: Validation               │◄─── ApplicationIR (ground truth)
         │  ComplianceValidator vs IR         │
         └────────────────────────────────────┘
```

---

## Desglose por Categoría

### Input & Analysis (Fases 1-1.5) - IR Generation

| Fase | IR Usage | Descripción |
|------|----------|-------------|
| **Fase 1** | ✅ EXTRAE | Lee spec markdown → **genera ApplicationIR** |
| **Fase 1.5** | ✅ | Identifica validaciones → ValidationModelIR |

### Planning & Architecture (Fases 2-5) - Mixed

| Fase | IR Usage | Descripción |
|------|----------|-------------|
| **Fase 2** | ✅ | Usa `ApplicationIR.get_dag_ground_truth()` |
| **Fase 3** | ✅ **MIGRADO** | DAG nodos desde IR (entities, endpoints, flows) |
| **Fase 4** | ❌ | Atomiza código (legacy planning) |
| **Fase 5** | ✅ | Hereda nodos IR de Phase 3 |

### Code Generation (Fases 6-6.6) - IR-Centric

| Fase | IR Usage | Descripción |
|------|----------|-------------|
| **Fase 6** | ✅ **REQUIERE** | `generate_from_application_ir()` |
| **Fase 6.5** | ✅ **REQUIERE** | ValidationModelIR → pytest tests |
| **Fase 6.6** | ✅ **REQUIERE** | BehaviorModelIR → service methods |

### Refinement (Fases 7-8.5) - Post-Generation

| Fase | IR Usage | Descripción |
|------|----------|-------------|
| **Fase 7** | ✅ **MIGRADO** | Usa ApplicationIR (DomainModelIR, APIModelIR) |
| **Fase 8** | ❌ | Ejecuta tests (output) |
| **Fase 8.5** | ✅ | Runtime smoke test con Docker + seed_db.py |

### Validation & Learning (Fases 9-11)

| Fase | IR Usage | Descripción |
|------|----------|-------------|
| **Fase 9** | ✅ **REQUIERE** | Compliance check contra ApplicationIR |
| **Fase 10** | ❌ | Health check operacional |
| **Fase 11** | ❌ | Learning patterns |

---

## Por qué algunas fases NO usan IR

| Fase | Justificación |
|------|---------------|
| **Phase 4** | Planificación interna - atomización legacy |
| **Phase 8** | Ejecuta tests sobre código, no necesita IR |
| **Phase 10** | Health check operacional - runtime |
| **Phase 11** | Pattern learning - meta-operación |

---

## Key IR Services

| Service | Input IR | Output |
|---------|----------|--------|
| `SpecToApplicationIR` | Natural language spec | ApplicationIR |
| `generate_from_application_ir()` | ApplicationIR | Generated code |
| `TestGeneratorFromIR` | ValidationModelIR | pytest tests |
| `ServiceGeneratorFromIR` | BehaviorModelIR | service methods |
| `RuntimeSmokeValidator` | ApplicationIR | smoke test results |
| `ComplianceValidator` | ApplicationIR + code | compliance report |

---

## Phase 8.5: Runtime Smoke Test

**Purpose**: Validación en runtime de la aplicación generada con Docker

**Components**:
1. **Docker Compose**: Levanta PostgreSQL + API server
2. **seed_db.py**: Genera datos de prueba desde DomainModelIR
3. **Smoke Tests**: Prueba HTTP endpoints con UUIDs predecibles

**IR Usage**:
- Genera `seed_db.py` desde DomainModelIR (entities + constraints)
- Lee `enum_values` desde `attr.constraints.enum_values`
- Genera UUIDs predecibles para cada entity type

**Key Files**:
- `runtime_smoke_validator.py`: Orchestrates Docker + smoke tests
- `code_generation_service.py`: Generates seed_db.py template
- `real_e2e_full_pipeline.py:_phase_8_5_runtime_smoke_test()`

**Bug History** (Nov 27, 2025):
- Bug #97-102: seed_db.py generation fixes for IR attribute names
- Bug #101: Pipeline now correctly reports FAILED when smoke test fails
- Bug #102: Fixed enum_values lookup (constraints dict vs direct attr)

---

## Related Documentation

- [E2E_STRATIFIED_INTEGRATION_SUMMARY.md](E2E_STRATIFIED_INTEGRATION_SUMMARY.md) - **Stratified architecture quick reference**
- [STRATIFIED_ENHANCEMENTS_PLAN.md](STRATIFIED_ENHANCEMENTS_PLAN.md) - Full stratified implementation details
- [E2E_IR_CENTRIC_INTEGRATION.md](E2E_IR_CENTRIC_INTEGRATION.md) - IR architecture overview
- [PIPELINE_E2E_PHASES.md](PIPELINE_E2E_PHASES.md) - Complete phase reference
- [SEMANTIC_VALIDATION_ARCHITECTURE.md](SEMANTIC_VALIDATION_ARCHITECTURE.md) - Validation system
