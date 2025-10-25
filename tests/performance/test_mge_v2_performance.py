"""
Performance Benchmarks - MGE V2 Gaps 5-9

Performance tests for dependency graph, atomization, topological sort,
concurrency, and cost guardrails with specific performance targets.

Author: DevMatrix Team
Date: 2025-10-25
"""

import pytest
import time
import asyncio
from uuid import uuid4
from unittest.mock import MagicMock

from src.dependency.graph_builder import GraphBuilder
from src.dependency.topological_sorter import TopologicalSorter
from src.concurrency.backpressure_queue import BackpressureQueue
from src.cost.cost_guardrails import CostGuardrails
from src.cost.cost_tracker import CostBreakdown
from src.models import AtomicUnit


# ============================================================================
# Helper Functions
# ============================================================================

def create_test_atom(atom_number: int, code_lines: int = 10):
    """Create test atom with specified lines of code"""
    code = "\n".join([f"def func_{i}(): pass" for i in range(code_lines)])
    return AtomicUnit(
        atom_id=uuid4(),
        masterplan_id=uuid4(),
        task_id=uuid4(),
        atom_number=atom_number,
        name=f"atom_{atom_number}",
        description=f"Atom {atom_number}",
        code_to_generate=code,
        file_path=f"src/atom_{atom_number}.py",
        language="python",
        loc=code_lines,
        complexity=1.0,
        status="pending",
        context_completeness=0.95
    )


# ============================================================================
# Performance Test 1: Dependency Graph with 1000 Atoms (Target: <5s)
# ============================================================================

def test_dependency_graph_1000_atoms_performance():
    """
    Performance benchmark: Dependency graph building with 1000 atoms
    Target: <5 seconds
    """
    # Create 1000 atoms with simple code
    atoms = [create_test_atom(i) for i in range(1000)]

    # Benchmark graph building
    graph_builder = GraphBuilder()
    start = time.time()
    graph = graph_builder.build_graph(atoms)
    duration = time.time() - start

    # Verify correctness
    assert graph.number_of_nodes() == 1000

    # Performance assertion
    assert duration < 5.0, f"Too slow: {duration:.2f}s > 5.0s target"

    print(f"\n✅ Graph building (1000 atoms): {duration:.3f}s (target: <5.0s)")


# ============================================================================
# Performance Test 2: Topological Sort 1000 Atoms (Target: <2s)
# ============================================================================

def test_topological_sort_1000_atoms_performance():
    """
    Performance benchmark: Topological sorting with 1000 atoms
    Target: <2 seconds
    """
    # Create 1000 atoms
    atoms = [create_test_atom(i) for i in range(1000)]

    # Build graph
    graph_builder = GraphBuilder()
    graph = graph_builder.build_graph(atoms)

    # Benchmark topological sort
    sorter = TopologicalSorter()
    start = time.time()
    plan = sorter.create_execution_plan(graph, atoms)
    duration = time.time() - start

    # Verify correctness
    assert plan.total_waves > 0

    # Count all atoms in plan
    total_atoms = sum(len(wave.atom_ids) for wave in plan.waves)
    assert total_atoms == 1000

    # Performance assertion
    assert duration < 2.0, f"Too slow: {duration:.2f}s > 2.0s target"

    print(f"\n✅ Topological sort (1000 atoms): {duration:.3f}s (target: <2.0s)")


# ============================================================================
# Performance Test 3: Queue Throughput (Target: >1000 req/s)
# ============================================================================

@pytest.mark.asyncio
async def test_queue_throughput_performance():
    """
    Performance benchmark: Queue throughput
    Target: >1000 requests/second
    """
    queue = BackpressureQueue(max_queue_size=2000, request_timeout_seconds=60)

    # Enqueue 1000 requests as fast as possible
    request_count = 1000
    start = time.time()

    for i in range(request_count):
        await queue.enqueue(
            request_id=f"req-{i}",
            payload={"data": i},
            priority=i  # Unique priorities to avoid heapq comparison
        )

    duration = time.time() - start
    throughput = request_count / duration

    # Verify correctness
    stats = queue.get_statistics()
    assert stats['enqueued_total'] == request_count

    # Performance assertion
    assert throughput > 1000.0, f"Too slow: {throughput:.0f} req/s < 1000 req/s target"

    print(f"\n✅ Queue throughput: {throughput:.0f} req/s (target: >1000 req/s)")


# ============================================================================
# Performance Test 4: Cost Check (Target: <100ms)
# ============================================================================

def test_cost_check_performance():
    """
    Performance benchmark: Cost guardrails check
    Target: <100ms
    """
    masterplan_id = uuid4()

    # Setup cost tracker mock
    mock_tracker = MagicMock()
    mock_tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=45.0,
        total_input_tokens=90000,
        total_output_tokens=45000,
        call_count=100
    )

    guardrails = CostGuardrails(
        cost_tracker=mock_tracker,
        default_soft_limit=50.0,
        default_hard_limit=100.0
    )

    # Benchmark cost check (run 100 times, measure average)
    iterations = 100
    start = time.time()

    for _ in range(iterations):
        result = guardrails.check_limits(masterplan_id)
        assert result['within_limits'] is True

    duration = time.time() - start
    avg_duration_ms = (duration / iterations) * 1000

    # Performance assertion
    assert avg_duration_ms < 100.0, f"Too slow: {avg_duration_ms:.1f}ms > 100ms target"

    print(f"\n✅ Cost check: {avg_duration_ms:.2f}ms avg (target: <100ms)")


# ============================================================================
# Performance Test 5: E2E Pipeline with 100 Atoms (Target: <10s)
# ============================================================================

@pytest.mark.asyncio
async def test_e2e_pipeline_100_atoms_performance():
    """
    Performance benchmark: Complete pipeline with 100 atoms
    Target: <10 seconds total
    """
    masterplan_id = uuid4()

    # Create 100 atoms
    atoms = [create_test_atom(i) for i in range(100)]

    start = time.time()

    # 1. Build dependency graph
    graph_builder = GraphBuilder()
    graph = graph_builder.build_graph(atoms)

    # 2. Create execution plan
    sorter = TopologicalSorter()
    plan = sorter.create_execution_plan(graph, atoms)

    # 3. Setup cost guardrails
    mock_tracker = MagicMock()
    mock_tracker.get_masterplan_cost.return_value = CostBreakdown(
        total_cost_usd=10.0,
        total_input_tokens=20000,
        total_output_tokens=10000,
        call_count=50
    )
    mock_tracker._calculate_cost.return_value = 1.0

    guardrails = CostGuardrails(
        cost_tracker=mock_tracker,
        default_soft_limit=500.0,
        default_hard_limit=1000.0
    )

    # Check cost limits
    result = guardrails.check_limits(masterplan_id)
    assert result['within_limits'] is True

    # 4. Setup queue
    queue = BackpressureQueue(max_queue_size=200, request_timeout_seconds=60)

    # Enqueue first wave
    atom_lookup = {str(atom.atom_id): atom for atom in atoms}
    if plan.waves:
        for idx, atom_id in enumerate(plan.waves[0].atom_ids):
            await queue.enqueue(
                str(atom_id),
                {"atom": atom_lookup[str(atom_id)]},
                priority=1 + idx
            )

    duration = time.time() - start

    # Verify correctness
    assert graph.number_of_nodes() == 100
    assert plan.total_waves > 0
    stats = queue.get_statistics()
    assert stats['current_size'] > 0

    # Performance assertion
    assert duration < 10.0, f"Too slow: {duration:.2f}s > 10.0s target"

    print(f"\n✅ E2E pipeline (100 atoms): {duration:.3f}s (target: <10.0s)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
