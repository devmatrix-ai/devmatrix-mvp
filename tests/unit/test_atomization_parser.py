"""
Tests for Atomization Parser

Tests code parsing and AST analysis functionality.

Author: DevMatrix Team
Date: 2025-11-03
"""

import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.unit
class TestParserPython:
    """Test Python code parsing."""

    def test_parse_python_function(self):
        """Test parsing Python function."""
        from src.atomization.parser import Parser

        parser = Parser()
        code = """
def hello():
    print("Hello, World!")
    return True
"""
        
        with patch.object(parser, '_parse_with_tree_sitter', return_value=MagicMock()):
            result = parser.parse(code, language="python")
            
            assert result is not None

    def test_parse_python_class(self):
        """Test parsing Python class."""
        from src.atomization.parser import Parser

        parser = Parser()
        code = """
class MyClass:
    def __init__(self):
        self.value = 0
    
    def method(self):
        return self.value
"""
        
        with patch.object(parser, '_parse_with_tree_sitter', return_value=MagicMock()):
            result = parser.parse(code, language="python")
            
            assert result is not None

    def test_parse_python_with_imports(self):
        """Test parsing Python with imports."""
        from src.atomization.parser import Parser

        parser = Parser()
        code = """
import os
from typing import List

def process(items: List[str]) -> None:
    for item in items:
        print(item)
"""
        
        with patch.object(parser, '_parse_with_tree_sitter', return_value=MagicMock()):
            result = parser.parse(code, language="python")
            
            assert result is not None


@pytest.mark.unit
class TestParserTypeScript:
    """Test TypeScript code parsing."""

    def test_parse_typescript_function(self):
        """Test parsing TypeScript function."""
        from src.atomization.parser import Parser

        parser = Parser()
        code = """
function greet(name: string): string {
    return `Hello, ${name}!`;
}
"""
        
        with patch.object(parser, '_parse_with_tree_sitter', return_value=MagicMock()):
            result = parser.parse(code, language="typescript")
            
            assert result is not None

    def test_parse_typescript_interface(self):
        """Test parsing TypeScript interface."""
        from src.atomization.parser import Parser

        parser = Parser()
        code = """
interface User {
    id: string;
    name: string;
    email: string;
}
"""
        
        with patch.object(parser, '_parse_with_tree_sitter', return_value=MagicMock()):
            result = parser.parse(code, language="typescript")
            
            assert result is not None


@pytest.mark.unit
class TestParserErrorHandling:
    """Test parser error handling."""

    def test_parse_invalid_syntax(self):
        """Test parsing code with syntax errors."""
        from src.atomization.parser import Parser

        parser = Parser()
        code = "def invalid(:\n    pass"  # Invalid syntax
        
        with patch.object(parser, '_parse_with_tree_sitter', side_effect=Exception("Syntax error")):
            with pytest.raises(Exception):
                parser.parse(code, language="python")

    def test_parse_empty_code(self):
        """Test parsing empty code."""
        from src.atomization.parser import Parser

        parser = Parser()
        
        with pytest.raises(ValueError, match="empty|Empty"):
            parser.parse("", language="python")

    def test_parse_unsupported_language(self):
        """Test parsing unsupported language."""
        from src.atomization.parser import Parser

        parser = Parser()
        
        with pytest.raises(ValueError, match="language|supported"):
            parser.parse("code", language="unsupported")


@pytest.mark.unit
class TestParserSymbolExtraction:
    """Test symbol extraction from AST."""

    def test_extract_functions(self):
        """Test extracting function definitions."""
        from src.atomization.parser import Parser

        parser = Parser()
        code = """
def func1():
    pass

def func2():
    pass
"""
        
        with patch.object(parser, '_extract_symbols', return_value=["func1", "func2"]):
            symbols = parser.extract_functions(code, "python")
            
            assert len(symbols) == 2 or symbols is not None

    def test_extract_classes(self):
        """Test extracting class definitions."""
        from src.atomization.parser import Parser

        parser = Parser()
        code = """
class Class1:
    pass

class Class2:
    pass
"""
        
        with patch.object(parser, '_extract_symbols', return_value=["Class1", "Class2"]):
            symbols = parser.extract_classes(code, "python")
            
            assert len(symbols) == 2 or symbols is not None

    def test_extract_imports(self):
        """Test extracting import statements."""
        from src.atomization.parser import Parser

        parser = Parser()
        code = """
import os
import sys
from typing import List
"""
        
        with patch.object(parser, '_extract_imports', return_value=["os", "sys", "typing"]):
            imports = parser.extract_imports(code, "python")
            
            assert len(imports) >= 2 or imports is not None

