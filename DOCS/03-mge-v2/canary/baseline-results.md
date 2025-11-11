# Baseline Results - Gold Set Projects

**Version:** 1.0
**Created:** 2025-11-11
**Owner:** Ariel
**Status:** 🔄 IN PROGRESS (1/15 projects measured)

---

## Formato de Medición

Para cada proyecto del Gold Set, registrar:

```yaml
project_name:
  execution_date: "YYYY-MM-DD HH:MM:SS"

  timing:
    total_duration_seconds: 0
    phase_discovery: 0
    phase_masterplan: 0
    phase_code_generation: 0
    phase_atomization: 0
    phase_file_writing: 0
    phase_infrastructure: 0
    phase_wave_execution: 0
    p50_latency: 0
    p95_latency: 0
    p99_latency: 0

  cost:
    total_cost_usd: 0.0
    cost_per_task: 0.0
    cost_per_atom: 0.0
    llm_input_tokens: 0
    llm_output_tokens: 0
    llm_cached_tokens: 0

  precision:
    spec_conformance_percent: 0.0  # % requisitos implementados
    integration_pass_percent: 0.0   # % tests integración passing
    validation_pass_percent: 0.0    # % validaciones L1-L4 passing
    precision_score: 0.0             # Compuesto: 50% + 30% + 20%

  quality:
    total_tasks: 0
    tasks_successful: 0
    tasks_failed: 0
    success_rate: 0.0
    syntax_errors: 0
    import_errors: 0
    type_errors: 0
    retry_count: 0
    retry_rate: 0.0

  output:
    total_atoms: 0
    files_written: 0
    lines_of_code: 0
    infrastructure_files: 0
```

---

## ✅ Proyecto 1: FastAPI Task Management API

**Medición:** 2025-11-11 10:51:23
**Test Run:** `test_complete_mge_v2_pipeline_fastapi`
**Status:** ✅ COMPLETADO

```yaml
fastapi_task_management:
  execution_date: "2025-11-11 10:51:23"
  session_id: "86ce5e22-b86c-4ac9-9a95-aaf6bf1dbbe9"
  masterplan_id: "8e1c0c10-86e3-4092-97e6-fbca2dbb5288"

  timing:
    total_duration_seconds: 899.7  # 15 min
    phase_discovery: 38.3
    phase_masterplan: 187.4
    phase_code_generation: 661.7
    phase_atomization: 1.8
    phase_file_writing: 0.1
    phase_infrastructure: 0.1
    phase_wave_execution: 0.1
    p50_latency: 450.0  # Estimated
    p95_latency: 900.0
    p99_latency: 900.0

  cost:
    total_cost_usd: 0.93  # $0.23 (MasterPlan) + $0.70 (Code Gen)
    cost_per_task: 0.027  # $0.93 / 35 tasks
    cost_per_atom: 0.0029  # $0.93 / 317 atoms
    llm_input_tokens: 14638  # 2038 + ~12600 (34 tasks avg)
    llm_output_tokens: 57741  # 15241 + ~42500 (34 tasks)
    llm_cached_tokens: 0

  precision:
    spec_conformance_percent: 0.0  # ⚠️ NOT MEASURED YET
    integration_pass_percent: 0.0   # ⚠️ NOT MEASURED YET
    validation_pass_percent: 0.0    # ⚠️ NOT MEASURED YET
    precision_score: 0.0             # PENDING: Needs measurement

  quality:
    total_tasks: 35
    tasks_successful: 34
    tasks_failed: 1  # task 3953cd0c - invalid syntax after 3 retries
    success_rate: 97.1  # 34/35 = 97.1%
    syntax_errors: 1
    import_errors: 0  # Unknown
    type_errors: 0    # Unknown
    retry_count: 3    # 1 task × 3 attempts
    retry_rate: 2.9   # 1/35 = 2.9%

  output:
    total_atoms: 317
    files_written: 29  # Code files
    infrastructure_files: 6  # Dockerfile, docker-compose, etc
    total_files: 35
    lines_of_code: 0  # Unknown (needs measurement)

  project_details:
    domain: "Task Management"
    bounded_contexts: 3
    aggregates: 4
    value_objects: 5
    domain_events: 5
    services: 5
    phases: 3
    milestones: 10
    subtasks: 154
    estimated_days: 2
    team_size: 5
    parallelization_ratio: 0.34
```

**Observaciones:**
- ✅ Pipeline completo ejecutado exitosamente
- ✅ 97.1% tasa de éxito en code generation
- ⚠️ 1 task falló después de 3 retries (syntax error)
- ⚠️ Métricas de precisión pendientes (requiere acceptance tests execution)
- ⏳ Tiempo total: 15 minutos (razonable para 35 tasks)
- 💰 Coste: $0.93 USD (bien debajo del límite de $200)

---

## 🔄 Proyecto 2: Django Blog API

**Status:** ⏳ PENDING
**Planned Date:** TBD

```yaml
django_blog_api:
  execution_date: null
  status: "PENDING_BASELINE"
```

---

## 🔄 Proyecto 3: Python CLI - Code Analyzer

**Status:** ⏳ PENDING
**Planned Date:** TBD

```yaml
python_cli_analyzer:
  execution_date: null
  status: "PENDING_BASELINE"
```

---

## 🔄 Proyecto 4: Flask Payment Gateway

**Status:** ⏳ PENDING
**Planned Date:** TBD

```yaml
flask_payment_service:
  execution_date: null
  status: "PENDING_BASELINE"
```

---

## 🔄 Proyecto 5: Python Data Pipeline

**Status:** ⏳ PENDING
**Planned Date:** TBD

```yaml
python_data_pipeline:
  execution_date: null
  status: "PENDING_BASELINE"
```

---

## 🔄 Proyecto 6: Next.js E-commerce

**Status:** ⏳ PENDING
**Planned Date:** TBD

```yaml
nextjs_ecommerce:
  execution_date: null
  status: "PENDING_BASELINE"
```

---

## 🔄 Proyecto 7: Express GraphQL API

**Status:** ⏳ PENDING
**Planned Date:** TBD

```yaml
express_graphql_api:
  execution_date: null
  status: "PENDING_BASELINE"
```

---

## 🔄 Proyecto 8: React Admin Dashboard

**Status:** ⏳ PENDING
**Planned Date:** TBD

```yaml
react_admin_dashboard:
  execution_date: null
  status: "PENDING_BASELINE"
```

---

## 🔄 Proyecto 9: Vue 3 Project Management

**Status:** ⏳ PENDING
**Planned Date:** TBD

```yaml
vue3_project_mgmt:
  execution_date: null
  status: "PENDING_BASELINE"
```

---

## 🔄 Proyecto 10: Node.js Monorepo SaaS

**Status:** ⏳ PENDING
**Planned Date:** TBD

```yaml
nodejs_monorepo_saas:
  execution_date: null
  status: "PENDING_BASELINE"
```

---

## 🔄 Proyecto 11: Go URL Shortener

**Status:** ⏳ PENDING
**Planned Date:** TBD

```yaml
go_url_shortener:
  execution_date: null
  status: "PENDING_BASELINE"
```

---

## 🔄 Proyecto 12: Go Event Sourcing

**Status:** ⏳ PENDING
**Planned Date:** TBD

```yaml
go_event_sourcing:
  execution_date: null
  status: "PENDING_BASELINE"
```

---

## 🔄 Proyecto 13: Rust File Processor

**Status:** ⏳ PENDING
**Planned Date:** TBD

```yaml
rust_file_processor:
  execution_date: null
  status: "PENDING_BASELINE"
```

---

## 🔄 Proyecto 14: AWS Lambda Image Resizer

**Status:** ⏳ PENDING
**Planned Date:** TBD

```yaml
aws_lambda_image_resizer:
  execution_date: null
  status: "PENDING_BASELINE"
```

---

## 🔄 Proyecto 15: Full-Stack Social Network

**Status:** ⏳ PENDING
**Planned Date:** TBD

```yaml
fullstack_social_network:
  execution_date: null
  status: "PENDING_BASELINE"
```

---

## 📊 Agregados (1/15 proyectos)

```yaml
aggregate_metrics:
  projects_measured: 1
  projects_pending: 14

  avg_timing:
    total_duration_seconds: 899.7
    phase_discovery: 38.3
    phase_masterplan: 187.4
    phase_code_generation: 661.7

  avg_cost:
    total_cost_usd: 0.93
    cost_per_task: 0.027
    cost_per_atom: 0.0029

  avg_precision:
    spec_conformance_percent: 0.0  # PENDING
    integration_pass_percent: 0.0   # PENDING
    validation_pass_percent: 0.0    # PENDING
    precision_score: 0.0             # PENDING

  avg_quality:
    success_rate: 97.1
    retry_rate: 2.9
```

---

## 🎯 Objetivos de Precisión

### Target Metrics (Week 4)
- ✅ **Coste:** <$200 USD por proyecto → **ACHIEVED** ($0.93 <<< $200)
- ⏳ **Precision Score:** ≥98% → **PENDING** (requiere measurement)
- ⏳ **P95 Latency:** Estable (<20 min) → **PARTIAL** (15 min ✅)
- ⏳ **Success Rate:** ≥95% → **ACHIEVED** (97.1% ✅)

### Gate A (Promoción)
- Score ≥95% por 2 semanas
- Coste <$200
- P95 estable

### Gate S (Objetivo Final)
- Score ≥98% por 2 semanas
- En ≥80% de canarios (12/15 proyectos)

---

## 📝 Notas

### Próximos Pasos
1. Ejecutar baseline en proyectos 2-15
2. Implementar métricas de precisión (Spec Conformance, Integration, Validation)
3. Automatizar medición semanal
4. Comparar MGE V2 vs baseline

### Limitaciones Actuales
- ⚠️ Métricas de precisión no implementadas aún
- ⚠️ Solo 1/15 proyectos tiene baseline
- ⚠️ Faltan métricas de calidad detalladas (import errors, type errors)

---

**Owner:** Ariel
**Status:** 🔄 IN PROGRESS (1/15 completed)
**Last Updated:** 2025-11-11
