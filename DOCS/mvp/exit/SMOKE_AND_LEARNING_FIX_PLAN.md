# 🔧 SMOKE TEST & LEARNING FIX PLAN

**Status**: IN PROGRESS - 3/7 bugs fixed
**Created**: 2025-12-01
**Updated**: 2025-12-01
**Priority**: P0 - Blocking MVP Quality

## ✅ PROGRESS TRACKER

| Bug | Description | Status | File Modified |
|-----|-------------|--------|---------------|
| **1** | avoidance_context never used | ✅ DONE | `code_generation_service.py` |
| **2** | 404 accepted in health check | ✅ DONE | `runtime_smoke_validator.py` |
| **3** | Pipeline continues after smoke fail | ✅ DONE | `real_e2e_full_pipeline.py` |
| **4** | Entity names case mismatch | ⏳ TODO | `negative_pattern_store.py` |
| **5** | Two smoke tests with different criteria | ⏳ TODO | smoke_runner_v2.py, runtime_smoke_validator.py |
| **6** | Quality gate OR logic (should be AND) | ⏳ TODO | real_e2e_full_pipeline.py |
| **7** | smoke_pass_rate missing from report | ⏳ TODO | real_e2e_full_pipeline.py |

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

### Fix 2.1: Unificar smoke test metrics

**Problema**: IR Smoke (76 scenarios) vs Repair Cycle (30 endpoints)

**Solución**: El Repair Cycle debe usar los mismos 76 scenarios del IR Smoke, no solo los 30 endpoints.

```python
# En smoke_repair_orchestrator.py, usar:
scenarios = tests_ir.get_smoke_scenarios()  # Los mismos 76 del IR Smoke

# En lugar de:
endpoints = app_ir.api_model.endpoints  # Solo 30 endpoints
```

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

