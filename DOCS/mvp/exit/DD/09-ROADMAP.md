# Technical Roadmap

**Version**: 2.0
**Date**: November 2025
**Status**: Active Development

---

## Overview

This roadmap outlines the technical improvements needed to achieve production-ready status. All items are prioritized based on impact and correctable complexity.

---

## Priority 1: Real Enforcement (2-3 weeks)

### P1.1: Read-Only Field Enforcement

**Files to Modify**:
- `src/services/production_code_generators.py`
- `src/services/code_generation_service.py`

**Deliverables**:
- [ ] Implement `IMMUTABLE` enforcement type
- [ ] Generate `Field(exclude=True)` for read-only
- [ ] Generate `@computed_field` for snapshots
- [ ] Update schemas to block update on immutable fields

**Example Output**:
```python
# In schemas.py:
registration_date: datetime = Field(..., exclude=True)
creation_date: datetime = Field(..., exclude=True)

# In entities.py:
created_at = Column(DateTime(timezone=True),
                    default=lambda: datetime.now(timezone.utc),
                    onupdate=None)
```

---

### P1.2: Auto-Calculated Fields

**Files to Modify**:
- `src/cognitive/ir/validation_model.py`
- `src/services/production_code_generators.py`

**Deliverables**:
- [ ] Add `COMPUTED_FIELD` enforcement type
- [ ] Generate `@computed_field` with calculation logic
- [ ] Extract calculation formula from IR

**Example Output**:
```python
@computed_field
@property
def total_amount(self) -> Decimal:
    """Auto-calculated sum of items"""
    return sum(item.quantity * item.unit_price for item in self.items)
```

---

### P1.3: Snapshot at Creation

**Files to Modify**:
- `src/services/production_code_generators.py`

**Deliverables**:
- [ ] Detect `snapshot_at_add_time` pattern
- [ ] Generate private storage field (`_unit_price`)
- [ ] Generate computed property that returns snapshot

**Example Output**:
```python
class CartItem(Base):
    _unit_price: Decimal = Column("unit_price", Numeric(10, 2))

    @computed_field
    @property
    def unit_price(self) -> Decimal:
        """Snapshot of unit price at cart add time"""
        return self._unit_price
```

---

### P1.4: SQLAlchemy Default Factory Fix

**Files to Modify**:
- `src/services/ast_generators.py`
- `src/services/production_code_generators.py`

**Deliverables**:
- [ ] Replace `default_factory` with `default=lambda: ...`
- [ ] Use `sa.text()` for SQL functions only
- [ ] Eliminate all SQLAlchemy warnings

---

## Priority 2: Semantic Matching Enhancement (3-4 weeks)

### P2.1: Complete IR Integration

**Status**: ✅ Phase 1-4 Complete

**Remaining**:
- [ ] Integrate with all extractors
- [ ] Verify 85%+ constraint match rate
- [ ] Document equivalence mappings

---

### P2.2: Validation Type Coverage

**Files to Modify**:
- `src/services/unified_constraint_extractor.py`

**Deliverables**:
- [ ] Support all 6 validation types in extraction
- [ ] Handle complex nested validations
- [ ] Support cross-entity validations

| Type | Status |
|------|--------|
| PRESENCE | ✅ |
| FORMAT | ✅ |
| RANGE | ✅ |
| UNIQUENESS | ✅ |
| RELATIONSHIP | 🔄 |
| STATUS_TRANSITION | 📋 |

---

## Priority 3: Functional Execution Tests (4-6 weeks)

### P3.1: Docker-Based Test Harness

**New Files**:
- `tests/functional/docker_runner.py`
- `tests/functional/api_tests.py`

**Deliverables**:
- [ ] Docker compose for generated app
- [ ] Automated API testing framework
- [ ] Database seeding for tests
- [ ] Health check validation

**Test Flow**:
```
1. Generate app
2. docker-compose up -d
3. Wait for health check
4. Run API tests
5. Validate responses
6. docker-compose down
```

---

### P3.2: Contract Testing

**Files to Modify**:
- `src/services/ir_test_generator.py`

**Deliverables**:
- [ ] Generate OpenAPI contract tests
- [ ] Validate response schemas
- [ ] Test error responses
- [ ] Performance baseline tests

---

### P3.3: Integration Testing

**Deliverables**:
- [ ] Cross-entity workflow tests
- [ ] Database constraint tests
- [ ] Foreign key validation
- [ ] Cascade delete tests

---

## Priority 4: Business Logic Enforcement (6-8 weeks)

### P4.1: State Machine Generation

**New Files**:
- `src/services/state_machine_generator.py`

**Deliverables**:
- [ ] Extract state transitions from IR
- [ ] Generate FSM validators
- [ ] Integrate with service layer
- [ ] Generate transition tests

**Example Output**:
```python
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
        return next_status in VALID_TRANSITIONS.get(current, [])
```

---

### P4.2: Stock Management

**Files to Modify**:
- `src/services/ir_service_generator.py`

**Deliverables**:
- [ ] Extract stock decrement rules from IR
- [ ] Generate service methods
- [ ] Add transactional safety
- [ ] Generate stock validation tests

**Example Output**:
```python
class CartCheckoutService:
    async def checkout(self, cart_id: UUID) -> Order:
        async with self.db.transaction():
            for item in cart.items:
                await self.product_repo.decrement_stock(
                    item.product_id,
                    item.quantity
                )
            return await self.order_repo.create(...)
```

---

### P4.3: Workflow Validation

**Deliverables**:
- [ ] Extract workflow rules from BehaviorModelIR
- [ ] Generate pre/post condition validators
- [ ] Add business rule enforcement
- [ ] Generate workflow tests

---

## Priority 5: Performance & Optimization (8+ weeks)

### P5.1: PatternBank Optimization

**Files to Modify**:
- `src/cognitive/inference/pattern_bank.py`

**Deliverables**:
- [ ] Implement promoted pattern fast-path
- [ ] Add caching for frequent patterns
- [ ] Reduce Qdrant queries
- [ ] Track pattern usage metrics

---

### P5.2: LLM Call Reduction

**Target**: <10 LLM calls per generation (currently ~50)

**Approach**:
- Promote more patterns to AST/Template
- Cache common repair patterns
- Batch LLM requests where possible

---

### P5.3: Generation Performance

**Target**: <1 minute (currently ~2.7 min)

**Approach**:
- Parallel AST generation
- Cached template rendering
- Optimized IR lookups

---

## Milestone Summary

| Milestone | Timeline | Deliverables | Impact |
|-----------|----------|--------------|--------|
| **M1: Enforcement** | Week 1-3 | Real enforcement for 6 fields | Compliance 0→100% |
| **M2: Semantic** | Week 4-6 | Complete IR matching | Match rate 85%+ |
| **M3: Testing** | Week 7-10 | Functional test suite | Runtime verification |
| **M4: Business** | Week 11-14 | State machines, workflows | Full business logic |
| **M5: Performance** | Week 15+ | Optimizations | <1 min, <10 LLM calls |

---

## Success Criteria

### Short Term (4 weeks)
- [ ] All 6 critical fields enforced
- [ ] SQLAlchemy warnings eliminated
- [ ] Compliance score ≥95%

### Medium Term (10 weeks)
- [ ] Functional tests passing
- [ ] Generated apps executable
- [ ] State machines implemented

### Long Term (16 weeks)
- [ ] Full business logic generation
- [ ] <10 LLM calls per generation
- [ ] <1 minute generation time
- [ ] PatternBank with >200 patterns

---

## Related Documentation

- [08-RISKS_GAPS.md](08-RISKS_GAPS.md) - Current gaps
- [10-VALUATION_BASIS.md](10-VALUATION_BASIS.md) - Impact on valuation
- [05-CODE_GENERATION.md](05-CODE_GENERATION.md) - Generation pipeline

---

*DevMatrix - Technical Roadmap*
