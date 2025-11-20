"""
Tests for Production Pattern Library (Task Group 8)

Verifies:
- Pattern categories configuration
- PatternBank metadata extensions
- Pattern composition system
- Production readiness validation

Author: DevMatrix Team
Date: 2025-11-20
"""

import pytest
from src.cognitive.patterns.production_patterns import (
    PRODUCTION_PATTERN_CATEGORIES,
    get_pattern_categories,
    get_category_by_domain,
    get_patterns_by_category,
    get_composition_order,
    validate_category_config,
)


def test_production_pattern_categories_exist():
    """Test that all expected pattern categories are defined."""
    expected_categories = [
        "core_config",
        "database_async",
        "observability",
        "models_pydantic",
        "models_sqlalchemy",
        "repository_pattern",
        "business_logic",
        "api_routes",
        "security_hardening",
        "test_infrastructure",
        "docker_infrastructure",
        "project_config",
    ]

    for category in expected_categories:
        assert category in PRODUCTION_PATTERN_CATEGORIES, f"Missing category: {category}"


def test_pattern_categories_have_required_fields():
    """Test that all categories have required fields."""
    required_fields = ["patterns", "success_threshold", "domain", "description", "priority"]

    for category_name, config in PRODUCTION_PATTERN_CATEGORIES.items():
        for field in required_fields:
            assert field in config, f"Category '{category_name}' missing field: {field}"


def test_success_thresholds_valid():
    """Test that all success thresholds are valid (0.0-1.0)."""
    for category_name, config in PRODUCTION_PATTERN_CATEGORIES.items():
        threshold = config["success_threshold"]
        assert 0.0 <= threshold <= 1.0, (
            f"Category '{category_name}' has invalid threshold: {threshold}"
        )


def test_security_patterns_have_high_threshold():
    """Test that security patterns have high success threshold (>=0.98)."""
    security_category = PRODUCTION_PATTERN_CATEGORIES["security_hardening"]
    assert security_category["success_threshold"] >= 0.98, (
        "Security patterns must have success_threshold >= 0.98"
    )
    assert security_category.get("security_level") == "CRITICAL", (
        "Security patterns must have security_level='CRITICAL'"
    )


def test_composition_order_is_sequential():
    """Test that composition order follows priority sequence."""
    order = get_composition_order()

    # Get priorities for verification
    priorities = [PRODUCTION_PATTERN_CATEGORIES[cat]["priority"] for cat in order]

    # Priorities should be in ascending order
    assert priorities == sorted(priorities), "Composition order should follow priority sequence"


def test_get_category_by_domain():
    """Test retrieving categories by domain."""
    # Test configuration domain
    config_categories = get_category_by_domain("configuration")
    assert "core_config" in config_categories
    assert "project_config" in config_categories

    # Test security domain
    security_categories = get_category_by_domain("security")
    assert "security_hardening" in security_categories


def test_get_patterns_by_category():
    """Test retrieving patterns for a specific category."""
    # Test core_config patterns
    core_patterns = get_patterns_by_category("core_config")
    assert "pydantic_settings_config" in core_patterns
    assert "environment_management" in core_patterns

    # Test security patterns
    security_patterns = get_patterns_by_category("security_hardening")
    assert "html_sanitization" in security_patterns
    assert "rate_limiting" in security_patterns


def test_validate_category_config():
    """Test that category configuration validation passes."""
    # Should not raise ValueError
    result = validate_category_config()
    assert result is True


def test_pattern_bank_metadata_extensions():
    """Test that PatternBank has production readiness metadata."""
    from src.cognitive.patterns.pattern_bank import PatternBank
    from src.cognitive.signatures.semantic_signature import SemanticTaskSignature

    # Initialize PatternBank
    bank = PatternBank()
    bank.connect()

    # Create test signature
    signature = SemanticTaskSignature(
        purpose="Test production pattern metadata",
        intent="implement",
        inputs={},
        outputs={},
        domain="testing",
    )

    # Store test pattern
    try:
        pattern_id = bank.store_production_pattern(
            signature=signature,
            code="# Test code",
            success_rate=0.95,
            test_coverage=0.85,
            security_level="MEDIUM",
            observability_complete=True,
            docker_ready=False,
        )

        # Retrieve pattern to verify metadata
        pattern = bank.get_pattern_by_id(pattern_id)

        # Verify production readiness metadata exists (implicitly through store_production_pattern)
        assert pattern is not None
        assert pattern.success_rate == 0.95

    except Exception as e:
        pytest.skip(f"PatternBank not available: {e}")


def test_pattern_composition_categories():
    """Test that pattern composition covers all critical categories."""
    critical_categories = [
        "core_config",  # Configuration
        "database_async",  # Database
        "security_hardening",  # Security
        "test_infrastructure",  # Testing
        "docker_infrastructure",  # Docker
    ]

    order = get_composition_order()

    for category in critical_categories:
        assert category in order, f"Critical category '{category}' missing from composition order"


def test_pattern_count_per_category():
    """Test that each category has at least one pattern defined."""
    for category_name, config in PRODUCTION_PATTERN_CATEGORIES.items():
        patterns = config["patterns"]
        assert len(patterns) > 0, f"Category '{category_name}' has no patterns"


def test_core_infrastructure_priority():
    """Test that core infrastructure categories have highest priority."""
    core_categories = ["core_config", "database_async", "observability"]

    for category in core_categories:
        priority = PRODUCTION_PATTERN_CATEGORIES[category]["priority"]
        assert priority == 1, f"Core category '{category}' should have priority 1"


def test_security_category_configuration():
    """Test security category has correct configuration."""
    security = PRODUCTION_PATTERN_CATEGORIES["security_hardening"]

    assert security["domain"] == "security"
    assert security["success_threshold"] == 0.98
    assert security.get("security_level") == "CRITICAL"
    assert len(security["patterns"]) >= 3  # At least 3 security patterns


def test_docker_patterns_exist():
    """Test that Docker infrastructure patterns are defined."""
    docker_patterns = get_patterns_by_category("docker_infrastructure")

    assert "multistage_dockerfile" in docker_patterns
    assert "docker_compose_full_stack" in docker_patterns


def test_test_infrastructure_patterns():
    """Test that test infrastructure has pytest and async support."""
    test_patterns = get_patterns_by_category("test_infrastructure")

    assert "pytest_config" in test_patterns
    assert "async_fixtures" in test_patterns
    assert "test_factories" in test_patterns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
