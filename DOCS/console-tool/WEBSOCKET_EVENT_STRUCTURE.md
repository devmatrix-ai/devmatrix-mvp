# WebSocket Event Structure - Console Tool

**Granularity Level**: Opción 2 - 1 evento por TASK (120 eventos total)
**Update Frequency**: En tiempo real (tan pronto como cada task completada)
**Total Events Expected**: ~120 + overhead events

---

## 📡 Evento Principal: Task Completion

El console tool espera este evento **cada vez que una TASK se completa**:

```json
{
  "type": "progress_update",
  "timestamp": "2025-11-16T16:34:45.123Z",
  "data": {
    "task_id": "task_001",
    "task_name": "Analyze authentication requirements",
    "phase": 1,
    "phase_name": "Analysis",
    "status": "completed",
    "progress": 10,
    "progress_percent": 8.33,
    "completed_tasks": 10,
    "total_tasks": 120,
    "current_wave": 1,
    "duration_ms": 2340,
    "subtask_status": {
      "subtask_1": "completed",
      "subtask_2": "completed"
    }
  }
}
```

### Campo por Campo:

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| `type` | string | Tipo de evento | `"progress_update"` |
| `timestamp` | ISO8601 | Cuándo ocurrió | `"2025-11-16T16:34:45.123Z"` |
| `task_id` | string | ID único de la task | `"task_001"` |
| `task_name` | string | Nombre legible | `"Implement auth.py"` |
| `phase` | integer | Número de fase (0-4) | `2` |
| `phase_name` | string | Nombre de fase | `"Planning"` |
| `status` | string | Estado de la task | `"completed"` |
| `progress` | integer | Tasks completadas (contador) | `45` |
| `progress_percent` | float | Porcentaje de progreso | `37.5` |
| `completed_tasks` | integer | Total tasks completadas | `45` |
| `total_tasks` | integer | Total tasks en el plan | `120` |
| `current_wave` | integer | Número de wave actual | `3` |
| `duration_ms` | float | Duración en milisegundos | `2340.5` |
| `subtask_status` | object | Estado de subtareas | Ver debajo |

---

## 🔄 Eventos Secundarios

### Cuando una WAVE se completa:

```json
{
  "type": "wave_completed",
  "timestamp": "2025-11-16T16:35:20.456Z",
  "data": {
    "wave_number": 3,
    "atoms_in_wave": 120,
    "atoms_completed": 120,
    "duration_ms": 45000,
    "success_rate": 0.98
  }
}
```

### Cuando se crea un ARTIFACT (archivo):

```json
{
  "type": "artifact_created",
  "timestamp": "2025-11-16T16:34:50.789Z",
  "data": {
    "path": "src/services/auth.py",
    "size": 2048,
    "type": "file",
    "language": "python",
    "task_id": "task_045"
  }
}
```

### Cuando hay un ERROR:

```json
{
  "type": "error",
  "timestamp": "2025-11-16T16:35:15.234Z",
  "data": {
    "task_id": "task_067",
    "task_name": "Run validation tests",
    "message": "Test assertion failed",
    "error_type": "AssertionError",
    "recoverable": true,
    "retry_attempt": 1,
    "max_retries": 4
  }
}
```

### Cuando comienza EJECUCIÓN:

```json
{
  "type": "execution_started",
  "timestamp": "2025-11-16T16:32:00.000Z",
  "data": {
    "execution_id": "exec_20251116_abc123",
    "total_tasks": 120,
    "total_atoms": 800,
    "estimated_duration_ms": 600000,
    "phases": [
      {
        "number": 0,
        "name": "Discovery",
        "tasks": 5
      },
      {
        "number": 1,
        "name": "Analysis",
        "tasks": 15
      },
      {
        "number": 2,
        "name": "Planning",
        "tasks": 20
      },
      {
        "number": 3,
        "name": "Execution",
        "tasks": 70
      },
      {
        "number": 4,
        "name": "Validation",
        "tasks": 10
      }
    ]
  }
}
```

### Cuando termina la EJECUCIÓN:

```json
{
  "type": "execution_completed",
  "timestamp": "2025-11-16T16:42:30.567Z",
  "data": {
    "execution_id": "exec_20251116_abc123",
    "status": "success",
    "total_tasks": 120,
    "completed_tasks": 120,
    "failed_tasks": 0,
    "duration_ms": 630000,
    "artifacts_created": 45,
    "tokens_used": 67450,
    "cost_usd": 0.42
  }
}
```

---

## 📊 Flujo Esperado Completo

```
1. execution_started
   └─ Informa: 120 tasks total, 8 fases

2. progress_update (x120)
   ├─ task_001 completed (8.33%)
   ├─ task_002 completed (16.67%)
   ├─ ...
   ├─ artifact_created (cada vez que genera archivo)
   ├─ error (si falla, con retry info)
   └─ task_120 completed (100%)

3. wave_completed (x8-10)
   ├─ wave_1 completed
   ├─ wave_2 completed
   └─ ...

4. execution_completed
   └─ Resumen final
```

---

## 🎯 Frecuencia de Eventos

| Evento | Frecuencia | Cantidad |
|--------|-----------|----------|
| `progress_update` | Cada task | 120 eventos |
| `artifact_created` | Cada archivo | ~45 eventos |
| `wave_completed` | Cada wave | 8-10 eventos |
| `error` | Si hay fallos | 0-20 eventos |
| `execution_started` | Al inicio | 1 evento |
| `execution_completed` | Al final | 1 evento |

**Total: ~180-200 eventos en toda la ejecución** (manejable)

---

## 💾 Cómo Enviar Desde Backend

### Pseudo-código:

```python
# En mge_v2_orchestration_service.py

for task in masterplan.tasks:
    # Ejecutar task
    result = execute_task(task)

    # Enviar evento vía WebSocket
    await websocket_manager.emit("progress_update", {
        "task_id": task.id,
        "task_name": task.name,
        "phase": task.phase_number,
        "phase_name": task.phase.name,
        "status": "completed",
        "progress": tasks_completed_count,
        "progress_percent": (tasks_completed_count / 120) * 100,
        "completed_tasks": tasks_completed_count,
        "total_tasks": 120,
        "current_wave": current_wave_number,
        "duration_ms": task.duration_ms,
        "timestamp": datetime.now().isoformat() + "Z"
    })

    # Si se crea artifact
    if result.artifact:
        await websocket_manager.emit("artifact_created", {
            "path": result.artifact.path,
            "size": result.artifact.size,
            "type": result.artifact.type,
            "language": detect_language(result.artifact.path),
            "task_id": task.id,
            "timestamp": datetime.now().isoformat() + "Z"
        })

    # Si hay error
    if result.error:
        await websocket_manager.emit("error", {
            "task_id": task.id,
            "task_name": task.name,
            "message": result.error.message,
            "error_type": result.error.type,
            "recoverable": result.error.recoverable,
            "retry_attempt": result.retry_count,
            "max_retries": 4,
            "timestamp": datetime.now().isoformat() + "Z"
        })
```

---

## ✅ Verificación Checklist

El backend debe:

- ✅ Enviar `execution_started` al inicio
- ✅ Enviar `progress_update` por cada task completada (120 total)
- ✅ Enviar `artifact_created` cada vez que genera archivo
- ✅ Enviar `error` si hay fallos con retry info
- ✅ Enviar `wave_completed` cuando termina cada wave
- ✅ Enviar `execution_completed` al finalizar

---

## 🎯 Qué Muestra el Console Tool

Con este flujo de eventos, el console tool mostrará:

```
Running authentication_feature...

Progress: [████████░░░░] 40%
Current Task: Implement auth.py (task_045)

Phase Progress:
├── Phase 0 (Discovery): ✅ [████████████] 100% (5/5 tasks)
├── Phase 1 (Analysis): ✅ [████████████] 100% (15/15 tasks)
├── Phase 2 (Planning): 🔄 [████████░░░░] 60% (12/20 tasks)
├── Phase 3 (Execution): ⏳ [░░░░░░░░░░░░] 0% (0/70 tasks)
└── Phase 4 (Validation): ⏳ [░░░░░░░░░░░░] 0% (0/10 tasks)

Wave Status:
├── Wave 1: ✅ Complete
├── Wave 2: ✅ Complete
├── Wave 3: 🔄 Running...
└── Waves 4-8: ⏳ Pending

Artifacts Created: 18 / 45 expected
├── src/auth.py (2.1 KB) ✅
├── src/models.py (3.5 KB) ✅
└── 16 more...

Tokens Used: 34,500 / 100,000 (34%)
Duration: 10m 23s
```

---

## 📝 Notes

- Timestamps deben ser ISO8601 format con `Z` al final
- `progress_percent` debe ser float (0-100)
- El console tool actualizará su display en tiempo real con cada evento
- Si hay múltiples eventos simultáneamente, se procesarán en orden
- El websocket_client.py bufferizará eventos si es necesario

---

**Con este esquema, el usuario verá progreso granular pero manejable.** ✅
