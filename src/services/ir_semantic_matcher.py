"""
Phase 3: IR-Aware Semantic Matcher.

Matches ConstraintIR objects directly, using a hierarchical matching strategy:
1. Exact IR match (entity + field + constraint_type + value)
2. ValidationType match (entity + field + validation_type)
3. Field match (entity + field only)
4. Embedding fallback (only if enabled)

PHASE 4 ALIGNED: Phase 2 already normalized types, so no equivalence groups needed.
"""

import logging
from dataclasses import dataclass
from typing import Optional, List, Tuple

from src.cognitive.ir.constraint_ir import ConstraintIR, validation_model_to_constraint_irs
from src.cognitive.ir.validation_model import ValidationType, ValidationModelIR

# Optional: SemanticMatcher for embedding fallback
try:
    from src.services.semantic_matcher import SemanticMatcher
    SEMANTIC_MATCHER_AVAILABLE = True
except ImportError:
    SEMANTIC_MATCHER_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class IRMatchResult:
    """Result of an IR-native match operation."""
    match: bool
    confidence: float
    method: str  # "exact_ir" | "validation_type_ir" | "field_ir" | "embedding" | "no_match"
    spec_constraint: ConstraintIR
    code_constraint: Optional[ConstraintIR]
    reason: str
    category_match: bool = False
    value_match: bool = False


class IRSemanticMatcher:
    """
    IR-Aware Semantic Matcher for Phase 3.

    Matches constraints at the IR level using a hierarchical strategy:
    1. Exact match: entity.field.constraint_type + value
    2. ValidationType match: entity.field.validation_type
    3. Field match: entity.field only
    4. Embedding fallback: semantic similarity (optional)

    PHASE 4 ALIGNED: Simplified matching because Phase 2 SemanticNormalizer
    already normalized all variants to canonical ValidationType values.
    """

    EXACT_MATCH_CONFIDENCE = 1.0
    CATEGORY_MATCH_CONFIDENCE = 0.9
    FIELD_MATCH_CONFIDENCE = 0.7
    EMBEDDING_THRESHOLD = 0.65

    def __init__(
        self,
        use_embedding_fallback: bool = True,
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        """
        Initialize the IR semantic matcher.

        Args:
            use_embedding_fallback: Whether to use SemanticMatcher for uncertain cases
            embedding_model: Sentence transformer model for embedding fallback
        """
        self.use_embedding_fallback = use_embedding_fallback

        # Initialize embedding matcher for fallback
        if use_embedding_fallback and SEMANTIC_MATCHER_AVAILABLE:
            self._embedding_matcher = SemanticMatcher(
                model_name=embedding_model,
                use_llm_fallback=False  # IR matching is already smart enough
            )
        else:
            self._embedding_matcher = None
            if use_embedding_fallback:
                logger.warning("SemanticMatcher not available, embedding fallback disabled")

    def match_ir(
        self,
        spec_constraint: ConstraintIR,
        code_constraint: ConstraintIR
    ) -> IRMatchResult:
        """
        Match two ConstraintIR objects directly.

        PHASE 4 ALIGNED: Simplified matching hierarchy.
        Phase 2 already normalized types, so no equivalence groups needed.

        Args:
            spec_constraint: Constraint from spec (ground truth)
            code_constraint: Constraint from code

        Returns:
            IRMatchResult with match status and confidence
        """
        # Level 1: Exact IR match (entity + field + constraint_type + value)
        if spec_constraint.matches_exactly(code_constraint):
            return IRMatchResult(
                match=True,
                confidence=self.EXACT_MATCH_CONFIDENCE,
                method="exact_ir",
                spec_constraint=spec_constraint,
                code_constraint=code_constraint,
                reason="Exact IR match: entity, field, type, value all match",
                category_match=True,
                value_match=True
            )

        # Level 2: ValidationType match (same entity + field + validation_type)
        if spec_constraint.matches_validation_type(code_constraint):
            value_compatible = self._values_compatible(spec_constraint, code_constraint)

            if value_compatible:
                return IRMatchResult(
                    match=True,
                    confidence=self.CATEGORY_MATCH_CONFIDENCE,
                    method="validation_type_ir",
                    spec_constraint=spec_constraint,
                    code_constraint=code_constraint,
                    reason=f"ValidationType match: both {spec_constraint.validation_type.value}, values compatible",
                    category_match=True,
                    value_match=value_compatible
                )

        # Level 3: Field match (same entity + field, different types)
        if spec_constraint.matches_field(code_constraint):
            return IRMatchResult(
                match=True,
                confidence=self.FIELD_MATCH_CONFIDENCE,
                method="field_ir",
                spec_constraint=spec_constraint,
                code_constraint=code_constraint,
                reason=f"Field match: same entity.field, different types ({spec_constraint.validation_type.value} vs {code_constraint.validation_type.value})",
                category_match=False,
                value_match=False
            )

        # Level 4: Embedding fallback (ONLY if enabled and needed)
        if self.use_embedding_fallback and self._embedding_matcher:
            return self._embedding_fallback(spec_constraint, code_constraint)

        # No match
        return IRMatchResult(
            match=False,
            confidence=0.0,
            method="no_match",
            spec_constraint=spec_constraint,
            code_constraint=code_constraint,
            reason="No IR match found",
            category_match=False,
            value_match=False
        )

    def _values_compatible(
        self,
        spec: ConstraintIR,
        code: ConstraintIR
    ) -> bool:
        """
        Check if values are compatible.

        PHASE 4 ALIGNED: Simplified logic because Phase 2 SemanticNormalizer
        already normalized constraint_type to canonical form.
        """
        if spec.validation_type != code.validation_type:
            return False

        # Same validation_type with same or no value = compatible
        if spec.constraint_type == code.constraint_type:
            if spec.value is None or code.value is None:
                return True
            return spec._values_match(spec.value, code.value)

        # For enum/status constraints, check value subset
        if spec.validation_type == ValidationType.STATUS_TRANSITION:
            return self._enum_values_compatible(spec, code)

        # Same validation_type, different constraint_type = compatible
        return True

    def _enum_values_compatible(self, spec: ConstraintIR, code: ConstraintIR) -> bool:
        """Check enum constraint compatibility - code should be superset of spec."""
        if spec.value is None or code.value is None:
            return True

        spec_values = set(spec.value) if isinstance(spec.value, list) else {spec.value}
        code_values = set(code.value) if isinstance(code.value, list) else {code.value}

        return spec_values.issubset(code_values)

    def _embedding_fallback(
        self,
        spec: ConstraintIR,
        code: ConstraintIR
    ) -> IRMatchResult:
        """
        Fall back to embedding-based matching for uncertain cases.

        Converts ConstraintIR to strings and uses SemanticMatcher.
        """
        spec_str = spec.to_string()
        code_str = code.to_string()

        result = self._embedding_matcher.match(spec_str, code_str)

        return IRMatchResult(
            match=result.match,
            confidence=result.confidence,
            method="embedding",
            spec_constraint=spec,
            code_constraint=code,
            reason=f"Embedding fallback: {result.reason}",
            category_match=False,
            value_match=False
        )

    def match_validation_models(
        self,
        spec_model: ValidationModelIR,
        code_model: ValidationModelIR
    ) -> Tuple[float, List[IRMatchResult]]:
        """
        Match two ValidationModelIR instances.

        Args:
            spec_model: ValidationModelIR from spec (ground truth)
            code_model: ValidationModelIR from code

        Returns:
            Tuple of (compliance_score, list of IRMatchResult)
        """
        spec_constraints = validation_model_to_constraint_irs(spec_model)
        code_constraints = validation_model_to_constraint_irs(code_model)

        return self.match_constraint_lists(spec_constraints, code_constraints)

    def match_constraint_lists(
        self,
        spec_constraints: List[ConstraintIR],
        code_constraints: List[ConstraintIR]
    ) -> Tuple[float, List[IRMatchResult]]:
        """
        Match lists of ConstraintIR objects.

        For each spec constraint, finds the best matching code constraint.

        Args:
            spec_constraints: Constraints from spec (ground truth)
            code_constraints: Constraints from code

        Returns:
            Tuple of (compliance_score, list of IRMatchResult)
        """
        results = []
        matched_count = 0
        total_rules = len(spec_constraints)

        if total_rules == 0:
            return 1.0, []  # No rules = 100% compliance

        # Build index for faster lookup
        code_by_field = {}
        for constraint in code_constraints:
            key = constraint.field_key
            if key not in code_by_field:
                code_by_field[key] = []
            code_by_field[key].append(constraint)

        for spec_constraint in spec_constraints:
            # Get candidate code constraints for this field
            candidates = code_by_field.get(spec_constraint.field_key, [])

            best_match: Optional[IRMatchResult] = None
            best_confidence = 0.0

            for code_constraint in candidates:
                result = self.match_ir(spec_constraint, code_constraint)

                if result.match and result.confidence > best_confidence:
                    best_match = result
                    best_confidence = result.confidence

            if best_match:
                matched_count += 1
                results.append(best_match)
            else:
                # No match found
                results.append(IRMatchResult(
                    match=False,
                    confidence=0.0,
                    method="no_match",
                    spec_constraint=spec_constraint,
                    code_constraint=None,
                    reason=f"No matching code constraint found for {spec_constraint.canonical_key}",
                    category_match=False,
                    value_match=False
                ))

        compliance = matched_count / total_rules
        logger.info(f"🧠 IR matching: {matched_count}/{total_rules} = {compliance:.1%}")

        return compliance, results

    def get_stats(self) -> dict:
        """Get matcher statistics."""
        return {
            "embedding_fallback_enabled": self.use_embedding_fallback,
            "embedding_matcher_available": self._embedding_matcher is not None,
            "exact_threshold": self.EXACT_MATCH_CONFIDENCE,
            "category_threshold": self.CATEGORY_MATCH_CONFIDENCE,
            "field_threshold": self.FIELD_MATCH_CONFIDENCE,
            "embedding_threshold": self.EMBEDDING_THRESHOLD,
        }


def match_validation_models_sync(
    spec_model: ValidationModelIR,
    code_model: ValidationModelIR,
    use_embedding_fallback: bool = True
) -> Tuple[float, List[IRMatchResult]]:
    """
    Synchronous convenience function for matching ValidationModelIRs.

    Args:
        spec_model: ValidationModelIR from spec
        code_model: ValidationModelIR from code
        use_embedding_fallback: Whether to use embedding fallback

    Returns:
        Tuple of (compliance_score, list of IRMatchResult)
    """
    matcher = IRSemanticMatcher(use_embedding_fallback=use_embedding_fallback)
    return matcher.match_validation_models(spec_model, code_model)
