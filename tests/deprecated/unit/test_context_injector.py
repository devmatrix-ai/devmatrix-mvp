"""
Unit Tests - ContextInjector

Tests context completeness scoring and metadata extraction.

Author: DevMatrix Team
Date: 2025-10-24
"""

import pytest
from src.atomization.context_injector import ContextInjector, AtomContext
from src.atomization.parser import MultiLanguageParser


@pytest.fixture
def parser():
    return MultiLanguageParser()


@pytest.fixture
def injector(parser):
    return ContextInjector(parser)


# ============================================================================
# Context Completeness Tests
# ============================================================================

def test_context_completeness_95_percent(injector):
    """Test context completeness ≥95%"""
    code = """
from typing import List

def calculate_total(items: List[dict]) -> float:
    '''Calculate total price from items'''
    total = 0.0
    for item in items:
        total += item['price']
    return total
"""
    context = injector.inject_context(code, "python", "Calculate total")

    assert context.completeness_score >= 0.95
    assert len(context.imports) > 0
    assert len(context.type_hints) > 0


def test_all_required_fields_populated(injector):
    """Test that all required fields are populated"""
    code = """
def greet(name: str) -> str:
    return f"Hello, {name}"
"""
    context = injector.inject_context(code, "python", "Greet function")

    assert context.imports is not None
    assert context.type_hints is not None
    assert context.preconditions is not None
    assert context.postconditions is not None
    assert context.test_cases is not None


def test_type_information_accurate(injector):
    """Test type information extraction"""
    code = """
def process(data: dict, count: int) -> List[str]:
    results: List[str] = []
    return results
"""
    context = injector.inject_context(code, "python", "Process data")

    assert "dict" in str(context.type_hints)
    assert "int" in str(context.type_hints)


# ============================================================================
# Import Extraction Tests
# ============================================================================

def test_extract_python_imports(injector):
    """Test Python import extraction"""
    code = """
import os
from typing import List, Dict
from datetime import datetime

def process(): pass
"""
    context = injector.inject_context(code, "python", "Test")

    assert "os" in context.imports
    assert any("typing" in imp or "List" in imp for imp in context.imports)


def test_extract_typescript_imports(injector):
    """Test TypeScript import extraction"""
    code = """
import express from 'express';
import { Router } from 'express';

function handler() {}
"""
    context = injector.inject_context(code, "typescript", "Test")

    assert any("express" in imp for imp in context.imports)


# ============================================================================
# Type Schema Tests
# ============================================================================

def test_infer_python_type_hints(injector):
    """Test Python type hint inference"""
    code = """
def calculate(a: int, b: float) -> float:
    return a + b
"""
    context = injector.inject_context(code, "python", "Calculate")

    assert len(context.type_hints) > 0
    assert any("int" in str(hint) for hint in context.type_hints.values())


def test_infer_typescript_interfaces(injector):
    """Test TypeScript interface inference"""
    code = """
interface User {
    id: number;
    name: string;
}

function getUser(id: number): User {
    return { id, name: "test" };
}
"""
    context = injector.inject_context(code, "typescript", "Get user")

    assert len(context.type_hints) > 0


# ============================================================================
# Pre/Postcondition Tests
# ============================================================================

def test_extract_preconditions(injector):
    """Test precondition extraction"""
    code = """
def divide(a: float, b: float) -> float:
    # Precondition: b != 0
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
"""
    context = injector.inject_context(code, "python", "Divide")

    assert len(context.preconditions) > 0
    assert any("b" in pre or "zero" in pre.lower() for pre in context.preconditions)


def test_extract_postconditions(injector):
    """Test postcondition extraction"""
    code = """
def get_positive(n: int) -> int:
    result = abs(n)
    # Postcondition: result >= 0
    return result
"""
    context = injector.inject_context(code, "python", "Get positive")

    assert len(context.postconditions) > 0


# ============================================================================
# Test Case Generation Tests
# ============================================================================

def test_generate_test_cases(injector):
    """Test case generation"""
    code = """
def add(a: int, b: int) -> int:
    return a + b
"""
    context = injector.inject_context(code, "python", "Add function")

    assert len(context.test_cases) > 0
    # Should generate basic test cases
    assert any("add" in test.lower() for test in context.test_cases)


# ============================================================================
# Dependency Hints Tests
# ============================================================================

def test_extract_dependency_hints(injector):
    """Test dependency hint extraction"""
    code = """
def process_user(user_id: int):
    user = get_user(user_id)  # Depends on get_user
    return user
"""
    context = injector.inject_context(code, "python", "Process user")

    assert len(context.dependency_hints) > 0
    assert any("get_user" in hint for hint in context.dependency_hints)


# ============================================================================
# Completeness Scoring Tests
# ============================================================================

def test_completeness_score_components(injector):
    """Test that completeness score uses all 5 components"""
    # Code with all components
    complete_code = """
from typing import List

def calculate(items: List[int]) -> int:
    '''Calculate sum'''
    # Precondition: items not empty
    total = sum(items)
    # Postcondition: total >= 0
    return total
"""
    context = injector.inject_context(complete_code, "python", "Calculate")

    # Score should be high with all components present
    assert context.completeness_score >= 0.8

    # Incomplete code
    incomplete_code = "def f(): pass"
    incomplete_context = injector.inject_context(incomplete_code, "python", "F")

    # Score should be lower
    assert incomplete_context.completeness_score < context.completeness_score


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
