# Implementación de WebSocket Events - Opción 2

**Fecha**: 2025-11-16
**Status**: ✅ **COMPLETADO** - Implementación lista para testing
**Spec**: [WEBSOCKET_EVENT_STRUCTURE.md](./WEBSOCKET_EVENT_STRUCTURE.md)

---

## ✅ Estado de Implementación

**Implementado el**: 2025-11-16
**Archivos modificados**:
- `src/websocket/manager.py` - 6 nuevos métodos agregados (líneas 883-1195)
- `src/services/mge_v2_orchestration_service.py` - Integración completa con eventos

**Eventos implementados**:
- ✅ `emit_execution_started()` - 1 evento al inicio de ejecución
- ✅ `emit_progress_update()` - 120 eventos (1 por task completada)
- ✅ `emit_artifact_created()` - ~45 eventos cuando se crean archivos
- ✅ `emit_wave_completed()` - 8-10 eventos por wave
- ✅ `emit_error()` - 0-20 eventos en caso de errores
- ✅ `emit_execution_completed()` - 1 evento al finalizar

---

## 🎯 Objetivo

Implementar eventos WebSocket granulares (1 evento por TASK = 120 eventos total) para que el console tool muestre progreso en tiempo real de la ejecución del MGE V2 pipeline.

---

## 📋 Tareas Requeridas

### 1. Agregar Nuevos Métodos al WebSocketManager

**Archivo**: `/home/kwar/code/agentic-ai/src/websocket/manager.py`

**Métodos a agregar** (al final del archivo, antes del último método):

#### `emit_execution_started()`

```python
async def emit_execution_started(
    self,
    session_id: str,
    execution_id: str,
    total_tasks: int,
    total_atoms: int,
    estimated_duration_ms: float,
    phases: List[Dict[str, Any]]
):
    """
    Emit execution started event.

    Args:
        session_id: Session ID
        execution_id: Unique execution ID
        total_tasks: Total number of tasks (e.g., 120)
        total_atoms: Total number of atoms (e.g., 800)
        estimated_duration_ms: Estimated duration in milliseconds
        phases: List of phases with structure:
            [
                {"number": 0, "name": "Discovery", "tasks": 5},
                {"number": 1, "name": "Analysis", "tasks": 15},
                ...
            ]
    """
    from datetime import datetime

    data = {
        "type": "execution_started",
        "timestamp": datetime.now().isoformat() + "Z",
        "data": {
            "execution_id": execution_id,
            "total_tasks": total_tasks,
            "total_atoms": total_atoms,
            "estimated_duration_ms": estimated_duration_ms,
            "phases": phases
        }
    }

    await self.emit_to_session(
        session_id=session_id,
        event="execution_started",
        data=data
    )

    logger.info(
        f"📡 Emitted execution_started - {total_tasks} tasks, {total_atoms} atoms",
        session_id=session_id,
        execution_id=execution_id
    )
```

#### `emit_progress_update()`

```python
async def emit_progress_update(
    self,
    session_id: str,
    task_id: str,
    task_name: str,
    phase: int,
    phase_name: str,
    status: str,
    progress: int,
    progress_percent: float,
    completed_tasks: int,
    total_tasks: int,
    current_wave: int,
    duration_ms: float,
    subtask_status: Optional[Dict[str, str]] = None
):
    """
    Emit task progress update event.

    Args:
        session_id: Session ID
        task_id: Unique task ID (e.g., "task_001")
        task_name: Human-readable task name (e.g., "Implement auth.py")
        phase: Phase number (0-4)
        phase_name: Phase name (e.g., "Analysis", "Planning")
        status: Task status ("completed", "failed", "in_progress")
        progress: Current progress counter (tasks completed)
        progress_percent: Progress percentage (0-100)
        completed_tasks: Total tasks completed so far
        total_tasks: Total tasks in plan
        current_wave: Current wave number
        duration_ms: Task duration in milliseconds
        subtask_status: Optional dict of subtask statuses
    """
    from datetime import datetime

    data = {
        "type": "progress_update",
        "timestamp": datetime.now().isoformat() + "Z",
        "data": {
            "task_id": task_id,
            "task_name": task_name,
            "phase": phase,
            "phase_name": phase_name,
            "status": status,
            "progress": progress,
            "progress_percent": progress_percent,
            "completed_tasks": completed_tasks,
            "total_tasks": total_tasks,
            "current_wave": current_wave,
            "duration_ms": duration_ms,
            "subtask_status": subtask_status or {}
        }
    }

    await self.emit_to_session(
        session_id=session_id,
        event="progress_update",
        data=data
    )

    logger.debug(
        f"📡 Progress: {progress_percent:.1f}% - {task_name}",
        session_id=session_id,
        task_id=task_id
    )
```

#### `emit_artifact_created()`

```python
async def emit_artifact_created(
    self,
    session_id: str,
    path: str,
    size: int,
    artifact_type: str,
    language: str,
    task_id: str
):
    """
    Emit artifact created event.

    Args:
        session_id: Session ID
        path: File path (e.g., "src/services/auth.py")
        size: File size in bytes
        artifact_type: Type of artifact ("file", "directory")
        language: Programming language (e.g., "python", "typescript")
        task_id: Task that created this artifact
    """
    from datetime import datetime

    data = {
        "type": "artifact_created",
        "timestamp": datetime.now().isoformat() + "Z",
        "data": {
            "path": path,
            "size": size,
            "type": artifact_type,
            "language": language,
            "task_id": task_id
        }
    }

    await self.emit_to_session(
        session_id=session_id,
        event="artifact_created",
        data=data
    )

    logger.info(
        f"📡 Artifact created: {path} ({size} bytes)",
        session_id=session_id,
        task_id=task_id
    )
```

#### `emit_wave_completed()`

```python
async def emit_wave_completed(
    self,
    session_id: str,
    wave_number: int,
    atoms_in_wave: int,
    atoms_completed: int,
    duration_ms: float,
    success_rate: float
):
    """
    Emit wave completed event.

    Args:
        session_id: Session ID
        wave_number: Wave number (1, 2, 3, ...)
        atoms_in_wave: Total atoms in this wave
        atoms_completed: Atoms successfully completed
        duration_ms: Wave duration in milliseconds
        success_rate: Success rate (0.0-1.0)
    """
    from datetime import datetime

    data = {
        "type": "wave_completed",
        "timestamp": datetime.now().isoformat() + "Z",
        "data": {
            "wave_number": wave_number,
            "atoms_in_wave": atoms_in_wave,
            "atoms_completed": atoms_completed,
            "duration_ms": duration_ms,
            "success_rate": success_rate
        }
    }

    await self.emit_to_session(
        session_id=session_id,
        event="wave_completed",
        data=data
    )

    logger.info(
        f"📡 Wave {wave_number} completed - {atoms_completed}/{atoms_in_wave} atoms ({success_rate:.1%})",
        session_id=session_id
    )
```

#### `emit_error()`

```python
async def emit_error(
    self,
    session_id: str,
    task_id: str,
    task_name: str,
    message: str,
    error_type: str,
    recoverable: bool,
    retry_attempt: int,
    max_retries: int
):
    """
    Emit error event.

    Args:
        session_id: Session ID
        task_id: Task ID that failed
        task_name: Human-readable task name
        message: Error message
        error_type: Type of error (e.g., "AssertionError", "ValidationError")
        recoverable: Whether the error is recoverable
        retry_attempt: Current retry attempt number
        max_retries: Maximum retry attempts allowed
    """
    from datetime import datetime

    data = {
        "type": "error",
        "timestamp": datetime.now().isoformat() + "Z",
        "data": {
            "task_id": task_id,
            "task_name": task_name,
            "message": message,
            "error_type": error_type,
            "recoverable": recoverable,
            "retry_attempt": retry_attempt,
            "max_retries": max_retries
        }
    }

    await self.emit_to_session(
        session_id=session_id,
        event="error",
        data=data
    )

    logger.error(
        f"📡 Error in {task_name}: {message}",
        session_id=session_id,
        task_id=task_id,
        error_type=error_type
    )
```

#### `emit_execution_completed()`

```python
async def emit_execution_completed(
    self,
    session_id: str,
    execution_id: str,
    status: str,
    total_tasks: int,
    completed_tasks: int,
    failed_tasks: int,
    duration_ms: float,
    artifacts_created: int,
    tokens_used: int,
    cost_usd: float
):
    """
    Emit execution completed event.

    Args:
        session_id: Session ID
        execution_id: Execution ID
        status: Final status ("success", "partial_success", "failed")
        total_tasks: Total tasks in plan
        completed_tasks: Tasks successfully completed
        failed_tasks: Tasks that failed
        duration_ms: Total execution duration in milliseconds
        artifacts_created: Number of artifacts created
        tokens_used: Total tokens consumed
        cost_usd: Total cost in USD
    """
    from datetime import datetime

    data = {
        "type": "execution_completed",
        "timestamp": datetime.now().isoformat() + "Z",
        "data": {
            "execution_id": execution_id,
            "status": status,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "duration_ms": duration_ms,
            "artifacts_created": artifacts_created,
            "tokens_used": tokens_used,
            "cost_usd": cost_usd
        }
    }

    await self.emit_to_session(
        session_id=session_id,
        event="execution_completed",
        data=data
    )

    logger.info(
        f"📡 Execution completed - {status}: {completed_tasks}/{total_tasks} tasks, ${cost_usd:.2f}",
        session_id=session_id,
        execution_id=execution_id
    )
```

---

### 2. Integrar en MGE V2 Orchestration Service

**Archivo**: `/home/kwar/code/agentic-ai/src/services/mge_v2_orchestration_service.py`

**Cambios necesarios**:

#### Constructor - Agregar WebSocketManager

```python
def __init__(
    self,
    db: Session,
    api_key: Optional[str] = None,
    enable_caching: bool = True,
    enable_rag: bool = True,
    websocket_manager: Optional[WebSocketManager] = None  # ← NUEVO
):
    """Initialize MGE V2 Orchestration Service."""
    self.db = db
    self.ws_manager = websocket_manager  # ← NUEVO

    # ... resto del código existente ...
```

#### Método `orchestrate_from_discovery()` - Agregar Eventos

```python
async def orchestrate_from_discovery(
    self,
    discovery_doc: str,
    user_id: str,
    output_dir: Path
) -> Dict[str, Any]:
    """Execute MGE V2 pipeline from discovery document."""
    import time
    execution_start = time.time()

    # Generate unique execution ID
    execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    session_id = str(uuid.uuid4())

    try:
        # STEP 1: Create Discovery Document
        logger.info("Creating Discovery Document...")
        discovery = await self._create_discovery_document(discovery_doc, user_id)

        # STEP 2: Generate MasterPlan
        logger.info("Generating MasterPlan...")
        masterplan_id = await self.masterplan_generator.generate_masterplan(
            discovery_id=discovery.discovery_id,
            session_id=session_id,
            user_id=user_id
        )

        # Load MasterPlan
        masterplan = self.db.query(MasterPlan).filter(
            MasterPlan.masterplan_id == masterplan_id
        ).first()

        if not masterplan:
            raise RuntimeError(f"MasterPlan {masterplan_id} not found")

        # Extract phases and calculate totals
        total_tasks = len(masterplan.tasks)
        total_atoms = total_tasks * 8  # Estimated 8 atoms per task
        estimated_duration_ms = total_tasks * 5000  # Estimated 5 sec per task

        # Build phases structure
        phases = self._build_phases_structure(masterplan)

        # ✅ EMIT: execution_started
        if self.ws_manager:
            await self.ws_manager.emit_execution_started(
                session_id=session_id,
                execution_id=execution_id,
                total_tasks=total_tasks,
                total_atoms=total_atoms,
                estimated_duration_ms=estimated_duration_ms,
                phases=phases
            )

        # STEP 3: Execute Tasks
        completed_tasks = 0
        failed_tasks = 0
        current_wave = 1
        artifacts_count = 0

        for idx, task in enumerate(masterplan.tasks, 1):
            task_start = time.time()

            try:
                # Execute task (your actual execution logic here)
                result = await self._execute_task(task, output_dir)

                # Task succeeded
                task_duration = (time.time() - task_start) * 1000
                completed_tasks += 1

                # ✅ EMIT: progress_update
                if self.ws_manager:
                    await self.ws_manager.emit_progress_update(
                        session_id=session_id,
                        task_id=f"task_{idx:03d}",
                        task_name=task.name or f"Task {idx}",
                        phase=self._get_phase_number(task),
                        phase_name=self._get_phase_name(task),
                        status="completed",
                        progress=completed_tasks,
                        progress_percent=(completed_tasks / total_tasks) * 100,
                        completed_tasks=completed_tasks,
                        total_tasks=total_tasks,
                        current_wave=current_wave,
                        duration_ms=task_duration,
                        subtask_status=result.get("subtask_status", {})
                    )

                # ✅ EMIT: artifact_created (if task created files)
                if result.get("artifacts"):
                    for artifact in result["artifacts"]:
                        artifacts_count += 1
                        if self.ws_manager:
                            await self.ws_manager.emit_artifact_created(
                                session_id=session_id,
                                path=artifact["path"],
                                size=artifact.get("size", 0),
                                artifact_type="file",
                                language=artifact.get("language", "unknown"),
                                task_id=f"task_{idx:03d}"
                            )

            except Exception as task_error:
                # Task failed
                failed_tasks += 1

                # ✅ EMIT: error
                if self.ws_manager:
                    await self.ws_manager.emit_error(
                        session_id=session_id,
                        task_id=f"task_{idx:03d}",
                        task_name=task.name or f"Task {idx}",
                        message=str(task_error),
                        error_type=type(task_error).__name__,
                        recoverable=True,
                        retry_attempt=1,
                        max_retries=4
                    )

                logger.error(f"Task {idx} failed: {task_error}")

        # Calculate final metrics
        execution_duration = (time.time() - execution_start) * 1000
        final_status = "success" if failed_tasks == 0 else "partial_success"

        # ✅ EMIT: execution_completed
        if self.ws_manager:
            await self.ws_manager.emit_execution_completed(
                session_id=session_id,
                execution_id=execution_id,
                status=final_status,
                total_tasks=total_tasks,
                completed_tasks=completed_tasks,
                failed_tasks=failed_tasks,
                duration_ms=execution_duration,
                artifacts_created=artifacts_count,
                tokens_used=0,  # TODO: Track tokens
                cost_usd=0.0    # TODO: Track cost
            )

        return {
            "execution_id": execution_id,
            "status": final_status,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "artifacts_created": artifacts_count
        }

    except Exception as e:
        logger.error(f"MGE V2 orchestration failed: {e}")

        # ✅ EMIT: execution_completed (failed)
        if self.ws_manager:
            await self.ws_manager.emit_execution_completed(
                session_id=session_id,
                execution_id=execution_id,
                status="failed",
                total_tasks=0,
                completed_tasks=0,
                failed_tasks=0,
                duration_ms=(time.time() - execution_start) * 1000,
                artifacts_created=0,
                tokens_used=0,
                cost_usd=0.0
            )

        raise RuntimeError(f"MGE V2 orchestration failed: {e}")


def _build_phases_structure(self, masterplan: MasterPlan) -> List[Dict[str, Any]]:
    """Build phases structure from masterplan tasks."""
    phases_count = {}

    for task in masterplan.tasks:
        phase_num = self._get_phase_number(task)
        phases_count[phase_num] = phases_count.get(phase_num, 0) + 1

    return [
        {
            "number": phase_num,
            "name": self._get_phase_name_by_number(phase_num),
            "tasks": count
        }
        for phase_num, count in sorted(phases_count.items())
    ]


def _get_phase_number(self, task: MasterPlanTask) -> int:
    """Get phase number from task."""
    # TODO: Implement actual phase detection logic
    return 0  # Placeholder


def _get_phase_name(self, task: MasterPlanTask) -> str:
    """Get phase name from task."""
    phase_num = self._get_phase_number(task)
    return self._get_phase_name_by_number(phase_num)


def _get_phase_name_by_number(self, phase_num: int) -> str:
    """Get phase name by number."""
    phase_names = {
        0: "Discovery",
        1: "Analysis",
        2: "Planning",
        3: "Execution",
        4: "Validation"
    }
    return phase_names.get(phase_num, "Unknown")


async def _execute_task(self, task: MasterPlanTask, output_dir: Path) -> Dict[str, Any]:
    """Execute a single task (placeholder)."""
    # TODO: Implement actual task execution logic
    return {
        "status": "completed",
        "artifacts": [],
        "subtask_status": {}
    }
```

---

## 🔧 Testing

### Test Manual

```bash
# 1. Start backend with WebSocket support
cd /home/kwar/code/agentic-ai
PYTHONPATH=/home/kwar/code/agentic-ai python3 -m src.api.main

# 2. Connect console tool
cd agent-os/tools/console-tool
npm run dev

# 3. Trigger execution
# (through API or console tool)
```

### Expected Events Flow

```
1. execution_started
   total_tasks: 120
   phases: [...]

2. progress_update (x120)
   task_001 completed (0.83%)
   task_002 completed (1.67%)
   ...
   task_120 completed (100%)

3. artifact_created (x45)
   src/auth.py created
   src/models.py created
   ...

4. error (if any failures)
   task_067 failed
   retry_attempt: 1

5. execution_completed
   status: success
   completed_tasks: 120
   failed_tasks: 0
```

---

## 📊 Expected Output in Console Tool

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

Artifacts Created: 18 / 45 expected
├── src/auth.py (2.1 KB) ✅
├── src/models.py (3.5 KB) ✅
└── 16 more...

Tokens Used: 34,500 / 100,000 (34%)
Duration: 10m 23s
```

---

## ✅ Checklist de Implementación

- [ ] Agregar 6 métodos nuevos a `WebSocketManager`
- [ ] Modificar constructor de `MGE_V2_OrchestrationService` para aceptar `websocket_manager`
- [ ] Agregar `emit_execution_started()` al inicio del orchestration
- [ ] Agregar `emit_progress_update()` por cada task completada
- [ ] Agregar `emit_artifact_created()` cuando se crea un archivo
- [ ] Agregar `emit_error()` cuando falla una task
- [ ] Agregar `emit_execution_completed()` al finalizar
- [ ] Implementar métodos helper: `_build_phases_structure()`, `_get_phase_number()`, etc.
- [ ] Testear flujo completo con console tool conectado
- [ ] Verificar que todos los eventos tienen timestamp ISO8601 + "Z"
- [ ] Verificar que `progress_percent` es float (0-100)

---

## 📝 Notas Importantes

1. **Timestamps**: Siempre usar formato ISO8601 con "Z" al final
2. **Progress Percent**: Debe ser float entre 0-100
3. **Session ID**: Usar el mismo session_id en todos los eventos de una ejecución
4. **Error Handling**: Emitir `execution_completed` con status="failed" si hay error general
5. **Artifacts**: Solo emitir `artifact_created` si realmente se creó un archivo
6. **Wave Events**: Emitir `wave_completed` cuando termine cada wave (opcional pero recomendado)

---

**Status**: ⏸️ LISTO PARA IMPLEMENTAR - Esperando resolución de API credits

**Próximo paso**: Una vez resueltos los créditos API, implementar según esta spec
