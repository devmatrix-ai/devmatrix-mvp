# Validation System

**Version**: 2.0
**Date**: November 2025
**Status**: Production

---

## Overview

DevMatrix uses a **multi-layer validation system** with ApplicationIR as the semantic source of truth. The system has achieved **300x performance improvement** through IR-centric batch matching.

---

## Validation Architecture

```
                 SPEC
                  │
                  ▼
             ApplicationIR  ◄──────────────────────┐
                  │                                │
        ┌─────────┼─────────┐                      │
        ▼         ▼         ▼                      │
   OpenAPI     AST-Pyd.   AST-SQLA                 │
  Extractor     Extract.    Extract.               │
        │         │         │                      │
        └─────────┼─────────┘                      │
                  ▼                                │
        SemanticNormalizer                         │
        (Extractor Rules → IR Rules)               │
                  │                                │
                  ▼                                │
    ValidationModelIR (Canonical)                  │
    (entity.field.constraint_type → enforcement)  │
                  │                                │
                  └────────────────────────────────┘
                  │
                  ▼
         ComplianceValidator
         (IR-aware matching)
                  │
                  ▼
              CodeRepair
```

---

## Implementation Phases

### Phase 1: SemanticMatcher Hybrid ✅ COMPLETE

**Impact**: +25-30% compliance recovery

**File**: `src/services/semantic_matcher.py` (~400 lines)

```python
class SemanticMatcher:
    """Hybrid embeddings + LLM matcher."""

    def __init__(self):
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.llm_client = AnthropicClient()

    def match(self, spec_constraint: str, code_constraint: str) -> MatchResult:
        # Step 1: Embedding similarity
        similarity = self._embedding_similarity(spec_constraint, code_constraint)

        if similarity > 0.8:
            return MatchResult(matched=True, confidence=similarity)
        elif similarity < 0.5:
            return MatchResult(matched=False, confidence=similarity)

        # Step 2: LLM validation for uncertain cases
        return self._llm_validate(spec_constraint, code_constraint)
```

### Phase 2: Unified Constraint Extractor ✅ COMPLETE

**Impact**: +15-20% compliance recovery

**Files**:
- `src/services/semantic_normalizer.py`
- `src/services/unified_constraint_extractor.py`

```python
class SemanticNormalizer:
    def normalize_rule(self, rule, ir_context: ApplicationIR):
        """Normalize extracted rule to ApplicationIR canonical form."""
        canonical_entity = ir_context.resolve_entity(rule.entity)
        canonical_field = ir_context.resolve_field(canonical_entity, rule.field)
        canonical_type = ir_context.resolve_constraint_type(rule.constraint_type)

        return NormalizedRule(
            entity=canonical_entity,
            field=canonical_field,
            constraint_type=canonical_type,
            value=rule.value,
            enforcement_type=rule.enforcement_type
        )
```

**Key Innovation**: Merge by semantic ID:
```python
constraint_key = f"{entity}.{field}.{constraint_type}"
# "price" and "unit_price" → same IR field
# "createdAt", "creation_date" → same canonical field
```

### Phase 3: IR-Aware Semantic Matching ✅ COMPLETE

**Impact**: +10-15% compliance recovery, 300x faster

**File**: `src/services/ir_semantic_matcher.py` (~1025 lines)

```python
class IRSemanticMatcher:
    """Matches constraints using typed IR comparison."""

    CONFIDENCE_SCORES = {
        "EXACT": 1.0,      # Exact entity.field.type match
        "CATEGORY": 0.9,   # Same constraint category
        "FIELD": 0.7,      # Same field, different constraint
        "FALLBACK": 0.5    # String-based fallback
    }

    def batch_match(
        self,
        spec_constraints: List[ConstraintIR],
        code_constraints: List[ConstraintIR]
    ) -> List[MatchResult]:
        """O(n) batch matching using IR indexing."""
        # Build index for O(1) lookup
        code_index = self._build_constraint_index(code_constraints)

        results = []
        for spec in spec_constraints:
            key = f"{spec.entity}.{spec.field}.{spec.constraint_type}"
            if key in code_index:
                results.append(MatchResult(matched=True, confidence=1.0))
            else:
                results.append(self._fuzzy_match(spec, code_index))

        return results
```

**Performance Achievement**: 50+ minutes → <10 seconds (300x faster)

### Phase 4: Ground Truth Normalization ✅ COMPLETE

**Impact**: +5-10% compliance recovery

**File**: `src/specs/spec_to_application_ir.py`

Natural language specs are transformed to ApplicationIR dynamically:
1. Parse spec (natural language)
2. Transform to ApplicationIR (canonical) via `SpecToApplicationIR`
3. Evaluate ground truth against IR via `ir_compliance_checker`

---

## Validation Layers (QA Stratum)

### Layer 1: Structural Validation

```python
def validate_structure(code: str) -> ValidationResult:
    """Basic structural checks."""
    # py_compile check
    try:
        py_compile.compile(code, doraise=True)
    except py_compile.PyCompileError as e:
        return ValidationResult(passed=False, error=str(e))

    # AST parse check
    try:
        ast.parse(code)
    except SyntaxError as e:
        return ValidationResult(passed=False, error=str(e))

    # No pass-only functions
    if re.search(r"def \w+\([^)]*\):\s*pass\s*$", code, re.MULTILINE):
        return ValidationResult(passed=False, error="Dead code detected")

    return ValidationResult(passed=True)
```

### Layer 2: Database Validation

- `alembic upgrade head` - migrations apply cleanly
- Tables created with correct schema
- Constraints (FK, unique, check) applied correctly

### Layer 3: Contract Validation

- OpenAPI vs IR compliance
- Strict and relaxed compliance modes
- Endpoint coverage verification

### Layer 4: Smoke Tests

- `docker-compose up` verification
- Health endpoint responses
- Happy path API tests

---

## Regression Detection

**File**: `src/validation/basic_pipeline.py`

```python
KNOWN_REGRESSIONS = [
    {
        "id": "REG-001",
        "description": "Literal strings in server_default instead of sa.text()",
        "pattern": r"server_default=sa\.text\(['\"](?!.*\(\))[^'\"]+['\"]\)"
    },
    {
        "id": "REG-002",
        "description": "Using deprecated service.get_all() instead of service.list()",
        "pattern": r"service\.get_all\("
    },
    {
        "id": "REG-003",
        "description": "Functions with only 'pass' body (dead code)",
        "pattern": r"def \w+\([^)]*\):\s*pass\s*$"
    },
    {
        "id": "REG-010",
        "description": "Ellipsis placeholders (excluding valid Field(...))",
        "pattern": r"(?<![Ff]ield\()\.\.\.(?!\s*,|\s*\))|(?<!\w)Ellipsis(?!\w)"
    }
]

def check_regressions(code: str) -> List[RegressionViolation]:
    violations = []
    for reg in KNOWN_REGRESSIONS:
        if re.search(reg["pattern"], code, re.MULTILINE):
            violations.append(RegressionViolation(
                id=reg["id"],
                description=reg["description"]
            ))
    return violations
```

---

## Quality Gate Policies

**File**: `src/services/quality_gate.py`

| Environment | Semantic | IR Relaxed | Warnings | Regressions |
|-------------|----------|------------|----------|-------------|
| **DEV** | ≥90% | ≥70% | Allowed | Allowed |
| **STAGING** | =100% | ≥85% | Blocked | Blocked |
| **PRODUCTION** | =100% | ≥95% | Blocked | Blocked + 10 runs |

```python
class QualityGate:
    def evaluate(self, metrics: ValidationMetrics) -> GateResult:
        policy = self.policies[self.environment]

        checks = [
            ("semantic", metrics.semantic_compliance >= policy.semantic_threshold),
            ("ir_relaxed", metrics.ir_relaxed >= policy.ir_relaxed_threshold),
            ("warnings", not policy.block_warnings or metrics.warnings == 0),
            ("regressions", not policy.block_regressions or metrics.regressions == 0)
        ]

        passed = all(check[1] for check in checks)
        return GateResult(passed=passed, checks=checks)
```

---

## Expected Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Pre-Repair Compliance | 64.4% | 92-96% | +27.6% |
| Validations Compliance | 71.2% | 95%+ | +23.8% |
| Validation Loss | -35.6% | <5% | +30.6% |
| Constraint Match Rate | 23.6% | 85-98% | +61.4% |
| Repair Iterations | 3 | 0-1 | -66% |
| Matching Performance | 50+ min | <10 sec | 300x faster |

---

## ConstraintIR Type System

**File**: `src/cognitive/ir/constraint_ir.py`

```python
@dataclass
class ConstraintIR:
    entity: str
    field: str
    constraint_type: str  # FORMAT, RANGE, PRESENCE, etc.
    value: Any
    enforcement: str  # STRICT, SOFT, WARNING

    @classmethod
    def from_validation_string(cls, validation_str: str) -> "ConstraintIR":
        """Parse validation string to typed ConstraintIR."""
        # "price: ge(0.01)" → ConstraintIR(field="price", type="RANGE", value={"ge": 0.01})
        pass
```

---

## File Structure

```
src/
├── services/
│   ├── semantic_matcher.py              [✅ Phase 1]
│   ├── semantic_normalizer.py           [✅ Phase 2]
│   ├── unified_constraint_extractor.py  [✅ Phase 2]
│   ├── ir_semantic_matcher.py           [✅ Phase 3]
│   ├── ir_compliance_checker.py         [✅ E2E integrated]
│   └── ir_test_generator.py             [✅ E2E integrated]
├── cognitive/ir/
│   ├── constraint_ir.py                 [✅ Phase 3]
│   ├── validation_model.py              [✅ Enhanced]
│   └── application_ir.py                [✅ Enhanced]
└── validation/
    ├── compliance_validator.py          [✅ Phase 3]
    ├── basic_pipeline.py                [✅ Regression detection]
    └── qa_levels.py                     [✅ Fast/Heavy modes]

tests/unit/
├── test_semantic_matcher.py             [✅ 16/16 passing]
├── test_semantic_normalizer.py          [✅ Phase 2]
├── test_unified_constraint_extractor.py [✅ Phase 2]
└── test_ir_semantic_matcher.py          [✅ 19/19 passing]
```

---

## Why This Matters

### Before (Heuristic):
- Manual `semantic_equivalences` dict (~100 rules)
- String-based matching with regex patterns
- Extractors pulling different representations
- No canonical form → inconsistencies cascade

### After (IR-Centric):
- Single canonical form (ValidationModelIR)
- All extractors normalize to IR
- Matching compares IR rules, not strings
- Deterministic: same spec → same IR → same constraints
- Reproducible across domains

---

## Related Documentation

- [04-IR_SYSTEM.md](04-IR_SYSTEM.md) - ApplicationIR architecture
- [05-CODE_GENERATION.md](05-CODE_GENERATION.md) - Generation pipeline
- [08-RISKS_GAPS.md](08-RISKS_GAPS.md) - Known gaps

---

*DevMatrix - Validation System*
