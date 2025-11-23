"""
Behavior Model Intermediate Representation.

Defines the dynamic behavior of the system: flows, invariants, policies, and state transitions.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class FlowType(str, Enum):
    WORKFLOW = "workflow"      # Complex multi-step process
    STATE_TRANSITION = "state_transition"
    POLICY = "policy"          # Invariant or rule
    EVENT_HANDLER = "event_handler"

class Step(BaseModel):
    order: int
    description: str
    action: str
    target_entity: Optional[str] = None
    condition: Optional[str] = None

class Flow(BaseModel):
    name: str
    type: FlowType
    trigger: str  # e.g., "On Checkout", "Before Save"
    steps: List[Step] = Field(default_factory=list)
    description: Optional[str] = None

class Invariant(BaseModel):
    """A condition that must always be true."""
    entity: str
    description: str
    expression: Optional[str] = None  # e.g., "balance >= 0"
    enforcement_level: str = "strict" # strict, eventual

class BehaviorModelIR(BaseModel):
    flows: List[Flow] = Field(default_factory=list)
    invariants: List[Invariant] = Field(default_factory=list)
