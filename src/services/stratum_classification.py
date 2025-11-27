"""
Stratum Classification for Code Generation

Defines the complexity strata for the stratified generation architecture:
- TEMPLATE: Static, pre-tested boilerplate
- AST: Deterministic IR→Code transforms
- LLM: Complex business logic only

Each generator function should be tagged with its correct stratum.

Phase 0.5.1: Added AtomKind enum for explicit stratum classification.
"""

from enum import Enum
from typing import Dict, Set, List, Optional
from dataclasses import dataclass
import re


class Stratum(str, Enum):
    """Code generation complexity strata."""
    TEMPLATE = "template"  # Static boilerplate, never changes
    AST = "ast"            # Deterministic from IR, no LLM
    LLM = "llm"            # Complex business logic, needs LLM
    QA = "qa"              # Validation layer, post-generation


class AtomKind(str, Enum):
    """
    Explicit classification of code generation atoms.

    Phase 0.5.1: Each AtomKind maps deterministically to a Stratum.
    This is the SINGLE SOURCE OF TRUTH for stratum routing.
    """
    # TEMPLATE stratum - static infrastructure, never changes
    INFRA = "infra"                        # docker-compose, Dockerfile, etc.
    HEALTH = "health"                      # health.py endpoints
    BASE_MODELS = "base_models"            # base.py, mixins
    PROJECT_STRUCTURE = "project_structure" # folder structure, __init__.py
    CONFIG = "config"                      # config.py, settings
    REQUIREMENTS = "requirements"          # requirements.txt, pyproject.toml
    ALEMBIC_INI = "alembic_ini"           # alembic.ini
    OBSERVABILITY = "observability"        # prometheus.yml, grafana configs

    # AST stratum - structured, rule-based generation
    ENTITY_MODEL = "entity_model"          # SQLAlchemy models
    PYDANTIC_SCHEMA = "pydantic_schema"    # Pydantic schemas (Create/Update/Read)
    CRUD_ENDPOINT = "crud_endpoint"        # Standard CRUD routes
    MIGRATION = "migration"                # Alembic migrations
    REPOSITORY = "repository"              # Repository pattern classes
    DATABASE_UTILS = "database_utils"      # database.py, session management

    # LLM stratum - generative, requires semantic understanding
    FLOW_SERVICE = "flow_service"          # Business logic flows
    CUSTOM_ENDPOINT = "custom_endpoint"    # Non-CRUD endpoints
    BUSINESS_RULE = "business_rule"        # Complex validation rules
    STATE_MACHINE = "state_machine"        # State transition logic
    INTEGRATION = "integration"            # External API integrations


# Deterministic mapping: AtomKind -> Stratum (SINGLE SOURCE OF TRUTH)
STRATUM_BY_KIND: Dict[AtomKind, Stratum] = {
    # TEMPLATE stratum
    AtomKind.INFRA: Stratum.TEMPLATE,
    AtomKind.HEALTH: Stratum.TEMPLATE,
    AtomKind.BASE_MODELS: Stratum.TEMPLATE,
    AtomKind.PROJECT_STRUCTURE: Stratum.TEMPLATE,
    AtomKind.CONFIG: Stratum.TEMPLATE,
    AtomKind.REQUIREMENTS: Stratum.TEMPLATE,
    AtomKind.ALEMBIC_INI: Stratum.TEMPLATE,
    AtomKind.OBSERVABILITY: Stratum.TEMPLATE,

    # AST stratum
    AtomKind.ENTITY_MODEL: Stratum.AST,
    AtomKind.PYDANTIC_SCHEMA: Stratum.AST,
    AtomKind.CRUD_ENDPOINT: Stratum.AST,
    AtomKind.MIGRATION: Stratum.AST,
    AtomKind.REPOSITORY: Stratum.AST,
    AtomKind.DATABASE_UTILS: Stratum.AST,

    # LLM stratum
    AtomKind.FLOW_SERVICE: Stratum.LLM,
    AtomKind.CUSTOM_ENDPOINT: Stratum.LLM,
    AtomKind.BUSINESS_RULE: Stratum.LLM,
    AtomKind.STATE_MACHINE: Stratum.LLM,
    AtomKind.INTEGRATION: Stratum.LLM,
}


def get_stratum_by_kind(kind: AtomKind) -> Stratum:
    """Get the stratum for an AtomKind. Always returns a valid stratum."""
    return STRATUM_BY_KIND.get(kind, Stratum.LLM)


@dataclass
class StratumClassification:
    """Classification result for a code generation task."""
    stratum: Stratum
    reason: str
    file_patterns: List[str]  # Which files this applies to


# =============================================================================
# TEMPLATE STRATUM - Static boilerplate, pre-tested, immutable
# =============================================================================

TEMPLATE_GENERATORS: Dict[str, StratumClassification] = {
    # Infrastructure
    "docker-compose.yml": StratumClassification(
        stratum=Stratum.TEMPLATE,
        reason="Static infrastructure, never changes per project",
        file_patterns=["docker-compose.yml"]
    ),
    "Dockerfile": StratumClassification(
        stratum=Stratum.TEMPLATE,
        reason="Static container config",
        file_patterns=["Dockerfile"]
    ),
    "prometheus.yml": StratumClassification(
        stratum=Stratum.TEMPLATE,
        reason="Static observability config",
        file_patterns=["prometheus.yml", "grafana/*"]
    ),

    # Config
    "requirements.txt": StratumClassification(
        stratum=Stratum.TEMPLATE,
        reason="Standard dependencies list",
        file_patterns=["requirements.txt"]
    ),
    "pyproject.toml": StratumClassification(
        stratum=Stratum.TEMPLATE,
        reason="Standard project config",
        file_patterns=["pyproject.toml"]
    ),
    ".env.example": StratumClassification(
        stratum=Stratum.TEMPLATE,
        reason="Static environment template",
        file_patterns=[".env.example", ".env"]
    ),
    "alembic.ini": StratumClassification(
        stratum=Stratum.TEMPLATE,
        reason="Static alembic config",
        file_patterns=["alembic.ini"]
    ),

    # Core
    "core/config.py": StratumClassification(
        stratum=Stratum.TEMPLATE,
        reason="Standard settings pattern",
        file_patterns=["src/core/config.py", "core/config.py"]
    ),
    "core/database.py": StratumClassification(
        stratum=Stratum.TEMPLATE,
        reason="Standard async SQLAlchemy setup",
        file_patterns=["src/core/database.py", "core/database.py"]
    ),

    # Health endpoints
    "routes/health.py": StratumClassification(
        stratum=Stratum.TEMPLATE,
        reason="Standard health check pattern",
        file_patterns=["src/api/routes/health.py", "src/routes/health.py"]
    ),

    # Main app setup
    "main.py": StratumClassification(
        stratum=Stratum.TEMPLATE,
        reason="Standard FastAPI app setup",
        file_patterns=["src/main.py", "main.py"]
    ),

    # Base repository
    "repositories/base.py": StratumClassification(
        stratum=Stratum.TEMPLATE,
        reason="Generic CRUD repository pattern",
        file_patterns=["src/repositories/base.py"]
    ),
}


# =============================================================================
# AST STRATUM - Deterministic from IR, no LLM
# =============================================================================

AST_GENERATORS: Dict[str, StratumClassification] = {
    # Models
    "models/entities.py": StratumClassification(
        stratum=Stratum.AST,
        reason="SQLAlchemy models from DomainModelIR.entities",
        file_patterns=["src/models/entities.py"]
    ),
    "models/schemas.py": StratumClassification(
        stratum=Stratum.AST,
        reason="Pydantic schemas from APIModelIR.schemas",
        file_patterns=["src/models/schemas.py"]
    ),

    # Repositories
    "repositories/*_repository.py": StratumClassification(
        stratum=Stratum.AST,
        reason="Entity-specific repos from DomainModelIR",
        file_patterns=["src/repositories/*_repository.py"]
    ),

    # Services (CRUD only)
    "services/*_service.py": StratumClassification(
        stratum=Stratum.AST,
        reason="Standard service pattern from entities",
        file_patterns=["src/services/*_service.py"]
    ),

    # Routes (CRUD only)
    "routes/*_routes.py": StratumClassification(
        stratum=Stratum.AST,
        reason="CRUD endpoints from APIModelIR.endpoints",
        file_patterns=["src/api/routes/*.py", "src/routes/*.py"]
    ),

    # Migrations
    "alembic/versions/*.py": StratumClassification(
        stratum=Stratum.AST,
        reason="Alembic migrations from DomainModelIR",
        file_patterns=["alembic/versions/*.py"]
    ),
}


# =============================================================================
# LLM STRATUM - Complex business logic only
# =============================================================================

LLM_GENERATORS: Dict[str, StratumClassification] = {
    # Business flow implementations
    "services/*_flow_methods.py": StratumClassification(
        stratum=Stratum.LLM,
        reason="Multi-entity workflow implementations",
        file_patterns=["src/services/*_flow_methods.py"]
    ),

    # Complex business rules
    "services/*_business_rules.py": StratumClassification(
        stratum=Stratum.LLM,
        reason="Complex invariant handlers",
        file_patterns=["src/services/*_business_rules.py"]
    ),

    # Custom (non-CRUD) endpoints
    "routes/*_custom.py": StratumClassification(
        stratum=Stratum.LLM,
        reason="Non-standard endpoints with business logic",
        file_patterns=["src/routes/*_custom.py"]
    ),

    # Repair patches
    "repair_patches/*.py": StratumClassification(
        stratum=Stratum.LLM,
        reason="IR-guided localized fixes",
        file_patterns=["repair_patches/*.py"]
    ),
}


# =============================================================================
# LLM CONSTRAINTS
# =============================================================================

# Files that LLM is NEVER allowed to write
LLM_FORBIDDEN_PATTERNS: Set[str] = {
    "docker-compose.yml",
    "Dockerfile",
    "prometheus.yml",
    "grafana/*",
    "requirements.txt",
    "pyproject.toml",
    ".env*",
    "alembic.ini",
    "alembic/env.py",
    "src/core/config.py",
    "src/core/database.py",
    "src/main.py",
    "src/models/base.py",
    "src/repositories/base.py",
    "src/api/routes/health.py",
}

# Files where LLM is allowed (with validation)
LLM_ALLOWED_PATTERNS: Set[str] = {
    "src/services/*_flow_methods.py",
    "src/services/*_business_rules.py",
    "src/routes/*_custom.py",
    "repair_patches/*.py",
}


def classify_file(file_path: str) -> Stratum:
    """
    Classify a file path into its correct stratum.

    Args:
        file_path: Path to the file (relative to project root)

    Returns:
        Stratum enum value
    """
    import fnmatch

    # Check TEMPLATE first (highest priority - never let LLM touch)
    for pattern_name, classification in TEMPLATE_GENERATORS.items():
        for pattern in classification.file_patterns:
            if fnmatch.fnmatch(file_path, pattern) or fnmatch.fnmatch(file_path, f"*/{pattern}"):
                return Stratum.TEMPLATE

    # Check LLM patterns (explicit business logic)
    for pattern_name, classification in LLM_GENERATORS.items():
        for pattern in classification.file_patterns:
            if fnmatch.fnmatch(file_path, pattern) or fnmatch.fnmatch(file_path, f"*/{pattern}"):
                return Stratum.LLM

    # Check AST patterns (deterministic from IR)
    for pattern_name, classification in AST_GENERATORS.items():
        for pattern in classification.file_patterns:
            if fnmatch.fnmatch(file_path, pattern) or fnmatch.fnmatch(file_path, f"*/{pattern}"):
                return Stratum.AST

    # Default: AST (prefer deterministic)
    return Stratum.AST


def is_llm_allowed(file_path: str) -> bool:
    """
    Check if LLM is allowed to generate/modify this file.

    Args:
        file_path: Path to check

    Returns:
        True if LLM can write to this file
    """
    import fnmatch

    # Check forbidden patterns first
    for pattern in LLM_FORBIDDEN_PATTERNS:
        if fnmatch.fnmatch(file_path, pattern) or fnmatch.fnmatch(file_path, f"*/{pattern}"):
            return False

    # Check allowed patterns
    for pattern in LLM_ALLOWED_PATTERNS:
        if fnmatch.fnmatch(file_path, pattern) or fnmatch.fnmatch(file_path, f"*/{pattern}"):
            return True

    # Default: not allowed (conservative)
    return False


def get_stratum_for_generator(generator_name: str) -> Stratum:
    """
    Get the correct stratum for a generator function.

    Maps generator function names to their strata based on what they produce.

    Args:
        generator_name: Name of the generator function

    Returns:
        Stratum enum value
    """
    # TEMPLATE generators
    TEMPLATE_FUNCTIONS = {
        "generate_config",
        "generate_docker_compose",
        "generate_dockerfile",
        "generate_requirements",
        "generate_health_routes",
        "generate_main_app",
        "generate_database_config",
        "generate_base_repository",
        "generate_alembic_env",
        "generate_alembic_ini",
        "generate_prometheus_config",
        "generate_grafana_dashboards",
    }

    # AST generators (deterministic from IR)
    AST_FUNCTIONS = {
        "generate_entities",
        "generate_schemas",
        "generate_repositories",
        "generate_services",
        "generate_routes",
        "generate_initial_migration",
        "generate_service_method",
        "_generate_entity_class",
        "_generate_schema_class",
        "_generate_repository_class",
        "_generate_crud_routes",
    }

    # LLM generators
    LLM_FUNCTIONS = {
        "generate_business_flows",
        "generate_complex_invariants",
        "generate_custom_endpoints",
        "repair_with_llm",
    }

    if generator_name in TEMPLATE_FUNCTIONS:
        return Stratum.TEMPLATE
    elif generator_name in AST_FUNCTIONS:
        return Stratum.AST
    elif generator_name in LLM_FUNCTIONS:
        return Stratum.LLM
    else:
        # Default: AST (prefer deterministic)
        return Stratum.AST


# =============================================================================
# FUNCTION CLASSIFICATION MAP
# =============================================================================
# Maps existing generator functions to their correct stratum

GENERATOR_STRATUM_MAP: Dict[str, Stratum] = {
    # production_code_generators.py
    "validate_python_syntax": Stratum.TEMPLATE,  # Utility, not generation
    "generate_entities": Stratum.AST,            # SQLAlchemy from IR
    "generate_config": Stratum.TEMPLATE,         # Static config
    "generate_schemas": Stratum.AST,             # Pydantic from IR
    "generate_service_method": Stratum.AST,      # Service from entity
    "generate_initial_migration": Stratum.AST,   # Alembic from IR
    "validate_generated_files": Stratum.TEMPLATE,  # Utility
    "get_validation_summary": Stratum.TEMPLATE,    # Utility

    # code_generation_service.py
    "_compose_patterns": Stratum.TEMPLATE,       # Pattern composition
    "_generate_with_llm_fallback": Stratum.LLM,  # LLM fallback
    "generate_from_application_ir": Stratum.AST, # IR-driven generation

    # Helpers (should be classified based on usage)
    "_get_enforcement_for_field": Stratum.AST,
    "_should_exclude_from_create": Stratum.AST,
    "_should_exclude_from_update": Stratum.AST,
    "_infer_sql_type": Stratum.AST,
}
