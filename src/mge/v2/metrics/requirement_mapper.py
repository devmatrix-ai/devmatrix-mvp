"""
RequirementMapper - Map requirements to acceptance tests

Maps masterplan requirements to their corresponding acceptance tests.
Tracks must/should requirements and validates test coverage.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from uuid import UUID

from src.mge.v2.metrics.precision_scorer import RequirementPriority

logger = logging.getLogger(__name__)


@dataclass
class Requirement:
    """Requirement specification"""
    requirement_id: str
    masterplan_id: UUID
    description: str
    priority: RequirementPriority
    test_ids: List[str]  # Mapped acceptance test IDs
    category: Optional[str] = None


@dataclass
class AcceptanceTest:
    """Acceptance test specification"""
    test_id: str
    requirement_id: str
    description: str
    test_type: str  # "contract", "invariant", "case"
    passed: bool


class RequirementMapper:
    """
    Map requirements to acceptance tests

    Provides mapping between requirements and tests, validates coverage,
    and checks for orphaned tests or requirements.

    Example:
        mapper = RequirementMapper()

        # Add requirement
        mapper.add_requirement(
            requirement_id="REQ-001",
            masterplan_id=masterplan_id,
            description="User can login with email/password",
            priority=RequirementPriority.MUST
        )

        # Map test to requirement
        mapper.map_test_to_requirement(
            test_id="TEST-001",
            requirement_id="REQ-001",
            description="Test login with valid credentials",
            test_type="case"
        )

        # Validate coverage
        coverage = mapper.validate_coverage(masterplan_id)
    """

    def __init__(self):
        """Initialize RequirementMapper"""
        self._requirements: Dict[str, Requirement] = {}
        self._tests: Dict[str, AcceptanceTest] = {}
        self._req_to_tests: Dict[str, Set[str]] = {}  # requirement_id -> test_ids
        self._test_to_req: Dict[str, str] = {}  # test_id -> requirement_id

    def add_requirement(
        self,
        requirement_id: str,
        masterplan_id: UUID,
        description: str,
        priority: RequirementPriority,
        category: Optional[str] = None
    ) -> Requirement:
        """
        Add requirement to mapper

        Args:
            requirement_id: Unique requirement ID
            masterplan_id: Masterplan UUID
            description: Requirement description
            priority: Requirement priority (MUST/SHOULD/COULD/WONT)
            category: Optional category (e.g., "auth", "api", "ui")

        Returns:
            Requirement instance
        """

        requirement = Requirement(
            requirement_id=requirement_id,
            masterplan_id=masterplan_id,
            description=description,
            priority=priority,
            test_ids=[],
            category=category
        )

        self._requirements[requirement_id] = requirement
        self._req_to_tests[requirement_id] = set()

        logger.debug(
            f"Added requirement {requirement_id} ({priority.value}): {description}"
        )

        return requirement

    def map_test_to_requirement(
        self,
        test_id: str,
        requirement_id: str,
        description: str,
        test_type: str,
        passed: bool = False
    ) -> AcceptanceTest:
        """
        Map acceptance test to requirement

        Args:
            test_id: Unique test ID
            requirement_id: Requirement ID this test covers
            description: Test description
            test_type: Test type ("contract", "invariant", "case")
            passed: Test pass status

        Returns:
            AcceptanceTest instance

        Raises:
            ValueError: If requirement_id doesn't exist
        """

        if requirement_id not in self._requirements:
            raise ValueError(f"Requirement {requirement_id} not found")

        test = AcceptanceTest(
            test_id=test_id,
            requirement_id=requirement_id,
            description=description,
            test_type=test_type,
            passed=passed
        )

        self._tests[test_id] = test
        self._req_to_tests[requirement_id].add(test_id)
        self._test_to_req[test_id] = requirement_id

        # Update requirement's test_ids
        self._requirements[requirement_id].test_ids = list(self._req_to_tests[requirement_id])

        logger.debug(
            f"Mapped test {test_id} ({test_type}) to requirement {requirement_id}"
        )

        return test

    def update_test_status(self, test_id: str, passed: bool) -> None:
        """
        Update test pass/fail status

        Args:
            test_id: Test ID
            passed: Test passed status

        Raises:
            ValueError: If test_id doesn't exist
        """

        if test_id not in self._tests:
            raise ValueError(f"Test {test_id} not found")

        self._tests[test_id].passed = passed
        logger.debug(f"Updated test {test_id} status: {'PASSED' if passed else 'FAILED'}")

    def get_requirement(self, requirement_id: str) -> Optional[Requirement]:
        """Get requirement by ID"""
        return self._requirements.get(requirement_id)

    def get_test(self, test_id: str) -> Optional[AcceptanceTest]:
        """Get test by ID"""
        return self._tests.get(test_id)

    def get_tests_for_requirement(self, requirement_id: str) -> List[AcceptanceTest]:
        """
        Get all tests for a requirement

        Args:
            requirement_id: Requirement ID

        Returns:
            List of AcceptanceTest instances
        """

        test_ids = self._req_to_tests.get(requirement_id, set())
        return [self._tests[tid] for tid in test_ids if tid in self._tests]

    def get_requirement_for_test(self, test_id: str) -> Optional[Requirement]:
        """
        Get requirement for a test

        Args:
            test_id: Test ID

        Returns:
            Requirement instance or None
        """

        requirement_id = self._test_to_req.get(test_id)
        if requirement_id:
            return self._requirements.get(requirement_id)
        return None

    def validate_coverage(self, masterplan_id: UUID) -> Dict:
        """
        Validate requirement → test coverage

        Checks:
        - All MUST requirements have at least one test
        - All SHOULD requirements have at least one test
        - No orphaned tests (test without requirement)

        Args:
            masterplan_id: Masterplan UUID

        Returns:
            Coverage report dict
        """

        # Filter requirements for this masterplan
        masterplan_requirements = [
            r for r in self._requirements.values()
            if r.masterplan_id == masterplan_id
        ]

        # Check coverage
        musts_without_tests = []
        shoulds_without_tests = []

        for req in masterplan_requirements:
            if req.priority == RequirementPriority.MUST and not req.test_ids:
                musts_without_tests.append(req.requirement_id)
            elif req.priority == RequirementPriority.SHOULD and not req.test_ids:
                shoulds_without_tests.append(req.requirement_id)

        # Find orphaned tests
        orphaned_tests = [
            tid for tid in self._tests.keys()
            if tid not in self._test_to_req
        ]

        # Calculate coverage
        musts = [r for r in masterplan_requirements if r.priority == RequirementPriority.MUST]
        shoulds = [r for r in masterplan_requirements if r.priority == RequirementPriority.SHOULD]

        musts_covered = len(musts) - len(musts_without_tests)
        shoulds_covered = len(shoulds) - len(shoulds_without_tests)

        must_coverage = (musts_covered / len(musts) * 100) if musts else 100.0
        should_coverage = (shoulds_covered / len(shoulds) * 100) if shoulds else 100.0

        coverage_report = {
            "masterplan_id": str(masterplan_id),
            "total_requirements": len(masterplan_requirements),
            "total_tests": len(self._tests),
            "must_requirements": {
                "total": len(musts),
                "covered": musts_covered,
                "uncovered": len(musts_without_tests),
                "coverage_percent": round(must_coverage, 2),
                "uncovered_ids": musts_without_tests
            },
            "should_requirements": {
                "total": len(shoulds),
                "covered": shoulds_covered,
                "uncovered": len(shoulds_without_tests),
                "coverage_percent": round(should_coverage, 2),
                "uncovered_ids": shoulds_without_tests
            },
            "orphaned_tests": orphaned_tests,
            "coverage_complete": len(musts_without_tests) == 0 and len(shoulds_without_tests) == 0
        }

        logger.info(
            f"Coverage for {masterplan_id}: "
            f"MUST {must_coverage:.1f}%, SHOULD {should_coverage:.1f}%"
        )

        return coverage_report

    def get_all_requirements(
        self,
        masterplan_id: Optional[UUID] = None,
        priority: Optional[RequirementPriority] = None
    ) -> List[Requirement]:
        """
        Get all requirements with optional filters

        Args:
            masterplan_id: Filter by masterplan
            priority: Filter by priority

        Returns:
            List of Requirement instances
        """

        requirements = list(self._requirements.values())

        if masterplan_id:
            requirements = [r for r in requirements if r.masterplan_id == masterplan_id]

        if priority:
            requirements = [r for r in requirements if r.priority == priority]

        return requirements
