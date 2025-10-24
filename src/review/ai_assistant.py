"""
AIAssistant - AI-powered review assistance

Provides AI-generated suggestions for code review:
- Issue detection
- Fix suggestions
- Alternative implementations
- Issue explanations
- Quality scoring

Author: DevMatrix Team
Date: 2025-10-24
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import re

from ..models import AtomicUnit, ValidationResult
from ..atomization.parser import MultiLanguageParser


@dataclass
class Issue:
    """Detected code issue"""
    type: str  # "syntax" | "logic" | "style" | "performance" | "security"
    severity: str  # "critical" | "high" | "medium" | "low"
    description: str
    line_number: Optional[int]
    code_snippet: Optional[str]


@dataclass
class FixSuggestion:
    """Fix suggestion for an issue"""
    issue_type: str
    suggested_fix: str
    code_before: str
    code_after: str
    explanation: str
    quality_score: float  # 0.0-1.0


class AIAssistant:
    """
    AI-powered code review assistant.

    Capabilities:
    - Detect common code issues
    - Suggest fixes with explanations
    - Generate alternative implementations
    - Quality score suggestions
    """

    def __init__(self):
        self.parser = MultiLanguageParser()

        # Issue patterns for detection
        self.ISSUE_PATTERNS = {
            "python": {
                "unused_import": r"^import\s+(\w+)",
                "global_var": r"global\s+\w+",
                "bare_except": r"except:",
                "print_statement": r"print\(",
                "hardcoded_path": r"['\"]\/[^'\"]*['\"]",
            },
            "typescript": {
                "any_type": r":\s*any",
                "console_log": r"console\.log\(",
                "var_keyword": r"\bvar\b",
            },
            "javascript": {
                "var_keyword": r"\bvar\b",
                "console_log": r"console\.log\(",
                "==_operator": r"==(?!=)",
            }
        }

    def detect_issues(self, atom: AtomicUnit) -> List[Issue]:
        """
        Detect issues in atom code.

        Args:
            atom: AtomicUnit to analyze

        Returns:
            List of detected issues
        """
        issues = []
        code = atom.code_to_generate

        # Pattern-based detection
        language = atom.language.lower()
        if language in self.ISSUE_PATTERNS:
            for issue_type, pattern in self.ISSUE_PATTERNS[language].items():
                matches = re.finditer(pattern, code, re.MULTILINE)
                for match in matches:
                    line_num = code[:match.start()].count('\n') + 1
                    issues.append(Issue(
                        type="style",
                        severity=self._get_severity(issue_type),
                        description=self._get_description(issue_type),
                        line_number=line_num,
                        code_snippet=match.group(0)
                    ))

        # Complexity check
        if atom.complexity >= 5.0:
            issues.append(Issue(
                type="performance",
                severity="medium",
                description=f"High complexity ({atom.complexity:.1f}), consider refactoring",
                line_number=None,
                code_snippet=None
            ))

        # Long function check
        loc = len([l for l in code.split('\n') if l.strip()])
        if loc > 15:
            issues.append(Issue(
                type="style",
                severity="low",
                description=f"Function too long ({loc} LOC), target is ≤15",
                line_number=None,
                code_snippet=None
            ))

        return issues

    def suggest_fixes(self, atom: AtomicUnit, issue: Issue) -> List[FixSuggestion]:
        """
        Generate fix suggestions for an issue.

        Args:
            atom: AtomicUnit with the issue
            issue: Issue to fix

        Returns:
            List of fix suggestions
        """
        suggestions = []

        # Pattern-based suggestions
        if issue.code_snippet:
            if "print(" in issue.code_snippet:
                suggestions.append(FixSuggestion(
                    issue_type="print_statement",
                    suggested_fix="Use logging instead of print",
                    code_before=issue.code_snippet,
                    code_after=issue.code_snippet.replace("print(", "logger.info("),
                    explanation="Use proper logging framework for production code",
                    quality_score=0.9
                ))

            elif "except:" in issue.code_snippet:
                suggestions.append(FixSuggestion(
                    issue_type="bare_except",
                    suggested_fix="Specify exception type",
                    code_before=issue.code_snippet,
                    code_after="except Exception:",
                    explanation="Bare except catches too much, specify exception types",
                    quality_score=0.95
                ))

            elif "var " in issue.code_snippet:
                suggestions.append(FixSuggestion(
                    issue_type="var_keyword",
                    suggested_fix="Use let or const instead of var",
                    code_before=issue.code_snippet,
                    code_after=issue.code_snippet.replace("var ", "const "),
                    explanation="var has function scope, use let/const for block scope",
                    quality_score=0.9
                ))

            elif "console.log(" in issue.code_snippet:
                suggestions.append(FixSuggestion(
                    issue_type="console_log",
                    suggested_fix="Remove console.log or use logger",
                    code_before=issue.code_snippet,
                    code_after="// " + issue.code_snippet,
                    explanation="Remove debug statements from production code",
                    quality_score=0.85
                ))

            elif ": any" in issue.code_snippet:
                suggestions.append(FixSuggestion(
                    issue_type="any_type",
                    suggested_fix="Use specific type instead of any",
                    code_before=issue.code_snippet,
                    code_after=issue.code_snippet.replace(": any", ": unknown"),
                    explanation="'any' disables type checking, use specific types",
                    quality_score=0.9
                ))

        # Complexity suggestions
        if issue.type == "performance" and "complexity" in issue.description.lower():
            suggestions.append(FixSuggestion(
                issue_type="high_complexity",
                suggested_fix="Extract nested logic into helper functions",
                code_before=atom.code_to_generate,
                code_after="# See alternative implementation below",
                explanation="Break down complex function into smaller, testable units",
                quality_score=0.85
            ))

        return suggestions

    def generate_alternatives(self, atom: AtomicUnit) -> List[str]:
        """
        Generate alternative implementations.

        Args:
            atom: AtomicUnit to generate alternatives for

        Returns:
            List of alternative code implementations
        """
        alternatives = []
        code = atom.code_to_generate

        # Simplification alternatives for complex code
        if atom.complexity >= 5.0:
            alternatives.append(
                "# Alternative 1: Extract helper functions\n"
                "# Break down complex logic into smaller functions\n"
                "# This improves testability and reduces complexity"
            )

        # Pattern alternatives
        if "for " in code and atom.language == "python":
            alternatives.append(
                "# Alternative 2: Use list comprehension\n"
                "# More Pythonic and often more efficient"
            )

        if "if" in code and "else" in code:
            alternatives.append(
                "# Alternative 3: Use early returns\n"
                "# Reduce nesting depth with guard clauses"
            )

        return alternatives

    def explain_issue(self, issue: Issue) -> str:
        """
        Generate detailed explanation for an issue.

        Args:
            issue: Issue to explain

        Returns:
            Detailed explanation string
        """
        explanations = {
            "print_statement": (
                "Print statements are not suitable for production code. "
                "Use a proper logging framework (e.g., Python's logging module) "
                "which provides log levels, formatting, and output control."
            ),
            "bare_except": (
                "Bare except clauses catch all exceptions including system exits "
                "and keyboard interrupts. Always specify exception types to catch "
                "only expected errors."
            ),
            "var_keyword": (
                "The 'var' keyword has function scope and can lead to unexpected "
                "behavior. Use 'let' for variables that change and 'const' for "
                "constants to enforce block scope."
            ),
            "console_log": (
                "Console.log statements should be removed from production code. "
                "Use a proper logging library or remove debug statements before "
                "committing."
            ),
            "any_type": (
                "The 'any' type disables TypeScript's type checking. Use specific "
                "types or 'unknown' with type guards for type safety."
            ),
            "high_complexity": (
                "High cyclomatic complexity indicates code that is difficult to "
                "test and maintain. Consider extracting nested logic into helper "
                "functions and using guard clauses to reduce nesting."
            ),
        }

        # Try to match issue type
        for key in explanations:
            if key in issue.description.lower():
                return explanations[key]

        # Generic explanation
        return (
            f"{issue.type.capitalize()} issue: {issue.description}. "
            f"Severity: {issue.severity}. Review and address as needed."
        )

    def quality_score_suggestion(self, suggestion: FixSuggestion) -> float:
        """
        Calculate quality score for a suggestion.

        Args:
            suggestion: FixSuggestion to score

        Returns:
            Quality score 0.0-1.0
        """
        # Already calculated in the suggestion
        return suggestion.quality_score

    def analyze_atom_for_review(self, atom: AtomicUnit) -> Dict:
        """
        Comprehensive analysis for review UI.

        Args:
            atom: AtomicUnit to analyze

        Returns:
            Dictionary with issues, suggestions, alternatives, and explanations
        """
        issues = self.detect_issues(atom)

        suggestions_by_issue = {}
        for issue in issues:
            suggestions = self.suggest_fixes(atom, issue)
            if suggestions:
                suggestions_by_issue[issue.description] = suggestions

        alternatives = self.generate_alternatives(atom)

        return {
            "atom_id": atom.atom_id,
            "total_issues": len(issues),
            "issues_by_severity": {
                "critical": sum(1 for i in issues if i.severity == "critical"),
                "high": sum(1 for i in issues if i.severity == "high"),
                "medium": sum(1 for i in issues if i.severity == "medium"),
                "low": sum(1 for i in issues if i.severity == "low"),
            },
            "issues": [
                {
                    "type": i.type,
                    "severity": i.severity,
                    "description": i.description,
                    "line_number": i.line_number,
                    "code_snippet": i.code_snippet,
                    "explanation": self.explain_issue(i)
                }
                for i in issues
            ],
            "suggestions": suggestions_by_issue,
            "alternatives": alternatives,
            "recommendation": self._get_recommendation(issues, atom)
        }

    def _get_severity(self, issue_type: str) -> str:
        """Get severity for issue type"""
        severity_map = {
            "bare_except": "high",
            "any_type": "high",
            "print_statement": "medium",
            "console_log": "medium",
            "var_keyword": "medium",
            "unused_import": "low",
            "hardcoded_path": "medium",
            "==_operator": "low",
        }
        return severity_map.get(issue_type, "low")

    def _get_description(self, issue_type: str) -> str:
        """Get description for issue type"""
        desc_map = {
            "bare_except": "Bare except clause catches too much",
            "any_type": "Using 'any' type disables type checking",
            "print_statement": "Print statement in production code",
            "console_log": "Console.log in production code",
            "var_keyword": "Using 'var' instead of 'let'/'const'",
            "unused_import": "Unused import statement",
            "hardcoded_path": "Hardcoded file path",
            "==_operator": "Using '==' instead of '==='",
            "global_var": "Global variable usage",
        }
        return desc_map.get(issue_type, f"Issue: {issue_type}")

    def _get_recommendation(self, issues: List[Issue], atom: AtomicUnit) -> str:
        """Get overall recommendation"""
        critical = sum(1 for i in issues if i.severity == "critical")
        high = sum(1 for i in issues if i.severity == "high")

        if critical > 0:
            return "REJECT - Critical issues must be fixed"
        elif high > 2:
            return "EDIT REQUIRED - Multiple high-severity issues detected"
        elif len(issues) > 5:
            return "REVIEW CAREFULLY - Many issues detected"
        elif len(issues) > 0:
            return "MINOR EDITS - Address style/minor issues"
        else:
            return "APPROVE - No issues detected"
