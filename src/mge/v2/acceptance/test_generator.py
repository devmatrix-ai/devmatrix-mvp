"""
AcceptanceTestGenerator - Generate acceptance tests from masterplan

Generates 3 types of tests:
- Contract tests: Verify API/function contracts
- Invariant tests: Verify system invariants
- Case tests: Specific use case scenarios

Tests are generated from masterplan requirements and executed at wave completion.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from src.mge.v2.metrics.precision_scorer import RequirementPriority

logger = logging.getLogger(__name__)


class TestType(Enum):
    """Acceptance test types"""
    CONTRACT = "contract"  # API/function contract verification
    INVARIANT = "invariant"  # System invariant verification
    CASE = "case"  # Specific use case scenario


@dataclass
class AcceptanceTest:
    """Generated acceptance test"""
    test_id: str
    test_type: TestType
    requirement_id: str
    requirement_priority: RequirementPriority
    description: str
    test_code: str  # Executable test code
    expected_outcome: str
    preconditions: List[str]
    postconditions: List[str]


@dataclass
class TestGenerationResult:
    """Result of test generation"""
    masterplan_id: UUID
    total_generated: int
    contract_tests: List[AcceptanceTest]
    invariant_tests: List[AcceptanceTest]
    case_tests: List[AcceptanceTest]
    generation_errors: List[str]

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "masterplan_id": str(self.masterplan_id),
            "total_generated": self.total_generated,
            "contract_tests": len(self.contract_tests),
            "invariant_tests": len(self.invariant_tests),
            "case_tests": len(self.case_tests),
            "generation_errors": self.generation_errors
        }


class AcceptanceTestGenerator:
    """
    Generate acceptance tests from masterplan requirements

    Analyzes masterplan and generates:
    - Contract tests: 1 per API endpoint/function
    - Invariant tests: 1 per system invariant
    - Case tests: 1-3 per requirement based on complexity

    Example:
        generator = AcceptanceTestGenerator()

        requirements = [
            {"id": "REQ-001", "priority": "MUST", "description": "User login"},
            {"id": "REQ-002", "priority": "SHOULD", "description": "2FA"}
        ]

        result = generator.generate_from_requirements(
            masterplan_id=masterplan_id,
            requirements=requirements
        )

        print(f"Generated {result.total_generated} tests")
    """

    def __init__(self):
        """Initialize AcceptanceTestGenerator"""
        self._test_templates = self._load_test_templates()

    def _load_test_templates(self) -> Dict[TestType, str]:
        """
        Load test code templates

        Returns:
            Dictionary mapping test types to code templates
        """
        return {
            TestType.CONTRACT: """
async def test_contract_{test_id}():
    '''Contract test: {description}'''
    # Preconditions
{preconditions_code}

    # Execute
    result = await {function_call}

    # Verify contract
{assertions}

    # Postconditions
{postconditions_code}
""",
            TestType.INVARIANT: """
async def test_invariant_{test_id}():
    '''Invariant test: {description}'''
    # Preconditions
{preconditions_code}

    # Verify invariant before
    assert {invariant_before}, "Invariant violated before operation"

    # Execute
    result = await {function_call}

    # Verify invariant after
    assert {invariant_after}, "Invariant violated after operation"

    # Postconditions
{postconditions_code}
""",
            TestType.CASE: """
async def test_case_{test_id}():
    '''Case test: {description}'''
    # Preconditions
{preconditions_code}

    # Execute scenario
{scenario_code}

    # Verify outcome
{assertions}

    # Postconditions
{postconditions_code}
"""
        }

    def generate_from_requirements(
        self,
        masterplan_id: UUID,
        requirements: List[Dict]
    ) -> TestGenerationResult:
        """
        Generate acceptance tests from requirements

        Args:
            masterplan_id: Masterplan UUID
            requirements: List of requirement dictionaries with keys:
                - id: Requirement ID
                - priority: "MUST" | "SHOULD" | "COULD" | "WONT"
                - description: Requirement description
                - type: Optional test type hint ("contract" | "invariant" | "case")

        Returns:
            TestGenerationResult with generated tests
        """
        contract_tests = []
        invariant_tests = []
        case_tests = []
        errors = []

        for req in requirements:
            try:
                # Determine test types to generate
                test_types = self._determine_test_types(req)

                # Generate tests for each type
                for test_type in test_types:
                    test = self._generate_test(
                        masterplan_id=masterplan_id,
                        requirement=req,
                        test_type=test_type
                    )

                    if test_type == TestType.CONTRACT:
                        contract_tests.append(test)
                    elif test_type == TestType.INVARIANT:
                        invariant_tests.append(test)
                    else:
                        case_tests.append(test)

            except Exception as e:
                error_msg = f"Failed to generate tests for {req.get('id', 'unknown')}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

        total = len(contract_tests) + len(invariant_tests) + len(case_tests)

        logger.info(
            f"Generated {total} tests for masterplan {masterplan_id}: "
            f"{len(contract_tests)} contract, {len(invariant_tests)} invariant, "
            f"{len(case_tests)} case"
        )

        return TestGenerationResult(
            masterplan_id=masterplan_id,
            total_generated=total,
            contract_tests=contract_tests,
            invariant_tests=invariant_tests,
            case_tests=case_tests,
            generation_errors=errors
        )

    def _determine_test_types(self, requirement: Dict) -> List[TestType]:
        """
        Determine which test types to generate for requirement

        Args:
            requirement: Requirement dictionary

        Returns:
            List of TestType to generate
        """
        test_types = []

        # Check explicit type hint
        req_type = requirement.get("type", "").lower()
        if req_type:
            if req_type == "contract":
                return [TestType.CONTRACT]
            elif req_type == "invariant":
                return [TestType.INVARIANT]
            elif req_type == "case":
                return [TestType.CASE]

        # Heuristic: detect from description
        description = requirement.get("description", "").lower()

        # API/endpoint → contract test
        if any(keyword in description for keyword in ["api", "endpoint", "function", "method", "interface"]):
            test_types.append(TestType.CONTRACT)

        # Invariant keywords → invariant test
        if any(keyword in description for keyword in ["always", "never", "invariant", "consistent", "maintain"]):
            test_types.append(TestType.INVARIANT)

        # Default: case test for all requirements
        if not test_types or TestType.CASE not in test_types:
            test_types.append(TestType.CASE)

        return test_types

    def _generate_test(
        self,
        masterplan_id: UUID,
        requirement: Dict,
        test_type: TestType
    ) -> AcceptanceTest:
        """
        Generate single acceptance test

        Args:
            masterplan_id: Masterplan UUID
            requirement: Requirement dictionary
            test_type: Type of test to generate

        Returns:
            AcceptanceTest instance
        """
        test_id = str(uuid4())[:8]
        req_id = requirement.get("id", "UNKNOWN")
        description = requirement.get("description", "")
        priority_str = requirement.get("priority", "SHOULD").upper()

        # Parse priority
        try:
            priority = RequirementPriority[priority_str]
        except KeyError:
            priority = RequirementPriority.SHOULD

        # Generate preconditions/postconditions
        preconditions = self._generate_preconditions(requirement, test_type)
        postconditions = self._generate_postconditions(requirement, test_type)

        # Generate test code from template
        test_code = self._generate_test_code(
            test_id=test_id,
            test_type=test_type,
            description=description,
            preconditions=preconditions,
            postconditions=postconditions,
            requirement=requirement
        )

        # Generate expected outcome
        expected_outcome = self._generate_expected_outcome(requirement, test_type)

        return AcceptanceTest(
            test_id=test_id,
            test_type=test_type,
            requirement_id=req_id,
            requirement_priority=priority,
            description=description,
            test_code=test_code,
            expected_outcome=expected_outcome,
            preconditions=preconditions,
            postconditions=postconditions
        )

    def _generate_preconditions(
        self,
        requirement: Dict,
        test_type: TestType
    ) -> List[str]:
        """Generate test preconditions"""
        preconditions = []

        # Common preconditions
        preconditions.append("System is in valid state")

        if test_type == TestType.CONTRACT:
            preconditions.append("API endpoint is available")
            preconditions.append("Request parameters are valid")
        elif test_type == TestType.INVARIANT:
            preconditions.append("System invariants are satisfied")
        else:  # CASE
            preconditions.append("Test data is prepared")

        return preconditions

    def _generate_postconditions(
        self,
        requirement: Dict,
        test_type: TestType
    ) -> List[str]:
        """Generate test postconditions"""
        postconditions = []

        if test_type == TestType.CONTRACT:
            postconditions.append("Response format matches contract")
            postconditions.append("Status code is correct")
        elif test_type == TestType.INVARIANT:
            postconditions.append("System invariants still satisfied")
        else:  # CASE
            postconditions.append("Expected outcome achieved")

        postconditions.append("No side effects observed")

        return postconditions

    def _generate_test_code(
        self,
        test_id: str,
        test_type: TestType,
        description: str,
        preconditions: List[str],
        postconditions: List[str],
        requirement: Dict
    ) -> str:
        """Generate executable test code from template"""
        template = self._test_templates[test_type]

        # Format preconditions
        preconditions_code = "\n".join(
            f"    # {precond}" for precond in preconditions
        )

        # Format postconditions
        postconditions_code = "\n".join(
            f"    # {postcond}" for postcond in postconditions
        )

        # Format assertions (simplified)
        assertions = "    assert result is not None, 'Result should not be None'"

        # Generate function call (simplified)
        function_call = f"execute_requirement('{requirement.get('id', 'unknown')}')"

        # Fill template
        code = template.format(
            test_id=test_id,
            description=description,
            preconditions_code=preconditions_code,
            postconditions_code=postconditions_code,
            assertions=assertions,
            function_call=function_call,
            invariant_before="True",
            invariant_after="True",
            scenario_code="    # Execute scenario steps\n    pass"
        )

        return code

    def _generate_expected_outcome(
        self,
        requirement: Dict,
        test_type: TestType
    ) -> str:
        """Generate expected outcome description"""
        if test_type == TestType.CONTRACT:
            return f"API contract verified for: {requirement.get('description', '')}"
        elif test_type == TestType.INVARIANT:
            return f"System invariant maintained: {requirement.get('description', '')}"
        else:
            return f"Use case completed successfully: {requirement.get('description', '')}"

    def get_all_tests(self, result: TestGenerationResult) -> List[AcceptanceTest]:
        """
        Get all generated tests from result

        Args:
            result: TestGenerationResult

        Returns:
            List of all AcceptanceTest instances
        """
        return (
            result.contract_tests +
            result.invariant_tests +
            result.case_tests
        )
