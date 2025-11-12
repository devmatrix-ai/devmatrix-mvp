"""
PrecisionScorer - Calculate composite precision score

Precision Score = 50% Spec Conformance + 30% Integration Pass + 20% Validation Pass

Components:
- Spec Conformance: Percentage of requirements met (must/should)
- Integration Pass: Percentage of integration tests passing
- Validation Pass: Percentage of L1-L4 validations passing

Target: ≥98% precision sustained over 2 consecutive weeks
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class RequirementPriority(Enum):
    """Requirement priority levels"""
    MUST = "must"  # Mandatory - 100% required
    SHOULD = "should"  # Important - ≥95% required
    COULD = "could"  # Optional - nice to have
    WONT = "wont"  # Future scope - not counted


class ValidationLevel(Enum):
    """Validation levels"""
    L1_SYNTAX = "l1_syntax"
    L2_IMPORTS = "l2_imports"
    L3_TYPES = "l3_types"
    L4_COMPLEXITY = "l4_complexity"


@dataclass
class RequirementResult:
    """Result of a single requirement check"""
    requirement_id: str
    priority: RequirementPriority
    passed: bool
    test_ids: List[str]  # IDs of acceptance tests for this requirement
    description: str


@dataclass
class IntegrationResult:
    """Result of integration tests"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    pass_rate: float

    def __post_init__(self):
        if self.total_tests > 0:
            self.pass_rate = self.passed_tests / self.total_tests
        else:
            self.pass_rate = 0.0


@dataclass
class ValidationResult:
    """Result of validation checks"""
    level: ValidationLevel
    total_checks: int
    passed_checks: int
    failed_checks: int
    pass_rate: float

    def __post_init__(self):
        if self.total_checks > 0:
            self.pass_rate = self.passed_checks / self.total_checks
        else:
            self.pass_rate = 1.0  # No checks = pass


@dataclass
class PrecisionScore:
    """
    Composite precision score

    Score = 50% spec_conformance + 30% integration_pass + 20% validation_pass
    """

    masterplan_id: UUID

    # Component scores (0-100)
    spec_conformance_score: float
    integration_pass_score: float
    validation_pass_score: float

    # Composite score (0-100)
    total_score: float

    # Component details
    spec_conformance_details: Dict
    integration_details: Dict
    validation_details: Dict

    # Target: ≥98%
    meets_target: bool

    def __post_init__(self):
        """Calculate composite score and check target"""
        self.total_score = (
            self.spec_conformance_score * 0.50 +
            self.integration_pass_score * 0.30 +
            self.validation_pass_score * 0.20
        )
        self.meets_target = self.total_score >= 98.0

    def to_dict(self) -> Dict:
        """Convert to dictionary for API/storage"""
        return {
            "masterplan_id": str(self.masterplan_id),
            "total_score": round(self.total_score, 2),
            "meets_target": self.meets_target,
            "components": {
                "spec_conformance": {
                    "score": round(self.spec_conformance_score, 2),
                    "weight": 0.50,
                    "details": self.spec_conformance_details
                },
                "integration_pass": {
                    "score": round(self.integration_pass_score, 2),
                    "weight": 0.30,
                    "details": self.integration_details
                },
                "validation_pass": {
                    "score": round(self.validation_pass_score, 2),
                    "weight": 0.20,
                    "details": self.validation_details
                }
            }
        }


class PrecisionScorer:
    """
    Calculate composite precision score

    Example:
        scorer = PrecisionScorer()

        # Add requirement results
        req_results = [
            RequirementResult("REQ-001", RequirementPriority.MUST, True, ["TEST-001"], "Login"),
            RequirementResult("REQ-002", RequirementPriority.SHOULD, False, ["TEST-002"], "2FA")
        ]

        # Add integration results
        integration = IntegrationResult(
            total_tests=50, passed_tests=48, failed_tests=2, skipped_tests=0, pass_rate=0.96
        )

        # Add validation results
        validations = [
            ValidationResult(ValidationLevel.L1_SYNTAX, 100, 100, 0, 1.0),
            ValidationResult(ValidationLevel.L2_IMPORTS, 100, 95, 5, 0.95)
        ]

        # Calculate score
        score = scorer.calculate_score(masterplan_id, req_results, integration, validations)
    """

    def calculate_score(
        self,
        masterplan_id: UUID,
        requirement_results: List[RequirementResult],
        integration_result: IntegrationResult,
        validation_results: List[ValidationResult]
    ) -> PrecisionScore:
        """
        Calculate composite precision score

        Args:
            masterplan_id: Masterplan UUID
            requirement_results: List of requirement check results
            integration_result: Integration test results
            validation_results: List of validation results (L1-L4)

        Returns:
            PrecisionScore with composite score and components
        """

        # Calculate spec conformance score
        spec_score, spec_details = self._calculate_spec_conformance(requirement_results)

        # Calculate integration pass score
        integration_score = integration_result.pass_rate * 100
        integration_details = {
            "total_tests": integration_result.total_tests,
            "passed_tests": integration_result.passed_tests,
            "failed_tests": integration_result.failed_tests,
            "pass_rate": round(integration_result.pass_rate, 4)
        }

        # Calculate validation pass score
        validation_score, validation_details = self._calculate_validation_pass(validation_results)

        logger.info(
            f"Precision score for {masterplan_id}: "
            f"spec={spec_score:.2f}%, integration={integration_score:.2f}%, "
            f"validation={validation_score:.2f}%"
        )

        return PrecisionScore(
            masterplan_id=masterplan_id,
            spec_conformance_score=spec_score,
            integration_pass_score=integration_score,
            validation_pass_score=validation_score,
            total_score=0.0,  # Calculated in __post_init__
            spec_conformance_details=spec_details,
            integration_details=integration_details,
            validation_details=validation_details,
            meets_target=False  # Calculated in __post_init__
        )

    def _calculate_spec_conformance(
        self,
        requirement_results: List[RequirementResult]
    ) -> tuple[float, Dict]:
        """
        Calculate spec conformance score

        Rules:
        - MUST requirements: 100% required (gate: if <100% → no release)
        - SHOULD requirements: ≥95% required
        - COULD/WONT: not counted

        Score = (passed_musts / total_musts * 100 + passed_shoulds / total_shoulds * 100) / 2

        Args:
            requirement_results: List of requirement results

        Returns:
            Tuple of (score 0-100, details dict)
        """

        musts = [r for r in requirement_results if r.priority == RequirementPriority.MUST]
        shoulds = [r for r in requirement_results if r.priority == RequirementPriority.SHOULD]

        # Calculate MUST pass rate
        total_musts = len(musts)
        passed_musts = sum(1 for r in musts if r.passed)
        must_pass_rate = (passed_musts / total_musts * 100) if total_musts > 0 else 100.0

        # Calculate SHOULD pass rate
        total_shoulds = len(shoulds)
        passed_shoulds = sum(1 for r in shoulds if r.passed)
        should_pass_rate = (passed_shoulds / total_shoulds * 100) if total_shoulds > 0 else 100.0

        # Composite score (equal weight for MUST and SHOULD)
        if total_musts > 0 and total_shoulds > 0:
            score = (must_pass_rate + should_pass_rate) / 2
        elif total_musts > 0:
            score = must_pass_rate
        elif total_shoulds > 0:
            score = should_pass_rate
        else:
            score = 100.0  # No requirements = perfect score

        details = {
            "musts": {
                "total": total_musts,
                "passed": passed_musts,
                "failed": total_musts - passed_musts,
                "pass_rate": round(must_pass_rate / 100, 4)
            },
            "shoulds": {
                "total": total_shoulds,
                "passed": passed_shoulds,
                "failed": total_shoulds - passed_shoulds,
                "pass_rate": round(should_pass_rate / 100, 4)
            },
            "gate_status": "PASS" if must_pass_rate == 100.0 else "FAIL"
        }

        logger.debug(
            f"Spec conformance: MUST {passed_musts}/{total_musts} ({must_pass_rate:.1f}%), "
            f"SHOULD {passed_shoulds}/{total_shoulds} ({should_pass_rate:.1f}%)"
        )

        return score, details

    def _calculate_validation_pass(
        self,
        validation_results: List[ValidationResult]
    ) -> tuple[float, Dict]:
        """
        Calculate validation pass score

        Average pass rate across all validation levels (L1-L4)

        Args:
            validation_results: List of validation results

        Returns:
            Tuple of (score 0-100, details dict)
        """

        if not validation_results:
            return 100.0, {"levels": []}

        # Calculate average pass rate
        total_pass_rate = sum(v.pass_rate for v in validation_results)
        avg_pass_rate = total_pass_rate / len(validation_results)
        score = avg_pass_rate * 100

        # Build details
        details = {
            "levels": [
                {
                    "level": v.level.value,
                    "total": v.total_checks,
                    "passed": v.passed_checks,
                    "failed": v.failed_checks,
                    "pass_rate": round(v.pass_rate, 4)
                }
                for v in validation_results
            ],
            "average_pass_rate": round(avg_pass_rate, 4)
        }

        logger.debug(
            f"Validation pass: {len(validation_results)} levels, "
            f"avg pass rate {avg_pass_rate:.1%}"
        )

        return score, details
