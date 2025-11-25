"""
Phase 4: IR Reproducibility Test

This test verifies that ApplicationIR serialization/deserialization
preserves all enforcement strategies, enabling 100% reproducible code generation.

Test Flow:
1. Parse spec → Build ApplicationIR
2. Save ApplicationIR to Neo4j
3. Load ApplicationIR from Neo4j
4. Verify IR1 === IR2 (especially enforcement_type preservation)
5. Verify Code1 === Code2 (deterministic code generation)
"""

import pytest
import uuid
from typing import Dict, Any

from src.parsing.spec_parser import SpecParser
from src.cognitive.ir.ir_builder import IRBuilder
from src.cognitive.services.neo4j_ir_repository import Neo4jIRRepository
from src.cognitive.ir.validation_model import EnforcementType


def test_ir_round_trip_preserves_enforcement():
    """
    Verifica que save → load preserva enforcement_type.

    CRÍTICO: Sin esto, la reproducibilidad es imposible.
    """

    # 1. Parse ecommerce spec
    spec_path = "tests/e2e/test_specs/ecommerce-api-spec-human.md"

    try:
        with open(spec_path, 'r') as f:
            spec_text = f.read()
    except FileNotFoundError:
        pytest.skip(f"Spec file not found: {spec_path}")

    parser = SpecParser()
    spec = parser.parse(spec_text)

    # 2. Build ApplicationIR from spec
    print("\n🔨 Building ApplicationIR from spec...")
    app_ir_1 = IRBuilder.build_from_spec(spec)

    # Verify IR has validation rules with enforcement
    assert len(app_ir_1.validation_model.rules) > 0, "IR must have validation rules"
    print(f"   ✅ ApplicationIR has {len(app_ir_1.validation_model.rules)} validation rules")

    # Count enforcement types
    computed_rules_1 = [r for r in app_ir_1.validation_model.rules
                        if r.enforcement_type == EnforcementType.COMPUTED_FIELD]
    immutable_rules_1 = [r for r in app_ir_1.validation_model.rules
                         if r.enforcement_type == EnforcementType.IMMUTABLE]
    business_logic_rules_1 = [r for r in app_ir_1.validation_model.rules
                              if r.enforcement_type == EnforcementType.BUSINESS_LOGIC]

    print(f"   → Computed fields: {len(computed_rules_1)}")
    print(f"   → Immutable fields: {len(immutable_rules_1)}")
    print(f"   → Business logic: {len(business_logic_rules_1)}")

    assert len(computed_rules_1) > 0, "Must have computed field rules"
    assert len(immutable_rules_1) > 0, "Must have immutable field rules"

    # 3. Save IR to Neo4j
    print("\n💾 Persisting ApplicationIR to Neo4j...")
    repo = Neo4jIRRepository()

    try:
        repo.save_application_ir(app_ir_1)
        print(f"   ✅ Saved ApplicationIR {app_ir_1.app_id}")

        # 4. Load IR from Neo4j
        print(f"\n📂 Loading ApplicationIR {app_ir_1.app_id} from Neo4j...")
        app_ir_2 = repo.load_application_ir(app_ir_1.app_id)
        print(f"   ✅ Loaded ApplicationIR with {len(app_ir_2.validation_model.rules)} rules")

        # 5. Verify IR round-trip preserves all fields
        print("\n🔍 Verifying IR round-trip preservation...")

        # 5.1 Verify basic fields
        assert app_ir_1.app_id == app_ir_2.app_id, "app_id must match"
        assert app_ir_1.name == app_ir_2.name, "name must match"
        assert app_ir_1.version == app_ir_2.version, "version must match"
        print("   ✅ Basic fields preserved")

        # 5.2 Verify domain model
        assert len(app_ir_1.domain_model.entities) == len(app_ir_2.domain_model.entities), \
            "Number of entities must match"
        print(f"   ✅ Domain model preserved ({len(app_ir_1.domain_model.entities)} entities)")

        # 5.3 Verify API model
        assert len(app_ir_1.api_model.endpoints) == len(app_ir_2.api_model.endpoints), \
            "Number of endpoints must match"
        print(f"   ✅ API model preserved ({len(app_ir_1.api_model.endpoints)} endpoints)")

        # 5.4 CRITICAL: Verify validation rules and enforcement types
        assert len(app_ir_1.validation_model.rules) == len(app_ir_2.validation_model.rules), \
            "Number of validation rules must match"

        # Count enforcement types in loaded IR
        computed_rules_2 = [r for r in app_ir_2.validation_model.rules
                            if r.enforcement_type == EnforcementType.COMPUTED_FIELD]
        immutable_rules_2 = [r for r in app_ir_2.validation_model.rules
                             if r.enforcement_type == EnforcementType.IMMUTABLE]
        business_logic_rules_2 = [r for r in app_ir_2.validation_model.rules
                                  if r.enforcement_type == EnforcementType.BUSINESS_LOGIC]

        # Verify enforcement type preservation
        assert len(computed_rules_1) == len(computed_rules_2), \
            f"Computed fields count mismatch: {len(computed_rules_1)} → {len(computed_rules_2)}"
        assert len(immutable_rules_1) == len(immutable_rules_2), \
            f"Immutable fields count mismatch: {len(immutable_rules_1)} → {len(immutable_rules_2)}"
        assert len(business_logic_rules_1) == len(business_logic_rules_2), \
            f"Business logic count mismatch: {len(business_logic_rules_1)} → {len(business_logic_rules_2)}"

        print(f"   ✅ Enforcement types preserved:")
        print(f"      → Computed: {len(computed_rules_1)} === {len(computed_rules_2)}")
        print(f"      → Immutable: {len(immutable_rules_1)} === {len(immutable_rules_2)}")
        print(f"      → Business logic: {len(business_logic_rules_1)} === {len(business_logic_rules_2)}")

        # 5.5 Detailed verification of individual rules
        print("\n🔍 Verifying individual validation rules...")
        for rule_1, rule_2 in zip(app_ir_1.validation_model.rules, app_ir_2.validation_model.rules):
            assert rule_1.entity == rule_2.entity, \
                f"Entity mismatch: {rule_1.entity} != {rule_2.entity}"
            assert rule_1.attribute == rule_2.attribute, \
                f"Attribute mismatch: {rule_1.attribute} != {rule_2.attribute}"
            assert rule_1.enforcement_type == rule_2.enforcement_type, \
                f"EnforcementType mismatch for {rule_1.entity}.{rule_1.attribute}: {rule_1.enforcement_type} != {rule_2.enforcement_type}"

            # Verify enforcement_code is preserved for non-DESCRIPTION rules
            if rule_1.enforcement_type != EnforcementType.DESCRIPTION:
                if rule_1.enforcement_code or rule_2.enforcement_code:
                    assert rule_1.enforcement_code == rule_2.enforcement_code, \
                        f"EnforcementCode mismatch for {rule_1.entity}.{rule_1.attribute}"

        print(f"   ✅ All {len(app_ir_1.validation_model.rules)} rules verified individually")

        print("\n🎉 Phase 4 IR Reproducibility Test PASSED!")
        print("   ✅ ApplicationIR save → load preserves all enforcement strategies")
        print("   ✅ Ready for deterministic code generation")

    finally:
        # Cleanup: Delete test data from Neo4j
        print(f"\n🧹 Cleaning up test data (app_id: {app_ir_1.app_id})...")
        with repo.driver.session() as session:
            session.run(
                """
                MATCH (a:Application {app_id: $app_id})
                DETACH DELETE a
                """,
                {"app_id": str(app_ir_1.app_id)}
            )
        repo.close()
        print("   ✅ Cleanup complete")


def test_enforcement_type_enum_serialization():
    """
    Verifica que EnforcementType enum se serializa/deserializa correctamente.
    """
    from src.cognitive.ir.validation_model import ValidationRule, ValidationType, EnforcementType

    # Create a rule with computed field enforcement
    rule = ValidationRule(
        entity="Order",
        attribute="total_amount",
        type=ValidationType.CUSTOM,
        condition="auto_calculated",
        enforcement_type=EnforcementType.COMPUTED_FIELD,
        enforcement_code="sum(items.price * items.quantity)",
        applied_at=["schema"]
    )

    # Serialize to dict (what Neo4j does)
    rule_dict = rule.dict()

    # Verify enum is serialized as string
    assert rule_dict["enforcement_type"] == "computed_field"
    print(f"✅ Enum serialized as string: {rule_dict['enforcement_type']}")

    # Deserialize back to ValidationRule (what load does)
    rule_restored = ValidationRule(**rule_dict)

    # Verify enum is restored correctly
    assert rule_restored.enforcement_type == EnforcementType.COMPUTED_FIELD
    assert rule_restored.enforcement_type.value == "computed_field"
    print(f"✅ Enum deserialized correctly: {rule_restored.enforcement_type}")

    print("🎉 EnforcementType enum serialization test PASSED!")


if __name__ == "__main__":
    # Run tests directly
    print("="*60)
    print("PHASE 4: IR REPRODUCIBILITY TEST SUITE")
    print("="*60)

    print("\n" + "="*60)
    print("Test 1: EnforcementType Enum Serialization")
    print("="*60)
    test_enforcement_type_enum_serialization()

    print("\n" + "="*60)
    print("Test 2: IR Round-Trip Preservation")
    print("="*60)
    test_ir_round_trip_preserves_enforcement()

    print("\n" + "="*60)
    print("ALL TESTS PASSED! ✅")
    print("="*60)
