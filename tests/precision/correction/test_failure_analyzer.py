"""
Unit Tests for FailureAnalyzer

Tests failure analysis, root cause identification, and atom mapping.
"""

import pytest
from pathlib import Path
from tests.precision.correction.failure_analyzer import (
    FailureAnalyzer,
    FailureAnalysis,
)
from tests.precision.validators.code_validator import TestResult


class TestErrorCategorization:
    """Test error pattern matching and categorization."""

    def test_categorize_missing_function_attribute_error(self):
        """Should categorize AttributeError as missing_function."""
        analyzer = FailureAnalyzer()

        error_message = "AttributeError: 'API' object has no attribute 'create_user'"
        stack_trace = "  File test.py, line 10\n    api.create_user()\nAttributeError"

        category = analyzer._categorize_error(error_message, stack_trace)

        assert category == "missing_function"

    def test_categorize_missing_function_name_error(self):
        """Should categorize NameError as missing_function."""
        analyzer = FailureAnalyzer()

        error_message = "NameError: name 'validate_email' is not defined"
        stack_trace = "  File test.py, line 15\n    validate_email()\nNameError"

        category = analyzer._categorize_error(error_message, stack_trace)

        assert category == "missing_function"

    def test_categorize_wrong_logic_assertion(self):
        """Should categorize AssertionError as wrong_logic."""
        analyzer = FailureAnalyzer()

        error_message = "AssertionError: expected True but got False"
        stack_trace = "  File test.py, line 20\n    assert result == True"

        category = analyzer._categorize_error(error_message, stack_trace)

        assert category == "wrong_logic"

    def test_categorize_validation_error(self):
        """Should categorize ValueError as validation_error."""
        analyzer = FailureAnalyzer()

        error_message = "ValueError: email must be valid format"
        stack_trace = "  File test.py, line 25\n    validate(email)"

        category = analyzer._categorize_error(error_message, stack_trace)

        assert category == "validation_error"

    def test_categorize_type_error(self):
        """Should categorize TypeError as type_error."""
        analyzer = FailureAnalyzer()

        error_message = "TypeError: expected str but got int"
        stack_trace = "  File test.py, line 30\n    process(123)"

        category = analyzer._categorize_error(error_message, stack_trace)

        assert category == "type_error"

    def test_categorize_import_error(self):
        """Should categorize ImportError as import_error."""
        analyzer = FailureAnalyzer()

        error_message = "ModuleNotFoundError: No module named 'requests'"
        stack_trace = "  File test.py, line 1\n    import requests"

        category = analyzer._categorize_error(error_message, stack_trace)

        assert category == "import_error"

    def test_categorize_unknown_error(self):
        """Should return 'unknown' for unrecognized errors."""
        analyzer = FailureAnalyzer()

        error_message = "WeirdError: something strange happened"
        stack_trace = "  File test.py, line 50"

        category = analyzer._categorize_error(error_message, stack_trace)

        assert category == "unknown"


class TestRootCauseIdentification:
    """Test root cause analysis logic."""

    def test_root_cause_missing_function(self):
        """Should identify missing function from error message."""
        analyzer = FailureAnalyzer()

        error_message = "AttributeError: 'User' object has no attribute 'validate'"
        root_cause = analyzer._identify_root_cause(
            error_message, "", "missing_function"
        )

        assert "Missing function or attribute: validate" in root_cause

    def test_root_cause_wrong_logic(self):
        """Should identify logic error."""
        analyzer = FailureAnalyzer()

        root_cause = analyzer._identify_root_cause(
            "AssertionError: 5 != 3", "", "wrong_logic"
        )

        assert "Logic error" in root_cause

    def test_root_cause_validation_error(self):
        """Should identify validation error."""
        analyzer = FailureAnalyzer()

        root_cause = analyzer._identify_root_cause(
            "ValueError: invalid email", "", "validation_error"
        )

        assert "Validation error" in root_cause

    def test_root_cause_type_error(self):
        """Should identify type error."""
        analyzer = FailureAnalyzer()

        root_cause = analyzer._identify_root_cause(
            "TypeError: expected int", "", "type_error"
        )

        assert "Type error" in root_cause

    def test_root_cause_import_error(self):
        """Should identify import error."""
        analyzer = FailureAnalyzer()

        root_cause = analyzer._identify_root_cause(
            "ImportError: No module named 'foo'", "", "import_error"
        )

        assert "Import error" in root_cause

    def test_root_cause_unknown(self):
        """Should return error message for unknown category."""
        analyzer = FailureAnalyzer()

        error_message = "Strange error occurred"
        root_cause = analyzer._identify_root_cause(error_message, "", "unknown")

        assert "Strange error occurred" in root_cause


class TestSeverityDetermination:
    """Test severity level calculation."""

    def test_severity_must_missing_function(self):
        """Should mark must requirement missing function as critical."""
        analyzer = FailureAnalyzer()

        severity = analyzer._determine_severity("missing_function", "must")

        assert severity == "critical"

    def test_severity_must_import_error(self):
        """Should mark must requirement import error as critical."""
        analyzer = FailureAnalyzer()

        severity = analyzer._determine_severity("import_error", "must")

        assert severity == "critical"

    def test_severity_must_wrong_logic(self):
        """Should mark must requirement wrong logic as high."""
        analyzer = FailureAnalyzer()

        severity = analyzer._determine_severity("wrong_logic", "must")

        assert severity == "high"

    def test_severity_should_missing_function(self):
        """Should mark should requirement missing function as medium."""
        analyzer = FailureAnalyzer()

        severity = analyzer._determine_severity("missing_function", "should")

        assert severity == "medium"

    def test_severity_should_validation_error(self):
        """Should mark should requirement validation error as low."""
        analyzer = FailureAnalyzer()

        severity = analyzer._determine_severity("validation_error", "should")

        assert severity == "low"


class TestAtomMapping:
    """Test atom mapping logic."""

    def test_map_atoms_with_requirement_id(self):
        """Should generate atom IDs based on requirement ID."""
        analyzer = FailureAnalyzer()

        atoms = analyzer._map_to_atoms(
            error_message="AttributeError: missing method",
            stack_trace="  File test.py, line 10",
            requirement_id=5,
            code_dir=None,
        )

        assert len(atoms) >= 2
        assert "atom-req005-impl-001" in atoms
        assert "atom-req005-validation-001" in atoms

    def test_map_atoms_with_stack_trace_functions(self):
        """Should extract function names from stack trace."""
        analyzer = FailureAnalyzer()

        stack_trace = """
  File api.py, line 10, in create_user()
  File db.py, line 25, in save_user()
"""

        atoms = analyzer._map_to_atoms(
            error_message="Error",
            stack_trace=stack_trace,
            requirement_id=3,
            code_dir=None,
        )

        # Should include base atoms + function atoms
        assert len(atoms) >= 4
        assert any("create_user" in atom for atom in atoms)
        assert any("save_user" in atom for atom in atoms)

    def test_map_atoms_no_requirement_id(self):
        """Should return empty list when requirement_id is None."""
        analyzer = FailureAnalyzer()

        atoms = analyzer._map_to_atoms(
            error_message="Error",
            stack_trace="",
            requirement_id=None,
            code_dir=None,
        )

        assert atoms == []


class TestFixSuggestions:
    """Test fix suggestion generation."""

    def test_suggestions_missing_function(self):
        """Should suggest implementing missing function."""
        analyzer = FailureAnalyzer()

        error_message = "AttributeError: 'API' object has no attribute 'create_user'"

        suggestions = analyzer._generate_fix_suggestions(
            "missing_function", error_message, "Missing function: create_user"
        )

        assert len(suggestions) > 0
        assert any("create_user" in s for s in suggestions)
        assert any("Implement" in s for s in suggestions)

    def test_suggestions_wrong_logic(self):
        """Should suggest reviewing logic."""
        analyzer = FailureAnalyzer()

        suggestions = analyzer._generate_fix_suggestions(
            "wrong_logic", "AssertionError", "Logic error"
        )

        assert len(suggestions) > 0
        assert any("logic" in s.lower() for s in suggestions)
        assert any("return values" in s.lower() for s in suggestions)

    def test_suggestions_validation_error(self):
        """Should suggest adding validation."""
        analyzer = FailureAnalyzer()

        suggestions = analyzer._generate_fix_suggestions(
            "validation_error", "ValueError", "Validation error"
        )

        assert len(suggestions) > 0
        assert any("validation" in s.lower() for s in suggestions)

    def test_suggestions_type_error(self):
        """Should suggest fixing signatures."""
        analyzer = FailureAnalyzer()

        suggestions = analyzer._generate_fix_suggestions(
            "type_error", "TypeError", "Type error"
        )

        assert len(suggestions) > 0
        assert any("type" in s.lower() for s in suggestions)

    def test_suggestions_import_error(self):
        """Should suggest adding imports."""
        analyzer = FailureAnalyzer()

        suggestions = analyzer._generate_fix_suggestions(
            "import_error", "ImportError", "Import error"
        )

        assert len(suggestions) > 0
        assert any("import" in s.lower() for s in suggestions)


class TestPriorityCalculation:
    """Test regeneration priority scoring."""

    def test_priority_critical_severity(self):
        """Should give priority 10 for critical severity."""
        analyzer = FailureAnalyzer()

        priority = analyzer._calculate_priority("critical", "missing_function", 2)

        assert priority == 10

    def test_priority_high_severity(self):
        """Should give priority 7 for high severity."""
        analyzer = FailureAnalyzer()

        priority = analyzer._calculate_priority("high", "wrong_logic", 2)

        assert priority == 7

    def test_priority_medium_severity(self):
        """Should give priority 5 for medium severity."""
        analyzer = FailureAnalyzer()

        priority = analyzer._calculate_priority("medium", "validation_error", 2)

        assert priority == 5

    def test_priority_boost_for_critical_errors(self):
        """Should boost priority for missing_function or import_error."""
        analyzer = FailureAnalyzer()

        priority_missing = analyzer._calculate_priority(
            "medium", "missing_function", 2
        )
        priority_import = analyzer._calculate_priority("medium", "import_error", 2)

        assert priority_missing > 5
        assert priority_import > 5

    def test_priority_boost_for_many_atoms(self):
        """Should boost priority when many atoms are affected."""
        analyzer = FailureAnalyzer()

        priority = analyzer._calculate_priority("medium", "wrong_logic", 5)

        assert priority > 5

    def test_priority_max_10(self):
        """Should never exceed priority 10."""
        analyzer = FailureAnalyzer()

        priority = analyzer._calculate_priority("critical", "import_error", 10)

        assert priority == 10


class TestFailureAnalysis:
    """Test complete failure analysis workflow."""

    def test_analyze_single_failure(self):
        """Should analyze single test failure completely."""
        analyzer = FailureAnalyzer()

        test_result = TestResult(
            test_name="test_requirement_001_create_user",
            status="failed",
            duration=0.5,
            error_message="AttributeError: 'API' object has no attribute 'create_user'",
            stack_trace="  File test_001.py, line 10, in test_requirement_001\n    api.create_user()\nAttributeError",
            requirement_id=1,
            requirement_type="must",
        )

        analysis = analyzer._analyze_single_failure(test_result, None)

        assert analysis.test_name == "test_requirement_001_create_user"
        assert analysis.requirement_id == 1
        assert analysis.error_type == "AttributeError"
        assert analysis.error_category == "missing_function"
        assert analysis.severity == "critical"
        assert len(analysis.suspected_atoms) > 0
        assert len(analysis.fix_suggestions) > 0
        assert analysis.regeneration_priority >= 1
        assert analysis.regeneration_priority <= 10

    def test_analyze_multiple_failures(self):
        """Should analyze multiple failures and sort by priority."""
        analyzer = FailureAnalyzer()

        test_results = [
            TestResult(
                test_name="test_001",
                status="failed",
                duration=0.5,
                error_message="AttributeError: missing method",
                stack_trace="",
                requirement_id=1,
                requirement_type="must",
            ),
            TestResult(
                test_name="test_002",
                status="failed",
                duration=0.3,
                error_message="AssertionError: wrong value",
                stack_trace="",
                requirement_id=2,
                requirement_type="should",
            ),
        ]

        analyses = analyzer.analyze_failures(test_results)

        assert len(analyses) == 2
        # Should be sorted by priority (critical must > medium should)
        assert analyses[0].severity in ["critical", "high"]
        assert analyses[1].severity in ["medium", "low"]

    def test_analyze_skips_passed_tests(self):
        """Should skip passed tests."""
        analyzer = FailureAnalyzer()

        test_results = [
            TestResult(
                test_name="test_001",
                status="passed",
                duration=0.5,
                requirement_id=1,
                requirement_type="must",
            ),
            TestResult(
                test_name="test_002",
                status="failed",
                duration=0.3,
                error_message="Error",
                stack_trace="",
                requirement_id=2,
                requirement_type="must",
            ),
        ]

        analyses = analyzer.analyze_failures(test_results)

        assert len(analyses) == 1
        assert analyses[0].test_name == "test_002"


class TestSummaryReport:
    """Test summary report generation."""

    def test_generate_report_with_failures(self):
        """Should generate markdown report with failure analysis."""
        analyzer = FailureAnalyzer()

        test_results = [
            TestResult(
                test_name="test_001",
                status="failed",
                duration=0.5,
                error_message="AttributeError: missing method",
                stack_trace="",
                requirement_id=1,
                requirement_type="must",
            ),
            TestResult(
                test_name="test_002",
                status="failed",
                duration=0.3,
                error_message="AssertionError: wrong value",
                stack_trace="",
                requirement_id=2,
                requirement_type="should",
            ),
        ]

        analyses = analyzer.analyze_failures(test_results)
        report = analyzer.generate_summary_report(analyses)

        assert "Failure Analysis Report" in report
        assert "**Total Failures:** 2" in report
        assert "Severity Breakdown" in report
        assert "Error Categories" in report
        assert "Top Priority Failures" in report

    def test_generate_report_no_failures(self):
        """Should return success message when no failures."""
        analyzer = FailureAnalyzer()

        report = analyzer.generate_summary_report([])

        assert "No failures to analyze" in report

    def test_report_includes_severity_icons(self):
        """Should include visual severity indicators."""
        analyzer = FailureAnalyzer()

        test_results = [
            TestResult(
                test_name="test_critical",
                status="failed",
                duration=0.5,
                error_message="ImportError: module missing",
                stack_trace="",
                requirement_id=1,
                requirement_type="must",
            ),
        ]

        analyses = analyzer.analyze_failures(test_results)
        report = analyzer.generate_summary_report(analyses)

        # Should include emoji severity indicators
        assert "🔴" in report or "critical" in report.lower()

    def test_report_shows_top_5_failures(self):
        """Should limit report to top 5 priority failures."""
        analyzer = FailureAnalyzer()

        # Create 10 failures
        test_results = [
            TestResult(
                test_name=f"test_{i:03d}",
                status="failed",
                duration=0.5,
                error_message="Error",
                stack_trace="",
                requirement_id=i,
                requirement_type="must",
            )
            for i in range(10)
        ]

        analyses = analyzer.analyze_failures(test_results)
        report = analyzer.generate_summary_report(analyses)

        # Should show total 10 but detail only top 5
        assert "**Total Failures:** 10" in report
        # Count how many "### N." headings appear (top N failures)
        failure_headings = report.count("###")
        assert failure_headings == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
