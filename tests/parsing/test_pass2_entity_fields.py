"""
Unit tests for Pass 2: Entity Field Extraction with Regex

Validates that regex patterns correctly extract fields, types, constraints,
and enforcement types from entity context windows.
"""
from pathlib import Path
from src.parsing.spec_parser import SpecParser
from src.parsing.field_extractor import (
    extract_entity_fields,
    detect_enforcement_type,
    extract_constraints
)


def test_field_extraction_on_ecommerce_spec():
    """
    Test that Pass 2 extracts fields correctly from ecommerce spec.
    """
    spec_path = Path("tests/e2e/test_specs/ecommerce-api-spec-human.md")
    assert spec_path.exists(), f"Test spec not found: {spec_path}"

    # Read full spec
    content = spec_path.read_text(encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"TEST: Pass 2 Field Extraction")
    print(f"{'='*60}")
    print(f"Spec: {spec_path.name}")

    # Run hierarchical extraction (Pass 1 + Pass 2)
    parser = SpecParser()
    entity_details = parser._extract_with_hierarchical_llm(content)

    assert entity_details is not None, "Hierarchical extraction failed"
    assert len(entity_details) > 0, f"No entities extracted"

    print(f"\n📊 EXTRACTED ENTITIES:")
    for entity_name, detail in entity_details.items():
        field_count = len(detail.fields)
        print(f"  {entity_name}: {field_count} fields")

        # Show first 3 fields
        for field in detail.fields[:3]:
            enforcement = f"[{field.enforcement_type}]" if field.enforcement_type != "normal" else ""
            print(f"    - {field.name} ({field.type}) {enforcement}")
        if len(detail.fields) > 3:
            print(f"    ... and {len(detail.fields) - 3} more")

    # Validate entity count
    assert len(entity_details) == 6, f"Expected 6 entities, got {len(entity_details)}"

    # Validate field extraction for Product entity
    assert "Product" in entity_details, "Product entity not found"
    product = entity_details["Product"]
    assert len(product.fields) > 0, "Product has no fields"

    print(f"\n✅ Product Fields:")
    for field in product.fields:
        enforcement = f" [{field.enforcement_type}]" if field.enforcement_type != "normal" else ""
        constraints = f" | Constraints: {', '.join(field.constraints)}" if field.constraints else ""
        print(f"  - {field.name} ({field.type}){enforcement}{constraints}")
        print(f"    └─ {field.description}")

    # Validate enforcement type detection
    enforcement_types = [f.enforcement_type for f in product.fields]
    print(f"\n✅ Enforcement types found: {set(enforcement_types)}")

    print(f"\n{'='*60}")
    print(f"🎉 PASS 2 TEST PASSED")
    print(f"{'='*60}\n")


def test_enforcement_type_detection():
    """
    Test that enforcement types are correctly detected from descriptions.
    """
    print(f"\n{'='*60}")
    print(f"TEST: Enforcement Type Detection")
    print(f"{'='*60}\n")

    # Test computed field
    enforcement, details = detect_enforcement_type(
        "order_total",
        "Computed field: sum of all item totals (quantity × unit_price)"
    )
    assert enforcement == "computed", f"Expected computed, got {enforcement}"
    print(f"✅ computed: order_total - {details}")

    # Test immutable field
    enforcement, details = detect_enforcement_type(
        "created_at",
        "Immutable field - captures creation timestamp at record creation"
    )
    assert enforcement == "immutable", f"Expected immutable, got {enforcement}"
    print(f"✅ immutable: created_at - {details}")

    # Test validator field
    enforcement, details = detect_enforcement_type(
        "email",
        "Unique email address - requires email format validation"
    )
    assert enforcement == "validator", f"Expected validator, got {enforcement}"
    print(f"✅ validator: email - {details}")

    # Test normal field
    enforcement, details = detect_enforcement_type(
        "quantity",
        "Number of items in cart"
    )
    assert enforcement == "normal", f"Expected normal, got {enforcement}"
    print(f"✅ normal: quantity")

    print(f"\n{'='*60}\n")


def test_constraint_extraction():
    """
    Test that constraints are correctly extracted from descriptions.
    """
    print(f"\n{'='*60}")
    print(f"TEST: Constraint Extraction")
    print(f"{'='*60}\n")

    # Test unique constraint
    constraints = extract_constraints("Unique email address", "string")
    assert "unique" in constraints, f"Expected 'unique' in {constraints}"
    print(f"✅ unique constraint: {constraints}")

    # Test length constraint
    constraints = extract_constraints("Product name, 1-255 characters", "string")
    assert any("length" in c for c in constraints), f"Expected length constraint in {constraints}"
    print(f"✅ length constraint: {constraints}")

    # Test range constraint
    constraints = extract_constraints("Positive integer quantity, range 1-1000", "integer")
    assert any("range" in c for c in constraints), f"Expected range constraint in {constraints}"
    print(f"✅ range constraint: {constraints}")

    # Test pattern constraint
    constraints = extract_constraints("Email address with email format validation", "string")
    assert any("pattern" in c for c in constraints), f"Expected pattern constraint in {constraints}"
    print(f"✅ pattern constraint: {constraints}")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    print("Running Pass 2 Field Extraction Tests...")

    try:
        test_field_extraction_on_ecommerce_spec()
        print("✅ Test 1 PASSED: Field extraction on ecommerce spec")
    except AssertionError as e:
        print(f"❌ Test 1 FAILED: {e}")

    try:
        test_enforcement_type_detection()
        print("✅ Test 2 PASSED: Enforcement type detection")
    except AssertionError as e:
        print(f"❌ Test 2 FAILED: {e}")

    try:
        test_constraint_extraction()
        print("✅ Test 3 PASSED: Constraint extraction")
    except AssertionError as e:
        print(f"❌ Test 3 FAILED: {e}")

    print("\n" + "="*60)
    print("Pass 2 Testing Complete")
    print("="*60)
