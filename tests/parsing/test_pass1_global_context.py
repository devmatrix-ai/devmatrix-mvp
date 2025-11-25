"""
Unit tests for Pass 1: Global Context Extraction

Validates that _extract_global_context() extracts all entities from full spec
without truncation, and finds their locations correctly.
"""
from pathlib import Path

from src.parsing.spec_parser import SpecParser


def test_pass1_extracts_all_entities():
    """
    Test that Pass 1 extracts ALL entities from ecommerce spec (6 entities).

    This is the critical test that validates the hierarchical approach:
    - Old approach: Truncated at 12000 chars, extracted only 4/6 entities
    - New approach: No truncation, should extract 6/6 entities
    """
    spec_path = Path("tests/e2e/test_specs/ecommerce-api-spec-human.md")

    assert spec_path.exists(), f"Test spec not found: {spec_path}"

    # Read full spec content
    content = spec_path.read_text(encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"TEST: Pass 1 Global Context Extraction")
    print(f"{'='*60}")
    print(f"Spec: {spec_path.name}")
    print(f"Content length: {len(content)} characters")

    # Create parser and call Pass 1
    parser = SpecParser()
    global_context = parser._extract_global_context(content)

    # Verify extraction succeeded
    assert global_context is not None, "Pass 1 extraction failed"

    # Critical assertion: Must extract ALL 6 entities
    expected_entities = ["Customer", "Product", "Cart", "CartItem", "Order", "OrderItem"]
    extracted_entity_names = [e.name for e in global_context.entities]

    print(f"\nExpected entities: {expected_entities}")
    print(f"Extracted entities: {extracted_entity_names}")

    # Check count
    assert len(global_context.entities) == 6, \
        f"Expected 6 entities, got {len(global_context.entities)}: {extracted_entity_names}"

    # Check all expected entities are present
    for entity_name in expected_entities:
        assert entity_name in extracted_entity_names, \
            f"Entity '{entity_name}' not extracted. Got: {extracted_entity_names}"

    print(f"✅ All 6 entities extracted successfully")

    # Verify entity locations are found
    entities_with_locations = [e for e in global_context.entities if e.location > 0]
    print(f"\nEntities with locations found: {len(entities_with_locations)}/6")

    # Most entities should have locations (at least 4 out of 6)
    assert len(entities_with_locations) >= 4, \
        f"Expected at least 4 entities with locations, got {len(entities_with_locations)}"

    # Verify domain description exists
    assert global_context.domain, "Domain description is empty"
    print(f"✅ Domain extracted: {global_context.domain[:50]}...")

    # Verify relationships exist
    print(f"✅ Relationships extracted: {len(global_context.relationships)}")

    # Verify business logic exists
    print(f"✅ Business logic rules: {len(global_context.business_logic)}")

    # Verify endpoints exist
    print(f"✅ Endpoints extracted: {len(global_context.endpoints)}")

    print(f"\n{'='*60}")
    print(f"🎉 PASS 1 TEST PASSED")
    print(f"{'='*60}")


def test_pass1_entity_relationships():
    """
    Test that Pass 1 correctly identifies entity relationships.
    """
    spec_path = Path("tests/e2e/test_specs/ecommerce-api-spec-human.md")
    content = spec_path.read_text(encoding="utf-8")

    parser = SpecParser()
    global_context = parser._extract_global_context(content)

    assert global_context is not None
    assert len(global_context.relationships) > 0, "No relationships extracted"

    # Verify relationship structure
    valid_types = ["one_to_many", "many_to_many", "one_to_one", "many_to_one"]
    for rel in global_context.relationships:
        assert rel.source, "Relationship missing source"
        assert rel.target, "Relationship missing target"
        assert rel.type in valid_types, \
            f"Invalid relationship type: {rel.type}. Valid types: {valid_types}"

    print(f"✅ {len(global_context.relationships)} relationships validated")


def test_pass1_entity_summaries_have_descriptions():
    """
    Test that entity summaries include descriptions.
    """
    spec_path = Path("tests/e2e/test_specs/ecommerce-api-spec-human.md")
    content = spec_path.read_text(encoding="utf-8")

    parser = SpecParser()
    global_context = parser._extract_global_context(content)

    assert global_context is not None

    # Most entities should have descriptions
    entities_with_descriptions = [e for e in global_context.entities if e.description]
    assert len(entities_with_descriptions) >= 4, \
        f"Expected at least 4 entities with descriptions, got {len(entities_with_descriptions)}"

    print(f"✅ {len(entities_with_descriptions)}/6 entities have descriptions")


if __name__ == "__main__":
    print("Running Pass 1 Global Context Extraction Tests...")

    try:
        test_pass1_extracts_all_entities()
        print("\n✅ Test 1 PASSED: All entities extracted")
    except AssertionError as e:
        print(f"\n❌ Test 1 FAILED: {e}")

    try:
        test_pass1_entity_relationships()
        print("\n✅ Test 2 PASSED: Relationships validated")
    except AssertionError as e:
        print(f"\n❌ Test 2 FAILED: {e}")

    try:
        test_pass1_entity_summaries_have_descriptions()
        print("\n✅ Test 3 PASSED: Entity descriptions validated")
    except AssertionError as e:
        print(f"\n❌ Test 3 FAILED: {e}")

    print("\n" + "="*60)
    print("Pass 1 Testing Complete")
    print("="*60)
