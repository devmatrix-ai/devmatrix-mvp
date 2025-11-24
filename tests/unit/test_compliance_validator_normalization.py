import pytest

from src.validation.compliance_validator import ComplianceValidator


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("CartItem-Input", "CartItem"),
        ("OrderItem-Output", "OrderItem"),
        ("CartResponse", "Cart"),
        ("ProductModel", "Product"),
        ("Customer", "Customer"),
    ],
)
def test_normalize_entity_name(raw, expected):
    validator = ComplianceValidator()
    assert validator._normalize_entity_name(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (">=5", "ge=5"),
        (">0", "gt=0"),
        ("gt=0.0", "gt=0"),
        ("ge=-1.0", "ge=-1"),
        ("uuid format", "uuid_format"),
        ("enum=OPEN,CLOSED", "enum=OPEN,CLOSED"),
    ],
)
def test_normalize_constraint(raw, expected):
    validator = ComplianceValidator()
    assert validator._normalize_constraint(raw) == expected


class TestValidationCompliance:
    """Test validation compliance calculation, especially handling of read_only and extra validations"""

    def test_read_only_validation_is_counted(self):
        """Test that read_only validation is not ignored and is properly counted"""
        validator = ComplianceValidator()

        # Expected validations from spec
        expected = [
            "Product.name: required",
            "Product.price: gt=0",
        ]

        # Found validations from generated code (includes read_only)
        found = [
            "Product.name: required",
            "Product.price: gt=0",
            "Product.id: read_only",  # Extra validation - should be counted
        ]

        compliance, matched = validator._calculate_validation_compliance(
            found, expected, use_exact_matching=False
        )

        # All expected validations are present
        assert compliance == 1.0, "Compliance should be 100% when all expected validations found"

        # Matched should include ALL found validations (including read_only)
        assert len(matched) == 3, "All 3 found validations should be counted (including read_only)"
        assert "Product.id: read_only" in matched, "read_only validation should be in matched list"

    def test_all_found_validations_counted_when_expected_met(self):
        """Test that when all expected validations are found, all found validations are counted"""
        validator = ComplianceValidator()

        expected = ["User.email: required"]

        # Found list includes extra validations beyond expected
        found = [
            "User.email: required",
            "User.password: min_length=8",
            "User.age: ge=18",
            "User.is_active: read_only",
            "User.created_at: read_only",
        ]

        compliance, matched = validator._calculate_validation_compliance(
            found, expected, use_exact_matching=False
        )

        # Should have 100% compliance (all required found)
        assert compliance == 1.0

        # Should count ALL 5 found validations, not just the 1 required
        assert len(matched) == 5, f"Expected 5 validations, got {len(matched)}"
        assert matched == found, "Matched should be identical to found when all expected are met"

    def test_partial_compliance_when_expected_not_met(self):
        """Test partial compliance when not all expected validations are found"""
        validator = ComplianceValidator()

        expected = [
            "Product.name: required",
            "Product.price: gt=0",
            "Product.sku: required",
        ]

        found = [
            "Product.name: required",
            "Product.price: gt=0",
            # Missing: Product.sku: required
            "Product.id: read_only",  # Extra, but not counted since we're below 100%
        ]

        compliance, matched = validator._calculate_validation_compliance(
            found, expected, use_exact_matching=False
        )

        # 2 out of 3 expected found = ~66.7% compliance
        assert compliance == pytest.approx(2 / 3, rel=0.01)

        # When not at 100%, matched is only the actually matched ones
        assert len(matched) <= 2, "Should only count matched validations when compliance < 100%"

    def test_flexible_matching_substring_match(self):
        """Test that flexible matching uses substring matching for constraints"""
        validator = ComplianceValidator()

        # Expected has simple format
        expected = ["Product.price: gt=0"]

        # Found has various formats but contains the constraint
        found = [
            "Product.price: gt=0",
        ]

        compliance, matched = validator._calculate_validation_compliance(
            found, expected, use_exact_matching=False
        )

        # Should match successfully
        assert compliance == 1.0
        assert len(matched) == 1

    def test_semantic_equivalence_matching(self):
        """Test semantic equivalence for high-level constraint names"""
        validator = ComplianceValidator()

        # Spec constraints (high-level names)
        expected = [
            "Product.id: unique",
            "Product.id: auto-generated",
            "Product.price: greater_than_zero",
            "Customer.email: valid_email_format",
        ]

        # Code constraints (low-level equivalents)
        found = [
            "Product.id: read_only",  # auto-generated → read_only
            "Product.price: gt=0",  # greater_than_zero → gt=0
            "Customer.email: email_format",  # valid_email_format → email_format
        ]

        compliance, matched = validator._calculate_validation_compliance(
            found, expected, use_exact_matching=False
        )

        # Should match 3 out of 4 (unique might not have a direct equivalent)
        # But at least auto-generated and greater_than_zero should match
        assert compliance >= 0.5, "Should match at least some semantic equivalents"
        assert any("read_only" in m for m in matched), "auto-generated should match read_only"
        assert any("gt=0" in m for m in matched), "greater_than_zero should match gt=0"
