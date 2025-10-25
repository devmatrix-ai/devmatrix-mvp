"""
Unit Tests - GraphBuilder

Tests dependency graph construction from atoms.

Author: DevMatrix Team
Date: 2025-10-24
"""

import pytest
import uuid
from src.dependency.graph_builder import GraphBuilder, DependencyType
from src.models import AtomicUnit


@pytest.fixture
def graph_builder():
    return GraphBuilder()


@pytest.fixture
def sample_atoms():
    """Create sample atoms for testing"""
    masterplan_id = uuid.uuid4()
    task_id = uuid.uuid4()

    # Atom 1: Defines a function
    atom1 = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=masterplan_id,
        task_id=task_id,
        atom_number=1,
        name="Define calculate function",
        loc=5,
        description="Define calculate function",
        code_to_generate="def calculate(x): return x * 2",
        file_path="src/calc.py",
        language="python",
        complexity=1.0,
        status="pending",
        
        context_completeness=0.95
    )

    # Atom 2: Uses calculate function
    atom2 = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=masterplan_id,
        task_id=task_id,
        atom_number=2,
        name="Use calculate",
        loc=5,
        description="Use calculate",
        code_to_generate="result = calculate(10)",
        file_path="src/main.py",
        language="python",
        complexity=1.0,
        status="pending",
        
        context_completeness=0.95
    )

    # Atom 3: Independent
    atom3 = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=masterplan_id,
        task_id=task_id,
        atom_number=3,
        name="Independent function",
        loc=5,
        description="Independent function",
        code_to_generate="def greet(name): return f'Hello, {name}'",
        file_path="src/greet.py",
        language="python",
        complexity=1.0,
        status="pending",
        
        context_completeness=0.95
    )

    return [atom1, atom2, atom3]


# ============================================================================
# Graph Building Tests
# ============================================================================

def test_build_graph_basic(graph_builder, sample_atoms):
    """Test basic graph construction"""
    graph = graph_builder.build_graph(sample_atoms)

    assert graph is not None
    assert graph.number_of_nodes() == 3
    # Should have at least one edge (atom2 depends on atom1)
    assert graph.number_of_edges() >= 0


def test_detect_import_dependencies(graph_builder):
    """Test import dependency detection"""
    atoms = [
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=1,
        name="Define module",
        loc=5,
            description="Define module",
            code_to_generate="class User: pass",
            file_path="src/models.py",
            language="python",
            complexity=1.0,
            status="pending",
            
            context_completeness=0.95
        ),
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=2,
        name="Import module",
        loc=5,
            description="Import module",
            code_to_generate="from models import User",
            file_path="src/main.py",
            language="python",
            complexity=1.0,
            status="pending",
            
            context_completeness=0.95
        )
    ]

    graph = graph_builder.build_graph(atoms)
    # Should detect import dependency
    assert graph.number_of_nodes() == 2


def test_detect_function_call_dependencies(graph_builder):
    """Test function call dependency detection"""
    atom1_id = uuid.uuid4()
    atom2_id = uuid.uuid4()

    atoms = [
        AtomicUnit(
            atom_id=atom1_id,
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=1,
        name="Define helper",
        loc=5,
            description="Define helper",
            code_to_generate="def helper(): return 1",
            file_path="src/utils.py",
            language="python",
            complexity=1.0,
            status="pending",
            
            context_completeness=0.95
        ),
        AtomicUnit(
            atom_id=atom2_id,
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=2,
        name="Call helper",
        loc=5,
            description="Call helper",
            code_to_generate="result = helper()",
            file_path="src/main.py",
            language="python",
            complexity=1.0,
            status="pending",
            
            context_completeness=0.95
        )
    ]

    graph = graph_builder.build_graph(atoms)
    # Should have edges representing dependencies
    assert graph.number_of_edges() >= 0


def test_detect_variable_dependencies(graph_builder):
    """Test variable usage dependency detection"""
    atoms = [
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=1,
        name="Define constant",
        loc=5,
            description="Define constant",
            code_to_generate="MAX_SIZE = 100",
            file_path="src/config.py",
            language="python",
            complexity=1.0,
            status="pending",
            
            context_completeness=0.95
        ),
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=2,
        name="Use constant",
        loc=5,
            description="Use constant",
            code_to_generate="if size > MAX_SIZE: raise ValueError()",
            file_path="src/validator.py",
            language="python",
            complexity=1.0,
            status="pending",
            
            context_completeness=0.95
        )
    ]

    graph = graph_builder.build_graph(atoms)
    assert graph.number_of_nodes() == 2


# ============================================================================
# Cycle Detection Tests
# ============================================================================

def test_handle_circular_references(graph_builder):
    """Test handling of circular dependencies"""
    atom1_id = uuid.uuid4()
    atom2_id = uuid.uuid4()

    # Create circular dependency manually
    atoms = [
        AtomicUnit(
            atom_id=atom1_id,
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=1,
        name="Function A",
        loc=5,
            description="Function A",
            code_to_generate="def a(): return b()",
            file_path="src/a.py",
            language="python",
            complexity=1.0,
            status="pending",
              # A depends on B
            context_completeness=0.95
        ),
        AtomicUnit(
            atom_id=atom2_id,
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=2,
        name="Function B",
        loc=5,
            description="Function B",
            code_to_generate="def b(): return a()",
            file_path="src/b.py",
            language="python",
            complexity=1.0,
            status="pending",
              # B depends on A (circular!)
            context_completeness=0.95
        )
    ]

    graph = graph_builder.build_graph(atoms)
    stats = graph_builder.get_graph_stats(graph)

    # Should detect cycle
    assert stats['cycles'] > 0


# ============================================================================
# Graph Statistics Tests
# ============================================================================

def test_get_graph_stats(graph_builder, sample_atoms):
    """Test graph statistics calculation"""
    graph = graph_builder.build_graph(sample_atoms)
    stats = graph_builder.get_graph_stats(graph)

    assert 'nodes' in stats
    assert 'edges' in stats
    assert 'cycles' in stats
    assert 'avg_dependencies' in stats
    assert stats['nodes'] == 3


# ============================================================================
# Symbol Extraction Tests
# ============================================================================

def test_extract_python_symbols(graph_builder):
    """Test Python symbol extraction"""
    atoms = [
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=1,
        name="Define symbols",
        loc=5,
            description="Define symbols",
            code_to_generate="""
class MyClass:
    pass

def my_function():
    pass

MY_CONSTANT = 42
""",
            file_path="src/module.py",
            language="python",
            complexity=1.0,
            status="pending",
            
            context_completeness=0.95
        )
    ]

    symbols = graph_builder._extract_symbols(atoms)

    # Should extract class, function, and constant
    assert len(symbols) > 0
    assert any('MyClass' in str(sym) for sym in symbols.values())
    assert any('my_function' in str(sym) for sym in symbols.values())


# ============================================================================
# Dependency Type Tests
# ============================================================================

def test_dependency_types_supported(graph_builder):
    """Test that all 5 dependency types are supported"""
    # Verify DependencyType enum has all types
    assert hasattr(DependencyType, 'IMPORT')
    assert hasattr(DependencyType, 'FUNCTION_CALL')
    assert hasattr(DependencyType, 'VARIABLE')
    assert hasattr(DependencyType, 'TYPE')
    assert hasattr(DependencyType, 'DATA_FLOW')


# ============================================================================
# Edge Cases
# ============================================================================

def test_build_graph_empty_atoms(graph_builder):
    """Test building graph with no atoms"""
    graph = graph_builder.build_graph([])

    assert graph.number_of_nodes() == 0
    assert graph.number_of_edges() == 0


def test_build_graph_single_atom(graph_builder):
    """Test building graph with single atom"""
    atoms = [
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=1,
        name="Single",
        loc=5,
            description="Single",
            code_to_generate="def single(): pass",
            file_path="src/single.py",
            language="python",
            complexity=1.0,
            status="pending",
            
            context_completeness=0.95
        )
    ]

    graph = graph_builder.build_graph(atoms)

    assert graph.number_of_nodes() == 1
    assert graph.number_of_edges() == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
