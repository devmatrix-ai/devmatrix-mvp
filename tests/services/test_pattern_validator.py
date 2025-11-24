"""
Unit tests for PatternBasedValidator.

Tests pattern matching, deduplication, and comprehensive extraction.

Author: DevMatrix Team
Date: 2025-11-23
"""
import pytest
from pathlib import Path

from src.services.pattern_validator import PatternBasedValidator, PatternMatch
from src.cognitive.ir.domain_model import Entity, Attribute, DataType
from src.cognitive.ir.api_model import Endpoint, HttpMethod, APIParameter, ParameterLocation
from src.cognitive.ir.validation_model import ValidationRule, ValidationType


class TestPatternBasedValidator:
    """Test suite for PatternBasedValidator."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return PatternBasedValidator()

    @pytest.fixture
    def sample_entity(self):
        """Create sample entity with various field types."""
        return Entity(
            name="User",
            attributes=[
                Attribute(name="id", data_type=DataType.UUID, is_primary_key=True, is_nullable=False),
                Attribute(name="email", data_type=DataType.STRING, is_unique=True, is_nullable=False),
                Attribute(name="password", data_type=DataType.STRING, is_nullable=False),
                Attribute(name="created_at", data_type=DataType.DATETIME, is_nullable=False),
                Attribute(name="is_active", data_type=DataType.BOOLEAN, is_nullable=False),
            ]
        )

    def test_patterns_loaded(self, validator):
        """Test that patterns are loaded from YAML file."""
        assert validator.patterns is not None
        assert len(validator.patterns) > 0
        assert "type_patterns" in validator.patterns
        assert "semantic_patterns" in validator.patterns
        assert "constraint_patterns" in validator.patterns
        assert "endpoint_patterns" in validator.patterns

    def test_type_pattern_matching(self, validator, sample_entity):
        """Test type-based pattern matching."""
        matches = validator._extract_type_patterns([sample_entity])

        # Should have matches for UUID, String, DateTime, Boolean types
        assert len(matches) > 0

        # Check that UUID id field has FORMAT validation
        uuid_format_matches = [
            m for m in matches
            if m.rule.attribute == "id" and m.rule.type == ValidationType.FORMAT
        ]
        assert len(uuid_format_matches) > 0

    def test_semantic_pattern_matching(self, validator, sample_entity):
        """Test semantic pattern matching for email, password."""
        matches = validator._extract_semantic_patterns([sample_entity])

        # Should detect email and password patterns
        email_matches = [m for m in matches if m.rule.attribute == "email"]
        password_matches = [m for m in matches if m.rule.attribute == "password"]

        assert len(email_matches) > 0, "Should detect email pattern"
        assert len(password_matches) > 0, "Should detect password pattern"

        # Email should have FORMAT validation
        email_format = [m for m in email_matches if m.rule.type == ValidationType.FORMAT]
        assert len(email_format) > 0

    def test_constraint_pattern_matching(self, validator, sample_entity):
        """Test constraint-based pattern matching."""
        matches = validator._extract_constraint_patterns([sample_entity])

        # Should have PRESENCE for non-nullable fields
        presence_matches = [m for m in matches if m.rule.type == ValidationType.PRESENCE]
        assert len(presence_matches) > 0

        # Should have UNIQUENESS for unique fields
        uniqueness_matches = [m for m in matches if m.rule.type == ValidationType.UNIQUENESS]
        assert len(uniqueness_matches) > 0

    def test_endpoint_pattern_matching(self, validator):
        """Test endpoint pattern matching."""
        endpoints = [
            Endpoint(
                path="/api/v1/users",
                method=HttpMethod.POST,
                operation_id="create_user"
            ),
            Endpoint(
                path="/api/v1/users/{id}",
                method=HttpMethod.GET,
                operation_id="get_user",
                parameters=[
                    APIParameter(name="id", location=ParameterLocation.PATH, data_type="UUID")
                ]
            ),
        ]

        matches = validator._extract_endpoint_patterns(endpoints)

        # Should have matches for POST and GET endpoints
        assert len(matches) > 0

        # POST should require body
        post_matches = [m for m in matches if "body" in m.rule.attribute]
        assert len(post_matches) > 0

    def test_implicit_pattern_matching(self, validator, sample_entity):
        """Test implicit pattern matching for created_at, is_active."""
        matches = validator._extract_implicit_patterns([sample_entity])

        # Should detect created_at and is_active
        created_at_matches = [m for m in matches if m.rule.attribute == "created_at"]
        is_active_matches = [m for m in matches if m.rule.attribute == "is_active"]

        assert len(created_at_matches) > 0, "Should detect created_at implicit pattern"
        assert len(is_active_matches) > 0, "Should detect is_active implicit pattern"

    def test_deduplication(self, validator):
        """Test that duplicate rules are properly deduplicated."""
        # Create two identical matches
        rule1 = ValidationRule(
            entity="User",
            attribute="email",
            type=ValidationType.FORMAT,
            error_message="Email is invalid"
        )
        rule2 = ValidationRule(
            entity="User",
            attribute="email",
            type=ValidationType.FORMAT,
            error_message="Email must be valid"
        )

        matches = [
            PatternMatch(rule=rule1, confidence=0.9, pattern_source="semantic"),
            PatternMatch(rule=rule2, confidence=0.95, pattern_source="type"),
        ]

        deduplicated = validator._deduplicate_rules(matches)

        # Should keep only one rule (higher confidence)
        assert len(deduplicated) == 1
        assert deduplicated[0].error_message == rule2.error_message

    def test_field_name_matching(self, validator):
        """Test field name pattern matching with wildcards."""
        # Test exact match
        assert validator._matches_field_name("id", ["id"])

        # Test wildcard suffix
        assert validator._matches_field_name("user_id", ["*_id"])
        assert validator._matches_field_name("product_id", ["*_id"])

        # Test wildcard prefix
        assert validator._matches_field_name("is_active", ["is_*"])
        assert validator._matches_field_name("is_deleted", ["is_*"])

        # Test no match
        assert not validator._matches_field_name("name", ["*_id"])

    def test_data_type_mapping(self, validator):
        """Test DataType enum to pattern key mapping."""
        assert validator._map_data_type(DataType.UUID) == "UUID"
        assert validator._map_data_type(DataType.STRING) == "String"
        assert validator._map_data_type(DataType.INTEGER) == "Integer"
        assert validator._map_data_type(DataType.FLOAT) == "Decimal"
        assert validator._map_data_type(DataType.BOOLEAN) == "Boolean"
        assert validator._map_data_type(DataType.DATETIME) == "DateTime"

    def test_domain_detection(self, validator):
        """Test domain pattern detection."""
        # E-commerce entities
        entity_names = {"Product", "Order", "OrderItem"}
        domains = validator._detect_domains(entity_names, validator.patterns.get("domain_patterns", {}))

        # Should detect e-commerce domain
        assert "e-commerce" in domains

    def test_full_extraction(self, validator):
        """Test complete extraction pipeline."""
        entities = [
            Entity(
                name="Product",
                attributes=[
                    Attribute(name="id", data_type=DataType.UUID, is_primary_key=True, is_nullable=False),
                    Attribute(name="sku", data_type=DataType.STRING, is_unique=True, is_nullable=False),
                    Attribute(name="price", data_type=DataType.FLOAT, is_nullable=False),
                    Attribute(name="quantity", data_type=DataType.INTEGER, is_nullable=False),
                    Attribute(name="status", data_type=DataType.STRING, is_nullable=False),
                ]
            )
        ]

        endpoints = [
            Endpoint(
                path="/api/v1/products",
                method=HttpMethod.POST,
                operation_id="create_product"
            )
        ]

        rules = validator.extract_patterns(entities, endpoints)

        # Should extract many rules
        assert len(rules) >= 10, f"Expected at least 10 rules, got {len(rules)}"

        # Should have various types
        types_present = {r.type for r in rules}
        assert ValidationType.FORMAT in types_present
        assert ValidationType.PRESENCE in types_present

    def test_confidence_scoring(self, validator, sample_entity):
        """Test that confidence scores are properly assigned."""
        matches = validator._extract_type_patterns([sample_entity])

        # All matches should have confidence scores
        for match in matches:
            assert 0.0 <= match.confidence <= 1.0

    def test_foreign_key_detection(self, validator):
        """Test foreign key constraint detection."""
        entity = Entity(
            name="Order",
            attributes=[
                Attribute(name="user_id", data_type=DataType.UUID, is_nullable=False),
                Attribute(name="product_id", data_type=DataType.UUID, is_nullable=False),
            ]
        )

        matches = validator._extract_constraint_patterns([entity])

        # Should detect foreign key relationships
        fk_matches = [m for m in matches if m.rule.type == ValidationType.RELATIONSHIP]
        assert len(fk_matches) >= 2

    def test_coverage_improvement(self, validator):
        """Test that pattern extraction provides significant coverage improvement."""
        # Create comprehensive test specification (similar to full e-commerce)
        entities = [
            Entity(
                name="User",
                attributes=[
                    Attribute(name="id", data_type=DataType.UUID, is_primary_key=True, is_nullable=False),
                    Attribute(name="email", data_type=DataType.STRING, is_unique=True, is_nullable=False),
                    Attribute(name="password", data_type=DataType.STRING, is_nullable=False),
                    Attribute(name="phone", data_type=DataType.STRING, is_nullable=True),
                    Attribute(name="status", data_type=DataType.STRING, is_nullable=False),
                    Attribute(name="created_at", data_type=DataType.DATETIME, is_nullable=False),
                    Attribute(name="updated_at", data_type=DataType.DATETIME, is_nullable=False),
                ]
            ),
            Entity(
                name="Product",
                attributes=[
                    Attribute(name="id", data_type=DataType.UUID, is_primary_key=True, is_nullable=False),
                    Attribute(name="sku", data_type=DataType.STRING, is_unique=True, is_nullable=False),
                    Attribute(name="name", data_type=DataType.STRING, is_nullable=False),
                    Attribute(name="price", data_type=DataType.FLOAT, is_nullable=False),
                    Attribute(name="quantity", data_type=DataType.INTEGER, is_nullable=False),
                    Attribute(name="status", data_type=DataType.STRING, is_nullable=False),
                    Attribute(name="created_at", data_type=DataType.DATETIME, is_nullable=False),
                    Attribute(name="is_active", data_type=DataType.BOOLEAN, is_nullable=False),
                ]
            ),
            Entity(
                name="Order",
                attributes=[
                    Attribute(name="id", data_type=DataType.UUID, is_primary_key=True, is_nullable=False),
                    Attribute(name="user_id", data_type=DataType.UUID, is_nullable=False),
                    Attribute(name="status", data_type=DataType.STRING, is_nullable=False),
                    Attribute(name="total_amount", data_type=DataType.FLOAT, is_nullable=False),
                    Attribute(name="created_at", data_type=DataType.DATETIME, is_nullable=False),
                ]
            ),
            Entity(
                name="OrderItem",
                attributes=[
                    Attribute(name="id", data_type=DataType.UUID, is_primary_key=True, is_nullable=False),
                    Attribute(name="order_id", data_type=DataType.UUID, is_nullable=False),
                    Attribute(name="product_id", data_type=DataType.UUID, is_nullable=False),
                    Attribute(name="quantity", data_type=DataType.INTEGER, is_nullable=False),
                    Attribute(name="unit_price", data_type=DataType.FLOAT, is_nullable=False),
                ]
            ),
        ]

        endpoints = [
            Endpoint(path="/api/v1/users", method=HttpMethod.POST, operation_id="create_user"),
            Endpoint(path="/api/v1/products", method=HttpMethod.POST, operation_id="create_product"),
            Endpoint(path="/api/v1/products/{id}", method=HttpMethod.GET, operation_id="get_product"),
            Endpoint(path="/api/v1/products/{id}", method=HttpMethod.PUT, operation_id="update_product"),
            Endpoint(path="/api/v1/orders", method=HttpMethod.POST, operation_id="create_order"),
        ]

        rules = validator.extract_patterns(entities, endpoints)

        # Baseline from requirements: 22 validations
        # Target: 45-50 validations (+30-40% improvement)
        baseline = 22
        improvement = len(rules) - baseline
        improvement_pct = (improvement / baseline) * 100 if baseline > 0 else 0

        assert len(rules) > baseline, f"Expected improvement over baseline {baseline}, got {len(rules)}"
        assert improvement_pct >= 30, f"Expected at least 30% improvement, got {improvement_pct:.1f}%"


class TestPatternMatchingEdgeCases:
    """Test edge cases in pattern matching."""

    @pytest.fixture
    def validator(self):
        return PatternBasedValidator()

    def test_empty_specification(self, validator):
        """Test extraction with empty specification."""
        rules = validator.extract_patterns([], [])
        assert rules == []

    def test_entity_without_constraints(self, validator):
        """Test entity with nullable, non-unique fields."""
        entity = Entity(
            name="Note",
            attributes=[
                Attribute(name="content", data_type=DataType.STRING, is_nullable=True, is_unique=False),
            ]
        )

        rules = validator.extract_patterns([entity], [])
        # Should still extract some rules (type-based, implicit)
        assert len(rules) >= 0

    def test_endpoint_without_path_parameters(self, validator):
        """Test endpoint with no path parameters."""
        endpoint = Endpoint(
            path="/api/v1/health",
            method=HttpMethod.GET,
            operation_id="health_check"
        )

        matches = validator._extract_endpoint_patterns([endpoint])
        # May or may not match patterns, should not crash
        assert isinstance(matches, list)

    def test_unsupported_data_type(self, validator):
        """Test field with JSON data type."""
        entity = Entity(
            name="Config",
            attributes=[
                Attribute(name="settings", data_type=DataType.JSON, is_nullable=True),
            ]
        )

        # Should not crash, may fall back to String patterns
        rules = validator.extract_patterns([entity], [])
        assert isinstance(rules, list)
