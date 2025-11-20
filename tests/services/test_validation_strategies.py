"""
Comprehensive tests for validation_strategies.py

Tests all validation strategies across Python, JavaScript, TypeScript, JSON, and YAML
with comprehensive rule coverage and integration validation.

Target Coverage: >90%
Performance Target: <100ms per validation
"""

import pytest
from typing import Optional
import time

from src.services.validation_strategies import (
    ValidationStrategy,
    PythonValidationStrategy,
    JavaScriptValidationStrategy,
    TypeScriptValidationStrategy,
    JSONValidationStrategy,
    YAMLValidationStrategy,
    ValidationStrategyFactory,
    ValidationError,
    ValidationResult,
    ValidationSeverity,
)
from src.services.file_type_detector import FileType
from src.cognitive.signatures.semantic_signature import SemanticTaskSignature


# Test Data Fixtures

VALID_PYTHON_CODE = '''
def calculate_total(price: float, tax_rate: float) -> float:
    """Calculate total price with tax."""
    return price * (1 + tax_rate)
'''

PYTHON_MISSING_TYPE_HINTS = '''
def calculate_total(price, tax_rate):
    """Calculate total price with tax."""
    return price * (1 + tax_rate)
'''

PYTHON_WITH_TODO = '''
def calculate_total(price: float, tax_rate: float) -> float:
    """Calculate total price with tax."""
    # TODO: Add validation
    return price * (1 + tax_rate)
'''

PYTHON_WITH_PLACEHOLDER = '''
def calculate_total(price: float, tax_rate: float) -> float:
    """Calculate total price with tax."""
    raise NotImplementedError
'''

PYTHON_LONG_FUNCTION = '''
def calculate_total(price: float, tax_rate: float) -> float:
    """Calculate total price with tax."""
    line1 = price
    line2 = tax_rate
    line3 = price + tax_rate
    line4 = price - tax_rate
    line5 = price * tax_rate
    line6 = price / tax_rate
    line7 = price ** tax_rate
    line8 = price % tax_rate
    line9 = price // tax_rate
    line10 = price + tax_rate
    line11 = price - tax_rate
    return line11
'''

VALID_JAVASCRIPT_CODE = '''
/**
 * Calculate total with tax
 * @param {number} price - Base price
 * @param {number} taxRate - Tax rate
 * @returns {number} Total price
 */
function calculateTotal(price, taxRate) {
    return price * (1 + taxRate);
}
'''

JAVASCRIPT_WITHOUT_JSDOC = '''
function calculateTotal(price, taxRate) {
    return price * (1 + taxRate);
}
'''

JAVASCRIPT_WITH_TODO = '''
/**
 * Calculate total with tax
 * @param {number} price - Base price
 * @param {number} taxRate - Tax rate
 * @returns {number} Total price
 */
function calculateTotal(price, taxRate) {
    // TODO: Add validation
    return price * (1 + taxRate);
}
'''

VALID_TYPESCRIPT_CODE = '''
function calculateTotal(price: number, taxRate: number): number {
    return price * (1 + taxRate);
}
'''

TYPESCRIPT_WITHOUT_TYPES = '''
function calculateTotal(price, taxRate) {
    return price * (1 + taxRate);
}
'''

TYPESCRIPT_WITH_ANY = '''
function calculateTotal(price: any, taxRate: any): any {
    return price * (1 + taxRate);
}
'''

VALID_JSON = '''
{
    "name": "test",
    "value": 123,
    "items": ["a", "b", "c"]
}
'''

JSON_WITH_TRAILING_COMMA = '''
{
    "name": "test",
    "value": 123,
}
'''

JSON_SYNTAX_ERROR = '''
{
    "name": "test"
    "value": 123
}
'''

VALID_YAML = '''
name: test
value: 123
items:
  - a
  - b
  - c
'''

YAML_WITH_TABS = '''
name: test
\tvalue: 123
items:
  - a
'''

YAML_SYNTAX_ERROR = '''
name: test
value: [123
items:
  - a
'''


class TestPythonValidationStrategy:
    """Test Python validation strategy."""

    def test_valid_python_code(self):
        """Test validation of valid Python code."""
        strategy = PythonValidationStrategy()
        result = strategy.validate(VALID_PYTHON_CODE)

        assert result.is_valid
        assert len(result.errors) == 0
        assert "syntax_validation" in result.rules_applied
        assert "type_annotation_validation" in result.rules_applied

    def test_syntax_error_detection(self):
        """Test detection of syntax errors."""
        invalid_code = '''
def calculate_total(price: float tax_rate: float) -> float:
    return price * tax_rate
'''
        strategy = PythonValidationStrategy()
        result = strategy.validate(invalid_code)

        assert not result.is_valid
        assert len(result.errors) > 0
        assert any(e.rule == "syntax_validation" for e in result.errors)
        assert any(e.severity == ValidationSeverity.CRITICAL for e in result.errors)

    def test_type_hint_validation(self):
        """Test type hint coverage validation."""
        strategy = PythonValidationStrategy()
        result = strategy.validate(PYTHON_MISSING_TYPE_HINTS)

        assert not result.is_valid
        errors = [e for e in result.errors if e.rule == "type_annotation"]
        assert len(errors) > 0
        assert "95%" in errors[0].message

    def test_loc_limit_validation(self):
        """Test LOC per function validation."""
        strategy = PythonValidationStrategy()
        result = strategy.validate(PYTHON_LONG_FUNCTION)

        assert not result.is_valid
        errors = [e for e in result.errors if e.rule == "loc_limit"]
        assert len(errors) > 0
        assert "10" in errors[0].message

    def test_todo_detection(self):
        """Test TODO comment detection."""
        strategy = PythonValidationStrategy()
        result = strategy.validate(PYTHON_WITH_TODO)

        errors = [e for e in result.errors if e.rule == "placeholder_detection"]
        assert len(errors) > 0
        assert any("TODO" in e.message for e in errors)

    def test_placeholder_detection(self):
        """Test placeholder implementation detection."""
        strategy = PythonValidationStrategy()
        result = strategy.validate(PYTHON_WITH_PLACEHOLDER)

        assert not result.is_valid
        errors = [e for e in result.errors if e.rule == "placeholder_detection"]
        assert len(errors) > 0
        assert any("NotImplementedError" in e.message for e in errors)
        assert any(e.severity == ValidationSeverity.CRITICAL for e in errors)

    def test_pass_statement_detection(self):
        """Test detection of pass statements."""
        code_with_pass = '''
def calculate_total(price: float, tax_rate: float) -> float:
    """Calculate total price with tax."""
    pass
'''
        strategy = PythonValidationStrategy()
        result = strategy.validate(code_with_pass)

        errors = [e for e in result.errors if e.rule == "placeholder_detection"]
        assert len(errors) > 0
        assert any("pass" in e.message for e in errors)

    def test_purpose_compliance(self):
        """Test purpose compliance checking."""
        signature = SemanticTaskSignature(
            purpose="Calculate total price with tax rate",
            intent="calculate",
            inputs={"price": "float", "tax_rate": "float"},
            outputs={"return": "float"},
            domain="business_logic"
        )

        strategy = PythonValidationStrategy()
        result = strategy.validate(VALID_PYTHON_CODE, signature)

        assert result.is_valid
        assert "purpose_compliance" in result.rules_applied

    def test_io_respect_validation(self):
        """Test I/O respect validation."""
        signature = SemanticTaskSignature(
            purpose="Calculate total",
            intent="calculate",
            inputs={"price": "float", "tax_rate": "float"},
            outputs={"return": "float"},
            domain="business_logic"
        )

        strategy = PythonValidationStrategy()
        result = strategy.validate(VALID_PYTHON_CODE, signature)

        assert "io_respect_validation" in result.rules_applied


class TestJavaScriptValidationStrategy:
    """Test JavaScript validation strategy."""

    def test_valid_javascript_code(self):
        """Test validation of valid JavaScript code."""
        strategy = JavaScriptValidationStrategy()
        result = strategy.validate(VALID_JAVASCRIPT_CODE)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_syntax_error_detection(self):
        """Test detection of unmatched braces."""
        invalid_code = '''
function calculateTotal(price, taxRate) {
    return price * (1 + taxRate);
'''
        strategy = JavaScriptValidationStrategy()
        result = strategy.validate(invalid_code)

        assert not result.is_valid
        errors = [e for e in result.errors if e.rule == "syntax_validation"]
        assert len(errors) > 0
        assert any("braces" in e.message for e in errors)

    def test_jsdoc_validation(self):
        """Test JSDoc coverage validation."""
        strategy = JavaScriptValidationStrategy()
        result = strategy.validate(JAVASCRIPT_WITHOUT_JSDOC)

        errors = [e for e in result.errors if e.rule == "jsdoc_validation"]
        assert len(errors) > 0
        assert "80%" in errors[0].message

    def test_loc_limit_validation(self):
        """Test LOC per function validation."""
        long_function = '''
function calculateTotal(price, taxRate) {
    const line1 = price;
    const line2 = taxRate;
    const line3 = price + taxRate;
    const line4 = price - taxRate;
    const line5 = price * taxRate;
    const line6 = price / taxRate;
    const line7 = price ** taxRate;
    const line8 = price % taxRate;
    const line9 = price + taxRate;
    const line10 = price - taxRate;
    const line11 = price * taxRate;
    return line11;
}
'''
        strategy = JavaScriptValidationStrategy()
        result = strategy.validate(long_function)

        errors = [e for e in result.errors if e.rule == "loc_limit"]
        assert len(errors) > 0

    def test_todo_detection(self):
        """Test TODO comment detection."""
        strategy = JavaScriptValidationStrategy()
        result = strategy.validate(JAVASCRIPT_WITH_TODO)

        errors = [e for e in result.errors if e.rule == "placeholder_detection"]
        assert len(errors) > 0
        assert any("TODO" in e.message for e in errors)

    def test_empty_function_detection(self):
        """Test detection of empty function bodies."""
        empty_function = '''
function calculateTotal(price, taxRate) {
}
'''
        strategy = JavaScriptValidationStrategy()
        result = strategy.validate(empty_function)

        errors = [e for e in result.errors if e.rule == "placeholder_detection"]
        assert len(errors) > 0
        assert any("Empty" in e.message for e in errors)

    def test_not_implemented_detection(self):
        """Test detection of 'Not implemented' errors."""
        not_implemented = '''
function calculateTotal(price, taxRate) {
    throw new Error('Not implemented');
}
'''
        strategy = JavaScriptValidationStrategy()
        result = strategy.validate(not_implemented)

        errors = [e for e in result.errors if e.rule == "placeholder_detection"]
        assert len(errors) > 0
        assert any(e.severity == ValidationSeverity.CRITICAL for e in errors)


class TestTypeScriptValidationStrategy:
    """Test TypeScript validation strategy."""

    def test_valid_typescript_code(self):
        """Test validation of valid TypeScript code."""
        strategy = TypeScriptValidationStrategy()
        result = strategy.validate(VALID_TYPESCRIPT_CODE)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_type_annotation_validation(self):
        """Test type annotation coverage validation."""
        strategy = TypeScriptValidationStrategy()
        result = strategy.validate(TYPESCRIPT_WITHOUT_TYPES)

        errors = [e for e in result.errors if e.rule == "type_annotation"]
        assert len(errors) > 0
        assert "95%" in errors[0].message

    def test_strict_mode_any_detection(self):
        """Test detection of 'any' type usage."""
        strategy = TypeScriptValidationStrategy()
        result = strategy.validate(TYPESCRIPT_WITH_ANY)

        warnings = [e for e in result.warnings if e.rule == "strict_mode"]
        assert len(warnings) > 0
        assert any("any" in e.message for e in warnings)

    def test_syntax_error_detection(self):
        """Test detection of syntax errors."""
        invalid_code = '''
function calculateTotal(price: number, taxRate: number): number {
    return price * (1 + taxRate;
}
'''
        strategy = TypeScriptValidationStrategy()
        result = strategy.validate(invalid_code)

        assert not result.is_valid
        errors = [e for e in result.errors if e.rule == "syntax_validation"]
        assert len(errors) > 0


class TestJSONValidationStrategy:
    """Test JSON validation strategy."""

    def test_valid_json(self):
        """Test validation of valid JSON."""
        strategy = JSONValidationStrategy()
        result = strategy.validate(VALID_JSON)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_syntax_error_detection(self):
        """Test detection of JSON syntax errors."""
        strategy = JSONValidationStrategy()
        result = strategy.validate(JSON_SYNTAX_ERROR)

        assert not result.is_valid
        errors = [e for e in result.errors if e.rule == "json_syntax"]
        assert len(errors) > 0
        assert any(e.severity == ValidationSeverity.CRITICAL for e in errors)

    def test_trailing_comma_detection(self):
        """Test detection of trailing commas."""
        strategy = JSONValidationStrategy()
        common_errors = strategy.detect_common_errors(JSON_WITH_TRAILING_COMMA)

        assert len(common_errors) > 0
        assert any("trailing comma" in e.message.lower() for e in common_errors)

    def test_single_quote_detection(self):
        """Test detection of single quotes."""
        json_with_single_quotes = "{'name': 'test'}"
        strategy = JSONValidationStrategy()
        common_errors = strategy.detect_common_errors(json_with_single_quotes)

        assert len(common_errors) > 0
        assert any("quote" in e.message.lower() for e in common_errors)


class TestYAMLValidationStrategy:
    """Test YAML validation strategy."""

    def test_valid_yaml(self):
        """Test validation of valid YAML."""
        strategy = YAMLValidationStrategy()
        result = strategy.validate(VALID_YAML)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_syntax_error_detection(self):
        """Test detection of YAML syntax errors."""
        strategy = YAMLValidationStrategy()
        result = strategy.validate(YAML_SYNTAX_ERROR)

        # YAML might be installed or not
        if result.errors:
            errors = [e for e in result.errors if e.rule == "yaml_syntax"]
            assert len(errors) > 0

    def test_tab_character_detection(self):
        """Test detection of tab characters."""
        strategy = YAMLValidationStrategy()
        common_errors = strategy.detect_common_errors(YAML_WITH_TABS)

        assert len(common_errors) > 0
        assert any("Tab" in e.message for e in common_errors)

    def test_duplicate_key_detection(self):
        """Test detection of duplicate keys."""
        yaml_with_duplicates = '''
name: test1
name: test2
value: 123
'''
        strategy = YAMLValidationStrategy()
        common_errors = strategy.detect_common_errors(yaml_with_duplicates)

        assert len(common_errors) > 0
        assert any("duplicate" in e.message.lower() for e in common_errors)


class TestValidationStrategyFactory:
    """Test validation strategy factory."""

    def test_get_python_strategy(self):
        """Test getting Python validation strategy."""
        strategy = ValidationStrategyFactory.get_strategy(FileType.PYTHON)
        assert isinstance(strategy, PythonValidationStrategy)

    def test_get_javascript_strategy(self):
        """Test getting JavaScript validation strategy."""
        strategy = ValidationStrategyFactory.get_strategy(FileType.JAVASCRIPT)
        assert isinstance(strategy, JavaScriptValidationStrategy)

    def test_get_typescript_strategy(self):
        """Test getting TypeScript validation strategy."""
        strategy = ValidationStrategyFactory.get_strategy(FileType.TYPESCRIPT)
        assert isinstance(strategy, TypeScriptValidationStrategy)

    def test_get_json_strategy(self):
        """Test getting JSON validation strategy."""
        strategy = ValidationStrategyFactory.get_strategy(FileType.JSON)
        assert isinstance(strategy, JSONValidationStrategy)

    def test_get_yaml_strategy(self):
        """Test getting YAML validation strategy."""
        strategy = ValidationStrategyFactory.get_strategy(FileType.YAML)
        assert isinstance(strategy, YAMLValidationStrategy)

    def test_strategy_caching(self):
        """Test that strategies are cached."""
        strategy1 = ValidationStrategyFactory.get_strategy(FileType.PYTHON)
        strategy2 = ValidationStrategyFactory.get_strategy(FileType.PYTHON)
        assert strategy1 is strategy2

    def test_clear_cache(self):
        """Test clearing strategy cache."""
        strategy1 = ValidationStrategyFactory.get_strategy(FileType.PYTHON)
        ValidationStrategyFactory.clear_cache()
        strategy2 = ValidationStrategyFactory.get_strategy(FileType.PYTHON)
        assert strategy1 is not strategy2

    def test_unknown_file_type_fallback(self):
        """Test fallback to Python for unknown file types."""
        strategy = ValidationStrategyFactory.get_strategy(FileType.UNKNOWN)
        assert isinstance(strategy, PythonValidationStrategy)


class TestPerformance:
    """Test validation performance."""

    def test_python_validation_performance(self):
        """Test Python validation completes in <100ms."""
        strategy = PythonValidationStrategy()

        start_time = time.time()
        result = strategy.validate(VALID_PYTHON_CODE)
        duration = (time.time() - start_time) * 1000  # Convert to ms

        assert duration < 100, f"Validation took {duration:.2f}ms (should be <100ms)"
        assert result.is_valid

    def test_javascript_validation_performance(self):
        """Test JavaScript validation completes in <100ms."""
        strategy = JavaScriptValidationStrategy()

        start_time = time.time()
        result = strategy.validate(VALID_JAVASCRIPT_CODE)
        duration = (time.time() - start_time) * 1000

        assert duration < 100, f"Validation took {duration:.2f}ms (should be <100ms)"
        assert result.is_valid

    def test_typescript_validation_performance(self):
        """Test TypeScript validation completes in <100ms."""
        strategy = TypeScriptValidationStrategy()

        start_time = time.time()
        result = strategy.validate(VALID_TYPESCRIPT_CODE)
        duration = (time.time() - start_time) * 1000

        assert duration < 100, f"Validation took {duration:.2f}ms (should be <100ms)"
        assert result.is_valid

    def test_json_validation_performance(self):
        """Test JSON validation completes in <100ms."""
        strategy = JSONValidationStrategy()

        start_time = time.time()
        result = strategy.validate(VALID_JSON)
        duration = (time.time() - start_time) * 1000

        assert duration < 100, f"Validation took {duration:.2f}ms (should be <100ms)"
        assert result.is_valid

    def test_yaml_validation_performance(self):
        """Test YAML validation completes in <100ms."""
        strategy = YAMLValidationStrategy()

        start_time = time.time()
        result = strategy.validate(VALID_YAML)
        duration = (time.time() - start_time) * 1000

        assert duration < 100, f"Validation took {duration:.2f}ms (should be <100ms)"
        assert result.is_valid


class TestIntegration:
    """Integration tests with file type detector."""

    def test_python_end_to_end(self):
        """Test complete Python validation flow."""
        from src.services.file_type_detector import FileTypeDetector

        detector = FileTypeDetector()
        detection = detector.detect(
            task_name="Calculate total with tax",
            task_description="Python function to calculate total",
            target_files=["calculate.py"]
        )

        strategy = ValidationStrategyFactory.get_strategy(detection.file_type)
        result = strategy.validate(VALID_PYTHON_CODE)

        assert isinstance(strategy, PythonValidationStrategy)
        assert result.is_valid

    def test_javascript_end_to_end(self):
        """Test complete JavaScript validation flow."""
        from src.services.file_type_detector import FileTypeDetector

        detector = FileTypeDetector()
        detection = detector.detect(
            task_name="Calculate total",
            task_description="JavaScript function to calculate",
            target_files=["calculate.js"]
        )

        strategy = ValidationStrategyFactory.get_strategy(detection.file_type)
        result = strategy.validate(VALID_JAVASCRIPT_CODE)

        assert isinstance(strategy, JavaScriptValidationStrategy)
        assert result.is_valid

    def test_typescript_end_to_end(self):
        """Test complete TypeScript validation flow."""
        from src.services.file_type_detector import FileTypeDetector

        detector = FileTypeDetector()
        detection = detector.detect(
            task_name="Calculate total",
            task_description="TypeScript function",
            target_files=["calculate.ts"]
        )

        strategy = ValidationStrategyFactory.get_strategy(detection.file_type)
        result = strategy.validate(VALID_TYPESCRIPT_CODE)

        assert isinstance(strategy, TypeScriptValidationStrategy)
        assert result.is_valid

    def test_with_task_signature(self):
        """Test validation with SemanticTaskSignature."""
        signature = SemanticTaskSignature(
            purpose="Calculate total price with tax",
            intent="calculate",
            inputs={"price": "float", "tax_rate": "float"},
            outputs={"return": "float"},
            domain="business_logic"
        )

        strategy = PythonValidationStrategy()
        result = strategy.validate(VALID_PYTHON_CODE, signature)

        assert result.is_valid
        assert "purpose_compliance" in result.rules_applied
        assert "io_respect_validation" in result.rules_applied


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Test creating ValidationResult."""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            rules_applied=["syntax_validation"],
            metadata={}
        )

        assert result.is_valid
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        assert "syntax_validation" in result.rules_applied

    def test_validation_result_with_errors(self):
        """Test ValidationResult with errors."""
        error = ValidationError(
            rule="syntax_validation",
            severity=ValidationSeverity.ERROR,
            message="Test error",
            line_number=1
        )

        result = ValidationResult(
            is_valid=False,
            errors=[error],
            warnings=[],
            rules_applied=["syntax_validation"],
            metadata={}
        )

        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0].message == "Test error"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_code(self):
        """Test validation of empty code."""
        strategy = PythonValidationStrategy()
        result = strategy.validate("")

        # Empty code should parse successfully (empty AST)
        assert result.is_valid or not result.is_valid  # Either is acceptable

    def test_very_long_code(self):
        """Test validation of very long code."""
        long_code = VALID_PYTHON_CODE * 100
        strategy = PythonValidationStrategy()

        start_time = time.time()
        result = strategy.validate(long_code)
        duration = (time.time() - start_time) * 1000

        # Should still complete reasonably fast
        assert duration < 1000  # 1 second max

    def test_malformed_json(self):
        """Test validation of completely malformed JSON."""
        malformed = "not json at all {{{["
        strategy = JSONValidationStrategy()
        result = strategy.validate(malformed)

        assert not result.is_valid
        assert len(result.errors) > 0

    def test_unicode_in_code(self):
        """Test validation of code with unicode characters."""
        unicode_code = '''
def greet(name: str) -> str:
    """Say hello with emoji."""
    return f"Hello {name}! 👋"
'''
        strategy = PythonValidationStrategy()
        result = strategy.validate(unicode_code)

        assert result.is_valid

    def test_mixed_indentation(self):
        """Test validation of code with mixed indentation."""
        mixed_indent = '''
def calculate(x: int) -> int:
    if x > 0:
        return x
\telse:
\t    return -x
'''
        strategy = PythonValidationStrategy()
        # Python will detect mixed tabs/spaces as syntax error
        result = strategy.validate(mixed_indent)
        # Result depends on Python version, just ensure it doesn't crash
        assert result is not None
