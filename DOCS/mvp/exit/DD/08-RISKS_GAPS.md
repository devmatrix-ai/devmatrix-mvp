# Risks & Known Gaps

**Version**: 2.0
**Date**: November 2025
**Status**: Production Assessment

---

## Risk Classification

| Level | Definition | Action Required |
|-------|------------|-----------------|
| 🔴 CRITICAL | Blocks production deployment | Immediate fix (2-3 weeks) |
| 🟠 HIGH | Affects core functionality | Planned fix (4-6 weeks) |
| 🟡 MEDIUM | Degrades quality/performance | Roadmap item |
| 🟢 LOW | Minor issues | Optional improvement |

---

## 🔴 Critical Risks (Correctable in 2-3 weeks)

### 1. Read-Only Field Enforcement

**Problem**: Read-only fields use descriptions instead of actual enforcement.

**Current State**:
```python
unit_price: Decimal = Field(..., description="Read-only field")
```

**Required State**:
```python
unit_price: Decimal = Field(..., exclude=True)  # Cannot be updated
# OR
@computed_field
@property
def unit_price(self) -> Decimal:
    return self._unit_price  # Stored separately
```

**Impact**: Users can modify fields that should be immutable.

**Fix Complexity**: Medium - requires code generator updates.

---

### 2. Auto-Calculated Fields Missing Implementation

**Problem**: Auto-calculated fields have descriptions but no actual logic.

**Current State**:
```python
total_amount: Decimal = Field(..., description="Auto-calculated: sum of items")
```

**Required State**:
```python
@computed_field
@property
def total_amount(self) -> Decimal:
    """Auto-calculated sum of items"""
    return sum(item.unit_price * item.quantity for item in self.items)
```

**Impact**: Calculations must be done manually by consuming code.

**Fix Complexity**: Medium - requires ValidationModelIR enhancement.

---

### 3. Complex Validations Lose Fidelity

**Problem**: Complex business rules transform to empty descriptions.

**Current State**:
- `"Cannot pay CANCELLED/REFUNDED order"` → `description=""`
- `"Stock must be decremented at checkout"` → Not implemented

**Impact**: Business rules not enforced in generated code.

**Fix Complexity**: High - requires new validation categories.

---

### 4. Missing End-to-End Execution Tests

**Problem**: No tests execute the generated application.

**Current State**:
- Unit tests: ✅
- IR tests: ✅
- Generated app execution: ❌

**Impact**: Cannot verify runtime behavior.

**Fix Complexity**: Medium - requires Docker-based test harness.

---

## 🟠 High Priority Gaps

### 5. State Machine / Workflow Validation

**Problem**: Status transitions not enforced.

**Example**:
```
Order status: pending → confirmed → shipped → delivered
                   └─→ cancelled

Spec says: "Cannot transition from delivered to pending"
Generated: No enforcement
```

**Required**:
```python
class OrderStatusValidator:
    VALID_TRANSITIONS = {
        'pending': ['confirmed', 'cancelled'],
        'confirmed': ['shipped', 'cancelled'],
        'shipped': ['delivered'],
        'delivered': [],
        'cancelled': []
    }
```

**Fix Complexity**: Medium - pattern exists, needs IR integration.

---

### 6. Business Logic in Service Layer

**Problem**: Business logic described in spec not generated.

**Example**:
- `"Decrement stock at checkout"` → Not implemented
- `"Calculate discount based on customer tier"` → Not implemented

**Impact**: Critical business operations missing.

**Fix Complexity**: High - requires BehaviorModelIR → service code.

---

### 7. LLM Dependency for Repairs

**Problem**: Code repair heavily depends on LLM.

**Risk**:
- Cost at scale
- Non-deterministic repairs
- Potential regressions

**Mitigation**: Pattern promotion system (LLM → AST → Template) reduces LLM calls over time.

---

### 8. SQLAlchemy Warnings

**Problem**: Persistent warnings about `default_factory`.

**Warning**:
```
SAWarning: 'default_factory' not recognized
```

**Fix**: Use `default=lambda: datetime.now(timezone.utc)` instead of `default_factory`.

---

## 🟡 Medium Priority Gaps

### 9. Constraint Duplication

**Problem**: CodeRepair can duplicate constraints when fixing issues.

**Impact**: Redundant validation code.

**Fix Complexity**: Low - deduplication logic needed.

---

### 10. Side Effects Not Implemented

**Problem**: Some API endpoints don't implement required side effects.

**Example**:
- `POST /orders` should send email notification → Not implemented
- `DELETE /products` should cascade to cart items → Not verified

**Fix Complexity**: Medium - requires side effect extraction from spec.

---

### 11. Pattern Caching Not Optimized

**Problem**: PatternBank doesn't cache promoted patterns efficiently.

**Impact**: Repeated LLM calls for similar patterns.

**Fix**: Implement promoted pattern fast-path.

---

### 12. Performance Metrics Missing

**Problem**: No evaluation of generated code performance.

**Impact**: Cannot guarantee performance characteristics.

**Fix**: Add performance benchmarks to E2E tests.

---

## 🟢 Low Priority Gaps

### 13. Template Documentation Incomplete

**Problem**: Not all templates are fully documented.

**Impact**: Harder to maintain templates.

---

### 14. UUID Serialization Inconsistencies

**Problem**: Some UUID patterns in AST are inconsistent.

**Impact**: Minor serialization issues in edge cases.

---

### 15. Entity Logic Gaps

**Problem**: Some entities have insufficient business logic.

**Impact**: Manual implementation needed.

---

## Risk Mitigation Status

### Implemented Mitigations

| Risk | Mitigation | Status |
|------|------------|--------|
| Semantic validation loss | IR-centric matching | ✅ Complete |
| False negative detections | 300x faster batch matching | ✅ Complete |
| Hardcoded e-commerce logic | Generic IR-driven generation | ✅ Complete |
| Regression detection | Automated pattern matching | ✅ Complete |
| Quality variability | Quality Gate policies | ✅ Complete |

### Pending Mitigations

| Risk | Mitigation | Status |
|------|------------|--------|
| Read-only enforcement | Computed fields/exclude | 🔄 In Progress |
| Business logic gaps | BehaviorModelIR → services | 🔄 In Progress |
| Test execution | Docker-based E2E | 📋 Planned |
| State machines | FSM in service layer | 📋 Planned |

---

## 6 Critical Fields Requiring Real Enforcement

| # | Field | Spec Requirement | Current | Target | Type |
|---|-------|------------------|---------|--------|------|
| 1 | `unit_price` | "snapshot at creation" | description="Read-only" | @computed_field | COMPUTED_FIELD |
| 2 | `registration_date` | "auto, read-only" | description="Read-only" | Field(exclude=True) | IMMUTABLE |
| 3 | `creation_date` | "auto, read-only" | description="Read-only" | Field(exclude=True) | IMMUTABLE |
| 4 | `total_amount` | "auto-calculated sum" | description="Auto-calculated" | @computed_field + logic | COMPUTED_FIELD |
| 5 | `stock` | "decrement at checkout" | Missing | Service method | BUSINESS_LOGIC |
| 6 | `status` | "workflow validations" | Missing | State machine FSM | STATE_MACHINE |

**Compliance**: 0/6 → 6/6 required for production.

---

## Technical Debt Assessment

| Category | Debt Level | Impact | Priority |
|----------|------------|--------|----------|
| Code Generation | Medium | Missing business logic | High |
| Validation | Low | IR-centric approach working | Medium |
| Testing | High | No runtime tests | High |
| Documentation | Low | Templates need docs | Low |
| Performance | Medium | No benchmarks | Medium |

---

## Investor Risk Summary

### Strengths (Risk Mitigated)
- ✅ Formal IR architecture (not ad-hoc prompting)
- ✅ Multi-pass planning (compiler-grade)
- ✅ Deterministic validation (reproducible)
- ✅ Pattern promotion (reduces LLM dependency)
- ✅ 90-98% code correctness

### Gaps (Remaining Risk)
- ❌ Business logic enforcement (partial)
- ❌ Runtime verification (missing)
- ❌ State machine handling (incomplete)
- ❌ LLM cost at scale (mitigated by promotion)

### Risk Timeline

| Period | Risk Level | Reason |
|--------|------------|--------|
| Now | Medium | Core architecture solid, gaps specific |
| +2 weeks | Low-Medium | Critical gaps fixed |
| +6 weeks | Low | Full compliance achieved |

---

## Related Documentation

- [09-ROADMAP.md](09-ROADMAP.md) - Fix timeline
- [10-VALUATION_BASIS.md](10-VALUATION_BASIS.md) - Impact on valuation
- [06-VALIDATION.md](06-VALIDATION.md) - Validation details

---

*DevMatrix - Risks & Known Gaps Assessment*
