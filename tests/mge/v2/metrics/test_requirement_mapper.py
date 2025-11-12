"""
Tests for RequirementMapper - Requirement to acceptance test mapping

Tests cover:
- Requirement CRUD operations
- Test mapping to requirements
- Coverage validation (MUST/SHOULD requirements)
- Orphan test detection
- Bidirectional mapping verification
- Edge cases (no requirements, no tests)
"""

import pytest
from uuid import uuid4
from src.mge.v2.metrics.requirement_mapper import (
    RequirementMapper,
    Requirement,
    AcceptanceTest
)
from src.mge.v2.metrics.precision_scorer import RequirementPriority


@pytest.fixture
def mapper():
    """Create RequirementMapper instance"""
    return RequirementMapper()


@pytest.fixture
def masterplan_id():
    """Generate test masterplan ID"""
    return uuid4()


# ============================================================
# Test: Requirement CRUD Operations
# ============================================================

def test_add_requirement_basic(mapper, masterplan_id):
    """Test adding a basic requirement"""

    requirement = mapper.add_requirement(
        requirement_id="REQ-001",
        masterplan_id=masterplan_id,
        description="User can login with email/password",
        priority=RequirementPriority.MUST
    )

    assert requirement.requirement_id == "REQ-001"
    assert requirement.masterplan_id == masterplan_id
    assert requirement.description == "User can login with email/password"
    assert requirement.priority == RequirementPriority.MUST
    assert requirement.test_ids == []
    assert requirement.category is None


def test_add_requirement_with_category(mapper, masterplan_id):
    """Test adding requirement with category"""

    requirement = mapper.add_requirement(
        requirement_id="REQ-002",
        masterplan_id=masterplan_id,
        description="API returns 401 for invalid credentials",
        priority=RequirementPriority.MUST,
        category="auth"
    )

    assert requirement.category == "auth"


def test_add_multiple_requirements(mapper, masterplan_id):
    """Test adding multiple requirements"""

    mapper.add_requirement(
        requirement_id="REQ-001",
        masterplan_id=masterplan_id,
        description="Requirement 1",
        priority=RequirementPriority.MUST
    )

    mapper.add_requirement(
        requirement_id="REQ-002",
        masterplan_id=masterplan_id,
        description="Requirement 2",
        priority=RequirementPriority.SHOULD
    )

    mapper.add_requirement(
        requirement_id="REQ-003",
        masterplan_id=masterplan_id,
        description="Requirement 3",
        priority=RequirementPriority.COULD
    )

    requirements = mapper.get_all_requirements(masterplan_id=masterplan_id)
    assert len(requirements) == 3


def test_get_requirement_by_id(mapper, masterplan_id):
    """Test retrieving requirement by ID"""

    mapper.add_requirement(
        requirement_id="REQ-001",
        masterplan_id=masterplan_id,
        description="Test requirement",
        priority=RequirementPriority.MUST
    )

    requirement = mapper.get_requirement("REQ-001")

    assert requirement is not None
    assert requirement.requirement_id == "REQ-001"


def test_get_requirement_not_found(mapper):
    """Test retrieving non-existent requirement"""

    requirement = mapper.get_requirement("REQ-999")
    assert requirement is None


# ============================================================
# Test: Test Mapping Operations
# ============================================================

def test_map_test_to_requirement_basic(mapper, masterplan_id):
    """Test mapping a basic test to requirement"""

    mapper.add_requirement(
        requirement_id="REQ-001",
        masterplan_id=masterplan_id,
        description="User can login",
        priority=RequirementPriority.MUST
    )

    test = mapper.map_test_to_requirement(
        test_id="TEST-001",
        requirement_id="REQ-001",
        description="Test login with valid credentials",
        test_type="case",
        passed=True
    )

    assert test.test_id == "TEST-001"
    assert test.requirement_id == "REQ-001"
    assert test.description == "Test login with valid credentials"
    assert test.test_type == "case"
    assert test.passed is True


def test_map_test_to_nonexistent_requirement(mapper):
    """Test mapping test to non-existent requirement raises ValueError"""

    with pytest.raises(ValueError, match="Requirement REQ-999 not found"):
        mapper.map_test_to_requirement(
            test_id="TEST-001",
            requirement_id="REQ-999",
            description="Test",
            test_type="case"
        )


def test_map_multiple_tests_to_same_requirement(mapper, masterplan_id):
    """Test mapping multiple tests to same requirement"""

    mapper.add_requirement(
        requirement_id="REQ-001",
        masterplan_id=masterplan_id,
        description="User can login",
        priority=RequirementPriority.MUST
    )

    mapper.map_test_to_requirement(
        test_id="TEST-001",
        requirement_id="REQ-001",
        description="Test login with email",
        test_type="case"
    )

    mapper.map_test_to_requirement(
        test_id="TEST-002",
        requirement_id="REQ-001",
        description="Test login with username",
        test_type="case"
    )

    mapper.map_test_to_requirement(
        test_id="TEST-003",
        requirement_id="REQ-001",
        description="Test login contract",
        test_type="contract"
    )

    tests = mapper.get_tests_for_requirement("REQ-001")
    assert len(tests) == 3


def test_map_test_updates_requirement_test_ids(mapper, masterplan_id):
    """Test that mapping test updates requirement's test_ids"""

    mapper.add_requirement(
        requirement_id="REQ-001",
        masterplan_id=masterplan_id,
        description="User can login",
        priority=RequirementPriority.MUST
    )

    mapper.map_test_to_requirement(
        test_id="TEST-001",
        requirement_id="REQ-001",
        description="Test",
        test_type="case"
    )

    requirement = mapper.get_requirement("REQ-001")
    assert "TEST-001" in requirement.test_ids


def test_test_types_contract_invariant_case(mapper, masterplan_id):
    """Test all test types: contract, invariant, case"""

    mapper.add_requirement(
        requirement_id="REQ-001",
        masterplan_id=masterplan_id,
        description="Requirement",
        priority=RequirementPriority.MUST
    )

    mapper.map_test_to_requirement(
        test_id="TEST-CONTRACT",
        requirement_id="REQ-001",
        description="Contract test",
        test_type="contract"
    )

    mapper.map_test_to_requirement(
        test_id="TEST-INVARIANT",
        requirement_id="REQ-001",
        description="Invariant test",
        test_type="invariant"
    )

    mapper.map_test_to_requirement(
        test_id="TEST-CASE",
        requirement_id="REQ-001",
        description="Case test",
        test_type="case"
    )

    tests = mapper.get_tests_for_requirement("REQ-001")
    test_types = [t.test_type for t in tests]
    assert "contract" in test_types
    assert "invariant" in test_types
    assert "case" in test_types


# ============================================================
# Test: Bidirectional Mapping
# ============================================================

def test_bidirectional_mapping_requirement_to_tests(mapper, masterplan_id):
    """Test bidirectional mapping: requirement → tests"""

    mapper.add_requirement(
        requirement_id="REQ-001",
        masterplan_id=masterplan_id,
        description="Requirement",
        priority=RequirementPriority.MUST
    )

    mapper.map_test_to_requirement(
        test_id="TEST-001",
        requirement_id="REQ-001",
        description="Test",
        test_type="case"
    )

    tests = mapper.get_tests_for_requirement("REQ-001")
    assert len(tests) == 1
    assert tests[0].test_id == "TEST-001"


def test_bidirectional_mapping_test_to_requirement(mapper, masterplan_id):
    """Test bidirectional mapping: test → requirement"""

    mapper.add_requirement(
        requirement_id="REQ-001",
        masterplan_id=masterplan_id,
        description="Requirement",
        priority=RequirementPriority.MUST
    )

    mapper.map_test_to_requirement(
        test_id="TEST-001",
        requirement_id="REQ-001",
        description="Test",
        test_type="case"
    )

    requirement = mapper.get_requirement_for_test("TEST-001")
    assert requirement is not None
    assert requirement.requirement_id == "REQ-001"


def test_get_requirement_for_nonexistent_test(mapper):
    """Test getting requirement for non-existent test"""

    requirement = mapper.get_requirement_for_test("TEST-999")
    assert requirement is None


# ============================================================
# Test: Update Test Status
# ============================================================

def test_update_test_status_basic(mapper, masterplan_id):
    """Test updating test status"""

    mapper.add_requirement(
        requirement_id="REQ-001",
        masterplan_id=masterplan_id,
        description="Requirement",
        priority=RequirementPriority.MUST
    )

    mapper.map_test_to_requirement(
        test_id="TEST-001",
        requirement_id="REQ-001",
        description="Test",
        test_type="case",
        passed=False
    )

    # Update to passed
    mapper.update_test_status("TEST-001", passed=True)

    test = mapper.get_test("TEST-001")
    assert test.passed is True


def test_update_test_status_nonexistent_test(mapper):
    """Test updating status of non-existent test raises ValueError"""

    with pytest.raises(ValueError, match="Test TEST-999 not found"):
        mapper.update_test_status("TEST-999", passed=True)


# ============================================================
# Test: Coverage Validation
# ============================================================

def test_validate_coverage_perfect(mapper, masterplan_id):
    """Test coverage validation with 100% coverage"""

    # Add MUST requirements
    mapper.add_requirement(
        requirement_id="REQ-MUST-1",
        masterplan_id=masterplan_id,
        description="Must requirement 1",
        priority=RequirementPriority.MUST
    )
    mapper.add_requirement(
        requirement_id="REQ-MUST-2",
        masterplan_id=masterplan_id,
        description="Must requirement 2",
        priority=RequirementPriority.MUST
    )

    # Add SHOULD requirements
    mapper.add_requirement(
        requirement_id="REQ-SHOULD-1",
        masterplan_id=masterplan_id,
        description="Should requirement 1",
        priority=RequirementPriority.SHOULD
    )

    # Map tests to all requirements
    mapper.map_test_to_requirement(
        test_id="TEST-1",
        requirement_id="REQ-MUST-1",
        description="Test for must 1",
        test_type="case"
    )
    mapper.map_test_to_requirement(
        test_id="TEST-2",
        requirement_id="REQ-MUST-2",
        description="Test for must 2",
        test_type="case"
    )
    mapper.map_test_to_requirement(
        test_id="TEST-3",
        requirement_id="REQ-SHOULD-1",
        description="Test for should 1",
        test_type="case"
    )

    coverage = mapper.validate_coverage(masterplan_id)

    assert coverage["total_requirements"] == 3
    assert coverage["total_tests"] == 3
    assert coverage["must_requirements"]["total"] == 2
    assert coverage["must_requirements"]["covered"] == 2
    assert coverage["must_requirements"]["uncovered"] == 0
    assert coverage["must_requirements"]["coverage_percent"] == 100.0
    assert coverage["should_requirements"]["total"] == 1
    assert coverage["should_requirements"]["covered"] == 1
    assert coverage["should_requirements"]["uncovered"] == 0
    assert coverage["should_requirements"]["coverage_percent"] == 100.0
    assert coverage["orphaned_tests"] == []
    assert coverage["coverage_complete"] is True


def test_validate_coverage_uncovered_must_requirements(mapper, masterplan_id):
    """Test coverage validation with uncovered MUST requirements"""

    mapper.add_requirement(
        requirement_id="REQ-MUST-1",
        masterplan_id=masterplan_id,
        description="Must requirement 1",
        priority=RequirementPriority.MUST
    )
    mapper.add_requirement(
        requirement_id="REQ-MUST-2",
        masterplan_id=masterplan_id,
        description="Must requirement 2",
        priority=RequirementPriority.MUST
    )

    # Only map test to first MUST requirement
    mapper.map_test_to_requirement(
        test_id="TEST-1",
        requirement_id="REQ-MUST-1",
        description="Test for must 1",
        test_type="case"
    )

    coverage = mapper.validate_coverage(masterplan_id)

    assert coverage["must_requirements"]["total"] == 2
    assert coverage["must_requirements"]["covered"] == 1
    assert coverage["must_requirements"]["uncovered"] == 1
    assert coverage["must_requirements"]["coverage_percent"] == 50.0
    assert "REQ-MUST-2" in coverage["must_requirements"]["uncovered_ids"]
    assert coverage["coverage_complete"] is False


def test_validate_coverage_uncovered_should_requirements(mapper, masterplan_id):
    """Test coverage validation with uncovered SHOULD requirements"""

    mapper.add_requirement(
        requirement_id="REQ-MUST-1",
        masterplan_id=masterplan_id,
        description="Must requirement 1",
        priority=RequirementPriority.MUST
    )
    mapper.add_requirement(
        requirement_id="REQ-SHOULD-1",
        masterplan_id=masterplan_id,
        description="Should requirement 1",
        priority=RequirementPriority.SHOULD
    )
    mapper.add_requirement(
        requirement_id="REQ-SHOULD-2",
        masterplan_id=masterplan_id,
        description="Should requirement 2",
        priority=RequirementPriority.SHOULD
    )

    # Map tests to MUST and one SHOULD
    mapper.map_test_to_requirement(
        test_id="TEST-1",
        requirement_id="REQ-MUST-1",
        description="Test for must 1",
        test_type="case"
    )
    mapper.map_test_to_requirement(
        test_id="TEST-2",
        requirement_id="REQ-SHOULD-1",
        description="Test for should 1",
        test_type="case"
    )

    coverage = mapper.validate_coverage(masterplan_id)

    assert coverage["must_requirements"]["coverage_percent"] == 100.0
    assert coverage["should_requirements"]["total"] == 2
    assert coverage["should_requirements"]["covered"] == 1
    assert coverage["should_requirements"]["uncovered"] == 1
    assert coverage["should_requirements"]["coverage_percent"] == 50.0
    assert "REQ-SHOULD-2" in coverage["should_requirements"]["uncovered_ids"]
    assert coverage["coverage_complete"] is False


def test_validate_coverage_orphaned_tests(mapper, masterplan_id):
    """Test detection of orphaned tests (tests without requirements)"""

    # This test cannot create orphaned tests because map_test_to_requirement
    # requires a valid requirement_id. Orphaned tests would only occur if
    # the internal _test_to_req mapping gets corrupted or if tests are
    # added through some other means.

    # For now, we test the case where no orphans exist
    mapper.add_requirement(
        requirement_id="REQ-001",
        masterplan_id=masterplan_id,
        description="Requirement",
        priority=RequirementPriority.MUST
    )

    mapper.map_test_to_requirement(
        test_id="TEST-001",
        requirement_id="REQ-001",
        description="Test",
        test_type="case"
    )

    coverage = mapper.validate_coverage(masterplan_id)
    assert coverage["orphaned_tests"] == []


def test_validate_coverage_no_requirements(mapper, masterplan_id):
    """Test coverage validation with no requirements"""

    coverage = mapper.validate_coverage(masterplan_id)

    assert coverage["total_requirements"] == 0
    assert coverage["total_tests"] == 0
    assert coverage["must_requirements"]["total"] == 0
    assert coverage["must_requirements"]["coverage_percent"] == 100.0
    assert coverage["should_requirements"]["total"] == 0
    assert coverage["should_requirements"]["coverage_percent"] == 100.0
    assert coverage["coverage_complete"] is True


def test_validate_coverage_only_could_wont_requirements(mapper, masterplan_id):
    """Test coverage validation with only COULD and WONT requirements"""

    mapper.add_requirement(
        requirement_id="REQ-COULD-1",
        masterplan_id=masterplan_id,
        description="Could requirement",
        priority=RequirementPriority.COULD
    )
    mapper.add_requirement(
        requirement_id="REQ-WONT-1",
        masterplan_id=masterplan_id,
        description="Wont requirement",
        priority=RequirementPriority.WONT
    )

    coverage = mapper.validate_coverage(masterplan_id)

    # COULD and WONT don't affect coverage
    assert coverage["total_requirements"] == 2
    assert coverage["must_requirements"]["total"] == 0
    assert coverage["should_requirements"]["total"] == 0
    assert coverage["coverage_complete"] is True


# ============================================================
# Test: Filter Operations
# ============================================================

def test_get_all_requirements_by_masterplan(mapper):
    """Test filtering requirements by masterplan"""

    masterplan_1 = uuid4()
    masterplan_2 = uuid4()

    mapper.add_requirement(
        requirement_id="REQ-MP1-1",
        masterplan_id=masterplan_1,
        description="Requirement for MP1",
        priority=RequirementPriority.MUST
    )
    mapper.add_requirement(
        requirement_id="REQ-MP1-2",
        masterplan_id=masterplan_1,
        description="Requirement for MP1",
        priority=RequirementPriority.MUST
    )
    mapper.add_requirement(
        requirement_id="REQ-MP2-1",
        masterplan_id=masterplan_2,
        description="Requirement for MP2",
        priority=RequirementPriority.MUST
    )

    requirements_mp1 = mapper.get_all_requirements(masterplan_id=masterplan_1)
    assert len(requirements_mp1) == 2

    requirements_mp2 = mapper.get_all_requirements(masterplan_id=masterplan_2)
    assert len(requirements_mp2) == 1


def test_get_all_requirements_by_priority(mapper, masterplan_id):
    """Test filtering requirements by priority"""

    mapper.add_requirement(
        requirement_id="REQ-MUST-1",
        masterplan_id=masterplan_id,
        description="Must requirement",
        priority=RequirementPriority.MUST
    )
    mapper.add_requirement(
        requirement_id="REQ-MUST-2",
        masterplan_id=masterplan_id,
        description="Must requirement",
        priority=RequirementPriority.MUST
    )
    mapper.add_requirement(
        requirement_id="REQ-SHOULD-1",
        masterplan_id=masterplan_id,
        description="Should requirement",
        priority=RequirementPriority.SHOULD
    )

    must_requirements = mapper.get_all_requirements(priority=RequirementPriority.MUST)
    assert len(must_requirements) == 2

    should_requirements = mapper.get_all_requirements(priority=RequirementPriority.SHOULD)
    assert len(should_requirements) == 1


def test_get_all_requirements_by_masterplan_and_priority(mapper):
    """Test filtering requirements by both masterplan and priority"""

    masterplan_1 = uuid4()
    masterplan_2 = uuid4()

    mapper.add_requirement(
        requirement_id="REQ-MP1-MUST",
        masterplan_id=masterplan_1,
        description="Must for MP1",
        priority=RequirementPriority.MUST
    )
    mapper.add_requirement(
        requirement_id="REQ-MP1-SHOULD",
        masterplan_id=masterplan_1,
        description="Should for MP1",
        priority=RequirementPriority.SHOULD
    )
    mapper.add_requirement(
        requirement_id="REQ-MP2-MUST",
        masterplan_id=masterplan_2,
        description="Must for MP2",
        priority=RequirementPriority.MUST
    )

    requirements = mapper.get_all_requirements(
        masterplan_id=masterplan_1,
        priority=RequirementPriority.MUST
    )
    assert len(requirements) == 1
    assert requirements[0].requirement_id == "REQ-MP1-MUST"


# ============================================================
# Test: Edge Cases
# ============================================================

def test_get_tests_for_requirement_with_no_tests(mapper, masterplan_id):
    """Test getting tests for requirement with no mapped tests"""

    mapper.add_requirement(
        requirement_id="REQ-001",
        masterplan_id=masterplan_id,
        description="Requirement",
        priority=RequirementPriority.MUST
    )

    tests = mapper.get_tests_for_requirement("REQ-001")
    assert tests == []


def test_get_tests_for_nonexistent_requirement(mapper):
    """Test getting tests for non-existent requirement"""

    tests = mapper.get_tests_for_requirement("REQ-999")
    assert tests == []


def test_get_test_by_id(mapper, masterplan_id):
    """Test retrieving test by ID"""

    mapper.add_requirement(
        requirement_id="REQ-001",
        masterplan_id=masterplan_id,
        description="Requirement",
        priority=RequirementPriority.MUST
    )

    mapper.map_test_to_requirement(
        test_id="TEST-001",
        requirement_id="REQ-001",
        description="Test",
        test_type="case"
    )

    test = mapper.get_test("TEST-001")
    assert test is not None
    assert test.test_id == "TEST-001"


def test_get_test_not_found(mapper):
    """Test retrieving non-existent test"""

    test = mapper.get_test("TEST-999")
    assert test is None
