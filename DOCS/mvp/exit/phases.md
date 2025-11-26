# Fases del Pipeline E2E

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

### Refinement (Fases 7-8) - Post-Generation

| Fase | IR Usage | Descripción |
|------|----------|-------------|
| **Fase 7** | ✅ **MIGRADO** | Usa ApplicationIR (DomainModelIR, APIModelIR) |
| **Fase 8** | ❌ | Ejecuta tests (output) |

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
| `ComplianceValidator` | ApplicationIR + code | compliance report |
