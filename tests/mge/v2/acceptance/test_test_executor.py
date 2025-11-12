"""
Tests for AcceptanceTestExecutor - Execute tests and apply gates

Tests cover:
- Test execution with MUST/SHOULD gates
- Report generation and statistics
- Gate pass/fail logic
- Test status tracking
"""

import pytest
from datetime import datetime
from uuid import uuid4

from src.mge.v2.acceptance.test_executor import (
    AcceptanceTestExecutor,
    TestStatus,
    TestResult,
    ExecutionReport
)
from src.mge.v2.acceptance.test_generator import (
    AcceptanceTest,
    TestType
)
from src.mge.v2.metrics.precision_scorer import RequirementPriority


@pytest.fixture
def executor():
    """Create AcceptanceTestExecutor instance"""
    return AcceptanceTestExecutor()


@pytest.fixture
def masterplan_id():
    """Generate test masterplan ID"""
    return uuid4()


@pytest.fixture
def sample_must_test():
    """Create sample MUST requirement test"""
    return AcceptanceTest(
        test_id="TEST-001",
        test_type=TestType.CASE,
        requirement_id="REQ-MUST-001",
        requirement_priority=RequirementPriority.MUST,
        description="Critical login test",
        test_code="async def test_case_001(): assert True",
        expected_outcome="Login successful",
        preconditions=["System running"],
        postconditions=["User logged in"]
    )


@pytest.fixture
def sample_should_test():
    """Create sample SHOULD requirement test"""
    return AcceptanceTest(
        test_id="TEST-002",
        test_type=TestType.CASE,
        requirement_id="REQ-SHOULD-001",
        requirement_priority=RequirementPriority.SHOULD,
        description="Nice to have feature",
        test_code="async def test_case_002(): assert True",
        expected_outcome="Feature works",
        preconditions=["Feature enabled"],
        postconditions=["No errors"]
    )


# ============================================================
# Test: Basic Execution
# ============================================================

def test_execute_single_test(executor, masterplan_id, sample_must_test):
    """Test executing single acceptance test"""

    report = executor.execute_tests(
        masterplan_id=masterplan_id,
        wave_number=1,
        tests=[sample_must_test]
    )

    assert report.masterplan_id == masterplan_id
    assert report.wave_number == 1
    assert report.total_tests == 1
    assert report.passed_tests == 1
    assert len(report.test_results) == 1


def test_execute_multiple_tests(executor, masterplan_id, sample_must_test, sample_should_test):
    """Test executing multiple acceptance tests"""

    report = executor.execute_tests(
        masterplan_id=masterplan_id,
        wave_number=1,
        tests=[sample_must_test, sample_should_test]
    )

    assert report.total_tests == 2
    assert report.passed_tests == 2
    assert len(report.test_results) == 2


# ============================================================
# Test: MUST Gate Logic
# ============================================================

def test_must_gate_passes_with_100_percent(executor, masterplan_id):
    """Test MUST gate passes when 100% of MUST tests pass"""

    must_tests = [
        AcceptanceTest(
            test_id=f"TEST-{i}",
            test_type=TestType.CASE,
            requirement_id=f"REQ-MUST-{i}",
            requirement_priority=RequirementPriority.MUST,
            description="Must requirement",
            test_code="async def test(): assert True",
            expected_outcome="Pass",
            preconditions=[],
            postconditions=[]
        )
        for i in range(1, 4)
    ]

    report = executor.execute_tests(
        masterplan_id=masterplan_id,
        wave_number=1,
        tests=must_tests
    )

    assert report.must_total == 3
    assert report.must_passed == 3
    assert report.must_failed == 0
    assert report.must_gate_passed is True
    assert report.overall_gate_passed is True


def test_must_gate_fails_with_less_than_100_percent(executor, masterplan_id):
    """Test MUST gate fails when any MUST test fails"""

    must_tests = [
        AcceptanceTest(
            test_id="TEST-1",
            test_type=TestType.CASE,
            requirement_id="REQ-MUST-1",
            requirement_priority=RequirementPriority.MUST,
            description="Must requirement",
            test_code="async def test(): assert True",
            expected_outcome="Pass",
            preconditions=[],
            postconditions=[]
        ),
        AcceptanceTest(
            test_id="TEST-2",
            test_type=TestType.CASE,
            requirement_id="REQ-MUST-2",
            requirement_priority=RequirementPriority.MUST,
            description="Must requirement fail",  # Contains "fail" keyword
            test_code="async def test(): assert True",
            expected_outcome="Pass",
            preconditions=[],
            postconditions=[]
        )
    ]

    report = executor.execute_tests(
        masterplan_id=masterplan_id,
        wave_number=1,
        tests=must_tests
    )

    assert report.must_total == 2
    assert report.must_passed == 1
    assert report.must_failed == 1
    assert report.must_gate_passed is False
    assert report.overall_gate_passed is False


# ============================================================
# Test: SHOULD Gate Logic
# ============================================================

def test_should_gate_passes_with_95_percent(executor, masterplan_id):
    """Test SHOULD gate passes with ≥95% pass rate"""

    # 19 passing, 1 failing = 95%
    should_tests = [
        AcceptanceTest(
            test_id=f"TEST-{i}",
            test_type=TestType.CASE,
            requirement_id=f"REQ-SHOULD-{i}",
            requirement_priority=RequirementPriority.SHOULD,
            description="Should requirement" if i <= 19 else "Should requirement fail",
            test_code="async def test(): assert True",
            expected_outcome="Pass",
            preconditions=[],
            postconditions=[]
        )
        for i in range(1, 21)
    ]

    report = executor.execute_tests(
        masterplan_id=masterplan_id,
        wave_number=1,
        tests=should_tests
    )

    assert report.should_total == 20
    assert report.should_passed == 19
    assert report.should_failed == 1
    assert report.should_gate_passed is True


def test_should_gate_fails_with_less_than_95_percent(executor, masterplan_id):
    """Test SHOULD gate fails with <95% pass rate"""

    # 18 passing, 2 failing = 90%
    should_tests = [
        AcceptanceTest(
            test_id=f"TEST-{i}",
            test_type=TestType.CASE,
            requirement_id=f"REQ-SHOULD-{i}",
            requirement_priority=RequirementPriority.SHOULD,
            description="Should requirement" if i <= 18 else "Should requirement fail",
            test_code="async def test(): assert True",
            expected_outcome="Pass",
            preconditions=[],
            postconditions=[]
        )
        for i in range(1, 21)
    ]

    report = executor.execute_tests(
        masterplan_id=masterplan_id,
        wave_number=1,
        tests=should_tests
    )

    assert report.should_total == 20
    assert report.should_passed == 18
    assert report.should_failed == 2
    assert report.should_gate_passed is False
    assert report.overall_gate_passed is False


# ============================================================
# Test: Combined Gates
# ============================================================

def test_overall_gate_passes_when_both_gates_pass(executor, masterplan_id):
    """Test overall gate passes when both MUST and SHOULD gates pass"""

    tests = [
        # 2 MUST tests, all pass
        AcceptanceTest(
            test_id="TEST-M1",
            test_type=TestType.CASE,
            requirement_id="REQ-MUST-1",
            requirement_priority=RequirementPriority.MUST,
            description="Must 1",
            test_code="async def test(): assert True",
            expected_outcome="Pass",
            preconditions=[],
            postconditions=[]
        ),
        AcceptanceTest(
            test_id="TEST-M2",
            test_type=TestType.CASE,
            requirement_id="REQ-MUST-2",
            requirement_priority=RequirementPriority.MUST,
            description="Must 2",
            test_code="async def test(): assert True",
            expected_outcome="Pass",
            preconditions=[],
            postconditions=[]
        ),
        # 20 SHOULD tests, 19 pass (95%)
    ] + [
        AcceptanceTest(
            test_id=f"TEST-S{i}",
            test_type=TestType.CASE,
            requirement_id=f"REQ-SHOULD-{i}",
            requirement_priority=RequirementPriority.SHOULD,
            description="Should" if i <= 19 else "Should fail",
            test_code="async def test(): assert True",
            expected_outcome="Pass",
            preconditions=[],
            postconditions=[]
        )
        for i in range(1, 21)
    ]

    report = executor.execute_tests(
        masterplan_id=masterplan_id,
        wave_number=1,
        tests=tests
    )

    assert report.must_gate_passed is True
    assert report.should_gate_passed is True
    assert report.overall_gate_passed is True


def test_overall_gate_fails_when_either_gate_fails(executor, masterplan_id):
    """Test overall gate fails when either MUST or SHOULD gate fails"""

    tests = [
        # MUST test that fails
        AcceptanceTest(
            test_id="TEST-M1",
            test_type=TestType.CASE,
            requirement_id="REQ-MUST-1",
            requirement_priority=RequirementPriority.MUST,
            description="Must fail",
            test_code="async def test(): assert True",
            expected_outcome="Pass",
            preconditions=[],
            postconditions=[]
        ),
        # SHOULD tests all pass
        AcceptanceTest(
            test_id="TEST-S1",
            test_type=TestType.CASE,
            requirement_id="REQ-SHOULD-1",
            requirement_priority=RequirementPriority.SHOULD,
            description="Should",
            test_code="async def test(): assert True",
            expected_outcome="Pass",
            preconditions=[],
            postconditions=[]
        )
    ]

    report = executor.execute_tests(
        masterplan_id=masterplan_id,
        wave_number=1,
        tests=tests
    )

    assert report.must_gate_passed is False
    assert report.overall_gate_passed is False


# ============================================================
# Test: Statistics by Type
# ============================================================

def test_statistics_by_test_type(executor, masterplan_id):
    """Test that statistics are tracked by test type"""

    tests = [
        # Contract test
        AcceptanceTest(
            test_id="TEST-C1",
            test_type=TestType.CONTRACT,
            requirement_id="REQ-1",
            requirement_priority=RequirementPriority.MUST,
            description="Contract",
            test_code="async def test(): assert True",
            expected_outcome="Pass",
            preconditions=[],
            postconditions=[]
        ),
        # Invariant test
        AcceptanceTest(
            test_id="TEST-I1",
            test_type=TestType.INVARIANT,
            requirement_id="REQ-2",
            requirement_priority=RequirementPriority.MUST,
            description="Invariant",
            test_code="async def test(): assert True",
            expected_outcome="Pass",
            preconditions=[],
            postconditions=[]
        ),
        # Case test
        AcceptanceTest(
            test_id="TEST-CA1",
            test_type=TestType.CASE,
            requirement_id="REQ-3",
            requirement_priority=RequirementPriority.MUST,
            description="Case",
            test_code="async def test(): assert True",
            expected_outcome="Pass",
            preconditions=[],
            postconditions=[]
        )
    ]

    report = executor.execute_tests(
        masterplan_id=masterplan_id,
        wave_number=1,
        tests=tests
    )

    assert report.contract_passed == 1
    assert report.contract_failed == 0
    assert report.invariant_passed == 1
    assert report.invariant_failed == 0
    assert report.case_passed == 1
    assert report.case_failed == 0


def test_failed_tests_counted_by_type(executor, masterplan_id):
    """Test that failed tests are counted by type"""

    tests = [
        AcceptanceTest(
            test_id="TEST-C1",
            test_type=TestType.CONTRACT,
            requirement_id="REQ-1",
            requirement_priority=RequirementPriority.MUST,
            description="Contract fail",
            test_code="async def test(): assert True",
            expected_outcome="Pass",
            preconditions=[],
            postconditions=[]
        ),
        AcceptanceTest(
            test_id="TEST-I1",
            test_type=TestType.INVARIANT,
            requirement_id="REQ-2",
            requirement_priority=RequirementPriority.MUST,
            description="Invariant fail",
            test_code="async def test(): assert True",
            expected_outcome="Pass",
            preconditions=[],
            postconditions=[]
        )
    ]

    report = executor.execute_tests(
        masterplan_id=masterplan_id,
        wave_number=1,
        tests=tests
    )

    assert report.contract_failed == 1
    assert report.invariant_failed == 1


# ============================================================
# Test: Edge Cases
# ============================================================

def test_empty_test_list(executor, masterplan_id):
    """Test executing with empty test list"""

    report = executor.execute_tests(
        masterplan_id=masterplan_id,
        wave_number=1,
        tests=[]
    )

    assert report.total_tests == 0
    assert report.passed_tests == 0
    assert report.must_gate_passed is True  # No MUST tests = gate passes
    assert report.should_gate_passed is True  # No SHOULD tests = gate passes
    assert report.overall_gate_passed is True


def test_only_must_requirements(executor, masterplan_id):
    """Test with only MUST requirements"""

    tests = [
        AcceptanceTest(
            test_id=f"TEST-{i}",
            test_type=TestType.CASE,
            requirement_id=f"REQ-MUST-{i}",
            requirement_priority=RequirementPriority.MUST,
            description="Must",
            test_code="async def test(): assert True",
            expected_outcome="Pass",
            preconditions=[],
            postconditions=[]
        )
        for i in range(1, 4)
    ]

    report = executor.execute_tests(
        masterplan_id=masterplan_id,
        wave_number=1,
        tests=tests
    )

    assert report.must_total == 3
    assert report.should_total == 0
    assert report.should_gate_passed is True  # No SHOULD tests = gate passes


def test_only_should_requirements(executor, masterplan_id):
    """Test with only SHOULD requirements"""

    tests = [
        AcceptanceTest(
            test_id=f"TEST-{i}",
            test_type=TestType.CASE,
            requirement_id=f"REQ-SHOULD-{i}",
            requirement_priority=RequirementPriority.SHOULD,
            description="Should",
            test_code="async def test(): assert True",
            expected_outcome="Pass",
            preconditions=[],
            postconditions=[]
        )
        for i in range(1, 4)
    ]

    report = executor.execute_tests(
        masterplan_id=masterplan_id,
        wave_number=1,
        tests=tests
    )

    assert report.should_total == 3
    assert report.must_total == 0
    assert report.must_gate_passed is True  # No MUST tests = gate passes


# ============================================================
# Test: Report to_dict
# ============================================================

def test_execution_report_to_dict(executor, masterplan_id):
    """Test ExecutionReport to_dict method"""

    tests = [
        AcceptanceTest(
            test_id="TEST-M1",
            test_type=TestType.CASE,
            requirement_id="REQ-MUST-1",
            requirement_priority=RequirementPriority.MUST,
            description="Must",
            test_code="async def test(): assert True",
            expected_outcome="Pass",
            preconditions=[],
            postconditions=[]
        ),
        AcceptanceTest(
            test_id="TEST-S1",
            test_type=TestType.CASE,
            requirement_id="REQ-SHOULD-1",
            requirement_priority=RequirementPriority.SHOULD,
            description="Should",
            test_code="async def test(): assert True",
            expected_outcome="Pass",
            preconditions=[],
            postconditions=[]
        )
    ]

    report = executor.execute_tests(
        masterplan_id=masterplan_id,
        wave_number=1,
        tests=tests
    )

    report_dict = report.to_dict()

    assert "masterplan_id" in report_dict
    assert "wave_number" in report_dict
    assert "total_tests" in report_dict
    assert "summary" in report_dict
    assert "must" in report_dict["summary"]
    assert "should" in report_dict["summary"]
    assert "pass_rate" in report_dict["summary"]["must"]
    assert "gate_passed" in report_dict["summary"]["must"]
    assert report_dict["overall_gate_passed"] is True


def test_pass_rate_calculations_in_dict(executor, masterplan_id):
    """Test pass rate calculations in to_dict"""

    # 2 MUST (1 pass, 1 fail) = 50%
    # 4 SHOULD (3 pass, 1 fail) = 75%
    tests = [
        AcceptanceTest(
            test_id="TEST-M1",
            test_type=TestType.CASE,
            requirement_id="REQ-MUST-1",
            requirement_priority=RequirementPriority.MUST,
            description="Must",
            test_code="async def test(): assert True",
            expected_outcome="Pass",
            preconditions=[],
            postconditions=[]
        ),
        AcceptanceTest(
            test_id="TEST-M2",
            test_type=TestType.CASE,
            requirement_id="REQ-MUST-2",
            requirement_priority=RequirementPriority.MUST,
            description="Must fail",
            test_code="async def test(): assert True",
            expected_outcome="Pass",
            preconditions=[],
            postconditions=[]
        ),
    ] + [
        AcceptanceTest(
            test_id=f"TEST-S{i}",
            test_type=TestType.CASE,
            requirement_id=f"REQ-SHOULD-{i}",
            requirement_priority=RequirementPriority.SHOULD,
            description="Should" if i <= 3 else "Should fail",
            test_code="async def test(): assert True",
            expected_outcome="Pass",
            preconditions=[],
            postconditions=[]
        )
        for i in range(1, 5)
    ]

    report = executor.execute_tests(
        masterplan_id=masterplan_id,
        wave_number=1,
        tests=tests
    )

    report_dict = report.to_dict()

    assert report_dict["summary"]["must"]["pass_rate"] == 50.0
    assert report_dict["summary"]["should"]["pass_rate"] == 75.0


# ============================================================
# Test: Error Handling
# ============================================================

def test_execution_error_handling(executor, masterplan_id):
    """Test that errors during test execution are properly caught"""

    # Create a test that will cause an error during execution
    test = AcceptanceTest(
        test_id="TEST-ERROR",
        test_type=TestType.CASE,
        requirement_id="REQ-001",
        requirement_priority=RequirementPriority.MUST,
        description=None,  # None will cause error when calling .lower()
        test_code="async def test(): assert True",
        expected_outcome="Pass",
        preconditions=[],
        postconditions=[]
    )

    report = executor.execute_tests(
        masterplan_id=masterplan_id,
        wave_number=1,
        tests=[test]
    )

    # Test should be marked as ERROR
    assert report.total_tests == 1
    assert report.error_tests == 1
    assert len(report.test_results) == 1

    result = report.test_results[0]
    assert result.status == TestStatus.ERROR
    assert result.error_message is not None
