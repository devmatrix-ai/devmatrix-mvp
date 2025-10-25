"""
Acceptance test execution engine

Executes generated acceptance tests with parallel execution and timeout handling.
"""
import asyncio
import subprocess
import tempfile
from pathlib import Path
from uuid import UUID
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import time

from src.models import AcceptanceTest, AcceptanceTestResult, ExecutionWave

logger = logging.getLogger(__name__)


class AcceptanceTestRunner:
    """
    Execute generated acceptance tests

    Features:
    - Parallel execution (max 10 concurrent tests)
    - Timeout handling (30s default)
    - Result aggregation
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.default_timeout = 30  # seconds
        self.max_concurrent = 10  # max parallel tests

    async def run_tests_for_wave(self, wave_id: UUID) -> Dict[str, any]:
        """
        Run all acceptance tests for a wave's masterplan

        Args:
            wave_id: Wave UUID

        Returns:
            Dict with results: {total, passed, failed, must_passed, should_passed, results}
        """
        # Get masterplan_id from wave
        result = await self.db.execute(
            select(ExecutionWave).where(ExecutionWave.wave_id == wave_id)
        )
        wave = result.scalar_one_or_none()

        if not wave:
            logger.error(f"Wave {wave_id} not found")
            return self._empty_results()

        masterplan_id = wave.graph.masterplan_id

        # Get all tests for masterplan
        result = await self.db.execute(
            select(AcceptanceTest).where(AcceptanceTest.masterplan_id == masterplan_id)
        )
        tests = result.scalars().all()

        if not tests:
            logger.warning(f"No acceptance tests found for masterplan {masterplan_id}")
            return self._empty_results()

        logger.info(f"Running {len(tests)} acceptance tests for wave {wave_id}")

        # Run tests in parallel (with concurrency limit)
        semaphore = asyncio.Semaphore(self.max_concurrent)
        tasks = [self._run_single_test(test, wave_id, semaphore) for test in tests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and log them
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Test {tests[i].test_id} failed with exception: {result}")
            else:
                valid_results.append(result)

        # Aggregate results
        return self._aggregate_results(valid_results)

    async def run_tests_for_masterplan(self, masterplan_id: UUID) -> Dict[str, any]:
        """
        Run all acceptance tests for a masterplan (without wave context)

        Args:
            masterplan_id: Masterplan UUID

        Returns:
            Dict with aggregated results
        """
        # Get all tests for masterplan
        result = await self.db.execute(
            select(AcceptanceTest).where(AcceptanceTest.masterplan_id == masterplan_id)
        )
        tests = result.scalars().all()

        if not tests:
            logger.warning(f"No acceptance tests found for masterplan {masterplan_id}")
            return self._empty_results()

        logger.info(f"Running {len(tests)} acceptance tests for masterplan {masterplan_id}")

        # Run tests in parallel
        semaphore = asyncio.Semaphore(self.max_concurrent)
        tasks = [self._run_single_test(test, None, semaphore) for test in tests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter exceptions
        valid_results = [r for r in results if not isinstance(r, Exception)]

        return self._aggregate_results(valid_results)

    async def _run_single_test(
        self,
        test: AcceptanceTest,
        wave_id: Optional[UUID],
        semaphore: asyncio.Semaphore
    ) -> AcceptanceTestResult:
        """
        Execute a single acceptance test

        Args:
            test: AcceptanceTest to run
            wave_id: Optional wave UUID
            semaphore: Concurrency control

        Returns:
            AcceptanceTestResult
        """
        async with semaphore:
            start_time = time.time()

            try:
                # Create temporary file for test
                suffix = self._get_file_suffix(test.test_language)
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix=suffix,
                    delete=False
                ) as f:
                    f.write(test.test_code)
                    test_file = f.name

                # Execute test based on framework
                cmd = self._get_test_command(test.test_language, test_file)

                logger.debug(f"Executing test {test.test_id}: {' '.join(cmd)}")

                # Run with timeout
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=Path(test_file).parent
                )

                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=test.timeout_seconds or self.default_timeout
                    )

                    execution_duration = int((time.time() - start_time) * 1000)

                    # Determine status from return code
                    if process.returncode == 0:
                        status = 'pass'
                        error_message = None
                    else:
                        status = 'fail'
                        error_message = stderr.decode('utf-8') if stderr else "Test failed"

                    logger.info(
                        f"Test {test.test_id} {status} "
                        f"(duration: {execution_duration}ms)"
                    )

                except asyncio.TimeoutError:
                    process.kill()
                    status = 'timeout'
                    error_message = f"Test exceeded timeout of {test.timeout_seconds}s"
                    stdout, stderr = b'', b''
                    execution_duration = test.timeout_seconds * 1000

                    logger.warning(f"Test {test.test_id} timed out")

                # Clean up temp file
                try:
                    Path(test_file).unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {test_file}: {e}")

            except Exception as e:
                status = 'error'
                error_message = str(e)
                stdout, stderr = b'', b''
                execution_duration = int((time.time() - start_time) * 1000)

                logger.error(f"Test {test.test_id} error: {e}")

            # Store result
            result = AcceptanceTestResult(
                test_id=test.test_id,
                wave_id=wave_id,
                status=status,
                error_message=error_message,
                execution_duration_ms=execution_duration,
                stdout=stdout.decode('utf-8') if stdout else None,
                stderr=stderr.decode('utf-8') if stderr else None
            )

            self.db.add(result)
            await self.db.commit()

            return result

    def _get_file_suffix(self, test_language: str) -> str:
        """Get file suffix for test language"""
        suffixes = {
            'pytest': '.py',
            'jest': '.test.js',
            'vitest': '.test.ts'
        }
        return suffixes.get(test_language, '.py')

    def _get_test_command(self, test_language: str, test_file: str) -> List[str]:
        """
        Get command to execute test

        Args:
            test_language: 'pytest', 'jest', or 'vitest'
            test_file: Path to test file

        Returns:
            Command as list of strings
        """
        if test_language == 'pytest':
            return ['pytest', test_file, '-v', '--tb=short', '--no-header']

        elif test_language == 'jest':
            return ['npx', 'jest', test_file, '--no-coverage']

        elif test_language == 'vitest':
            return ['npx', 'vitest', 'run', test_file]

        else:
            logger.warning(f"Unknown test language {test_language}, defaulting to pytest")
            return ['pytest', test_file, '-v', '--tb=short']

    def _aggregate_results(self, results: List[AcceptanceTestResult]) -> Dict[str, any]:
        """
        Aggregate test results into summary

        Args:
            results: List of AcceptanceTestResult

        Returns:
            Dict with aggregated statistics
        """
        if not results:
            return self._empty_results()

        total = len(results)
        passed = sum(1 for r in results if r.status == 'pass')
        failed = sum(1 for r in results if r.status in ['fail', 'timeout', 'error'])

        # Get must/should breakdown
        must_results = []
        should_results = []

        for result in results:
            # Need to fetch test to get priority
            # This is already loaded from the relationship, but being explicit
            if result.test.requirement_priority == 'must':
                must_results.append(result)
            else:
                should_results.append(result)

        must_total = len(must_results)
        must_passed = sum(1 for r in must_results if r.status == 'pass')

        should_total = len(should_results)
        should_passed = sum(1 for r in should_results if r.status == 'pass')

        # Calculate pass rates
        overall_pass_rate = passed / total if total > 0 else 0.0
        must_pass_rate = must_passed / must_total if must_total > 0 else 0.0
        should_pass_rate = should_passed / should_total if should_total > 0 else 0.0

        # Execution time stats
        durations = [r.execution_duration_ms for r in results if r.execution_duration_ms]
        avg_duration = sum(durations) / len(durations) if durations else 0
        max_duration = max(durations) if durations else 0

        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'overall_pass_rate': overall_pass_rate,

            'must_total': must_total,
            'must_passed': must_passed,
            'must_pass_rate': must_pass_rate,

            'should_total': should_total,
            'should_passed': should_passed,
            'should_pass_rate': should_pass_rate,

            'avg_duration_ms': int(avg_duration),
            'max_duration_ms': max_duration,

            'results': results
        }

    def _empty_results(self) -> Dict[str, any]:
        """Return empty results structure"""
        return {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'overall_pass_rate': 0.0,
            'must_total': 0,
            'must_passed': 0,
            'must_pass_rate': 0.0,
            'should_total': 0,
            'should_passed': 0,
            'should_pass_rate': 0.0,
            'avg_duration_ms': 0,
            'max_duration_ms': 0,
            'results': []
        }

    async def get_latest_results(
        self,
        masterplan_id: UUID,
        wave_id: Optional[UUID] = None
    ) -> Dict[str, any]:
        """
        Get latest test results for a masterplan

        Args:
            masterplan_id: Masterplan UUID
            wave_id: Optional wave UUID to filter by

        Returns:
            Aggregated results dict
        """
        # Get all tests for masterplan
        result = await self.db.execute(
            select(AcceptanceTest).where(AcceptanceTest.masterplan_id == masterplan_id)
        )
        tests = result.scalars().all()

        if not tests:
            return self._empty_results()

        # Get latest result for each test
        latest_results = []
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
                latest_results.append(latest_result)

        return self._aggregate_results(latest_results)
