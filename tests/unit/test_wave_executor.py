"""
Unit Tests - WaveExecutor

Tests parallel execution of atoms within waves with dependency coordination.

Author: DevMatrix Team
Date: 2025-10-24
"""

import pytest
import uuid
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from src.execution.wave_executor import (
    WaveExecutor, AtomExecutionResult, WaveExecutionResult, AtomStatus
)
from src.models import AtomicUnit, DependencyGraph


@pytest.fixture
def mock_db():
    """Create mock database session"""
    db = Mock()
    db.query.return_value = db
    db.filter.return_value = db
    db.first.return_value = None
    db.all.return_value = []
    db.commit.return_value = None
    return db


@pytest.fixture
def mock_code_generator():
    """Create mock code generator"""
    async def generator(atom, retry_count):
        # Simulate code generation
        await asyncio.sleep(0.01)  # Simulate some work
        return f"# Generated code for {atom.description}"
    return generator


@pytest.fixture
def sample_atoms():
    """Create sample atoms for testing"""
    masterplan_id = uuid.uuid4()
    task_id = uuid.uuid4()

    atoms = []
    for i in range(10):
        atom = AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=masterplan_id,
            task_id=task_id,
            atom_number=i + 1,
            description=f"Test atom {i + 1}",
            code_to_generate=f"def test_{i}(): pass",
            file_path=f"src/test_{i}.py",
            language="python",
            complexity=1.5,
            status="pending",
            dependencies=[],
            context_completeness=0.95
        )
        atoms.append(atom)

    return atoms


@pytest.fixture
def wave_executor(mock_db):
    """Create WaveExecutor instance"""
    return WaveExecutor(db=mock_db, max_concurrent=100)


# ============================================================================
# Basic Execution Tests
# ============================================================================

@pytest.mark.asyncio
async def test_execute_single_atom(wave_executor, sample_atoms, mock_db):
    """Test single atom execution"""
    atom = sample_atoms[0]
    masterplan_id = atom.masterplan_id

    result = await wave_executor.execute_atom(atom, masterplan_id)

    assert result.atom_id == atom.atom_id
    assert result.status == AtomStatus.SUCCESS
    assert result.generated_code == atom.code_to_generate
    assert result.error_message is None
    assert result.execution_time_seconds > 0


@pytest.mark.asyncio
async def test_execute_atom_with_code_generator(mock_db, mock_code_generator, sample_atoms):
    """Test atom execution with custom code generator"""
    executor = WaveExecutor(db=mock_db, code_generator=mock_code_generator)
    atom = sample_atoms[0]

    result = await executor.execute_atom(atom, atom.masterplan_id)

    assert result.status == AtomStatus.SUCCESS
    assert "Generated code" in result.generated_code
    assert atom.description in result.generated_code


@pytest.mark.asyncio
async def test_execute_atom_timeout(mock_db, sample_atoms):
    """Test atom execution timeout handling"""
    async def slow_generator(atom, retry_count):
        await asyncio.sleep(10)  # Will timeout
        return "code"

    executor = WaveExecutor(db=mock_db, code_generator=slow_generator, timeout_seconds=0.1)
    atom = sample_atoms[0]

    result = await executor.execute_atom(atom, atom.masterplan_id)

    assert result.status == AtomStatus.FAILED
    assert "timeout" in result.error_message.lower()


@pytest.mark.asyncio
async def test_execute_atom_exception(mock_db, sample_atoms):
    """Test atom execution exception handling"""
    async def failing_generator(atom, retry_count):
        raise ValueError("Test error")

    executor = WaveExecutor(db=mock_db, code_generator=failing_generator)
    atom = sample_atoms[0]

    result = await executor.execute_atom(atom, atom.masterplan_id)

    assert result.status == AtomStatus.FAILED
    assert "Test error" in result.error_message


# ============================================================================
# Wave Execution Tests
# ============================================================================

@pytest.mark.asyncio
async def test_execute_wave_small(wave_executor, sample_atoms):
    """Test wave execution with small batch"""
    wave_atoms = sample_atoms[:5]  # 5 atoms
    masterplan_id = wave_atoms[0].masterplan_id

    result = await wave_executor.execute_wave(0, wave_atoms, masterplan_id)

    assert result.wave_number == 0
    assert result.total_atoms == 5
    assert result.successful == 5
    assert result.failed == 0
    assert result.skipped == 0
    assert len(result.atom_results) == 5
    assert result.execution_time_seconds > 0


@pytest.mark.asyncio
async def test_execute_wave_large_parallel(mock_db, mock_code_generator):
    """Test wave execution with 100+ atoms in parallel"""
    # Create 150 atoms
    masterplan_id = uuid.uuid4()
    task_id = uuid.uuid4()

    large_atom_batch = []
    for i in range(150):
        atom = AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=masterplan_id,
            task_id=task_id,
            atom_number=i + 1,
            description=f"Atom {i + 1}",
            code_to_generate=f"def func_{i}(): pass",
            file_path=f"src/module_{i}.py",
            language="python",
            complexity=1.0,
            status="pending",
            dependencies=[],
            context_completeness=0.95
        )
        large_atom_batch.append(atom)

    executor = WaveExecutor(db=mock_db, code_generator=mock_code_generator, max_concurrent=100)

    start_time = datetime.utcnow()
    result = await executor.execute_wave(0, large_atom_batch, masterplan_id)
    execution_time = (datetime.utcnow() - start_time).total_seconds()

    assert result.total_atoms == 150
    assert result.successful == 150
    assert result.failed == 0

    # With 100 concurrent, should complete much faster than sequential
    # Sequential would be ~1.5s (150 * 0.01s), parallel should be ~0.02s
    assert execution_time < 1.0, f"Parallel execution took {execution_time}s, expected < 1.0s"


@pytest.mark.asyncio
async def test_execute_wave_with_failures(mock_db, sample_atoms):
    """Test wave execution handles individual atom failures"""
    async def selective_generator(atom, retry_count):
        # Fail atoms 2 and 5
        if atom.atom_number in [2, 5]:
            raise ValueError(f"Failed atom {atom.atom_number}")
        await asyncio.sleep(0.01)
        return f"# Code for {atom.description}"

    executor = WaveExecutor(db=mock_db, code_generator=selective_generator)
    wave_atoms = sample_atoms[:10]

    result = await executor.execute_wave(0, wave_atoms, wave_atoms[0].masterplan_id)

    assert result.total_atoms == 10
    assert result.successful == 8
    assert result.failed == 2
    assert len(result.errors) == 2


# ============================================================================
# Dependency Coordination Tests
# ============================================================================

@pytest.mark.asyncio
async def test_dependency_checking_satisfied(wave_executor, sample_atoms):
    """Test dependency checking when dependencies are satisfied"""
    atom1 = sample_atoms[0]
    atom2 = sample_atoms[1]

    # Execute atom1 first
    result1 = await wave_executor.execute_atom(atom1, atom1.masterplan_id)
    assert result1.status == AtomStatus.SUCCESS

    # atom2 depends on atom1
    atom2.dependencies = [atom1.atom_id]

    # Execute atom2
    result2 = await wave_executor.execute_atom(atom2, atom2.masterplan_id)
    assert result2.status == AtomStatus.SUCCESS


@pytest.mark.asyncio
async def test_dependency_checking_not_satisfied(wave_executor, sample_atoms):
    """Test dependency checking when dependencies are not satisfied"""
    atom1 = sample_atoms[0]
    atom2 = sample_atoms[1]

    # atom2 depends on atom1, but atom1 not executed yet
    atom2.dependencies = [atom1.atom_id]

    # Execute atom2 (should be skipped)
    result = await wave_executor.execute_atom(atom2, atom2.masterplan_id)

    assert result.status == AtomStatus.SKIPPED
    assert "dependencies not satisfied" in result.error_message.lower()


@pytest.mark.asyncio
async def test_dependency_checking_failed_dependency(wave_executor, sample_atoms):
    """Test that failed dependencies prevent execution"""
    atom1 = sample_atoms[0]
    atom2 = sample_atoms[1]

    # Simulate atom1 failure
    wave_executor._execution_state[atom1.atom_id] = AtomExecutionResult(
        atom_id=atom1.atom_id,
        status=AtomStatus.FAILED,
        error_message="Test failure"
    )

    # atom2 depends on atom1
    atom2.dependencies = [atom1.atom_id]

    # Execute atom2 (should be skipped due to failed dependency)
    result = await wave_executor.execute_atom(atom2, atom2.masterplan_id)

    assert result.status == AtomStatus.SKIPPED


@pytest.mark.asyncio
async def test_coordinate_dependencies(wave_executor, sample_atoms, mock_db):
    """Test dependency coordination organizes atoms into waves"""
    masterplan_id = sample_atoms[0].masterplan_id

    # Create mock dependency graph with 3 waves
    dep_graph = DependencyGraph(
        graph_id=uuid.uuid4(),
        masterplan_id=masterplan_id,
        total_atoms=10,
        total_dependencies=8,
        has_cycles=False,
        max_parallelism=5,
        waves=[
            {"wave": 0, "atoms": [str(sample_atoms[0].atom_id), str(sample_atoms[1].atom_id)]},
            {"wave": 1, "atoms": [str(sample_atoms[2].atom_id), str(sample_atoms[3].atom_id)]},
            {"wave": 2, "atoms": [str(sample_atoms[4].atom_id)]}
        ],
        created_at=datetime.utcnow()
    )

    # Mock database queries
    mock_db.query.return_value = mock_db
    mock_db.filter.side_effect = [
        Mock(first=Mock(return_value=dep_graph)),  # DependencyGraph query
        Mock(all=Mock(return_value=sample_atoms))   # AtomicUnit query
    ]

    waves = wave_executor.coordinate_dependencies(masterplan_id)

    assert len(waves) == 3
    assert len(waves[0]) == 2  # Wave 0 has 2 atoms
    assert len(waves[1]) == 2  # Wave 1 has 2 atoms
    assert len(waves[2]) == 1  # Wave 2 has 1 atom


# ============================================================================
# Concurrency Management Tests
# ============================================================================

def test_manage_concurrency(wave_executor):
    """Test concurrency limit management"""
    assert wave_executor.max_concurrent == 100

    wave_executor.manage_concurrency(50)
    assert wave_executor.max_concurrent == 50

    wave_executor.manage_concurrency(200)
    assert wave_executor.max_concurrent == 200


@pytest.mark.asyncio
async def test_concurrency_limit_enforced(mock_db, sample_atoms):
    """Test that concurrency limit is enforced"""
    executor = WaveExecutor(db=mock_db, max_concurrent=5)

    # Track concurrent executions
    concurrent_count = 0
    max_concurrent = 0

    async def tracked_generator(atom, retry_count):
        nonlocal concurrent_count, max_concurrent
        concurrent_count += 1
        max_concurrent = max(max_concurrent, concurrent_count)
        await asyncio.sleep(0.05)  # Simulate work
        concurrent_count -= 1
        return "code"

    executor.code_generator = tracked_generator

    # Execute 10 atoms (should be limited to 5 concurrent)
    await executor.execute_wave(0, sample_atoms[:10], sample_atoms[0].masterplan_id)

    assert max_concurrent <= 5, f"Max concurrent was {max_concurrent}, expected <= 5"


# ============================================================================
# Progress Tracking Tests
# ============================================================================

@pytest.mark.asyncio
async def test_track_progress_empty(wave_executor):
    """Test progress tracking with no executions"""
    progress = wave_executor.track_progress()

    assert progress['total'] == 0
    assert progress['completed'] == 0
    assert progress['failed'] == 0
    assert progress['progress_percentage'] == 0.0


@pytest.mark.asyncio
async def test_track_progress_partial(wave_executor, sample_atoms):
    """Test progress tracking during execution"""
    # Execute 5 atoms
    for i in range(5):
        await wave_executor.execute_atom(sample_atoms[i], sample_atoms[i].masterplan_id)

    progress = wave_executor.track_progress()

    assert progress['total'] == 5
    assert progress['completed'] == 5
    assert progress['failed'] == 0
    assert progress['progress_percentage'] == 100.0


@pytest.mark.asyncio
async def test_track_progress_with_failures(mock_db, sample_atoms):
    """Test progress tracking with some failures"""
    async def selective_generator(atom, retry_count):
        if atom.atom_number % 2 == 0:
            raise ValueError("Even atom failure")
        return "code"

    executor = WaveExecutor(db=mock_db, code_generator=selective_generator)

    # Execute 10 atoms (5 should fail)
    for atom in sample_atoms[:10]:
        await executor.execute_atom(atom, atom.masterplan_id)

    progress = executor.track_progress()

    assert progress['total'] == 10
    assert progress['completed'] == 5
    assert progress['failed'] == 5
    assert progress['progress_percentage'] == 50.0


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.asyncio
async def test_handle_errors_empty(wave_executor):
    """Test error handling with no failures"""
    errors = wave_executor.handle_errors()
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_handle_errors_with_failures(mock_db, sample_atoms):
    """Test error handling retrieves failed atoms"""
    async def failing_generator(atom, retry_count):
        if atom.atom_number in [2, 4, 6]:
            raise ValueError(f"Failed {atom.atom_number}")
        return "code"

    executor = WaveExecutor(db=mock_db, code_generator=failing_generator)

    # Execute 10 atoms
    for atom in sample_atoms[:10]:
        await executor.execute_atom(atom, atom.masterplan_id)

    errors = executor.handle_errors()

    assert len(errors) == 3
    assert all(e.status == AtomStatus.FAILED for e in errors)
    assert all(e.error_message is not None for e in errors)


# ============================================================================
# State Management Tests
# ============================================================================

@pytest.mark.asyncio
async def test_reset_state(wave_executor, sample_atoms):
    """Test state reset clears execution history"""
    # Execute some atoms
    for atom in sample_atoms[:5]:
        await wave_executor.execute_atom(atom, atom.masterplan_id)

    assert len(wave_executor._execution_state) == 5

    # Reset state
    wave_executor.reset_state()

    assert len(wave_executor._execution_state) == 0
    progress = wave_executor.track_progress()
    assert progress['total'] == 0


@pytest.mark.asyncio
async def test_execution_state_persistence(wave_executor, sample_atoms):
    """Test execution state persists across calls"""
    atom = sample_atoms[0]

    result1 = await wave_executor.execute_atom(atom, atom.masterplan_id)

    assert atom.atom_id in wave_executor._execution_state
    stored_result = wave_executor._execution_state[atom.atom_id]
    assert stored_result.atom_id == result1.atom_id
    assert stored_result.status == result1.status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
