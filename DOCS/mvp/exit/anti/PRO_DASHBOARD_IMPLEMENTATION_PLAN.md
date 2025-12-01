# DevMatrix Pro Dashboard – Implementation Plan

**Owner:** Platform/Console
**Status:** Draft → **REVISED**
**Version:** 3.0 (Rich Live nativo con `live.console.print()`)
**Scope:** Dashboard profesional usando capacidades nativas de Rich 14.x

---

## 🔍 Descubrimiento Clave (Dic 2025)

**Rich ya resuelve el problema de flickering nativamente:**

```python
# Documentación oficial Rich 14.1.0:
# "If you print or log to this console, the output will be displayed
#  ABOVE the live display."

with Live(dashboard, refresh_per_second=4) as live:
    live.console.print("Este texto aparece ARRIBA del dashboard")  # ✅ Sin flickering
```

Además, Rich tiene `redirect_stdout=True` (default) que captura `print()` automáticamente.

---

## 🎨 UI Design: Dashboard Minimalista

### Principios de Diseño

| Principio | Aplicación |
|-----------|------------|
| **Focus on NOW** | La fase actual es el hero, el resto es contexto |
| **Progressive disclosure** | Solo mostrar detalle cuando hay problemas |
| **Meaningful animation** | Spinners solo en elementos activos |
| **Color = Signal** | Verde=OK, Amarillo=Warning, Rojo=Error, Azul=Running |

### Layout: 3 Zonas

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ZONA 1: HERO                                │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  ◐ Code Generation                              Phase 7/13    │  │
│  │  ████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  45%  2.3s │  │
│  │  Generating models/inventory.py...                            │  │
│  └───────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│                       ZONA 2: MÉTRICAS                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │ Tests       │ │ Compliance  │ │ LLM Cost    │ │ Repair      │   │
│  │ 45/47 ✓     │ │ 98.2%  ━━━━ │ │ $0.12       │ │ ○○○ SKIP    │   │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                        ZONA 3: LOGS                                 │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 10:30:02 ✓ Generated 12 files                                 │  │
│  │ 10:30:01 ✓ IR validated (98.2% compliance)                    │  │
│  │ 10:30:00   Starting code generation...                        │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📐 Componentes UI Detallados

### ZONA 1: Hero (Fase Actual)

```
┌─────────────────────────────────────────────────────────────────┐
│  ◐ Code Generation                                  Phase 7/13  │
│  ████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  45%  2.3s │
│  Generating models/inventory.py...                              │
└─────────────────────────────────────────────────────────────────┘
```

**Elementos:**
| Elemento | Tipo | Animación |
|----------|------|-----------|
| `◐` | Spinner | Rotación cada 100ms (solo si running) |
| Barra de progreso | ProgressBar | Smooth fill |
| `45%` | Texto | Update en cada cambio |
| `2.3s` | Timer | Tick cada segundo |
| Subtarea | Texto | Cambia con cada archivo |

**Estados del Spinner:**
- `◐ ◓ ◑ ◒` = Running (animado)
- `✓` = Completed (verde)
- `✗` = Failed (rojo)
- `⊘` = Skipped (gris)
- `⏳` = Pending (estático)

### ZONA 2: Métricas (4 Cards)

```
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Tests       │ │ Compliance  │ │ LLM         │ │ Repair      │
│ 45/47 ✓     │ │ 98.2%  ━━━━ │ │ $0.12  42K  │ │ ●○○ 1/3     │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

**Card 1: Tests**
```
Estado Normal:    45/47 ✓     (verde si 100%, amarillo si <100%, rojo si <80%)
Estado Failed:    43/47 ✗ 4   (rojo, muestra count de failures)
```

**Card 2: Compliance (IR)**
```
Barra visual:  ━━━━━━━━━━━━━━━━━━━━░░░░  98.2%
Colores:       Verde >=95%, Amarillo >=80%, Rojo <80%
```

**Card 3: LLM**
```
$0.12  42K tokens
Crece con cada llamada LLM
```

**Card 4: Repair Loop**
```
○○○  SKIP     (gris - no necesitó repair)
●○○  1/3      (azul - iteración 1)
●●○  2/3      (amarillo - iteración 2)
●●●  3/3      (rojo si aún falla, verde si pasó)
```

### ZONA 3: Logs (Últimos 5)

```
┌───────────────────────────────────────────────────────────────┐
│ 10:30:02 ✓ Generated 12 files                                 │
│ 10:30:01 ✓ IR validated (98.2% compliance)                    │
│ 10:30:00   Starting code generation...                        │
│ 10:29:58 ✓ DAG constructed (15 nodes, 23 edges)               │
│ 10:29:55 ✓ Atomization complete (8 atoms)                     │
└───────────────────────────────────────────────────────────────┘
```

**Formato de línea:**
```
{timestamp} {icon} {message}
```

**Iconos por nivel:**
- `✓` verde = success
- `⚠` amarillo = warning
- `✗` rojo = error
- ` ` (espacio) = info

---

## 🎬 Estados del Dashboard

### Estado: Running Normal

```
┌─────────────────────────────────────────────────────────────────┐
│  ◐ Code Generation                                  Phase 7/13  │
│  ████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  45%  2.3s │
│  Generating models/inventory.py...                              │
├─────────────────────────────────────────────────────────────────┤
│  Tests       │  Compliance  │  LLM         │  Repair            │
│  45/47 ✓     │  98.2%  ━━━━ │  $0.12  42K  │  ○○○ SKIP          │
├─────────────────────────────────────────────────────────────────┤
│ 10:30:02 ✓ Generated 12 files                                   │
│ 10:30:01 ✓ IR validated (98.2% compliance)                      │
└─────────────────────────────────────────────────────────────────┘
```

### Estado: Repair Loop Activo

```
┌─────────────────────────────────────────────────────────────────┐
│  ◐ Code Repair                                      Phase 9/13  │
│  ████████████████████████████████░░░░░░░░░░░░░░░░░░░  67%  8.1s │
│  Fixing test_inventory_crud.py (2 failures)                     │
├─────────────────────────────────────────────────────────────────┤
│  Tests       │  Compliance  │  LLM         │  Repair            │
│  43/47 ⚠     │  91.5%  ━━━░ │  $0.18  58K  │  ●●○ 2/3           │
├─────────────────────────────────────────────────────────────────┤
│ 10:31:15 ⚠ Repair iteration 2: 2 tests still failing           │
│ 10:31:10 ✓ Fixed: test_create_inventory                        │
│ 10:31:05 ✓ Fixed: test_list_inventory                          │
└─────────────────────────────────────────────────────────────────┘
```

### Estado: Error Crítico

```
┌─────────────────────────────────────────────────────────────────┐
│  ✗ Code Generation                                  Phase 7/13  │
│  ████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  45% FAILED│
│  ERROR: Docker container crashed                                │
├─────────────────────────────────────────────────────────────────┤
│  Tests       │  Compliance  │  LLM         │  Repair            │
│  --/--       │  --          │  $0.08  28K  │  ○○○ --            │
├─────────────────────────────────────────────────────────────────┤
│ 10:30:15 ✗ Docker container exited with code 137 (OOM)         │
│ 10:30:14   Attempting recovery...                               │
│ 10:30:02 ✓ Generated 8 files                                    │
└─────────────────────────────────────────────────────────────────┘
```

### Estado: Completado

```
┌─────────────────────────────────────────────────────────────────┐
│  ✓ Pipeline Complete                                    SUCCESS │
│  ████████████████████████████████████████████████████ 100% 45.2s│
│  All 13 phases completed successfully                           │
├─────────────────────────────────────────────────────────────────┤
│  Tests       │  Compliance  │  LLM         │  Repair            │
│  47/47 ✓     │  99.8%  ━━━━ │  $0.24  89K  │  ○○○ SKIP          │
├─────────────────────────────────────────────────────────────────┤
│ 10:31:45 ✓ Pipeline completed in 45.2s                          │
│ 10:31:44 ✓ Health verification passed                           │
│ 10:31:40 ✓ All smoke tests passed (47/47)                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Arquitectura Técnica (v3.0)

### Solución: Rich Live con `live.console.print()`

```python
from rich.live import Live
from rich.console import Console

console = Console()

with Live(dashboard.render(), console=console, refresh_per_second=4) as live:
    # Logs aparecen ARRIBA del dashboard automáticamente
    live.console.print("[green]✓[/] Starting code generation...")

    # Actualizar dashboard
    dashboard.update_phase("Code Generation", progress=0.45)
    live.update(dashboard.render())
```

### Componentes

| Componente | Archivo | Responsabilidad |
|------------|---------|-----------------|
| `DashboardState` | `src/console/dashboard_state.py` | Dataclass con estado actual |
| `DashboardRenderer` | `src/console/dashboard_renderer.py` | Genera Rich renderables |
| `DashboardManager` | `src/console/dashboard_manager.py` | Wrapper para Live + API |

### Flujo

```
Pipeline                    DashboardManager                Rich Live
────────                    ────────────────                ─────────
start_phase("CodeGen") ──►  state.current_phase = ...  ──►  live.update()
log("Generated file")  ──►  live.console.print(...)    ──►  Aparece arriba
update_metrics(...)    ──►  state.metrics = ...        ──►  live.update()
```

---

## 📦 API del Dashboard

```python
class DashboardManager:
    """API pública del dashboard."""

    def __enter__(self) -> "DashboardManager":
        """Inicia Rich Live."""

    def __exit__(self, *args):
        """Cierra Rich Live."""

    # === Fases ===
    def start_phase(self, name: str, total_steps: int = 1):
        """Marca fase como running."""

    def update_progress(self, current: int, message: str = ""):
        """Actualiza progreso de fase actual."""

    def complete_phase(self):
        """Marca fase actual como completada."""

    def fail_phase(self, error: str):
        """Marca fase actual como fallida."""

    # === Métricas ===
    def update_tests(self, passed: int, total: int):
        """Actualiza card de tests."""

    def update_compliance(self, percentage: float):
        """Actualiza card de compliance."""

    def update_llm(self, cost: float, tokens: int):
        """Actualiza card de LLM."""

    def update_repair(self, iteration: int, max_iter: int = 3, status: str = "running"):
        """Actualiza card de repair loop."""

    # === Logs ===
    def log(self, message: str, level: str = "info"):
        """Agrega log (aparece arriba del dashboard)."""

    def success(self, message: str):
        """Shortcut para log success."""

    def warning(self, message: str):
        """Shortcut para log warning."""

    def error(self, message: str):
        """Shortcut para log error."""
```

### Uso en Pipeline

```python
from src.console.dashboard_manager import DashboardManager

with DashboardManager() as dash:
    # Fase 1
    dash.start_phase("Spec Ingestion", total_steps=4)
    dash.log("Loading spec file...")
    dash.update_progress(1, "Parsing markdown...")
    dash.update_progress(2, "Extracting requirements...")
    dash.success("Spec loaded: 15 requirements found")
    dash.complete_phase()

    # Fase 7
    dash.start_phase("Code Generation", total_steps=12)
    for i, file in enumerate(files_to_generate):
        dash.update_progress(i + 1, f"Generating {file}...")
        generate_file(file)
        dash.update_llm(cost=0.02 * i, tokens=1500 * i)
    dash.complete_phase()

    # Tests
    dash.update_tests(passed=45, total=47)
    dash.update_compliance(98.2)

    # Repair (si necesario)
    dash.update_repair(iteration=1, status="running")
    # ...
    dash.update_repair(iteration=2, status="completed")
```

---

## 📋 Plan de Trabajo (v3.0)

| # | Task | Effort | Entregable | Status |
|---|------|--------|------------|--------|
| 1 | **DashboardState** | 1h | Dataclass con estado | ✅ DONE |
| 2 | **DashboardRenderer** | 3h | Genera Rich Layout | ✅ DONE |
| 3 | **DashboardManager** | 2h | Wrapper con API | ✅ DONE |
| 4 | **Integrar en pipeline** | 2h | Reemplazar prints | 🔮 DEFERRED |
| 5 | **Tests** | 1h | Unit tests básicos | 🔮 DEFERRED |
| 6 | **Docs** | 1h | README con ejemplos | 🔮 DEFERRED |

**Progress: 3/6 tasks complete (Core components ready)**

### Archivos Creados:
- `src/console/dashboard_state.py` - Dataclass con estado completo
- `src/console/dashboard_renderer.py` - Renderer con 3 zonas (Hero, Metrics, Logs)
- `src/console/dashboard_manager.py` - API pública con context manager

### Decisión (Dic 2025):
**Tasks 4-6 diferidos hasta refactor del pipeline.**
- El pipeline actual tiene ~41 prints dispersos
- Integración requiere refactor significativo
- Componentes core están listos para cuando se necesiten

**Total: ~10h (3h completadas, 7h diferidas)**

---

## ✅ Validación / DoD

- [ ] Dashboard renderiza correctamente en terminal 80x24
- [ ] Spinner animado en fase running
- [ ] Progress bar smooth
- [ ] Logs aparecen arriba sin flickering
- [ ] Colores correctos según estado
- [ ] Funciona con pipeline E2E real
- [ ] Sin dependencias nuevas

---

## 📊 Comparativa de Versiones

| Aspecto | v1.1 | v2.0 | v3.0 |
|---------|------|------|------|
| **Arquitectura** | Rich Live (roto) | File + Viewer | Rich Live (nativo) |
| **Flickering** | ❌ | ✅ | ✅ |
| **Procesos** | 1 | 2 | 1 |
| **Effort** | ~40h | ~12h | ~10h |
| **Animaciones** | ❌ | ❌ | ✅ |
| **UX** | Mala | OK | Excelente |
