"""
Tests for PrecisionScorer - Composite precision scoring system

Tests cover:
- Perfect score scenarios (100% all components)
- Partial failures across components
- MUST requirement gate failures
- Edge cases (no requirements, no validations)
- Target threshold validation (≥98%)
- Weighted scoring formula verification
"""

import pytest
from uuid import uuid4
from src.mge.v2.metrics.precision_scorer import (
    PrecisionScorer,
    PrecisionScore,
    RequirementPriority,
    ValidationLevel,
    RequirementResult,
    IntegrationResult,
    ValidationResult
)


@pytest.fixture
def precision_scorer():
    """Create PrecisionScorer instance"""
    return PrecisionScorer()


@pytest.fixture
def masterplan_id():
    """Generate test masterplan ID"""
    return uuid4()


# ============================================================
# Test: Perfect Score (100% all components)
# ============================================================

def test_perfect_score_all_components_pass(precision_scorer, masterplan_id):
    """Test perfect score when all requirements, integration, and validation pass"""

    requirement_results = [
        RequirementResult(
            requirement_id="REQ-001",
            priority=RequirementPriority.MUST,
            passed=True,
            test_ids=["TEST-001"],
            description="Must requirement 1"
        ),
        RequirementResult(
            requirement_id="REQ-002",
            priority=RequirementPriority.MUST,
            passed=True,
            test_ids=["TEST-002"],
            description="Must requirement 2"
        ),
        RequirementResult(
            requirement_id="REQ-003",
            priority=RequirementPriority.SHOULD,
            passed=True,
            test_ids=["TEST-003"],
            description="Should requirement 1"
        ),
        RequirementResult(
            requirement_id="REQ-004",
            priority=RequirementPriority.SHOULD,
            passed=True,
            test_ids=["TEST-004"],
            description="Should requirement 2"
        ),
    ]

    integration_result = IntegrationResult(
        total_tests=10,
        passed_tests=10,
        failed_tests=0,
        skipped_tests=0,
        pass_rate=1.0
    )

    validation_results = [
        ValidationResult(
            level=ValidationLevel.L1_SYNTAX,
            total_checks=1,
            passed_checks=1,
            failed_checks=0,
            pass_rate=1.0
        ),
        ValidationResult(
            level=ValidationLevel.L2_IMPORTS,
            total_checks=1,
            passed_checks=1,
            failed_checks=0,
            pass_rate=1.0
        ),
        ValidationResult(
            level=ValidationLevel.L3_TYPES,
            total_checks=1,
            passed_checks=1,
            failed_checks=0,
            pass_rate=1.0
        ),
        ValidationResult(
            level=ValidationLevel.L4_COMPLEXITY,
            total_checks=1,
            passed_checks=1,
            failed_checks=0,
            pass_rate=1.0
        ),
    ]

    score = precision_scorer.calculate_score(
        masterplan_id=masterplan_id,
        requirement_results=requirement_results,
        integration_result=integration_result,
        validation_results=validation_results
    )

    assert score.spec_conformance_score == 100.0
    assert score.integration_pass_score == 100.0
    assert score.validation_pass_score == 100.0
    assert score.total_score == 100.0  # 100*0.5 + 100*0.3 + 100*0.2
    assert score.meets_target is True
    assert score.spec_conformance_details["gate_status"] == "PASS"


# ============================================================
# Test: MUST Requirement Gate Failures
# ============================================================

def test_must_requirement_gate_failure_blocks_release(precision_scorer, masterplan_id):
    """Test that failing a single MUST requirement blocks release (gate fail)"""

    requirement_results = [
        RequirementResult(
            requirement_id="REQ-001",
            priority=RequirementPriority.MUST,
            passed=True,
            test_ids=["TEST-001"],
            description="Must requirement 1"
        ),
        RequirementResult(
            requirement_id="REQ-002",
            priority=RequirementPriority.MUST,
            passed=False,  # FAIL
            test_ids=["TEST-002"],
            description="Must requirement 2"
        ),
        RequirementResult(
            requirement_id="REQ-003",
            priority=RequirementPriority.SHOULD,
            passed=True,
            test_ids=["TEST-003"],
            description="Should requirement"
        ),
    ]

    integration_result = IntegrationResult(
        total_tests=10,
        passed_tests=10,
        failed_tests=0,
        skipped_tests=0,
        pass_rate=1.0
    )

    validation_results = [
        ValidationResult(level=ValidationLevel.L1_SYNTAX, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L2_IMPORTS, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L3_TYPES, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L4_COMPLEXITY, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
    ]

    score = precision_scorer.calculate_score(
        masterplan_id=masterplan_id,
        requirement_results=requirement_results,
        integration_result=integration_result,
        validation_results=validation_results
    )

    # MUST pass rate = 50% (1 of 2 passed)
    assert score.spec_conformance_details["musts"]["pass_rate"] == 0.5
    assert score.spec_conformance_details["gate_status"] == "FAIL"

    # Total score affected by failed spec conformance
    assert score.total_score < 98.0
    assert score.meets_target is False


def test_all_must_requirements_fail(precision_scorer, masterplan_id):
    """Test scenario where all MUST requirements fail"""

    requirement_results = [
        RequirementResult(
            requirement_id="REQ-001",
            priority=RequirementPriority.MUST,
            passed=False,
            test_ids=["TEST-001"],
            description="Must requirement 1"
        ),
        RequirementResult(
            requirement_id="REQ-002",
            priority=RequirementPriority.MUST,
            passed=False,
            test_ids=["TEST-002"],
            description="Must requirement 2"
        ),
        RequirementResult(
            requirement_id="REQ-003",
            priority=RequirementPriority.SHOULD,
            passed=True,
            test_ids=["TEST-003"],
            description="Should requirement"
        ),
    ]

    integration_result = IntegrationResult(
        total_tests=10,
        passed_tests=10,
        failed_tests=0,
        skipped_tests=0,
        pass_rate=1.0
    )
    validation_results = [
        ValidationResult(level=ValidationLevel.L1_SYNTAX, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L2_IMPORTS, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L3_TYPES, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L4_COMPLEXITY, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
    ]

    score = precision_scorer.calculate_score(
        masterplan_id=masterplan_id,
        requirement_results=requirement_results,
        integration_result=integration_result,
        validation_results=validation_results
    )

    assert score.spec_conformance_details["musts"]["pass_rate"] == 0.0
    assert score.spec_conformance_details["gate_status"] == "FAIL"
    assert score.meets_target is False


# ============================================================
# Test: SHOULD Requirement Failures (≥95% required)
# ============================================================

def test_should_requirement_below_95_percent(precision_scorer, masterplan_id):
    """Test that SHOULD requirements below 95% lower precision score"""

    requirement_results = [
        RequirementResult(requirement_id="REQ-001", priority=RequirementPriority.MUST, passed=True, test_ids=["T1"], description="M1"),
        RequirementResult(requirement_id="REQ-002", priority=RequirementPriority.MUST, passed=True, test_ids=["T2"], description="M2"),
        # 10 SHOULD requirements, 9 pass = 90% (below 95% target)
        RequirementResult(requirement_id="REQ-S01", priority=RequirementPriority.SHOULD, passed=True, test_ids=["TS1"], description="S1"),
        RequirementResult(requirement_id="REQ-S02", priority=RequirementPriority.SHOULD, passed=True, test_ids=["TS2"], description="S2"),
        RequirementResult(requirement_id="REQ-S03", priority=RequirementPriority.SHOULD, passed=True, test_ids=["TS3"], description="S3"),
        RequirementResult(requirement_id="REQ-S04", priority=RequirementPriority.SHOULD, passed=True, test_ids=["TS4"], description="S4"),
        RequirementResult(requirement_id="REQ-S05", priority=RequirementPriority.SHOULD, passed=True, test_ids=["TS5"], description="S5"),
        RequirementResult(requirement_id="REQ-S06", priority=RequirementPriority.SHOULD, passed=True, test_ids=["TS6"], description="S6"),
        RequirementResult(requirement_id="REQ-S07", priority=RequirementPriority.SHOULD, passed=True, test_ids=["TS7"], description="S7"),
        RequirementResult(requirement_id="REQ-S08", priority=RequirementPriority.SHOULD, passed=True, test_ids=["TS8"], description="S8"),
        RequirementResult(requirement_id="REQ-S09", priority=RequirementPriority.SHOULD, passed=True, test_ids=["TS9"], description="S9"),
        RequirementResult(requirement_id="REQ-S10", priority=RequirementPriority.SHOULD, passed=False, test_ids=["TS10"], description="S10"),
    ]

    integration_result = IntegrationResult(total_tests=10, passed_tests=10, failed_tests=0, skipped_tests=0, pass_rate=1.0)
    validation_results = [
        ValidationResult(level=ValidationLevel.L1_SYNTAX, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L2_IMPORTS, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L3_TYPES, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L4_COMPLEXITY, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
    ]

    score = precision_scorer.calculate_score(
        masterplan_id=masterplan_id,
        requirement_results=requirement_results,
        integration_result=integration_result,
        validation_results=validation_results
    )

    # MUST: 100%, SHOULD: 90%
    assert score.spec_conformance_details["musts"]["pass_rate"] == 1.0
    assert score.spec_conformance_details["shoulds"]["pass_rate"] == 0.9
    assert score.spec_conformance_details["gate_status"] == "PASS"  # MUST still 100%

    # Spec conformance = (100 + 90) / 2 = 95
    assert score.spec_conformance_score == 95.0

    # Total = 95*0.5 + 100*0.3 + 100*0.2 = 47.5 + 30 + 20 = 97.5
    assert score.total_score == 97.5
    assert score.meets_target is False  # Below 98%


# ============================================================
# Test: Integration Test Failures
# ============================================================

def test_integration_test_partial_failure(precision_scorer, masterplan_id):
    """Test partial integration test failures"""

    requirement_results = [
        RequirementResult(requirement_id="REQ-001", priority=RequirementPriority.MUST, passed=True, test_ids=["T1"], description="R1"),
        RequirementResult(requirement_id="REQ-002", priority=RequirementPriority.SHOULD, passed=True, test_ids=["T2"], description="R2"),
    ]

    # 70% integration pass rate
    integration_result = IntegrationResult(
        total_tests=10,
        passed_tests=7,
        failed_tests=3,
        skipped_tests=0,
        pass_rate=0.7
    )

    validation_results = [
        ValidationResult(level=ValidationLevel.L1_SYNTAX, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L2_IMPORTS, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L3_TYPES, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L4_COMPLEXITY, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
    ]

    score = precision_scorer.calculate_score(
        masterplan_id=masterplan_id,
        requirement_results=requirement_results,
        integration_result=integration_result,
        validation_results=validation_results
    )

    assert score.integration_pass_score == 70.0

    # Total = 100*0.5 + 70*0.3 + 100*0.2 = 50 + 21 + 20 = 91
    assert score.total_score == 91.0
    assert score.meets_target is False


def test_integration_test_complete_failure(precision_scorer, masterplan_id):
    """Test all integration tests failing"""

    requirement_results = [
        RequirementResult(requirement_id="REQ-001", priority=RequirementPriority.MUST, passed=True, test_ids=["T1"], description="R1"),
    ]

    integration_result = IntegrationResult(
        total_tests=10,
        passed_tests=0,
        failed_tests=10,
        skipped_tests=0,
        pass_rate=0.0
    )

    validation_results = [
        ValidationResult(level=ValidationLevel.L1_SYNTAX, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L2_IMPORTS, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L3_TYPES, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L4_COMPLEXITY, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
    ]

    score = precision_scorer.calculate_score(
        masterplan_id=masterplan_id,
        requirement_results=requirement_results,
        integration_result=integration_result,
        validation_results=validation_results
    )

    assert score.integration_pass_score == 0.0

    # Total = 100*0.5 + 0*0.3 + 100*0.2 = 50 + 0 + 20 = 70
    assert score.total_score == 70.0
    assert score.meets_target is False


# ============================================================
# Test: Validation Level Failures
# ============================================================

def test_validation_l1_syntax_failure(precision_scorer, masterplan_id):
    """Test L1 syntax validation failure"""

    requirement_results = [
        RequirementResult(requirement_id="REQ-001", priority=RequirementPriority.MUST, passed=True, test_ids=["T1"], description="R1"),
    ]

    integration_result = IntegrationResult(total_tests=10, passed_tests=10, failed_tests=0, skipped_tests=0, pass_rate=1.0)

    validation_results = [
        ValidationResult(level=ValidationLevel.L1_SYNTAX, total_checks=1, passed_checks=0, failed_checks=1, pass_rate=0.0),
        ValidationResult(level=ValidationLevel.L2_IMPORTS, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L3_TYPES, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L4_COMPLEXITY, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
    ]

    score = precision_scorer.calculate_score(
        masterplan_id=masterplan_id,
        requirement_results=requirement_results,
        integration_result=integration_result,
        validation_results=validation_results
    )

    # Validation pass = 75% (3 of 4 levels)
    assert score.validation_pass_score == 75.0

    # Total = 100*0.5 + 100*0.3 + 75*0.2 = 50 + 30 + 15 = 95
    assert score.total_score == 95.0
    assert score.meets_target is False


def test_validation_multiple_level_failures(precision_scorer, masterplan_id):
    """Test multiple validation level failures"""

    requirement_results = [
        RequirementResult(requirement_id="REQ-001", priority=RequirementPriority.MUST, passed=True, test_ids=["T1"], description="R1"),
    ]

    integration_result = IntegrationResult(total_tests=10, passed_tests=10, failed_tests=0, skipped_tests=0, pass_rate=1.0)

    validation_results = [
        ValidationResult(level=ValidationLevel.L1_SYNTAX, total_checks=1, passed_checks=0, failed_checks=1, pass_rate=0.0),
        ValidationResult(level=ValidationLevel.L2_IMPORTS, total_checks=1, passed_checks=0, failed_checks=1, pass_rate=0.0),
        ValidationResult(level=ValidationLevel.L3_TYPES, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L4_COMPLEXITY, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
    ]

    score = precision_scorer.calculate_score(
        masterplan_id=masterplan_id,
        requirement_results=requirement_results,
        integration_result=integration_result,
        validation_results=validation_results
    )

    # Validation pass = 50% (2 of 4 levels)
    assert score.validation_pass_score == 50.0

    # Total = 100*0.5 + 100*0.3 + 50*0.2 = 50 + 30 + 10 = 90
    assert score.total_score == 90.0
    assert score.meets_target is False


def test_validation_all_levels_fail(precision_scorer, masterplan_id):
    """Test all validation levels failing"""

    requirement_results = [
        RequirementResult(requirement_id="REQ-001", priority=RequirementPriority.MUST, passed=True, test_ids=["T1"], description="R1"),
    ]

    integration_result = IntegrationResult(total_tests=10, passed_tests=10, failed_tests=0, skipped_tests=0, pass_rate=1.0)

    validation_results = [
        ValidationResult(level=ValidationLevel.L1_SYNTAX, total_checks=1, passed_checks=0, failed_checks=1, pass_rate=0.0),
        ValidationResult(level=ValidationLevel.L2_IMPORTS, total_checks=1, passed_checks=0, failed_checks=1, pass_rate=0.0),
        ValidationResult(level=ValidationLevel.L3_TYPES, total_checks=1, passed_checks=0, failed_checks=1, pass_rate=0.0),
        ValidationResult(level=ValidationLevel.L4_COMPLEXITY, total_checks=1, passed_checks=0, failed_checks=1, pass_rate=0.0),
    ]

    score = precision_scorer.calculate_score(
        masterplan_id=masterplan_id,
        requirement_results=requirement_results,
        integration_result=integration_result,
        validation_results=validation_results
    )

    assert score.validation_pass_score == 0.0

    # Total = 100*0.5 + 100*0.3 + 0*0.2 = 50 + 30 + 0 = 80
    assert score.total_score == 80.0
    assert score.meets_target is False


# ============================================================
# Test: Edge Cases
# ============================================================

def test_edge_case_integration_no_tests(precision_scorer, masterplan_id):
    """Test IntegrationResult with zero tests"""

    requirement_results = [
        RequirementResult(requirement_id="REQ-001", priority=RequirementPriority.MUST, passed=True, test_ids=["T1"], description="R1"),
    ]

    # Zero integration tests
    integration_result = IntegrationResult(
        total_tests=0,
        passed_tests=0,
        failed_tests=0,
        skipped_tests=0,
        pass_rate=0.0
    )

    validation_results = [
        ValidationResult(level=ValidationLevel.L1_SYNTAX, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L2_IMPORTS, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L3_TYPES, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L4_COMPLEXITY, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
    ]

    score = precision_scorer.calculate_score(
        masterplan_id=masterplan_id,
        requirement_results=requirement_results,
        integration_result=integration_result,
        validation_results=validation_results
    )

    # Integration score should be 0 due to no tests
    assert score.integration_pass_score == 0.0


def test_edge_case_validation_no_checks(precision_scorer, masterplan_id):
    """Test ValidationResult with zero checks"""

    requirement_results = [
        RequirementResult(requirement_id="REQ-001", priority=RequirementPriority.MUST, passed=True, test_ids=["T1"], description="R1"),
    ]

    integration_result = IntegrationResult(total_tests=10, passed_tests=10, failed_tests=0, skipped_tests=0, pass_rate=1.0)

    # Validation level with zero checks
    validation_results = [
        ValidationResult(level=ValidationLevel.L1_SYNTAX, total_checks=0, passed_checks=0, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L2_IMPORTS, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L3_TYPES, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L4_COMPLEXITY, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
    ]

    score = precision_scorer.calculate_score(
        masterplan_id=masterplan_id,
        requirement_results=requirement_results,
        integration_result=integration_result,
        validation_results=validation_results
    )

    # Validation pass rate should be 100% (average of 1.0, 1.0, 1.0, 1.0)
    assert score.validation_pass_score == 100.0


def test_edge_case_only_should_requirements(precision_scorer, masterplan_id):
    """Test with only SHOULD requirements (no MUSTS)"""

    requirement_results = [
        RequirementResult(requirement_id="REQ-S1", priority=RequirementPriority.SHOULD, passed=True, test_ids=["T1"], description="S1"),
        RequirementResult(requirement_id="REQ-S2", priority=RequirementPriority.SHOULD, passed=True, test_ids=["T2"], description="S2"),
        RequirementResult(requirement_id="REQ-S3", priority=RequirementPriority.SHOULD, passed=False, test_ids=["T3"], description="S3"),
    ]

    integration_result = IntegrationResult(total_tests=10, passed_tests=10, failed_tests=0, skipped_tests=0, pass_rate=1.0)
    validation_results = [
        ValidationResult(level=ValidationLevel.L1_SYNTAX, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L2_IMPORTS, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L3_TYPES, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L4_COMPLEXITY, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
    ]

    score = precision_scorer.calculate_score(
        masterplan_id=masterplan_id,
        requirement_results=requirement_results,
        integration_result=integration_result,
        validation_results=validation_results
    )

    # Only SHOULD requirements: 2/3 passed = 66.67%
    # Spec score should be 66.67% (just should_pass_rate, no musts)
    assert score.spec_conformance_details["shoulds"]["total"] == 3
    assert score.spec_conformance_details["shoulds"]["passed"] == 2
    assert score.spec_conformance_details["musts"]["total"] == 0
    # Gate should PASS since no MUST requirements exist
    assert score.spec_conformance_details["gate_status"] == "PASS"


def test_edge_case_no_requirements(precision_scorer, masterplan_id):
    """Test edge case with no requirements"""

    requirement_results = []

    integration_result = IntegrationResult(total_tests=10, passed_tests=10, failed_tests=0, skipped_tests=0, pass_rate=1.0)

    validation_results = [
        ValidationResult(level=ValidationLevel.L1_SYNTAX, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L2_IMPORTS, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L3_TYPES, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L4_COMPLEXITY, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
    ]

    score = precision_scorer.calculate_score(
        masterplan_id=masterplan_id,
        requirement_results=requirement_results,
        integration_result=integration_result,
        validation_results=validation_results
    )

    # No requirements → 100% spec conformance (default)
    assert score.spec_conformance_score == 100.0
    assert score.spec_conformance_details["musts"]["total"] == 0
    assert score.spec_conformance_details["shoulds"]["total"] == 0
    assert score.total_score == 100.0


def test_edge_case_no_validation_results(precision_scorer, masterplan_id):
    """Test edge case with no validation results"""

    requirement_results = [
        RequirementResult(requirement_id="REQ-001", priority=RequirementPriority.MUST, passed=True, test_ids=["T1"], description="R1"),
    ]

    integration_result = IntegrationResult(total_tests=10, passed_tests=10, failed_tests=0, skipped_tests=0, pass_rate=1.0)

    validation_results = []

    score = precision_scorer.calculate_score(
        masterplan_id=masterplan_id,
        requirement_results=requirement_results,
        integration_result=integration_result,
        validation_results=validation_results
    )

    # No validations → 100% validation pass (default)
    assert score.validation_pass_score == 100.0
    assert score.total_score == 100.0


def test_edge_case_only_could_and_wont_requirements(precision_scorer, masterplan_id):
    """Test edge case with only COULD and WONT requirements"""

    requirement_results = [
        RequirementResult(requirement_id="REQ-001", priority=RequirementPriority.COULD, passed=True, test_ids=["T1"], description="R1"),
        RequirementResult(requirement_id="REQ-002", priority=RequirementPriority.COULD, passed=False, test_ids=["T2"], description="R2"),
        RequirementResult(requirement_id="REQ-003", priority=RequirementPriority.WONT, passed=False, test_ids=["T3"], description="R3"),
    ]

    integration_result = IntegrationResult(total_tests=10, passed_tests=10, failed_tests=0, skipped_tests=0, pass_rate=1.0)

    validation_results = [
        ValidationResult(level=ValidationLevel.L1_SYNTAX, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L2_IMPORTS, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L3_TYPES, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L4_COMPLEXITY, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
    ]

    score = precision_scorer.calculate_score(
        masterplan_id=masterplan_id,
        requirement_results=requirement_results,
        integration_result=integration_result,
        validation_results=validation_results
    )

    # No MUST/SHOULD → 100% spec conformance (default)
    assert score.spec_conformance_score == 100.0
    assert score.spec_conformance_details["musts"]["total"] == 0
    assert score.spec_conformance_details["shoulds"]["total"] == 0


# ============================================================
# Test: Target Threshold (≥98%)
# ============================================================

def test_exactly_98_percent_meets_target(precision_scorer, masterplan_id):
    """Test that exactly 98% precision meets target"""

    requirement_results = [
        RequirementResult(requirement_id="REQ-001", priority=RequirementPriority.MUST, passed=True, test_ids=["T1"], description="R1"),
        RequirementResult(requirement_id="REQ-002", priority=RequirementPriority.MUST, passed=True, test_ids=["T2"], description="R2"),
    ]

    # Need: 100*0.5 + X*0.3 + Y*0.2 = 98
    # Try: spec=100, integration=93.33, validation=100
    # 100*0.5 + 93.33*0.3 + 100*0.2 = 50 + 28 + 20 = 98

    integration_result = IntegrationResult(
        total_tests=30,
        passed_tests=28,
        failed_tests=2,
        skipped_tests=0,
        pass_rate=28/30  # 93.33%
    )

    validation_results = [
        ValidationResult(level=ValidationLevel.L1_SYNTAX, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L2_IMPORTS, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L3_TYPES, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L4_COMPLEXITY, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
    ]

    score = precision_scorer.calculate_score(
        masterplan_id=masterplan_id,
        requirement_results=requirement_results,
        integration_result=integration_result,
        validation_results=validation_results
    )

    assert abs(score.total_score - 98.0) < 0.1
    assert score.meets_target is True


def test_just_below_98_percent_fails_target(precision_scorer, masterplan_id):
    """Test that 97.9% precision fails target"""

    requirement_results = [
        RequirementResult(requirement_id="REQ-001", priority=RequirementPriority.MUST, passed=True, test_ids=["T1"], description="R1"),
        RequirementResult(requirement_id="REQ-002", priority=RequirementPriority.MUST, passed=True, test_ids=["T2"], description="R2"),
    ]

    # 100*0.5 + 90*0.3 + 100*0.2 = 50 + 27 + 20 = 97
    integration_result = IntegrationResult(
        total_tests=10,
        passed_tests=9,
        failed_tests=1,
        skipped_tests=0,
        pass_rate=0.9
    )

    validation_results = [
        ValidationResult(level=ValidationLevel.L1_SYNTAX, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L2_IMPORTS, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L3_TYPES, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L4_COMPLEXITY, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
    ]

    score = precision_scorer.calculate_score(
        masterplan_id=masterplan_id,
        requirement_results=requirement_results,
        integration_result=integration_result,
        validation_results=validation_results
    )

    assert score.total_score == 97.0
    assert score.meets_target is False


# ============================================================
# Test: Weighted Formula Verification
# ============================================================

def test_weighted_formula_50_30_20(precision_scorer, masterplan_id):
    """Test that weighted formula is correct: 50% spec + 30% integration + 20% validation"""

    requirement_results = [
        RequirementResult(requirement_id="REQ-001", priority=RequirementPriority.MUST, passed=True, test_ids=["T1"], description="R1"),
        RequirementResult(requirement_id="REQ-002", priority=RequirementPriority.MUST, passed=True, test_ids=["T2"], description="R2"),
    ]

    # Specific values to test formula
    # Spec: 100, Integration: 80, Validation: 50
    integration_result = IntegrationResult(
        total_tests=10,
        passed_tests=8,
        failed_tests=2,
        skipped_tests=0,
        pass_rate=0.8
    )

    validation_results = [
        ValidationResult(level=ValidationLevel.L1_SYNTAX, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L2_IMPORTS, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L3_TYPES, total_checks=1, passed_checks=0, failed_checks=1, pass_rate=0.0),
        ValidationResult(level=ValidationLevel.L4_COMPLEXITY, total_checks=1, passed_checks=0, failed_checks=1, pass_rate=0.0),
    ]

    score = precision_scorer.calculate_score(
        masterplan_id=masterplan_id,
        requirement_results=requirement_results,
        integration_result=integration_result,
        validation_results=validation_results
    )

    assert score.spec_conformance_score == 100.0
    assert score.integration_pass_score == 80.0
    assert score.validation_pass_score == 50.0  # 2 of 4 levels pass

    # Expected: 100*0.5 + 80*0.3 + 50*0.2 = 50 + 24 + 10 = 84
    assert score.total_score == 84.0
    assert score.meets_target is False


# ============================================================
# Test: PrecisionScore Dataclass
# ============================================================

def test_precision_score_to_dict(precision_scorer, masterplan_id):
    """Test PrecisionScore to_dict() method"""

    requirement_results = [
        RequirementResult(requirement_id="REQ-001", priority=RequirementPriority.MUST, passed=True, test_ids=["T1"], description="R1"),
    ]

    integration_result = IntegrationResult(total_tests=10, passed_tests=10, failed_tests=0, skipped_tests=0, pass_rate=1.0)

    validation_results = [
        ValidationResult(level=ValidationLevel.L1_SYNTAX, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L2_IMPORTS, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L3_TYPES, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
        ValidationResult(level=ValidationLevel.L4_COMPLEXITY, total_checks=1, passed_checks=1, failed_checks=0, pass_rate=1.0),
    ]

    score = precision_scorer.calculate_score(
        masterplan_id=masterplan_id,
        requirement_results=requirement_results,
        integration_result=integration_result,
        validation_results=validation_results
    )

    score_dict = score.to_dict()

    assert "masterplan_id" in score_dict
    assert "total_score" in score_dict
    assert "meets_target" in score_dict
    assert "components" in score_dict
    assert "spec_conformance" in score_dict["components"]
    assert "integration_pass" in score_dict["components"]
    assert "validation_pass" in score_dict["components"]
    assert score_dict["total_score"] == 100.0
    assert score_dict["meets_target"] is True
    assert score_dict["components"]["spec_conformance"]["score"] == 100.0
    assert score_dict["components"]["integration_pass"]["score"] == 100.0
    assert score_dict["components"]["validation_pass"]["score"] == 100.0
