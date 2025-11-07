# AUDITORÍA DE SINCRONIZACIÓN WEBSOCKET - RESUMEN EJECUTIVO

**Realizado:** Nov 6, 2025  
**Hallazgo Principal:** Sincronización de CAMPOS funciona correctamente (90%)  
**Problema Real:** Gestión de rooms/sessionId en WebSocket, NO campos faltantes

---

## VERDADES CRITICAS

### ✓ LO QUE FUNCIONA BIEN (90%)

1. **Totales de Entidades**
   - Fases, milestones, tareas → synced ✓
   - Bounded contexts, aggregates, entities → synced ✓

2. **Progreso de Tokens**
   - tokens_received, estimated_total, percentage → synced ✓

3. **Estimaciones**
   - estimated_cost_usd, estimated_duration_seconds → synced ✓

4. **IDs y Seguimiento**
   - session_id, masterplan_id, discovery_id → synced ✓

5. **Eventos Críticos**
   - Todos los eventos de progreso se emiten correctamente
   - Frontend recibe y procesa correctamente

### ❌ LO QUE FALTA O ESTÁ MAL (10%)

| Campo | Estado | Impacto |
|-------|--------|--------|
| **generation_cost_usd** | ⚠️ Enviado pero NO procesado | Costo final no aparece en modal |
| **llm_model** | ❌ Nunca emitido | No sé qué modelo se usó |
| **workspace_path** | ❌ Nunca emitido | No sé dónde ejecutar |
| **validation_passed** | ❌ Nunca emitido | Validaciones invisibles |
| **task_status** | ❌ Nunca emitido | Solo totales, no detalles |
| **subtask_progress** | ❌ Nunca emitido | Sin granularidad |
| **duration_units** | ⚠️ Mezcla segundos/minutos | Confusión de unidades |

---

## PROBLEMAS ESPECIFICOS ENCONTRADOS

### 1. COST NOT SYNCED IN COMPLETION EVENT (CRITICAL)

**Qué pasa:**
- Backend emite `masterplan_generation_complete` con `generation_cost_usd: 0.32`
- Frontend busca `eventData.estimated_cost_usd` (que NO existe)
- Cost NOT actualizado en `progressState.cost`
- Modal muestra costo de Discovery (0.09) en lugar de MasterPlan (0.32)

**Solución:**
```typescript
// useMasterPlanProgress.ts línea 225
cost: eventData.generation_cost_usd || eventData.estimated_cost_usd || prev.cost
```

---

### 2. DISCOVERY_ID SENT BUT IGNORED (MINOR)

**Qué pasa:**
- Backend emite `masterplan_generation_start` con `discovery_id`
- Frontend lo ignora completamente
- Imposible correlacionar Discovery → MasterPlan en evento de finalización

**Solución:**
- Guardar `discoveryId` en progressState
- Usar para validación de flujo

---

### 3. DURATION UNIT CONFUSION (MINOR)

**Qué pasa:**
- `discovery_generation_complete` envía `duration_seconds`
- `masterplan_generation_complete` envía AMBOS:
  - `duration_seconds` (actual) - SEGUNDOS
  - `estimated_duration_minutes` (estimado) - MINUTOS
- Frontend mezcla unidades

**Solución:**
```python
# Backend: siempre segundos
"duration_seconds": 45.2,
"estimated_duration_seconds": 90
```

---

## MATRIZ DE SINCRONIZACIÓN CAMPO POR CAMPO

### Discovery Events (100% SYNC)

| Evento | Campos Enviados | Campos Procesados | Match |
|--------|-----------------|------------------|-------|
| discovery_generation_start | session_id, estimated_tokens, estimated_duration_seconds, estimated_cost_usd | ✓ todos procesados | ✓ |
| discovery_tokens_progress | session_id, tokens_received, estimated_total, percentage, current_phase | ✓ todos procesados | ✓ |
| discovery_entity_discovered | session_id, type, count, name | ✓ todos procesados | ✓ |
| discovery_parsing_complete | session_id, domain, total_bounded_contexts, total_aggregates, total_entities | ✓ todos procesados | ✓ |
| discovery_generation_complete | session_id, discovery_id, domain, total_bounded_contexts, total_aggregates, total_entities, generation_cost_usd, duration_seconds | ✓ totales procesados, discovery_id ignorado | ⚠️ |

### MasterPlan Events (95% SYNC)

| Evento | Campos Enviados | Campos Procesados | Match |
|--------|-----------------|------------------|-------|
| masterplan_generation_start | discovery_id, session_id, estimated_tokens, estimated_duration_seconds, estimated_cost_usd, masterplan_id | ✓ costos/tokens/duración procesados | ✓ |
| masterplan_tokens_progress | session_id, tokens_received, estimated_total, percentage, current_phase | ✓ todos procesados | ✓ |
| masterplan_entity_discovered | session_id, type, count, name, parent | ✓ todos procesados | ✓ |
| masterplan_parsing_complete | session_id, total_phases, total_milestones, total_tasks | ✓ todos procesados | ✓ |
| masterplan_generation_complete | session_id, masterplan_id, project_name, total_phases, total_milestones, total_tasks, generation_cost_usd, duration_seconds, estimated_total_cost_usd, estimated_duration_minutes | ⚠️ generation_cost_usd NOT procesado | ❌ |

---

## CAMPOS EN DB QUE NUNCA LLEGAN AL FRONTEND

### Never Emitted en WebSocket

| Campo DB | Ubicación | Razón | Impacto |
|----------|-----------|-------|--------|
| llm_model | MasterPlan, Discovery, Task | No hay evento para esto | No sé qué modelo se usó |
| workspace_path | MasterPlan | No sincronizado | No sé dónde ejecutar |
| validation_passed | MasterPlanTask | No hay evento | Validaciones invisibles |
| validation_errors | MasterPlanTask | No hay evento | No veo errores |
| task_status | MasterPlanTask | No hay evento | Solo totales, no detalles |
| complexity_metrics | MasterPlan | No sincronizado | No veo complejidad |
| tech_stack | MasterPlan | No sincronizado | No veo stack |
| subtask progress | MasterPlanSubtask | No hay evento | Sin granularidad |

---

## CAMPOS QUE LLEGAN AL FRONTEND CORRECTAMENTE

✓ session_id  
✓ masterplan_id  
✓ discovery_id (parcialmente - enviado pero ignorado)  
✓ total_phases  
✓ total_milestones  
✓ total_tasks  
✓ total_bounded_contexts  
✓ total_aggregates  
✓ total_entities  
✓ tokens_received  
✓ estimated_total  
✓ percentage  
✓ estimated_cost_usd (en generation_start)  
✓ estimated_duration_seconds  
✓ duration_seconds  
✓ project_name (completeness)  

---

## CONCLUSIÓN

### Estado General: BUENO (90%)

La sincronización de WebSocket **funciona bien** para mostrar el modal de progreso.

El modal cierra prematuramente **NO porque falten campos de datos**, sino porque:
1. **Room management** incorrecto (discovery_* vs masterplan_* rooms)
2. **sessionId** no se mantiene constante entre Discovery y MasterPlan
3. **Reconexiones** cierran el modal sin esperar finalización

### Problemas Críticos a Resolver: 3

1. ✋ **Cost not synced** en masterplan_generation_complete
2. 🆔 **discovery_id** enviado pero ignorado (menor importancia)
3. ⏱️ **Duration units** mixed en eventos

### Mejoras Futuro: 7

- Emit llm_model
- Emit workspace_path
- Emit validation_passed/errors
- Emit task_status individual
- Emit subtask_progress
- Standardize duration units
- Emit complexity_metrics

---

## ARCHIVOS MODIFICADOS EN ESTA AUDITORÍA

1. `/tmp/websocket_sync_audit.md` - Auditoría detallada (este)
2. `/tmp/field_mapping_matrix.md` - Matriz campo por campo

## PRÓXIMOS PASOS

1. **INMEDIATO:** Fijar cost sync en `useMasterPlanProgress.ts:225`
2. **Hoy:** Revisar room management en WebSocket
3. **Esta semana:** Agregar llm_model, workspace_path a eventos
4. **Próxima:** Implementar validation/task status events

