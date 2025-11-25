# Phase 4.1: EnforcementStrategy in ValidationModelIR Implementation Plan

**Document Version**: 1.0
**Date**: November 25, 2025
**Status**: ✅ COMPLETADA
**Timeline**: 1.5 hours (planned) → 50 min (actual)
**Priority**: 🟡 IMPORTANT - Unblocked by Phase 4.0 ✅
**Completion Date**: November 25, 2025 - 16:05 UTC

---

## 📋 Executive Summary

### Problem Statement
Current `ValidationRule` in `ValidationModelIR` only stores:
- `field: str` - Field name
- `rule_type: str` - Constraint type ("unique", "range", "read_only", etc.)
- `constraint: str` - Natural language constraint

**Problem**: No information about HOW to enforce the constraint (strategy, implementation, templates)

Result: Code generators don't know whether to use:
- Description string (fake enforcement ❌)
- Pydantic @computed_field (real enforcement ✅)
- Field(exclude=True) (real enforcement ✅)
- @field_validator (real enforcement ✅)
- Service-layer logic (real enforcement ✅)

### Solution: EnforcementStrategy
Add structured enforcement metadata to ValidationRule:

```python
class EnforcementStrategy:
    type: EnforcementType  # COMPUTED_FIELD, IMMUTABLE, VALIDATOR, etc.
    implementation: str    # Actual enforcement code/pattern
    applied_at: List[str]  # ["schema", "entity", "service"]
    template_name: str     # e.g., "computed_field_sum"
    parameters: dict       # Template parameters

class ValidationRule:
    field: str
    rule_type: str
    constraint: str
    enforcement: EnforcementStrategy  # ← NEW
```

### Expected Outcomes
✅ ValidationRule has complete enforcement information
✅ Code generators can use correct enforcement pattern
✅ IR serialization preserves enforcement semantics
✅ Foundation for Phase 4.2-4.4 (IR determinism + reproducibility)

---

## 🛠️ Technical Architecture

### Current State (BEFORE)
```python
# src/cognitive/ir/validation_model.py

class ValidationRule(BaseModel):
    field: str
    rule_type: str  # "unique", "range", "read_only", "computed", etc.
    constraint: str  # "Snapshot of product price at order creation"
    source: str = "spec"
    confidence: float = 1.0

class ValidationModelIR(BaseModel):
    rules: List[ValidationRule]
```

### Target State (AFTER)
```python
# src/cognitive/ir/validation_model.py

from enum import Enum

class EnforcementType(str, Enum):
    """How to enforce the validation."""
    DESCRIPTION = "description"  # Only description string (NOT enforcement)
    VALIDATOR = "validator"      # Pydantic @field_validator
    COMPUTED_FIELD = "computed_field"  # Pydantic @computed_field
    IMMUTABLE = "immutable"      # Field(exclude=True) or onupdate=None
    STATE_MACHINE = "state_machine"  # Workflow state transitions
    BUSINESS_LOGIC = "business_logic"  # Service-layer enforcement

class EnforcementStrategy(BaseModel):
    """
    Enforcement strategy for a validation rule.
    Defines HOW to enforce the constraint, not just WHAT to validate.
    """
    type: EnforcementType
    implementation: str  # Code pattern or template name
    applied_at: List[Literal["schema", "entity", "service", "endpoint"]]

    # Template metadata for reproducibility
    template_name: Optional[str] = None  # e.g., "computed_field_sum"
    parameters: dict = Field(default_factory=dict)  # Template parameters

class ValidationRule(BaseModel):
    """Validation rule with enforcement strategy."""
    field: str
    entity: Optional[str] = None
    rule_type: str
    constraint: str

    # NEW: Enforcement strategy
    enforcement: EnforcementStrategy

    source: str = "spec"
    confidence: float = 1.0

class ValidationModelIR(BaseModel):
    """Collection of validation rules with enforcement strategies."""
    rules: List[ValidationRule]

    def get_rules_by_enforcement(self, enforcement_type: EnforcementType) -> List[ValidationRule]:
        """Get all rules with specific enforcement type."""
        return [r for r in self.rules if r.enforcement.type == enforcement_type]

    def get_rules_for_entity(self, entity_name: str) -> List[ValidationRule]:
        """Get all rules for specific entity."""
        return [r for r in self.rules if r.entity == entity_name]
```

### Data Flow

```
┌─────────────────────────────────────────────────┐
│  SpecRequirements (from hierarchical extraction)│
│  - entities: [6]                                │
│  - endpoints: [21]                              │
│  - business_logic: [12]                         │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
         ┌──────────────────────────┐
         │  BusinessLogicExtractor  │
         │  Extract validation rules│
         └────────────┬─────────────┘
                      │
                      ▼
     ┌───────────────────────────────────┐
     │  ValidationRule (old version)     │
     │  - field: "unit_price"            │
     │  - rule_type: "snapshot"          │
     │  - constraint: "captures price"   │
     └────────────────┬──────────────────┘
                      │
         ┌────────────┴─────────────────────┐
         │ Phase 4.1: ADD ENFORCEMENT STRATEGY
         │
         │ Enrich with:
         │ - type: BUSINESS_LOGIC
         │ - implementation: "capture_value_at_creation"
         │ - applied_at: ["service"]
         │ - template_name: "snapshot_field"
         │
         └────────────┬─────────────────────┘
                      │
                      ▼
     ┌──────────────────────────────────────┐
     │  ValidationRule (new version)        │
     │  - field: "unit_price"               │
     │  - rule_type: "snapshot"             │
     │  - constraint: "captures price"      │
     │  - enforcement:                      │
     │    - type: BUSINESS_LOGIC            │
     │    - implementation: "capture_at_creation" │
     │    - applied_at: ["service"]         │
     │    - template_name: "snapshot_field" │
     └────────────────┬──────────────────────┘
                      │
                      ▼
         ┌──────────────────────────┐
         │   ValidationModelIR      │
         │   Complete with all      │
         │   enforcement strategies │
         └────────────┬─────────────┘
                      │
                      ▼
         ┌──────────────────────────┐
         │  Neo4j IR Repository     │
         │  Persist enforcement     │
         │  (Phase 4.3 later)       │
         └──────────────────────────┘
```

---

## 📝 Implementation Plan

### Task 1: Create EnforcementStrategy Classes

**File**: `src/cognitive/ir/validation_model.py`

**Changes**:
```python
from enum import Enum
from typing import Literal, Optional, List
from pydantic import BaseModel, Field

# 1. Define EnforcementType enum
class EnforcementType(str, Enum):
    """How to enforce the validation."""
    DESCRIPTION = "description"  # Only description (NOT enforcement)
    VALIDATOR = "validator"  # @field_validator
    COMPUTED_FIELD = "computed_field"  # @computed_field
    IMMUTABLE = "immutable"  # exclude=True or onupdate=None
    STATE_MACHINE = "state_machine"  # Workflow transitions
    BUSINESS_LOGIC = "business_logic"  # Service-layer

# 2. Define EnforcementStrategy
class EnforcementStrategy(BaseModel):
    """Enforcement strategy for validation."""
    type: EnforcementType
    implementation: str
    applied_at: List[Literal["schema", "entity", "service", "endpoint"]]
    template_name: Optional[str] = None
    parameters: dict = Field(default_factory=dict)

# 3. Update ValidationRule
class ValidationRule(BaseModel):
    """Validation rule with enforcement."""
    field: str
    entity: Optional[str] = None
    rule_type: str
    constraint: str
    enforcement: EnforcementStrategy  # ← NEW
    source: str = "spec"
    confidence: float = 1.0

# 4. Update ValidationModelIR
class ValidationModelIR(BaseModel):
    """Validation model with enforcement strategies."""
    rules: List[ValidationRule]

    def get_rules_by_enforcement(self, enforcement_type: EnforcementType) -> List[ValidationRule]:
        return [r for r in self.rules if r.enforcement.type == enforcement_type]

    def get_rules_for_entity(self, entity_name: str) -> List[ValidationRule]:
        return [r for r in self.rules if r.entity == entity_name]
```

**Tests**: `tests/cognitive/ir/test_enforcement_strategy.py`
```python
def test_enforcement_strategy_creation():
    """Test EnforcementStrategy creation."""
    strategy = EnforcementStrategy(
        type=EnforcementType.COMPUTED_FIELD,
        implementation="@computed_field",
        applied_at=["schema"],
        template_name="computed_field_sum",
        parameters={"calculation": "sum of items"}
    )
    assert strategy.type == EnforcementType.COMPUTED_FIELD
    assert strategy.template_name == "computed_field_sum"

def test_validation_rule_with_enforcement():
    """Test ValidationRule with enforcement."""
    rule = ValidationRule(
        field="total_amount",
        entity="Order",
        rule_type="computed",
        constraint="sum of order items",
        enforcement=EnforcementStrategy(
            type=EnforcementType.COMPUTED_FIELD,
            implementation="@computed_field",
            applied_at=["schema"]
        )
    )
    assert rule.enforcement.type == EnforcementType.COMPUTED_FIELD

def test_validation_model_get_rules_by_enforcement():
    """Test getting rules by enforcement type."""
    model = ValidationModelIR(rules=[
        ValidationRule(
            field="total",
            rule_type="computed",
            constraint="auto-calculated",
            enforcement=EnforcementStrategy(
                type=EnforcementType.COMPUTED_FIELD,
                implementation="@computed_field",
                applied_at=["schema"]
            )
        ),
        ValidationRule(
            field="created_at",
            rule_type="immutable",
            constraint="read-only",
            enforcement=EnforcementStrategy(
                type=EnforcementType.IMMUTABLE,
                implementation="exclude=True",
                applied_at=["schema"]
            )
        )
    ])

    computed = model.get_rules_by_enforcement(EnforcementType.COMPUTED_FIELD)
    assert len(computed) == 1
    assert computed[0].field == "total"
```

**Validation**:
- ✅ EnforcementStrategy pydantic model validates all fields
- ✅ EnforcementType enum has 6 valid values
- ✅ ValidationRule can be created with enforcement
- ✅ ValidationModelIR helper methods work
- ✅ Serialization/deserialization preserves enforcement

---

### Task 2: Update BusinessLogicExtractor

**File**: `src/services/business_logic_extractor.py`

**Current Code** (lines 50-120):
```python
def _extract_from_field_descriptions(self, entities):
    """Extract validations from field descriptions."""
    rules = []

    for entity in entities:
        for field in entity.get("fields", []):
            # Current: Only creates basic ValidationRule
            rules.append(ValidationRule(
                field=field.get("name"),
                rule_type="validation",
                constraint=field.get("description", "")
            ))

    return rules
```

**New Code** (with enforcement):
```python
def _extract_from_field_descriptions(self, entities):
    """Extract validations from field descriptions with enforcement."""
    from src.cognitive.ir.validation_model import (
        EnforcementType,
        EnforcementStrategy,
        ValidationRule
    )

    rules = []

    for entity in entities:
        entity_name = entity.get("name")

        for field in entity.get("fields", []):
            field_name = field.get("name")
            field_desc = field.get("description", "").lower()

            # Determine enforcement strategy
            enforcement = self._determine_enforcement_strategy(
                field_name=field_name,
                field_desc=field_desc,
                field_type=field.get("type"),
                entity_name=entity_name
            )

            # Create enriched ValidationRule
            rule = ValidationRule(
                field=field_name,
                entity=entity_name,
                rule_type=self._infer_rule_type(field_desc),
                constraint=field.get("description", ""),
                enforcement=enforcement,  # ← NEW
                source="spec",
                confidence=1.0
            )
            rules.append(rule)

    return rules

def _determine_enforcement_strategy(self, field_name, field_desc, field_type, entity_name):
    """Determine enforcement strategy for field."""
    from src.cognitive.ir.validation_model import EnforcementType, EnforcementStrategy

    # Computed fields: auto-calculated, derived, sum of, etc.
    if any(kw in field_desc for kw in ["auto-calculated", "computed", "sum of", "derived"]):
        calc_logic = self._extract_calculation_logic(field_desc, field_name)
        return EnforcementStrategy(
            type=EnforcementType.COMPUTED_FIELD,
            implementation=calc_logic or "@computed_field",
            applied_at=["schema"],
            template_name="computed_field",
            parameters={"calculation": field_desc}
        )

    # Immutable/read-only fields
    if any(kw in field_desc for kw in ["read-only", "immutable", "cannot change"]):
        return EnforcementStrategy(
            type=EnforcementType.IMMUTABLE,
            implementation="exclude=True",
            applied_at=["schema"],
            template_name="immutable_field",
            parameters={"reason": field_desc}
        )

    # Snapshot fields: capture value at creation
    if "snapshot" in field_desc or "at time of" in field_desc:
        return EnforcementStrategy(
            type=EnforcementType.BUSINESS_LOGIC,
            implementation="capture_value_at_creation",
            applied_at=["service"],
            template_name="snapshot_field",
            parameters={"source": entity_name}
        )

    # Validator fields: unique, validation, requires, etc.
    if any(kw in field_desc for kw in ["unique", "validate", "requires", "must"]):
        return EnforcementStrategy(
            type=EnforcementType.VALIDATOR,
            implementation=f"validate_{field_name}",
            applied_at=["schema"],
            template_name="field_validator",
            parameters={"constraints": field_desc}
        )

    # Default: Description only (no enforcement)
    return EnforcementStrategy(
        type=EnforcementType.DESCRIPTION,
        implementation="description_only",
        applied_at=[],
        template_name=None,
        parameters={}
    )

def _infer_rule_type(self, field_desc):
    """Infer rule type from description."""
    if "computed" in field_desc or "auto" in field_desc:
        return "computed"
    if "read-only" in field_desc or "immutable" in field_desc:
        return "immutable"
    if "snapshot" in field_desc:
        return "snapshot"
    if "unique" in field_desc or "validate" in field_desc:
        return "validation"
    return "constraint"

def _extract_calculation_logic(self, description, field_name):
    """Extract calculation logic from description."""
    if "sum" in description or "total" in field_name.lower():
        return "@computed_field\n@property\ndef total(self):\n    return sum(...)"
    return None
```

**Tests**: `tests/services/test_business_logic_extractor_enforcement.py`
```python
def test_extract_with_enforcement_strategy():
    """Test BusinessLogicExtractor creates ValidationRules with enforcement."""
    extractor = BusinessLogicExtractor()

    entities = [{
        "name": "Order",
        "fields": [
            {
                "name": "total_amount",
                "type": "decimal",
                "description": "Auto-calculated field: sum of all item totals"
            },
            {
                "name": "created_at",
                "type": "datetime",
                "description": "Immutable: timestamp set at record creation"
            }
        ]
    }]

    rules = extractor._extract_from_field_descriptions(entities)

    # Verify enforcement strategies
    total_rule = [r for r in rules if r.field == "total_amount"][0]
    assert total_rule.enforcement.type == EnforcementType.COMPUTED_FIELD
    assert "@computed_field" in total_rule.enforcement.implementation

    created_rule = [r for r in rules if r.field == "created_at"][0]
    assert created_rule.enforcement.type == EnforcementType.IMMUTABLE
    assert "exclude=True" in created_rule.enforcement.implementation
```

**Validation**:
- ✅ _determine_enforcement_strategy works for all types
- ✅ BusinessLogicExtractor creates ValidationRules with enforcement
- ✅ Enforcement metadata is preserved

---

## 🧪 Integration Tests

**File**: `tests/cognitive/ir/test_phase4_1_enforcement_strategy.py`

```python
import pytest
from src.cognitive.ir.validation_model import (
    EnforcementType,
    EnforcementStrategy,
    ValidationRule,
    ValidationModelIR
)

class TestEnforcementStrategy:
    """Tests for Phase 4.1 EnforcementStrategy."""

    def test_enforcement_strategy_serialization(self):
        """Test EnforcementStrategy can be serialized/deserialized."""
        strategy = EnforcementStrategy(
            type=EnforcementType.COMPUTED_FIELD,
            implementation="@computed_field",
            applied_at=["schema"],
            template_name="computed_field_sum",
            parameters={"calculation": "sum of items"}
        )

        # Serialize
        serialized = strategy.model_dump_json()

        # Deserialize
        deserialized = EnforcementStrategy.model_validate_json(serialized)

        assert deserialized.type == strategy.type
        assert deserialized.template_name == strategy.template_name

    def test_validation_rule_with_enforcement(self):
        """Test ValidationRule with EnforcementStrategy."""
        enforcement = EnforcementStrategy(
            type=EnforcementType.IMMUTABLE,
            implementation="exclude=True",
            applied_at=["schema"]
        )

        rule = ValidationRule(
            field="registration_date",
            entity="Customer",
            rule_type="immutable",
            constraint="read-only field",
            enforcement=enforcement
        )

        assert rule.enforcement.type == EnforcementType.IMMUTABLE
        assert "exclude=True" in rule.enforcement.implementation

    def test_validation_model_get_rules_by_enforcement(self):
        """Test ValidationModelIR helper methods."""
        computed_enforcement = EnforcementStrategy(
            type=EnforcementType.COMPUTED_FIELD,
            implementation="@computed_field",
            applied_at=["schema"]
        )

        immutable_enforcement = EnforcementStrategy(
            type=EnforcementType.IMMUTABLE,
            implementation="exclude=True",
            applied_at=["schema"]
        )

        model = ValidationModelIR(rules=[
            ValidationRule(
                field="total",
                entity="Order",
                rule_type="computed",
                constraint="sum",
                enforcement=computed_enforcement
            ),
            ValidationRule(
                field="created_at",
                entity="Order",
                rule_type="immutable",
                constraint="read-only",
                enforcement=immutable_enforcement
            )
        ])

        # Get by enforcement type
        computed = model.get_rules_by_enforcement(EnforcementType.COMPUTED_FIELD)
        assert len(computed) == 1
        assert computed[0].field == "total"

        # Get by entity
        order_rules = model.get_rules_for_entity("Order")
        assert len(order_rules) == 2

    def test_enforcement_type_enum_values(self):
        """Test EnforcementType enum has all required values."""
        assert EnforcementType.DESCRIPTION.value == "description"
        assert EnforcementType.VALIDATOR.value == "validator"
        assert EnforcementType.COMPUTED_FIELD.value == "computed_field"
        assert EnforcementType.IMMUTABLE.value == "immutable"
        assert EnforcementType.STATE_MACHINE.value == "state_machine"
        assert EnforcementType.BUSINESS_LOGIC.value == "business_logic"
```

---

## ✅ Success Criteria

1. ✅ EnforcementStrategy class created with proper fields
2. ✅ EnforcementType enum with 6 enforcement types
3. ✅ ValidationRule updated with enforcement field
4. ✅ ValidationModelIR has helper methods (get_rules_by_enforcement, get_rules_for_entity)
5. ✅ BusinessLogicExtractor creates ValidationRules with enforcement
6. ✅ Serialization/deserialization preserves enforcement
7. ✅ All tests pass (unit + integration)
8. ✅ Documentation updated

---

## 📊 Test Results Format

**When complete, report**:
```
✅ Phase 4.1 Implementation Complete

Tests Passed:
- test_enforcement_strategy_creation: PASS
- test_validation_rule_with_enforcement: PASS
- test_validation_model_get_rules_by_enforcement: PASS
- test_enforcement_type_enum_values: PASS
- test_enforcement_strategy_serialization: PASS
- test_business_logic_extractor_enforcement: PASS

Validation:
✅ EnforcementStrategy validates all fields
✅ ValidationRule has enforcement field
✅ BusinessLogicExtractor creates enforcement
✅ Serialization works
✅ Helper methods work

Ready for Phase 4.2: IRBuilder
```

---

## 🔗 Integration with Phase 4

**Prerequisite**: Phase 4.0 (Hierarchical Extraction) ✅ COMPLETE

**Enables**: Phase 4.2 (IRBuilder enforcement determination)

**Impact**:
- ValidationModelIR now has complete enforcement information
- Code generators can use correct patterns (no more description-only)
- Foundation for deterministic IR reproducibility
- Neo4j can persist enforcement metadata (Phase 4.3)

---

## 📅 Timeline

**Total Time**: 1.5 hours

| Task | Time | Status |
|------|------|--------|
| 1. Create EnforcementStrategy classes | 30 min | ⏳ TODO |
| 2. Update BusinessLogicExtractor | 40 min | ⏳ TODO |
| 3. Write integration tests | 20 min | ⏳ TODO |
| **Total** | **1.5 hours** | ⏳ READY |

---

**Status**: ⏳ READY FOR IMPLEMENTATION
**Next Phase**: Phase 4.2 - IRBuilder Enforcement Determination
**Prepared by**: Dany (SuperClaude)
**Date**: November 25, 2025
