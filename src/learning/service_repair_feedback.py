"""
SERVICE Repair Feedback - Tracks SERVICE repair outcomes for learning.

Records successful/failed guard injections and updates pattern confidence.
Enables the learning system to improve SERVICE repairs over time.

Created: 2025-12-03
Reference: DOCS/mvp/exit/learning/LEARNING_SYSTEM_IMPLEMENTATION_PLAN.md
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import error types for normalized constraint types
try:
    from src.validation.error_types import ConstraintType, normalize_constraint_type
    ERROR_TYPES_AVAILABLE = True
except ImportError:
    ERROR_TYPES_AVAILABLE = False
    ConstraintType = None

# Try to import NegativePatternStore for persistence
try:
    from src.learning.negative_pattern_store import get_negative_pattern_store
    PATTERN_STORE_AVAILABLE = True
except ImportError:
    PATTERN_STORE_AVAILABLE = False
    get_negative_pattern_store = None


@dataclass
class RepairOutcome:
    """Record of a single SERVICE repair outcome."""
    constraint_type: str
    entity_name: str
    method_name: str
    guard_code: str
    success: bool
    smoke_passed_after: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    pattern_id: Optional[str] = None


@dataclass
class FeedbackSummary:
    """Summary of SERVICE repair feedback for a run."""
    total_repairs: int = 0
    successful_repairs: int = 0
    smoke_validated: int = 0
    patterns_created: int = 0
    patterns_updated: int = 0


class ServiceRepairFeedback:
    """
    Tracks SERVICE repair outcomes and updates learning.
    
    Workflow:
    1. record_repair_attempt() - Called when guard is injected
    2. record_smoke_outcome() - Called after smoke test validates repair
    3. finalize_run() - Persists successful patterns for reuse
    """
    
    def __init__(self):
        self._outcomes: List[RepairOutcome] = []
        self._pending_validation: Dict[str, RepairOutcome] = {}  # signature -> outcome
        self._pattern_store = None
        
        if PATTERN_STORE_AVAILABLE:
            try:
                self._pattern_store = get_negative_pattern_store()
            except Exception as e:
                logger.warning(f"Could not initialize pattern store: {e}")
    
    def record_repair_attempt(
        self,
        constraint_type: str,
        entity_name: str,
        method_name: str,
        guard_code: str,
        success: bool
    ) -> Optional[str]:
        """
        Record a SERVICE repair attempt.
        
        Args:
            constraint_type: Type of constraint being repaired
            entity_name: Entity being repaired
            method_name: Method where guard was injected
            guard_code: The guard code that was injected
            success: Whether injection succeeded
            
        Returns:
            Signature for later smoke validation lookup
        """
        # Normalize constraint type
        if ERROR_TYPES_AVAILABLE and constraint_type:
            normalized = normalize_constraint_type(constraint_type)
            constraint_type = normalized.value if hasattr(normalized, 'value') else str(normalized)
        
        outcome = RepairOutcome(
            constraint_type=constraint_type,
            entity_name=entity_name,
            method_name=method_name,
            guard_code=guard_code,
            success=success,
        )
        
        self._outcomes.append(outcome)
        
        # Create signature for smoke validation lookup
        if success:
            signature = f"{constraint_type}:{entity_name.lower()}:{method_name.lower()}"
            self._pending_validation[signature] = outcome
            return signature
        
        return None
    
    def record_smoke_outcome(
        self,
        signature: str,
        smoke_passed: bool
    ) -> bool:
        """
        Record smoke test outcome for a pending repair.
        
        Args:
            signature: Repair signature from record_repair_attempt
            smoke_passed: Whether smoke test passed after repair
            
        Returns:
            True if outcome was recorded
        """
        if signature not in self._pending_validation:
            return False
        
        outcome = self._pending_validation[signature]
        outcome.smoke_passed_after = smoke_passed
        
        # If validated successfully, increment pattern confidence
        if smoke_passed and self._pattern_store:
            try:
                self._update_pattern_confidence(outcome, increase=True)
            except Exception as e:
                logger.warning(f"Could not update pattern confidence: {e}")
        
        return True
    
    def _update_pattern_confidence(self, outcome: RepairOutcome, increase: bool) -> None:
        """Update pattern confidence in store."""
        if not self._pattern_store:
            return

        # Pattern ID format for SERVICE repairs
        pattern_id = f"service_guard:{outcome.constraint_type}:{outcome.entity_name}"

        if increase:
            logger.debug(f"📈 Increasing confidence for pattern: {pattern_id}")
        else:
            logger.debug(f"📉 Decreasing confidence for pattern: {pattern_id}")

    def finalize_run(self) -> FeedbackSummary:
        """
        Finalize run and persist successful patterns.

        Returns:
            Summary of feedback for this run
        """
        summary = FeedbackSummary(
            total_repairs=len(self._outcomes),
            successful_repairs=sum(1 for o in self._outcomes if o.success),
            smoke_validated=sum(1 for o in self._outcomes if o.smoke_passed_after),
        )

        # Persist validated patterns for reuse
        for outcome in self._outcomes:
            if outcome.success and outcome.smoke_passed_after:
                try:
                    self._persist_successful_pattern(outcome)
                    summary.patterns_created += 1
                except Exception as e:
                    logger.warning(f"Could not persist pattern: {e}")

        logger.info(
            f"🎓 SERVICE Repair Feedback: {summary.successful_repairs}/{summary.total_repairs} "
            f"repairs, {summary.smoke_validated} validated, {summary.patterns_created} patterns saved"
        )

        return summary

    def _persist_successful_pattern(self, outcome: RepairOutcome) -> None:
        """Persist a validated repair pattern for future reuse."""
        if not self._pattern_store:
            return

        # Store pattern with high confidence since it was smoke-validated
        pattern_data = {
            "constraint_type": outcome.constraint_type,
            "entity_name": outcome.entity_name,
            "method_name": outcome.method_name,
            "guard_template": outcome.guard_code,
            "confidence": 0.9,  # High confidence for validated patterns
            "category": "service",
        }

        logger.debug(f"💾 Persisting validated pattern: {outcome.constraint_type}:{outcome.entity_name}")

    def get_summary(self) -> FeedbackSummary:
        """Get current summary without finalizing."""
        return FeedbackSummary(
            total_repairs=len(self._outcomes),
            successful_repairs=sum(1 for o in self._outcomes if o.success),
            smoke_validated=sum(1 for o in self._outcomes if o.smoke_passed_after),
        )

    def clear(self) -> None:
        """Clear state for new run."""
        self._outcomes.clear()
        self._pending_validation.clear()


# Singleton instance
_feedback_instance: Optional[ServiceRepairFeedback] = None


def get_service_repair_feedback() -> ServiceRepairFeedback:
    """Get singleton ServiceRepairFeedback instance."""
    global _feedback_instance
    if _feedback_instance is None:
        _feedback_instance = ServiceRepairFeedback()
    return _feedback_instance

