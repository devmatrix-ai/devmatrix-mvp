"""
Normalized Error Types for Smoke Repair Routing.

Provides enums for consistent error classification across the repair pipeline.
Ensures routing decisions are based on explicit type checks, not string matching.

Created: 2025-12-03
Reference: DOCS/mvp/exit/learning/LEARNING_SYSTEM_IMPLEMENTATION_PLAN.md
"""
from enum import Enum


class ViolationErrorType(str, Enum):
    """
    Normalized error types for routing violations to repair agents.
    
    Based on HTTP status codes and error semantics:
    - 404 → MISSING_PRECONDITION (entity doesn't exist)
    - 422 with business logic → BUSINESS_LOGIC (status/stock/workflow)
    - 422 with schema → SCHEMA_VALIDATION (Pydantic validation)
    - 500 → INTERNAL_ERROR (server crash)
    """
    MISSING_PRECONDITION = "MISSING_PRECONDITION"   # 404 - entity not found
    BUSINESS_LOGIC = "BUSINESS_LOGIC"              # 422 - status/stock/workflow
    SCHEMA_VALIDATION = "SCHEMA_VALIDATION"        # 422 - Pydantic validation
    INTERNAL_ERROR = "INTERNAL_ERROR"              # 500 - server error
    UNKNOWN = "UNKNOWN"                            # Fallback


class ConstraintType(str, Enum):
    """
    Normalized constraint types for SERVICE repair routing.
    
    These map to guard templates in ServiceRepairAgent:
    - STATUS_TRANSITION → status check guard
    - STOCK_CONSTRAINT → quantity check guard
    - WORKFLOW_CONSTRAINT → existence check guard
    - PRECONDITION_REQUIRED → precondition not met
    - CUSTOM → requires manual review
    """
    STATUS_TRANSITION = "status_transition"
    STOCK_CONSTRAINT = "stock_constraint"
    WORKFLOW_CONSTRAINT = "workflow_constraint"
    PRECONDITION_REQUIRED = "precondition_required"
    CUSTOM = "custom"


def normalize_error_type(
    status_code: int,
    error_message: str = "",
    constraint_type: str = ""
) -> ViolationErrorType:
    """
    Normalize raw error info to ViolationErrorType.
    
    Args:
        status_code: HTTP status code (explicit int, not string)
        error_message: Error message for additional context
        constraint_type: Optional constraint type from IR
        
    Returns:
        Normalized ViolationErrorType
    """
    msg_lower = error_message.lower() if error_message else ""
    
    # Explicit status code checks (no string matching)
    if status_code == 404:
        return ViolationErrorType.MISSING_PRECONDITION
    
    if status_code == 422:
        # Business logic keywords
        if any(kw in msg_lower for kw in ["status", "stock", "workflow", "transition", "constraint"]):
            return ViolationErrorType.BUSINESS_LOGIC
        # Precondition keywords
        if "precondition" in msg_lower:
            return ViolationErrorType.MISSING_PRECONDITION
        # Default 422 → schema validation
        return ViolationErrorType.SCHEMA_VALIDATION
    
    if status_code == 500:
        return ViolationErrorType.INTERNAL_ERROR
    
    return ViolationErrorType.UNKNOWN


def normalize_constraint_type(raw_type: str) -> ConstraintType:
    """
    Normalize raw constraint type string to ConstraintType enum.
    
    Args:
        raw_type: Raw constraint type string from IR or error
        
    Returns:
        Normalized ConstraintType
    """
    type_lower = raw_type.lower() if raw_type else ""
    
    if "status" in type_lower or "transition" in type_lower:
        return ConstraintType.STATUS_TRANSITION
    
    if "stock" in type_lower or "quantity" in type_lower or "inventory" in type_lower:
        return ConstraintType.STOCK_CONSTRAINT
    
    if "workflow" in type_lower or "precondition" in type_lower:
        return ConstraintType.WORKFLOW_CONSTRAINT
    
    if type_lower == "custom":
        return ConstraintType.CUSTOM
    
    # Default to precondition for unknown types
    return ConstraintType.PRECONDITION_REQUIRED


# Constants for routing decisions
SERVICE_REPAIR_CONSTRAINTS = {
    ConstraintType.STATUS_TRANSITION,
    ConstraintType.STOCK_CONSTRAINT,
    ConstraintType.WORKFLOW_CONSTRAINT,
    ConstraintType.PRECONDITION_REQUIRED,
}

MANUAL_REVIEW_CONSTRAINTS = {
    ConstraintType.CUSTOM,
}


def should_route_to_service_repair(
    status_code: int,
    constraint_type: str = ""
) -> bool:
    """
    Determine if violation should be routed to SERVICE repair.
    
    Args:
        status_code: HTTP status code (explicit int)
        constraint_type: Optional constraint type from IR
        
    Returns:
        True if should go to SERVICE repair, False for SCHEMA repair
    """
    # 404 always goes to SERVICE (precondition issue)
    if status_code == 404:
        return True
    
    # Check constraint type
    if constraint_type:
        normalized = normalize_constraint_type(constraint_type)
        return normalized in SERVICE_REPAIR_CONSTRAINTS
    
    return False

