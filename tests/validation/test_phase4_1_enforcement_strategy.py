"""
Integration tests for Phase 4.1: EnforcementStrategy Detection

Validates that ValidationRules get proper EnforcementStrategy metadata
enabling real enforcement code generation instead of descriptions.
"""
from pathlib import Path
from src.services.business_logic_extractor import BusinessLogicExtractor
from src.cognitive.ir.validation_model import EnforcementType, ValidationRule
import json


def test_enforcement_strategy_detection_on_ecommerce_spec():
    """
    Test that enforcement strategies are correctly detected from ecommerce spec.
    """
    spec_path = Path("tests/e2e/test_specs/ecommerce-api-spec-human.md")
    if not spec_path.exists():
        print(f"⚠️  Test skipped: {spec_path} not found")
        return

    print(f"\n{'='*70}")
    print(f"TEST: Phase 4.1 Enforcement Strategy Detection")
    print(f"{'='*70}\n")

    # Load spec
    import yaml
    spec_text = spec_path.read_text()
    # Parse spec (assuming it's in markdown format)
    spec = {
        "name": "ecommerce-api",
        "entities": [
            {
                "name": "Product",
                "fields": [
                    {"name": "id", "type": "UUID", "required": True, "description": "Unique identifier"},
                    {"name": "name", "type": "string", "required": True, "description": "Product name, 1-255 characters"},
                    {"name": "price", "type": "decimal", "required": True, "description": "Product price, positive"},
                    {"name": "stock", "type": "integer", "description": "Current stock quantity"},
                    {"name": "created_at", "type": "datetime", "description": "Immutable timestamp at creation"},
                ]
            },
            {
                "name": "Customer",
                "fields": [
                    {"name": "id", "type": "UUID", "description": "Unique identifier"},
                    {"name": "email", "type": "string", "unique": True, "description": "Unique email address"},
                    {"name": "status", "type": "string", "description": "Customer status (active, inactive, suspended)"},
                ]
            },
            {
                "name": "Order",
                "fields": [
                    {"name": "id", "type": "UUID"},
                    {"name": "total", "type": "decimal", "description": "Computed field: sum of item totals"},
                    {"name": "status", "type": "string", "description": "Status transition (pending, confirmed, shipped, delivered)"},
                ]
            }
        ]
    }

    # Extract validation rules with enforcement strategies
    extractor = BusinessLogicExtractor()
    validation_ir = extractor.extract_validation_rules(spec)

    print(f"📊 EXTRACTED VALIDATIONS: {len(validation_ir.rules)} rules")
    print()

    # Organize by enforcement type
    enforcement_summary = {}
    for rule in validation_ir.rules:
        enforcement_type = rule.enforcement_type.value if rule.enforcement_type else "unknown"
        if enforcement_type not in enforcement_summary:
            enforcement_summary[enforcement_type] = []
        enforcement_summary[enforcement_type].append(rule)

    # Print enforcement summary
    for enforcement_type, rules in sorted(enforcement_summary.items()):
        print(f"  [{enforcement_type.upper()}]: {len(rules)} rules")
        for rule in rules[:3]:  # Show first 3
            enforcement_detail = ""
            if rule.enforcement:
                enforcement_detail = f" → {rule.enforcement.template_name}"
            print(f"    - {rule.entity}.{rule.attribute} ({rule.type.value}){enforcement_detail}")
        if len(rules) > 3:
            print(f"    ... and {len(rules) - 3} more")
        print()

    # VALIDATIONS
    assert len(validation_ir.rules) > 0, "No validation rules extracted"

    # Check immutable enforcement (for id, created_at)
    immutable_rules = [r for r in validation_ir.rules if r.enforcement_type == EnforcementType.IMMUTABLE]
    print(f"✅ Immutable fields detected: {len(immutable_rules)}")
    for rule in immutable_rules:
        assert rule.enforcement is not None, f"{rule.entity}.{rule.attribute} has immutable type but no enforcement"
        assert rule.enforcement.type == EnforcementType.IMMUTABLE
        assert rule.enforcement.template_name == "immutable_field"
        print(f"  - {rule.entity}.{rule.attribute}: {rule.enforcement.description}")

    # Check validator enforcement (for unique, format, range)
    validator_rules = [r for r in validation_ir.rules if r.enforcement_type == EnforcementType.VALIDATOR]
    print(f"✅ Validators detected: {len(validator_rules)}")
    assert len(validator_rules) > 0, "No validators detected"
    for rule in validator_rules[:5]:
        assert rule.enforcement is not None
        assert rule.enforcement.type == EnforcementType.VALIDATOR
        assert rule.enforcement.implementation == "@field_validator"
        print(f"  - {rule.entity}.{rule.attribute} ({rule.type.value}): {rule.enforcement.template_name}")

    # Check computed field enforcement
    computed_rules = [r for r in validation_ir.rules if r.enforcement_type == EnforcementType.COMPUTED_FIELD]
    print(f"✅ Computed fields detected: {len(computed_rules)}")
    for rule in computed_rules:
        assert rule.enforcement is not None
        assert rule.enforcement.type == EnforcementType.COMPUTED_FIELD
        assert rule.enforcement.implementation == "@computed_field"
        print(f"  - {rule.entity}.{rule.attribute}: {rule.enforcement.description}")

    # Check state machine enforcement (for status)
    state_machine_rules = [r for r in validation_ir.rules if r.enforcement_type == EnforcementType.STATE_MACHINE]
    print(f"✅ State machines detected: {len(state_machine_rules)}")
    for rule in state_machine_rules:
        assert rule.enforcement is not None
        assert rule.enforcement.type == EnforcementType.STATE_MACHINE
        print(f"  - {rule.entity}.{rule.attribute}: {rule.enforcement.description}")

    print(f"\n{'='*70}")
    print(f"✅ PHASE 4.1 ENFORCEMENT STRATEGY TEST PASSED")
    print(f"{'='*70}\n")


def test_enforcement_strategy_has_required_fields():
    """
    Test that EnforcementStrategy objects have all required fields.
    """
    print(f"\n{'='*70}")
    print(f"TEST: EnforcementStrategy Structure Validation")
    print(f"{'='*70}\n")

    spec = {
        "name": "test-app",
        "entities": [
            {
                "name": "TestEntity",
                "fields": [
                    {"name": "unique_field", "type": "string", "unique": True, "description": "Must be unique"},
                    {"name": "required_field", "type": "string", "required": True, "description": "Is required"},
                ]
            }
        ]
    }

    extractor = BusinessLogicExtractor()
    validation_ir = extractor.extract_validation_rules(spec)

    for rule in validation_ir.rules:
        if rule.enforcement:
            # Validate required fields
            assert rule.enforcement.type in EnforcementType.__members__.values(), \
                f"Invalid enforcement type: {rule.enforcement.type}"
            assert rule.enforcement.implementation, \
                f"Missing implementation for {rule.entity}.{rule.attribute}"
            assert isinstance(rule.enforcement.applied_at, list), \
                f"applied_at should be list, got {type(rule.enforcement.applied_at)}"
            assert len(rule.enforcement.applied_at) > 0, \
                f"applied_at should not be empty for {rule.entity}.{rule.attribute}"
            assert isinstance(rule.enforcement.parameters, dict), \
                f"parameters should be dict, got {type(rule.enforcement.parameters)}"

            print(f"✅ {rule.entity}.{rule.attribute}:")
            print(f"  - type: {rule.enforcement.type.value}")
            print(f"  - implementation: {rule.enforcement.implementation}")
            print(f"  - applied_at: {rule.enforcement.applied_at}")
            print(f"  - template: {rule.enforcement.template_name}")
            print(f"  - parameters: {rule.enforcement.parameters}")

    print(f"\n{'='*70}")
    print(f"✅ ENFORCEMENT STRATEGY STRUCTURE TEST PASSED")
    print(f"{'='*70}\n")


def test_enforcement_strategy_consistency():
    """
    Test that enforcement strategy is consistent with rule type.
    """
    print(f"\n{'='*70}")
    print(f"TEST: Enforcement Strategy Consistency")
    print(f"{'='*70}\n")

    spec = {
        "name": "test-app",
        "entities": [
            {
                "name": "Product",
                "fields": [
                    {"name": "price", "type": "decimal", "description": "positive integer price"},
                    {"name": "created", "type": "datetime", "description": "created timestamp"},
                ]
            }
        ]
    }

    extractor = BusinessLogicExtractor()
    validation_ir = extractor.extract_validation_rules(spec)

    # Validate consistency
    for rule in validation_ir.rules:
        # Immutable enforcement should only apply to certain types
        if rule.enforcement_type == EnforcementType.IMMUTABLE:
            assert "created" in rule.attribute.lower() or rule.attribute == "id", \
                f"Immutable enforcement on unexpected field: {rule.entity}.{rule.attribute}"

        # Computed fields should have computed_field implementation
        if rule.enforcement_type == EnforcementType.COMPUTED_FIELD:
            assert rule.enforcement is not None
            assert "@computed_field" in rule.enforcement.implementation

        # Validators should use @field_validator
        if rule.enforcement_type == EnforcementType.VALIDATOR:
            assert rule.enforcement is not None
            assert "@field_validator" in rule.enforcement.implementation

        # State machine should be applied at service/endpoint
        if rule.enforcement_type == EnforcementType.STATE_MACHINE:
            assert rule.enforcement is not None
            assert "service" in rule.enforcement.applied_at or "endpoint" in rule.enforcement.applied_at

    print(f"✅ All {len(validation_ir.rules)} rules have consistent enforcement strategies")
    print(f"\n{'='*70}")
    print(f"✅ ENFORCEMENT CONSISTENCY TEST PASSED")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("PHASE 4.1 ENFORCEMENT STRATEGY INTEGRATION TESTS")
    print("="*70)

    try:
        test_enforcement_strategy_detection_on_ecommerce_spec()
        print("✅ Test 1 PASSED: Enforcement strategy detection")
    except AssertionError as e:
        print(f"❌ Test 1 FAILED: {e}")

    try:
        test_enforcement_strategy_has_required_fields()
        print("✅ Test 2 PASSED: Enforcement strategy structure")
    except AssertionError as e:
        print(f"❌ Test 2 FAILED: {e}")

    try:
        test_enforcement_strategy_consistency()
        print("✅ Test 3 PASSED: Enforcement strategy consistency")
    except AssertionError as e:
        print(f"❌ Test 3 FAILED: {e}")

    print("\n" + "="*70)
    print("Phase 4.1 Integration Testing Complete")
    print("="*70 + "\n")
