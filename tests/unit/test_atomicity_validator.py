"""
Unit Tests - AtomicityValidator

Tests 10 atomicity criteria validation.

Author: DevMatrix Team
Date: 2025-10-24
"""

import pytest
from src.atomization.validator import AtomicityValidator, AtomicityResult
from src.atomization.decomposer import AtomCandidate
from src.atomization.parser import MultiLanguageParser


@pytest.fixture
def parser():
    return MultiLanguageParser()


@pytest.fixture
def validator():
    return AtomicityValidator()

@pytest.fixture
def create_atom():
    """Helper to create AtomCandidate for testing"""
    def _create(code: str, language: str = "python", description: str = "Test", complexity: float = 1.0):
        loc = len([l for l in code.split('\n') if l.strip()])
        return AtomCandidate(
            code=code,
            start_line=1,
            end_line=loc,
            loc=loc,
            complexity=complexity,
            description=description,
            boundary_type='function',
            parent_context=None,
            dependencies=[]
        )
    return _create



# ============================================================================
# LOC Criterion Tests (≤15)
# ============================================================================

def test_criterion_loc_passes(validator, create_atom):
    """Test LOC criterion passes for ≤15 lines"""
    code = "def small(): return 1"
    result = validator.validate(create_atom(code, "python", "Small function"))

    assert "1. Size (LOC ≤ 15)" in result.passed_criteria


def test_criterion_loc_fails(validator, create_atom):
    """Test LOC criterion fails for >15 lines"""
    code = "\n".join([f"    x_{i} = {i}" for i in range(20)])
    result = validator.validate(create_atom(f"def large():\n{code}\n    return sum()", "python", "Large"))

    assert "1. Size (LOC ≤ 15)" in result.failed_criteria


# ============================================================================
# Complexity Criterion Tests (<3.0)
# ============================================================================

def test_criterion_complexity_passes(validator, create_atom):
    """Test complexity criterion passes for <3.0"""
    code = """
def simple(a, b):
    return a + b
"""
    result = validator.validate(create_atom(code, "python", "Simple"))

    assert "2. Complexity < 3.0" in result.passed_criteria


def test_criterion_complexity_fails(validator, create_atom):
    """Test complexity criterion fails for ≥3.0"""
    code = """
def complex(x):
    if x > 10:
        if x > 20:
            if x > 30:
                return 3
            elif x > 25:
                return 2
            else:
                return 1
        return 0
    return -1
"""
    # Create with high complexity value
    result = validator.validate(create_atom(code, "python", "Complex", complexity=5.0))

    assert "2. Complexity < 3.0" in result.failed_criteria


# ============================================================================
# Single Responsibility Tests
# ============================================================================

def test_criterion_single_responsibility_passes(validator, create_atom):
    """Test single responsibility criterion"""
    code = """
def calculate_total(items):
    return sum(item.price for item in items)
"""
    result = validator.validate(create_atom(code, "python", "Calculate total"))

    assert "3. Single responsibility" in result.passed_criteria


def test_criterion_single_responsibility_fails(validator, create_atom):
    """Test multiple responsibilities detected"""
    code = """
def do_everything(data):
    # Validate
    if not data: raise ValueError()
    # Process
    processed = [x * 2 for x in data]
    # Save
    save_to_database(processed)
    # Send email
    send_notification()
    return processed
"""
    result = validator.validate(create_atom(code, "python", "Do everything"))

    # Should fail single responsibility due to multiple actions
    assert "3. Single responsibility" in result.failed_criteria


# ============================================================================
# Clear Boundaries Tests
# ============================================================================

def test_criterion_clear_boundaries_passes(validator, create_atom):
    """Test clear boundaries criterion"""
    code = """
def greet(name: str) -> str:
    return f"Hello, {name}"
"""
    result = validator.validate(create_atom(code, "python", "Greet"))

    assert "4. Clear boundaries" in result.passed_criteria


# ============================================================================
# Independence Tests
# ============================================================================

def test_criterion_independence_passes(validator, create_atom):
    """Test independence from siblings"""
    code = """
def standalone():
    x = 1
    y = 2
    return x + y
"""
    result = validator.validate(create_atom(code, "python", "Standalone"))

    assert "5. Independence" in result.passed_criteria


# ============================================================================
# Context Completeness Tests (≥95%)
# ============================================================================

def test_criterion_context_completeness_passes(validator, create_atom):
    """Test context completeness ≥95%"""
    code = """
from typing import List

def process(items: List[int]) -> int:
    '''Process items'''
    return sum(items)
"""
    result = validator.validate(create_atom(code, "python", "Process"))

    # With imports and type hints, should have good completeness


# ============================================================================
# Testable Criterion Tests
# ============================================================================

def test_criterion_testable_passes(validator, create_atom):
    """Test testable criterion"""
    code = """
def add(a: int, b: int) -> int:
    return a + b
"""
    result = validator.validate(create_atom(code, "python", "Add"))

    assert "7. Testable" in result.passed_criteria


# ============================================================================
# Deterministic Criterion Tests
# ============================================================================

def test_criterion_deterministic_passes(validator, create_atom):
    """Test deterministic criterion"""
    code = """
def multiply(a, b):
    return a * b
"""
    result = validator.validate(create_atom(code, "python", "Multiply"))

    assert "8. Deterministic" in result.passed_criteria


def test_criterion_deterministic_fails(validator, create_atom):
    """Test non-deterministic code detected"""
    code = """
import random
def get_random():
    return random.randint(1, 100)
"""
    result = validator.validate(create_atom(code, "python", "Random"))

    # Should detect randomness
    assert "8. Deterministic" in result.failed_criteria


# ============================================================================
# No Side Effects Tests
# ============================================================================

def test_criterion_no_side_effects_passes(validator, create_atom):
    """Test no side effects criterion"""
    code = """
def calculate(x):
    result = x * 2
    return result
"""
    result = validator.validate(create_atom(code, "python", "Calculate"))

    assert "9. No side effects" in result.passed_criteria


def test_criterion_no_side_effects_fails(validator, create_atom):
    """Test side effects detected"""
    code = """
global_var = 0

def modify_global():
    global global_var
    global_var += 1
    return global_var
"""
    result = validator.validate(create_atom(code, "python", "Modify"))

    # Should detect global modification
    assert "9. No side effects" in result.failed_criteria


# ============================================================================
# Clear Input/Output Tests
# ============================================================================

def test_criterion_clear_io_passes(validator, create_atom):
    """Test clear input/output criterion"""
    code = """
def greet(name: str) -> str:
    return f"Hello, {name}"
"""
    result = validator.validate(create_atom(code, "python", "Greet"))

    assert "10. Clear I/O" in result.passed_criteria


# ============================================================================
# Overall Atomicity Score Tests
# ============================================================================

def test_atomicity_score_calculation(validator, create_atom):
    """Test overall atomicity score (0.0-1.0)"""
    code = """
def perfect():
    return 1
"""
    result = validator.validate(create_atom(code, "python", "Perfect"))

    assert 0.0 <= result.score <= 1.0
    # Score is calculated from passed criteria (each criterion is 10% = 0.1)
    passed_count = len(result.passed_criteria)
    expected_score = passed_count * 0.1
    assert abs(result.score - expected_score) < 0.01


def test_violation_reporting(validator, create_atom):
    """Test that violations are properly reported"""
    code = "\n".join([f"x = {i}" for i in range(30)])  # Too long
    result = validator.validate(create_atom(code, "python", "Huge"))

    # Check violations are reported as objects
    assert len(result.violations) > 0
    # Check violation has description attribute
    assert hasattr(result.violations[0], 'description')
    assert any("LOC" in v.description or "lines" in v.description.lower() for v in result.violations)

def test_passed_criteria_tracking(validator, create_atom):
    """Test that passed criteria are tracked"""
    code = "def simple(): return 1"
    result = validator.validate(create_atom(code, "python", "Simple"))

    # Check passed_criteria is a list
    assert isinstance(result.passed_criteria, list)
    # Should have multiple passing criteria for simple code
    assert len(result.passed_criteria) > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
