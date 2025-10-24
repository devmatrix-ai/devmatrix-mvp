"""
Atomicity Validator - 10-criteria validation

Validates atomic units against 10 atomicity criteria.

10 Atomicity Criteria:
1. LOC ≤ 15
2. Complexity < 3.0
3. Single responsibility
4. Clear boundaries
5. Independence from siblings
6. Complete context
7. Testable
8. Deterministic
9. No side effects (prefer)
10. Clear input/output

Target: Atomicity score ≥ 0.8

Author: DevMatrix Team
Date: 2025-10-23
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging
import re

from .decomposer import AtomCandidate
from .context_injector import AtomContext

logger = logging.getLogger(__name__)


@dataclass
class AtomicityViolation:
    """Atomicity criterion violation"""
    criterion_number: int
    criterion_name: str
    severity: str  # 'critical', 'warning', 'info'
    description: str
    suggestion: str


@dataclass
class AtomicityResult:
    """Result of atomicity validation"""
    is_atomic: bool
    score: float  # 0.0-1.0
    violations: List[AtomicityViolation]
    passed_criteria: List[str]
    failed_criteria: List[str]


class AtomicityValidator:
    """
    Atomicity validator - 10-criteria validation

    Validates atomic units against:
    1. Size (LOC ≤ 15)
    2. Complexity (< 3.0)
    3. Single responsibility
    4. Clear boundaries
    5. Independence
    6. Context completeness (≥ 95%)
    7. Testability
    8. Determinism
    9. Side effects (minimal)
    10. Clear I/O

    Score calculation:
    - Each criterion: 10% (0.1)
    - Total: 1.0
    - Threshold: ≥0.8 is atomic
    """

    def __init__(
        self,
        max_loc: int = 15,
        max_complexity: float = 3.0,
        min_context_completeness: float = 0.95,
        min_score_threshold: float = 0.8
    ):
        """
        Initialize validator

        Args:
            max_loc: Maximum lines of code
            max_complexity: Maximum cyclomatic complexity
            min_context_completeness: Minimum context completeness
            min_score_threshold: Minimum score to be considered atomic
        """
        self.max_loc = max_loc
        self.max_complexity = max_complexity
        self.min_context_completeness = min_context_completeness
        self.min_score_threshold = min_score_threshold

        logger.info(f"AtomicityValidator initialized (max_loc={max_loc}, max_complexity={max_complexity}, threshold={min_score_threshold})")

    def validate(
        self,
        atom: AtomCandidate,
        context: Optional[AtomContext] = None,
        siblings: Optional[List[AtomCandidate]] = None
    ) -> AtomicityResult:
        """
        Validate atom against 10 atomicity criteria

        Args:
            atom: Atomic unit candidate
            context: Execution context (if available)
            siblings: Other atoms in same task (for independence check)

        Returns:
            AtomicityResult with score and violations
        """
        logger.debug(f"Validating atomicity for: {atom.description}")

        violations = []
        passed = []
        failed = []
        score = 0.0

        # Criterion 1: LOC ≤ 15
        if self._validate_size(atom):
            score += 0.1
            passed.append("1. Size (LOC ≤ 15)")
        else:
            failed.append("1. Size (LOC ≤ 15)")
            violations.append(AtomicityViolation(
                criterion_number=1,
                criterion_name="Size",
                severity="critical",
                description=f"Atom has {atom.loc} LOC, exceeds maximum of {self.max_loc}",
                suggestion="Split into smaller atoms"
            ))

        # Criterion 2: Complexity < 3.0
        if self._validate_complexity(atom):
            score += 0.1
            passed.append("2. Complexity < 3.0")
        else:
            failed.append("2. Complexity < 3.0")
            violations.append(AtomicityViolation(
                criterion_number=2,
                criterion_name="Complexity",
                severity="critical",
                description=f"Complexity {atom.complexity:.1f} exceeds maximum of {self.max_complexity}",
                suggestion="Simplify logic, reduce decision points"
            ))

        # Criterion 3: Single responsibility
        resp_result = self._validate_single_responsibility(atom)
        if resp_result[0]:
            score += 0.1
            passed.append("3. Single responsibility")
        else:
            failed.append("3. Single responsibility")
            violations.append(AtomicityViolation(
                criterion_number=3,
                criterion_name="Single Responsibility",
                severity="warning",
                description=resp_result[1],
                suggestion="Focus on one task per atom"
            ))

        # Criterion 4: Clear boundaries
        if self._validate_clear_boundaries(atom):
            score += 0.1
            passed.append("4. Clear boundaries")
        else:
            failed.append("4. Clear boundaries")
            violations.append(AtomicityViolation(
                criterion_number=4,
                criterion_name="Clear Boundaries",
                severity="warning",
                description="Atom boundaries are ambiguous",
                suggestion="Use function/class/block boundaries"
            ))

        # Criterion 5: Independence from siblings
        if self._validate_independence(atom, siblings):
            score += 0.1
            passed.append("5. Independence")
        else:
            failed.append("5. Independence")
            violations.append(AtomicityViolation(
                criterion_number=5,
                criterion_name="Independence",
                severity="warning",
                description="Atom has strong coupling with siblings",
                suggestion="Reduce dependencies between atoms"
            ))

        # Criterion 6: Complete context
        if context:
            if self._validate_context_completeness(context):
                score += 0.1
                passed.append("6. Context completeness")
            else:
                failed.append("6. Context completeness")
                violations.append(AtomicityViolation(
                    criterion_number=6,
                    criterion_name="Context Completeness",
                    severity="critical",
                    description=f"Context completeness {context.completeness_score:.1%}, target is ≥{self.min_context_completeness:.0%}",
                    suggestion=f"Complete missing: {', '.join(context.missing_elements)}"
                ))
        else:
            # No context provided - skip
            score += 0.1
            passed.append("6. Context completeness (not checked)")

        # Criterion 7: Testable
        if self._validate_testability(atom):
            score += 0.1
            passed.append("7. Testable")
        else:
            failed.append("7. Testable")
            violations.append(AtomicityViolation(
                criterion_number=7,
                criterion_name="Testability",
                severity="warning",
                description="Atom is difficult to test",
                suggestion="Reduce side effects, make deterministic"
            ))

        # Criterion 8: Deterministic
        if self._validate_determinism(atom):
            score += 0.1
            passed.append("8. Deterministic")
        else:
            failed.append("8. Deterministic")
            violations.append(AtomicityViolation(
                criterion_number=8,
                criterion_name="Determinism",
                severity="info",
                description="Atom has non-deterministic elements",
                suggestion="Remove randomness, time dependencies"
            ))

        # Criterion 9: No side effects (prefer)
        side_effect_result = self._validate_side_effects(atom)
        if side_effect_result[0]:
            score += 0.1
            passed.append("9. No side effects")
        else:
            failed.append("9. No side effects")
            violations.append(AtomicityViolation(
                criterion_number=9,
                criterion_name="Side Effects",
                severity="info",
                description=f"Side effects detected: {side_effect_result[1]}",
                suggestion="Minimize or isolate side effects"
            ))

        # Criterion 10: Clear input/output
        if self._validate_clear_io(atom):
            score += 0.1
            passed.append("10. Clear I/O")
        else:
            failed.append("10. Clear I/O")
            violations.append(AtomicityViolation(
                criterion_number=10,
                criterion_name="Clear I/O",
                severity="warning",
                description="Input/output not clearly defined",
                suggestion="Add type hints, document parameters"
            ))

        # Determine if atomic
        is_atomic = score >= self.min_score_threshold

        result = AtomicityResult(
            is_atomic=is_atomic,
            score=score,
            violations=violations,
            passed_criteria=passed,
            failed_criteria=failed
        )

        logger.debug(f"Atomicity score: {score:.2f} ({'PASS' if is_atomic else 'FAIL'})")
        return result

    def _validate_size(self, atom: AtomCandidate) -> bool:
        """Criterion 1: LOC ≤ 15"""
        return atom.loc <= self.max_loc

    def _validate_complexity(self, atom: AtomCandidate) -> bool:
        """Criterion 2: Complexity < 3.0"""
        return atom.complexity < self.max_complexity

    def _validate_single_responsibility(self, atom: AtomCandidate) -> Tuple[bool, str]:
        """Criterion 3: Single responsibility"""
        # Heuristic: check for multiple responsibilities
        code = atom.code

        # Count different types of operations
        operations = {
            'data_manipulation': len(re.findall(r'\w+\s*=\s*', code)),
            'function_calls': len(re.findall(r'\w+\(', code)),
            'control_flow': len(re.findall(r'if |for |while ', code)),
            'io_operations': len(re.findall(r'print\(|input\(|open\(|read\(|write\(', code)),
        }

        # Multiple types suggest multiple responsibilities
        non_zero = sum(1 for count in operations.values() if count > 0)
        if non_zero > 2:
            return False, f"Multiple operation types detected: {operations}"

        return True, ""

    def _validate_clear_boundaries(self, atom: AtomCandidate) -> bool:
        """Criterion 4: Clear boundaries"""
        # Check if boundary type is well-defined
        return atom.boundary_type in ['function', 'class', 'block', 'complete']

    def _validate_independence(
        self,
        atom: AtomCandidate,
        siblings: Optional[List[AtomCandidate]]
    ) -> bool:
        """Criterion 5: Independence from siblings"""
        if not siblings:
            return True  # No siblings to check

        # Check if atom depends on variables defined in siblings
        # Simple heuristic: no shared variable names
        atom_vars = set(re.findall(r'\b([a-zA-Z_]\w*)\b', atom.code))

        for sibling in siblings:
            if sibling == atom:
                continue
            sibling_vars = set(re.findall(r'\b([a-zA-Z_]\w*)\b', sibling.code))

            # High overlap suggests coupling
            overlap = atom_vars & sibling_vars
            if len(overlap) > 5:  # More than 5 shared identifiers
                return False

        return True

    def _validate_context_completeness(self, context: AtomContext) -> bool:
        """Criterion 6: Complete context (≥ 95%)"""
        return context.completeness_score >= self.min_context_completeness

    def _validate_testability(self, atom: AtomCandidate) -> bool:
        """Criterion 7: Testable"""
        code = atom.code

        # Indicators of poor testability
        bad_indicators = [
            'global ',  # Global state
            'time.',    # Time dependencies
            'random.',  # Randomness
            'input(',   # User input
        ]

        for indicator in bad_indicators:
            if indicator in code:
                return False

        return True

    def _validate_determinism(self, atom: AtomCandidate) -> bool:
        """Criterion 8: Deterministic"""
        code = atom.code

        # Non-deterministic patterns
        non_det_patterns = [
            r'random\.',
            r'time\.',
            r'datetime\.now',
            r'uuid\.',
            r'input\(',
        ]

        for pattern in non_det_patterns:
            if re.search(pattern, code):
                return False

        return True

    def _validate_side_effects(self, atom: AtomCandidate) -> Tuple[bool, str]:
        """Criterion 9: No side effects (prefer)"""
        code = atom.code

        # Side effect patterns
        side_effects = []

        if 'print(' in code or 'console.log(' in code:
            side_effects.append('stdout')
        if 'input(' in code or 'prompt(' in code:
            side_effects.append('stdin')
        if 'open(' in code or 'fs.' in code:
            side_effects.append('file_io')
        if 'requests.' in code or 'fetch(' in code:
            side_effects.append('network')
        if 'global ' in code:
            side_effects.append('global_state')

        if side_effects:
            return False, ', '.join(side_effects)

        return True, ""

    def _validate_clear_io(self, atom: AtomCandidate) -> bool:
        """Criterion 10: Clear input/output"""
        code = atom.code

        # Check for type hints (Python)
        has_type_hints = '->' in code or ': ' in code

        # Check for function signature
        has_function = 'def ' in code or 'function ' in code or '=>' in code

        # If it's a function, it should have clear signature
        if has_function:
            return has_type_hints or '(' in code

        # For non-functions, accept as clear
        return True
