"""
ValidationRoutingMatrix - Routes constraints to correct validation layer.

This eliminates misrouting problems where schema repair is applied to runtime errors.
Each constraint type is mapped to its correct handler layer.

Layers:
- schema: Pydantic validation (field types, formats, required)
- runtime: RuntimeFlowValidator (stock, status, business guards)
- workflow: FlowTransitionEngine (state machines, transitions)
- behavior: GuardEngine (preconditions, invariants)
"""
from enum import Enum
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class ValidationLayer(str, Enum):
    """Validation layers in the system."""
    SCHEMA = "schema"       # Pydantic, type validation
    RUNTIME = "runtime"     # Business logic at runtime
    WORKFLOW = "workflow"   # State machine transitions
    BEHAVIOR = "behavior"   # Guards, preconditions


class HandlerType(str, Enum):
    """Handler types for each layer."""
    PYDANTIC = "PydanticValidator"
    RUNTIME_FLOW = "RuntimeFlowValidator"
    TRANSITION_ENGINE = "FlowTransitionEngine"
    GUARD_ENGINE = "GuardEngine"


@dataclass
class RoutingEntry:
    """A single routing table entry."""
    constraint_type: str
    layer: ValidationLayer
    handler: HandlerType
    repair_strategy: str  # Maps to RepairStrategyType


# The routing matrix - maps constraint types to their correct layer
VALIDATION_ROUTING_MATRIX: Dict[str, RoutingEntry] = {
    # Schema layer constraints (Pydantic handles these)
    'field_constraint': RoutingEntry('field_constraint', ValidationLayer.SCHEMA, HandlerType.PYDANTIC, 'VALIDATION'),
    'type_constraint': RoutingEntry('type_constraint', ValidationLayer.SCHEMA, HandlerType.PYDANTIC, 'VALIDATION'),
    'format_constraint': RoutingEntry('format_constraint', ValidationLayer.SCHEMA, HandlerType.PYDANTIC, 'VALIDATION'),
    'required_field': RoutingEntry('required_field', ValidationLayer.SCHEMA, HandlerType.PYDANTIC, 'VALIDATION'),
    'enum_constraint': RoutingEntry('enum_constraint', ValidationLayer.SCHEMA, HandlerType.PYDANTIC, 'VALIDATION'),
    
    # Runtime layer constraints (RuntimeFlowValidator)
    'stock_constraint': RoutingEntry('stock_constraint', ValidationLayer.RUNTIME, HandlerType.RUNTIME_FLOW, 'SERVICE'),
    'quantity_constraint': RoutingEntry('quantity_constraint', ValidationLayer.RUNTIME, HandlerType.RUNTIME_FLOW, 'SERVICE'),
    'balance_constraint': RoutingEntry('balance_constraint', ValidationLayer.RUNTIME, HandlerType.RUNTIME_FLOW, 'SERVICE'),
    'inventory_constraint': RoutingEntry('inventory_constraint', ValidationLayer.RUNTIME, HandlerType.RUNTIME_FLOW, 'SERVICE'),
    'custom': RoutingEntry('custom', ValidationLayer.RUNTIME, HandlerType.RUNTIME_FLOW, 'SERVICE'),
    
    # Workflow layer constraints (FlowTransitionEngine)
    'status_transition': RoutingEntry('status_transition', ValidationLayer.WORKFLOW, HandlerType.TRANSITION_ENGINE, 'SERVICE'),
    'state_machine': RoutingEntry('state_machine', ValidationLayer.WORKFLOW, HandlerType.TRANSITION_ENGINE, 'SERVICE'),
    'workflow_constraint': RoutingEntry('workflow_constraint', ValidationLayer.WORKFLOW, HandlerType.TRANSITION_ENGINE, 'SERVICE'),
    
    # Behavior layer constraints (GuardEngine)
    'precondition': RoutingEntry('precondition', ValidationLayer.BEHAVIOR, HandlerType.GUARD_ENGINE, 'SERVICE'),
    'guard': RoutingEntry('guard', ValidationLayer.BEHAVIOR, HandlerType.GUARD_ENGINE, 'SERVICE'),
    'invariant': RoutingEntry('invariant', ValidationLayer.BEHAVIOR, HandlerType.GUARD_ENGINE, 'SERVICE'),
    'business_rule': RoutingEntry('business_rule', ValidationLayer.BEHAVIOR, HandlerType.GUARD_ENGINE, 'SERVICE'),
}


def get_routing(constraint_type: str) -> Optional[RoutingEntry]:
    """Get routing entry for a constraint type."""
    return VALIDATION_ROUTING_MATRIX.get(constraint_type.lower())


def get_layer_for_constraint(constraint_type: str) -> ValidationLayer:
    """Get the validation layer for a constraint type."""
    entry = get_routing(constraint_type)
    if entry:
        return entry.layer
    # Default: if unknown, assume schema (safest)
    logger.warning(f"Unknown constraint type '{constraint_type}', defaulting to SCHEMA layer")
    return ValidationLayer.SCHEMA


def get_repair_strategy(constraint_type: str) -> str:
    """Get the repair strategy for a constraint type."""
    entry = get_routing(constraint_type)
    if entry:
        return entry.repair_strategy
    return 'VALIDATION'  # Default to schema repair


def is_business_logic_constraint(constraint_type: str) -> bool:
    """Check if a constraint type is business logic (not schema)."""
    entry = get_routing(constraint_type)
    if entry:
        return entry.layer in (ValidationLayer.RUNTIME, ValidationLayer.WORKFLOW, ValidationLayer.BEHAVIOR)
    return False


def get_constraints_for_layer(layer: ValidationLayer) -> List[str]:
    """Get all constraint types handled by a layer."""
    return [ct for ct, entry in VALIDATION_ROUTING_MATRIX.items() if entry.layer == layer]


def classify_error_to_layer(status_code: int, error_detail: str) -> ValidationLayer:
    """
    Classify an HTTP error to a validation layer based on status code and detail.
    
    This is used when we don't have explicit constraint type info.
    """
    error_lower = error_detail.lower() if error_detail else ""
    
    # 422 errors
    if status_code == 422:
        # Check for business logic keywords
        if any(kw in error_lower for kw in ['stock', 'inventory', 'quantity', 'available']):
            return ValidationLayer.RUNTIME
        if any(kw in error_lower for kw in ['status', 'transition', 'state', 'cannot']):
            return ValidationLayer.WORKFLOW
        if any(kw in error_lower for kw in ['guard', 'precondition', 'must be', 'required first']):
            return ValidationLayer.BEHAVIOR
        # Default 422 is schema
        return ValidationLayer.SCHEMA
    
    # 500 errors are usually workflow/behavior
    if status_code == 500:
        return ValidationLayer.BEHAVIOR
    
    # 404 could be reference integrity
    if status_code == 404:
        return ValidationLayer.RUNTIME
    
    return ValidationLayer.SCHEMA


# Convenience: Layer → Handler mapping
LAYER_HANDLERS: Dict[ValidationLayer, HandlerType] = {
    ValidationLayer.SCHEMA: HandlerType.PYDANTIC,
    ValidationLayer.RUNTIME: HandlerType.RUNTIME_FLOW,
    ValidationLayer.WORKFLOW: HandlerType.TRANSITION_ENGINE,
    ValidationLayer.BEHAVIOR: HandlerType.GUARD_ENGINE,
}

