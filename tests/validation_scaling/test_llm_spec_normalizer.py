"""
Test: LLM Spec Normalizer (Option B & C)

Tests the LLMSpecNormalizer and HybridSpecNormalizer on ecommerce_api_simple.md.
Goal: Verify that normalization converts 44/62 gap → 90-100+/62 validations.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.llm_spec_normalizer import LLMSpecNormalizer, HybridSpecNormalizer
from src.services.business_logic_extractor import BusinessLogicExtractor


def test_llm_normalizer_basic():
    """Test Option B: Basic LLM normalization"""
    print("=" * 80)
    print("TEST: LLM Spec Normalizer (Option B)")
    print("=" * 80 + "\n")

    # Load markdown spec
    spec_path = Path("tests/e2e/test_specs/ecommerce_api_simple.md")
    with open(spec_path) as f:
        markdown_spec = f.read()

    print(f"Input: {spec_path}")
    print(f"  Markdown length: {len(markdown_spec)} chars")
    print(f"  Markdown lines: {len(markdown_spec.splitlines())}\n")

    # Normalize using LLM
    print("Normalizing with LLM...")
    normalizer = LLMSpecNormalizer()
    try:
        formal_spec = normalizer.normalize(markdown_spec)
        print("✅ LLM normalization succeeded\n")
    except Exception as e:
        print(f"❌ LLM normalization failed: {e}\n")
        return False

    # Show normalized spec structure
    print("Normalized Spec Structure:")
    print("-" * 80)
    print(f"  Entities: {len(formal_spec.get('entities', []))}")
    for entity in formal_spec.get('entities', []):
        print(f"    - {entity['name']}: {len(entity.get('fields', []))} fields")

    print(f"\n  Relationships: {len(formal_spec.get('relationships', []))}")
    print(f"  Endpoints: {len(formal_spec.get('endpoints', []))}\n")

    # Extract validations from normalized spec
    print("Extracting validations from normalized spec...")
    extractor = BusinessLogicExtractor()
    validations = extractor.extract_validations(formal_spec)

    print(f"✅ Extracted: {len(validations)} validations\n")

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

    # Analysis
    print(f"\n{'='*80}")
    print("ANALYSIS")
    print(f"{'='*80}\n")

    expected = 62
    coverage = (len(validations) / expected * 100) if expected > 0 else 0

    print(f"Target:    62/62 (100%)")
    print(f"Achieved:  {len(validations)}/{expected} ({coverage:.1f}%)")
    print(f"\nGap vs E2E real (44):  {len(validations) - 44} extra validations")
    print(f"Gap vs test_all (94):  {94 - len(validations)} fewer validations")

    if coverage >= 90:
        print(f"\n✅ EXCELLENT - Option B works! Coverage ≥ 90%")
        return True
    elif coverage >= 80:
        print(f"\n⚠️  GOOD - Option B viable but could improve")
        return False
    else:
        print(f"\n❌ BELOW TARGET - Option B needs improvement")
        return False


def test_hybrid_normalizer():
    """Test Option C: Hybrid normalization with fallback"""
    print("\n" + "=" * 80)
    print("TEST: Hybrid Spec Normalizer (Option C)")
    print("=" * 80 + "\n")

    # Load markdown spec
    spec_path = Path("tests/e2e/test_specs/ecommerce_api_simple.md")
    with open(spec_path) as f:
        markdown_spec = f.read()

    # Load fallback (formal JSON if it exists)
    fallback_spec = None
    fallback_path = Path("tests/e2e/test_specs/ecommerce_api_formal.json")
    if fallback_path.exists():
        with open(fallback_path) as f:
            fallback_spec = json.load(f)
        print(f"Fallback spec loaded: {fallback_path}\n")

    # Create hybrid normalizer
    hybrid = HybridSpecNormalizer(max_retries=2, fallback_spec=fallback_spec)

    print("Normalizing with Hybrid (LLM + retry + fallback)...")
    try:
        formal_spec = hybrid.normalize(markdown_spec)
        print("✅ Hybrid normalization succeeded\n")
    except Exception as e:
        print(f"❌ Hybrid normalization failed: {e}\n")
        return False

    # Extract validations
    print("Extracting validations from hybrid-normalized spec...")
    extractor = BusinessLogicExtractor()
    validations = extractor.extract_validations(formal_spec)

    print(f"✅ Extracted: {len(validations)} validations\n")

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

    # Analysis
    print(f"\n{'='*80}")
    print("ANALYSIS")
    print(f"{'='*80}\n")

    expected = 62
    coverage = (len(validations) / expected * 100) if expected > 0 else 0

    print(f"Target:    62/62 (100%)")
    print(f"Achieved:  {len(validations)}/{expected} ({coverage:.1f}%)")

    if coverage >= 90:
        print(f"\n✅ EXCELLENT - Option C works! Coverage ≥ 90%")
        return True
    elif coverage >= 80:
        print(f"\n⚠️  GOOD - Option C viable")
        return False
    else:
        print(f"\n❌ BELOW TARGET - Option C needs improvement")
        return False


def save_normalized_spec(markdown_path: str, output_path: str):
    """Save normalized spec to file for reuse"""
    print("=" * 80)
    print("UTILITY: Save Normalized Spec")
    print("=" * 80 + "\n")

    # Load markdown
    with open(markdown_path) as f:
        markdown_spec = f.read()

    # Normalize
    print(f"Normalizing {markdown_path}...")
    normalizer = LLMSpecNormalizer()
    formal_spec = normalizer.normalize(markdown_spec)

    # Save
    with open(output_path, 'w') as f:
        json.dump(formal_spec, f, indent=2)

    print(f"✅ Saved to {output_path}\n")


if __name__ == "__main__":
    print("\n🧪 TESTING LLM SPEC NORMALIZER (OPTIONS B & C)\n")

    # Test Option B
    result_b = test_llm_normalizer_basic()

    # Test Option C
    result_c = test_hybrid_normalizer()

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80 + "\n")

    print(f"Option B (LLM Normalizer):   {'✅ PASSED' if result_b else '❌ FAILED'}")
    print(f"Option C (Hybrid):            {'✅ PASSED' if result_c else '❌ FAILED'}")

    if result_b and result_c:
        print(f"\n✅ Both options viable - ready for integration")
        exit(0)
    else:
        print(f"\n⚠️  At least one option needs improvement")
        exit(1)
