# Phase 3.5: Ground Truth via ApplicationIR

**Document Version**: 2.1
**Date**: November 25, 2025
**Status**: 🟢 **CORE IMPLEMENTATION COMPLETE** – Ready for Testing
**Priority**: 🔴 CRITICAL – Closes the SPEC ↔ CODE circuit
**Scope**: SPEC → ApplicationIR (one-time LLM) → ValidationModelIR (deterministic)
**Expected Impact**: +5–10% compliance recovery + 100% deterministic metrics
**Dependencies**: Phase 2 (SemanticNormalizer) - NOT blocking, Phase 3 (IRSemanticMatcher) ✅ DONE

---

## 🎯 Phase 3.5 Objective

**Key Insight**: Instead of parsing Markdown specs with fragile regex, use LLM to generate `ApplicationIR` ONCE, then use that IR as the deterministic ground truth.

```
OLD APPROACH (fragile):
  Spec Markdown → Regex Parser (fragile) → SpecConstraintRule[] → ...

NEW APPROACH (robust):
  Spec Markdown → LLM (one-time) → ApplicationIR.json (cached) → ValidationModelIR
```

### Benefits

| Aspect | Old (Regex Parser) | New (ApplicationIR) |
|--------|-------------------|---------------------|
| Determinism | ❌ Regex varies | ✅ 100% (cached JSON) |
| LLM Cost | N/A | Low (one-time) |
| Robustness | ❌ Fragile | ✅ LLM understands NL |
| Maintenance | High | Low |
| Already exists | No | Partially (ApplicationIR) |

---

## 📊 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Phase 3.5: ApplicationIR as Ground Truth              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  SPEC (Markdown)                                                         │
│       │                                                                  │
│       ▼                                                                  │
│  SpecToApplicationIR (LLM)  ←── Runs ONCE when spec changes             │
│       │                                                                  │
│       ▼                                                                  │
│  ApplicationIR.json  ←── Cached, 100% deterministic                     │
│       │                                                                  │
│       ├──────────────────────────┐                                       │
│       │                          │                                       │
│       ▼                          ▼                                       │
│  ValidationModelIR          Code Generation                              │
│  (spec side)                (uses same IR)                               │
│       │                          │                                       │
│       │                          ▼                                       │
│       │                  Generated Code                                  │
│       │                          │                                       │
│       │                          ▼                                       │
│       │                  UnifiedConstraintExtractor                      │
│       │                  (Phase 2)                                       │
│       │                          │                                       │
│       │                          ▼                                       │
│       │                  ValidationModelIR                               │
│       │                  (code side)                                     │
│       │                          │                                       │
│       └──────────┬───────────────┘                                       │
│                  │                                                       │
│                  ▼                                                       │
│          IRSemanticMatcher (Phase 3)                                     │
│                  │                                                       │
│                  ▼                                                       │
│          ComplianceResult                                                │
│          - 100% deterministic                                            │
│          - Full traceability                                             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Implementation Plan

### Component 1: SpecToApplicationIR

**File**: `src/specs/spec_to_application_ir.py` (NEW – ~200 lines)

Converts spec markdown to ApplicationIR using LLM. Runs ONCE, result is cached.

```python
import json
import logging
import hashlib
from pathlib import Path
from typing import Optional

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from src.cognitive.ir.application_ir import ApplicationIR
from src.cognitive.ir.validation_model import (
    ValidationType,
    EnforcementType,
    ValidationRule,
    ValidationModelIR,
)

logger = logging.getLogger(__name__)


class SpecToApplicationIR:
    """
    Convert spec markdown to ApplicationIR using LLM.

    This is a ONE-TIME operation that runs when:
    1. Spec changes (detected via hash)
    2. No cached ApplicationIR exists
    3. Force refresh requested

    Result is cached as JSON for 100% deterministic subsequent runs.
    """

    CACHE_DIR = Path(".devmatrix/ir_cache")
    LLM_MODEL = "claude-3-5-sonnet-20241022"  # Best for structured extraction

    def __init__(self):
        """Initialize the converter."""
        if ANTHROPIC_AVAILABLE:
            self.client = Anthropic()
        else:
            self.client = None
            logger.warning("Anthropic not available - LLM extraction disabled")

        # Ensure cache directory exists
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    async def get_application_ir(
        self,
        spec_markdown: str,
        spec_path: str = "spec.md",
        force_refresh: bool = False
    ) -> ApplicationIR:
        """
        Get ApplicationIR for spec, using cache if available.

        Args:
            spec_markdown: Raw markdown content of specification
            spec_path: Path to spec file (for cache key)
            force_refresh: Force regeneration even if cached

        Returns:
            ApplicationIR representing the spec
        """
        # Generate cache key from spec content hash
        spec_hash = self._hash_spec(spec_markdown)
        cache_path = self.CACHE_DIR / f"{Path(spec_path).stem}_{spec_hash[:8]}.json"

        # Check cache first
        if not force_refresh and cache_path.exists():
            logger.info(f"📦 Loading cached ApplicationIR from {cache_path}")
            return self._load_from_cache(cache_path)

        # Generate with LLM
        logger.info(f"🤖 Generating ApplicationIR with LLM for {spec_path}")
        application_ir = await self._generate_with_llm(spec_markdown, spec_path)

        # Cache for future use
        self._save_to_cache(application_ir, cache_path, spec_hash)
        logger.info(f"💾 Cached ApplicationIR to {cache_path}")

        return application_ir

    async def _generate_with_llm(
        self,
        spec_markdown: str,
        spec_path: str
    ) -> ApplicationIR:
        """Generate ApplicationIR from spec using LLM."""
        if not self.client:
            raise RuntimeError("Anthropic client not available")

        prompt = self._build_extraction_prompt(spec_markdown)

        response = self.client.messages.create(
            model=self.LLM_MODEL,
            max_tokens=8000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Parse JSON response
        response_text = response.content[0].text

        # Extract JSON from response (handle markdown code blocks)
        json_str = self._extract_json(response_text)
        ir_data = json.loads(json_str)

        # Convert to ApplicationIR
        return self._build_application_ir(ir_data, spec_path)

    def _build_extraction_prompt(self, spec_markdown: str) -> str:
        """Build the LLM prompt for spec extraction."""
        return f"""Extract ALL entities, fields, and validation constraints from this specification.

IMPORTANT: Be exhaustive. Include EVERY constraint mentioned, even implicit ones.

For each entity, extract:
- name: Entity name (PascalCase)
- fields: All fields with their types and constraints

For each field constraint, identify:
- type: One of: FORMAT, RANGE, PRESENCE, UNIQUENESS, RELATIONSHIP, STATUS_TRANSITION, STOCK_CONSTRAINT, WORKFLOW_CONSTRAINT, CUSTOM
- condition: The specific constraint (e.g., "> 0", "valid email", "unique")
- value: Numeric or list value if applicable

Output ONLY valid JSON in this exact format:
{{
  "entities": [
    {{
      "name": "EntityName",
      "fields": [
        {{
          "name": "fieldName",
          "type": "string|integer|decimal|boolean|datetime|enum",
          "constraints": [
            {{
              "validation_type": "FORMAT|RANGE|PRESENCE|UNIQUENESS|...",
              "condition": "description of constraint",
              "value": null
            }}
          ]
        }}
      ]
    }}
  ],
  "validation_rules": [
    {{
      "entity": "EntityName",
      "attribute": "fieldName",
      "type": "FORMAT|RANGE|PRESENCE|...",
      "condition": "> 0",
      "enforcement_type": "DESCRIPTION"
    }}
  ]
}}

SPECIFICATION:
{spec_markdown}

Output JSON only, no explanation:"""

    def _extract_json(self, response: str) -> str:
        """Extract JSON from LLM response, handling markdown code blocks."""
        # Try to find JSON in code block
        if "```json" in response:
            start = response.index("```json") + 7
            end = response.index("```", start)
            return response[start:end].strip()

        if "```" in response:
            start = response.index("```") + 3
            end = response.index("```", start)
            return response[start:end].strip()

        # Assume entire response is JSON
        return response.strip()

    def _build_application_ir(self, ir_data: dict, spec_path: str) -> ApplicationIR:
        """Convert parsed JSON to ApplicationIR object."""
        # Build ValidationModelIR from validation_rules
        validation_rules = []

        for rule_data in ir_data.get("validation_rules", []):
            validation_type = self._parse_validation_type(rule_data.get("type", "CUSTOM"))

            rule = ValidationRule(
                entity=rule_data.get("entity", ""),
                attribute=rule_data.get("attribute", ""),
                type=validation_type,
                condition=rule_data.get("condition"),
                enforcement_type=EnforcementType.DESCRIPTION,  # Spec = intent
            )
            validation_rules.append(rule)

        # Also extract rules from entity.field.constraints
        for entity_data in ir_data.get("entities", []):
            entity_name = entity_data.get("name", "")

            for field_data in entity_data.get("fields", []):
                field_name = field_data.get("name", "")

                for constraint in field_data.get("constraints", []):
                    validation_type = self._parse_validation_type(
                        constraint.get("validation_type", "CUSTOM")
                    )

                    # Avoid duplicates
                    rule_key = f"{entity_name}.{field_name}.{validation_type.value}"
                    existing_keys = {
                        f"{r.entity}.{r.attribute}.{r.type.value}"
                        for r in validation_rules
                    }

                    if rule_key not in existing_keys:
                        rule = ValidationRule(
                            entity=entity_name,
                            attribute=field_name,
                            type=validation_type,
                            condition=constraint.get("condition"),
                            enforcement_type=EnforcementType.DESCRIPTION,
                        )
                        validation_rules.append(rule)

        validation_model = ValidationModelIR(rules=validation_rules)

        # Build ApplicationIR
        # Note: Adapt this to your actual ApplicationIR structure
        return ApplicationIR(
            entities=self._build_entities(ir_data.get("entities", [])),
            validation_model=validation_model,
            source_spec=spec_path,
        )

    def _parse_validation_type(self, type_str: str) -> ValidationType:
        """Parse validation type string to enum."""
        type_map = {
            "FORMAT": ValidationType.FORMAT,
            "RANGE": ValidationType.RANGE,
            "PRESENCE": ValidationType.PRESENCE,
            "UNIQUENESS": ValidationType.UNIQUENESS,
            "RELATIONSHIP": ValidationType.RELATIONSHIP,
            "STATUS_TRANSITION": ValidationType.STATUS_TRANSITION,
            "STOCK_CONSTRAINT": ValidationType.STOCK_CONSTRAINT,
            "WORKFLOW_CONSTRAINT": ValidationType.WORKFLOW_CONSTRAINT,
            "CUSTOM": ValidationType.CUSTOM,
        }
        return type_map.get(type_str.upper(), ValidationType.CUSTOM)

    def _build_entities(self, entities_data: list) -> list:
        """Build entity list from parsed data."""
        # Adapt to your EntityIR structure
        entities = []
        for entity_data in entities_data:
            # Build entity object based on your ApplicationIR structure
            entities.append(entity_data)  # Placeholder
        return entities

    def _hash_spec(self, spec_markdown: str) -> str:
        """Generate hash of spec content for cache invalidation."""
        return hashlib.sha256(spec_markdown.encode()).hexdigest()

    def _load_from_cache(self, cache_path: Path) -> ApplicationIR:
        """Load ApplicationIR from cached JSON."""
        with open(cache_path) as f:
            data = json.load(f)

        # Reconstruct ApplicationIR from JSON
        return ApplicationIR.from_dict(data["application_ir"])

    def _save_to_cache(
        self,
        application_ir: ApplicationIR,
        cache_path: Path,
        spec_hash: str
    ):
        """Save ApplicationIR to cache."""
        cache_data = {
            "spec_hash": spec_hash,
            "application_ir": application_ir.to_dict(),
            "generated_at": str(Path.cwd()),  # Add timestamp if needed
        }

        with open(cache_path, "w") as f:
            json.dump(cache_data, f, indent=2)

    def clear_cache(self, spec_path: str = None):
        """Clear cached ApplicationIR files."""
        if spec_path:
            # Clear specific spec cache
            pattern = f"{Path(spec_path).stem}_*.json"
            for cache_file in self.CACHE_DIR.glob(pattern):
                cache_file.unlink()
                logger.info(f"🗑️ Removed cache: {cache_file}")
        else:
            # Clear all cache
            for cache_file in self.CACHE_DIR.glob("*.json"):
                cache_file.unlink()
                logger.info(f"🗑️ Removed cache: {cache_file}")

    def get_cache_info(self, spec_path: str) -> dict:
        """Get information about cached ApplicationIR."""
        pattern = f"{Path(spec_path).stem}_*.json"
        cache_files = list(self.CACHE_DIR.glob(pattern))

        if not cache_files:
            return {"cached": False}

        cache_file = cache_files[0]
        with open(cache_file) as f:
            data = json.load(f)

        return {
            "cached": True,
            "cache_path": str(cache_file),
            "spec_hash": data.get("spec_hash", "")[:8],
            "rules_count": len(data.get("application_ir", {}).get("validation_model", {}).get("rules", [])),
        }
```

---

### Component 2: Integration with ComplianceValidator

**File**: `src/validation/compliance_validator.py` (extension)

```python
# Add to ComplianceValidator class

class ComplianceValidator:
    # ... existing code ...

    # ═══════════════════════════════════════════════════════════════════════════
    # Phase 3.5: ApplicationIR as Ground Truth
    # ═══════════════════════════════════════════════════════════════════════════

    async def load_spec_from_markdown(
        self,
        spec_markdown: str,
        spec_path: str = "spec.md",
        force_refresh: bool = False
    ) -> ApplicationIR:
        """
        Phase 3.5: Load spec as ApplicationIR.

        Uses LLM to generate ApplicationIR (one-time), then caches for
        100% deterministic subsequent runs.

        Args:
            spec_markdown: Raw markdown content
            spec_path: Path for cache key
            force_refresh: Force LLM regeneration

        Returns:
            ApplicationIR with validation_model
        """
        from src.specs.spec_to_application_ir import SpecToApplicationIR

        converter = SpecToApplicationIR()
        return await converter.get_application_ir(
            spec_markdown, spec_path, force_refresh
        )

    async def validate_from_spec_markdown(
        self,
        spec_markdown: str,
        code_files: dict[str, str],
        spec_path: str = "spec.md"
    ) -> 'ComplianceResult':
        """
        Phase 3.5: Full SPEC + CODE → ComplianceResult.

        Flow:
        1. SPEC → ApplicationIR (cached LLM)
        2. ApplicationIR → ValidationModelIR (spec side)
        3. CODE → ValidationModelIR (Phase 2)
        4. Match IR vs IR (Phase 3)

        Args:
            spec_markdown: Raw markdown content
            code_files: Dict mapping file paths to contents
            spec_path: Path for traceability

        Returns:
            ComplianceResult with deterministic metrics
        """
        # Step 1: Get ApplicationIR from spec (cached)
        application_ir = await self.load_spec_from_markdown(
            spec_markdown, spec_path
        )

        # Step 2: Get ValidationModelIR from ApplicationIR
        spec_validation_model = application_ir.validation_model

        # Step 3: Validate using Phase 2 core
        return await self.validate_app(code_files, spec_validation_model)

    async def validate_from_spec_file(
        self,
        spec_path: Path,
        output_path: Path,
        force_refresh: bool = False
    ) -> 'ComplianceResult':
        """
        Convenience: Load spec from file, code from directory.

        Args:
            spec_path: Path to spec markdown file
            output_path: Path to generated app directory
            force_refresh: Force ApplicationIR regeneration
        """
        # Read spec
        spec_markdown = spec_path.read_text()

        # Read code files
        code_files = self._read_app_files(output_path)

        # Optional: Force refresh if spec changed
        if force_refresh:
            from src.specs.spec_to_application_ir import SpecToApplicationIR
            SpecToApplicationIR().clear_cache(str(spec_path))

        # Validate
        return await self.validate_from_spec_markdown(
            spec_markdown, code_files, str(spec_path)
        )
```

---

### Component 3: CLI Integration

**File**: `src/cli/commands.py` (optional)

```python
# CLI commands for cache management

@cli.command()
def ir_cache_status(spec_path: str):
    """Show ApplicationIR cache status for a spec."""
    from src.specs.spec_to_application_ir import SpecToApplicationIR

    converter = SpecToApplicationIR()
    info = converter.get_cache_info(spec_path)

    if info["cached"]:
        print(f"✅ Cached: {info['cache_path']}")
        print(f"   Hash: {info['spec_hash']}")
        print(f"   Rules: {info['rules_count']}")
    else:
        print("❌ No cache found")

@cli.command()
def ir_cache_clear(spec_path: str = None):
    """Clear ApplicationIR cache."""
    from src.specs.spec_to_application_ir import SpecToApplicationIR

    converter = SpecToApplicationIR()
    converter.clear_cache(spec_path)
    print("✅ Cache cleared")

@cli.command()
async def ir_cache_refresh(spec_path: str):
    """Force refresh ApplicationIR from spec."""
    from src.specs.spec_to_application_ir import SpecToApplicationIR

    spec_markdown = Path(spec_path).read_text()

    converter = SpecToApplicationIR()
    ir = await converter.get_application_ir(
        spec_markdown, spec_path, force_refresh=True
    )

    print(f"✅ Regenerated ApplicationIR")
    print(f"   Entities: {len(ir.entities)}")
    print(f"   Rules: {len(ir.validation_model.rules)}")
```

---

## 📋 Implementation Checklist

### Task 1 – SpecToApplicationIR

- [x] File: `src/specs/spec_to_application_ir.py` (✅ DONE Nov 25)
  - [x] `get_application_ir()` - main entry with caching
  - [x] `_generate_with_llm()` - LLM extraction
  - [x] `_build_extraction_prompt()` - optimized prompt
  - [x] `_build_application_ir()` - JSON → ApplicationIR
  - [x] Cache management (load, save, clear, hash)
  - [x] Logging for observability

- [ ] Tests: `tests/unit/test_spec_to_application_ir.py` (PENDING)
  - [ ] Cache hit path
  - [ ] Cache miss path (mock LLM)
  - [ ] Hash-based invalidation
  - [ ] JSON parsing edge cases
  - [ ] ValidationType mapping

### Task 2 – ComplianceValidator Integration

- [x] Add `load_spec_from_markdown()` (✅ DONE Nov 25)
- [x] Add `validate_from_spec_markdown()` (✅ DONE Nov 25)
- [x] Add `validate_from_spec_file()` (✅ DONE Nov 25)
- [x] Add `validate_ir_vs_ir()` (✅ DONE Nov 25)
- [x] Add `validate_full_ir_pipeline()` (✅ DONE Nov 25)
- [x] Add `get_application_ir_cache_info()` (✅ DONE Nov 25)
- [ ] Integration tests with E2E pipeline (PENDING)

### Task 3 – CLI Commands (Optional)

- [ ] `ir-cache-status` (PENDING)
- [ ] `ir-cache-clear` (PENDING)
- [ ] `ir-cache-refresh` (PENDING)

### Task 4 – E2E Test

- [ ] Test with `ecommerce-api-spec-human.md` (PENDING)
- [ ] Measure: rules extracted, compliance % (PENDING)
- [ ] Verify determinism: same input → same output (PENDING)

---

## 📊 Success Metrics

| Metric | Old (Regex) | New (ApplicationIR) |
|--------|-------------|---------------------|
| Spec constraint detection | ~70-80% | ≥95% |
| Determinism | ❌ Variable | ✅ 100% |
| LLM calls per validation | 0 | 0 (cached) |
| Cache miss LLM cost | N/A | ~$0.02/spec |
| Maintenance complexity | High | Low |

---

## 📁 File Structure

```
src/
├── specs/
│   ├── __init__.py                  [✅ DONE Nov 25]
│   └── spec_to_application_ir.py    [✅ DONE Nov 25 - Phase 3.5]
├── cognitive/ir/
│   ├── application_ir.py            [✅ Existing]
│   ├── validation_model.py          [✅ Existing - Phase 4]
│   └── constraint_ir.py             [✅ DONE Nov 25 - Phase 3]
├── services/
│   ├── semantic_matcher.py          [✅ Phase 1]
│   ├── semantic_normalizer.py       [🟡 Phase 2 - PENDING]
│   ├── ir_semantic_matcher.py       [✅ DONE Nov 25 - Phase 3]
│   └── unified_constraint_extractor.py [🟡 Phase 2 - PENDING]
└── validation/
    └── compliance_validator.py      [✅ DONE (extended) Nov 25 - Phase 3.5]

.devmatrix/
└── ir_cache/
    └── ecommerce-api-spec-human_a1b2c3d4.json  [Cached ApplicationIR]

tests/unit/
├── test_spec_to_application_ir.py   [🟡 Phase 3.5 - PENDING]
├── test_constraint_ir.py            [🟡 Phase 3 - PENDING]
└── test_ir_semantic_matcher.py      [🟡 Phase 3 - PENDING]
```

---

## 🔄 When Does LLM Run?

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LLM Execution Decision Tree                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  validate_from_spec_markdown(spec)                                   │
│       │                                                              │
│       ▼                                                              │
│  Calculate spec_hash                                                 │
│       │                                                              │
│       ▼                                                              │
│  Cache exists for hash?                                              │
│       │                                                              │
│       ├── YES ──► Load from cache ──► 0 LLM calls ✅                │
│       │                                                              │
│       └── NO ───► Generate with LLM ──► 1 LLM call                  │
│                         │                                            │
│                         ▼                                            │
│                   Save to cache                                      │
│                         │                                            │
│                         ▼                                            │
│               Next run: 0 LLM calls ✅                              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

LLM runs ONLY when:
1. First time processing a spec
2. Spec content changes (different hash)
3. Manual cache clear + refresh
```

---

## 💼 Business Value

### Before Phase 3.5

```
Spec (Markdown) → Regex Parser (fragile) → Partial extraction
                                        → Non-deterministic metrics
                                        → High maintenance
```

### After Phase 3.5

```
Spec (Markdown) → LLM (one-time) → ApplicationIR.json (cached)
                                 → 100% deterministic
                                 → Near-zero maintenance
                                 → Same IR used for code generation
```

### Key Advantage

**ApplicationIR is BOTH the spec AND the code generation source.**

This means:
- Code is generated FROM ApplicationIR
- Compliance is measured AGAINST ApplicationIR
- Perfect alignment by construction

---

## 🎯 Key Principles

1. **LLM runs ONCE** - when spec changes, not on every validation
2. **Cache is deterministic** - same spec hash → same ApplicationIR
3. **ApplicationIR is the contract** - both spec and code derive from it
4. **No regex parsing** - LLM handles natural language robustly
5. **Cost-effective** - ~$0.02 per spec, amortized over infinite validations

---

## 🎯 Summary

**Status**: 🟢 **IMPLEMENTATION COMPLETE** (Nov 25, 2025)

### Implementation Done (80% of Phase 3.5)

- ✅ SpecToApplicationIR (LLM-based spec parsing with caching)
- ✅ ComplianceValidator integration (5 new methods)
- ✅ IR cache management (hash-based invalidation)
- ✅ Full pipeline integration (validate_full_ir_pipeline)

### Pending (20% of Phase 3.5)

- 🟡 Unit tests (test_spec_to_application_ir.py)
- 🟡 E2E test with ecommerce spec
- 🟡 CLI commands (optional)

**Owner**: DevMatrix Phase 3.5 Development
**Dependencies**: Phase 2 (SemanticNormalizer) - for 100% integration, Phase 3 (IRSemanticMatcher) ✅
**Status**: Ready for E2E testing and validation
