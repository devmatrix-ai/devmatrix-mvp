"""
Unit tests for AcceptanceTestGate (Gate S enforcement)

Tests Gate S logic:
- 100% must + ≥95% should pass rate enforcement
- Gate pass/fail decision logic
- Failed requirements tracking
- Report generation
- Requirements filtering by status
"""
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from src.testing.acceptance_gate import AcceptanceTestGate
from src.models import AcceptanceTest, AcceptanceTestResult


@pytest.fixture
def mock_async_db():
    """Mock async database session"""
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.execute = AsyncMock()
    return mock_db


@pytest.fixture
def sample_must_tests():
    """Create sample MUST tests"""
    masterplan_id = uuid4()
    return [
        AcceptanceTest(
            test_id=uuid4(),
            masterplan_id=masterplan_id,
            requirement_text="Must use JWT tokens",
            requirement_priority="must",
            test_code="",
            test_language="pytest"
        ),
        AcceptanceTest(
            test_id=uuid4(),
            masterplan_id=masterplan_id,
            requirement_text="Must be ACID compliant",
            requirement_priority="must",
            test_code="",
            test_language="pytest"
        ),
    ]


@pytest.fixture
def sample_should_tests():
    """Create sample SHOULD tests"""
    masterplan_id = uuid4()
    return [
        AcceptanceTest(
            test_id=uuid4(),
            masterplan_id=masterplan_id,
            requirement_text="Should be responsive",
            requirement_priority="should",
            test_code="",
            test_language="pytest"
        ),
        AcceptanceTest(
            test_id=uuid4(),
            masterplan_id=masterplan_id,
            requirement_text="Should be fast",
            requirement_priority="should",
            test_code="",
            test_language="pytest"
        ),
    ]


class TestAcceptanceTestGate:
    """Test AcceptanceTestGate Gate S enforcement"""

    # ========================================
    # Threshold Tests
    # ========================================

    def test_must_threshold_is_100_percent(self, mock_async_db):
        """Test MUST threshold is exactly 100%"""
        gate = AcceptanceTestGate(mock_async_db)
        assert gate.must_threshold == 1.0

    def test_should_threshold_is_95_percent(self, mock_async_db):
        """Test SHOULD threshold is 95%"""
        gate = AcceptanceTestGate(mock_async_db)
        assert gate.should_threshold == 0.95

    # ========================================
    # Gate Pass Logic Tests
    # ========================================

    @pytest.mark.asyncio
    async def test_gate_passes_100_must_100_should(self, mock_async_db, sample_must_tests, sample_should_tests):
        """Test gate passes with 100% must and 100% should"""
        masterplan_id = sample_must_tests[0].masterplan_id
        all_tests = sample_must_tests + sample_should_tests

        # Mock test query
        mock_test_result = AsyncMock()
        mock_test_result.scalars.return_value.all.return_value = all_tests

        # Mock result queries (all pass)
        mock_results = []
        for test in all_tests:
            result = AcceptanceTestResult(
                test_id=test.test_id,
                wave_id=None,
                status='pass',
                error_message=None,
                execution_duration_ms=100
            )
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = result
            mock_results.append(mock_result)

        # Setup execute to return mocks
        mock_async_db.execute.side_effect = [mock_test_result] + mock_results

        gate = AcceptanceTestGate(mock_async_db)
        result = await gate.check_gate(masterplan_id)

        assert result['gate_passed'] is True
        assert result['must_pass_rate'] == 1.0
        assert result['should_pass_rate'] == 1.0
        assert result['can_release'] is True
        assert result['gate_status'] == 'PASS'

    @pytest.mark.asyncio
    async def test_gate_passes_100_must_95_should(self, mock_async_db, sample_must_tests):
        """Test gate passes with 100% must and exactly 95% should"""
        masterplan_id = sample_must_tests[0].masterplan_id

        # Create 20 should tests (19 pass, 1 fail = 95%)
        should_tests = []
        for i in range(20):
            should_tests.append(AcceptanceTest(
                test_id=uuid4(),
                masterplan_id=masterplan_id,
                requirement_text=f"Should requirement {i}",
                requirement_priority="should",
                test_code="",
                test_language="pytest"
            ))

        all_tests = sample_must_tests + should_tests

        # Mock test query
        mock_test_result = AsyncMock()
        mock_test_result.scalars.return_value.all.return_value = all_tests

        # Mock results (2 must pass, 19 should pass, 1 should fail)
        mock_results = []
        for idx, test in enumerate(all_tests):
            # First 2 are must (all pass), next 19 should pass, last should fails
            status = 'pass' if idx < 21 else 'fail'
            result = AcceptanceTestResult(
                test_id=test.test_id,
                wave_id=None,
                status=status,
                error_message=None if status == 'pass' else "Failed",
                execution_duration_ms=100
            )
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = result
            mock_results.append(mock_result)

        mock_async_db.execute.side_effect = [mock_test_result] + mock_results

        gate = AcceptanceTestGate(mock_async_db)
        result = await gate.check_gate(masterplan_id)

        assert result['gate_passed'] is True
        assert result['must_pass_rate'] == 1.0
        assert result['should_pass_rate'] == 0.95
        assert result['gate_status'] == 'PASS'

    @pytest.mark.asyncio
    async def test_gate_fails_99_must(self, mock_async_db, sample_must_tests, sample_should_tests):
        """Test gate fails with 99% must (not 100%)"""
        masterplan_id = sample_must_tests[0].masterplan_id

        # Add more must tests to get 99% (99 pass, 1 fail)
        must_tests = sample_must_tests.copy()
        for i in range(98):
            must_tests.append(AcceptanceTest(
                test_id=uuid4(),
                masterplan_id=masterplan_id,
                requirement_text=f"Must requirement {i}",
                requirement_priority="must",
                test_code="",
                test_language="pytest"
            ))

        all_tests = must_tests + sample_should_tests

        # Mock test query
        mock_test_result = AsyncMock()
        mock_test_result.scalars.return_value.all.return_value = all_tests

        # Mock results (99 must pass, 1 must fail, 2 should pass)
        mock_results = []
        for idx, test in enumerate(all_tests):
            # First 99 must pass, 1 must fails, all should pass
            status = 'fail' if idx == 99 else 'pass'
            result = AcceptanceTestResult(
                test_id=test.test_id,
                wave_id=None,
                status=status,
                error_message=None if status == 'pass' else "Failed",
                execution_duration_ms=100
            )
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = result
            mock_results.append(mock_result)

        mock_async_db.execute.side_effect = [mock_test_result] + mock_results

        gate = AcceptanceTestGate(mock_async_db)
        result = await gate.check_gate(masterplan_id)

        assert result['gate_passed'] is False
        assert result['must_pass_rate'] == 0.99
        assert result['can_release'] is False  # Can't release with <100% must
        assert result['gate_status'] == 'FAIL'

    @pytest.mark.asyncio
    async def test_gate_fails_94_should(self, mock_async_db, sample_must_tests):
        """Test gate fails with 94% should (below 95%)"""
        masterplan_id = sample_must_tests[0].masterplan_id

        # Create 100 should tests (94 pass, 6 fail = 94%)
        should_tests = []
        for i in range(100):
            should_tests.append(AcceptanceTest(
                test_id=uuid4(),
                masterplan_id=masterplan_id,
                requirement_text=f"Should requirement {i}",
                requirement_priority="should",
                test_code="",
                test_language="pytest"
            ))

        all_tests = sample_must_tests + should_tests

        # Mock test query
        mock_test_result = AsyncMock()
        mock_test_result.scalars.return_value.all.return_value = all_tests

        # Mock results (2 must pass, 94 should pass, 6 should fail)
        mock_results = []
        for idx, test in enumerate(all_tests):
            # First 2 must pass, next 94 should pass, last 6 should fail
            status = 'pass' if idx < 96 else 'fail'
            result = AcceptanceTestResult(
                test_id=test.test_id,
                wave_id=None,
                status=status,
                error_message=None if status == 'pass' else "Failed",
                execution_duration_ms=100
            )
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = result
            mock_results.append(mock_result)

        mock_async_db.execute.side_effect = [mock_test_result] + mock_results

        gate = AcceptanceTestGate(mock_async_db)
        result = await gate.check_gate(masterplan_id)

        assert result['gate_passed'] is False
        assert result['must_pass_rate'] == 1.0
        assert result['should_pass_rate'] == 0.94
        assert result['can_release'] is True  # Can release (100% must) but gate failed
        assert result['gate_status'] == 'FAIL'

    @pytest.mark.asyncio
    async def test_gate_no_tests(self, mock_async_db):
        """Test gate fails when no tests exist"""
        masterplan_id = uuid4()

        # Mock empty test query
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_async_db.execute.return_value = mock_result

        gate = AcceptanceTestGate(mock_async_db)
        result = await gate.check_gate(masterplan_id)

        assert result['gate_passed'] is False
        assert result['must_pass_rate'] == 0.0
        assert result['should_pass_rate'] == 0.0
        assert result['can_release'] is False
        assert result['gate_status'] == 'FAIL'
        assert 'No acceptance tests found' in result['failed_requirements']

    # ========================================
    # Failed Requirements Tracking Tests
    # ========================================

    @pytest.mark.asyncio
    async def test_failed_requirements_tracked(self, mock_async_db, sample_must_tests, sample_should_tests):
        """Test failed requirements are tracked correctly"""
        masterplan_id = sample_must_tests[0].masterplan_id
        all_tests = sample_must_tests + sample_should_tests

        # Mock test query
        mock_test_result = AsyncMock()
        mock_test_result.scalars.return_value.all.return_value = all_tests

        # Mock results (1 must fails, 1 should fails)
        mock_results = []
        for idx, test in enumerate(all_tests):
            status = 'pass' if idx in [0, 2] else 'fail'
            result = AcceptanceTestResult(
                test_id=test.test_id,
                wave_id=None,
                status=status,
                error_message=f"Error {idx}" if status == 'fail' else None,
                execution_duration_ms=100
            )
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = result
            mock_results.append(mock_result)

        mock_async_db.execute.side_effect = [mock_test_result] + mock_results

        gate = AcceptanceTestGate(mock_async_db)
        result = await gate.check_gate(masterplan_id)

        assert len(result['failed_requirements']) == 2

        # Check must failure tracked
        must_failure = [r for r in result['failed_requirements'] if r['priority'] == 'must'][0]
        assert 'ACID' in must_failure['requirement']
        assert must_failure['status'] == 'fail'
        assert 'Error' in must_failure['error']

        # Check should failure tracked
        should_failure = [r for r in result['failed_requirements'] if r['priority'] == 'should'][0]
        assert 'fast' in should_failure['requirement']

    # ========================================
    # Block Progression Tests
    # ========================================

    @pytest.mark.asyncio
    async def test_block_progression_gate_passed(self, mock_async_db, sample_must_tests, sample_should_tests):
        """Test progression allowed when gate passes"""
        masterplan_id = sample_must_tests[0].masterplan_id
        wave_id = uuid4()
        all_tests = sample_must_tests + sample_should_tests

        # Mock all pass
        mock_test_result = AsyncMock()
        mock_test_result.scalars.return_value.all.return_value = all_tests

        mock_results = []
        for test in all_tests:
            result = AcceptanceTestResult(
                test_id=test.test_id,
                wave_id=wave_id,
                status='pass',
                error_message=None,
                execution_duration_ms=100
            )
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = result
            mock_results.append(mock_result)

        mock_async_db.execute.side_effect = [mock_test_result] + mock_results

        gate = AcceptanceTestGate(mock_async_db)
        can_proceed = await gate.block_progression_if_gate_fails(masterplan_id, wave_id)

        assert can_proceed is True

    @pytest.mark.asyncio
    async def test_block_progression_gate_failed(self, mock_async_db, sample_must_tests):
        """Test progression blocked when gate fails"""
        masterplan_id = sample_must_tests[0].masterplan_id
        wave_id = uuid4()

        # Mock 1 must fail
        mock_test_result = AsyncMock()
        mock_test_result.scalars.return_value.all.return_value = sample_must_tests

        mock_results = []
        for idx, test in enumerate(sample_must_tests):
            result = AcceptanceTestResult(
                test_id=test.test_id,
                wave_id=wave_id,
                status='pass' if idx == 0 else 'fail',
                error_message=None if idx == 0 else "Failed",
                execution_duration_ms=100
            )
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = result
            mock_results.append(mock_result)

        mock_async_db.execute.side_effect = [mock_test_result] + mock_results

        gate = AcceptanceTestGate(mock_async_db)
        can_proceed = await gate.block_progression_if_gate_fails(masterplan_id, wave_id)

        assert can_proceed is False

    # ========================================
    # Report Generation Tests
    # ========================================

    @pytest.mark.asyncio
    async def test_get_gate_report_format(self, mock_async_db, sample_must_tests, sample_should_tests):
        """Test gate report contains expected sections"""
        masterplan_id = sample_must_tests[0].masterplan_id
        all_tests = sample_must_tests + sample_should_tests

        # Mock all pass
        mock_test_result = AsyncMock()
        mock_test_result.scalars.return_value.all.return_value = all_tests

        mock_results = []
        for test in all_tests:
            result = AcceptanceTestResult(
                test_id=test.test_id,
                wave_id=None,
                status='pass',
                error_message=None,
                execution_duration_ms=100
            )
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = result
            mock_results.append(mock_result)

        mock_async_db.execute.side_effect = [mock_test_result] + mock_results

        gate = AcceptanceTestGate(mock_async_db)
        report = await gate.get_gate_report(masterplan_id)

        assert "GATE S REPORT" in report
        assert "MUST Requirements" in report
        assert "SHOULD Requirements" in report
        assert "GATE DECISION" in report
        assert "Status: PASS" in report
        assert "Can Release: YES" in report

    # ========================================
    # Requirements by Status Tests
    # ========================================

    @pytest.mark.asyncio
    async def test_get_requirements_by_status_pass(self, mock_async_db, sample_must_tests):
        """Test filtering requirements by pass status"""
        masterplan_id = sample_must_tests[0].masterplan_id

        # Mock test query
        mock_test_result = AsyncMock()
        mock_test_result.scalars.return_value.all.return_value = sample_must_tests

        # Mock results (1 pass, 1 fail)
        mock_results = []
        for idx, test in enumerate(sample_must_tests):
            result = AcceptanceTestResult(
                test_id=test.test_id,
                wave_id=None,
                status='pass' if idx == 0 else 'fail',
                error_message=None if idx == 0 else "Failed",
                execution_duration_ms=100
            )
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = result
            mock_results.append(mock_result)

        mock_async_db.execute.side_effect = [mock_test_result] + mock_results

        gate = AcceptanceTestGate(mock_async_db)
        passed_reqs = await gate.get_requirements_by_status(masterplan_id, 'pass')

        assert len(passed_reqs) == 1
        assert 'JWT' in passed_reqs[0]['requirement_text']
