"""
Phase 4: IR Reproducibility with Structured Specs

This test validates the COMPLETE E2E flow using structured YAML specifications:
1. Parse structured YAML spec → SpecRequirements
2. Build ApplicationIR with enforcement types
3. Save to Neo4j
4. Load from Neo4j
5. Verify enforcement preservation
"""

from pathlib import Path

from src.parsing.structured_spec_parser import StructuredSpecParser
from src.cognitive.ir.ir_builder import IRBuilder
from src.cognitive.services.neo4j_ir_repository import Neo4jIRRepository
from src.cognitive.ir.validation_model import EnforcementType


def test_phase4_structured_e2e():
    """
    Complete E2E test with structured spec:
    Spec YAML → Parse → IR → Neo4j → Load → Verify
    """

    print("\n" + "="*60)
    print("PHASE 4: STRUCTURED SPEC E2E TEST")
    print("="*60)

    # 1. Parse structured spec
    spec_path = Path("tests/e2e/test_specs/ecommerce-api-structured.yaml")

    print(f"\n📄 Parsing structured spec: {spec_path.name}")
    parser = StructuredSpecParser()
    spec = parser.parse(spec_path)

    print(f"   ✅ Parsed {len(spec.entities)} entities, {len(spec.endpoints)} endpoints")

    # Verify parsing worked
    assert len(spec.entities) > 0, "Must have entities"
    assert any(e.name == "Order" for e in spec.entities), "Must have Order entity"

    # 2. Build ApplicationIR from spec
    print("\n🔨 Building ApplicationIR from spec...")
    app_ir_1 = IRBuilder.build_from_spec(spec)

    print(f"   ✅ ApplicationIR has {len(app_ir_1.validation_model.rules)} validation rules")

    # Count enforcement types
    computed_rules_1 = [r for r in app_ir_1.validation_model.rules
                        if r.enforcement_type == EnforcementType.COMPUTED_FIELD]
    immutable_rules_1 = [r for r in app_ir_1.validation_model.rules
                         if r.enforcement_type == EnforcementType.IMMUTABLE]
    validator_rules_1 = [r for r in app_ir_1.validation_model.rules
                         if r.enforcement_type == EnforcementType.VALIDATOR]

    print(f"   → Computed fields: {len(computed_rules_1)}")
    print(f"   → Immutable fields: {len(immutable_rules_1)}")
    print(f"   → Validators: {len(validator_rules_1)}")

    # Verify we have enforcement types
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

        # 5. Verify IR round-trip preservation
        print("\n🔍 Verifying IR round-trip preservation...")

        # 5.1 Basic fields
        assert app_ir_1.app_id == app_ir_2.app_id
        assert app_ir_1.name == app_ir_2.name
        print("   ✅ Basic fields preserved")

        # 5.2 Domain model
        assert len(app_ir_1.domain_model.entities) == len(app_ir_2.domain_model.entities)
        print(f"   ✅ Domain model preserved ({len(app_ir_1.domain_model.entities)} entities)")

        # 5.3 API model
        assert len(app_ir_1.api_model.endpoints) == len(app_ir_2.api_model.endpoints)
        print(f"   ✅ API model preserved ({len(app_ir_1.api_model.endpoints)} endpoints)")

        # 5.4 CRITICAL: Verification of enforcement types
        assert len(app_ir_1.validation_model.rules) == len(app_ir_2.validation_model.rules)

        computed_rules_2 = [r for r in app_ir_2.validation_model.rules
                            if r.enforcement_type == EnforcementType.COMPUTED_FIELD]
        immutable_rules_2 = [r for r in app_ir_2.validation_model.rules
                             if r.enforcement_type == EnforcementType.IMMUTABLE]
        validator_rules_2 = [r for r in app_ir_2.validation_model.rules
                             if r.enforcement_type == EnforcementType.VALIDATOR]

        assert len(computed_rules_1) == len(computed_rules_2), \
            f"Computed count mismatch: {len(computed_rules_1)} → {len(computed_rules_2)}"
        assert len(immutable_rules_1) == len(immutable_rules_2), \
            f"Immutable count mismatch: {len(immutable_rules_1)} → {len(immutable_rules_2)}"

        print(f"   ✅ Enforcement types preserved:")
        print(f"      → Computed: {len(computed_rules_1)} === {len(computed_rules_2)}")
        print(f"      → Immutable: {len(immutable_rules_1)} === {len(immutable_rules_2)}")
        print(f"      → Validators: {len(validator_rules_1)} === {len(validator_rules_2)}")

        # 5.5 Detailed rule verification
        print("\n🔍 Verifying individual validation rules...")
        for rule_1, rule_2 in zip(app_ir_1.validation_model.rules, app_ir_2.validation_model.rules):
            assert rule_1.entity == rule_2.entity
            assert rule_1.attribute == rule_2.attribute
            assert rule_1.enforcement_type == rule_2.enforcement_type

        print(f"   ✅ All {len(app_ir_1.validation_model.rules)} rules verified individually")

        print("\n" + "="*60)
        print("🎉 PHASE 4 STRUCTURED SPEC E2E TEST PASSED!")
        print("="*60)
        print("✅ Structured YAML parsing works")
        print("✅ IRBuilder detects enforcement types")
        print("✅ Neo4j persistence preserves enforcement")
        print("✅ IR Reproducibility VALIDATED")
        print("\n📊 Phase 4 Status: COMPLETE ✅")
        print("📊 100% Compliance: READY ✅")
        print("="*60)

    finally:
        # Cleanup
        print(f"\n🧹 Cleaning up test data (app_id: {app_ir_1.app_id})...")
        with repo.driver.session() as session:
            session.run(
                "MATCH (a:Application {app_id: $app_id}) DETACH DELETE a",
                {"app_id": str(app_ir_1.app_id)}
            )
        repo.close()
        print("   ✅ Cleanup complete")


if __name__ == "__main__":
    test_phase4_structured_e2e()
