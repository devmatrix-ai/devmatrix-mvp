# IR-Agnostic Implementation Plan

**Date**: 2025-12-01
**Version**: 1.1
**Status**: ✅ COMPLETE + PIPELINE CLEANUP
**Estimated Effort**: 17-25 days (3-5 weeks)
**Actual Effort**: 4.5 days (Phases 1-4 complete)

---

## Progress Tracker

| Phase | Component | Status | Days Est | Days Actual | Owner |
|-------|-----------|--------|----------|-------------|-------|
| **1** | **Auto-Seed IR-Aware** | [x] Complete | **5-7** | **1.5** | |
| 1.1 | Relationship inference from ValidationModelIR | [x] Complete | 1-2 | 0.5 | |
| 1.2 | Payload generation from constraints | [x] Complete | 2 | 0.5 | |
| 1.3 | Refactor SeedDataAgent to use IR | [x] Complete | 2-3 | 0.5 | |
| **2** | **Runtime Flow Repair** | [x] Complete | **10-15** | **2** | |
| 2.1 | Failure classifier (3 types) | [x] Complete | 3-4 | 0.5 | |
| 2.2 | DB snapshot diff engine | [x] Complete | 2-3 | 0.5 | |
| 2.3 | AST repair engine extension | [x] Complete | 3-5 | 0.5 | |
| 2.4 | IR-to-repair mapping | [x] Complete | 2-3 | 0.5 | |
| **3** | **Pipeline Integration** | [x] Complete | **2-3** | **0.5** | |
| 3.1 | Smoke → Classifier → Repair loop | [x] Complete | 2-3 | 0.5 | |
| **4** | **Bug Fixes (Blocking)** | | **Completed** | | |
| 4.1 | Bug #199: request_schema in inferred endpoints | [x] Complete | 0.5 | 0.5 | |
| 4.2 | Bug #200: Code generator ignoring IR schemas | [x] Complete | 0.5 | 0.5 | |

---

## Executive Summary

This plan implements the vision from `IR_ENHANCEMENTS.md`: making DevMatrix **100% domain-agnostic**.

### Current State
- DevMatrix can generate code from any spec
- BUT: Some components still have domain-aware heuristics (e.g., "CartItem", "OrderItem")
- Pass rate: ~89% on ecommerce spec

### Target State
- **Zero domain knowledge** in code generation
- All behavior derived from IR (entities, relationships, constraints, flows)
- Pass rate: **95%+** on any domain spec

---

## Phase 1: Auto-Seed IR-Aware (5-7 days)

### Goal
Generate test seed data **entirely from IR**, without knowing entity names.

### 1.1 Relationship Inference (1-2 days)

**Problem**: Current seeding hardcodes relationships like `cart.customer_id`.

**Solution**: Extract FK relationships from ValidationModelIR:

```python
# From ValidationModelIR
for rule in validation_model.rules:
    if rule.rule_type == ValidationType.RELATIONSHIP:
        # "entity_x.field_id references entity_y.id"
        parent = rule.target_field.split('.')[0]
        child = rule.condition  # parsed to get parent entity
        relationships.append((child, parent))
```

**Files to modify**:
- `src/cognitive/ir/validation_model.py` - Add relationship extraction
- `src/validation/agents/seed_data_agent.py` - Use extracted relationships

### 1.2 Payload Generation from Constraints (2 days)

**Problem**: Seed payloads have hardcoded values.

**Solution**: Generate valid values from ValidationModelIR:

| Constraint | Generated Value |
|------------|-----------------|
| `min_value=0` | `1` (min + 1) |
| `max_length=255` | Random string ≤255 |
| `enum=OPEN,CLOSED` | First value: `"OPEN"` |
| `required` | Always include |
| `uuid_format` | Generated UUID |
| `email_format` | `test_{n}@example.com` |

**Files to modify**:
- `src/services/tests_ir_generator.py` - Add constraint-aware value generator
- `src/validation/agents/seed_data_agent.py` - Use generator

### 1.3 Refactor SeedDataAgent (2-3 days)

**Problem**: `SeedDataAgent` has domain-specific logic.

**Solution**: Pure IR-driven seeding:

```python
class IRSeedGenerator:
    def __init__(self, app_ir: ApplicationIR):
        self.domain = app_ir.domain_model
        self.validation = app_ir.validation_model
        self.api = app_ir.api_model
    
    def generate_seed_script(self) -> str:
        # 1. Topological sort entities by FK dependencies
        ordered = self._get_dependency_order()
        
        # 2. For each entity, generate create payload
        for entity in ordered:
            payload = self._generate_payload(entity)
            # Uses POST endpoint from APIModelIR
            endpoint = self._find_create_endpoint(entity)
```

**Files to modify**:
- `src/validation/agents/seed_data_agent.py` - Complete rewrite
- `src/cognitive/ir/tests_model.py` - Add `get_seed_order()` enhancements

---

## Phase 2: Runtime Flow Repair (10-15 days)

### Goal
Classify and repair smoke test failures **using only IR semantics**.

### 2.1 Failure Classifier (3-4 days)

Three failure types, detected from IR:

| Type | Detection | Example |
|------|-----------|---------|
| `MISSING_PRECONDITION` | 404 + entity doesn't exist | GET /carts/{id} → 404 |
| `WRONG_STATUS_CODE` | IR says valid, code says error | IR: flow valid → 422 |
| `MISSING_SIDE_EFFECT` | Postcondition not met | stock unchanged after purchase |

```python
class FailureClassifier:
    def classify(self, failure: SmokeFailure, ir: ApplicationIR) -> FailureType:
        if failure.actual_status == 404:
            # Check if precondition entity exists
            if not await self._entity_exists(failure.path_params):
                return FailureType.MISSING_PRECONDITION
        
        if self._ir_says_valid(failure, ir):
            return FailureType.WRONG_STATUS_CODE
        
        if not await self._postconditions_met(failure, ir):
            return FailureType.MISSING_SIDE_EFFECT
```

**Files to create**:
- `src/validation/failure_classifier.py`

### 2.2 DB Snapshot Diff (2-3 days)

Compare database state before/after flow execution:

```python
class DBSnapshotDiff:
    async def take_snapshot(self, entities: List[str]) -> Dict:
        """Capture current state of all entities."""
        
    async def diff(self, before: Dict, after: Dict) -> List[Change]:
        """Detect what changed."""
        
    def check_postconditions(self, diff: List[Change], flow: Flow) -> bool:
        """Verify IR postconditions are satisfied."""
```

**Files to create**:
- `src/validation/db_snapshot.py`

### 2.3 AST Repair Engine Extension (3-5 days)

Extend existing repair to handle IR-based fixes:

| Failure Type | Repair Action |
|--------------|---------------|
| `WRONG_STATUS_CODE` | Change `status_code=X` to IR value |
| `MISSING_SIDE_EFFECT` | Inject service call from IR flow |
| `MISSING_PRECONDITION` | Add existence check |

**Files to modify**:
- `src/validation/smoke_repair_orchestrator.py`
- `src/validation/code_repair_agent.py`

### 2.4 IR-to-Repair Mapping (2-3 days)

Map IR semantics to AST changes:

```python
class IRRepairMapper:
    def map_to_ast_fix(self, failure: ClassifiedFailure, ir: ApplicationIR) -> ASTFix:
        if failure.type == FailureType.WRONG_STATUS_CODE:
            return self._status_code_fix(failure)
        elif failure.type == FailureType.MISSING_SIDE_EFFECT:
            return self._side_effect_fix(failure, ir.behavior_model)
```

**Files to create**:
- `src/validation/ir_repair_mapper.py`

---

## Phase 3: Pipeline Integration (2-3 days)

### Goal
Connect all components into the main pipeline.

```
Smoke Test → Failure Classifier → IR Repair Mapper → AST Fix → Rebuild → Re-test
     ↑                                                                      │
     └──────────────────────────────────────────────────────────────────────┘
```

**Files to modify**:
- `tests/e2e/real_e2e_full_pipeline.py`
- `src/validation/smoke_repair_orchestrator.py`

---

## Architecture Impact

### New Components

```
src/
├── validation/
│   ├── failure_classifier.py      # NEW: Classify failures by IR
│   ├── db_snapshot.py             # NEW: Before/after diff
│   ├── ir_repair_mapper.py        # NEW: IR → AST fix mapping
│   └── agents/
│       └── seed_data_agent.py     # REFACTOR: IR-driven
```

### Modified Components

| File | Change |
|------|--------|
| `smoke_repair_orchestrator.py` | Add classifier + mapper integration |
| `tests_ir_generator.py` | Constraint-aware value generation |
| `validation_model.py` | Relationship extraction |
| `code_generation_service.py` | Use IR schemas (Bug #200) |

---

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Smoke pass rate (ecommerce) | 89% | 95%+ |
| Domain-specific code lines | ~50 | 0 |
| New domain spec pass rate | N/A | 90%+ |

---

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| IR extraction misses relationships | Medium | High | Add LLM validation pass |
| AST repair introduces bugs | Medium | High | Syntax check after each fix |
| Performance degradation | Low | Medium | Cache snapshots |

---

## Phase 4: Pipeline Domain-Agnostic Cleanup (0.5 days) ✅ COMPLETE

### Goal
Remove ALL hardcoded entity names from the entire pipeline.

### Files Refactored

| File | Changes | Status |
|------|---------|--------|
| `src/validation/smoke_runner_v2.py` | Dynamic `_build_seed_uuids()` from IR entities | ✅ |
| `src/validation/runtime_smoke_validator.py` | Domain-agnostic `_substitute_path_params()` and `_generate_test_payload()` | ✅ |
| `src/cognitive/patterns/pattern_bank.py` | Replaced entity-specific workflows with action verb workflows | ✅ |
| `src/cognitive/planning/multi_pass_planner.py` | IR-based `_extract_entity()` and `_check_workflow_ordering()` | ✅ |
| `src/services/inferred_endpoint_enricher.py` | FK-based nested resource detection (no hardcoded patterns) | ✅ |
| `src/services/production_code_generators.py` | Parent FK detection from entity name | ✅ |
| `src/validation/basic_pipeline.py` | Generic `*Create` pattern instead of `ProductCreate` | ✅ |

### Key Refactoring Patterns

1. **Entity Names**: Replaced hardcoded `['product', 'customer', 'cart', 'order']` with IR entity extraction
2. **UUID Maps**: Replaced hardcoded UUID maps with `_build_seed_uuids()` that generates from IR
3. **FK Detection**: Replaced `NESTED_PATTERNS` dict with dynamic FK relationship detection
4. **Workflow Detection**: Replaced entity-based workflow detection with action verb detection

---

## Summary of All Changes

### New Files Created (Phase 1-3)
- `src/validation/failure_classifier.py` - Domain-agnostic failure classification
- `src/validation/db_snapshot.py` - DB state snapshot engine
- `src/validation/ir_repair_mapper.py` - IR-to-repair action mapper

### Files Modified (All Phases)
1. `src/cognitive/ir/validation_model.py` - Added `get_fk_relationships()`, `get_entity_constraints()`
2. `src/validation/agents/seed_data_agent.py` - Added `_get_value_from_ir()`
3. `src/services/tests_ir_generator.py` - Added constraint cache, dynamic entity UUID map
4. `src/validation/smoke_repair_orchestrator.py` - IR-centric classification and repair
5. `src/validation/smoke_runner_v2.py` - Dynamic seed UUID generation
6. `src/validation/runtime_smoke_validator.py` - Domain-agnostic path/payload generation
7. `src/cognitive/patterns/pattern_bank.py` - Action verb workflows
8. `src/cognitive/planning/multi_pass_planner.py` - IR-based entity/workflow detection
9. `src/services/inferred_endpoint_enricher.py` - FK-based nested resource inference
10. `src/services/production_code_generators.py` - Parent FK detection
11. `src/validation/basic_pipeline.py` - Generic schema patterns
12. `src/services/code_generation_service.py` - Dynamic join table detection

---

## Next Steps

1. [x] Complete Bug #200 verification
2. [x] Complete Phase 1-3 implementation
3. [x] Complete Phase 4 pipeline cleanup
4. [/] Run E2E test to verify pass rate improvement
5. [ ] Document any remaining domain-aware code (should be 0)

---

## Phase 5: Seed DB UUID Consistency Bug (BLOCKING) 🔴

**Date Discovered**: 2025-12-01
**Status**: ROOT CAUSE IDENTIFIED - READY TO FIX

---

### 🔍 Root Cause: TWO SEPARATE UUID SYSTEMS

Hay **DOS sistemas de generación de UUIDs** que no están sincronizados:

| Archivo | Función | Propósito | UUIDs |
|---------|---------|-----------|-------|
| `code_generation_service.py` | `_generate_seed_db_script()` | Genera `seed_db.py` | Sistema A |
| `smoke_runner_v2.py` | `_build_seed_uuids()` | Ejecuta smoke tests | Sistema B |

---

### 📊 Sistema A: `code_generation_service.py` (líneas 5564-5572)

```python
uuid_base = "00000000-0000-4000-8000-00000000000"      # 11 zeros (1 digit)
uuid_base_delete = "00000000-0000-4000-8000-0000000000"  # 10 zeros (2 digits)

for idx, entity in enumerate(entities_list, start=1):
    primary_uuid = f"{uuid_base}{idx}"      # ...001, ...002, ...003
    delete_uuid = f"{uuid_base_delete}{idx + 10}"  # ...011, ...012, ...013
    entity_uuids[entity.name.lower()] = (primary_uuid, delete_uuid)
```

**Resultado esperado:**
| Entity | Primary UUID | Delete UUID |
|--------|--------------|-------------|
| Product | ...001 | ...011 |
| Customer | ...002 | ...012 |
| Cart | ...003 | ...013 |
| Order | ...005 | ...015 |

---

### 📊 Sistema B: `smoke_runner_v2.py` (líneas 205-222)

```python
uuid_base = "00000000-0000-4000-8000-0000000000"  # 10 zeros (2 digits)
offset = 10 if is_delete else 0
item_offset = 20 if not is_delete else 21  # Items start at 20

for idx, seed in enumerate(self.tests_model.seed_scenarios, start=1):
    if 'item' in entity_name:
        uuid_num = item_offset + item_counter  # 20, 21, 22...
    else:
        uuid_num = idx + offset  # 1, 2, 3... (or 11, 12, 13...)
    seed_uuids[entity_name] = f"{uuid_base}{uuid_num:02d}"  # ...01, ...02
```

**Resultado:**
| Entity | Primary UUID | Delete UUID |
|--------|--------------|-------------|
| Product | ...01 | ...11 |
| Customer | ...02 | ...12 |
| Cart | ...03 | ...13 |
| CartItem | ...20 | ...21 |
| Order | ...05 | ...15 |
| OrderItem | ...22 | ...23 |

---

### ❌ El Problema Real

El **output generado** muestra UUIDs `...020, ...022, ...024` pero el código de Sistema A debería generar `...001, ...002, ...003`.

**Evidencia del seed_db.py generado:**
```python
# Product obtiene ...020 (NO ...001)
test_product = ProductEntity(
    id=UUID("00000000-0000-4000-8000-000000000020"),  # ❌ Debería ser ...001
    ...
)

# Cart obtiene ...024 pero customer_id apunta a ...002
test_cart = CartEntity(
    id=UUID("00000000-0000-4000-8000-000000000024"),  # ❌ Debería ser ...003
    customer_id=UUID("00000000-0000-4000-8000-000000000002"),  # De entity_uuids
    ...
)

# CartItem apunta a cart_id ...003 que NO EXISTE
test_cartitem = CartItemEntity(
    cart_id=UUID("00000000-0000-4000-8000-000000000003"),  # ❌ Cart real es ...024
    ...
)
```

---

### 🎯 Hipótesis

1. **¿entities_list vacío?** - El loop de línea 5568 no ejecuta, `entity_uuids` queda vacío
2. **¿Otro generador?** - Hay otro código que genera seed_db.py con lógica diferente
3. **¿Estado corrupto?** - seed_blocks tiene datos de una ejecución anterior
4. **¿IR incorrecto?** - `spec_requirements` no tiene `domain_model.entities`

---

### ✅ Solución Propuesta

**Unificar los dos sistemas en UNO SOLO:**

```python
# NUEVO: Función compartida para UUID generation
def generate_entity_uuids(entities: List, is_delete: bool = False) -> Dict[str, str]:
    """
    Generate consistent UUIDs for all entities.
    Used by both seed_db.py generator and smoke_runner.
    """
    uuid_base = "00000000-0000-4000-8000-0000000000"  # 10 zeros, 2 digits
    offset = 10 if is_delete else 0
    item_offset = 20 if not is_delete else 21

    uuids = {}
    item_counter = 0
    regular_idx = 1

    for entity in entities:
        name = entity.name.lower() if hasattr(entity, 'name') else str(entity).lower()
        if 'item' in name:
            uuid_num = item_offset + item_counter
            item_counter += 1
        else:
            uuid_num = regular_idx + offset
            regular_idx += 1
        uuids[name] = f"{uuid_base}{uuid_num:02d}"

    return uuids
```

**Archivos a modificar:**
1. `src/services/code_generation_service.py` - Usar función compartida
2. `src/validation/smoke_runner_v2.py` - Usar función compartida
3. Crear `src/utils/uuid_generator.py` - Ubicación de la función compartida

---

### 📋 Acciones Pendientes

| # | Acción | Prioridad |
|---|--------|-----------|
| 1 | Agregar debug logging para verificar `entities_list` | Alta |
| 2 | Verificar si IR llega correctamente a `_generate_seed_db_script()` | Alta |
| 3 | Crear función compartida de UUIDs | Alta |
| 4 | Actualizar ambos archivos para usar función compartida | Alta |
| 5 | Re-ejecutar E2E test | Alta |

---

### 🧪 Test de Verificación

```bash
# Después del fix, estos UUIDs deben coincidir:
# seed_db.py Cart.id == smoke_runner Cart UUID
# seed_db.py CartItem.cart_id == seed_db.py Cart.id
```

