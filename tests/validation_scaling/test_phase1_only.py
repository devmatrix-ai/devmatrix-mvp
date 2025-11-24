"""
Test: Phase 1 ONLY (Pattern-based, no LLM)

Extracts validations from JSON formal using only Phase 1 patterns.
No LLM, no transformations - pure pattern-based extraction from JSON.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.business_logic_extractor import BusinessLogicExtractor


def test_phase1_only():
    """Extract validations using ONLY Phase 1 pattern-based rules"""

    print("=" * 80)
    print("TEST: Phase 1 ONLY (Pattern-based, No LLM)")
    print("=" * 80 + "\n")

    # Load formal JSON spec
    spec_path = Path("tests/e2e/test_specs/ecommerce_api_formal.json")
    with open(spec_path) as f:
        spec = json.load(f)

    print(f"Input: {spec_path}")
    print(f"  (Formal JSON - explicit constraints)\n")

    # Show spec structure
    print("Spec Structure:")
    print("-" * 80)
    entities = spec.get("entities", [])
    print(f"  Entities: {len(entities)}")
    total_fields = 0
    for e in entities:
        fields = e.get("fields", [])
        total_fields += len(fields)
        print(f"    - {e['name']}: {len(fields)} fields")

    relationships = spec.get("relationships", [])
    print(f"\n  Total fields: {total_fields}")
    print(f"  Relationships: {len(relationships)}")
    print(f"  Endpoints: {len(spec.get('endpoints', []))}\n")

    # Extract validations - PHASE 1 ONLY
    print("Extracting validations using PHASE 1 patterns...")

    extractor = BusinessLogicExtractor()

    # Get Phase 1 (pattern-based) only
    rules = []

    # Stage 1-5: Pattern-based extraction
    if "entities" in spec:
        rules.extend(extractor._extract_from_entities(spec["entities"]))

    rules.extend(extractor._extract_from_field_descriptions(spec.get("entities", [])))

    if "endpoints" in spec:
        try:
            rules.extend(extractor._extract_from_endpoints(spec.get("endpoints", []), spec.get("entities", [])))
        except Exception as e:
            print(f"  (Endpoint extraction skipped: {e})")

    rules.extend(extractor._extract_from_workflows(spec))

    if "schema" in spec or "database_schema" in spec:
        rules.extend(extractor._extract_constraint_validations(spec))

    if "validation_rules" in spec or "business_rules" in spec:
        rules.extend(extractor._extract_business_rules(spec))

    # Stage 6.5: Pattern-based rules
    try:
        pattern_rules = extractor._extract_pattern_rules(spec)
        rules.extend(pattern_rules)
        print(f"  Phase 1 patterns: {len(pattern_rules)} rules")
    except Exception as e:
        print(f"  (Pattern extraction: {e})")

    # Deduplicate
    initial = len(rules)
    rules = extractor._deduplicate_rules(rules)
    dedup = initial - len(rules)

    print(f"✅ Phase 1 extraction complete\n")

    # Analysis
    print("=" * 80)
    print("RESULTS: Phase 1 Only (JSON Formal + Patterns)")
    print("=" * 80 + "\n")

    print(f"Total validations extracted: {len(rules)}/62")
    print(f"Coverage: {len(rules)/62*100:.1f}%")
    print(f"Deduplication: {initial} → {len(rules)} ({dedup} duplicates)\n")

    # Breakdown by type
    by_type = {}
    for v in rules:
        v_type = str(v.type)
        by_type[v_type] = by_type.get(v_type, 0) + 1

    print("Breakdown by Type:")
    for v_type in sorted(by_type.keys()):
        count = by_type[v_type]
        pct = (count / len(rules) * 100) if rules else 0
        print(f"  {v_type:30} {count:3} ({pct:5.1f}%)")

    return {
        "total": len(rules),
        "initial": initial,
        "dedup_removed": dedup,
        "coverage": len(rules) / 62 * 100,
        "by_type": by_type
    }


if __name__ == "__main__":
    print("\n🔬 TESTING PHASE 1 ONLY (No LLM)\n")

    result = test_phase1_only()

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✅ Phase 1 extracted: {result['total']}/62 ({result['coverage']:.1f}%)")
    print(f"   Initial rules: {result['initial']}, Duplicates removed: {result['dedup_removed']}")

    if result['coverage'] >= 90:
        print(f"\n✅ Phase 1 ALONE achieves ≥90% coverage - LLM may be optional")
    elif result['coverage'] >= 75:
        print(f"\n⚠️  Phase 1 gets {result['coverage']:.1f}% - LLM would add {100-result['coverage']:.1f}%")
    else:
        print(f"\n❌ Phase 1 only gets {result['coverage']:.1f}% - LLM needed for full coverage")

    exit(0)
