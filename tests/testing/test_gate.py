"""
Tests for AcceptanceTestGate

Tests Gate S enforcement (100% must + ≥95% should).
"""
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from src.testing.acceptance_gate import AcceptanceTestGate
from src.models import AcceptanceTest, AcceptanceTestResult


@pytest.mark.asyncio
class TestAcceptanceTestGate:
    """Test AcceptanceTestGate functionality"""

    @pytest.fixture
    def masterplan_id(self):
        """Generate test masterplan ID"""
        return uuid4()

    @pytest.fixture
    def wave_id(self):
        """Generate test wave ID"""
        return uuid4()

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock()

    @pytest.fixture
    async def gate(self, mock_db):
        """Create AcceptanceTestGate instance"""
        return AcceptanceTestGate(mock_db)

    @pytest.fixture
    def mock_must_tests(self, masterplan_id):
        """Create mock MUST tests"""
        return [
            AcceptanceTest(
                test_id=uuid4(),
                masterplan_id=masterplan_id,
                requirement_text="Must do A",
                requirement_priority='must',
                test_code='code',
                test_language='pytest'
            ),
            AcceptanceTest(
                test_id=uuid4(),
                masterplan_id=masterplan_id,
                requirement_text="Must do B",
                requirement_priority='must',
                test_code='code',
                test_language='pytest'
            )
        ]

    @pytest.fixture
    def mock_should_tests(self, masterplan_id):
        """Create mock SHOULD tests"""
        return [
            AcceptanceTest(
                test_id=uuid4(),
                masterplan_id=masterplan_id,
                requirement_text="Should do C",
                requirement_priority='should',
                test_code='code',
                test_language='pytest'
            )
        ]

    async def test_gate_pass_all_requirements_pass(self, gate, masterplan_id, mock_must_tests, mock_should_tests, mock_db):
        """Test gate passes when all requirements pass"""
        all_tests = mock_must_tests + mock_should_tests

        # Mock tests query
        tests_result = MagicMock()
        tests_result.scalars().all.return_value = all_tests

        # Mock results query - all passing
        passing_results = [
            AcceptanceTestResult(
                result_id=uuid4(),
                test_id=test.test_id,
                wave_id=uuid4(),
                status='pass',
                execution_duration_ms=100
            )
            for test in all_tests
        ]

        results_mock = [MagicMock() for _ in all_tests]
        for i, result in enumerate(passing_results):
            results_mock[i].scalar_one_or_none.return_value = result

        mock_db.execute.side_effect = [tests_result] + results_mock

        gate_result = await gate.check_gate(masterplan_id)

        assert gate_result['gate_passed'] is True
        assert gate_result['gate_status'] == 'PASS'
        assert gate_result['must_pass_rate'] == 1.0
        assert gate_result['should_pass_rate'] == 1.0

    async def test_gate_fail_must_requirement_fails(self, gate, masterplan_id, mock_must_tests, mock_should_tests, mock_db):
        """Test gate fails when MUST requirement fails"""
        all_tests = mock_must_tests + mock_should_tests

        # Mock tests query
        tests_result = MagicMock()
        tests_result.scalars().all.return_value = all_tests

        # Mock results - one MUST fails
        results = [
            AcceptanceTestResult(
                result_id=uuid4(),
                test_id=mock_must_tests[0].test_id,
                wave_id=uuid4(),
                status='fail',  # MUST fails
                execution_duration_ms=100,
                error_message="Test failed"
            ),
            AcceptanceTestResult(
                result_id=uuid4(),
                test_id=mock_must_tests[1].test_id,
                wave_id=uuid4(),
                status='pass',
                execution_duration_ms=100
            ),
            AcceptanceTestResult(
                result_id=uuid4(),
                test_id=mock_should_tests[0].test_id,
                wave_id=uuid4(),
                status='pass',
                execution_duration_ms=100
            )
        ]

        results_mock = [MagicMock() for _ in results]
        for i, result in enumerate(results):
            results_mock[i].scalar_one_or_none.return_value = result

        mock_db.execute.side_effect = [tests_result] + results_mock

        gate_result = await gate.check_gate(masterplan_id)

        assert gate_result['gate_passed'] is False
        assert gate_result['gate_status'] == 'FAIL'
        assert gate_result['must_pass_rate'] < 1.0
        assert gate_result['can_release'] is False

    async def test_gate_fail_should_below_threshold(self, gate, masterplan_id, mock_db):
        """Test gate fails when SHOULD pass rate < 95%"""
        # Create 20 SHOULD tests (95% = 19 must pass)
        must_tests = [
            AcceptanceTest(
                test_id=uuid4(),
                masterplan_id=masterplan_id,
                requirement_text=f"Must do {i}",
                requirement_priority='must',
                test_code='code',
                test_language='pytest'
            )
            for i in range(5)
        ]

        should_tests = [
            AcceptanceTest(
                test_id=uuid4(),
                masterplan_id=masterplan_id,
                requirement_text=f"Should do {i}",
                requirement_priority='should',
                test_code='code',
                test_language='pytest'
            )
            for i in range(20)
        ]

        all_tests = must_tests + should_tests

        # Mock tests query
        tests_result = MagicMock()
        tests_result.scalars().all.return_value = all_tests

        # All MUST pass, but only 18/20 SHOULD pass (90% < 95%)
        results = []

        # All MUST pass
        for test in must_tests:
            results.append(
                AcceptanceTestResult(
                    result_id=uuid4(),
                    test_id=test.test_id,
                    wave_id=uuid4(),
                    status='pass',
                    execution_duration_ms=100
                )
            )

        # 18/20 SHOULD pass
        for i, test in enumerate(should_tests):
            status = 'fail' if i >= 18 else 'pass'
            results.append(
                AcceptanceTestResult(
                    result_id=uuid4(),
                    test_id=test.test_id,
                    wave_id=uuid4(),
                    status=status,
                    execution_duration_ms=100
                )
            )

        results_mock = [MagicMock() for _ in results]
        for i, result in enumerate(results):
            results_mock[i].scalar_one_or_none.return_value = result

        mock_db.execute.side_effect = [tests_result] + results_mock

        gate_result = await gate.check_gate(masterplan_id)

        assert gate_result['gate_passed'] is False
        assert gate_result['gate_status'] == 'FAIL'
        assert gate_result['must_pass_rate'] == 1.0
        assert gate_result['should_pass_rate'] < 0.95
        assert gate_result['can_release'] is True  # Can release because 100% MUST

    async def test_thresholds_correct(self, gate):
        """Test gate thresholds are configured correctly"""
        assert gate.must_threshold == 1.0  # 100%
        assert gate.should_threshold == 0.95  # 95%

    async def test_failed_requirements_list(self, gate, masterplan_id, mock_must_tests, mock_db):
        """Test failed requirements are listed"""
        # Mock tests query
        tests_result = MagicMock()
        tests_result.scalars().all.return_value = mock_must_tests

        # Mock results - one fails
        results = [
            AcceptanceTestResult(
                result_id=uuid4(),
                test_id=mock_must_tests[0].test_id,
                wave_id=uuid4(),
                status='fail',
                execution_duration_ms=100,
                error_message="Test error"
            ),
            AcceptanceTestResult(
                result_id=uuid4(),
                test_id=mock_must_tests[1].test_id,
                wave_id=uuid4(),
                status='pass',
                execution_duration_ms=100
            )
        ]

        results_mock = [MagicMock() for _ in results]
        for i, result in enumerate(results):
            results_mock[i].scalar_one_or_none.return_value = result

        mock_db.execute.side_effect = [tests_result] + results_mock

        gate_result = await gate.check_gate(masterplan_id)

        assert len(gate_result['failed_requirements']) == 1
        assert gate_result['failed_requirements'][0]['priority'] == 'must'
        assert gate_result['failed_requirements'][0]['status'] == 'fail'

    async def test_no_tests_found(self, gate, masterplan_id, mock_db):
        """Test gate fails gracefully when no tests found"""
        # Mock empty tests query
        tests_result = MagicMock()
        tests_result.scalars().all.return_value = []
        mock_db.execute.return_value = tests_result

        gate_result = await gate.check_gate(masterplan_id)

        assert gate_result['gate_passed'] is False
        assert gate_result['gate_status'] == 'FAIL'
        assert 'No acceptance tests found' in str(gate_result['failed_requirements'])

    async def test_get_gate_report_format(self, gate, masterplan_id, mock_must_tests, mock_db):
        """Test gate report formatting"""
        # Mock successful gate
        tests_result = MagicMock()
        tests_result.scalars().all.return_value = mock_must_tests

        results = [
            AcceptanceTestResult(
                result_id=uuid4(),
                test_id=test.test_id,
                wave_id=uuid4(),
                status='pass',
                execution_duration_ms=100
            )
            for test in mock_must_tests
        ]

        results_mock = [MagicMock() for _ in results]
        for i, result in enumerate(results):
            results_mock[i].scalar_one_or_none.return_value = result

        mock_db.execute.side_effect = [tests_result] + results_mock + [tests_result] + results_mock

        report = await gate.get_gate_report(masterplan_id)

        assert "GATE S REPORT" in report
        assert "MUST Requirements" in report
        assert "SHOULD Requirements" in report
        assert "GATE DECISION" in report

    async def test_can_release_flag(self, gate, masterplan_id, mock_db):
        """Test can_release flag logic (100% MUST only)"""
        must_tests = [
            AcceptanceTest(
                test_id=uuid4(),
                masterplan_id=masterplan_id,
                requirement_text="Must do A",
                requirement_priority='must',
                test_code='code',
                test_language='pytest'
            )
        ]

        should_tests = [
            AcceptanceTest(
                test_id=uuid4(),
                masterplan_id=masterplan_id,
                requirement_text=f"Should do {i}",
                requirement_priority='should',
                test_code='code',
                test_language='pytest'
            )
            for i in range(20)
        ]

        all_tests = must_tests + should_tests

        tests_result = MagicMock()
        tests_result.scalars().all.return_value = all_tests

        # 100% MUST, but only 50% SHOULD
        results = []

        # MUST passes
        results.append(
            AcceptanceTestResult(
                result_id=uuid4(),
                test_id=must_tests[0].test_id,
                wave_id=uuid4(),
                status='pass',
                execution_duration_ms=100
            )
        )

        # 50% SHOULD pass
        for i, test in enumerate(should_tests):
            status = 'pass' if i < 10 else 'fail'
            results.append(
                AcceptanceTestResult(
                    result_id=uuid4(),
                    test_id=test.test_id,
                    wave_id=uuid4(),
                    status=status,
                    execution_duration_ms=100
                )
            )

        results_mock = [MagicMock() for _ in results]
        for i, result in enumerate(results):
            results_mock[i].scalar_one_or_none.return_value = result

        mock_db.execute.side_effect = [tests_result] + results_mock

        gate_result = await gate.check_gate(masterplan_id)

        # Gate fails (should < 95%)
        assert gate_result['gate_passed'] is False
        # But can release (must = 100%)
        assert gate_result['can_release'] is True
        assert gate_result['must_pass_rate'] == 1.0
        assert gate_result['should_pass_rate'] == 0.5
