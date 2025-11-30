# DevMatrix Pro Dashboard – Implementation Plan

**Owner:** Platform/Console
**Status:** Draft
**Version:** 1.1 (Enhanced with Learning System visibility)
**Scope:** Reemplazar los dashboards ad-hoc (CLI roto + `tests/e2e/progress_dashboard.py`) por un dashboard profesional y unificado para monitorear ejecución del pipeline, estado de infra, **learning system** y debugging en vivo.

---

## Objetivos
- **UX unificada:** Dashboard único invocado desde CLI y usable en runs locales/CI.
- **Signal completo:** Progreso por fase, métricas clave (tests, IR compliance, LLM tokens/costo), salud de infra (Docker, Neo4j, Qdrant, Redis), eventos de errores y artefactos generados.
- **Learning visibility:** Mostrar estado del sistema de aprendizaje (patterns cargados, anti-patterns inyectados, fixes reutilizados).
- **Repair loop tracking:** Visualizar iteraciones del repair loop, pass rate por iteration, y decisiones de skip/execute.
- **Baja fricción:** Sin flicker, sin dependencias rotas; API mínima para integrarse al pipeline y al websocket del CLI.
- **Observabilidad real:** Log tail y acciones sugeridas (approve, retry) visibles en tiempo real.
- **Compatibilidad:** Funciona offline (mock) y online (WS), sin requerir front-end adicional.

## No Objetivos
- UI web nueva (queda fuera de alcance).
- Persistencia histórica larga; solo buffer de la run actual.
- Control de infra (start/stop) vía CLI por ahora solo lectura de salud.

---

## Requerimientos Funcionales
1) **Progreso de fases**
   - Mapa de fases del pipeline (1-13) con estado (pending/running/completed/failed/skipped), % y tiempo.
   - Overall progress calculado y visible.
2) **Métricas en vivo**
   - Test pass rate, counts (pass/fail).
   - IR compliance y pipeline precision/pattern F1.
   - LLM tokens y costo estimado.
   - Artefactos generados y errores acumulados.
3) **Infra/servicios**
   - Estados: docker, neo4j, qdrant, redis (ok/degraded/offline + detalle).
4) **Learning System metrics** (NEW)
   - Patterns loaded from Neo4j (FixPatternLearner, NegativePatternStore, SmokeTestPatternAdapter).
   - Anti-patterns injected in prompts (count, top 3 tipos).
   - Fix patterns reused vs new (reutilización efectiva).
   - Prevention rate (errores evitados por warnings).
5) **Repair Loop visibility** (NEW)
   - Iteration actual (1/3, 2/3, 3/3).
   - Pass rate por iteration (muestra progreso: 65% → 80% → 95%).
   - Estado: ACTIVE / SKIPPED / CONVERGED / MAX_ITERATIONS.
   - Motivo de skip si aplica ("target reached", "no violations").
6) **Eventos y logs**
   - Buffer de últimos N eventos (nivel info/warn/error).
   - Mostrar timestamps y mensaje limpio para debugging rápido.
7) **Contexto en vivo**
   - Tarea actual y hints de acción (approve pendiente, revisar infra).
8) **Modos**
   - Online: alimentado por WebSocket del pipeline/CLI.
   - Offline/mock: simulación para demos/tests sin backend.  

## Requerimientos No Funcionales
- **Render estable:** sin flicker; usa Rich Layout con áreas fijas.
- **API chica:** `set_status`, `set_current_task`, `update_phase`, `update_metrics`, `update_infra_status`, `update_learning_stats`, `update_repair_status`, `add_log`, `update()`.  
- **Backwards safety:** si no hay WS, cae a mock/solo consola.  
- **ASCII only:** sin caracteres fuera de UTF-8 básico.  

---

## Diseño / Arquitectura
- **Fuente de datos:** eventos de pipeline (WS) y callbacks actuales del CLI (`src/console/cli.py`), más health checks opcionales desde pipeline.  
- **Componente central:** `src/console/live_dashboard.py` (Rich) — layout header / phases / context / metrics / infra / logs.  
- **Integración CLI:** `DevMatrixConsole` crea el dashboard y reenvía eventos `_on_pipeline_update`, `_on_phase_started`, `_on_phase_completed`, `_on_error`, `_on_artifact_created`, `_on_test_result`, `_on_approval_request`.  
- **Integración pipeline:** `tests/e2e/real_e2e_full_pipeline.py` publica métricas/health via WS; fallback a stdout si WS no está.  
- **Mock/Demo:** modo simulado desde CLI para validación manual y demos.  

---

## Plan de Trabajo
1) **Limpieza / Base (DONE parcial)**  
   - Crear nuevo `src/console/live_dashboard.py` con layout Rich y API mínima.  
   - Eliminar dependencias rotas (import inexistente).  
2) **Wiring CLI**  
   - Ajustar `src/console/cli.py` para usar la nueva API (phases dict → PhaseState).  
   - Manejar fase desconocida creando PhaseState on-the-fly.  
3) **Alimentar métricas reales**  
   - Mapear eventos WS a `update_metrics` (tests, compliance, llm_tokens/cost).  
   - Incluir contador de artefactos y errores.  
4) **Salud de infra**  
   - Definir payload WS/CLI para `docker/neo4j/qdrant/redis` con estado y detalle.  
   - Exponer hook en pipeline para enviar health snapshots (opcional, best-effort).  
5) **Eventos/log tail**  
   - Normalizar niveles (info/success/warning/error).  
   - Restringir a buffer de 30 eventos.  
6) **Mock / Offline**  
   - Añadir comando en CLI para correr modo demo (simulado) y validación rápida.  
7) **Docs y validación**  
   - Añadir guía de uso en `tests/e2e/DASHBOARD_USAGE.md` y CLI README.  
   - Smoke manual en local (mock + WS) y verificación de import en `py_compile`.  

---

## Tabla de Seguimiento
| Workstream | Owner | Status | Priority | Next Milestone | Notas |
|------------|-------|--------|----------|----------------|-------|
| Base dashboard Rich (`live_dashboard.py`) | Platform | ✅ Done | P0 | Merge wiring en CLI | Layout header/phases/metrics/infra/logs listo. |
| Wiring CLI → dashboard API | Platform | 🟡 In Progress | P0 | Ajustar callbacks y tipos PhaseState | Sustituir acceso dict por métodos. |
| **Learning System metrics** | Platform | 🔲 Todo | **P1** | Integrar con singletons arreglados | Bug #146-148 arreglados, exponer stats. |
| **Repair Loop visibility** | Platform | 🔲 Todo | **P1** | Mostrar iteration/pass_rate/status | Crítico para debugging repair issues. |
| Métricas (tests/compliance/LLM) | Platform | 🔲 Todo | P1 | Mapear payload WS a update_metrics | Requiere definir keys consistentes. |
| Infra health (docker/neo4j/qdrant/redis) | Platform | 🔲 Todo | P2 | Recibir snapshot y pintar status | Neo4j crítico para learning system. |
| Logs/event stream | Platform | 🔲 Todo | P2 | Normalizar niveles y trimming | Buffer 30 eventos; mostrar últimos 15. |
| Mock/offline mode | Platform | 🔲 Todo | P3 | Comando de demo en CLI | Reusar simulación o datos sintéticos. |
| Docs & QA | Platform | 🔲 Todo | P3 | Update DASHBOARD_USAGE + README | Incluir captura textual. |

Legend: ✅ Done | 🟡 In Progress | 🔲 Todo | **P0** = Blocker | **P1** = High | **P2** = Medium | **P3** = Low

---

## Riesgos y Mitigaciones
- **Eventos incompletos del pipeline:** Mitigar con defaults y modo offline; logs claros cuando faltan campos.
- **Flicker en terminales lentas:** Mantener layout fijo y refresco moderado (3–4 fps).
- **Desalineación de keys métricas:** Definir contrato WS (tests_passed, tests_failed, ir_compliance, llm_tokens, llm_cost).
- **Infra health no disponible:** Mostrar `unknown` sin romper render; agregar toggle para ocultar.
- **Neo4j no disponible:** Learning metrics muestran "offline" pero no crashean; system sigue sin learning.
- **Repair Loop skipped silently:** Dashboard muestra claramente cuando se skipea y por qué.

---

## API Payload Contracts (NEW)

### Learning Stats Payload
```python
update_learning_stats({
    "fix_patterns_loaded": 42,        # From FixPatternLearner
    "anti_patterns_loaded": 18,       # From NegativePatternStore
    "score_patterns_loaded": 35,      # From SmokeTestPatternAdapter
    "anti_patterns_injected": 5,      # In current generation
    "fix_patterns_reused": 3,         # Reutilized from previous runs
    "prevention_rate": 0.65,          # Errores evitados / total inyectados
    "neo4j_status": "connected"       # connected/disconnected/error
})
```

### Repair Loop Payload
```python
update_repair_status({
    "status": "ACTIVE",               # ACTIVE/SKIPPED/CONVERGED/MAX_ITERATIONS
    "iteration": 2,                   # Current iteration
    "max_iterations": 3,              # Config max
    "pass_rate_history": [0.65, 0.82],  # Per-iteration pass rates
    "target_pass_rate": 1.0,          # Config target
    "skip_reason": None,              # If skipped: "target_reached", "no_violations"
    "violations_fixed": 8,            # Total fixed this run
    "violations_remaining": 3         # Pending
})
```

### Infra Health Payload (Enhanced)
```python
update_infra_status({
    "docker": {"status": "ok", "detail": "3 containers running"},
    "neo4j": {"status": "ok", "detail": "Learning system connected"},  # Critical!
    "qdrant": {"status": "degraded", "detail": "High latency"},
    "redis": {"status": "offline", "detail": "Connection refused"}
})  

---

## Validación / DoD
- `python -m py_compile src/console/live_dashboard.py src/console/cli.py` pasa.  
- CLI en modo demo muestra dashboard sin errores.  
- En modo WS, fases avanzan y métricas/infra/logs se reflejan.  
- Sin WS, CLI sigue funcionando (no exceptions).  
- Documentación actualizada con comando de uso.  

