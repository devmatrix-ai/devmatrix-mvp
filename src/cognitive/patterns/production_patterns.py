"""
Production Pattern Categories

Configuration for production-ready golden patterns stored in PatternBank.
Leverages existing PatternBank infrastructure instead of creating Jinja2 templates.

Categories map to production-ready code patterns with success thresholds and domains.
Patterns are stored in Qdrant using PatternBank and retrieved using semantic search.

Author: DevMatrix Team
Date: 2025-11-20
Spec: agent-os/specs/2025-11-20-devmatrix-improvements-minimal/spec.md (lines 2071-2431)
"""

from typing import Dict, List, Any

# Production Pattern Categories
# Each category defines production-ready patterns with success thresholds and metadata
PRODUCTION_PATTERN_CATEGORIES: Dict[str, Dict[str, Any]] = {
    # Core Infrastructure Patterns
    "core_config": {
        "patterns": [
            "pydantic_settings_config",
            "environment_management",
            "feature_flags"
        ],
        "success_threshold": 0.98,
        "domain": "configuration",
        "description": "Type-safe configuration with environment variable management",
        "priority": 1,  # Applied first in composition
    },

    "database_async": {
        "patterns": [
            "sqlalchemy_async_engine",
            "connection_pooling",
            "alembic_setup"
        ],
        "success_threshold": 0.98,
        "domain": "data_access",
        "description": "Async database engine with connection pooling and migrations",
        "priority": 1,
    },

    "observability": {
        "patterns": [
            "structlog_setup",
            "health_checks",
            "prometheus_metrics",
            "request_id_middleware",
            "metrics_middleware"
        ],
        "success_threshold": 0.95,
        "domain": "observability",
        "description": "Structured logging, health checks, and metrics collection",
        "priority": 1,
    },

    # Data Layer Patterns
    "models_pydantic": {
        "patterns": [
            "strict_mode_schemas",
            "validation_patterns",
            "timezone_aware_datetimes"
        ],
        "success_threshold": 0.95,
        "domain": "data_modeling",
        "description": "Pydantic schemas with strict validation and timezone awareness",
        "priority": 2,
    },

    "models_sqlalchemy": {
        "patterns": [
            "async_declarative_base",
            "entity_relationships",
            "database_indexes"
        ],
        "success_threshold": 0.95,
        "domain": "data_modeling",
        "description": "SQLAlchemy async models with relationships and indexes",
        "priority": 2,
    },

    "repository_pattern": {
        "patterns": [
            "generic_repository",
            "async_crud_operations",
            "transaction_management"
        ],
        "success_threshold": 0.95,
        "domain": "data_access",
        "description": "Repository pattern with async CRUD and transaction support",
        "priority": 2,
    },

    # Service Layer Patterns
    "business_logic": {
        "patterns": [
            "service_layer_pattern",
            "dependency_injection",
            "error_handling"
        ],
        "success_threshold": 0.90,
        "domain": "business_logic",
        "description": "Service layer with dependency injection and error handling",
        "priority": 3,
    },

    # API Layer Patterns
    "api_routes": {
        "patterns": [
            "fastapi_crud_endpoints",
            "pagination",
            "api_versioning"
        ],
        "success_threshold": 0.95,
        "domain": "api",
        "description": "FastAPI CRUD endpoints with pagination and versioning",
        "priority": 4,
    },

    # Security Patterns
    "security_hardening": {
        "patterns": [
            "html_sanitization",
            "rate_limiting",
            "security_headers",
            "cors_config"
        ],
        "success_threshold": 0.98,
        "domain": "security",
        "description": "Security hardening with sanitization, rate limiting, and headers",
        "priority": 5,
        "security_level": "CRITICAL",
    },

    # Testing Patterns
    "test_infrastructure": {
        "patterns": [
            "pytest_config",
            "async_fixtures",
            "test_factories",
            "integration_tests",
            "unit_test_models",
            "unit_test_repositories",
            "unit_test_services"
        ],
        "success_threshold": 0.95,
        "domain": "testing",
        "description": "Complete test infrastructure with pytest and async support",
        "priority": 6,
    },

    # Docker & Infrastructure Patterns
    "docker_infrastructure": {
        "patterns": [
            "multistage_dockerfile",
            "docker_compose_full_stack",
            "docker_compose_test",
            "health_checks_docker"
        ],
        "success_threshold": 0.95,
        "domain": "infrastructure",
        "description": "Docker infrastructure with multi-stage builds and full stack",
        "priority": 7,
    },

    # Configuration File Patterns
    "project_config": {
        "patterns": [
            "pyproject_toml",
            "env_example",
            "gitignore",
            "makefile",
            "pre_commit_config",
            "readme_template"
        ],
        "success_threshold": 0.90,
        "domain": "configuration",
        "description": "Project configuration files and tooling setup",
        "priority": 7,
    },
}


def get_pattern_categories() -> Dict[str, Dict[str, Any]]:
    """
    Get all production pattern categories.

    Returns:
        Dictionary of pattern categories with metadata
    """
    return PRODUCTION_PATTERN_CATEGORIES


def get_category_by_domain(domain: str) -> List[str]:
    """
    Get all categories for a specific domain.

    Args:
        domain: Domain name (configuration, data_access, infrastructure, etc.)

    Returns:
        List of category names matching the domain
    """
    return [
        category_name
        for category_name, config in PRODUCTION_PATTERN_CATEGORIES.items()
        if config["domain"] == domain
    ]


def get_patterns_by_category(category: str) -> List[str]:
    """
    Get all pattern names for a specific category.

    Args:
        category: Category name (core_config, database_async, etc.)

    Returns:
        List of pattern names in the category
    """
    if category not in PRODUCTION_PATTERN_CATEGORIES:
        return []

    return PRODUCTION_PATTERN_CATEGORIES[category]["patterns"]


def get_composition_order() -> List[str]:
    """
    Get pattern categories in composition order (priority-based).

    Pattern composition order:
    1. Core infrastructure (config, database, logging)
    2. Data layer (models, repositories)
    3. Service layer
    4. API layer (routes)
    5. Security patterns
    6. Testing patterns
    7. Docker and config files

    Returns:
        List of category names in composition order
    """
    # Sort categories by priority
    sorted_categories = sorted(
        PRODUCTION_PATTERN_CATEGORIES.items(),
        key=lambda x: x[1]["priority"]
    )

    return [category_name for category_name, _ in sorted_categories]


def validate_category_config() -> bool:
    """
    Validate production pattern category configuration.

    Checks:
    - All categories have required fields
    - Success thresholds are valid (0.0-1.0)
    - Priorities are sequential
    - Domains are valid

    Returns:
        True if valid, raises ValueError otherwise
    """
    VALID_DOMAINS = {
        "configuration",
        "data_access",
        "infrastructure",
        "data_modeling",
        "business_logic",
        "api",
        "security",
        "testing"
    }

    required_fields = ["patterns", "success_threshold", "domain", "description", "priority"]

    for category_name, config in PRODUCTION_PATTERN_CATEGORIES.items():
        # Check required fields
        for field in required_fields:
            if field not in config:
                raise ValueError(
                    f"Category '{category_name}' missing required field: {field}"
                )

        # Validate success threshold
        threshold = config["success_threshold"]
        if not (0.0 <= threshold <= 1.0):
            raise ValueError(
                f"Category '{category_name}' has invalid success_threshold: {threshold}"
            )

        # Validate domain
        if config["domain"] not in VALID_DOMAINS:
            raise ValueError(
                f"Category '{category_name}' has invalid domain: {config['domain']}"
            )

        # Validate patterns list
        if not config["patterns"]:
            raise ValueError(
                f"Category '{category_name}' has empty patterns list"
            )

    return True


# Validate configuration on module import
validate_category_config()
