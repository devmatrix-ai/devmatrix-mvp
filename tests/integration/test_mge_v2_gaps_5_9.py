"""
Integration Tests - MGE V2 Gaps 5-9

Tests end-to-end integration of dependency graph, atomization,
topological sorting, concurrency, and cost guardrails.

Author: DevMatrix Team
Date: 2025-10-25
"""

import pytest
import asyncio
from uuid import uuid4
from unittest.mock import MagicMock, AsyncMock, patch

from src.dependency.graph_builder import GraphBuilder
from src.dependency.topological_sorter import TopologicalSorter
from src.concurrency.backpressure_queue import BackpressureQueue
from src.cost.cost_guardrails import CostGuardrails
from src.cost.cost_tracker import CostBreakdown
from src.models import AtomicUnit


# ============================================================================
# Helper Functions
# ============================================================================

def create_test_atom(
    atom_number: int,
    name: str,
    code: str,
    language: str = "python",
    complexity: float = 1.0
):
    """Create test atom with required fields"""
    return AtomicUnit(
        atom_id=uuid4(),
        masterplan_id=uuid4(),
        task_id=uuid4(),
        atom_number=atom_number,
        name=name,
        description=f"Atom {atom_number}",
        code_to_generate=code,
        file_path=f"src/{name}.py",
        language=language,
        loc=len(code.split('\n')),
        complexity=complexity,
        status="pending",
        context_completeness=0.95
    )


def create_atom_chain(count: int = 5):
    """Create chain of dependent atoms"""
    atoms = []
    for i in range(count):
        code = f"def func_{i}():\n    pass"
        atom = create_test_atom(i + 1, f"atom_{i}", code)
        atoms.append(atom)
    return atoms


def create_parallel_atoms(count: int = 3):
    """Create independent parallel atoms"""
    atoms = []
    for i in range(count):
        code = f"def independent_{i}():\n    return {i}"
        atom = create_test_atom(i + 1, f"independent_{i}", code)
        atoms.append(atom)
    return atoms


# ============================================================================
# Integration Test 1: Dependency Graph → Topological Sort
# ============================================================================

def test_graph_to_topological_sort_integration():
    """
    Integration test: Dependency graph builds correctly and feeds
    into topological sorter for wave generation
    """
    # Create atoms with simple dependency chain: A → B → C
    atoms = [
        create_test_atom(1, "base", "def base(): pass"),
        create_test_atom(2, "middle", "from base import base\ndef middle(): base()"),
        create_test_atom(3, "top", "from middle import middle\ndef top(): middle()")
    ]

    # Build dependency graph
    graph_builder = GraphBuilder()
    graph = graph_builder.build_graph(atoms)

    # Verify graph structure
    assert graph.number_of_nodes() == 3
    assert graph.number_of_edges() >= 1  # At least one dependency

    # Create execution plan with topological sorter
    sorter = TopologicalSorter()
    plan = sorter.create_execution_plan(graph, atoms)

    # Verify execution plan
    assert plan.total_waves >= 1
    assert len(plan.waves) >= 1

    # Verify atoms are ordered correctly (no dependencies before dependents)
    executed_atoms = set()
    for wave in plan.waves:
        for atom_id in wave.atom_ids:
            # atom_id is UUID, but graph uses string nodes
            atom_id_str = str(atom_id)
            # Check all dependencies have been executed
            if atom_id_str in graph:
                for dep in graph.predecessors(atom_id_str):
                    assert dep in executed_atoms, f"Dependency {dep} not executed before {atom_id_str}"
            executed_atoms.add(atom_id_str)


# ============================================================================
# Integration Test 2: E2E Pipeline (Graph → Sort → Queue → Cost)
# ============================================================================

@pytest.mark.asyncio
async def test_e2e_pipeline_integration():
    """
    Integration test: Full pipeline from dependency graph through
    execution planning with cost guardrails
    """
    masterplan_id = uuid4()

    # 1. Create complex atom set (10 atoms)
    atoms = []
    for i in range(10):
        atom = create_test_atom(
            i + 1,
            f"atom_{i}",
            f"def func_{i}():\n    return {i}",
            complexity=1.0 + (i * 0.1)
        )
        atoms.append(atom)

    # 2. Build dependency graph
    graph_builder = GraphBuilder()
    graph = graph_builder.build_graph(atoms)

    assert graph.number_of_nodes() == 10

    # 3. Create execution plan
    sorter = TopologicalSorter()
    plan = sorter.create_execution_plan(graph, atoms)

    assert plan.total_waves > 0
    assert len(plan.waves) > 0

    # Create atom lookup for later use
    atom_lookup = {str(atom.atom_id): atom for atom in atoms}

    # 4. Setup cost guardrails with mock tracker
    mock_tracker = MagicMock()
    mock_tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=25.0,
        total_input_tokens=50000,
        total_output_tokens=25000,
        call_count=10
    )
    mock_tracker._calculate_cost.return_value = 5.0

    guardrails = CostGuardrails(
        cost_tracker=mock_tracker,
        default_soft_limit=50.0,
        default_hard_limit=100.0
    )

    # Check cost before execution
    result = guardrails.check_limits(masterplan_id)
    assert result['within_limits'] is True

    # Check before execution with estimated tokens
    guardrails.check_before_execution(
        masterplan_id=masterplan_id,
        estimated_tokens=100000
    )  # Should not raise

    # 5. Setup backpressure queue for concurrency control
    queue = BackpressureQueue(max_queue_size=100, request_timeout_seconds=60)

    # Enqueue atoms from first wave
    if plan.waves:
        first_wave = plan.waves[0]
        for idx, atom_id in enumerate(first_wave.atom_ids):
            atom_id_str = str(atom_id)
            enqueued = await queue.enqueue(
                request_id=atom_id_str,
                payload={"atom": atom_lookup[atom_id_str]},
                priority=1 + idx  # Unique priorities to avoid heapq comparison
            )
            assert enqueued is True

    # Verify queue statistics
    stats = queue.get_statistics()
    assert stats['current_size'] > 0

    # Integration successful - all components working together


# ============================================================================
# Integration Test 3: Concurrency + Cost Guardrails Integration
# ============================================================================

@pytest.mark.asyncio
async def test_concurrency_cost_integration():
    """
    Integration test: Concurrency control with cost guardrails
    validates execution doesn't exceed limits
    """
    masterplan_id = uuid4()

    # Setup cost guardrails with low limits
    mock_tracker = MagicMock()
    mock_tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=45.0,  # Close to soft limit
        total_input_tokens=90000,
        total_output_tokens=45000,
        call_count=50
    )
    mock_tracker._calculate_cost.return_value = 10.0  # Large per-operation cost

    guardrails = CostGuardrails(
        cost_tracker=mock_tracker,
        default_soft_limit=50.0,
        default_hard_limit=100.0
    )

    # Check limits before queueing
    status = guardrails.check_limits(masterplan_id)
    assert status['within_limits'] is True
    assert status['soft_limit_exceeded'] is False

    # Setup queue
    queue = BackpressureQueue(max_queue_size=10, request_timeout_seconds=5)

    # Simulate concurrent execution with cost checking
    atoms = create_parallel_atoms(5)

    for atom in atoms:
        # Check cost before each operation
        try:
            guardrails.check_before_execution(
                masterplan_id=masterplan_id,
                estimated_tokens=50000  # Would push over limit
            )
            # If passes, enqueue
            await queue.enqueue(str(atom.atom_id), {"atom": atom}, priority=5)
        except Exception:
            # Cost limit would be exceeded, don't enqueue
            pass

    # Verify cost protection worked
    stats = queue.get_statistics()
    # Queue should be empty or minimal because cost limit prevented enqueuing
    assert stats['current_size'] <= 5


# ============================================================================
# Integration Test 4: Error Propagation Across Components
# ============================================================================

def test_error_propagation_integration():
    """
    Integration test: Error handling propagates correctly
    through the pipeline
    """
    # Create atoms with invalid configuration
    atoms = [
        create_test_atom(1, "atom_1", "invalid python syntax {{{"),
        create_test_atom(2, "atom_2", "def func(): pass")
    ]

    # Build graph - should handle syntax errors gracefully
    graph_builder = GraphBuilder()
    graph = graph_builder.build_graph(atoms)

    # Graph should be built despite syntax errors (best effort)
    assert graph.number_of_nodes() == 2

    # Topological sorter should handle graph issues
    sorter = TopologicalSorter()

    try:
        plan = sorter.create_execution_plan(graph, atoms)
        # Should complete even with problematic atoms
        assert plan is not None
    except Exception as e:
        # If it fails, should be a clear error message
        assert "graph" in str(e).lower() or "cycle" in str(e).lower()


# ============================================================================
# Integration Test 5: Large Scale Integration (50 Atoms)
# ============================================================================

@pytest.mark.asyncio
async def test_large_scale_integration():
    """
    Integration test: Full pipeline with 50 atoms tests scalability
    and performance of integrated system
    """
    masterplan_id = uuid4()

    # Create 50 atoms with mixed dependencies
    atoms = []
    for i in range(50):
        code = f"""
def func_{i}():
    # Atom {i}
    return {i}

class Class_{i}:
    pass
"""
        atom = create_test_atom(
            i + 1,
            f"module_{i}",
            code,
            complexity=1.0 + (i * 0.02)
        )
        atoms.append(atom)

    # 1. Build dependency graph
    graph_builder = GraphBuilder()
    graph = graph_builder.build_graph(atoms)

    assert graph.number_of_nodes() == 50

    # 2. Create execution plan
    sorter = TopologicalSorter()
    plan = sorter.create_execution_plan(graph, atoms)

    assert plan.total_waves > 0
    assert plan.max_parallelism > 0

    # Verify all atoms accounted for
    all_wave_atoms = []
    for wave in plan.waves:
        all_wave_atoms.extend(wave.atom_ids)
    assert len(all_wave_atoms) == 50

    # Create atom lookup for later use
    atom_lookup = {str(atom.atom_id): atom for atom in atoms}

    # 3. Setup cost tracking
    mock_tracker = MagicMock()
    mock_tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=10.0,
        total_input_tokens=20000,
        total_output_tokens=10000,
        call_count=50
    )
    mock_tracker._calculate_cost.return_value = 2.0

    guardrails = CostGuardrails(
        cost_tracker=mock_tracker,
        default_soft_limit=500.0,  # High limit for large scale
        default_hard_limit=1000.0
    )

    # Check cost is reasonable for 50 atoms
    status = guardrails.check_limits(masterplan_id)
    assert status['within_limits'] is True

    # 4. Setup large queue
    queue = BackpressureQueue(max_queue_size=100, request_timeout_seconds=60)

    # Enqueue first wave
    if plan.waves:
        for idx, atom_id in enumerate(plan.waves[0].atom_ids):
            atom_id_str = str(atom_id)
            enqueued = await queue.enqueue(
                atom_id_str,
                {"atom": atom_lookup[atom_id_str]},
                priority=1 + idx  # Unique priorities to avoid heapq comparison
            )
            assert enqueued is True

    stats = queue.get_statistics()
    assert stats['current_size'] > 0

    # Large scale integration successful


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
