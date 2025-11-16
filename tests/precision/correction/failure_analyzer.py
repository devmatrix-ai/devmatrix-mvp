"""
Failure Analyzer

Analyzes test failures to identify root causes and problematic atoms.

Architecture:
    Test Failures + Stack Traces + Code → Analysis → Root Causes + Atom Mapping

Features:
    - Stack trace parsing and analysis
    - Error pattern recognition
    - Atom-level failure mapping
    - Priority classification (critical/high/medium/low)
    - Fix suggestions generation
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from collections import Counter


@dataclass
class FailureAnalysis:
    """Analysis of a single test failure."""

    test_name: str
    requirement_id: Optional[int]
    error_type: str  # "AssertionError" | "ValueError" | "AttributeError" | etc
    error_message: str
    stack_trace: str

    # Root cause analysis
    root_cause: str
    error_category: str  # "missing_function" | "wrong_logic" | "validation_error" | etc
    severity: str  # "critical" | "high" | "medium" | "low"

    # Atom mapping
    suspected_atoms: List[str]  # List of atom IDs that might be problematic
    affected_requirements: List[int]

    # Fix suggestions
    fix_suggestions: List[str]
    regeneration_priority: int  # 1-10, 10 = highest priority


class FailureAnalyzer:
    """
    Analyzes test failures to identify root causes and problematic code.

    Provides detailed analysis for auto-correction system.
    """

    def __init__(self):
        """Initialize failure analyzer."""
        # Common error patterns for categorization
        self.error_patterns = {
            "missing_function": [
                r"AttributeError.*has no attribute '(\w+)'",
                r"NameError.*name '(\w+)' is not defined",
            ],
            "wrong_logic": [
                r"AssertionError.*expected (\w+) but got (\w+)",
                r"AssertionError.*(\d+) != (\d+)",
            ],
            "validation_error": [
                r"ValueError.*must be.*",
                r"ValueError.*invalid.*",
            ],
            "type_error": [
                r"TypeError.*expected.*got.*",
                r"TypeError.*takes.*positional argument",
            ],
            "import_error": [
                r"ImportError.*No module named.*",
                r"ModuleNotFoundError.*",
            ],
        }

    def analyze_failures(
        self,
        test_results: List[Any],
        code_dir: Optional[Path] = None,
    ) -> List[FailureAnalysis]:
        """
        Analyze all test failures and identify root causes.

        Args:
            test_results: List of TestResult objects from validator
            code_dir: Directory with generated code (optional, for code analysis)

        Returns:
            List of FailureAnalysis objects with detailed diagnostics
        """
        analyses = []

        for test_result in test_results:
            if test_result.status in ["failed", "error"]:
                analysis = self._analyze_single_failure(test_result, code_dir)
                analyses.append(analysis)

        # Sort by priority (highest first)
        analyses.sort(key=lambda a: a.regeneration_priority, reverse=True)

        return analyses

    def _analyze_single_failure(
        self, test_result: Any, code_dir: Optional[Path]
    ) -> FailureAnalysis:
        """
        Analyze a single test failure.

        Args:
            test_result: TestResult object
            code_dir: Code directory for additional context

        Returns:
            FailureAnalysis with root cause and suggestions
        """
        # Extract basic info
        test_name = test_result.test_name
        requirement_id = test_result.requirement_id
        error_message = test_result.error_message or "Unknown error"
        stack_trace = test_result.stack_trace or ""

        # Categorize error
        error_type = self._extract_error_type(error_message)
        error_category = self._categorize_error(error_message, stack_trace)

        # Determine root cause
        root_cause = self._identify_root_cause(
            error_message, stack_trace, error_category
        )

        # Determine severity
        severity = self._determine_severity(error_category, test_result.requirement_type)

        # Map to suspected atoms
        suspected_atoms = self._map_to_atoms(
            error_message, stack_trace, requirement_id, code_dir
        )

        # Identify affected requirements
        affected_requirements = [requirement_id] if requirement_id else []

        # Generate fix suggestions
        fix_suggestions = self._generate_fix_suggestions(
            error_category, error_message, root_cause
        )

        # Calculate regeneration priority
        priority = self._calculate_priority(severity, error_category, len(suspected_atoms))

        return FailureAnalysis(
            test_name=test_name,
            requirement_id=requirement_id,
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            root_cause=root_cause,
            error_category=error_category,
            severity=severity,
            suspected_atoms=suspected_atoms,
            affected_requirements=affected_requirements,
            fix_suggestions=fix_suggestions,
            regeneration_priority=priority,
        )

    def _extract_error_type(self, error_message: str) -> str:
        """Extract error type from error message."""
        # Match pattern like "AssertionError: ..."
        match = re.match(r"^(\w+Error|\w+Exception):", error_message)
        if match:
            return match.group(1)
        return "UnknownError"

    def _categorize_error(self, error_message: str, stack_trace: str) -> str:
        """
        Categorize error based on patterns.

        Returns:
            Error category string
        """
        full_text = f"{error_message}\n{stack_trace}"

        for category, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, full_text, re.IGNORECASE):
                    return category

        # Default category
        return "unknown"

    def _identify_root_cause(
        self, error_message: str, stack_trace: str, category: str
    ) -> str:
        """
        Identify human-readable root cause.

        Args:
            error_message: Error message
            stack_trace: Stack trace
            category: Error category

        Returns:
            Root cause description
        """
        if category == "missing_function":
            # Extract function/attribute name
            match = re.search(r"has no attribute '(\w+)'", error_message)
            if match:
                return f"Missing function or attribute: {match.group(1)}"
            return "Required function/method not implemented"

        elif category == "wrong_logic":
            return "Logic error: Incorrect implementation of requirement"

        elif category == "validation_error":
            return "Validation error: Input validation not properly implemented"

        elif category == "type_error":
            return "Type error: Incorrect data types or function signatures"

        elif category == "import_error":
            return "Import error: Missing module or incorrect imports"

        else:
            # Generic root cause from error message
            return f"Error: {error_message[:100]}"

    def _determine_severity(self, error_category: str, requirement_type: Optional[str]) -> str:
        """
        Determine severity of failure.

        Args:
            error_category: Category of error
            requirement_type: "must" or "should"

        Returns:
            Severity level: "critical" | "high" | "medium" | "low"
        """
        # Must requirements are always critical or high
        if requirement_type == "must":
            if error_category in ["missing_function", "import_error"]:
                return "critical"
            else:
                return "high"

        # Should requirements
        if error_category in ["missing_function", "wrong_logic"]:
            return "medium"
        else:
            return "low"

    def _map_to_atoms(
        self,
        error_message: str,
        stack_trace: str,
        requirement_id: Optional[int],
        code_dir: Optional[Path],
    ) -> List[str]:
        """
        Map failure to suspected atoms.

        In real implementation, this would use atom metadata to identify
        which atoms are responsible for the failing requirement.

        Args:
            error_message: Error message
            stack_trace: Stack trace
            requirement_id: Requirement ID that failed
            code_dir: Code directory

        Returns:
            List of atom IDs
        """
        # TODO: Integrate with MGE V2 atom metadata
        # For now, generate placeholder atom IDs based on requirement

        if requirement_id is None:
            return []

        # Mock atom mapping (in production, query from DB)
        # Format: atom-{module}-{requirement_id}-{sub_id}
        suspected_atoms = [
            f"atom-req{requirement_id:03d}-impl-001",  # Main implementation atom
            f"atom-req{requirement_id:03d}-validation-001",  # Validation atom
        ]

        # Extract function names from stack trace for more specific mapping
        function_matches = re.findall(r"in (\w+)\(", stack_trace)
        if function_matches:
            # Add atoms related to specific functions
            for func in function_matches[:2]:  # Limit to 2 most relevant
                suspected_atoms.append(f"atom-func-{func}")

        return suspected_atoms

    def _generate_fix_suggestions(
        self, error_category: str, error_message: str, root_cause: str
    ) -> List[str]:
        """
        Generate actionable fix suggestions.

        Args:
            error_category: Category of error
            error_message: Original error message
            root_cause: Identified root cause

        Returns:
            List of fix suggestions
        """
        suggestions = []

        if error_category == "missing_function":
            # Extract function name if possible
            match = re.search(r"has no attribute '(\w+)'", error_message)
            if match:
                func_name = match.group(1)
                suggestions.append(f"Implement missing function: {func_name}()")
                suggestions.append(
                    f"Add {func_name} method to the class with correct signature"
                )
            else:
                suggestions.append("Implement all required functions from specification")

        elif error_category == "wrong_logic":
            suggestions.append("Review and correct the business logic implementation")
            suggestions.append("Ensure return values match specification requirements")
            suggestions.append("Add proper error handling and edge case coverage")

        elif error_category == "validation_error":
            suggestions.append("Add input validation with proper error messages")
            suggestions.append("Implement precondition checks before operations")
            suggestions.append("Use guard clauses for invalid inputs")

        elif error_category == "type_error":
            suggestions.append("Fix function signatures to match specification")
            suggestions.append("Add type hints for better type safety")
            suggestions.append("Ensure correct data types for all parameters and returns")

        elif error_category == "import_error":
            suggestions.append("Add missing import statements")
            suggestions.append("Check module structure and file organization")

        else:
            suggestions.append(f"Address: {root_cause}")
            suggestions.append("Review specification and regenerate code")

        return suggestions

    def _calculate_priority(
        self, severity: str, error_category: str, atom_count: int
    ) -> int:
        """
        Calculate regeneration priority (1-10, 10 = highest).

        Args:
            severity: Severity level
            error_category: Error category
            atom_count: Number of suspected atoms

        Returns:
            Priority score 1-10
        """
        # Base priority by severity
        severity_scores = {
            "critical": 10,
            "high": 7,
            "medium": 5,
            "low": 3,
        }

        priority = severity_scores.get(severity, 5)

        # Adjust by error category
        if error_category in ["missing_function", "import_error"]:
            priority = min(10, priority + 1)  # Boost priority

        # Adjust by atom count (more atoms = more complex, higher priority)
        if atom_count > 3:
            priority = min(10, priority + 1)

        return priority

    def generate_summary_report(self, analyses: List[FailureAnalysis]) -> str:
        """
        Generate human-readable summary report of failures.

        Args:
            analyses: List of failure analyses

        Returns:
            Markdown formatted report
        """
        if not analyses:
            return "✅ No failures to analyze"

        report = []
        report.append("# Failure Analysis Report\n")
        report.append(f"**Total Failures:** {len(analyses)}\n")

        # Severity breakdown
        severity_counts = Counter(a.severity for a in analyses)
        report.append("## Severity Breakdown")
        for severity in ["critical", "high", "medium", "low"]:
            count = severity_counts.get(severity, 0)
            if count > 0:
                icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}[severity]
                report.append(f"- {icon} {severity.upper()}: {count}")
        report.append("")

        # Category breakdown
        category_counts = Counter(a.error_category for a in analyses)
        report.append("## Error Categories")
        for category, count in category_counts.most_common():
            report.append(f"- {category}: {count}")
        report.append("")

        # Top priority failures
        report.append("## Top Priority Failures (Regeneration Order)\n")
        for i, analysis in enumerate(analyses[:5], 1):  # Top 5
            report.append(f"### {i}. {analysis.test_name}")
            report.append(f"**Priority:** {analysis.regeneration_priority}/10")
            report.append(f"**Severity:** {analysis.severity.upper()}")
            report.append(f"**Root Cause:** {analysis.root_cause}")
            report.append(f"**Suspected Atoms:** {', '.join(analysis.suspected_atoms)}")
            report.append("\n**Fix Suggestions:**")
            for suggestion in analysis.fix_suggestions:
                report.append(f"- {suggestion}")
            report.append("")

        return "\n".join(report)


# Example usage
if __name__ == "__main__":
    from tests.precision.validators.code_validator import TestResult

    # Mock test failures
    test_results = [
        TestResult(
            test_name="test_requirement_001_create_user",
            status="failed",
            duration=0.5,
            error_message="AttributeError: 'API' object has no attribute 'create_user'",
            stack_trace="  File test_001.py, line 10, in test_requirement_001\n    api.create_user()\nAttributeError",
            requirement_id=1,
            requirement_type="must",
        ),
        TestResult(
            test_name="test_requirement_002_validate_email",
            status="failed",
            duration=0.3,
            error_message="AssertionError: expected True but got False",
            stack_trace="  File test_002.py, line 15, in test_requirement_002\n    assert result == True\nAssertionError",
            requirement_id=2,
            requirement_type="should",
        ),
    ]

    analyzer = FailureAnalyzer()
    analyses = analyzer.analyze_failures(test_results)

    # Generate report
    report = analyzer.generate_summary_report(analyses)
    print(report)
