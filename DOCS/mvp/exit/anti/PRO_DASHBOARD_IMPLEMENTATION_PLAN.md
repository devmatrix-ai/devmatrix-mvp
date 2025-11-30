# DevMatrix Pro Dashboard – Implementation Plan

**Owner:** Platform/Console  
**Status:** Draft  
**Scope:** Reemplazar los dashboards ad-hoc (CLI roto + `tests/e2e/progress_dashboard.py`) por un dashboard profesional y unificado para monitorear ejecución del pipeline, estado de infra y debugging en vivo.

---

## Objetivos
- **UX unificada:** Dashboard único invocado desde CLI y usable en runs locales/CI.
- **Signal completo:** Progreso por fase, métricas clave (tests, IR compliance, LLM tokens/costo), salud de infra (Docker, Neo4j, Qdrant, Redis), eventos de errores y artefactos generados.
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
4) **Eventos y logs**  
   - Buffer de últimos N eventos (nivel info/warn/error).  
   - Mostrar timestamps y mensaje limpio para debugging rápido.  
5) **Contexto en vivo**  
   - Tarea actual y hints de acción (approve pendiente, revisar infra).  
6) **Modos**  
   - Online: alimentado por WebSocket del pipeline/CLI.  
   - Offline/mock: simulación para demos/tests sin backend.  

## Requerimientos No Funcionales
- **Render estable:** sin flicker; usa Rich Layout con áreas fijas.  
- **API chica:** `set_status`, `set_current_task`, `update_phase`, `update_metrics`, `update_infra_status`, `add_log`, `update()`.  
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
| Workstream | Owner | Status | Next Milestone | Notas |
|------------|-------|--------|----------------|-------|
| Base dashboard Rich (`live_dashboard.py`) | Platform | ✅ Done | Merge wiring en CLI | Layout header/phases/metrics/infra/logs listo. |
| Wiring CLI → dashboard API | Platform | 🟡 In Progress | Ajustar callbacks y tipos PhaseState | Sustituir acceso dict por métodos; manejar fase dinámica. |
| Métricas (tests/compliance/LLM) | Platform | 🔲 Todo | Mapear payload WS a update_metrics | Requiere definir keys consistentes desde pipeline. |
| Infra health (docker/neo4j/qdrant/redis) | Platform | 🔲 Todo | Recibir snapshot y pintar status | Puede iniciar en modo best-effort (unknown → ok/offline). |
| Logs/event stream | Platform | 🔲 Todo | Normalizar niveles y trimming | Buffer 30 eventos; mostrar últimos 15. |
| Mock/offline mode | Platform | 🔲 Todo | Comando de demo en CLI | Reusar simulación actual o generar datos sintéticos. |
| Docs & QA | Platform | 🔲 Todo | Update DASHBOARD_USAGE + README | Incluir captura textual y comando de uso. |

Legend: ✅ Done | 🟡 In Progress | 🔲 Todo

---

## Riesgos y Mitigaciones
- **Eventos incompletos del pipeline:** Mitigar con defaults y modo offline; logs claros cuando faltan campos.  
- **Flicker en terminales lentas:** Mantener layout fijo y refresco moderado (3–4 fps).  
- **Desalineación de keys métricas:** Definir contrato WS (tests_passed, tests_failed, ir_compliance, llm_tokens, llm_cost).  
- **Infra health no disponible:** Mostrar `unknown` sin romper render; agregar toggle para ocultar.  

---

## Validación / DoD
- `python -m py_compile src/console/live_dashboard.py src/console/cli.py` pasa.  
- CLI en modo demo muestra dashboard sin errores.  
- En modo WS, fases avanzan y métricas/infra/logs se reflejan.  
- Sin WS, CLI sigue funcionando (no exceptions).  
- Documentación actualizada con comando de uso.  

