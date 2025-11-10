"""
Atomic Validator - MGE V2 Integration

Integrates real atomic validation from src.validation.atomic_validator
with MGE V2 execution pipeline.

Author: DevMatrix Team
Date: 2025-11-10
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import logging

from .models import ValidationIssue, ValidationSeverity


logger = logging.getLogger(__name__)


@dataclass
class AtomicValidationResult:
    """Result of atomic unit validation."""
    passed: bool
    issues: List[ValidationIssue]
    metrics: Dict[str, Any]


class AtomicValidator:
    """
    Atomic unit validator for MGE V2.

    Wraps the comprehensive atomic validator from src.validation.atomic_validator
    and adapts it for MGE V2's execution pipeline.
    """

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize atomic validator.

        Args:
            db: Optional database session for atom lookup
        """
        self.db = db
        self._real_validator = None

        # Initialize real validator if db is available
        if db:
            try:
                from src.validation.atomic_validator import AtomicValidator as RealValidator
                self._real_validator = RealValidator(db=db)
                logger.info("Real AtomicValidator initialized for MGE V2")
            except ImportError as e:
                logger.warning(f"Could not import real validator: {e}. Using basic validation.")

    async def validate(self, atom_spec) -> AtomicValidationResult:
        """
        Validate atomic unit.

        Args:
            atom_spec: Atomic unit to validate (AtomicUnit model)

        Returns:
            Validation result with issues and metrics
        """
        # If we have a real validator and the atom is persisted, use it
        if self._real_validator and hasattr(atom_spec, 'atom_id') and atom_spec.atom_id:
            try:
                # Use real validator
                result = self._real_validator.validate_atom(atom_spec.atom_id)

                # Convert to MGE V2 format
                issues = [
                    ValidationIssue(
                        severity=self._map_severity(issue.level),
                        category=issue.category,
                        message=issue.message,
                        line=issue.line or 0,
                        suggestion=issue.suggestion
                    )
                    for issue in result.issues
                ]

                return AtomicValidationResult(
                    passed=result.is_valid,
                    issues=issues,
                    metrics={
                        "validation_score": result.validation_score,
                        "syntax_valid": result.syntax_valid,
                        "semantic_valid": result.semantic_valid,
                        "atomicity_valid": result.atomicity_valid,
                        "type_safe": result.type_safe,
                        "runtime_safe": result.runtime_safe,
                        "errors_count": len(result.errors),
                        "warnings_count": len(result.warnings)
                    }
                )

            except Exception as e:
                logger.error(f"Real validation failed: {e}. Falling back to basic validation.")

        # Fallback: Basic validation (syntax check only)
        return await self._basic_validation(atom_spec)

    async def _basic_validation(self, atom_spec) -> AtomicValidationResult:
        """
        Basic validation when real validator is unavailable.

        Performs simple checks:
        - Code is not empty
        - Code has reasonable length
        - Basic syntax validation (if possible)

        Args:
            atom_spec: Atomic unit to validate

        Returns:
            Basic validation result
        """
        issues = []

        # Get code to validate
        code = getattr(atom_spec, 'code', None) or getattr(atom_spec, 'code_to_generate', '')

        # Check code is not empty
        if not code or len(code.strip()) == 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="completeness",
                message="Code is empty",
                line=0,
                suggestion="Generate code for this atom"
            ))

        # Check code length is reasonable (not too long for an atom)
        lines = code.split('\n')
        if len(lines) > 50:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="atomicity",
                message=f"Code has {len(lines)} lines (exceeds recommended 10-15 LOC for atoms)",
                line=0,
                suggestion="Consider breaking into smaller atoms"
            ))

        # Basic syntax validation (Python only)
        language = getattr(atom_spec, 'language', '').lower()
        if language == 'python' and code:
            try:
                import ast
                ast.parse(code)
            except SyntaxError as e:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="syntax",
                    message=f"Syntax error: {e.msg}",
                    line=e.lineno or 0,
                    suggestion="Fix syntax error"
                ))

        # Determine if passed
        error_issues = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        passed = len(error_issues) == 0

        return AtomicValidationResult(
            passed=passed,
            issues=issues,
            metrics={
                "validation_score": 1.0 if passed else 0.5,
                "validation_type": "basic",
                "code_length": len(code),
                "lines_of_code": len(lines)
            }
        )

    def _map_severity(self, level: str) -> ValidationSeverity:
        """Map old validation level to new severity enum."""
        level_lower = level.lower()
        if level_lower == 'error':
            return ValidationSeverity.ERROR
        elif level_lower == 'warning':
            return ValidationSeverity.WARNING
        elif level_lower == 'info':
            return ValidationSeverity.INFO
        else:
            return ValidationSeverity.WARNING
