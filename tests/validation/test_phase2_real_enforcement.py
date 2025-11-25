"""
Phase 2: Real Enforcement vs Description Integration Tests
===========================================================

Tests verifying that 6 validation rules have real enforcement (not just descriptions):
1. unit_price: @computed_field (snapshot of price at add-time)
2. registration_date: immutable Field(exclude=True)
3. creation_date: immutable Field(exclude=True)
4. total_amount: @computed_field with calculation
5. stock: Service-layer business logic (decrement)
6. status: State machine validation with FSM

All tests verify that enforcement is actually implemented, not just described.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from uuid import UUID, uuid4
from pydantic import ValidationError

from src.cognitive.ir.validation_model import (
    ValidationRule, ValidationModelIR, ValidationType, EnforcementType, EnforcementStrategy
)
from src.services.business_logic_extractor import BusinessLogicExtractor


class TestPhase2RealEnforcement:
    """Integration tests for Phase 2 real enforcement implementation."""

    @pytest.fixture
    def extractor(self):
        """Fixture providing BusinessLogicExtractor instance."""
        return BusinessLogicExtractor()

    @pytest.fixture
    def sample_spec(self):
        """Fixture providing a sample ecommerce spec."""
        return {
            "name": "ECommerceAPI",
            "entities": [
                {
                    "name": "CartItem",
                    "plural": "cart_items",
                    "fields": [
                        {
                            "name": "unit_price",
                            "type": "Decimal",
                            "required": True,
                            "description": "snapshot del precio EN ESE MOMENTO cuando se agrega al carrito"
                        },
                    ]
                },
                {
                    "name": "Customer",
                    "plural": "customers",
                    "fields": [
                        {
                            "name": "registration_date",
                            "type": "datetime",
                            "required": True,
                            "description": "automática, solo lectura"
                        },
                    ]
                },
                {
                    "name": "Order",
                    "plural": "orders",
                    "fields": [
                        {
                            "name": "creation_date",
                            "type": "datetime",
                            "required": True,
                            "description": "automática, solo lectura"
                        },
                        {
                            "name": "total_amount",
                            "type": "Decimal",
                            "required": True,
                            "description": "suma automática items × cantidad"
                        },
                        {
                            "name": "stock",
                            "type": "int",
                            "required": True,
                            "description": "decrementar al checkout"
                        },
                        {
                            "name": "status",
                            "type": "str",
                            "required": True,
                            "enum": ["pending", "confirmed", "shipped", "delivered", "cancelled"],
                            "description": "workflow validations"
                        },
                    ]
                },
            ]
        }

    # Test 1: unit_price → COMPUTED_FIELD
    def test_unit_price_computed_field(self, extractor, sample_spec):
        """
        Test 1: Verify unit_price has real @computed_field enforcement, not just description.

        Requirement: unit_price is a "snapshot del precio EN ESE MOMENTO"
        → Must be COMPUTED_FIELD with real @computed_field decorator generation
        """
        # Extract validations
        validation_ir = extractor.extract_validation_rules(sample_spec)
        rules = validation_ir.rules

        # Find unit_price rule
        unit_price_rule = None
        for rule in rules:
            if rule.entity == "CartItem" and rule.attribute == "unit_price":
                unit_price_rule = rule
                break

        # Assertion 1: Rule exists
        assert unit_price_rule is not None, "No validation rule found for CartItem.unit_price"

        # Assertion 2: Has COMPUTED_FIELD enforcement (not DESCRIPTION)
        assert unit_price_rule.enforcement_type == EnforcementType.COMPUTED_FIELD, \
            f"unit_price should be COMPUTED_FIELD, got {unit_price_rule.enforcement_type}"

        # Assertion 3: Enforcement strategy exists and has code snippet
        assert unit_price_rule.enforcement is not None, "unit_price has no enforcement strategy"
        assert unit_price_rule.enforcement.code_snippet is not None, \
            "unit_price enforcement has no code snippet"

        # Assertion 4: Code snippet contains @computed_field decorator
        assert "@computed_field" in unit_price_rule.enforcement.code_snippet, \
            "unit_price code snippet missing @computed_field decorator"

        # Assertion 5: Applied at schema level
        assert "entity" in unit_price_rule.enforcement.applied_at, \
            "unit_price enforcement should be applied at entity level"

        print("✅ Test 1 PASSED: unit_price has real @computed_field enforcement")

    # Test 2: registration_date → IMMUTABLE
    def test_registration_date_immutable(self, extractor, sample_spec):
        """
        Test 2: Verify registration_date has real immutable enforcement.

        Requirement: registration_date is "automática, solo lectura"
        → Must be IMMUTABLE with exclude=True
        """
        # Extract validations
        validation_ir = extractor.extract_validation_rules(sample_spec)
        rules = validation_ir.rules

        # Find registration_date rule
        reg_date_rule = None
        for rule in rules:
            if rule.entity == "Customer" and rule.attribute == "registration_date":
                reg_date_rule = rule
                break

        # Assertion 1: Rule exists
        assert reg_date_rule is not None, "No validation rule found for Customer.registration_date"

        # Assertion 2: Has IMMUTABLE enforcement (not DESCRIPTION)
        assert reg_date_rule.enforcement_type == EnforcementType.IMMUTABLE, \
            f"registration_date should be IMMUTABLE, got {reg_date_rule.enforcement_type}"

        # Assertion 3: Enforcement strategy exists
        assert reg_date_rule.enforcement is not None, "registration_date has no enforcement strategy"

        # Assertion 4: Implementation mentions exclude=True
        assert "exclude" in reg_date_rule.enforcement.implementation.lower(), \
            "registration_date enforcement should use exclude=True"

        # Assertion 5: Parameters have allow_mutation=False
        assert reg_date_rule.enforcement.parameters.get("allow_mutation") == False, \
            "registration_date should have allow_mutation=False"

        print("✅ Test 2 PASSED: registration_date has real immutable enforcement")

    # Test 3: creation_date → IMMUTABLE
    def test_creation_date_immutable(self, extractor, sample_spec):
        """
        Test 3: Verify creation_date has real immutable enforcement.

        Requirement: creation_date is "automática, solo lectura"
        → Must be IMMUTABLE with exclude=True
        """
        # Extract validations
        validation_ir = extractor.extract_validation_rules(sample_spec)
        rules = validation_ir.rules

        # Find creation_date rule
        create_date_rule = None
        for rule in rules:
            if rule.entity == "Order" and rule.attribute == "creation_date":
                create_date_rule = rule
                break

        # Assertion 1: Rule exists
        assert create_date_rule is not None, "No validation rule found for Order.creation_date"

        # Assertion 2: Has IMMUTABLE enforcement (not DESCRIPTION)
        assert create_date_rule.enforcement_type == EnforcementType.IMMUTABLE, \
            f"creation_date should be IMMUTABLE, got {create_date_rule.enforcement_type}"

        # Assertion 3: Enforcement strategy exists
        assert create_date_rule.enforcement is not None, "creation_date has no enforcement strategy"

        # Assertion 4: Implementation mentions exclude=True
        assert "exclude" in create_date_rule.enforcement.implementation.lower(), \
            "creation_date enforcement should use exclude=True"

        # Assertion 5: Applied at schema and entity level
        assert "schema" in create_date_rule.enforcement.applied_at or "entity" in create_date_rule.enforcement.applied_at, \
            "creation_date enforcement should be applied at schema/entity level"

        print("✅ Test 3 PASSED: creation_date has real immutable enforcement")

    # Test 4: total_amount → COMPUTED_FIELD
    def test_total_amount_computed_field(self, extractor, sample_spec):
        """
        Test 4: Verify total_amount has real @computed_field enforcement with calculation logic.

        Requirement: total_amount is "suma automática items × cantidad"
        → Must be COMPUTED_FIELD with actual calculation in code snippet
        """
        # Extract validations
        validation_ir = extractor.extract_validation_rules(sample_spec)
        rules = validation_ir.rules

        # Find total_amount rule
        total_rule = None
        for rule in rules:
            if rule.entity == "Order" and rule.attribute == "total_amount":
                total_rule = rule
                break

        # Assertion 1: Rule exists
        assert total_rule is not None, "No validation rule found for Order.total_amount"

        # Assertion 2: Has COMPUTED_FIELD enforcement (not DESCRIPTION)
        assert total_rule.enforcement_type == EnforcementType.COMPUTED_FIELD, \
            f"total_amount should be COMPUTED_FIELD, got {total_rule.enforcement_type}"

        # Assertion 3: Enforcement strategy exists
        assert total_rule.enforcement is not None, "total_amount has no enforcement strategy"

        # Assertion 4: Code snippet contains @computed_field
        assert "@computed_field" in total_rule.enforcement.code_snippet, \
            "total_amount code snippet missing @computed_field"

        # Assertion 5: Code snippet contains calculation logic (sum/total)
        assert "sum" in total_rule.enforcement.code_snippet.lower() or \
               "total" in total_rule.enforcement.code_snippet.lower(), \
            "total_amount code snippet should contain calculation logic"

        # Assertion 6: Parameters contain calculation info
        assert "calculation" in total_rule.enforcement.parameters or \
               total_rule.enforcement.code_snippet is not None, \
            "total_amount should have calculation parameters or code snippet"

        print("✅ Test 4 PASSED: total_amount has real @computed_field enforcement with calculation")

    # Test 5: stock → BUSINESS_LOGIC
    def test_stock_business_logic(self, extractor, sample_spec):
        """
        Test 5: Verify stock has real BUSINESS_LOGIC enforcement (service layer).

        Requirement: stock "decrementar al checkout"
        → Must be BUSINESS_LOGIC with decrement operation in service
        """
        # Extract validations
        validation_ir = extractor.extract_validation_rules(sample_spec)
        rules = validation_ir.rules

        # Find stock rule
        stock_rule = None
        for rule in rules:
            if rule.entity == "Order" and rule.attribute == "stock":
                stock_rule = rule
                break

        # Assertion 1: Rule exists
        assert stock_rule is not None, "No validation rule found for Order.stock"

        # Assertion 2: Has BUSINESS_LOGIC enforcement (not DESCRIPTION)
        assert stock_rule.enforcement_type == EnforcementType.BUSINESS_LOGIC, \
            f"stock should be BUSINESS_LOGIC, got {stock_rule.enforcement_type}"

        # Assertion 3: Enforcement strategy exists
        assert stock_rule.enforcement is not None, "stock has no enforcement strategy"

        # Assertion 4: Applied at service layer
        assert "service" in stock_rule.enforcement.applied_at, \
            "stock enforcement should be applied at service layer"

        # Assertion 5: Parameters contain operation info
        assert stock_rule.enforcement.parameters.get("operation") == "decrement", \
            "stock enforcement should have operation=decrement"

        # Assertion 6: Code snippet contains decrement logic
        assert "decrement" in stock_rule.enforcement.code_snippet.lower(), \
            "stock code snippet should mention decrement"

        print("✅ Test 5 PASSED: stock has real BUSINESS_LOGIC enforcement (decrement)")

    # Test 6: status → STATE_MACHINE
    def test_status_state_machine(self, extractor, sample_spec):
        """
        Test 6: Verify status has real STATE_MACHINE enforcement.

        Requirement: status with "workflow validations"
        → Must be STATE_MACHINE with valid state transitions
        """
        # Extract validations
        validation_ir = extractor.extract_validation_rules(sample_spec)
        rules = validation_ir.rules

        # Find status rule
        status_rule = None
        for rule in rules:
            if rule.entity == "Order" and rule.attribute == "status":
                status_rule = rule
                break

        # Assertion 1: Rule exists
        assert status_rule is not None, "No validation rule found for Order.status"

        # Assertion 2: Has STATE_MACHINE enforcement (not DESCRIPTION)
        assert status_rule.enforcement_type == EnforcementType.STATE_MACHINE, \
            f"status should be STATE_MACHINE, got {status_rule.enforcement_type}"

        # Assertion 3: Enforcement strategy exists
        assert status_rule.enforcement is not None, "status has no enforcement strategy"

        # Assertion 4: Code snippet contains state machine logic
        assert "valid_transitions" in status_rule.enforcement.code_snippet or \
               "state" in status_rule.enforcement.code_snippet.lower(), \
            "status code snippet should contain state machine logic"

        # Assertion 5: Applied at service and endpoint level
        assert "service" in status_rule.enforcement.applied_at or "endpoint" in status_rule.enforcement.applied_at, \
            "status enforcement should be applied at service/endpoint level"

        # Assertion 6: Template name indicates state machine
        assert "state" in status_rule.enforcement.template_name.lower() or \
               "fsm" in status_rule.enforcement.template_name.lower(), \
            "status should use state_machine_fsm template"

        print("✅ Test 6 PASSED: status has real STATE_MACHINE enforcement")

    # Summary test: All 6 fields have real enforcement
    def test_all_six_fields_have_real_enforcement(self, extractor, sample_spec):
        """
        Summary test: Verify that all 6 target fields have REAL enforcement (not DESCRIPTION).

        This is the critical compliance check: 0/6 → 6/6 compliance.
        """
        # Extract validations
        validation_ir = extractor.extract_validation_rules(sample_spec)
        rules = validation_ir.rules

        # Map of target fields and their required enforcement types
        target_fields = {
            ("CartItem", "unit_price"): EnforcementType.COMPUTED_FIELD,
            ("Customer", "registration_date"): EnforcementType.IMMUTABLE,
            ("Order", "creation_date"): EnforcementType.IMMUTABLE,
            ("Order", "total_amount"): EnforcementType.COMPUTED_FIELD,
            ("Order", "stock"): EnforcementType.BUSINESS_LOGIC,
            ("Order", "status"): EnforcementType.STATE_MACHINE,
        }

        # Find and verify each field
        enforcement_count = 0
        for (entity, field), expected_type in target_fields.items():
            rule = None
            for r in rules:
                if r.entity == entity and r.attribute == field:
                    rule = r
                    break

            assert rule is not None, f"No rule found for {entity}.{field}"
            assert rule.enforcement_type == expected_type, \
                f"{entity}.{field} should be {expected_type}, got {rule.enforcement_type}"
            assert rule.enforcement is not None, \
                f"{entity}.{field} has no enforcement strategy"
            assert rule.enforcement.type != EnforcementType.DESCRIPTION, \
                f"{entity}.{field} is still DESCRIPTION-only (not real enforcement)"

            enforcement_count += 1

        # Assertion: All 6 fields have real enforcement
        assert enforcement_count == 6, f"Only {enforcement_count}/6 fields have real enforcement"

        print(f"✅ COMPLIANCE CHECK PASSED: 6/6 fields have real enforcement (0/6 → 6/6)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
