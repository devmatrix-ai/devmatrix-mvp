"""
Atomic Validator (Stub)

Temporary validator for testing. Real implementation from Phase 2.
"""

from dataclasses import dataclass
from typing import List, Dict, Any

from .models import ValidationIssue


@dataclass
class AtomicValidationResult:
    """Result of atomic unit validation."""
    passed: bool
    issues: List[ValidationIssue]
    metrics: Dict[str, Any]


class AtomicValidator:
    """
    Atomic unit validator (stub).

    Real implementation should come from Phase 2 validation framework.
    """

    async def validate(self, atom_spec) -> AtomicValidationResult:
        """
        Validate atomic unit (stub).

        Args:
            atom_spec: Atomic unit to validate

        Returns:
            Validation result
        """
        # Stub implementation - always pass
        return AtomicValidationResult(
            passed=True,
            issues=[],
            metrics={}
        )
