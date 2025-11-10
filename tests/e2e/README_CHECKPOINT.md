# E2E Test Checkpoint & Recovery System

Sistema de checkpoint y recuperación para tests E2E de larga duración en el pipeline MGE V2.

## 🎯 Problema Resuelto

Los tests E2E del pipeline MGE V2 toman ~12-17 minutos y cuestan ~$7 en llamadas LLM. Cuando fallan por errores transitorios (conexión API, timeouts), se pierde todo el progreso.

## ✨ Solución

Sistema automático de checkpoint que:
- **Persiste estado** después de cada fase
- **Recupera automáticamente** desde el último checkpoint
- **Reintenta con backoff** en errores transitorios (ConnectionResetError, etc.)
- **Trackea progreso** detallado por fase

## 📁 Archivos

### `checkpoint_manager.py`
Gestiona persistencia y carga de checkpoints en `/tests/e2e/checkpoints/`.

**Clases principales:**
- `PhaseCheckpoint`: Estado de una fase individual (discovery, masterplan, etc.)
- `TestCheckpoint`: Estado completo del test con todas sus fases
- `CheckpointManager`: CRUD operations para checkpoints

**Features:**
- Serialización JSON con metadata detallada
- Tracking de duración, intentos, errores por fase
- Estado granular: PENDING, IN_PROGRESS, COMPLETED, FAILED, SKIPPED
- Cleanup automático en éxito

### `retry_handler.py`
Implementa retry logic con exponential backoff para errores transitorios.

**Clases principales:**
- `RetryConfig`: Configuración de retries (max_retries, delays, exponential_base)
- `PhaseRetryHandler`: Ejecutor con retry automático

**Features:**
- Exponential backoff: `delay = initial * (base ^ attempt)`
- Jitter aleatorio para evitar thundering herd
- Errores retryables: ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError
- Logging detallado de intentos y delays

### `test_mge_v2_complete_pipeline.py`
Test E2E modificado con soporte completo de checkpoint/recovery.

**Cambios principales:**
- Fixtures: `checkpoint_manager`, `retry_handler`
- Wrapper: `execute_phase_with_checkpoint()` persiste estado automáticamente
- Recovery: Detecta checkpoint existente y resume desde fase fallida
- Fases separadas: `run_discovery()`, `run_masterplan_generation()`, `run_code_generation()`, etc.

## 🚀 Uso

### Ejecutar test con checkpoint
```bash
pytest tests/e2e/test_mge_v2_complete_pipeline.py::test_complete_mge_v2_pipeline_fastapi -v -s
```

### Comportamiento automático

**Primera ejecución:**
```
🚀 Starting MGE V2 E2E Test - FastAPI Project (with recovery)
💾 Created checkpoint: fastapi_pipeline_abc12345

▶️  Starting phase: discovery
✅ Phase discovery completed successfully

▶️  Starting phase: masterplan
✅ Phase masterplan completed successfully

▶️  Starting phase: code_generation
⚠️ Phase code_generation failed (attempt 1/4)
   Error: ConnectionResetError: [Errno 104] Connection reset by peer
⏳ Retrying in 5.0s with exponential backoff...
```

**Reanudar después de fallo:**
```
🚀 Starting MGE V2 E2E Test - FastAPI Project (with recovery)
♻️  Found existing checkpoint - resuming from last state

============================================================
📋 Checkpoint Status: MGE V2 FastAPI Pipeline
🆔 Test ID: fastapi_pipeline_abc12345
⏱️  Started: 2025-11-10T18:31:48
⏱️  Duration: 1023.4s
🔄 Total Retries: 1
============================================================

✅ discovery: completed - 36.2s
✅ masterplan: completed - 213.4s
❌ code_generation: failed (retry 2) - 450.1s
⏳ atomization: pending - N/A
⏳ wave_execution: pending - N/A
⏳ file_writing: pending - N/A
⏳ infrastructure: pending - N/A

▶️  Resuming from phase: code_generation

⏭️  Phase discovery already completed - skipping
⏭️  Phase masterplan already completed - skipping

▶️  Starting phase: code_generation (attempt 2)
✅ Phase code_generation completed successfully

▶️  Starting phase: atomization
...
```

## 📊 Estructura de Checkpoint

```json
{
  "test_name": "MGE V2 FastAPI Pipeline",
  "test_id": "fastapi_pipeline_abc12345",
  "started_at": "2025-11-10T18:31:48.123Z",
  "last_updated_at": "2025-11-10T18:48:52.456Z",
  "total_duration_seconds": 1024.3,
  "current_phase": "code_generation",
  "total_retries": 2,
  "user_request": "Create a FastAPI REST API...",
  "phases": {
    "discovery": {
      "phase_name": "discovery",
      "status": "completed",
      "started_at": "2025-11-10T18:31:48.200Z",
      "completed_at": "2025-11-10T18:32:24.350Z",
      "duration_seconds": 36.15,
      "retry_count": 1,
      "discovery_id": "550e8400-e29b-41d4-a716-446655440000",
      "domain": "Task Management System",
      "bounded_contexts_count": 3,
      "aggregates_count": 4,
      "entities_count": 8,
      "error": null
    },
    "masterplan": {
      "phase_name": "masterplan",
      "status": "completed",
      "started_at": "2025-11-10T18:32:24.400Z",
      "completed_at": "2025-11-10T18:35:57.800Z",
      "duration_seconds": 213.4,
      "retry_count": 1,
      "masterplan_id": "660e8400-e29b-41d4-a716-446655440001",
      "project_name": "task_management_api",
      "total_phases": 5,
      "total_milestones": 12,
      "generated_tasks_count": 33,
      "error": null
    },
    "code_generation": {
      "phase_name": "code_generation",
      "status": "failed",
      "started_at": "2025-11-10T18:35:58.000Z",
      "completed_at": "2025-11-10T18:48:28.100Z",
      "duration_seconds": 750.1,
      "retry_count": 2,
      "generated_code_count": 33,
      "total_code_lines": 4521,
      "total_cost_usd": 0.62,
      "error": "ConnectionResetError: [Errno 104] Connection reset by peer"
    },
    "atomization": {
      "phase_name": "atomization",
      "status": "pending",
      "started_at": null,
      "completed_at": null,
      "duration_seconds": null,
      "retry_count": 0,
      "error": null
    }
    // ... más fases
  }
}
```

## ⚙️ Configuración

### Retry Configuration
```python
config = RetryConfig(
    max_retries=3,           # Máximo 3 reintentos (4 intentos totales)
    initial_delay=5.0,       # Primer reintento después de 5s
    max_delay=120.0,         # Delay máximo de 2 minutos
    exponential_base=2.0,    # Duplica el delay cada intento
    jitter=True              # ±10% jitter aleatorio
)
```

**Progresión de delays:**
- Intento 1: Falla inmediatamente
- Intento 2: Espera 5s (5.0 * 2^0 = 5s)
- Intento 3: Espera 10s (5.0 * 2^1 = 10s)
- Intento 4: Espera 20s (5.0 * 2^2 = 20s)

### Checkpoint Locations
- **Directorio:** `/tests/e2e/checkpoints/`
- **Formato:** `checkpoint_{test_id}.json`
- **Ejemplo:** `checkpoint_fastapi_pipeline_abc12345.json`

## 🧹 Cleanup

### Automático
Cuando el test completa exitosamente, el checkpoint se elimina automáticamente:
```python
checkpoint_manager.cleanup_checkpoint(test_id)
```

### Manual
Para limpiar checkpoints manualmente:
```bash
# Limpiar todos los checkpoints
rm -rf tests/e2e/checkpoints/*

# Limpiar checkpoint específico
rm tests/e2e/checkpoints/checkpoint_fastapi_pipeline_*.json
```

## 📈 Beneficios

### Antes (sin checkpoint)
- ❌ Fallo en minuto 17 = pierde 17 minutos + $0.62
- ❌ Rerun completo desde cero
- ❌ Misma probabilidad de fallo en mismo punto
- ❌ Testing lento e impredecible

### Después (con checkpoint)
- ✅ Fallo en minuto 17 = recupera progreso en segundos
- ✅ Resume desde fase fallida
- ✅ Retry con backoff exponencial
- ✅ Testing resiliente y predecible
- ✅ Ahorro de tiempo y costo

## 🔍 Debugging

### Ver checkpoint actual
```bash
cat tests/e2e/checkpoints/checkpoint_fastapi_pipeline_*.json | jq
```

### Forzar cleanup
```python
# En pytest o Python REPL
from tests.e2e.checkpoint_manager import CheckpointManager

manager = CheckpointManager()
manager.cleanup_checkpoint("fastapi_pipeline_abc12345")
```

### Inspeccionar estado
```python
from tests.e2e.checkpoint_manager import CheckpointManager

manager = CheckpointManager()
checkpoint = manager.load_checkpoint("fastapi_pipeline_abc12345")

if checkpoint:
    manager.print_checkpoint_status(checkpoint)

    # Ver fase específica
    discovery = checkpoint.phases['discovery']
    print(f"Discovery status: {discovery.status}")
    print(f"Discovery ID: {discovery.discovery_id}")
```

## 🎯 Casos de Uso

### 1. Desarrollo de nuevas fases
Cuando agregas una nueva fase al pipeline, el checkpoint te permite:
- Ejecutar solo la nueva fase (skipea las anteriores)
- Iterar rápidamente sin regenerar todo
- Validar integración con fases anteriores

### 2. Debugging de fases específicas
Para debuggear una fase:
1. Ejecutar test hasta que falle
2. Checkpoint guarda progreso
3. Modificar código de la fase
4. Rerun test - solo ejecuta la fase modificada

### 3. CI/CD resilience
En CI/CD con límites de tiempo:
- Test puede fallar por timeout
- Próxima ejecución resume desde checkpoint
- Eventualmente completa todas las fases

### 4. Testing costoso
Para tests que cuestan mucho en LLM:
- No repite fases ya completadas
- Ahorra dinero en reruns
- Permite testing más frecuente

## ⚠️ Limitaciones

- Checkpoints son específicos del test ID (basado en session_id)
- No persiste objetos de base de datos (solo IDs)
- Requiere que fases sean idempotentes o skippables
- Checkpoint files pueden acumularse si no hay cleanup
- No funciona cross-sesión si test_user_id o test_session_id cambian

## 🚀 Futuras Mejoras

1. **Checkpoint compression**: Gzip de checkpoints grandes
2. **TTL automático**: Limpiar checkpoints después de N días
3. **Dashboard**: UI para ver estado de checkpoints
4. **Cloud storage**: Guardar checkpoints en S3/GCS para compartir entre runners
5. **Parallel phase execution**: Ejecutar fases independientes en paralelo
6. **Smart resume**: Detectar si código cambió y invalidar checkpoints afectados

## 📝 Contribuir

Para agregar soporte de checkpoint a nuevas fases:

1. Definir función `run_nueva_fase()` que retorna dict con datos relevantes
2. Llamar `execute_phase_with_checkpoint("nueva_fase", run_nueva_fase)`
3. Agregar "nueva_fase" a lista de fases en checkpoint creation
4. Los datos retornados se guardan automáticamente en checkpoint

Ejemplo:
```python
async def run_nueva_fase():
    """Execute nueva fase."""
    # ... lógica de ejecución ...

    return {
        'resultado_id': str(uuid.uuid4()),
        'items_procesados': 42,
        'costo_usd': 1.23
    }

result = await execute_phase_with_checkpoint(
    "nueva_fase",
    run_nueva_fase
)
```

El checkpoint guardará automáticamente todos los campos retornados en `PhaseCheckpoint`.
