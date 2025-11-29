"""
Repair Confidence Model - Probabilistic Repair Ranking.

Orders repair strategies by probability of success using historical patterns,
IR context matching, and semantic similarity.

Reference: SMOKE_DRIVEN_REPAIR_ARCHITECTURE.md - Task 9
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

class RepairStrategyType(str, Enum):
    """Types of repair strategies."""
    ADD_NULLABLE = "add_nullable"
    FIX_IMPORT = "fix_import"
    ADD_VALIDATOR = "add_validator"
    FIX_FOREIGN_KEY = "fix_foreign_key"
    FIX_ROUTE = "fix_route"
    FIX_TYPE = "fix_type"
    ADD_DEFAULT = "add_default"
    GENERIC = "generic_fix"


@dataclass
class RepairCandidate:
    """A candidate repair with confidence score."""
    strategy_type: RepairStrategyType
    target_file: str
    fix_description: str

    # Confidence components
    pattern_score: float = 0.5      # Historical success rate
    ir_context_score: float = 0.5   # How well IR matches the error
    semantic_score: float = 0.5     # Semantic similarity to known fixes

    # Combined confidence
    confidence: float = 0.5

    # Metadata
    violation_endpoint: str = ""
    error_type: str = ""
    exception_class: str = ""

    def __post_init__(self):
        """Calculate combined confidence after init."""
        if self.confidence == 0.5:  # Not explicitly set
            self.calculate_confidence()

    def calculate_confidence(
        self,
        alpha: float = 0.4,
        beta: float = 0.35,
        gamma: float = 0.25
    ):
        """
        Calculate combined confidence score.

        confidence = α * pattern_score + β * ir_context_score + γ * semantic_score

        Args:
            alpha: Weight for historical pattern success
            beta: Weight for IR context match
            gamma: Weight for semantic similarity
        """
        self.confidence = (
            alpha * self.pattern_score +
            beta * self.ir_context_score +
            gamma * self.semantic_score
        )


@dataclass
class CausalChain:
    """Causal chain from failing test to IR root cause."""
    failing_test: str           # "POST /products [create_product_happy_path]"
    error_type: str             # "IntegrityError"
    ast_location: str           # "src/models/schemas.py:ProductCreate"
    ir_constraint: str          # "price > 0 (required)"
    generated_constraint: str   # "MISSING" or actual
    root_cause: str             # "ValidationModelIR → Schema generation"
    confidence: float = 0.5


@dataclass
class ConfidenceModelResult:
    """Result of confidence model scoring."""
    candidates: List[RepairCandidate]
    best_candidate: Optional[RepairCandidate]
    average_confidence: float
    high_confidence_count: int  # Candidates with confidence >= 0.7


# =============================================================================
# Confidence Model
# =============================================================================

class RepairConfidenceModel:
    """
    Computes confidence scores for repair candidates.

    confidence = α * pattern_score + β * ir_context_score + γ * semantic_match

    Where:
    - pattern_score: Success rate from historical FixPattern data
    - ir_context_score: How well IR explains the failure
    - semantic_match_score: Keyword similarity to successful fixes
    """

    # Weights for confidence calculation
    ALPHA = 0.4   # Weight for historical pattern success
    BETA = 0.35   # Weight for IR context match
    GAMMA = 0.25  # Weight for semantic similarity

    # Strategy-to-error mappings for IR context scoring
    STRATEGY_ERROR_MAPPINGS = {
        RepairStrategyType.ADD_NULLABLE: [
            "constraint", "nullable", "required", "null", "none",
            "integrityerror", "notnull"
        ],
        RepairStrategyType.FIX_IMPORT: [
            "import", "module", "not found", "undefined", "nameerror",
            "modulenotfound", "importerror"
        ],
        RepairStrategyType.ADD_VALIDATOR: [
            "validation", "format", "range", "value", "invalid",
            "validationerror", "valueerror"
        ],
        RepairStrategyType.FIX_FOREIGN_KEY: [
            "foreign key", "relationship", "reference", "constraint",
            "foreignkey", "integrityerror"
        ],
        RepairStrategyType.FIX_ROUTE: [
            "route", "endpoint", "path", "404", "not found",
            "handler", "router"
        ],
        RepairStrategyType.FIX_TYPE: [
            "type", "cast", "conversion", "mismatch", "typeerror",
            "expected", "got"
        ],
        RepairStrategyType.ADD_DEFAULT: [
            "default", "missing", "required", "argument", "parameter"
        ],
    }

    def __init__(self, pattern_store=None):
        """
        Initialize confidence model.

        Args:
            pattern_store: Optional FixPatternLearner for historical patterns
        """
        self.pattern_store = pattern_store
        self.logger = logging.getLogger(f"{__name__}.RepairConfidenceModel")

    def score_candidates(
        self,
        candidates: List[RepairCandidate],
        violation: Dict[str, Any],
        causal_chain: Optional[CausalChain] = None,
        application_ir=None
    ) -> ConfidenceModelResult:
        """
        Score and rank repair candidates by confidence.

        Args:
            candidates: List of repair candidates to score
            violation: The smoke test violation being addressed
            causal_chain: Optional causal attribution chain
            application_ir: Optional ApplicationIR for context

        Returns:
            ConfidenceModelResult with ranked candidates
        """
        if not candidates:
            return ConfidenceModelResult(
                candidates=[],
                best_candidate=None,
                average_confidence=0.0,
                high_confidence_count=0
            )

        scored = []
        for candidate in candidates:
            # 1. Pattern score from history
            candidate.pattern_score = self._compute_pattern_score(
                candidate, violation
            )

            # 2. IR context score
            candidate.ir_context_score = self._compute_ir_context_score(
                candidate, violation, causal_chain, application_ir
            )

            # 3. Semantic match score
            candidate.semantic_score = self._compute_semantic_score(
                candidate, violation, causal_chain
            )

            # 4. Combined confidence
            candidate.calculate_confidence(self.ALPHA, self.BETA, self.GAMMA)

            scored.append(candidate)

        # Sort by confidence descending
        scored.sort(key=lambda c: c.confidence, reverse=True)

        # Calculate statistics
        avg_confidence = sum(c.confidence for c in scored) / len(scored)
        high_conf_count = sum(1 for c in scored if c.confidence >= 0.7)

        return ConfidenceModelResult(
            candidates=scored,
            best_candidate=scored[0] if scored else None,
            average_confidence=avg_confidence,
            high_confidence_count=high_conf_count
        )

    def _compute_pattern_score(
        self,
        candidate: RepairCandidate,
        violation: Dict[str, Any]
    ) -> float:
        """Compute pattern score from historical success rate."""
        if not self.pattern_store:
            return 0.5  # Neutral without history

        try:
            error_type = violation.get('error_type', 'unknown')
            endpoint = violation.get('endpoint', violation.get('path', ''))
            exception_class = violation.get('exception_class',
                                           violation.get('error', 'Unknown'))

            # Query pattern store for known fix
            pattern = self.pattern_store.get_known_fix(
                error_type=error_type,
                endpoint=endpoint,
                exception_class=exception_class
            )

            if pattern:
                return pattern.success_rate

        except Exception as e:
            self.logger.warning(f"Error querying pattern store: {e}")

        return 0.5  # Neutral if no pattern found

    def _compute_ir_context_score(
        self,
        candidate: RepairCandidate,
        violation: Dict[str, Any],
        causal_chain: Optional[CausalChain],
        application_ir=None
    ) -> float:
        """
        Compute how well the repair strategy addresses the IR gap.

        Higher score if strategy type matches error signature.
        """
        score = 0.3  # Base score

        # Get error context
        error_type = violation.get('error_type', '').lower()
        error_message = str(violation.get('error_message', '')).lower()
        exception_class = violation.get('exception_class', '').lower()

        # Check if causal chain provides root cause
        root_cause = ''
        if causal_chain:
            root_cause = causal_chain.root_cause.lower()

        # Combine all error context
        error_context = f"{error_type} {error_message} {exception_class} {root_cause}"

        # Check strategy-specific keywords
        strategy_keywords = self.STRATEGY_ERROR_MAPPINGS.get(
            candidate.strategy_type, []
        )

        matches = sum(1 for kw in strategy_keywords if kw in error_context)
        if matches > 0:
            # Scale score based on matches (max 1.0)
            score = min(0.3 + (matches * 0.15), 1.0)

        # Boost if strategy matches causal chain
        if causal_chain and self._strategy_matches_causal(candidate, causal_chain):
            score = min(score + 0.2, 1.0)

        return score

    def _compute_semantic_score(
        self,
        candidate: RepairCandidate,
        violation: Dict[str, Any],
        causal_chain: Optional[CausalChain]
    ) -> float:
        """
        Compute semantic similarity between fix description and error.

        Uses simple keyword matching (could be extended with embeddings).
        """
        score = 0.3  # Base score

        fix_desc = candidate.fix_description.lower()
        error_msg = str(violation.get('error_message', '')).lower()

        # Simple keyword overlap
        fix_words = set(fix_desc.split())
        error_words = set(error_msg.split())

        # Remove common words
        common_words = {'the', 'a', 'an', 'is', 'in', 'to', 'for', 'of', 'and'}
        fix_words -= common_words
        error_words -= common_words

        if fix_words and error_words:
            overlap = len(fix_words & error_words)
            total = len(fix_words | error_words)
            if total > 0:
                jaccard = overlap / total
                score = 0.3 + (jaccard * 0.7)

        # Boost for specific error type mentions
        if causal_chain:
            if causal_chain.exception_class.lower() in fix_desc:
                score = min(score + 0.15, 1.0)

        return score

    def _strategy_matches_causal(
        self,
        candidate: RepairCandidate,
        causal_chain: CausalChain
    ) -> bool:
        """Check if strategy type matches causal chain root cause."""
        root_cause = causal_chain.root_cause.lower()
        exception = causal_chain.error_type.lower()

        strategy_matches = {
            RepairStrategyType.ADD_NULLABLE: [
                "constraint", "nullable", "required"
            ],
            RepairStrategyType.FIX_IMPORT: [
                "import", "module"
            ],
            RepairStrategyType.ADD_VALIDATOR: [
                "validation", "schema"
            ],
            RepairStrategyType.FIX_FOREIGN_KEY: [
                "relationship", "foreign"
            ],
        }

        keywords = strategy_matches.get(candidate.strategy_type, [])
        return any(kw in root_cause or kw in exception for kw in keywords)

    def generate_candidates_for_violation(
        self,
        violation: Dict[str, Any],
        app_path: str
    ) -> List[RepairCandidate]:
        """
        Generate repair candidates for a violation.

        Args:
            violation: The smoke test violation
            app_path: Path to generated app

        Returns:
            List of RepairCandidate with basic metadata
        """
        candidates = []
        error_type = violation.get('error_type', 'unknown').lower()
        endpoint = violation.get('endpoint', violation.get('path', ''))

        # Generate candidates based on error type
        if 'integrity' in error_type or '500' in str(violation.get('status_code', '')):
            candidates.append(RepairCandidate(
                strategy_type=RepairStrategyType.ADD_NULLABLE,
                target_file=f"{app_path}/src/models/entities.py",
                fix_description="Add nullable=True to optional columns",
                violation_endpoint=endpoint,
                error_type=error_type
            ))
            candidates.append(RepairCandidate(
                strategy_type=RepairStrategyType.ADD_DEFAULT,
                target_file=f"{app_path}/src/models/entities.py",
                fix_description="Add default values for required columns",
                violation_endpoint=endpoint,
                error_type=error_type
            ))

        if 'validation' in error_type or '422' in str(violation.get('status_code', '')):
            candidates.append(RepairCandidate(
                strategy_type=RepairStrategyType.ADD_VALIDATOR,
                target_file=f"{app_path}/src/models/schemas.py",
                fix_description="Fix Pydantic schema validation",
                violation_endpoint=endpoint,
                error_type=error_type
            ))

        if 'import' in error_type or 'module' in error_type:
            candidates.append(RepairCandidate(
                strategy_type=RepairStrategyType.FIX_IMPORT,
                target_file=f"{app_path}/src/main.py",
                fix_description="Fix missing import statements",
                violation_endpoint=endpoint,
                error_type=error_type
            ))

        if '404' in str(violation.get('status_code', '')):
            candidates.append(RepairCandidate(
                strategy_type=RepairStrategyType.FIX_ROUTE,
                target_file=f"{app_path}/src/api/routes/",
                fix_description="Fix route registration",
                violation_endpoint=endpoint,
                error_type=error_type
            ))

        # Always add generic as fallback
        candidates.append(RepairCandidate(
            strategy_type=RepairStrategyType.GENERIC,
            target_file=f"{app_path}/src/",
            fix_description="Apply generic repair based on error analysis",
            violation_endpoint=endpoint,
            error_type=error_type
        ))

        return candidates


# =============================================================================
# Causal Attribution (Lightweight)
# =============================================================================

class LightweightCausalAttributor:
    """
    Lightweight causal attribution from error to potential root cause.

    Maps error signatures to likely IR transformation issues.
    """

    # Error signature to root cause mappings
    ERROR_CAUSE_MAPPINGS = {
        'integrityerror': {
            'null': 'DomainModelIR → Entity generation: nullable constraint missing',
            'foreign': 'DomainModelIR → Relationship mapping: FK reference invalid',
            'duplicate': 'DomainModelIR → Constraint generation: unique constraint missing',
            'default': 'DomainModelIR → Entity generation: default value missing',
        },
        'validationerror': {
            'field required': 'ValidationModelIR → Schema generation: required field mismatch',
            'type': 'ValidationModelIR → Schema generation: type annotation wrong',
            'value': 'ValidationModelIR → Constraint generation: value validation missing',
        },
        'importerror': {
            'default': 'CodeGeneration → Import resolution: missing module',
        },
        'attributeerror': {
            'default': 'CodeGeneration → Attribute access: undefined attribute',
        },
        'typeerror': {
            'default': 'CodeGeneration → Type handling: type mismatch',
        },
    }

    def attribute_failure(
        self,
        violation: Dict[str, Any],
        stack_trace: Optional[Dict[str, Any]] = None,
        application_ir=None
    ) -> CausalChain:
        """
        Attribute a failure to its likely root cause.

        Args:
            violation: The smoke test violation
            stack_trace: Optional parsed stack trace
            application_ir: Optional ApplicationIR

        Returns:
            CausalChain with attributed root cause
        """
        endpoint = violation.get('endpoint', violation.get('path', ''))
        error_type = violation.get('error_type', 'unknown')
        error_message = str(violation.get('error_message', ''))
        exception_class = violation.get('exception_class', error_type)

        # Determine root cause
        root_cause = self._determine_root_cause(
            exception_class, error_message
        )

        # Extract AST location from stack trace
        ast_location = 'unknown'
        if stack_trace:
            ast_location = f"{stack_trace.get('file', 'unknown')}:{stack_trace.get('line', 0)}"

        # Determine IR constraint
        ir_constraint, generated = self._find_ir_mismatch(
            endpoint, error_message, application_ir
        )

        # Confidence based on how specific the attribution is
        confidence = 0.6
        if 'default' not in root_cause.lower():
            confidence = 0.75
        if ir_constraint != 'unknown':
            confidence = 0.85

        return CausalChain(
            failing_test=f"{violation.get('method', 'GET')} {endpoint}",
            error_type=exception_class,
            ast_location=ast_location,
            ir_constraint=ir_constraint,
            generated_constraint=generated,
            root_cause=root_cause,
            confidence=confidence
        )

    def _determine_root_cause(
        self,
        exception_class: str,
        error_message: str
    ) -> str:
        """Determine root cause from error signature."""
        exc_lower = exception_class.lower()
        msg_lower = error_message.lower()

        # Find matching error type
        for error_key, causes in self.ERROR_CAUSE_MAPPINGS.items():
            if error_key in exc_lower:
                # Find most specific cause
                for keyword, cause in causes.items():
                    if keyword in msg_lower:
                        return cause
                # Return default for this error type
                return causes.get('default', f"Unknown {error_key} cause")

        return "Unknown root cause - requires manual investigation"

    def _find_ir_mismatch(
        self,
        endpoint: str,
        error_message: str,
        application_ir
    ) -> tuple:
        """Find mismatch between IR constraint and generated code."""
        # Extract entity from endpoint
        entity_name = self._extract_entity(endpoint)

        if not application_ir or not entity_name:
            return 'unknown', 'unknown'

        # Try to find relevant IR constraint
        ir_constraint = 'unknown'
        generated = 'MISSING'

        # Check domain model constraints
        if hasattr(application_ir, 'domain_model') and application_ir.domain_model:
            for entity in application_ir.domain_model.entities:
                if entity.name.lower() == entity_name.lower():
                    if hasattr(entity, 'constraints'):
                        for c in entity.constraints:
                            if self._constraint_matches_error(c, error_message):
                                ir_constraint = f"{c.field}: {c.type}"
                                break

        return ir_constraint, generated

    def _extract_entity(self, endpoint: str) -> Optional[str]:
        """Extract entity name from endpoint."""
        parts = endpoint.strip('/').split('/')
        if parts:
            return parts[0].rstrip('s').title()
        return None

    def _constraint_matches_error(self, constraint, error_message: str) -> bool:
        """Check if constraint is related to error."""
        if not hasattr(constraint, 'field'):
            return False
        return constraint.field.lower() in error_message.lower()


# =============================================================================
# Convenience Functions
# =============================================================================

def rank_repair_candidates(
    candidates: List[Dict[str, Any]],
    violation: Dict[str, Any],
    pattern_store=None
) -> List[Dict[str, Any]]:
    """
    Convenience function to rank repair candidates.

    Args:
        candidates: List of candidate dicts with 'strategy_type', 'target_file', 'fix_description'
        violation: The violation being repaired
        pattern_store: Optional pattern store for historical data

    Returns:
        Ranked list of candidates with 'confidence' added
    """
    model = RepairConfidenceModel(pattern_store)

    # Convert to RepairCandidate objects
    candidate_objs = []
    for c in candidates:
        strategy = RepairStrategyType(c.get('strategy_type', 'generic_fix'))
        candidate_objs.append(RepairCandidate(
            strategy_type=strategy,
            target_file=c.get('target_file', ''),
            fix_description=c.get('fix_description', ''),
            violation_endpoint=c.get('violation_endpoint', ''),
            error_type=c.get('error_type', '')
        ))

    # Score candidates
    result = model.score_candidates(candidate_objs, violation)

    # Convert back to dicts with confidence
    ranked = []
    for c in result.candidates:
        ranked.append({
            'strategy_type': c.strategy_type.value,
            'target_file': c.target_file,
            'fix_description': c.fix_description,
            'confidence': c.confidence,
            'pattern_score': c.pattern_score,
            'ir_context_score': c.ir_context_score,
            'semantic_score': c.semantic_score
        })

    return ranked


def attribute_violation_cause(
    violation: Dict[str, Any],
    stack_trace: Optional[Dict[str, Any]] = None,
    application_ir=None
) -> Dict[str, Any]:
    """
    Convenience function for causal attribution.

    Args:
        violation: The smoke test violation
        stack_trace: Optional parsed stack trace
        application_ir: Optional ApplicationIR

    Returns:
        Dict with causal chain information
    """
    attributor = LightweightCausalAttributor()
    chain = attributor.attribute_failure(violation, stack_trace, application_ir)

    return {
        'failing_test': chain.failing_test,
        'error_type': chain.error_type,
        'ast_location': chain.ast_location,
        'ir_constraint': chain.ir_constraint,
        'generated_constraint': chain.generated_constraint,
        'root_cause': chain.root_cause,
        'confidence': chain.confidence
    }
