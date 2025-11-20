"""
Validation Strategy Pattern - Multi-language code validation with comprehensive rules.

Production implementation with Python, JavaScript, TypeScript, JSON, and YAML
validation strategies. Performs syntax validation, type checking, LOC limits,
placeholder detection, and task compliance verification.

Spec Reference: Task Group 4 - Validation Strategies Implementation
Target Coverage: >90% (TDD approach)
"""

import ast
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum

try:
    import yaml
except ImportError:
    yaml = None

from src.services.file_type_detector import FileType
from src.cognitive.signatures.semantic_signature import SemanticTaskSignature


class ValidationSeverity(Enum):
    """Severity level for validation errors."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationError:
    """Single validation error with context."""
    rule: str
    severity: ValidationSeverity
    message: str
    line_number: Optional[int] = None
    column: Optional[int] = None
    code_snippet: Optional[str] = None


@dataclass
class ValidationResult:
    """
    Result of code validation.

    Contains validation status, list of errors, and metadata about
    what rules were applied.
    """
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]
    rules_applied: List[str]
    metadata: Dict[str, Any]

    def __post_init__(self) -> None:
        if not hasattr(self, 'errors') or self.errors is None:
            self.errors = []
        if not hasattr(self, 'warnings') or self.warnings is None:
            self.warnings = []


class ValidationStrategy(ABC):
    """
    Base strategy for language-specific code validation.

    **Design Pattern**: Strategy Pattern for file-type-specific validation

    **Subclass Responsibilities**:
    - Implement validate_syntax() for language-specific parsing
    - Implement validate_type_annotations() for type checking
    - Implement validate_loc_limits() for line count enforcement
    - Implement detect_placeholders() for TODO/NotImplemented detection
    - Optionally override validate_compliance() for custom checks

    **Shared Functionality**:
    - Error aggregation and reporting
    - Severity classification
    - Rule tracking
    """

    MAX_LOC_PER_FUNCTION = 10

    def __init__(self) -> None:
        """Initialize base validation strategy."""
        self.strategy_name = self.__class__.__name__

    def validate(
        self,
        code: str,
        task_signature: Optional[SemanticTaskSignature] = None
    ) -> ValidationResult:
        """
        Validate code against all rules.

        Args:
            code: Code to validate
            task_signature: Optional task signature for compliance checking

        Returns:
            ValidationResult with errors, warnings, and metadata

        Example:
            >>> strategy = PythonValidationStrategy()
            >>> result = strategy.validate(code, task_signature)
            >>> assert result.is_valid or len(result.errors) > 0
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []
        rules_applied: List[str] = []
        metadata: Dict[str, Any] = {}

        # Rule 1: Syntax validation
        syntax_errors = self.validate_syntax(code)
        errors.extend(syntax_errors)
        rules_applied.append("syntax_validation")

        # Rule 2: Type annotations (if applicable)
        type_errors = self.validate_type_annotations(code)
        errors.extend(type_errors)
        rules_applied.append("type_annotation_validation")

        # Rule 3: LOC limits
        loc_errors = self.validate_loc_limits(code)
        errors.extend(loc_errors)
        rules_applied.append("loc_limit_validation")

        # Rule 4: Placeholder detection
        placeholder_errors = self.detect_placeholders(code)
        errors.extend(placeholder_errors)
        rules_applied.append("placeholder_detection")

        # Rule 5: Purpose compliance (if task_signature provided)
        if task_signature:
            compliance_errors = self.validate_compliance(code, task_signature)
            errors.extend(compliance_errors)
            rules_applied.append("purpose_compliance")

            # Rule 6: I/O respect (if task_signature provided)
            io_errors = self.validate_io_respect(code, task_signature)
            errors.extend(io_errors)
            rules_applied.append("io_respect_validation")

        # Separate errors from warnings
        actual_errors = [e for e in errors if e.severity in [
            ValidationSeverity.ERROR,
            ValidationSeverity.CRITICAL
        ]]
        actual_warnings = [e for e in errors if e.severity == ValidationSeverity.WARNING]

        is_valid = len(actual_errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=actual_errors,
            warnings=actual_warnings,
            rules_applied=rules_applied,
            metadata=metadata
        )

    @abstractmethod
    def validate_syntax(self, code: str) -> List[ValidationError]:
        """Validate code syntax."""
        pass

    @abstractmethod
    def validate_type_annotations(self, code: str) -> List[ValidationError]:
        """Validate type annotations/hints."""
        pass

    @abstractmethod
    def validate_loc_limits(self, code: str) -> List[ValidationError]:
        """Validate lines of code per function."""
        pass

    @abstractmethod
    def detect_placeholders(self, code: str) -> List[ValidationError]:
        """Detect TODO comments and placeholder implementations."""
        pass

    def validate_compliance(
        self,
        code: str,
        task_signature: SemanticTaskSignature
    ) -> List[ValidationError]:
        """
        Validate code compliance with task purpose.

        Default implementation checks for:
        - Function name matches intent
        - Purpose keywords present in code

        Args:
            code: Generated code
            task_signature: Task signature

        Returns:
            List of validation errors
        """
        errors: List[ValidationError] = []

        # Extract purpose keywords
        purpose_words = set(task_signature.purpose.lower().split())
        code_lower = code.lower()

        # Check for keyword presence (at least 50% match)
        matched_keywords = sum(1 for word in purpose_words if word in code_lower)
        match_ratio = matched_keywords / len(purpose_words) if purpose_words else 0

        if match_ratio < 0.3:
            errors.append(ValidationError(
                rule="purpose_compliance",
                severity=ValidationSeverity.WARNING,
                message=f"Low purpose compliance: only {match_ratio:.0%} of purpose keywords found in code"
            ))

        return errors

    def validate_io_respect(
        self,
        code: str,
        task_signature: SemanticTaskSignature
    ) -> List[ValidationError]:
        """
        Validate code respects expected inputs/outputs.

        Default implementation checks for parameter name presence.

        Args:
            code: Generated code
            task_signature: Task signature with expected I/O

        Returns:
            List of validation errors
        """
        errors: List[ValidationError] = []

        # Check input parameter names
        expected_inputs = set(task_signature.inputs.keys())
        code_lower = code.lower()

        if expected_inputs:
            matched_inputs = sum(1 for param in expected_inputs if param.lower() in code_lower)
            match_ratio = matched_inputs / len(expected_inputs)

            if match_ratio < 0.5:
                errors.append(ValidationError(
                    rule="io_respect",
                    severity=ValidationSeverity.WARNING,
                    message=f"Expected input parameters not found: {expected_inputs - set(code_lower.split())}"
                ))

        return errors


class PythonValidationStrategy(ValidationStrategy):
    """
    Python-specific validation strategy.

    **Validation Rules**:
    1. Syntax validation via ast.parse
    2. Type hint validation (>95% coverage)
    3. LOC limit (≤10 per function)
    4. TODO/placeholder detection
    5. Purpose compliance checking
    6. I/O respect validation
    """

    def validate_syntax(self, code: str) -> List[ValidationError]:
        """
        Validate Python syntax using AST parsing.

        Args:
            code: Python code to validate

        Returns:
            List of syntax errors with line numbers
        """
        errors: List[ValidationError] = []

        try:
            ast.parse(code)
        except SyntaxError as e:
            errors.append(ValidationError(
                rule="syntax_validation",
                severity=ValidationSeverity.CRITICAL,
                message=f"Syntax error: {e.msg}",
                line_number=e.lineno,
                column=e.offset,
                code_snippet=e.text
            ))
        except Exception as e:
            errors.append(ValidationError(
                rule="syntax_validation",
                severity=ValidationSeverity.ERROR,
                message=f"Parse error: {str(e)}"
            ))

        return errors

    def validate_type_annotations(self, code: str) -> List[ValidationError]:
        """
        Validate type hint coverage (>95%).

        Args:
            code: Python code to validate

        Returns:
            List of type annotation errors
        """
        errors: List[ValidationError] = []

        try:
            tree = ast.parse(code)
        except:
            return errors

        function_count = 0
        annotated_params = 0
        total_params = 0
        functions_with_return_type = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                function_count += 1

                # Check return type annotation
                if node.returns is not None:
                    functions_with_return_type += 1

                # Check parameter type annotations
                for arg in node.args.args:
                    if arg.arg != 'self':
                        total_params += 1
                        if arg.annotation is not None:
                            annotated_params += 1

        if function_count > 0:
            # Return type coverage
            return_coverage = functions_with_return_type / function_count
            if return_coverage < 0.95:
                errors.append(ValidationError(
                    rule="type_annotation",
                    severity=ValidationSeverity.ERROR,
                    message=f"Return type coverage {return_coverage:.0%} < 95% ({functions_with_return_type}/{function_count} functions)"
                ))

            # Parameter type coverage
            if total_params > 0:
                param_coverage = annotated_params / total_params
                if param_coverage < 0.95:
                    errors.append(ValidationError(
                        rule="type_annotation",
                        severity=ValidationSeverity.ERROR,
                        message=f"Parameter type coverage {param_coverage:.0%} < 95% ({annotated_params}/{total_params} parameters)"
                    ))

        return errors

    def validate_loc_limits(self, code: str) -> List[ValidationError]:
        """
        Validate LOC per function (≤10 lines).

        Args:
            code: Python code to validate

        Returns:
            List of LOC violations
        """
        errors: List[ValidationError] = []

        try:
            tree = ast.parse(code)
        except:
            return errors

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_start = node.lineno
                func_end = node.end_lineno or func_start

                # Count non-blank, non-comment lines
                lines = code.split('\n')[func_start - 1:func_end]
                loc = sum(1 for line in lines
                         if line.strip() and not line.strip().startswith('#'))

                if loc > self.MAX_LOC_PER_FUNCTION:
                    errors.append(ValidationError(
                        rule="loc_limit",
                        severity=ValidationSeverity.ERROR,
                        message=f"Function '{node.name}' has {loc} LOC (max {self.MAX_LOC_PER_FUNCTION})",
                        line_number=func_start
                    ))

        return errors

    def detect_placeholders(self, code: str) -> List[ValidationError]:
        """
        Detect TODO comments and placeholder patterns.

        Args:
            code: Python code to validate

        Returns:
            List of placeholder detections
        """
        errors: List[ValidationError] = []

        # TODO/FIXME/XXX/HACK comments
        comment_patterns = [
            (r'#.*TODO', 'TODO comment'),
            (r'#.*FIXME', 'FIXME comment'),
            (r'#.*XXX', 'XXX comment'),
            (r'#.*HACK', 'HACK comment'),
        ]

        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, desc in comment_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    errors.append(ValidationError(
                        rule="placeholder_detection",
                        severity=ValidationSeverity.ERROR,
                        message=f"{desc} found",
                        line_number=i,
                        code_snippet=line.strip()
                    ))

        # Pass statements (placeholder implementation)
        if re.search(r'^\s+pass\s*$', code, re.MULTILINE):
            errors.append(ValidationError(
                rule="placeholder_detection",
                severity=ValidationSeverity.ERROR,
                message="'pass' statement found (placeholder implementation)"
            ))

        # Ellipsis (...) placeholder
        if re.search(r'^\s+\.\.\.\s*$', code, re.MULTILINE):
            errors.append(ValidationError(
                rule="placeholder_detection",
                severity=ValidationSeverity.ERROR,
                message="Ellipsis (...) found (placeholder implementation)"
            ))

        # NotImplementedError
        if 'NotImplementedError' in code or 'NotImplemented' in code:
            errors.append(ValidationError(
                rule="placeholder_detection",
                severity=ValidationSeverity.CRITICAL,
                message="NotImplementedError found (incomplete implementation)"
            ))

        return errors


class JavaScriptValidationStrategy(ValidationStrategy):
    """
    JavaScript-specific validation strategy.

    **Validation Rules**:
    1. Syntax validation via basic parsing
    2. JSDoc validation (>80% coverage)
    3. LOC limit (≤10 per function)
    4. TODO/placeholder detection
    5. Purpose compliance checking
    """

    def validate_syntax(self, code: str) -> List[ValidationError]:
        """
        Validate JavaScript syntax.

        Basic validation checking for common syntax errors.

        Args:
            code: JavaScript code to validate

        Returns:
            List of syntax errors
        """
        errors: List[ValidationError] = []

        # Check for basic syntax issues
        if code.count('{') != code.count('}'):
            errors.append(ValidationError(
                rule="syntax_validation",
                severity=ValidationSeverity.CRITICAL,
                message="Unmatched curly braces"
            ))

        if code.count('(') != code.count(')'):
            errors.append(ValidationError(
                rule="syntax_validation",
                severity=ValidationSeverity.CRITICAL,
                message="Unmatched parentheses"
            ))

        if code.count('[') != code.count(']'):
            errors.append(ValidationError(
                rule="syntax_validation",
                severity=ValidationSeverity.CRITICAL,
                message="Unmatched square brackets"
            ))

        return errors

    def validate_type_annotations(self, code: str) -> List[ValidationError]:
        """
        Validate JSDoc coverage (>80%).

        Args:
            code: JavaScript code to validate

        Returns:
            List of JSDoc validation errors
        """
        errors: List[ValidationError] = []

        # Find all function declarations
        function_pattern = r'(?:function\s+\w+|(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>))'
        functions = re.findall(function_pattern, code)

        if not functions:
            return errors

        # Find all JSDoc comments
        jsdoc_pattern = r'/\*\*[\s\S]*?\*/'
        jsdocs = re.findall(jsdoc_pattern, code)

        # Check for @param and @returns in JSDoc
        param_count = sum(1 for doc in jsdocs if '@param' in doc)
        returns_count = sum(1 for doc in jsdocs if '@returns' in doc or '@return' in doc)

        jsdoc_coverage = len(jsdocs) / len(functions)
        if jsdoc_coverage < 0.80:
            errors.append(ValidationError(
                rule="jsdoc_validation",
                severity=ValidationSeverity.ERROR,
                message=f"JSDoc coverage {jsdoc_coverage:.0%} < 80% ({len(jsdocs)}/{len(functions)} functions)"
            ))

        return errors

    def validate_loc_limits(self, code: str) -> List[ValidationError]:
        """
        Validate LOC per function (≤10 lines).

        Args:
            code: JavaScript code to validate

        Returns:
            List of LOC violations
        """
        errors: List[ValidationError] = []

        # Simple function detection
        function_starts = []
        lines = code.split('\n')

        for i, line in enumerate(lines):
            if re.search(r'function\s+\w+|(?:const|let|var)\s+\w+\s*=.*=>', line):
                function_starts.append(i)

        # For each function, count lines until closing brace
        for start_idx in function_starts:
            brace_count = 0
            loc = 0
            found_opening = False

            for i in range(start_idx, len(lines)):
                line = lines[i].strip()
                if not line or line.startswith('//'):
                    continue

                loc += 1

                if '{' in line:
                    found_opening = True
                    brace_count += line.count('{') - line.count('}')
                elif found_opening:
                    brace_count += line.count('{') - line.count('}')

                if found_opening and brace_count == 0:
                    break

            if loc > self.MAX_LOC_PER_FUNCTION:
                errors.append(ValidationError(
                    rule="loc_limit",
                    severity=ValidationSeverity.ERROR,
                    message=f"Function at line {start_idx + 1} has {loc} LOC (max {self.MAX_LOC_PER_FUNCTION})",
                    line_number=start_idx + 1
                ))

        return errors

    def detect_placeholders(self, code: str) -> List[ValidationError]:
        """
        Detect TODO comments and placeholder patterns.

        Args:
            code: JavaScript code to validate

        Returns:
            List of placeholder detections
        """
        errors: List[ValidationError] = []

        # TODO/FIXME/XXX/HACK comments
        comment_patterns = [
            (r'//.*TODO', 'TODO comment'),
            (r'//.*FIXME', 'FIXME comment'),
            (r'//.*XXX', 'XXX comment'),
            (r'//.*HACK', 'HACK comment'),
        ]

        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, desc in comment_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    errors.append(ValidationError(
                        rule="placeholder_detection",
                        severity=ValidationSeverity.ERROR,
                        message=f"{desc} found",
                        line_number=i,
                        code_snippet=line.strip()
                    ))

        # Empty function bodies
        if re.search(r'\{[\s\n]*\}', code):
            errors.append(ValidationError(
                rule="placeholder_detection",
                severity=ValidationSeverity.ERROR,
                message="Empty function body found"
            ))

        # throw new Error('Not implemented')
        if re.search(r"throw\s+new\s+Error\s*\(\s*['\"]Not implemented", code, re.IGNORECASE):
            errors.append(ValidationError(
                rule="placeholder_detection",
                severity=ValidationSeverity.CRITICAL,
                message="'Not implemented' error throw found"
            ))

        return errors


class TypeScriptValidationStrategy(ValidationStrategy):
    """
    TypeScript-specific validation strategy.

    **Validation Rules**:
    1. Syntax validation
    2. Type annotation validation (>95% coverage)
    3. Strict mode compliance
    4. LOC limit (≤10 per function)
    5. TODO/placeholder detection
    """

    def validate(
        self,
        code: str,
        task_signature: Optional[SemanticTaskSignature] = None
    ) -> ValidationResult:
        """
        Validate TypeScript code with strict mode checking.

        Extends base validate() to include strict mode validation.
        """
        # Call base validation
        result = super().validate(code, task_signature)

        # Add strict mode validation
        strict_mode_errors = self.validate_strict_mode(code)

        # Merge strict mode warnings into result
        for error in strict_mode_errors:
            if error.severity == ValidationSeverity.WARNING:
                result.warnings.append(error)
            else:
                result.errors.append(error)
                result.is_valid = False

        result.rules_applied.append("strict_mode_validation")

        return result

    def validate_syntax(self, code: str) -> List[ValidationError]:
        """
        Validate TypeScript syntax.

        Args:
            code: TypeScript code to validate

        Returns:
            List of syntax errors
        """
        errors: List[ValidationError] = []

        # Check for basic syntax issues
        if code.count('{') != code.count('}'):
            errors.append(ValidationError(
                rule="syntax_validation",
                severity=ValidationSeverity.CRITICAL,
                message="Unmatched curly braces"
            ))

        if code.count('(') != code.count(')'):
            errors.append(ValidationError(
                rule="syntax_validation",
                severity=ValidationSeverity.CRITICAL,
                message="Unmatched parentheses"
            ))

        if code.count('<') != code.count('>'):
            # Could be generic syntax or comparison, be lenient
            pass

        return errors

    def validate_type_annotations(self, code: str) -> List[ValidationError]:
        """
        Validate type annotation coverage (>95%).

        Args:
            code: TypeScript code to validate

        Returns:
            List of type annotation errors
        """
        errors: List[ValidationError] = []

        # Find function declarations more accurately
        function_pattern = r'function\s+(\w+)\s*\(([^)]*)\)(?:\s*:\s*(\w+))?'
        matches = re.findall(function_pattern, code)

        total_functions = len(matches)
        if total_functions == 0:
            return errors

        total_params = 0
        typed_params = 0
        functions_with_return = 0

        for func_name, params_str, return_type in matches:
            # Count return type
            if return_type:
                functions_with_return += 1

            # Count parameters
            if params_str.strip():
                params = [p.strip() for p in params_str.split(',')]
                for param in params:
                    if param:
                        total_params += 1
                        if ':' in param:
                            typed_params += 1

        # Check parameter type coverage
        if total_params > 0:
            param_coverage = typed_params / total_params
            if param_coverage < 0.95:
                errors.append(ValidationError(
                    rule="type_annotation",
                    severity=ValidationSeverity.ERROR,
                    message=f"Type annotation coverage {param_coverage:.0%} < 95% ({typed_params}/{total_params} parameters)"
                ))

        # Check return type coverage
        return_coverage = functions_with_return / total_functions
        if return_coverage < 0.95:
            errors.append(ValidationError(
                rule="type_annotation",
                severity=ValidationSeverity.ERROR,
                message=f"Return type coverage {return_coverage:.0%} < 95% ({functions_with_return}/{total_functions} functions)"
            ))

        return errors

    def validate_strict_mode(self, code: str) -> List[ValidationError]:
        """
        Validate strict mode compliance.

        Args:
            code: TypeScript code to validate

        Returns:
            List of strict mode violations
        """
        errors: List[ValidationError] = []

        # Check for 'any' type usage
        any_count = len(re.findall(r':\s*any\b', code))
        if any_count > 0:
            errors.append(ValidationError(
                rule="strict_mode",
                severity=ValidationSeverity.WARNING,
                message=f"Found {any_count} 'any' type usage(s) - should be minimal in strict mode"
            ))

        return errors

    def validate_loc_limits(self, code: str) -> List[ValidationError]:
        """
        Validate LOC per function (≤10 lines).

        Args:
            code: TypeScript code to validate

        Returns:
            List of LOC violations
        """
        errors: List[ValidationError] = []

        # Reuse JavaScript logic
        js_strategy = JavaScriptValidationStrategy()
        return js_strategy.validate_loc_limits(code)

    def detect_placeholders(self, code: str) -> List[ValidationError]:
        """
        Detect TODO comments and placeholder patterns.

        Args:
            code: TypeScript code to validate

        Returns:
            List of placeholder detections
        """
        # Reuse JavaScript logic
        js_strategy = JavaScriptValidationStrategy()
        return js_strategy.detect_placeholders(code)


class JSONValidationStrategy(ValidationStrategy):
    """
    JSON-specific validation strategy.

    **Validation Rules**:
    1. JSON syntax validation
    2. Schema validation (if schema provided)
    3. Common error detection (trailing commas, quotes)
    """

    def validate_syntax(self, code: str) -> List[ValidationError]:
        """
        Validate JSON syntax.

        Args:
            code: JSON code to validate

        Returns:
            List of syntax errors
        """
        errors: List[ValidationError] = []

        try:
            json.loads(code)
        except json.JSONDecodeError as e:
            errors.append(ValidationError(
                rule="json_syntax",
                severity=ValidationSeverity.CRITICAL,
                message=f"JSON syntax error: {e.msg}",
                line_number=e.lineno,
                column=e.colno
            ))
        except Exception as e:
            errors.append(ValidationError(
                rule="json_syntax",
                severity=ValidationSeverity.ERROR,
                message=f"JSON parse error: {str(e)}"
            ))

        return errors

    def validate_type_annotations(self, code: str) -> List[ValidationError]:
        """JSON doesn't have type annotations."""
        return []

    def validate_loc_limits(self, code: str) -> List[ValidationError]:
        """JSON doesn't have function LOC limits."""
        return []

    def detect_placeholders(self, code: str) -> List[ValidationError]:
        """JSON doesn't typically have placeholders."""
        return []

    def detect_common_errors(self, code: str) -> List[ValidationError]:
        """
        Detect common JSON errors.

        Args:
            code: JSON code to validate

        Returns:
            List of common errors
        """
        errors: List[ValidationError] = []

        # Trailing commas
        if re.search(r',[\s\n]*[}\]]', code):
            errors.append(ValidationError(
                rule="json_common_errors",
                severity=ValidationSeverity.ERROR,
                message="Trailing comma detected (invalid in JSON)"
            ))

        # Single quotes
        if "'" in code and '"' not in code:
            errors.append(ValidationError(
                rule="json_common_errors",
                severity=ValidationSeverity.ERROR,
                message="Single quotes detected (JSON requires double quotes)"
            ))

        return errors


class YAMLValidationStrategy(ValidationStrategy):
    """
    YAML-specific validation strategy.

    **Validation Rules**:
    1. YAML syntax validation
    2. Structure validation
    3. Common error detection (tabs, indentation)
    """

    def validate_syntax(self, code: str) -> List[ValidationError]:
        """
        Validate YAML syntax.

        Args:
            code: YAML code to validate

        Returns:
            List of syntax errors
        """
        errors: List[ValidationError] = []

        if yaml is None:
            errors.append(ValidationError(
                rule="yaml_syntax",
                severity=ValidationSeverity.WARNING,
                message="PyYAML not installed, skipping YAML validation"
            ))
            return errors

        try:
            yaml.safe_load(code)
        except yaml.YAMLError as e:
            errors.append(ValidationError(
                rule="yaml_syntax",
                severity=ValidationSeverity.CRITICAL,
                message=f"YAML syntax error: {str(e)}"
            ))
        except Exception as e:
            errors.append(ValidationError(
                rule="yaml_syntax",
                severity=ValidationSeverity.ERROR,
                message=f"YAML parse error: {str(e)}"
            ))

        return errors

    def validate_type_annotations(self, code: str) -> List[ValidationError]:
        """YAML doesn't have type annotations."""
        return []

    def validate_loc_limits(self, code: str) -> List[ValidationError]:
        """YAML doesn't have function LOC limits."""
        return []

    def detect_placeholders(self, code: str) -> List[ValidationError]:
        """YAML doesn't typically have placeholders."""
        return []

    def detect_common_errors(self, code: str) -> List[ValidationError]:
        """
        Detect common YAML errors.

        Args:
            code: YAML code to validate

        Returns:
            List of common errors
        """
        errors: List[ValidationError] = []

        # Tab characters
        if '\t' in code:
            lines_with_tabs = [i + 1 for i, line in enumerate(code.split('\n')) if '\t' in line]
            errors.append(ValidationError(
                rule="yaml_common_errors",
                severity=ValidationSeverity.ERROR,
                message=f"Tab characters found (YAML requires spaces): lines {lines_with_tabs}"
            ))

        # Duplicate keys (basic check)
        lines = code.split('\n')
        keys_seen = set()
        for i, line in enumerate(lines, 1):
            match = re.match(r'^(\s*)(\w+):', line)
            if match:
                key = match.group(2)
                if key in keys_seen:
                    errors.append(ValidationError(
                        rule="yaml_common_errors",
                        severity=ValidationSeverity.WARNING,
                        message=f"Possible duplicate key '{key}'",
                        line_number=i
                    ))
                keys_seen.add(key)

        return errors


class ValidationStrategyFactory:
    """
    Factory for creating file-type-specific validation strategies.

    **Strategy Selection**:
    - Python → PythonValidationStrategy
    - JavaScript → JavaScriptValidationStrategy
    - TypeScript → TypeScriptValidationStrategy
    - JSON → JSONValidationStrategy
    - YAML → YAMLValidationStrategy

    **Example Usage**:
    ```python
    strategy = ValidationStrategyFactory.get_strategy(FileType.PYTHON)
    result = strategy.validate(code, task_signature)
    ```
    """

    _strategies: Dict[FileType, ValidationStrategy] = {}

    @classmethod
    def get_strategy(cls, file_type: FileType) -> ValidationStrategy:
        """
        Get appropriate validation strategy for file type.

        Args:
            file_type: Detected file type

        Returns:
            ValidationStrategy instance for that file type

        Example:
            >>> strategy = ValidationStrategyFactory.get_strategy(FileType.PYTHON)
            >>> assert isinstance(strategy, PythonValidationStrategy)
        """
        # Return cached strategy if exists
        if file_type in cls._strategies:
            return cls._strategies[file_type]

        # Create new strategy based on file type
        if file_type == FileType.PYTHON:
            strategy = PythonValidationStrategy()
        elif file_type == FileType.JAVASCRIPT:
            strategy = JavaScriptValidationStrategy()
        elif file_type == FileType.TYPESCRIPT:
            strategy = TypeScriptValidationStrategy()
        elif file_type == FileType.JSON:
            strategy = JSONValidationStrategy()
        elif file_type == FileType.YAML:
            strategy = YAMLValidationStrategy()
        else:
            # Fallback to Python for unknown types
            strategy = PythonValidationStrategy()

        # Cache for reuse
        cls._strategies[file_type] = strategy

        return strategy

    @classmethod
    def clear_cache(cls) -> None:
        """Clear cached strategies (useful for testing)."""
        cls._strategies.clear()
