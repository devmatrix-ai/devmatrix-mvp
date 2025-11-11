"""
Tests for AIAssistant

Verifies error analysis and fix suggestion generation.
"""

import pytest
from uuid import uuid4

from src.mge.v2.review.ai_assistant import (
    AIAssistant,
    CodeIssue,
    FixSuggestion,
    IssueType,
    IssueSeverity
)


@pytest.fixture
def assistant():
    """Create AIAssistant instance"""
    return AIAssistant()


@pytest.fixture
def sample_code():
    """Sample Python code for testing"""
    return """
def calculate_total(items):
    total = 0
    for item in items:
        if item.price > 0:
            total += item.price
    return total
"""


class TestAIAssistant:
    """Test AIAssistant functionality"""

    def test_analyze_syntax_error(self, assistant):
        """Test syntax error analysis"""
        validation_results = {
            "l1_syntax": {
                "error": "SyntaxError: invalid syntax at line 3"
            }
        }

        code = "def foo():\n    print('hello'\nreturn True"

        issues = assistant.analyze_validation_errors(validation_results, code)

        assert len(issues) == 1
        assert issues[0].issue_type == IssueType.SYNTAX_ERROR
        assert issues[0].severity == IssueSeverity.CRITICAL
        assert issues[0].line_number == 3

    def test_analyze_indentation_error(self, assistant):
        """Test indentation error analysis"""
        validation_results = {
            "l1_syntax": {
                "error": "IndentationError: unindent does not match any outer indentation level"
            }
        }

        code = "def foo():\nprint('hello')"

        issues = assistant.analyze_validation_errors(validation_results, code)

        assert len(issues) == 1
        assert issues[0].issue_type == IssueType.SYNTAX_ERROR
        assert issues[0].severity == IssueSeverity.CRITICAL
        assert "indentation" in issues[0].message.lower()

    def test_analyze_import_error_no_module(self, assistant):
        """Test import error - module not found"""
        validation_results = {
            "l2_imports": {
                "error": "ImportError: No module named 'nonexistent'"
            }
        }

        code = "import nonexistent"

        issues = assistant.analyze_validation_errors(validation_results, code)

        assert len(issues) == 1
        assert issues[0].issue_type == IssueType.IMPORT_ERROR
        assert issues[0].severity == IssueSeverity.HIGH
        assert "nonexistent" in issues[0].message

    def test_analyze_import_error_cannot_import_name(self, assistant):
        """Test import error - name not found"""
        validation_results = {
            "l2_imports": {
                "error": "ImportError: cannot import name 'FooBar' from 'module'"
            }
        }

        code = "from module import FooBar"

        issues = assistant.analyze_validation_errors(validation_results, code)

        assert len(issues) == 1
        assert issues[0].issue_type == IssueType.IMPORT_ERROR
        assert issues[0].severity == IssueSeverity.HIGH
        assert "FooBar" in issues[0].message

    def test_analyze_type_error_no_attribute(self, assistant):
        """Test type error - attribute not found"""
        validation_results = {
            "l3_types": {
                "errors": [
                    {
                        "message": "AttributeError: 'int' object has no attribute 'append'",
                        "line": 5
                    }
                ]
            }
        }

        code = sample_code = "x = 5\nx.append(10)"

        issues = assistant.analyze_validation_errors(validation_results, code)

        assert len(issues) == 1
        assert issues[0].issue_type == IssueType.TYPE_ERROR
        assert issues[0].severity == IssueSeverity.HIGH
        assert issues[0].line_number == 5

    def test_analyze_type_error_mismatch(self, assistant):
        """Test type error - type mismatch"""
        validation_results = {
            "l3_types": {
                "errors": [
                    {
                        "message": "TypeError: expected str, got int",
                        "line": 10
                    }
                ]
            }
        }

        code = "name: str = 123"

        issues = assistant.analyze_validation_errors(validation_results, code)

        assert len(issues) == 1
        assert issues[0].issue_type == IssueType.TYPE_ERROR
        assert issues[0].line_number == 10

    def test_analyze_complexity_high_cyclomatic(self, assistant):
        """Test high cyclomatic complexity"""
        validation_results = {
            "l4_complexity": {
                "cyclomatic_complexity": 25,
                "cognitive_complexity": 10
            }
        }

        code = "def complex_function():\n    pass"

        issues = assistant.analyze_validation_errors(validation_results, code)

        assert len(issues) == 1
        assert issues[0].issue_type == IssueType.COMPLEXITY_HIGH
        assert issues[0].severity == IssueSeverity.MEDIUM
        assert "cyclomatic" in issues[0].message.lower()
        assert "25" in issues[0].message

    def test_analyze_complexity_high_cognitive(self, assistant):
        """Test high cognitive complexity"""
        validation_results = {
            "l4_complexity": {
                "cyclomatic_complexity": 10,
                "cognitive_complexity": 35
            }
        }

        code = "def complex_function():\n    pass"

        issues = assistant.analyze_validation_errors(validation_results, code)

        assert len(issues) == 1
        assert issues[0].issue_type == IssueType.COMPLEXITY_HIGH
        assert "cognitive" in issues[0].message.lower()
        assert "35" in issues[0].message

    def test_analyze_multiple_errors(self, assistant):
        """Test multiple errors simultaneously"""
        validation_results = {
            "l1_syntax": {
                "error": "SyntaxError: invalid syntax"
            },
            "l2_imports": {
                "error": "ImportError: No module named 'foo'"
            },
            "l4_complexity": {
                "cyclomatic_complexity": 25
            }
        }

        code = "import foo\ndef bar(\npass"

        issues = assistant.analyze_validation_errors(validation_results, code)

        # Should detect 3 issues: syntax, import, complexity
        assert len(issues) == 3

        issue_types = [i.issue_type for i in issues]
        assert IssueType.SYNTAX_ERROR in issue_types
        assert IssueType.IMPORT_ERROR in issue_types
        assert IssueType.COMPLEXITY_HIGH in issue_types

    def test_suggest_fix_syntax_error_colon(self, assistant):
        """Test fix suggestion for missing colon"""
        issue = CodeIssue(
            issue_type=IssueType.SYNTAX_ERROR,
            severity=IssueSeverity.CRITICAL,
            line_number=3,
            column_number=None,
            message="SyntaxError: invalid syntax (missing colon)"
        )

        code = "def foo()\n    pass"

        suggestion = assistant.suggest_fix(issue, code)

        assert "colon" in suggestion.primary_fix.lower()
        assert suggestion.quality_score >= 80.0
        assert suggestion.estimated_effort == "trivial"
        assert len(suggestion.alternatives) > 0

    def test_suggest_fix_syntax_error_indentation(self, assistant):
        """Test fix suggestion for indentation"""
        issue = CodeIssue(
            issue_type=IssueType.SYNTAX_ERROR,
            severity=IssueSeverity.CRITICAL,
            line_number=2,
            column_number=None,
            message="IndentationError: inconsistent indentation"
        )

        code = "def foo():\nprint('hello')"

        suggestion = assistant.suggest_fix(issue, code)

        assert "indentation" in suggestion.primary_fix.lower()
        assert suggestion.quality_score >= 80.0
        assert suggestion.estimated_effort == "trivial"

    def test_suggest_fix_import_error_no_module(self, assistant):
        """Test fix suggestion for missing module"""
        issue = CodeIssue(
            issue_type=IssueType.IMPORT_ERROR,
            severity=IssueSeverity.HIGH,
            line_number=None,
            column_number=None,
            message="ImportError: No module named 'requests'"
        )

        code = "import requests"

        suggestion = assistant.suggest_fix(issue, code, context=None)

        assert "install" in suggestion.primary_fix.lower() or "pip" in suggestion.primary_fix.lower()
        assert suggestion.quality_score >= 75.0
        assert suggestion.estimated_effort in ["trivial", "simple"]

    def test_suggest_fix_type_error_attribute(self, assistant):
        """Test fix suggestion for attribute error"""
        issue = CodeIssue(
            issue_type=IssueType.TYPE_ERROR,
            severity=IssueSeverity.HIGH,
            line_number=5,
            column_number=None,
            message="AttributeError: 'int' object has no attribute 'append'"
        )

        code = "x = 5\nx.append(10)"

        suggestion = assistant.suggest_fix(issue, code)

        assert "attribute" in suggestion.primary_fix.lower()
        assert suggestion.quality_score >= 75.0
        assert suggestion.estimated_effort == "simple"
        assert len(suggestion.alternatives) > 0

    def test_suggest_fix_type_error_mismatch(self, assistant):
        """Test fix suggestion for type mismatch"""
        issue = CodeIssue(
            issue_type=IssueType.TYPE_ERROR,
            severity=IssueSeverity.HIGH,
            line_number=10,
            column_number=None,
            message="Type error: expected str, got int"
        )

        code = "name: str = 123"

        suggestion = assistant.suggest_fix(issue, code)

        assert "convert" in suggestion.primary_fix.lower() or "type" in suggestion.primary_fix.lower()
        assert suggestion.quality_score >= 75.0
        assert suggestion.estimated_effort == "simple"

    def test_suggest_fix_complexity_cyclomatic(self, assistant):
        """Test fix suggestion for cyclomatic complexity"""
        issue = CodeIssue(
            issue_type=IssueType.COMPLEXITY_HIGH,
            severity=IssueSeverity.MEDIUM,
            line_number=None,
            column_number=None,
            message="Cyclomatic complexity too high: 25 (threshold: 20)"
        )

        code = "def complex_function():\n    pass"

        suggestion = assistant.suggest_fix(issue, code)

        assert "refactor" in suggestion.primary_fix.lower()
        assert "function" in suggestion.primary_fix.lower()
        assert suggestion.quality_score >= 70.0
        assert suggestion.estimated_effort in ["moderate", "complex"]
        assert len(suggestion.alternatives) >= 2

    def test_suggest_fix_complexity_cognitive(self, assistant):
        """Test fix suggestion for cognitive complexity"""
        issue = CodeIssue(
            issue_type=IssueType.COMPLEXITY_HIGH,
            severity=IssueSeverity.MEDIUM,
            line_number=None,
            column_number=None,
            message="Cognitive complexity too high: 35 (threshold: 30)"
        )

        code = "def complex_function():\n    pass"

        suggestion = assistant.suggest_fix(issue, code)

        assert "simplify" in suggestion.primary_fix.lower() or "refactor" in suggestion.primary_fix.lower()
        assert suggestion.quality_score >= 70.0
        assert suggestion.estimated_effort in ["moderate", "complex"]

    def test_extract_code_snippet(self, assistant, sample_code):
        """Test code snippet extraction"""
        line_number = 4  # Middle line

        snippet = assistant._extract_code_snippet(sample_code, line_number, context_lines=2)

        # Should include lines 2-6 (line 4 ± 2)
        assert "for item in items:" in snippet
        assert "if item.price > 0:" in snippet
        assert "total += item.price" in snippet

        # Should have line numbers
        assert "2 |" in snippet or "3 |" in snippet
        assert "4 |" in snippet
        assert "5 |" in snippet or "6 |" in snippet

    def test_extract_code_snippet_boundary(self, assistant):
        """Test code snippet extraction at file boundaries"""
        code = "line1\nline2\nline3"

        # First line
        snippet_start = assistant._extract_code_snippet(code, 1, context_lines=2)
        assert "line1" in snippet_start
        assert "line2" in snippet_start

        # Last line
        snippet_end = assistant._extract_code_snippet(code, 3, context_lines=2)
        assert "line2" in snippet_end
        assert "line3" in snippet_end

    def test_extract_code_snippet_invalid_line(self, assistant):
        """Test code snippet extraction with invalid line number"""
        code = "line1\nline2\nline3"

        # Line number too high
        snippet = assistant._extract_code_snippet(code, 100, context_lines=2)
        assert snippet == ""

        # Line number too low
        snippet = assistant._extract_code_snippet(code, 0, context_lines=2)
        assert snippet == ""

    def test_code_issue_to_dict(self):
        """Test CodeIssue serialization"""
        issue = CodeIssue(
            issue_type=IssueType.SYNTAX_ERROR,
            severity=IssueSeverity.CRITICAL,
            line_number=10,
            column_number=5,
            message="Test error",
            code_snippet="test code",
            file_path="test.py"
        )

        issue_dict = issue.to_dict()

        assert issue_dict["issue_type"] == "syntax_error"
        assert issue_dict["severity"] == "critical"
        assert issue_dict["line_number"] == 10
        assert issue_dict["column_number"] == 5
        assert issue_dict["message"] == "Test error"
        assert issue_dict["code_snippet"] == "test code"
        assert issue_dict["file_path"] == "test.py"

    def test_fix_suggestion_to_dict(self):
        """Test FixSuggestion serialization"""
        suggestion = FixSuggestion(
            primary_fix="Fix this way",
            alternatives=["Alternative 1", "Alternative 2"],
            explanation="Here's why",
            quality_score=85.5,
            estimated_effort="simple"
        )

        suggestion_dict = suggestion.to_dict()

        assert suggestion_dict["primary_fix"] == "Fix this way"
        assert len(suggestion_dict["alternatives"]) == 2
        assert suggestion_dict["explanation"] == "Here's why"
        assert suggestion_dict["quality_score"] == 85.5
        assert suggestion_dict["estimated_effort"] == "simple"

    def test_quality_scores_range(self, assistant):
        """Test that quality scores are within 0-100 range"""
        issue_types = [
            IssueType.SYNTAX_ERROR,
            IssueType.IMPORT_ERROR,
            IssueType.TYPE_ERROR,
            IssueType.COMPLEXITY_HIGH
        ]

        code = "test code"

        for issue_type in issue_types:
            issue = CodeIssue(
                issue_type=issue_type,
                severity=IssueSeverity.HIGH,
                line_number=1,
                column_number=None,
                message="Test error"
            )

            suggestion = assistant.suggest_fix(issue, code)

            assert 0 <= suggestion.quality_score <= 100

    def test_effort_estimation_values(self, assistant):
        """Test that effort estimations use valid values"""
        valid_efforts = {"trivial", "simple", "moderate", "complex"}

        issue_types = [
            IssueType.SYNTAX_ERROR,
            IssueType.IMPORT_ERROR,
            IssueType.TYPE_ERROR,
            IssueType.COMPLEXITY_HIGH
        ]

        code = "test code"

        for issue_type in issue_types:
            issue = CodeIssue(
                issue_type=issue_type,
                severity=IssueSeverity.HIGH,
                line_number=1,
                column_number=None,
                message="Test error"
            )

            suggestion = assistant.suggest_fix(issue, code)

            assert suggestion.estimated_effort in valid_efforts
