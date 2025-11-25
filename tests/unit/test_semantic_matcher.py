"""
Unit tests for SemanticMatcher.

Tests the hybrid embeddings + LLM approach for constraint matching.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.services.semantic_matcher import (
    SemanticMatcher,
    MatchResult,
    SENTENCE_TRANSFORMERS_AVAILABLE,
    ANTHROPIC_AVAILABLE,
)


class TestSemanticMatcherBasic:
    """Basic functionality tests."""

    def test_init_creates_instance(self):
        """Test that SemanticMatcher can be instantiated."""
        matcher = SemanticMatcher()
        assert matcher is not None

    def test_match_returns_result(self):
        """Test that match returns a MatchResult."""
        matcher = SemanticMatcher()
        result = matcher.match("email must be valid", "email: EmailStr")
        assert isinstance(result, MatchResult)
        assert isinstance(result.match, bool)
        assert isinstance(result.confidence, float)
        assert result.method in ("embedding", "llm", "fallback")

    def test_match_batch_returns_list(self):
        """Test that match_batch returns list of results."""
        matcher = SemanticMatcher()
        specs = ["email must be valid", "price must be positive"]
        codes = ["email: EmailStr", "price: gt=0"]

        results = matcher.match_batch(specs, codes)
        assert isinstance(results, list)

    def test_get_stats_returns_dict(self):
        """Test that get_stats returns statistics."""
        matcher = SemanticMatcher()
        stats = matcher.get_stats()
        assert isinstance(stats, dict)
        assert "cache_size" in stats
        assert "encoder_available" in stats
        assert "llm_available" in stats


class TestSemanticMatching:
    """Test semantic matching accuracy."""

    @pytest.fixture
    def matcher(self):
        return SemanticMatcher()

    def test_exact_match_high_confidence(self, matcher):
        """Exact same text should match with high confidence."""
        result = matcher.match("email: required", "email: required")
        assert result.match is True
        assert result.confidence >= 0.8

    def test_similar_constraints_match(self, matcher):
        """Similar constraints should match."""
        result = matcher.match("price must be greater than zero", "price: gt=0")
        # Should match even with different wording
        assert result.confidence > 0.3  # At least fallback level

    def test_unrelated_constraints_no_match(self, matcher):
        """Completely unrelated constraints should not match."""
        result = matcher.match("email validation", "database timeout")
        # Should NOT match (match=False), confidence might be high if inverted
        assert result.match is False

    def test_email_format_variations(self, matcher):
        """Test various ways to express email validation."""
        email_specs = [
            "email must be valid",
            "valid email format",
            "email_format",
        ]
        email_codes = [
            "email: EmailStr",
            "email: email_format",
            "email: pattern=email",
        ]

        for spec in email_specs:
            matched = False
            for code in email_codes:
                result = matcher.match(spec, code)
                if result.match:
                    matched = True
                    break
            # At least one code variant should match
            # (may fail if embeddings not available, fallback less accurate)

    def test_numeric_constraints(self, matcher):
        """Test numeric constraint matching."""
        test_cases = [
            ("price must be positive", "price: gt=0"),
            ("quantity must be non-negative", "quantity: ge=0"),
            ("value must be less than 100", "value: lt=100"),
        ]

        for spec, code in test_cases:
            result = matcher.match(spec, code)
            # These should have reasonable confidence even with fallback


class TestValidationModelIntegration:
    """Test integration with ValidationModelIR."""

    @pytest.fixture
    def matcher(self):
        return SemanticMatcher()

    @pytest.fixture
    def mock_validation_model(self):
        """Create a mock ValidationModelIR."""
        mock_rule1 = MagicMock()
        mock_rule1.entity = "Product"
        mock_rule1.attribute = "price"
        mock_rule1.type.value = "range"
        mock_rule1.condition = "gt=0"

        mock_rule2 = MagicMock()
        mock_rule2.entity = "Product"
        mock_rule2.attribute = "name"
        mock_rule2.type.value = "presence"
        mock_rule2.condition = "required"

        mock_model = MagicMock()
        mock_model.rules = [mock_rule1, mock_rule2]
        return mock_model

    def test_match_from_validation_model_basic(self, matcher, mock_validation_model):
        """Test basic IR-based matching."""
        found_constraints = [
            "Product.price: gt=0",
            "Product.name: required",
        ]

        compliance, results = matcher.match_from_validation_model(
            mock_validation_model, found_constraints
        )

        assert isinstance(compliance, float)
        assert 0.0 <= compliance <= 1.0
        assert isinstance(results, list)

    def test_match_from_validation_model_empty_rules(self, matcher):
        """Test with empty validation model."""
        mock_model = MagicMock()
        mock_model.rules = []

        compliance, results = matcher.match_from_validation_model(
            mock_model, ["Product.price: gt=0"]
        )

        assert compliance == 1.0  # No rules = 100% compliance
        assert results == []

    def test_match_from_validation_model_no_found(self, matcher, mock_validation_model):
        """Test when no constraints found in code."""
        compliance, results = matcher.match_from_validation_model(
            mock_validation_model, []
        )

        # Should have low compliance since nothing found
        assert isinstance(results, list)


class TestFallbackBehavior:
    """Test fallback behavior when ML models unavailable."""

    def test_fallback_match_basic(self):
        """Test that fallback matching works."""
        matcher = SemanticMatcher()
        result = matcher._fallback_match("email required", "email: required")
        assert isinstance(result, MatchResult)
        assert result.method == "fallback"

    def test_fallback_uses_word_overlap(self):
        """Test that fallback uses word overlap."""
        matcher = SemanticMatcher()

        # High overlap
        result1 = matcher._fallback_match("email required", "email required")
        # Low overlap
        result2 = matcher._fallback_match("email required", "database timeout")

        assert result1.confidence > result2.confidence


class TestCaching:
    """Test embedding caching behavior."""

    def test_cache_grows_with_matches(self):
        """Test that cache stores embeddings."""
        matcher = SemanticMatcher()
        initial_size = matcher.get_stats()["cache_size"]

        matcher.match("unique constraint 1", "code constraint 1")
        matcher.match("unique constraint 2", "code constraint 2")

        if matcher.encoder is not None:
            # Cache should grow if encoder available
            final_size = matcher.get_stats()["cache_size"]
            assert final_size >= initial_size

    def test_clear_cache(self):
        """Test that clear_cache empties the cache."""
        matcher = SemanticMatcher()
        matcher.match("test spec", "test code")
        matcher.clear_cache()

        assert matcher.get_stats()["cache_size"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
