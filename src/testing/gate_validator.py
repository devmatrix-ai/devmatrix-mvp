"""
Gate Validator for MGE V2

Simple validator for Gate S (Spec Conformance Gate) logic.
Validates must/should pass rates without database access.
"""
from typing import Dict, List


class GateValidator:
    """
    Validates Gate S requirements.

    Gate S logic:
    - MUST requirements: 100% pass rate required
    - SHOULD requirements: ≥95% pass rate required
    - Gate passed: Both thresholds met
    """

    def __init__(self):
        """Initialize GateValidator."""
        self.must_threshold = 1.0  # 100%
        self.should_threshold = 0.95  # 95%

    def validate_gate_s(
        self,
        must_pass_rate: float,
        should_pass_rate: float
    ) -> Dict[str, any]:
        """
        Validate Gate S based on pass rates.

        Args:
            must_pass_rate: MUST requirements pass rate (0.0-1.0)
            should_pass_rate: SHOULD requirements pass rate (0.0-1.0)

        Returns:
            Dict with keys:
                - passed: bool - Whether gate passed
                - message: str - Gate result message
                - failures: List[str] - List of failure reasons (if any)
        """
        failures = []

        # Check MUST threshold
        if must_pass_rate < self.must_threshold:
            failures.append(
                f"MUST pass rate {must_pass_rate:.1%} below required {self.must_threshold:.1%}"
            )

        # Check SHOULD threshold
        if should_pass_rate < self.should_threshold:
            failures.append(
                f"SHOULD pass rate {should_pass_rate:.1%} below required {self.should_threshold:.1%}"
            )

        # Gate passed if no failures
        passed = len(failures) == 0

        if passed:
            message = (
                f"Gate S PASSED: MUST {must_pass_rate:.1%}, SHOULD {should_pass_rate:.1%}"
            )
        else:
            message = (
                f"Gate S FAILED: MUST {must_pass_rate:.1%}, SHOULD {should_pass_rate:.1%}"
            )

        return {
            'passed': passed,
            'message': message,
            'failures': failures
        }
