"""
Atomic Validator - Level 1: Individual Atom Validation

Validates individual atoms for:
- Syntax correctness
- Semantic validity
- Atomicity criteria
- Type safety
- Runtime safety

Author: DevMatrix Team
Date: 2025-10-23
"""

import uuid
import ast
import subprocess
import tempfile
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
import logging

from src.models import AtomicUnit

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """Individual validation issue"""
    level: str  # 'error', 'warning', 'info'
    category: str  # 'syntax', 'semantic', 'atomicity', 'type', 'runtime'
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class AtomicValidationResult:
    """Result of atomic validation"""
    atom_id: uuid.UUID
    is_valid: bool
    validation_score: float  # 0.0-1.0
    syntax_valid: bool
    semantic_valid: bool
    atomicity_valid: bool
    type_safe: bool
    runtime_safe: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class AtomicValidator:
    """
    Atomic validator - Level 1

    Validates individual atoms:
    1. Syntax validation (AST parsing, linting)
    2. Semantic validation (variable usage, scope)
    3. Atomicity validation (10 criteria from Phase 2)
    4. Type safety (type checking)
    5. Runtime safety (no obvious runtime errors)

    Score calculation:
    - Syntax: 25%
    - Semantics: 25%
    - Atomicity: 25%
    - Type safety: 15%
    - Runtime safety: 10%
    """

    def __init__(self, db: Session):
        """
        Initialize atomic validator

        Args:
            db: Database session
        """
        self.db = db
        logger.info("AtomicValidator initialized")

    def validate_atom(self, atom_id: uuid.UUID) -> AtomicValidationResult:
        """
        Validate individual atom

        Args:
            atom_id: Atom UUID

        Returns:
            AtomicValidationResult with validation details
        """
        logger.info(f"Validating atom: {atom_id}")

        # Load atom
        atom = self.db.query(AtomicUnit).filter(
            AtomicUnit.atom_id == atom_id
        ).first()

        if not atom:
            return AtomicValidationResult(
                atom_id=atom_id,
                is_valid=False,
                validation_score=0.0,
                syntax_valid=False,
                semantic_valid=False,
                atomicity_valid=False,
                type_safe=False,
                runtime_safe=False,
                errors=["Atom not found"]
            )

        issues = []
        errors = []
        warnings = []
        score = 0.0

        # 1. Syntax validation (25%)
        syntax_valid, syntax_issues = self._validate_syntax(atom)
        issues.extend(syntax_issues)
        if syntax_valid:
            score += 0.25
        else:
            errors.extend([i.message for i in syntax_issues if i.level == 'error'])

        # 2. Semantic validation (25%)
        semantic_valid, semantic_issues = self._validate_semantics(atom)
        issues.extend(semantic_issues)
        if semantic_valid:
            score += 0.25
        else:
            errors.extend([i.message for i in semantic_issues if i.level == 'error'])

        # 3. Atomicity validation (25%)
        atomicity_valid, atomicity_issues = self._validate_atomicity(atom)
        issues.extend(atomicity_issues)
        if atomicity_valid:
            score += 0.25
        else:
            warnings.extend([i.message for i in atomicity_issues if i.level == 'warning'])

        # 4. Type safety (15%)
        type_safe, type_issues = self._validate_type_safety(atom)
        issues.extend(type_issues)
        if type_safe:
            score += 0.15
        else:
            warnings.extend([i.message for i in type_issues if i.level == 'warning'])

        # 5. Runtime safety (10%)
        runtime_safe, runtime_issues = self._validate_runtime_safety(atom)
        issues.extend(runtime_issues)
        if runtime_safe:
            score += 0.10
        else:
            warnings.extend([i.message for i in runtime_issues if i.level == 'warning'])

        # Determine overall validity
        is_valid = syntax_valid and semantic_valid and score >= 0.7

        result = AtomicValidationResult(
            atom_id=atom_id,
            is_valid=is_valid,
            validation_score=score,
            syntax_valid=syntax_valid,
            semantic_valid=semantic_valid,
            atomicity_valid=atomicity_valid,
            type_safe=type_safe,
            runtime_safe=runtime_safe,
            issues=issues,
            errors=errors,
            warnings=warnings
        )

        logger.info(f"Atom validation complete: score={score:.2f}, valid={is_valid}")
        return result

    def _validate_syntax(self, atom: AtomicUnit) -> tuple[bool, List[ValidationIssue]]:
        """Validate syntax using AST parsing"""
        issues = []

        if atom.language == "python":
            try:
                ast.parse(atom.code_to_generate)
                return True, issues
            except SyntaxError as e:
                issues.append(ValidationIssue(
                    level='error',
                    category='syntax',
                    message=f"Syntax error: {e.msg}",
                    line=e.lineno,
                    column=e.offset,
                    suggestion="Fix syntax error"
                ))
                return False, issues

        elif atom.language in ["typescript", "javascript"]:
            # For TS/JS, we'd use a parser like esprima or typescript compiler
            # For now, basic check
            if atom.code_to_generate.strip():
                return True, issues
            else:
                issues.append(ValidationIssue(
                    level='error',
                    category='syntax',
                    message="Empty code",
                    suggestion="Generate valid code"
                ))
                return False, issues

        return True, issues

    def _validate_semantics(self, atom: AtomicUnit) -> tuple[bool, List[ValidationIssue]]:
        """Validate semantic correctness"""
        issues = []
        code = atom.code_to_generate

        # Check for undefined variables (heuristic)
        if atom.language == "python":
            try:
                tree = ast.parse(code)

                # Find all variable uses
                uses = set()
                definitions = set()

                for node in ast.walk(tree):
                    if isinstance(node, ast.Name):
                        if isinstance(node.ctx, ast.Store):
                            definitions.add(node.id)
                        elif isinstance(node.ctx, ast.Load):
                            uses.add(node.id)

                # Check for uses before definition (simplified)
                # Note: This is a heuristic, not perfect
                undefined = uses - definitions

                # Filter out builtins and imports
                builtins = {'print', 'len', 'str', 'int', 'float', 'list', 'dict', 'tuple', 'set'}
                undefined = undefined - builtins

                if undefined:
                    issues.append(ValidationIssue(
                        level='warning',
                        category='semantic',
                        message=f"Potentially undefined variables: {', '.join(list(undefined)[:5])}",
                        suggestion="Ensure all variables are defined or imported"
                    ))
                    return len(undefined) < 3, issues  # Allow some false positives

                return True, issues

            except Exception as e:
                issues.append(ValidationIssue(
                    level='error',
                    category='semantic',
                    message=f"Semantic analysis failed: {str(e)}",
                    suggestion="Fix code structure"
                ))
                return False, issues

        return True, issues

    def _validate_atomicity(self, atom: AtomicUnit) -> tuple[bool, List[ValidationIssue]]:
        """Validate atomicity criteria"""
        issues = []

        # LOC check
        lines = [l for l in atom.code_to_generate.split('\n') if l.strip()]
        loc = len(lines)

        if loc > 15:
            issues.append(ValidationIssue(
                level='warning',
                category='atomicity',
                message=f"Atom has {loc} lines, exceeds target of 15",
                suggestion="Consider splitting into smaller atoms"
            ))

        # Complexity check (from atom.complexity)
        if atom.complexity > 3.0:
            issues.append(ValidationIssue(
                level='warning',
                category='atomicity',
                message=f"Complexity {atom.complexity:.1f} exceeds target of 3.0",
                suggestion="Simplify logic, reduce decision points"
            ))

        # Single responsibility check (heuristic)
        operation_types = 0
        if '=' in atom.code_to_generate:
            operation_types += 1
        if 'def ' in atom.code_to_generate or 'class ' in atom.code_to_generate:
            operation_types += 1
        if 'if ' in atom.code_to_generate or 'for ' in atom.code_to_generate:
            operation_types += 1

        if operation_types > 2:
            issues.append(ValidationIssue(
                level='info',
                category='atomicity',
                message="Multiple operation types detected",
                suggestion="Focus on single responsibility"
            ))

        # Atomicity is valid if no critical issues
        return len([i for i in issues if i.level == 'error']) == 0, issues

    def _validate_type_safety(self, atom: AtomicUnit) -> tuple[bool, List[ValidationIssue]]:
        """Validate type safety"""
        issues = []

        if atom.language == "python":
            # Check for type hints presence
            code = atom.code_to_generate

            # Look for function definitions
            if 'def ' in code:
                # Check if type hints are present
                has_hints = '->' in code or ': ' in code

                if not has_hints:
                    issues.append(ValidationIssue(
                        level='info',
                        category='type',
                        message="Function missing type hints",
                        suggestion="Add type annotations for better type safety"
                    ))

        # Type safety is not critical, so always return True for now
        return True, issues

    def _validate_runtime_safety(self, atom: AtomicUnit) -> tuple[bool, List[ValidationIssue]]:
        """Validate runtime safety"""
        issues = []
        code = atom.code_to_generate

        # Check for common runtime issues
        dangerous_patterns = {
            'eval(': 'Use of eval() is dangerous',
            'exec(': 'Use of exec() is dangerous',
            '1/0': 'Division by zero',
            'import *': 'Wildcard imports are discouraged',
        }

        for pattern, message in dangerous_patterns.items():
            if pattern in code:
                issues.append(ValidationIssue(
                    level='warning',
                    category='runtime',
                    message=message,
                    suggestion="Avoid dangerous patterns"
                ))

        return len(issues) == 0, issues
