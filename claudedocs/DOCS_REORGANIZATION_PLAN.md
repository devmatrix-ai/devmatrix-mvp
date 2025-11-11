# Plan Completo de Reorganización de Documentación

**Fecha**: 2025-11-10
**Estado**: Listo para ejecución
**Archivos analizados**: 151 archivos markdown
**Directorios**: 14 carpetas principales

---

## 📊 Estado Actual - Análisis Completo

### Inventario Total

**Archivos por ubicación:**
```
Raíz de DOCS:                17 archivos
MGE_V2/:                     26 archivos
rag/:                        38 archivos
test-suite-enhancement/:     13 archivos
guides/:                      8 archivos
guides-tutorials/:            5 archivos
project-status/:              6 archivos
masterplan/:                  9 archivos
integration/:                 3 archivos
implementation-reports/:      3 archivos
archive/:                    11 archivos
reference/:                   4 archivos
analysis/:                    1 archivo
api/:                         1 archivo
eval/:                        2 archivos
graph-improvements/:          1 archivo
templates/:                   6 archivos (NO markdown, sino Jinja2)
────────────────────────────────────────
Total:                      151+ archivos
```

### Problemas Identificados

1. **Archivos sueltos en raíz** (17 archivos):
   - `WORKPLAN.md`, `PROJECT_MEMORY.md`, `CURRENT_STATE.md`
   - `MASTERPLAN_FLOW_ANALYSIS.md`, `MASTERPLAN_FLOW_DIAGRAM.md`
   - `MGE_V2_IMPLEMENTATION_COMPLETE.md`
   - 3 archivos `mge_v2_*.md` duplicados con carpeta MGE_V2/
   - Archivos de features, security, RAG metrics en raíz

2. **Duplicación y redundancia**:
   - Múltiples archivos de "status" en diferentes carpetas
   - Información de MGE V2 dispersa (raíz + MGE_V2/ + integration/)
   - Reportes de implementación duplicados

3. **Falta de jerarquía lógica**:
   - No hay estructura numerada para orden de lectura
   - Carpetas sin READMEs explicativos
   - Mezcla de guías técnicas con reportes históricos

4. **Documentación incompleta de Infrastructure Generation**:
   - Feature implementado pero sin docs en DOCS/
   - Templates existen en `/templates/` pero sin guía de uso
   - No hay troubleshooting ni ejemplos

5. **Carpetas con nombres inconsistentes**:
   - `guides/` vs `guides-tutorials/` (confuso)
   - `test-suite-enhancement/` nombre muy largo
   - `eval/` nombre no descriptivo

---

## 🎯 Estructura Objetivo

### Jerarquía Propuesta con Numeración

```
DOCS/
│
├── README.md                               # ✨ NUEVO: Índice maestro completo
│
├── 00-getting-started/                     # ✨ NUEVO: Quick start
│   ├── README.md                           # Índice de sección
│   ├── quick-start.md                      # ✨ NUEVO: 5 min setup
│   ├── installation.md                     # ✨ NUEVO: Instalación detallada
│   ├── first-project.md                    # ✨ NUEVO: Tu primer proyecto
│   └── concepts.md                         # ✨ NUEVO: Conceptos básicos DDD
│
├── 01-architecture/                        # Sistema de alto nivel
│   ├── README.md                           # Índice de sección
│   ├── overview.md                         # ← MERGE de ANALYSIS.md + parts de ARCHITECTURE_STATUS
│   ├── system-design.md                    # ← ARCHITECTURE.md (reference/)
│   ├── data-flow.md                        # ✨ NUEVO: Flujo end-to-end
│   ├── technology-stack.md                 # ✨ NUEVO: Tech stack actual
│   └── domain-driven-design.md             # ✨ NUEVO: DDD en DevMatrix
│
├── 02-core-features/                       # Features principales
│   ├── README.md                           # Índice de features
│   │
│   ├── authentication/
│   │   ├── README.md                       # ← AUTHENTICATION_SYSTEM.md
│   │   ├── architecture.md                 # Detalles técnicos
│   │   └── api-reference.md                # Endpoints
│   │
│   ├── discovery/
│   │   ├── README.md                       # ✨ NUEVO: Discovery overview
│   │   ├── ddd-extraction.md               # ✨ NUEVO: DDD extraction
│   │   └── requirements-analysis.md        # ✨ NUEVO: Análisis de reqs
│   │
│   ├── masterplan/
│   │   ├── README.md                       # ← MASTERPLAN_DESIGN.md
│   │   ├── generation.md                   # Generación de masterplan
│   │   ├── flow-analysis.md                # ← MASTERPLAN_FLOW_ANALYSIS.md
│   │   ├── flow-diagram.md                 # ← MASTERPLAN_FLOW_DIAGRAM.md
│   │   ├── issues-prioritized.md           # ← MASTERPLAN_ISSUES_PRIORITIZED.md
│   │   ├── intelligent-calculation.md      # ← masterplan/INTELLIGENT_TASK_CALCULATION.md
│   │   ├── frontend-integration.md         # ← masterplan/FRONTEND_INTEGRATION_*
│   │   └── progress-ui.md                  # ← MASTERPLAN_PROGRESS_UI_DESIGN.md
│   │
│   ├── rag-system/
│   │   ├── README.md                       # ← rag/README.md + 00_ANALYSIS_INDEX.md
│   │   ├── INDEX.md                        # ← rag/INDEX.md
│   │   ├── architecture.md                 # ✨ NUEVO: RAG architecture
│   │   ├── optimization-summary.md         # ← RAG_OPTIMIZATION_FINAL_SUMMARY.md
│   │   ├── metrics.md                      # ← RAG_METRICS.md
│   │   ├── quick-reference.md              # ← rag/QUICK_REFERENCE.md
│   │   ├── troubleshooting.md              # ← rag/troubleshooting.md
│   │   ├── dashboard.md                    # ← rag/dashboard.md
│   │   ├── embedding-models.md             # ← MERGE de embedding_*.md
│   │   ├── maintenance-log.md              # ← rag/maintenance_log.md
│   │   │
│   │   ├── phases/                         # Fases de optimización RAG
│   │   │   ├── phase-1-gpu.md              # ← rag/PHASE1_*
│   │   │   ├── phase-2-completion.md       # ← rag/PHASE2_*
│   │   │   ├── phase-3-query-expansion.md  # ← rag/PHASE3_*
│   │   │   └── phase-4-final.md            # ← rag/PHASE4_FINAL_REPORT.md
│   │   │
│   │   └── analysis/                       # Análisis RAG
│   │       ├── deep-analysis.md            # ← rag/ANALISIS_RAG_PROFUNDO.md
│   │       ├── quality-analysis.md         # ← rag/RAG_QUALITY_ANALYSIS_REPORT.md
│   │       ├── code-quality.md             # ← rag/ANALISIS_CODIGO_QUALITY_RAG.md
│   │       ├── deliverables.md             # ← rag/ANALISIS_RAG_DELIVERABLES.md
│   │       └── data-gaps.md                # ← rag/RAG_DATA_GAPS_SUMMARY.md
│   │
│   ├── multi-tenancy/
│   │   └── README.md                       # ← MULTI_TENANCY.md
│   │
│   ├── web-ui/
│   │   ├── README.md                       # ← WEB_UI.md
│   │   └── frontend-roadmap.md             # ← FRONTEND_ROADMAP.md
│   │
│   └── graph-system/
│       └── roadmap.md                      # ← graph-improvements/ROADMAP.md
│
├── 03-mge-v2/                              # MGE V2 completo
│   ├── README.md                           # ← MGE_V2/README.md (actualizado)
│   │
│   ├── 00-executive-summary.md             # ← MGE_V2/00_EXECUTIVE_SUMMARY.md
│   ├── 01-context.md                       # ← MGE_V2/01_CONTEXT_MVP_TO_V2.md
│   ├── 02-why-v2.md                        # ← MGE_V2/02_WHY_V2_NOT_V1.md
│   ├── 03-architecture.md                  # ← MGE_V2/03_ARCHITECTURE_OVERVIEW.md
│   ├── 04-comparison.md                    # ← MGE_V2/ARCHITECTURE_COMPARISON.md
│   ├── 05-complete-spec.md                 # ← MGE_V2/MGE_V2_COMPLETE_TECHNICAL_SPEC.md
│   │
│   ├── phases/                             # Fases de implementación
│   │   ├── README.md                       # Índice de fases
│   │   ├── phase-0-2-foundation.md         # ← MGE_V2/04_PHASE_0_2_FOUNDATION.md
│   │   ├── phase-3-atomization.md          # ← MGE_V2/05_PHASE_3_AST_ATOMIZATION.md
│   │   ├── phase-4-dependency.md           # ← MGE_V2/06_PHASE_4_DEPENDENCY_GRAPH.md
│   │   ├── phase-5-validation.md           # ← MGE_V2/07_PHASE_5_HIERARCHICAL_VALIDATION.md
│   │   ├── phase-6-execution.md            # ← MGE_V2/08_PHASE_6_EXECUTION_RETRY.md
│   │   └── phase-7-human-review.md         # ← MGE_V2/09_PHASE_7_HUMAN_REVIEW.md
│   │
│   ├── infrastructure-generation/          # ✨ NUEVO: Infrastructure docs
│   │   ├── README.md                       # ✨ NUEVO: Overview completo
│   │   ├── architecture.md                 # ✨ NUEVO: Diseño técnico
│   │   ├── templates-guide.md              # ✨ NUEVO: Guía de templates
│   │   ├── usage-examples.md               # ✨ NUEVO: Ejemplos de uso
│   │   ├── troubleshooting.md              # ✨ NUEVO: Solución de problemas
│   │   └── plan.md                         # ← mge_v2_complete_project_generation_plan.md
│   │
│   ├── implementation/                     # Implementación y testing
│   │   ├── README.md                       # Índice de implementación
│   │   ├── roadmap.md                      # ← MGE_V2/11_IMPLEMENTATION_ROADMAP.md
│   │   ├── testing-strategy.md             # ← MGE_V2/12_TESTING_STRATEGY.md
│   │   ├── testing-summary.md              # ← MGE_V2/TESTING_SUMMARY.md
│   │   ├── performance-cost.md             # ← MGE_V2/13_PERFORMANCE_COST.md
│   │   ├── risks-mitigation.md             # ← MGE_V2/14_RISKS_MITIGATION.md
│   │   ├── caching-guide.md                # ← MGE_V2/caching_guide.md
│   │   ├── precision-deep-dive.md          # ← MGE_V2/MGE_PRECISION_DEEP_DIVE.md
│   │   ├── precision-readiness.md          # ← MGE_V2/precision_readiness_checklist.md
│   │   └── gap-10-summary.md               # ← MGE_V2/gap-10-implementation-summary.md
│   │
│   ├── integration/                        # Integración con sistema
│   │   ├── README.md                       # ← integration/MGE_V2_INTEGRATION_GUIDE.md
│   │   ├── status.md                       # ← integration/MGE_V2_INTEGRATION_STATUS.md
│   │   ├── complete.md                     # ← integration/MGE_V2_INTEGRATION_COMPLETE.md
│   │   └── devmatrix.md                    # ← MGE_V2/10_INTEGRATION_DEVMATRIX.md
│   │
│   ├── migration/                          # Estrategia de migración
│   │   ├── README.md                       # ← MGE_V2/MIGRATION_EXECUTIVE_SUMMARY.md
│   │   └── dual-mode-strategy.md           # ← MGE_V2/DUAL_MODE_MIGRATION_STRATEGY.md
│   │
│   └── status/                             # Estado de implementación
│       ├── README.md                       # Estado actual consolidado
│       ├── implementation-complete.md      # ← MGE_V2_IMPLEMENTATION_COMPLETE.md
│       ├── implementation-status.md        # ← MGE_V2/implementation_status_report.md
│       ├── analysis-plan.md                # ← mge_v2_analysis_and_implementation_plan.md
│       ├── final-status.md                 # ← mge_v2_final_status_report.md
│       └── comparison.md                   # ← eval/MGE_V1_VS_V2_COMPARISON.md
│
├── 04-api-reference/                       # API documentation
│   ├── README.md                           # ← API_REFERENCE.md
│   ├── rest-api/
│   │   └── validation-api.md               # ← api/validation-api.md
│   ├── websocket-api/
│   │   └── streaming.md                    # ✨ NUEVO: WebSocket streaming
│   └── internal-services/
│       └── README.md                       # ✨ NUEVO: Servicios internos
│
├── 05-guides/                              # Guías operacionales
│   ├── README.md                           # Índice de guías
│   │
│   ├── development/
│   │   ├── README.md                       # ← GUIA_DE_USO.md
│   │   ├── checklist.md                    # ← DEVELOPMENT_CHECKLIST.md
│   │   ├── local-operations.md             # ← LOCAL_OPERATIONS_RUNBOOK.md
│   │   └── troubleshooting.md              # ← guides/TROUBLESHOOTING.md
│   │
│   ├── deployment/
│   │   ├── README.md                       # ← DEPLOYMENT.md
│   │   ├── docker.md                       # ✨ NUEVO: Docker deployment
│   │   └── production.md                   # ✨ NUEVO: Production setup
│   │
│   └── monitoring/
│       ├── README.md                       # ← MONITORING_GUIDE.md
│       └── quickstart.md                   # ← MONITORING_QUICKSTART.md
│
├── 06-tutorials/                           # Tutoriales paso a paso
│   ├── README.md                           # Índice de tutorials
│   └── demo-final.md                       # ← DEMO_FINAL.md
│
├── 07-testing/                             # Testing completo
│   ├── README.md                           # ← test-suite-enhancement/README_TEST_SUITE.md
│   │
│   ├── overview/
│   │   ├── project-summary.md              # ← test-suite-enhancement/PROJECT_COMPLETE_SUMMARY.md
│   │   ├── branch-summary.md               # ← test-suite-enhancement/BRANCH_COMPLETE_SUMMARY.md
│   │   └── coverage-audit.md               # ← test-suite-enhancement/COVERAGE_AUDIT_BASELINE.md
│   │
│   ├── reports/
│   │   ├── phase-2-completion.md           # ← test-suite-enhancement/PHASE_2_COMPLETION_REPORT.md
│   │   ├── phase-6-final.md                # ← test-suite-enhancement/PHASE_6_FINAL_REPORT.md
│   │   ├── final-implementation.md         # ← test-suite-enhancement/FINAL_IMPLEMENTATION_REPORT.md
│   │   ├── comprehensive-results.md        # ← test-suite-enhancement/COMPREHENSIVE_TEST_RESULTS.md
│   │   ├── test-execution.md               # ← test-suite-enhancement/TEST_EXECUTION_REPORT.md
│   │   ├── test-results.md                 # ← test-suite-enhancement/TEST_RESULTS.md
│   │   └── e2e-results.md                  # ← test-suite-enhancement/E2E_TEST_RESULTS.md
│   │
│   ├── compliance/
│   │   └── constitution-compliance.md      # ← test-suite-enhancement/CONSTITUTION_COMPLIANCE_REPORT.md
│   │
│   └── progress/
│       └── test-suite-progress.md          # ← test-suite-enhancement/TEST_SUITE_PROGRESS.md
│
├── 08-implementation-reports/              # Reportes de features
│   ├── README.md                           # Índice de reportes
│   ├── summary.md                          # ← implementation-reports/IMPLEMENTATION_SUMMARY.md
│   ├── rag-phase2.md                       # ← implementation-reports/RAG_PHASE2_IMPLEMENTATION.md
│   ├── rag-population.md                   # ← implementation-reports/RAG_POPULATION_REPORT.md
│   └── p0-critical-fixes.md                # ← P0_CRITICAL_FIXES_IMPLEMENTATION.md
│
├── 09-security/                            # ✨ NUEVO: Seguridad
│   ├── README.md                           # ✨ NUEVO: Security overview
│   ├── phase-1-summary.md                  # ← PHASE_1_SECURITY_SUMMARY.md
│   └── phase-1-test-report.md              # ← PHASE_1_SECURITY_TEST_REPORT.md
│
├── 10-project-status/                      # Estado del proyecto
│   ├── README.md                           # Estado actual consolidado
│   ├── current-state.md                    # ← CURRENT_STATE.md
│   ├── features-completed.md               # ← FEATURES_COMPLETED.md
│   ├── architecture-status.md              # ← project-status/ARCHITECTURE_STATUS.md
│   ├── system-audit.md                     # ← project-status/SYSTEM_AUDIT_2025_11_03.md
│   ├── project-updates.md                  # ← project-status/PROJECT_UPDATES.md
│   ├── phase-1-complete.md                 # ← project-status/PHASE_1_COMPLETE.md
│   ├── precision-readiness.md              # ← project-status/PRECISION_READINESS_100_UPDATED.md
│   ├── masterplan-progress.md              # ← project-status/MASTERPLAN_PROGRESS_E2E_COMPLETE.md
│   ├── masterplan-impl-status.md           # ← guides/MASTERPLAN_PROGRESS_IMPLEMENTATION_STATUS.md
│   ├── roadmap.md                          # ← WORKPLAN.md
│   └── project-memory.md                   # ← PROJECT_MEMORY.md (archivo histórico)
│
├── 11-analysis/                            # Análisis técnicos
│   ├── README.md                           # Índice de análisis
│   ├── codebase-deep-analysis.md           # ← eval/2025-11-10_CODEBASE_DEEP_ANALYSIS.md
│   ├── llm-architecture.md                 # ← guides/LLM_COMPUTATIONAL_ARCHITECTURE.md
│   │
│   └── masterplan/                         # Análisis de Masterplan
│       ├── diagnostic-results.md           # ← masterplan/DIAGNOSTIC_RESULTS.md
│       ├── findings-summary.md             # ← masterplan/FINDINGS_SUMMARY.md
│       ├── implementation-status.md        # ← masterplan/IMPLEMENTATION_STATUS.md
│       ├── implementation-summary.md       # ← masterplan/IMPLEMENTATION_SUMMARY.md
│       └── test-results.md                 # ← masterplan/TEST_RESULTS.md
│
└── 99-archive/                             # Documentos obsoletos
    ├── README.md                           # ← archive/README.md (actualizado)
    │
    ├── obsolete-plans/
    │   ├── chromadb-rag-plan.md            # ← archive/CHROMADB_RAG_IMPLEMENTATION_PLAN.md
    │   ├── local-production-plan.md        # ← archive/LOCAL_PRODUCTION_READY_PLAN.md
    │   ├── logging-completion.md           # ← archive/LOGGING_COMPLETION_PLAN.md
    │   └── logging-improvement.md          # ← archive/LOGGING_IMPROVEMENT_PLAN.md
    │
    ├── future-plans/
    │   ├── ast-atomization.md              # ← archive/devmatrix-ast-atomization.md
    │   ├── ml-continuous-learning.md       # ← archive/devmatrix-ml-continuous-learning (1).md
    │   └── rag-implementation.md           # ← archive/devmatrix-rag-implementation (1).md
    │
    ├── historical-reports/
    │   ├── final-test-report.md            # ← archive/FINAL_TEST_REPORT.md
    │   ├── mvp-completion.md               # ← archive/MVP_COMPLETION_REPORT.md
    │   └── devmatrix-architecture-2025.md  # ← archive/devmatrix-architecture-2025.md
    │
    └── troubleshooting/
        └── troubleshooting-old.md          # ← archive/TROUBLESHOOTING.md
```

---

## 📋 Tabla de Categorización Completa

### Archivos en Raíz (17 archivos) - Mover todos

| Archivo Actual | Categoría | Destino | Acción |
|----------------|-----------|---------|--------|
| `README.md` | Index | `README.md` (actualizar) | **ACTUALIZAR** |
| `CURRENT_STATE.md` | Status | `10-project-status/current-state.md` | **MOVER** |
| `FEATURES_COMPLETED.md` | Status | `10-project-status/features-completed.md` | **MOVER** |
| `PROJECT_MEMORY.md` | Status/Historical | `10-project-status/project-memory.md` | **MOVER** |
| `WORKPLAN.md` | Status/Roadmap | `10-project-status/roadmap.md` | **MOVER** |
| `MASTERPLAN_FLOW_ANALYSIS.md` | Feature | `02-core-features/masterplan/flow-analysis.md` | **MOVER** |
| `MASTERPLAN_FLOW_DIAGRAM.md` | Feature | `02-core-features/masterplan/flow-diagram.md` | **MOVER** |
| `MASTERPLAN_ISSUES_PRIORITIZED.md` | Feature | `02-core-features/masterplan/issues-prioritized.md` | **MOVER** |
| `MGE_V2_IMPLEMENTATION_COMPLETE.md` | MGE V2 | `03-mge-v2/status/implementation-complete.md` | **MOVER** |
| `mge_v2_analysis_and_implementation_plan.md` | MGE V2 | `03-mge-v2/status/analysis-plan.md` | **MOVER** |
| `mge_v2_complete_project_generation_plan.md` | MGE V2/Infra | `03-mge-v2/infrastructure-generation/plan.md` | **MOVER** |
| `mge_v2_final_status_report.md` | MGE V2 | `03-mge-v2/status/final-status.md` | **MOVER** |
| `P0_CRITICAL_FIXES_IMPLEMENTATION.md` | Implementation | `08-implementation-reports/p0-critical-fixes.md` | **MOVER** |
| `PHASE_1_SECURITY_SUMMARY.md` | Security | `09-security/phase-1-summary.md` | **MOVER** |
| `PHASE_1_SECURITY_TEST_REPORT.md` | Security | `09-security/phase-1-test-report.md` | **MOVER** |
| `RAG_METRICS.md` | RAG | `02-core-features/rag-system/metrics.md` | **MOVER** |
| `RAG_OPTIMIZATION.md` | RAG | `02-core-features/rag-system/optimization-summary.md` | **MOVER** |

---

## ✨ Archivos Nuevos a Crear

### Getting Started (6 archivos)
1. `00-getting-started/README.md` - Índice de inicio rápido
2. `00-getting-started/quick-start.md` - Setup en 5 minutos
3. `00-getting-started/installation.md` - Instalación detallada
4. `00-getting-started/first-project.md` - Tutorial primer proyecto
5. `00-getting-started/concepts.md` - Conceptos básicos DDD
6. *(carpeta completa nueva)*

### Architecture (4 archivos)
1. `01-architecture/README.md` - Índice de arquitectura
2. `01-architecture/data-flow.md` - Flujo de datos end-to-end
3. `01-architecture/technology-stack.md` - Stack tecnológico
4. `01-architecture/domain-driven-design.md` - DDD en DevMatrix

### Core Features (3 archivos)
1. `02-core-features/README.md` - Índice de features
2. `02-core-features/discovery/` - (carpeta completa nueva con 3 docs)
3. Varios READMEs de subcarpetas

### Infrastructure Generation (6 archivos) ⭐ PRIORIDAD
1. `03-mge-v2/infrastructure-generation/README.md` - Overview completo
2. `03-mge-v2/infrastructure-generation/architecture.md` - Diseño técnico
3. `03-mge-v2/infrastructure-generation/templates-guide.md` - Guía templates
4. `03-mge-v2/infrastructure-generation/usage-examples.md` - Ejemplos
5. `03-mge-v2/infrastructure-generation/troubleshooting.md` - Troubleshooting
6. *(esta carpeta es CRÍTICA - feature recién implementado)*

### API Reference (3 archivos)
1. `04-api-reference/README.md` - Índice de APIs
2. `04-api-reference/websocket-api/streaming.md` - WebSocket docs
3. `04-api-reference/internal-services/README.md` - Servicios internos

### Security Section (1 archivo)
1. `09-security/README.md` - Security overview

### READMEs adicionales (~15 archivos)
- Cada carpeta debe tener su README.md explicativo
- Total estimado: 35-40 archivos nuevos

---

## 🔄 Mapeo Detallado de Movimientos

### MGE_V2/ (26 archivos) → 03-mge-v2/

```bash
MGE_V2/README.md → 03-mge-v2/README.md
MGE_V2/00_EXECUTIVE_SUMMARY.md → 03-mge-v2/00-executive-summary.md
MGE_V2/01_CONTEXT_MVP_TO_V2.md → 03-mge-v2/01-context.md
MGE_V2/02_WHY_V2_NOT_V1.md → 03-mge-v2/02-why-v2.md
MGE_V2/03_ARCHITECTURE_OVERVIEW.md → 03-mge-v2/03-architecture.md
MGE_V2/ARCHITECTURE_COMPARISON.md → 03-mge-v2/04-comparison.md
MGE_V2/MGE_V2_COMPLETE_TECHNICAL_SPEC.md → 03-mge-v2/05-complete-spec.md

MGE_V2/04_PHASE_0_2_FOUNDATION.md → 03-mge-v2/phases/phase-0-2-foundation.md
MGE_V2/05_PHASE_3_AST_ATOMIZATION.md → 03-mge-v2/phases/phase-3-atomization.md
MGE_V2/06_PHASE_4_DEPENDENCY_GRAPH.md → 03-mge-v2/phases/phase-4-dependency.md
MGE_V2/07_PHASE_5_HIERARCHICAL_VALIDATION.md → 03-mge-v2/phases/phase-5-validation.md
MGE_V2/08_PHASE_6_EXECUTION_RETRY.md → 03-mge-v2/phases/phase-6-execution.md
MGE_V2/09_PHASE_7_HUMAN_REVIEW.md → 03-mge-v2/phases/phase-7-human-review.md

MGE_V2/10_INTEGRATION_DEVMATRIX.md → 03-mge-v2/integration/devmatrix.md
MGE_V2/11_IMPLEMENTATION_ROADMAP.md → 03-mge-v2/implementation/roadmap.md
MGE_V2/12_TESTING_STRATEGY.md → 03-mge-v2/implementation/testing-strategy.md
MGE_V2/TESTING_SUMMARY.md → 03-mge-v2/implementation/testing-summary.md
MGE_V2/13_PERFORMANCE_COST.md → 03-mge-v2/implementation/performance-cost.md
MGE_V2/14_RISKS_MITIGATION.md → 03-mge-v2/implementation/risks-mitigation.md
MGE_V2/caching_guide.md → 03-mge-v2/implementation/caching-guide.md
MGE_V2/MGE_PRECISION_DEEP_DIVE.md → 03-mge-v2/implementation/precision-deep-dive.md
MGE_V2/precision_readiness_checklist.md → 03-mge-v2/implementation/precision-readiness.md
MGE_V2/gap-10-implementation-summary.md → 03-mge-v2/implementation/gap-10-summary.md

MGE_V2/MIGRATION_EXECUTIVE_SUMMARY.md → 03-mge-v2/migration/README.md
MGE_V2/DUAL_MODE_MIGRATION_STRATEGY.md → 03-mge-v2/migration/dual-mode-strategy.md

MGE_V2/implementation_status_report.md → 03-mge-v2/status/implementation-status.md
```

### rag/ (38 archivos) → 02-core-features/rag-system/

```bash
rag/README.md → 02-core-features/rag-system/README.md (merge with 00_ANALYSIS_INDEX)
rag/INDEX.md → 02-core-features/rag-system/INDEX.md
rag/QUICK_REFERENCE.md → 02-core-features/rag-system/quick-reference.md
rag/troubleshooting.md → 02-core-features/rag-system/troubleshooting.md
rag/dashboard.md → 02-core-features/rag-system/dashboard.md
rag/maintenance_log.md → 02-core-features/rag-system/maintenance-log.md

# Phases
rag/PHASE1_*.md → 02-core-features/rag-system/phases/phase-1-gpu.md (consolidate 3 files)
rag/PHASE2_*.md → 02-core-features/rag-system/phases/phase-2-completion.md (consolidate 2 files)
rag/PHASE3_*.md → 02-core-features/rag-system/phases/phase-3-query-expansion.md (consolidate 2 files)
rag/PHASE4_*.md → 02-core-features/rag-system/phases/phase-4-final.md (consolidate 6 files)

# Analysis
rag/ANALISIS_RAG_PROFUNDO.md → 02-core-features/rag-system/analysis/deep-analysis.md
rag/RAG_QUALITY_ANALYSIS_REPORT.md → 02-core-features/rag-system/analysis/quality-analysis.md
rag/ANALISIS_CODIGO_QUALITY_RAG.md → 02-core-features/rag-system/analysis/code-quality.md
rag/ANALISIS_RAG_DELIVERABLES.md → 02-core-features/rag-system/analysis/deliverables.md
rag/RAG_DATA_GAPS_SUMMARY.md → 02-core-features/rag-system/analysis/data-gaps.md
rag/RAG_IMPLEMENTATION_ANALYSIS.md → 02-core-features/rag-system/analysis/implementation.md
rag/IMPLEMENTACION_FIXES_RAG.md → 02-core-features/rag-system/analysis/fixes.md
rag/RAG_CODE_QUALITY_IMPROVED.md → 02-core-features/rag-system/analysis/code-improvements.md
rag/improvement_report.md → 02-core-features/rag-system/analysis/improvement-report.md

# Consolidar archivos de embedding
rag/embedding_model.md + embedding_model_research.md + embedding_benchmark.md
  → 02-core-features/rag-system/embedding-models.md (merge de 3 archivos)

# Otros
rag/adding_examples.md → 02-core-features/rag-system/adding-examples.md
rag/RESUMEN_RAG.md → 02-core-features/rag-system/summary.md
rag/RESUMEN_FASE_ANALISIS_RAG_COMPLETA.md → 02-core-features/rag-system/analysis-phase-summary.md
rag/RAG_DATA_INGESTION_PLAN.md → 02-core-features/rag-system/data-ingestion-plan.md
```

### test-suite-enhancement/ (13 archivos) → 07-testing/

```bash
test-suite-enhancement/README_TEST_SUITE.md → 07-testing/README.md
test-suite-enhancement/PROJECT_COMPLETE_SUMMARY.md → 07-testing/overview/project-summary.md
test-suite-enhancement/BRANCH_COMPLETE_SUMMARY.md → 07-testing/overview/branch-summary.md
test-suite-enhancement/COVERAGE_AUDIT_BASELINE.md → 07-testing/overview/coverage-audit.md

test-suite-enhancement/PHASE_2_COMPLETION_REPORT.md → 07-testing/reports/phase-2-completion.md
test-suite-enhancement/PHASE_6_FINAL_REPORT.md → 07-testing/reports/phase-6-final.md
test-suite-enhancement/FINAL_IMPLEMENTATION_REPORT.md → 07-testing/reports/final-implementation.md
test-suite-enhancement/COMPREHENSIVE_TEST_RESULTS.md → 07-testing/reports/comprehensive-results.md
test-suite-enhancement/TEST_EXECUTION_REPORT.md → 07-testing/reports/test-execution.md
test-suite-enhancement/TEST_RESULTS.md → 07-testing/reports/test-results.md
test-suite-enhancement/E2E_TEST_RESULTS.md → 07-testing/reports/e2e-results.md

test-suite-enhancement/CONSTITUTION_COMPLIANCE_REPORT.md → 07-testing/compliance/constitution-compliance.md
test-suite-enhancement/TEST_SUITE_PROGRESS.md → 07-testing/progress/test-suite-progress.md

# Archivos .txt (no markdown) - IGNORAR o ARCHIVAR
test-suite-enhancement/FINAL_SUMMARY.txt → 99-archive/ (optional)
test-suite-enhancement/MISSION_ACCOMPLISHED.txt → 99-archive/ (optional)
test-suite-enhancement/ORGANIZATION_COMPLETE.txt → 99-archive/ (optional)
```

### guides/ (8 archivos) → 02-core-features/ y 11-analysis/

```bash
guides/AUTHENTICATION_SYSTEM.md → 02-core-features/authentication/README.md
guides/MULTI_TENANCY.md → 02-core-features/multi-tenancy/README.md
guides/WEB_UI.md → 02-core-features/web-ui/README.md
guides/FRONTEND_ROADMAP.md → 02-core-features/web-ui/frontend-roadmap.md

guides/MASTERPLAN_DESIGN.md → 02-core-features/masterplan/README.md
guides/MASTERPLAN_PROGRESS_IMPLEMENTATION_STATUS.md → 10-project-status/masterplan-impl-status.md
guides/MASTERPLAN_PROGRESS_UI_DESIGN.md → 02-core-features/masterplan/progress-ui.md

guides/LLM_COMPUTATIONAL_ARCHITECTURE.md → 11-analysis/llm-architecture.md
guides/TROUBLESHOOTING.md → 05-guides/development/troubleshooting.md
```

### guides-tutorials/ (5 archivos) → 05-guides/ y 06-tutorials/

```bash
guides-tutorials/GUIA_DE_USO.md → 05-guides/development/README.md
guides-tutorials/DEVELOPMENT_CHECKLIST.md → 05-guides/development/checklist.md
guides-tutorials/DEPLOYMENT.md → 05-guides/deployment/README.md
guides-tutorials/MONITORING_QUICKSTART.md → 05-guides/monitoring/quickstart.md
guides-tutorials/DEMO_FINAL.md → 06-tutorials/demo-final.md
```

### reference/ (4 archivos) → 01-architecture/, 04-api-reference/, 05-guides/

```bash
reference/ARCHITECTURE.md → 01-architecture/system-design.md
reference/API_REFERENCE.md → 04-api-reference/README.md
reference/LOCAL_OPERATIONS_RUNBOOK.md → 05-guides/development/local-operations.md
reference/MONITORING_GUIDE.md → 05-guides/monitoring/README.md
```

### project-status/ (6 archivos) → 10-project-status/

```bash
project-status/ARCHITECTURE_STATUS.md → 10-project-status/architecture-status.md
project-status/SYSTEM_AUDIT_2025_11_03.md → 10-project-status/system-audit.md
project-status/PROJECT_UPDATES.md → 10-project-status/project-updates.md
project-status/PHASE_1_COMPLETE.md → 10-project-status/phase-1-complete.md
project-status/PRECISION_READINESS_100_UPDATED.md → 10-project-status/precision-readiness.md
project-status/MASTERPLAN_PROGRESS_E2E_COMPLETE.md → 10-project-status/masterplan-progress.md
```

### masterplan/ (9 archivos) → 11-analysis/masterplan/

```bash
masterplan/DIAGNOSTIC_RESULTS.md → 11-analysis/masterplan/diagnostic-results.md
masterplan/FINDINGS_SUMMARY.md → 11-analysis/masterplan/findings-summary.md
masterplan/IMPLEMENTATION_STATUS.md → 11-analysis/masterplan/implementation-status.md
masterplan/IMPLEMENTATION_SUMMARY.md → 11-analysis/masterplan/implementation-summary.md
masterplan/TEST_RESULTS.md → 11-analysis/masterplan/test-results.md
masterplan/INTELLIGENT_TASK_CALCULATION.md → 02-core-features/masterplan/intelligent-calculation.md
masterplan/FRONTEND_INTEGRATION_*.md → 02-core-features/masterplan/frontend-integration.md (consolidate 3)
masterplan/MASTERPLAN_FLOW_ANALYSIS.md → 02-core-features/masterplan/flow-analysis.md
```

### integration/ (3 archivos) → 03-mge-v2/integration/

```bash
integration/MGE_V2_INTEGRATION_GUIDE.md → 03-mge-v2/integration/README.md
integration/MGE_V2_INTEGRATION_STATUS.md → 03-mge-v2/integration/status.md
integration/MGE_V2_INTEGRATION_COMPLETE.md → 03-mge-v2/integration/complete.md
```

### implementation-reports/ (3 archivos) → 08-implementation-reports/

```bash
implementation-reports/IMPLEMENTATION_SUMMARY.md → 08-implementation-reports/summary.md
implementation-reports/RAG_PHASE2_IMPLEMENTATION.md → 08-implementation-reports/rag-phase2.md
implementation-reports/RAG_POPULATION_REPORT.md → 08-implementation-reports/rag-population.md
```

### eval/ (2 archivos) → 03-mge-v2/status/ y 11-analysis/

```bash
eval/MGE_V1_VS_V2_COMPARISON.md → 03-mge-v2/status/comparison.md
eval/2025-11-10_CODEBASE_DEEP_ANALYSIS.md → 11-analysis/codebase-deep-analysis.md
```

### analysis/ (1 archivo) → 01-architecture/

```bash
analysis/ANALYSIS.md → 01-architecture/overview.md (merge con ARCHITECTURE_STATUS)
```

### api/ (1 archivo) → 04-api-reference/

```bash
api/validation-api.md → 04-api-reference/rest-api/validation-api.md
```

### graph-improvements/ (1 archivo) → 02-core-features/

```bash
graph-improvements/ROADMAP.md → 02-core-features/graph-system/roadmap.md
```

### archive/ (11 archivos) → 99-archive/ (reorganizar)

```bash
archive/CHROMADB_RAG_IMPLEMENTATION_PLAN.md → 99-archive/obsolete-plans/chromadb-rag-plan.md
archive/LOCAL_PRODUCTION_READY_PLAN.md → 99-archive/obsolete-plans/local-production-plan.md
archive/LOGGING_COMPLETION_PLAN.md → 99-archive/obsolete-plans/logging-completion.md
archive/LOGGING_IMPROVEMENT_PLAN.md → 99-archive/obsolete-plans/logging-improvement.md

archive/devmatrix-ast-atomization.md → 99-archive/future-plans/ast-atomization.md
archive/devmatrix-ml-continuous-learning (1).md → 99-archive/future-plans/ml-continuous-learning.md
archive/devmatrix-rag-implementation (1).md → 99-archive/future-plans/rag-implementation.md

archive/FINAL_TEST_REPORT.md → 99-archive/historical-reports/final-test-report.md
archive/MVP_COMPLETION_REPORT.md → 99-archive/historical-reports/mvp-completion.md
archive/devmatrix-architecture-2025.md → 99-archive/historical-reports/devmatrix-architecture-2025.md

archive/TROUBLESHOOTING.md → 99-archive/troubleshooting/troubleshooting-old.md
archive/README.md → 99-archive/README.md (actualizar)
```

---

## 📝 Archivos a Consolidar (Merge)

### 1. RAG Embedding Models (3 → 1)
**Archivos origen:**
- `rag/embedding_model.md`
- `rag/embedding_model_research.md`
- `rag/embedding_benchmark.md`

**Destino:** `02-core-features/rag-system/embedding-models.md`

**Estrategia:**
1. Crear documento único con secciones:
   - Overview (de embedding_model.md)
   - Research & Selection (de embedding_model_research.md)
   - Benchmarks (de embedding_benchmark.md)
2. Eliminar duplicación de información
3. Mantener tablas de comparación

### 2. RAG Phase 1 (3 → 1)
**Archivos origen:**
- `rag/PHASE1_EXECUTION_REPORT.md`
- `rag/PHASE1_GPU_OPTIMIZATION_COMPLETE.md`
- `rag/PHASE1_OPENAI_RESULTS.md`

**Destino:** `02-core-features/rag-system/phases/phase-1-gpu.md`

**Estrategia:**
1. Cronología de implementación
2. Resultados consolidados
3. Lecciones aprendidas

### 3. RAG Phase 2 (2 → 1)
**Archivos origen:**
- `rag/PHASE2_COMPLETION.md`
- `rag/PHASE2_ROADMAP.md`

**Destino:** `02-core-features/rag-system/phases/phase-2-completion.md`

### 4. RAG Phase 3 (2 → 1)
**Archivos origen:**
- `rag/PHASE3_QUERY_EXPANSION_RESULTS.md`
- `rag/PHASE3_ROADMAP.md`

**Destino:** `02-core-features/rag-system/phases/phase-3-query-expansion.md`

### 5. RAG Phase 4 (6 → 1)
**Archivos origen:**
- `rag/PHASE4_FINAL_REPORT.md`
- `rag/PHASE4_CROSS_ENCODER_RESULTS.md`
- `rag/PHASE4_HYBRID_DISCOVERY.md`
- `rag/PHASE4_MODEL_EXPERIMENT.md`
- `rag/PHASE4_PROGRESS_REPORT.md`
- `rag/PHASE4_STRATEGIC_OPTIONS.md`
- `rag/PHASE4_STRATEGY.md`

**Destino:** `02-core-features/rag-system/phases/phase-4-final.md`

**Estrategia:**
1. PHASE4_FINAL_REPORT.md como base
2. Integrar resultados de experimentos
3. Consolidar strategy y options
4. Mantener solo información relevante

### 6. Masterplan Frontend Integration (3 → 1)
**Archivos origen:**
- `masterplan/FRONTEND_INTEGRATION_ANALYSIS.md`
- `masterplan/FRONTEND_INTEGRATION_SPEC.md`
- `masterplan/FRONTEND_INTEGRATION_TASKS.md`

**Destino:** `02-core-features/masterplan/frontend-integration.md`

### 7. Architecture Overview (2 → 1)
**Archivos origen:**
- `analysis/ANALYSIS.md` (DevMatrix flow analysis)
- `project-status/ARCHITECTURE_STATUS.md` (current architecture)

**Destino:** `01-architecture/overview.md`

**Estrategia:**
1. Combinar arquitectura actual con análisis de flujo
2. Diagrams unificados
3. Estado actual + diseño

### 8. RAG Analysis Index (2 → 1)
**Archivos origen:**
- `rag/README.md`
- `rag/00_ANALYSIS_INDEX.md`

**Destino:** `02-core-features/rag-system/README.md`

---

## 🗑️ Archivos a Archivar

### Criterio de Archivo:
1. Documentos completamente obsoletos
2. Plans superseded por implementación
3. Reportes históricos sin valor de referencia
4. Duplicados completos

### Archivos ya en Archive/ - Mantener donde están:
- Todos los 11 archivos en `archive/` ya están correctamente archivados
- Solo reorganizar en subcarpetas dentro de `99-archive/`

### Candidatos Adicionales para Archivo:
1. **test-suite-enhancement/*.txt** (3 archivos ASCII art)
   - `FINAL_SUMMARY.txt`
   - `MISSION_ACCOMPLISHED.txt`
   - `ORGANIZATION_COMPLETE.txt`
   - **Razón:** No son markdown, son decorativos
   - **Destino:** `99-archive/historical-reports/test-suite-celebration/`

2. **rag/RESUMEN_*.md** (archivos en español con información duplicada)
   - `rag/RESUMEN_RAG.md` - info duplicada en otros docs
   - `rag/RESUMEN_FASE_ANALISIS_RAG_COMPLETA.md` - superseded por phase reports
   - **Razón:** Resúmenes early-stage ahora obsoletos
   - **Acción:** Consolidar información útil en README principal, archivar

3. **PROJECT_MEMORY.md** - archivo histórico de desarrollo
   - **Razón:** Log histórico de decisiones, útil para referencia pero no activo
   - **Destino:** `10-project-status/project-memory.md` (mantener pero marcar como histórico)

---

## 🔨 Bash Script de Ejecución

```bash
#!/bin/bash
# DOCS Reorganization Script
# Date: 2025-11-10
# Purpose: Complete reorganization of DOCS/ directory
# Author: Dany (SuperClaude)

set -e  # Exit on error
set -u  # Exit on undefined variable

DOCS_DIR="/home/kwar/code/agentic-ai/DOCS"
BACKUP_DIR="/home/kwar/code/agentic-ai/DOCS_BACKUP_$(date +%Y%m%d_%H%M%S)"

echo "🚀 Starting DOCS reorganization..."
echo "📦 Backup directory: $BACKUP_DIR"

# ========================================
# STEP 1: Create backup
# ========================================
echo ""
echo "📦 STEP 1/7: Creating backup..."
cp -r "$DOCS_DIR" "$BACKUP_DIR"
echo "✅ Backup created at: $BACKUP_DIR"

# ========================================
# STEP 2: Create new directory structure
# ========================================
echo ""
echo "📁 STEP 2/7: Creating new directory structure..."

cd "$DOCS_DIR"

# Main directories
mkdir -p 00-getting-started
mkdir -p 01-architecture
mkdir -p 02-core-features/{authentication,discovery,masterplan,rag-system,multi-tenancy,web-ui,graph-system}
mkdir -p 02-core-features/rag-system/{phases,analysis}
mkdir -p 03-mge-v2/{phases,infrastructure-generation,implementation,integration,migration,status}
mkdir -p 04-api-reference/{rest-api,websocket-api,internal-services}
mkdir -p 05-guides/{development,deployment,monitoring}
mkdir -p 06-tutorials
mkdir -p 07-testing/{overview,reports,compliance,progress}
mkdir -p 08-implementation-reports
mkdir -p 09-security
mkdir -p 10-project-status
mkdir -p 11-analysis/masterplan
mkdir -p 99-archive/{obsolete-plans,future-plans,historical-reports,troubleshooting}

echo "✅ Directory structure created"

# ========================================
# STEP 3: Move root files
# ========================================
echo ""
echo "📄 STEP 3/7: Moving root files..."

# Status & Planning
mv CURRENT_STATE.md 10-project-status/current-state.md 2>/dev/null || true
mv FEATURES_COMPLETED.md 10-project-status/features-completed.md 2>/dev/null || true
mv PROJECT_MEMORY.md 10-project-status/project-memory.md 2>/dev/null || true
mv WORKPLAN.md 10-project-status/roadmap.md 2>/dev/null || true

# Masterplan
mv MASTERPLAN_FLOW_ANALYSIS.md 02-core-features/masterplan/flow-analysis.md 2>/dev/null || true
mv MASTERPLAN_FLOW_DIAGRAM.md 02-core-features/masterplan/flow-diagram.md 2>/dev/null || true
mv MASTERPLAN_ISSUES_PRIORITIZED.md 02-core-features/masterplan/issues-prioritized.md 2>/dev/null || true

# MGE V2
mv MGE_V2_IMPLEMENTATION_COMPLETE.md 03-mge-v2/status/implementation-complete.md 2>/dev/null || true
mv mge_v2_analysis_and_implementation_plan.md 03-mge-v2/status/analysis-plan.md 2>/dev/null || true
mv mge_v2_complete_project_generation_plan.md 03-mge-v2/infrastructure-generation/plan.md 2>/dev/null || true
mv mge_v2_final_status_report.md 03-mge-v2/status/final-status.md 2>/dev/null || true

# Implementation & Security
mv P0_CRITICAL_FIXES_IMPLEMENTATION.md 08-implementation-reports/p0-critical-fixes.md 2>/dev/null || true
mv PHASE_1_SECURITY_SUMMARY.md 09-security/phase-1-summary.md 2>/dev/null || true
mv PHASE_1_SECURITY_TEST_REPORT.md 09-security/phase-1-test-report.md 2>/dev/null || true

# RAG
mv RAG_METRICS.md 02-core-features/rag-system/metrics.md 2>/dev/null || true
mv RAG_OPTIMIZATION.md 02-core-features/rag-system/optimization-summary.md 2>/dev/null || true

echo "✅ Root files moved"

# ========================================
# STEP 4: Move MGE_V2/ contents
# ========================================
echo ""
echo "📁 STEP 4/7: Moving MGE_V2/ contents..."

# Core docs
mv MGE_V2/README.md 03-mge-v2/README.md 2>/dev/null || true
mv MGE_V2/00_EXECUTIVE_SUMMARY.md 03-mge-v2/00-executive-summary.md 2>/dev/null || true
mv MGE_V2/01_CONTEXT_MVP_TO_V2.md 03-mge-v2/01-context.md 2>/dev/null || true
mv MGE_V2/02_WHY_V2_NOT_V1.md 03-mge-v2/02-why-v2.md 2>/dev/null || true
mv MGE_V2/03_ARCHITECTURE_OVERVIEW.md 03-mge-v2/03-architecture.md 2>/dev/null || true
mv MGE_V2/ARCHITECTURE_COMPARISON.md 03-mge-v2/04-comparison.md 2>/dev/null || true
mv MGE_V2/MGE_V2_COMPLETE_TECHNICAL_SPEC.md 03-mge-v2/05-complete-spec.md 2>/dev/null || true

# Phases
mv MGE_V2/04_PHASE_0_2_FOUNDATION.md 03-mge-v2/phases/phase-0-2-foundation.md 2>/dev/null || true
mv MGE_V2/05_PHASE_3_AST_ATOMIZATION.md 03-mge-v2/phases/phase-3-atomization.md 2>/dev/null || true
mv MGE_V2/06_PHASE_4_DEPENDENCY_GRAPH.md 03-mge-v2/phases/phase-4-dependency.md 2>/dev/null || true
mv MGE_V2/07_PHASE_5_HIERARCHICAL_VALIDATION.md 03-mge-v2/phases/phase-5-validation.md 2>/dev/null || true
mv MGE_V2/08_PHASE_6_EXECUTION_RETRY.md 03-mge-v2/phases/phase-6-execution.md 2>/dev/null || true
mv MGE_V2/09_PHASE_7_HUMAN_REVIEW.md 03-mge-v2/phases/phase-7-human-review.md 2>/dev/null || true

# Implementation
mv MGE_V2/10_INTEGRATION_DEVMATRIX.md 03-mge-v2/integration/devmatrix.md 2>/dev/null || true
mv MGE_V2/11_IMPLEMENTATION_ROADMAP.md 03-mge-v2/implementation/roadmap.md 2>/dev/null || true
mv MGE_V2/12_TESTING_STRATEGY.md 03-mge-v2/implementation/testing-strategy.md 2>/dev/null || true
mv MGE_V2/TESTING_SUMMARY.md 03-mge-v2/implementation/testing-summary.md 2>/dev/null || true
mv MGE_V2/13_PERFORMANCE_COST.md 03-mge-v2/implementation/performance-cost.md 2>/dev/null || true
mv MGE_V2/14_RISKS_MITIGATION.md 03-mge-v2/implementation/risks-mitigation.md 2>/dev/null || true
mv MGE_V2/caching_guide.md 03-mge-v2/implementation/caching-guide.md 2>/dev/null || true
mv MGE_V2/MGE_PRECISION_DEEP_DIVE.md 03-mge-v2/implementation/precision-deep-dive.md 2>/dev/null || true
mv MGE_V2/precision_readiness_checklist.md 03-mge-v2/implementation/precision-readiness.md 2>/dev/null || true
mv MGE_V2/gap-10-implementation-summary.md 03-mge-v2/implementation/gap-10-summary.md 2>/dev/null || true

# Migration
mv MGE_V2/MIGRATION_EXECUTIVE_SUMMARY.md 03-mge-v2/migration/README.md 2>/dev/null || true
mv MGE_V2/DUAL_MODE_MIGRATION_STRATEGY.md 03-mge-v2/migration/dual-mode-strategy.md 2>/dev/null || true

# Status
mv MGE_V2/implementation_status_report.md 03-mge-v2/status/implementation-status.md 2>/dev/null || true

# Remove empty directory
rmdir MGE_V2 2>/dev/null || true

echo "✅ MGE_V2/ contents moved"

# ========================================
# STEP 5: Move rag/ contents
# ========================================
echo ""
echo "📁 STEP 5/7: Moving rag/ contents..."

# Main files
mv rag/README.md 02-core-features/rag-system/README.md 2>/dev/null || true
mv rag/INDEX.md 02-core-features/rag-system/INDEX.md 2>/dev/null || true
mv rag/QUICK_REFERENCE.md 02-core-features/rag-system/quick-reference.md 2>/dev/null || true
mv rag/troubleshooting.md 02-core-features/rag-system/troubleshooting.md 2>/dev/null || true
mv rag/dashboard.md 02-core-features/rag-system/dashboard.md 2>/dev/null || true
mv rag/maintenance_log.md 02-core-features/rag-system/maintenance-log.md 2>/dev/null || true
mv rag/adding_examples.md 02-core-features/rag-system/adding-examples.md 2>/dev/null || true

# Phase reports (Note: Manual consolidation needed later)
mv rag/PHASE1_EXECUTION_REPORT.md 02-core-features/rag-system/phases/phase-1-execution.md 2>/dev/null || true
mv rag/PHASE1_GPU_OPTIMIZATION_COMPLETE.md 02-core-features/rag-system/phases/phase-1-gpu.md 2>/dev/null || true
mv rag/PHASE1_OPENAI_RESULTS.md 02-core-features/rag-system/phases/phase-1-openai.md 2>/dev/null || true
mv rag/PHASE2_COMPLETION.md 02-core-features/rag-system/phases/phase-2-completion.md 2>/dev/null || true
mv rag/PHASE2_ROADMAP.md 02-core-features/rag-system/phases/phase-2-roadmap.md 2>/dev/null || true
mv rag/PHASE3_QUERY_EXPANSION_RESULTS.md 02-core-features/rag-system/phases/phase-3-query-expansion.md 2>/dev/null || true
mv rag/PHASE3_ROADMAP.md 02-core-features/rag-system/phases/phase-3-roadmap.md 2>/dev/null || true
mv rag/PHASE4_FINAL_REPORT.md 02-core-features/rag-system/phases/phase-4-final.md 2>/dev/null || true
mv rag/PHASE4_*.md 02-core-features/rag-system/phases/ 2>/dev/null || true

# Analysis
mv rag/ANALISIS_RAG_PROFUNDO.md 02-core-features/rag-system/analysis/deep-analysis.md 2>/dev/null || true
mv rag/RAG_QUALITY_ANALYSIS_REPORT.md 02-core-features/rag-system/analysis/quality-analysis.md 2>/dev/null || true
mv rag/ANALISIS_CODIGO_QUALITY_RAG.md 02-core-features/rag-system/analysis/code-quality.md 2>/dev/null || true
mv rag/ANALISIS_RAG_DELIVERABLES.md 02-core-features/rag-system/analysis/deliverables.md 2>/dev/null || true
mv rag/RAG_DATA_GAPS_SUMMARY.md 02-core-features/rag-system/analysis/data-gaps.md 2>/dev/null || true
mv rag/RAG_IMPLEMENTATION_ANALYSIS.md 02-core-features/rag-system/analysis/implementation.md 2>/dev/null || true
mv rag/IMPLEMENTACION_FIXES_RAG.md 02-core-features/rag-system/analysis/fixes.md 2>/dev/null || true
mv rag/RAG_CODE_QUALITY_IMPROVED.md 02-core-features/rag-system/analysis/code-improvements.md 2>/dev/null || true
mv rag/improvement_report.md 02-core-features/rag-system/analysis/improvement-report.md 2>/dev/null || true

# Embedding (Note: Manual consolidation needed)
mv rag/embedding_model.md 02-core-features/rag-system/embedding-model.md 2>/dev/null || true
mv rag/embedding_model_research.md 02-core-features/rag-system/embedding-research.md 2>/dev/null || true
mv rag/embedding_benchmark.md 02-core-features/rag-system/embedding-benchmark.md 2>/dev/null || true

# Others
mv rag/RAG_OPTIMIZATION_FINAL_SUMMARY.md 02-core-features/rag-system/optimization-final.md 2>/dev/null || true
mv rag/RESUMEN_RAG.md 02-core-features/rag-system/summary-es.md 2>/dev/null || true
mv rag/RESUMEN_FASE_ANALISIS_RAG_COMPLETA.md 02-core-features/rag-system/analysis-phase-summary.md 2>/dev/null || true
mv rag/RAG_DATA_INGESTION_PLAN.md 02-core-features/rag-system/data-ingestion-plan.md 2>/dev/null || true
mv rag/00_ANALYSIS_INDEX.md 02-core-features/rag-system/analysis-index.md 2>/dev/null || true

# Remove empty directory
rmdir rag 2>/dev/null || true

echo "✅ rag/ contents moved"

# ========================================
# STEP 6: Move remaining directories
# ========================================
echo ""
echo "📁 STEP 6/7: Moving remaining directories..."

# test-suite-enhancement
mv test-suite-enhancement/README_TEST_SUITE.md 07-testing/README.md 2>/dev/null || true
mv test-suite-enhancement/PROJECT_COMPLETE_SUMMARY.md 07-testing/overview/project-summary.md 2>/dev/null || true
mv test-suite-enhancement/BRANCH_COMPLETE_SUMMARY.md 07-testing/overview/branch-summary.md 2>/dev/null || true
mv test-suite-enhancement/COVERAGE_AUDIT_BASELINE.md 07-testing/overview/coverage-audit.md 2>/dev/null || true
mv test-suite-enhancement/PHASE_2_COMPLETION_REPORT.md 07-testing/reports/phase-2-completion.md 2>/dev/null || true
mv test-suite-enhancement/PHASE_6_FINAL_REPORT.md 07-testing/reports/phase-6-final.md 2>/dev/null || true
mv test-suite-enhancement/FINAL_IMPLEMENTATION_REPORT.md 07-testing/reports/final-implementation.md 2>/dev/null || true
mv test-suite-enhancement/COMPREHENSIVE_TEST_RESULTS.md 07-testing/reports/comprehensive-results.md 2>/dev/null || true
mv test-suite-enhancement/TEST_EXECUTION_REPORT.md 07-testing/reports/test-execution.md 2>/dev/null || true
mv test-suite-enhancement/TEST_RESULTS.md 07-testing/reports/test-results.md 2>/dev/null || true
mv test-suite-enhancement/E2E_TEST_RESULTS.md 07-testing/reports/e2e-results.md 2>/dev/null || true
mv test-suite-enhancement/CONSTITUTION_COMPLIANCE_REPORT.md 07-testing/compliance/constitution-compliance.md 2>/dev/null || true
mv test-suite-enhancement/TEST_SUITE_PROGRESS.md 07-testing/progress/test-suite-progress.md 2>/dev/null || true
mv test-suite-enhancement/*.txt 99-archive/historical-reports/ 2>/dev/null || true
rmdir test-suite-enhancement 2>/dev/null || true

# guides
mv guides/AUTHENTICATION_SYSTEM.md 02-core-features/authentication/README.md 2>/dev/null || true
mv guides/MULTI_TENANCY.md 02-core-features/multi-tenancy/README.md 2>/dev/null || true
mv guides/WEB_UI.md 02-core-features/web-ui/README.md 2>/dev/null || true
mv guides/FRONTEND_ROADMAP.md 02-core-features/web-ui/frontend-roadmap.md 2>/dev/null || true
mv guides/MASTERPLAN_DESIGN.md 02-core-features/masterplan/README.md 2>/dev/null || true
mv guides/MASTERPLAN_PROGRESS_IMPLEMENTATION_STATUS.md 10-project-status/masterplan-impl-status.md 2>/dev/null || true
mv guides/MASTERPLAN_PROGRESS_UI_DESIGN.md 02-core-features/masterplan/progress-ui.md 2>/dev/null || true
mv guides/LLM_COMPUTATIONAL_ARCHITECTURE.md 11-analysis/llm-architecture.md 2>/dev/null || true
mv guides/TROUBLESHOOTING.md 05-guides/development/troubleshooting.md 2>/dev/null || true
rmdir guides 2>/dev/null || true

# guides-tutorials
mv guides-tutorials/GUIA_DE_USO.md 05-guides/development/README.md 2>/dev/null || true
mv guides-tutorials/DEVELOPMENT_CHECKLIST.md 05-guides/development/checklist.md 2>/dev/null || true
mv guides-tutorials/DEPLOYMENT.md 05-guides/deployment/README.md 2>/dev/null || true
mv guides-tutorials/MONITORING_QUICKSTART.md 05-guides/monitoring/quickstart.md 2>/dev/null || true
mv guides-tutorials/DEMO_FINAL.md 06-tutorials/demo-final.md 2>/dev/null || true
rmdir guides-tutorials 2>/dev/null || true

# reference
mv reference/ARCHITECTURE.md 01-architecture/system-design.md 2>/dev/null || true
mv reference/API_REFERENCE.md 04-api-reference/README.md 2>/dev/null || true
mv reference/LOCAL_OPERATIONS_RUNBOOK.md 05-guides/development/local-operations.md 2>/dev/null || true
mv reference/MONITORING_GUIDE.md 05-guides/monitoring/README.md 2>/dev/null || true
rmdir reference 2>/dev/null || true

# project-status
mv project-status/*.md 10-project-status/ 2>/dev/null || true
rmdir project-status 2>/dev/null || true

# masterplan
mv masterplan/DIAGNOSTIC_RESULTS.md 11-analysis/masterplan/diagnostic-results.md 2>/dev/null || true
mv masterplan/FINDINGS_SUMMARY.md 11-analysis/masterplan/findings-summary.md 2>/dev/null || true
mv masterplan/IMPLEMENTATION_STATUS.md 11-analysis/masterplan/implementation-status.md 2>/dev/null || true
mv masterplan/IMPLEMENTATION_SUMMARY.md 11-analysis/masterplan/implementation-summary.md 2>/dev/null || true
mv masterplan/TEST_RESULTS.md 11-analysis/masterplan/test-results.md 2>/dev/null || true
mv masterplan/INTELLIGENT_TASK_CALCULATION.md 02-core-features/masterplan/intelligent-calculation.md 2>/dev/null || true
mv masterplan/FRONTEND_INTEGRATION_*.md 02-core-features/masterplan/ 2>/dev/null || true
mv masterplan/MASTERPLAN_FLOW_ANALYSIS.md 02-core-features/masterplan/flow-analysis-alt.md 2>/dev/null || true
rmdir masterplan 2>/dev/null || true

# integration
mv integration/*.md 03-mge-v2/integration/ 2>/dev/null || true
rmdir integration 2>/dev/null || true

# implementation-reports
mv implementation-reports/IMPLEMENTATION_SUMMARY.md 08-implementation-reports/summary.md 2>/dev/null || true
mv implementation-reports/RAG_PHASE2_IMPLEMENTATION.md 08-implementation-reports/rag-phase2.md 2>/dev/null || true
mv implementation-reports/RAG_POPULATION_REPORT.md 08-implementation-reports/rag-population.md 2>/dev/null || true
rmdir implementation-reports 2>/dev/null || true

# eval
mv eval/MGE_V1_VS_V2_COMPARISON.md 03-mge-v2/status/comparison.md 2>/dev/null || true
mv eval/2025-11-10_CODEBASE_DEEP_ANALYSIS.md 11-analysis/codebase-deep-analysis.md 2>/dev/null || true
rmdir eval 2>/dev/null || true

# analysis
mv analysis/ANALYSIS.md 01-architecture/overview.md 2>/dev/null || true
rmdir analysis 2>/dev/null || true

# api
mv api/validation-api.md 04-api-reference/rest-api/validation-api.md 2>/dev/null || true
rmdir api 2>/dev/null || true

# graph-improvements
mv graph-improvements/ROADMAP.md 02-core-features/graph-system/roadmap.md 2>/dev/null || true
rmdir graph-improvements 2>/dev/null || true

# archive - reorganize
mv archive/CHROMADB_RAG_IMPLEMENTATION_PLAN.md 99-archive/obsolete-plans/chromadb-rag-plan.md 2>/dev/null || true
mv archive/LOCAL_PRODUCTION_READY_PLAN.md 99-archive/obsolete-plans/local-production-plan.md 2>/dev/null || true
mv archive/LOGGING_COMPLETION_PLAN.md 99-archive/obsolete-plans/logging-completion.md 2>/dev/null || true
mv archive/LOGGING_IMPROVEMENT_PLAN.md 99-archive/obsolete-plans/logging-improvement.md 2>/dev/null || true
mv archive/devmatrix-ast-atomization.md 99-archive/future-plans/ast-atomization.md 2>/dev/null || true
mv archive/devmatrix-ml-continuous-learning*.md 99-archive/future-plans/ml-continuous-learning.md 2>/dev/null || true
mv archive/devmatrix-rag-implementation*.md 99-archive/future-plans/rag-implementation.md 2>/dev/null || true
mv archive/FINAL_TEST_REPORT.md 99-archive/historical-reports/final-test-report.md 2>/dev/null || true
mv archive/MVP_COMPLETION_REPORT.md 99-archive/historical-reports/mvp-completion.md 2>/dev/null || true
mv archive/devmatrix-architecture-2025.md 99-archive/historical-reports/devmatrix-architecture-2025.md 2>/dev/null || true
mv archive/TROUBLESHOOTING.md 99-archive/troubleshooting/troubleshooting-old.md 2>/dev/null || true
mv archive/README.md 99-archive/README.md 2>/dev/null || true
rmdir archive 2>/dev/null || true

echo "✅ Remaining directories moved"

# ========================================
# STEP 7: Summary and next steps
# ========================================
echo ""
echo "=========================================="
echo "✅ STEP 7/7: Reorganization Complete!"
echo "=========================================="
echo ""
echo "📊 Summary:"
echo "  - ✅ Backup created: $BACKUP_DIR"
echo "  - ✅ New structure created with numbered directories"
echo "  - ✅ All files moved to appropriate locations"
echo "  - ✅ Old directories removed"
echo ""
echo "⚠️  Manual Tasks Remaining:"
echo "  1. Create new README.md files (see checklist below)"
echo "  2. Consolidate duplicate files (embedding models, phases, etc.)"
echo "  3. Write Infrastructure Generation docs (6 new files)"
echo "  4. Update cross-references and links"
echo "  5. Review and update main README.md"
echo ""
echo "📝 Files to Create (Priority Order):"
echo "  🔴 HIGH PRIORITY:"
echo "     - 03-mge-v2/infrastructure-generation/*.md (6 files)"
echo "     - 00-getting-started/*.md (6 files)"
echo "     - README.md (main index - update)"
echo ""
echo "  🟡 MEDIUM PRIORITY:"
echo "     - 01-architecture/README.md"
echo "     - 02-core-features/README.md"
echo "     - 04-api-reference/README.md"
echo "     - 05-guides/README.md"
echo ""
echo "  🟢 LOW PRIORITY:"
echo "     - Subcarpeta READMEs (~15 files)"
echo "     - Consolidate embedding docs (3 → 1)"
echo "     - Consolidate RAG phase docs"
echo ""
echo "📍 Next Command:"
echo "  cd $DOCS_DIR"
echo "  ls -la  # Verify new structure"
echo ""
echo "🔧 To rollback:"
echo "  rm -rf $DOCS_DIR"
echo "  mv $BACKUP_DIR $DOCS_DIR"
echo ""
echo "=========================================="
echo "🎉 Reorganization script completed!"
echo "=========================================="
```

---

## ✅ Checklist de Nuevos Archivos a Crear

### 🔴 PRIORIDAD ALTA

#### Infrastructure Generation (6 archivos) ⭐ MÁS IMPORTANTE

1. **`03-mge-v2/infrastructure-generation/README.md`**
   - Overview completo del feature
   - Qué genera (Dockerfile, docker-compose, etc.)
   - Beneficios y casos de uso
   - Links a otros docs

2. **`03-mge-v2/infrastructure-generation/architecture.md`**
   - Diseño técnico del servicio
   - Componentes: InfrastructureGenerationService, TemplateLoader
   - Diagrama de flujo
   - Integración con MGE V2 pipeline

3. **`03-mge-v2/infrastructure-generation/templates-guide.md`**
   - Catálogo de templates disponibles
   - Estructura de templates (Jinja2)
   - Cómo crear custom templates
   - Variables disponibles

4. **`03-mge-v2/infrastructure-generation/usage-examples.md`**
   - Ejemplos completos paso a paso
   - FastAPI project generation
   - Node.js/Express project
   - React/Next.js project
   - Output esperado

5. **`03-mge-v2/infrastructure-generation/troubleshooting.md`**
   - Problemas comunes
   - Docker no levanta
   - Variables de entorno faltantes
   - Templates errors
   - Debugging tips

6. **`03-mge-v2/infrastructure-generation/plan.md`**
   - ← Ya existe: mover `mge_v2_complete_project_generation_plan.md`

#### Getting Started (5 archivos)

7. **`00-getting-started/README.md`**
   - Welcome message
   - Prerequisites
   - Navigation guide
   - Links a quick-start

8. **`00-getting-started/quick-start.md`**
   - Setup en 5 minutos
   - Docker installation
   - Environment variables
   - First API call

9. **`00-getting-started/installation.md`**
   - Instalación detallada
   - Dependencies
   - Configuration
   - Verification steps

10. **`00-getting-started/first-project.md`**
    - Tutorial completo primer proyecto
    - "Build a TODO API" step-by-step
    - Expected output
    - Next steps

11. **`00-getting-started/concepts.md`**
    - DDD concepts (Aggregate, Entity, Value Object)
    - MasterPlan structure
    - Atomization concept
    - Validation levels

#### Main README.md (1 archivo)

12. **`README.md` (root - ACTUALIZAR)**
    - Complete index con links a todo
    - Quick navigation por rol (Dev, QA, DevOps, PM)
    - Structure overview
    - Getting started link destacado

### 🟡 PRIORIDAD MEDIA

#### Architecture (4 archivos)

13. **`01-architecture/README.md`**
    - Índice de arquitectura
    - Links a diagrams
    - Overview of system design

14. **`01-architecture/data-flow.md`**
    - End-to-end data flow
    - Discovery → MasterPlan → Execution
    - Diagrams

15. **`01-architecture/technology-stack.md`**
    - Full tech stack
    - Versions
    - Justifications

16. **`01-architecture/domain-driven-design.md`**
    - DDD in DevMatrix
    - Bounded contexts
    - Aggregates

#### Core Features (4 archivos)

17. **`02-core-features/README.md`**
    - Índice de features
    - Quick links

18. **`02-core-features/discovery/README.md`**
    - Discovery overview
    - DDD extraction

19. **`02-core-features/discovery/ddd-extraction.md`**
    - Technical details

20. **`02-core-features/discovery/requirements-analysis.md`**
    - Requirements extraction

#### API & Guides (4 archivos)

21. **`04-api-reference/README.md`**
    - API overview
    - Authentication

22. **`04-api-reference/websocket-api/streaming.md`**
    - WebSocket streaming
    - Event types

23. **`05-guides/README.md`**
    - Guides index

24. **`09-security/README.md`**
    - Security overview
    - Best practices

### 🟢 PRIORIDAD BAJA

#### Subcarpeta READMEs (~15 archivos)

25-39. READMEs para cada subcarpeta que los necesite

#### Consolidations (3 archivos)

40. **`02-core-features/rag-system/embedding-models.md`**
    - MERGE de 3 archivos embedding

41. **`02-core-features/rag-system/phases/phase-1-gpu.md`**
    - CONSOLIDATE 3 phase 1 files

42. **`02-core-features/rag-system/phases/phase-4-final.md`**
    - CONSOLIDATE 6 phase 4 files

---

## 📊 Métricas de Éxito

### Antes de Reorganización
- **Archivos en raíz**: 17
- **Carpetas sin README**: 12
- **Duplicados**: ~10 archivos
- **Documentación Infrastructure**: 0 archivos
- **Estructura**: Plana, sin jerarquía

### Después de Reorganización (Objetivo)
- **Archivos en raíz**: 1 (README.md)
- **Carpetas sin README**: 0
- **Duplicados consolidados**: ~5 archivos merge
- **Documentación Infrastructure**: 6 archivos completos
- **Estructura**: Jerárquica numerada, lógica de lectura

### Objetivos de Calidad
- ✅ Cada carpeta tiene README.md
- ✅ Numeración facilita orden de lectura
- ✅ Getting Started para nuevos usuarios
- ✅ Infrastructure Generation completamente documentado
- ✅ Sin archivos sueltos en raíz
- ✅ Archive limpio y organizado
- ✅ Links cruzados funcionando

---

## 🚀 Ejecución del Plan

### Opción 1: Ejecución Completa (Recomendado)

```bash
# 1. Save script
cat > /tmp/reorganize_docs.sh << 'SCRIPT_END'
[Copiar el bash script completo de arriba]
SCRIPT_END

# 2. Make executable
chmod +x /tmp/reorganize_docs.sh

# 3. Review script
less /tmp/reorganize_docs.sh

# 4. Execute
/tmp/reorganize_docs.sh

# 5. Verify
cd /home/kwar/code/agentic-ai/DOCS
find . -maxdepth 1 -type d | sort
```

### Opción 2: Ejecución Manual por Fases

```bash
# Phase 1: Backup
cp -r /home/kwar/code/agentic-ai/DOCS /home/kwar/code/agentic-ai/DOCS_BACKUP_$(date +%Y%m%d)

# Phase 2: Create directories
cd /home/kwar/code/agentic-ai/DOCS
mkdir -p 00-getting-started 01-architecture ...

# Phase 3-6: Execute moves section by section
# (Copy commands from script)

# Phase 7: Verify
find . -type d | sort
```

### Opción 3: Dry-Run (Testing)

```bash
# Add to start of script:
DRY_RUN=true  # Set to false for actual execution

# Replace all 'mv' with:
if [ "$DRY_RUN" = true ]; then
  echo "DRY RUN: mv $src $dst"
else
  mv "$src" "$dst"
fi
```

---

## ⚠️ Notas de Seguridad

1. **Backup Automático**: El script crea backup automáticamente
2. **Non-Destructive**: Usa `mv`, no `rm`, preserva todo
3. **Rollback Simple**: Comando de rollback incluido en output
4. **Error Handling**: `set -e` detiene en primer error
5. **2>/dev/null**: Ignora errores de archivos faltantes (OK)

---

## 📅 Timeline de Implementación

### Sprint 1: Reorganización Física (1-2 días)
- Día 1 AM: Ejecutar bash script
- Día 1 PM: Verificar movimientos, fix errors
- Día 2: Crear READMEs básicos

### Sprint 2: Infrastructure Docs (2-3 días) ⭐ PRIORIDAD
- Día 3-4: Escribir 6 docs de Infrastructure Generation
- Día 5: Review y ejemplos

### Sprint 3: Getting Started (2 días)
- Día 6: Escribir quick-start e installation
- Día 7: Escribir first-project y concepts

### Sprint 4: READMEs y Consolidación (2-3 días)
- Día 8-9: Crear READMEs faltantes
- Día 10: Consolidar archivos duplicados

### Sprint 5: Review y Links (1 día)
- Día 11: Actualizar cross-references
- Día 11: Final QA

**Total: 11 días de trabajo**

---

## 🎯 Próximos Pasos Inmediatos

1. **EJECUTAR bash script** para reorganizar estructura
2. **CREAR** documentación de Infrastructure Generation (6 archivos)
3. **CREAR** Getting Started section (5 archivos)
4. **ACTUALIZAR** README.md principal
5. **CONSOLIDAR** archivos duplicados (embedding, phases)
6. **CREAR** READMEs faltantes
7. **ACTUALIZAR** links cruzados

---

**Fin del Plan de Reorganización**

**Fecha**: 2025-11-10
**Autor**: Dany (SuperClaude)
**Estado**: ✅ Listo para ejecución
**Backup**: Automático en script
