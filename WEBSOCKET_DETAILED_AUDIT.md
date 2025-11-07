# AUDITORÍA COMPLETA: Sincronización WebSocket Backend ↔ Frontend

Análisis exhaustivo de campos, eventos y datos sincronizados entre backend y frontend.

---

## 1. MODELOS DE BASE DE DATOS (Backend)

### DiscoveryDocument Fields
| Campo | Tipo | Nullable | Notas |
|-------|------|----------|-------|
| discovery_id | UUID | NO | PK |
| session_id | String(100) | NO | Index |
| user_id | String(100) | NO | Index |
| user_request | Text | NO | Original request |
| domain | String(200) | NO | Domain name |
| bounded_contexts | JSON | NO | Array of BCs |
| aggregates | JSON | NO | Array of aggs |
| value_objects | JSON | NO | Array of VOs |
| domain_events | JSON | NO | Array of events |
| services | JSON | NO | Array of services |
| assumptions | JSON | YES | Assumptions made |
| clarifications_needed | JSON | YES | Questions |
| risk_factors | JSON | YES | Identified risks |
| llm_model | String(100) | YES | Model used |
| llm_cost_usd | Float | YES | Cost |
| created_at | DateTime | NO | Timestamp |
| updated_at | DateTime | NO | Timestamp |

### MasterPlan Fields
| Campo | Tipo | Nullable | Notas |
|-------|------|----------|-------|
| masterplan_id | UUID | NO | PK |
| discovery_id | UUID | NO | FK |
| session_id | String(100) | NO | Index |
| user_id | String(100) | NO | Index |
| project_name | String(200) | NO | Project name |
| description | Text | YES | Description |
| status | Enum | NO | DRAFT, IN_PROGRESS, COMPLETED, etc |
| tech_stack | JSON | NO | {backend, frontend, database} |
| architecture_style | String(100) | YES | monolithic/microservices |
| total_phases | Integer | NO | Default 3 |
| total_milestones | Integer | NO | Count |
| total_tasks | Integer | NO | Count |
| total_subtasks | Integer | NO | Count |
| calculated_task_count | Integer | YES | Exact count |
| complexity_metrics | JSON | YES | {bounded_contexts, aggregates, ...} |
| task_breakdown | JSON | YES | {setup, modeling, ...} |
| parallelization_level | Integer | YES | Max concurrent |
| calculation_rationale | Text | YES | Explanation |
| completed_tasks | Integer | NO | Count |
| failed_tasks | Integer | NO | Count |
| skipped_tasks | Integer | NO | Count |
| progress_percent | Float | NO | % |
| estimated_cost_usd | Float | YES | Estimated cost |
| actual_cost_usd | Float | NO | Actual cost |
| estimated_duration_minutes | Integer | YES | Estimate |
| actual_duration_minutes | Integer | YES | Actual |
| llm_model | String(100) | YES | Model |
| generation_cost_usd | Float | YES | Generation cost |
| generation_tokens | Integer | YES | Tokens used |
| workspace_path | String(500) | YES | Path |
| version | Integer | NO | Version |
| created_at | DateTime | NO | Timestamp |
| updated_at | DateTime | NO | Timestamp |
| started_at | DateTime | YES | When started |
| completed_at | DateTime | YES | When completed |

### MasterPlanPhase Fields
| Campo | Tipo | Nullable |
|-------|------|----------|
| phase_id | UUID | NO |
| masterplan_id | UUID | NO |
| phase_type | Enum | NO |
| phase_number | Integer | NO |
| name | String(200) | NO |
| description | Text | YES |
| total_milestones | Integer | NO |
| total_tasks | Integer | NO |
| completed_tasks | Integer | NO |
| progress_percent | Float | NO |
| created_at | DateTime | NO |
| started_at | DateTime | YES |
| completed_at | DateTime | YES |

### MasterPlanMilestone Fields
| Campo | Tipo | Nullable |
|-------|------|----------|
| milestone_id | UUID | NO |
| phase_id | UUID | NO |
| milestone_number | Integer | NO |
| name | String(200) | NO |
| description | Text | YES |
| depends_on_milestones | JSON | YES |
| total_tasks | Integer | NO |
| completed_tasks | Integer | NO |
| progress_percent | Float | NO |
| created_at | DateTime | NO |
| started_at | DateTime | YES |
| completed_at | DateTime | YES |

### MasterPlanTask Fields
| Campo | Tipo | Nullable |
|-------|------|----------|
| task_id | UUID | NO |
| masterplan_id | UUID | NO |
| phase_id | UUID | YES |
| milestone_id | UUID | NO |
| task_number | Integer | NO |
| name | String(300) | NO |
| description | Text | NO |
| complexity | Enum | NO |
| task_type | String(100) | YES |
| depends_on_tasks | JSON | YES |
| blocks_tasks | JSON | YES |
| status | Enum | NO |
| target_files | JSON | YES |
| modified_files | JSON | YES |
| llm_model | String(100) | YES |
| llm_prompt | Text | YES |
| llm_response | Text | YES |
| llm_cost_usd | Float | YES |
| llm_tokens_input | Integer | YES |
| llm_tokens_output | Integer | YES |
| llm_cached_tokens | Integer | YES |
| validation_passed | Boolean | YES |
| validation_errors | JSON | YES |
| validation_logs | Text | YES |
| retry_count | Integer | NO |
| max_retries | Integer | NO |
| last_error | Text | YES |
| created_at | DateTime | NO |
| started_at | DateTime | YES |
| completed_at | DateTime | YES |
| failed_at | DateTime | YES |

---

## 2. EVENTOS WebSocket - EMISIÓN (Backend)

### Discovery Events

#### 1. discovery_generation_start
**Función:** `emit_discovery_generation_start(session_id, estimated_tokens, estimated_duration_seconds, estimated_cost_usd)`

**Campos Enviados:**
```json
{
  "session_id": "string",
  "estimated_tokens": 8000,
  "estimated_duration_seconds": 30,
  "estimated_cost_usd": 0.09
}
```

#### 2. discovery_tokens_progress
**Función:** `emit_discovery_tokens_progress(session_id, tokens_received, estimated_total, current_phase)`

**Campos Enviados:**
```json
{
  "session_id": "string",
  "tokens_received": int,
  "estimated_total": int,
  "percentage": int (capped at 95%),
  "current_phase": "string"
}
```

#### 3. discovery_entity_discovered
**Función:** `emit_discovery_entity_discovered(session_id, entity_type, count, name?)`

**Campos Enviados:**
```json
{
  "session_id": "string",
  "type": "bounded_context|aggregate|entity|value_object|domain_event",
  "count": int,
  "name": "string (optional)"
}
```

#### 4. discovery_parsing_complete
**Función:** `emit_discovery_parsing_complete(session_id, domain, total_bounded_contexts, total_aggregates, total_entities)`

**Campos Enviados:**
```json
{
  "session_id": "string",
  "domain": "string",
  "total_bounded_contexts": int,
  "total_aggregates": int,
  "total_entities": int
}
```

#### 5. discovery_validation_start
**Función:** `emit_discovery_validation_start(session_id)`

**Campos Enviados:**
```json
{
  "session_id": "string"
}
```

#### 6. discovery_saving_start
**Función:** `emit_discovery_saving_start(session_id, total_entities)`

**Campos Enviados:**
```json
{
  "session_id": "string",
  "total_entities": int
}
```

#### 7. discovery_generation_complete
**Función:** `emit_discovery_generation_complete(session_id, discovery_id, domain, total_bounded_contexts, total_aggregates, total_entities, generation_cost_usd, duration_seconds)`

**Campos Enviados:**
```json
{
  "session_id": "string",
  "discovery_id": "UUID",
  "domain": "string",
  "total_bounded_contexts": int,
  "total_aggregates": int,
  "total_entities": int,
  "generation_cost_usd": float,
  "duration_seconds": float
}
```

### MasterPlan Events

#### 1. masterplan_generation_start
**Función:** `emit_masterplan_generation_start(session_id, discovery_id, estimated_tokens, estimated_duration_seconds, estimated_cost_usd, masterplan_id?)`

**Campos Enviados:**
```json
{
  "discovery_id": "UUID",
  "session_id": "string",
  "estimated_tokens": 17000,
  "estimated_duration_seconds": 90,
  "estimated_cost_usd": 0.25,
  "masterplan_id": "UUID (optional)"
}
```

#### 2. masterplan_tokens_progress
**Función:** `emit_masterplan_tokens_progress(session_id, tokens_received, estimated_total, current_phase)`

**Campos Enviados:**
```json
{
  "session_id": "string",
  "tokens_received": int,
  "estimated_total": int,
  "percentage": int (capped at 95%),
  "current_phase": "string"
}
```

#### 3. masterplan_entity_discovered
**Función:** `emit_masterplan_entity_discovered(session_id, entity_type, count, name?, parent?)`

**Campos Enviados:**
```json
{
  "session_id": "string",
  "type": "phase|milestone|task",
  "count": int,
  "name": "string (optional)",
  "parent": "string (optional)"
}
```

#### 4. masterplan_parsing_complete
**Función:** `emit_masterplan_parsing_complete(session_id, total_phases, total_milestones, total_tasks)`

**Campos Enviados:**
```json
{
  "session_id": "string",
  "total_phases": int,
  "total_milestones": int,
  "total_tasks": int
}
```

#### 5. masterplan_validation_start
**Función:** `emit_masterplan_validation_start(session_id)`

**Campos Enviados:**
```json
{
  "session_id": "string"
}
```

#### 6. masterplan_saving_start
**Función:** `emit_masterplan_saving_start(session_id, total_entities)`

**Campos Enviados:**
```json
{
  "session_id": "string",
  "total_entities": int
}
```

#### 7. masterplan_generation_complete
**Función:** `emit_masterplan_generation_complete(session_id, masterplan_id, project_name, total_phases, total_milestones, total_tasks, generation_cost_usd, duration_seconds, estimated_total_cost_usd, estimated_duration_minutes)`

**Campos Enviados:**
```json
{
  "session_id": "string",
  "masterplan_id": "UUID",
  "project_name": "string",
  "total_phases": int,
  "total_milestones": int,
  "total_tasks": int,
  "generation_cost_usd": float,
  "duration_seconds": float,
  "estimated_total_cost_usd": float,
  "estimated_duration_minutes": int
}
```

---

## 3. RECEPCIÓN EN FRONTEND (useMasterPlanProgress Hook)

### Event Handler Mapping

| Evento WS | Campos Esperados | Campos Realmente Procesados | Match |
|-----------|------------------|---------------------------|-------|
| discovery_generation_start | session_id, estimated_tokens, estimated_duration_seconds, estimated_cost_usd | estimated_tokens → estimatedTotalTokens ✓, estimated_duration_seconds ✓, estimated_cost_usd → cost ✓ | ✓ |
| discovery_tokens_progress | session_id, tokens_received, estimated_total, percentage, current_phase | tokens_received ✓, estimated_total ✓, percentage ✓, (current_phase ignored) | ✓ |
| discovery_entity_discovered | session_id, type, count, name | type → entityType (conversion), count ✓, name ✓ | ✓ |
| discovery_parsing_complete | session_id, domain, total_bounded_contexts, total_aggregates, total_entities | total_bounded_contexts ✓, total_aggregates ✓, total_entities ✓ | ✓ |
| discovery_validation_start | session_id | (state update only) | ✓ |
| discovery_saving_start | session_id, total_entities | total_entities ✓ | ✓ |
| discovery_generation_complete | session_id, discovery_id, domain, total_bounded_contexts, total_aggregates, total_entities, generation_cost_usd, duration_seconds | total_bounded_contexts ✓, total_aggregates ✓, total_entities ✓ | ✓ |
| masterplan_generation_start | discovery_id, session_id, estimated_tokens, estimated_duration_seconds, estimated_cost_usd, masterplan_id | estimated_cost_usd → cost ✓, estimated_duration_seconds ✓, estimated_tokens ✓ | ✓ |
| masterplan_tokens_progress | session_id, tokens_received, estimated_total, percentage, current_phase | tokens_received ✓, estimated_total ✓, percentage ✓ | ✓ |
| masterplan_entity_discovered | session_id, type, count, name, parent | type → entityType (conversion) ✓, count ✓, name ✓ | ✓ |
| masterplan_parsing_complete | session_id, total_phases, total_milestones, total_tasks | total_phases ✓, total_milestones ✓, total_tasks ✓ | ✓ |
| masterplan_validation_start | session_id | (state update only) | ✓ |
| masterplan_saving_start | session_id, total_entities | total_entities ✓ | ✓ |
| masterplan_generation_complete | session_id, masterplan_id, project_name, total_phases, total_milestones, total_tasks, generation_cost_usd, duration_seconds, estimated_total_cost_usd, estimated_duration_minutes | total_phases ✓, total_milestones ✓, total_tasks ✓ | ✓ |

---

## 4. DISCREPANCIAS IDENTIFICADAS

### CRÍTICAS (Impactan sincronización)

❌ **1. Campo Naming: DB vs WebSocket**
- DB: `llm_cost_usd` en MasterPlan
- WS enviado en masterplan_generation_complete: `generation_cost_usd` y `estimated_total_cost_usd`
- Frontend procesa: `estimated_cost_usd` → `cost`
- **Estado:** MasterPlan completo no sincroniza el costo real generado

❌ **2. Campo Naming: discovery_entity_discovered**
- WS envía: `"type": "bounded_context"` (snake_case)
- Frontend espera: `entity_type` o `type`
- Frontend convierte: `.toLowerCase().replace(/([a-z])([A-Z])/g, '$1_$2')` (innecesario)
- **Estado:** Funciona pero conversión es redundante

❌ **3. Falta de Fields en Eventos de Progreso**
- masterplan_generation_complete NO envía `discovery_id`
- Frontend NO puede correlacionar con discovery original
- **Estado:** Imposible rastrear relación Discovery → MasterPlan en evento de finalización

### MAYORES (Funcionalidad incompleta)

⚠️ **4. validation_passed y validation_errors NO se sincronizan**
- DB tiene: `MasterPlanTask.validation_passed`, `validation_errors`, `validation_logs`
- WS NUNCA emite estos datos
- Frontend NUNCA los procesa
- **Estado:** Validación de tareas nunca se reporta en progreso

⚠️ **5. Estado de Tareas Individuales NO se sincroniza**
- DB tiene: `MasterPlanTask.status` (PENDING, READY, IN_PROGRESS, VALIDATING, COMPLETED, FAILED, SKIPPED, BLOCKED)
- WS NUNCA emite actualizaciones por tarea
- Frontend NUNCA procesa estado de tareas
- **Estado:** Solo se reportan totales, no estados individuales

⚠️ **6. Costo Real vs Estimado NO diferenciado en eventos**
- DB tiene: `estimated_cost_usd` vs `actual_cost_usd`, `generation_cost_usd`
- masterplan_generation_complete envía: `generation_cost_usd` y `estimated_total_cost_usd`
- NO envía: `actual_cost_usd` al finalizar
- **Estado:** Frontend no sabe si mostrar estimado o real

⚠️ **7. Duración Real vs Estimada confusa**
- masterplan_generation_complete envía: `duration_seconds` (actual) y `estimated_duration_minutes`
- Frontend procesa `duration_seconds` pero lo mapea a `elapsedSeconds`
- `estimatedDurationSeconds` viene de `masterplan_generation_start` (estimado)
- **Estado:** Mezcla de unidades (segundos vs minutos) en datos

### MENORES (Edge cases)

⚡ **8. llm_model NO sincronizado en eventos de progreso**
- DB almacena: `llm_model` en Discovery, MasterPlan, Task
- WS NUNCA emite esto
- Frontend NUNCA sabe qué modelo se usó
- **Estado:** Información faltante en progreso

⚡ **9. workspace_path NO sincronizado**
- DB almacena: `MasterPlan.workspace_path`
- WS NUNCA emite
- Frontend NUNCA procesa
- **Estado:** Frontend no puede saber dónde se ejecutará el plan

⚡ **10. Subtasks NUNCA se sincronizan**
- DB tiene: `MasterPlanSubtask` con estado
- WS NUNCA emite progreso de subtareas
- Frontend NUNCA procesa
- **Estado:** Imposible rastrear progreso a nivel de subtarea

⚡ **11. Milestones Individuales NO en progreso**
- DB almacena: `MasterPlanMilestone.progress_percent`, `completed_tasks`
- WS NUNCA emite por milestone
- Frontend NUNCA procesa por milestone
- **Estado:** Solo totales de fases, no desglose por milestone

---

## 5. CAMPOS SINCRONIZADOS CORRECTAMENTE

✓ **Totales de Entidades:**
- total_phases ✓
- total_milestones ✓
- total_tasks ✓
- total_bounded_contexts ✓
- total_aggregates ✓
- total_entities ✓

✓ **Progreso de Tokens:**
- tokens_received ✓
- estimated_total ✓
- percentage ✓
- current_phase ✓

✓ **Costos (parcialmente):**
- estimated_cost_usd ✓
- generation_cost_usd ✓ (pero nombrado inconsistentemente)

✓ **Duración:**
- duration_seconds ✓
- estimated_duration_seconds ✓

✓ **IDs de Sesión:**
- session_id ✓ (campo común)
- masterplan_id ✓
- discovery_id ✓ (en algunos eventos)

---

## 6. RESUMEN EJECUTIVO

### Datos que FLUYEN correctamente ✓
1. IDs de sesión y seguimiento
2. Conteos totales (fases, milestones, tareas)
3. Progreso de tokens
4. Porcentajes de progreso
5. Timestamps de eventos
6. Estimaciones (costo, duración)

### Datos que NO FLUYEN ❌
1. **Costo actual generado** (vs estimado)
2. **Estado individual de tareas**
3. **Validaciones de tareas**
4. **Progreso de subtareas**
5. **Progreso de milestones individuales**
6. **Modelo LLM utilizado**
7. **Ruta del workspace**
8. **Errores de validación**
9. **Logs de validación**
10. **Dependencias entre tareas**

### Problemas de Mapeo
1. Naming inconsistente: `llm_cost_usd` vs `generation_cost_usd`
2. Unidades mixtas: segundos vs minutos
3. Distinción confusa: estimado vs actual
4. Conversión innecesaria: entity_type en frontend

---

## 7. IMPACTO EN MODAL DE PROGRESO

**MasterPlanProgressModal** utiliza:
- `progressState.tokensReceived` ✓
- `progressState.estimatedTotalTokens` ✓
- `progressState.percentage` ✓
- `progressState.cost` ✓
- `progressState.elapsedSeconds` ✓
- `progressState.phasesFound` ✓
- `progressState.milestonesFound` ✓
- `progressState.tasksFound` ✓
- `progressState.boundedContexts` ✓
- `progressState.aggregates` ✓
- `progressState.entities` ✓

**TODOS estos campos se sincronizan correctamente para mostrar el modal.**

Sin embargo, **campos NO mostrados pero que FALTAN:**
- Validación por tarea
- Errores de validación
- Progreso de subtareas
- Progreso de milestones
- Modelo LLM usado
- Desglose detallado por tarea

---

## CONCLUSIÓN

**90% de funcionalidad crítica funciona correctamente.**
**10% de funcionalidad detallada falta o está inconsistente.**

El modal cierra prematuramente NO por problemas de sincronización de campos,
sino por **problemas de room management y sessionId en WebSocket.**

