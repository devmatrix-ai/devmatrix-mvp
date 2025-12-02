"""
ICBR - Intermediate Canonical Behavior Representation.

This is the bridge between BehaviorModelIR and code generation.
Provides deterministic lowering of behavior logic to executable constructs.

Key guarantees:
- Same input BehaviorModelIR → Same ICBR output (determinism)
- All preconditions/postconditions/guards are canonicalized
- No LLM involvement in lowering (pure transformation)
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Set
from enum import Enum
import hashlib

from .behavior_model import BehaviorModelIR, Flow, FlowType, Invariant, Step


class PredicateType(str, Enum):
    """Types of canonical predicates."""
    EXISTENCE = "existence"      # entity.exists
    COMPARISON = "comparison"    # field > value
    MEMBERSHIP = "membership"    # field in [values]
    STATE = "state"              # entity.status == value
    REFERENCE = "reference"      # entity.ref_id → other.id


class OperationType(str, Enum):
    """Types of atomic operations."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    TRANSITION = "transition"    # Status change
    DECREMENT = "decrement"      # Stock decrease
    INCREMENT = "increment"      # Stock increase
    VALIDATE = "validate"        # Check without modify


@dataclass
class CanonicalPredicate:
    """A canonicalized boolean predicate."""
    predicate_id: str
    predicate_type: PredicateType
    entity: str
    field: Optional[str] = None
    operator: Optional[str] = None  # ==, >, <, >=, <=, in, exists
    value: Optional[Any] = None
    expression: Optional[str] = None  # Raw expression if complex
    
    def to_python_expression(self) -> str:
        """Convert to executable Python expression."""
        if self.expression:
            return self.expression
        if self.predicate_type == PredicateType.EXISTENCE:
            return f"{self.entity.lower()} is not None"
        if self.predicate_type == PredicateType.STATE:
            return f"{self.entity.lower()}.{self.field} == '{self.value}'"
        if self.predicate_type == PredicateType.COMPARISON:
            return f"{self.entity.lower()}.{self.field} {self.operator} {self.value}"
        if self.predicate_type == PredicateType.REFERENCE:
            return f"await db.get({self.value}, {self.entity.lower()}.{self.field}) is not None"
        return self.expression or "True"


@dataclass
class CanonicalGuard:
    """A guard that must be true before an operation."""
    guard_id: str
    name: str
    predicates: List[str]  # List of predicate_ids that must ALL be true
    error_code: int = 422
    error_message: str = "Guard failed"
    
    def to_python_check(self, predicates_map: Dict[str, CanonicalPredicate]) -> str:
        """Generate Python guard check code."""
        conditions = []
        for pred_id in self.predicates:
            if pred_id in predicates_map:
                conditions.append(predicates_map[pred_id].to_python_expression())
        if not conditions:
            return ""
        condition = " and ".join(conditions)
        return f'if not ({condition}):\n    raise HTTPException(status_code={self.error_code}, detail="{self.error_message}")'


@dataclass
class AtomicOperation:
    """An atomic operation on an entity."""
    operation_id: str
    operation_type: OperationType
    entity: str
    field: Optional[str] = None
    value: Optional[Any] = None
    guards: List[str] = field(default_factory=list)  # guard_ids that must pass


@dataclass
class StateTransition:
    """A valid state transition."""
    transition_id: str
    entity: str
    from_state: str
    to_state: str
    guards: List[str] = field(default_factory=list)
    effects: List[str] = field(default_factory=list)  # operation_ids to execute


@dataclass
class CanonicalInvariant:
    """An invariant that must always hold."""
    invariant_id: str
    entity: str
    description: str
    predicate_id: str  # The predicate that must always be true
    enforcement_level: str = "strict"  # strict, eventual


@dataclass
class ICBR:
    """
    Intermediate Canonical Behavior Representation.
    
    This is the deterministic lowering of BehaviorModelIR to
    a form that can be directly translated to code.
    """
    # Core elements
    predicates: Dict[str, CanonicalPredicate] = field(default_factory=dict)
    guards: Dict[str, CanonicalGuard] = field(default_factory=dict)
    operations: Dict[str, AtomicOperation] = field(default_factory=dict)
    transitions: Dict[str, StateTransition] = field(default_factory=dict)
    invariants: Dict[str, CanonicalInvariant] = field(default_factory=dict)
    
    # Metadata
    source_flows: List[str] = field(default_factory=list)  # Flow IDs this came from
    version: str = "1.0.0"
    
    def get_guards_for_entity(self, entity: str) -> List[CanonicalGuard]:
        """Get all guards that apply to an entity."""
        # Guards apply if their predicates reference the entity
        result = []
        for guard in self.guards.values():
            for pred_id in guard.predicates:
                if pred_id in self.predicates:
                    if self.predicates[pred_id].entity.lower() == entity.lower():
                        result.append(guard)
                        break
        return result
    
    def get_transitions_for_entity(self, entity: str) -> List[StateTransition]:
        """Get all valid transitions for an entity."""
        return [t for t in self.transitions.values() 
                if t.entity.lower() == entity.lower()]
    
    def compute_hash(self) -> str:
        """Compute deterministic hash of ICBR for caching."""
        content = f"{len(self.predicates)}:{len(self.guards)}:{len(self.operations)}"
        content += f":{len(self.transitions)}:{len(self.invariants)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

