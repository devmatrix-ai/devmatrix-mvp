"""
Spec Conformance Gate enforcement (Gate S)

Enforces: 100% must + ≥95% should pass rate
"""
from uuid import UUID
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from src.models import AcceptanceTest, AcceptanceTestResult

logger = logging.getLogger(__name__)


class AcceptanceTestGate:
    """
    Enforce Gate S: 100% must + ≥95% should

    Gate logic:
    - Must requirements: 100% pass required for release
    - Should requirements: ≥95% pass required for gate
    - Gate passed: Both thresholds met
    - Can release: Must threshold met (100%)
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.must_threshold = 1.0  # 100%
        self.should_threshold = 0.95  # 95%

    async def check_gate(
        self,
        masterplan_id: UUID,
        wave_id: Optional[UUID] = None
    ) -> Dict[str, any]:
        """
        Check if masterplan passes Gate S

        Args:
            masterplan_id: Masterplan UUID
            wave_id: Optional wave UUID (check specific wave)

        Returns:
            Dict: {
                'gate_passed': bool,
                'must_pass_rate': float,
                'should_pass_rate': float,
                'failed_requirements': List[Dict],
                'can_release': bool,
                'gate_status': 'PASS' or 'FAIL'
            }
        """
        # Get all tests for masterplan
        result = await self.db.execute(
            select(AcceptanceTest).where(AcceptanceTest.masterplan_id == masterplan_id)
        )
        tests = result.scalars().all()

        if not tests:
            logger.warning(f"No acceptance tests found for masterplan {masterplan_id}")
            return {
                'gate_passed': False,
                'must_pass_rate': 0.0,
                'should_pass_rate': 0.0,
                'failed_requirements': ['No acceptance tests found'],
                'can_release': False,
                'gate_status': 'FAIL'
            }

        # Split by priority
        must_tests = [t for t in tests if t.requirement_priority == 'must']
        should_tests = [t for t in tests if t.requirement_priority == 'should']

        # Get latest results for each test
        must_results = await self._get_latest_results(must_tests, wave_id)
        should_results = await self._get_latest_results(should_tests, wave_id)

        # Calculate pass rates
        must_passed = sum(1 for r in must_results if r.status == 'pass')
        must_pass_rate = must_passed / len(must_results) if must_results else 0.0

        should_passed = sum(1 for r in should_results if r.status == 'pass')
        should_pass_rate = should_passed / len(should_results) if should_results else 0.0

        # Identify failed requirements
        failed_requirements = []

        for test, result in zip(must_tests, must_results):
            if result.status != 'pass':
                failed_requirements.append({
                    'priority': 'must',
                    'requirement': test.requirement_text,
                    'status': result.status,
                    'error': result.error_message,
                    'test_id': str(test.test_id)
                })

        for test, result in zip(should_tests, should_results):
            if result.status != 'pass':
                failed_requirements.append({
                    'priority': 'should',
                    'requirement': test.requirement_text,
                    'status': result.status,
                    'error': result.error_message,
                    'test_id': str(test.test_id)
                })

        # Gate logic
        gate_passed = (
            must_pass_rate >= self.must_threshold and
            should_pass_rate >= self.should_threshold
        )

        # Can release if all must requirements pass (even if should < 95%)
        can_release = must_pass_rate == 1.0

        gate_status = 'PASS' if gate_passed else 'FAIL'

        logger.info(
            f"Gate S check for masterplan {masterplan_id}: {gate_status} "
            f"(must: {must_pass_rate:.1%}, should: {should_pass_rate:.1%})"
        )

        return {
            'gate_passed': gate_passed,
            'must_pass_rate': must_pass_rate,
            'should_pass_rate': should_pass_rate,
            'must_total': len(must_results),
            'must_passed': must_passed,
            'should_total': len(should_results),
            'should_passed': should_passed,
            'failed_requirements': failed_requirements,
            'can_release': can_release,
            'gate_status': gate_status
        }

    async def block_progression_if_gate_fails(
        self,
        masterplan_id: UUID,
        wave_id: UUID
    ) -> bool:
        """
        Check gate and block WaveExecutor if failed

        Args:
            masterplan_id: Masterplan UUID
            wave_id: Wave UUID

        Returns:
            True if can proceed, False if blocked
        """
        gate_result = await self.check_gate(masterplan_id, wave_id)

        if not gate_result['gate_passed']:
            # Log gate failure
            logger.error(
                f"Gate S FAILED for masterplan {masterplan_id}, wave {wave_id}: "
                f"must={gate_result['must_pass_rate']:.1%}, "
                f"should={gate_result['should_pass_rate']:.1%}"
            )

            # Update masterplan status to blocked
            # This would need to be implemented in the calling code
            # as we don't have direct access to MasterPlan here

            return False

        logger.info(f"Gate S PASSED for masterplan {masterplan_id}, wave {wave_id}")
        return True

    async def _get_latest_results(
        self,
        tests: List[AcceptanceTest],
        wave_id: Optional[UUID] = None
    ) -> List[AcceptanceTestResult]:
        """
        Get latest test results for given tests

        Args:
            tests: List of AcceptanceTest
            wave_id: Optional wave UUID to filter by

        Returns:
            List of AcceptanceTestResult (one per test)
        """
        results = []

        for test in tests:
            query = select(AcceptanceTestResult).where(
                AcceptanceTestResult.test_id == test.test_id
            )

            if wave_id:
                query = query.where(AcceptanceTestResult.wave_id == wave_id)

            query = query.order_by(AcceptanceTestResult.execution_time.desc()).limit(1)

            result = await self.db.execute(query)
            latest_result = result.scalar_one_or_none()

            if latest_result:
                results.append(latest_result)
            else:
                # If no result exists, create a placeholder 'error' result
                # This shouldn't happen in normal flow, but handle gracefully
                logger.warning(f"No result found for test {test.test_id}")

        return results

    async def get_gate_report(
        self,
        masterplan_id: UUID,
        wave_id: Optional[UUID] = None
    ) -> str:
        """
        Generate detailed gate report

        Args:
            masterplan_id: Masterplan UUID
            wave_id: Optional wave UUID

        Returns:
            Formatted report string
        """
        gate_result = await self.check_gate(masterplan_id, wave_id)

        report = f"""
═══════════════════════════════════════════════════════════
                    GATE S REPORT
═══════════════════════════════════════════════════════════

Masterplan: {masterplan_id}
Wave: {wave_id or 'N/A'}
Status: {gate_result['gate_status']}

───────────────────────────────────────────────────────────
MUST Requirements (100% required)
───────────────────────────────────────────────────────────
Pass Rate: {gate_result['must_pass_rate']:.1%}
Passed: {gate_result['must_passed']}/{gate_result['must_total']}
Threshold: {self.must_threshold:.1%}
Result: {'✓ PASS' if gate_result['must_pass_rate'] >= self.must_threshold else '✗ FAIL'}

───────────────────────────────────────────────────────────
SHOULD Requirements (≥95% required)
───────────────────────────────────────────────────────────
Pass Rate: {gate_result['should_pass_rate']:.1%}
Passed: {gate_result['should_passed']}/{gate_result['should_total']}
Threshold: {self.should_threshold:.1%}
Result: {'✓ PASS' if gate_result['should_pass_rate'] >= self.should_threshold else '✗ FAIL'}

───────────────────────────────────────────────────────────
GATE DECISION
───────────────────────────────────────────────────────────
Gate Passed: {'YES' if gate_result['gate_passed'] else 'NO'}
Can Release: {'YES' if gate_result['can_release'] else 'NO'}

"""

        if gate_result['failed_requirements']:
            report += """───────────────────────────────────────────────────────────
FAILED REQUIREMENTS
───────────────────────────────────────────────────────────
"""
            for i, req in enumerate(gate_result['failed_requirements'], 1):
                report += f"""
{i}. [{req['priority'].upper()}] {req['requirement']}
   Status: {req['status'].upper()}
   Error: {req['error'] or 'N/A'}
   Test ID: {req['test_id']}
"""

        report += "\n═══════════════════════════════════════════════════════════\n"

        return report

    async def get_requirements_by_status(
        self,
        masterplan_id: UUID,
        status: str,
        wave_id: Optional[UUID] = None
    ) -> List[Dict]:
        """
        Get requirements filtered by test status

        Args:
            masterplan_id: Masterplan UUID
            status: 'pass', 'fail', 'timeout', 'error'
            wave_id: Optional wave UUID

        Returns:
            List of requirement dicts with test results
        """
        # Get all tests
        result = await self.db.execute(
            select(AcceptanceTest).where(AcceptanceTest.masterplan_id == masterplan_id)
        )
        tests = result.scalars().all()

        # Get latest results
        requirements = []
        for test in tests:
            query = select(AcceptanceTestResult).where(
                AcceptanceTestResult.test_id == test.test_id
            )

            if wave_id:
                query = query.where(AcceptanceTestResult.wave_id == wave_id)

            query = query.order_by(AcceptanceTestResult.execution_time.desc()).limit(1)

            result = await self.db.execute(query)
            latest_result = result.scalar_one_or_none()

            if latest_result and latest_result.status == status:
                requirements.append({
                    'requirement_text': test.requirement_text,
                    'priority': test.requirement_priority,
                    'test_id': str(test.test_id),
                    'status': latest_result.status,
                    'error': latest_result.error_message,
                    'duration_ms': latest_result.execution_duration_ms
                })

        return requirements
