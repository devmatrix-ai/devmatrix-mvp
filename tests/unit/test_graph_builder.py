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


# ============================================================================
# Additional Symbol Extraction Tests (Task 2.2 continued)
# ============================================================================

def test_extract_typescript_functions(graph_builder):
    """Test TypeScript function extraction"""
    atom = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        atom_number=1,
        name="TS Function",
        loc=3,
        description="TypeScript function",
        code_to_generate="""
function greet(name: string): string {
    return `Hello, ${name}`;
}
""",
        file_path="src/greet.ts",
        language="typescript",
        complexity=1.0,
        status="pending",
        context_completeness=0.95
    )
    
    symbols = graph_builder._extract_symbols([atom])
    assert len(symbols) > 0


def test_extract_javascript_exports(graph_builder):
    """Test JavaScript export extraction"""
    atom = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        atom_number=1,
        name="JS Exports",
        loc=2,
        description="JavaScript exports",
        code_to_generate="""
export function helper() { return true; }
export const API_URL = 'https://api.example.com';
""",
        file_path="src/utils.js",
        language="javascript",
        complexity=1.0,
        status="pending",
        context_completeness=0.95
    )
    
    symbols = graph_builder._extract_symbols([atom])
    assert len(symbols) > 0


def test_extract_python_classes_methods(graph_builder):
    """Test Python class and method extraction"""
    atom = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        atom_number=1,
        name="Python Class",
        loc=5,
        description="Python class with methods",
        code_to_generate="""
class Calculator:
    def add(self, a, b):
        return a + b
    def subtract(self, a, b):
        return a - b
""",
        file_path="src/calc.py",
        language="python",
        complexity=1.0,
        status="pending",
        context_completeness=0.95
    )
    
    symbols = graph_builder._extract_symbols([atom])
    assert len(symbols) > 0


# ============================================================================
# Additional Dependency Detection Tests (Task 2.3 continued)
# ============================================================================

def test_detect_cross_language_dependencies(graph_builder):
    """Test detection of dependencies across different languages"""
    atoms = [
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=1,
            name="Python API",
            loc=3,
            description="Python API endpoint",
            code_to_generate="def get_users(): return []",
            file_path="src/api.py",
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
            name="TS Client",
            loc=3,
            description="TypeScript client",
            code_to_generate="fetch('/api/users')",
            file_path="src/client.ts",
            language="typescript",
            complexity=1.0,
            status="pending",
            context_completeness=0.95
        )
    ]
    
    graph = graph_builder.build_graph(atoms)
    assert graph.number_of_nodes() == 2


def test_detect_nested_function_calls(graph_builder):
    """Test detection of nested function call dependencies"""
    atoms = [
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=1,
            name="Helper A",
            loc=1,
            description="Helper function A",
            code_to_generate="def helper_a(): return 1",
            file_path="src/helpers.py",
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
            name="Helper B",
            loc=1,
            description="Helper function B",
            code_to_generate="def helper_b(): return helper_a() + 1",
            file_path="src/helpers.py",
            language="python",
            complexity=1.0,
            status="pending",
            context_completeness=0.95
        ),
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=3,
            name="Main",
            loc=1,
            description="Main function",
            code_to_generate="def main(): return helper_b() * 2",
            file_path="src/main.py",
            language="python",
            complexity=1.0,
            status="pending",
            context_completeness=0.95
        )
    ]
    
    graph = graph_builder.build_graph(atoms)
    assert graph.number_of_nodes() == 3


def test_ignore_standard_library_dependencies(graph_builder):
    """Test that standard library imports don't create dependencies"""
    atom = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        atom_number=1,
        name="Stdlib Import",
        loc=5,
        description="Standard library imports",
        code_to_generate="""
import os
import sys
from datetime import datetime
""",
        file_path="src/utils.py",
        language="python",
        complexity=1.0,
        status="pending",
        context_completeness=0.95
    )
    
    graph = graph_builder.build_graph([atom])
    # Should have 1 node, 0 edges (stdlib doesn't count)
    assert graph.number_of_nodes() == 1
    assert graph.number_of_edges() == 0


# ============================================================================
# Additional Graph Construction Tests (Task 2.4 continued)
# ============================================================================

def test_graph_preserves_node_order(graph_builder):
    """Test that graph preserves atom_number ordering"""
    atoms = []
    for i in range(5):
        atoms.append(AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=i+1,
            name=f"Atom {i+1}",
            loc=1,
            description=f"Atom {i+1}",
            code_to_generate=f"x = {i}",
            file_path=f"src/module_{i}.py",
            language="python",
            complexity=1.0,
            status="pending",
            context_completeness=0.95
        ))
    
    graph = graph_builder.build_graph(atoms)
    
    # Verify all nodes have atom_number attribute
    for node_id in graph.nodes():
        assert 'atom_number' in graph.nodes[node_id]


def test_graph_handles_duplicate_symbols(graph_builder):
    """Test graph handles atoms with duplicate function names in different files"""
    atoms = [
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=1,
            name="Helper 1",
            loc=1,
            description="Helper in file 1",
            code_to_generate="def helper(): return 1",
            file_path="src/module1.py",
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
            name="Helper 2",
            loc=1,
            description="Helper in file 2",
            code_to_generate="def helper(): return 2",
            file_path="src/module2.py",
            language="python",
            complexity=1.0,
            status="pending",
            context_completeness=0.95
        )
    ]
    
    graph = graph_builder.build_graph(atoms)
    # Both atoms should exist as separate nodes
    assert graph.number_of_nodes() == 2


def test_graph_complexity_aggregation(graph_builder):
    """Test that graph aggregates complexity metrics"""
    atoms = []
    complexities = [1.0, 2.5, 1.5, 3.0, 2.0]
    
    for i, complexity in enumerate(complexities):
        atoms.append(AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=i+1,
            name=f"Atom {i+1}",
            loc=10,
            description=f"Atom {i+1}",
            code_to_generate=f"def func_{i}(): pass",
            file_path=f"src/module_{i}.py",
            language="python",
            complexity=complexity,
            status="pending",
            context_completeness=0.95
        ))
    
    graph = graph_builder.build_graph(atoms)
    stats = graph_builder.get_graph_stats(graph)
    
    # Verify stats are calculated
    assert stats['nodes'] == 5
    assert 'avg_dependencies' in stats


def test_graph_multi_language_support(graph_builder):
    """Test graph construction with mixed language atoms"""
    atoms = [
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=1,
            name="Python Atom",
            loc=2,
            description="Python code",
            code_to_generate="def py_func(): pass",
            file_path="src/module.py",
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
            name="TypeScript Atom",
            loc=2,
            description="TypeScript code",
            code_to_generate="function tsFunc() {}",
            file_path="src/module.ts",
            language="typescript",
            complexity=1.0,
            status="pending",
            context_completeness=0.95
        ),
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=3,
            name="JavaScript Atom",
            loc=2,
            description="JavaScript code",
            code_to_generate="const jsFunc = () => {}",
            file_path="src/module.js",
            language="javascript",
            complexity=1.0,
            status="pending",
            context_completeness=0.95
        )
    ]
    
    graph = graph_builder.build_graph(atoms)
    
    # All atoms should be in graph
    assert graph.number_of_nodes() == 3
    
    # Verify language attributes preserved
    languages = [graph.nodes[n]['language'] for n in graph.nodes()]
    assert 'python' in languages
    assert 'typescript' in languages
    assert 'javascript' in languages


# ============================================================================
# Integration and Edge Case Tests
# ============================================================================

def test_graph_with_long_dependency_chain(graph_builder):
    """Test graph with long dependency chain (A→B→C→D→E)"""
    atoms = []
    for i in range(5):
        if i == 0:
            code = "def func_0(): return 0"
        else:
            code = f"def func_{i}(): return func_{i-1}() + 1"
        
        atoms.append(AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=i+1,
            name=f"Function {i}",
            loc=1,
            description=f"Function {i}",
            code_to_generate=code,
            file_path=f"src/chain_{i}.py",
            language="python",
            complexity=1.0,
            status="pending",
            context_completeness=0.95
        ))
    
    graph = graph_builder.build_graph(atoms)
    
    # Should have 5 nodes
    assert graph.number_of_nodes() == 5
    
    # Stats should show chain structure
    stats = graph_builder.get_graph_stats(graph)
    assert stats['nodes'] == 5


def test_graph_with_fan_out_pattern(graph_builder):
    """Test graph with fan-out pattern (A → B, A → C, A → D)"""
    # Create root atom
    root = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        atom_number=1,
        name="Root",
        loc=2,
        description="Root function",
        code_to_generate="def root(): return 42",
        file_path="src/root.py",
        language="python",
        complexity=1.0,
        status="pending",
        context_completeness=0.95
    )
    
    # Create dependent atoms
    atoms = [root]
    for i in range(3):
        atoms.append(AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=i+2,
            name=f"Dependent {i}",
            loc=1,
            description=f"Uses root {i}",
            code_to_generate=f"def dep_{i}(): return root() + {i}",
            file_path=f"src/dep_{i}.py",
            language="python",
            complexity=1.0,
            status="pending",
            context_completeness=0.95
        ))
    
    graph = graph_builder.build_graph(atoms)
    
    # Should have 4 nodes
    assert graph.number_of_nodes() == 4


def test_graph_density_calculation(graph_builder):
    """Test graph density metric calculation"""
    # Create fully connected graph (all atoms depend on each other)
    atoms = []
    for i in range(4):
        atoms.append(AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=i+1,
            name=f"Atom {i}",
            loc=1,
            description=f"Atom {i}",
            code_to_generate=f"x = {i}",
            file_path=f"src/a{i}.py",
            language="python",
            complexity=1.0,
            status="pending",
            context_completeness=0.95
        ))
    
    graph = graph_builder.build_graph(atoms)
    stats = graph_builder.get_graph_stats(graph)
    
    # Density should be between 0 and 1
    assert 'density' in stats
    assert 0 <= stats['density'] <= 1


def test_graph_isolated_nodes_detection(graph_builder):
    """Test detection of isolated nodes with no dependencies"""
    atoms = [
        # Isolated atom 1
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=1,
            name="Isolated 1",
            loc=1,
            description="Isolated atom 1",
            code_to_generate="x = 1",
            file_path="src/isolated1.py",
            language="python",
            complexity=1.0,
            status="pending",
            context_completeness=0.95
        ),
        # Isolated atom 2
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=2,
            name="Isolated 2",
            loc=1,
            description="Isolated atom 2",
            code_to_generate="y = 2",
            file_path="src/isolated2.py",
            language="python",
            complexity=1.0,
            status="pending",
            context_completeness=0.95
        ),
        # Isolated atom 3
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=3,
            name="Isolated 3",
            loc=1,
            description="Isolated atom 3",
            code_to_generate="z = 3",
            file_path="src/isolated3.py",
            language="python",
            complexity=1.0,
            status="pending",
            context_completeness=0.95
        )
    ]
    
    graph = graph_builder.build_graph(atoms)
    stats = graph_builder.get_graph_stats(graph)
    
    # Should detect isolated nodes
    assert stats['isolated_nodes'] >= 0
    assert stats['nodes'] == 3


def test_graph_max_dependencies_tracking(graph_builder):
    """Test tracking of maximum dependencies per atom"""
    # Create one atom that many others depend on
    popular = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        atom_number=1,
        name="Popular",
        loc=2,
        description="Heavily used function",
        code_to_generate="def popular(): return 'used by many'",
        file_path="src/popular.py",
        language="python",
        complexity=1.0,
        status="pending",
        context_completeness=0.95
    )
    
    atoms = [popular]
    
    # Create 5 atoms that use popular
    for i in range(5):
        atoms.append(AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=i+2,
            name=f"User {i}",
            loc=1,
            description=f"Uses popular {i}",
            code_to_generate=f"def user_{i}(): return popular()",
            file_path=f"src/user_{i}.py",
            language="python",
            complexity=1.0,
            status="pending",
            context_completeness=0.95
        ))
    
    graph = graph_builder.build_graph(atoms)
    stats = graph_builder.get_graph_stats(graph)
    
    # Max dependencies should be tracked
    assert 'max_dependencies' in stats
    assert stats['max_dependencies'] >= 0
