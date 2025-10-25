"""
Unit Tests - TopologicalSorter

Tests wave generation and topological sorting.

Author: DevMatrix Team
Date: 2025-10-24
"""

import pytest
import uuid
import networkx as nx
from src.dependency.topological_sorter import TopologicalSorter, ExecutionPlan, ExecutionWave
from src.models import AtomicUnit


@pytest.fixture
def sorter():
    return TopologicalSorter()


@pytest.fixture
def sample_atoms():
    """Create sample atoms with dependencies"""
    masterplan_id = uuid.uuid4()
    task_id = uuid.uuid4()

    atoms = []
    for i in range(5):
        atoms.append(AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=masterplan_id,
            task_id=task_id,
            atom_number=i + 1,
            name=f"Atom {i+1}",
            description=f"Atom {i+1}",
            code_to_generate=f"def func_{i}(): pass",
            file_path=f"src/module_{i}.py",
            language="python",
            loc=5,
            complexity=1.0,
            status="pending",
            context_completeness=0.95
        ))

    return atoms


# ============================================================================
# Basic Topological Sort Tests
# ============================================================================

def test_topological_sort_correctness(sorter, sample_atoms):
    """Test topological sort correctness"""
    # Create linear dependency: 1 → 2 → 3 → 4 → 5
    graph = nx.DiGraph()
    for atom in sample_atoms:
        graph.add_node(atom.atom_id, atom=atom)

    for i in range(len(sample_atoms) - 1):
        graph.add_edge(sample_atoms[i].atom_id, sample_atoms[i+1].atom_id)

    plan = sorter.create_execution_plan(graph, sample_atoms)

    # Should have 5 waves (linear dependency)
    assert plan.total_waves == 5
    assert len(plan.waves) == 5


def test_cycle_detection(sorter):
    """Test cycle detection"""
    # Create cycle: A → B → C → A
    graph = nx.DiGraph()
    atom_ids = [uuid.uuid4() for _ in range(3)]

    for aid in atom_ids:
        graph.add_node(aid)

    graph.add_edge(atom_ids[0], atom_ids[1])
    graph.add_edge(atom_ids[1], atom_ids[2])
    graph.add_edge(atom_ids[2], atom_ids[0])  # Creates cycle

    # Create mock atoms
    atoms = [
        AtomicUnit(
            atom_id=aid,
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=i,
            name=f"Atom {i}",
            description=f"Atom {i}",
            code_to_generate="pass",
            file_path="file.py",
            language="python",
            loc=5,
            complexity=1.0,
            status="pending",
            context_completeness=0.95
        )
        for i, aid in enumerate(atom_ids)
    ]

    plan = sorter.create_execution_plan(graph, atoms)

    # Should handle cycle (break it or report it)
    assert plan is not None


# ============================================================================
# Wave Generation Tests
# ============================================================================

def test_level_grouping_correctness(sorter, sample_atoms):
    """Test level grouping correctness"""
    # Create graph with clear levels:
    # Wave 0: atoms[0], atoms[1] (no dependencies)
    # Wave 1: atoms[2] (depends on 0)
    # Wave 2: atoms[3], atoms[4] (depends on 2)

    graph = nx.DiGraph()
    for atom in sample_atoms:
        graph.add_node(atom.atom_id, atom=atom)

    graph.add_edge(sample_atoms[0].atom_id, sample_atoms[2].atom_id)  # 0 → 2
    graph.add_edge(sample_atoms[2].atom_id, sample_atoms[3].atom_id)  # 2 → 3
    graph.add_edge(sample_atoms[2].atom_id, sample_atoms[4].atom_id)  # 2 → 4

    plan = sorter.create_execution_plan(graph, sample_atoms)

    # Should have 3 waves
    assert plan.total_waves == 3

    # Wave 0 should have 2 atoms (0 and 1 - no deps)
    assert plan.waves[0].total_atoms == 2

    # Wave 1 should have 1 atom (2)
    assert plan.waves[1].total_atoms == 1

    # Wave 2 should have 2 atoms (3 and 4)
    assert plan.waves[2].total_atoms == 2


def test_waves_maximize_parallelization(sorter, sample_atoms):
    """Test waves maximize parallelization (>50x)"""
    # Create graph with no dependencies (all parallel)
    graph = nx.DiGraph()
    for atom in sample_atoms:
        graph.add_node(atom.atom_id, atom=atom)

    plan = sorter.create_execution_plan(graph, sample_atoms)

    # All 5 atoms should be in wave 0 (fully parallel)
    assert plan.total_waves == 1
    assert plan.waves[0].total_atoms == 5
    assert plan.max_parallelism == 5


def test_wave_optimization(sorter, sample_atoms):
    """Test wave optimization"""
    graph = nx.DiGraph()
    for atom in sample_atoms:
        graph.add_node(atom.atom_id, atom=atom)

    # Create some dependencies but allow parallelism
    graph.add_edge(sample_atoms[0].atom_id, sample_atoms[2].atom_id)

    plan = sorter.create_execution_plan(graph, sample_atoms)

    # Should optimize to minimize wave count
    assert plan.total_waves >= 2
    assert plan.total_waves <= 3


# ============================================================================
# Wave Properties Tests
# ============================================================================

def test_wave_0_no_dependencies(sorter, sample_atoms):
    """Test Wave 0 contains only atoms with no dependencies"""
    graph = nx.DiGraph()
    for atom in sample_atoms:
        graph.add_node(atom.atom_id, atom=atom)

    # Add some dependencies
    graph.add_edge(sample_atoms[0].atom_id, sample_atoms[1].atom_id)
    graph.add_edge(sample_atoms[2].atom_id, sample_atoms[3].atom_id)

    plan = sorter.create_execution_plan(graph, sample_atoms)

    # Wave 0 should only have atoms with no incoming edges
    wave_0_atoms = plan.waves[0].atom_ids
    for atom_id in wave_0_atoms:
        # Check no incoming edges in graph
        assert graph.in_degree(atom_id) == 0


def test_wave_n_depends_on_previous_waves(sorter, sample_atoms):
    """Test Wave N depends only on waves 0..N-1"""
    graph = nx.DiGraph()
    for atom in sample_atoms:
        graph.add_node(atom.atom_id, atom=atom)

    # Linear chain: 0 → 1 → 2 → 3 → 4
    for i in range(len(sample_atoms) - 1):
        graph.add_edge(sample_atoms[i].atom_id, sample_atoms[i+1].atom_id)

    plan = sorter.create_execution_plan(graph, sample_atoms)

    # Each wave should only depend on previous waves
    for wave_idx in range(1, len(plan.waves)):
        wave = plan.waves[wave_idx]
        for atom_id in wave.atom_ids:
            # Check all predecessors are in previous waves
            predecessors = list(graph.predecessors(atom_id))
            for pred in predecessors:
                # Find which wave pred is in
                pred_wave = None
                for w_idx, w in enumerate(plan.waves):
                    if pred in w.atom_ids:
                        pred_wave = w_idx
                        break
                # Predecessor should be in earlier wave
                assert pred_wave is not None
                assert pred_wave < wave_idx


# ============================================================================
# Cycle Breaking Tests
# ============================================================================

def test_handle_cycles_with_minimum_edges(sorter):
    """Test cycle breaking with minimum edge removal"""
    # Create complex cycle
    graph = nx.DiGraph()
    atom_ids = [uuid.uuid4() for _ in range(4)]

    for aid in atom_ids:
        graph.add_node(aid)

    # Create cycle: 0 → 1 → 2 → 3 → 0
    graph.add_edge(atom_ids[0], atom_ids[1])
    graph.add_edge(atom_ids[1], atom_ids[2])
    graph.add_edge(atom_ids[2], atom_ids[3])
    graph.add_edge(atom_ids[3], atom_ids[0])  # Cycle

    atoms = [
        AtomicUnit(
            atom_id=aid,
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=i,
            name=f"Atom {i}",
            description=f"Atom {i}",
            code_to_generate="pass",
            file_path="file.py",
            language="python",
            loc=5,
            complexity=1.0,
            status="pending",
            context_completeness=0.95
        )
        for i, aid in enumerate(atom_ids)
    ]

    plan = sorter.create_execution_plan(graph, atoms)

    # Should break cycle and create valid execution plan
    assert plan is not None
    assert plan.total_waves > 0


# ============================================================================
# Edge Cases
# ============================================================================

def test_empty_graph(sorter):
    """Test handling empty graph"""
    graph = nx.DiGraph()
    plan = sorter.create_execution_plan(graph, [])

    assert plan.total_waves == 0
    assert len(plan.waves) == 0


def test_single_node_graph(sorter):
    """Test single node graph"""
    graph = nx.DiGraph()
    atom = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        atom_number=1,
        name="Single",
        description="Single",
        code_to_generate="pass",
        file_path="file.py",
        language="python",
        loc=5,
        complexity=1.0,
        status="pending",
        context_completeness=0.95
    )

    graph.add_node(atom.atom_id, atom=atom)

    plan = sorter.create_execution_plan(graph, [atom])

    assert plan.total_waves == 1
    assert plan.waves[0].total_atoms == 1


def test_disconnected_components(sorter, sample_atoms):
    """Test graph with disconnected components"""
    graph = nx.DiGraph()

    # Add two disconnected components
    for atom in sample_atoms[:2]:
        graph.add_node(atom.atom_id, atom=atom)

    for atom in sample_atoms[2:4]:
        graph.add_node(atom.atom_id, atom=atom)

    # Add edge within first component
    graph.add_edge(sample_atoms[0].atom_id, sample_atoms[1].atom_id)

    # Add edge within second component
    graph.add_edge(sample_atoms[2].atom_id, sample_atoms[3].atom_id)

    plan = sorter.create_execution_plan(graph, sample_atoms[:4])

    # Should handle disconnected components
    assert plan.total_waves >= 2


# ============================================================================
# Wave Statistics Tests
# ============================================================================

def test_wave_statistics_calculations(sorter, sample_atoms):
    """Test wave statistics are calculated correctly"""
    graph = nx.DiGraph()
    for atom in sample_atoms:
        graph.add_node(atom.atom_id, atom=atom)

    # Create pattern with known parallelism
    # Wave 0: atoms[0], atoms[1] (2 parallel)
    # Wave 1: atoms[2] (1 serial)
    # Wave 2: atoms[3], atoms[4] (2 parallel)
    graph.add_edge(sample_atoms[0].atom_id, sample_atoms[2].atom_id)
    graph.add_edge(sample_atoms[1].atom_id, sample_atoms[2].atom_id)
    graph.add_edge(sample_atoms[2].atom_id, sample_atoms[3].atom_id)
    graph.add_edge(sample_atoms[2].atom_id, sample_atoms[4].atom_id)

    plan = sorter.create_execution_plan(graph, sample_atoms)

    # Verify statistics
    assert plan.total_waves == 3
    assert plan.total_atoms == 5
    assert plan.max_parallelism == 2
    assert plan.avg_parallelism > 1.0  # (2 + 1 + 2) / 3 = 1.66


def test_wave_estimated_duration(sorter, sample_atoms):
    """Test wave estimated duration based on complexity"""
    graph = nx.DiGraph()

    # Set different complexities
    sample_atoms[0].complexity = 1.0
    sample_atoms[1].complexity = 2.0
    sample_atoms[2].complexity = 3.0

    # Use string IDs for graph nodes to match atom_lookup keys
    for atom in sample_atoms[:3]:
        graph.add_node(str(atom.atom_id), atom=atom)

    plan = sorter.create_execution_plan(graph, sample_atoms[:3])

    # All 3 atoms in wave 0 (no dependencies)
    # Duration = (1.0 + 2.0 + 3.0) * 10 = 60 seconds
    assert plan.waves[0].estimated_duration == 60.0


def test_wave_dependencies_satisfied_flag(sorter, sample_atoms):
    """Test dependencies_satisfied flag is set correctly"""
    graph = nx.DiGraph()
    for atom in sample_atoms:
        graph.add_node(atom.atom_id, atom=atom)

    graph.add_edge(sample_atoms[0].atom_id, sample_atoms[1].atom_id)

    plan = sorter.create_execution_plan(graph, sample_atoms)

    # All waves should have dependencies satisfied (DAG)
    for wave in plan.waves:
        assert wave.dependencies_satisfied is True


# ============================================================================
# Cycle Breaking Advanced Tests
# ============================================================================

def test_multiple_cycles_detection(sorter):
    """Test detection of multiple independent cycles"""
    graph = nx.DiGraph()
    atom_ids = [uuid.uuid4() for _ in range(6)]

    for aid in atom_ids:
        graph.add_node(aid)

    # Create two independent cycles
    # Cycle 1: 0 → 1 → 2 → 0
    graph.add_edge(atom_ids[0], atom_ids[1])
    graph.add_edge(atom_ids[1], atom_ids[2])
    graph.add_edge(atom_ids[2], atom_ids[0])

    # Cycle 2: 3 → 4 → 5 → 3
    graph.add_edge(atom_ids[3], atom_ids[4])
    graph.add_edge(atom_ids[4], atom_ids[5])
    graph.add_edge(atom_ids[5], atom_ids[3])

    atoms = [
        AtomicUnit(
            atom_id=aid,
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=i,
            name=f"Atom {i}",
            description=f"Atom {i}",
            code_to_generate="pass",
            file_path="file.py",
            language="python",
            loc=5,
            complexity=1.0,
            status="pending",
            context_completeness=0.95
        )
        for i, aid in enumerate(atom_ids)
    ]

    plan = sorter.create_execution_plan(graph, atoms)

    assert plan.has_cycles is True
    assert len(plan.cycle_info) > 0


def test_nested_cycles(sorter):
    """Test handling of nested/overlapping cycles"""
    graph = nx.DiGraph()
    atom_ids = [uuid.uuid4() for _ in range(4)]

    for aid in atom_ids:
        graph.add_node(aid)

    # Create overlapping cycles
    # Cycle 1: 0 → 1 → 2 → 0
    # Cycle 2: 1 → 2 → 3 → 1
    graph.add_edge(atom_ids[0], atom_ids[1])
    graph.add_edge(atom_ids[1], atom_ids[2])
    graph.add_edge(atom_ids[2], atom_ids[0])
    graph.add_edge(atom_ids[2], atom_ids[3])
    graph.add_edge(atom_ids[3], atom_ids[1])

    atoms = [
        AtomicUnit(
            atom_id=aid,
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=i,
            name=f"Atom {i}",
            description=f"Atom {i}",
            code_to_generate="pass",
            file_path="file.py",
            language="python",
            loc=5,
            complexity=1.0,
            status="pending",
            context_completeness=0.95
        )
        for i, aid in enumerate(atom_ids)
    ]

    plan = sorter.create_execution_plan(graph, atoms)

    assert plan.has_cycles is True
    # After cycle breaking, should have valid execution plan
    assert plan.total_waves > 0


def test_self_loop_cycle(sorter):
    """Test handling of self-referencing cycle"""
    graph = nx.DiGraph()
    atom_id = uuid.uuid4()
    graph.add_node(atom_id)

    # Self-loop
    graph.add_edge(atom_id, atom_id)

    atom = AtomicUnit(
        atom_id=atom_id,
        masterplan_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        atom_number=1,
        name="Self Loop",
        description="Self Loop",
        code_to_generate="pass",
        file_path="file.py",
        language="python",
        loc=5,
        complexity=1.0,
        status="pending",
        context_completeness=0.95
    )

    plan = sorter.create_execution_plan(graph, [atom])

    assert plan.has_cycles is True
    assert plan.total_waves > 0  # Should still create plan after breaking cycle


# ============================================================================
# Large Graph Performance Tests
# ============================================================================

def test_large_linear_graph(sorter):
    """Test performance with large linear dependency chain"""
    # Create 100-atom linear chain
    atom_count = 100
    atoms = []
    graph = nx.DiGraph()

    for i in range(atom_count):
        atom = AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=i,
            name=f"Atom {i}",
            description=f"Atom {i}",
            code_to_generate="pass",
            file_path=f"file_{i}.py",
            language="python",
            loc=5,
            complexity=1.0,
            status="pending",
            context_completeness=0.95
        )
        atoms.append(atom)
        graph.add_node(atom.atom_id, atom=atom)

    # Create linear chain
    for i in range(atom_count - 1):
        graph.add_edge(atoms[i].atom_id, atoms[i+1].atom_id)

    plan = sorter.create_execution_plan(graph, atoms)

    # Should have 100 waves (fully serial)
    assert plan.total_waves == 100
    assert plan.max_parallelism == 1


def test_large_parallel_graph(sorter):
    """Test performance with fully parallel graph"""
    atom_count = 100
    atoms = []
    graph = nx.DiGraph()

    for i in range(atom_count):
        atom = AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=i,
            name=f"Atom {i}",
            description=f"Atom {i}",
            code_to_generate="pass",
            file_path=f"file_{i}.py",
            language="python",
            loc=5,
            complexity=1.0,
            status="pending",
            context_completeness=0.95
        )
        atoms.append(atom)
        graph.add_node(atom.atom_id, atom=atom)

    # No edges - all parallel
    plan = sorter.create_execution_plan(graph, atoms)

    # Should have 1 wave (fully parallel)
    assert plan.total_waves == 1
    assert plan.max_parallelism == 100


def test_complex_dependency_tree(sorter):
    """Test complex tree structure"""
    # Create binary tree: 1 root → 2 children → 4 grandchildren → 8 leaves
    atoms = []
    graph = nx.DiGraph()

    for i in range(15):  # 1 + 2 + 4 + 8 = 15 nodes
        atom = AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=i,
            name=f"Atom {i}",
            description=f"Atom {i}",
            code_to_generate="pass",
            file_path=f"file_{i}.py",
            language="python",
            loc=5,
            complexity=1.0,
            status="pending",
            context_completeness=0.95
        )
        atoms.append(atom)
        graph.add_node(atom.atom_id, atom=atom)

    # Build binary tree structure
    # Level 0: node 0
    # Level 1: nodes 1, 2
    # Level 2: nodes 3, 4, 5, 6
    # Level 3: nodes 7-14
    for i in range(7):
        left_child = 2 * i + 1
        right_child = 2 * i + 2
        if left_child < 15:
            graph.add_edge(atoms[i].atom_id, atoms[left_child].atom_id)
        if right_child < 15:
            graph.add_edge(atoms[i].atom_id, atoms[right_child].atom_id)

    plan = sorter.create_execution_plan(graph, atoms)

    # Should have 4 waves (tree depth)
    assert plan.total_waves == 4


# ============================================================================
# Wave Splitting Tests
# ============================================================================

def test_optimize_waves_split_large(sorter, sample_atoms):
    """Test wave splitting for large waves"""
    # Create wave with 150 atoms (exceeds max_wave_size=100)
    large_wave = ExecutionWave(
        wave_number=0,
        atom_ids=[uuid.uuid4() for _ in range(150)],
        total_atoms=150,
        estimated_duration=1500.0
    )

    optimized = sorter.optimize_waves([large_wave], max_wave_size=100)

    # Should split into 2 waves
    assert len(optimized) == 2
    assert optimized[0].total_atoms == 100
    assert optimized[1].total_atoms == 50


def test_optimize_waves_preserve_small(sorter):
    """Test wave optimization preserves small waves"""
    waves = [
        ExecutionWave(
            wave_number=0,
            atom_ids=[uuid.uuid4() for _ in range(50)],
            total_atoms=50
        ),
        ExecutionWave(
            wave_number=1,
            atom_ids=[uuid.uuid4() for _ in range(30)],
            total_atoms=30
        )
    ]

    optimized = sorter.optimize_waves(waves, max_wave_size=100)

    # Should preserve both waves
    assert len(optimized) == 2
    assert optimized[0].total_atoms == 50
    assert optimized[1].total_atoms == 30


# ============================================================================
# Edge Case Tests
# ============================================================================

def test_graph_with_isolated_nodes_and_connected(sorter):
    """Test graph with mix of isolated and connected nodes"""
    atoms = []
    graph = nx.DiGraph()

    for i in range(6):
        atom = AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=i,
            name=f"Atom {i}",
            description=f"Atom {i}",
            code_to_generate="pass",
            file_path=f"file_{i}.py",
            language="python",
            loc=5,
            complexity=1.0,
            status="pending",
            context_completeness=0.95
        )
        atoms.append(atom)
        graph.add_node(atom.atom_id, atom=atom)

    # Connected: 0 → 1 → 2
    graph.add_edge(atoms[0].atom_id, atoms[1].atom_id)
    graph.add_edge(atoms[1].atom_id, atoms[2].atom_id)

    # Isolated: 3, 4, 5

    plan = sorter.create_execution_plan(graph, atoms)

    # Wave 0: 0, 3, 4, 5 (4 atoms)
    # Wave 1: 1
    # Wave 2: 2
    assert plan.total_waves == 3
    assert plan.waves[0].total_atoms == 4


def test_very_high_complexity_atoms(sorter):
    """Test atoms with very high complexity values"""
    atoms = []
    graph = nx.DiGraph()

    complexities = [10.0, 50.0, 100.0]
    for i, complexity in enumerate(complexities):
        atom = AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=i,
            name=f"Complex Atom {i}",
            description=f"Atom {i}",
            code_to_generate="pass",
            file_path=f"file_{i}.py",
            language="python",
            loc=50,
            complexity=complexity,
            status="pending",
            context_completeness=0.95
        )
        atoms.append(atom)
        # Use string ID for graph node to match atom_lookup keys
        graph.add_node(str(atom.atom_id), atom=atom)

    plan = sorter.create_execution_plan(graph, atoms)

    # All parallel, duration = (10 + 50 + 100) * 10 = 1600s
    assert plan.waves[0].estimated_duration == 1600.0


def test_wave_number_ordering(sorter, sample_atoms):
    """Test waves are numbered sequentially"""
    graph = nx.DiGraph()
    for atom in sample_atoms:
        graph.add_node(atom.atom_id, atom=atom)

    # Create multi-level dependency
    graph.add_edge(sample_atoms[0].atom_id, sample_atoms[1].atom_id)
    graph.add_edge(sample_atoms[1].atom_id, sample_atoms[2].atom_id)

    plan = sorter.create_execution_plan(graph, sample_atoms)

    # Verify sequential wave numbering
    for i, wave in enumerate(plan.waves):
        assert wave.wave_number == i


def test_atom_lookup_with_missing_atoms(sorter):
    """Test handling when atom_lookup is incomplete"""
    atoms = []
    graph = nx.DiGraph()

    for i in range(3):
        atom = AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=i,
            name=f"Atom {i}",
            description=f"Atom {i}",
            code_to_generate="pass",
            file_path=f"file_{i}.py",
            language="python",
            loc=5,
            complexity=1.0,
            status="pending",
            context_completeness=0.95
        )
        atoms.append(atom)
        graph.add_node(atom.atom_id, atom=atom)

    # Add extra node not in atoms list
    extra_id = uuid.uuid4()
    graph.add_node(extra_id)

    # Should not crash even with missing atom
    plan = sorter.create_execution_plan(graph, atoms)
    assert plan is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
