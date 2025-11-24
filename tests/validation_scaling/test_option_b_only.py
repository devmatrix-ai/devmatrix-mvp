"""
Test: Option B ONLY (LLM Normalization - No Fallback)

Measures real validation count from LLM normalization alone.
No fallback, no manual JSON - pure LLM output.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.llm_spec_normalizer import LLMSpecNormalizer
from src.services.business_logic_extractor import BusinessLogicExtractor


def test_option_b_only():
    """Test ONLY LLMSpecNormalizer (no fallback)"""

    print("=" * 80)
    print("TEST: Option B ONLY (LLM Normalization)")
    print("=" * 80 + "\n")

    # Load markdown spec
    spec_path = Path("tests/e2e/test_specs/ecommerce_api_simple.md")
    with open(spec_path) as f:
        markdown_spec = f.read()

    print(f"Input: {spec_path}")
    print(f"  Size: {len(markdown_spec)} chars\n")

    # Normalize with LLM ONLY (no fallback)
    print("Normalizing with LLMSpecNormalizer (no fallback)...")
    normalizer = LLMSpecNormalizer()  # No fallback

    try:
        normalized_spec = normalizer.normalize(markdown_spec)
        print("✅ LLM normalization succeeded\n")
    except Exception as e:
        print(f"❌ LLM normalization FAILED: {e}\n")
        return None

    # Show spec structure
    print("Normalized Spec Structure:")
    print("-" * 80)
    entities = normalized_spec.get("entities", [])
    print(f"  Entities: {len(entities)}")
    for e in entities:
        print(f"    - {e['name']}: {len(e.get('fields', []))} fields")

    relationships = normalized_spec.get("relationships", [])
    print(f"\n  Relationships: {len(relationships)}")

    endpoints = normalized_spec.get("endpoints", [])
    print(f"  Endpoints: {len(endpoints)}\n")

    # Extract validations
    print("Extracting validations from LLM-normalized spec...")
    extractor = BusinessLogicExtractor()

    try:
        validations = extractor.extract_validations(normalized_spec)
        print(f"✅ Extraction succeeded\n")
    except Exception as e:
        print(f"❌ Extraction FAILED: {e}\n")
        return None

    # Analysis
    print("=" * 80)
    print("RESULTS: Option B (LLM Only)")
    print("=" * 80 + "\n")

    print(f"Total validations extracted: {len(validations)}/62")
    print(f"Coverage: {len(validations)/62*100:.1f}%\n")

    # Breakdown by type
    by_type = {}
    for v in validations:
        v_type = str(v.type)
        by_type[v_type] = by_type.get(v_type, 0) + 1

    print("Breakdown by Type:")
    for v_type in sorted(by_type.keys()):
        count = by_type[v_type]
        pct = (count / len(validations) * 100) if validations else 0
        print(f"  {v_type:30} {count:3} ({pct:5.1f}%)")

    # Check for duplicates
    print("\n" + "-" * 80)
    print("Duplicate Analysis:")
    seen = set()
    duplicates = []
    for v in validations:
        key = (getattr(v, 'entity_name', ''),
               getattr(v, 'field_name', ''),
               str(v.type),
               getattr(v, 'description', ''))
        if key in seen:
            duplicates.append(v)
        seen.add(key)

    print(f"Total unique validations: {len(seen)}")
    print(f"Duplicates found: {len(duplicates)}")
    if duplicates and len(duplicates) <= 5:
        print("\nDuplicate examples:")
        for d in duplicates[:5]:
            print(f"  - {getattr(d, 'entity_name', '?')}.{getattr(d, 'field_name', '?')}: {d.type}")

    return {
        "total": len(validations),
        "unique": len(seen),
        "duplicates": len(duplicates),
        "coverage": len(validations) / 62 * 100,
        "by_type": by_type
    }


if __name__ == "__main__":
    print("\n🔬 TESTING OPTION B ONLY (LLM)\n")

    result = test_option_b_only()

    if result:
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"✅ Option B extracted: {result['total']}/62 ({result['coverage']:.1f}%)")
        print(f"   Unique: {result['unique']}, Duplicates: {result['duplicates']}")
        exit(0)
    else:
        print("\n" + "=" * 80)
        print("FAILED")
        print("=" * 80)
        exit(1)
