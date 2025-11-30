"""
State machine for F15: Cancel Order entity.
"""
from enum import Enum
from typing import Dict, Any, List, Optional
from src.state_machines import BaseStateMachine, StateTransitionError

class F15CancelOrderState(Enum):
    """States for F15: Cancel Order entity."""
    INITIAL = "initial"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class F15CancelOrderStateMachine(BaseStateMachine):
    """
    State machine for F15: Cancel Order entity.

    Manages state transitions and enforces invariants.
    """

    def __init__(self, initial_state: F15CancelOrderState = None):
        if initial_state is None:
            initial_state = F15CancelOrderState.INITIAL
        super().__init__(initial_state.value)
        self.state_enum = F15CancelOrderState

    def can_transition_to(self, new_state: str) -> bool:
        """Check if transition to new_state is valid."""
        transitions = self._get_transition_map()
        current_transitions = transitions.get(self.current_state, [])
        return new_state in current_transitions

    def get_valid_transitions(self) -> List[str]:
        """Get list of valid transitions from current state."""
        transitions = self._get_transition_map()
        return transitions.get(self.current_state, [])

    def _get_transition_map(self) -> Dict[str, List[str]]:
        """Define valid state transitions."""
        return {
            "initial": ["processing"],
            "processing": ["completed", "error"],
            "completed": [],
            "error": ["processing"],
        }

    def validate_invariants(self, entity_data: Dict[str, Any]) -> bool:
        """
        Validate all invariants for the entity.

        Args:
            entity_data: Current entity data

        Returns:
            True if all invariants are satisfied
        """
        # Check: F15: Cancel Order uses Order
        # Extension point: Implement invariant check
        
        # Check: F15: Cancel Order uses Product
        # Extension point: Implement invariant check
        return True