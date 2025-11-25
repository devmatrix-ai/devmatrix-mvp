# Fases del Pipeline E2E

## Orden de Ejecución

| # | Fase | Método | Descripción |
|---|------|--------|-------------|
| 1 | Spec Ingestion | `_phase_1_spec_ingestion()` | Parsea spec MD, extrae requirements, entities, endpoints |
| 1.5 | Validation Scaling | `_phase_1_5_validation_scaling()` | Extrae validaciones con BusinessLogicExtractor |
| 2 | Requirements Analysis | `_phase_2_requirements_analysis()` | Clasifica requirements semánticamente, busca patrones |
| 3 | Multi-Pass Planning | `_phase_3_multi_pass_planning()` | Construye DAG, infiere dependencias, crea waves |
| 4 | Atomization | `_phase_4_atomization()` | Divide en atomic units, valida granularidad |
| 5 | DAG Construction | `_phase_5_dag_construction()` | Construye grafo de dependencias final |
| 6 | Code Generation | `_phase_6_code_generation()` | Genera código real usando CodeGenerationService |
| 7 | Deployment | `_phase_7_deployment()` | Escribe archivos al disco |
| 8 | Code Repair | `_phase_8_code_repair()` | Itera reparación: compliance check → fix → validate |
| 9 | Validation | `_phase_9_validation()` | Tests reales, coverage real, compliance |
| 10 | Health Verification | `_phase_10_health_verification()` | Verifica app está ready |
| 11 | Learning | `_phase_11_learning()` | Registra patrones exitosos para feedback |

---

## Desglose por Categoría

### Input & Analysis (Fases 1-1.5)

| Fase | Descripción |
|------|-------------|
| **Fase 1** | Lee spec markdown + extrae metadata |
| **Fase 1.5** | Identifica validaciones (nuevas en v2) |

### Planning & Architecture (Fases 2-5)

| Fase | Descripción |
|------|-------------|
| **Fase 2** | Clasifica requirements (semántico con RequirementsClassifier) |
| **Fase 3** | Planifica ejecución (DAG + topological sort) |
| **Fase 4** | Atomiza código en unidades pequeñas |
| **Fase 5** | Construye grafo final de dependencias |

### Code Generation (Fase 6)

| Fase | Descripción |
|------|-------------|
| **Fase 6** | Genera código Python real desde IR |

### Refinement (Fases 7-8)

| Fase | Descripción |
|------|-------------|
| **Fase 7** | Escribe archivos |
| **Fase 8** | Repair loop iterativo (hasta 3 iteraciones máx o compliance ≥80%) |

### Validation & Learning (Fases 9-11)

| Fase | Descripción |
|------|-------------|
| **Fase 9** | Ejecuta tests reales |
| **Fase 10** | Verifica salud de app |
| **Fase 11** | Almacena patrones para feedback |
