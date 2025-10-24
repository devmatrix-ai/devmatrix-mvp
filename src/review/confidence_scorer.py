"""
ConfidenceScorer - Calculate confidence scores for atoms

Confidence scoring based on 4 components:
1. Validation results (40%) - syntax, semantics, atomicity checks
2. Attempts needed (30%) - number of retries required
3. Complexity (20%) - cyclomatic complexity
4. Integration tests (10%) - test execution results

Author: DevMatrix Team
Date: 2025-10-24
"""

from typing import Dict, Optional, List
from dataclasses import dataclass
from sqlalchemy.orm import Session

from ..models import AtomicUnit, ValidationResult, AtomRetryHistory


@dataclass
class ConfidenceScore:
    """Confidence score result"""
    atom_id: str
    overall_score: float  # 0.0-1.0
    validation_score: float  # 0.0-1.0 (40% weight)
    attempts_score: float  # 0.0-1.0 (30% weight)
    complexity_score: float  # 0.0-1.0 (20% weight)
    integration_score: float  # 0.0-1.0 (10% weight)
    confidence_level: str  # "high" | "medium" | "low" | "critical"
    needs_review: bool
    issues: List[str]


class ConfidenceScorer:
    """
    Calculate confidence scores for atoms based on validation,
    retry attempts, complexity, and integration tests.

    Score calculation:
    - Validation: 40% (syntax, semantics, atomicity)
    - Attempts: 30% (fewer retries = higher score)
    - Complexity: 20% (lower complexity = higher score)
    - Integration: 10% (test pass rate)

    Confidence levels:
    - High: ≥0.85 (no review needed)
    - Medium: 0.70-0.84 (optional review)
    - Low: 0.50-0.69 (review recommended)
    - Critical: <0.50 (review required)
    """

    def __init__(self, db: Session):
        self.db = db

        # Component weights
        self.VALIDATION_WEIGHT = 0.40
        self.ATTEMPTS_WEIGHT = 0.30
        self.COMPLEXITY_WEIGHT = 0.20
        self.INTEGRATION_WEIGHT = 0.10

        # Thresholds
        self.HIGH_THRESHOLD = 0.85
        self.MEDIUM_THRESHOLD = 0.70
        self.LOW_THRESHOLD = 0.50

        # Max attempts for scoring (beyond this, score = 0)
        self.MAX_ATTEMPTS = 5

        # Complexity threshold (target: <3.0)
        self.TARGET_COMPLEXITY = 3.0
        self.MAX_COMPLEXITY = 10.0

    def calculate_confidence(self, atom_id: str) -> ConfidenceScore:
        """
        Calculate overall confidence score for an atom.

        Args:
            atom_id: Atom ID to score

        Returns:
            ConfidenceScore with overall score and component breakdown
        """
        # Load atom
        atom = self.db.query(AtomicUnit).filter(
            AtomicUnit.atom_id == atom_id
        ).first()

        if not atom:
            raise ValueError(f"Atom {atom_id} not found")

        # Calculate component scores
        validation_score = self.score_validation_results(atom)
        attempts_score = self.score_attempts(atom)
        complexity_score = self.score_complexity(atom.complexity)
        integration_score = self.score_integration_tests(atom)

        # Calculate weighted overall score
        overall_score = (
            validation_score * self.VALIDATION_WEIGHT +
            attempts_score * self.ATTEMPTS_WEIGHT +
            complexity_score * self.COMPLEXITY_WEIGHT +
            integration_score * self.INTEGRATION_WEIGHT
        )

        # Determine confidence level
        if overall_score >= self.HIGH_THRESHOLD:
            confidence_level = "high"
            needs_review = False
        elif overall_score >= self.MEDIUM_THRESHOLD:
            confidence_level = "medium"
            needs_review = False  # Optional
        elif overall_score >= self.LOW_THRESHOLD:
            confidence_level = "low"
            needs_review = True
        else:
            confidence_level = "critical"
            needs_review = True

        # Collect issues
        issues = self._identify_issues(
            atom,
            validation_score,
            attempts_score,
            complexity_score,
            integration_score
        )

        return ConfidenceScore(
            atom_id=atom_id,
            overall_score=overall_score,
            validation_score=validation_score,
            attempts_score=attempts_score,
            complexity_score=complexity_score,
            integration_score=integration_score,
            confidence_level=confidence_level,
            needs_review=needs_review,
            issues=issues
        )

    def score_validation_results(self, atom: AtomicUnit) -> float:
        """
        Score validation results (40% weight).

        Checks:
        - Syntax validation passed
        - Semantic validation passed
        - Atomicity criteria met
        - Type safety validation
        - Runtime safety validation

        Args:
            atom: AtomicUnit to score

        Returns:
            Score 0.0-1.0
        """
        # Get latest validation result
        validation = self.db.query(ValidationResult).filter(
            ValidationResult.atom_id == atom.atom_id
        ).order_by(ValidationResult.created_at.desc()).first()

        if not validation:
            # No validation = low score
            return 0.3

        # Parse validation data
        checks = validation.validation_data or {}

        # Count passed checks
        passed = 0
        total = 0

        # Syntax check (critical)
        if checks.get("syntax", {}).get("passed"):
            passed += 2  # Double weight
        total += 2

        # Semantic check (critical)
        if checks.get("semantics", {}).get("passed"):
            passed += 2  # Double weight
        total += 2

        # Atomicity check
        if checks.get("atomicity", {}).get("passed"):
            passed += 1
        total += 1

        # Type safety check
        if checks.get("type_safety", {}).get("passed"):
            passed += 1
        total += 1

        # Runtime safety check
        if checks.get("runtime_safety", {}).get("passed"):
            passed += 1
        total += 1

        return passed / total if total > 0 else 0.0

    def score_attempts(self, atom: AtomicUnit) -> float:
        """
        Score based on number of retry attempts (30% weight).

        Fewer attempts = higher score
        - 0 attempts (first try): 1.0
        - 1 attempt: 0.8
        - 2 attempts: 0.6
        - 3 attempts: 0.4
        - 4 attempts: 0.2
        - 5+ attempts: 0.0

        Args:
            atom: AtomicUnit to score

        Returns:
            Score 0.0-1.0
        """
        # Count retry attempts
        retry_count = self.db.query(AtomRetryHistory).filter(
            AtomRetryHistory.atom_id == atom.atom_id
        ).count()

        if retry_count == 0:
            return 1.0
        elif retry_count >= self.MAX_ATTEMPTS:
            return 0.0
        else:
            # Linear decay
            return 1.0 - (retry_count / self.MAX_ATTEMPTS)

    def score_complexity(self, complexity: float) -> float:
        """
        Score based on cyclomatic complexity (20% weight).

        Lower complexity = higher score
        - <3.0 (target): 1.0
        - 3.0-5.0: 0.8
        - 5.0-7.0: 0.6
        - 7.0-10.0: 0.4
        - >10.0: 0.0

        Args:
            complexity: Cyclomatic complexity value

        Returns:
            Score 0.0-1.0
        """
        if complexity < self.TARGET_COMPLEXITY:
            return 1.0
        elif complexity >= self.MAX_COMPLEXITY:
            return 0.0
        else:
            # Linear decay from target to max
            return 1.0 - (
                (complexity - self.TARGET_COMPLEXITY) /
                (self.MAX_COMPLEXITY - self.TARGET_COMPLEXITY)
            )

    def score_integration_tests(self, atom: AtomicUnit) -> float:
        """
        Score based on integration test results (10% weight).

        Currently placeholder - will integrate with actual test results.

        Args:
            atom: AtomicUnit to score

        Returns:
            Score 0.0-1.0
        """
        # TODO: Integrate with actual test execution results
        # For now, return neutral score
        return 0.5

    def _identify_issues(
        self,
        atom: AtomicUnit,
        validation_score: float,
        attempts_score: float,
        complexity_score: float,
        integration_score: float
    ) -> List[str]:
        """
        Identify specific issues based on component scores.

        Args:
            atom: AtomicUnit being scored
            validation_score: Validation component score
            attempts_score: Attempts component score
            complexity_score: Complexity component score
            integration_score: Integration component score

        Returns:
            List of issue descriptions
        """
        issues = []

        if validation_score < 0.5:
            issues.append("Validation failures detected (syntax/semantics/atomicity)")

        if attempts_score < 0.5:
            issues.append(f"High retry count (required multiple attempts)")

        if complexity_score < 0.5:
            issues.append(f"High complexity ({atom.complexity:.1f}, target <3.0)")

        if integration_score < 0.3:
            issues.append("Integration test failures detected")

        # Check atom status
        if atom.status == "failed":
            issues.append("Atom execution failed")

        if atom.status == "pending":
            issues.append("Atom not yet executed")

        return issues

    def batch_calculate_confidence(
        self,
        atom_ids: List[str]
    ) -> Dict[str, ConfidenceScore]:
        """
        Calculate confidence scores for multiple atoms.

        Args:
            atom_ids: List of atom IDs to score

        Returns:
            Dictionary mapping atom_id to ConfidenceScore
        """
        results = {}

        for atom_id in atom_ids:
            try:
                results[atom_id] = self.calculate_confidence(atom_id)
            except Exception as e:
                # Log error but continue with other atoms
                print(f"Error scoring atom {atom_id}: {e}")
                continue

        return results

    def get_low_confidence_atoms(
        self,
        masterplan_id: str,
        threshold: float = 0.70
    ) -> List[ConfidenceScore]:
        """
        Get all atoms below confidence threshold for a masterplan.

        Args:
            masterplan_id: MasterPlan ID
            threshold: Minimum confidence score (default: 0.70)

        Returns:
            List of ConfidenceScore objects sorted by score (lowest first)
        """
        # Get all atoms for masterplan
        atoms = self.db.query(AtomicUnit).filter(
            AtomicUnit.masterplan_id == masterplan_id
        ).all()

        # Calculate scores
        scores = []
        for atom in atoms:
            try:
                score = self.calculate_confidence(atom.atom_id)
                if score.overall_score < threshold:
                    scores.append(score)
            except Exception as e:
                print(f"Error scoring atom {atom.atom_id}: {e}")
                continue

        # Sort by score (lowest first - highest priority for review)
        scores.sort(key=lambda x: x.overall_score)

        return scores
