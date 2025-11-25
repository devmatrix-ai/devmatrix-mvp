"""
Unit tests for Phase 2: SemanticNormalizer.

Tests constraint normalization from raw format to canonical ApplicationIR form.
"""

import pytest
from src.services.semantic_normalizer import (
    SemanticNormalizer,
    ConstraintRule,
    NormalizedRule,
)
from src.cognitive.ir.application_ir import ApplicationIR
from src.cognitive.ir.domain_model import (
    DomainModelIR,
    Entity,
    Attribute,
    DataType,
)
from src.cognitive.ir.api_model import APIModelIR
from src.cognitive.ir.infrastructure_model import (
    InfrastructureModelIR,
    DatabaseConfig,
    DatabaseType,
)
from src.cognitive.ir.validation_model import (
    ValidationType,
    EnforcementType,
)


@pytest.fixture
def sample_application_ir():
    """Create sample ApplicationIR for testing."""
    # Domain model with Product and Order entities
    domain_model = DomainModelIR(
        entities=[
            Entity(
                name="Product",
                attributes=[
                    Attribute(
                        name="id",
                        data_type=DataType.UUID,
                        is_primary_key=True,
                    ),
                    Attribute(
                        name="name",
                        data_type=DataType.STRING,
                    ),
                    Attribute(
                        name="price",
                        data_type=DataType.FLOAT,
                    ),
                    Attribute(
                        name="stock",
                        data_type=DataType.INTEGER,
                    ),
                ],
            ),
            Entity(
                name="Order",
                attributes=[
                    Attribute(
                        name="id",
                        data_type=DataType.UUID,
                        is_primary_key=True,
                    ),
                    Attribute(
                        name="status",
                        data_type=DataType.STRING,
                    ),
                    Attribute(
                        name="createdAt",
                        data_type=DataType.DATETIME,
                    ),
                ],
            ),
        ]
    )

    # Create infrastructure model with required database config
    infrastructure_model = InfrastructureModelIR(
        database=DatabaseConfig(
            type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            name="test_db",
            user="test_user",
            password_env_var="DB_PASSWORD",
        )
    )

    return ApplicationIR(
        name="test_app",
        domain_model=domain_model,
        api_model=APIModelIR(endpoints=[]),
        infrastructure_model=infrastructure_model,
    )


class TestSemanticNormalizerInitialization:
    """Tests for SemanticNormalizer initialization."""

    def test_init_with_application_ir(self, sample_application_ir):
        """Test initialization with ApplicationIR."""
        normalizer = SemanticNormalizer(sample_application_ir)
        assert normalizer.ir == sample_application_ir
        assert len(normalizer.entity_lookup) > 0
        assert len(normalizer.field_lookup) > 0

    def test_entity_lookup_built_correctly(self, sample_application_ir):
        """Test that entity lookup table is built correctly."""
        normalizer = SemanticNormalizer(sample_application_ir)
        assert "product" in normalizer.entity_lookup
        assert normalizer.entity_lookup["product"] == "Product"
        assert "order" in normalizer.entity_lookup
        assert normalizer.entity_lookup["order"] == "Order"

    def test_field_lookup_built_correctly(self, sample_application_ir):
        """Test that field lookup table is built correctly."""
        normalizer = SemanticNormalizer(sample_application_ir)
        assert "Product" in normalizer.field_lookup
        assert "price" in normalizer.field_lookup["Product"]
        assert normalizer.field_lookup["Product"]["price"] == "price"


class TestEntityResolution:
    """Tests for entity name resolution."""

    def test_exact_match(self, sample_application_ir):
        """Test exact entity name match."""
        normalizer = SemanticNormalizer(sample_application_ir)
        canonical, match_type = normalizer._resolve_entity("Product")
        assert canonical == "Product"
        assert match_type == "exact_match"

    def test_case_variation(self, sample_application_ir):
        """Test case-insensitive entity resolution."""
        normalizer = SemanticNormalizer(sample_application_ir)
        canonical, match_type = normalizer._resolve_entity("product")
        assert canonical == "Product"
        assert match_type == "case_variation"

    def test_case_uppercase(self, sample_application_ir):
        """Test uppercase entity resolution."""
        normalizer = SemanticNormalizer(sample_application_ir)
        canonical, match_type = normalizer._resolve_entity("PRODUCT")
        assert canonical == "Product"
        assert match_type == "case_variation"

    def test_plural_form(self, sample_application_ir):
        """Test plural entity resolution."""
        normalizer = SemanticNormalizer(sample_application_ir)
        canonical, match_type = normalizer._resolve_entity("products")
        # Should resolve plural to singular entity
        assert canonical == "Product"
        # Match type should be case_variation (from plural lookup)
        assert match_type == "case_variation"

    def test_nonexistent_entity(self, sample_application_ir):
        """Test nonexistent entity returns None."""
        normalizer = SemanticNormalizer(sample_application_ir)
        canonical, match_type = normalizer._resolve_entity("NonExistent")
        assert canonical is None
        assert match_type == "no_match"

    def test_empty_entity_name(self, sample_application_ir):
        """Test empty entity name."""
        normalizer = SemanticNormalizer(sample_application_ir)
        canonical, match_type = normalizer._resolve_entity("")
        assert canonical is None
        assert match_type == "empty"


class TestFieldResolution:
    """Tests for field name resolution."""

    def test_exact_field_match(self, sample_application_ir):
        """Test exact field name match."""
        normalizer = SemanticNormalizer(sample_application_ir)
        canonical, match_type = normalizer._resolve_field("Product", "price")
        assert canonical == "price"
        assert match_type == "exact_match"

    def test_case_insensitive_field(self, sample_application_ir):
        """Test case-insensitive field resolution."""
        normalizer = SemanticNormalizer(sample_application_ir)
        canonical, match_type = normalizer._resolve_field("Product", "PRICE")
        assert canonical == "price"
        assert match_type == "case_variation"

    def test_camel_case_field(self, sample_application_ir):
        """Test camelCase field resolution."""
        normalizer = SemanticNormalizer(sample_application_ir)
        canonical, match_type = normalizer._resolve_field("Order", "createdAt")
        assert canonical == "createdAt"
        assert match_type == "exact_match"

    def test_nonexistent_field(self, sample_application_ir):
        """Test nonexistent field returns None."""
        normalizer = SemanticNormalizer(sample_application_ir)
        canonical, match_type = normalizer._resolve_field("Product", "nonexistent")
        assert canonical is None
        assert match_type == "no_match"

    def test_wrong_entity(self, sample_application_ir):
        """Test field resolution with wrong entity."""
        normalizer = SemanticNormalizer(sample_application_ir)
        canonical, match_type = normalizer._resolve_field("NonExistent", "price")
        assert canonical is None


class TestConstraintTypeResolution:
    """Tests for constraint type normalization."""

    def test_email_format_constraint(self, sample_application_ir):
        """Test email format constraint resolution."""
        normalizer = SemanticNormalizer(sample_application_ir)
        vtype, match_type = normalizer._resolve_constraint_type(
            "EmailStr", "Product", "email"
        )
        assert vtype == ValidationType.FORMAT
        assert match_type == "pattern_inference"

    def test_range_min_constraint(self, sample_application_ir):
        """Test minimum range constraint."""
        normalizer = SemanticNormalizer(sample_application_ir)
        vtype, match_type = normalizer._resolve_constraint_type("gt=0", "Product", "price")
        assert vtype == ValidationType.RANGE
        assert match_type == "pattern_inference"

    def test_uniqueness_constraint(self, sample_application_ir):
        """Test uniqueness constraint."""
        normalizer = SemanticNormalizer(sample_application_ir)
        vtype, match_type = normalizer._resolve_constraint_type(
            "unique", "Product", "sku"
        )
        assert vtype == ValidationType.UNIQUENESS
        assert match_type == "pattern_inference"

    def test_required_constraint(self, sample_application_ir):
        """Test required/presence constraint."""
        normalizer = SemanticNormalizer(sample_application_ir)
        vtype, match_type = normalizer._resolve_constraint_type(
            "required", "Product", "name"
        )
        assert vtype == ValidationType.PRESENCE
        assert match_type == "pattern_inference"

    def test_status_transition_constraint(self, sample_application_ir):
        """Test status/workflow constraint."""
        normalizer = SemanticNormalizer(sample_application_ir)
        vtype, match_type = normalizer._resolve_constraint_type(
            "status transition", "Order", "status"
        )
        assert vtype == ValidationType.STATUS_TRANSITION
        assert match_type == "pattern_inference"

    def test_direct_validation_type_match(self, sample_application_ir):
        """Test direct ValidationType name match."""
        normalizer = SemanticNormalizer(sample_application_ir)
        vtype, match_type = normalizer._resolve_constraint_type(
            "format", "Product", "email"
        )
        assert vtype == ValidationType.FORMAT
        assert match_type == "direct_match"


class TestEnforcementTypeMapping:
    """Tests for enforcement type mapping."""

    def test_validator_enforcement(self, sample_application_ir):
        """Test validator enforcement mapping."""
        normalizer = SemanticNormalizer(sample_application_ir)
        etype = normalizer._map_enforcement_type("validator")
        assert etype == EnforcementType.VALIDATOR

    def test_database_enforcement(self, sample_application_ir):
        """Test database enforcement mapping."""
        normalizer = SemanticNormalizer(sample_application_ir)
        etype = normalizer._map_enforcement_type("database")
        assert etype == EnforcementType.VALIDATOR

    def test_computed_field_enforcement(self, sample_application_ir):
        """Test computed field enforcement."""
        normalizer = SemanticNormalizer(sample_application_ir)
        etype = normalizer._map_enforcement_type("computed_field")
        assert etype == EnforcementType.COMPUTED_FIELD

    def test_state_machine_enforcement(self, sample_application_ir):
        """Test state machine enforcement."""
        normalizer = SemanticNormalizer(sample_application_ir)
        etype = normalizer._map_enforcement_type("state_machine")
        assert etype == EnforcementType.STATE_MACHINE

    def test_default_enforcement(self, sample_application_ir):
        """Test default enforcement mapping."""
        normalizer = SemanticNormalizer(sample_application_ir)
        etype = normalizer._map_enforcement_type("unknown_type")
        assert etype == EnforcementType.VALIDATOR


class TestValueNormalization:
    """Tests for value normalization."""

    def test_range_value_string_to_float(self, sample_application_ir):
        """Test converting string range value to float."""
        normalizer = SemanticNormalizer(sample_application_ir)
        result = normalizer._normalize_value(
            ValidationType.RANGE, "100.5", "price"
        )
        assert result == 100.5
        assert isinstance(result, float)

    def test_range_value_keeps_numeric(self, sample_application_ir):
        """Test that numeric range values are preserved."""
        normalizer = SemanticNormalizer(sample_application_ir)
        result = normalizer._normalize_value(ValidationType.RANGE, 50, "price")
        assert result == 50

    def test_format_value_preserved(self, sample_application_ir):
        """Test that format values are preserved."""
        normalizer = SemanticNormalizer(sample_application_ir)
        result = normalizer._normalize_value(
            ValidationType.FORMAT, "^[a-z]+$", "name"
        )
        assert result == "^[a-z]+$"

    def test_none_value_preserved(self, sample_application_ir):
        """Test that None values are preserved."""
        normalizer = SemanticNormalizer(sample_application_ir)
        result = normalizer._normalize_value(ValidationType.PRESENCE, None, "name")
        assert result is None


class TestFullConstraintNormalization:
    """Tests for complete constraint normalization."""

    def test_normalize_simple_rule(self, sample_application_ir):
        """Test normalizing a simple constraint rule."""
        normalizer = SemanticNormalizer(sample_application_ir)

        raw_rule = ConstraintRule(
            entity="product",
            field="PRICE",
            constraint_type="range",
            value="0",
            enforcement_type="validator",
            source="openapi",
        )

        normalized = normalizer.normalize_rule(raw_rule)

        assert normalized.entity == "Product"
        assert normalized.field == "price"
        assert normalized.validation_type == ValidationType.RANGE
        assert normalized.value == 0.0
        assert normalized.enforcement_type == EnforcementType.VALIDATOR
        assert normalized.confidence > 0.0

    def test_normalize_with_case_variations(self, sample_application_ir):
        """Test normalization with case variations."""
        normalizer = SemanticNormalizer(sample_application_ir)

        raw_rule = ConstraintRule(
            entity="ORDER",
            field="status",
            constraint_type="STATUS_TRANSITION",
            source="business_logic",
        )

        normalized = normalizer.normalize_rule(raw_rule)

        assert normalized.entity == "Order"
        assert normalized.field == "status"
        assert normalized.validation_type == ValidationType.STATUS_TRANSITION

    def test_normalize_missing_entity_raises_error(self, sample_application_ir):
        """Test that missing entity raises ValueError."""
        normalizer = SemanticNormalizer(sample_application_ir)

        raw_rule = ConstraintRule(
            entity="NonExistentEntity",
            field="field",
            constraint_type="required",
            source="openapi",
        )

        with pytest.raises(ValueError, match="Cannot resolve entity"):
            normalizer.normalize_rule(raw_rule)

    def test_normalize_missing_field_raises_error(self, sample_application_ir):
        """Test that missing field raises ValueError."""
        normalizer = SemanticNormalizer(sample_application_ir)

        raw_rule = ConstraintRule(
            entity="Product",
            field="nonexistent_field",
            constraint_type="required",
            source="openapi",
        )

        with pytest.raises(ValueError, match="Cannot resolve field"):
            normalizer.normalize_rule(raw_rule)


class TestConfidenceScoring:
    """Tests for confidence score calculation."""

    def test_exact_match_high_confidence(self, sample_application_ir):
        """Test that exact matches have high confidence."""
        normalizer = SemanticNormalizer(sample_application_ir)

        raw_rule = ConstraintRule(
            entity="Product",
            field="price",
            constraint_type="range",
            value=0,
            source="ast_sqlalchemy",
        )

        normalized = normalizer.normalize_rule(raw_rule)
        # Exact matches should have high confidence (>= 0.85)
        # Small penalty for source priority still applies
        assert normalized.confidence >= 0.85

    def test_fuzzy_match_lower_confidence(self, sample_application_ir):
        """Test that fuzzy matches have lower confidence."""
        normalizer = SemanticNormalizer(sample_application_ir)

        raw_rule = ConstraintRule(
            entity="product",  # case variation
            field="PRICE",     # case variation
            constraint_type="range",
            value="0",         # string instead of number
            source="openapi",  # lower reliability
        )

        normalized = normalizer.normalize_rule(raw_rule)
        # Should be lower than exact match but still reasonable
        assert 0.5 < normalized.confidence < 0.9

    def test_confidence_source_impact(self, sample_application_ir):
        """Test that source impacts confidence."""
        normalizer = SemanticNormalizer(sample_application_ir)

        # High reliability source
        rule_high = ConstraintRule(
            entity="Product",
            field="price",
            constraint_type="range",
            source="ast_sqlalchemy",
        )
        normalized_high = normalizer.normalize_rule(rule_high)

        # Low reliability source
        rule_low = ConstraintRule(
            entity="Product",
            field="price",
            constraint_type="range",
            source="business_logic",
        )
        normalized_low = normalizer.normalize_rule(rule_low)

        # High reliability should have better confidence
        assert normalized_high.confidence > normalized_low.confidence


class TestBatchNormalization:
    """Tests for batch rule normalization."""

    def test_normalize_multiple_rules(self, sample_application_ir):
        """Test normalizing multiple rules."""
        normalizer = SemanticNormalizer(sample_application_ir)

        rules = [
            ConstraintRule(
                entity="product",
                field="price",
                constraint_type="range",
                source="openapi",
            ),
            ConstraintRule(
                entity="order",
                field="status",
                constraint_type="status",
                source="business_logic",
            ),
        ]

        normalized, errors = normalizer.normalize_rules(rules)

        assert len(normalized) == 2
        assert len(errors) == 0

    def test_batch_with_errors(self, sample_application_ir):
        """Test batch normalization with invalid rules."""
        normalizer = SemanticNormalizer(sample_application_ir)

        rules = [
            ConstraintRule(
                entity="Product",
                field="price",
                constraint_type="range",
                source="openapi",
            ),
            ConstraintRule(
                entity="InvalidEntity",
                field="field",
                constraint_type="required",
                source="openapi",
            ),
        ]

        normalized, errors = normalizer.normalize_rules(rules)

        assert len(normalized) == 1
        assert len(errors) == 1


class TestCaseConversion:
    """Tests for case conversion utilities."""

    def test_snake_to_camel(self, sample_application_ir):
        """Test snake_case to camelCase conversion."""
        result = SemanticNormalizer._snake_to_camel("created_at")
        assert result == "createdAt"

    def test_camel_to_snake(self, sample_application_ir):
        """Test camelCase to snake_case conversion."""
        result = SemanticNormalizer._camel_to_snake("createdAt")
        assert result == "created_at"

    def test_single_word_snake_to_camel(self, sample_application_ir):
        """Test single word in snake_to_camel."""
        result = SemanticNormalizer._snake_to_camel("price")
        assert result == "price"
