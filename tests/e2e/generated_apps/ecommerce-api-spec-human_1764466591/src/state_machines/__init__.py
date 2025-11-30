"""
State machine implementations for business entities.
"""
from enum import Enum
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass


class BaseStateMachine:
    """Base class for state machines."""

    def __init__(self, initial_state: str):
        self.current_state = initial_state
        self.transition_history = []
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def transition_to(self, new_state: str, context: Dict[str, Any] = None) -> bool:
        """
        Attempt to transition to a new state.

        Args:
            new_state: Target state
            context: Optional transition context

        Returns:
            True if transition successful

        Raises:
            StateTransitionError: If transition is invalid
        """
        if not self.can_transition_to(new_state):
            raise StateTransitionError(
                f"Cannot transition from {self.current_state} to {new_state}"
            )

        old_state = self.current_state
        self.current_state = new_state
        self.transition_history.append({
            "from": old_state,
            "to": new_state,
            "context": context
        })

        self.logger.info(f"Transitioned from {old_state} to {new_state}")
        return True

    def can_transition_to(self, new_state: str) -> bool:
        """Check if transition to new_state is valid."""
        raise NotImplementedError("Subclasses must implement can_transition_to")

    def get_valid_transitions(self) -> List[str]:
        """Get list of valid transitions from current state."""
        raise NotImplementedError("Subclasses must implement get_valid_transitions")