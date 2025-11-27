"""
Basic Validation Pipeline - Fast QA Layer (No Docker)

Phase 0.5.5: Validates generated code BEFORE acceptance.

This pipeline runs ALWAYS and FAST:
- py_compile: Syntax validation
- Regression patterns: Known bug detection
- Dead code: Empty functions, pass-only
- Import check: Missing/invalid imports

NO Docker, NO database, NO network = FAST feedback.
"""

import ast
import logging
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """Severity of validation errors."""
    ERROR = "error"       # Blocks acceptance
    WARNING = "warning"   # Logged but allowed
    INFO = "info"         # Informational


@dataclass
class ValidationError:
    """A validation error or warning."""
    severity: ValidationSeverity
    file_path: str
    line_number: Optional[int]
    message: str
    category: str
    fix_hint: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of validation pipeline."""
    passed: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    files_checked: int = 0
    duration_ms: float = 0.0

    def add_error(self, error: ValidationError) -> None:
        if error.severity == ValidationSeverity.ERROR:
            self.errors.append(error)
            self.passed = False
        else:
            self.warnings.append(error)

    def summary(self) -> str:
        status = "✅ PASSED" if self.passed else "❌ FAILED"
        return (
            f"{status} | "
            f"Files: {self.files_checked} | "
            f"Errors: {len(self.errors)} | "
            f"Warnings: {len(self.warnings)} | "
            f"Time: {self.duration_ms:.0f}ms"
        )


# =============================================================================
# KNOWN REGRESSION PATTERNS (Inline for fast loading)
# =============================================================================

REGRESSION_PATTERNS: List[Dict] = [
    {
        "id": "REG-001",
        "pattern": r"server_default\s*=\s*sa\.text\s*\(\s*['\"](?!now\(\)|gen_random_uuid\(\)|current_timestamp|uuid_generate_v4\(\))[A-Z_]+['\"]\s*\)",
        "message": "sa.text() used for string literal (should be plain string)",
        "category": "server_default",
        "severity": ValidationSeverity.ERROR,
        "fix_hint": "Use server_default='VALUE' instead of sa.text('VALUE')",
    },
    {
        "id": "REG-002",
        # Bug #43 Fix v2: Properly limit to same class using negative lookahead
        # - (?!class\s+\w+) ensures we stop at next class definition
        # - (?<![a-zA-Z_])id\s*: excludes *_id fields (customer_id, product_id, etc.)
        "pattern": r"class\s+\w+Create\([^)]*\):\s*\n(?:(?!class\s+\w+)[^\n]*\n){0,15}[^\n]*(?<![a-zA-Z_])id\s*:",
        "message": "ID field in Create schema (should be server-generated)",
        "category": "schema_error",
        "severity": ValidationSeverity.ERROR,
        "fix_hint": "Remove 'id' from Create schemas - it's auto-generated",
    },
    {
        "id": "REG-003",
        "pattern": r"from\s+\.\.\s+import|from\s+\.\.\.\s+import",
        "message": "Relative import going up more than one level",
        "category": "import_error",
        "severity": ValidationSeverity.WARNING,
        "fix_hint": "Use absolute imports (from src.x import y)",
    },
    {
        "id": "REG-004",
        "pattern": r"eval\s*\(|exec\s*\(",
        "message": "Dangerous eval/exec detected",
        "category": "security",
        "severity": ValidationSeverity.ERROR,
        "fix_hint": "Never use eval/exec in production code",
    },
    {
        "id": "REG-005",
        "pattern": r"await\s+\w+\.commit\(\)\s*\n\s*return",
        "message": "Missing refresh after commit before return",
        "category": "async_pattern",
        "severity": ValidationSeverity.WARNING,
        "fix_hint": "Add 'await session.refresh(obj)' after commit",
    },
    {
        "id": "REG-006",
        "pattern": r"\bProductCreate\b.*\bPUT\b|\bPUT\b.*\bProductCreate\b",
        "message": "Using Create schema for PUT (should use Update)",
        "category": "schema_error",
        "severity": ValidationSeverity.ERROR,
        "fix_hint": "Use ProductUpdate for PUT endpoints, not ProductCreate",
    },
    {
        "id": "REG-007",
        "pattern": r"def\s+\w+\([^)]*\):\s*\n\s*pass\s*$",
        "message": "Empty function (pass-only)",
        "category": "dead_code",
        "severity": ValidationSeverity.WARNING,
        "fix_hint": "Implement the function or remove it",
    },
    {
        "id": "REG-008",
        "pattern": r"#\s*TODO|#\s*FIXME|#\s*XXX|#\s*HACK",
        "message": "TODO/FIXME comment in generated code",
        "category": "incomplete_code",
        "severity": ValidationSeverity.WARNING,
        "fix_hint": "Generated code should be complete, no TODOs",
    },
    {
        "id": "REG-009",
        # FIXED: Exclude intentional abstract method patterns
        # Valid: raise NotImplementedError("Subclasses must implement...")
        # Invalid: raise NotImplementedError() or raise NotImplementedError("TODO")
        "pattern": r"raise\s+NotImplementedError\s*\(\s*\)|raise\s+NotImplementedError\s*\(\s*['\"](?!Subclasses must implement|Override this method)['\"]",
        "message": "NotImplementedError in generated code (not abstract method pattern)",
        "category": "incomplete_code",
        "severity": ValidationSeverity.ERROR,
        "fix_hint": "All generated code should be implemented (abstract methods should use 'Subclasses must implement' message)",
    },
    {
        "id": "REG-010",
        # FIXED: Exclude valid Pydantic Field(...) syntax AND string literals
        # Field(...) with ellipsis is VALID syntax for required fields
        # "..." or '...' are valid string literals (e.g., for truncation indicators)
        # Only match standalone ... or Ellipsis not in Field() or string context
        # Bug #37 fix: Added negative lookbehind for quote characters
        "pattern": r"(?<![Ff]ield\()(?<![\"'])\.\.\.(?![\"'])(?!\s*,|\s*\))|(?<!\w)Ellipsis(?!\w)",
        "message": "Ellipsis (...) placeholder in generated code (not in Field or string context)",
        "category": "incomplete_code",
        "severity": ValidationSeverity.ERROR,
        "fix_hint": "Replace placeholder with actual implementation",
    },
]


class BasicValidationPipeline:
    """
    Fast validation pipeline that runs ALWAYS (no Docker).

    Phase 0.5.5: Pre-acceptance validation for generated code.
    """

    def __init__(self):
        self._regression_patterns = [
            (re.compile(p["pattern"], re.MULTILINE), p)
            for p in REGRESSION_PATTERNS
        ]

    def validate(self, files: Dict[str, str]) -> ValidationResult:
        """
        Validate a set of generated files.

        Args:
            files: Dict mapping file_path -> content

        Returns:
            ValidationResult with all errors and warnings
        """
        import time
        start_time = time.time()

        result = ValidationResult(passed=True, files_checked=len(files))

        for file_path, content in files.items():
            # Only validate Python files
            if not file_path.endswith('.py'):
                continue

            # 1. Syntax validation (py_compile)
            self._validate_syntax(file_path, content, result)

            # 2. Regression patterns
            self._check_regressions(file_path, content, result)

            # 3. AST analysis (dead code, structure)
            self._analyze_ast(file_path, content, result)

            # 4. Import validation
            self._validate_imports(file_path, content, result)

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    def _validate_syntax(
        self,
        file_path: str,
        content: str,
        result: ValidationResult
    ) -> None:
        """Validate Python syntax using compile()."""
        try:
            compile(content, file_path, 'exec')
        except SyntaxError as e:
            result.add_error(ValidationError(
                severity=ValidationSeverity.ERROR,
                file_path=file_path,
                line_number=e.lineno,
                message=f"Syntax error: {e.msg}",
                category="syntax",
                fix_hint=f"Fix syntax at line {e.lineno}: {e.text}" if e.text else None,
            ))

    def _check_regressions(
        self,
        file_path: str,
        content: str,
        result: ValidationResult
    ) -> None:
        """Check for known regression patterns."""
        for pattern, info in self._regression_patterns:
            matches = pattern.finditer(content)
            for match in matches:
                # Calculate line number
                line_number = content[:match.start()].count('\n') + 1

                result.add_error(ValidationError(
                    severity=info["severity"],
                    file_path=file_path,
                    line_number=line_number,
                    message=f"[{info['id']}] {info['message']}",
                    category=info["category"],
                    fix_hint=info.get("fix_hint"),
                ))

    def _analyze_ast(
        self,
        file_path: str,
        content: str,
        result: ValidationResult
    ) -> None:
        """Analyze AST for structural issues."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Already caught by syntax validation
            return

        # Check for empty classes
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if class only has pass
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    result.add_error(ValidationError(
                        severity=ValidationSeverity.WARNING,
                        file_path=file_path,
                        line_number=node.lineno,
                        message=f"Empty class: {node.name}",
                        category="dead_code",
                        fix_hint="Add class content or remove if unused",
                    ))

            # Check for empty functions (except __init__ with pass)
            if isinstance(node, ast.FunctionDef):
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    if node.name != "__init__":
                        result.add_error(ValidationError(
                            severity=ValidationSeverity.WARNING,
                            file_path=file_path,
                            line_number=node.lineno,
                            message=f"Empty function: {node.name}",
                            category="dead_code",
                            fix_hint="Implement function or remove if unused",
                        ))

    def _validate_imports(
        self,
        file_path: str,
        content: str,
        result: ValidationResult
    ) -> None:
        """Validate import statements."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return

        for node in ast.walk(tree):
            # Check for * imports
            if isinstance(node, ast.ImportFrom):
                if node.names and any(alias.name == '*' for alias in node.names):
                    result.add_error(ValidationError(
                        severity=ValidationSeverity.WARNING,
                        file_path=file_path,
                        line_number=node.lineno,
                        message=f"Wildcard import: from {node.module} import *",
                        category="import_style",
                        fix_hint="Use explicit imports instead of wildcard",
                    ))

    def validate_single_file(
        self,
        file_path: str,
        content: str
    ) -> ValidationResult:
        """Validate a single file."""
        return self.validate({file_path: content})


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_pipeline: Optional[BasicValidationPipeline] = None


def get_validation_pipeline() -> BasicValidationPipeline:
    """Get singleton validation pipeline."""
    global _pipeline
    if _pipeline is None:
        _pipeline = BasicValidationPipeline()
    return _pipeline


def validate_generated_files(files: Dict[str, str]) -> ValidationResult:
    """
    Validate generated files using the basic pipeline.

    Args:
        files: Dict of file_path -> content

    Returns:
        ValidationResult
    """
    return get_validation_pipeline().validate(files)


def validate_code(code: str, file_path: str = "generated.py") -> ValidationResult:
    """
    Validate a single code string.

    Args:
        code: Python code to validate
        file_path: Virtual file path for reporting

    Returns:
        ValidationResult
    """
    return get_validation_pipeline().validate_single_file(file_path, code)


def quick_syntax_check(code: str) -> Tuple[bool, Optional[str]]:
    """
    Quick syntax check without full pipeline.

    Args:
        code: Python code to check

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        compile(code, "<string>", "exec")
        return (True, None)
    except SyntaxError as e:
        return (False, f"Line {e.lineno}: {e.msg}")
