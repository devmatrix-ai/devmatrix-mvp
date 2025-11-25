"""
Unit tests for Phase 2: UnifiedConstraintExtractor.

Tests constraint extraction, merging, and deduplication.
"""

import pytest
from src.services.unified_constraint_extractor import UnifiedConstraintExtractor
from src.cognitive.ir.application_ir import ApplicationIR
from src.cognitive.ir.domain_model import (
    DomainModelIR,
    Entity,
    Attribute,
    DataType,
)
from src.cognitive.ir.api_model import APIModelIR
from src.cognitive.ir.infrastructure_model import InfrastructureModelIR
from src.cognitive.ir.validation_model import (
    ValidationRule,
    ValidationType,
    EnforcementType,
)


@pytest.fixture
def sample_application_ir():
    """Create sample ApplicationIR for testing."""
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
                ],
            ),
        ]
    )

    # Create infrastructure model with required database config
    from src.cognitive.ir.infrastructure_model import DatabaseConfig, DatabaseType

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


class TestUnifiedConstraintExtractorInitialization:
    """Tests for initialization."""

    def test_init(self, sample_application_ir):
        """Test initialization."""
        extractor = UnifiedConstraintExtractor(sample_application_ir)
        assert extractor.ir == sample_application_ir
        assert extractor.business_logic_extractor is not None
        assert extractor.semantic_normalizer is not None


class TestConstraintKeyGeneration:
    """Tests for constraint key generation."""

    def test_make_constraint_key(self, sample_application_ir):
        """Test constraint key generation."""
        extractor = UnifiedConstraintExtractor(sample_application_ir)

        rule = ValidationRule(
            entity="Product",
            attribute="price",
            type=ValidationType.RANGE,
        )

        key = extractor._make_constraint_key(rule)
        assert key == "Product.price.range"

    def test_constraint_key_uniqueness(self, sample_application_ir):
        """Test that different rules have different keys."""
        extractor = UnifiedConstraintExtractor(sample_application_ir)

        rule1 = ValidationRule(
            entity="Product",
            attribute="price",
            type=ValidationType.RANGE,
        )

        rule2 = ValidationRule(
            entity="Product",
            attribute="name",
            type=ValidationType.FORMAT,
        )

        key1 = extractor._make_constraint_key(rule1)
        key2 = extractor._make_constraint_key(rule2)

        assert key1 != key2


class TestSourceInference:
    """Tests for source inference."""

    def test_infer_business_logic_source(self, sample_application_ir):
        """Test inferring business_logic source."""
        extractor = UnifiedConstraintExtractor(sample_application_ir)

        rule = ValidationRule(
            entity="Product",
            attribute="price",
            type=ValidationType.RANGE,
            enforcement_type=EnforcementType.BUSINESS_LOGIC,
        )

        source = extractor._infer_source(rule)
        assert source == "business_logic"

    def test_infer_pydantic_source(self, sample_application_ir):
        """Test inferring pydantic source from code."""
        extractor = UnifiedConstraintExtractor(sample_application_ir)

        rule = ValidationRule(
            entity="Product",
            attribute="price",
            type=ValidationType.RANGE,
            enforcement_code="@field_validator('price')",
        )

        source = extractor._infer_source(rule)
        assert source == "ast_pydantic"

    def test_infer_sqlalchemy_source(self, sample_application_ir):
        """Test inferring SQLAlchemy source from code."""
        extractor = UnifiedConstraintExtractor(sample_application_ir)

        rule = ValidationRule(
            entity="Product",
            attribute="price",
            type=ValidationType.RANGE,
            enforcement_code="Column(Float, CheckConstraint('price > 0'))",
        )

        source = extractor._infer_source(rule)
        assert source == "ast_sqlalchemy"

    def test_infer_unknown_source(self, sample_application_ir):
        """Test inferring unknown source."""
        extractor = UnifiedConstraintExtractor(sample_application_ir)

        rule = ValidationRule(
            entity="Product",
            attribute="price",
            type=ValidationType.RANGE,
        )

        source = extractor._infer_source(rule)
        assert source == "unknown"


class TestSemanticMerge:
    """Tests for semantic merge and deduplication."""

    def test_merge_no_duplicates(self, sample_application_ir):
        """Test merging rules with no duplicates."""
        extractor = UnifiedConstraintExtractor(sample_application_ir)

        rules = [
            ValidationRule(
                entity="Product",
                attribute="price",
                type=ValidationType.RANGE,
            ),
            ValidationRule(
                entity="Product",
                attribute="name",
                type=ValidationType.FORMAT,
            ),
        ]

        merged = extractor._semantic_merge(rules)
        assert len(merged) == 2

    def test_merge_removes_duplicates(self, sample_application_ir):
        """Test that duplicates are removed."""
        extractor = UnifiedConstraintExtractor(sample_application_ir)

        rules = [
            ValidationRule(
                entity="Product",
                attribute="price",
                type=ValidationType.RANGE,
                enforcement_type=EnforcementType.VALIDATOR,
            ),
            ValidationRule(
                entity="Product",
                attribute="price",
                type=ValidationType.RANGE,
                enforcement_type=EnforcementType.VALIDATOR,
            ),
        ]

        merged = extractor._semantic_merge(rules)
        assert len(merged) == 1

    def test_merge_keeps_higher_priority_source(self, sample_application_ir):
        """Test that higher priority source is kept."""
        extractor = UnifiedConstraintExtractor(sample_application_ir)

        # Create two identical constraints from different sources
        rule_low = ValidationRule(
            entity="Product",
            attribute="price",
            type=ValidationType.RANGE,
            enforcement_code="# from business_logic",
        )

        rule_high = ValidationRule(
            entity="Product",
            attribute="price",
            type=ValidationType.RANGE,
            enforcement_code="Column(Float)",  # SQLAlchemy
        )

        # Add to list in order (low, then high)
        rules = [rule_low, rule_high]

        merged = extractor._semantic_merge(rules)
        assert len(merged) == 1
        # Higher priority (SQLAlchemy) should be kept
        assert "Column" in merged[0].enforcement_code

    def test_merge_multiple_duplicates(self, sample_application_ir):
        """Test merging multiple duplicate constraints."""
        extractor = UnifiedConstraintExtractor(sample_application_ir)

        rules = [
            ValidationRule(
                entity="Product",
                attribute="price",
                type=ValidationType.RANGE,
            ),
            ValidationRule(
                entity="Product",
                attribute="price",
                type=ValidationType.RANGE,
            ),
            ValidationRule(
                entity="Product",
                attribute="price",
                type=ValidationType.RANGE,
            ),
            ValidationRule(
                entity="Product",
                attribute="name",
                type=ValidationType.PRESENCE,
            ),
        ]

        merged = extractor._semantic_merge(rules)
        assert len(merged) == 2
        assert any(r.attribute == "price" for r in merged)
        assert any(r.attribute == "name" for r in merged)


class TestExtractAll:
    """Tests for complete extraction."""

    @pytest.mark.asyncio
    async def test_extract_all_with_empty_spec(self, sample_application_ir):
        """Test extraction with empty spec."""
        extractor = UnifiedConstraintExtractor(sample_application_ir)

        spec = {}
        result = await extractor.extract_all(spec)

        assert result is not None
        assert hasattr(result, "rules")

    @pytest.mark.asyncio
    async def test_extract_all_returns_validation_model_ir(self, sample_application_ir):
        """Test that extract_all returns ValidationModelIR."""
        extractor = UnifiedConstraintExtractor(sample_application_ir)

        spec = {
            "name": "test",
            "entities": [
                {
                    "name": "Product",
                    "fields": [
                        {
                            "name": "price",
                            "type": "float",
                            "constraints": {
                                "required": True,
                                "minimum": 0,
                            },
                        }
                    ],
                }
            ],
        }

        result = await extractor.extract_all(spec)

        assert result is not None
        assert len(result.rules) > 0  # Should extract at least one rule
        assert all(isinstance(r, ValidationRule) for r in result.rules)


class TestSourcePriority:
    """Tests for source priority."""

    def test_source_priority_ordering(self, sample_application_ir):
        """Test that source priority is correctly ordered."""
        extractor = UnifiedConstraintExtractor(sample_application_ir)

        # Verify priority values
        assert (
            extractor.SOURCE_PRIORITY["ast_sqlalchemy"]
            < extractor.SOURCE_PRIORITY["ast_pydantic"]
        )
        assert (
            extractor.SOURCE_PRIORITY["ast_pydantic"]
            < extractor.SOURCE_PRIORITY["openapi"]
        )
        assert (
            extractor.SOURCE_PRIORITY["openapi"]
            < extractor.SOURCE_PRIORITY["business_logic"]
        )

    def test_higher_priority_overwrites_lower(self, sample_application_ir):
        """Test that higher priority source overwrites lower."""
        extractor = UnifiedConstraintExtractor(sample_application_ir)

        # Build a scenario with duplicate constraints from different sources
        rule_business = ValidationRule(
            entity="Product",
            attribute="price",
            type=ValidationType.RANGE,
            enforcement_type=EnforcementType.BUSINESS_LOGIC,
        )

        rule_database = ValidationRule(
            entity="Product",
            attribute="price",
            type=ValidationType.RANGE,
            enforcement_type=EnforcementType.VALIDATOR,
            enforcement_code="Column(Float)",
        )

        # Merge with database rule having higher priority
        rules = [rule_business, rule_database]
        merged = extractor._semantic_merge(rules)

        assert len(merged) == 1
        # Should keep the database rule (higher priority source)
        assert "Column" in merged[0].enforcement_code


class TestIntegrationWithComplianceValidator:
    """Tests for integration with ComplianceValidator."""

    def test_extractor_can_be_used_by_compliance_validator(self, sample_application_ir):
        """Test that extractor is compatible with ComplianceValidator."""
        from src.validation.compliance_validator import ComplianceValidator

        validator = ComplianceValidator(application_ir=sample_application_ir)
        extractor = UnifiedConstraintExtractor(sample_application_ir)

        # Should not raise errors
        assert extractor is not None
        assert validator is not None
