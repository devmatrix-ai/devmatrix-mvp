"""
Test: Ecommerce API Formal Spec

Validates that the formal JSON spec achieves 90-100+ validation coverage.
This spec is equivalent to the ecommerce_api_simple.md but with explicit constraints.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.business_logic_extractor import BusinessLogicExtractor


def test_ecommerce_formal_spec():
    """Test extraction from formal ecommerce spec"""

    print("="*80)
    print("VALIDATION EXTRACTION TEST: Ecommerce API (Formal Spec)")
    print("="*80 + "\n")

    # Load spec
    spec_path = Path("tests/e2e/test_specs/ecommerce_api_formal.json")
    with open(spec_path) as f:
        spec = json.load(f)

    print(f"Spec loaded from: {spec_path}")
    print(f"  Entities: {len(spec['entities'])}")
    print(f"  Fields: {sum(len(e['fields']) for e in spec['entities'])}")
    print(f"  Relationships: {len(spec['relationships'])}")
    print(f"  Endpoints: {len(spec['endpoints'])}\n")

    # Extract validations
    extractor = BusinessLogicExtractor()
    validations = extractor.extract_validations(spec)

    print(f"RESULT: {len(validations)} validations extracted\n")

    # Breakdown
    by_type = {}
    for v in validations:
        v_type = str(v.type)
        by_type[v_type] = by_type.get(v_type, 0) + 1

    print("Breakdown by Type:")
    for v_type in sorted(by_type.keys()):
        count = by_type[v_type]
        pct = (count / len(validations) * 100) if validations else 0
        print(f"  {v_type:30} {count:3} ({pct:5.1f}%)")

    # Summary
    print(f"\n{'='*80}")
    print(f"VALIDATION COVERAGE ANALYSIS")
    print(f"{'='*80}\n")

    expected = 62
    coverage = (len(validations) / expected * 100) if expected > 0 else 0

    print(f"Target:    62/62 (100%)")
    print(f"Achieved:  {len(validations)}/{expected} ({coverage:.1f}%)")

    if coverage >= 100:
        print(f"\n✅ EXCELLENT - Coverage target ACHIEVED!")
        print(f"   Formal spec successfully replaces markdown version.")
        return True
    elif coverage >= 80:
        print(f"\n⚠️  GOOD - Coverage is good but below target")
        print(f"   Missing: {expected - len(validations)} validations")
        return False
    else:
        print(f"\n❌ BELOW TARGET - Coverage is insufficient")
        print(f"   Missing: {expected - len(validations)} validations")
        return False


if __name__ == "__main__":
    success = test_ecommerce_formal_spec()
    exit(0 if success else 1)
