"""
Code Validator - Syntax and Basic Quality Checks

Validates generated code for MVP:
1. Syntax checking (Python: ast.parse, JavaScript: basic checks)
2. File existence validation
3. Basic linting (imports, naming conventions)

MVP Scope: Focus on "code compiles" validation, not deep quality checks.
"""

import ast
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from src.observability import get_logger

logger = get_logger("code_validator")


class ValidationError:
    """Validation error result."""

    def __init__(
        self,
        file_path: str,
        line: int,
        message: str,
        severity: str = "error"
    ):
        self.file_path = file_path
        self.line = line
        self.message = message
        self.severity = severity  # error, warning

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file_path,
            "line": self.line,
            "message": self.message,
            "severity": self.severity
        }


class CodeValidator:
    """
    Code validator for syntax and basic quality checks.

    Usage:
        validator = CodeValidator()
        is_valid, errors = validator.validate_file("path/to/file.py")
    """

    def __init__(self):
        """Initialize code validator."""
        logger.info("CodeValidator initialized")

    def validate_file(
        self,
        file_path: str,
        content: Optional[str] = None
    ) -> Tuple[bool, List[ValidationError]]:
        """
        Validate a single file.

        Args:
            file_path: Path to file
            content: File content (if None, reads from file_path)

        Returns:
            Tuple of (is_valid, list of validation errors)
        """
        path = Path(file_path)

        # Read content if not provided
        if content is None:
            if not path.exists():
                return False, [ValidationError(
                    file_path=file_path,
                    line=0,
                    message=f"File does not exist: {file_path}",
                    severity="error"
                )]

            content = path.read_text()

        # Determine file type and validate
        if file_path.endswith('.py'):
            return self._validate_python(file_path, content)
        elif file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
            return self._validate_javascript(file_path, content)
        elif file_path.endswith(('.json',)):
            return self._validate_json(file_path, content)
        elif file_path.endswith(('.yaml', '.yml')):
            return self._validate_yaml(file_path, content)
        else:
            # Unknown file type - assume valid
            logger.debug(f"Skipping validation for unknown file type: {file_path}")
            return True, []

    def validate_files(
        self,
        files: List[str]
    ) -> Tuple[bool, Dict[str, List[ValidationError]]]:
        """
        Validate multiple files.

        Args:
            files: List of file paths

        Returns:
            Tuple of (all_valid, dict of {file: errors})
        """
        all_errors = {}
        all_valid = True

        for file_path in files:
            is_valid, errors = self.validate_file(file_path)

            if not is_valid:
                all_valid = False
                all_errors[file_path] = errors

        return all_valid, all_errors

    def _validate_python(
        self,
        file_path: str,
        content: str
    ) -> Tuple[bool, List[ValidationError]]:
        """
        Validate Python file using ast.parse.

        Args:
            file_path: File path
            content: Python code

        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []

        # 1. Syntax check with ast.parse
        try:
            ast.parse(content)
            logger.debug(f"Python syntax valid: {file_path}")

        except SyntaxError as e:
            errors.append(ValidationError(
                file_path=file_path,
                line=e.lineno or 0,
                message=f"SyntaxError: {e.msg}",
                severity="error"
            ))
            logger.error(f"Python syntax error in {file_path}: {e}")

        except Exception as e:
            errors.append(ValidationError(
                file_path=file_path,
                line=0,
                message=f"Parsing error: {str(e)}",
                severity="error"
            ))
            logger.error(f"Python parsing error in {file_path}: {e}")

        # 2. Basic linting checks
        if not errors:  # Only if syntax is valid
            lint_errors = self._lint_python(file_path, content)
            errors.extend(lint_errors)

        is_valid = len([e for e in errors if e.severity == "error"]) == 0

        return is_valid, errors

    def _lint_python(
        self,
        file_path: str,
        content: str
    ) -> List[ValidationError]:
        """
        Basic Python linting checks.

        Args:
            file_path: File path
            content: Python code

        Returns:
            List of validation errors/warnings
        """
        errors = []
        lines = content.split('\n')

        # Check: Lines too long (>120 chars)
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                errors.append(ValidationError(
                    file_path=file_path,
                    line=i,
                    message=f"Line too long ({len(line)} > 120 chars)",
                    severity="warning"
                ))

        # Check: Missing docstrings for classes/functions
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if not ast.get_docstring(node):
                    errors.append(ValidationError(
                        file_path=file_path,
                        line=node.lineno,
                        message=f"Missing docstring for {node.name}",
                        severity="warning"
                    ))

        # Check: Unused imports (basic check)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])

        # Very basic unused import detection (check if import name appears in code)
        for import_name in imports:
            if import_name not in content:
                errors.append(ValidationError(
                    file_path=file_path,
                    line=0,
                    message=f"Potentially unused import: {import_name}",
                    severity="warning"
                ))

        return errors

    def _validate_javascript(
        self,
        file_path: str,
        content: str
    ) -> Tuple[bool, List[ValidationError]]:
        """
        Basic JavaScript/TypeScript validation.

        Note: This is a simplified check. For production, use eslint/tsc.

        Args:
            file_path: File path
            content: JavaScript code

        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []

        # Basic syntax checks
        # 1. Check for unmatched braces/brackets/parens
        braces = {'(': ')', '[': ']', '{': '}'}
        stack = []

        for i, char in enumerate(content):
            if char in braces.keys():
                stack.append(char)
            elif char in braces.values():
                if not stack:
                    errors.append(ValidationError(
                        file_path=file_path,
                        line=content[:i].count('\n') + 1,
                        message=f"Unmatched closing '{char}'",
                        severity="error"
                    ))
                else:
                    expected = braces[stack.pop()]
                    if char != expected:
                        errors.append(ValidationError(
                            file_path=file_path,
                            line=content[:i].count('\n') + 1,
                            message=f"Mismatched brackets: expected '{expected}', got '{char}'",
                            severity="error"
                        ))

        if stack:
            errors.append(ValidationError(
                file_path=file_path,
                line=0,
                message=f"Unclosed brackets: {stack}",
                severity="error"
            ))

        # 2. Check for common syntax errors
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Missing semicolons before return/if/for/while (not exhaustive)
            if re.match(r'^\s*(return|if|for|while|switch)\s+', line):
                prev_line = lines[i-2] if i > 1 else ""
                if prev_line.strip() and not prev_line.strip().endswith((';', '{', '}', '//')):
                    errors.append(ValidationError(
                        file_path=file_path,
                        line=i-1,
                        message="Missing semicolon before control statement",
                        severity="warning"
                    ))

        is_valid = len([e for e in errors if e.severity == "error"]) == 0

        logger.debug(f"JavaScript validation complete for {file_path}: {'valid' if is_valid else 'invalid'}")

        return is_valid, errors

    def _validate_json(
        self,
        file_path: str,
        content: str
    ) -> Tuple[bool, List[ValidationError]]:
        """Validate JSON file."""
        import json as json_module

        try:
            json_module.loads(content)
            logger.debug(f"JSON valid: {file_path}")
            return True, []

        except json_module.JSONDecodeError as e:
            error = ValidationError(
                file_path=file_path,
                line=e.lineno,
                message=f"JSON decode error: {e.msg}",
                severity="error"
            )
            logger.error(f"JSON error in {file_path}: {e}")
            return False, [error]

    def _validate_yaml(
        self,
        file_path: str,
        content: str
    ) -> Tuple[bool, List[ValidationError]]:
        """Validate YAML file."""
        try:
            import yaml
            yaml.safe_load(content)
            logger.debug(f"YAML valid: {file_path}")
            return True, []

        except yaml.YAMLError as e:
            error = ValidationError(
                file_path=file_path,
                line=getattr(e, 'problem_mark', None).line + 1 if hasattr(e, 'problem_mark') else 0,
                message=f"YAML parse error: {str(e)}",
                severity="error"
            )
            logger.error(f"YAML error in {file_path}: {e}")
            return False, [error]

        except ImportError:
            # pyyaml not installed - skip validation
            logger.warning("pyyaml not installed, skipping YAML validation")
            return True, []

    def validate_project(
        self,
        project_dir: str,
        file_patterns: List[str] = None
    ) -> Tuple[bool, Dict[str, List[ValidationError]]]:
        """
        Validate entire project directory.

        Args:
            project_dir: Project directory path
            file_patterns: List of glob patterns (e.g., ["*.py", "src/**/*.py"])

        Returns:
            Tuple of (all_valid, dict of {file: errors})
        """
        if file_patterns is None:
            file_patterns = ["**/*.py", "**/*.js", "**/*.ts", "**/*.json"]

        project_path = Path(project_dir)

        if not project_path.exists():
            logger.error(f"Project directory does not exist: {project_dir}")
            return False, {}

        # Collect all files matching patterns
        files_to_validate = set()
        for pattern in file_patterns:
            files_to_validate.update(project_path.glob(pattern))

        # Convert to strings
        file_paths = [str(f) for f in files_to_validate]

        logger.info(f"Validating {len(file_paths)} files in {project_dir}")

        # Validate all files
        return self.validate_files(file_paths)

    def get_validation_summary(
        self,
        validation_results: Dict[str, List[ValidationError]]
    ) -> Dict[str, Any]:
        """
        Generate validation summary.

        Args:
            validation_results: Dict of {file: errors}

        Returns:
            Summary dict
        """
        total_errors = sum(
            len([e for e in errors if e.severity == "error"])
            for errors in validation_results.values()
        )

        total_warnings = sum(
            len([e for e in errors if e.severity == "warning"])
            for errors in validation_results.values()
        )

        total_files_with_errors = len([
            file for file, errors in validation_results.items()
            if any(e.severity == "error" for e in errors)
        ])

        return {
            "total_files_validated": len(validation_results),
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "files_with_errors": total_files_with_errors,
            "is_valid": total_errors == 0
        }
