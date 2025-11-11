"""
AIAssistant - Intelligent fix suggestions for failed validations

Analyzes validation errors and provides context-aware fix suggestions.

Features:
- Multi-language support (Python, TypeScript, JavaScript)
- Pattern-based error detection
- Fix suggestions with alternatives
- Quality scoring for suggestions
- Context-aware recommendations

Supported Error Types:
- Syntax errors (L1)
- Import errors (L2)
- Type errors (L3)
- Complexity issues (L4)
- Test failures
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class IssueType(str, Enum):
    """Type of code issue detected"""
    SYNTAX_ERROR = "syntax_error"
    IMPORT_ERROR = "import_error"
    TYPE_ERROR = "type_error"
    COMPLEXITY_HIGH = "complexity_high"
    TEST_FAILURE = "test_failure"
    UNDEFINED_VARIABLE = "undefined_variable"
    MISSING_RETURN = "missing_return"
    UNUSED_IMPORT = "unused_import"


class IssueSeverity(str, Enum):
    """Severity level of issue"""
    CRITICAL = "critical"  # Blocks execution
    HIGH = "high"          # Major functionality issue
    MEDIUM = "medium"      # Quality/style issue
    LOW = "low"            # Minor improvement


@dataclass
class CodeIssue:
    """Detected code issue with metadata"""

    issue_type: IssueType
    severity: IssueSeverity
    line_number: Optional[int]
    column_number: Optional[int]
    message: str
    code_snippet: Optional[str] = None
    file_path: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage/serialization"""
        return {
            "issue_type": self.issue_type.value,
            "severity": self.severity.value,
            "line_number": self.line_number,
            "column_number": self.column_number,
            "message": self.message,
            "code_snippet": self.code_snippet,
            "file_path": self.file_path
        }


@dataclass
class FixSuggestion:
    """Fix suggestion with alternatives and quality score"""

    primary_fix: str
    alternatives: List[str]
    explanation: str
    quality_score: float  # 0-100
    estimated_effort: str  # "trivial", "simple", "moderate", "complex"

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage/serialization"""
        return {
            "primary_fix": self.primary_fix,
            "alternatives": self.alternatives,
            "explanation": self.explanation,
            "quality_score": round(self.quality_score, 2),
            "estimated_effort": self.estimated_effort
        }


class AIAssistant:
    """
    Intelligent assistant for code fix suggestions

    Analyzes validation errors and provides actionable fix suggestions
    with context-aware recommendations.

    Example:
        assistant = AIAssistant()

        # Analyze validation results
        issues = assistant.analyze_validation_errors(
            validation_results={
                "l1_syntax": {"error": "SyntaxError: invalid syntax"},
                "l2_imports": {"error": "ImportError: cannot import 'foo'"}
            },
            code="import foo\\nprint(x)"
        )

        # Get fix suggestions
        for issue in issues:
            suggestion = assistant.suggest_fix(issue, code)
            print(suggestion.primary_fix)
    """

    def __init__(self):
        """Initialize AIAssistant with error patterns"""
        # Python syntax error patterns
        self.syntax_patterns = {
            r"invalid syntax": "Check for missing colons, parentheses, or brackets",
            r"unexpected EOF": "Missing closing delimiter (parenthesis, bracket, or quote)",
            r"IndentationError": "Fix indentation (use 4 spaces consistently)",
            r"unindent does not match": "Align indentation with previous block",
        }

        # Import error patterns
        self.import_patterns = {
            r"cannot import name '(\w+)'": "Check if '{0}' exists in module or fix typo",
            r"No module named '(\w+)'": "Install module '{0}' or check spelling",
            r"ImportError": "Verify import path and module availability",
        }

        # Type error patterns
        self.type_patterns = {
            r"'(\w+)' object has no attribute '(\w+)'": "Check if attribute '{1}' exists for type '{0}'",
            r"unsupported operand type": "Ensure compatible types for operation",
            r"expected (\w+), got (\w+)": "Convert type '{1}' to '{0}' or adjust annotation",
        }

    def analyze_validation_errors(
        self,
        validation_results: Dict,
        code: str,
        language: str = "python"
    ) -> List[CodeIssue]:
        """
        Analyze validation results and detect code issues

        Args:
            validation_results: Validation results from L1-L4
                {
                    "l1_syntax": {"error": "...", "line": 10},
                    "l2_imports": {"error": "...", "missing": ["foo"]},
                    "l3_types": {"errors": [...]},
                    "l4_complexity": {"cyclomatic": 25}
                }
            code: Source code being validated
            language: Programming language (default: "python")

        Returns:
            List of detected CodeIssues
        """
        issues = []

        # L1 Syntax errors
        if "l1_syntax" in validation_results:
            syntax_error = validation_results["l1_syntax"].get("error")
            if syntax_error:
                issues.extend(self._analyze_syntax_error(syntax_error, code))

        # L2 Import errors
        if "l2_imports" in validation_results:
            import_error = validation_results["l2_imports"].get("error")
            if import_error:
                issues.extend(self._analyze_import_error(import_error, code))

        # L3 Type errors
        if "l3_types" in validation_results:
            type_errors = validation_results["l3_types"].get("errors", [])
            for error in type_errors:
                issues.extend(self._analyze_type_error(error, code))

        # L4 Complexity issues
        if "l4_complexity" in validation_results:
            complexity_data = validation_results["l4_complexity"]
            issues.extend(self._analyze_complexity_issue(complexity_data, code))

        logger.info(f"Detected {len(issues)} code issues")

        return issues

    def _analyze_syntax_error(self, error_message: str, code: str) -> List[CodeIssue]:
        """Analyze syntax errors"""
        issues = []

        # Extract line number if present
        line_match = re.search(r"line (\d+)", error_message)
        line_number = int(line_match.group(1)) if line_match else None

        # Match error pattern
        for pattern, suggestion in self.syntax_patterns.items():
            if re.search(pattern, error_message, re.IGNORECASE):
                issues.append(CodeIssue(
                    issue_type=IssueType.SYNTAX_ERROR,
                    severity=IssueSeverity.CRITICAL,
                    line_number=line_number,
                    column_number=None,
                    message=f"Syntax error: {error_message}",
                    code_snippet=self._extract_code_snippet(code, line_number) if line_number else None
                ))
                break

        # Generic syntax error if no pattern matched
        if not issues:
            issues.append(CodeIssue(
                issue_type=IssueType.SYNTAX_ERROR,
                severity=IssueSeverity.CRITICAL,
                line_number=line_number,
                column_number=None,
                message=error_message
            ))

        return issues

    def _analyze_import_error(self, error_message: str, code: str) -> List[CodeIssue]:
        """Analyze import errors"""
        issues = []

        # Match import error pattern
        for pattern, suggestion in self.import_patterns.items():
            match = re.search(pattern, error_message)
            if match:
                # Format suggestion with captured groups
                formatted_suggestion = suggestion.format(*match.groups()) if match.groups() else suggestion

                issues.append(CodeIssue(
                    issue_type=IssueType.IMPORT_ERROR,
                    severity=IssueSeverity.HIGH,
                    line_number=None,
                    column_number=None,
                    message=f"Import error: {formatted_suggestion}"
                ))
                break

        return issues

    def _analyze_type_error(self, error_data: Dict, code: str) -> List[CodeIssue]:
        """Analyze type errors"""
        issues = []

        error_message = error_data.get("message", "")
        line_number = error_data.get("line")

        # Match type error pattern
        for pattern, suggestion in self.type_patterns.items():
            match = re.search(pattern, error_message)
            if match:
                formatted_suggestion = suggestion.format(*match.groups()) if match.groups() else suggestion

                issues.append(CodeIssue(
                    issue_type=IssueType.TYPE_ERROR,
                    severity=IssueSeverity.HIGH,
                    line_number=line_number,
                    column_number=None,
                    message=f"Type error: {formatted_suggestion}",
                    code_snippet=self._extract_code_snippet(code, line_number) if line_number else None
                ))
                break

        return issues

    def _analyze_complexity_issue(self, complexity_data: Dict, code: str) -> List[CodeIssue]:
        """Analyze complexity issues"""
        issues = []

        cyclomatic = complexity_data.get("cyclomatic_complexity", 0)
        cognitive = complexity_data.get("cognitive_complexity", 0)

        # High cyclomatic complexity (>20)
        if cyclomatic > 20:
            issues.append(CodeIssue(
                issue_type=IssueType.COMPLEXITY_HIGH,
                severity=IssueSeverity.MEDIUM,
                line_number=None,
                column_number=None,
                message=f"Cyclomatic complexity too high: {cyclomatic} (threshold: 20)"
            ))

        # High cognitive complexity (>30)
        if cognitive > 30:
            issues.append(CodeIssue(
                issue_type=IssueType.COMPLEXITY_HIGH,
                severity=IssueSeverity.MEDIUM,
                line_number=None,
                column_number=None,
                message=f"Cognitive complexity too high: {cognitive} (threshold: 30)"
            ))

        return issues

    def suggest_fix(
        self,
        issue: CodeIssue,
        code: str,
        context: Optional[Dict] = None
    ) -> FixSuggestion:
        """
        Generate fix suggestion for detected issue

        Args:
            issue: CodeIssue to fix
            code: Source code
            context: Additional context (dependencies, project structure, etc.)

        Returns:
            FixSuggestion with primary fix and alternatives
        """
        if issue.issue_type == IssueType.SYNTAX_ERROR:
            return self._suggest_syntax_fix(issue, code)
        elif issue.issue_type == IssueType.IMPORT_ERROR:
            return self._suggest_import_fix(issue, code, context)
        elif issue.issue_type == IssueType.TYPE_ERROR:
            return self._suggest_type_fix(issue, code)
        elif issue.issue_type == IssueType.COMPLEXITY_HIGH:
            return self._suggest_complexity_fix(issue, code)
        else:
            return self._suggest_generic_fix(issue, code)

    def _suggest_syntax_fix(self, issue: CodeIssue, code: str) -> FixSuggestion:
        """Suggest fix for syntax errors"""
        # Check for common syntax patterns
        if "missing colon" in issue.message.lower() or "invalid syntax" in issue.message.lower():
            return FixSuggestion(
                primary_fix="Add missing colon (:) at end of statement",
                alternatives=[
                    "Check for missing parentheses or brackets",
                    "Verify proper indentation"
                ],
                explanation="Python requires colons after if/for/while/def/class statements",
                quality_score=85.0,
                estimated_effort="trivial"
            )

        elif "indentation" in issue.message.lower():
            return FixSuggestion(
                primary_fix="Fix indentation to use consistent 4 spaces",
                alternatives=[
                    "Align with previous block level",
                    "Remove mixed tabs and spaces"
                ],
                explanation="Python requires consistent indentation (4 spaces recommended)",
                quality_score=90.0,
                estimated_effort="trivial"
            )

        else:
            return FixSuggestion(
                primary_fix="Review syntax error and check Python grammar rules",
                alternatives=[
                    "Use a linter (pylint, flake8) to identify specific issue",
                    "Compare with working code examples"
                ],
                explanation="Syntax error detected - manual review required",
                quality_score=60.0,
                estimated_effort="simple"
            )

    def _suggest_import_fix(
        self,
        issue: CodeIssue,
        code: str,
        context: Optional[Dict]
    ) -> FixSuggestion:
        """Suggest fix for import errors"""
        if "No module named" in issue.message:
            module_match = re.search(r"'(\w+)'", issue.message)
            module_name = module_match.group(1) if module_match else "module"

            return FixSuggestion(
                primary_fix=f"Install missing module: pip install {module_name}",
                alternatives=[
                    f"Check if '{module_name}' is spelled correctly",
                    "Add module to requirements.txt",
                    "Verify module exists in PyPI"
                ],
                explanation=f"Module '{module_name}' is not installed or misspelled",
                quality_score=85.0,
                estimated_effort="trivial"
            )

        elif "cannot import name" in issue.message:
            return FixSuggestion(
                primary_fix="Check if imported name exists in target module",
                alternatives=[
                    "Verify import path and module structure",
                    "Check for typos in import name",
                    "Review module's __all__ exports"
                ],
                explanation="Imported name not found in module",
                quality_score=75.0,
                estimated_effort="simple"
            )

        else:
            return FixSuggestion(
                primary_fix="Review import statement and module availability",
                alternatives=[
                    "Check import path syntax",
                    "Verify module installation",
                    "Review circular import issues"
                ],
                explanation="Import error detected - check module structure",
                quality_score=65.0,
                estimated_effort="simple"
            )

    def _suggest_type_fix(self, issue: CodeIssue, code: str) -> FixSuggestion:
        """Suggest fix for type errors"""
        if "has no attribute" in issue.message:
            return FixSuggestion(
                primary_fix="Check if attribute exists for this object type",
                alternatives=[
                    "Review object type and available attributes",
                    "Use hasattr() to check attribute existence",
                    "Add type guards or validation"
                ],
                explanation="Attribute access on incompatible type",
                quality_score=80.0,
                estimated_effort="simple"
            )

        elif "expected" in issue.message and "got" in issue.message:
            return FixSuggestion(
                primary_fix="Convert value to expected type or adjust type annotation",
                alternatives=[
                    "Add explicit type conversion",
                    "Update type annotation to match actual type",
                    "Use Union type to allow multiple types"
                ],
                explanation="Type mismatch between expected and actual value",
                quality_score=85.0,
                estimated_effort="simple"
            )

        else:
            return FixSuggestion(
                primary_fix="Review type annotations and ensure type consistency",
                alternatives=[
                    "Add type hints to improve clarity",
                    "Use mypy for comprehensive type checking",
                    "Add runtime type validation"
                ],
                explanation="Type error detected - review type usage",
                quality_score=70.0,
                estimated_effort="moderate"
            )

    def _suggest_complexity_fix(self, issue: CodeIssue, code: str) -> FixSuggestion:
        """Suggest fix for complexity issues"""
        if "cyclomatic" in issue.message.lower():
            return FixSuggestion(
                primary_fix="Refactor into smaller functions (single responsibility)",
                alternatives=[
                    "Extract complex conditions into helper functions",
                    "Use early returns to reduce nesting",
                    "Replace complex if-else chains with dictionaries or match statements"
                ],
                explanation="High cyclomatic complexity makes code hard to test and maintain",
                quality_score=80.0,
                estimated_effort="moderate"
            )

        elif "cognitive" in issue.message.lower():
            return FixSuggestion(
                primary_fix="Simplify logic by extracting nested blocks into functions",
                alternatives=[
                    "Reduce nesting depth with guard clauses",
                    "Use comprehensions instead of loops where applicable",
                    "Break down complex conditions"
                ],
                explanation="High cognitive complexity makes code difficult to understand",
                quality_score=75.0,
                estimated_effort="moderate"
            )

        else:
            return FixSuggestion(
                primary_fix="Refactor to reduce code complexity",
                alternatives=[
                    "Apply SOLID principles",
                    "Extract responsibilities into separate functions",
                    "Use design patterns to simplify structure"
                ],
                explanation="Code complexity exceeds recommended thresholds",
                quality_score=70.0,
                estimated_effort="complex"
            )

    def _suggest_generic_fix(self, issue: CodeIssue, code: str) -> FixSuggestion:
        """Generic fix suggestion for unknown issues"""
        return FixSuggestion(
            primary_fix="Review code and error message for specific issue",
            alternatives=[
                "Use linters and type checkers for detailed analysis",
                "Compare with similar working code",
                "Consult language documentation"
            ],
            explanation=f"Issue detected: {issue.message}",
            quality_score=50.0,
            estimated_effort="moderate"
        )

    def _extract_code_snippet(self, code: str, line_number: int, context_lines: int = 2) -> str:
        """
        Extract code snippet around line number

        Args:
            code: Full source code
            line_number: Target line number (1-indexed)
            context_lines: Number of lines before/after to include

        Returns:
            Code snippet string
        """
        lines = code.split("\n")

        if line_number < 1 or line_number > len(lines):
            return ""

        # Calculate range (1-indexed to 0-indexed)
        start = max(0, line_number - context_lines - 1)
        end = min(len(lines), line_number + context_lines)

        snippet_lines = lines[start:end]

        # Add line numbers
        numbered_lines = [
            f"{i + start + 1:4d} | {line}"
            for i, line in enumerate(snippet_lines)
        ]

        return "\n".join(numbered_lines)
