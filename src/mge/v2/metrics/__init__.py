"""
MGE V2 Metrics Module

Precision scoring and requirement mapping for MGE V2.

Components:
- PrecisionScorer: Calculate composite precision scores (50% Spec + 30% Integration + 20% Validation)
- RequirementMapper: Map requirements to acceptance tests and validate coverage
"""

from .precision_scorer import (
    PrecisionScorer,
    PrecisionScore,
    RequirementPriority,
    ValidationLevel,
    RequirementResult,
    IntegrationResult,
    ValidationResult
)
from .requirement_mapper import (
    RequirementMapper,
    Requirement,
    AcceptanceTest
)

__all__ = [
    "PrecisionScorer",
    "PrecisionScore",
    "RequirementPriority",
    "ValidationLevel",
    "RequirementResult",
    "IntegrationResult",
    "ValidationResult",
    "RequirementMapper",
    "Requirement",
    "AcceptanceTest",
]
