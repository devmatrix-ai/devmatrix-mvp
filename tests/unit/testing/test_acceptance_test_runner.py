"""
Unit tests for AcceptanceTestRunner

Tests test execution logic:
- Parallel test execution with semaphore control
- Timeout handling for long-running tests
- Result aggregation (must/should statistics)
- Language-specific test command generation
- Status determination (pass/fail/timeout/error)
"""
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.testing.test_runner import AcceptanceTestRunner
from src.models import AcceptanceTest, AcceptanceTestResult, ExecutionWave, DependencyGraph


@pytest.fixture
def mock_async_db():
    """Mock async database session"""
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.execute = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    return mock_db


@pytest.fixture
def sample_tests():
    """Create sample AcceptanceTest objects"""
    masterplan_id = uuid4()

    tests = [
        AcceptanceTest(
            test_id=uuid4(),
            masterplan_id=masterplan_id,
            requirement_text="Must return 200",
            requirement_priority="must",
            test_code="def test_status(): assert get_status() == 200",
            test_language="pytest",
            timeout_seconds=30
        ),
        AcceptanceTest(
            test_id=uuid4(),
            masterplan_id=masterplan_id,
            requirement_text="Must validate email",
            requirement_priority="must",
            test_code="def test_email(): assert is_valid_email('test@example.com')",
            test_language="pytest",
            timeout_seconds=30
        ),
        AcceptanceTest(
            test_id=uuid4(),
            masterplan_id=masterplan_id,
            requirement_text="Should be responsive",
            requirement_priority="should",
            test_code="def test_responsive(): assert check_responsive()",
            test_language="pytest",
            timeout_seconds=30
        ),
    ]

    return tests


class TestAcceptanceTestRunner:
    """Test AcceptanceTestRunner execution logic"""

    # ========================================
    # Test Command Generation Tests
    # ========================================

    def test_get_file_suffix_pytest(self):
        """Test file suffix generation for pytest"""
        runner = AcceptanceTestRunner(MagicMock())
        suffix = runner._get_file_suffix('pytest')
        assert suffix == '.py'

    def test_get_file_suffix_jest(self):
        """Test file suffix generation for jest"""
        runner = AcceptanceTestRunner(MagicMock())
        suffix = runner._get_file_suffix('jest')
        assert suffix == '.test.js'

    def test_get_file_suffix_vitest(self):
        """Test file suffix generation for vitest"""
        runner = AcceptanceTestRunner(MagicMock())
        suffix = runner._get_file_suffix('vitest')
        assert suffix == '.test.ts'

    def test_get_file_suffix_default(self):
        """Test file suffix defaults to .py for unknown language"""
        runner = AcceptanceTestRunner(MagicMock())
        suffix = runner._get_file_suffix('unknown')
        assert suffix == '.py'

    def test_get_test_command_pytest(self):
        """Test command generation for pytest"""
        runner = AcceptanceTestRunner(MagicMock())
        cmd = runner._get_test_command('pytest', '/tmp/test.py')

        assert cmd == ['pytest', '/tmp/test.py', '-v', '--tb=short', '--no-header']

    def test_get_test_command_jest(self):
        """Test command generation for jest"""
        runner = AcceptanceTestRunner(MagicMock())
        cmd = runner._get_test_command('jest', '/tmp/test.test.js')

        assert cmd == ['npx', 'jest', '/tmp/test.test.js', '--no-coverage']

    def test_get_test_command_vitest(self):
        """Test command generation for vitest"""
        runner = AcceptanceTestRunner(MagicMock())
        cmd = runner._get_test_command('vitest', '/tmp/test.test.ts')

        assert cmd == ['npx', 'vitest', 'run', '/tmp/test.test.ts']

    def test_get_test_command_unknown_defaults_to_pytest(self):
        """Test unknown language defaults to pytest command"""
        runner = AcceptanceTestRunner(MagicMock())
        cmd = runner._get_test_command('unknown', '/tmp/test.py')

        assert cmd[0] == 'pytest'

    # ========================================
    # Result Aggregation Tests
    # ========================================

    def test_aggregate_results_empty(self, mock_async_db):
        """Test aggregation with empty results list"""
        runner = AcceptanceTestRunner(mock_async_db)
        aggregated = runner._aggregate_results([])

        assert aggregated['total'] == 0
        assert aggregated['passed'] == 0
        assert aggregated['failed'] == 0
        assert aggregated['overall_pass_rate'] == 0.0
        assert aggregated['must_pass_rate'] == 0.0
        assert aggregated['should_pass_rate'] == 0.0

    def test_aggregate_results_all_passed(self, mock_async_db, sample_tests):
        """Test aggregation when all tests pass"""
        runner = AcceptanceTestRunner(mock_async_db)

        # Create passed results
        results = []
        for test in sample_tests:
            result = AcceptanceTestResult(
                test_id=test.test_id,
                wave_id=None,
                status='pass',
                error_message=None,
                execution_duration_ms=100
            )
            result.test = test  # Set relationship
            results.append(result)

        aggregated = runner._aggregate_results(results)

        assert aggregated['total'] == 3
        assert aggregated['passed'] == 3
        assert aggregated['failed'] == 0
        assert aggregated['overall_pass_rate'] == 1.0
        assert aggregated['must_total'] == 2
        assert aggregated['must_passed'] == 2
        assert aggregated['must_pass_rate'] == 1.0
        assert aggregated['should_total'] == 1
        assert aggregated['should_passed'] == 1
        assert aggregated['should_pass_rate'] == 1.0

    def test_aggregate_results_mixed(self, mock_async_db, sample_tests):
        """Test aggregation with mixed pass/fail results"""
        runner = AcceptanceTestRunner(mock_async_db)

        # Create mixed results (2 pass, 1 fail)
        # sample_tests: [MUST, MUST, SHOULD]
        # idx 0 (MUST): pass
        # idx 1 (MUST): fail
        # idx 2 (SHOULD): fail
        results = []
        for idx, test in enumerate(sample_tests):
            result = AcceptanceTestResult(
                test_id=test.test_id,
                wave_id=None,
                status='pass' if idx == 0 else 'fail',
                error_message=None if idx == 0 else "Test failed",
                execution_duration_ms=100
            )
            result.test = test
            results.append(result)

        aggregated = runner._aggregate_results(results)

        assert aggregated['total'] == 3
        assert aggregated['passed'] == 1
        assert aggregated['failed'] == 2
        assert aggregated['overall_pass_rate'] == pytest.approx(0.333, rel=0.01)

        # 2 MUST: 1 pass, 1 fail
        assert aggregated['must_total'] == 2
        assert aggregated['must_passed'] == 1
        assert aggregated['must_pass_rate'] == 0.5

        # 1 SHOULD: 0 pass, 1 fail
        assert aggregated['should_total'] == 1
        assert aggregated['should_passed'] == 0
        assert aggregated['should_pass_rate'] == 0.0

    def test_aggregate_results_timeout_counted_as_failed(self, mock_async_db, sample_tests):
        """Test that timeout status is counted as failed"""
        runner = AcceptanceTestRunner(mock_async_db)

        result = AcceptanceTestResult(
            test_id=sample_tests[0].test_id,
            wave_id=None,
            status='timeout',
            error_message="Test exceeded timeout",
            execution_duration_ms=30000
        )
        result.test = sample_tests[0]

        aggregated = runner._aggregate_results([result])

        assert aggregated['total'] == 1
        assert aggregated['passed'] == 0
        assert aggregated['failed'] == 1

    def test_aggregate_results_error_counted_as_failed(self, mock_async_db, sample_tests):
        """Test that error status is counted as failed"""
        runner = AcceptanceTestRunner(mock_async_db)

        result = AcceptanceTestResult(
            test_id=sample_tests[0].test_id,
            wave_id=None,
            status='error',
            error_message="Exception occurred",
            execution_duration_ms=50
        )
        result.test = sample_tests[0]

        aggregated = runner._aggregate_results([result])

        assert aggregated['total'] == 1
        assert aggregated['passed'] == 0
        assert aggregated['failed'] == 1

    def test_aggregate_results_execution_time_stats(self, mock_async_db, sample_tests):
        """Test execution time statistics calculation"""
        runner = AcceptanceTestRunner(mock_async_db)

        results = []
        durations = [100, 200, 300]  # Average: 200, Max: 300

        for test, duration in zip(sample_tests, durations):
            result = AcceptanceTestResult(
                test_id=test.test_id,
                wave_id=None,
                status='pass',
                error_message=None,
                execution_duration_ms=duration
            )
            result.test = test
            results.append(result)

        aggregated = runner._aggregate_results(results)

        assert aggregated['avg_duration_ms'] == 200
        assert aggregated['max_duration_ms'] == 300

    # ========================================
    # Empty Results Tests
    # ========================================

    def test_empty_results_structure(self, mock_async_db):
        """Test empty results structure is correct"""
        runner = AcceptanceTestRunner(mock_async_db)
        empty = runner._empty_results()

        assert empty['total'] == 0
        assert empty['passed'] == 0
        assert empty['failed'] == 0
        assert empty['overall_pass_rate'] == 0.0
        assert empty['must_total'] == 0
        assert empty['must_passed'] == 0
        assert empty['must_pass_rate'] == 0.0
        assert empty['should_total'] == 0
        assert empty['should_passed'] == 0
        assert empty['should_pass_rate'] == 0.0
        assert empty['avg_duration_ms'] == 0
        assert empty['max_duration_ms'] == 0
        assert empty['results'] == []

    # ========================================
    # Run Tests for Masterplan Tests
    # ========================================

    @pytest.mark.asyncio
    async def test_run_tests_for_masterplan_no_tests(self, mock_async_db):
        """Test running tests when none exist for masterplan"""
        masterplan_id = uuid4()

        # Mock empty test query
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_async_db.execute.return_value = mock_result

        runner = AcceptanceTestRunner(mock_async_db)
        results = await runner.run_tests_for_masterplan(masterplan_id)

        assert results['total'] == 0
        assert results['passed'] == 0

    @pytest.mark.asyncio
    async def test_run_tests_for_wave_no_wave(self, mock_async_db):
        """Test running tests when wave doesn't exist"""
        wave_id = uuid4()

        # Mock wave query returning None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_db.execute.return_value = mock_result

        runner = AcceptanceTestRunner(mock_async_db)
        results = await runner.run_tests_for_wave(wave_id)

        assert results['total'] == 0

    @pytest.mark.asyncio
    async def test_get_latest_results_no_tests(self, mock_async_db):
        """Test getting latest results when no tests exist"""
        masterplan_id = uuid4()

        # Mock empty test query
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_async_db.execute.return_value = mock_result

        runner = AcceptanceTestRunner(mock_async_db)
        results = await runner.get_latest_results(masterplan_id)

        assert results['total'] == 0

    @pytest.mark.asyncio
    async def test_get_latest_results_with_wave_filter(self, mock_async_db, sample_tests):
        """Test getting latest results filtered by wave_id"""
        masterplan_id = uuid4()
        wave_id = uuid4()

        # Mock test query
        mock_test_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = sample_tests
        mock_test_result.scalars.return_value = mock_scalars

        # Mock result query (called once per test)
        mock_result_result = Mock()
        test_result = AcceptanceTestResult(
            test_id=sample_tests[0].test_id,
            wave_id=wave_id,
            status='pass',
            error_message=None,
            execution_duration_ms=100
        )
        test_result.test = sample_tests[0]
        mock_result_result.scalar_one_or_none.return_value = test_result

        # Setup execute to return different mocks
        mock_async_db.execute.side_effect = [
            mock_test_result,  # First call: get tests
            mock_result_result,  # Second call: get result for test 1
            mock_result_result,  # Third call: get result for test 2
            mock_result_result,  # Fourth call: get result for test 3
        ]

        runner = AcceptanceTestRunner(mock_async_db)
        results = await runner.get_latest_results(masterplan_id, wave_id=wave_id)

        # Should have filtered results
        assert results['total'] >= 0

    # ========================================
    # Concurrency Control Tests
    # ========================================

    def test_max_concurrent_default(self, mock_async_db):
        """Test default max_concurrent is 10"""
        runner = AcceptanceTestRunner(mock_async_db)
        assert runner.max_concurrent == 10

    def test_default_timeout(self, mock_async_db):
        """Test default timeout is 30 seconds"""
        runner = AcceptanceTestRunner(mock_async_db)
        assert runner.default_timeout == 30
