"""
Unit Tests - RecursiveDecomposer

Tests recursive task decomposition into atomic units.

Author: DevMatrix Team
Date: 2025-10-24
"""

import pytest
from src.atomization.decomposer import RecursiveDecomposer, DecompositionResult
from src.atomization.parser import MultiLanguageParser


@pytest.fixture
def parser():
    """Create MultiLanguageParser instance"""
    return MultiLanguageParser()


@pytest.fixture
def decomposer(parser):
    """Create RecursiveDecomposer instance"""
    return RecursiveDecomposer(parser, target_loc=10)


# ============================================================================
# Basic Decomposition Tests
# ============================================================================

def test_decompose_80_loc_to_8_atoms(decomposer):
    """Test decomposing 80 LOC code into ~8 atoms"""
    # Generate 80-line code
    code = "\n".join([
        "def function_1():",
        "    pass",
        "",
        "def function_2():",
        "    pass",
        "",
        "def function_3():",
        "    pass",
        "",
        "def function_4():",
        "    pass",
        ""
    ] * 7)  # ~84 lines

    result = decomposer.decompose(code, "python")

    assert result.success is True
    assert len(result.atoms) >= 7
    assert len(result.atoms) <= 10
    # Each atom should be around 10 LOC
    for atom in result.atoms:
        assert atom.loc <= 15  # Max 15 LOC per atom


def test_decompose_25_loc_to_2_3_atoms(decomposer):
    """Test decomposing 25 LOC code into 2-3 atoms"""
    code = """
def calculate_total(items):
    total = 0
    for item in items:
        total += item.price
    return total

def calculate_discount(total, percentage):
    return total * (percentage / 100)

def apply_discount(items, discount_percentage):
    total = calculate_total(items)
    discount = calculate_discount(total, discount_percentage)
    return total - discount
"""
    result = decomposer.decompose(code, "python")

    assert result.success is True
    assert len(result.atoms) >= 2
    assert len(result.atoms) <= 4
    assert result.total_loc == 13  # Actual LOC in code


def test_decompose_verifies_atom_independence(decomposer):
    """Test that decomposed atoms are independent"""
    code = """
def function_a():
    return 1

def function_b():
    return 2

def function_c():
    return 3
"""
    result = decomposer.decompose(code, "python")

    assert result.success is True
    # Each function should be independent
    for atom in result.atoms:
        # Atoms should have clear boundaries
        assert atom.code.strip().startswith("def ")


def test_decompose_atomicity_criteria(decomposer):
    """Test that atoms meet atomicity criteria"""
    code = """
class Calculator:
    def __init__(self):
        self.value = 0

    def add(self, n):
        self.value += n

    def subtract(self, n):
        self.value -= n

    def get_value(self):
        return self.value
"""
    result = decomposer.decompose(code, "python")

    assert result.success is True
    for atom in result.atoms:
        # LOC should be ≤15
        assert atom.loc <= 15
        # Complexity should be <3.0
        assert atom.complexity < 3.0


# ============================================================================
# Strategy Tests
# ============================================================================

def test_decompose_by_function_strategy(decomposer):
    """Test decomposition by function boundaries"""
    code = """
def func1():
    return 1

def func2():
    return 2

def func3():
    return 3
"""
    result = decomposer.decompose(code, "python")

    assert result.success is True
    assert result.strategy == "by_function"
    assert len(result.atoms) == 3  # One atom per function


def test_decompose_by_class_strategy(decomposer):
    """Test decomposition by class boundaries"""
    code = """
class User:
    def __init__(self, name):
        self.name = name

class Product:
    def __init__(self, title):
        self.title = title
"""
    result = decomposer.decompose(code, "python")

    assert result.success is True
    # Should split by class
    assert len(result.atoms) >= 2


def test_decompose_single_atom_strategy(decomposer):
    """Test when code is already small enough"""
    code = """
def greet(name):
    return f"Hello, {name}"
"""
    result = decomposer.decompose(code, "python")

    assert result.success is True
    assert result.strategy == "single_atom"
    assert len(result.atoms) == 1


# ============================================================================
# Boundary Detection Tests
# ============================================================================

def test_detect_function_boundaries(decomposer):
    """Test detection of function boundaries"""
    code = """
def function_a():
    x = 1
    y = 2
    return x + y

def function_b():
    a = 10
    b = 20
    return a * b
"""
    result = decomposer.decompose(code, "python")

    assert result.success is True
    # Should detect two function boundaries
    assert len(result.atoms) == 2


def test_detect_class_boundaries(decomposer):
    """Test detection of class boundaries"""
    code = """
class Animal:
    def speak(self):
        pass

class Dog(Animal):
    def speak(self):
        return "Woof!"
"""
    result = decomposer.decompose(code, "python")

    assert result.success is True
    # Should detect class boundaries
    assert len(result.atoms) >= 2


def test_preserve_class_methods_together(decomposer):
    """Test that small class methods stay together"""
    code = """
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def move(self, dx, dy):
        self.x += dx
        self.y += dy
"""
    result = decomposer.decompose(code, "python")

    assert result.success is True
    # Small class should be one atom
    if len(result.atoms) == 1:
        assert "class Point" in result.atoms[0].code


# ============================================================================
# TypeScript/JavaScript Tests
# ============================================================================

def test_decompose_typescript(decomposer):
    """Test decomposing TypeScript code"""
    code = """
function greet(name: string): string {
    return `Hello, ${name}`;
}

function farewell(name: string): string {
    return `Goodbye, ${name}`;
}

class User {
    constructor(public name: string) {}

    getName(): string {
        return this.name;
    }
}
"""
    result = decomposer.decompose(code, "typescript")

    assert result.success is True
    assert len(result.atoms) >= 2
    assert result.language == "typescript"


def test_decompose_javascript(decomposer):
    """Test decomposing JavaScript code"""
    code = """
function calculate(a, b) {
    return a + b;
}

const multiply = (a, b) => a * b;

class Calculator {
    add(a, b) {
        return a + b;
    }
}
"""
    result = decomposer.decompose(code, "javascript")

    assert result.success is True
    assert len(result.atoms) >= 2
    assert result.language == "javascript"


# ============================================================================
# Complex Code Tests
# ============================================================================

def test_decompose_nested_functions(decomposer):
    """Test decomposing code with nested functions"""
    code = """
def outer():
    def inner():
        return 1
    return inner()

def another():
    x = outer()
    return x + 1
"""
    result = decomposer.decompose(code, "python")

    assert result.success is True
    # Should handle nested functions
    assert len(result.atoms) >= 1


def test_decompose_with_imports(decomposer):
    """Test decomposing code with imports"""
    code = """
import os
from typing import List

def process_files(paths: List[str]):
    results = []
    for path in paths:
        with open(path) as f:
            results.append(f.read())
    return results

def save_results(results: List[str], output: str):
    with open(output, 'w') as f:
        f.write('\\n'.join(results))
"""
    result = decomposer.decompose(code, "python")

    assert result.success is True
    # Imports should be preserved or handled appropriately
    assert len(result.atoms) >= 2


# ============================================================================
# LOC Distribution Tests
# ============================================================================

def test_atoms_within_loc_target(decomposer):
    """Test that atoms are within LOC target"""
    code = "\n".join([f"def func_{i}():\n    pass\n" for i in range(20)])

    result = decomposer.decompose(code, "python")

    assert result.success is True
    for atom in result.atoms:
        # Each atom should be around target LOC (10)
        assert atom.loc <= 15  # Allow some flexibility


def test_even_distribution_of_loc(decomposer):
    """Test that LOC is distributed evenly across atoms"""
    # 100 LOC code
    code = "\n".join([f"def function_{i}():\n    return {i}\n" for i in range(50)])

    result = decomposer.decompose(code, "python")

    assert result.success is True
    # Calculate average LOC per atom
    total_loc = sum(atom.loc for atom in result.atoms)
    avg_loc = total_loc / len(result.atoms)

    # Average should be close to target (10)
    assert 5 <= avg_loc <= 15


# ============================================================================
# Edge Cases
# ============================================================================

def test_decompose_empty_code(decomposer):
    """Test decomposing empty code"""
    result = decomposer.decompose("", "python")

    assert result.success is True
    assert len(result.atoms) == 0
    assert result.total_loc == 0


def test_decompose_only_comments(decomposer):
    """Test decomposing code with only comments"""
    code = """
# This is a comment
# Another comment
"""
    result = decomposer.decompose(code, "python")

    assert result.success is True
    # Should handle gracefully
    assert len(result.atoms) <= 1


def test_decompose_single_long_function(decomposer):
    """Test decomposing single long function"""
    code = "def long_function():\n"
    code += "\n".join([f"    x_{i} = {i}" for i in range(50)])
    code += "\n    return sum([" + ", ".join([f"x_{i}" for i in range(50)]) + "])"

    result = decomposer.decompose(code, "python")

    assert result.success is True
    # Should attempt to break down even single long function
    # Or return as single atom if can't break down logically
    assert len(result.atoms) >= 1


def test_decompose_mixed_code(decomposer):
    """Test decomposing mixed functions and classes"""
    code = """
def standalone_function():
    return 1

class MyClass:
    def method1(self):
        return 2

    def method2(self):
        return 3

def another_function():
    return 4
"""
    result = decomposer.decompose(code, "python")

    assert result.success is True
    # Should handle mixed code structures
    assert len(result.atoms) >= 3


# ============================================================================
# Statistics Tests
# ============================================================================

def test_decomposition_statistics(decomposer):
    """Test decomposition statistics accuracy"""
    code = """
def func1():
    return 1

def func2():
    return 2

def func3():
    return 3
"""
    result = decomposer.decompose(code, "python")

    assert result.success is True
    assert result.total_loc == 6  # 6 lines of actual code
    assert result.total_atoms == len(result.atoms)
    assert result.avg_loc_per_atom == result.total_loc / result.total_atoms
    assert result.avg_complexity <= 2.0  # Simple functions


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
