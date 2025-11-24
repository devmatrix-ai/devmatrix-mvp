"""
Test: JSON Formal ONLY (No LLM, No Normalization)

Measures real validation count from formal JSON spec alone.
No LLM, no transformation - pure formal JSON extraction.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.business_logic_extractor import BusinessLogicExtractor


def test_json_formal_only():
    """Test ONLY formal JSON extraction (no LLM)"""

    print("=" * 80)
    print("TEST: JSON Formal ONLY (No LLM)")
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

    endpoints = spec.get("endpoints", [])
    print(f"  Endpoints: {len(endpoints)}\n")

    # Extract validations
    print("Extracting validations from formal JSON spec...")
    extractor = BusinessLogicExtractor()

    try:
        validations = extractor.extract_validations(spec)
        print(f"✅ Extraction succeeded\n")
    except Exception as e:
        print(f"❌ Extraction FAILED: {e}\n")
        return None

    # Analysis
    print("=" * 80)
    print("RESULTS: JSON Formal Only")
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
    print("\n🔬 TESTING JSON FORMAL ONLY\n")

    result = test_json_formal_only()

    if result:
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"✅ JSON Formal extracted: {result['total']}/62 ({result['coverage']:.1f}%)")
        print(f"   Unique: {result['unique']}, Duplicates: {result['duplicates']}")
        exit(0)
    else:
        print("\n" + "=" * 80)
        print("FAILED")
        print("=" * 80)
        exit(1)
