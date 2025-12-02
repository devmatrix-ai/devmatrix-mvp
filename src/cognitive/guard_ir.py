"""
Guard IR - Domain-Agnostic Guard Expression Model

This module defines the intermediate representation for guards/constraints
that is completely independent of any specific domain (no Cart, Order, Product).

All expressions use abstract references to entities and fields from the IR.
The CodeGenerationService is responsible for translating these to concrete
Python code using a varmap.
"""

from dataclasses import dataclass, field
from typing import Literal, Union, Tuple, List

# =============================================================================
# Reference Types - Abstract pointers to IR elements
# =============================================================================

# EntityRef: ("entity:EntityName", "field_name")
# Examples: ("entity:X", "status"), ("entity:Y", "quantity")
EntityRef = Tuple[str, str]

# ContextRef: ("context_role", "field_name")
# Examples: ("input", "quantity"), ("current_user", "id")
ContextRef = Tuple[str, str]

# Unified reference type
Ref = Union[EntityRef, ContextRef]


# =============================================================================
# Guard Expressions - Domain-Agnostic Logic
# =============================================================================

@dataclass(frozen=True)
class ComparisonExpr:
    """
    Comparison between two references or a reference and a literal.
    
    Examples:
        - ("entity:X", "quantity") <= ("entity:Y", "stock")
        - ("entity:X", "price") > 0
    """
    left: Ref
    op: Literal["<", "<=", "==", "!=", ">=", ">"]
    right: Union[Ref, float, int, str]


@dataclass(frozen=True)
class MembershipExpr:
    """
    Check if a field value is in/not in a set of allowed values.
    
    Examples:
        - ("entity:X", "status") in ["OPEN", "PENDING"]
        - ("entity:X", "type") not in ["CANCELLED", "DELETED"]
    """
    left: Ref
    op: Literal["in", "not in"]
    right: List[str]


@dataclass(frozen=True)
class ExistsExpr:
    """
    Check if a related entity exists.
    
    Examples:
        - ("entity:X", "id") exists as entity
        - ("entity:X", "parent_id") exists as relation
    """
    target: Ref
    kind: Literal["entity", "relation"]


@dataclass(frozen=True)
class NotEmptyExpr:
    """
    Check if a collection is not empty.
    
    Examples:
        - ("entity:X", "items") is not empty
    """
    target: Ref


@dataclass(frozen=True)
class LogicalExpr:
    """
    Combine multiple expressions with AND/OR.
    
    Examples:
        - expr1 AND expr2
        - expr1 OR expr2
    """
    op: Literal["and", "or"]
    operands: List["GuardExpr"]


# Union of all expression types
GuardExpr = Union[ComparisonExpr, MembershipExpr, ExistsExpr, NotEmptyExpr, LogicalExpr]


# =============================================================================
# Guard Specification - Complete guard with metadata
# =============================================================================

@dataclass(frozen=True)
class GuardSpec:
    """
    Complete specification of a guard with its expression and metadata.
    
    Attributes:
        expr: The guard expression (domain-agnostic)
        error_code: HTTP status code to return on failure (422/404/409)
        message: Error message template (may contain {field} placeholders)
        source_constraint_id: ID of the originating constraint in IR (traceability)
        phase: When to evaluate this guard (pre/post/invariant)
    """
    expr: GuardExpr
    error_code: int
    message: str
    source_constraint_id: str
    phase: Literal["pre", "post", "invariant"]


@dataclass
class FlowGuards:
    """
    Collection of guards for a specific flow/operation.
    
    Attributes:
        pre: Guards to check before the operation
        post: Guards to check after the operation
        invariants: Guards that must always hold
    """
    pre: List[GuardSpec] = field(default_factory=list)
    post: List[GuardSpec] = field(default_factory=list)
    invariants: List[GuardSpec] = field(default_factory=list)


# =============================================================================
# Flow Key - Identifier for a specific flow
# =============================================================================

# FlowKey: (entity_name, operation_name)
# Examples: ("X", "create"), ("Y", "update"), ("Z", "transition_status")
FlowKey = Tuple[str, str]


# =============================================================================
# Helper Functions - Create refs in a consistent way
# =============================================================================

def make_entity_ref(entity: str, field: str) -> EntityRef:
    """
    Create a reference to an entity's field.

    Args:
        entity: Entity name (e.g., "Order", "Cart")
        field: Field name (e.g., "status", "quantity")

    Returns:
        EntityRef tuple ("entity:Order", "status")
    """
    return (f"entity:{entity}", field)


def make_input_ref(field: str) -> ContextRef:
    """
    Create a reference to an input/payload field.

    Args:
        field: Field name in the input payload

    Returns:
        ContextRef tuple ("input", "quantity")
    """
    return ("input", field)


def make_context_ref(context: str, field: str) -> ContextRef:
    """
    Create a reference to a context field.

    Args:
        context: Context role (e.g., "current_user", "session")
        field: Field name

    Returns:
        ContextRef tuple
    """
    return (context, field)

