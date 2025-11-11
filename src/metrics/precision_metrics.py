"""
Precision Metrics Calculator for MGE V2

Implements composite precision score:
- 50% Spec Conformance (acceptance tests pass rate)
- 30% Integration Pass (integration tests pass rate)
- 20% Validation Pass (L1-L4 validation pass rate)

Target: ≥98% precision score
"""
from uuid import UUID
from typing import Dict, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import logging

from src.models import (
    AcceptanceTest,
    AcceptanceTestResult,
    AtomicUnit,
    ExecutionWave,
    MasterPlan
)

logger = logging.getLogger(__name__)


class PrecisionMetricsCalculator:
    """
    Calculate composite precision score for masterplans

    Formula:
    Precision = 50% × Spec Conformance + 30% × Integration + 20% × Validation

    Where:
    - Spec Conformance: % acceptance tests passing (must=100%, should≥95%)
    - Integration: % atoms with successful integration
    - Validation: % atoms passing L1-L4 validation
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

        # Pesos de la fórmula
        self.SPEC_WEIGHT = 0.50
        self.INTEGRATION_WEIGHT = 0.30
        self.VALIDATION_WEIGHT = 0.20

        # Target precision
        self.TARGET_PRECISION = 0.98  # 98%
        self.GATE_A_PRECISION = 0.95  # 95%

    async def calculate_precision_score(
        self,
        masterplan_id: UUID,
        wave_id: Optional[UUID] = None
    ) -> Dict[str, any]:
        """
        Calculate composite precision score for a masterplan

        Args:
            masterplan_id: MasterPlan UUID
            wave_id: Optional wave UUID (calculate for specific wave)

        Returns:
            Dict with precision metrics:
            {
                'precision_score': float,  # 0.0-1.0 (composite)
                'spec_conformance': float,  # 0.0-1.0
                'integration_pass': float,   # 0.0-1.0
                'validation_pass': float,    # 0.0-1.0
                'components': {...},         # Detailed breakdowns
                'meets_target': bool,        # ≥98%
                'meets_gate_a': bool,        # ≥95%
                'timestamp': str
            }
        """
        logger.info(
            f"Calculating precision score for masterplan {masterplan_id}"
            + (f", wave {wave_id}" if wave_id else "")
        )

        # Component 1: Spec Conformance (50%)
        spec_score = await self._calculate_spec_conformance(masterplan_id, wave_id)

        # Component 2: Integration Pass (30%)
        integration_score = await self._calculate_integration_pass(masterplan_id, wave_id)

        # Component 3: Validation Pass (20%)
        validation_score = await self._calculate_validation_pass(masterplan_id, wave_id)

        # Composite precision score
        precision_score = (
            self.SPEC_WEIGHT * spec_score['score'] +
            self.INTEGRATION_WEIGHT * integration_score['score'] +
            self.VALIDATION_WEIGHT * validation_score['score']
        )

        # Gate checks
        meets_target = precision_score >= self.TARGET_PRECISION
        meets_gate_a = precision_score >= self.GATE_A_PRECISION

        result = {
            'precision_score': round(precision_score, 4),
            'precision_percent': round(precision_score * 100, 2),
            'spec_conformance': spec_score['score'],
            'spec_conformance_percent': round(spec_score['score'] * 100, 2),
            'integration_pass': integration_score['score'],
            'integration_pass_percent': round(integration_score['score'] * 100, 2),
            'validation_pass': validation_score['score'],
            'validation_pass_percent': round(validation_score['score'] * 100, 2),
            'components': {
                'spec_conformance': spec_score,
                'integration_pass': integration_score,
                'validation_pass': validation_score
            },
            'weights': {
                'spec': self.SPEC_WEIGHT,
                'integration': self.INTEGRATION_WEIGHT,
                'validation': self.VALIDATION_WEIGHT
            },
            'gates': {
                'target_precision': self.TARGET_PRECISION,
                'gate_a_precision': self.GATE_A_PRECISION,
                'meets_target': meets_target,
                'meets_gate_a': meets_gate_a
            },
            'masterplan_id': str(masterplan_id),
            'wave_id': str(wave_id) if wave_id else None
        }

        logger.info(
            f"Precision score calculated: {precision_score:.1%} "
            f"(spec={spec_score['score']:.1%}, "
            f"integration={integration_score['score']:.1%}, "
            f"validation={validation_score['score']:.1%})"
        )

        return result

    async def _calculate_spec_conformance(
        self,
        masterplan_id: UUID,
        wave_id: Optional[UUID] = None
    ) -> Dict[str, any]:
        """
        Calculate Spec Conformance: % acceptance tests passing

        Enforces:
        - 100% MUST requirements passing
        - ≥95% SHOULD requirements passing

        Returns score 0.0-1.0
        """
        # Get all acceptance tests for masterplan
        result = await self.db.execute(
            select(AcceptanceTest).where(
                AcceptanceTest.masterplan_id == masterplan_id
            )
        )
        tests = result.scalars().all()

        if not tests:
            logger.warning(f"No acceptance tests found for masterplan {masterplan_id}")
            return {
                'score': 0.0,
                'must_pass_rate': 0.0,
                'should_pass_rate': 0.0,
                'total_tests': 0,
                'must_tests': 0,
                'should_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0
            }

        # Split by priority
        must_tests = [t for t in tests if t.requirement_priority == 'must']
        should_tests = [t for t in tests if t.requirement_priority == 'should']

        # Get latest test results
        must_results = await self._get_latest_test_results(must_tests, wave_id)
        should_results = await self._get_latest_test_results(should_tests, wave_id)

        # Calculate pass rates
        must_passed = sum(1 for r in must_results if r.status == 'pass')
        must_pass_rate = must_passed / len(must_results) if must_results else 0.0

        should_passed = sum(1 for r in should_results if r.status == 'pass')
        should_pass_rate = should_passed / len(should_results) if should_results else 1.0  # Default 100% if no should tests

        # Conformance score
        # - If MUST <100%: score is (must_pass_rate)
        # - If MUST =100% and SHOULD <95%: score is (0.75 + 0.25×should_pass_rate)
        # - If MUST =100% and SHOULD ≥95%: score is 1.0

        if must_pass_rate < 1.0:
            # MUST requirements not met: score reflects must pass rate
            score = must_pass_rate
        elif should_pass_rate < 0.95:
            # MUST OK but SHOULD below threshold
            score = 0.75 + 0.25 * should_pass_rate
        else:
            # Both gates passed
            score = 1.0

        return {
            'score': round(score, 4),
            'must_pass_rate': round(must_pass_rate, 4),
            'should_pass_rate': round(should_pass_rate, 4),
            'total_tests': len(tests),
            'must_tests': len(must_tests),
            'should_tests': len(should_tests),
            'must_passed': must_passed,
            'should_passed': should_passed,
            'passed_tests': must_passed + should_passed,
            'failed_tests': len(tests) - (must_passed + should_passed)
        }

    async def _calculate_integration_pass(
        self,
        masterplan_id: UUID,
        wave_id: Optional[UUID] = None
    ) -> Dict[str, any]:
        """
        Calculate Integration Pass: % atoms with successful integration

        Integration success means:
        - Atom was executed successfully
        - No runtime errors during execution
        - Dependencies resolved correctly

        Returns score 0.0-1.0
        """
        # Get all atoms for masterplan
        query = select(AtomicUnit).where(
            AtomicUnit.masterplan_id == masterplan_id
        )

        if wave_id:
            query = query.where(AtomicUnit.wave_id == wave_id)

        result = await self.db.execute(query)
        atoms = result.scalars().all()

        if not atoms:
            logger.warning(f"No atoms found for masterplan {masterplan_id}")
            return {
                'score': 0.0,
                'total_atoms': 0,
                'integrated_atoms': 0,
                'failed_atoms': 0,
                'integration_rate': 0.0
            }

        # Count successful integrations
        # An atom is "integrated" if it has execution_status = 'success'
        integrated = sum(
            1 for atom in atoms
            if atom.execution_status == 'success'
        )

        failed = sum(
            1 for atom in atoms
            if atom.execution_status in ('failed', 'error', 'timeout')
        )

        integration_rate = integrated / len(atoms) if atoms else 0.0

        return {
            'score': round(integration_rate, 4),
            'total_atoms': len(atoms),
            'integrated_atoms': integrated,
            'failed_atoms': failed,
            'pending_atoms': len(atoms) - integrated - failed,
            'integration_rate': round(integration_rate, 4)
        }

    async def _calculate_validation_pass(
        self,
        masterplan_id: UUID,
        wave_id: Optional[UUID] = None
    ) -> Dict[str, any]:
        """
        Calculate Validation Pass: % atoms passing L1-L4 validation

        Validation layers:
        - L1: Syntax validation (Python AST, TS parser)
        - L2: Import resolution
        - L3: Type checking
        - L4: Complexity and quality metrics

        Returns score 0.0-1.0
        """
        # Get all atoms for masterplan
        query = select(AtomicUnit).where(
            AtomicUnit.masterplan_id == masterplan_id
        )

        if wave_id:
            query = query.where(AtomicUnit.wave_id == wave_id)

        result = await self.db.execute(query)
        atoms = result.scalars().all()

        if not atoms:
            logger.warning(f"No atoms found for masterplan {masterplan_id}")
            return {
                'score': 0.0,
                'total_atoms': 0,
                'validated_atoms': 0,
                'validation_failures': {
                    'L1_syntax': 0,
                    'L2_imports': 0,
                    'L3_types': 0,
                    'L4_complexity': 0
                }
            }

        # Count validation results per layer
        # validation_results is a JSONB field with structure:
        # {
        #   'L1_syntax': {'passed': bool, 'errors': []},
        #   'L2_imports': {'passed': bool, 'errors': []},
        #   'L3_types': {'passed': bool, 'errors': []},
        #   'L4_complexity': {'passed': bool, 'metrics': {}}
        # }

        validation_failures = {
            'L1_syntax': 0,
            'L2_imports': 0,
            'L3_types': 0,
            'L4_complexity': 0
        }

        fully_validated = 0

        for atom in atoms:
            if not atom.validation_results:
                # No validation results yet
                continue

            # Check each layer
            all_passed = True
            for layer in ['L1_syntax', 'L2_imports', 'L3_types', 'L4_complexity']:
                layer_result = atom.validation_results.get(layer, {})
                if not layer_result.get('passed', False):
                    validation_failures[layer] += 1
                    all_passed = False

            if all_passed:
                fully_validated += 1

        validation_rate = fully_validated / len(atoms) if atoms else 0.0

        return {
            'score': round(validation_rate, 4),
            'total_atoms': len(atoms),
            'validated_atoms': fully_validated,
            'validation_rate': round(validation_rate, 4),
            'validation_failures': validation_failures,
            'failure_rates': {
                layer: round(count / len(atoms), 4) if atoms else 0.0
                for layer, count in validation_failures.items()
            }
        }

    async def _get_latest_test_results(
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

            query = query.order_by(
                AcceptanceTestResult.execution_time.desc()
            ).limit(1)

            result = await self.db.execute(query)
            latest_result = result.scalar_one_or_none()

            if latest_result:
                results.append(latest_result)

        return results

    async def get_precision_report(
        self,
        masterplan_id: UUID,
        wave_id: Optional[UUID] = None
    ) -> str:
        """
        Generate detailed precision report

        Args:
            masterplan_id: MasterPlan UUID
            wave_id: Optional wave UUID

        Returns:
            Formatted report string
        """
        metrics = await self.calculate_precision_score(masterplan_id, wave_id)

        report = f"""
═══════════════════════════════════════════════════════════
                    PRECISION SCORE REPORT
═══════════════════════════════════════════════════════════

MasterPlan: {masterplan_id}
Wave: {wave_id or 'N/A'}

───────────────────────────────────────────────────────────
COMPOSITE PRECISION SCORE
───────────────────────────────────────────────────────────
Score: {metrics['precision_percent']:.2f}%
Target: {metrics['gates']['target_precision'] * 100:.0f}%
Status: {'✓ MEETS TARGET' if metrics['gates']['meets_target'] else '✗ BELOW TARGET'}

───────────────────────────────────────────────────────────
COMPONENTS
───────────────────────────────────────────────────────────
1. Spec Conformance (50% weight): {metrics['spec_conformance_percent']:.2f}%
   • MUST pass rate: {metrics['components']['spec_conformance']['must_pass_rate']:.1%}
   • SHOULD pass rate: {metrics['components']['spec_conformance']['should_pass_rate']:.1%}
   • Total tests: {metrics['components']['spec_conformance']['total_tests']}
   • Passed: {metrics['components']['spec_conformance']['passed_tests']}
   • Failed: {metrics['components']['spec_conformance']['failed_tests']}

2. Integration Pass (30% weight): {metrics['integration_pass_percent']:.2f}%
   • Total atoms: {metrics['components']['integration_pass']['total_atoms']}
   • Integrated: {metrics['components']['integration_pass']['integrated_atoms']}
   • Failed: {metrics['components']['integration_pass']['failed_atoms']}

3. Validation Pass (20% weight): {metrics['validation_pass_percent']:.2f}%
   • Total atoms: {metrics['components']['validation_pass']['total_atoms']}
   • Validated: {metrics['components']['validation_pass']['validated_atoms']}
   • Failure rates:
     - L1 (Syntax): {metrics['components']['validation_pass']['failure_rates']['L1_syntax']:.1%}
     - L2 (Imports): {metrics['components']['validation_pass']['failure_rates']['L2_imports']:.1%}
     - L3 (Types): {metrics['components']['validation_pass']['failure_rates']['L3_types']:.1%}
     - L4 (Complexity): {metrics['components']['validation_pass']['failure_rates']['L4_complexity']:.1%}

───────────────────────────────────────────────────────────
GATES
───────────────────────────────────────────────────────────
Gate A (95%): {'✓ PASS' if metrics['gates']['meets_gate_a'] else '✗ FAIL'}
Gate S (98%): {'✓ PASS' if metrics['gates']['meets_target'] else '✗ FAIL'}

═══════════════════════════════════════════════════════════
"""

        return report
