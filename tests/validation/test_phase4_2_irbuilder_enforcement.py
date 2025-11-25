"""
Integration tests for Phase 4.2: IRBuilder Enforcement Optimization

Validates that enforcement rules are correctly optimized for placement
in schema, entity, service, and endpoint layers.
"""
from pathlib import Path
from src.cognitive.ir.ir_builder import IRBuilder
from src.cognitive.ir.validation_model import EnforcementType, ValidationType
from src.parsing.spec_parser import SpecParser


def test_enforcement_placement_validators():
    """
    Test that VALIDATOR enforcement is placed in schema + entity.
    For UNIQUENESS, should also include service.
    """
    print(f"\n{'='*70}")
    print(f"TEST: Validator Enforcement Placement")
    print(f"{'='*70}\n")

    # Load and parse spec
    spec_path = Path("tests/e2e/test_specs/ecommerce-api-spec-human.md")
    if not spec_path.exists():
        print(f"⚠️  Test skipped: {spec_path} not found")
        return

    parser = SpecParser()
    spec = parser.parse(spec_path)

    # Build ApplicationIR
    ir = IRBuilder.build_from_spec(spec)
    assert ir is not None, "Failed to build ApplicationIR"

    # Find VALIDATOR rules
    validator_rules = [
        r for r in ir.validation_model.rules
        if r.enforcement_type == EnforcementType.VALIDATOR
    ]

    print(f"📊 FOUND VALIDATORS: {len(validator_rules)} rules\n")
    assert len(validator_rules) > 0, "No VALIDATOR rules found"

    # Check placement for each validator
    validators_checked = 0
    for rule in validator_rules[:5]:  # Check first 5
        assert rule.enforcement is not None, f"No enforcement for {rule.entity}.{rule.attribute}"
        assert rule.enforcement.applied_at is not None, f"No applied_at for {rule.entity}.{rule.attribute}"

        # All validators should have schema + entity
        assert "schema" in rule.enforcement.applied_at, \
            f"{rule.entity}.{rule.attribute}: missing 'schema' in applied_at"
        assert "entity" in rule.enforcement.applied_at, \
            f"{rule.entity}.{rule.attribute}: missing 'entity' in applied_at"

        # Uniqueness should also include service
        if rule.type == ValidationType.UNIQUENESS:
            assert "service" in rule.enforcement.applied_at, \
                f"{rule.entity}.{rule.attribute}: UNIQUENESS missing 'service' in applied_at"
            print(f"  ✅ {rule.entity}.{rule.attribute} (UNIQUENESS): schema + entity + service")
        else:
            print(f"  ✅ {rule.entity}.{rule.attribute} ({rule.type.value}): schema + entity")

        validators_checked += 1

    print(f"\n✅ All {validators_checked} validator placement checks PASSED\n")


def test_enforcement_placement_immutable():
    """
    Test that IMMUTABLE enforcement is placed in schema + entity only.
    """
    print(f"\n{'='*70}")
    print(f"TEST: Immutable Enforcement Placement")
    print(f"{'='*70}\n")

    spec_path = Path("tests/e2e/test_specs/ecommerce-api-spec-human.md")
    if not spec_path.exists():
        print(f"⚠️  Test skipped: {spec_path} not found")
        return

    parser = SpecParser()
    spec = parser.parse(spec_path)

    ir = IRBuilder.build_from_spec(spec)
    assert ir is not None

    # Find IMMUTABLE rules
    immutable_rules = [
        r for r in ir.validation_model.rules
        if r.enforcement_type == EnforcementType.IMMUTABLE
    ]

    print(f"📊 FOUND IMMUTABLE: {len(immutable_rules)} rules\n")

    if len(immutable_rules) > 0:
        for rule in immutable_rules:
            assert rule.enforcement is not None
            assert rule.enforcement.applied_at is not None

            # Immutable should have schema + entity
            assert "schema" in rule.enforcement.applied_at, \
                f"{rule.entity}.{rule.attribute}: missing 'schema'"
            assert "entity" in rule.enforcement.applied_at, \
                f"{rule.entity}.{rule.attribute}: missing 'entity'"

            # Should NOT have service or endpoint
            assert "service" not in rule.enforcement.applied_at, \
                f"{rule.entity}.{rule.attribute}: should not have 'service'"
            assert "endpoint" not in rule.enforcement.applied_at, \
                f"{rule.entity}.{rule.attribute}: should not have 'endpoint'"

            print(f"  ✅ {rule.entity}.{rule.attribute}: schema + entity (no service/endpoint)")

        print(f"\n✅ All {len(immutable_rules)} immutable placement checks PASSED\n")
    else:
        print(f"⚠️  No IMMUTABLE rules found (may not be in this spec)\n")


def test_enforcement_placement_computed_field():
    """
    Test that COMPUTED_FIELD enforcement is placed in entity only.
    """
    print(f"\n{'='*70}")
    print(f"TEST: Computed Field Enforcement Placement")
    print(f"{'='*70}\n")

    spec_path = Path("tests/e2e/test_specs/ecommerce-api-spec-human.md")
    if not spec_path.exists():
        print(f"⚠️  Test skipped: {spec_path} not found")
        return

    parser = SpecParser()
    spec = parser.parse(spec_path)

    ir = IRBuilder.build_from_spec(spec)
    assert ir is not None

    # Find COMPUTED_FIELD rules
    computed_rules = [
        r for r in ir.validation_model.rules
        if r.enforcement_type == EnforcementType.COMPUTED_FIELD
    ]

    print(f"📊 FOUND COMPUTED_FIELD: {len(computed_rules)} rules\n")

    if len(computed_rules) > 0:
        for rule in computed_rules:
            assert rule.enforcement is not None
            assert rule.enforcement.applied_at is not None

            # Computed fields should have entity only
            assert "entity" in rule.enforcement.applied_at, \
                f"{rule.entity}.{rule.attribute}: missing 'entity'"

            # Should NOT have schema, service, or endpoint
            assert "schema" not in rule.enforcement.applied_at, \
                f"{rule.entity}.{rule.attribute}: should not have 'schema'"
            assert "service" not in rule.enforcement.applied_at, \
                f"{rule.entity}.{rule.attribute}: should not have 'service'"
            assert "endpoint" not in rule.enforcement.applied_at, \
                f"{rule.entity}.{rule.attribute}: should not have 'endpoint'"

            print(f"  ✅ {rule.entity}.{rule.attribute}: entity only (no schema/service/endpoint)")

        print(f"\n✅ All {len(computed_rules)} computed field placement checks PASSED\n")
    else:
        print(f"⚠️  No COMPUTED_FIELD rules found (may not be in this spec)\n")


def test_enforcement_placement_state_machine():
    """
    Test that STATE_MACHINE enforcement is placed in service + endpoint.
    """
    print(f"\n{'='*70}")
    print(f"TEST: State Machine Enforcement Placement")
    print(f"{'='*70}\n")

    spec_path = Path("tests/e2e/test_specs/ecommerce-api-spec-human.md")
    if not spec_path.exists():
        print(f"⚠️  Test skipped: {spec_path} not found")
        return

    parser = SpecParser()
    spec = parser.parse(spec_path)

    ir = IRBuilder.build_from_spec(spec)
    assert ir is not None

    # Find STATE_MACHINE rules
    state_machine_rules = [
        r for r in ir.validation_model.rules
        if r.enforcement_type == EnforcementType.STATE_MACHINE
    ]

    print(f"📊 FOUND STATE_MACHINE: {len(state_machine_rules)} rules\n")

    if len(state_machine_rules) > 0:
        for rule in state_machine_rules:
            assert rule.enforcement is not None
            assert rule.enforcement.applied_at is not None

            # State machines should have service + endpoint
            assert "service" in rule.enforcement.applied_at, \
                f"{rule.entity}.{rule.attribute}: missing 'service'"
            assert "endpoint" in rule.enforcement.applied_at, \
                f"{rule.entity}.{rule.attribute}: missing 'endpoint'"

            # Should NOT have schema
            assert "schema" not in rule.enforcement.applied_at, \
                f"{rule.entity}.{rule.attribute}: should not have 'schema'"

            print(f"  ✅ {rule.entity}.{rule.attribute}: service + endpoint (no schema)")

        print(f"\n✅ All {len(state_machine_rules)} state machine placement checks PASSED\n")
    else:
        print(f"⚠️  No STATE_MACHINE rules found (may not be in this spec)\n")


def test_enforcement_placement_optimization_consistency():
    """
    Test that all rules with enforcement have valid applied_at placement.
    """
    print(f"\n{'='*70}")
    print(f"TEST: Enforcement Placement Optimization Consistency")
    print(f"{'='*70}\n")

    spec_path = Path("tests/e2e/test_specs/ecommerce-api-spec-human.md")
    if not spec_path.exists():
        print(f"⚠️  Test skipped: {spec_path} not found")
        return

    parser = SpecParser()
    spec = parser.parse(spec_path)

    ir = IRBuilder.build_from_spec(spec)
    assert ir is not None

    # Check all rules
    rules_with_enforcement = [
        r for r in ir.validation_model.rules
        if r.enforcement is not None and r.enforcement_type != EnforcementType.DESCRIPTION
    ]

    print(f"📊 TOTAL RULES WITH ENFORCEMENT: {len(rules_with_enforcement)}\n")

    valid_locations = {"schema", "entity", "service", "endpoint"}
    placement_summary = {}

    for rule in rules_with_enforcement:
        enforcement_type = rule.enforcement_type.value
        applied_at = tuple(sorted(rule.enforcement.applied_at)) if rule.enforcement.applied_at else ()

        # Track placement patterns
        if enforcement_type not in placement_summary:
            placement_summary[enforcement_type] = {}
        if applied_at not in placement_summary[enforcement_type]:
            placement_summary[enforcement_type][applied_at] = 0
        placement_summary[enforcement_type][applied_at] += 1

        # Validate each location is valid
        for location in rule.enforcement.applied_at:
            assert location in valid_locations, \
                f"Invalid location '{location}' for {rule.entity}.{rule.attribute}"

        # Validate applied_at is not empty
        assert len(rule.enforcement.applied_at) > 0, \
            f"Empty applied_at for {rule.entity}.{rule.attribute}"

    # Print summary
    print("📋 ENFORCEMENT PLACEMENT PATTERNS:\n")
    for enforcement_type, patterns in sorted(placement_summary.items()):
        print(f"  [{enforcement_type.upper()}]:")
        for locations, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True):
            loc_str = " + ".join(locations) if locations else "none"
            print(f"    - {loc_str}: {count} rules")
        print()

    print(f"✅ All {len(rules_with_enforcement)} rules have valid enforcement placement\n")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("PHASE 4.2 ENFORCEMENT PLACEMENT INTEGRATION TESTS")
    print("="*70)

    try:
        test_enforcement_placement_validators()
        print("✅ Test 1 PASSED: Validator placement")
    except AssertionError as e:
        print(f"❌ Test 1 FAILED: {e}")

    try:
        test_enforcement_placement_immutable()
        print("✅ Test 2 PASSED: Immutable placement")
    except AssertionError as e:
        print(f"❌ Test 2 FAILED: {e}")

    try:
        test_enforcement_placement_computed_field()
        print("✅ Test 3 PASSED: Computed field placement")
    except AssertionError as e:
        print(f"❌ Test 3 FAILED: {e}")

    try:
        test_enforcement_placement_state_machine()
        print("✅ Test 4 PASSED: State machine placement")
    except AssertionError as e:
        print(f"❌ Test 4 FAILED: {e}")

    try:
        test_enforcement_placement_optimization_consistency()
        print("✅ Test 5 PASSED: Placement consistency")
    except AssertionError as e:
        print(f"❌ Test 5 FAILED: {e}")

    print("\n" + "="*70)
    print("Phase 4.2 Enforcement Placement Testing Complete")
    print("="*70 + "\n")
