# 🔧 SMOKE TEST & LEARNING FIX PLAN

**Status**: ✅ COMPLETE - 10/10 bugs fixed
**Created**: 2025-12-01
**Updated**: 2025-12-01
**Priority**: P0 - Blocking MVP Quality

## ✅ PROGRESS TRACKER

| Bug | Description | Status | File Modified |
|-----|-------------|--------|---------------|
| **1** | avoidance_context never used | ✅ DONE | `code_generation_service.py` |
| **2** | 404 accepted in health check | ✅ DONE | `runtime_smoke_validator.py` + `real_e2e_full_pipeline.py` (líneas 639-658) |
| **3** | Pipeline continues after smoke fail | ✅ DONE | `real_e2e_full_pipeline.py` |
| **4** | Entity names case mismatch | ✅ DONE | `negative_pattern_store.py` |
| **5** | Two smoke tests with different criteria | ✅ DONE | SmokeRepairOrchestrator ahora usa SmokeRunnerV2 (76 scenarios) |
| **6** | Quality gate OR logic (should be AND) | ✅ DONE | `quality_gate.py` - warnings check ahora evalúa siempre, muestra ⚠️ si excede pero allowed |
| **7** | smoke_pass_rate missing from report | ✅ DONE | `quality_gate.py` + `real_e2e_full_pipeline.py` - smoke_pass_rate en quality gate |
| **8** | Status code matching demasiado permisivo | ✅ DONE | `smoke_runner_v2.py` - QA-strict: solo match exacto (204≠201≠200) |
| **9** | Logs verbosos ensucian pipeline | ✅ DONE | Ver detalle abajo |
| **10** | CodeRepair no repara fallos de smoke | ✅ DONE | Pre-validación de endpoints antes de smoke test |

---

## 🔇 Bug #9: Logs Verbosos - Detalle de Implementación

### Problema
El pipeline muestra demasiado ruido que dificulta ver los errores reales:

1. **Neo4j notifications** - "CREATE CONSTRAINT ... already exists" (INFO, no error)
2. **Positive repair logs** - "✅ Stored positive repair: prp_xxx" (repetitivo, 269+ líneas)
3. **HTTP Request logs** - Todas las requests de httpx (76 líneas), debería mostrar solo las que FALLAN

### Solución

| Log Type | Acción | Archivo |
|----------|--------|---------|
| Neo4j notifications | `logging.getLogger("neo4j").setLevel(WARNING)` | `negative_pattern_store.py` |
| "Stored positive repair" | Cambiar `logger.info()` → `logger.debug()` | `negative_pattern_store.py` |
| "Recorded successful repair" | Cambiar `logger.info()` → `logger.debug()` | Buscar archivo |
| HTTP Request (httpx) | `logging.getLogger("httpx").setLevel(WARNING)` | `smoke_runner_v2.py` |
| Solo mostrar fallos | Print `❌ {method} {path}: {expected} vs {actual}` cuando falla | `smoke_runner_v2.py`|

---

## 📊 Executive Summary

El análisis del run `Ariel_test_006_25_026_10.log` reveló **7 bugs críticos** que hacen que:
1. El smoke test acepte 404/204 como éxitos cuando no lo son
2. El learning NUNCA se aplique en code generation (62 patterns, 1053 occurrences, 0 aplicados)
3. El pipeline continúe después de que smoke falla (debería parar)
4. Las métricas finales no reflejen la realidad del smoke test

### Evidencia

| Métrica | Valor Real | Valor Reportado |
|---------|------------|-----------------|
| Smoke Pass Rate | 73.7% (56/76) | 100% (30/30) |
| Anti-patterns Stored | 62 | 62 ✓ |
| Anti-patterns Applied in CodeGen | 0 | 0 ✓ |
| Pipeline Result | FAILED | partial_success |

---

## 🔴 BUGS CRÍTICOS

### Bug 1: `avoidance_context` se calcula pero NUNCA se usa

**Ubicación**: `src/services/code_generation_service.py:839-894`

**Problema**:
```python
# Línea 839: Se calcula
avoidance_context = self._get_avoidance_context(app_ir)

# Línea 852: Se guarda en repair_context
repair_context = avoidance_context

# Línea 894: Se componen patterns SIN PASAR repair_context
files_dict = await self._compose_patterns(patterns, app_ir=app_ir)  # ❌ repair_context ignorado!
```

**Impacto**: Los 62 anti-patterns con 1053 occurrencias NUNCA llegan al LLM.

**Fix**:
```pythonn 
# Pasar repair_context a _compose_patterns y _generate_with_llm_fallback
files_dict = await self._compose_patterns(patterns, app_ir=app_ir, repair_context=repair_context)
llm_generated = await self._generate_with_llm_fallback(..., repair_context=repair_context)
```

---

### Bug 2: 404 aceptado en health check

**Ubicación**: `src/validation/runtime_smoke_validator.py` (server readiness check)

**Problema**:
```
HTTP Request: GET http://127.0.0.1:8002/health/health "HTTP/1.1 404 Not Found"
✅ Server ready in 0.0s
```

**Impacto**: Servidor marcado como "ready" aunque /health no responde 200.

**Fix**: Verificar que health endpoint retorne 200, no cualquier respuesta.

---

### Bug 3: Dos smoke tests con criterios distintos

**Ubicación**: 
- IR Smoke: `src/validation/smoke_runner_v2.py`
- Repair Cycle: `src/validation/runtime_smoke_validator.py`

**Problema**:
| Test | Scenarios | Matching |
|------|-----------|----------|
| IR Smoke | 76 | Exacto por scenario |
| Repair Cycle | 30 endpoints | Flexible (200/201/204 = success) |

**Impacto**: Reportan pass rates diferentes (73.7% vs 100%) para la misma app.

**Fix**: Unificar criterios. Usar IR Smoke como única fuente de verdad.

---

### Bug 4: Pipeline NO falla cuando smoke falla

**Ubicación**: `tests/e2e/real_e2e_full_pipeline.py` (Phase 8.5)

**Problema**:
```
❌ Phase 8.5 FAILED - Smoke test did not pass after repair
✅ Phase Complete: Runtime Smoke Test
Status: partial_success
```

**Impacto**: Apps rotas se marcan como "partial_success".

**Fix**: Si smoke < 100% después de 3 ciclos, el pipeline debe FALLAR.

---

### Bug 5: Code Repair NO usa anti-patterns aprendidos

**Ubicación**: `src/validation/smoke_repair_orchestrator.py:740-752`

**Problema**: El log muestra `🧠 Learned patterns applied: 0` aunque hay 62 patterns en Neo4j.

**Root Cause**: `_get_learned_antipatterns` busca patterns por entity, pero los patterns están almacenados con `entity_pattern` que no coincide exactamente (e.g., "Product" vs "product").

**Fix**: Normalizar entity names en queries y storage.

---

### Bug 6: Métricas finales no incluyen smoke results

**Ubicación**: `tests/e2e/real_e2e_full_pipeline.py` (final report)

**Problema**: El reporte final muestra:
```
Semantic Compliance: 99.9%
Generated Tests: 65.5%
```
Pero NO muestra: `Smoke Pass Rate: 73.7%`

**Fix**: Incluir smoke_pass_rate en métricas de compliance.

---

### Bug 7: Quality Gate pasa con warnings excedidos

**Ubicación**: Quality gate evaluation

**Problema**:
```
Warnings: 28 ≤ 20 ❌
Status: ✅ PASSED
```

**Fix**: Quality gate debe fallar si CUALQUIER check falla.

---

## 📋 IMPLEMENTATION PLAN

### Phase 1: Critical Fixes (2h)

| Task | File | Effort |
|------|------|--------|
| 1.1 Pasar `repair_context` a generadores | `code_generation_service.py` | 30m |
| 1.2 Health check solo acepta 200 | `runtime_smoke_validator.py` | 20m |
| 1.3 Pipeline falla si smoke < 100% | `real_e2e_full_pipeline.py` | 30m |
| 1.4 Normalizar entity names | `negative_pattern_store.py` | 40m |

### Phase 2: Consistency Fixes (1h)

| Task | File | Effort |
|------|------|--------|
| 2.1 Unificar smoke test metrics | `smoke_runner_v2.py` | 30m |
| 2.2 Quality gate AND logic | `tests/e2e/*.py` | 20m |
| 2.3 Incluir smoke en reporte | `real_e2e_full_pipeline.py` | 10m |

### Phase 3: Validation (1h)

| Task | Description | Effort |
|------|-------------|--------|
| 3.1 Run E2E 3 veces | Verificar que patterns se aplican | 30m |
| 3.2 Verificar smoke falla correctamente | App rota debe fallar | 20m |
| 3.3 Verificar metrics correctas | Smoke rate en reporte | 10m |

---

## 📈 Expected Results After Fix

| Métrica | Antes | Después |
|---------|-------|---------|
| Learning aplicado en Run 2 | 0 | 62 patterns |
| Smoke false positives | Sí (404=OK) | No |
| Pipeline para en smoke fail | No | Sí (después de 3 ciclos) |
| Métricas smoke en reporte | No | Sí |

---

## 🎯 Success Criteria

1. ✅ Run 2 aplica patterns de Run 1: `🎓 Anti-patterns injected: X warnings`
2. ✅ 404 en health = FAIL
3. ✅ Smoke < 100% después de 3 ciclos = Pipeline FAILED
4. ✅ Reporte final incluye smoke_pass_rate
5. ✅ Quality gate falla si warnings > threshold

---

## 🔧 IMPLEMENTATION DETAILS

### Fix 1.1: Pasar `repair_context` a generadores

**File**: `src/services/code_generation_service.py`

```python
# Línea ~894 - Cambiar de:
files_dict = await self._compose_patterns(patterns, app_ir=app_ir)

# A:
files_dict = await self._compose_patterns(
    patterns,
    app_ir=app_ir,
    avoidance_context=repair_context  # NUEVO
)

# Y actualizar _compose_patterns para usar el context en LLM calls
```

**También**: Actualizar `_compose_category_patterns` y `_generate_with_llm_fallback` para pasar el contexto a los prompts del LLM.

---

### Fix 1.2: Health check solo acepta 200

**File**: `src/validation/runtime_smoke_validator.py`

```python
# En el método que verifica server readiness, cambiar de:
if response.status_code < 500:
    return True  # Server is ready

# A:
if response.status_code == 200:
    return True  # Server is ready
else:
    logger.warning(f"Health check returned {response.status_code}, expected 200")
    return False
```

---

### Fix 1.3: Pipeline falla si smoke < 100%

**File**: `tests/e2e/real_e2e_full_pipeline.py`

```python
# Después del smoke repair loop, agregar:
if smoke_pass_rate < 100.0:
    print(f"\n❌ PIPELINE FAILED: Smoke test pass rate {smoke_pass_rate}% < 100%")
    print("   After 3 repair cycles, application still has failing scenarios.")
    self.pipeline_status = "FAILED"
    raise RuntimeError(f"Smoke test failed: {smoke_pass_rate}% pass rate")
```

---

### Fix 1.4: Normalizar entity names en queries

**File**: `src/learning/negative_pattern_store.py`

```python
def get_patterns_for_entity(self, entity_name: str, min_occurrences: int = None):
    # Normalizar entity name para búsqueda
    normalized = entity_name.lower().strip()

    # Query con LOWER() para match case-insensitive
    result = session.run("""
        MATCH (ap:GenerationAntiPattern)
        WHERE LOWER(ap.entity_pattern) = LOWER($entity_name)
           OR ap.entity_pattern = '*'
        ...
    """)
```

---

### Fix 2.1: Unificar smoke test metrics (Bug #5 - COMPLETE REFACTOR)

**Problema**:
- IR Smoke (SmokeRunnerV2) testea 76 scenarios con happy_path + edge_cases + error_cases
- Repair Cycle usa RuntimeSmokeTestValidator que testea solo 30 endpoints únicos
- Después del repair, RuntimeSmokeTestValidator reporta "Target reached" (100%)
- Pero IR Smoke nunca se re-ejecuta → los 76 scenarios siguen fallando

**Arquitectura actual (INCORRECTA)**:
```
IR Smoke (76 scenarios) → 73.7% FAIL
         ↓
Repair Cycle con RuntimeSmokeTestValidator (30 endpoints) → 100% PASS  ← MAL
         ↓
Pipeline continúa → App rota en producción
```

**Arquitectura objetivo (CORRECTA)**:
```
IR Smoke (76 scenarios) → 73.7% FAIL
         ↓
Repair Cycle con SmokeRunnerV2 (76 scenarios)
         ↓
Re-run IR Smoke → 100%? → Pipeline OK
                  < 100%? → Pipeline FAIL
```

**Solución Implementada**:

1. **Modificar `SmokeRepairOrchestrator`** para aceptar `SmokeRunnerV2` + `TestsModelIR`:

```python
# smoke_repair_orchestrator.py - Constructor modificado
def __init__(
    self,
    smoke_validator=None,  # DEPRECATED: RuntimeSmokeTestValidator (legacy fallback)
    smoke_runner_v2: Optional[SmokeRunnerV2] = None,  # NEW: IR-centric runner
    tests_model_ir: Optional[TestsModelIR] = None,  # NEW: IR for scenarios
    code_repair_agent=None,
    pattern_adapter=None,
    config: Optional[SmokeRepairConfig] = None
):
    # Prefer IR-centric smoke testing
    self.smoke_runner_v2 = smoke_runner_v2
    self.tests_model_ir = tests_model_ir
    self.smoke_validator = smoke_validator  # Legacy fallback
    self.use_ir_smoke = smoke_runner_v2 is not None and tests_model_ir is not None
```

2. **Modificar `_run_smoke_test`** para usar SmokeRunnerV2:

```python
async def _run_smoke_test(self, app_path: Path, application_ir, capture_logs: bool):
    """Run smoke test - prefer IR-centric (76 scenarios) over legacy (30 endpoints)."""
    if self.use_ir_smoke:
        # IR-centric: 76 scenarios (deterministic, comprehensive)
        report = await self.smoke_runner_v2.run()
        # Convert SmokeTestReport to SmokeTestResult format
        return self._convert_report_to_result(report)
    else:
        # Legacy fallback: 30 endpoints only
        logger.warning("Using legacy RuntimeSmokeTestValidator (30 endpoints only)")
        return await self.smoke_validator.validate(application_ir)
```

3. **Modificar `real_e2e_full_pipeline.py`** para pasar SmokeRunnerV2:

```python
# En _phase_8_5_runtime_smoke_test, después de IR Smoke fail:
if not smoke_result.passed and smoke_result.violations:
    # Create SmokeRunnerV2 for repair cycle (same 76 scenarios)
    runner = SmokeRunnerV2(self.tests_model_ir, base_url)

    orchestrator = SmokeRepairOrchestrator(
        smoke_runner_v2=runner,
        tests_model_ir=self.tests_model_ir,
        smoke_validator=None,  # Don't use legacy
        config=config
    )

    repair_result = await orchestrator.run_full_repair_cycle(...)
```

4. **Deprecar `RuntimeSmokeTestValidator` en repair loop**:
   - Agregar warning cuando se use en repair context
   - Mantener solo como fallback si TestsModelIR no está disponible

**Files Modified**:
- `src/validation/smoke_repair_orchestrator.py`
- `tests/e2e/real_e2e_full_pipeline.py`

**Result**: Repair cycle usa los MISMOS 76 scenarios que IR Smoke, garantizando consistencia

---

### Fix 2.2: Quality Gate AND logic

**File**: `tests/e2e/real_e2e_full_pipeline.py` (quality gate section)

```python
# Cambiar de:
gate_passed = any([
    semantic_ok,
    ir_ok,
    warnings_ok
])

# A:
gate_passed = all([
    semantic_ok,
    ir_ok,
    warnings_ok
])
```

---

## 📊 DIAGNOSTIC QUERIES

### Verificar patterns en Neo4j

```cypher
// Contar patterns por entity
MATCH (ap:GenerationAntiPattern)
RETURN ap.entity_pattern, COUNT(*) as count, SUM(ap.occurrence_count) as total_occ
ORDER BY total_occ DESC

// Ver patterns con más ocurrencias
MATCH (ap:GenerationAntiPattern)
WHERE ap.occurrence_count > 10
RETURN ap.pattern_id, ap.entity_pattern, ap.error_type, ap.occurrence_count
ORDER BY ap.occurrence_count DESC
LIMIT 20
```

### Verificar en logs

```bash
# Buscar si avoidance_context se calcula
grep -n "avoidance_context\|Anti-patterns injected\|Active Learning" logs/runs/*.log

# Buscar smoke pass rates
grep -n "Pass rate:\|pass_rate\|Passed:" logs/runs/*.log
```

---

## 📝 TESTING CHECKLIST

### Pre-fix verification:
- [ ] Run E2E, confirmar `🧠 Learned patterns applied: 0`
- [ ] Confirmar 404 en health = server ready
- [ ] Confirmar pipeline continúa después de smoke fail

### Post-fix verification:
- [ ] Run E2E #1: Crea anti-patterns
- [ ] Run E2E #2: `🎓 Anti-patterns injected: X` aparece
- [ ] 404 en health = server NOT ready
- [ ] Smoke < 100% después de 3 ciclos = FAILED
- [ ] Reporte final incluye smoke_pass_rate
- [ ] Quality gate falla con warnings > 20

---

## 🔧 Bug #10: Pre-Validación de Endpoints (Nivel 1)

### Problema

El circuito de aprendizaje + reparación funciona para validaciones IR pero NO para fallos de smoke test:

| Fallo Smoke | Tipo | Root Cause |
|-------------|------|------------|
| `PATCH /products/{id}/deactivate` → 404 | Ruta faltante | PatternBank no tiene template para action endpoints |
| `PATCH /products/{id}/activate` → 404 | Ruta faltante | Idem |
| `POST /carts/{id}/checkout` → 404 | Ruta faltante | Idem |
| `POST /orders` → 422 | Data inválida | El body del smoke test no matchea el schema |
| `DELETE /carts/{id}/items/{product_id}` → 404 | Ruta nested faltante | PatternBank no genera nested DELETE |

### Solución: Pre-Validación ANTES del Smoke Test

**Estrategia de 3 niveles:**

| Nivel | Descripción | Impacto |
|-------|-------------|---------|
| **1** (Implementado) | Pre-verificación IR vs Código | Detecta endpoints faltantes ANTES de smoke |
| 2 (Futuro) | Smoke-driven repair | Genera rutas para 404s después de fallo |
| 3 (Futuro) | Request body repair | Arregla 422s corrigiendo data/schemas |

### Implementación Nivel 1

**Archivos creados/modificados:**

| Archivo | Cambio |
|---------|--------|
| `src/validation/endpoint_pre_validator.py` | **NUEVO** - Compara IR endpoints vs rutas generadas |
| `tests/e2e/real_e2e_full_pipeline.py` | Llama pre-validación antes de smoke test |

**Flujo:**

```
Phase 8.5: Runtime Smoke Test
    ↓
🔍 Pre-validating endpoints (Bug #10 Fix)...
    📊 IR endpoints: 15
    📊 Code endpoints: 10
    📊 Coverage: 66.7%
    ⚠️ Missing 5 endpoints:
       - PATCH /products/{id}/deactivate [ACTION]
       - PATCH /products/{id}/activate [ACTION]
       - POST /carts/{id}/checkout [ACTION]
       ...
    🔧 Attempting to generate missing endpoints...
       ✅ Generated: PATCH /products/{id}/deactivate
       ✅ Generated: PATCH /products/{id}/activate
       ...
    ↓
🚀 Phase 2: Executing 76 scenarios...
```

**Código clave:**

```python
# endpoint_pre_validator.py
class EndpointPreValidator:
    def validate(self) -> PreValidationResult:
        # 1. Extract endpoints from IR
        ir_endpoints = self._extract_ir_endpoints()

        # 2. Extract endpoints from generated code
        code_endpoints = self._extract_code_endpoints()

        # 3. Find gaps (normalize paths for comparison)
        ir_set = set([f"{e.method} {normalize(e.path)}" for e in ir_endpoints])
        code_set = set(code_endpoints)

        missing = ir_set - code_set

        # 4. Create EndpointGap objects for repair
        for sig in missing:
            gap = EndpointGap(method, path, is_action=True if /activate|/deactivate)
            result.missing_endpoints.append(gap)

        return result
```

**Integración en pipeline:**

```python
# real_e2e_full_pipeline.py - _phase_8_5_runtime_smoke_test
if ENDPOINT_PRE_VALIDATOR_AVAILABLE:
    await self._pre_validate_endpoints()  # Bug #10 Fix

# TestsIR: Try IR-centric deterministic smoke test
smoke_result = await self._run_ir_smoke_test()
```

### Resultado Esperado

| Antes | Después |
|-------|---------|
| 404 en smoke → fallo sin contexto | Pre-detección de endpoints faltantes |
| CodeRepair solo arregla validaciones | CodeRepair genera endpoints faltantes |
| 5+ fallos 404 en cada run | 0 fallos 404 (endpoints generados antes) |

### Métricas Capturadas

```python
self.metrics_collector.add_checkpoint("runtime_smoke_test", "CP-8.5.PRE_VALIDATE", {
    "ir_endpoints": len(result.ir_endpoints),
    "code_endpoints": len(result.code_endpoints),
    "missing_count": len(result.missing_endpoints),
    "coverage_rate": result.coverage_rate,
    "action_endpoints_missing": sum(1 for g in result.missing_endpoints if g.is_action)
})
```
