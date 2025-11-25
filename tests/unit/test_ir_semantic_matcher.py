"""
Unit tests for Phase 3: IRSemanticMatcher.

Tests IR-native constraint matching, hierarchical matching strategy,
and confidence scoring.
"""

import pytest
from src.services.ir_semantic_matcher import IRSemanticMatcher, IRMatchResult
from src.cognitive.ir.constraint_ir import ConstraintIR
from src.cognitive.ir.validation_model import ValidationType, EnforcementType, ValidationRule, ValidationModelIR


@pytest.fixture
def matcher():
    """Create IRSemanticMatcher instance."""
    return IRSemanticMatcher(use_embedding_fallback=False)


@pytest.fixture
def sample_constraints():
    """Create sample ConstraintIR objects for testing."""
    return {
        "price_range": ConstraintIR(
            entity="Product",
            field="price",
            validation_type=ValidationType.RANGE,
            constraint_type="range",
            value=0,
        ),
        "product_id_uuid": ConstraintIR(
            entity="Product",
            field="id",
            validation_type=ValidationType.FORMAT,
            constraint_type="uuid",
            value=None,
        ),
        "order_status_enum": ConstraintIR(
            entity="Order",
            field="status",
            validation_type=ValidationType.STATUS_TRANSITION,
            constraint_type="enum",
            value=["pending", "processing", "completed"],
        ),
    }


class TestIRSemanticMatcherInitialization:
    """Tests for IRSemanticMatcher initialization."""

    def test_init_without_embedding(self):
        """Test initialization without embedding fallback."""
        matcher = IRSemanticMatcher(use_embedding_fallback=False)
        assert matcher.use_embedding_fallback is False
        assert matcher._embedding_matcher is None

    def test_init_with_embedding(self):
        """Test initialization with embedding fallback."""
        matcher = IRSemanticMatcher(use_embedding_fallback=True)
        assert matcher.use_embedding_fallback is True

    def test_confidence_thresholds(self):
        """Test that confidence thresholds are set correctly."""
        matcher = IRSemanticMatcher()
        assert matcher.EXACT_MATCH_CONFIDENCE == 1.0
        assert matcher.CATEGORY_MATCH_CONFIDENCE == 0.9
        assert matcher.FIELD_MATCH_CONFIDENCE == 0.7


class TestExactMatching:
    """Tests for exact IR matching (Level 1)."""

    def test_exact_match_same_entity_field_type_value(self, matcher, sample_constraints):
        """Test exact match when all components match."""
        constraint1 = ConstraintIR(
            entity="Product",
            field="price",
            validation_type=ValidationType.RANGE,
            constraint_type="range",
            value=0,
        )
        constraint2 = ConstraintIR(
            entity="Product",
            field="price",
            validation_type=ValidationType.RANGE,
            constraint_type="range",
            value=0,
        )

        result = matcher.match_ir(constraint1, constraint2)

        assert result.match is True
        assert result.confidence == 1.0
        assert result.method == "exact_ir"
        assert result.category_match is True
        assert result.value_match is True

    def test_no_match_different_entity(self, matcher):
        """Test no match when entities differ."""
        constraint1 = ConstraintIR(
            entity="Product",
            field="price",
            validation_type=ValidationType.RANGE,
            constraint_type="range",
        )
        constraint2 = ConstraintIR(
            entity="Order",
            field="price",
            validation_type=ValidationType.RANGE,
            constraint_type="range",
        )

        result = matcher.match_ir(constraint1, constraint2)

        assert result.match is False
        assert result.method == "no_match"

    def test_no_match_different_field(self, matcher):
        """Test no match when fields differ."""
        constraint1 = ConstraintIR(
            entity="Product",
            field="price",
            validation_type=ValidationType.RANGE,
            constraint_type="range",
        )
        constraint2 = ConstraintIR(
            entity="Product",
            field="cost",
            validation_type=ValidationType.RANGE,
            constraint_type="range",
        )

        result = matcher.match_ir(constraint1, constraint2)

        assert result.match is False


class TestValidationTypeMatching:
    """Tests for ValidationType matching (Level 2)."""

    def test_validation_type_match_different_constraint_types(self, matcher):
        """Test match when validation_type matches but constraint_type differs."""
        constraint1 = ConstraintIR(
            entity="Product",
            field="price",
            validation_type=ValidationType.RANGE,
            constraint_type="range_min",
            value=0,
        )
        constraint2 = ConstraintIR(
            entity="Product",
            field="price",
            validation_type=ValidationType.RANGE,
            constraint_type="range_max",
            value=100,
        )

        result = matcher.match_ir(constraint1, constraint2)

        assert result.match is True
        assert result.confidence == 0.9
        assert result.method == "validation_type_ir"
        assert result.category_match is True


class TestFieldMatching:
    """Tests for field-level matching (Level 3)."""

    def test_field_match_different_validation_types(self, matcher):
        """Test match when only entity and field match."""
        constraint1 = ConstraintIR(
            entity="Product",
            field="price",
            validation_type=ValidationType.RANGE,
            constraint_type="range",
        )
        constraint2 = ConstraintIR(
            entity="Product",
            field="price",
            validation_type=ValidationType.FORMAT,
            constraint_type="currency",
        )

        result = matcher.match_ir(constraint1, constraint2)

        assert result.match is True
        assert result.confidence == 0.7
        assert result.method == "field_ir"
        assert result.category_match is False


class TestValueCompatibility:
    """Tests for value compatibility checking."""

    def test_numeric_values_within_tolerance(self, matcher):
        """Test that numeric values within tolerance are compatible."""
        constraint1 = ConstraintIR(
            entity="Product",
            field="price",
            validation_type=ValidationType.RANGE,
            constraint_type="range",
            value=0,
        )
        constraint2 = ConstraintIR(
            entity="Product",
            field="price",
            validation_type=ValidationType.RANGE,
            constraint_type="range",
            value=0.0001,
        )

        result = matcher.match_ir(constraint1, constraint2)

        assert result.match is True
        assert result.value_match is True

    def test_list_values_order_independent(self, matcher):
        """Test that list values are compared order-independently."""
        constraint1 = ConstraintIR(
            entity="Order",
            field="status",
            validation_type=ValidationType.STATUS_TRANSITION,
            constraint_type="enum",
            value=["pending", "processing", "completed"],
        )
        constraint2 = ConstraintIR(
            entity="Order",
            field="status",
            validation_type=ValidationType.STATUS_TRANSITION,
            constraint_type="enum",
            value=["completed", "pending", "processing"],
        )

        result = matcher.match_ir(constraint1, constraint2)

        assert result.value_match is True

    def test_string_values_case_insensitive(self, matcher):
        """Test that string values are compared case-insensitively."""
        constraint1 = ConstraintIR(
            entity="Product",
            field="name",
            validation_type=ValidationType.FORMAT,
            constraint_type="format",
            value="uppercase",
        )
        constraint2 = ConstraintIR(
            entity="Product",
            field="name",
            validation_type=ValidationType.FORMAT,
            constraint_type="format",
            value="UPPERCASE",
        )

        assert constraint1._values_match(constraint1.value, constraint2.value) is True


class TestConstraintKeyGeneration:
    """Tests for constraint key generation."""

    def test_canonical_key_format(self):
        """Test canonical key format."""
        constraint = ConstraintIR(
            entity="Product",
            field="price",
            validation_type=ValidationType.RANGE,
            constraint_type="range",
        )

        assert constraint.canonical_key == "Product.price.range"

    def test_validation_type_key_format(self):
        """Test validation type key format."""
        constraint = ConstraintIR(
            entity="Product",
            field="price",
            validation_type=ValidationType.RANGE,
            constraint_type="range",
        )

        assert constraint.validation_type_key == "Product.price.range"

    def test_field_key_format(self):
        """Test field key format."""
        constraint = ConstraintIR(
            entity="Product",
            field="price",
            validation_type=ValidationType.RANGE,
            constraint_type="range",
        )

        assert constraint.field_key == "Product.price"


class TestListMatching:
    """Tests for matching lists of constraints."""

    def test_match_lists_with_all_matching(self, matcher):
        """Test matching lists where all spec constraints have code matches."""
        spec_constraints = [
            ConstraintIR(
                entity="Product",
                field="price",
                validation_type=ValidationType.RANGE,
                constraint_type="range",
            ),
            ConstraintIR(
                entity="Product",
                field="name",
                validation_type=ValidationType.PRESENCE,
                constraint_type="required",
            ),
        ]

        code_constraints = [
            ConstraintIR(
                entity="Product",
                field="price",
                validation_type=ValidationType.RANGE,
                constraint_type="range",
            ),
            ConstraintIR(
                entity="Product",
                field="name",
                validation_type=ValidationType.PRESENCE,
                constraint_type="required",
            ),
        ]

        compliance, results = matcher.match_constraint_lists(spec_constraints, code_constraints)

        assert compliance == 1.0  # 100% compliance
        assert len(results) == 2
        assert all(r.match for r in results)

    def test_match_lists_with_partial_matching(self, matcher):
        """Test matching lists with partial matches."""
        spec_constraints = [
            ConstraintIR(
                entity="Product",
                field="price",
                validation_type=ValidationType.RANGE,
                constraint_type="range",
            ),
            ConstraintIR(
                entity="Product",
                field="name",
                validation_type=ValidationType.PRESENCE,
                constraint_type="required",
            ),
        ]

        code_constraints = [
            ConstraintIR(
                entity="Product",
                field="price",
                validation_type=ValidationType.RANGE,
                constraint_type="range",
            ),
        ]

        compliance, results = matcher.match_constraint_lists(spec_constraints, code_constraints)

        assert compliance == 0.5  # 50% compliance
        assert len(results) == 2
        assert results[0].match is True
        assert results[1].match is False

    def test_match_empty_lists(self, matcher):
        """Test matching empty constraint lists."""
        compliance, results = matcher.match_constraint_lists([], [])

        assert compliance == 1.0  # No constraints = 100% compliance
        assert len(results) == 0

    def test_match_lists_no_matching_fields(self, matcher):
        """Test matching lists where spec fields don't exist in code."""
        spec_constraints = [
            ConstraintIR(
                entity="Product",
                field="price",
                validation_type=ValidationType.RANGE,
                constraint_type="range",
            ),
        ]

        code_constraints = [
            ConstraintIR(
                entity="Product",
                field="cost",
                validation_type=ValidationType.RANGE,
                constraint_type="range",
            ),
        ]

        compliance, results = matcher.match_constraint_lists(spec_constraints, code_constraints)

        assert compliance == 0.0  # No matches
        assert len(results) == 1
        assert results[0].match is False


class TestMatchStats:
    """Tests for matcher statistics."""

    def test_get_stats(self, matcher):
        """Test getting matcher statistics."""
        stats = matcher.get_stats()

        assert "embedding_fallback_enabled" in stats
        assert "exact_threshold" in stats
        assert stats["exact_threshold"] == 1.0
        assert stats["category_threshold"] == 0.9
        assert stats["field_threshold"] == 0.7
