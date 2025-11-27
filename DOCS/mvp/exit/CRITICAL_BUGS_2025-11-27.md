# Critical Bugs Found - November 27, 2025

**Analysis Date**: 2025-11-27
**Test Run**: `ecommerce-api-spec-human_1764201312`
**Status**: CRITICAL - Pipeline produces misleading results

---

## Executive Summary

El pipeline E2E muestra resultados engañosos. Dice "✅ PASSED" con 98.6% compliance pero:
- Code Repair no funciona (aplica repairs que no persisten)
- Endpoints del spec no están en el IR
- Métricas inconsistentes entre fases
- Tests no ejecutan (0% pass rate pero dice PASSED)

---

## Bug #45: Code Repair Aplica Mismos Repairs Repetidamente

**Severity**: HIGH
**Category**: Code Repair Loop
**Status**: NEW

### Síntoma
```
⏳ Iteration 1/3
Added non=True to Product.name
Added greater_than_zero=True to Product.price
Added non_negative=True to Product.stock
✓ Applied 44 repairs

⏳ Iteration 2/3
Added non=True to Product.name          ← MISMO REPAIR DE NUEVO
Added greater_than_zero=True to Product.price  ← MISMO REPAIR DE NUEVO
Added non_negative=True to Product.stock       ← MISMO REPAIR DE NUEVO
✓ Applied 39 repairs
```

### Root Cause
CodeRepairAgent no verifica si el repair ya fue aplicado. Cada iteración:
1. Lee los failures
2. Aplica repairs sin verificar estado actual
3. No persiste cambios correctamente O no re-lee el archivo modificado

### Impact
- Ciclos de repair inútiles (waste of compute)
- Nunca mejora compliance
- False sense of progress ("Applied 44 repairs" pero nada cambió)

### Files Involved
- `src/mge/v2/agents/code_repair_agent.py`

---

## Bug #46: Compliance No Mejora Pese a "44 Repairs Applied"

**Severity**: CRITICAL
**Category**: Code Repair Effectiveness
**Status**: NEW

### Síntoma
```
✓ Applied 44 repairs
    ├─ Endpoints added: 13
    ├─ Validations added: 31
📝 Re-validating compliance...
OpenAPI-based compliance validation complete: 93.0%
ℹ️ Post-repair compliance: 93.0% → 93.0%
    ├─ Status: ⚠️
    ├─ Delta: +0.0%
```

### Root Cause Options
1. **Repairs no se escriben a disco** - Solo en memoria
2. **Repairs se escriben pero validator no re-lee** - Cache stale
3. **Repairs son sintácticamente incorrectos** - Se agregan pero no son válidos
4. **Validator mide algo diferente** - Mismatch entre lo que repair agrega y lo que validator busca

### Impact
- Code Repair phase es completamente inútil
- Pipeline gasta tiempo sin mejorar nada
- Métricas son mentira

### Files Involved
- `src/mge/v2/agents/code_repair_agent.py`
- `src/validation/compliance_validator.py`

---

## Bug #47: Endpoints del Spec No Están en APIModelIR

**Severity**: CRITICAL
**Category**: IR Extraction
**Status**: ✅ FIXED (2025-11-27)

### Síntoma
```
Endpoint PATCH /products/{id}/deactivate marked missing but not in APIModelIR (may be inferred or custom)
Endpoint PUT /carts/{id}/items/{product_id} marked missing but not in APIModelIR (may be inferred or custom)
Endpoint DELETE /carts/{id}/items/{product_id} marked missing but not in APIModelIR (may be inferred or custom)
```

### Spec Says
```markdown
### 1. Producto (Product)
Acciones permitidas:
- Desactivar un producto (sin eliminarlo físicamente)  ← PATCH /products/{id}/deactivate

### 3. Carrito (Cart)
Acciones permitidas:
- Agregar productos al carrito      ← POST/PUT /carts/{id}/items
- Eliminar items                    ← DELETE /carts/{id}/items/{product_id}
```

### Root Cause
`SpecToApplicationIR` o `BusinessLogicExtractor` no extrae estos endpoints:
1. Solo extrae endpoints CRUD básicos
2. No reconoce "custom operations" como deactivate
3. No reconoce nested resources como `/carts/{id}/items/{product_id}`

### Impact
- **CodeRepair no puede reparar** endpoints que no están en IR
- **Compliance nunca llega a 100%** para estos endpoints
- **Spec-to-App fidelity es falsa** - dice 98.6% pero faltan endpoints críticos

### Files Involved
- `src/specs/spec_to_application_ir.py`
- `src/services/business_logic_extractor.py`
- `src/cognitive/ir/api_model.py`
- `src/services/inferred_endpoint_enricher.py` (FIXED)

### Fix Implemented (2025-11-27)

Added two new inference methods to `InferredEndpointEnricher`:

1. **`_infer_custom_operations()`**
   - Detects custom operations from flow names: deactivate, activate, checkout, cancel, pay
   - Generates endpoints like `PATCH /products/{id}/deactivate`
   - Triggered when flows mention these operations

2. **`_infer_nested_resource_endpoints()`**
   - Detects nested resources from entity relationships
   - For CartItem → generates `PUT /carts/{id}/items/{product_id}` and `DELETE /carts/{id}/items/{product_id}`
   - For OrderItem → generates similar nested endpoints

Modified `enrich_api_model()` to accept:
- `domain_model` - for relationship inference
- `flows_data` - for custom operation detection

Updated `spec_to_application_ir.py` (line 657) to pass these parameters during enrichment.

**Test Results** (2025-11-27):
```
📊 Total endpoints en APIModelIR: 45

✅ Custom operations encontradas: 16
   PATCH /products/{id}/deactivate (inferred=True)
   PATCH /products/{id}/activate (inferred=True)
   POST /carts/{id}/checkout (inferred=True)
   ...

✅ Nested resources encontradas: 5
   PUT /carts/{id}/items/{product_id} (inferred=True)
   DELETE /carts/{id}/items/{product_id} (inferred=True)
   ...

🔍 Verificación Bug #47:
   ✅ PATCH /products/{id}/deactivate
   ✅ PUT /carts/{id}/items/{product_id}
   ✅ DELETE /carts/{id}/items/{product_id}

🎉 Bug #47 FIXED - Todos los endpoints faltantes ahora están en el IR!
```

---

## Bug #48: Cart.items y Order.items Nunca Matchean

**Severity**: MEDIUM
**Category**: Semantic Matching
**Status**: NEW

### Síntoma
```
⚠️ Semantic matching: 57/59 = 96.6%
   Unmatched: ['Cart.items: required', 'Order.items: required']
```

Aparece en TODAS las iteraciones, nunca se resuelve.

### Root Cause
`IRSemanticMatcher` no tiene pattern para "relationship required":
- `Cart.items` es una relación one-to-many con CartItem
- `Order.items` es una relación one-to-many con OrderItem
- El matcher busca "required" como field constraint, no como relationship

### Impact
- 2 validations siempre fallan
- Compliance máximo = 96.6% para validations (nunca 100%)

### Files Involved
- `src/services/ir_compliance_checker.py`
- `src/services/semantic_matcher.py`

---

## Bug #49: Métricas Inconsistentes Entre Fases

**Severity**: HIGH
**Category**: Metrics/Reporting
**Status**: NEW

### Síntoma

**Phase 6.5 (Code Repair)**:
```
Endpoints: 28/19  ← 28 required, 19 found = 67.8%
Validations: 57/59 = 96.6%
Overall: 93.0%
```

**Phase 7 (Validation)**:
```
Endpoints: 29/19 required matched (+10 inferred = 29 total)  ← Ahora son 29?
Semantic Compliance: 98.6%  ← Subió de 93% a 98.6%?
```

**Dashboard**:
```
│ Semantic Compliance:      98.6% ✅              │
│ IR Compliance (Relaxed):  84.0% ⚠️              │
│ IR Compliance (Strict):   91.8% ✅              │
```

### Root Cause
- Diferentes fases usan diferentes fuentes de verdad
- Phase 6.5 usa OpenAPI extraction
- Phase 7 usa ApplicationIR
- Los números no coinciden

### Impact
- No se puede confiar en ninguna métrica
- "98.6% compliance" es engañoso
- Due diligence imposible de realizar

---

## Bug #50: Tests No Ejecutan Pero Pipeline Dice PASSED

**Severity**: HIGH
**Category**: Test Execution
**Status**: NEW

### Síntoma
```
📋 Test files discovered: 5
⚠️  Tests found (5 files) but none executed
   pytest exit code: 4
   Error: ERROR: file or directory not found: tests/e2e/generated_apps/.../tests

✅ Validation Results Summary
   Test Pass Rate: 0.0%  ⚠️
   Overall Validation Status: ✅ PASSED  ← WTF?
```

### Root Cause
1. Tests se generan en `src/tests/` pero pytest busca en `tests/`
2. Quality gate permite 0% test pass rate en DEV mode
3. Pipeline muestra PASSED aunque tests no corran

### Impact
- **False confidence** - Dice PASSED pero tests no corren
- **No real validation** - Solo syntax check, no functional test
- **Production risk** - Código puede tener bugs funcionales

### Files Involved
- `tests/e2e/real_e2e_full_pipeline.py` (pytest path)
- `src/services/ir_test_generator.py` (output path)
- `src/services/qa_levels.py` (quality gate thresholds)

---

## Summary Table

| Bug | Severity | Category | Status | Quick Description |
|-----|----------|----------|--------|-------------------|
| #45 | HIGH | Code Repair | NEW | Same repairs applied repeatedly |
| #46 | CRITICAL | Code Repair | NEW | 44 repairs but 0% improvement |
| #47 | CRITICAL | IR Extraction | ✅ FIXED | Spec endpoints missing from IR |
| #48 | MEDIUM | Semantic Matching | NEW | Cart.items/Order.items never match |
| #49 | HIGH | Metrics | NEW | Inconsistent numbers between phases |
| #50 | HIGH | Testing | NEW | 0% tests pass but says PASSED |

---

## Recommended Fix Priority

1. ~~**Bug #47** (IR Extraction) - Root cause of many issues~~ ✅ FIXED
2. **Bug #46** (Repair Effectiveness) - Core functionality broken
3. **Bug #50** (Tests) - False confidence is dangerous
4. **Bug #49** (Metrics) - Trust issue
5. **Bug #45** (Repeated Repairs) - Efficiency
6. **Bug #48** (Semantic Matching) - Edge case

---

## Conclusion

El pipeline actual produce resultados que parecen buenos pero son engañosos:
- **98.6% compliance** suena bien pero endpoints críticos faltan
- **44 repairs applied** suena productivo pero nada cambió
- **✅ PASSED** suena seguro pero tests no corren

**Esto es inaceptable para due diligence o producción.**
