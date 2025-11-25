# Phase 4.2: Update IRBuilder to Determine Enforcement

**Document Version**: 1.0
**Date**: November 25, 2025
**Status**: ✅ COMPLETADA
**Timeline**: 2 hours (planned) → 35 min (actual) - 71% más rápido ⚡
**Priority**: 🟡 IMPORTANT - Unblocked by Phase 4.1 ✅
**Completion Date**: November 25, 2025

---

## 📋 Executive Summary

### Problem Statement
**Current State**: ValidationRule has EnforcementStrategy metadata (Phase 4.1 ✅) but IRBuilder doesn't use it
**Gap**: When building ApplicationIR, enforcement strategies are not systematically determined or assigned
**Result**: IR has enforcement data but it's incomplete/inconsistent across all rules

### Solution: IRBuilder Enforcement Determination
Update IRBuilder to:
1. Receive ValidationModelIR with enforcement strategies from BusinessLogicExtractor
2. Determine optimal enforcement placement (schema/entity/service/endpoint)
3. Assign enforcement strategies to all ApplicationIR validation rules
4. Ensure consistency across entire IR structure

### Expected Outcomes
✅ All ApplicationIR validation rules have complete EnforcementStrategy
✅ Enforcement placement optimized for code generation
✅ Consistent enforcement metadata across IR
✅ Foundation for Phase 4.3 (Neo4j persistence)

---

## 🛠️ Implementation Plan

### Task 1: Analyze Current IRBuilder Structure
**File**: `src/cognitive/ir/ir_builder.py`
**Duration**: 20 min

**Actions**:
- Review current `build_from_spec()` method
- Understand how ValidationModelIR is integrated
- Identify where enforcement strategies should be applied
- Check how ApplicationIR receives validation rules

**Output**: Understanding of IR building flow

### Task 2: Enhance IRBuilder with Enforcement Logic
**File**: `src/cognitive/ir/ir_builder.py`
**Duration**: 60 min

**Changes**:
```python
class IRBuilder:
    def build_from_spec(self, spec: Dict[str, Any]) -> ApplicationIR:
        """Build ApplicationIR with enforcement strategies."""
        # 1. Extract validation model (has enforcement metadata)
        validation_ir = self.extractor.extract_validation_rules(spec)

        # 2. Determine enforcement placement for each rule
        for rule in validation_ir.rules:
            if rule.enforcement:
                rule = self._optimize_enforcement_placement(rule)

        # 3. Build complete IR with enforcement
        return self._build_ir_with_enforcement(spec, validation_ir)

    def _optimize_enforcement_placement(self, rule: ValidationRule) -> ValidationRule:
        """
        Optimize enforcement placement based on rule type and application context.

        Returns: Updated rule with optimized enforcement placement
        """
        enforcement = rule.enforcement
        if not enforcement:
            return rule

        # Optimize placement for different enforcement types
        if enforcement.type == EnforcementType.VALIDATOR:
            # Validators go to entity by default
            if "unique" in rule.condition.lower():
                # Unique validators should also check in service
                enforcement.applied_at = ["entity", "service"]
            else:
                enforcement.applied_at = ["entity"]

        elif enforcement.type == EnforcementType.IMMUTABLE:
            # Immutable fields: schema + entity
            enforcement.applied_at = ["schema", "entity"]

        elif enforcement.type == EnforcementType.COMPUTED_FIELD:
            # Computed fields: only entity (Pydantic @computed_field)
            enforcement.applied_at = ["entity"]

        elif enforcement.type == EnforcementType.STATE_MACHINE:
            # State machines: service + endpoint
            enforcement.applied_at = ["service", "endpoint"]

        elif enforcement.type == EnforcementType.BUSINESS_LOGIC:
            # Business logic: service layer only
            enforcement.applied_at = ["service"]

        rule.enforcement = enforcement
        return rule

    def _build_ir_with_enforcement(self, spec: Dict[str, Any], validation_ir: ValidationModelIR) -> ApplicationIR:
        """
        Build ApplicationIR ensuring all rules have enforcement strategies.

        Returns: Complete ApplicationIR with enforcement metadata
        """
        ir = ApplicationIR()

        # ... existing IR building logic ...

        # Add validation rules with enforcement metadata
        ir.validations = validation_ir.rules

        return ir
```

**Validation**:
- Verify each rule type has appropriate placement
- Ensure no conflicts in placement
- Check consistency with enforcement type

### Task 3: Write Integration Tests
**File**: `tests/validation/test_phase4_2_irbuilder_enforcement.py`
**Duration**: 40 min

**Test Cases**:
1. `test_irbuilder_with_enforcement_strategies` - Build IR with enforcement metadata
2. `test_enforcement_placement_optimization` - Verify placement logic
3. `test_consistency_across_ir_rules` - All rules have enforcement

**Success Criteria**:
- ✅ All 3 tests PASS
- ✅ Each enforcement type has correct placement
- ✅ Placement is consistent and optimized

---

## 📊 Success Criteria

1. ✅ IRBuilder receives ValidationModelIR with enforcement metadata
2. ✅ All ApplicationIR rules have EnforcementStrategy assigned
3. ✅ Enforcement placement optimized by type (validator→entity, immutable→schema+entity, etc.)
4. ✅ No conflicts in enforcement placement
5. ✅ Integration tests PASS (3/3)
6. ✅ Enforcement metadata round-trips through IR build

---

## 🔄 Phase Transition

**After Phase 4.2 Completion**:
→ Phase 4.3: Persist enforcement to Neo4j
→ Prerequisite: ApplicationIR has complete enforcement metadata ✅

**Blocked By**: Phase 4.1 ✅

---

## 📋 Checklist

- [x] Task 1: Analyze IRBuilder structure ✅
- [x] Task 2: Implement enforcement logic ✅
- [x] Task 3: Write integration tests ✅
- [x] Tests PASS (5/5) ✅
- [x] Documentation updated ✅

---

## 📝 Implementation Summary

**Files Modified**:
- `src/cognitive/ir/ir_builder.py` - Added `_optimize_enforcement_placement()` method
- `tests/validation/test_phase4_2_irbuilder_enforcement.py` - Created with 5 integration tests

**Key Changes**:
1. **Import EnforcementType**: Added to validation_model imports
2. **_optimize_enforcement_placement() method** (60 lines):
   - Routes enforcement to optimal layers based on type
   - VALIDATOR → schema + entity (+ service for UNIQUENESS)
   - IMMUTABLE → schema + entity
   - COMPUTED_FIELD → entity only
   - STATE_MACHINE → service + endpoint
   - BUSINESS_LOGIC → service only
3. **Integration into _build_validation_model()**: Optimizes all rules before returning ValidationModelIR

**Tests Created** (5 total):
1. test_enforcement_placement_validators
2. test_enforcement_placement_immutable
3. test_enforcement_placement_computed_field
4. test_enforcement_placement_state_machine
5. test_enforcement_placement_optimization_consistency

---

**Timeline**: 2 hours (planned) → 35 min (actual) - 71% más rápido ⚡
**Status**: ✅ PHASE 4.2 COMPLETADA

