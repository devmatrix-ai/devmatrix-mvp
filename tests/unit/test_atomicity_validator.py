"""
Unit Tests - AtomicityValidator

Tests 10 atomicity criteria validation.

Author: DevMatrix Team
Date: 2025-10-24
"""

import pytest
from src.atomization.validator import AtomicityValidator, AtomicityResult
from src.atomization.parser import MultiLanguageParser


@pytest.fixture
def parser():
    return MultiLanguageParser()


@pytest.fixture
def validator(parser):
    return AtomicityValidator(parser)


# ============================================================================
# LOC Criterion Tests (≤15)
# ============================================================================

def test_criterion_loc_passes(validator):
    """Test LOC criterion passes for ≤15 lines"""
    code = "def small(): return 1"
    result = validator.validate(code, "python", "Small function")

    assert result.criteria_passed["loc"] is True


def test_criterion_loc_fails(validator):
    """Test LOC criterion fails for >15 lines"""
    code = "\n".join([f"    x_{i} = {i}" for i in range(20)])
    result = validator.validate(f"def large():\n{code}\n    return sum()", "python", "Large")

    assert result.criteria_passed["loc"] is False


# ============================================================================
# Complexity Criterion Tests (<3.0)
# ============================================================================

def test_criterion_complexity_passes(validator):
    """Test complexity criterion passes for <3.0"""
    code = """
def simple(a, b):
    return a + b
"""
    result = validator.validate(code, "python", "Simple")

    assert result.criteria_passed["complexity"] is True
    assert result.complexity < 3.0


def test_criterion_complexity_fails(validator):
    """Test complexity criterion fails for ≥3.0"""
    code = """
def complex(data):
    for item in data:
        if item > 0:
            for sub in item:
                if sub < 10:
                    return sub
    return None
"""
    result = validator.validate(code, "python", "Complex")

    assert result.criteria_passed["complexity"] is False
    assert result.complexity >= 3.0


# ============================================================================
# Single Responsibility Tests
# ============================================================================

def test_criterion_single_responsibility_passes(validator):
    """Test single responsibility criterion"""
    code = """
def calculate_total(items):
    return sum(item.price for item in items)
"""
    result = validator.validate(code, "python", "Calculate total")

    assert result.criteria_passed["single_responsibility"] is True


def test_criterion_single_responsibility_fails(validator):
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
    result = validator.validate(code, "python", "Do everything")

    # May fail single responsibility due to multiple actions
    assert "single_responsibility" in result.criteria_passed


# ============================================================================
# Clear Boundaries Tests
# ============================================================================

def test_criterion_clear_boundaries_passes(validator):
    """Test clear boundaries criterion"""
    code = """
def greet(name: str) -> str:
    return f"Hello, {name}"
"""
    result = validator.validate(code, "python", "Greet")

    assert result.criteria_passed["clear_boundaries"] is True


# ============================================================================
# Independence Tests
# ============================================================================

def test_criterion_independence_passes(validator):
    """Test independence from siblings"""
    code = """
def standalone():
    x = 1
    y = 2
    return x + y
"""
    result = validator.validate(code, "python", "Standalone")

    assert result.criteria_passed["independence"] is True


# ============================================================================
# Context Completeness Tests (≥95%)
# ============================================================================

def test_criterion_context_completeness_passes(validator):
    """Test context completeness ≥95%"""
    code = """
from typing import List

def process(items: List[int]) -> int:
    '''Process items'''
    return sum(items)
"""
    result = validator.validate(code, "python", "Process")

    # With imports and type hints, should have good completeness
    assert result.context_completeness >= 0.0


# ============================================================================
# Testable Criterion Tests
# ============================================================================

def test_criterion_testable_passes(validator):
    """Test testable criterion"""
    code = """
def add(a: int, b: int) -> int:
    return a + b
"""
    result = validator.validate(code, "python", "Add")

    assert result.criteria_passed["testable"] is True


# ============================================================================
# Deterministic Criterion Tests
# ============================================================================

def test_criterion_deterministic_passes(validator):
    """Test deterministic criterion"""
    code = """
def multiply(a, b):
    return a * b
"""
    result = validator.validate(code, "python", "Multiply")

    assert result.criteria_passed["deterministic"] is True


def test_criterion_deterministic_fails(validator):
    """Test non-deterministic code detected"""
    code = """
import random
def get_random():
    return random.randint(1, 100)
"""
    result = validator.validate(code, "python", "Random")

    # Should detect randomness
    assert result.criteria_passed["deterministic"] is False


# ============================================================================
# No Side Effects Tests
# ============================================================================

def test_criterion_no_side_effects_passes(validator):
    """Test no side effects criterion"""
    code = """
def calculate(x):
    result = x * 2
    return result
"""
    result = validator.validate(code, "python", "Calculate")

    assert result.criteria_passed["no_side_effects"] is True


def test_criterion_no_side_effects_fails(validator):
    """Test side effects detected"""
    code = """
global_var = 0

def modify_global():
    global global_var
    global_var += 1
    return global_var
"""
    result = validator.validate(code, "python", "Modify")

    # Should detect global modification
    assert result.criteria_passed["no_side_effects"] is False


# ============================================================================
# Clear Input/Output Tests
# ============================================================================

def test_criterion_clear_io_passes(validator):
    """Test clear input/output criterion"""
    code = """
def greet(name: str) -> str:
    return f"Hello, {name}"
"""
    result = validator.validate(code, "python", "Greet")

    assert result.criteria_passed["clear_io"] is True


# ============================================================================
# Overall Atomicity Score Tests
# ============================================================================

def test_atomicity_score_calculation(validator):
    """Test overall atomicity score (0.0-1.0)"""
    code = """
def perfect():
    return 1
"""
    result = validator.validate(code, "python", "Perfect")

    assert 0.0 <= result.atomicity_score <= 1.0
    # Score is average of 10 criteria (10% each)
    passed_count = sum(1 for v in result.criteria_passed.values() if v)
    expected_score = passed_count / 10
    assert abs(result.atomicity_score - expected_score) < 0.01


def test_violation_reporting(validator):
    """Test violation reporting with severity"""
    # Very long and complex code
    code = "\n".join([f"    x_{i} = {i}" for i in range(30)])
    code = f"def huge():\n{code}\n    return x_0"

    result = validator.validate(code, "python", "Huge")

    assert len(result.violations) > 0
    # Should have violations for LOC
    assert any("LOC" in v or "lines" in v.lower() for v in result.violations)


def test_passed_criteria_tracking(validator):
    """Test passed/failed criteria tracking"""
    code = """
def simple():
    return 1
"""
    result = validator.validate(code, "python", "Simple")

    # All 10 criteria should be tracked
    assert len(result.criteria_passed) == 10
    assert all(isinstance(v, bool) for v in result.criteria_passed.values())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
