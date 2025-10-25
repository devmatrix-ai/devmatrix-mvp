"""
Tests for AcceptanceTestRunner

Tests test execution with parallel processing and timeout handling.
"""
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from src.testing.test_runner import AcceptanceTestRunner
from src.models import AcceptanceTest, AcceptanceTestResult, ExecutionWave


@pytest.mark.asyncio
class TestAcceptanceTestRunner:
    """Test AcceptanceTestRunner functionality"""

    @pytest.fixture
    def wave_id(self):
        """Generate test wave ID"""
        return uuid4()

    @pytest.fixture
    def masterplan_id(self):
        """Generate test masterplan ID"""
        return uuid4()

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        db = AsyncMock()
        db.commit = AsyncMock()
        db.add = MagicMock()
        return db

    @pytest.fixture
    async def runner(self, mock_db):
        """Create AcceptanceTestRunner instance"""
        return AcceptanceTestRunner(mock_db)

    @pytest.fixture
    def mock_wave(self, wave_id, masterplan_id):
        """Create mock ExecutionWave"""
        wave = MagicMock()
        wave.wave_id = wave_id
        wave.graph = MagicMock()
        wave.graph.masterplan_id = masterplan_id
        return wave

    @pytest.fixture
    def mock_tests(self, masterplan_id):
        """Create mock AcceptanceTest list"""
        return [
            AcceptanceTest(
                test_id=uuid4(),
                masterplan_id=masterplan_id,
                requirement_text="Must do A",
                requirement_priority='must',
                test_code='def test_a():\n    assert True',
                test_language='pytest',
                timeout_seconds=30
            ),
            AcceptanceTest(
                test_id=uuid4(),
                masterplan_id=masterplan_id,
                requirement_text="Should do B",
                requirement_priority='should',
                test_code='def test_b():\n    assert True',
                test_language='pytest',
                timeout_seconds=30
            )
        ]

    async def test_run_tests_for_wave(self, runner, wave_id, mock_wave, mock_tests, mock_db):
        """Test running tests for a wave"""
        # Mock wave query
        wave_result = MagicMock()
        wave_result.scalar_one_or_none.return_value = mock_wave

        # Mock tests query
        tests_result = MagicMock()
        tests_result.scalars().all.return_value = mock_tests

        mock_db.execute.side_effect = [wave_result, tests_result]

        # Mock subprocess execution
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b'', b'')
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            results = await runner.run_tests_for_wave(wave_id)

            assert results['total'] == 2
            assert results['passed'] >= 0
            assert 'results' in results

    async def test_aggregate_results_calculates_pass_rates(self, runner, mock_tests):
        """Test result aggregation calculates correct pass rates"""
        # Create mock results
        results = [
            AcceptanceTestResult(
                result_id=uuid4(),
                test_id=mock_tests[0].test_id,
                wave_id=uuid4(),
                status='pass',
                execution_duration_ms=100
            ),
            AcceptanceTestResult(
                result_id=uuid4(),
                test_id=mock_tests[1].test_id,
                wave_id=uuid4(),
                status='fail',
                execution_duration_ms=200
            )
        ]

        # Attach test objects to results
        results[0].test = mock_tests[0]
        results[1].test = mock_tests[1]

        aggregated = runner._aggregate_results(results)

        assert aggregated['total'] == 2
        assert aggregated['passed'] == 1
        assert aggregated['failed'] == 1
        assert 0 < aggregated['overall_pass_rate'] < 1

    async def test_empty_results_handling(self, runner):
        """Test handling of empty results"""
        result = runner._empty_results()

        assert result['total'] == 0
        assert result['passed'] == 0
        assert result['failed'] == 0
        assert result['overall_pass_rate'] == 0.0

    async def test_get_test_command_pytest(self, runner):
        """Test pytest command generation"""
        cmd = runner._get_test_command('pytest', '/tmp/test.py')

        assert cmd[0] == 'pytest'
        assert '/tmp/test.py' in cmd
        assert '-v' in cmd

    async def test_get_test_command_jest(self, runner):
        """Test Jest command generation"""
        cmd = runner._get_test_command('jest', '/tmp/test.js')

        assert 'jest' in cmd
        assert '/tmp/test.js' in cmd

    async def test_file_suffix_pytest(self, runner):
        """Test file suffix for pytest"""
        suffix = runner._get_file_suffix('pytest')
        assert suffix == '.py'

    async def test_file_suffix_jest(self, runner):
        """Test file suffix for Jest"""
        suffix = runner._get_file_suffix('jest')
        assert suffix == '.test.js'

    async def test_concurrency_limit(self, runner):
        """Test concurrency limit is respected"""
        assert runner.max_concurrent == 10

    async def test_timeout_default(self, runner):
        """Test default timeout"""
        assert runner.default_timeout == 30
