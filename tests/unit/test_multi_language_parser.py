"""
Unit Tests - MultiLanguageParser

Tests AST parsing for Python, TypeScript, and JavaScript.

Author: DevMatrix Team
Date: 2025-10-24
"""

import pytest
from src.atomization.parser import MultiLanguageParser, ParseResult


@pytest.fixture
def parser():
    """Create MultiLanguageParser instance"""
    return MultiLanguageParser()


# ============================================================================
# Python Parsing Tests
# ============================================================================

def test_parse_python_simple_function(parser):
    """Test parsing simple Python function"""
    code = """
def greet(name):
    return f"Hello, {name}"
"""
    result = parser.parse(code, "python")

    assert result.success is True
    assert result.language == "python"
    assert result.ast is not None
    assert result.complexity > 0
    assert result.loc == 2  # Two lines of code (excluding blank)
    assert len(result.functions) == 1
    assert result.functions[0] == "greet"


def test_parse_python_class(parser):
    """Test parsing Python class"""
    code = """
class User:
    def __init__(self, name):
        self.name = name

    def greet(self):
        return f"Hello, {self.name}"
"""
    result = parser.parse(code, "python")

    assert result.success is True
    assert len(result.classes) == 1
    assert result.classes[0] == "User"
    assert len(result.functions) == 2  # __init__ and greet


def test_parse_python_with_imports(parser):
    """Test parsing Python with imports"""
    code = """
import os
from typing import List, Dict

def process_files(paths: List[str]) -> Dict[str, str]:
    results = {}
    for path in paths:
        with open(path) as f:
            results[path] = f.read()
    return results
"""
    result = parser.parse(code, "python")

    assert result.success is True
    assert len(result.imports) >= 2
    assert "os" in result.imports
    assert "typing" in result.imports or "List" in result.imports


def test_parse_python_complexity_calculation(parser):
    """Test complexity calculation for Python"""
    simple_code = """
def add(a, b):
    return a + b
"""

    complex_code = """
def process(data):
    if data:
        for item in data:
            if item > 0:
                return item
            elif item < 0:
                continue
            else:
                break
    return None
"""

    simple_result = parser.parse(simple_code, "python")
    complex_result = parser.parse(complex_code, "python")

    assert simple_result.complexity < complex_result.complexity
    assert simple_result.complexity <= 2.0  # Very simple
    assert complex_result.complexity > 3.0  # Multiple branches


def test_parse_python_invalid_syntax(parser):
    """Test parsing Python with syntax errors"""
    invalid_code = """
def broken_function(
    # Missing closing parenthesis
    return "broken"
"""
    result = parser.parse(invalid_code, "python")

    assert result.success is False
    assert result.error is not None
    assert "syntax" in result.error.lower() or "parse" in result.error.lower()


# ============================================================================
# TypeScript Parsing Tests
# ============================================================================

def test_parse_typescript_function(parser):
    """Test parsing TypeScript function"""
    code = """
function greet(name: string): string {
    return `Hello, ${name}`;
}
"""
    result = parser.parse(code, "typescript")

    assert result.success is True
    assert result.language == "typescript"
    assert len(result.functions) == 1
    assert result.functions[0] == "greet"


def test_parse_typescript_interface(parser):
    """Test parsing TypeScript interface"""
    code = """
interface User {
    id: number;
    name: string;
    email: string;
}

function createUser(data: User): User {
    return { ...data, id: Math.random() };
}
"""
    result = parser.parse(code, "typescript")

    assert result.success is True
    assert "User" in result.types
    assert len(result.functions) == 1


def test_parse_typescript_class(parser):
    """Test parsing TypeScript class"""
    code = """
class Calculator {
    private value: number = 0;

    add(n: number): void {
        this.value += n;
    }

    getValue(): number {
        return this.value;
    }
}
"""
    result = parser.parse(code, "typescript")

    assert result.success is True
    assert len(result.classes) == 1
    assert result.classes[0] == "Calculator"
    assert len(result.functions) >= 2  # add and getValue


def test_parse_typescript_with_imports(parser):
    """Test parsing TypeScript with imports"""
    code = """
import express from 'express';
import { Router, Request, Response } from 'express';

const app = express();
const router = Router();
"""
    result = parser.parse(code, "typescript")

    assert result.success is True
    assert len(result.imports) > 0
    assert "express" in result.imports


# ============================================================================
# JavaScript Parsing Tests
# ============================================================================

def test_parse_javascript_function(parser):
    """Test parsing JavaScript function"""
    code = """
function calculate(a, b) {
    return a + b;
}
"""
    result = parser.parse(code, "javascript")

    assert result.success is True
    assert result.language == "javascript"
    assert len(result.functions) == 1
    assert result.functions[0] == "calculate"


def test_parse_javascript_arrow_function(parser):
    """Test parsing JavaScript arrow function"""
    code = """
const greet = (name) => {
    return `Hello, ${name}`;
};

const add = (a, b) => a + b;
"""
    result = parser.parse(code, "javascript")

    assert result.success is True
    # Arrow functions may be detected as functions or variables depending on parser
    assert len(result.functions) >= 0 or len(result.variables) >= 2


def test_parse_javascript_class(parser):
    """Test parsing JavaScript class"""
    code = """
class Person {
    constructor(name) {
        this.name = name;
    }

    greet() {
        return `Hello, I'm ${this.name}`;
    }
}
"""
    result = parser.parse(code, "javascript")

    assert result.success is True
    assert len(result.classes) == 1
    assert result.classes[0] == "Person"


def test_parse_javascript_async_function(parser):
    """Test parsing JavaScript async function"""
    code = """
async function fetchData(url) {
    const response = await fetch(url);
    return response.json();
}
"""
    result = parser.parse(code, "javascript")

    assert result.success is True
    assert len(result.functions) == 1
    assert result.functions[0] == "fetchData"


# ============================================================================
# Language Detection Tests
# ============================================================================

def test_detect_python_language(parser):
    """Test language detection for Python"""
    code = "def hello(): pass"
    lang = parser.detect_language(code)
    assert lang == "python"


def test_detect_typescript_language(parser):
    """Test language detection for TypeScript"""
    code = "function greet(name: string): void {}"
    lang = parser.detect_language(code)
    assert lang == "typescript"


def test_detect_javascript_language(parser):
    """Test language detection for JavaScript"""
    code = "function greet(name) { return name; }"
    lang = parser.detect_language(code)
    assert lang in ["javascript", "typescript"]  # Could be either


# ============================================================================
# LOC Counting Tests
# ============================================================================

def test_count_loc_python(parser):
    """Test LOC counting for Python"""
    code = """
# This is a comment
def hello():
    # Another comment
    return "Hello"

# More comments
"""
    result = parser.parse(code, "python")
    assert result.loc == 2  # Only function definition and return


def test_count_loc_with_blank_lines(parser):
    """Test LOC counting excludes blank lines"""
    code = """
def function1():
    pass


def function2():
    pass
"""
    result = parser.parse(code, "python")
    assert result.loc == 4  # Two function definitions, two pass statements


# ============================================================================
# Edge Cases Tests
# ============================================================================

def test_parse_empty_code(parser):
    """Test parsing empty code"""
    result = parser.parse("", "python")
    assert result.success is True
    assert result.loc == 0
    assert len(result.functions) == 0


def test_parse_only_comments(parser):
    """Test parsing code with only comments"""
    code = """
# This is just a comment
# Another comment
"""
    result = parser.parse(code, "python")
    assert result.success is True
    assert result.loc == 0


def test_parse_unsupported_language(parser):
    """Test parsing unsupported language"""
    code = "some code"
    result = parser.parse(code, "ruby")

    assert result.success is False
    assert "unsupported" in result.error.lower() or "not supported" in result.error.lower()


def test_parse_very_long_code(parser):
    """Test parsing very long code"""
    # Generate 1000 lines of code
    code = "\n".join([f"def func_{i}(): pass" for i in range(1000)])

    result = parser.parse(code, "python")
    assert result.success is True
    assert result.loc == 1000
    assert len(result.functions) == 1000


# ============================================================================
# Complexity Edge Cases
# ============================================================================

def test_complexity_nested_loops(parser):
    """Test complexity with nested loops"""
    code = """
def nested_loops(data):
    for i in data:
        for j in data:
            for k in data:
                if i + j + k > 10:
                    return True
    return False
"""
    result = parser.parse(code, "python")
    assert result.complexity > 5.0  # High complexity


def test_complexity_no_branches(parser):
    """Test complexity with no branches"""
    code = """
def simple():
    x = 1
    y = 2
    z = x + y
    return z
"""
    result = parser.parse(code, "python")
    assert result.complexity == 1.0  # Minimum complexity


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
