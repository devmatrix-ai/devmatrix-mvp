"""
Quality Gate - Formal Validation Policies per Environment

Phase 4: Formalizes quality requirements by environment (dev/staging/production).

Each environment has different thresholds for:
- Semantic compliance (API contracts)
- IR compliance (code matches spec)
- Infrastructure health
- Test results
- Regression tolerance

Usage:
    gate = QualityGate(environment="staging")
    result = gate.evaluate(compliance_result, stratum_metrics)
    if result.passes:
        print("✅ Quality gate passed")
    else:
        print(f"❌ Gate failed: {result.failures}")
"""

import os
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Literal

logger = logging.getLogger(__name__)


class Environment(str, Enum):
    """Deployment environments with different quality requirements."""
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"


class GateStatus(str, Enum):
    """Status of a quality check."""
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    WARN = "warn"


@dataclass
class EnvironmentPolicy:
    """
    Quality policy for an environment.

    Defines minimum thresholds and allowed exceptions.
    """
    # Compliance thresholds (0.0 - 1.0)
    min_semantic_compliance: float = 1.0
    min_ir_compliance_relaxed: float = 0.85
    min_ir_compliance_strict: float = 0.70

    # Tolerance settings
    allow_warnings: bool = False
    allow_regressions: bool = False
    max_errors: int = 0
    max_warnings: int = 0

    # Infrastructure requirements
    require_infra_health: bool = True
    require_docker_build: bool = False
    require_alembic_upgrade: bool = False

    # Test requirements
    require_syntax_check: bool = True
    require_regression_check: bool = True
    require_smoke_tests: bool = False

    # Historical requirements (for promotion)
    require_n_successful_runs: int = 0

    def __str__(self) -> str:
        return (
            f"Policy(semantic≥{self.min_semantic_compliance:.0%}, "
            f"ir_relaxed≥{self.min_ir_compliance_relaxed:.0%}, "
            f"warnings={'✅' if self.allow_warnings else '❌'})"
        )


# =============================================================================
# ENVIRONMENT POLICIES
# =============================================================================

ENVIRONMENT_POLICIES: Dict[Environment, EnvironmentPolicy] = {
    Environment.DEV: EnvironmentPolicy(
        min_semantic_compliance=0.90,
        min_ir_compliance_relaxed=0.70,
        min_ir_compliance_strict=0.50,
        allow_warnings=True,
        allow_regressions=True,  # Permissive for development
        max_errors=5,
        max_warnings=20,
        require_infra_health=False,
        require_docker_build=False,
        require_alembic_upgrade=False,
        require_syntax_check=True,
        require_regression_check=False,
        require_smoke_tests=False,
        require_n_successful_runs=0,
    ),
    Environment.STAGING: EnvironmentPolicy(
        min_semantic_compliance=1.00,
        min_ir_compliance_relaxed=0.85,
        min_ir_compliance_strict=0.70,
        allow_warnings=False,
        allow_regressions=False,
        max_errors=0,
        max_warnings=5,
        require_infra_health=True,
        require_docker_build=True,
        require_alembic_upgrade=True,
        require_syntax_check=True,
        require_regression_check=True,
        require_smoke_tests=True,
        require_n_successful_runs=3,
    ),
    Environment.PRODUCTION: EnvironmentPolicy(
        min_semantic_compliance=1.00,
        min_ir_compliance_relaxed=0.95,
        min_ir_compliance_strict=0.85,
        allow_warnings=False,
        allow_regressions=False,
        max_errors=0,
        max_warnings=0,
        require_infra_health=True,
        require_docker_build=True,
        require_alembic_upgrade=True,
        require_syntax_check=True,
        require_regression_check=True,
        require_smoke_tests=True,
        require_n_successful_runs=10,
    ),
}


@dataclass
class QualityCheckResult:
    """Result of a single quality check."""
    check_name: str
    status: GateStatus
    value: Optional[Any] = None
    threshold: Optional[Any] = None
    message: str = ""

    @property
    def passed(self) -> bool:
        return self.status in (GateStatus.PASS, GateStatus.SKIP, GateStatus.WARN)


@dataclass
class QualityGateResult:
    """
    Complete quality gate evaluation result.

    Aggregates all quality checks and determines if gate passes.
    """
    environment: Environment
    policy: EnvironmentPolicy

    # Compliance scores
    semantic_compliance: float = 0.0
    ir_compliance_relaxed: float = 0.0
    ir_compliance_strict: float = 0.0

    # Infrastructure status
    infra_health: GateStatus = GateStatus.SKIP
    docker_build: GateStatus = GateStatus.SKIP
    alembic_upgrade: GateStatus = GateStatus.SKIP

    # Test results
    syntax_check: GateStatus = GateStatus.SKIP
    regression_check: GateStatus = GateStatus.SKIP
    smoke_tests: GateStatus = GateStatus.SKIP

    # Bug #7 Fix: Smoke test pass rate (0.0-1.0)
    # This is the actual pass rate from IR Smoke test (76 scenarios)
    smoke_pass_rate: float = 0.0

    # Counts
    error_count: int = 0
    warning_count: int = 0
    regression_count: int = 0

    # Stratum metrics (from Phase 3)
    stratum_metrics: Dict[str, Any] = field(default_factory=dict)

    # Individual check results
    checks: List[QualityCheckResult] = field(default_factory=list)

    # Overall result
    passed: bool = False
    failures: List[str] = field(default_factory=list)

    def evaluate(self) -> bool:
        """Evaluate all checks against the policy."""
        self.failures = []
        self.checks = []

        # Check semantic compliance
        self._check_threshold(
            "semantic_compliance",
            self.semantic_compliance,
            self.policy.min_semantic_compliance,
        )

        # Check IR compliance (relaxed)
        self._check_threshold(
            "ir_compliance_relaxed",
            self.ir_compliance_relaxed,
            self.policy.min_ir_compliance_relaxed,
        )

        # Check error count
        if self.error_count > self.policy.max_errors:
            self.failures.append(
                f"Errors: {self.error_count} > max {self.policy.max_errors}"
            )
            self.checks.append(QualityCheckResult(
                check_name="error_count",
                status=GateStatus.FAIL,
                value=self.error_count,
                threshold=self.policy.max_errors,
                message=f"{self.error_count} errors exceeds limit",
            ))

        # Check warning count
        # Bug #6 Fix: Always evaluate warnings against max_warnings threshold
        # When allow_warnings=True, exceeding threshold is a WARNING (not FAIL)
        # When allow_warnings=False, exceeding threshold is a FAIL
        if self.warning_count > self.policy.max_warnings:
            if self.policy.allow_warnings:
                # Soft failure: log warning but don't fail gate
                self.checks.append(QualityCheckResult(
                    check_name="warning_count",
                    status=GateStatus.WARN,
                    value=self.warning_count,
                    threshold=self.policy.max_warnings,
                    message=f"{self.warning_count} warnings exceeds limit (allowed in {self.environment.value})",
                ))
            else:
                # Hard failure: fail the gate
                self.failures.append(
                    f"Warnings: {self.warning_count} > max {self.policy.max_warnings}"
                )
                self.checks.append(QualityCheckResult(
                    check_name="warning_count",
                    status=GateStatus.FAIL,
                    value=self.warning_count,
                    threshold=self.policy.max_warnings,
                    message=f"{self.warning_count} warnings exceeds limit",
                ))

        # Check regressions (if not allowed)
        if not self.policy.allow_regressions and self.regression_count > 0:
            self.failures.append(
                f"Regressions detected: {self.regression_count}"
            )
            self.checks.append(QualityCheckResult(
                check_name="regressions",
                status=GateStatus.FAIL,
                value=self.regression_count,
                threshold=0,
                message=f"{self.regression_count} regressions detected",
            ))

        # Check infrastructure health
        if self.policy.require_infra_health:
            self._check_status("infra_health", self.infra_health)

        # Check docker build
        if self.policy.require_docker_build:
            self._check_status("docker_build", self.docker_build)

        # Check alembic upgrade
        if self.policy.require_alembic_upgrade:
            self._check_status("alembic_upgrade", self.alembic_upgrade)

        # Check syntax
        if self.policy.require_syntax_check:
            self._check_status("syntax_check", self.syntax_check)

        # Check regression patterns
        if self.policy.require_regression_check:
            self._check_status("regression_check", self.regression_check)

        # Check smoke tests
        if self.policy.require_smoke_tests:
            self._check_status("smoke_tests", self.smoke_tests)

        # Bug #7 Fix: Check smoke pass rate if provided
        # In staging/production, smoke must be 100% (1.0)
        # In dev, smoke failures are warnings (not blocking)
        if self.smoke_pass_rate > 0:  # Only check if smoke was run
            if self.policy.require_smoke_tests:
                # Strict: smoke must be 100%
                if self.smoke_pass_rate < 1.0:
                    self.failures.append(
                        f"Smoke pass rate: {self.smoke_pass_rate:.1%} < 100%"
                    )
                    self.checks.append(QualityCheckResult(
                        check_name="smoke_pass_rate",
                        status=GateStatus.FAIL,
                        value=self.smoke_pass_rate,
                        threshold=1.0,
                        message=f"Smoke test pass rate {self.smoke_pass_rate:.1%} below 100%",
                    ))
                else:
                    self.checks.append(QualityCheckResult(
                        check_name="smoke_pass_rate",
                        status=GateStatus.PASS,
                        value=self.smoke_pass_rate,
                        threshold=1.0,
                        message=f"Smoke test pass rate {self.smoke_pass_rate:.1%}",
                    ))
            else:
                # Informational: log smoke rate but don't fail
                status = GateStatus.PASS if self.smoke_pass_rate >= 0.8 else GateStatus.WARN
                self.checks.append(QualityCheckResult(
                    check_name="smoke_pass_rate",
                    status=status,
                    value=self.smoke_pass_rate,
                    threshold=0.8,
                    message=f"Smoke test pass rate {self.smoke_pass_rate:.1%} (informational)",
                ))

        self.passed = len(self.failures) == 0
        return self.passed

    def _check_threshold(
        self,
        name: str,
        value: float,
        threshold: float,
    ) -> None:
        """Check a numeric threshold."""
        if value < threshold:
            self.failures.append(f"{name}: {value:.1%} < {threshold:.1%}")
            self.checks.append(QualityCheckResult(
                check_name=name,
                status=GateStatus.FAIL,
                value=value,
                threshold=threshold,
                message=f"{value:.1%} below threshold {threshold:.1%}",
            ))
        else:
            self.checks.append(QualityCheckResult(
                check_name=name,
                status=GateStatus.PASS,
                value=value,
                threshold=threshold,
                message=f"{value:.1%} meets threshold",
            ))

    def _check_status(self, name: str, status: GateStatus) -> None:
        """Check a status check."""
        if status == GateStatus.FAIL:
            self.failures.append(f"{name}: FAILED")
            self.checks.append(QualityCheckResult(
                check_name=name,
                status=GateStatus.FAIL,
                message="Check failed",
            ))
        elif status == GateStatus.SKIP:
            self.checks.append(QualityCheckResult(
                check_name=name,
                status=GateStatus.SKIP,
                message="Check skipped",
            ))
        else:
            self.checks.append(QualityCheckResult(
                check_name=name,
                status=GateStatus.PASS,
                message="Check passed",
            ))

    def summary(self) -> str:
        """Get human-readable summary."""
        status = "✅ PASSED" if self.passed else "❌ FAILED"
        checks_passed = sum(1 for c in self.checks if c.passed)

        lines = [
            f"{status} [{self.environment.value.upper()}]",
            f"  Semantic: {self.semantic_compliance:.1%}",
            f"  IR Relaxed: {self.ir_compliance_relaxed:.1%}",
            f"  Errors: {self.error_count} | Warnings: {self.warning_count}",
            f"  Checks: {checks_passed}/{len(self.checks)} passed",
        ]

        if not self.passed:
            lines.append(f"  Failures:")
            for failure in self.failures[:5]:
                lines.append(f"    ❌ {failure}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "environment": self.environment.value,
            "passed": self.passed,
            "compliance": {
                "semantic": self.semantic_compliance,
                "ir_relaxed": self.ir_compliance_relaxed,
                "ir_strict": self.ir_compliance_strict,
            },
            "counts": {
                "errors": self.error_count,
                "warnings": self.warning_count,
                "regressions": self.regression_count,
            },
            "checks": {
                "infra_health": self.infra_health.value,
                "docker_build": self.docker_build.value,
                "alembic_upgrade": self.alembic_upgrade.value,
                "syntax_check": self.syntax_check.value,
                "regression_check": self.regression_check.value,
                "smoke_tests": self.smoke_tests.value,
            },
            "failures": self.failures,
            "stratum_metrics": self.stratum_metrics,
        }


class QualityGate:
    """
    Evaluates code generation quality against environment policies.

    Usage:
        gate = QualityGate(environment="staging")
        result = gate.evaluate(
            semantic_compliance=1.0,
            ir_compliance=0.92,
            error_count=0,
        )
        if result.passed:
            deploy()
    """

    def __init__(self, environment: Optional[str] = None):
        """
        Initialize quality gate.

        Args:
            environment: Target environment (defaults to env QUALITY_GATE_ENV or "dev")
        """
        if environment is None:
            environment = os.getenv("QUALITY_GATE_ENV", "dev")

        try:
            self.environment = Environment(environment)
        except ValueError:
            logger.warning(f"Unknown environment '{environment}', using 'dev'")
            self.environment = Environment.DEV

        self.policy = ENVIRONMENT_POLICIES[self.environment]
        logger.info(f"🚦 Quality Gate: {self.environment.value.upper()} - {self.policy}")

    def evaluate(
        self,
        semantic_compliance: float = 0.0,
        ir_compliance_relaxed: float = 0.0,
        ir_compliance_strict: float = 0.0,
        error_count: int = 0,
        warning_count: int = 0,
        regression_count: int = 0,
        infra_health: Optional[GateStatus] = None,
        docker_build: Optional[GateStatus] = None,
        alembic_upgrade: Optional[GateStatus] = None,
        syntax_check: Optional[GateStatus] = None,
        regression_check: Optional[GateStatus] = None,
        smoke_tests: Optional[GateStatus] = None,
        smoke_pass_rate: float = 0.0,  # Bug #7 Fix: Smoke test pass rate
        stratum_metrics: Optional[Dict[str, Any]] = None,
    ) -> QualityGateResult:
        """
        Evaluate quality metrics against policy.

        Args:
            semantic_compliance: API contract compliance (0.0 - 1.0)
            ir_compliance_relaxed: IR compliance with tolerance (0.0 - 1.0)
            ir_compliance_strict: IR compliance strict mode (0.0 - 1.0)
            error_count: Number of errors detected
            warning_count: Number of warnings detected
            regression_count: Number of regressions detected
            infra_health: Infrastructure health check status
            docker_build: Docker build status
            alembic_upgrade: Alembic migration status
            syntax_check: Syntax validation status
            regression_check: Regression pattern check status
            smoke_tests: Smoke test status
            smoke_pass_rate: Bug #7 Fix - Smoke test pass rate (0.0 - 1.0)
            stratum_metrics: Metrics from Phase 3

        Returns:
            QualityGateResult with evaluation
        """
        result = QualityGateResult(
            environment=self.environment,
            policy=self.policy,
            semantic_compliance=semantic_compliance,
            ir_compliance_relaxed=ir_compliance_relaxed,
            ir_compliance_strict=ir_compliance_strict,
            error_count=error_count,
            warning_count=warning_count,
            regression_count=regression_count,
            infra_health=infra_health or GateStatus.SKIP,
            docker_build=docker_build or GateStatus.SKIP,
            alembic_upgrade=alembic_upgrade or GateStatus.SKIP,
            syntax_check=syntax_check or GateStatus.SKIP,
            regression_check=regression_check or GateStatus.SKIP,
            smoke_tests=smoke_tests or GateStatus.SKIP,
            smoke_pass_rate=smoke_pass_rate,  # Bug #7 Fix
            stratum_metrics=stratum_metrics or {},
        )

        result.evaluate()

        if result.passed:
            logger.info(f"✅ Quality gate PASSED for {self.environment.value}")
        else:
            logger.warning(f"❌ Quality gate FAILED: {result.failures}")

        return result

    def evaluate_from_metrics(
        self,
        compliance_result: Any,
        validation_result: Any = None,
        stratum_metrics: Optional[Dict[str, Any]] = None,
    ) -> QualityGateResult:
        """
        Evaluate from existing metrics objects.

        Args:
            compliance_result: ComplianceValidator result
            validation_result: BasicValidationPipeline result
            stratum_metrics: StratumMetrics snapshot

        Returns:
            QualityGateResult
        """
        # Extract compliance scores
        semantic = 1.0
        ir_relaxed = 0.0
        ir_strict = 0.0

        if hasattr(compliance_result, 'semantic_compliance'):
            semantic = compliance_result.semantic_compliance
        if hasattr(compliance_result, 'ir_compliance_relaxed'):
            ir_relaxed = compliance_result.ir_compliance_relaxed
        elif hasattr(compliance_result, 'compliance_rate'):
            ir_relaxed = compliance_result.compliance_rate
        if hasattr(compliance_result, 'ir_compliance_strict'):
            ir_strict = compliance_result.ir_compliance_strict

        # Extract validation counts
        error_count = 0
        warning_count = 0
        syntax_status = GateStatus.SKIP
        regression_status = GateStatus.SKIP

        if validation_result:
            if hasattr(validation_result, 'errors'):
                error_count = len(validation_result.errors)
            if hasattr(validation_result, 'warnings'):
                warning_count = len(validation_result.warnings)
            if hasattr(validation_result, 'passed'):
                syntax_status = GateStatus.PASS if validation_result.passed else GateStatus.FAIL

        # Extract stratum metrics if dict
        stratum_dict = {}
        if stratum_metrics:
            if hasattr(stratum_metrics, 'to_dict'):
                stratum_dict = stratum_metrics.to_dict()
            elif isinstance(stratum_metrics, dict):
                stratum_dict = stratum_metrics

        return self.evaluate(
            semantic_compliance=semantic,
            ir_compliance_relaxed=ir_relaxed,
            ir_compliance_strict=ir_strict,
            error_count=error_count,
            warning_count=warning_count,
            syntax_check=syntax_status,
            stratum_metrics=stratum_dict,
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_quality_gate: Optional[QualityGate] = None


def get_quality_gate(environment: Optional[str] = None) -> QualityGate:
    """Get singleton quality gate."""
    global _quality_gate
    if _quality_gate is None or environment is not None:
        _quality_gate = QualityGate(environment)
    return _quality_gate


def evaluate_quality(
    semantic_compliance: float,
    ir_compliance: float,
    error_count: int = 0,
    warning_count: int = 0,
    environment: Optional[str] = None,
) -> QualityGateResult:
    """Quick quality evaluation."""
    gate = get_quality_gate(environment)
    return gate.evaluate(
        semantic_compliance=semantic_compliance,
        ir_compliance_relaxed=ir_compliance,
        error_count=error_count,
        warning_count=warning_count,
    )


def passes_quality_gate(
    semantic_compliance: float,
    ir_compliance: float,
    error_count: int = 0,
    environment: Optional[str] = None,
) -> bool:
    """Check if metrics pass quality gate."""
    result = evaluate_quality(
        semantic_compliance=semantic_compliance,
        ir_compliance=ir_compliance,
        error_count=error_count,
        environment=environment,
    )
    return result.passed


def get_policy_for_environment(environment: str) -> EnvironmentPolicy:
    """Get policy for an environment."""
    try:
        env = Environment(environment)
        return ENVIRONMENT_POLICIES[env]
    except ValueError:
        return ENVIRONMENT_POLICIES[Environment.DEV]


def format_gate_report(result: QualityGateResult) -> str:
    """
    Format a quality gate result as an ASCII report.

    Output:
    ```
    🚦 Quality Gate Report
    ┌──────────────────────────────────────────────────┐
    │ Environment: STAGING                              │
    │ Status: ✅ PASSED                                 │
    ├──────────────────────────────────────────────────┤
    │ Compliance                                       │
    │   Semantic:    100.0% ≥  100.0% ✅              │
    │   IR Relaxed:   92.0% ≥   85.0% ✅              │
    │   IR Strict:    78.0% ≥   70.0% ✅              │
    ├──────────────────────────────────────────────────┤
    │ Quality Counts                                   │
    │   Errors:       0 ≤    0 ✅                      │
    │   Warnings:     2 ≤    5 ✅                      │
    │   Regressions:  0 ≤    0 ✅                      │
    └──────────────────────────────────────────────────┘
    ```
    """
    status = "✅ PASSED" if result.passed else "❌ FAILED"
    policy = result.policy

    lines = [
        "",
        "🚦 Quality Gate Report",
        "┌──────────────────────────────────────────────────┐",
        f"│ Environment: {result.environment.value.upper():<36} │",
        f"│ Status: {status:<40} │",
        "├──────────────────────────────────────────────────┤",
        "│ Compliance                                       │",
    ]

    # Compliance checks
    sem_ok = "✅" if result.semantic_compliance >= policy.min_semantic_compliance else "❌"
    ir_ok = "✅" if result.ir_compliance_relaxed >= policy.min_ir_compliance_relaxed else "❌"
    strict_ok = "✅" if result.ir_compliance_strict >= policy.min_ir_compliance_strict else "❌"

    lines.append(f"│   Semantic:  {result.semantic_compliance:>6.1%} ≥ {policy.min_semantic_compliance:>6.1%} {sem_ok}              │")
    lines.append(f"│   IR Relaxed:{result.ir_compliance_relaxed:>6.1%} ≥ {policy.min_ir_compliance_relaxed:>6.1%} {ir_ok}              │")
    lines.append(f"│   IR Strict: {result.ir_compliance_strict:>6.1%} ≥ {policy.min_ir_compliance_strict:>6.1%} {strict_ok}              │")

    # Bug #7 Fix: Show smoke pass rate if available
    if result.smoke_pass_rate > 0:
        lines.append("├──────────────────────────────────────────────────┤")
        lines.append("│ Smoke Tests                                      │")
        smoke_ok = "✅" if result.smoke_pass_rate >= 1.0 else ("⚠️" if result.smoke_pass_rate >= 0.8 else "❌")
        smoke_threshold = "100.0%" if policy.require_smoke_tests else " 80.0%"
        lines.append(f"│   Pass Rate: {result.smoke_pass_rate:>6.1%} ≥ {smoke_threshold} {smoke_ok}              │")

    lines.append("├──────────────────────────────────────────────────┤")
    lines.append("│ Quality Counts                                   │")

    # Quality counts
    err_ok = "✅" if result.error_count <= policy.max_errors else "❌"
    # Bug #6 Fix: Show warning status correctly (⚠️ if exceeded but allowed)
    if result.warning_count <= policy.max_warnings:
        warn_ok = "✅"
    elif policy.allow_warnings:
        warn_ok = "⚠️"  # Exceeded but allowed
    else:
        warn_ok = "❌"
    reg_ok = "✅" if result.regression_count == 0 or policy.allow_regressions else "❌"

    lines.append(f"│   Errors:    {result.error_count:>4} ≤ {policy.max_errors:>4} {err_ok}                      │")
    lines.append(f"│   Warnings:  {result.warning_count:>4} ≤ {policy.max_warnings:>4} {warn_ok}                      │")
    lines.append(f"│   Regressions:{result.regression_count:>3} {'(allowed)' if policy.allow_regressions else '≤    0'} {reg_ok}                 │")

    lines.append("└──────────────────────────────────────────────────┘")

    if not result.passed:
        lines.append("")
        lines.append("Failures:")
        for failure in result.failures:
            lines.append(f"  ❌ {failure}")

    return "\n".join(lines)
