"""
AtomicSpec Validator - Pre-Generation Validation

Validates AtomicSpec instances BEFORE code generation.
Ensures specs meet atomicity criteria and are executable.

Validation Criteria:
1. Single responsibility
2. Size: 5-15 LOC
3. Complexity: ≤3.0
4. Testability: ≥1 test case
5. Type safety: explicit types
6. Context completeness: imports specified
7. Purity (if required)
8. Clear I/O

Author: DevMatrix Team
Date: 2025-11-12
"""

from typing import List, Tuple
from src.models.atomic_spec import AtomicSpec, AtomicSpecValidationResult
import logging

logger = logging.getLogger(__name__)


class AtomicSpecValidator:
    """
    AtomicSpec Validator - Pre-generation validation

    Validates atomic specifications BEFORE code generation.
    Ensures specs are atomic, testable, and executable.

    Usage:
        validator = AtomicSpecValidator()
        result = validator.validate(spec)
        if result.is_valid:
            # Proceed with code generation
        else:
            # Reject and re-generate
    """

    def __init__(
        self,
        max_loc: int = 15,
        max_complexity: float = 3.0,
        min_test_cases: int = 1
    ):
        """
        Initialize validator

        Args:
            max_loc: Maximum lines of code allowed (default: 15)
            max_complexity: Maximum cyclomatic complexity (default: 3.0)
            min_test_cases: Minimum test cases required (default: 1)
        """
        self.max_loc = max_loc
        self.max_complexity = max_complexity
        self.min_test_cases = min_test_cases

        logger.info(
            f"AtomicSpecValidator initialized "
            f"(max_loc={max_loc}, max_complexity={max_complexity}, min_tests={min_test_cases})"
        )

    def validate(self, spec: AtomicSpec) -> AtomicSpecValidationResult:
        """
        Validate atomic spec against atomicity criteria

        Checks:
        1. Single responsibility (description analysis)
        2. LOC within range (5-15)
        3. Complexity within limit (≤3.0)
        4. Test cases present (≥1)
        5. Type safety (I/O types specified)
        6. Context completeness (imports for non-trivial specs)
        7. Purity constraints (if required)
        8. Testability (clear I/O)

        Args:
            spec: AtomicSpec to validate

        Returns:
            AtomicSpecValidationResult with errors and warnings
        """
        logger.debug(f"Validating spec: {spec.description}")

        errors = []
        warnings = []
        score = 1.0

        # 1. Single Responsibility Check (CRITICAL)
        if not self._has_single_responsibility(spec):
            errors.append(
                f"Description '{spec.description}' suggests multiple responsibilities. "
                f"Each spec should have ONE clear purpose (one action verb)."
            )
            score -= 0.2

        # 2. LOC Target Check (CRITICAL)
        if spec.target_loc > self.max_loc:
            errors.append(
                f"Target LOC {spec.target_loc} exceeds maximum {self.max_loc}. "
                f"Split into smaller atomic specs."
            )
            score -= 0.2
        elif spec.target_loc < 5:
            warnings.append(
                f"Target LOC {spec.target_loc} is very small (<5). "
                f"Consider merging with related specs."
            )
            score -= 0.05

        # 3. Complexity Check (CRITICAL)
        if spec.complexity_limit > self.max_complexity:
            errors.append(
                f"Complexity limit {spec.complexity_limit} exceeds maximum {self.max_complexity}. "
                f"Simplify logic or split into simpler specs."
            )
            score -= 0.2

        # 4. Test Cases Check (CRITICAL)
        if len(spec.test_cases) < self.min_test_cases:
            errors.append(
                f"At least {self.min_test_cases} test case(s) required, got {len(spec.test_cases)}. "
                f"Testability is mandatory for atomic specs."
            )
            score -= 0.2

        # 5. Type Safety Check (WARNING)
        if not spec.output_type:
            warnings.append("No output type specified - type safety recommended")
            score -= 0.05

        if not spec.input_types and spec.target_loc > 5:
            warnings.append("No input types specified for non-trivial spec - type safety recommended")
            score -= 0.05

        # 6. Context Completeness Check (WARNING)
        if not spec.imports_required and spec.target_loc > 7:
            warnings.append(
                f"No imports specified for {spec.target_loc} LOC spec. "
                f"Context completeness is important for generation."
            )
            score -= 0.05

        # 7. Purity Check (CRITICAL if required)
        if spec.must_be_pure:
            if self._has_side_effects_indicators(spec):
                errors.append(
                    "Spec marked as 'must_be_pure' but description contains side effect indicators "
                    "(save, write, update, send, etc.). Pure functions cannot have side effects."
                )
                score -= 0.15

        # 8. Testability Check (CRITICAL)
        if not self._is_testable(spec):
            errors.append(
                "Spec is not testable - missing clear I/O definition. "
                "All specs must have verifiable input/output behavior."
            )
            score -= 0.2

        # 9. Dependency Validation (WARNING)
        if len(spec.dependencies) > 5:
            warnings.append(
                f"Spec has {len(spec.dependencies)} dependencies (high coupling). "
                f"Consider reducing dependencies for better atomicity."
            )
            score -= 0.05

        # Clamp score to [0.0, 1.0]
        score = max(0.0, min(1.0, score))

        # Determine validity
        is_valid = len(errors) == 0

        result = AtomicSpecValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            score=score
        )

        logger.debug(
            f"Validation complete: {'VALID' if is_valid else 'INVALID'} "
            f"(score={score:.2f}, errors={len(errors)}, warnings={len(warnings)})"
        )

        return result

    def validate_batch(
        self,
        specs: List[AtomicSpec]
    ) -> Tuple[List[AtomicSpec], List[Tuple[AtomicSpec, AtomicSpecValidationResult]]]:
        """
        Validate multiple specs and separate valid from invalid

        Args:
            specs: List of AtomicSpec instances to validate

        Returns:
            Tuple of (valid_specs, invalid_specs_with_results)
            - valid_specs: List of specs that passed validation
            - invalid_specs_with_results: List of (spec, validation_result) tuples for failed specs
        """
        logger.info(f"Validating batch of {len(specs)} specs")

        valid = []
        invalid = []

        for spec in specs:
            result = self.validate(spec)
            if result.is_valid:
                valid.append(spec)
            else:
                invalid.append((spec, result))

        logger.info(
            f"Batch validation complete: {len(valid)} valid, {len(invalid)} invalid"
        )

        return valid, invalid

    # ==================== Private Validation Methods ====================

    def _has_single_responsibility(self, spec: AtomicSpec) -> bool:
        """
        Check if description suggests single responsibility

        Heuristics:
        - Max 1 action verb in description
        - Max 1 "and" conjunction
        - No multiple responsibilities keywords
        """
        description = spec.description.lower()

        # Common action verbs
        action_verbs = [
            'create', 'update', 'delete', 'validate', 'send', 'fetch',
            'process', 'parse', 'transform', 'calculate', 'generate',
            'build', 'construct', 'save', 'load', 'write', 'read'
        ]

        # Count action verbs (should be ≤1)
        words = description.split()
        verb_count = sum(1 for word in words if word in action_verbs)

        # Count "and" conjunctions (should be ≤1)
        and_count = description.count(' and ')

        # Multiple responsibilities indicators
        multi_responsibility_keywords = [
            ' then ', ' also ', ' additionally ', ' furthermore ',
            ' moreover ', ' besides '
        ]
        has_multi_keywords = any(kw in description for kw in multi_responsibility_keywords)

        # Single responsibility if:
        # - ≤1 action verb
        # - ≤1 "and"
        # - No multiple responsibility keywords
        return verb_count <= 1 and and_count <= 1 and not has_multi_keywords

    def _has_side_effects_indicators(self, spec: AtomicSpec) -> bool:
        """
        Check for side effect indicators in spec description

        Side effects include:
        - I/O operations (save, write, print, log)
        - State mutations (update, delete, modify)
        - Network calls (send, publish, post)
        - External system interactions
        """
        description = spec.description.lower()

        side_effect_keywords = [
            'save', 'persist', 'write', 'update', 'delete', 'modify',
            'send', 'publish', 'post', 'put', 'patch',
            'log', 'print', 'output',
            'create table', 'insert', 'drop'
        ]

        return any(keyword in description for keyword in side_effect_keywords)

    def _is_testable(self, spec: AtomicSpec) -> bool:
        """
        Check if spec is testable

        Testable specs have:
        - Clear inputs (input_types OR parameters in description)
        - Clear outputs (output_type)
        - At least min_test_cases test cases
        """
        has_inputs = len(spec.input_types) > 0 or bool(spec.description)
        has_outputs = bool(spec.output_type)
        has_test_cases = len(spec.test_cases) >= self.min_test_cases

        return has_inputs and has_outputs and has_test_cases

    def validate_dependency_graph(
        self,
        specs: List[AtomicSpec]
    ) -> Tuple[bool, List[str]]:
        """
        Validate dependency graph for circular dependencies and validity

        Args:
            specs: List of all specs in the task

        Returns:
            Tuple of (is_valid, errors)
            - is_valid: True if no circular dependencies
            - errors: List of error messages
        """
        logger.info(f"Validating dependency graph for {len(specs)} specs")

        errors = []
        spec_ids = {spec.spec_id for spec in specs}

        # Build adjacency list
        graph = {spec.spec_id: spec.dependencies for spec in specs}

        # Check for invalid dependencies (reference to non-existent specs)
        for spec in specs:
            for dep_id in spec.dependencies:
                if dep_id not in spec_ids:
                    errors.append(
                        f"Spec '{spec.spec_id}' depends on non-existent spec '{dep_id}'"
                    )

        # Check for circular dependencies (DFS)
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            """DFS to detect cycles"""
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        # Check all nodes
        for spec_id in spec_ids:
            if spec_id not in visited:
                if has_cycle(spec_id):
                    errors.append(
                        "Circular dependency detected in spec dependency graph"
                    )
                    break

        is_valid = len(errors) == 0

        logger.info(
            f"Dependency graph validation: {'VALID' if is_valid else 'INVALID'} "
            f"({len(errors)} errors)"
        )

        return is_valid, errors
