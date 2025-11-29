# Smoke Test → Code Repair Disconnect

**Fecha:** 2025-11-29
**Severidad:** CRÍTICA
**Estado:** Diagnosticado, plan de fix pendiente

---

## Problema Detectado

El pipeline tiene una desconexión arquitectural crítica entre smoke tests y code repair:

```
┌─────────────────────────────────────────────────────────────────────┐
│                      ESTADO ACTUAL (ROTO)                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Phase 6.5: Code Repair                                            │
│       │                                                            │
│       └── Trigger: compliance_score < 100%                         │
│           Result: SKIPPED (compliance = 100%)                      │
│                                                                     │
│  Phase 8.5: Smoke Test                                             │
│       │                                                            │
│       └── Result: 56% pass rate (33 failures)                      │
│           Action: NINGUNA (no feedback a repair)                   │
│                                                                     │
│  Learning System                                                   │
│       │                                                            │
│       └── Registra: 33 negative events                             │
│           Action: NINGUNA (no usa data para mejorar)               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Métricas Observadas

| Métrica | Valor | Problema |
|---------|-------|----------|
| Semantic Compliance | 100% | Code Repair ve esto → SKIP |
| Smoke Test Pass Rate | 56% | 33/75 scenarios failed |
| Code Repair Triggered | NO | Porque compliance = 100% |
| Learning Applied | NO | Solo registra, no actúa |

### Errores Específicos del Smoke Test

```
POST /products → 500 Internal Server Error
PUT /products/{id} → 500 Internal Server Error
POST /customers → 500 Internal Server Error
POST /carts → 500 Internal Server Error
POST /carts/{cart_id}/items → 500 Internal Server Error
POST /orders/{order_id}/pay → 500 Internal Server Error
POST /orders/{order_id}/cancel → 500 Internal Server Error
```

**Patrón común:** Todos los endpoints de CREATE/mutation dan 500.

---

## Root Cause Analysis

### 1. Code Repair Solo Mira Compliance Semántica

```python
# Actual (real_e2e_full_pipeline.py línea ~3190)
if compliance_score >= 1.0:
    print("⏭️ Skipping repair: Compliance is perfect (100.0%)")
    return  # NO REPARA
```

**Problema:** Compliance semántica mide:
- ✅ Entidades existen (6/6)
- ✅ Endpoints existen (35/34)
- ✅ Validaciones declaradas (187/187)

**NO mide:**
- ❌ Código funciona en runtime
- ❌ Endpoints responden correctamente
- ❌ Base de datos conecta

### 2. Smoke Test Corre DESPUÉS de Code Repair

```
Phase 6.5: Code Repair    ← Compliance 100% → SKIP
Phase 7: Validation       ← Semantic check
Phase 8.5: Smoke Test     ← 56% pass rate → TOO LATE
```

El smoke test detecta problemas que el repair ya no puede arreglar.

### 3. Learning Registra Pero No Actúa

```python
# Actual
score_summary = process_smoke_results_to_patterns(smoke_result, manifest, app_id)
# Registra 33 negative events
# Actualiza pattern scores a 0.35
# PERO: No usa esos patterns para reparar
```

---

## Solución Propuesta

### Arquitectura Corregida

```
┌─────────────────────────────────────────────────────────────────────┐
│                      ESTADO DESEADO (CORREGIDO)                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Phase 8.5: Smoke Test (PRIMERA PASADA)                            │
│       │                                                            │
│       └── Result: 56% pass rate                                    │
│           ↓                                                        │
│  Phase 8.6: Smoke-Driven Repair (NUEVO)                            │
│       │                                                            │
│       ├── Trigger: smoke_pass_rate < 80%                           │
│       ├── Input: smoke violations (500 errors)                     │
│       ├── Action: Fix specific failing endpoints                   │
│       └── Output: Repaired code                                    │
│           ↓                                                        │
│  Phase 8.7: Smoke Test (SEGUNDA PASADA)                            │
│       │                                                            │
│       └── Verify fixes, iterate if needed                          │
│           ↓                                                        │
│  Learning System (FEEDBACK LOOP)                                   │
│       │                                                            │
│       ├── Record: fix patterns que funcionaron                     │
│       ├── Promote: patterns con >70% success                       │
│       └── Apply: patterns exitosos en próxima generación           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Plan de Implementación

### Task 1: Smoke-Driven Repair Trigger (2h)

**Archivo:** `tests/e2e/real_e2e_full_pipeline.py`

**Cambios:**
1. Mover smoke test ANTES de validation
2. Agregar trigger basado en `smoke_pass_rate`
3. Pasar violations al Code Repair Agent

```python
# Nuevo trigger
async def _should_trigger_smoke_repair(self, smoke_result) -> bool:
    """Trigger repair based on smoke test results, not just compliance."""
    smoke_pass_rate = smoke_result.endpoints_passed / smoke_result.endpoints_tested

    if smoke_pass_rate < 0.8:  # < 80% pass rate
        return True

    # Also trigger for any 500 errors (server bugs)
    has_500_errors = any(
        v.get('actual_status') == 500
        for v in smoke_result.violations
    )

    return has_500_errors
```

### Task 2: Smoke Violation → Repair Input (3h)

**Archivo:** `src/mge/v2/agents/code_repair_agent.py`

**Cambios:**
1. Nuevo modo: `repair_from_smoke_violations`
2. Parser de 500 errors para identificar archivos afectados
3. Extraction de stack traces del server log

```python
async def repair_from_smoke_violations(
    self,
    violations: List[Dict],
    server_logs: str,
    app_path: Path
) -> RepairResult:
    """
    Repair code based on smoke test failures.

    Strategy:
    1. Parse violations to identify failing endpoints
    2. Extract stack traces from server logs
    3. Identify root cause files (routes, services, models)
    4. Apply targeted fixes
    """
    # Group violations by endpoint
    by_endpoint = self._group_violations_by_endpoint(violations)

    # For each failing endpoint, identify fix
    for endpoint, errors in by_endpoint.items():
        if errors[0].get('actual_status') == 500:
            # Server error - need stack trace
            fix = await self._fix_500_error(endpoint, server_logs, app_path)
        elif errors[0].get('actual_status') == 404:
            # Route not found - check route registration
            fix = await self._fix_404_error(endpoint, app_path)
        # ...
```

### Task 3: Server Log Capture (1h)

**Archivo:** `src/validation/runtime_smoke_validator.py`

**Cambios:**
1. Capturar stdout/stderr del container durante smoke tests
2. Parsear stack traces
3. Retornar con smoke results

```python
async def run_smoke_test(self, ...):
    # ... existing code ...

    # NEW: Capture server logs
    server_logs = await self._capture_container_logs(container_name)

    return SmokeTestResult(
        # ... existing fields ...
        server_logs=server_logs,  # NEW
        stack_traces=self._extract_stack_traces(server_logs)  # NEW
    )
```

### Task 4: Iterative Smoke→Repair Loop (2h)

**Archivo:** `tests/e2e/real_e2e_full_pipeline.py`

**Cambios:**
1. Loop de smoke→repair hasta pass_rate >= 80% o max iterations
2. Track de mejoras por iteración

```python
async def _phase_8_5_smoke_repair_loop(self):
    """Iterative smoke test and repair until pass rate >= 80%."""
    MAX_ITERATIONS = 3
    TARGET_PASS_RATE = 0.8

    for iteration in range(MAX_ITERATIONS):
        print(f"\n  🔄 Smoke-Repair Iteration {iteration + 1}/{MAX_ITERATIONS}")

        # Run smoke test
        smoke_result = await self._run_smoke_test()
        pass_rate = smoke_result.endpoints_passed / smoke_result.endpoints_tested

        print(f"    📊 Pass rate: {pass_rate:.1%}")

        if pass_rate >= TARGET_PASS_RATE:
            print(f"    ✅ Target reached!")
            break

        # Repair based on failures
        repair_result = await self.code_repair_agent.repair_from_smoke_violations(
            violations=smoke_result.violations,
            server_logs=smoke_result.server_logs,
            app_path=self.output_path
        )

        print(f"    🔧 Fixed {repair_result.files_fixed} files")

        # Record learning
        self._record_smoke_repair_learning(smoke_result, repair_result)

    return smoke_result
```

### Task 5: Learning Feedback Integration (2h)

**Archivo:** `src/validation/smoke_test_pattern_adapter.py`

**Cambios:**
1. Record de fix patterns exitosos
2. Query de fix patterns para problemas similares
3. Aplicación automática de fixes conocidos

```python
def get_known_fix_for_violation(self, violation: Dict) -> Optional[FixPattern]:
    """
    Query learned fix patterns for similar violations.

    Returns fix pattern if:
    - Same endpoint pattern (e.g., POST /entities)
    - Same error type (500, 404, 422)
    - Fix has success_rate > 70%
    """
    # Query Neo4j for matching patterns
    # Return highest-scoring fix
    pass

def record_successful_fix(self, violation: Dict, fix_applied: str, success: bool):
    """
    Record fix attempt for learning.

    Updates fix pattern success rate.
    Promotes patterns with high success rate.
    """
    pass
```

---

## Métricas de Éxito

| Métrica | Actual | Target | Cómo Medir |
|---------|--------|--------|------------|
| Smoke Pass Rate | 56% | >80% | `endpoints_passed / endpoints_tested` |
| 500 Errors | 33 | 0 | Count de violations con status 500 |
| Repair Triggered | No | Yes | Log de Code Repair Agent |
| Fixes Applied | 0 | >10 | `repair_result.files_fixed` |
| Learning Loop | Broken | Working | Pattern promotion count > 0 |

---

## Archivos a Modificar

| Archivo | Cambio | Prioridad |
|---------|--------|-----------|
| `tests/e2e/real_e2e_full_pipeline.py` | Smoke→Repair loop | P0 |
| `src/mge/v2/agents/code_repair_agent.py` | `repair_from_smoke_violations` | P0 |
| `src/validation/runtime_smoke_validator.py` | Server log capture | P1 |
| `src/validation/smoke_test_pattern_adapter.py` | Fix pattern learning | P1 |
| `src/services/error_pattern_store.py` | Fix pattern queries | P2 |

---

## Timeline Estimado

| Task | Esfuerzo | Dependencia |
|------|----------|-------------|
| Task 1: Smoke-Driven Trigger | 2h | - |
| Task 2: Violation → Repair | 3h | Task 1 |
| Task 3: Server Log Capture | 1h | - |
| Task 4: Iterative Loop | 2h | Task 1, 2, 3 |
| Task 5: Learning Integration | 2h | Task 4 |
| **Total** | **10h** | |

---

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Server logs no capturan stack trace | Media | Alto | Agregar error handler en FastAPI que loguee |
| Repair introduce regresiones | Media | Alto | Run smoke test después de cada fix |
| Loop infinito de repairs | Baja | Alto | Max 3 iterations, early exit |
| Neo4j auth errors persisten | Alta | Medio | In-memory fallback ya implementado |

---

**Documento creado:** 2025-11-29
**Autor:** DevMatrix Pipeline Team
**Próximos pasos:** Implementar Task 1 y 2 como POC
