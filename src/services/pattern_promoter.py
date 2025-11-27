"""
Pattern Promoter - Stratum Graduation System (Phase 7 Enhanced)

Manages the promotion flow: LLM → AST → TEMPLATE

Patterns start in LLM stratum (lowest trust) and graduate based on:
1. Success rate over multiple runs
2. No regressions detected
3. Code stability (no changes needed)
4. Human review (for TEMPLATE promotion)
5. Semantic compliance scores (Phase 7)
6. Golden app validation (Phase 7)
7. Cross-project validation (Phase 7)

Design: Conservative promotion, aggressive demotion.

Phase 7 Additions:
- Formal numeric criteria for LLM→AST and AST→TEMPLATE
- Golden app regression tracking
- Cross-project usage tracking
- Semantic compliance thresholds
"""

import logging
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.services.stratum_classification import Stratum
from src.services.regression_detector import (
    RegressionDetector,
    get_regression_detector,
    BugSeverity,
)

logger = logging.getLogger(__name__)


class PromotionStatus(str, Enum):
    """Status of a promotion request."""
    APPROVED = "approved"
    DENIED = "denied"
    PENDING_REVIEW = "pending_review"
    NEEDS_MORE_DATA = "needs_more_data"


@dataclass
class PromotionCriteria:
    """Criteria for stratum promotion."""
    min_success_rate: float
    min_runs: int
    max_regressions: int
    requires_human_review: bool
    stability_days: int  # Days without code changes


@dataclass
class FormalPromotionCriteria:
    """
    Phase 7: Formal numeric criteria for stratum promotion.

    These are the production-grade requirements that patterns must meet
    to graduate between strata. More strict than basic PromotionCriteria.
    """
    min_distinct_projects: int          # Number of unique projects validated
    min_semantic_compliance: float      # Minimum semantic compliance score (0.0-1.0)
    max_regressions_golden_apps: int    # Max regressions in golden apps
    min_successful_runs: int            # Minimum successful runs
    max_generation_time_variance: float # Maximum time variance (0.0-1.0 = 0-100%)
    requires_no_project_context: bool   # Must work without project-specific context
    description: str                    # Human-readable description


# Phase 7: Formal promotion criteria by target transition
PROMOTION_CRITERIA_FORMAL: Dict[str, FormalPromotionCriteria] = {
    "llm_to_ast": FormalPromotionCriteria(
        min_distinct_projects=3,
        min_semantic_compliance=1.00,       # 100% semantic compliance required
        max_regressions_golden_apps=0,
        min_successful_runs=10,
        max_generation_time_variance=0.50,  # 50% variance allowed (LLM is variable)
        requires_no_project_context=False,  # May use project context
        description="Pattern validated in 3+ distinct projects, 100% compliance, 0 golden app regressions"
    ),
    "ast_to_template": FormalPromotionCriteria(
        min_distinct_projects=5,
        min_semantic_compliance=1.00,       # Perfect compliance
        max_regressions_golden_apps=0,
        min_successful_runs=50,
        max_generation_time_variance=0.10,  # 10% variance max (deterministic)
        requires_no_project_context=True,   # Must be context-independent
        description="10+ uses in production, 0 bugs, stable times, no project context needed"
    ),
}


@dataclass
class PatternMetrics:
    """Metrics for a pattern candidate."""
    pattern_id: str
    file_path: str
    current_stratum: Stratum
    success_rate: float
    total_runs: int
    successful_runs: int
    failed_runs: int
    regression_count: int
    last_modified: datetime
    last_failure: Optional[datetime] = None
    code_hash: Optional[str] = None

    # Phase 7: Extended metrics
    distinct_projects: Set[str] = field(default_factory=set)
    semantic_compliance_scores: List[float] = field(default_factory=list)
    golden_app_regressions: int = 0
    generation_times: List[float] = field(default_factory=list)
    uses_project_context: bool = True

    @property
    def distinct_project_count(self) -> int:
        """Number of distinct projects this pattern was validated in."""
        return len(self.distinct_projects)

    @property
    def avg_semantic_compliance(self) -> float:
        """Average semantic compliance score."""
        if not self.semantic_compliance_scores:
            return 0.0
        return sum(self.semantic_compliance_scores) / len(self.semantic_compliance_scores)

    @property
    def min_semantic_compliance(self) -> float:
        """Minimum semantic compliance score (worst case)."""
        if not self.semantic_compliance_scores:
            return 0.0
        return min(self.semantic_compliance_scores)

    @property
    def generation_time_variance(self) -> float:
        """Variance in generation times (0.0-1.0)."""
        if len(self.generation_times) < 2:
            return 0.0
        avg = sum(self.generation_times) / len(self.generation_times)
        if avg == 0:
            return 0.0
        variance = sum((t - avg) ** 2 for t in self.generation_times) / len(self.generation_times)
        std_dev = variance ** 0.5
        return std_dev / avg  # Coefficient of variation


@dataclass
class PromotionResult:
    """Result of a promotion evaluation."""
    pattern_id: str
    current_stratum: Stratum
    target_stratum: Stratum
    status: PromotionStatus
    reasons: List[str] = field(default_factory=list)
    blocking_issues: List[str] = field(default_factory=list)


# =============================================================================
# PROMOTION CRITERIA BY TARGET STRATUM
# =============================================================================

PROMOTION_CRITERIA: Dict[Stratum, PromotionCriteria] = {
    # LLM → AST: Moderate requirements
    Stratum.AST: PromotionCriteria(
        min_success_rate=0.95,      # 95% success rate
        min_runs=10,                 # At least 10 runs
        max_regressions=0,           # No regressions allowed
        requires_human_review=False, # Automatic promotion allowed
        stability_days=3,            # 3 days without changes
    ),

    # AST → TEMPLATE: Strict requirements
    Stratum.TEMPLATE: PromotionCriteria(
        min_success_rate=0.99,      # 99% success rate
        min_runs=50,                 # At least 50 runs
        max_regressions=0,           # Zero tolerance
        requires_human_review=True,  # Human must approve
        stability_days=14,           # 2 weeks stability
    ),
}

# Demotion thresholds (more aggressive)
DEMOTION_THRESHOLDS = {
    "failure_rate": 0.10,     # >10% failures triggers demotion
    "regression_count": 1,    # Any regression triggers demotion
    "recent_failures": 3,     # 3 failures in last 10 runs
}


class PatternPromoter:
    """
    Manages pattern promotion between strata.

    Flow: LLM → AST → TEMPLATE

    Principles:
    - Conservative promotion (earn trust slowly)
    - Aggressive demotion (lose trust quickly)
    - Zero regression tolerance for promotion
    - Human review required for TEMPLATE
    """

    def __init__(self):
        self.regression_detector = get_regression_detector()
        self._pattern_metrics: Dict[str, PatternMetrics] = {}
        self._promotion_history: List[PromotionResult] = []

    def evaluate_promotion(
        self,
        pattern_id: str,
        code: str,
        file_path: str,
        metrics: PatternMetrics
    ) -> PromotionResult:
        """
        Evaluate if a pattern is eligible for promotion.

        Args:
            pattern_id: Unique pattern identifier
            code: Current code content
            file_path: File path of the pattern
            metrics: Current metrics for the pattern

        Returns:
            PromotionResult with status and reasons
        """
        current = metrics.current_stratum
        target = self._get_next_stratum(current)

        if target is None:
            return PromotionResult(
                pattern_id=pattern_id,
                current_stratum=current,
                target_stratum=current,
                status=PromotionStatus.DENIED,
                reasons=["Already at highest stratum (TEMPLATE)"],
            )

        criteria = PROMOTION_CRITERIA[target]
        blocking = []
        reasons = []

        # Check 1: Minimum runs
        if metrics.total_runs < criteria.min_runs:
            blocking.append(
                f"Insufficient runs: {metrics.total_runs}/{criteria.min_runs}"
            )

        # Check 2: Success rate
        if metrics.success_rate < criteria.min_success_rate:
            blocking.append(
                f"Success rate too low: {metrics.success_rate:.1%} < {criteria.min_success_rate:.1%}"
            )
        else:
            reasons.append(f"Success rate: {metrics.success_rate:.1%} ✓")

        # Check 3: Regression scan
        is_clean, regressions = self.regression_detector.check_promotion_eligibility(
            code, file_path
        )
        if not is_clean:
            blocking.append(
                f"Regressions detected: {len(regressions)} bugs found"
            )
        else:
            reasons.append("No regressions detected ✓")

        # Check 4: Historical regressions
        if metrics.regression_count > criteria.max_regressions:
            blocking.append(
                f"Too many historical regressions: {metrics.regression_count}"
            )

        # Check 5: Stability period
        days_since_modified = (datetime.now() - metrics.last_modified).days
        if days_since_modified < criteria.stability_days:
            blocking.append(
                f"Not stable enough: {days_since_modified}/{criteria.stability_days} days"
            )
        else:
            reasons.append(f"Stable for {days_since_modified} days ✓")

        # Check 6: Human review requirement
        if criteria.requires_human_review:
            if blocking:
                status = PromotionStatus.DENIED
            else:
                status = PromotionStatus.PENDING_REVIEW
                reasons.append("Awaiting human review")
        else:
            status = PromotionStatus.APPROVED if not blocking else PromotionStatus.DENIED

        result = PromotionResult(
            pattern_id=pattern_id,
            current_stratum=current,
            target_stratum=target,
            status=status,
            reasons=reasons,
            blocking_issues=blocking,
        )

        self._promotion_history.append(result)

        # Log result
        if status == PromotionStatus.APPROVED:
            logger.info(
                f"✅ PROMOTION APPROVED: {pattern_id}\n"
                f"   {current.value} → {target.value}\n"
                f"   Reasons: {reasons}"
            )
        elif status == PromotionStatus.PENDING_REVIEW:
            logger.info(
                f"⏳ PENDING REVIEW: {pattern_id}\n"
                f"   {current.value} → {target.value}\n"
                f"   Needs human approval"
            )
        else:
            logger.warning(
                f"❌ PROMOTION DENIED: {pattern_id}\n"
                f"   {current.value} → {target.value}\n"
                f"   Blocking: {blocking}"
            )

        return result

    def evaluate_formal_promotion(
        self,
        pattern_id: str,
        metrics: PatternMetrics,
    ) -> PromotionResult:
        """
        Phase 7: Evaluate promotion using formal numeric criteria.

        This is the production-grade promotion evaluation that uses
        strict numeric thresholds for cross-project validation,
        semantic compliance, and golden app regressions.

        Args:
            pattern_id: Pattern identifier
            metrics: Extended metrics with Phase 7 fields

        Returns:
            PromotionResult with detailed status
        """
        current = metrics.current_stratum
        target = self._get_next_stratum(current)

        if target is None:
            return PromotionResult(
                pattern_id=pattern_id,
                current_stratum=current,
                target_stratum=current,
                status=PromotionStatus.DENIED,
                reasons=["Already at highest stratum (TEMPLATE)"],
            )

        # Get formal criteria for this transition
        transition_key = f"{current.value}_to_{target.value}"
        formal_criteria = PROMOTION_CRITERIA_FORMAL.get(transition_key)

        if not formal_criteria:
            # Fall back to basic evaluation
            return self.evaluate_promotion(
                pattern_id, "", metrics.file_path, metrics
            )

        blocking = []
        reasons = []

        # Check 1: Distinct projects
        if metrics.distinct_project_count < formal_criteria.min_distinct_projects:
            blocking.append(
                f"Insufficient projects: {metrics.distinct_project_count}/{formal_criteria.min_distinct_projects}"
            )
        else:
            reasons.append(f"Validated in {metrics.distinct_project_count} projects ✓")

        # Check 2: Semantic compliance (use minimum, not average)
        if metrics.min_semantic_compliance < formal_criteria.min_semantic_compliance:
            blocking.append(
                f"Semantic compliance too low: {metrics.min_semantic_compliance:.1%} < {formal_criteria.min_semantic_compliance:.1%}"
            )
        else:
            reasons.append(f"Semantic compliance: {metrics.min_semantic_compliance:.1%} ✓")

        # Check 3: Golden app regressions
        if metrics.golden_app_regressions > formal_criteria.max_regressions_golden_apps:
            blocking.append(
                f"Golden app regressions: {metrics.golden_app_regressions} (max: {formal_criteria.max_regressions_golden_apps})"
            )
        else:
            reasons.append(f"Zero golden app regressions ✓")

        # Check 4: Successful runs
        if metrics.successful_runs < formal_criteria.min_successful_runs:
            blocking.append(
                f"Insufficient runs: {metrics.successful_runs}/{formal_criteria.min_successful_runs}"
            )
        else:
            reasons.append(f"Successful runs: {metrics.successful_runs} ✓")

        # Check 5: Generation time variance
        if metrics.generation_time_variance > formal_criteria.max_generation_time_variance:
            blocking.append(
                f"Time variance too high: {metrics.generation_time_variance:.1%} > {formal_criteria.max_generation_time_variance:.1%}"
            )
        else:
            reasons.append(f"Time variance: {metrics.generation_time_variance:.1%} ✓")

        # Check 6: Project context independence (for TEMPLATE)
        if formal_criteria.requires_no_project_context and metrics.uses_project_context:
            blocking.append(
                "Pattern still uses project-specific context"
            )
        elif not formal_criteria.requires_no_project_context:
            reasons.append("Project context: allowed ✓")
        else:
            reasons.append("Context-independent ✓")

        # Determine status
        if blocking:
            status = PromotionStatus.DENIED
        elif target == Stratum.TEMPLATE:
            status = PromotionStatus.PENDING_REVIEW
            reasons.append("Requires human review for TEMPLATE promotion")
        else:
            status = PromotionStatus.APPROVED

        result = PromotionResult(
            pattern_id=pattern_id,
            current_stratum=current,
            target_stratum=target,
            status=status,
            reasons=reasons,
            blocking_issues=blocking,
        )

        self._promotion_history.append(result)

        # Log with formal criteria context
        criteria_desc = formal_criteria.description
        if status == PromotionStatus.APPROVED:
            logger.info(
                f"✅ FORMAL PROMOTION APPROVED: {pattern_id}\n"
                f"   {current.value} → {target.value}\n"
                f"   Criteria: {criteria_desc}\n"
                f"   Reasons: {reasons}"
            )
        elif status == PromotionStatus.PENDING_REVIEW:
            logger.info(
                f"⏳ FORMAL PROMOTION PENDING: {pattern_id}\n"
                f"   {current.value} → {target.value}\n"
                f"   Criteria: {criteria_desc}\n"
                f"   Awaiting human review"
            )
        else:
            logger.warning(
                f"❌ FORMAL PROMOTION DENIED: {pattern_id}\n"
                f"   {current.value} → {target.value}\n"
                f"   Criteria: {criteria_desc}\n"
                f"   Blocking: {blocking}"
            )

        return result

    def record_extended_metrics(
        self,
        pattern_id: str,
        project_name: str,
        semantic_compliance: float,
        generation_time: float,
        golden_app_regression: bool = False,
    ) -> PatternMetrics:
        """
        Phase 7: Record extended metrics for a pattern.

        Args:
            pattern_id: Pattern identifier
            project_name: Name of the project this run was for
            semantic_compliance: Compliance score (0.0-1.0)
            generation_time: Time taken to generate (seconds)
            golden_app_regression: Whether a golden app regression was detected

        Returns:
            Updated metrics
        """
        if pattern_id not in self._pattern_metrics:
            raise ValueError(f"Pattern not found: {pattern_id}")

        metrics = self._pattern_metrics[pattern_id]

        # Update Phase 7 fields
        metrics.distinct_projects.add(project_name)
        metrics.semantic_compliance_scores.append(semantic_compliance)
        metrics.generation_times.append(generation_time)

        if golden_app_regression:
            metrics.golden_app_regressions += 1

        return metrics

    def get_formal_promotion_report(self, pattern_id: str) -> Dict:
        """
        Generate a detailed promotion eligibility report.

        Returns dict with current status and requirements to meet.
        """
        if pattern_id not in self._pattern_metrics:
            return {"error": f"Pattern not found: {pattern_id}"}

        metrics = self._pattern_metrics[pattern_id]
        current = metrics.current_stratum
        target = self._get_next_stratum(current)

        if target is None:
            return {
                "pattern_id": pattern_id,
                "current_stratum": current.value,
                "status": "MAXIMUM_STRATUM",
                "message": "Already at TEMPLATE stratum"
            }

        transition_key = f"{current.value}_to_{target.value}"
        criteria = PROMOTION_CRITERIA_FORMAL.get(transition_key)

        if not criteria:
            return {
                "pattern_id": pattern_id,
                "current_stratum": current.value,
                "target_stratum": target.value,
                "status": "NO_FORMAL_CRITERIA",
            }

        return {
            "pattern_id": pattern_id,
            "current_stratum": current.value,
            "target_stratum": target.value,
            "criteria_description": criteria.description,
            "current_values": {
                "distinct_projects": metrics.distinct_project_count,
                "min_semantic_compliance": metrics.min_semantic_compliance,
                "golden_app_regressions": metrics.golden_app_regressions,
                "successful_runs": metrics.successful_runs,
                "generation_time_variance": metrics.generation_time_variance,
                "uses_project_context": metrics.uses_project_context,
            },
            "required_values": {
                "min_distinct_projects": criteria.min_distinct_projects,
                "min_semantic_compliance": criteria.min_semantic_compliance,
                "max_regressions_golden_apps": criteria.max_regressions_golden_apps,
                "min_successful_runs": criteria.min_successful_runs,
                "max_generation_time_variance": criteria.max_generation_time_variance,
                "requires_no_project_context": criteria.requires_no_project_context,
            },
            "gaps": {
                "projects_needed": max(0, criteria.min_distinct_projects - metrics.distinct_project_count),
                "compliance_gap": max(0, criteria.min_semantic_compliance - metrics.min_semantic_compliance),
                "runs_needed": max(0, criteria.min_successful_runs - metrics.successful_runs),
            }
        }

    def evaluate_demotion(
        self,
        pattern_id: str,
        metrics: PatternMetrics,
        recent_results: List[bool]  # Last N run results (True=success)
    ) -> Optional[Stratum]:
        """
        Evaluate if a pattern should be demoted.

        Args:
            pattern_id: Pattern identifier
            metrics: Current metrics
            recent_results: Recent run results (True=success, False=failure)

        Returns:
            Target stratum if demotion needed, None otherwise
        """
        current = metrics.current_stratum

        # Can't demote from LLM (already lowest)
        if current == Stratum.LLM:
            return None

        demote = False
        reason = ""

        # Check 1: Overall failure rate
        if metrics.total_runs > 0:
            failure_rate = metrics.failed_runs / metrics.total_runs
            if failure_rate > DEMOTION_THRESHOLDS["failure_rate"]:
                demote = True
                reason = f"High failure rate: {failure_rate:.1%}"

        # Check 2: Regression count
        if metrics.regression_count >= DEMOTION_THRESHOLDS["regression_count"]:
            demote = True
            reason = f"Regressions detected: {metrics.regression_count}"

        # Check 3: Recent failures
        if len(recent_results) >= 10:
            recent_failures = sum(1 for r in recent_results[-10:] if not r)
            if recent_failures >= DEMOTION_THRESHOLDS["recent_failures"]:
                demote = True
                reason = f"Recent failures: {recent_failures}/10"

        if demote:
            target = self._get_previous_stratum(current)
            logger.warning(
                f"⬇️ DEMOTION TRIGGERED: {pattern_id}\n"
                f"   {current.value} → {target.value}\n"
                f"   Reason: {reason}"
            )
            return target

        return None

    def record_run_result(
        self,
        pattern_id: str,
        file_path: str,
        success: bool,
        had_regression: bool = False
    ) -> PatternMetrics:
        """
        Record a run result for a pattern.

        Args:
            pattern_id: Pattern identifier
            file_path: File path
            success: Whether the run succeeded
            had_regression: Whether a regression was detected

        Returns:
            Updated metrics
        """
        if pattern_id not in self._pattern_metrics:
            # Initialize metrics
            self._pattern_metrics[pattern_id] = PatternMetrics(
                pattern_id=pattern_id,
                file_path=file_path,
                current_stratum=Stratum.LLM,  # Start at lowest
                success_rate=0.0,
                total_runs=0,
                successful_runs=0,
                failed_runs=0,
                regression_count=0,
                last_modified=datetime.now(),
            )

        metrics = self._pattern_metrics[pattern_id]

        # Update counts
        metrics.total_runs += 1
        if success:
            metrics.successful_runs += 1
        else:
            metrics.failed_runs += 1
            metrics.last_failure = datetime.now()

        if had_regression:
            metrics.regression_count += 1

        # Recalculate success rate
        metrics.success_rate = metrics.successful_runs / metrics.total_runs

        return metrics

    def promote_pattern(
        self,
        pattern_id: str,
        target_stratum: Stratum
    ) -> bool:
        """
        Execute pattern promotion.

        Args:
            pattern_id: Pattern to promote
            target_stratum: Target stratum

        Returns:
            True if promotion was executed
        """
        if pattern_id not in self._pattern_metrics:
            logger.error(f"Pattern not found: {pattern_id}")
            return False

        metrics = self._pattern_metrics[pattern_id]
        old_stratum = metrics.current_stratum

        if self._stratum_order(target_stratum) <= self._stratum_order(old_stratum):
            logger.error(
                f"Invalid promotion: {old_stratum.value} → {target_stratum.value}"
            )
            return False

        metrics.current_stratum = target_stratum
        logger.info(
            f"🎉 PROMOTED: {pattern_id}\n"
            f"   {old_stratum.value} → {target_stratum.value}"
        )

        return True

    def demote_pattern(
        self,
        pattern_id: str,
        target_stratum: Stratum
    ) -> bool:
        """
        Execute pattern demotion.

        Args:
            pattern_id: Pattern to demote
            target_stratum: Target stratum

        Returns:
            True if demotion was executed
        """
        if pattern_id not in self._pattern_metrics:
            logger.error(f"Pattern not found: {pattern_id}")
            return False

        metrics = self._pattern_metrics[pattern_id]
        old_stratum = metrics.current_stratum

        if self._stratum_order(target_stratum) >= self._stratum_order(old_stratum):
            logger.error(
                f"Invalid demotion: {old_stratum.value} → {target_stratum.value}"
            )
            return False

        metrics.current_stratum = target_stratum
        logger.warning(
            f"⬇️ DEMOTED: {pattern_id}\n"
            f"   {old_stratum.value} → {target_stratum.value}"
        )

        return True

    def get_promotion_candidates(
        self,
        target_stratum: Stratum
    ) -> List[PatternMetrics]:
        """
        Get patterns that might be ready for promotion.

        Args:
            target_stratum: Target stratum to promote to

        Returns:
            List of candidate patterns
        """
        candidates = []
        criteria = PROMOTION_CRITERIA.get(target_stratum)

        if not criteria:
            return candidates

        prev_stratum = self._get_previous_stratum(target_stratum)

        for metrics in self._pattern_metrics.values():
            # Must be at previous stratum
            if metrics.current_stratum != prev_stratum:
                continue

            # Quick eligibility check (without full regression scan)
            if metrics.total_runs >= criteria.min_runs and \
               metrics.success_rate >= criteria.min_success_rate * 0.95:  # 95% of threshold
                candidates.append(metrics)

        return candidates

    def get_stratum_distribution(self) -> Dict[str, int]:
        """Get count of patterns in each stratum."""
        distribution = {s.value: 0 for s in Stratum}

        for metrics in self._pattern_metrics.values():
            distribution[metrics.current_stratum.value] += 1

        return distribution

    def _get_next_stratum(self, current: Stratum) -> Optional[Stratum]:
        """Get next stratum in promotion order."""
        order = [Stratum.LLM, Stratum.AST, Stratum.TEMPLATE]
        try:
            idx = order.index(current)
            return order[idx + 1] if idx + 1 < len(order) else None
        except ValueError:
            return None

    def _get_previous_stratum(self, current: Stratum) -> Optional[Stratum]:
        """Get previous stratum in promotion order."""
        order = [Stratum.LLM, Stratum.AST, Stratum.TEMPLATE]
        try:
            idx = order.index(current)
            return order[idx - 1] if idx > 0 else None
        except ValueError:
            return None

    def _stratum_order(self, stratum: Stratum) -> int:
        """Get numeric order of stratum (higher = more trusted)."""
        order = {Stratum.LLM: 0, Stratum.AST: 1, Stratum.TEMPLATE: 2}
        return order.get(stratum, -1)


# Singleton instance
_promoter: Optional[PatternPromoter] = None


def get_pattern_promoter() -> PatternPromoter:
    """Get singleton PatternPromoter instance."""
    global _promoter
    if _promoter is None:
        _promoter = PatternPromoter()
    return _promoter
