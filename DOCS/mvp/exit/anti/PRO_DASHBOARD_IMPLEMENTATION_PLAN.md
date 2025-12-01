# DevMatrix Pro Dashboard – Implementation Plan

**Owner:** Platform/Console
**Status:** Draft → **REVISED**
**Version:** 2.0 (File-based architecture - zero flickering)
**Scope:** Reemplazar los dashboards ad-hoc (CLI roto + stubs en `tests/e2e/`) por un dashboard profesional basado en **archivo + tail**, eliminando el problema de flickering.

---

## 🔴 Diagnóstico: Por qué el Plan v1.1 No Funciona

| Problema | Evidencia | Impacto |
|----------|-----------|---------|
| **Rich Live deshabilitado** | `RICH_PROGRESS = False` en pipeline | Dashboard nunca se usa |
| **Flickering no resuelto** | "Rich Live display conflicts with print()" | UX inutilizable |
| **CLI roto** | `ModuleNotFoundError: src.cli.approval_manager` | No se puede probar |
| **Pipeline usa stubs** | `def update_metrics(**kwargs): pass` | Métricas perdidas |
| **WebSocket no existe** | Plan asume WS, no hay implementación | Arquitectura fantasma |
| **APIs faltantes** | No existe `update_learning_stats()` ni `update_repair_status()` | Features no implementables |

### Root Cause
El plan v1.1 asumía que Rich Live y prints pueden coexistir. **No pueden**. El pipeline hace ~500 prints durante ejecución, Rich Live los sobrescribe → flickering.

---

## ✅ Nuevo Approach: File-Based Dashboard (Opción C)

### Arquitectura

```
┌─────────────────────┐         ┌──────────────────────┐
│  Pipeline (E2E)     │         │  Dashboard Viewer    │
│                     │         │  (Terminal 2)        │
│  - Fases normales   │         │                      │
│  - Prints normales  │  JSON   │  tail -f + jq/rich   │
│  - dashboard.write()├────────►│  OR                  │
│                     │  file   │  watch + rich format │
└─────────────────────┘         └──────────────────────┘
        │                                  │
        ▼                                  ▼
   dashboard.jsonl                 Real-time display
   (append-only)                   (zero flickering)
```

### Ventajas

| Beneficio | Descripción |
|-----------|-------------|
| **Zero flickering** | Pipeline y viewer son procesos separados |
| **Sin refactor masivo** | Pipeline sigue haciendo prints normales |
| **Decoupled** | Dashboard es un viewer opcional |
| **CI compatible** | Sin viewer, el archivo se puede analizar post-run |
| **Debuggable** | `cat dashboard.jsonl` muestra todo el histórico |

---

## Objetivos (Revisados)

- **UX desacoplada:** Dashboard viewer en terminal separado, pipeline sin cambios de prints.
- **Signal completo:** Progreso por fase, métricas clave, salud de infra, learning metrics.
- **Zero flickering:** Arquitectura file-based elimina conflictos Rich vs print.
- **Baja fricción:** Un solo archivo JSON Lines, viewer simple con Rich.
- **CI compatible:** Sin viewer, archivo analizable post-mortem.

## No Objetivos
- ~~WebSocket~~ (eliminado - innecesario para E2E local)
- UI web nueva
- Modificar prints existentes del pipeline

---

## Requerimientos Funcionales (v2.0)

### Writer (Pipeline Side)

1. **DashboardWriter** - Clase simple que escribe a `dashboard.jsonl`:
   - `write_phase(name, status, progress, duration_ms)`
   - `write_metrics(tests_passed, tests_failed, ir_compliance, llm_tokens, llm_cost)`
   - `write_infra(docker, neo4j, qdrant, redis)`
   - `write_learning(fix_patterns, anti_patterns, reuse_rate)`
   - `write_repair(iteration, max_iter, pass_rate, status)`
   - `write_log(level, message)`

2. **Formato JSON Lines** (append-only):

```json
{"ts": "2024-01-15T10:30:00", "type": "phase", "name": "Code Generation", "status": "running", "progress": 0.45}
{"ts": "2024-01-15T10:30:01", "type": "metrics", "tests_passed": 45, "tests_failed": 2, "ir_compliance": 0.98}
{"ts": "2024-01-15T10:30:02", "type": "repair", "iteration": 2, "max": 3, "pass_rate": 0.85, "status": "ACTIVE"}
{"ts": "2024-01-15T10:30:03", "type": "log", "level": "info", "message": "Generated 12 files"}
```

### Viewer (Separate Terminal)

3. **DashboardViewer** - Rich-based viewer que lee el archivo:
   - `tail -f` del archivo con parsing
   - Layout Rich similar al existente
   - Refresh cada 500ms
   - Estado calculado desde últimos eventos

4. **CLI Command**:

```bash
# Terminal 1: Run pipeline
python -m tests.e2e.real_e2e_full_pipeline specs/inventory.md

# Terminal 2: Watch dashboard
python -m src.console.dashboard_viewer --file logs/runs/current/dashboard.jsonl
```

## Requerimientos No Funcionales (v2.0)

- **Zero flickering:** Procesos separados, sin conflicto Rich/print
- **Append-only:** Archivo solo crece, no se reescribe
- **JSON Lines:** Una línea = un evento, fácil de parsear
- **Backwards compatible:** Pipeline funciona sin viewer

---

## Diseño / Arquitectura (v2.0)

### Componentes

| Componente | Ubicación | Responsabilidad |
|------------|-----------|-----------------|
| `DashboardWriter` | `src/console/dashboard_writer.py` | Escribe eventos a JSONL |
| `DashboardViewer` | `src/console/dashboard_viewer.py` | Lee JSONL y renderiza con Rich |
| `dashboard.jsonl` | `logs/runs/{run_id}/` | Archivo de eventos (append-only) |

### Flujo de Datos

```text
Pipeline                          Archivo                    Viewer
────────                          ───────                    ──────
start_phase("CodeGen")  ──────►  {"type":"phase"...}  ◄────  tail -f
update_metrics(...)     ──────►  {"type":"metrics"...}       parse JSON
write_log("info",...)   ──────►  {"type":"log"...}           render Rich
```

### Integración en Pipeline

```python
# tests/e2e/real_e2e_full_pipeline.py

from src.console.dashboard_writer import DashboardWriter

# Al inicio del pipeline
dashboard = DashboardWriter(f"logs/runs/{run_id}/dashboard.jsonl")

# En cada fase
dashboard.write_phase("Code Generation", "running", progress=0.0)
# ... código existente con prints normales ...
dashboard.write_phase("Code Generation", "completed", progress=1.0, duration_ms=12345)

# Métricas
dashboard.write_metrics(tests_passed=45, tests_failed=2, ir_compliance=0.98)
```

---

## Plan de Trabajo (v2.0)

| # | Task | Effort | Deps | Entregable |
|---|------|--------|------|------------|
| 1 | **DashboardWriter** | 2h | - | `src/console/dashboard_writer.py` |
| 2 | **DashboardViewer** | 4h | 1 | `src/console/dashboard_viewer.py` |
| 3 | **Integrar en pipeline** | 2h | 1 | Llamadas a `dashboard.write_*()` en E2E |
| 4 | **Learning metrics** | 1h | 1,3 | `write_learning()` desde singletons |
| 5 | **Repair loop visibility** | 1h | 1,3 | `write_repair()` desde repair loop |
| 6 | **CLI command** | 1h | 2 | `python -m src.console.dashboard_viewer` |
| 7 | **Docs** | 1h | all | README con uso |

**Total: ~12h** (vs ~40h del plan v1.1)

---

## Tabla de Seguimiento (v2.0)

| Workstream | Status | Priority | Effort | Notas |
|------------|--------|----------|--------|-------|
| DashboardWriter | 🔲 Todo | P0 | 2h | Archivo JSON Lines append-only |
| DashboardViewer | 🔲 Todo | P0 | 4h | Rich layout, tail -f parsing |
| Pipeline integration | 🔲 Todo | P0 | 2h | Llamadas en cada fase |
| Learning metrics | 🔲 Todo | P1 | 1h | Exponer desde singletons |
| Repair loop visibility | 🔲 Todo | P1 | 1h | Iteration/pass_rate/status |
| CLI command | 🔲 Todo | P2 | 1h | `--file` argument |
| Docs | 🔲 Todo | P3 | 1h | README + ejemplos |

Legend: ✅ Done | 🟡 In Progress | 🔲 Todo

---

## Riesgos y Mitigaciones (v2.0)

| Riesgo | Mitigación |
|--------|------------|
| **Archivo crece mucho** | Rotate per-run, cleanup después de 7 días |
| **Viewer no encuentra archivo** | Mensaje claro + path suggestion |
| **JSON malformado** | Try/except en cada línea, skip inválidas |
| **Latencia viewer** | Buffer de 100 líneas, refresh 500ms |

---

## API Payload Contracts (v2.0)

### Event Types

```python
# Phase event
{"ts": "...", "type": "phase", "name": str, "status": str, "progress": float, "duration_ms": int}

# Metrics event
{"ts": "...", "type": "metrics", "tests_passed": int, "tests_failed": int, "ir_compliance": float, "llm_tokens": int, "llm_cost": float}

# Infra event
{"ts": "...", "type": "infra", "docker": str, "neo4j": str, "qdrant": str, "redis": str}

# Learning event
{"ts": "...", "type": "learning", "fix_patterns": int, "anti_patterns": int, "reuse_rate": float, "prevention_rate": float}

# Repair event
{"ts": "...", "type": "repair", "iteration": int, "max": int, "pass_rate": float, "status": str, "skip_reason": str|null}

# Log event
{"ts": "...", "type": "log", "level": str, "message": str}
```

---

## Validación / DoD (v2.0)

- [ ] `python -m py_compile src/console/dashboard_writer.py` pasa
- [ ] `python -m py_compile src/console/dashboard_viewer.py` pasa
- [ ] Pipeline escribe a `dashboard.jsonl` durante E2E run
- [ ] Viewer muestra fases, métricas, logs en tiempo real
- [ ] Zero flickering en viewer
- [ ] Sin dependencias nuevas (solo Rich, ya instalado)
- [ ] Docs con ejemplo de uso

---

## Comparativa v1.1 vs v2.0

| Aspecto | v1.1 (Rich Live + WS) | v2.0 (File + Viewer) |
|---------|----------------------|----------------------|
| **Flickering** | ❌ No resuelto | ✅ Eliminado |
| **Complejidad** | Alta (WS, callbacks) | Baja (archivo) |
| **Effort** | ~40h | ~12h |
| **CI compatible** | ❌ Requiere terminal | ✅ Solo archivo |
| **Debugging** | Difícil | `cat dashboard.jsonl` |
| **Arquitectura** | Acoplada | Desacoplada |
