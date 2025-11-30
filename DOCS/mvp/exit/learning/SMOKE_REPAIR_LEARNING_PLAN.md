# Smoke Repair & Learning Upgrade Plan

**Date:** 2025-11-30  
**Owner:** Platform / Learning  
**Scope:** Hacer que el loop smoke→repair→learning realmente repare (no solo fixes genéricos) y que el aprendizaje se reutilice en siguientes generaciones/reparaciones.

---

## Contexto (Run 052 Observaciones)
- Smoke IR falló 23/76 escenarios (69.7% pass).  
- Repair loop corrió 2 iteraciones con Docker rebuild ON, pero:
  - Aplicó 4 fixes genéricos (“Generic error on … HTTP_500”).  
  - Pass rate quedó en 86.7% (converged sin mejora).  
  - FixPatternLearner registró patrones genéricos (poca señal).  
  - NegativePatternStore no guió reparaciones (sin stack traces útiles).  
- CodeGenerationService no se usó para regenerar flows/servicios; solo parches locales.  
- Docker rebuild durante repair puede fallar si no hay Dockerfile (riesgo recurrente).

---

## Problemas Identificados
1) **Datos pobres en violaciones**: las `violations` no incluyen stack traces/exception class, lo que fuerza estrategia `GENERIC`.  
2) **Aprendizaje débil**: FixPatternLearner recibe strings genéricos sin metadatos (endpoint/error/exception), no puede proponer fixes específicos.  
3) **Anti-patterns no aplicados**: NegativePatternStore no tiene señal porque no se pasa stack trace ni patrón de endpoint adecuado.  
4) **Estrategias sin mapeo fino**: 500/404/422 no se enrutan a estrategias ROUTE/VALIDATION/SERVICE; cae en `generic`.  
5) **Sin fallback de regeneración**: ante plateau (delta 0) no se llama a CodeGeneration para re-sintetizar flows/servicios.  
6) **Política Docker rebuild**: `SMOKE_REPAIR_DOCKER_REBUILD` activado por defecto puede bloquear repair si falta Dockerfile.

---

## Objetivos
- Reparar con señales ricas (stack traces, endpoint, exception) y estrategias específicas.  
- Grabar aprendizaje reutilizable (FixPatternLearner/NegativePatternStore) con metadatos y éxito/fracaso.  
- Hacer fallback a regeneración parcial cuando el patching no mejora pass rate.  
- Evitar bloqueos por Docker rebuild sin Dockerfile.

---

## Plan de Trabajo
### 1) Enriquecer violaciones y trazas
- Adjuntar `StackTrace` parseada a cada `SmokeViolation` (endpoint, exception_class, file, line, full_trace).  
- Extraer `response.text` en 500s/422s y parsear traceback real del server.  
- Aceptación: `_try_known_fix` y NegativePatternStore reciben `stack_traces` ≠ 0; logs muestran exception_class por violación.

### 2) Datos útiles para FixPatternLearner
- Cambiar `record_repair_attempt` para aceptar dicts con `endpoint`, `error_type`, `exception_class`, `fix_type`, `success`.  
- Persistir en Neo4j con claves específicas (no “generic”).  
- Aceptación: consultas por endpoint/exception devuelven patrones con success_rate > 0 para reuse; `_try_known_fix` los usa.

### 3) Uso efectivo de NegativePatternStore
- Pasar stack traces y endpoint al query; mapear entity/endpoint/exception.  
- Aplicar `correct_pattern` si `wrong_pattern` aparece en el archivo target.  
- Aceptación: logs “Applied learned anti-pattern fix …” en iteraciones con fallos repetidos.

### 4) Estrategias y fallback
- Mapear status→estrategia (500→SERVICE/ROUTE, 422→VALIDATION, 404→ROUTE/DB).  
- Si delta pass rate = 0 tras iteración, activar modo de **regeneración parcial** con CodeGenerationService para los endpoints fallados (services/flows).  
- Aceptación: reparaciones incluyen tipos no genéricos; si plateau, se dispara regeneración y se registra diff.

### 5) Política Docker rebuild
- Default: `SMOKE_REPAIR_DOCKER_REBUILD=false` salvo que se verifique Dockerfile presente.  
- Aceptación: no hay “failed to read dockerfile” durante repair; rebuild opt-in.

### 6) Observabilidad
- Loguear inicio/fin de cada iteración de repair, pass rate antes/después, número de fixes por tipo.  
- Incluir en checkpoint el uso de patrones conocidos y anti-patterns aplicados.  
- Aceptación: run logs muestran iteraciones con métricas claras y razones de convergencia.

---

## Checklist de Implementación
- [ ] Enriquecer `RuntimeSmokeTestValidator`: adjuntar stack traces a `violations`.  
- [ ] Actualizar `SmokeRepairOrchestrator` para usar stack traces en `_try_known_fix` y anti-patterns.  
- [ ] Reestructurar `record_repair_attempt` (FixPatternLearner) para dicts con metadatos y persistencia específica.  
- [ ] Estrategia por status/error → candidate generation no genérica.  
- [ ] Fallback de regeneración parcial en plateau (CodeGenerationService).  
- [ ] Cambiar default `SMOKE_REPAIR_DOCKER_REBUILD` a false y validar Dockerfile antes de rebuild.  
- [ ] Añadir logging detallado de iteraciones y patrones aplicados.

---

## Referencias
- Log Run 052: `logs/runs/test_devmatrix_000_052.log` (Phase 8.5, converged at 86.7%).  
- Código relevante: `src/validation/runtime_smoke_validator.py`, `src/validation/smoke_repair_orchestrator.py`, `src/validation/smoke_test_pattern_adapter.py`.  
- Estado actual de toggles: `.env` contiene `ENFORCE_DOCKER_RUNTIME=true`, `SMOKE_REPAIR_DOCKER_REBUILD=true` (recomendado: desactivar por defecto).
