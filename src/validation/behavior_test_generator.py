"""
Behavior Test Generator - Generates test scenarios from BehaviorModelIR.

Instead of manually writing smoke tests, this generates them from:
- Flow definitions (preconditions, postconditions)
- Invariants (what must always be true)
- State transitions (valid status changes)

This ensures tests are always in sync with IR.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ScenarioType(str, Enum):
    """Types of test scenarios."""
    HAPPY_PATH = "happy_path"
    GUARD_VIOLATION = "guard_violation"
    TRANSITION_VALID = "transition_valid"
    TRANSITION_INVALID = "transition_invalid"
    INVARIANT_CHECK = "invariant_check"


@dataclass
class TestStep:
    """A step in a test scenario."""
    order: int
    method: str
    endpoint: str
    body: Optional[Dict[str, Any]] = None
    expected_status: int = 200
    expected_in_response: Optional[Dict[str, Any]] = None


@dataclass
class TestScenario:
    """A complete test scenario."""
    scenario_id: str
    name: str
    scenario_type: ScenarioType
    flow_id: Optional[str] = None
    entity: Optional[str] = None
    steps: List[TestStep] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    expected_outcome: str = "success"


class BehaviorTestGenerator:
    """
    Generates test scenarios from BehaviorModelIR.
    
    Creates:
    - Happy path tests for each flow
    - Guard violation tests (expect 422)
    - Valid transition tests
    - Invalid transition tests (expect 422)
    """
    
    def __init__(self):
        self.scenarios: List[TestScenario] = []
        self._counter = 0
    
    def generate_from_ir(self, behavior_ir: Any) -> List[TestScenario]:
        """Generate all test scenarios from BehaviorModelIR."""
        self.scenarios = []
        
        if not behavior_ir:
            return []
        
        # Generate from flows
        for flow in getattr(behavior_ir, 'flows', []):
            self._generate_flow_tests(flow)
        
        # Generate from invariants
        for invariant in getattr(behavior_ir, 'invariants', []):
            self._generate_invariant_tests(invariant)
        
        logger.info(f"Generated {len(self.scenarios)} test scenarios from IR")
        return self.scenarios
    
    def _generate_flow_tests(self, flow: Any):
        """Generate tests for a flow."""
        flow_id = getattr(flow, 'flow_id', None) or getattr(flow, 'name', 'unknown')
        entity = getattr(flow, 'primary_entity', None)
        endpoint = getattr(flow, 'endpoint', None)
        
        if not endpoint:
            return
        
        # 1. Happy path test
        self._counter += 1
        happy = TestScenario(
            scenario_id=f"test:{self._counter}",
            name=f"Happy path: {flow_id}",
            scenario_type=ScenarioType.HAPPY_PATH,
            flow_id=flow_id,
            entity=entity,
            steps=[TestStep(
                order=1,
                method=self._infer_method(endpoint),
                endpoint=endpoint,
                expected_status=self._infer_success_status(endpoint)
            )],
            preconditions=getattr(flow, 'preconditions', []),
            expected_outcome="success"
        )
        self.scenarios.append(happy)
        
        # 2. Guard violation tests (one per precondition)
        for i, precond in enumerate(getattr(flow, 'preconditions', [])):
            self._counter += 1
            guard_test = TestScenario(
                scenario_id=f"test:{self._counter}",
                name=f"Guard violation: {flow_id} - {precond[:30]}",
                scenario_type=ScenarioType.GUARD_VIOLATION,
                flow_id=flow_id,
                entity=entity,
                steps=[TestStep(
                    order=1,
                    method=self._infer_method(endpoint),
                    endpoint=endpoint,
                    expected_status=422  # Guard should reject
                )],
                preconditions=[f"NOT({precond})"],
                expected_outcome="guard_rejection"
            )
            self.scenarios.append(guard_test)
    
    def _generate_invariant_tests(self, invariant: Any):
        """Generate tests for an invariant."""
        entity = getattr(invariant, 'entity', 'Unknown')
        description = getattr(invariant, 'description', '')
        
        self._counter += 1
        self.scenarios.append(TestScenario(
            scenario_id=f"test:{self._counter}",
            name=f"Invariant check: {entity} - {description[:30]}",
            scenario_type=ScenarioType.INVARIANT_CHECK,
            entity=entity,
            expected_outcome="invariant_holds"
        ))
    
    def generate_transition_tests(self, entity: str, transitions: Dict[str, List[str]]) -> List[TestScenario]:
        """Generate tests for status transitions."""
        tests = []
        
        for from_status, to_statuses in transitions.items():
            # Valid transitions
            for to_status in to_statuses:
                self._counter += 1
                tests.append(TestScenario(
                    scenario_id=f"test:{self._counter}",
                    name=f"Valid transition: {entity} {from_status}→{to_status}",
                    scenario_type=ScenarioType.TRANSITION_VALID,
                    entity=entity,
                    expected_outcome="success"
                ))
            
            # Invalid transition (to a status not in valid list)
            invalid_to = "INVALID_STATUS"
            self._counter += 1
            tests.append(TestScenario(
                scenario_id=f"test:{self._counter}",
                name=f"Invalid transition: {entity} {from_status}→{invalid_to}",
                scenario_type=ScenarioType.TRANSITION_INVALID,
                entity=entity,
                steps=[TestStep(1, "PUT", f"/{entity.lower()}s/{{id}}", 
                               {"status": invalid_to}, expected_status=422)],
                expected_outcome="rejection"
            ))
        
        self.scenarios.extend(tests)
        return tests
    
    def _infer_method(self, endpoint: str) -> str:
        """Infer HTTP method from endpoint pattern."""
        if '{' in endpoint and '/items' in endpoint:
            return "POST"  # Add item
        if '{' in endpoint:
            return "PUT"  # Update
        return "POST"  # Create
    
    def _infer_success_status(self, endpoint: str) -> int:
        """Infer expected success status."""
        method = self._infer_method(endpoint)
        if method == "POST":
            return 201
        if method == "DELETE":
            return 204
        return 200
    
    def get_scenarios_for_entity(self, entity: str) -> List[TestScenario]:
        """Get all scenarios for an entity."""
        return [s for s in self.scenarios 
                if s.entity and s.entity.lower() == entity.lower()]

