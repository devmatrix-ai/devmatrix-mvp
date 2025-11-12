"""
Unit Tests for WaveExecutor

Tests wave execution, parallel processing, concurrency, and metrics.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from uuid import uuid4

from src.mge.v2.execution.wave_executor import WaveExecutor, ExecutionResult, WaveResult
from src.mge.v2.execution.retry_orchestrator import RetryResult
from src.mge.v2.validation.atomic_validator import AtomicValidationResult


@pytest.fixture
def mock_retry_orchestrator():
    """Mock retry orchestrator."""
    orchestrator = AsyncMock()
    orchestrator.execute_with_retry = AsyncMock()
    return orchestrator


@pytest.fixture
def mock_atoms():
    """Create mock atoms for testing."""
    atoms = {}
    for i in range(5):
        atom = Mock()
        atom.id = uuid4()
        atom.name = f"atom_{i}"
        atom.depends_on = []
        atom.code = None
        atoms[str(atom.id)] = atom
    return atoms


@pytest.fixture
def mock_wave():
    """Create mock execution wave."""
    wave = Mock()
    wave.level = 1
    wave.atom_ids = []
    return wave


@pytest.mark.asyncio
class TestWaveExecutorBasics:
    """Test basic WaveExecutor functionality."""

    async def test_initialization(self, mock_retry_orchestrator):
        """Test WaveExecutor initialization."""
        executor = WaveExecutor(mock_retry_orchestrator)

        assert executor.retry_orchestrator == mock_retry_orchestrator
        assert executor.max_concurrency == 100

    async def test_initialization_custom_concurrency(self, mock_retry_orchestrator):
        """Test WaveExecutor with custom concurrency limit."""
        executor = WaveExecutor(mock_retry_orchestrator, max_concurrency=50)

        assert executor.max_concurrency == 50

    async def test_execute_empty_wave(self, mock_retry_orchestrator, mock_atoms):
        """Test executing wave with no atoms."""
        executor = WaveExecutor(mock_retry_orchestrator)

        result = await executor.execute_wave(
            wave_id=1,
            wave_atoms=[],
            all_atoms=mock_atoms
        )

        assert result.wave_id == 1
        assert result.total_atoms == 0
        assert result.succeeded == 0
        assert result.failed == 0
        assert len(result.atom_results) == 0


@pytest.mark.asyncio
class TestSingleWaveExecution:
    """Test single wave execution."""

    async def test_execute_wave_all_success(self, mock_retry_orchestrator, mock_atoms):
        """Test wave execution where all atoms succeed."""
        # Setup: all retries succeed
        mock_retry_orchestrator.execute_with_retry.return_value = RetryResult(
            code="def foo(): pass",
            validation_result=AtomicValidationResult(passed=True, issues=[], metrics={}),
            attempts_used=1,
            success=True
        )

        executor = WaveExecutor(mock_retry_orchestrator)
        wave_atoms = list(mock_atoms.values())[:3]

        result = await executor.execute_wave(
            wave_id=1,
            wave_atoms=wave_atoms,
            all_atoms=mock_atoms
        )

        assert result.wave_id == 1
        assert result.total_atoms == 3
        assert result.succeeded == 3
        assert result.failed == 0
        assert len(result.atom_results) == 3
        assert mock_retry_orchestrator.execute_with_retry.call_count == 3

    async def test_execute_wave_partial_failure(self, mock_retry_orchestrator, mock_atoms):
        """Test wave execution with some failures."""
        # Setup: first succeeds, second fails, third succeeds
        mock_retry_orchestrator.execute_with_retry.side_effect = [
            RetryResult(
                code="def foo(): pass",
                validation_result=AtomicValidationResult(passed=True, issues=[], metrics={}),
                attempts_used=1,
                success=True
            ),
            RetryResult(
                code="def bar(): error",
                validation_result=AtomicValidationResult(passed=False, issues=[], metrics={}),
                attempts_used=4,
                success=False,
                error_message="Failed after 4 attempts"
            ),
            RetryResult(
                code="def baz(): pass",
                validation_result=AtomicValidationResult(passed=True, issues=[], metrics={}),
                attempts_used=1,
                success=True
            ),
        ]

        executor = WaveExecutor(mock_retry_orchestrator)
        wave_atoms = list(mock_atoms.values())[:3]

        result = await executor.execute_wave(
            wave_id=1,
            wave_atoms=wave_atoms,
            all_atoms=mock_atoms
        )

        assert result.total_atoms == 3
        assert result.succeeded == 2
        assert result.failed == 1

    async def test_execute_wave_all_failure(self, mock_retry_orchestrator, mock_atoms):
        """Test wave execution where all atoms fail."""
        mock_retry_orchestrator.execute_with_retry.return_value = RetryResult(
            code="",
            validation_result=AtomicValidationResult(passed=False, issues=[], metrics={}),
            attempts_used=4,
            success=False,
            error_message="Failed"
        )

        executor = WaveExecutor(mock_retry_orchestrator)
        wave_atoms = list(mock_atoms.values())[:3]

        result = await executor.execute_wave(
            wave_id=1,
            wave_atoms=wave_atoms,
            all_atoms=mock_atoms
        )

        assert result.succeeded == 0
        assert result.failed == 3


@pytest.mark.asyncio
class TestDependencyResolution:
    """Test dependency resolution."""

    async def test_dependencies_passed_to_retry(self, mock_retry_orchestrator):
        """Test dependencies are correctly passed to retry orchestrator."""
        # Create atoms with dependencies
        dep1 = Mock()
        dep1.id = uuid4()
        dep1.name = "dep1"
        dep1.code = "def dep1(): pass"

        dep2 = Mock()
        dep2.id = uuid4()
        dep2.name = "dep2"
        dep2.code = "def dep2(): pass"

        main_atom = Mock()
        main_atom.id = uuid4()
        main_atom.name = "main"
        main_atom.depends_on = [str(dep1.id), str(dep2.id)]

        all_atoms = {
            str(dep1.id): dep1,
            str(dep2.id): dep2,
            str(main_atom.id): main_atom
        }

        mock_retry_orchestrator.execute_with_retry.return_value = RetryResult(
            code="def main(): pass",
            validation_result=AtomicValidationResult(passed=True, issues=[], metrics={}),
            attempts_used=1,
            success=True
        )

        executor = WaveExecutor(mock_retry_orchestrator)

        result = await executor.execute_wave(
            wave_id=2,
            wave_atoms=[main_atom],
            all_atoms=all_atoms
        )

        # Verify dependencies were passed
        call_args = mock_retry_orchestrator.execute_with_retry.call_args
        dependencies = call_args[1]["dependencies"]

        assert len(dependencies) == 2
        assert dep1 in dependencies
        assert dep2 in dependencies

    async def test_missing_dependencies_ignored(self, mock_retry_orchestrator):
        """Test atoms with missing dependencies still execute."""
        atom = Mock()
        atom.id = uuid4()
        atom.name = "atom"
        atom.depends_on = [str(uuid4()), str(uuid4())]  # Non-existent deps

        all_atoms = {str(atom.id): atom}

        mock_retry_orchestrator.execute_with_retry.return_value = RetryResult(
            code="def atom(): pass",
            validation_result=AtomicValidationResult(passed=True, issues=[], metrics={}),
            attempts_used=1,
            success=True
        )

        executor = WaveExecutor(mock_retry_orchestrator)

        result = await executor.execute_wave(
            wave_id=1,
            wave_atoms=[atom],
            all_atoms=all_atoms
        )

        # Should execute with empty dependencies
        assert result.succeeded == 1
        call_args = mock_retry_orchestrator.execute_with_retry.call_args
        dependencies = call_args[1]["dependencies"]
        assert len(dependencies) == 0


@pytest.mark.asyncio
class TestConcurrencyControl:
    """Test concurrency limits."""

    async def test_concurrency_limit_respected(self, mock_retry_orchestrator, mock_atoms):
        """Test max concurrency is respected."""
        # Track concurrent executions
        concurrent_count = 0
        max_concurrent = 0
        lock = asyncio.Lock()

        async def mock_execute(*args, **kwargs):
            nonlocal concurrent_count, max_concurrent
            async with lock:
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)

            await asyncio.sleep(0.05)  # Simulate work (increased to ensure overlap)

            async with lock:
                concurrent_count -= 1

            return RetryResult(
                code="def foo(): pass",
                validation_result=AtomicValidationResult(passed=True, issues=[], metrics={}),
                attempts_used=1,
                success=True
            )

        mock_retry_orchestrator.execute_with_retry.side_effect = mock_execute

        # Create 9 atoms with max_concurrency=3 (use 9 to ensure multiple batches)
        # Using only 5 atoms from mock_atoms to avoid duplicates
        atoms_list = list(mock_atoms.values())[:5]

        # Add 4 more unique atoms
        for i in range(4):
            atom = Mock()
            atom.id = uuid4()
            atom.name = f"extra_atom_{i}"
            atom.depends_on = []
            atoms_list.append(atom)

        executor = WaveExecutor(mock_retry_orchestrator, max_concurrency=3)

        result = await executor.execute_wave(
            wave_id=1,
            wave_atoms=atoms_list,
            all_atoms=mock_atoms
        )

        # Verify concurrency was limited
        assert max_concurrent <= 3
        assert result.succeeded == 9

    async def test_high_concurrency_allowed(self, mock_retry_orchestrator, mock_atoms):
        """Test high concurrency (100) works."""
        mock_retry_orchestrator.execute_with_retry.return_value = RetryResult(
            code="def foo(): pass",
            validation_result=AtomicValidationResult(passed=True, issues=[], metrics={}),
            attempts_used=1,
            success=True
        )

        # Create 150 atoms
        many_atoms = {}
        atoms_list = []
        for i in range(150):
            atom = Mock()
            atom.id = uuid4()
            atom.name = f"atom_{i}"
            atom.depends_on = []
            many_atoms[str(atom.id)] = atom
            atoms_list.append(atom)

        executor = WaveExecutor(mock_retry_orchestrator, max_concurrency=100)

        result = await executor.execute_wave(
            wave_id=1,
            wave_atoms=atoms_list,
            all_atoms=many_atoms
        )

        assert result.succeeded == 150


@pytest.mark.asyncio
class TestExceptionHandling:
    """Test exception handling in wave execution."""

    async def test_exception_in_single_atom(self, mock_retry_orchestrator, mock_atoms):
        """Test exception in one atom doesn't crash wave."""
        # First atom raises exception, others succeed
        mock_retry_orchestrator.execute_with_retry.side_effect = [
            Exception("LLM error"),
            RetryResult(
                code="def foo(): pass",
                validation_result=AtomicValidationResult(passed=True, issues=[], metrics={}),
                attempts_used=1,
                success=True
            ),
            RetryResult(
                code="def bar(): pass",
                validation_result=AtomicValidationResult(passed=True, issues=[], metrics={}),
                attempts_used=1,
                success=True
            ),
        ]

        executor = WaveExecutor(mock_retry_orchestrator)
        wave_atoms = list(mock_atoms.values())[:3]

        result = await executor.execute_wave(
            wave_id=1,
            wave_atoms=wave_atoms,
            all_atoms=mock_atoms
        )

        # First failed, others succeeded
        assert result.total_atoms == 3
        assert result.succeeded == 2
        assert result.failed == 1

        # Check failed atom has error message
        failed_results = [r for r in result.atom_results.values() if not r.success]
        assert len(failed_results) == 1
        assert "Exception" in failed_results[0].error_message

    async def test_exception_in_gather(self, mock_retry_orchestrator, mock_atoms):
        """Test exception returned by gather (not raised)."""
        # Simulate gather returning an exception instead of raising it
        import asyncio
        from unittest.mock import patch

        # Make execute_with_retry return normally for first atom, but we'll inject exception in gather
        mock_retry_orchestrator.execute_with_retry.return_value = RetryResult(
            code="def foo(): pass",
            validation_result=AtomicValidationResult(passed=True, issues=[], metrics={}),
            attempts_used=1,
            success=True
        )

        executor = WaveExecutor(mock_retry_orchestrator)
        wave_atoms = list(mock_atoms.values())[:2]

        # Patch gather to return an exception in results
        original_gather = asyncio.gather

        async def mock_gather(*args, **kwargs):
            # Call original gather
            results = await original_gather(*args, **kwargs)
            # Replace first result with an exception
            return [Exception("Gather exception"), results[1]]

        with patch('asyncio.gather', side_effect=mock_gather):
            result = await executor.execute_wave(
                wave_id=1,
                wave_atoms=wave_atoms,
                all_atoms=mock_atoms
            )

        # First atom should be marked as failed due to gather exception
        assert result.total_atoms == 2
        assert result.failed >= 1

        # Check that gather exception was handled
        failed_results = [r for r in result.atom_results.values() if not r.success]
        assert len(failed_results) >= 1
        assert any("Gather exception" in r.error_message for r in failed_results)


@pytest.mark.asyncio
class TestMultiWaveExecution:
    """Test multi-wave execution plan."""

    async def test_execute_plan_single_wave(self, mock_retry_orchestrator, mock_atoms):
        """Test execute_plan with single wave."""
        mock_retry_orchestrator.execute_with_retry.return_value = RetryResult(
            code="def foo(): pass",
            validation_result=AtomicValidationResult(passed=True, issues=[], metrics={}),
            attempts_used=1,
            success=True
        )

        wave = Mock()
        wave.level = 1
        wave.atom_ids = list(mock_atoms.keys())[:3]

        executor = WaveExecutor(mock_retry_orchestrator)

        results = await executor.execute_plan(
            execution_plan=[wave],
            atoms=mock_atoms
        )

        assert len(results) == 3
        assert all(r.success for r in results.values())

    async def test_execute_plan_multiple_waves(self, mock_retry_orchestrator):
        """Test execute_plan with multiple sequential waves."""
        mock_retry_orchestrator.execute_with_retry.return_value = RetryResult(
            code="def foo(): pass",
            validation_result=AtomicValidationResult(passed=True, issues=[], metrics={}),
            attempts_used=1,
            success=True
        )

        # Create atoms for 3 waves
        all_atoms = {}
        waves = []

        for wave_num in range(3):
            wave = Mock()
            wave.level = wave_num
            wave.atom_ids = []

            for i in range(2):
                atom = Mock()
                atom.id = uuid4()
                atom.name = f"wave{wave_num}_atom{i}"
                atom.depends_on = []
                all_atoms[str(atom.id)] = atom
                wave.atom_ids.append(str(atom.id))

            waves.append(wave)

        executor = WaveExecutor(mock_retry_orchestrator)

        results = await executor.execute_plan(
            execution_plan=waves,
            atoms=all_atoms
        )

        # 3 waves * 2 atoms = 6 total
        assert len(results) == 6
        assert all(r.success for r in results.values())

    async def test_execute_plan_empty_plan(self, mock_retry_orchestrator, mock_atoms):
        """Test execute_plan with empty plan."""
        executor = WaveExecutor(mock_retry_orchestrator)

        results = await executor.execute_plan(
            execution_plan=[],
            atoms=mock_atoms
        )

        assert len(results) == 0


@pytest.mark.asyncio
class TestProgressTracking:
    """Test progress tracking and reporting."""

    async def test_wave_result_statistics(self, mock_retry_orchestrator, mock_atoms):
        """Test WaveResult contains correct statistics."""
        mock_retry_orchestrator.execute_with_retry.return_value = RetryResult(
            code="def foo(): pass",
            validation_result=AtomicValidationResult(passed=True, issues=[], metrics={}),
            attempts_used=1,
            success=True
        )

        executor = WaveExecutor(mock_retry_orchestrator)
        wave_atoms = list(mock_atoms.values())[:3]

        result = await executor.execute_wave(
            wave_id=5,
            wave_atoms=wave_atoms,
            all_atoms=mock_atoms
        )

        assert result.wave_id == 5
        assert result.total_atoms == 3
        assert result.succeeded == 3
        assert result.failed == 0
        assert result.execution_time_seconds > 0
        assert len(result.atom_results) == 3

    async def test_execution_time_tracked(self, mock_retry_orchestrator, mock_atoms):
        """Test execution time is tracked."""
        async def slow_execute(*args, **kwargs):
            await asyncio.sleep(0.1)
            return RetryResult(
                code="def foo(): pass",
                validation_result=AtomicValidationResult(passed=True, issues=[], metrics={}),
                attempts_used=1,
                success=True
            )

        mock_retry_orchestrator.execute_with_retry.side_effect = slow_execute

        executor = WaveExecutor(mock_retry_orchestrator)
        wave_atoms = list(mock_atoms.values())[:2]

        result = await executor.execute_wave(
            wave_id=1,
            wave_atoms=wave_atoms,
            all_atoms=mock_atoms
        )

        # Should be > 0.1s for 2 concurrent tasks with 0.1s each
        assert result.execution_time_seconds >= 0.1


@pytest.mark.asyncio
class TestMetricsEmission:
    """Test Prometheus metrics emission."""

    @patch("src.mge.v2.execution.wave_executor.WAVE_TIME_SECONDS")
    @patch("src.mge.v2.execution.wave_executor.WAVE_ATOM_THROUGHPUT")
    @patch("src.mge.v2.execution.wave_executor.ATOMS_SUCCEEDED_TOTAL")
    async def test_wave_metrics_emitted(
        self, mock_succeeded, mock_throughput, mock_time,
        mock_retry_orchestrator, mock_atoms
    ):
        """Test wave metrics are emitted."""
        mock_retry_orchestrator.execute_with_retry.return_value = RetryResult(
            code="def foo(): pass",
            validation_result=AtomicValidationResult(passed=True, issues=[], metrics={}),
            attempts_used=1,
            success=True
        )

        executor = WaveExecutor(mock_retry_orchestrator)
        wave_atoms = list(mock_atoms.values())[:3]

        result = await executor.execute_wave(
            wave_id=1,
            wave_atoms=wave_atoms,
            all_atoms=mock_atoms
        )

        # Verify metrics were called
        assert mock_time.labels.called
        assert mock_throughput.set.called
        assert mock_succeeded.labels.called

    @patch("src.mge.v2.execution.wave_executor.WAVE_COMPLETION_PERCENT")
    async def test_completion_percent_emitted(
        self, mock_completion,
        mock_retry_orchestrator, mock_atoms
    ):
        """Test wave completion percentage is emitted."""
        mock_retry_orchestrator.execute_with_retry.return_value = RetryResult(
            code="def foo(): pass",
            validation_result=AtomicValidationResult(passed=True, issues=[], metrics={}),
            attempts_used=1,
            success=True
        )

        wave = Mock()
        wave.level = 1
        wave.atom_ids = list(mock_atoms.keys())[:3]

        executor = WaveExecutor(mock_retry_orchestrator)

        results = await executor.execute_plan(
            execution_plan=[wave],
            atoms=mock_atoms
        )

        # Should emit completion percentage
        assert mock_completion.labels.called


@pytest.mark.asyncio
class TestMasterplanIntegration:
    """Test masterplan ID integration."""

    async def test_masterplan_id_passed_through(self, mock_retry_orchestrator, mock_atoms):
        """Test masterplan ID is passed to retry orchestrator."""
        mock_retry_orchestrator.execute_with_retry.return_value = RetryResult(
            code="def foo(): pass",
            validation_result=AtomicValidationResult(passed=True, issues=[], metrics={}),
            attempts_used=1,
            success=True
        )

        masterplan_id = uuid4()
        executor = WaveExecutor(mock_retry_orchestrator)
        wave_atoms = list(mock_atoms.values())[:1]

        result = await executor.execute_wave(
            wave_id=1,
            wave_atoms=wave_atoms,
            all_atoms=mock_atoms,
            masterplan_id=masterplan_id
        )

        # Verify masterplan_id was passed
        call_args = mock_retry_orchestrator.execute_with_retry.call_args
        assert call_args[1]["masterplan_id"] == masterplan_id

    async def test_masterplan_id_in_plan(self, mock_retry_orchestrator, mock_atoms):
        """Test masterplan ID propagates through execute_plan."""
        mock_retry_orchestrator.execute_with_retry.return_value = RetryResult(
            code="def foo(): pass",
            validation_result=AtomicValidationResult(passed=True, issues=[], metrics={}),
            attempts_used=1,
            success=True
        )

        wave = Mock()
        wave.level = 1
        wave.atom_ids = list(mock_atoms.keys())[:2]

        masterplan_id = uuid4()
        executor = WaveExecutor(mock_retry_orchestrator)

        results = await executor.execute_plan(
            execution_plan=[wave],
            atoms=mock_atoms,
            masterplan_id=masterplan_id
        )

        # All calls should have masterplan_id
        for call in mock_retry_orchestrator.execute_with_retry.call_args_list:
            assert call[1]["masterplan_id"] == masterplan_id


@pytest.mark.asyncio
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    async def test_wave_with_missing_atoms(self, mock_retry_orchestrator, mock_atoms):
        """Test wave with atom IDs that don't exist in all_atoms."""
        mock_retry_orchestrator.execute_with_retry.return_value = RetryResult(
            code="def foo(): pass",
            validation_result=AtomicValidationResult(passed=True, issues=[], metrics={}),
            attempts_used=1,
            success=True
        )

        wave = Mock()
        wave.level = 1
        wave.atom_ids = [str(uuid4()), str(uuid4())]  # Non-existent IDs

        executor = WaveExecutor(mock_retry_orchestrator)

        results = await executor.execute_plan(
            execution_plan=[wave],
            atoms=mock_atoms
        )

        # Should handle gracefully (no atoms found)
        assert len(results) == 0

    async def test_atom_without_depends_on_attribute(self, mock_retry_orchestrator):
        """Test atoms without depends_on attribute."""
        mock_retry_orchestrator.execute_with_retry.return_value = RetryResult(
            code="def foo(): pass",
            validation_result=AtomicValidationResult(passed=True, issues=[], metrics={}),
            attempts_used=1,
            success=True
        )

        # Create atom without depends_on
        atom = Mock(spec=['id', 'name'])  # Only id and name, no depends_on
        atom.id = uuid4()
        atom.name = "atom"

        all_atoms = {str(atom.id): atom}

        executor = WaveExecutor(mock_retry_orchestrator)

        result = await executor.execute_wave(
            wave_id=1,
            wave_atoms=[atom],
            all_atoms=all_atoms
        )

        # Should handle gracefully (no dependencies)
        assert result.succeeded == 1


@pytest.mark.asyncio
class TestAcceptanceTestsIntegration:
    """Test PHASE 8 acceptance tests integration."""

    async def test_execute_plan_with_acceptance_tests_success(self, mock_retry_orchestrator, mock_atoms):
        """Test execute_plan with acceptance tests enabled (passing gate)."""
        mock_retry_orchestrator.execute_with_retry.return_value = RetryResult(
            code="def foo(): pass",
            validation_result=AtomicValidationResult(passed=True, issues=[], metrics={}),
            attempts_used=1,
            success=True
        )

        # Mock async DB session
        mock_db_session = AsyncMock()

        # Create executor with async_db_session
        executor = WaveExecutor(mock_retry_orchestrator, async_db_session=mock_db_session)

        # Create execution plan
        wave = Mock()
        wave.level = 1
        wave.atom_ids = [list(mock_atoms.keys())[0]]

        masterplan_id = uuid4()

        # Mock the acceptance test runner
        with patch('src.testing.test_runner.AcceptanceTestRunner') as mock_runner_class:
            mock_runner = AsyncMock()
            mock_runner.run_tests_for_masterplan.return_value = {
                'total': 10,
                'passed': 10,
                'failed': 0,
                'overall_pass_rate': 1.0,
                'must_total': 5,
                'must_passed': 5,
                'must_pass_rate': 1.0,
                'should_total': 5,
                'should_passed': 5,
                'should_pass_rate': 1.0
            }
            mock_runner_class.return_value = mock_runner

            with patch('src.testing.gate_validator.GateValidator') as mock_gate_class:
                mock_gate = Mock()
                mock_gate.validate_gate_s.return_value = {
                    'passed': True,
                    'message': 'All gates passed'
                }
                mock_gate_class.return_value = mock_gate

                # Execute
                results = await executor.execute_plan(
                    execution_plan=[wave],
                    atoms=mock_atoms,
                    masterplan_id=masterplan_id
                )

        # Verify acceptance tests were run
        mock_runner.run_tests_for_masterplan.assert_called_once_with(masterplan_id)
        mock_gate.validate_gate_s.assert_called_once()

        # Verify execution completed
        assert len(results) > 0

    async def test_execute_plan_with_acceptance_tests_failure(self, mock_retry_orchestrator, mock_atoms):
        """Test execute_plan with acceptance tests enabled (failing gate)."""
        mock_retry_orchestrator.execute_with_retry.return_value = RetryResult(
            code="def foo(): pass",
            validation_result=AtomicValidationResult(passed=True, issues=[], metrics={}),
            attempts_used=1,
            success=True
        )

        # Mock async DB session
        mock_db_session = AsyncMock()

        # Create executor with async_db_session
        executor = WaveExecutor(mock_retry_orchestrator, async_db_session=mock_db_session)

        # Create execution plan
        wave = Mock()
        wave.level = 1
        wave.atom_ids = [list(mock_atoms.keys())[0]]

        masterplan_id = uuid4()

        # Mock the acceptance test runner
        with patch('src.testing.test_runner.AcceptanceTestRunner') as mock_runner_class:
            mock_runner = AsyncMock()
            mock_runner.run_tests_for_masterplan.return_value = {
                'total': 10,
                'passed': 8,
                'failed': 2,
                'overall_pass_rate': 0.8,
                'must_total': 5,
                'must_passed': 4,
                'must_pass_rate': 0.8,
                'should_total': 5,
                'should_passed': 4,
                'should_pass_rate': 0.8
            }
            mock_runner_class.return_value = mock_runner

            with patch('src.testing.gate_validator.GateValidator') as mock_gate_class:
                mock_gate = Mock()
                mock_gate.validate_gate_s.return_value = {
                    'passed': False,
                    'message': 'Gate failed',
                    'failures': ['MUST pass rate below 100%', 'SHOULD pass rate below 95%']
                }
                mock_gate_class.return_value = mock_gate

                # Execute
                results = await executor.execute_plan(
                    execution_plan=[wave],
                    atoms=mock_atoms,
                    masterplan_id=masterplan_id
                )

        # Verify acceptance tests were run
        mock_runner.run_tests_for_masterplan.assert_called_once_with(masterplan_id)
        mock_gate.validate_gate_s.assert_called_once()

        # Verify execution completed despite gate failure
        assert len(results) > 0

    async def test_execute_plan_with_acceptance_tests_exception(self, mock_retry_orchestrator, mock_atoms):
        """Test execute_plan when acceptance tests raise exception."""
        mock_retry_orchestrator.execute_with_retry.return_value = RetryResult(
            code="def foo(): pass",
            validation_result=AtomicValidationResult(passed=True, issues=[], metrics={}),
            attempts_used=1,
            success=True
        )

        # Mock async DB session
        mock_db_session = AsyncMock()

        # Create executor with async_db_session
        executor = WaveExecutor(mock_retry_orchestrator, async_db_session=mock_db_session)

        # Create execution plan
        wave = Mock()
        wave.level = 1
        wave.atom_ids = [list(mock_atoms.keys())[0]]

        masterplan_id = uuid4()

        # Mock the acceptance test runner to raise exception
        with patch('src.testing.test_runner.AcceptanceTestRunner') as mock_runner_class:
            mock_runner = AsyncMock()
            mock_runner.run_tests_for_masterplan.side_effect = Exception("Test runner failed")
            mock_runner_class.return_value = mock_runner

            # Execute - should continue despite exception
            results = await executor.execute_plan(
                execution_plan=[wave],
                atoms=mock_atoms,
                masterplan_id=masterplan_id
            )

        # Verify execution completed despite exception
        assert len(results) > 0
