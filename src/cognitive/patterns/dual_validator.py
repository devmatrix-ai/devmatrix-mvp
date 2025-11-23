"""
Real DualValidator Implementation for Pattern Learning System.

This module implements the actual validation logic for the pattern promotion pipeline,
replacing the mock validator with real metrics-based validation.

Author: DevMatrix Team
Date: 2025-11-23
"""

import re
import logging
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum

from src.cognitive.signatures.semantic_signature import SemanticTaskSignature

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security levels for pattern validation."""
    CRITICAL = "critical"  # No security issues found
    HIGH = "high"         # Minor security considerations
    MEDIUM = "medium"     # Some security issues, acceptable for most use cases
    LOW = "low"          # Significant security issues
    FAILED = "failed"    # Critical security flaws


class ComplianceLevel(Enum):
    """Compliance levels for pattern validation."""
    FULL = "full"           # Fully compliant with all standards
    PARTIAL = "partial"     # Mostly compliant with minor issues
    MINIMAL = "minimal"     # Basic compliance only
    NONE = "none"          # No compliance checks passed


@dataclass
class ValidationResult:
    """Result from validation process."""
    is_valid: bool
    success_rate: float
    test_coverage: float
    security_level: SecurityLevel
    compliance_level: ComplianceLevel
    performance_score: float
    quality_score: float
    should_promote: bool
    reasoning: str
    issues: List[str]
    recommendations: List[str]


@dataclass
class QualityMetrics:
    """Quality metrics for validation."""
    success_rate: float
    test_coverage: float
    validation_score: float
    performance_score: float
    overall_quality: float


class RealDualValidator:
    """
    Real implementation of DualValidator with actual validation logic.

    This validator performs comprehensive checks on patterns including:
    - Quality metrics validation
    - Security analysis
    - Performance evaluation
    - Compliance checking
    - Best practices verification
    """

    # Thresholds for promotion
    MIN_SUCCESS_RATE = 0.95      # 95% test success rate required
    MIN_TEST_COVERAGE = 0.80      # 80% test coverage required
    MIN_SECURITY_LEVEL = SecurityLevel.MEDIUM
    MIN_COMPLIANCE_LEVEL = ComplianceLevel.PARTIAL
    MIN_PERFORMANCE_SCORE = 0.70
    MIN_QUALITY_SCORE = 0.75

    # Pattern usage requirements
    MIN_USAGE_COUNT = 5           # Pattern must be used at least 5 times
    MAX_ERROR_COUNT = 2           # Maximum 2 errors allowed

    def __init__(self):
        """Initialize the real dual validator."""
        self.validation_history: Dict[str, List[bool]] = {}
        self.pattern_usage_count: Dict[str, int] = {}
        self.pattern_error_count: Dict[str, int] = {}
        logger.info("Initialized RealDualValidator with production validation logic")

    def validate_pattern(
        self,
        pattern: Any,  # Would be StoredPattern in production
        context: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate a pattern using real metrics and criteria.

        Args:
            pattern: The pattern to validate
            context: Validation context including metrics

        Returns:
            ValidationResult with comprehensive validation details
        """
        logger.info(f"Validating pattern with real metrics")

        # Extract metrics from context
        quality_metrics = context.get('quality_metrics')
        code = context.get('code', '')
        signature = context.get('signature')

        if not quality_metrics:
            logger.warning("No quality metrics provided, using defaults")
            quality_metrics = QualityMetrics(
                success_rate=0.0,
                test_coverage=0.0,
                validation_score=0.0,
                performance_score=0.0,
                overall_quality=0.0
            )

        # Perform validation checks
        issues = []
        recommendations = []

        # 1. Validate success rate
        success_rate = quality_metrics.success_rate
        if success_rate < self.MIN_SUCCESS_RATE:
            issues.append(f"Success rate {success_rate:.2%} below minimum {self.MIN_SUCCESS_RATE:.0%}")
            recommendations.append("Improve test reliability and fix failing tests")

        # 2. Validate test coverage
        test_coverage = quality_metrics.test_coverage
        if test_coverage < self.MIN_TEST_COVERAGE:
            issues.append(f"Test coverage {test_coverage:.2%} below minimum {self.MIN_TEST_COVERAGE:.0%}")
            recommendations.append("Add more comprehensive test cases")

        # 3. Security validation
        security_level = self._analyze_security(code)
        if security_level.value > self.MIN_SECURITY_LEVEL.value:
            issues.append(f"Security level {security_level.value} is insufficient")
            recommendations.append("Address security vulnerabilities")

        # 4. Performance validation
        performance_score = quality_metrics.performance_score
        if performance_score < self.MIN_PERFORMANCE_SCORE:
            issues.append(f"Performance score {performance_score:.2f} below minimum {self.MIN_PERFORMANCE_SCORE:.2f}")
            recommendations.append("Optimize code for better performance")

        # 5. Compliance validation
        compliance_level = self._check_compliance(code)

        # 6. Calculate overall quality score
        quality_score = self._calculate_quality_score(
            success_rate=success_rate,
            test_coverage=test_coverage,
            security_level=security_level,
            performance_score=performance_score,
            compliance_level=compliance_level
        )

        # Determine if pattern should be promoted
        should_promote = self._should_promote_internal(
            success_rate=success_rate,
            test_coverage=test_coverage,
            security_level=security_level,
            compliance_level=compliance_level,
            performance_score=performance_score,
            quality_score=quality_score,
            pattern_id=context.get('pattern_id', 'unknown')
        )

        # Build reasoning
        reasoning = self._build_reasoning(
            success_rate=success_rate,
            test_coverage=test_coverage,
            security_level=security_level,
            compliance_level=compliance_level,
            performance_score=performance_score,
            quality_score=quality_score,
            should_promote=should_promote
        )

        result = ValidationResult(
            is_valid=len(issues) == 0,
            success_rate=success_rate,
            test_coverage=test_coverage,
            security_level=security_level,
            compliance_level=compliance_level,
            performance_score=performance_score,
            quality_score=quality_score,
            should_promote=should_promote,
            reasoning=reasoning,
            issues=issues,
            recommendations=recommendations
        )

        # Track validation result
        pattern_id = context.get('pattern_id', 'unknown')
        if pattern_id not in self.validation_history:
            self.validation_history[pattern_id] = []
        self.validation_history[pattern_id].append(result.is_valid)

        logger.info(f"Validation result: {result.should_promote} (quality: {quality_score:.2f})")

        return result

    def should_promote(self, pattern: Any) -> bool:
        """
        Determine if a pattern should be promoted based on comprehensive criteria.

        Args:
            pattern: The pattern to evaluate

        Returns:
            True if pattern meets all promotion criteria
        """
        # Get pattern ID (in production, this would come from pattern object)
        pattern_id = getattr(pattern, 'id', 'unknown')

        # Check usage count
        usage_count = self.pattern_usage_count.get(pattern_id, 0)
        if usage_count < self.MIN_USAGE_COUNT:
            logger.info(f"Pattern {pattern_id} not promoted: usage count {usage_count} < {self.MIN_USAGE_COUNT}")
            return False

        # Check error count
        error_count = self.pattern_error_count.get(pattern_id, 0)
        if error_count > self.MAX_ERROR_COUNT:
            logger.info(f"Pattern {pattern_id} not promoted: error count {error_count} > {self.MAX_ERROR_COUNT}")
            return False

        # Check validation history
        validation_history = self.validation_history.get(pattern_id, [])
        if not validation_history:
            logger.info(f"Pattern {pattern_id} not promoted: no validation history")
            return False

        # Calculate validation success rate
        validation_success_rate = sum(validation_history) / len(validation_history)
        if validation_success_rate < 0.8:  # 80% of validations must pass
            logger.info(f"Pattern {pattern_id} not promoted: validation success rate {validation_success_rate:.2%} < 80%")
            return False

        logger.info(f"Pattern {pattern_id} meets promotion criteria")
        return True

    def _analyze_security(self, code: str) -> SecurityLevel:
        """
        Analyze security aspects of the code.

        Args:
            code: Code to analyze

        Returns:
            SecurityLevel assessment
        """
        if not code:
            return SecurityLevel.MEDIUM

        critical_patterns = [
            r'eval\s*\(',
            r'exec\s*\(',
            r'__import__\s*\(',
            r'compile\s*\(',
        ]

        high_risk_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']',
        ]

        medium_risk_patterns = [
            r'\.format\s*\(',
            r'%\s*\(',
            r'subprocess\.',
            r'os\.system',
        ]

        # Check for critical security issues
        for pattern in critical_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return SecurityLevel.FAILED

        # Check for high risk patterns
        high_risk_count = 0
        for pattern in high_risk_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                high_risk_count += 1

        if high_risk_count > 1:
            return SecurityLevel.LOW
        elif high_risk_count == 1:
            return SecurityLevel.MEDIUM

        # Check for medium risk patterns
        medium_risk_count = 0
        for pattern in medium_risk_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                medium_risk_count += 1

        if medium_risk_count > 2:
            return SecurityLevel.MEDIUM
        elif medium_risk_count > 0:
            return SecurityLevel.HIGH

        return SecurityLevel.CRITICAL  # No security issues found

    def _check_compliance(self, code: str) -> ComplianceLevel:
        """
        Check code compliance with standards.

        Args:
            code: Code to check

        Returns:
            ComplianceLevel assessment
        """
        if not code:
            return ComplianceLevel.MINIMAL

        compliance_checks = {
            'has_docstrings': bool(re.search(r'"""[\s\S]*?"""', code)),
            'has_type_hints': bool(re.search(r':\s*\w+', code)),
            'has_error_handling': bool(re.search(r'try:', code)),
            'has_logging': bool(re.search(r'logger\.|logging\.', code)),
            'follows_naming': not bool(re.search(r'def [A-Z]', code)),  # No uppercase function names
            'no_todos': not bool(re.search(r'#\s*TODO', code, re.IGNORECASE)),
        }

        passed_checks = sum(compliance_checks.values())
        total_checks = len(compliance_checks)

        compliance_ratio = passed_checks / total_checks

        if compliance_ratio >= 0.9:
            return ComplianceLevel.FULL
        elif compliance_ratio >= 0.7:
            return ComplianceLevel.PARTIAL
        elif compliance_ratio >= 0.4:
            return ComplianceLevel.MINIMAL
        else:
            return ComplianceLevel.NONE

    def _calculate_quality_score(
        self,
        success_rate: float,
        test_coverage: float,
        security_level: SecurityLevel,
        performance_score: float,
        compliance_level: ComplianceLevel
    ) -> float:
        """
        Calculate overall quality score.

        Args:
            success_rate: Test success rate
            test_coverage: Test coverage percentage
            security_level: Security assessment
            performance_score: Performance score
            compliance_level: Compliance assessment

        Returns:
            Overall quality score (0.0-1.0)
        """
        # Convert security level to score
        security_scores = {
            SecurityLevel.CRITICAL: 1.0,
            SecurityLevel.HIGH: 0.85,
            SecurityLevel.MEDIUM: 0.70,
            SecurityLevel.LOW: 0.40,
            SecurityLevel.FAILED: 0.0
        }
        security_score = security_scores.get(security_level, 0.5)

        # Convert compliance level to score
        compliance_scores = {
            ComplianceLevel.FULL: 1.0,
            ComplianceLevel.PARTIAL: 0.75,
            ComplianceLevel.MINIMAL: 0.50,
            ComplianceLevel.NONE: 0.25
        }
        compliance_score = compliance_scores.get(compliance_level, 0.5)

        # Weighted average
        quality_score = (
            0.25 * success_rate +
            0.25 * test_coverage +
            0.20 * security_score +
            0.15 * performance_score +
            0.15 * compliance_score
        )

        return min(1.0, max(0.0, quality_score))

    def _should_promote_internal(
        self,
        success_rate: float,
        test_coverage: float,
        security_level: SecurityLevel,
        compliance_level: ComplianceLevel,
        performance_score: float,
        quality_score: float,
        pattern_id: str
    ) -> bool:
        """
        Internal logic to determine if pattern should be promoted.

        Returns:
            True if all criteria are met
        """
        # Check all thresholds
        criteria = {
            'success_rate': success_rate >= self.MIN_SUCCESS_RATE,
            'test_coverage': test_coverage >= self.MIN_TEST_COVERAGE,
            'security_level': security_level.value <= self.MIN_SECURITY_LEVEL.value,
            'compliance_level': compliance_level.value <= ComplianceLevel.PARTIAL.value,
            'performance_score': performance_score >= self.MIN_PERFORMANCE_SCORE,
            'quality_score': quality_score >= self.MIN_QUALITY_SCORE,
        }

        # Log failed criteria
        failed_criteria = [name for name, passed in criteria.items() if not passed]
        if failed_criteria:
            logger.debug(f"Pattern {pattern_id} failed promotion criteria: {failed_criteria}")

        return all(criteria.values())

    def _build_reasoning(
        self,
        success_rate: float,
        test_coverage: float,
        security_level: SecurityLevel,
        compliance_level: ComplianceLevel,
        performance_score: float,
        quality_score: float,
        should_promote: bool
    ) -> str:
        """
        Build human-readable reasoning for validation decision.

        Returns:
            Reasoning string
        """
        if should_promote:
            return (
                f"Pattern meets all promotion criteria: "
                f"success_rate={success_rate:.2%}, "
                f"coverage={test_coverage:.2%}, "
                f"security={security_level.value}, "
                f"performance={performance_score:.2f}, "
                f"quality={quality_score:.2f}"
            )
        else:
            reasons = []
            if success_rate < self.MIN_SUCCESS_RATE:
                reasons.append(f"low success rate ({success_rate:.2%})")
            if test_coverage < self.MIN_TEST_COVERAGE:
                reasons.append(f"insufficient coverage ({test_coverage:.2%})")
            if security_level.value > self.MIN_SECURITY_LEVEL.value:
                reasons.append(f"security issues ({security_level.value})")
            if performance_score < self.MIN_PERFORMANCE_SCORE:
                reasons.append(f"poor performance ({performance_score:.2f})")
            if quality_score < self.MIN_QUALITY_SCORE:
                reasons.append(f"low quality ({quality_score:.2f})")

            return f"Pattern not promoted due to: {', '.join(reasons)}"

    def track_usage(self, pattern_id: str) -> None:
        """Track pattern usage."""
        if pattern_id not in self.pattern_usage_count:
            self.pattern_usage_count[pattern_id] = 0
        self.pattern_usage_count[pattern_id] += 1
        logger.debug(f"Pattern {pattern_id} usage count: {self.pattern_usage_count[pattern_id]}")

    def track_error(self, pattern_id: str) -> None:
        """Track pattern error."""
        if pattern_id not in self.pattern_error_count:
            self.pattern_error_count[pattern_id] = 0
        self.pattern_error_count[pattern_id] += 1
        logger.warning(f"Pattern {pattern_id} error count: {self.pattern_error_count[pattern_id]}")

    def reset_pattern_stats(self, pattern_id: str) -> None:
        """Reset statistics for a pattern."""
        self.pattern_usage_count[pattern_id] = 0
        self.pattern_error_count[pattern_id] = 0
        self.validation_history[pattern_id] = []
        logger.info(f"Reset statistics for pattern {pattern_id}")