# Fase 2: Convertir 6 Validaciones de Descripción a Enforcement Real

**Document Version**: 1.0
**Date**: November 25, 2025
**Status**: 🔄 IN PROGRESS
**Estimated Timeline**: 4-6 hours
**Priority**: 🟠 HIGH - Fundamental for compliance

---

## 📋 Executive Summary

### Problem Statement
**Current State**: 6 validaciones solo tienen descripción (texto), NO enforcement real
**Gap**: Código generado no implementa las restricciones especificadas
**Result**: Compliance 0/6 para estos campos

### Solution: Implement Real Enforcement
Convertir cada validación de descripción a enforcement real implementado en código:

| # | Campo | Spec Requirement | Current | Target | Type |
|---|-------|------------------|---------|--------|------|
| 1 | `unit_price` | "snapshot del precio EN ESE MOMENTO" | description="Read-only" | @computed_field | COMPUTED_FIELD |
| 2 | `registration_date` | "automática, solo lectura" | description="Read-only" | Field(exclude=True) | IMMUTABLE |
| 3 | `creation_date` | "automática, solo lectura" | description="Read-only" | Field(exclude=True) | IMMUTABLE |
| 4 | `total_amount` | "suma automática items × cantidad" | description="Auto-calculated" | @computed_field + logic | COMPUTED_FIELD |
| 5 | `stock` | "decrementar al checkout" | Missing | Service method | BUSINESS_LOGIC |
| 6 | `status` | "workflow validations" | Missing | State machine FSM | STATE_MACHINE |

---

## 🛠️ Implementation Plan

### Task 1: Update ValidationModelIR Fields (15 min)
**File**: `src/cognitive/ir/validation_model.py`

Asegurar que cada ValidationRule puede expresar enforcement real:
- ✅ `enforcement_type` enum (ya existe con 6 tipos)
- ✅ `enforcement` strategy object (ya existe)
- ✅ Metadata fields (type, implementation, applied_at, parameters)

### Task 2: Update BusinessLogicExtractor (45 min)
**File**: `src/services/business_logic_extractor.py`

Método `_determine_enforcement_type()` que asigne enforcement correcto:
- `unit_price` → COMPUTED_FIELD (es snapshot)
- `registration_date` → IMMUTABLE (auto, read-only)
- `creation_date` → IMMUTABLE (auto, read-only)
- `total_amount` → COMPUTED_FIELD (auto-calculated)
- `stock` → BUSINESS_LOGIC (decrementar es lógica de negocio)
- `status` → STATE_MACHINE (workflow validations)

### Task 3: Update Code Generators (90 min)
**Files**:
- `src/services/production_code_generators.py`
- `src/services/code_generation_service.py`

Generar código correcto para cada tipo:

**COMPUTED_FIELD** (unit_price, total_amount):
```python
@computed_field
@property
def unit_price(self) -> Decimal:
    """Snapshot of unit price at cart add time"""
    return self._unit_price  # Stored separately

@computed_field
@property
def total_amount(self) -> Decimal:
    """Auto-calculated sum of items"""
    return sum(item.quantity * item.unit_price for item in self.items)
```

**IMMUTABLE** (registration_date, creation_date):
```python
# In schemas.py:
registration_date: datetime = Field(..., exclude=True)  # Cannot be updated
creation_date: datetime = Field(..., exclude=True)  # Cannot be updated

# In entities.py:
registration_date = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=None)
```

**STATE_MACHINE** (status):
```python
# In service layer:
class OrderStatusValidator:
    VALID_TRANSITIONS = {
        'pending': ['confirmed', 'cancelled'],
        'confirmed': ['shipped', 'cancelled'],
        'shipped': ['delivered'],
        'delivered': [],
        'cancelled': []
    }

    @staticmethod
    def validate_transition(current: str, next_status: str) -> bool:
        return next_status in OrderStatusValidator.VALID_TRANSITIONS.get(current, [])
```

**BUSINESS_LOGIC** (stock decrement):
```python
# In service layer:
class CartCheckoutService:
    async def checkout(self, cart_id: UUID) -> Order:
        # Decrement stock for each item
        for item in cart.items:
            await product_repo.decrement_stock(item.product_id, item.quantity)
        # Create order
        return await order_repo.create(...)
```

### Task 4: Write Integration Tests (60 min)
**File**: `tests/validation/test_phase2_real_enforcement.py`

Create 6 tests (one per field):
1. `test_unit_price_computed_field` - Verify @computed_field works
2. `test_registration_date_immutable` - Verify cannot update
3. `test_creation_date_immutable` - Verify cannot update
4. `test_total_amount_computed_field` - Verify calculation works
5. `test_stock_business_logic` - Verify decrement happens
6. `test_status_state_machine` - Verify valid transitions

### Task 5: Update Generated Code (30 min)
Update 5 generated applications with real enforcement:
- ecommerce-api-spec-human_1764073703
- ecommerce-api-spec-human_1764079784
- ecommerce-api-spec-human_1764082377
- ecommerce-api-spec-human_1764070513
- ecommerce-api-spec-human_1764074467

---

## 📊 Success Criteria

1. ✅ All 6 fields have real enforcement (not descriptions)
2. ✅ Generated code implements enforcement correctly
3. ✅ All 6 integration tests PASS
4. ✅ Compliance metric: 0/6 → 6/6
5. ✅ Syntax validation passes (no Python errors)

---

## 🔄 Phase Completion

**After Phase 2 Completion**:
→ Real Enforcement vs Description: **0/6 → 6/6** ✅
→ Compliance foundation complete for Phase 3 (overall compliance)

**Blocked By**: None (can start immediately)

---

## 📋 Checklist

- [ ] Task 1: Verify ValidationModelIR structure
- [ ] Task 2: Implement enforcement determination logic
- [ ] Task 3: Update code generators
- [ ] Task 4: Write integration tests (6/6 PASS)
- [ ] Task 5: Update generated applications
- [ ] All tests PASS
- [ ] Compliance plan updated (0/6 → 6/6)

---

**Timeline**: 4-6 hours (estimated)
**Actual**: ___ (to be filled on completion)
**Status**: 🔄 IN PROGRESS
