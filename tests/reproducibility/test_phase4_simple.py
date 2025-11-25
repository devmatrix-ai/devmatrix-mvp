"""
Phase 4: Simple IR Reproducibility Test (Mock Data)

This test validates ONLY Neo4jIRRepository.load_application_ir()
using manually created ApplicationIR with enforcement types.

NO dependencies on SpecParser or IRBuilder - pure round-trip test.
"""

import uuid
from datetime import datetime

from src.cognitive.ir.application_ir import ApplicationIR
from src.cognitive.ir.domain_model import DomainModelIR, Entity, Attribute, DataType
from src.cognitive.ir.api_model import APIModelIR, Endpoint, HttpMethod
from src.cognitive.ir.infrastructure_model import InfrastructureModelIR, DatabaseConfig, DatabaseType, ObservabilityConfig
from src.cognitive.ir.behavior_model import BehaviorModelIR
from src.cognitive.ir.validation_model import ValidationModelIR, ValidationRule, ValidationType, EnforcementType
from src.cognitive.services.neo4j_ir_repository import Neo4jIRRepository


def test_phase4_simple_round_trip():
    """
    Simple test: Create IR → Save → Load → Verify

    This validates that load_application_ir() works correctly.
    """

    print("\n" + "="*60)
    print("PHASE 4: SIMPLE IR ROUND-TRIP TEST (Mock Data)")
    print("="*60)

    # 1. Create ApplicationIR manually with enforcement types
    print("\n🔨 Creating ApplicationIR manually with enforcement...")

    # Create entities
    product_entity = Entity(
        name="Product",
        attributes=[
            Attribute(name="id", data_type=DataType.UUID, is_primary_key=True),
            Attribute(name="name", data_type=DataType.STRING),
            Attribute(name="price", data_type=DataType.FLOAT),
            Attribute(name="stock", data_type=DataType.INTEGER),
        ]
    )

    order_entity = Entity(
        name="Order",
        attributes=[
            Attribute(name="id", data_type=DataType.UUID, is_primary_key=True),
            Attribute(name="total_amount", data_type=DataType.FLOAT, description="Auto-calculated"),
            Attribute(name="creation_date", data_type=DataType.DATETIME, description="Read-only"),
        ]
    )

    domain_model = DomainModelIR(entities=[product_entity, order_entity])

    # Create API endpoints
    api_model = APIModelIR(endpoints=[
        Endpoint(path="/products", method=HttpMethod.POST, operation_id="create_product"),
        Endpoint(path="/orders", method=HttpMethod.POST, operation_id="create_order"),
    ])

    # Create infrastructure
    infrastructure_model = InfrastructureModelIR(
        database=DatabaseConfig(
            type=DatabaseType.POSTGRESQL,
            port=5432,
            name="test_db",
            user="test",
            password_env_var="DB_PASSWORD"
        )
    )

    # Create behavior model
    behavior_model = BehaviorModelIR()

    # Create validation rules with ENFORCEMENT TYPES (CRITICAL!)
    validation_rules = [
        ValidationRule(
            entity="Product",
            attribute="price",
            type=ValidationType.RANGE,
            condition="greater_than_zero",
            enforcement_type=EnforcementType.VALIDATOR,  # ✅
            enforcement_code="gt=0",
            applied_at=["schema"],
            error_message="Price must be greater than 0"
        ),
        ValidationRule(
            entity="Order",
            attribute="total_amount",
            type=ValidationType.CUSTOM,
            condition="auto_calculated",
            enforcement_type=EnforcementType.COMPUTED_FIELD,  # ✅
            enforcement_code="sum(items.price * items.quantity)",
            applied_at=["schema"],
            error_message="Total amount is auto-calculated"
        ),
        ValidationRule(
            entity="Order",
            attribute="creation_date",
            type=ValidationType.CUSTOM,
            condition="read_only",
            enforcement_type=EnforcementType.IMMUTABLE,  # ✅
            enforcement_code="exclude=True",
            applied_at=["schema", "entity"],
            error_message="Creation date is read-only"
        ),
    ]

    validation_model = ValidationModelIR(rules=validation_rules)

    # Create ApplicationIR
    app_ir_1 = ApplicationIR(
        name="Test Ecommerce API",
        description="Test application for Phase 4",
        domain_model=domain_model,
        api_model=api_model,
        infrastructure_model=infrastructure_model,
        behavior_model=behavior_model,
        validation_model=validation_model,
    )

    print(f"   ✅ Created ApplicationIR with:")
    print(f"      → {len(domain_model.entities)} entities")
    print(f"      → {len(api_model.endpoints)} endpoints")
    print(f"      → {len(validation_model.rules)} validation rules")

    # Count enforcement types
    computed = [r for r in validation_model.rules if r.enforcement_type == EnforcementType.COMPUTED_FIELD]
    immutable = [r for r in validation_model.rules if r.enforcement_type == EnforcementType.IMMUTABLE]
    validator = [r for r in validation_model.rules if r.enforcement_type == EnforcementType.VALIDATOR]

    print(f"      → Enforcement: {len(computed)} computed, {len(immutable)} immutable, {len(validator)} validator")

    # 2. Save to Neo4j
    print(f"\n💾 Saving ApplicationIR to Neo4j...")
    repo = Neo4jIRRepository()

    try:
        repo.save_application_ir(app_ir_1)
        print(f"   ✅ Saved ApplicationIR {app_ir_1.app_id}")

        # 3. Load from Neo4j
        print(f"\n📂 Loading ApplicationIR from Neo4j...")
        app_ir_2 = repo.load_application_ir(app_ir_1.app_id)
        print(f"   ✅ Loaded ApplicationIR with {len(app_ir_2.validation_model.rules)} rules")

        # 4. Verify round-trip
        print(f"\n🔍 Verifying round-trip preservation...")

        # 4.1 Basic fields
        assert app_ir_1.app_id == app_ir_2.app_id
        assert app_ir_1.name == app_ir_2.name
        print(f"   ✅ Basic fields preserved")

        # 4.2 Domain model
        assert len(app_ir_1.domain_model.entities) == len(app_ir_2.domain_model.entities)
        print(f"   ✅ Domain model preserved ({len(app_ir_1.domain_model.entities)} entities)")

        # 4.3 API model
        assert len(app_ir_1.api_model.endpoints) == len(app_ir_2.api_model.endpoints)
        print(f"   ✅ API model preserved ({len(app_ir_1.api_model.endpoints)} endpoints)")

        # 4.4 CRITICAL: Validation rules and enforcement types
        assert len(app_ir_1.validation_model.rules) == len(app_ir_2.validation_model.rules)

        computed_2 = [r for r in app_ir_2.validation_model.rules if r.enforcement_type == EnforcementType.COMPUTED_FIELD]
        immutable_2 = [r for r in app_ir_2.validation_model.rules if r.enforcement_type == EnforcementType.IMMUTABLE]
        validator_2 = [r for r in app_ir_2.validation_model.rules if r.enforcement_type == EnforcementType.VALIDATOR]

        assert len(computed) == len(computed_2)
        assert len(immutable) == len(immutable_2)
        assert len(validator) == len(validator_2)

        print(f"   ✅ Enforcement types preserved:")
        print(f"      → Computed: {len(computed)} === {len(computed_2)}")
        print(f"      → Immutable: {len(immutable)} === {len(immutable_2)}")
        print(f"      → Validator: {len(validator)} === {len(validator_2)}")

        # 4.5 Detailed rule verification
        for rule_1, rule_2 in zip(app_ir_1.validation_model.rules, app_ir_2.validation_model.rules):
            assert rule_1.entity == rule_2.entity
            assert rule_1.attribute == rule_2.attribute
            assert rule_1.enforcement_type == rule_2.enforcement_type
            assert rule_1.enforcement_code == rule_2.enforcement_code

        print(f"   ✅ All {len(app_ir_1.validation_model.rules)} rules verified individually")

        print("\n" + "="*60)
        print("🎉 PHASE 4 SIMPLE TEST PASSED!")
        print("="*60)
        print("✅ Neo4jIRRepository.load_application_ir() WORKS CORRECTLY")
        print("✅ Enforcement types are PRESERVED in round-trip")
        print("✅ IR Reproducibility VALIDATED")
        print("\n📊 Phase 4 Status: COMPLETE ✅")
        print("="*60)

    finally:
        # Cleanup
        print(f"\n🧹 Cleaning up...")
        with repo.driver.session() as session:
            session.run(
                "MATCH (a:Application {app_id: $app_id}) DETACH DELETE a",
                {"app_id": str(app_ir_1.app_id)}
            )
        repo.close()
        print("   ✅ Cleanup complete")


if __name__ == "__main__":
    test_phase4_simple_round_trip()
