"""
ConfidenceScorer - Calculate confidence scores for atomic units

Weighted scoring algorithm for determining review priority:
- 40% Validation Score (L1-L4 pass rate)
- 30% Retry Penalty (more retries = lower confidence)
- 20% Complexity Penalty (higher complexity = lower confidence)
- 10% Test Coverage Score

Confidence Levels:
- muy_alta: score ≥ 90 (no review needed)
- alta: 75 ≤ score < 90 (spot check recommended)
- media: 60 ≤ score < 75 (review recommended)
- baja: score < 60 (mandatory review)

Target: Bottom 15-20% enter review queue (baja + some media)
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class ConfidenceLevel(str, Enum):
    """Confidence level classification"""
    MUY_ALTA = "muy_alta"  # ≥90 - no review needed
    ALTA = "alta"          # 75-89 - spot check recommended
    MEDIA = "media"        # 60-74 - review recommended
    BAJA = "baja"          # <60 - mandatory review


@dataclass
class ConfidenceScore:
    """Complete confidence score breakdown"""

    atom_id: UUID
    total_score: float  # 0-100
    level: ConfidenceLevel

    # Component scores (0-100 each)
    validation_score: float  # 40% weight
    retry_score: float       # 30% weight
    complexity_score: float  # 20% weight
    test_score: float        # 10% weight

    # Raw metrics for transparency
    validation_metrics: Dict
    retry_metrics: Dict
    complexity_metrics: Dict
    test_metrics: Dict

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage/serialization"""
        return {
            "atom_id": str(self.atom_id),
            "total_score": round(self.total_score, 2),
            "level": self.level.value,
            "components": {
                "validation_score": round(self.validation_score, 2),
                "retry_score": round(self.retry_score, 2),
                "complexity_score": round(self.complexity_score, 2),
                "test_score": round(self.test_score, 2)
            },
            "metrics": {
                "validation": self.validation_metrics,
                "retry": self.retry_metrics,
                "complexity": self.complexity_metrics,
                "test": self.test_metrics
            }
        }


class ConfidenceScorer:
    """
    Calculate confidence scores for atomic units

    Scoring Algorithm:
    1. Validation Score (40%): L1-L4 validation pass rate
    2. Retry Score (30%): Penalty for multiple retry attempts
    3. Complexity Score (20%): Penalty for high complexity
    4. Test Score (10%): Test coverage and pass rate

    Example:
        scorer = ConfidenceScorer()
        score = scorer.calculate_score(
            atom_id=atom.id,
            validation_results={...},
            retry_count=1,
            complexity_metrics={...},
            test_results={...}
        )

        if score.level in [ConfidenceLevel.BAJA, ConfidenceLevel.MEDIA]:
            # Add to review queue
    """

    def __init__(self):
        """Initialize confidence scorer with weights"""
        # Component weights (must sum to 1.0)
        self.weights = {
            "validation": 0.40,  # 40% - most critical
            "retry": 0.30,       # 30% - reliability indicator
            "complexity": 0.20,  # 20% - risk factor
            "test": 0.10         # 10% - quality assurance
        }

        # Confidence level thresholds
        self.thresholds = {
            ConfidenceLevel.MUY_ALTA: 90.0,  # ≥90
            ConfidenceLevel.ALTA: 75.0,       # 75-89
            ConfidenceLevel.MEDIA: 60.0,      # 60-74
            ConfidenceLevel.BAJA: 0.0         # <60
        }

    def calculate_score(
        self,
        atom_id: UUID,
        validation_results: Dict,
        retry_count: int,
        complexity_metrics: Dict,
        test_results: Optional[Dict] = None
    ) -> ConfidenceScore:
        """
        Calculate complete confidence score for atom

        Args:
            atom_id: Atom UUID
            validation_results: L1-L4 validation results
                {
                    "l1_syntax": bool,
                    "l2_imports": bool,
                    "l3_types": bool,
                    "l4_complexity": bool
                }
            retry_count: Number of retry attempts (0 = first attempt)
            complexity_metrics: Complexity analysis results
                {
                    "cyclomatic_complexity": int,
                    "cognitive_complexity": int,
                    "lines_of_code": int
                }
            test_results: Test execution results (optional)
                {
                    "tests_executed": int,
                    "tests_passed": int,
                    "coverage_percent": float
                }

        Returns:
            ConfidenceScore with breakdown and level
        """
        # Calculate component scores
        validation_score = self._calculate_validation_score(validation_results)
        retry_score = self._calculate_retry_score(retry_count)
        complexity_score = self._calculate_complexity_score(complexity_metrics)
        test_score = self._calculate_test_score(test_results)

        # Weighted total score
        total_score = (
            validation_score * self.weights["validation"] +
            retry_score * self.weights["retry"] +
            complexity_score * self.weights["complexity"] +
            test_score * self.weights["test"]
        )

        # Determine confidence level
        level = self._determine_level(total_score)

        logger.info(
            f"Confidence score calculated for {atom_id}: "
            f"{total_score:.2f} ({level.value}) "
            f"[val={validation_score:.1f}, retry={retry_score:.1f}, "
            f"complex={complexity_score:.1f}, test={test_score:.1f}]"
        )

        return ConfidenceScore(
            atom_id=atom_id,
            total_score=total_score,
            level=level,
            validation_score=validation_score,
            retry_score=retry_score,
            complexity_score=complexity_score,
            test_score=test_score,
            validation_metrics=validation_results,
            retry_metrics={"retry_count": retry_count},
            complexity_metrics=complexity_metrics,
            test_metrics=test_results or {}
        )

    def _calculate_validation_score(self, validation_results: Dict) -> float:
        """
        Calculate validation component score (0-100)

        L1-L4 validation levels with equal weight:
        - L1 Syntax: Basic Python syntax correctness
        - L2 Imports: Import resolution and availability
        - L3 Types: Type annotation correctness
        - L4 Complexity: Complexity within limits

        Score = (passed_levels / total_levels) * 100
        """
        levels = ["l1_syntax", "l2_imports", "l3_types", "l4_complexity"]

        passed = sum(1 for level in levels if validation_results.get(level, False))
        total = len(levels)

        score = (passed / total) * 100

        logger.debug(
            f"Validation score: {score:.2f} ({passed}/{total} levels passed)"
        )

        return score

    def _calculate_retry_score(self, retry_count: int) -> float:
        """
        Calculate retry penalty score (0-100)

        Exponential penalty for multiple retries:
        - 0 retries (first attempt): 100 points (perfect)
        - 1 retry: 80 points (-20%)
        - 2 retries: 60 points (-40%)
        - 3 retries: 40 points (-60%)
        - 4+ retries: 20 points (-80%)

        Formula: max(20, 100 - (retry_count * 20))
        """
        penalty_per_retry = 20
        min_score = 20

        score = max(min_score, 100 - (retry_count * penalty_per_retry))

        logger.debug(
            f"Retry score: {score:.2f} ({retry_count} retries, "
            f"penalty={retry_count * penalty_per_retry})"
        )

        return score

    def _calculate_complexity_score(self, complexity_metrics: Dict) -> float:
        """
        Calculate complexity penalty score (0-100)

        Penalizes high complexity as risk factor:
        - Cyclomatic complexity (50% weight)
        - Cognitive complexity (30% weight)
        - Lines of code (20% weight)

        Thresholds:
        - Cyclomatic: ≤10 = 100pts, >20 = 0pts (linear scale)
        - Cognitive: ≤15 = 100pts, >30 = 0pts (linear scale)
        - LOC: ≤100 = 100pts, >300 = 0pts (linear scale)
        """
        # Cyclomatic complexity score (50% weight)
        cyclomatic = complexity_metrics.get("cyclomatic_complexity", 0)
        cyclomatic_score = max(0, min(100, (1 - (cyclomatic - 10) / 10) * 100))

        # Cognitive complexity score (30% weight)
        cognitive = complexity_metrics.get("cognitive_complexity", 0)
        cognitive_score = max(0, min(100, (1 - (cognitive - 15) / 15) * 100))

        # Lines of code score (20% weight)
        loc = complexity_metrics.get("lines_of_code", 0)
        loc_score = max(0, min(100, (1 - (loc - 100) / 200) * 100))

        # Weighted total
        total_score = (
            cyclomatic_score * 0.50 +
            cognitive_score * 0.30 +
            loc_score * 0.20
        )

        logger.debug(
            f"Complexity score: {total_score:.2f} "
            f"[cyclo={cyclomatic_score:.1f}, cog={cognitive_score:.1f}, "
            f"loc={loc_score:.1f}]"
        )

        return total_score

    def _calculate_test_score(self, test_results: Optional[Dict]) -> float:
        """
        Calculate test quality score (0-100)

        If no tests: 50 points (neutral)
        If tests available:
        - Pass rate (70% weight): (tests_passed / tests_executed) * 100
        - Coverage (30% weight): coverage_percent

        Score = (pass_rate * 0.7) + (coverage * 0.3)
        """
        if not test_results:
            # No tests = neutral score (50 points)
            logger.debug("Test score: 50.00 (no tests available)")
            return 50.0

        tests_executed = test_results.get("tests_executed", 0)
        tests_passed = test_results.get("tests_passed", 0)
        coverage = test_results.get("coverage_percent", 0.0)

        if tests_executed == 0:
            # Tests defined but not executed = 50 points (neutral)
            return 50.0

        # Pass rate score (70% weight)
        pass_rate = (tests_passed / tests_executed) * 100
        pass_score = pass_rate * 0.70

        # Coverage score (30% weight)
        coverage_score = coverage * 0.30

        total_score = pass_score + coverage_score

        logger.debug(
            f"Test score: {total_score:.2f} "
            f"[pass_rate={pass_rate:.1f}%, coverage={coverage:.1f}%]"
        )

        return total_score

    def _determine_level(self, total_score: float) -> ConfidenceLevel:
        """
        Determine confidence level from total score

        Thresholds:
        - muy_alta: score ≥ 90
        - alta: 75 ≤ score < 90
        - media: 60 ≤ score < 75
        - baja: score < 60
        """
        if total_score >= self.thresholds[ConfidenceLevel.MUY_ALTA]:
            return ConfidenceLevel.MUY_ALTA
        elif total_score >= self.thresholds[ConfidenceLevel.ALTA]:
            return ConfidenceLevel.ALTA
        elif total_score >= self.thresholds[ConfidenceLevel.MEDIA]:
            return ConfidenceLevel.MEDIA
        else:
            return ConfidenceLevel.BAJA

    def should_enter_review_queue(self, score: ConfidenceScore) -> bool:
        """
        Determine if atom should enter human review queue

        Review criteria:
        - baja (score < 60): Always review (mandatory)
        - media (60 ≤ score < 75): Review recommended
        - alta (75 ≤ score < 90): Spot check only (skip queue)
        - muy_alta (score ≥ 90): Skip review entirely

        Target: Bottom 15-20% in review queue
        """
        return score.level in [ConfidenceLevel.BAJA, ConfidenceLevel.MEDIA]
