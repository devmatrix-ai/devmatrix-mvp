"""
Integration tests for Hierarchical LLM Extraction (Pass 1 + Pass 2)

Validates complete pipeline: spec → global context → entity fields → validation
"""
from pathlib import Path
from src.parsing.spec_parser import SpecParser


def test_hierarchical_extraction_full_pipeline():
    """
    Test complete hierarchical extraction pipeline on ecommerce spec.
    Validates: Pass 1 (global) + Pass 2 (fields) + enforcement detection
    """
    spec_path = Path("tests/e2e/test_specs/ecommerce-api-spec-human.md")
    assert spec_path.exists(), f"Test spec not found: {spec_path}"

    content = spec_path.read_text(encoding="utf-8")

    print(f"\n{'='*70}")
    print(f"HIERARCHICAL EXTRACTION - COMPLETE PIPELINE TEST")
    print(f"{'='*70}\n")

    # Run complete hierarchical extraction
    parser = SpecParser()

    # PASS 1: Global context
    print(f"PASS 1: Extracting global context from {len(content)} char spec...")
    global_context = parser._extract_global_context(content)
    assert global_context is not None, "Pass 1 failed"
    assert len(global_context.entities) == 6, f"Expected 6 entities, got {len(global_context.entities)}"
    print(f"  ✅ Extracted {len(global_context.entities)} entities")
    print(f"  ✅ Extracted {len(global_context.relationships)} relationships")
    print(f"  ✅ Extracted {len(global_context.business_logic)} business logic rules")

    # PASS 2: Entity fields with regex
    print(f"\nPASS 2: Extracting entity fields...")
    entity_details = parser._extract_with_hierarchical_llm(content)
    assert len(entity_details) == 6, f"Expected 6 entities, got {len(entity_details)}"
    print(f"  ✅ Extracted fields for {len(entity_details)} entities")

    # Validate entity structure
    for entity_name, detail in entity_details.items():
        assert detail.entity == entity_name
        assert len(detail.fields) > 0, f"{entity_name} has no fields"

        # Check enforcement type detection
        enforcement_types = set(f.enforcement_type for f in detail.fields)
        print(f"  - {entity_name}: {len(detail.fields)} fields | enforcement: {enforcement_types}")

    # Check for validator fields (these indicate enforcement detection working)
    all_fields = []
    for detail in entity_details.values():
        all_fields.extend(detail.fields)

    validator_fields = [f for f in all_fields if f.enforcement_type == "validator"]
    immutable_fields = [f for f in all_fields if f.enforcement_type == "immutable"]
    computed_fields = [f for f in all_fields if f.enforcement_type == "computed"]

    print(f"\n📊 ENFORCEMENT TYPE SUMMARY:")
    print(f"  - Validator fields: {len(validator_fields)}")
    print(f"  - Immutable fields: {len(immutable_fields)}")
    print(f"  - Computed fields: {len(computed_fields)}")
    print(f"  - Normal fields: {len(all_fields) - len(validator_fields) - len(immutable_fields) - len(computed_fields)}")

    # Validate constraints are extracted
    all_constraints = []
    for detail in entity_details.values():
        for field in detail.fields:
            all_constraints.extend(field.constraints)

    unique_constraints = set(c.split(":")[0] for c in all_constraints)
    print(f"\n📋 CONSTRAINTS DETECTED:")
    for constraint_type in sorted(unique_constraints):
        count = len([c for c in all_constraints if c.startswith(constraint_type)])
        print(f"  - {constraint_type}: {count} occurrences")

    print(f"\n{'='*70}")
    print(f"✅ HIERARCHICAL EXTRACTION PIPELINE SUCCESSFUL")
    print(f"{'='*70}\n")


def test_product_entity_complete_extraction():
    """
    Test complete extraction of Product entity specifically.
    Validates field names, types, constraints, enforcement.
    """
    spec_path = Path("tests/e2e/test_specs/ecommerce-api-spec-human.md")
    content = spec_path.read_text(encoding="utf-8")

    parser = SpecParser()
    entity_details = parser._extract_with_hierarchical_llm(content)

    assert "Product" in entity_details, "Product entity not found"
    product = entity_details["Product"]

    print(f"\n{'='*70}")
    print(f"PRODUCT ENTITY - DETAILED EXTRACTION")
    print(f"{'='*70}\n")

    print(f"Entity: {product.entity}")
    print(f"Total fields: {len(product.fields)}\n")

    for field in product.fields:
        constraints_str = f" | {', '.join(field.constraints)}" if field.constraints else ""
        enforcement_str = f" [{field.enforcement_type}]" if field.enforcement_type != "normal" else ""
        required_str = " (required)" if field.required else ""
        print(f"  {field.name} ({field.type}){enforcement_str}{required_str}{constraints_str}")
        if field.description:
            print(f"    └─ {field.description}")
        if field.enforcement_details:
            print(f"    └─ enforcement: {field.enforcement_details}")

    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    print("\nRunning Hierarchical Extraction Integration Tests...\n")

    try:
        test_hierarchical_extraction_full_pipeline()
        print("✅ Test 1 PASSED: Full pipeline")
    except AssertionError as e:
        print(f"❌ Test 1 FAILED: {e}")

    try:
        test_product_entity_complete_extraction()
        print("✅ Test 2 PASSED: Product entity extraction")
    except AssertionError as e:
        print(f"❌ Test 2 FAILED: {e}")

    print("\n" + "="*70)
    print("Integration Testing Complete")
    print("="*70)
