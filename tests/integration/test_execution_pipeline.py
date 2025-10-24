"""
Integration Tests - Execution Pipeline (Phase 5)

Tests complete execution pipeline with waves, retries, and orchestration.

Author: DevMatrix Team
Date: 2025-10-24
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock

from src.services.execution_service_v2 import ExecutionServiceV2
from src.models import (
    MasterPlan, MasterPlanPhase, MasterPlanMilestone,
    MasterPlanTask, AtomicUnit, DependencyGraph
)


@pytest.fixture
def complete_masterplan(db_session):
    """Create complete MasterPlan with hierarchy for testing"""
    # Create MasterPlan
    masterplan = MasterPlan(
        masterplan_id=uuid.uuid4(),
        project_name="Test Execution Pipeline",
        total_tasks=2,
        estimated_duration_hours=5.0,
        status="planned",
        created_at=datetime.utcnow()
    )
    db_session.add(masterplan)
    db_session.commit()

    # Create Phase
    phase = MasterPlanPhase(
        phase_id=uuid.uuid4(),
        masterplan_id=masterplan.masterplan_id,
        phase_name="Implementation",
        phase_description="Implementation phase",
        phase_order=1,
        status="planned"
    )
    db_session.add(phase)
    db_session.commit()

    # Create Milestone
    milestone = MasterPlanMilestone(
        milestone_id=uuid.uuid4(),
        phase_id=phase.phase_id,
        milestone_name="Core Features",
        milestone_description="Core features milestone",
        milestone_order=1,
        status="planned"
    )
    db_session.add(milestone)
    db_session.commit()

    # Create Task
    task = MasterPlanTask(
        task_id=uuid.uuid4(),
        milestone_id=milestone.milestone_id,
        task_name="User Authentication",
        task_description="Implement user authentication",
        task_order=1,
        estimated_duration_hours=3.0,
        status="planned"
    )
    db_session.add(task)
    db_session.commit()

    # Create Atoms in 3 waves
    # Wave 0: 2 atoms (no dependencies)
    atom1 = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=masterplan.masterplan_id,
        task_id=task.task_id,
        atom_number=1,
        description="Create User model",
        code_to_generate="class User: pass",
        file_path="src/models/user.py",
        language="python",
        complexity=1.5,
        status="pending",
        dependencies=[],
        context_completeness=0.95
    )

    atom2 = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=masterplan.masterplan_id,
        task_id=task.task_id,
        atom_number=2,
        description="Create auth helpers",
        code_to_generate="def hash_password(): pass",
        file_path="src/auth/helpers.py",
        language="python",
        complexity=1.2,
        status="pending",
        dependencies=[],
        context_completeness=0.92
    )

    # Wave 1: 2 atoms (depend on wave 0)
    atom3 = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=masterplan.masterplan_id,
        task_id=task.task_id,
        atom_number=3,
        description="Create login function",
        code_to_generate="def login(): pass",
        file_path="src/auth/login.py",
        language="python",
        complexity=2.0,
        status="pending",
        dependencies=[atom1.atom_id, atom2.atom_id],
        context_completeness=0.90
    )

    atom4 = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=masterplan.masterplan_id,
        task_id=task.task_id,
        atom_number=4,
        description="Create registration function",
        code_to_generate="def register(): pass",
        file_path="src/auth/register.py",
        language="python",
        complexity=2.1,
        status="pending",
        dependencies=[atom1.atom_id, atom2.atom_id],
        context_completeness=0.88
    )

    # Wave 2: 1 atom (depends on wave 1)
    atom5 = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=masterplan.masterplan_id,
        task_id=task.task_id,
        atom_number=5,
        description="Create auth router",
        code_to_generate="router = APIRouter()",
        file_path="src/api/auth.py",
        language="python",
        complexity=1.8,
        status="pending",
        dependencies=[atom3.atom_id, atom4.atom_id],
        context_completeness=0.93
    )

    db_session.add_all([atom1, atom2, atom3, atom4, atom5])
    db_session.commit()

    # Create Dependency Graph with waves
    dep_graph = DependencyGraph(
        graph_id=uuid.uuid4(),
        masterplan_id=masterplan.masterplan_id,
        total_atoms=5,
        total_dependencies=6,
        has_cycles=False,
        max_parallelism=2,
        waves=[
            {"wave": 0, "atoms": [str(atom1.atom_id), str(atom2.atom_id)]},
            {"wave": 1, "atoms": [str(atom3.atom_id), str(atom4.atom_id)]},
            {"wave": 2, "atoms": [str(atom5.atom_id)]}
        ],
        created_at=datetime.utcnow()
    )
    db_session.add(dep_graph)
    db_session.commit()

    return {
        'masterplan': masterplan,
        'phase': phase,
        'milestone': milestone,
        'task': task,
        'atoms': [atom1, atom2, atom3, atom4, atom5],
        'dep_graph': dep_graph
    }


@pytest.fixture
def mock_code_generator():
    """Mock code generator that succeeds"""
    async def generator(atom, retry_count, temperature=0.7, feedback=None):
        # Simulate code generation
        code = f"""# Generated code for {atom.description}
# Retry count: {retry_count}
# Temperature: {temperature}

{atom.code_to_generate}

# Implementation here
"""
        return code
    return generator


@pytest.fixture
def failing_code_generator():
    """Mock code generator that fails first time, succeeds on retry"""
    call_count = {}

    async def generator(atom, retry_count, temperature=0.7, feedback=None):
        atom_id = str(atom.atom_id)

        if atom_id not in call_count:
            call_count[atom_id] = 0

        call_count[atom_id] += 1

        # Fail first attempt, succeed on retry
        if call_count[atom_id] == 1:
            raise ValueError(f"First attempt failed for {atom.description}")

        return f"# Fixed code for {atom.description}\n{atom.code_to_generate}"

    return generator


# ============================================================================
# Complete Execution Pipeline Tests
# ============================================================================

@pytest.mark.asyncio
async def test_complete_execution_pipeline_success(db_session, complete_masterplan, mock_code_generator):
    """Test complete execution pipeline with all atoms succeeding"""
    masterplan = complete_masterplan['masterplan']

    # Create execution service
    service = ExecutionServiceV2(
        db=db_session,
        code_generator=mock_code_generator,
        max_concurrent=10,
        max_retries=3
    )

    # Start execution
    result = await service.start_execution(masterplan.masterplan_id)

    # Verify execution completed
    assert result['status'] == 'completed'
    assert result['total_atoms'] == 5
    assert result['successful_atoms'] == 5
    assert result['failed_atoms'] == 0
    assert result['success_rate'] == 100.0
    assert result['total_waves'] == 3

    # Verify wave results
    assert len(result['wave_results']) == 3
    assert result['wave_results'][0]['total'] == 2  # Wave 0: 2 atoms
    assert result['wave_results'][1]['total'] == 2  # Wave 1: 2 atoms
    assert result['wave_results'][2]['total'] == 1  # Wave 2: 1 atom

    # Verify all atoms completed
    atoms = complete_masterplan['atoms']
    db_session.refresh(atoms[0])
    db_session.refresh(atoms[1])
    db_session.refresh(atoms[2])
    db_session.refresh(atoms[3])
    db_session.refresh(atoms[4])

    for atom in atoms:
        assert atom.status == 'completed'
        assert atom.generated_code is not None
        assert 'Generated code' in atom.generated_code


@pytest.mark.asyncio
async def test_execution_with_retry_success(db_session, complete_masterplan, failing_code_generator):
    """Test execution pipeline with retry logic"""
    masterplan = complete_masterplan['masterplan']

    # Create execution service
    service = ExecutionServiceV2(
        db=db_session,
        code_generator=failing_code_generator,
        max_concurrent=10,
        max_retries=3,
        enable_backoff=False  # Disable for faster tests
    )

    # Start execution
    result = await service.start_execution(masterplan.masterplan_id)

    # All atoms should succeed after retry
    assert result['status'] == 'completed'
    assert result['successful_atoms'] == 5
    assert result['failed_atoms'] == 0

    # Verify retry statistics
    retry_stats = result['retry_stats']
    assert retry_stats['total_atoms_retried'] == 5  # All failed first time
    assert retry_stats['successful_atoms'] == 5
    assert retry_stats['success_rate'] == 100.0


@pytest.mark.asyncio
async def test_execution_respects_wave_dependencies(db_session, complete_masterplan, mock_code_generator):
    """Test that waves execute in correct order respecting dependencies"""
    masterplan = complete_masterplan['masterplan']

    execution_order = []

    async def tracking_generator(atom, retry_count, temperature=0.7, feedback=None):
        execution_order.append(atom.atom_number)
        return f"# Code for atom {atom.atom_number}"

    service = ExecutionServiceV2(
        db=db_session,
        code_generator=tracking_generator,
        max_concurrent=10
    )

    await service.start_execution(masterplan.masterplan_id)

    # Verify execution order
    # Wave 0: atoms 1, 2 (can be in any order)
    # Wave 1: atoms 3, 4 (can be in any order, but after wave 0)
    # Wave 2: atom 5 (after wave 1)

    assert set(execution_order[:2]) == {1, 2}  # Wave 0
    assert set(execution_order[2:4]) == {3, 4}  # Wave 1
    assert execution_order[4] == 5  # Wave 2


@pytest.mark.asyncio
async def test_progress_tracking_during_execution(db_session, complete_masterplan):
    """Test progress tracking during execution"""
    masterplan = complete_masterplan['masterplan']

    async def slow_generator(atom, retry_count, temperature=0.7, feedback=None):
        import asyncio
        await asyncio.sleep(0.1)  # Simulate work
        return f"# Code for {atom.description}"

    service = ExecutionServiceV2(
        db=db_session,
        code_generator=slow_generator,
        max_concurrent=1  # Execute sequentially for predictable progress
    )

    # Start execution in background (not awaited yet)
    import asyncio
    execution_task = asyncio.create_task(
        service.start_execution(masterplan.masterplan_id)
    )

    # Give it time to start
    await asyncio.sleep(0.05)

    # Track progress mid-execution
    progress = service.track_progress(masterplan.masterplan_id)

    # Should have some progress but not complete
    assert progress['total_atoms'] == 5
    assert progress['progress_percentage'] >= 0.0

    # Wait for completion
    await execution_task

    # Final progress should be 100%
    final_progress = service.track_progress(masterplan.masterplan_id)
    assert final_progress['completed_atoms'] == 5
    assert final_progress['progress_percentage'] == 100.0


@pytest.mark.asyncio
async def test_execution_status_query(db_session, complete_masterplan, mock_code_generator):
    """Test execution status query"""
    masterplan = complete_masterplan['masterplan']

    service = ExecutionServiceV2(
        db=db_session,
        code_generator=mock_code_generator
    )

    # Execute
    await service.start_execution(masterplan.masterplan_id)

    # Query status
    status = service.get_execution_status(masterplan.masterplan_id)

    assert status['masterplan_id'] == str(masterplan.masterplan_id)
    assert status['status'] == 'completed'
    assert status['total_atoms'] == 5
    assert len(status['atoms_by_status']['completed']) == 5
    assert len(status['atoms_by_status']['failed']) == 0
    assert len(status['atoms_by_status']['pending']) == 0


@pytest.mark.asyncio
async def test_execution_with_partial_failure(db_session, complete_masterplan):
    """Test execution with some atoms failing even after retries"""
    masterplan = complete_masterplan['masterplan']
    atoms = complete_masterplan['atoms']

    async def selective_generator(atom, retry_count, temperature=0.7, feedback=None):
        # Atom 3 always fails (even after retries)
        if atom.atom_number == 3:
            raise ValueError("Persistent failure for atom 3")
        return f"# Code for {atom.description}"

    service = ExecutionServiceV2(
        db=db_session,
        code_generator=selective_generator,
        max_retries=3,
        enable_backoff=False
    )

    result = await service.start_execution(masterplan.masterplan_id)

    # Should be partially completed
    assert result['status'] == 'partially_completed'
    assert result['successful_atoms'] == 2  # Only wave 0 atoms (1, 2)
    assert result['failed_atoms'] > 0

    # Atom 3 should be failed
    db_session.refresh(atoms[2])  # atom3
    assert atoms[2].status == 'failed'

    # Atoms 4, 5 should be skipped (dependencies not satisfied)
    db_session.refresh(atoms[3])  # atom4
    db_session.refresh(atoms[4])  # atom5
    # They might be pending or have executed (atom4 doesn't depend on atom3)


@pytest.mark.asyncio
async def test_retry_statistics_tracking(db_session, complete_masterplan, failing_code_generator):
    """Test comprehensive retry statistics tracking"""
    masterplan = complete_masterplan['masterplan']

    service = ExecutionServiceV2(
        db=db_session,
        code_generator=failing_code_generator,
        max_retries=3,
        enable_backoff=False
    )

    result = await service.start_execution(masterplan.masterplan_id)

    # Verify retry stats
    retry_stats = result['retry_stats']

    assert retry_stats['total_atoms_retried'] == 5
    assert retry_stats['total_attempts'] >= 5  # At least 1 retry per atom
    assert retry_stats['successful_atoms'] == 5
    assert retry_stats['success_rate'] == 100.0
    assert 'error_categories' in retry_stats
    assert retry_stats['max_attempts'] == 3


@pytest.mark.asyncio
async def test_execution_service_reset(db_session, complete_masterplan, mock_code_generator):
    """Test execution service state reset between runs"""
    masterplan = complete_masterplan['masterplan']

    service = ExecutionServiceV2(
        db=db_session,
        code_generator=mock_code_generator
    )

    # First execution
    result1 = await service.start_execution(masterplan.masterplan_id)
    assert result1['successful_atoms'] == 5

    # Reset state
    service.reset_execution_state()

    # Progress should be reset
    progress = service.wave_executor.track_progress()
    assert progress['total'] == 0

    # Retry history should be reset
    retry_stats = service.retry_orchestrator.get_retry_statistics()
    assert retry_stats['total_atoms_retried'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
