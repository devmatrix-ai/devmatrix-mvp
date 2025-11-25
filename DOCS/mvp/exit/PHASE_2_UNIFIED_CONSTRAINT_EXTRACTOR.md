# Phase 2: Unified Constraint Extractor → IR Loader

**Document Version**: 1.2
**Date**: November 25, 2025
**Status**: ✅ **IMPLEMENTATION & TESTING COMPLETE - PRODUCTION READY** (Nov 25, 2025)
**Priority**: 🔴 CRITICAL - Foundation for Phases 3-4 full operationalization
**Scope**: Constraint normalization and unified extraction
**Expected Impact**: +15-20% compliance recovery
**Testing**: ✅ 57/57 Tests Passing (100% success rate)

- SemanticNormalizer: 41/41 tests PASSED
- UnifiedConstraintExtractor: 16/16 tests PASSED
- Integration Tests: All passing

---

## 🎯 Phase 2 Objective

Transform **divergent constraint representations** (OpenAPI literals, AST patterns, business logic rules) into a **unified ApplicationIR canonical form**, enabling:

1. ✅ Deterministic constraint identification across all extractors
2. ✅ Semantic deduplication (price ≡ unit_price → single canonical field)
3. ✅ Foundation for Phase 3 IR-aware matching
4. ✅ Reproducibility across domains and specs

---

## 📊 Current State

| Component | Current | Target | Gap |
|-----------|---------|--------|-----|
| Constraint detection | 148 found | 148 found | ✅ Working |
| Constraint deduplication | ~70% overlap | 100% dedup | -30% |
| Semantic alignment | 23.6% match | 85-90% match | -61.4% |
| Extractor consolidation | 3 divergent | 1 unified | N/A |
| Compliance (Phase 1 + Phase 2) | 64.4% | 82-85% | +18.1% |

**Why Phase 2 matters**: Phase 1 (SemanticMatcher) solved *recognition*. Phase 2 solves *normalization* so we're comparing apples-to-apples from the start.

---

## ✅ Testing Results

### SemanticNormalizer Test Suite (41 tests - 100% PASSED)

**Entity Resolution** (6 tests)

- Exact name matching
- Case-insensitive resolution
- Automatic pluralization (Product ↔ Products)
- Unknown entity handling

**Field Resolution** (5 tests)

- Case-insensitive field lookup
- Snake_case ↔ camelCase conversion
- Non-existent field handling

**Constraint Type Mapping** (6 tests)

- Email format patterns
- Range constraints (gt, min, max)
- Uniqueness and primary key constraints
- Required/presence constraints
- Status transition patterns
- Direct ValidationType enum matching

**Enforcement Type Mapping** (5 tests)

- Validator mapping
- Database constraint mapping
- Computed field enforcement
- State machine workflows
- Default enforcement fallback

**Value Normalization** (4 tests)

- String to numeric conversion
- Type-specific normalization
- Format preservation
- Null value handling

**Confidence Scoring** (3 tests)

- High confidence for exact matches
- Penalties for fuzzy matches
- Source priority impact

**Batch Operations** (5 tests)

- Multiple rule normalization
- Error handling and preservation
- Order preservation
- Case conversion utilities

### UnifiedConstraintExtractor Test Suite (16 tests - 100% PASSED)

**Constraint Key Generation** (2 tests)

- Semantic constraint key format
- Key uniqueness validation

**Source Inference** (4 tests)

- Business logic source detection
- Pydantic AST pattern recognition
- SQLAlchemy constraint detection
- Unknown source handling

**Semantic Merge** (4 tests)

- Duplicate removal
- Source priority enforcement
- Multi-source conflict resolution
- Merge result validation

**Extract All Integration** (2 tests)

- Empty spec handling
- ValidationModelIR output validation
  - ✅ Fixed: Replaced bomb assertion `>= 0` with proper `> 0` validation (ensures rules are actually extracted)

**Source Priority Ordering** (2 tests)

- SQLAlchemy > Pydantic > OpenAPI > Business Logic > Unknown
- Higher priority source overwriting

**ComplianceValidator Integration** (1 test)

- Extractor compatibility verification

### Quality Metrics

- **Total Tests**: 57
- **Pass Rate**: 100% (57/57)
- **Code Coverage**: Entity/field resolution, constraint type mapping, enforcement mapping, value normalization
- **Edge Cases**: Plural forms, case variations, missing fields, batch errors

---

## 🏗️ Architecture Overview

```
SOURCE CONSTRAINTS
        │
    ┌───┼───────────────────┐
    │   │                   │
    ▼   ▼                   ▼
OpenAPI AST-Pydantic   AST-SQLAlchemy  Business Logic
Extract. Extract.      Extract.         Patterns
    │   │                   │               │
    └───┼───────────────────┴───────────────┘
        │
        ▼
    SemanticNormalizer (NEW)
    - Resolve entity names → canonical entities
    - Resolve field names → canonical fields
    - Normalize constraint types → canonical types
    - Preserve enforcement strategy
        │
        ▼
    NormalizedRule
    (entity, field, constraint_type, value, enforcement)
        │
    ┌───┴───┐
    │       │
    ▼       ▼
Dedup    Merge (NEW)
by ID    (UnifiedConstraintExtractor)
    │       │
    └───┬───┘
        │
        ▼
ValidationModelIR Builder
(constraints → rules with enforcement)
        │
        ▼
ComplianceValidator + SemanticMatcher (Phase 1)
        │
        ▼
CodeRepair → Output
```

---

## 🛠️ Implementation Plan

### Component 1: SemanticNormalizer

**File**: `src/services/semantic_normalizer.py` (NEW - ~300 lines)

#### Core Purpose
Convert extracted constraints from any format to canonical ApplicationIR form.

#### Architecture

```python
@dataclass
class ConstraintRule:
    """Raw extracted constraint from any source."""
    entity: str              # "Product", "product", "PRODUCT"
    field: str               # "price", "unit_price", "unitPrice"
    constraint_type: str     # "range", "gt", "greater_than", "min"
    value: Optional[Any]     # 0, "0", [0, 1000]
    enforcement_type: str    # "validator", "database", "computed"
    source: str              # "openapi" | "ast_pydantic" | "ast_sqlalchemy" | "business_logic"

@dataclass
class NormalizedRule:
    """Canonical ApplicationIR form - aligned with Phase 4 ValidationRule."""
    entity: str              # Canonical entity name (from IR)
    field: str               # Canonical field name (from IR)
    constraint_type: ValidationType     # Phase 4 enum (FORMAT, RANGE, PRESENCE, etc.)
    value: Optional[Any]     # Normalized value
    enforcement_type: EnforcementType   # Phase 4 enum (VALIDATOR, COMPUTED_FIELD, IMMUTABLE, etc.)
    enforcement: Optional[EnforcementStrategy] = None  # Phase 4 detailed strategy
    confidence: float        # 0.0-1.0: certainty of normalization
    original_rule: ConstraintRule  # Reference to source

class SemanticNormalizer:
    """Normalizes constraints from multiple sources to canonical IR form."""

    def __init__(self, application_ir: ApplicationIR):
        """Initialize with ApplicationIR providing canonical forms."""
        self.ir = application_ir
        self.entity_mappings = self._build_entity_mappings()
        self.field_mappings = self._build_field_mappings()
        self.constraint_type_mappings = self._build_constraint_mappings()

    def normalize_rule(self, rule: ConstraintRule) -> NormalizedRule:
        """
        Convert extracted rule to canonical ApplicationIR form.

        Algorithm:
        1. Resolve entity name → canonical entity
        2. Resolve field name → canonical field (within entity)
        3. Normalize constraint type → canonical type
        4. Map enforcement type → canonical enforcement
        5. Return NormalizedRule with confidence score
        """
        # Step 1: Entity normalization
        canonical_entity = self._resolve_entity(rule.entity)
        if not canonical_entity:
            raise ValueError(f"Cannot resolve entity: {rule.entity}")

        # Step 2: Field normalization
        canonical_field = self._resolve_field(canonical_entity, rule.field)
        if not canonical_field:
            raise ValueError(
                f"Cannot resolve field '{rule.field}' in entity '{canonical_entity}'"
            )

        # Step 3: Constraint type normalization
        canonical_type = self._resolve_constraint_type(
            rule.constraint_type, canonical_field
        )
        if not canonical_type:
            raise ValueError(f"Cannot resolve constraint type: {rule.constraint_type}")

        # Step 4: Enforcement mapping
        canonical_enforcement = self._map_enforcement_type(rule.enforcement_type)

        # Step 5: Value normalization (type-specific)
        normalized_value = self._normalize_value(
            canonical_type, rule.value, canonical_field
        )

        return NormalizedRule(
            entity=canonical_entity,
            field=canonical_field,
            constraint_type=canonical_type,
            value=normalized_value,
            enforcement_type=canonical_enforcement,
            confidence=self._compute_confidence(rule),
            original_rule=rule
        )

    def _resolve_entity(self, entity_name: str) -> Optional[str]:
        """
        Resolve entity name to canonical form using ApplicationIR.

        Examples:
          "Product" → "Product"
          "product" → "Product"
          "PRODUCT" → "Product"
          "prod" → "Product" (if exact match in IR)
          "items" → "OrderItem" (if plural maps in IR)
        """
        # Exact match (case-insensitive)
        for entity in self.ir.entities:
            if entity.name.lower() == entity_name.lower():
                return entity.name

        # Plural/singular mapping
        if entity_name.endswith("s"):
            singular = entity_name[:-1]
            for entity in self.ir.entities:
                if entity.name.lower() == singular.lower():
                    return entity.name

        # Custom abbreviations (stored in IR or mapping)
        if entity_name in self.entity_mappings:
            return self.entity_mappings[entity_name]

        return None

    def _resolve_field(self, entity: str, field_name: str) -> Optional[str]:
        """
        Resolve field name within entity to canonical form.

        Examples:
          entity="Product", field="unit_price" → "unitPrice"
          entity="Product", field="unitPrice" → "unitPrice"
          entity="Product", field="price" → "price"
          entity="Order", field="created_at" → "createdAt"
        """
        ir_entity = self.ir.get_entity(entity)
        if not ir_entity:
            return None

        # Exact match (case-sensitive first, then insensitive)
        for field in ir_entity.fields:
            if field.name == field_name:
                return field.name

        for field in ir_entity.fields:
            if field.name.lower() == field_name.lower():
                return field.name

        # Snake case ↔ camelCase conversion
        canonical_field = self._convert_case(field_name)
        for field in ir_entity.fields:
            if field.name.lower() == canonical_field.lower():
                return field.name

        # Synonym mapping (field_name → canonical alias)
        if (entity, field_name) in self.field_mappings:
            return self.field_mappings[(entity, field_name)]

        return None

    def _resolve_constraint_type(
        self, constraint_type: str, field_name: str
    ) -> Optional[str]:
        """
        Resolve constraint type to canonical ValidationType enum.

        Examples:
          "EmailStr" → "FORMAT_EMAIL"
          "email validator" → "FORMAT_EMAIL"
          "gt=0" → "RANGE_MIN"
          "unique" → "UNIQUE"
          "PRIMARY KEY" → "PRIMARY_KEY"
          "exclude=True" → "IMMUTABLE"
        """
        # Direct ValidationType match
        for vtype in self.ir.validation_types:
            if vtype.name.lower() == constraint_type.lower():
                return vtype.name

        # Pattern-based matching
        constraint_lower = constraint_type.lower()

        # Email patterns
        if any(p in constraint_lower for p in ["email", "emailstr", "valid email"]):
            return "FORMAT_EMAIL"

        # Range patterns
        if any(p in constraint_lower for p in ["gt", "greater", "min", ">="]):
            return "RANGE_MIN"
        if any(p in constraint_lower for p in ["lt", "less", "max", "<="]):
            return "RANGE_MAX"

        # Uniqueness patterns
        if "unique" in constraint_lower or "distinct" in constraint_lower:
            return "UNIQUE"

        # Primary key patterns
        if "primary" in constraint_lower or "pk" in constraint_lower:
            return "PRIMARY_KEY"

        # Immutability patterns (field exclusion = immutable)
        if any(p in constraint_lower for p in ["exclude", "readonly", "immutable"]):
            return "IMMUTABLE"

        # Required/presence patterns
        if any(p in constraint_lower for p in ["required", "not null", "mandatory"]):
            return "REQUIRED"

        # Computed/read-only patterns
        if "computed" in constraint_lower or "generated" in constraint_lower:
            return "COMPUTED"

        # Custom mapping
        if constraint_type in self.constraint_type_mappings:
            return self.constraint_type_mappings[constraint_type]

        return None

    def _map_enforcement_type(self, enforcement_type: str) -> EnforcementType:
        """Map source enforcement type to Phase 4 EnforcementType enum."""
        from src.cognitive.ir.validation_model import EnforcementType

        enforcement_map = {
            "validator": EnforcementType.VALIDATOR,
            "database": EnforcementType.VALIDATOR,  # DB constraints → validator
            "computed_field": EnforcementType.COMPUTED_FIELD,
            "computed": EnforcementType.COMPUTED_FIELD,
            "immutable": EnforcementType.IMMUTABLE,
            "state_machine": EnforcementType.STATE_MACHINE,
            "business_logic": EnforcementType.BUSINESS_LOGIC,
            "description": EnforcementType.DESCRIPTION,
        }

        normalized = enforcement_type.lower().replace(" ", "_")
        return enforcement_map.get(normalized, EnforcementType.VALIDATOR)

    def _normalize_value(
        self, constraint_type: str, value: Any, field_name: str
    ) -> Any:
        """
        Normalize constraint value based on type.

        Examples:
          constraint_type="RANGE_MIN", value="0" → 0
          constraint_type="RANGE_MIN", value=0 → 0
          constraint_type="FORMAT_EMAIL", value=None → None
        """
        if value is None:
            return None

        if constraint_type in ["RANGE_MIN", "RANGE_MAX"]:
            try:
                return float(value) if isinstance(value, str) else value
            except (ValueError, TypeError):
                return value

        if constraint_type == "STRING_LENGTH":
            try:
                return int(value) if isinstance(value, str) else value
            except (ValueError, TypeError):
                return value

        # For other types, keep as-is
        return value

    def _compute_confidence(self, rule: ConstraintRule) -> float:
        """
        Compute confidence of normalization (0.0-1.0).

        High confidence: Exact matches in IR
        Medium confidence: Fuzzy matches, case variations
        Low confidence: Synonym mappings, pattern inference
        """
        if not hasattr(rule, '_normalization_steps'):
            return 0.95  # Default high confidence

        # Could add more sophisticated confidence tracking
        return 0.95

    def normalize_rules(
        self, rules: list[ConstraintRule]
    ) -> list[NormalizedRule]:
        """Normalize multiple rules, preserving errors as warnings."""
        normalized = []
        errors = []

        for rule in rules:
            try:
                normalized_rule = self.normalize_rule(rule)
                normalized.append(normalized_rule)
            except Exception as e:
                errors.append((rule, str(e)))
                logger.warning(f"Failed to normalize rule {rule}: {e}")

        return normalized, errors
```

---

### Component 2: UnifiedConstraintExtractor

**File**: `src/services/unified_constraint_extractor.py` (NEW - ~250 lines)

#### Core Purpose
Merge constraints from all sources, deduplicate by semantic ID, produce unified ValidationModelIR.

```python
class UnifiedConstraintExtractor:
    """
    Unified constraint extraction and merging.

    Flow:
    1. Extract from OpenAPI, AST-Pydantic, AST-SQLAlchemy, business logic
    2. Normalize all to ApplicationIR canonical form
    3. Merge by semantic constraint_key
    4. Output deduplicated ValidationModelIR
    """

    def __init__(self, application_ir: ApplicationIR):
        self.ir = application_ir
        self.normalizer = SemanticNormalizer(application_ir)
        self.openapi_extractor = OpenAPIExtractor()
        self.ast_pydantic_extractor = ASTConstraintExtractor()  # Pydantic variant
        self.ast_sqlalchemy_extractor = ASTConstraintExtractor()  # SQLAlchemy variant
        self.business_logic_extractor = BusinessLogicExtractor()

    async def extract_all(self, code_files: dict) -> ValidationModelIR:
        """
        Extract all constraints from all sources and merge to unified IR.

        Args:
            code_files: Dict mapping file paths to file contents

        Returns:
            ValidationModelIR with fully merged constraint set
        """
        # Step 1: Extract from all sources (can be parallelized)
        openapi_rules = await self.openapi_extractor.extract(code_files)
        ast_pydantic_rules = await self.ast_pydantic_extractor.extract(code_files)
        ast_sqlalchemy_rules = await self.ast_sqlalchemy_extractor.extract(code_files)
        business_logic_rules = await self.business_logic_extractor.extract(code_files)

        # Step 2: Convert to ConstraintRule format
        all_raw_rules = [
            *self._to_constraint_rules(openapi_rules, "openapi"),
            *self._to_constraint_rules(ast_pydantic_rules, "ast_pydantic"),
            *self._to_constraint_rules(ast_sqlalchemy_rules, "ast_sqlalchemy"),
            *self._to_constraint_rules(business_logic_rules, "business_logic"),
        ]

        logger.info(f"📊 Extracted {len(all_raw_rules)} total constraints from all sources")

        # Step 3: Normalize all to canonical form
        normalized_rules, norm_errors = self.normalizer.normalize_rules(all_raw_rules)

        if norm_errors:
            logger.warning(f"⚠️ {len(norm_errors)} normalization errors (will skip)")

        logger.info(f"✅ Normalized {len(normalized_rules)} constraints to canonical form")

        # Step 4: Merge and deduplicate
        merged_rules = self._semantic_merge(normalized_rules)

        logger.info(f"🔗 Merged to {len(merged_rules)} unique constraints")

        # Step 5: Build ValidationModelIR
        validation_model = self._build_validation_model_ir(merged_rules)

        return validation_model

    def _to_constraint_rules(
        self, extracted: list, source: str
    ) -> list[ConstraintRule]:
        """Convert extractor output to ConstraintRule format."""
        # This depends on extractor output format
        # Would be implemented based on existing extractors
        pass

    def _semantic_merge(self, normalized_rules: list[NormalizedRule]) -> list[NormalizedRule]:
        """
        Merge deduplicate by semantic ID: entity.field.constraint_type.

        Algorithm:
        1. Build constraint_key for each rule
        2. Group by constraint_key
        3. For duplicates, keep highest-confidence rule
        4. Return deduplicated list
        """
        constraint_map: dict[str, NormalizedRule] = {}

        for rule in normalized_rules:
            constraint_key = self._make_constraint_key(rule)

            if constraint_key not in constraint_map:
                # First occurrence
                constraint_map[constraint_key] = rule
            else:
                # Duplicate - keep higher confidence
                existing = constraint_map[constraint_key]
                if rule.confidence > existing.confidence:
                    logger.info(
                        f"🔄 Replacing duplicate {constraint_key} "
                        f"({existing.original_rule.source} @ {existing.confidence:.2f} "
                        f"→ {rule.original_rule.source} @ {rule.confidence:.2f})"
                    )
                    constraint_map[constraint_key] = rule
                else:
                    logger.debug(
                        f"✓ Keeping existing {constraint_key} from "
                        f"{existing.original_rule.source} over {rule.original_rule.source}"
                    )

        dedup_count = len(normalized_rules) - len(constraint_map)
        logger.info(f"🎯 Deduplicated: removed {dedup_count} duplicates")

        return list(constraint_map.values())

    def _make_constraint_key(self, rule: NormalizedRule) -> str:
        """
        Create semantic constraint key for deduplication.

        Key = "{entity}.{field}.{constraint_type}"

        This groups equivalent constraints across sources:
        - price.product.RANGE_MIN (OpenAPI extraction)
        - unit_price.product.RANGE_MIN (AST extraction)
        → Same key, deduplicated to one rule
        """
        return f"{rule.entity}.{rule.field}.{rule.constraint_type}"

    def _build_validation_model_ir(
        self, merged_rules: list[NormalizedRule]
    ) -> ValidationModelIR:
        """
        Build ValidationModelIR from merged normalized rules.

        Converts NormalizedRule → ValidationRule with enforcement mapping.
        """
        validation_rules = []

        for norm_rule in merged_rules:
            # Map normalized rule to ValidationRule
            validation_rule = ValidationRule(
                entity=norm_rule.entity,
                attribute=norm_rule.field,
                type=self._map_to_validation_type(norm_rule.constraint_type),
                condition=str(norm_rule.value) if norm_rule.value else None,
                enforcement_type=self._map_to_enforcement_type(norm_rule.enforcement_type),
                enforcement=self.ir.resolve_enforcement(norm_rule.enforcement_type),
                source_rule=norm_rule  # Keep reference to source
            )

            validation_rules.append(validation_rule)

        return ValidationModelIR(
            rules=validation_rules,
            merged_from_sources=[
                "openapi",
                "ast_pydantic",
                "ast_sqlalchemy",
                "business_logic"
            ]
        )

    def _map_to_validation_type(self, constraint_type: str) -> ValidationType:
        """Convert normalized constraint type to Phase 4 ValidationType enum."""
        from src.cognitive.ir.validation_model import ValidationType

        # Map specific constraint types to Phase 4 ValidationType categories
        type_map = {
            # Format constraints
            "FORMAT_EMAIL": ValidationType.FORMAT,
            "FORMAT_URL": ValidationType.FORMAT,
            "FORMAT_UUID": ValidationType.FORMAT,
            "FORMAT_PHONE": ValidationType.FORMAT,
            # Range constraints
            "RANGE_MIN": ValidationType.RANGE,
            "RANGE_MAX": ValidationType.RANGE,
            "STRING_LENGTH": ValidationType.RANGE,
            # Presence constraints
            "REQUIRED": ValidationType.PRESENCE,
            "OPTIONAL": ValidationType.PRESENCE,
            # Uniqueness constraints
            "UNIQUE": ValidationType.UNIQUENESS,
            "PRIMARY_KEY": ValidationType.UNIQUENESS,
            # Relationship constraints
            "FOREIGN_KEY": ValidationType.RELATIONSHIP,
            # Status/workflow constraints
            "ENUM": ValidationType.STATUS_TRANSITION,
            "STATE_MACHINE": ValidationType.STATUS_TRANSITION,
            # Custom/computed (not a ValidationType - handled via EnforcementType)
            "IMMUTABLE": ValidationType.CUSTOM,
            "COMPUTED": ValidationType.CUSTOM,
        }
        return type_map.get(constraint_type, ValidationType.CUSTOM)

    def _map_to_enforcement_type(self, enforcement_type: EnforcementType) -> EnforcementType:
        """Already EnforcementType from SemanticNormalizer - pass through."""
        # Phase 2 SemanticNormalizer already returns EnforcementType
        # This is a no-op for type consistency
        return enforcement_type
```

---

### Component 3: Integration Points

#### 3.1 With Phase 1 (SemanticMatcher)

**In ComplianceValidator**:
```python
class ComplianceValidator:
    def __init__(
        self,
        application_ir: ApplicationIR = None,
        use_semantic_matching: bool = True,
        use_unified_extractor: bool = True  # NEW Phase 2
    ):
        self.application_ir = application_ir
        self.semantic_matcher = SemanticMatcher() if use_semantic_matching else None

        # NEW: Use unified extractor if Phase 2 available
        if use_unified_extractor and application_ir:
            self.constraint_extractor = UnifiedConstraintExtractor(application_ir)
            self.validation_model = self.constraint_extractor.extract_all(code_files)
        else:
            self.validation_model = application_ir.validation_model if application_ir else None
```

#### 3.2 With Phase 3 (IR-Aware Matching)

Phase 3 will consume the ValidationModelIR produced by Phase 2:
```python
# Phase 1: SemanticMatcher.match() - string matching
# Phase 2: UnifiedConstraintExtractor - produces ValidationModelIR
# Phase 3: SemanticMatcher.match_from_validation_model() - IR matching
```

#### 3.3 With Phase 4 (Ground Truth)

Phase 4 will normalize spec constraints using same SemanticNormalizer:
```python
spec_constraints = parse_spec(spec_text)
normalized_spec = self.normalizer.normalize_rules(spec_constraints)
# Compare normalized_spec vs code_validation_model
```

#### 3.4 E2E Pipeline Integration

**Current Pipeline** (`tests/e2e/real_e2e_full_pipeline.py`):
```python
# Current call pattern
result = compliance_validator.validate_from_app(spec_requirements, output_path)
# - Reads files from disk
# - Imports FastAPI app
# - Extracts OpenAPI schema
# - Does compliance checking
```

**Phase 2 Integration Strategy**:

`validate_from_app()` becomes a **wrapper** that:
1. Reads code files from disk
2. Builds spec ValidationModelIR from requirements
3. Calls the new `validate_app()` (Phase 2 core logic)

```python
class ComplianceValidator:
    """Updated for Phase 2 with E2E pipeline compatibility."""

    async def validate_from_app(
        self,
        spec_requirements: dict,
        output_path: Path
    ) -> ComplianceResult:
        """
        Pipeline-compatible entry point.

        WRAPPER that maintains backward compatibility with existing E2E tests
        while using Phase 2 internal logic.

        Args:
            spec_requirements: Dict from spec parsing (current pipeline format)
            output_path: Path to generated app directory

        Returns:
            ComplianceResult compatible with existing pipeline expectations
        """
        # Step 1: Read code files from output directory
        code_files = self._read_app_files(output_path)

        # Step 2: Build spec ValidationModelIR from requirements
        spec_validation_model = self._build_spec_validation_model(spec_requirements)

        # Step 3: Call Phase 2 core logic
        return await self.validate_app(code_files, spec_validation_model)

    def _read_app_files(self, output_path: Path) -> dict[str, str]:
        """
        Read all relevant code files from generated app.

        Returns dict mapping file paths to contents:
        {
            "src/models/schemas.py": "...",
            "src/models/entities.py": "...",
            "src/api/routes.py": "...",
        }
        """
        code_files = {}

        # Patterns for relevant files
        patterns = [
            "src/models/*.py",
            "src/api/*.py",
            "src/services/*.py",
            "main.py",
        ]

        for pattern in patterns:
            for file_path in output_path.glob(pattern):
                if file_path.is_file():
                    relative_path = str(file_path.relative_to(output_path))
                    code_files[relative_path] = file_path.read_text()

        return code_files

    def _build_spec_validation_model(
        self,
        spec_requirements: dict
    ) -> ValidationModelIR:
        """
        Convert pipeline spec_requirements to ValidationModelIR.

        This bridges the gap between:
        - Pipeline format: {"entities": [...], "constraints": [...]}
        - Phase 2 format: ValidationModelIR with ValidationRules
        """
        # Use SemanticNormalizer to normalize spec constraints too
        spec_rules = []

        for entity_name, entity_data in spec_requirements.get("entities", {}).items():
            for field_name, field_data in entity_data.get("fields", {}).items():
                for constraint in field_data.get("constraints", []):
                    raw_rule = ConstraintRule(
                        entity=entity_name,
                        field=field_name,
                        constraint_type=constraint.get("type", ""),
                        value=constraint.get("value"),
                        enforcement_type=constraint.get("enforcement", "validator"),
                        source="spec"
                    )
                    spec_rules.append(raw_rule)

        # Normalize spec constraints using same normalizer
        normalized_spec, _ = self.unified_extractor.normalizer.normalize_rules(spec_rules)

        # Build ValidationModelIR
        return self.unified_extractor._build_validation_model_ir(normalized_spec)

    async def validate_app(
        self,
        code_files: dict[str, str],
        spec_validation_model: ValidationModelIR = None
    ) -> ComplianceResult:
        """
        Core Phase 2 validation logic.

        This is the NEW entry point that Phase 2 introduces.
        All validation flows through here.

        Args:
            code_files: Dict mapping file paths to file contents
            spec_validation_model: Expected constraints from spec

        Returns:
            ComplianceResult with scores and detailed breakdown
        """
        # Step 1: Extract and normalize code constraints
        code_validation_model = await self.unified_extractor.extract_all(code_files)

        # Step 2: Get spec model (from parameter or IR)
        spec_model = spec_validation_model or (
            self.application_ir.validation_model if self.application_ir else None
        )

        if not spec_model:
            raise ValueError("No spec validation model available")

        # Step 3: Match spec vs code
        # Phase 1: SemanticMatcher
        # Phase 3: IRSemanticMatcher (future)
        compliance, match_results = self.semantic_matcher.match_from_validation_model(
            spec_model,
            [f"{r.entity}.{r.attribute}: {r.condition}" for r in code_validation_model.rules]
        )

        return ComplianceResult(
            compliance_score=compliance,
            matched_constraints=len([r for r in match_results if r.match]),
            total_constraints=len(spec_model.rules),
            match_details=match_results,
            code_validation_model=code_validation_model,
            spec_validation_model=spec_model
        )
```

**Pipeline Flow After Phase 2**:
```
┌─────────────────────────────────────────────────────────────────┐
│                    E2E Pipeline (unchanged API)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  compliance_validator.validate_from_app(spec, output_path)      │
│                           │                                      │
│                           ▼                                      │
│  ┌───────────────────────────────────────────────────────┐      │
│  │          validate_from_app() [WRAPPER]                │      │
│  │  1. _read_app_files(output_path) → code_files        │      │
│  │  2. _build_spec_validation_model(spec) → spec_ir     │      │
│  │  3. validate_app(code_files, spec_ir) → result       │      │
│  └───────────────────────────────────────────────────────┘      │
│                           │                                      │
│                           ▼                                      │
│  ┌───────────────────────────────────────────────────────┐      │
│  │           validate_app() [PHASE 2 CORE]               │      │
│  │  1. unified_extractor.extract_all(code_files)        │      │
│  │  2. semantic_matcher.match_from_validation_model()   │      │
│  │  3. return ComplianceResult                          │      │
│  └───────────────────────────────────────────────────────┘      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Benefits**:
1. ✅ **Backward compatible**: Existing E2E tests work unchanged
2. ✅ **Single entry point**: All validation flows through `validate_app()`
3. ✅ **Testable**: `validate_app()` can be unit tested with mock code_files
4. ✅ **Phase 3 ready**: `validate_app()` is where IR-aware matching plugs in

---

## 📋 Implementation Checklist

### Task 1: Create SemanticNormalizer
- [ ] File: `src/services/semantic_normalizer.py` (~300 lines)
  - [ ] `SemanticNormalizer.__init__()` with IR context
  - [ ] `normalize_rule()` core algorithm (5 steps)
  - [ ] `_resolve_entity()` with fuzzy matching
  - [ ] `_resolve_field()` with case conversion
  - [ ] `_resolve_constraint_type()` with pattern matching
  - [ ] `_map_enforcement_type()` normalization
  - [ ] `_normalize_value()` type-specific handling
  - [ ] `_compute_confidence()` scoring
  - [ ] `normalize_rules()` batch processing
- [ ] Unit tests: `tests/unit/test_semantic_normalizer.py`
  - [ ] Entity resolution (exact, fuzzy, plural)
  - [ ] Field resolution (camelCase/snake_case)
  - [ ] Constraint type normalization (all 8 types)
  - [ ] Enforcement mapping
  - [ ] Value normalization
  - [ ] Confidence scoring
  - [ ] Batch processing
  - [ ] Error handling

### Task 2: Create UnifiedConstraintExtractor
- [ ] File: `src/services/unified_constraint_extractor.py` (~250 lines)
  - [ ] `UnifiedConstraintExtractor.__init__()` with all extractors
  - [ ] `extract_all()` orchestration method
  - [ ] `_to_constraint_rules()` format conversion
  - [ ] `_semantic_merge()` deduplication algorithm
  - [ ] `_make_constraint_key()` key generation
  - [ ] `_build_validation_model_ir()` IR construction
  - [ ] Mapping methods (type, enforcement)
- [ ] Unit tests: `tests/unit/test_unified_constraint_extractor.py`
  - [ ] Multi-source extraction
  - [ ] Deduplication logic
  - [ ] Constraint key generation
  - [ ] Confidence-based merging
  - [ ] ValidationModelIR building
  - [ ] Error handling
  - [ ] Source tracking

### Task 3: Integrate with Phase 1
- [ ] Modify `src/validation/compliance_validator.py`
  - [ ] Add `use_unified_extractor` parameter
  - [ ] Initialize UnifiedConstraintExtractor if available
  - [ ] Use produced ValidationModelIR as primary source
  - [ ] Fallback to manual IR if unavailable
- [ ] Update integration tests

### Task 4: Documentation
- [ ] Create `DOCS/mvp/exit/SEMANTIC_NORMALIZER_REFERENCE.md`
- [ ] Create `DOCS/mvp/exit/CONSTRAINT_EQUIVALENCE_MAPPING.md`
  - Entity mappings (product/Product, etc.)
  - Field mappings (price/unit_price/unitPrice, etc.)
  - Constraint type mappings (all patterns)
- [ ] Update architecture diagrams in main document
- [ ] Add examples of normalization flows

### Task 5: Metrics & Validation
- [ ] Create test suite validating:
  - [ ] 100% constraint coverage (all detected constraints map to IR)
  - [ ] 0% false deduplication (no valid constraints merged incorrectly)
  - [ ] >95% confidence for exact matches
  - [ ] >85% confidence for fuzzy matches
  - [ ] Deterministic: Same input → Same output (verified 10 runs)
- [ ] Measure:
  - [ ] Deduplication ratio (how many duplicates found)
  - [ ] Confidence distribution
  - [ ] Normalization errors and fallback rate

---

## 🔄 Expected Workflow

### Execution Phase
1. **Extract** (parallel): OpenAPI + AST-Pydantic + AST-SQLAlchemy + Business Logic
2. **Normalize**: Each source → canonical form via SemanticNormalizer
3. **Merge**: Deduplicate by entity.field.constraint_type key
4. **Build**: Unified ValidationModelIR
5. **Validate**: Compliance checking with Phase 1 SemanticMatcher

### Success Criteria
| Metric | Phase 1 | Phase 1+2 | Target |
|--------|---------|----------|--------|
| Constraint detection | 148 | 148 | 148 ✓ |
| Deduplication ratio | 70% | 100% | 100% ✓ |
| Constraint match rate | 58.1% | 82.5% | 85%+ ✓ |
| Compliance pre-repair | 64.4% | 82-85% | 92%+ |
| Determinism | 95% | 100% | 100% ✓ |

**Total expected gain**: +18% compliance from Phase 2 alone

---

## 📁 File Structure

```
src/
├── services/
│   ├── semantic_matcher.py                  [✅ Phase 1]
│   ├── semantic_normalizer.py               [🟡 Phase 2 - PENDING IMPLEMENTATION]
│   ├── unified_constraint_extractor.py      [🟡 Phase 2 - PENDING IMPLEMENTATION]
│   ├── ir_semantic_matcher.py               [✅ Phase 3 - DONE Nov 25]
│   └── business_logic_extractor.py          [✅ Existing]
├── specs/
│   └── spec_to_application_ir.py            [✅ Phase 3.5 - DONE Nov 25]
└── validation/
    └── compliance_validator.py              [✅ Extended Nov 25]

tests/unit/
├── test_semantic_matcher.py                 [✅ Phase 1]
├── test_semantic_normalizer.py              [🟡 Phase 2 - PENDING]
├── test_unified_constraint_extractor.py     [🟡 Phase 2 - PENDING]
├── test_constraint_ir.py                    [🟡 Phase 3 - PENDING]
└── test_ir_semantic_matcher.py              [🟡 Phase 3 - PENDING]
```

---

## 🚀 Phase 2 → Phase 3 Handoff

When Phase 2 is complete:
- ✅ Unified ValidationModelIR available
- ✅ All constraints normalized to canonical form
- ✅ Deduplication at 100%
- ✅ Semantic confidence scores attached

Phase 3 will:
1. Use unified ValidationModelIR as primary source
2. Enhance SemanticMatcher to be fully IR-aware
3. Remove string-based matching entirely
4. Achieve +10-15% additional compliance recovery

---

## 📊 Business Value

### Before Phase 2 (Phase 1 only)
```
spec → string extraction
code → string extraction
→ SemanticMatcher (embeddings + LLM)
→ Some matches recognized, some missed
Problem: Divergent source representations
```

### After Phase 2
```
spec → extraction → NORMALIZATION → Canonical IR
code → extraction → NORMALIZATION → Canonical IR
→ SemanticMatcher (IR-aware)
→ All equivalent constraints recognized
Problem: SOLVED ✓
```

**Impact**: Enterprise-grade semantic validation pipeline, VC-ready, reproducible across domains.

---

## 🎯 Next Phase: Phase 3

Once Phase 2 complete, Phase 3 will:
1. Make SemanticMatcher fully IR-aware
2. Remove all string-based matching
3. Use ValidationModelIR as explicit contract
4. Expected: +10-15% additional compliance recovery
5. Total: 64.4% → 92-95% (VC-ready target)

---

**Status**: 🔴 **CRITICAL BLOCKER - PENDING IMPLEMENTATION** (Nov 25, 2025)

**What's Done**:
- ✅ Phase 3 (IRSemanticMatcher) - IMPLEMENTED
- ✅ Phase 3.5 (SpecToApplicationIR) - IMPLEMENTED
- ✅ ComplianceValidator (extended with Phase 3.5 integration methods) - DONE

**What's Blocking Phase 3/3.5 Full Operationalization**:
- 🟡 SemanticNormalizer (converts constraints to Phase 4 types)
- 🟡 UnifiedConstraintExtractor (unifies multi-source extraction)
- 🟡 Tests for all Phase 2 components

**Critical Issue**: Phase 3 + 3.5 are implemented but cannot work end-to-end without Phase 2's SemanticNormalizer to normalize extracted constraints to ValidationType/EnforcementType.

**Owner**: DevMatrix Phase 2 Development
**Priority**: URGENT - Unblocks 2 completed phases
**Impact**: Phase 2 implementation = immediate 15-20% compliance recovery

---

## 🔧 REVISION 1.1: Critical Corrections

**Date**: November 25, 2025
**Based on**: Expert review feedback

### ❌ Issue 1: ComplianceValidator Integration Unrealistic

**Problem**: Original design showed `code_files` in `__init__`, but it doesn't exist there.

**Original (WRONG)**:
```python
class ComplianceValidator:
    def __init__(..., use_unified_extractor: bool = True):
        if use_unified_extractor and application_ir:
            self.constraint_extractor = UnifiedConstraintExtractor(application_ir)
            self.validation_model = self.constraint_extractor.extract_all(code_files)  # ❌ code_files doesn't exist here!
```

**Corrected (RIGHT)**:
```python
class ComplianceValidator:
    def __init__(
        self,
        application_ir: ApplicationIR = None,
        use_semantic_matching: bool = True,
        use_unified_extractor: bool = True
    ):
        self.application_ir = application_ir
        self.use_unified_extractor = use_unified_extractor

        # Initialize extractor (lazy - no extraction yet)
        self.unified_extractor = (
            UnifiedConstraintExtractor(application_ir)
            if use_unified_extractor and application_ir
            else None
        )

        # Phase 1 matcher for fallback
        self.semantic_matcher = (
            SemanticMatcher() if use_semantic_matching else None
        )

    async def validate_app(
        self,
        code_files: dict,
        spec_validation_model: ValidationModelIR = None
    ) -> ComplianceResult:
        """
        Main validation entry point.

        Args:
            code_files: Dict mapping file paths to file contents
            spec_validation_model: Expected constraints from spec (optional, uses IR if not provided)

        Returns:
            ComplianceResult with scores and detailed breakdown
        """
        # Extract code constraints using unified extractor
        if self.unified_extractor:
            code_validation_model = await self.unified_extractor.extract_all(code_files)
        else:
            code_validation_model = None

        # Get spec constraints
        spec_model = spec_validation_model or (
            self.application_ir.validation_model if self.application_ir else None
        )

        if not spec_model:
            raise ValueError("No spec validation model available")

        # Phase 3 will do IR-aware matching here
        # For now, Phase 1 semantic matching
        return await self._calculate_compliance(spec_model, code_validation_model)
```

---

### ❌ Issue 2: SemanticMatcher vs SemanticNormalizer Boundary Unclear

**Problem**: Risk of duplicating normalization logic across components.

**Solution**: Explicit boundary rule:

```
┌─────────────────────────────────────────────────────────────────────┐
│ HARD RULE: Component Responsibilities                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│ SemanticNormalizer (Phase 2):                                       │
│   ✅ ÚNICA puerta de entrada de constraints crudas → IR             │
│   ✅ Resuelve entidades, campos, tipos                              │
│   ✅ Asigna confidence scores                                        │
│   ❌ NO compara constraints                                          │
│   ❌ NO hace matching                                                │
│                                                                      │
│ SemanticMatcher (Phase 1/3):                                        │
│   ✅ Compara spec vs code                                           │
│   ✅ Solo recibe NormalizedRules o ValidationModelIR                │
│   ❌ NO normaliza strings raw                                        │
│   ❌ NO resuelve entidades/campos                                    │
│                                                                      │
│ UnifiedConstraintExtractor:                                         │
│   ✅ Orquesta extracción de todas las fuentes                       │
│   ✅ Llama a SemanticNormalizer                                     │
│   ✅ Hace merge/deduplicación                                        │
│   ❌ NO tiene lógica de normalización propia                        │
│                                                                      │
│ ComplianceValidator:                                                │
│   ✅ Entry point para validación                                    │
│   ✅ Coordina extractor + matcher                                   │
│   ❌ NO normaliza                                                    │
│   ❌ NO extrae constraints                                           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

### ❌ Issue 3: _compute_confidence es un Stub

**Problem**: `_compute_confidence` siempre retorna 0.95.

**Solution A: Implementación Real** (Recomendado para production):

```python
class SemanticNormalizer:

    def _compute_confidence(self, rule: ConstraintRule, steps: NormalizationSteps) -> float:
        """
        Compute confidence based on normalization path taken.

        Confidence factors:
        1. Match type (exact, case, fuzzy, inference)
        2. Source reliability (database > pydantic > openapi > business_logic)
        3. Value preservation (value unchanged vs transformed)
        """
        base_confidence = 1.0

        # Factor 1: Match type penalties
        match_penalties = {
            "exact": 0.0,           # Perfect match
            "case_variation": 0.02, # product → Product
            "case_conversion": 0.05, # unit_price → unitPrice
            "plural_singular": 0.08, # items → item
            "synonym_mapping": 0.12, # price → unitPrice
            "pattern_inference": 0.20, # inferred from pattern
            "fallback": 0.40,       # couldn't resolve, used default
        }

        entity_penalty = match_penalties.get(steps.entity_match_type, 0.20)
        field_penalty = match_penalties.get(steps.field_match_type, 0.20)
        type_penalty = match_penalties.get(steps.type_match_type, 0.20)

        # Factor 2: Source reliability bonus
        source_reliability = {
            "ast_sqlalchemy": 0.0,    # Database = highest reliability
            "ast_pydantic": 0.02,     # Model validation
            "openapi": 0.05,          # Schema definition
            "business_logic": 0.10,   # Inferred patterns
        }
        source_penalty = source_reliability.get(rule.source, 0.15)

        # Factor 3: Value transformation penalty
        value_penalty = 0.0 if steps.value_unchanged else 0.05

        # Calculate final confidence
        total_penalty = entity_penalty + field_penalty + type_penalty + source_penalty + value_penalty
        confidence = max(0.0, base_confidence - total_penalty)

        return round(confidence, 2)

@dataclass
class NormalizationSteps:
    """Track how each normalization was achieved."""
    entity_match_type: str  # exact, case_variation, synonym_mapping, etc.
    field_match_type: str
    type_match_type: str
    value_unchanged: bool
```

**Solution B: Regla Determinista** (Alternativa simple):

```python
# En lugar de confidence variable, usar prioridad fija por source
SOURCE_PRIORITY = {
    "ast_sqlalchemy": 1,   # Highest priority (database is truth)
    "ast_pydantic": 2,
    "openapi": 3,
    "business_logic": 4,   # Lowest priority
}

def _semantic_merge(self, normalized_rules: list[NormalizedRule]) -> list[NormalizedRule]:
    """Merge using deterministic source priority instead of confidence."""
    constraint_map: dict[str, NormalizedRule] = {}

    for rule in normalized_rules:
        key = self._make_constraint_key(rule)
        existing = constraint_map.get(key)

        if not existing:
            constraint_map[key] = rule
        else:
            # Deterministic: prefer higher priority source
            existing_priority = SOURCE_PRIORITY.get(existing.original_rule.source, 99)
            new_priority = SOURCE_PRIORITY.get(rule.original_rule.source, 99)

            if new_priority < existing_priority:  # Lower number = higher priority
                constraint_map[key] = rule

    return list(constraint_map.values())
```

---

### ❌ Issue 4: _resolve_field Tiene Demasiada Magia

**Problem**: Si crece, se vuelve inmantenible.

**Solution**: Mínima magia + configuración explícita en IR:

```python
class SemanticNormalizer:

    def _resolve_field(self, entity: str, field_name: str) -> Optional[str]:
        """
        Resolve field name to canonical form.

        Strategy (in order):
        1. Check ApplicationIR explicit mappings FIRST
        2. Exact match in IR entity
        3. Case-insensitive match
        4. STOP HERE - no more magic

        If ApplicationIR needs more mappings, update ApplicationIR, NOT this method.
        """
        ir_entity = self.ir.get_entity(entity)
        if not ir_entity:
            return None

        # Strategy 1: IR explicit mappings (most reliable)
        if hasattr(ir_entity, 'field_aliases'):
            canonical = ir_entity.field_aliases.get(field_name.lower())
            if canonical:
                return canonical

        # Strategy 2: Exact match
        for field in ir_entity.fields:
            if field.name == field_name:
                return field.name

        # Strategy 3: Case-insensitive
        for field in ir_entity.fields:
            if field.name.lower() == field_name.lower():
                return field.name

        # Strategy 4: NO MORE MAGIC
        # If we can't resolve, return None and log
        logger.warning(
            f"Cannot resolve field '{field_name}' in entity '{entity}'. "
            f"Consider adding to ApplicationIR.field_aliases."
        )
        return None
```

**ApplicationIR Enhancement**:

```python
# In ApplicationIR entity definition
class EntityIR:
    name: str
    fields: list[FieldIR]
    field_aliases: dict[str, str] = {}  # NEW: explicit mapping

# Example usage:
product_entity = EntityIR(
    name="Product",
    fields=[...],
    field_aliases={
        "unit_price": "price",
        "unitprice": "price",
        "product_price": "price",
        "created": "createdAt",
        "creation_date": "createdAt",
    }
)
```

---

### ❌ Issue 5: BusinessLogicExtractor No Documentado

**Problem**: Aparece como "Existing" pero no está descrito.

**Solution**: Documentación concreta:

```python
class BusinessLogicExtractor:
    """
    Extracts constraints from business logic patterns in code.

    Detects:
    1. State machines (order.status transitions)
    2. Workflow constraints (can't ship before payment)
    3. Invariantes (total = sum(items.price * items.quantity))
    4. Custom validators (@validator decorators with business logic)

    Integration with IR:
    - State machines → ENUM constraints + STATE_MACHINE enforcement
    - Workflows → BUSINESS_LOGIC enforcement type
    - Invariantes → COMPUTED_FIELD enforcement
    - Custom validators → VALIDATOR enforcement with condition
    """

    def __init__(self, application_ir: ApplicationIR):
        self.ir = application_ir
        self.pattern_detectors = [
            StateMachineDetector(),
            WorkflowConstraintDetector(),
            InvariantDetector(),
            CustomValidatorDetector(),
        ]

    async def extract(self, code_files: dict) -> list[dict]:
        """
        Extract business logic constraints from code.

        Returns list of raw constraint dicts:
        {
            "entity": "Order",
            "field": "status",
            "constraint_type": "state_machine",
            "value": ["pending", "confirmed", "shipped", "delivered"],
            "enforcement_type": "state_machine",
            "source_location": "src/models/order.py:45",
            "pattern_type": "enum_with_transitions"
        }
        """
        constraints = []

        for file_path, content in code_files.items():
            if not file_path.endswith('.py'):
                continue

            for detector in self.pattern_detectors:
                detected = detector.detect(content, file_path, self.ir)
                constraints.extend(detected)

        return constraints

# Pattern detector example
class StateMachineDetector:
    """Detects state machine patterns in model definitions."""

    PATTERNS = [
        # Literal enum with transitions
        r'status\s*[=:]\s*(?:Literal|Enum)\s*\[(.*?)\]',
        # Class-based enum
        r'class\s+(\w+Status)\s*\(.*?Enum\)',
        # State transition methods
        r'def\s+(transition_to|change_status|set_state)',
    ]

    def detect(self, content: str, file_path: str, ir: ApplicationIR) -> list[dict]:
        # Implementation...
        pass
```

---

## 📋 Updated Implementation Checklist

### Core Components (Updated)

- [ ] **SemanticNormalizer** (reduced scope)
  - [ ] `_resolve_entity()` - exact + case-insensitive ONLY
  - [ ] `_resolve_field()` - IR aliases + exact + case-insensitive ONLY
  - [ ] `_resolve_constraint_type()` - IR types + pattern matching
  - [ ] `_compute_confidence()` - REAL implementation (not stub)

- [ ] **UnifiedConstraintExtractor**
  - [ ] Orchestration only, NO normalization logic

- [ ] **ComplianceValidator.validate_app()** (NEW method)
  - [ ] Move extraction from `__init__` to `validate_app()`
  - [ ] Accept `code_files` as parameter

- [ ] **BusinessLogicExtractor** (document existing)
  - [ ] Add docstrings explaining what it detects
  - [ ] Document integration with IR

- [ ] **ApplicationIR Enhancement**
  - [ ] Add `field_aliases` to EntityIR
  - [ ] Document explicit mappings instead of magic

---

## 🎯 Final Architecture Summary

```
                        ApplicationIR (CONFIG)
                              │
                              │ provides canonical names,
                              │ field_aliases, constraint types
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  OpenAPI ─────┐                                                    │
│  AST-Pydantic ┼─► UnifiedConstraintExtractor ─► SemanticNormalizer │
│  AST-SQLA ────┤         (orchestration)           (única puerta    │
│  BusinessLogic┘                                    de normalización)│
│                                                          │          │
│                                                          ▼          │
│                                              NormalizedRules        │
│                                                          │          │
│                                                          ▼          │
│                                              ValidationModelIR      │
│                                                          │          │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ComplianceValidator.validate_app()
                              │
                              ▼
              SemanticMatcher (Phase 1) or
              IRSemanticMatcher (Phase 3)
                              │
                              ▼
                      ComplianceResult
```

**Key principles**:
1. ApplicationIR es la fuente de configuración (aliases, types)
2. SemanticNormalizer es la ÚNICA puerta de normalización
3. ComplianceValidator.validate_app() recibe code_files como parámetro
4. Confidence es REAL o se usa prioridad determinista por source
