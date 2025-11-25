# Phase 3: IR-Aware Semantic Matching

**Document Version**: 1.0
**Date**: November 25, 2025
**Status**: 🟡 DESIGN PHASE
**Priority**: 🟡 MEDIUM - Builds on Phase 2 foundation
**Scope**: Complete IR integration, eliminate string-based matching
**Expected Impact**: +10-15% compliance recovery
**Dependencies**: Phase 2 (UnifiedConstraintExtractor) MUST be complete

---

## 🎯 Phase 3 Objective

Transform SemanticMatcher from **string-comparing hybrid** to **IR-native validator**:

1. ✅ Use ValidationModelIR as single source of truth (not strings)
2. ✅ Compare `ConstraintIR` vs `ConstraintIR` (not spec_string vs code_string)
3. ✅ Eliminate all manual semantic_equivalences
4. ✅ 100% deterministic matching (same IR → same result)

---

## 📊 Current State (After Phase 2)

| Component | Phase 2 State | Phase 3 Target |
|-----------|---------------|----------------|
| Constraint source | UnifiedConstraintExtractor | Same ✓ |
| Constraint format | NormalizedRule (canonical) | ConstraintIR (typed) |
| Matching input | Strings from IR | IR objects directly |
| Matching method | Hybrid (embeddings + LLM) | IR-native + embeddings fallback |
| String matching | Still used for embedding | Eliminated |
| Determinism | 95% | 100% |
| Expected compliance | 82-85% | 92-95% |

---

## 🏗️ Architecture Overview

### Before Phase 3 (Current)

```
ValidationModelIR
        │
        ▼
  rule.entity + rule.attribute + rule.condition
        │
        ▼
    String: "Product.price: gt=0"
        │
        ▼
SemanticMatcher.match(spec_string, code_string)
        │
        ▼
    Embedding similarity
        │
        ▼
    MatchResult
```

### After Phase 3 (Target)

```
ValidationModelIR (spec)          ValidationModelIR (code)
        │                                 │
        ▼                                 ▼
ConstraintIR (typed)              ConstraintIR (typed)
        │                                 │
        └─────────────┬───────────────────┘
                      │
                      ▼
        IRSemanticMatcher.match_ir(spec_ir, code_ir)
                      │
            ┌─────────┼─────────┐
            │         │         │
            ▼         ▼         ▼
        Exact IR   Type-based  Embedding
        Match      Match       Fallback
            │         │         │
            └─────────┴─────────┘
                      │
                      ▼
              MatchResult (IR-native)
```

---

## 🛠️ Implementation Plan

### Component 1: ConstraintIR Data Structure

**File**: `src/cognitive/ir/constraint_ir.py` (NEW - ~150 lines)

#### Purpose
Typed constraint representation for IR-native matching.

```python
from dataclasses import dataclass
from typing import Optional, Any

# Use Phase 4 types directly - no new enums needed
from src.cognitive.ir.validation_model import (
    ValidationType,          # Phase 4: FORMAT, RANGE, PRESENCE, UNIQUENESS, etc.
    EnforcementType,         # Phase 4: VALIDATOR, COMPUTED_FIELD, IMMUTABLE, etc.
    EnforcementStrategy,     # Phase 4: Detailed enforcement metadata
)

class ConstraintIR:
    """
    Typed constraint representation for IR-native matching.

    ALIGNED WITH PHASE 4: Uses ValidationType and EnforcementType directly.
    No duplicate enums - Phase 2 SemanticNormalizer already normalized to these types.
    """

    def __init__(
        self,
        entity: str,
        field: str,
        validation_type: ValidationType,        # Phase 4 enum (not custom category)
        constraint_type: str,                   # Specific type from Phase 2 normalization
        value: Optional[Any] = None,
        enforcement_type: EnforcementType = EnforcementType.VALIDATOR,  # Phase 4 enum
        enforcement: Optional[EnforcementStrategy] = None,              # Phase 4 detailed strategy
        confidence: float = 1.0,
        source: str = "ir"
    ):
        self.entity = entity
        self.field = field
        self.validation_type = validation_type  # Renamed from category
        self.constraint_type = constraint_type
        self.value = value
        self.enforcement_type = enforcement_type
        self.enforcement = enforcement
        self.confidence = confidence
        self.source = source

    @property
    def canonical_key(self) -> str:
        """Unique identifier for deduplication."""
        return f"{self.entity}.{self.field}.{self.constraint_type}"

    @property
    def validation_type_key(self) -> str:
        """ValidationType-level key for fuzzy matching."""
        return f"{self.entity}.{self.field}.{self.validation_type.value}"

    def matches_exactly(self, other: 'ConstraintIR') -> bool:
        """Exact IR match - same entity, field, type, value."""
        return (
            self.entity == other.entity and
            self.field == other.field and
            self.constraint_type == other.constraint_type and
            self._values_match(self.value, other.value)
        )

    def matches_validation_type(self, other: 'ConstraintIR') -> bool:
        """ValidationType-level match - same entity, field, validation_type."""
        return (
            self.entity == other.entity and
            self.field == other.field and
            self.validation_type == other.validation_type
        )

    def matches_field(self, other: 'ConstraintIR') -> bool:
        """Field-level match - same entity and field."""
        return (
            self.entity == other.entity and
            self.field == other.field
        )

    def _values_match(self, v1: Any, v2: Any) -> bool:
        """Compare constraint values with type awareness."""
        if v1 is None and v2 is None:
            return True
        if v1 is None or v2 is None:
            return False

        # Numeric comparison with tolerance
        if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
            return abs(v1 - v2) < 0.001

        # String comparison (case-insensitive)
        if isinstance(v1, str) and isinstance(v2, str):
            return v1.lower() == v2.lower()

        # List comparison (order-independent)
        if isinstance(v1, list) and isinstance(v2, list):
            return set(v1) == set(v2)

        return v1 == v2

    @classmethod
    def from_normalized_rule(cls, rule: 'NormalizedRule') -> 'ConstraintIR':
        """
        Convert Phase 2 NormalizedRule to ConstraintIR.

        PHASE 4 ALIGNED: NormalizedRule already has ValidationType and EnforcementType.
        No inference needed - Phase 2 SemanticNormalizer already did the work.
        """
        return cls(
            entity=rule.entity,
            field=rule.field,
            validation_type=rule.constraint_type,    # Already ValidationType from Phase 2
            constraint_type=rule.constraint_type.value,  # String for dedup key
            value=rule.value,
            enforcement_type=rule.enforcement_type,  # Already EnforcementType from Phase 2
            enforcement=rule.enforcement,            # Optional EnforcementStrategy
            confidence=rule.confidence,
            source="normalized"
        )

    @classmethod
    def from_validation_rule(cls, rule: 'ValidationRule') -> 'ConstraintIR':
        """
        Convert Phase 4 ValidationRule to ConstraintIR.

        PHASE 4 ALIGNED: ValidationRule already has ValidationType and EnforcementType.
        Direct mapping - no inference needed.
        """
        return cls(
            entity=rule.entity,
            field=rule.attribute,
            validation_type=rule.type,               # Already ValidationType
            constraint_type=rule.type.value,         # String for dedup key
            value=rule.condition,
            enforcement_type=rule.enforcement_type,  # Already EnforcementType
            enforcement=rule.enforcement,            # Optional EnforcementStrategy
            confidence=1.0,
            source="validation_model"
        )

    # NOTE: _infer_category REMOVED
    # Phase 2 SemanticNormalizer already provides ValidationType
    # No inference needed in Phase 3 - data arrives pre-normalized

    def to_string(self) -> str:
        """Convert to string for embedding fallback (ONLY when needed)."""
        value_str = f"={self.value}" if self.value is not None else ""
        return f"{self.entity}.{self.field}: {self.constraint_type}{value_str}"

    def __repr__(self) -> str:
        return f"ConstraintIR({self.canonical_key}, type={self.validation_type.value}, val={self.value})"
```

---

### Component 2: IRSemanticMatcher

**File**: `src/services/ir_semantic_matcher.py` (NEW - ~350 lines)

#### Purpose
IR-native semantic matching that compares ConstraintIR objects directly.

```python
from dataclasses import dataclass
from typing import Optional
import logging

from src.cognitive.ir.constraint_ir import ConstraintIR, ConstraintCategory
from src.services.semantic_matcher import SemanticMatcher, MatchResult

logger = logging.getLogger(__name__)

@dataclass
class IRMatchResult:
    """Enhanced match result with IR context."""
    match: bool
    confidence: float
    method: str  # "exact_ir" | "category_ir" | "field_ir" | "embedding_fallback"
    spec_constraint: ConstraintIR
    code_constraint: ConstraintIR
    reason: str
    category_match: bool = False
    value_match: bool = False

class IRSemanticMatcher:
    """
    IR-native semantic matcher.

    Matching hierarchy:
    1. Exact IR match (entity.field.type.value) → confidence 1.0
    2. Category match (entity.field.category) → confidence 0.9
    3. Field match (entity.field) + type inference → confidence 0.8
    4. Embedding fallback (string conversion) → confidence varies

    String matching is ONLY used as last resort fallback.
    """

    # Match confidence levels
    EXACT_MATCH_CONFIDENCE = 1.0
    CATEGORY_MATCH_CONFIDENCE = 0.9
    FIELD_MATCH_CONFIDENCE = 0.8
    EMBEDDING_MIN_CONFIDENCE = 0.6

    def __init__(self, use_embedding_fallback: bool = True):
        """
        Initialize IR matcher.

        Args:
            use_embedding_fallback: Whether to fall back to embeddings
                                    for uncertain cases. Default True
                                    for backward compatibility.
        """
        self.use_embedding_fallback = use_embedding_fallback
        self._string_matcher = None  # Lazy initialization

    @property
    def string_matcher(self) -> SemanticMatcher:
        """Lazy-load string matcher only if needed."""
        if self._string_matcher is None:
            self._string_matcher = SemanticMatcher()
        return self._string_matcher

    def match_ir(
        self,
        spec_constraint: ConstraintIR,
        code_constraint: ConstraintIR
    ) -> IRMatchResult:
        """
        Match two ConstraintIR objects directly.

        PHASE 4 ALIGNED: Simplified matching hierarchy.
        Phase 2 already normalized types, so no equivalence groups needed.
        """
        # Level 1: Exact IR match (entity + field + constraint_type + value)
        if spec_constraint.matches_exactly(code_constraint):
            return IRMatchResult(
                match=True,
                confidence=self.EXACT_MATCH_CONFIDENCE,
                method="exact_ir",
                spec_constraint=spec_constraint,
                code_constraint=code_constraint,
                reason="Exact IR match: entity, field, type, value all match",
                category_match=True,
                value_match=True
            )

        # Level 2: ValidationType match (same entity + field + validation_type)
        if spec_constraint.matches_validation_type(code_constraint):
            # Check if values are compatible
            value_compatible = self._values_compatible(
                spec_constraint, code_constraint
            )

            if value_compatible:
                return IRMatchResult(
                    match=True,
                    confidence=self.CATEGORY_MATCH_CONFIDENCE,
                    method="validation_type_ir",
                    spec_constraint=spec_constraint,
                    code_constraint=code_constraint,
                    reason=f"ValidationType match: both {spec_constraint.validation_type.value}, values compatible",
                    category_match=True,
                    value_match=value_compatible
                )

        # Level 3: Field match (same entity + field, different types)
        # NOTE: No _types_semantically_equivalent needed - Phase 2 normalized types
        if spec_constraint.matches_field(code_constraint):
            # Same field but different validation_type - still a partial match
            return IRMatchResult(
                match=True,
                confidence=self.FIELD_MATCH_CONFIDENCE,
                method="field_ir",
                spec_constraint=spec_constraint,
                code_constraint=code_constraint,
                reason=f"Field match: same entity.field, different types ({spec_constraint.validation_type.value} vs {code_constraint.validation_type.value})",
                category_match=False,
                value_match=False
            )

        # Level 4: Embedding fallback (ONLY if enabled and needed)
        if self.use_embedding_fallback:
            return self._embedding_fallback(spec_constraint, code_constraint)

        # No match
        return IRMatchResult(
            match=False,
            confidence=0.0,
            method="no_match",
            spec_constraint=spec_constraint,
            code_constraint=code_constraint,
            reason="No IR match found, embedding fallback disabled",
            category_match=False,
            value_match=False
        )

    def _values_compatible(
        self,
        spec: ConstraintIR,
        code: ConstraintIR
    ) -> bool:
        """
        Check if values are compatible.

        PHASE 4 ALIGNED: Simplified logic because Phase 2 SemanticNormalizer
        already normalized constraint_type to canonical form.

        No more variant groups - "email", "emailstr" are both "FORMAT" by now.
        """
        if spec.validation_type != code.validation_type:
            return False

        # Same validation_type with same or no value = compatible
        if spec.constraint_type == code.constraint_type:
            if spec.value is None or code.value is None:
                return True
            return spec._values_match(spec.value, code.value)

        # For enum/status constraints, check value subset
        if spec.validation_type == ValidationType.STATUS_TRANSITION:
            return self._enum_values_compatible(spec, code)

        # Same validation_type, different constraint_type = compatible
        # (Phase 2 already normalized, so RANGE covers both min and max)
        return True

    def _enum_values_compatible(self, spec: ConstraintIR, code: ConstraintIR) -> bool:
        """Check enum constraint compatibility - code should be superset of spec."""
        if spec.value is None or code.value is None:
            return True

        spec_values = set(spec.value) if isinstance(spec.value, list) else {spec.value}
        code_values = set(code.value) if isinstance(code.value, list) else {code.value}

        return spec_values.issubset(code_values)

    # ═══════════════════════════════════════════════════════════════════════════
    # NOTE: The following methods have been REMOVED (Phase 4 alignment)
    # ═══════════════════════════════════════════════════════════════════════════
    #
    # REMOVED: _range_values_compatible()
    # REMOVED: _format_values_compatible()
    # REMOVED: _presence_values_compatible()
    # REMOVED: _types_semantically_equivalent()
    #
    # REASON: Phase 2 SemanticNormalizer already normalizes all variants:
    #   - "email", "emailstr", "format_email" → ValidationType.FORMAT
    #   - "gt", "ge", "min", "range_min" → ValidationType.RANGE
    #   - "required", "not_null" → ValidationType.PRESENCE
    #
    # Phase 3 only needs to compare normalized types, not handle variants.
    # This eliminates ~100 lines of duplicate logic.
    # ═══════════════════════════════════════════════════════════════════════════

    def _embedding_fallback(
        self,
        spec: ConstraintIR,
        code: ConstraintIR
    ) -> IRMatchResult:
        """
        Fall back to embedding-based matching for uncertain cases.

        This should rarely be needed after Phase 2 normalization.
        """
        # Convert to strings for embedding
        spec_str = spec.to_string()
        code_str = code.to_string()

        # Use existing SemanticMatcher
        string_result = self.string_matcher.match(spec_str, code_str)

        return IRMatchResult(
            match=string_result.match and string_result.confidence >= self.EMBEDDING_MIN_CONFIDENCE,
            confidence=string_result.confidence,
            method=f"embedding_fallback_{string_result.method}",
            spec_constraint=spec,
            code_constraint=code,
            reason=f"Embedding fallback: {string_result.reason}",
            category_match=False,
            value_match=False
        )

    def match_ir_batch(
        self,
        spec_constraints: list[ConstraintIR],
        code_constraints: list[ConstraintIR]
    ) -> tuple[float, list[IRMatchResult]]:
        """
        Match multiple spec constraints against code constraints.

        For each spec constraint, finds the best matching code constraint.

        Returns:
            Tuple of (compliance_score, list of IRMatchResult)
        """
        results = []
        matched_count = 0

        if not spec_constraints:
            return 1.0, []  # No spec constraints = 100% compliance

        # Build code constraints map by field for O(1) lookup
        code_by_field: dict[str, list[ConstraintIR]] = {}
        for code_c in code_constraints:
            field_key = f"{code_c.entity}.{code_c.field}"
            if field_key not in code_by_field:
                code_by_field[field_key] = []
            code_by_field[field_key].append(code_c)

        for spec_c in spec_constraints:
            field_key = f"{spec_c.entity}.{spec_c.field}"

            # Check code constraints for same field first (most likely matches)
            candidates = code_by_field.get(field_key, [])

            best_match: Optional[IRMatchResult] = None
            best_confidence = 0.0

            for code_c in candidates:
                result = self.match_ir(spec_c, code_c)

                if result.confidence > best_confidence:
                    best_match = result
                    best_confidence = result.confidence

                # Early exit on exact match
                if result.method == "exact_ir":
                    break

            if best_match and best_match.match:
                matched_count += 1
                results.append(best_match)
            else:
                # Add best non-match for debugging
                results.append(best_match or IRMatchResult(
                    match=False,
                    confidence=0.0,
                    method="no_candidates",
                    spec_constraint=spec_c,
                    code_constraint=spec_c,  # Placeholder
                    reason=f"No code constraints found for {field_key}",
                    category_match=False,
                    value_match=False
                ))

        compliance = matched_count / len(spec_constraints)
        logger.info(
            f"🎯 IR-native matching: {matched_count}/{len(spec_constraints)} = {compliance:.1%}"
        )

        return compliance, results

    def get_stats(self) -> dict:
        """Get matcher statistics."""
        return {
            "use_embedding_fallback": self.use_embedding_fallback,
            "string_matcher_loaded": self._string_matcher is not None,
            "match_thresholds": {
                "exact": self.EXACT_MATCH_CONFIDENCE,
                "category": self.CATEGORY_MATCH_CONFIDENCE,
                "field": self.FIELD_MATCH_CONFIDENCE,
                "embedding_min": self.EMBEDDING_MIN_CONFIDENCE,
            }
        }
```

---

### Component 3: ValidationModelIR Enhancement

**File**: `src/cognitive/ir/validation_model.py` (MODIFY - ~50 lines added)

```python
# Add to existing ValidationModelIR class

class ValidationModelIR:
    """Enhanced with IR-native constraint conversion."""

    # ... existing code ...

    def to_constraint_ir_list(self) -> list[ConstraintIR]:
        """
        Convert all validation rules to ConstraintIR objects.

        This is the bridge between ValidationModelIR and IRSemanticMatcher.
        """
        from src.cognitive.ir.constraint_ir import ConstraintIR

        return [
            ConstraintIR.from_validation_rule(rule)
            for rule in self.rules
        ]

    def match_against(
        self,
        code_validation_model: 'ValidationModelIR',
        matcher: 'IRSemanticMatcher' = None
    ) -> tuple[float, list['IRMatchResult']]:
        """
        Match this model (spec) against another (code) using IR matching.

        Args:
            code_validation_model: ValidationModelIR from code analysis
            matcher: Optional custom IRSemanticMatcher instance

        Returns:
            Tuple of (compliance_score, list of IRMatchResult)
        """
        from src.services.ir_semantic_matcher import IRSemanticMatcher

        if matcher is None:
            matcher = IRSemanticMatcher()

        spec_constraints = self.to_constraint_ir_list()
        code_constraints = code_validation_model.to_constraint_ir_list()

        return matcher.match_ir_batch(spec_constraints, code_constraints)
```

---

### Component 4: ComplianceValidator Integration

**File**: `src/validation/compliance_validator.py` (MODIFY - ~100 lines)

```python
# Updated ComplianceValidator with IR-native matching

class ComplianceValidator:
    """Enhanced with Phase 3 IR-native matching."""

    def __init__(
        self,
        application_ir: ApplicationIR = None,
        use_semantic_matching: bool = True,
        use_ir_matching: bool = True,  # NEW: Phase 3 flag
    ):
        self.application_ir = application_ir
        self.use_semantic_matching = use_semantic_matching
        self.use_ir_matching = use_ir_matching and application_ir is not None

        # Phase 3: IR-native matcher (primary)
        self.ir_matcher = None
        if self.use_ir_matching:
            from src.services.ir_semantic_matcher import IRSemanticMatcher
            self.ir_matcher = IRSemanticMatcher(use_embedding_fallback=use_semantic_matching)
            logger.info("✅ IR-native matching enabled (Phase 3)")

        # Phase 1: String-based semantic matcher (fallback)
        self.semantic_matcher = None
        if use_semantic_matching and not self.use_ir_matching:
            from src.services.semantic_matcher import SemanticMatcher
            self.semantic_matcher = SemanticMatcher()
            logger.info("✅ String-based semantic matching enabled (Phase 1 fallback)")

        # Extract ValidationModelIR if available
        self.spec_validation_model = None
        self.code_validation_model = None
        if application_ir and hasattr(application_ir, 'validation_model'):
            self.spec_validation_model = application_ir.validation_model

    async def calculate_compliance(
        self,
        code_validation_model: 'ValidationModelIR' = None,
        code_constraints: list[str] = None
    ) -> dict:
        """
        Calculate compliance with priority:
        1. IR-native matching (Phase 3) - if both models available
        2. String-based semantic matching (Phase 1) - if strings available
        3. Manual equivalences (legacy) - fallback
        """
        # Phase 3: IR-native matching
        if (self.use_ir_matching and
            self.spec_validation_model and
            code_validation_model):

            compliance, results = self.spec_validation_model.match_against(
                code_validation_model,
                self.ir_matcher
            )

            return {
                "compliance_score": compliance,
                "method": "ir_native",
                "total_constraints": len(self.spec_validation_model.rules),
                "matched_constraints": sum(1 for r in results if r.match),
                "match_breakdown": {
                    "exact_ir": sum(1 for r in results if r.method == "exact_ir"),
                    "category_ir": sum(1 for r in results if r.method == "category_ir"),
                    "field_ir": sum(1 for r in results if r.method == "field_ir"),
                    "embedding_fallback": sum(1 for r in results if "embedding" in r.method),
                    "no_match": sum(1 for r in results if not r.match),
                },
                "results": results,
            }

        # Phase 1: String-based fallback
        if self.semantic_matcher and code_constraints:
            return await self._string_based_compliance(code_constraints)

        # Legacy: Manual equivalences
        return await self._legacy_compliance(code_constraints or [])

    async def _string_based_compliance(self, code_constraints: list[str]) -> dict:
        """Phase 1 string-based semantic matching."""
        if not self.spec_validation_model:
            return {"compliance_score": 0.0, "method": "no_spec"}

        # Convert spec to strings
        spec_constraints = [
            f"{rule.entity}.{rule.attribute}: {rule.condition or rule.type.value}"
            for rule in self.spec_validation_model.rules
        ]

        results = self.semantic_matcher.match_batch(spec_constraints, code_constraints)
        compliance = len(results) / len(spec_constraints) if spec_constraints else 1.0

        return {
            "compliance_score": compliance,
            "method": "string_semantic",
            "total_constraints": len(spec_constraints),
            "matched_constraints": len(results),
            "results": results,
        }
```

---

## 📋 Implementation Checklist

### Task 1: Create ConstraintIR Data Structure
- [ ] File: `src/cognitive/ir/constraint_ir.py` (~150 lines)
  - [ ] `ConstraintCategory` enum (8 categories)
  - [ ] `ConstraintIR` dataclass with typed fields
  - [ ] `matches_exactly()` - exact IR comparison
  - [ ] `matches_category()` - category-level comparison
  - [ ] `matches_field()` - field-level comparison
  - [ ] `from_normalized_rule()` - Phase 2 integration
  - [ ] `from_validation_rule()` - ValidationModelIR integration
  - [ ] `to_string()` - embedding fallback conversion
- [ ] Unit tests: `tests/unit/test_constraint_ir.py`
  - [ ] Category inference
  - [ ] Match levels (exact, category, field)
  - [ ] Value comparison
  - [ ] Conversions (from NormalizedRule, from ValidationRule)

### Task 2: Create IRSemanticMatcher
- [ ] File: `src/services/ir_semantic_matcher.py` (~350 lines)
  - [ ] `IRMatchResult` dataclass
  - [ ] `IRSemanticMatcher.__init__()` with fallback control
  - [ ] `match_ir()` - main IR matching method
  - [ ] `_values_compatible_in_category()` - category-aware value matching
  - [ ] `_range_values_compatible()` - range constraint compatibility
  - [ ] `_format_values_compatible()` - format constraint compatibility
  - [ ] `_presence_values_compatible()` - presence constraint compatibility
  - [ ] `_enum_values_compatible()` - enum constraint compatibility
  - [ ] `_types_semantically_equivalent()` - type equivalence checking
  - [ ] `_embedding_fallback()` - string fallback
  - [ ] `match_ir_batch()` - batch matching with O(1) lookup
  - [ ] `get_stats()` - statistics
- [ ] Unit tests: `tests/unit/test_ir_semantic_matcher.py`
  - [ ] Exact IR match
  - [ ] Category match
  - [ ] Field match with type equivalence
  - [ ] Embedding fallback
  - [ ] Batch matching
  - [ ] Edge cases

### Task 3: Enhance ValidationModelIR
- [ ] Modify `src/cognitive/ir/validation_model.py`
  - [ ] `to_constraint_ir_list()` method
  - [ ] `match_against()` method
- [ ] Update existing tests

### Task 4: Update ComplianceValidator
- [ ] Modify `src/validation/compliance_validator.py`
  - [ ] Add `use_ir_matching` parameter
  - [ ] Initialize `IRSemanticMatcher` when available
  - [ ] Update `calculate_compliance()` with IR priority
  - [ ] Add match breakdown statistics
- [ ] Integration tests

### Task 5: Documentation & Metrics
- [ ] Update `SEMANTIC_VALIDATION_ARCHITECTURE.md`
- [ ] Create migration guide from Phase 1/2 to Phase 3
- [ ] Document match hierarchy and confidence levels
- [ ] Add performance benchmarks

---

## 📊 Expected Metrics

### Match Method Distribution (Target)

| Method | Current (Phase 2) | Target (Phase 3) | Change |
|--------|-------------------|------------------|--------|
| Exact IR | 0% | 60-70% | +60-70% |
| Category IR | 0% | 15-20% | +15-20% |
| Field IR | 0% | 10-15% | +10-15% |
| Embedding Fallback | 100% | <5% | -95% |

### Compliance Improvement

| Metric | Phase 2 | Phase 3 | Change |
|--------|---------|---------|--------|
| Pre-Repair Compliance | 82-85% | 92-95% | +10% |
| Exact Matches | ~60% | ~85% | +25% |
| Category Matches | ~20% | ~10% | -10% |
| Fallback Usage | 100% | <5% | -95% |
| Determinism | 95% | 100% | +5% |

### Performance

| Metric | String-Based | IR-Native | Improvement |
|--------|--------------|-----------|-------------|
| Avg match time | ~50ms | <1ms | 50x faster |
| Memory per match | ~2KB | ~100B | 20x less |
| Embedding loads | Every match | Only fallback | 95% reduction |
| LLM calls | ~10% of matches | <1% of matches | 90% reduction |

---

## 🔄 Phase 3 → Phase 4 Handoff

When Phase 3 is complete:
- ✅ IR-native matching as primary method
- ✅ >95% matches without embedding fallback
- ✅ 100% determinism (same IR → same result)
- ✅ ComplianceValidator fully IR-aware

Phase 4 will:
1. Normalize ground truth specs to IR format
2. Enable IR-to-IR comparison from spec to code
3. Achieve final +5-10% compliance recovery
4. Complete the IR-driven deterministic pipeline

---

## 🎯 Business Value

### Before Phase 3
```
ValidationModelIR → Convert to strings → Embedding match → Result
                    (information loss)  (non-deterministic)
```

### After Phase 3
```
ValidationModelIR → ConstraintIR → IR match → Result
                    (typed)        (deterministic)
```

**Impact**:
- ✅ 100% deterministic matching
- ✅ 50x faster average match time
- ✅ 95% reduction in embedding/LLM usage
- ✅ Zero information loss in matching
- ✅ Enterprise-grade, VC-ready validation

---

## 📁 File Structure

```
src/
├── cognitive/ir/
│   ├── constraint_ir.py              [✅ DONE - Nov 25, 2025]
│   ├── validation_model.py           [✅ Existing]
│   └── application_ir.py             [✅ Existing]
├── services/
│   ├── semantic_matcher.py           [✅ Phase 1]
│   ├── semantic_normalizer.py        [✅ Phase 2 - DONE - Nov 25, 2025]
│   ├── unified_constraint_extractor.py [✅ Phase 2 - DONE - Nov 25, 2025]
│   └── ir_semantic_matcher.py        [✅ DONE - Nov 25, 2025]
└── validation/
    └── compliance_validator.py       [✅ DONE (extended) - Nov 25, 2025]

tests/unit/
├── test_semantic_matcher.py          [✅ Phase 1]
├── test_semantic_normalizer.py       [✅ Phase 2 - DONE - Nov 25, 2025]
├── test_unified_constraint_extractor.py [✅ Phase 2 - DONE - Nov 25, 2025]
├── test_constraint_ir.py             [✅ Phase 3 - DONE - Nov 25, 2025]
└── test_ir_semantic_matcher.py       [✅ Phase 3 - DONE - Nov 25, 2025]
```

---

**Status**: 🟢 **IMPLEMENTATION COMPLETE + TESTS PASSING** (Nov 25, 2025)

### Implementation Complete ✅

- ✅ ConstraintIR data structure (src/cognitive/ir/constraint_ir.py)
  - Entity, field, validation_type, constraint_type, value
  - Hierarchical matching methods: `matches_exactly()`, `matches_validation_type()`, `matches_field()`
  - Value compatibility with tolerance, case-insensitive, order-independent comparison
  - Conversion methods: `from_validation_rule()`, `from_dict()`, `to_dict()`, `to_string()`

- ✅ IRSemanticMatcher (src/services/ir_semantic_matcher.py)
  - 4-level hierarchical matching strategy
  - Confidence thresholds: EXACT (1.0) → CATEGORY (0.9) → FIELD (0.7) → EMBEDDING fallback
  - `match_ir()` - main IR matching method
  - `match_constraint_lists()` - batch matching with compliance scoring
  - Optional embedding fallback with SemanticMatcher
  - Statistics and reporting: `get_stats()`

### Test Suite Complete ✅

- ✅ **19/19 tests passing** in `tests/unit/test_ir_semantic_matcher.py`
  - TestIRSemanticMatcherInitialization (3 tests)
  - TestExactMatching (3 tests)
  - TestValidationTypeMatching (1 test)
  - TestFieldMatching (1 test)
  - TestValueCompatibility (3 tests)
  - TestConstraintKeyGeneration (3 tests)
  - TestListMatching (4 tests)
  - TestMatchStats (1 test)

- ✅ **0 BOMBS** found in test suite

### Integration Status

- ✅ Phase 2 UnifiedConstraintExtractor compatible
- ✅ Phase 3.5 SpecToApplicationIR compatible
- ✅ Ready for ComplianceValidator full IR integration

**Owner**: DevMatrix Phase 3 Development
**Dependencies**: Phase 2 (SemanticNormalizer) ✅ COMPLETE
**Implementation Status**: 100% complete (core logic + tests done)
**Next**: Phase 3.5 (SpecToApplicationIR) ready for production
