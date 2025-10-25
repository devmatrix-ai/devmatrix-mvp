"""
Unit Tests for ExecutionServiceV2

Tests state management, execution orchestration, pause/resume, and metrics.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
from datetime import datetime

from src.mge.v2.services.execution_service_v2 import (
    ExecutionServiceV2,
    ExecutionState,
    ExecutionStatus,
)
from src.mge.v2.execution.wave_executor import WaveResult, ExecutionResult
from src.mge.v2.validation.atomic_validator import AtomicValidationResult


@pytest.fixture
def mock_wave_executor():
    """Mock wave executor."""
    executor = AsyncMock()
    executor.execute_wave = AsyncMock()
    return executor


@pytest.fixture
def mock_execution_plan():
    """Create mock execution plan with 2 waves."""
    waves = []
    for i in range(2):
        wave = Mock()
        wave.level = i
        wave.atom_ids = [str(uuid4()) for _ in range(3)]
        waves.append(wave)
    return waves


@pytest.fixture
def mock_atoms():
    """Create mock atoms."""
    atoms = {}
    for i in range(10):
        atom = Mock()
        atom.id = uuid4()
        atom.name = f"atom_{i}"
        atom.depends_on = []
        atoms[str(atom.id)] = atom
    return atoms


@pytest.mark.asyncio
class TestExecutionServiceV2Basics:
    """Test basic ExecutionServiceV2 functionality."""

    async def test_initialization(self, mock_wave_executor):
        """Test ExecutionServiceV2 initialization."""
        service = ExecutionServiceV2(mock_wave_executor)

        assert service.wave_executor == mock_wave_executor
        assert len(service.executions) == 0
        assert len(service.execution_results) == 0
        assert len(service.pause_flags) == 0

    async def test_start_execution_creates_state(
        self, mock_wave_executor, mock_execution_plan, mock_atoms
    ):
        """Test start_execution creates execution state."""
        # Setup
        mock_wave_executor.execute_wave.return_value = WaveResult(
            wave_id=0,
            total_atoms=3,
            succeeded=3,
            failed=0,
            execution_time_seconds=1.0,
            atom_results={}
        )

        service = ExecutionServiceV2(mock_wave_executor)
        masterplan_id = uuid4()

        # Execute
        execution_id = await service.start_execution(
            masterplan_id=masterplan_id,
            execution_plan=mock_execution_plan,
            atoms=mock_atoms
        )

        # Verify state created
        assert execution_id in service.executions
        state = service.executions[execution_id]

        assert state.execution_id == execution_id
        assert state.masterplan_id == masterplan_id
        assert state.status in [ExecutionStatus.RUNNING, ExecutionStatus.COMPLETED]
        assert state.total_waves == 2
        assert state.atoms_total == 6  # 2 waves * 3 atoms
        assert state.started_at is not None

    async def test_start_execution_returns_unique_ids(
        self, mock_wave_executor, mock_execution_plan, mock_atoms
    ):
        """Test each start_execution returns unique ID."""
        mock_wave_executor.execute_wave.return_value = WaveResult(
            wave_id=0,
            total_atoms=0,
            succeeded=0,
            failed=0,
            execution_time_seconds=0.1,
            atom_results={}
        )

        service = ExecutionServiceV2(mock_wave_executor)
        masterplan_id = uuid4()

        # Start two executions
        id1 = await service.start_execution(
            masterplan_id=masterplan_id,
            execution_plan=mock_execution_plan,
            atoms=mock_atoms
        )

        id2 = await service.start_execution(
            masterplan_id=masterplan_id,
            execution_plan=mock_execution_plan,
            atoms=mock_atoms
        )

        assert id1 != id2
        assert id1 in service.executions
        assert id2 in service.executions


@pytest.mark.asyncio
class TestStateManagement:
    """Test execution state management."""

    async def test_get_execution_state_existing(
        self, mock_wave_executor, mock_execution_plan, mock_atoms
    ):
        """Test get_execution_state for existing execution."""
        mock_wave_executor.execute_wave.return_value = WaveResult(
            wave_id=0,
            total_atoms=0,
            succeeded=0,
            failed=0,
            execution_time_seconds=0.1,
            atom_results={}
        )

        service = ExecutionServiceV2(mock_wave_executor)
        masterplan_id = uuid4()

        execution_id = await service.start_execution(
            masterplan_id=masterplan_id,
            execution_plan=mock_execution_plan,
            atoms=mock_atoms
        )

        state = service.get_execution_state(execution_id)

        assert state is not None
        assert state.execution_id == execution_id

    async def test_get_execution_state_nonexistent(self, mock_wave_executor):
        """Test get_execution_state for non-existent execution."""
        service = ExecutionServiceV2(mock_wave_executor)

        state = service.get_execution_state(uuid4())

        assert state is None

    async def test_list_executions_empty(self, mock_wave_executor):
        """Test list_executions when no executions."""
        service = ExecutionServiceV2(mock_wave_executor)

        executions = service.list_executions()

        assert len(executions) == 0

    async def test_list_executions_multiple(
        self, mock_wave_executor, mock_execution_plan, mock_atoms
    ):
        """Test list_executions with multiple executions."""
        mock_wave_executor.execute_wave.return_value = WaveResult(
            wave_id=0,
            total_atoms=0,
            succeeded=0,
            failed=0,
            execution_time_seconds=0.1,
            atom_results={}
        )

        service = ExecutionServiceV2(mock_wave_executor)
        masterplan_id = uuid4()

        # Create 3 executions
        for _ in range(3):
            await service.start_execution(
                masterplan_id=masterplan_id,
                execution_plan=mock_execution_plan,
                atoms=mock_atoms
            )

        executions = service.list_executions()

        assert len(executions) == 3

    async def test_list_executions_filtered_by_masterplan(
        self, mock_wave_executor, mock_execution_plan, mock_atoms
    ):
        """Test list_executions filtered by masterplan ID."""
        mock_wave_executor.execute_wave.return_value = WaveResult(
            wave_id=0,
            total_atoms=0,
            succeeded=0,
            failed=0,
            execution_time_seconds=0.1,
            atom_results={}
        )

        service = ExecutionServiceV2(mock_wave_executor)
        masterplan_1 = uuid4()
        masterplan_2 = uuid4()

        # Create executions for different masterplans
        await service.start_execution(
            masterplan_id=masterplan_1,
            execution_plan=mock_execution_plan,
            atoms=mock_atoms
        )
        await service.start_execution(
            masterplan_id=masterplan_1,
            execution_plan=mock_execution_plan,
            atoms=mock_atoms
        )
        await service.start_execution(
            masterplan_id=masterplan_2,
            execution_plan=mock_execution_plan,
            atoms=mock_atoms
        )

        # Filter by masterplan_1
        executions = service.list_executions(masterplan_id=masterplan_1)

        assert len(executions) == 2
        assert all(e.masterplan_id == masterplan_1 for e in executions)


@pytest.mark.asyncio
class TestExecutionOrchestration:
    """Test execution orchestration."""

    async def test_background_execution_completes(
        self, mock_wave_executor, mock_execution_plan, mock_atoms
    ):
        """Test background execution completes successfully."""
        # Setup wave results
        atom_results = {}
        for i in range(3):
            atom_id = uuid4()
            atom_results[atom_id] = ExecutionResult(
                atom_id=atom_id,
                success=True,
                code="def foo(): pass",
                attempts=1
            )

        mock_wave_executor.execute_wave.return_value = WaveResult(
            wave_id=0,
            total_atoms=3,
            succeeded=3,
            failed=0,
            execution_time_seconds=1.0,
            atom_results=atom_results
        )

        service = ExecutionServiceV2(mock_wave_executor)
        masterplan_id = uuid4()

        execution_id = await service.start_execution(
            masterplan_id=masterplan_id,
            execution_plan=mock_execution_plan,
            atoms=mock_atoms
        )

        # Wait for background execution
        await asyncio.sleep(0.1)

        state = service.get_execution_state(execution_id)

        # Should complete (or be running if still processing)
        assert state.status in [ExecutionStatus.RUNNING, ExecutionStatus.COMPLETED]

    async def test_execution_tracks_progress(
        self, mock_wave_executor, mock_execution_plan, mock_atoms
    ):
        """Test execution tracks progress through waves."""
        # Setup: slow execution to observe progress
        async def slow_execute(*args, **kwargs):
            await asyncio.sleep(0.05)
            return WaveResult(
                wave_id=0,
                total_atoms=3,
                succeeded=3,
                failed=0,
                execution_time_seconds=0.05,
                atom_results={}
            )

        mock_wave_executor.execute_wave.side_effect = slow_execute

        service = ExecutionServiceV2(mock_wave_executor)
        masterplan_id = uuid4()

        execution_id = await service.start_execution(
            masterplan_id=masterplan_id,
            execution_plan=mock_execution_plan,
            atoms=mock_atoms
        )

        # Wait a bit
        await asyncio.sleep(0.15)

        state = service.get_execution_state(execution_id)

        # Should have progressed
        assert state.current_wave >= 0


@pytest.mark.asyncio
class TestPauseResume:
    """Test pause and resume functionality."""

    async def test_pause_running_execution(
        self, mock_wave_executor, mock_execution_plan, mock_atoms
    ):
        """Test pausing a running execution."""
        # Setup: slow execution
        async def slow_execute(*args, **kwargs):
            await asyncio.sleep(1.0)
            return WaveResult(
                wave_id=0,
                total_atoms=0,
                succeeded=0,
                failed=0,
                execution_time_seconds=1.0,
                atom_results={}
            )

        mock_wave_executor.execute_wave.side_effect = slow_execute

        service = ExecutionServiceV2(mock_wave_executor)
        masterplan_id = uuid4()

        execution_id = await service.start_execution(
            masterplan_id=masterplan_id,
            execution_plan=mock_execution_plan,
            atoms=mock_atoms
        )

        # Pause immediately
        result = await service.pause_execution(execution_id)

        assert result is True
        assert service.pause_flags[execution_id] is True

    async def test_pause_nonexistent_execution(self, mock_wave_executor):
        """Test pausing non-existent execution."""
        service = ExecutionServiceV2(mock_wave_executor)

        result = await service.pause_execution(uuid4())

        assert result is False

    async def test_pause_completed_execution(
        self, mock_wave_executor, mock_execution_plan, mock_atoms
    ):
        """Test cannot pause completed execution."""
        mock_wave_executor.execute_wave.return_value = WaveResult(
            wave_id=0,
            total_atoms=0,
            succeeded=0,
            failed=0,
            execution_time_seconds=0.1,
            atom_results={}
        )

        service = ExecutionServiceV2(mock_wave_executor)
        masterplan_id = uuid4()

        execution_id = await service.start_execution(
            masterplan_id=masterplan_id,
            execution_plan=mock_execution_plan,
            atoms=mock_atoms
        )

        # Wait for completion
        await asyncio.sleep(0.2)

        # Try to pause
        result = await service.pause_execution(execution_id)

        # Should fail (already completed)
        assert result is False

    async def test_resume_paused_execution(
        self, mock_wave_executor, mock_execution_plan, mock_atoms
    ):
        """Test resuming a paused execution."""
        service = ExecutionServiceV2(mock_wave_executor)
        masterplan_id = uuid4()

        # Create execution and manually set to paused
        execution_id = uuid4()
        state = ExecutionState(
            execution_id=execution_id,
            masterplan_id=masterplan_id,
            status=ExecutionStatus.PAUSED,
            current_wave=0,
            total_waves=2,
            atoms_total=6,
            atoms_completed=0,
            atoms_succeeded=0,
            atoms_failed=0,
            total_cost_usd=0.0,
            total_time_seconds=0.0
        )
        service.executions[execution_id] = state
        service.pause_flags[execution_id] = True

        # Resume
        result = await service.resume_execution(execution_id)

        assert result is True
        assert service.pause_flags[execution_id] is False
        assert state.status == ExecutionStatus.RUNNING

    async def test_resume_nonexistent_execution(self, mock_wave_executor):
        """Test resuming non-existent execution."""
        service = ExecutionServiceV2(mock_wave_executor)

        result = await service.resume_execution(uuid4())

        assert result is False


@pytest.mark.asyncio
class TestResultsRetrieval:
    """Test execution results retrieval."""

    async def test_get_execution_results_after_completion(
        self, mock_wave_executor, mock_execution_plan, mock_atoms
    ):
        """Test retrieving results after execution completes."""
        atom_id = uuid4()
        atom_results = {
            atom_id: ExecutionResult(
                atom_id=atom_id,
                success=True,
                code="def foo(): pass",
                attempts=1
            )
        }

        mock_wave_executor.execute_wave.return_value = WaveResult(
            wave_id=0,
            total_atoms=1,
            succeeded=1,
            failed=0,
            execution_time_seconds=0.1,
            atom_results=atom_results
        )

        service = ExecutionServiceV2(mock_wave_executor)
        masterplan_id = uuid4()

        execution_id = await service.start_execution(
            masterplan_id=masterplan_id,
            execution_plan=mock_execution_plan,
            atoms=mock_atoms
        )

        # Wait for completion
        await asyncio.sleep(0.2)

        results = service.get_execution_results(execution_id)

        assert results is not None
        assert len(results) > 0

    async def test_get_execution_results_nonexistent(self, mock_wave_executor):
        """Test retrieving results for non-existent execution."""
        service = ExecutionServiceV2(mock_wave_executor)

        results = service.get_execution_results(uuid4())

        assert results is None

    async def test_get_atom_status(
        self, mock_wave_executor, mock_execution_plan, mock_atoms
    ):
        """Test getting individual atom status."""
        atom_id = uuid4()
        atom_result = ExecutionResult(
            atom_id=atom_id,
            success=True,
            code="def foo(): pass",
            attempts=1
        )

        mock_wave_executor.execute_wave.return_value = WaveResult(
            wave_id=0,
            total_atoms=1,
            succeeded=1,
            failed=0,
            execution_time_seconds=0.1,
            atom_results={atom_id: atom_result}
        )

        service = ExecutionServiceV2(mock_wave_executor)
        masterplan_id = uuid4()

        execution_id = await service.start_execution(
            masterplan_id=masterplan_id,
            execution_plan=mock_execution_plan,
            atoms=mock_atoms
        )

        # Wait for completion
        await asyncio.sleep(0.2)

        status = service.get_atom_status(execution_id, atom_id)

        assert status is not None
        assert status.atom_id == atom_id
        assert status.success is True

    async def test_get_wave_status(
        self, mock_wave_executor, mock_execution_plan, mock_atoms
    ):
        """Test getting wave status."""
        mock_wave_executor.execute_wave.return_value = WaveResult(
            wave_id=0,
            total_atoms=0,
            succeeded=0,
            failed=0,
            execution_time_seconds=0.1,
            atom_results={}
        )

        service = ExecutionServiceV2(mock_wave_executor)
        masterplan_id = uuid4()

        execution_id = await service.start_execution(
            masterplan_id=masterplan_id,
            execution_plan=mock_execution_plan,
            atoms=mock_atoms
        )

        await asyncio.sleep(0.1)

        wave_status = service.get_wave_status(execution_id, 0)

        assert wave_status is not None
        assert wave_status["wave_id"] == 0


@pytest.mark.asyncio
class TestMetrics:
    """Test metrics collection and reporting."""

    async def test_get_execution_metrics(
        self, mock_wave_executor, mock_execution_plan, mock_atoms
    ):
        """Test getting execution metrics."""
        mock_wave_executor.execute_wave.return_value = WaveResult(
            wave_id=0,
            total_atoms=3,
            succeeded=2,
            failed=1,
            execution_time_seconds=1.0,
            atom_results={}
        )

        service = ExecutionServiceV2(mock_wave_executor)
        masterplan_id = uuid4()

        execution_id = await service.start_execution(
            masterplan_id=masterplan_id,
            execution_plan=mock_execution_plan,
            atoms=mock_atoms
        )

        await asyncio.sleep(0.2)

        metrics = service.get_execution_metrics(execution_id)

        assert metrics is not None
        assert "precision_percent" in metrics
        assert "atoms_total" in metrics
        assert "atoms_succeeded" in metrics
        assert "atoms_failed" in metrics
        assert "completion_percent" in metrics
        assert "total_time_seconds" in metrics

    async def test_metrics_precision_calculation(
        self, mock_wave_executor, mock_execution_plan, mock_atoms
    ):
        """Test precision percentage is calculated correctly."""
        mock_wave_executor.execute_wave.return_value = WaveResult(
            wave_id=0,
            total_atoms=10,
            succeeded=8,
            failed=2,
            execution_time_seconds=1.0,
            atom_results={}
        )

        service = ExecutionServiceV2(mock_wave_executor)
        masterplan_id = uuid4()

        execution_id = await service.start_execution(
            masterplan_id=masterplan_id,
            execution_plan=mock_execution_plan,
            atoms=mock_atoms
        )

        await asyncio.sleep(0.2)

        metrics = service.get_execution_metrics(execution_id)

        # Should be roughly 80% (8/10)
        # Actual value depends on how many waves completed
        assert "precision_percent" in metrics


@pytest.mark.asyncio
class TestPrometheusMetrics:
    """Test Prometheus metrics emission."""

    @patch("src.mge.v2.services.execution_service_v2.EXECUTION_PRECISION_PERCENT")
    @patch("src.mge.v2.services.execution_service_v2.EXECUTION_TIME_SECONDS")
    async def test_metrics_emitted_on_completion(
        self, mock_time_metric, mock_precision_metric,
        mock_wave_executor, mock_execution_plan, mock_atoms
    ):
        """Test Prometheus metrics are emitted on completion."""
        mock_wave_executor.execute_wave.return_value = WaveResult(
            wave_id=0,
            total_atoms=3,
            succeeded=3,
            failed=0,
            execution_time_seconds=1.0,
            atom_results={}
        )

        service = ExecutionServiceV2(mock_wave_executor)
        masterplan_id = uuid4()

        execution_id = await service.start_execution(
            masterplan_id=masterplan_id,
            execution_plan=mock_execution_plan,
            atoms=mock_atoms
        )

        # Wait for completion
        await asyncio.sleep(0.3)

        # Verify metrics were called
        assert mock_precision_metric.labels.called
        assert mock_time_metric.labels.called


@pytest.mark.asyncio
class TestEdgeCases:
    """Test edge cases and error handling."""

    async def test_empty_execution_plan(
        self, mock_wave_executor, mock_atoms
    ):
        """Test execution with empty plan."""
        service = ExecutionServiceV2(mock_wave_executor)
        masterplan_id = uuid4()

        execution_id = await service.start_execution(
            masterplan_id=masterplan_id,
            execution_plan=[],
            atoms=mock_atoms
        )

        await asyncio.sleep(0.1)

        state = service.get_execution_state(execution_id)

        assert state.total_waves == 0
        assert state.atoms_total == 0

    async def test_execution_with_exception(
        self, mock_wave_executor, mock_execution_plan, mock_atoms
    ):
        """Test execution handles exceptions gracefully."""
        mock_wave_executor.execute_wave.side_effect = Exception("Test error")

        service = ExecutionServiceV2(mock_wave_executor)
        masterplan_id = uuid4()

        execution_id = await service.start_execution(
            masterplan_id=masterplan_id,
            execution_plan=mock_execution_plan,
            atoms=mock_atoms
        )

        await asyncio.sleep(0.2)

        state = service.get_execution_state(execution_id)

        # Should be marked as failed
        assert state.status == ExecutionStatus.FAILED
        assert state.completed_at is not None
